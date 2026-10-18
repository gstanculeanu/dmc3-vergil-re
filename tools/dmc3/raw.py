"""Raw (untagged) PAC chunk payloads.

Some PAC slots carry no ASCII tag: ``pl021.pac`` has nine occupied untagged
slots (0, 5, 6, 7, 9, 10, 11, 21, 22) holding bone transforms, UV tables,
primitive groups and other untagged tables (evidence E-008).  This module
decodes only what is *observed* in real bytes; every field meaning is
[UNKNOWN] until engine ground truth arrives.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .pac import f32, u16, u32

SLOT0_HEADER_SIZE = 0x18
"""Size of the decoded header of ``pl021.pac`` slot 0: six u32s."""

SLOT10_PAIR_COUNT = 23
"""Number of u16 pairs in the leading table of ``pl021.pac`` slot 10.

Observed (evidence E-037): the table occupies bytes +0x00..+0x5B (23 pairs,
stride 4) and is followed by a little-endian f32 stream from +0x5C to the end
of the chunk.  Whether the count is stored somewhere in the chunk or is fixed
is [UNKNOWN]; this constant locks the single observed layout.
"""


@dataclass(frozen=True)
class Slot10Table:
    """Leading table of ``pl021.pac`` slot 10 (evidence E-037).

    Observed at file offset 0x077ED0 of ``pl021.pac`` (chunk-relative body
    starts at +0x00)::

        +0x00  u16 pairs, stride 4, ``SLOT10_PAIR_COUNT`` pairs
        +0x5C  little-endian f32 stream to end of chunk

    Every field meaning is [UNKNOWN]: the pairs look like index/offset pairs
    (first element constantly 92 == 0x5C, i.e. the table's byte size, in the
    observed chunk) and the f32 stream holds small magnitude values, but neither
    is established from bytes alone.  The parser reads exactly the observed
    layout and interprets nothing.
    """

    pairs: tuple[tuple[int, int], ...]
    """``SLOT10_PAIR_COUNT`` little-endian u16 pairs, stride 4."""

    floats: tuple[float, ...]
    """Little-endian f32s from +0x5C to the end of the chunk."""

    @classmethod
    def parse(cls, data: bytes) -> "Slot10Table":
        """Parse the slot-10 layout from ``data`` (chunk-relative bytes)."""
        pair_bytes = 4 * SLOT10_PAIR_COUNT
        if len(data) < pair_bytes:
            raise ValueError(
                f"slot-10 table only {len(data)} bytes, need {pair_bytes} "
                f"for {SLOT10_PAIR_COUNT} pairs"
            )
        pairs = tuple(
            (u16(data, 4 * index), u16(data, 4 * index + 2))
            for index in range(SLOT10_PAIR_COUNT)
        )
        remainder = len(data) - pair_bytes
        floats = tuple(
            f32(data, pair_bytes + 4 * index)
            for index in range(remainder // 4)
        )
        return cls(pairs=pairs, floats=floats)


def maybe_slot10_table(data: bytes) -> Optional[Slot10Table]:
    """Like :meth:`Slot10Table.parse` but returns ``None`` on short input."""
    try:
        return Slot10Table.parse(data)
    except ValueError:
        return None


@dataclass(frozen=True)
class RawHeader:
    """Leading header of a raw chunk, as observed in ``pl021.pac`` slot 0.

    Observed at file offset 0x80 of ``pl021.pac`` (evidence E-033): six
    little-endian u32s (5, 43, 22, 43, 5, 1), then zero bytes until
    body+0x0800 where small sub-fields appear; an embedded ``DDS `` magic is
    present at body+0x0870 (file offset 0x8F0).  Every field's meaning is
    [UNKNOWN] and is deliberately not named beyond its offset.  The rest of
    the slot's ~235 KB body is undecoded (issue F3).
    """

    field_00: int
    field_04: int
    field_08: int
    field_0c: int
    field_10: int
    field_14: int

    @classmethod
    def parse(cls, data: bytes) -> "RawHeader":
        """Parse the first 24 bytes of a raw chunk payload."""
        if len(data) < SLOT0_HEADER_SIZE:
            raise ValueError(
                f"raw chunk only {len(data)} bytes, need {SLOT0_HEADER_SIZE} for the header"
            )
        return cls(*(u32(data, 4 * index) for index in range(6)))


def maybe_raw_header(data: bytes) -> Optional[RawHeader]:
    """Like :meth:`RawHeader.parse` but returns ``None`` on short input."""
    try:
        return RawHeader.parse(data)
    except ValueError:
        return None
