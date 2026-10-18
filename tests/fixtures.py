"""Synthetic fixtures that mirror the byte layouts observed in real DMC3 data.

Building fixtures in code (rather than shipping game files) keeps the repository
free of copyrighted assets while still exercising the parsers.
"""

import struct
from typing import Optional

MOT_BONES = 24
MOT_STRIDE = 0x38
MOT_TABLE_OFFSET = 0x22
MOT_TABLE_LEN = 23
MOT_HEADER_SIZE = MOT_TABLE_OFFSET + 2 * MOT_TABLE_LEN  # 0x50


def plain_chunk(tag: bytes, payload: bytes = b"", pad_to: int = 80) -> bytes:
    """A chunk whose tag is its first four bytes (``MOD ``, ``SHW ``)."""
    assert len(tag) == 4
    blob = bytearray(tag + payload)
    if len(blob) < pad_to:
        blob += b"\x00" * (pad_to - len(blob))
    return bytes(blob)


def motion_chunk(
    bones: int = MOT_BONES,
    stride: int = MOT_STRIDE,
    duration: float = 50.0,
    flag_a: int = 0,
    unknown_1e: int = 0x01C0,
    unknown_20: int = 0x01C0,
    track_bytes: int = 64,
    table_value: Optional[int] = None,
) -> bytes:
    """A size-prefixed ``MOT\\0`` chunk mirroring pl021_00_*.pac.

    ``bones`` is written to ``+0x1A`` and ``+0x1C``; ``table_value`` defaults to
    ``stride`` so the 23-entry table at ``+0x22`` matches the dominant shape.
    """
    header_size = MOT_TABLE_OFFSET + 2 * MOT_TABLE_LEN
    blob = bytearray(header_size + track_bytes)
    struct.pack_into("<I", blob, 0x00, header_size)
    blob[0x04:0x08] = b"MOT\x00"
    struct.pack_into("<I", blob, 0x08, 0)
    struct.pack_into("<f", blob, 0x0C, duration)
    struct.pack_into("<I", blob, 0x10, 0)
    struct.pack_into("<f", blob, 0x14, duration)
    struct.pack_into("<H", blob, 0x18, flag_a)
    struct.pack_into("<H", blob, 0x1A, bones)
    struct.pack_into("<H", blob, 0x1C, bones)
    struct.pack_into("<H", blob, 0x1E, unknown_1e)
    struct.pack_into("<H", blob, 0x20, unknown_20)
    value = stride if table_value is None else table_value
    for index in range(MOT_TABLE_LEN):
        struct.pack_into("<H", blob, MOT_TABLE_OFFSET + 2 * index, value)
    for offset in range(header_size, header_size + track_bytes, 4):
        struct.pack_into("<I", blob, offset, 0xA5A50000 | offset)
    return bytes(blob)


def mot_payload_with_records(record_groups=(4, 2, 6), tail: int = 0) -> bytes:
    """A MOT payload: ``u32 count`` then records of ``(size, groups, a, b, data)``.

    Mirrors the verified structure (E-019): ``size == 8 * (groups + 4)`` and the
    data is ``8 * (groups + 3)`` bytes.
    """
    blob = bytearray(struct.pack("<I", len(record_groups)))
    for index, groups in enumerate(record_groups):
        size = 8 * (groups + 4)
        blob += struct.pack("<HHHH", size, groups, 3, 0)
        for g in range(groups + 3):
            # 8 bytes per group; deterministic so tests can assert on it
            blob += struct.pack("<HHHH", 0x8000, index, g, 0x3FFF)
    blob += b"\x00" * tail
    return bytes(blob)


def motion_chunk_with_records(record_groups=(4, 2, 6), tail: int = 0) -> bytes:
    """A complete size-prefixed MOT chunk whose payload holds real records."""
    payload = mot_payload_with_records(record_groups, tail)
    header_size = MOT_TABLE_OFFSET + 2 * MOT_TABLE_LEN
    blob = bytearray(header_size)
    struct.pack_into("<I", blob, 0x00, header_size)
    blob[0x04:0x08] = b"MOT\x00"
    struct.pack_into("<f", blob, 0x0C, 100.0)
    struct.pack_into("<f", blob, 0x14, 100.0)
    struct.pack_into("<H", blob, 0x18, 1)
    struct.pack_into("<H", blob, 0x1A, 23)
    struct.pack_into("<H", blob, 0x1C, 24)
    struct.pack_into("<H", blob, 0x1E, 0)
    struct.pack_into("<H", blob, 0x20, 448)
    for index in range(MOT_TABLE_LEN):
        struct.pack_into("<H", blob, MOT_TABLE_OFFSET + 2 * index, 56)
    return bytes(blob) + payload


