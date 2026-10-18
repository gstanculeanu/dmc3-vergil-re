"""Read-only face-value parser for the GoW3R ``DEPENDENCYGRAPH.IFF`` WadGraph registry.

Status (evidence E-045): the **header** and the **32-byte name records** of the
registry are decoded from the real file. What remains unknown is the exact
relation between a record's ``name_offset`` field and the NUL-terminated name
strings (some records point exactly at a name, others land within a few bytes),
and the meaning of ``field_b`` / ``field_c`` / the constant trailer. This module
parses exactly the observed layout and claims no semantics beyond it.

There is no writer: the registry is treated as read-only reconnaissance. Binding
a registry name to a physical WAD (issue G10) is not resolved by this parser.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import List, Optional

HEADER_SIZE = 0x40
BANNER_OFFSET = 0x08
BANNER_FIELD = 0x38
RECORD_SIZE = 0x20
RECORD_START = 0x40

#: Every record carries this sentinel at +0x12 (observed in every record scanned).
RECORD_SENTINEL = 0xFFFFFFFFFFFFFFFF
#: Every record ends with this constant u32 at +0x1C (observed in every record scanned).
TRAILER_CONSTANT = 0x55555555


class WadGraphError(ValueError):
    """Raised when a file does not look like a WadGraph registry."""


@dataclass(frozen=True)
class WadGraphHeader:
    """The 0x40-byte file header (observed on ``DEPENDENCYGRAPH.IFF``).

    ``field_00`` was 23 and ``field_02`` was 1 on the only sample; ``size_field``
    was 265,712, i.e. the file size minus the 0x40-byte header. All meanings
    are [UNKNOWN]. The banner is zero-padded, e.g. ``"WadGraph"``.
    """

    field_00: int
    field_02: int
    size_field: int
    banner: str

    @property
    def looks_valid(self) -> bool:
        return bool(self.banner)


@dataclass(frozen=True)
class WadGraphRecord:
    """One 32-byte registry record (observed layout, all offsets file-relative).

    ``name_offset`` is a u32 that correlates with the NUL-terminated name
    strings stored later in the file: on the real sample some records point
    exactly at a name (e.g. ``name_offset == 241454`` -> ``"Stub_1472"``),
    while early records land within a few bytes of a name start. The exact
    relation is [UNKNOWN].

    ``field_b`` (u32, +0x08) and ``field_c`` (u16, +0x10) are [UNKNOWN];
    ``field_d`` (u32, +0x0C) was 0 or 0x00F00000 on the sample. The trailing
    u32 at +0x1C was constantly 0x55555555.
    """

    offset: int            # file offset of this record
    name_offset: int       # u32 @ +0x00
    field_b: int           # u32 @ +0x08, [UNKNOWN]
    field_d: int           # u32 @ +0x0C, [UNKNOWN]
    field_c: int           # u16 @ +0x10, [UNKNOWN]
    pad_byte: int          # u8  @ +0x1B, [UNKNOWN] (observed 0x00/0x02/0x24/0x34)
    trailer: int           # u32 @ +0x1C, constantly 0x55555555


@dataclass(frozen=True)
class WadGraph:
    """Face-value parse of a WadGraph registry file.

    ``records`` holds every 32-byte window from offset 0x40 that matches the
    observed record pattern (sentinel -1 at +0x12, zero u32 at +0x04/+0x0C,
    zero byte at +0x1A, trailer 0x55555555 at +0x1C). Windows that do not
    match are skipped, so the record list may be non-contiguous; gaps are
    [UNKNOWN] structure.
    """

    header: WadGraphHeader
    records: List[WadGraphRecord] = field(default_factory=list)


def parse_header(data: bytes) -> WadGraphHeader:
    if len(data) < HEADER_SIZE:
        raise WadGraphError(f"file too small ({len(data)} bytes) for a WadGraph header")
    field_00 = int.from_bytes(data[0x00:0x02], "little")
    field_02 = int.from_bytes(data[0x02:0x04], "little")
    size_field = int.from_bytes(data[0x04:0x08], "little")
    end = data.find(b"\x00", BANNER_OFFSET)
    if end < 0:
        end = BANNER_OFFSET + BANNER_FIELD
    banner = data[BANNER_OFFSET:end].decode("latin-1", "replace")
    return WadGraphHeader(field_00=field_00, field_02=field_02,
                          size_field=size_field, banner=banner)


def _record_matches(data: bytes, offset: int) -> bool:
    if offset + RECORD_SIZE > len(data):
        return False
    if int.from_bytes(data[offset + 0x04:offset + 0x08], "little") != 0:
        return False
    # +0x0C (field_d) was 0 or 0x00F00000 on the sample; it is not a validity
    # signal and is deliberately not checked here.
    if int.from_bytes(data[offset + 0x12:offset + 0x1A], "little") != RECORD_SENTINEL:
        return False
    if data[offset + 0x1A] != 0:
        return False
    if int.from_bytes(data[offset + 0x1C:offset + 0x20], "little") != TRAILER_CONSTANT:
        return False
    return True


def parse_records(data: bytes) -> List[WadGraphRecord]:
    """Scan stride-0x20 windows from 0x40 and collect every matching record."""
    records: List[WadGraphRecord] = []
    offset = RECORD_START
    while offset + RECORD_SIZE <= len(data):
        if _record_matches(data, offset):
            name_offset = int.from_bytes(data[offset:offset + 0x04], "little")
            field_b = int.from_bytes(data[offset + 0x08:offset + 0x0C], "little")
            field_d = int.from_bytes(data[offset + 0x0C:offset + 0x10], "little")
            field_c = int.from_bytes(data[offset + 0x10:offset + 0x12], "little")
            pad_byte = data[offset + 0x1B]
            records.append(WadGraphRecord(
                offset=offset, name_offset=name_offset, field_b=field_b,
                field_d=field_d, field_c=field_c, pad_byte=pad_byte,
                trailer=TRAILER_CONSTANT,
            ))
        offset += RECORD_SIZE
    return records


def parse(data: bytes) -> WadGraph:
    """Parse a WadGraph file at face value (header + every matching record)."""
    return WadGraph(header=parse_header(data), records=parse_records(data))


def record_name(data: bytes, record: WadGraphRecord, max_len: int = 0x80) -> Optional[str]:
    """Best-effort name for a record.

    Reads a NUL-terminated printable string at ``record.name_offset``.
    Returns ``None`` when the offset does not land on such a string; the
    name_offset -> string relation is [UNKNOWN], so this is a heuristic, not
    a guaranteed binding.
    """
    start = record.name_offset
    if start < 0 or start >= len(data):
        return None
    end = data.find(b"\x00", start)
    if end < 0 or end - start > max_len or end - start < 1:
        return None
    raw = data[start:end]
    if not all(32 <= b < 127 for b in raw):
        return None
    return raw.decode("latin-1")


def is_wadgraph(data: bytes) -> bool:
    try:
        return parse_header(data).looks_valid
    except WadGraphError:
        return False
