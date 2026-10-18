"""DMC3 ``SHW `` chunk header reader.

``SHW `` chunks are the plain-tagged shader/material payloads inside a PAC
container (evidence E-002).  Only the header fields that are **observed**
across real archives are exposed here; the header at +0x30/+0x38/+0x40/+0x48
points at sub-tables, of which the +0x38 index buffer and +0x40 position
buffer are structurally decoded (evidence E-038).  The texture binding and the
remaining payload semantics stay open (issue F2).

Header layout as read from the four ``SHW `` chunks of ``pl021.pac``
(slots 8, 14, 24, 26; slots 24 and 26 are byte-identical), all integers
little-endian::

    +0x00  char[4]  "SHW "
    +0x04  f32      0.5 (0x3F000000) in every observed chunk
    +0x08  u32      0 in every observed chunk
    +0x0C  u32      0 in every observed chunk   ([UNKNOWN] purpose)
    +0x10  u32      varies per chunk   (0x00011811, 0x00002707, 0x00020101, ...)
    +0x14  u32      varies per chunk   (100, 102, 0x000315D8, ...)
    +0x18  u32      0 in every observed chunk
    +0x1C  u32      0 in every observed chunk   ([UNKNOWN] purpose)
    +0x20  u16      varies per chunk   (e.g. 0x000A)
    +0x22  u16      varies per chunk   (e.g. 0x0010)
    +0x24  u32      0 in every observed chunk
    +0x28  u32      0 in every observed chunk
    +0x2C  u32      0 in every observed chunk
    +0x30  u32      varies per chunk   (0x460, 0x1E0, 0x60, 0x60; points at a
                                     16-byte-block index table in all four)
    +0x34  u32      0 in every observed chunk
    +0x38  u32      varies per chunk   (0x560, 0x460, 0x480, 0x480)
    +0x3C  u32      0 in every observed chunk
    +0x40  u32      varies per chunk   (0x5E0, 0x5A0, 0x690, 0x690)
    +0x44  u32      0 in every observed chunk
    +0x48  u32      varies per chunk   (0x680, 0x700, 0x900, 0x900)
    +0x4C  u32      0 in every observed chunk
    +0x50  zero bytes                         (16 bytes of padding)

The four varying fields at +0x30/+0x38/+0x40/+0x48 each point at a sub-table
inside the chunk (+0x30's table holds three small u32 indices plus a zero per
16-byte entry in all four chunks); the sub-table layouts and the fields'
meanings are [UNKNOWN] and deliberately not decoded here.

See docs/EVIDENCE.md E-036 for the raw-byte observations and docs/FORMATS.md
§5 for the spec.  This module never writes into a game installation.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Optional

from .pac import Chunk, f32, u16, u32

TAG_SHADER = b"SHW "
"""The plain chunk tag that identifies a ``SHW `` chunk."""

HEADER_SIZE = 0x50
"""Header size covered by this reader (through the field at +0x4C)."""


@dataclass(frozen=True)
class ShwHeader:
    """Fields of a ``SHW `` chunk header backed by evidence (E-036).

    All u32/f32 fields below are **verified bytes**; only the constant-ness
    of some of them (4/4 chunks for ``alpha`` and the zero fields) reaches
    [INFERRED].  The varying fields' meanings are [UNKNOWN] and are
    deliberately not named beyond their offset.
    """

    alpha: float
    """``+0x04`` — f32, 0.5 in every observed chunk."""

    field_08: int
    """``+0x08`` — u32, 0 in every observed chunk."""

    field_0c: int
    """``+0x0C`` — u32, 0 in every observed chunk. Purpose [UNKNOWN]."""

    field_10: int
    """``+0x10`` — u32, varies per chunk (e.g. 0x00011811). Meaning [UNKNOWN]."""

    field_14: int
    """``+0x14`` — u32, varies per chunk (e.g. 100, 102, 0x315D8). Meaning [UNKNOWN]."""

    field_18: int
    """``+0x18`` — u32, 0 in every observed chunk."""

    field_1c: int
    """``+0x1C`` — u32, 0 in every observed chunk. Purpose [UNKNOWN]."""

    pair_20_0: int
    """``+0x20`` — u16, varies per chunk (e.g. 0x000A). Meaning [UNKNOWN]."""

    pair_20_1: int
    """``+0x22`` — u16, varies per chunk (e.g. 0x0010). Meaning [UNKNOWN]."""

    field_24: int
    """``+0x24`` — u32, 0 in every observed chunk."""

    field_28: int
    """``+0x28`` — u32, 0 in every observed chunk."""

    field_2c: int
    """``+0x2C`` — u32, 0 in every observed chunk."""

    field_30: int
    """``+0x30`` — u32, varies per chunk (0x460, 0x1E0, 0x60, 0x60).  It
    points at a sub-table of 16-byte entries (three small u32 indices plus a
    zero) in all four observed chunks — an inference from the bytes, not
    engine-verified; the field's meaning is [UNKNOWN]."""

    field_34: int
    """``+0x34`` — u32, 0 in every observed chunk."""

    field_38: int
    """``+0x38`` — u32, varies per chunk.  Chunk-relative offset of a buffer of
    ``[u16 i0, u16 i1, u16 i2, u16 0]`` index entries; decoded by
    :func:`parse_shw_sub_tables` (structure [PARTIAL], semantics [UNKNOWN];
    evidence E-038)."""

    field_3c: int
    """``+0x3C`` — u32, 0 in every observed chunk."""

    field_40: int
    """``+0x40`` — u32, varies per chunk.  Chunk-relative offset of a buffer of
    ``[f32 x, f32 y, f32 z, f32 1.0]`` position entries; decoded by
    :func:`parse_shw_sub_tables` (structure [PARTIAL], semantics [UNKNOWN];
    evidence E-038)."""

    field_44: int
    """``+0x44`` — u32, 0 in every observed chunk."""

    field_48: int
    """``+0x48`` — u32, varies per chunk.  Chunk-relative offset of a further
    sub-table (begins with a constant-byte run, then a u32 stream; layout and
    meaning [UNKNOWN]; evidence E-038)."""

    field_4c: int
    """``+0x4C`` — u32, 0 in every observed chunk."""

    @classmethod
    def parse(cls, chunk: Chunk) -> "ShwHeader":
        """Parse the header of a plain-tagged ``SHW `` chunk."""
        if chunk.tag != TAG_SHADER:
            raise ValueError(
                f"chunk is not a SHW payload (tag={chunk.tag!r})"
            )
        data = chunk.data
        if len(data) < HEADER_SIZE:
            raise ValueError(
                f"SHW chunk only {len(data)} bytes, need {HEADER_SIZE} for the header"
            )
        return cls(
            alpha=f32(data, 0x04),
            field_08=u32(data, 0x08),
            field_0c=u32(data, 0x0C),
            field_10=u32(data, 0x10),
            field_14=u32(data, 0x14),
            field_18=u32(data, 0x18),
            field_1c=u32(data, 0x1C),
            pair_20_0=u16(data, 0x20),
            pair_20_1=u16(data, 0x22),
            field_24=u32(data, 0x24),
            field_28=u32(data, 0x28),
            field_2c=u32(data, 0x2C),
            field_30=u32(data, 0x30),
            field_34=u32(data, 0x34),
            field_38=u32(data, 0x38),
            field_3c=u32(data, 0x3C),
            field_40=u32(data, 0x40),
            field_44=u32(data, 0x44),
            field_48=u32(data, 0x48),
            field_4c=u32(data, 0x4C),
        )


