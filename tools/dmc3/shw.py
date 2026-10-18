"""DMC3 ``SHW `` chunk header reader.

``SHW `` chunks are plain-tagged payloads inside a PAC container (evidence
E-002).  A chunk is a **stream of records**, each a small closed mesh::

    [u32 i0, u32 i1, u32 i2, u32 0] x N   triangles (16 B each)
    [u16 n0, u16 n1, u16 n2, u16 0] x N   per-triangle edge adjacency (8 B each)
    [f32 x, f32 y, f32 z, f32 1.0]  x P   positions (16 B each)
    [u8  value]                     x P   one byte per position, NUL-padded to
                                          a 16-byte boundary

Record 0's four sections are named by the header fields ``+0x30`` (triangles),
``+0x38`` (adjacency), ``+0x40`` (positions) and ``+0x48`` (the per-position byte
array); every later record simply follows the previous record's array.  This
was decoded on all 58 ``SHW `` chunks of the install (591 records, E-103):

* ``+0x30`` — the **triangle table**: ``[u32 i0, u32 i1, u32 i2, u32 0]`` per
  triangle, indexing the ``+0x40`` positions (E-102).
* ``+0x38`` — the **adjacency table**: ``[u16 n0, u16 n1, u16 n2, u16 0]`` per
  triangle, naming the three edge-neighbour *triangles* (E-102).  E-038 read
  these as a vertex index buffer; that reading is disproved (E-102).
* ``+0x40`` — the **position table**: ``[f32 x, f32 y, f32 z, f32 1.0]`` per
  vertex (E-038).
* ``+0x48`` — the first record's **per-position byte array** (one ``u8`` per
  position, constant within a record on 591/591 records), *not* a further
  table (E-103, correcting E-038/E-102).  The array is followed by NUL padding
  to a 16-byte boundary, then the next record.

The ``+0x20`` u16 pair is record 0's ``(position_count, triangle_count)`` on
58/58 chunks (E-103).  The meaning of the per-position byte, ``alpha``,
``field_10`` and ``field_14``, the texture binding and the remaining payload
semantics stay open (issue F2).  ``SHW `` being shadow-volume geometry rather
than a material payload is [INFERRED], not established.

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
    +0x20  u16      varies per chunk   (e.g. 0x000A = record 0's position count,
                                       E-103)
    +0x22  u16      varies per chunk   (e.g. 0x0010 = record 0's triangle count,
                                       E-103)
    +0x24  u32      0 in every observed chunk
    +0x28  u32      0 in every observed chunk
    +0x2C  u32      0 in every observed chunk
    +0x30  u32      varies per chunk   (0x460, 0x1E0, 0x60, 0x60; offset of the
                                      triangle table, E-102)
    +0x34  u32      0 in every observed chunk
    +0x38  u32      varies per chunk   (0x560, 0x460, 0x480, 0x480; offset of
                                      the adjacency table, E-102)
    +0x3C  u32      0 in every observed chunk
    +0x40  u32      varies per chunk   (0x5E0, 0x5A0, 0x690, 0x690; offset of
                                      the position table, E-038)
    +0x44  u32      0 in every observed chunk
    +0x48  u32      varies per chunk   (0x680, 0x700, 0x900, 0x900; offset of
                                      the first record's per-position u8 array,
                                      E-103)
    +0x4C  u32      0 in every observed chunk
    +0x50  zero bytes                         (16 bytes of padding)

The four varying fields at +0x30/+0x38/+0x40/+0x48 name the four sections of
**record 0**; later records follow it (E-103, :func:`parse_shw_records`).  See
docs/EVIDENCE.md E-036, E-102 and E-103 for the raw-byte observations and
docs/FORMATS.md §5 for the spec.  This module never writes into a game
installation.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Optional

from .pac import Chunk, align_up, f32, u16, u32

TAG_SHADER = b"SHW "
"""The plain chunk tag that identifies a ``SHW `` chunk."""

HEADER_SIZE = 0x50
"""Header size covered by this reader (through the field at +0x4C)."""

RECORD_ALIGNMENT = 16
"""Records (and their per-position byte arrays) are 16-byte aligned (E-103)."""

POSITION_W_BYTES = b"\x00\x00\x80\x3f"
"""Raw little-endian ``f32`` 1.0 — the fourth component of every position."""


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
    """``+0x20`` — u16, record 0's **position count** on 58/58 chunks (E-103)."""

    pair_20_1: int
    """``+0x22`` — u16, record 0's **triangle count** on 58/58 chunks (E-103)."""

    field_24: int
    """``+0x24`` — u32, 0 in every observed chunk."""

    field_28: int
    """``+0x28`` — u32, 0 in every observed chunk."""

    field_2c: int
    """``+0x2C`` — u32, 0 in every observed chunk."""

    field_30: int
    """``+0x30`` — u32, varies per chunk (0x460, 0x1E0, 0x60, 0x60).  It is the
    chunk-relative offset of the **triangle table** decoded by
    :func:`parse_shw_sub_tables` (E-102; structure [VERIFIED], semantics
    [INFERRED] as the chunk's triangle list)."""

    field_34: int
    """``+0x34`` — u32, 0 in every observed chunk."""

    field_38: int
    """``+0x38`` — u32, varies per chunk.  Chunk-relative offset of the
    **adjacency table**: ``[u16 n0, u16 n1, u16 n2, u16 0]`` per triangle,
    naming edge-neighbour triangle indices (E-102; structure [VERIFIED]).
    E-038 read this as a vertex index buffer; that reading is disproved."""

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
    """``+0x48`` — u32, varies per chunk.  Chunk-relative offset of **record 0's
    per-position byte array**: one ``u8`` per position, constant within the
    record, followed by NUL padding to a 16-byte boundary (E-103, correcting
    E-038/E-102's "further sub-table" reading)."""

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

