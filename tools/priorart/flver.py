"""FromSoftware FLVER reader for the prior-art package.

Reads the fixed header block and the section table of ``BD_M_10100.flver``
(Vergil's body) from the third-party Bloodborne Vergil mod package
(docs/PRIOR-ART.md, E-014). This is a *bounded* decoder: it reports raw field
values and marks every field's meaning [UNKNOWN] until engine ground truth or a
format spec confirms it.

Real bytes observed in ``BD_M_10100.flver`` (467,008 bytes), file offset 0x00::

    0x00  46 4C 56 45 52 00  "FLVER\0"
    0x06  4C 00              u16 76
    0x08  14 00              u16 20
    0x0A  02 00              u16 2
    0x0C  30 F0 00 00        u32 61488
    0x10  10 30 06 00        u32 405520
    0x14  00 00 00 00        u32 0
    0x18  06 00 00 00        u32 6
    0x1C  4E 01 00 00        u32 334
    0x20  06 00 00 00        u32 6
    0x24  0C 00 00 00        u32 12
    0x28  4A 36 37 BF        f32 -0.7157...      <- six f32s, 0x28..0x3F
    0x2C  00 00 00 00        f32 0.0
    0x30  5D CB 4A BE        f32 -0.1980...
    0x34  47 D0 37 3F        f32 0.7180...
    0x38  7A 3D E5 3F        f32 1.7909...
    0x3C  1E 41 76 3E        f32 0.2405...
    0x40  9E 6D 00 00        u32 28062
    0x44  9E 6D 00 00        u32 28062
    0x48  00 01 00 00        u32 256
    0x4C  00 00 00 00        u32 0
    0x50  24 00 00 00        u32 36
    0x54  0A 00 00 00        u32 10
    0x58  2A 00 00 00        u32 42
    0x5C..0x7F zero bytes

From 0x80 the file holds a section table: six 32-byte sections
(0x80..0x140), observed as consecutive 16-byte record pairs:

    0x80  C0 C1 00 00 D0 C1 00 00 07 00 00 00 00 00 00 00  | 49600, 49616, 7, 0
    0x90  6E 01 00 00 20 BC 00 00 00 00 00 00 00 00 00 00  | 366, 48160, 0, 0
    0xA0  2E C3 00 00 38 C3 00 00 07 00 00 00 07 00 00 00  | 49966, 49976, 7, 7
    0xB0  68 01 00 00 10 BD 00 00 01 00 00 00 00 00 00 00  | 360, 48400, 1, 0
    0xC0  96 C4 00 00 A2 C4 00 00 07 00 00 00 0E 00 00 00  | 50326, 50338, 7, 14
    0xD0  6A 01 00 00 00 BE 00 00 02 00 00 00 00 00 00 00  | 362, 48640, 2, 0
    0xE0  00 C6 00 00 0C C6 00 00 07 00 00 00 15 00 00 00  | 50688, 50700, 7, 21
    0xF0  72 01 00 00 F0 BE 00 00 03 00 00 00 00 00 00 00  | 370, 48880, 3, 0
    0x100 5A C8 00 00 52 C8 00 00 07 00 00 00 1C 00 00 00  | 51058, 51082, 7, 28
    0x110 B6 01 00 00 20 C3 00 00 04 00 00 00 00 00 00 00  | 374, 49120, 4, 0
    0x120 D8 C8 00 00 D2 C8 00 00 07 00 00 00 23 00 00 00  | 51432, 51442, 7, 35
    0x130 7E 01 00 00 80 C4 00 00 05 00 00 00 00 00 00 00  | 334, 49360, 5, 0

Observed structure (meanings all [UNKNOWN]): each 32-byte section reads as
u32_00, u32_04, u32_08=7, u32_0c=7*section_index, u32_10, u32_14,
u32_18=section_type (0..5), u32_1c=0. The u32_00 values form a running offset
whose delta equals the previous section's u32_10 (49600, +366, +360, +362,
+370, +374); u32_14 = 48160 + 240*index points at a "GX**" magic block which
starts a 240-byte GX group (eight blocks: GX00, GX04, GX20, GX22, GX24, GX26,
GX30, then a 0x7FFFFFFF sentinel — layout in section 6.1, evidence E-041).
Exact for all six sections in this file. u32_10 of the
last section (334) equals header +0x1C — coincidence or not is not established.
At u32_00 of section 0 (0xC1C0, immediately after group 5) a UTF-16 name
string begins ("costume_parsn_..."). Header +0x0C (61488 = 0xF030) points at
u16 index data
(25, 39, 0 / 25, 40, 39 ...); header +0x10 (405520 = 0x63010) points at
24-byte record data beginning 0, 0x7F7F7F7F, 0x004B0039...; header +0x10 +
header +0x0C == file size (405520 + 61488 == 467008) — an inference, not an
observation of intent.

Nothing here writes a game asset into the repository; output goes wherever the
caller asks.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import List, Tuple

HEADER_SIZE = 0x80  # fixed 128-byte header block, zero-padded

SECTION_TABLE_OFFSET = 0x80
SECTION_SIZE = 0x20  # 32-byte section entry, observed as two 16-byte records


class FlverError(ValueError):
    """Raised when a FLVER payload does not match the observed header layout."""


@dataclass(frozen=True)
class FlverHeader:
    """Raw 128-byte FLVER header fields.

    Every field below is a verbatim observation from
    ``BD_M_10100.flver``; none of the field meanings is established.
    """

    magic: bytes                      # 0x00  b"FLVER\0"  [VERIFIED]
    u16_06: int                       # 0x06  76          [UNKNOWN]
    u16_08: int                       # 0x08  20          [UNKNOWN]
    u16_0a: int                       # 0x0A  2           [UNKNOWN]
    u32_0c: int                       # 0x0C  61488       [UNKNOWN]
    u32_10: int                       # 0x10  405520      [UNKNOWN]
    u32_14: int                       # 0x14  0           [UNKNOWN]
    u32_18: int                       # 0x18  6           [UNKNOWN]
    u32_1c: int                       # 0x1C  334         [UNKNOWN]
    u32_20: int                       # 0x20  6           [UNKNOWN]
    u32_24: int                       # 0x24  12          [UNKNOWN]
    bbox: Tuple[float, float, float, float, float, float]  # 0x28..0x3F six f32 [UNKNOWN]
    u32_40: int                       # 0x40  28062       [UNKNOWN]
    u32_44: int                       # 0x44  28062       [UNKNOWN]
    u32_48: int                       # 0x48  256         [UNKNOWN]
    u32_4c: int                       # 0x4C  0           [UNKNOWN]
    u32_50: int                       # 0x50  36          [UNKNOWN]
    u32_54: int                       # 0x54  10          [UNKNOWN]
    u32_58: int                       # 0x58  42          [UNKNOWN]


def parse_flver_header(data: bytes) -> FlverHeader:
    """Parse the 128-byte FLVER header from ``data``.

    Only the magic and the raw field values are checked; no field is assigned a
    meaning. Raises :class:`FlverError` on truncation or a bad magic.
    """
    if len(data) < HEADER_SIZE:
        raise FlverError(
            f"FLVER header needs {HEADER_SIZE} bytes, got {len(data)}"
        )
    magic = data[0x00:0x06]
    if magic != b"FLVER\x00":
        raise FlverError(f"bad FLVER magic: {magic!r}")

    bbox = struct.unpack_from("<6f", data, 0x28)
    return FlverHeader(
        magic=magic,
        u16_06=struct.unpack_from("<H", data, 0x06)[0],
        u16_08=struct.unpack_from("<H", data, 0x08)[0],
        u16_0a=struct.unpack_from("<H", data, 0x0A)[0],
        u32_0c=struct.unpack_from("<I", data, 0x0C)[0],
        u32_10=struct.unpack_from("<I", data, 0x10)[0],
        u32_14=struct.unpack_from("<I", data, 0x14)[0],
        u32_18=struct.unpack_from("<I", data, 0x18)[0],
        u32_1c=struct.unpack_from("<I", data, 0x1C)[0],
        u32_20=struct.unpack_from("<I", data, 0x20)[0],
        u32_24=struct.unpack_from("<I", data, 0x24)[0],
        bbox=bbox,
        u32_40=struct.unpack_from("<I", data, 0x40)[0],
        u32_44=struct.unpack_from("<I", data, 0x44)[0],
        u32_48=struct.unpack_from("<I", data, 0x48)[0],
        u32_4c=struct.unpack_from("<I", data, 0x4C)[0],
        u32_50=struct.unpack_from("<I", data, 0x50)[0],
        u32_54=struct.unpack_from("<I", data, 0x54)[0],
        u32_58=struct.unpack_from("<I", data, 0x58)[0],
    )


@dataclass(frozen=True)
class FlverSection:
    """Raw 32-byte FLVER section entry.

    Observed at 0x80 in ``BD_M_10100.flver`` as six 32-byte entries
    (each two 16-byte records). Every field is a verbatim observation;
    none of the field meanings is established.

    Structural observations from this one file (not rules, not semantics):

    * u32_08 is 7 in every entry; u32_0c is 7 times the entry index;
      u32_1c is 0 in every entry.
    * u32_00 forms a running offset: each entry's u32_00 equals the previous
      entry's u32_00 plus the previous entry's u32_10.
    * u32_14 = 48160 + 240 * index, pointing at a "GX**" magic block.
    * u32_18 takes the values 0..5 across the six entries.
    """

    u32_00: int  # 0x00  running data offset candidate   [UNKNOWN]
    u32_04: int  # 0x04  small value (16/10/12/12/24/10) [UNKNOWN]
    u32_08: int  # 0x08  constant 7                        [UNKNOWN]
    u32_0c: int  # 0x0C  7 * section index                 [UNKNOWN]
    u32_10: int  # 0x10  candidate size (366/360/362/370/374/334) [UNKNOWN]
    u32_14: int  # 0x14  candidate data offset (48160+240i) [UNKNOWN]
    u32_18: int  # 0x18  section type 0..5                   [UNKNOWN]
    u32_1c: int  # 0x1C  constant 0                          [UNKNOWN]


def parse_flver_sections(data: bytes) -> List[FlverSection]:
    """Parse the FLVER section table from ``data``.

    The table starts at :data:`SECTION_TABLE_OFFSET` (0x80) and contains
    :attr:`FlverHeader.u32_18` entries of :data:`SECTION_SIZE` bytes each
    (6 entries in ``BD_M_10100.flver``; whether +0x18 is the count source is
    [UNKNOWN]). Raises :class:`FlverError` on truncation or a bad magic.
    """
    header = parse_flver_header(data)
    count = header.u32_18  # [UNKNOWN] whether this is the section count
    end = SECTION_TABLE_OFFSET + count * SECTION_SIZE
    if len(data) < end:
        raise FlverError(
            f"FLVER section table needs {end} bytes, got {len(data)}"
        )
    sections: List[FlverSection] = []
    for index in range(count):
        off = SECTION_TABLE_OFFSET + index * SECTION_SIZE
        fields = struct.unpack_from("<8I", data, off)
        sections.append(FlverSection(*fields))
    return sections


GX_BLOCK_HEADER_SIZE = 0x0C  # u32 tag + u32 constant + u32 size
GX_BLOCK_CONSTANT = 0x64     # 100, observed in every block
GX_GROUP_SIZE = 0xF0         # 240 bytes per group, observed 6/6 groups
GX_SENTINEL_TAG = 0x7FFFFFFF  # group terminator, observed as the last tag


@dataclass(frozen=True)
class FlverGxBlock:
    """One raw GX block.

    Observed in ``BD_M_10100.flver`` at each section's ``u32_14`` group:

        u32 tag        block tag, e.g. b"GX00"; the group terminator reads
                       u32 0x7FFFFFFF                                      [UNKNOWN]
        u32 constant   100 (0x64) in every block, sentinel included        [UNKNOWN]
        u32 size       total block bytes including this 12-byte header      [UNKNOWN]
        bytes payload  size - 12 bytes                                      [UNKNOWN]

    Block sizes observed in this file: GX00 44, GX04 64, GX20/GX22/GX24/GX26/
    GX30 24 each, sentinel 12 (44 + 64 + 5*24 + 12 == 240). Every field
    meaning is [UNKNOWN].
    """

    tag: bytes      # 4 raw bytes                                        [UNKNOWN]
    constant: int   # u32 == 100 observed everywhere                     [UNKNOWN]
    size: int       # u32 total block size including the 12-byte header    [UNKNOWN]
    payload: bytes  # size - 12 bytes                                      [UNKNOWN]


@dataclass(frozen=True)
class FlverGxGroup:
    """One 240-byte GX group.

    Observed layout at every section's ``u32_14`` in ``BD_M_10100.flver``:

        GX00(44), GX04(64), GX20(24), GX22(24), GX24(24), GX26(24),
        GX30(24), sentinel(12)  == 240 bytes

    All six sections' groups are byte-identical in this file. What follows
    the last group (section 0's u32_00 = 0xC1C0) is a UTF-16 name string,
    not another group. Every field meaning is [UNKNOWN].
    """

    blocks: Tuple[FlverGxBlock, ...]  # seven tagged blocks + sentinel [UNKNOWN]


def parse_flver_gx_block(data: bytes, offset: int) -> Tuple[FlverGxBlock, int]:
    """Parse one GX block at ``offset``.

    Layout: ``u32 tag; u32 constant (observed 100); u32 size; bytes payload``
    where ``payload`` is ``size - 12`` bytes. Returns ``(block, next_offset)``.

    Raises :class:`FlverError` on truncation, on a ``size`` smaller than the
    12-byte header, or when the block overruns ``data``.
    """
    if offset + GX_BLOCK_HEADER_SIZE > len(data):
        raise FlverError(
            f"GX block header needs {GX_BLOCK_HEADER_SIZE} bytes at 0x{offset:04X}, "
            f"got {len(data) - offset}"
        )
    tag = data[offset:offset + 4]
    constant, size = struct.unpack_from("<II", data, offset + 4)
    if size < GX_BLOCK_HEADER_SIZE:
        raise FlverError(
            f"GX block size {size} < header {GX_BLOCK_HEADER_SIZE} at 0x{offset:04X}"
        )
    end = offset + size
    if end > len(data):
        raise FlverError(
            f"GX block at 0x{offset:04X} overruns data: size {size}, "
            f"available {len(data) - offset}"
        )
    payload = data[offset + GX_BLOCK_HEADER_SIZE:end]
    return (
        FlverGxBlock(tag=tag, constant=constant, size=size, payload=payload),
        end,
    )


def parse_flver_gx_group(data: bytes, offset: int) -> Tuple[FlverGxGroup, int]:
    """Parse one GX group starting at ``offset``.

    A group is a sequence of blocks terminated by the sentinel block whose tag
    is u32 0x7FFFFFFF with size 12. Observed group size is 240 bytes with tags
    GX00, GX04, GX20, GX22, GX24, GX26, GX30, then the sentinel.

    Returns ``(group, next_offset)`` where ``next_offset`` is the first byte
    after the sentinel block. Raises :class:`FlverError` on truncation or when
    no sentinel terminates the group.
    """
    blocks: List[FlverGxBlock] = []
    pos = offset
    sentinel = struct.pack("<I", GX_SENTINEL_TAG)
    for _ in range(8):  # seven tagged blocks + sentinel, observed 6/6 groups
        block, pos = parse_flver_gx_block(data, pos)
        blocks.append(block)
        if block.tag == sentinel:
            break
    else:
        raise FlverError(
            f"no GX sentinel tag (0x7FFFFFFF) within 8 blocks at 0x{offset:04X}"
        )
    if blocks[-1].size != 12:
        raise FlverError(
            f"GX sentinel block size {blocks[-1].size} != 12 at 0x{offset:04X}"
        )
    if pos - offset != GX_GROUP_SIZE:
        raise FlverError(
            f"GX group at 0x{offset:04X} is {pos - offset} bytes, expected "
            f"{GX_GROUP_SIZE}"
        )
    return FlverGxGroup(blocks=tuple(blocks)), pos


def parse_flver_gx_groups(data: bytes) -> List[FlverGxGroup]:
    """Parse the GX group referenced by each section's ``u32_14``.

    Returns one :class:`FlverGxGroup` per section, in table order. Raises
    :class:`FlverError` on truncation or a bad magic (via
    :func:`parse_flver_sections`) or on a malformed group.
    """
    sections = parse_flver_sections(data)
    return [
        parse_flver_gx_group(data, section.u32_14)[0] for section in sections
    ]
