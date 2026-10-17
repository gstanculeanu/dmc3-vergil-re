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