TRIANGLE_TABLE_OFFSET = 0x30
"""Header offset of the triangle table (``SHW +0x30``)."""

TRIANGLE_STRIDE = 16
"""Stride of the triangle table at ``SHW +0x30``: ``[u32 i0, u32 i1, u32 i2, u32 0]``."""

ADJACENCY_STRIDE = 8
"""Stride of the adjacency table at ``SHW +0x38``: ``[u16 n0, u16 n1, u16 n2, u16 0]``."""

POSITION_STRIDE = 16
"""Stride of the position table at ``SHW +0x40``: ``[f32 x, f32 y, f32 z, f32 1.0]``."""


@dataclass(frozen=True)
class ShwTriangleTable:
    """Triangle list pointed at by ``SHW +0x30`` (evidence E-102).

    Layout: ``[u32 i0, u32 i1, u32 i2, u32 0]`` repeated ``count`` times.  The
    count is derived from ``field_38 - field_30`` (stride 16) and equals the
    ``+0x38`` adjacency entry count.  E-038 saw these entries but did not name
    them; E-102 shows all three indices are distinct and fall within the
    ``+0x40`` position table on 58/58 ``SHW `` chunks in the install, and that
    every position is referenced at least once (58/58).  Reading them as the
    chunk's triangles is [INFERRED] from that structure.
    """

    count: int
    """Number of triangle entries."""

    triangles: tuple[tuple[int, int, int], ...]
    """The ``(i0, i1, i2)`` vertex indices; the fourth u32 is zero on 58/58
    real chunks and is stripped."""

    def references(self, position_count: int) -> bool:
        """True when every index falls inside ``[0, position_count)``."""
        return all(0 <= i < position_count for t in self.triangles for i in t)