def mod_chunk(
    scale: float = 1.0099999904632568,
    field_08: int = 0,
    field_0c: int = 0,
    field_10: int = 0x10101,
    field_14: int = 0xAF258,
    field_18: int = 0,
    field_1c: int = 0,
    field_20: int = 0x160,
    body: bytes = b"",
) -> bytes:
    """A synthetic plain-tagged ``MOD `` chunk mirroring pl021.pac (E-030).

    Header: ``MOD `` tag, f32 scale (1.0099… in 285/286 real chunks), then
    seven u32 fields whose meanings are still [UNKNOWN].  The body follows at
    +0x24 and is stored verbatim.
    """
    blob = bytearray(b"\x00" * 0x24)
    blob[0:4] = b"MOD "
    struct.pack_into("<f", blob, 0x04, scale)
    struct.pack_into("<I", blob, 0x08, field_08)
    struct.pack_into("<I", blob, 0x0C, field_0c)
    struct.pack_into("<I", blob, 0x10, field_10)
    struct.pack_into("<I", blob, 0x14, field_14)
    struct.pack_into("<I", blob, 0x18, field_18)
    struct.pack_into("<I", blob, 0x1C, field_1c)
    struct.pack_into("<I", blob, 0x20, field_20)
    blob += body
    return bytes(blob)


def mod_body(
    marker: int = 0x8001,
    count: int = 182,
    field_24: int = 128,
    field_2c: int = 0x00120002,
    vector: tuple[float, float, float, float] = (-0.196165, 0.0, 42.0706, 73.5689),
    repeat: int = 182,
) -> bytes:
    """A synthetic ``MOD `` payload body mirroring pl021.pac slot 23 (E-031).

    Layout (body-relative, little-endian), all other prefix bytes zero::

        +0x1C u16 marker   (observed 0x8001)
        +0x1E u16 count    (observed 474/300/182/182 across pl021.pac MOD chunks)
        +0x24 u32 field    (observed 768/192/128/128)
        +0x2C u32 field    (observed varies)
        +0x4C 4x f32       vector/quaternion-like, meaning [UNKNOWN]
        +0x5C u32 repeat   (equals ``count`` for the duplicated slots 23/25)
    """
    # BODY_PREFIX_SIZE (0x60) covers through ``repeat`` at body +0x5C.
    blob = bytearray(0x60)
    struct.pack_into("<H", blob, 0x1C, marker)
    struct.pack_into("<H", blob, 0x1E, count)
    struct.pack_into("<I", blob, 0x24, field_24)
    struct.pack_into("<I", blob, 0x2C, field_2c)
    struct.pack_into("<4f", blob, 0x4C, *vector)
    struct.pack_into("<I", blob, 0x5C, repeat)
    return bytes(blob)


