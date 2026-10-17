"""MOT (motion / animation) chunk parser for DMC3.

A ``MOT`` chunk uses the **size-prefixed** framing::

    +0x00  u32     header_size
    +0x04  char[4] "MOT\\0"
    +0x08  ...
    +0x50  ...     track payload

Only the fields listed below are backed by evidence.  See docs/EVIDENCE.md
(E-003) and docs/FORMATS.md; the observed *distributions* are recorded there.

Verified (statistics over 840 MOT chunks in 194 PAC files):

* ``+0x00`` header size is ``0x50`` in 839/840 chunks (one is ``0x60``).
* ``+0x04`` is always the ASCII magic ``MOT\\0``.
* ``+0x0C`` and ``+0x14`` are ``f32`` and always equal each other; their values
  are plausible animation durations in seconds (29 .. 115 in the sample).
* ``header_size == 0x22 + 2 * len(table)`` holds, with ``table`` read from
  ``+0x22``.  For the common ``0x50`` header that is exactly **23** ``u16``
  table entries.
* ``+0x1A`` and ``+0x1C`` are small counts. ``+0x1C`` is 24 in 821/840 chunks
  and 23 in 18; 24 is consistent with a 24-bone skeleton.

Inferred, **not** proven:

* ``+0x1C`` is the bone count.  The table at ``+0x22`` is therefore *one short*
  of the bone count, so it is not a naive per-bone array.
* ``+0x18`` is a flag (0 or 1); ``+0x1E``/``+0x20`` are counters or byte sizes.

Unknown (open issues):

* the meaning of the ``+0x22`` table (23 entries in **all** 840 chunks; usually
  56, sometimes 0 or 504).
* how the 8-byte groups inside a record encode keyframes (see E-019).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .pac import Chunk, f32, u16, u32

MOT_MAGIC = b"MOT\x00"

HEADER_MIN = 0x20
TABLE_OFFSET = 0x22
TABLE_MAX = 23
HEADER_SIZE_COMMON = 0x50


class MotError(ValueError):
    """Raised when a MOT chunk does not match the observed layout."""


def is_mot(chunk: Chunk) -> bool:
    """True when ``chunk`` carries the MOT magic under either framing."""
    return chunk.tag == MOT_MAGIC


@dataclass(frozen=True)
class MotHeader:
    """Fields of a MOT header that are supported by evidence."""

    header_size: int
    duration: float
    duration_dup: float
    flag_a: int
    count_a: int
    count_b: int
    unknown_1e: int
    unknown_20: int
    table: List[int] = field(default_factory=list)

    @property
    def payload_offset(self) -> int:
        """Chunk-relative offset where track payload begins."""
        return self.header_size

    @property
    def durations_match(self) -> bool:
        return self.duration == self.duration_dup

    @property
    def likely_bone_count(self) -> int:
        """``+0x1C`` — the skeleton bone count this project infers, but has not proven."""
        return self.count_b

    def is_common_shape(self) -> bool:
        """True when the chunk matches the dominant 0x50/23-entry shape."""
        return self.header_size == HEADER_SIZE_COMMON and len(self.table) == TABLE_MAX


def parse_mot(chunk: Chunk) -> MotHeader:
    """Parse the header of a size-prefixed ``MOT`` chunk."""
    data = chunk.data
    if chunk.tag != MOT_MAGIC:
        raise MotError(f"chunk is not a MOT payload (tag={chunk.tag!r})")
    if chunk.tag_offset != 4:
        raise MotError("unsupported MOT framing: magic is not size-prefixed")
    if len(data) < HEADER_MIN:
        raise MotError("MOT chunk shorter than its minimum header")

    header_size = u32(data, 0x00)
    if header_size < HEADER_MIN or header_size % 2 != 0:
        raise MotError(f"implausible MOT header size {header_size}")
    if header_size > len(data):
        raise MotError(
            f"MOT header size 0x{header_size:X} extends past the chunk end"
        )

    table_len = 0
    if header_size > TABLE_OFFSET:
        table_len = (header_size - TABLE_OFFSET) // 2
    table_len = min(table_len, TABLE_MAX, (len(data) - TABLE_OFFSET) // 2)
    table = [u16(data, TABLE_OFFSET + 2 * i) for i in range(max(0, table_len))]

    return MotHeader(
        header_size=header_size,
        duration=f32(data, 0x0C),
        duration_dup=f32(data, 0x14),
        flag_a=u16(data, 0x18),
        count_a=u16(data, 0x1A),
        count_b=u16(data, 0x1C),
        unknown_1e=u16(data, 0x1E),
        unknown_20=u16(data, 0x20),
        table=table,
    )


def parse_mot_from_bytes(payload: bytes) -> MotHeader:
    """Convenience wrapper for callers holding a bare payload."""
    return parse_mot(Chunk(index=0, offset=0, span=len(payload), data=payload))


def maybe_track_payload(chunk: Chunk) -> Optional[bytes]:
    """Return everything after the MOT header, or ``None`` if the chunk is invalid.

    The payload length is not stored, so this returns the remainder of the
    chunk (an upper bound that may include padding).
    """
    try:
        header = parse_mot(chunk)
    except MotError:
        return None
    return chunk.data[header.payload_offset:]


# ---------------------------------------------------------------------------
# Payload: the record list (evidence E-019)
# ---------------------------------------------------------------------------
#
# After the header comes::
#
#     u32  record_count
#     record_count x {
#         u16 size          total record size in bytes
#         u16 groups
#         u16 field_a       observed 3
#         u16 field_b       observed 0
#         (size - 8) bytes  data
#     }
#     tail                 0..12 bytes of zero padding
#
# Verified on **all 840 MOT chunks in the install** (0 walk failures, 59,269
# records) with ``record_count`` taken from the stored value.  In 796/840 chunks
# every record also satisfies ``size == 8 * (groups + 4)``, i.e.
# ``size - 8 == 8 * (groups + 3)``; the remaining 44 have at least one record
# that does not, so the relation is strong but not universal.
#
# The meaning of the 8-byte groups is still open (issue F4).

RECORD_HEADER_SIZE = 8
MAX_TAIL_BYTES = 16


@dataclass(frozen=True)
class MotRecord:
    """One record of a MOT payload."""

    index: int
    offset: int
    """Chunk-relative offset of the record's 8-byte header."""

    size: int
    """Total record size, header included."""

    groups: int
    """The ``u16`` at ``+2``.  Usually ``size // 8 - 4``."""

    field_a: int
    field_b: int
    data: bytes
    """``size - 8`` bytes of record payload."""

    @property
    def size_is_consistent(self) -> bool:
        """True when ``size == 8 * (groups + 4)`` (holds for 796/840 chunks)."""
        return self.size == 8 * (self.groups + 4)

    @property
    def group_count(self) -> int:
        return len(self.data) // 8

    def group_bytes(self) -> List[bytes]:
        """The record data split into 8-byte groups."""
        return [self.data[i:i + 8] for i in range(0, len(self.data) - 7, 8)]


