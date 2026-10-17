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