def shw_chunk(
    alpha: float = 0.5,
    field_08: int = 0,
    field_0c: int = 0,
    field_10: int = 0x00011811,
    field_14: int = 100,
    field_18: int = 0,
    field_1c: int = 0,
    pair_20_0: int = 0x000A,
    pair_20_1: int = 0x0010,
    field_24: int = 0,
    field_28: int = 0,
    field_2c: int = 0,
    field_30: int = 0x460,
    field_34: int = 0,
    field_38: int = 0x560,
    field_3c: int = 0,
    field_40: int = 0x5E0,
    field_44: int = 0,
    field_48: int = 0x680,
    field_4c: int = 0,
    pad_to: int = 0x60,
) -> bytes:
    """A synthetic plain-tagged ``SHW `` chunk mirroring pl021.pac slot 8 (E-036).

    Header (body-relative, little-endian)::

        +0x00 char[4] "SHW "
        +0x04 f32 alpha             (observed 0.5 in all four real chunks)
        +0x10 u32 field_10          (observed 0x00011811 / 0x00002707 / ...)
        +0x14 u32 field_14          (observed 100 / 102 / 0x315D8 / ...)
        +0x20 u16 pair_20_0         (observed 0x000A / 0x0016 / 0x0027 / ...)
        +0x22 u16 pair_20_1         (observed 0x0010 / 0x0028 / 0x0042 / ...)
        +0x28 u32 field_28          (observed 0 in all four real chunks)
        +0x30 u32 field_30          (observed 0x460 / 0x1E0 / 0x60 / 0x60;
                                     points at a sub-table in each chunk)
        +0x38 u32 field_38          (observed 0x560 / 0x460 / 0x480 / ...)
        +0x40 u32 field_40          (observed 0x5E0 / 0x5A0 / 0x690 / ...)
        +0x48 u32 field_48          (observed 0x680 / 0x700 / 0x900 / ...)

    All offsets not listed are zero.  Meanings are [UNKNOWN]; this fixture
    locks in the observed byte layout so a parser can't silently drift from
    the real artifact.
    """
    blob = bytearray(b"\x00" * pad_to)
    blob[0:4] = b"SHW "
    struct.pack_into("<f", blob, 0x04, alpha)
    struct.pack_into("<I", blob, 0x08, field_08)
    struct.pack_into("<I", blob, 0x0C, field_0c)
    struct.pack_into("<I", blob, 0x10, field_10)
    struct.pack_into("<I", blob, 0x14, field_14)
    struct.pack_into("<I", blob, 0x18, field_18)
    struct.pack_into("<I", blob, 0x1C, field_1c)
    struct.pack_into("<H", blob, 0x20, pair_20_0)
    struct.pack_into("<H", blob, 0x22, pair_20_1)
    struct.pack_into("<I", blob, 0x24, field_24)
    struct.pack_into("<I", blob, 0x28, field_28)
    struct.pack_into("<I", blob, 0x2C, field_2c)
    struct.pack_into("<I", blob, 0x30, field_30)
    struct.pack_into("<I", blob, 0x34, field_34)
    struct.pack_into("<I", blob, 0x38, field_38)
    struct.pack_into("<I", blob, 0x3C, field_3c)
    struct.pack_into("<I", blob, 0x40, field_40)
    struct.pack_into("<I", blob, 0x44, field_44)
    struct.pack_into("<I", blob, 0x48, field_48)
    struct.pack_into("<I", blob, 0x4C, field_4c)
    return bytes(blob)


def shw_chunk_with_tables(
    field_38: int = 0x50,
    field_40: Optional[int] = None,
    field_48: Optional[int] = None,
    indices: tuple[tuple[int, int, int], ...] = (
        (1, 2, 3),
        (4, 5, 6),
        (7, 8, 9),
        (0, 9, 2),
    ),
    positions: tuple[tuple[float, float, float, float], ...] = (
        (1.0, 2.0, 3.0, 1.0),
        (-4.0, 5.0, -6.0, 1.0),
        (7.5, -8.5, 9.5, 1.0),
    ),
) -> bytes:
    """A synthetic ``SHW `` chunk whose +0x38/+0x40/+0x48 point at contiguous
    index and position sub-tables (evidence E-038).

    Layout (chunk-relative, little-endian)::

        +0x38 u32 field_38   offset of the index table
        +0x40 u32 field_40   offset of the position table
        +0x48 u32 field_48   offset of the next (undecoded) table
        [field_38]  [u16 i0, u16 i1, u16 i2, u16 0] x len(indices)
        [field_40]  [f32 x, f32 y, f32 z, f32 1.0] x len(positions)

    If ``field_40``/``field_48`` are not given they are derived from the table
    sizes so the pointer-difference invariant (index bytes = field_40 - field_38,
    position bytes = field_48 - field_40) holds exactly.  All data values are
    synthetic; no game bytes are committed.
    """
    INDEX_STRIDE = 8
    POSITION_STRIDE = 16
    if field_40 is None:
        field_40 = field_38 + INDEX_STRIDE * len(indices)
    if field_48 is None:
        field_48 = field_40 + POSITION_STRIDE * len(positions)
    size = field_48 + POSITION_STRIDE
    blob = bytearray(b"\x00" * size)
    blob[0:4] = b"SHW "
    struct.pack_into("<f", blob, 0x04, 0.5)
    struct.pack_into("<I", blob, 0x38, field_38)
    struct.pack_into("<I", blob, 0x40, field_40)
    struct.pack_into("<I", blob, 0x48, field_48)
    for i, (i0, i1, i2) in enumerate(indices):
        struct.pack_into("<HHHH", blob, field_38 + INDEX_STRIDE * i, i0, i1, i2, 0)
    for i, (x, y, z, w) in enumerate(positions):
        struct.pack_into("<4f", blob, field_40 + POSITION_STRIDE * i, x, y, z, w)
    return bytes(blob)