@dataclass
class MotPayload:
    """A fully walked MOT payload."""

    record_count: int
    records: List[MotRecord] = field(default_factory=list)
    tail: bytes = b""

    @property
    def decoded(self) -> int:
        return len(self.records)

    @property
    def complete(self) -> bool:
        """True when the stored record count was reached and the tail is small."""
        return self.decoded == self.record_count and len(self.tail) <= MAX_TAIL_BYTES

    @property
    def all_sizes_consistent(self) -> bool:
        return all(r.size_is_consistent for r in self.records)

    def group_histogram(self) -> dict:
        histogram: dict = {}
        for record in self.records:
            histogram[record.groups] = histogram.get(record.groups, 0) + 1
        return histogram


def walk_records(chunk: Chunk) -> MotPayload:
    """Walk the record list of a MOT chunk.

    Raises :class:`MotError` if the payload does not parse, so callers that want
    a best-effort result should use :func:`try_walk_records`.
    """
    header = parse_mot(chunk)
    payload = chunk.data[header.payload_offset:]
    if len(payload) < 4:
        raise MotError("MOT payload too short to hold a record count")

    record_count = u32(payload, 0)
    position = 4
    records: List[MotRecord] = []

    for index in range(record_count):
        if position + RECORD_HEADER_SIZE > len(payload):
            raise MotError(
                f"record {index} header runs past the payload "
                f"(+0x{position:X} of 0x{len(payload):X})"
            )
        size = u16(payload, position)
        groups = u16(payload, position + 2)
        field_a = u16(payload, position + 4)
        field_b = u16(payload, position + 6)

        if size < RECORD_HEADER_SIZE:
            raise MotError(f"record {index} has an invalid size {size}")
        if position + size > len(payload):
            raise MotError(
                f"record {index} (size {size}) runs past the payload "
                f"(+0x{position:X} of 0x{len(payload):X})"
            )

        records.append(
            MotRecord(
                index=index,
                offset=header.payload_offset + position,
                size=size,
                groups=groups,
                field_a=field_a,
                field_b=field_b,
                data=payload[position + RECORD_HEADER_SIZE:position + size],
            )
        )
        position += size

    return MotPayload(
        record_count=record_count,
        records=records,
        tail=payload[position:],
    )


def try_walk_records(chunk: Chunk) -> Optional[MotPayload]:
    """Like :func:`walk_records` but returns ``None`` instead of raising."""
    try:
        return walk_records(chunk)
    except MotError:
        return None
