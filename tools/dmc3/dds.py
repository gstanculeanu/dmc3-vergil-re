"""DDS pixel conversion for the DMC3 texture pipeline (issue T2).

Converts an embedded DDS blob (as extracted from an HD-Collection ``.tm2`` by
:mod:`dmc3.tm2`) into a PNG.  Only uncompressed BGRA32 DDS payloads are decoded
here: the DDS BGRA layout is reordered to PNG RGBA byte-for-byte, so the alpha
channel is carried through unchanged.  DXT1/DXT3/DXT5-compressed payloads and
DX10 extended headers raise :class:`DdsError` with a message pointing at an
external DXT decoder (the local install's textures, e.g. ``i001_90.tm2``, are
DXT3).  Writing a DXT decoder from memory would be unverifiable without engine
ground truth, so that path is deliberately left documented rather than guessed.

Only the top mip level is decoded.

Evidence: docs/EVIDENCE.md E-005, E-034 (TM2 wraps a plain DDS blob).
"""

from __future__ import annotations

import struct
import zlib
from binascii import crc32

from .tm2 import Tm2Error, parse_dds_header

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class DdsError(Tm2Error):
    """Raised when a DDS payload cannot be converted to PNG."""


def _png_chunk(ch_type: bytes, data: bytes) -> bytes:
    """Build a PNG chunk: length, type, data, CRC32 (all big-endian)."""
    body = ch_type + data
    return (
        struct.pack(">I", len(data))
        + body
        + struct.pack(">I", crc32(body) & 0xFFFFFFFF)
    )


def dds_to_png(dds: bytes) -> bytes:
    """Convert an uncompressed BGRA32 DDS blob to PNG bytes.

    ``dds`` must begin with the ``DDS `` magic.  Only uncompressed RGB payloads
    (``fourcc == 0``, 32 bpp) are supported; DXT1/DXT3/DXT5 and DX10 extended
    headers raise :class:`DdsError`.  Alpha is preserved byte-for-byte.
    """
    info = parse_dds_header(dds)  # validates magic, header size, dimensions

    if info.is_compressed:
        raise DdsError(
            f"compressed DDS ({info.fourcc!r}) is not supported; decode with an "
            f"external DXT tool such as texconv first (see docs/FORMATS.md)"
        )
    if info.rgb_bits != 32:
        raise DdsError(
            f"uncompressed DDS with {info.rgb_bits} bpp is not supported; "
            f"expecting 32 bpp BGRA"
        )

    width, height = info.width, info.height
    # Pitch (bytes per row) lives at DDS header offset 0x14; fall back to
    # width * 4 when the header stores 0.
    pitch = struct.unpack_from("<I", dds, 0x14)[0] or width * 4
    data = dds[info.data_offset:]
    if len(data) < height * pitch:
        raise DdsError(
            f"DDS payload truncated: {len(data)} bytes, expected {height * pitch}"
        )

    rows = bytearray()
    for y in range(height):
        row = data[y * pitch : y * pitch + width * 4]
        if len(row) < width * 4:
            raise DdsError("DDS payload ends mid-row")
        rows.append(0)  # PNG filter type 0 = None
        # DDS BGRA -> PNG RGBA: swap B and R, keep G and A in place.
        for i in range(0, width * 4, 4):
            b, g, r, a = row[i], row[i + 1], row[i + 2], row[i + 3]
            rows += bytes((r, g, b, a))

    idat = zlib.compress(bytes(rows))
    ihdr = struct.pack(
        ">IIBBBBB",
        width,
        height,
        8,   # bit depth
        6,   # color type: truecolor + alpha (RGBA)
        0,   # compression
        0,   # filter
        0,   # interlace
    )
    return (
        _PNG_SIGNATURE
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", idat)
        + _png_chunk(b"IEND", b"")
    )