@dataclass(frozen=True)
class ShwAdjacencyTable:
    """Per-triangle edge-neighbour table pointed at by ``SHW +0x38`` (E-102).

    Layout: ``[u16 n0, u16 n1, u16 n2, u16 0]`` repeated ``count`` times.  The
    three u16s are **triangle** indices into the ``+0x30`` table, not vertex
    indices: on all 58 ``SHW `` chunks of the install the multiset of values is
    exactly three copies of ``0..count-1``, the relation is symmetric
    (``k in neighbours[n]`` for every ``n in neighbours[k]``), and each
    neighbour triangle shares at least two vertices with the triangle it names
    — i.e. they share an edge.  E-038's "vertex index buffer" reading is
    disproved by the value range alone (``count`` exceeds the position count on
    58/58 chunks).

    The adjacency relation is what a shadow-volume pass needs to find
    silhouette edges; that semantic use is [INFERRED], not established.
    """

    count: int
    """Number of adjacency entries (equal to the triangle count)."""

    neighbours: tuple[tuple[int, int, int], ...]
    """The ``(n0, n1, n2)`` edge-neighbour triangle indices; the fourth u16 is
    zero on 58/58 real chunks and is stripped."""

    def symmetric(self) -> bool:
        """True when every named neighbour names this entry back (58/58 real)."""
        for k, row in enumerate(self.neighbours):
            for n in row:
                if n >= self.count or k not in self.neighbours[n]:
                    return False
        return True

    def three_regular(self) -> bool:
        """True when every triangle index occurs as a neighbour exactly 3 times.

        Holds on 58/58 real chunks; that is the signature of a closed surface
        where every triangle has three edge-adjacent faces.
        """
        counts = [0] * self.count
        for row in self.neighbours:
            for n in row:
                if n >= self.count:
                    return False
                counts[n] += 1
        return all(c == 3 for c in counts)


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
    """The three geometry tables of **record 0** (evidence E-038, E-102).

    ``field_30``/``field_38``/``field_40`` are record 0's chunk-relative
    triangle/adjacency/position offsets.  Buffer sizes come from the
    consecutive-pointer differences:

    * triangle bytes  = ``field_38 - field_30``  (stride 16)
    * adjacency bytes = ``field_40 - field_38``  (stride 8)
    * position bytes  = ``field_48 - field_40``  (stride 16)

    The triangle and adjacency tables always have the same entry count (E-102).
    A chunk normally contains several such records; :func:`parse_shw_records`
    returns the whole stream and this class is the first one's geometry.
    """

    triangle_table: ShwTriangleTable
    adjacency_table: ShwAdjacencyTable
    position_table: ShwPositionTable

    @property
    def consistent(self) -> bool:
        """True when the tables satisfy every structural invariant seen on the
        install: the triangles index the positions, the adjacency names only
        triangles, is symmetric, and is three-regular (E-102)."""
        return (
            self.triangle_table.references(self.position_table.count)
            and self.adjacency_table.count == self.triangle_table.count
            and self.adjacency_table.symmetric()
            and self.adjacency_table.three_regular()
        )

    def shared_edges(self) -> bool:
        """True when every adjacency neighbour shares at least two vertices
        with the triangle that names it (58/58 real chunks, E-102)."""
        triangles = self.triangle_table.triangles
        for k, row in enumerate(self.adjacency_table.neighbours):
            for n in row:
                if n >= len(triangles):
                    return False
                if len(set(triangles[k]) & set(triangles[n])) < 2:
                    return False
        return True


def _build_sub_tables(
    data: bytes,
    triangle_offset: int,
    triangle_count: int,
    position_offset: int,
    position_count: int,
) -> ShwSubTables:
    """Read one record's triangle/adjacency/position tables and validate them."""
    triangles: list[tuple[int, int, int]] = []
    for i in range(triangle_count):
        base = triangle_offset + TRIANGLE_STRIDE * i
        if base + TRIANGLE_STRIDE > len(data):
            raise ValueError(
                f"SHW triangle entry {i} at {base:#x} runs past {len(data)} bytes"
            )
        i0, i1, i2, pad = struct.unpack_from("<IIII", data, base)
        if pad != 0:
            raise ValueError(
                f"SHW triangle entry {i} has nonzero fourth u32 {pad:#x} (observed 0 in all real chunks)"
            )
        triangles.append((i0, i1, i2))

    neighbours: list[tuple[int, int, int]] = []
    adjacency_offset = triangle_offset + TRIANGLE_STRIDE * triangle_count
    for i in range(triangle_count):
        base = adjacency_offset + ADJACENCY_STRIDE * i
        if base + ADJACENCY_STRIDE > len(data):
            raise ValueError(
                f"SHW adjacency entry {i} at {base:#x} runs past {len(data)} bytes"
            )
        n0, n1, n2, pad = struct.unpack_from("<HHHH", data, base)
        if pad != 0:
            raise ValueError(
                f"SHW adjacency entry {i} has nonzero fourth u16 {pad:#x} (observed 0 in all real chunks)"
            )
        neighbours.append((n0, n1, n2))

    positions: list[tuple[float, float, float, float]] = []
    for i in range(position_count):
        base = position_offset + POSITION_STRIDE * i
        if base + POSITION_STRIDE > len(data):
            raise ValueError(
                f"SHW position entry {i} at {base:#x} runs past {len(data)} bytes"
            )
        positions.append(struct.unpack_from("<4f", data, base))

    return ShwSubTables(
        triangle_table=ShwTriangleTable(
            count=triangle_count, triangles=tuple(triangles)
        ),
        adjacency_table=ShwAdjacencyTable(
            count=triangle_count, neighbours=tuple(neighbours)
        ),
        position_table=ShwPositionTable(
            count=position_count, positions=tuple(positions)
        ),
    )