def pnst_archive() -> bytes:
    """A synthetic ``PNST`` container mirroring plwp_vergilsword.pac (E-006).

    Layout (little-endian), all values synthetic::

        +0x00  char[4]  "PNST"
        +0x04  u32      entry_count
        +0x08  u32      offset[entry_count]   file-relative; 0 == empty slot
        ...   zero padding to 16-byte alignment
        data   chunks at the recorded offsets, gaps padded to 16 bytes

    Slots: 0 = ``MOD ``, 1 = ``SHW ``, 2 = empty, 3 = text
    (``;wp005.clt``), 4 = raw mystery block (``01 00 00 00 11 ...``).  No game
    bytes are committed; every value below is invented to exercise the parser.
    """
    TAG_MODEL = b"MOD "
    TAG_SHADER = b"SHW "
    entries: list[Optional[tuple[Optional[bytes], bytes]]] = [
        (TAG_MODEL, b"\x01\x02\x03\x04"),                    # slot 0: model
        (TAG_SHADER, b"\xAA" * 8),                            # slot 1: shader
        None,                                                  # slot 2: empty
        (None, b";wp005.clt\r\n\r\nClothNum\t1\r\n\r\nClothNo     0\r\nClothId     0\r\n"),  # slot 3: text
        (None, b"\x01\x00\x00\x00\x11\x00\x00\x00" + b"\x00" * 24),  # slot 4: raw
    ]
    count = len(entries)
    table_end = 0x08 + 4 * count
    body = bytearray()
    cursor = (table_end + 15) & ~15
    offsets: list[int] = [0] * count
    for index, entry in enumerate(entries):
        if entry is None:
            continue
        tag, payload = entry
        chunk = bytearray()
        if tag is not None:
            chunk += tag
        chunk += payload
        offsets[index] = cursor
        body += chunk
        cursor += len(chunk)
        pad = (-cursor) & 15
        body += b"\x00" * pad
        cursor += pad
    header = bytearray(b"PNST")
    header += struct.pack("<I", count)
    for off in offsets:
        header += struct.pack("<I", off)
    header += b"\x00" * ((-len(header)) & 15)
    return bytes(header) + bytes(body)


def pnst_raw_block(field_a: int = 1, field_b: int = 17, tail: bytes = b"") -> bytes:
    """A synthetic PNST raw mystery block mirroring plwp_*.pac slots 0/3 (E-048).

    Observed header, body-relative and little-endian::

        +0x00 u32 field_a   (observed 1)
        +0x04 u32 field_b   (observed 17, 0x11)

    Identical in slots 0 and 3 of both weapon archives. Everything after the
    header is [UNKNOWN]; the fixture appends an optional synthetic tail. No
    game bytes are committed; the fixture locks the observed header so a parser
    can't silently drift from the real artifact.
    """
    blob = bytearray(8)
    struct.pack_into("<II", blob, 0, field_a, field_b)
    blob += tail
    return bytes(blob)


def raw_chunk_slot0() -> bytes:
    """A synthetic raw chunk mirroring pl021.pac slot 0's header (E-033).

    Body-relative layout (little-endian), all trailing bytes zero::

        +0x00 u32 field_00   (observed 5)
        +0x04 u32 field_04   (observed 43)
        +0x08 u32 field_08   (observed 22)
        +0x0C u32 field_0c   (observed 43)
        +0x10 u32 field_10   (observed 5)
        +0x14 u32 field_14   (observed 1)
    """
    blob = bytearray(0x80)
    struct.pack_into("<IIIIII", blob, 0, 5, 43, 22, 43, 5, 1)
    return bytes(blob)