def maybe_shw_header(chunk: Chunk) -> Optional[ShwHeader]:
    """Like :meth:`ShwHeader.parse` but returns ``None`` for invalid chunks."""
    try:
        return ShwHeader.parse(chunk)
    except (ValueError, IndexError):
        return None


# ---------------------------------------------------------------------------
# Payload sub-tables (the part of issue F2 that is still [UNKNOWN] in meaning)
# ---------------------------------------------------------------------------

INDEX_STRIDE = 8
"""Stride of the index table at ``SHW +0x38``: ``[u16 i0, u16 i1, u16 i2, u16 0]``."""

POSITION_STRIDE = 16
"""Stride of the position table at ``SHW +0x40``: ``[f32 x, f32 y, f32 z, f32 1.0]``."""


@dataclass(frozen=True)
class ShwIndexTable:
    """Triangle index buffer pointed at by ``SHW +0x38`` (evidence E-038).

    Layout: ``[u16 i0, u16 i1, u16 i2, u16 0]`` repeated ``count`` times.  The
    fourth u16 of every entry is observed to be zero in all four real chunks.
    The count is derived from the pointer difference ``field_40 - field_38``,
    which is a verified invariant across all four ``SHW `` chunks.

    What the indices reference is [UNKNOWN]: for slots 24/26 the indices fall
    within the +0x40 position table, but for slots 8 and 14 the maximum index
    exceeds that table's count, so additional vertex buffers or separate
    sub-meshes may be involved.
    """

    count: int
    """Number of index entries (triangles)."""

    indices: tuple[tuple[int, int, int], ...]
    """The ``(i0, i1, i2)`` triples; the trailing zero u16 of each entry is
    stripped, as it is constantly zero and carries no information."""