def parse_shw_sub_tables(data: bytes, header: ShwHeader) -> ShwSubTables:
    """Decode **record 0**'s triangle, adjacency and position tables.

    ``data`` is the chunk's raw bytes (``chunk.data``); the ``field_30``,
    ``field_38``, ``field_40`` and ``field_48`` offsets are chunk-relative.
    Raises ``ValueError`` if the offsets are not strictly increasing, if a
    pointer difference is not divisible by the observed stride, if a table runs
    past the end of the data, if a table offset lies inside the header, or if
    the triangle and adjacency counts differ (a 58/58 invariant, E-102).

    A chunk is a stream of records (E-103); use :func:`parse_shw_records` to
    read all of them.
    """
    if header.field_30 < HEADER_SIZE:
        raise ValueError(
            f"SHW +0x30 offset {header.field_30:#x} lies inside the 0x{HEADER_SIZE:X}-byte header"
        )
    if not (
        header.field_30
        < header.field_38
        <= header.field_40
        <= header.field_48
    ):
        raise ValueError(
            "SHW sub-table offsets are not increasing: "
            f"+0x30={header.field_30:#x} +0x38={header.field_38:#x} "
            f"+0x40={header.field_40:#x} +0x48={header.field_48:#x}"
        )
    if header.field_48 > len(data):
        raise ValueError(
            f"SHW +0x48 offset {header.field_48:#x} runs past {len(data)} bytes of chunk data"
        )

    triangle_bytes = header.field_38 - header.field_30
    adjacency_bytes = header.field_40 - header.field_38
    position_bytes = header.field_48 - header.field_40
    if triangle_bytes % TRIANGLE_STRIDE != 0:
        raise ValueError(
            f"SHW triangle size {triangle_bytes} is not a multiple of the {TRIANGLE_STRIDE}-byte triangle stride"
        )
    if adjacency_bytes % ADJACENCY_STRIDE != 0:
        raise ValueError(
            f"SHW adjacency size {adjacency_bytes} is not a multiple of the {ADJACENCY_STRIDE}-byte adjacency stride"
        )
    if position_bytes % POSITION_STRIDE != 0:
        raise ValueError(
            f"SHW position size {position_bytes} is not a multiple of the {POSITION_STRIDE}-byte position stride"
        )

    triangle_count = triangle_bytes // TRIANGLE_STRIDE
    adjacency_count = adjacency_bytes // ADJACENCY_STRIDE
    position_count = position_bytes // POSITION_STRIDE
    if triangle_count != adjacency_count:
        raise ValueError(
            f"SHW triangle count {triangle_count} differs from adjacency count "
            f"{adjacency_count} (equal on every real chunk, E-102)"
        )

    return _build_sub_tables(
        data, header.field_30, triangle_count, header.field_40, position_count
    )


def maybe_shw_sub_tables(
    data: bytes, header: ShwHeader
) -> Optional[ShwSubTables]:
    """Like :func:`parse_shw_sub_tables` but returns ``None`` on invalid input."""
    try:
        return parse_shw_sub_tables(data, header)
    except ValueError:
        return None


@dataclass(frozen=True)
class ShwRecord:
    """One record of a ``SHW `` chunk's record stream (evidence E-103).

    Layout (chunk-relative, 16-byte aligned start)::

        triangle table   [u32 i0, u32 i1, u32 i2, u32 0] x N
        adjacency table  [u16 n0, u16 n1, u16 n2, u16 0] x N
        position table   [f32 x, f32 y, f32 z, f32 1.0]  x P
        byte array       [u8 value]                      x P, then NUL padding
                                                            to a 16-byte boundary

    Record 0's four offsets are the header fields ``+0x30``/``+0x38``/``+0x40``/
    ``+0x48``; each later record starts at the previous record's padded array
    end.  On all 58 ``SHW `` chunks of the install (591 records) every byte of
    the array is the same value, the array length equals the record's position
    count, and the trailing bytes to the alignment boundary are zero.  What the
    value *means* is [UNKNOWN] — one plausible reading is a per-record
    bone/palette id, but nothing in the bytes confirms it.
    """

    index: int
    """Zero-based position in the chunk's record stream."""

    triangle_offset: int
    """Chunk-relative start of the triangle table."""

    position_offset: int
    """Chunk-relative start of the position table."""

    array_offset: int
    """Chunk-relative start of the per-position byte array."""

    tables: ShwSubTables
    """The record's triangle, adjacency and position tables."""

    vertex_bytes: tuple[int, ...]
    """The per-position byte array (``len == tables.position_table.count``)."""

    @property
    def value(self) -> int:
        """The single byte value repeated in :attr:`vertex_bytes` (E-103)."""
        return self.vertex_bytes[0]

    @property
    def end(self) -> int:
        """Chunk-relative end of the record (after the padded byte array)."""
        return self.array_offset + align_up(len(self.vertex_bytes), RECORD_ALIGNMENT)

    @property
    def consistent(self) -> bool:
        """True when the record satisfies every E-102/E-103 structural
        invariant seen on the install (triangles index the positions, adjacency
        is symmetric and three-regular, neighbours share an edge)."""
        return self.tables.consistent and self.tables.shared_edges()