def raw_chunk_slot10() -> bytes:
    """A synthetic raw chunk mirroring pl021.pac slot 10's layout (E-037).

    Body-relative layout (little-endian)::

        +0x00  u16 pairs, stride 4 (23 pairs, mirroring the real chunk):
            pairs 0-14  (92, 132 + 20*i)
            pair  15    (112, 432)
            pair  16    (92, 432)
            pairs 17-22 (92, 132) x 6
        +0x5C  little-endian f32 stream (mirrors 0.3, ~0, -0.1, 0.0, 0.7,
               then zero padding)

    Every field meaning is [UNKNOWN]; this fixture locks the observed byte
    layout so a parser can't silently drift from the real artifact.
    """
    blob = bytearray()
    for i in range(15):
        blob += struct.pack("<HH", 92, 132 + 20 * i)
    blob += struct.pack("<HH", 112, 432)
    blob += struct.pack("<HH", 92, 432)
    for _ in range(6):
        blob += struct.pack("<HH", 92, 132)
    assert len(blob) == 4 * 23, "slot-10 pair table must be 23 pairs"
    # f32 stream mirroring the real chunk's +0x5C.. verbatim
    # (9A 99 99 3E, 0A D7 A3 BC, CD CC CC BD, 00 00 00 00, 66 66 66 3F):
    blob += bytes.fromhex("9a99993e0ad7a3bccdccccbd000000006666663f")
    blob += b"\x00" * 24
    return bytes(blob)


def raw_chunk_slot21() -> bytes:
    """A synthetic ``pl021.pac`` slot-21 chunk mirroring the observed u16
    segment layout (evidence E-043).

    Layout (body-relative, little-endian)::
        14 u16 segments separated by the ``0xFFFF`` separator; the last
        segment is not followed by a separator.

    Segment sizes mirror the real chunk (2, 6, 1, 8, 10, 31, 111, 34, 1, 6,
    8, 27, 84, 26 u16s). Segment 0 uses the verbatim real values ``(6, 408)``;
    the remaining segments hold synthetic distinct values. No game bytes are
    committed; the fixture locks the observed segmentation so a parser can't
    silently drift from the real artifact.
    """
    SEP = 0xFFFF
    sizes = (2, 6, 1, 8, 10, 31, 111, 34, 1, 6, 8, 27, 84, 26)
    blob = bytearray()
    for index, size in enumerate(sizes):
        if index:
            blob += struct.pack("<H", SEP)
        if index == 0:
            # Verbatim real segment 0 from pl021.pac slot 21 (E-043).
            blob += struct.pack("<HH", 6, 408)
        else:
            blob += struct.pack(f"<{size}H", *range(1000 + index, 1000 + index + size))
    return bytes(blob)


def raw_chunk_slot5() -> bytes:
    """A synthetic ``pl021.pac`` slot-5 chunk mirroring the observed u16
    segment layout (evidence E-052).

    Layout (body-relative, little-endian)::
        u16 stream split into segments by the ``0xFFFF`` separator; the last
        segment is not followed by a separator.

    The head mirrors the real chunk at file offset 0x06B6E0 verbatim:
        segment 0: (6, 0x37D0)
        segment 1: (4,)
        segment 2 opens: (70, 0x7AC, 0xD4E, 0xEBE, 0x15E2, 0x1D54, 0x2636,
                          0x26A4, 0x2DC0, 0x335A, 0xEBE x 9)
    and is padded to the real chunk's observed segment-2 size of 34 u16s.
    Remaining segments hold synthetic distinct values, including one that
    carries 0x7FFF as data (never a delimiter). No game bytes are committed;
    the fixture locks the observed head and separator discipline so a parser
    can't silently drift from the real artifact.
    """
    SEP = 0xFFFF
    seg0 = (6, 0x37D0)
    seg1 = (4,)
    seg2 = (
        70, 0x7AC, 0xD4E, 0xEBE, 0x15E2, 0x1D54, 0x2636,
        0x26A4, 0x2DC0, 0x335A,
    ) + (0xEBE,) * 9
    seg2 += tuple(0x2000 + i for i in range(34 - len(seg2)))
    segments = [seg0, seg1, seg2, (0x1234, 0x5678, 0x9ABC), (7, 8, 9, 10, 11),
                (0x7FFF, 0xABCD)]
    blob = bytearray()
    for index, segment in enumerate(segments):
        if index:
            blob += struct.pack("<H", SEP)
        blob += struct.pack("<%dH" % len(segment), *segment)
    return bytes(blob)


