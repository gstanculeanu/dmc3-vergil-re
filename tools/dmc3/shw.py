"""DMC3 ``SHW `` chunk header reader.

``SHW `` chunks are plain-tagged payloads inside a PAC container (evidence
E-002).  Only the header fields that are **observed** across real archives are
exposed here; the header at +0x30/+0x38/+0x40/+0x48 points at sub-tables, three
of which are structurally decoded:

* ``+0x30`` — the **triangle table**: ``[u32 i0, u32 i1, u32 i2, u32 0]`` per
  triangle, indexing the ``+0x40`` positions (E-102).
* ``+0x38`` — the **adjacency table**: ``[u16 n0, u16 n1, u16 n2, u16 0]`` per
  triangle, naming the three edge-neighbour *triangles* (E-102).  E-038 read
  these as a vertex index buffer; that reading is disproved (E-102).
* ``+0x40`` — the **position table**: ``[f32 x, f32 y, f32 z, f32 1.0]`` per
  vertex (E-038).

The ``+0x48`` region, the texture binding and the remaining payload semantics
stay open (issue F2).  ``SHW `` being shadow-volume geometry rather than a
material payload is [INFERRED], not established.

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
    +0x30  u32      varies per chunk   (0x460, 0x1E0, 0x60, 0x60; offset of the
                                      triangle table, E-102)
    +0x34  u32      0 in every observed chunk
    +0x38  u32      varies per chunk   (0x560, 0x460, 0x480, 0x480; offset of
                                      the adjacency table, E-102)
    +0x3C  u32      0 in every observed chunk
    +0x40  u32      varies per chunk   (0x5E0, 0x5A0, 0x690, 0x690; offset of
                                      the position table, E-038)
    +0x44  u32      0 in every observed chunk
    +0x48  u32      varies per chunk   (0x680, 0x700, 0x900, 0x900)
    +0x4C  u32      0 in every observed chunk
    +0x50  zero bytes                         (16 bytes of padding)

The four varying fields at +0x30/+0x38/+0x40/+0x48 each point at a sub-table.
The +0x30 and +0x38 tables have the **same entry count** N, the +0x30 entries
index the +0x40 position table, and the +0x38 entries index the +0x30 triangle
table — see E-102 and :func:`parse_shw_sub_tables`.  The +0x48 region's layout
and every field's *meaning* remain [UNKNOWN] and are deliberately not decoded.

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
    """The decoded ``SHW`` sub-tables (evidence E-038, E-102).

    ``field_30``/``field_38``/``field_40``/``field_48`` are chunk-relative
    offsets into the chunk's data, in that order.  Buffer sizes come from the
    consecutive-pointer differences:

    * triangle bytes  = ``field_38 - field_30``  (stride 16)
    * adjacency bytes = ``field_40 - field_38``  (stride 8)
    * position bytes  = ``field_48 - field_40``  (stride 16)

    The triangle and adjacency tables always have the same entry count (E-102).
    The first two differences held exactly on all four ``pl021.pac`` chunks in
    E-038 as well, but the ``+0x30`` table was not decoded then.
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


def parse_shw_sub_tables(data: bytes, header: ShwHeader) -> ShwSubTables:
    """Decode the triangle, adjacency and position sub-tables of a ``SHW `` chunk.

    ``data`` is the chunk's raw bytes (``chunk.data``); the ``field_30``,
    ``field_38``, ``field_40`` and ``field_48`` offsets are chunk-relative.
    Raises ``ValueError`` if the offsets are not strictly increasing, if a
    pointer difference is not divisible by the observed stride, if a table runs
    past the end of the data, if a table offset lies inside the header, or if
    the triangle and adjacency counts differ (a 58/58 invariant, E-102).
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

    triangles: list[tuple[int, int, int]] = []
    for i in range(triangle_count):
        base = header.field_30 + TRIANGLE_STRIDE * i
        i0, i1, i2, pad = struct.unpack_from("<IIII", data, base)
        if pad != 0:
            raise ValueError(
                f"SHW triangle entry {i} has nonzero fourth u32 {pad:#x} (observed 0 in all real chunks)"
            )
        triangles.append((i0, i1, i2))

    neighbours: list[tuple[int, int, int]] = []
    for i in range(adjacency_count):
        base = header.field_38 + ADJACENCY_STRIDE * i
        n0, n1, n2, pad = struct.unpack_from("<HHHH", data, base)
        if pad != 0:
            raise ValueError(
                f"SHW adjacency entry {i} has nonzero fourth u16 {pad:#x} (observed 0 in all real chunks)"
            )
        neighbours.append((n0, n1, n2))

    positions: list[tuple[float, float, float, float]] = []
    for i in range(position_count):
        base = header.field_40 + POSITION_STRIDE * i
        positions.append(struct.unpack_from("<4f", data, base))

    return ShwSubTables(
        triangle_table=ShwTriangleTable(
            count=triangle_count, triangles=tuple(triangles)
        ),
        adjacency_table=ShwAdjacencyTable(
            count=adjacency_count, neighbours=tuple(neighbours)
        ),
        position_table=ShwPositionTable(
            count=position_count, positions=tuple(positions)
        ),
    )


def maybe_shw_sub_tables(
    data: bytes, header: ShwHeader
) -> Optional[ShwSubTables]:
    """Like :func:`parse_shw_sub_tables` but returns ``None`` on invalid input."""
    try:
        return parse_shw_sub_tables(data, header)
    except ValueError:
        return None