def _position_count_at(data: bytes, offset: int) -> int:
    """Count consecutive 16-byte position entries with ``w == 1.0`` at ``offset``."""
    count = 0
    while offset + POSITION_STRIDE * (count + 1) <= len(data):
        base = offset + POSITION_STRIDE * count
        if data[base + 12:base + 16] != POSITION_W_BYTES:
            break
        count += 1
    return count


def _record_candidates(data: bytes, start: int, index: int):
    """Yield structurally valid records whose triangle table begins at ``start``."""
    stride = TRIANGLE_STRIDE + ADJACENCY_STRIDE
    position_offset = start + stride
    while position_offset + POSITION_STRIDE <= len(data):
        delta = position_offset - start
        if delta % stride == 0:
            triangle_count = delta // stride
            position_count = _position_count_at(data, position_offset)
            if position_count:
                array_offset = position_offset + POSITION_STRIDE * position_count
                array_end = array_offset + align_up(position_count, RECORD_ALIGNMENT)
                if array_end <= len(data):
                    value = data[array_offset]
                    array = data[array_offset:array_offset + position_count]
                    padding = data[array_offset + position_count:array_end]
                    if all(b == value for b in array) and not any(padding):
                        try:
                            tables = _build_sub_tables(
                                data,
                                start,
                                triangle_count,
                                position_offset,
                                position_count,
                            )
                        except ValueError:
                            pass
                        else:
                            if (
                                tables.triangle_table.references(position_count)
                                and all(
                                    0 <= n < triangle_count
                                    for row in tables.adjacency_table.neighbours
                                    for n in row
                                )
                            ):
                                yield ShwRecord(
                                    index=index,
                                    triangle_offset=start,
                                    position_offset=position_offset,
                                    array_offset=array_offset,
                                    tables=tables,
                                    vertex_bytes=tuple(array),
                                )
        position_offset += 4


def parse_shw_records(data: bytes, header: ShwHeader) -> tuple[ShwRecord, ...]:
    """Decode a ``SHW `` chunk's full **record stream** (evidence E-103).

    Record 0's table offsets come from the header (``+0x30``/``+0x38``/``+0x40``
    /``+0x48``); each later record follows the previous record's padded
    per-position byte array.  A later record's triangle count is recovered from
    the distance to its position table, which is located by the ``w == 1.0``
    signature of its entries; a candidate is accepted only when the triangles
    index its positions, the adjacency names its triangles, and the byte array
    is constant and exactly ``P`` bytes long.

    Returns the records in order.  Raises ``ValueError`` on inconsistent input;
    trailing all-zero bytes after the last record (the observed chunk padding)
    are ignored.
    """
    first = parse_shw_sub_tables(data, header)
    position_count = first.position_table.count
    if header.field_48 + position_count > len(data):
        raise ValueError(
            f"SHW record 0 byte array (+0x48, {position_count} bytes) runs past "
            f"{len(data)} bytes of chunk data"
        )
    first_array = data[header.field_48:header.field_48 + position_count]
    if len(set(first_array)) != 1:
        raise ValueError(
            "SHW record 0 per-position byte array at +0x48 is not constant "
            "(constant on all 591 real records, E-103)"
        )
    first_end = header.field_48 + align_up(position_count, RECORD_ALIGNMENT)
    if any(data[header.field_48 + position_count:first_end]):
        raise ValueError(
            "SHW record 0 byte-array padding at +0x48 is not zero"
        )

    records = [
        ShwRecord(
            index=0,
            triangle_offset=header.field_30,
            position_offset=header.field_40,
            array_offset=header.field_48,
            tables=first,
            vertex_bytes=tuple(first_array),
        )
    ]
    start = first_end
    while start < len(data) and any(data[start:]):
        candidates = list(_record_candidates(data, start, len(records)))
        if not candidates:
            raise ValueError(
                f"SHW record stream is not decodable from offset {start:#x}"
            )
        consistent = [r for r in candidates if r.consistent]
        record = (consistent or candidates)[0]
        records.append(record)
        if record.end <= start:
            raise ValueError(
                f"SHW record {record.index} at {start:#x} does not advance"
            )
        start = record.end
    return tuple(records)


def maybe_shw_records(
    data: bytes, header: ShwHeader
) -> Optional[tuple[ShwRecord, ...]]:
    """Like :func:`parse_shw_records` but returns ``None`` on invalid input."""
    try:
        return parse_shw_records(data, header)
    except ValueError:
        return None