def raw_chunk_slot9() -> bytes:
    """A synthetic ``pl021.pac`` slot-9 chunk mirroring the observed f32 array
    (evidence E-053).

    Layout (body-relative, little-endian)::
        +0x00  224 little-endian f32s, no header, no count field, no separators.

    The first f32s mirror the real chunk verbatim (10.4, -1.2, 10.0, 12.0,
    -1.2, 15.0 ...); the remaining values are synthetic. No game bytes are
    committed; the fixture locks the observed array length so a parser can't
    silently drift from the real artifact.
    """
    real_prefix = (10.4, -1.2, 10.0, 12.0, -1.2, 15.0, 10.4, -0.8, 6.4,
                   12.4, -0.8, 12.0)
    blob = bytearray()
    for value in real_prefix:
        blob += struct.pack("<f", value)
    blob += struct.pack("<212f", *(0.0,) * 212)
    assert len(blob) == 4 * 224, "slot-9 array must be 224 f32s"
    return bytes(blob)


def cloth_text() -> bytes:
    return b";pl021_02.clt\r\n\r\nClothNum\t1\r\n\r\nClothNo     0\r\nClothId     0\r\n"


def dds_header(
    width: int = 256,
    height: int = 256,
    fourcc: bytes = b"DXT5",
    mipmaps: int = 8,
) -> bytes:
    """A legacy 128-byte DDS header."""
    blob = bytearray(128)
    blob[0:4] = b"DDS "
    struct.pack_into("<I", blob, 4, 124)
    struct.pack_into("<I", blob, 8, 0x00081007)
    struct.pack_into("<I", blob, 12, height)
    struct.pack_into("<I", blob, 16, width)
    struct.pack_into("<I", blob, 20, 0)
    struct.pack_into("<I", blob, 24, 0)
    struct.pack_into("<I", blob, 28, mipmaps)
    struct.pack_into("<I", blob, 76, 32)
    struct.pack_into("<I", blob, 80, 0x4)
    blob[84:88] = fourcc
    struct.pack_into("<I", blob, 88, 0)
    return bytes(blob)


def tm2_file(dds_prefix: int = 0x70, payload: bytes = b"\xAB" * 32) -> bytes:
    """An HD-Collection ``.tm2``: platform header then an embedded DDS blob."""
    header = bytearray(dds_prefix)
    struct.pack_into("<I", header, 0x08, 0x00020100)
    struct.pack_into("<I", header, 0x0C, 0x0000AAE4)
    return bytes(header) + dds_header() + payload


def real_tm2_preheader() -> bytes:
    """The exact 0x70-byte platform header observed in ``i001_90.tm2`` (E-034).

    All 28 little-endian u32s; offsets not listed are zero. Meanings are
    [UNKNOWN]; this fixture locks in the observed bytes so a parser can't
    silently drift from the real artifact.
    """
    blob = bytearray(0x70)
    fields = {
        0x08: 0x00020100,
        0x0C: 0x0000AAE4,
        0x10: 0x01000100,
        0x14: 1,
        0x20: 64,
        0x38: 0x00010000,
        0x44: 0x00800080,
        0x48: 0x3C000000,
        0x4C: 0x3C000000,
        0x64: 0x00010080,
        0x68: 8,
    }
    for off, val in fields.items():
        struct.pack_into("<I", blob, off, val)
    return bytes(blob)


def real_tm2_dds() -> bytes:
    """The exact 128-byte DDS header observed in ``i001_90.tm2`` at file 0x70.

    ``dwSize=124, flags=0x00081007, 256×256, one mip level, fourCC DXT3``
    (E-005).  Written out byte-for-byte so ``parse_dds_header`` can be exercised
    against the real artifact's values rather than the synthetic ``dds_header``.
    """
    return bytes(
        b"DDS "
        + struct.pack("<I", 124)            # dwSize
        + struct.pack("<I", 0x00081007)     # dwFlags
        + struct.pack("<I", 256)            # dwHeight
        + struct.pack("<I", 256)            # dwWidth
        + struct.pack("<I", 65536)          # dwPitchOrLinearSize
        + struct.pack("<I", 0)              # dwDepth
        + struct.pack("<I", 1)              # dwMipMapCount
        + b"\x00" * 44                      # dwReserved1[11]
        + struct.pack("<I", 32)             # ddspf.dwSize
        + struct.pack("<I", 0x4)            # ddspf.dwFlags (fourCC)
        + b"DXT3"                           # ddspf.dwFourCC
        + b"\x00" * 20                      # RGBBitCount + masks
        + b"\x00" * 20                      # dwCaps[4] + dwReserved2
    )


def real_tm2() -> bytes:
    """A synthetic ``.tm2`` mirroring ``i001_90.tm2`` exactly (E-034 + E-005)."""
    return real_tm2_preheader() + real_tm2_dds() + b"\xAB" * 32