@dataclass(frozen=True)
class ShwPositionTable:
    """Vertex position buffer pointed at by ``SHW +0x40`` (evidence E-038).

    Layout: ``[f32 x, f32 y, f32 z, f32 1.0]`` repeated ``count`` times.  The
    w component is observed to be exactly 1.0 in every entry of all four real
    chunks, and the values show left/right symmetry consistent with vertex
    coordinates (e.g. slot 14: ``(-14.87, 4.02, 7.75)`` / ``(+15.30, 4.02, 7.75)``).
    The count is derived from ``field_48 - field_40``, a verified invariant.

    Object-space vs world-space, and which mesh the positions belong to, are
    [UNKNOWN].
    """

    count: int
    """Number of position entries (vertices)."""

    positions: tuple[tuple[float, float, float, float], ...]
    """The ``(x, y, z, w)`` vectors; ``w`` is constantly 1.0 and is retained for
    byte-faithfulness."""


@dataclass(frozen=True)
class ShwSubTables:
    """The two decoded ``SHW`` sub-tables (evidence E-038).

    ``field_38``/``field_40``/``field_48`` are chunk-relative offsets into the
    chunk's data.  Buffer sizes come from the consecutive-pointer differences:

    * index bytes   = ``field_40 - field_38``   (stride 8)
    * position bytes = ``field_48 - field_40``  (stride 16)

    This held exactly for all four real chunks (slots 8, 14, 24, 26).
    """

    index_table: ShwIndexTable
    position_table: ShwPositionTable


def parse_shw_sub_tables(data: bytes, header: ShwHeader) -> ShwSubTables:
    """Decode the index and position sub-tables of a ``SHW `` chunk.

    ``data`` is the chunk's raw bytes (``chunk.data``); the ``field_38``,
    ``field_40`` and ``field_48`` offsets are chunk-relative.  Raises
    ``ValueError`` if a pointer difference is not divisible by the observed
    stride, if a table runs past the end of the data, or if a table offset lies
    inside the header.
    """
    if header.field_38 < HEADER_SIZE:
        raise ValueError(
            f"SHW +0x38 offset {header.field_38:#x} lies inside the 0x{HEADER_SIZE:X}-byte header"
        )
    if header.field_48 > len(data):
        raise ValueError(
            f"SHW +0x48 offset {header.field_48:#x} runs past {len(data)} bytes of chunk data"
        )

    index_bytes = header.field_40 - header.field_38
    position_bytes = header.field_48 - header.field_40
    if index_bytes % INDEX_STRIDE != 0:
        raise ValueError(
            f"SHW index size {index_bytes} is not a multiple of the {INDEX_STRIDE}-byte index stride"
        )
    if position_bytes % POSITION_STRIDE != 0:
        raise ValueError(
            f"SHW position size {position_bytes} is not a multiple of the {POSITION_STRIDE}-byte position stride"
        )

    index_count = index_bytes // INDEX_STRIDE
    position_count = position_bytes // POSITION_STRIDE

    indices: list[tuple[int, int, int]] = []
    for i in range(index_count):
        base = header.field_38 + INDEX_STRIDE * i
        i0, i1, i2, pad = struct.unpack_from("<HHHH", data, base)
        if pad != 0:
            raise ValueError(
                f"SHW index entry {i} has nonzero fourth u16 {pad:#x} (observed 0 in all real chunks)"
            )
        indices.append((i0, i1, i2))

    positions: list[tuple[float, float, float, float]] = []
    for i in range(position_count):
        base = header.field_40 + POSITION_STRIDE * i
        positions.append(struct.unpack_from("<4f", data, base))

    return ShwSubTables(
        index_table=ShwIndexTable(count=index_count, indices=tuple(indices)),
        position_table=ShwPositionTable(count=position_count, positions=tuple(positions)),
    )


def maybe_shw_sub_tables(
    data: bytes, header: ShwHeader
) -> Optional[ShwSubTables]:
    """Like :func:`parse_shw_sub_tables` but returns ``None`` on invalid input."""
    try:
        return parse_shw_sub_tables(data, header)
    except ValueError:
        return None