# ---------------------------------------------------------------------------
# GoW3R WAD fixtures (layout from E-016 / E-022)
# ---------------------------------------------------------------------------

def wad_bytes(
    banner: str = "WAD_R_Sword00",
    names=(),
    dc_count: int = 6,
    bad_dc_prefix: bool = False,
    pad: int = 0x40,
) -> bytes:
    """A synthetic ``R_*.WAD``: header, some names, then ``DC_<banner>`` markers."""
    blob = bytearray()
    blob += struct.pack("<II", 20, 8)
    blob += banner.encode("latin-1")
    blob += b"\x00" * (pad - len(blob))

    for i, name in enumerate(names):
        blob += struct.pack("<II", i + 1, 0)
        raw = name.encode("latin-1")
        blob += raw + b"\x00" * (0x38 - len(raw))

    for _ in range(dc_count):
        if bad_dc_prefix:
            blob += b"\xFF" * 16
        else:
            blob += b"\x00" * 8 + b"\x0b\x00\x09\x00\x04\x00\x00\x00"
        raw = ("DC_" + banner).encode("latin-1")
        blob += raw + b"\x00" * (0x38 - len(raw))
    return bytes(blob)


def _named_record(type_code: int, size: int, name: str) -> bytes:
    raw = name.encode("latin-1")
    assert len(raw) < 0x38
    return (struct.pack("<II", type_code, size)
            + raw + b"\x00" * (0x38 - len(raw)))


def _marker_record(class_id: int, body: int = 8) -> bytes:
    """A typed marker. Total size is 8 + body and must be 16-byte aligned, so
    ``body`` is 8 (total 0x10) or 24 (total 0x20) — matching real files."""
    assert (8 + body) % 0x10 == 0, "marker record must be 16-byte aligned"
    return struct.pack("<II", 0x80000000 | class_id, 0) + b"\x00" * body


def wad_records_bytes(
    banner: str = "WAD_R_Sword00",
    resource_classes=(("WAD", 20), ("TXRX", 7), ("MDLX", 13), ("BHVX", 18)),
) -> bytes:
    """A synthetic WAD carrying a proper record stream (E-023/E-024).

    ``resource_classes`` is a sequence of ``(prefix, class_id)``; each becomes a
    ``GroupStart``, a resource, a marker and a ``GroupEnd``, matching the real
    layout. Ends with ``PopHeap`` and the root banner record.
    """
    blob = bytearray()
    blob += struct.pack("<II", 20, 8)
    blob += banner.encode("latin-1")
    blob += b"\x00" * (0x50 - len(blob))       # records start at 0x50 (E-025)

    for prefix, class_id in resource_classes:
        blob += _named_record(2, 0, "GroupStart")
        blob += _named_record(1, 0x18 if prefix == "WAD" else 0x10,
                              f"{prefix}_{banner[4:] if prefix == 'WAD' else banner}")
        blob += _marker_record(class_id, body=24 if prefix == "WAD" else 8)
        blob += _named_record(3, 0, "GroupEnd")

    blob += _named_record(0x15, 0, "PopHeap")
    blob += _named_record(0x12, 0, banner)
    return bytes(blob)


def dc_chunk(banner: str, chunk_id: int, payload: bytes) -> bytes:
    """One ``DC_`` data chunk: 16-byte prefix + 0x34 name field + payload."""
    prefix = (b"\x00" * 8 + struct.pack("<HH", chunk_id, 0x0009)
              + struct.pack("<I", len(payload)))
    name = ("DC_" + banner).encode("latin-1")
    blob = prefix + name + b"\x00" * (0x34 - len(name)) + payload
    pad = (-len(blob)) % 0x10
    return blob + b"\x00" * pad


def wad_with_data_chunks(banner: str = "WAD_R_Sword00",
                         sizes=(4, 0x40, 8, 4, 0x30, 0x20)) -> bytes:
    """A synthetic WAD: directory then six ``DC_`` data chunks (E-025)."""
    blob = bytearray(fixtures_records(banner))
    for index, size in enumerate(sizes):
        payload = bytes((index + 1,)) * size
        blob += dc_chunk(banner, 0x0B + index, payload)
    return bytes(blob)


def fixtures_records(banner: str = "WAD_R_Sword00") -> bytes:
    return wad_records_bytes(banner)
