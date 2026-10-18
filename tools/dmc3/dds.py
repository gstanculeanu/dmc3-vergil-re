"""DDS pixel conversion for the DMC3 texture pipeline (issue T2).

Converts an embedded DDS blob (as extracted from an HD-Collection ``.tm2`` by
:mod:`dmc3.tm2`) into a PNG.  Only the top mip level is decoded.

Supported payloads:

* uncompressed 32 bpp BGRA (fourCC == 0): the BGRA layout is reordered to PNG
  RGBA byte-for-byte, so the alpha channel is carried through unchanged;
* DXT1 / DXT3 / DXT5 (S3TC/BC1–BC3): decoded from the public, deterministic
  block specification.  Per-channel interpolation uses integer (floor)
  arithmetic; a hardware decoder may differ by +/- 1, which is not claimed here.

DXT decoding is verifiable without engine ground truth: synthetic blocks with
known endpoints and indices produce exact, predictable pixels, and those are
locked in by tests/test_dds.py.  DX10 extended headers and other fourCCs raise
:class:`DdsError`.

Evidence: docs/EVIDENCE.md E-005, E-034 (TM2 wraps a plain DDS blob),
E-047 (real DXT3 payload from ``i001_90.tm2``).
"""

from __future__ import annotations

import struct
import zlib
from binascii import crc32

from .tm2 import Tm2Error, parse_dds_header

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# Compressed block payloads: fourCC -> bytes per 4x4 block (DXT1: 8, DXT3/5: 16).
_BLOCK_BYTES = {
    b"DXT1": 8,
    b"DXT3": 16,
    b"DXT5": 16,
}


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


def _png_rows(width: int, height: int, pixels) -> bytes:
    """Filter type 0 (None) PNG rows from an iterable of (r, g, b, a) pixels."""
    rows = bytearray()
    for y in range(height):
        rows.append(0)  # PNG filter type 0 = None
        base = y * width
        for x in range(width):
            r, g, b, a = pixels[base + x]
            rows += bytes((r, g, b, a))
    return bytes(rows)


def _png(width: int, height: int, pixels) -> bytes:
    """Wrap RGBA pixels in a structural PNG (signature, IHDR, IDAT, IEND)."""
    idat = zlib.compress(_png_rows(width, height, pixels))
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


# ---------------------------------------------------------------------------
# Uncompressed BGRA32
# ---------------------------------------------------------------------------

def _uncompressed_pixels(dds: bytes, info) -> list[tuple[int, int, int, int]]:
    width, height = info.width, info.height
    pitch = struct.unpack_from("<I", dds, 0x14)[0] or width * 4
    data = dds[info.data_offset:]
    if len(data) < height * pitch:
        raise DdsError(
            f"DDS payload truncated: {len(data)} bytes, expected {height * pitch}"
        )
    pixels = []
    for y in range(height):
        row = data[y * pitch : y * pitch + width * 4]
        if len(row) < width * 4:
            raise DdsError("DDS payload ends mid-row")
        for i in range(0, width * 4, 4):
            b, g, r, a = row[i], row[i + 1], row[i + 2], row[i + 3]
            pixels.append((r, g, b, a))  # DDS BGRA -> PNG RGBA
    return pixels


# ---------------------------------------------------------------------------
# DXT / S3TC compressed blocks (public specification)
# ---------------------------------------------------------------------------

def _color565(b0: int, b1: int) -> tuple[int, int, int]:
    """5:6:5 RGB from two little-endian bytes (values in 0..31 / 0..63 / 0..31)."""
    v = b0 | (b1 << 8)
    return (v >> 11) & 0x1F, (v >> 5) & 0x3F, v & 0x1F


def _expand5(v: int) -> int:
    return (v << 3) | (v >> 2)


def _expand6(v: int) -> int:
    return (v << 2) | (v >> 4)


def _indices_2bit(data: bytes) -> list[int]:
    """Four texels per byte, 2 bits each, texel 0 in the lowest bits."""
    indices = []
    for byte in data:
        for shift in (0, 2, 4, 6):
            indices.append((byte >> shift) & 0x3)
    return indices


def _indices_3bit(data: bytes) -> list[int]:
    """Sixteen texels from six bytes, 3 bits each, texel 0 in the lowest bit."""
    bits = 0
    for shift, byte in enumerate(data):
        bits |= byte << (8 * shift)
    return [(bits >> (3 * t)) & 0x7 for t in range(16)]


def _dxt1_colors(c0: bytes, c1: bytes, indices) -> list[tuple[int, int, int, int]]:
    """DXT1 colour block: 16 RGBA texels (alpha 255, or 0 for the transparent
    index when c0 <= c1).  Interpolation is integer (floor) per channel in
    5:6:5 space."""
    r0, g0, b0 = _color565(c0[0], c0[1])
    r1, g1, b1 = _color565(c1[0], c1[1])
    c0_val = c0[0] | (c0[1] << 8)
    c1_val = c1[0] | (c1[1] << 8)

    def lerp2(a, b):
        return (a + b) // 2

    def lerp3(a, b):
        return (2 * a + b) // 3

    def lerp3b(a, b):
        return (a + 2 * b) // 3

    if c0_val > c1_val:
        table = (
            (_expand5(r0), _expand6(g0), _expand5(b0), 255),
            (_expand5(r1), _expand6(g1), _expand5(b1), 255),
            (_expand5(lerp3(r0, r1)), _expand6(lerp3(g0, g1)), _expand5(lerp3(b0, b1)), 255),
            (_expand5(lerp3b(r0, r1)), _expand6(lerp3b(g0, g1)), _expand5(lerp3b(b0, b1)), 255),
        )
    else:
        # c0 <= c1: index 3 is transparent black.
        table = (
            (_expand5(r0), _expand6(g0), _expand5(b0), 255),
            (_expand5(r1), _expand6(g1), _expand5(b1), 255),
            (_expand5(lerp2(r0, r1)), _expand6(lerp2(g0, g1)), _expand5(lerp2(b0, b1)), 255),
            (0, 0, 0, 0),
        )
    return [table[index] for index in indices]


def _dxt1_block(block: bytes) -> list[tuple[int, int, int, int]]:
    return _dxt1_colors(block[0:2], block[2:4], _indices_2bit(block[4:8]))


def _dxt3_block(block: bytes) -> list[tuple[int, int, int, int]]:
    """DXT3: explicit 4-bit alpha bitmap (low nibble first, texel 2i then 2i+1
    in byte i, expanded x17) plus a DXT1 colour block."""
    alphas = []
    for byte in block[0:8]:
        alphas.extend(((byte & 0xF) * 17, (byte >> 4) * 17))
    colors = _dxt1_colors(block[8:10], block[10:12], _indices_2bit(block[12:16]))
    return [(r, g, b, a) for (r, g, b, _), a in zip(colors, alphas)]


def _dxt5_alphas(a0: int, a1: int, indices) -> list[int]:
    if a0 > a1:
        table = (
            a0, a1,
            (6 * a0 + 1 * a1) // 7, (5 * a0 + 2 * a1) // 7,
            (4 * a0 + 3 * a1) // 7, (3 * a0 + 4 * a1) // 7,
            (2 * a0 + 5 * a1) // 7, (1 * a0 + 6 * a1) // 7,
        )
    else:
        table = (
            a0, a1,
            (4 * a0 + 1 * a1) // 5, (3 * a0 + 2 * a1) // 5,
            (2 * a0 + 3 * a1) // 5, (1 * a0 + 4 * a1) // 5,
            0, 255,
        )
    return [table[index] for index in indices]


def _dxt5_block(block: bytes) -> list[tuple[int, int, int, int]]:
    """DXT5: interpolated alpha (2 endpoints + 3-bit indices) plus a DXT1 colour
    block."""
    a0, a1 = block[0], block[1]
    alphas = _dxt5_alphas(a0, a1, _indices_3bit(block[2:8]))
    colors = _dxt1_colors(block[8:10], block[10:12], _indices_2bit(block[12:16]))
    return [(r, g, b, a) for (r, g, b, _), a in zip(colors, alphas)]


_BLOCK_DECODERS = {
    b"DXT1": _dxt1_block,
    b"DXT3": _dxt3_block,
    b"DXT5": _dxt5_block,
}


def _dxt_pixels(dds: bytes, info) -> list[tuple[int, int, int, int]]:
    width, height = info.width, info.height
    block_w = (width + 3) // 4
    block_h = (height + 3) // 4
    block_bytes = _BLOCK_BYTES[info.fourcc]
    needed = block_w * block_h * block_bytes
    data = dds[info.data_offset:]
    if len(data) < needed:
        raise DdsError(
            f"DXT payload truncated: {len(data)} bytes, expected {needed}"
        )
    decoder = _BLOCK_DECODERS[info.fourcc]
    pixels = [(0, 0, 0, 0)] * (width * height)
    for by in range(block_h):
        y0 = by * 4
        if y0 >= height:
            continue
        for bx in range(block_w):
            x0 = bx * 4
            if x0 >= width:
                continue
            block = data[(by * block_w + bx) * block_bytes:
                         (by * block_w + bx) * block_bytes + block_bytes]
            texels = decoder(block)
            for ty in range(4):
                y = y0 + ty
                if y >= height:
                    continue
                base = y * width + x0
                for tx in range(4):
                    x = x0 + tx
                    if x >= width:
                        continue
                    pixels[base + tx] = texels[ty * 4 + tx]
    return pixels


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def dds_to_png(dds: bytes) -> bytes:
    """Convert a DDS blob (uncompressed BGRA32 or DXT1/DXT3/DXT5) to PNG bytes.

    ``dds`` must begin with the ``DDS `` magic.  Only the top mip level is
    decoded; alpha is preserved byte-for-byte (DXT3/DXT5 alpha expanded from
    4-bit / interpolated, DXT1 alpha is 255 or 0).  DX10 extended headers and
    unsupported fourCCs raise :class:`DdsError`.
    """
    info = parse_dds_header(dds)  # validates magic, header size, dimensions

    if info.is_compressed:
        if info.fourcc not in _BLOCK_BYTES:
            raise DdsError(
                f"compressed DDS ({info.fourcc!r}) is not supported; only "
                f"DXT1/DXT3/DXT5 are decoded (see docs/FORMATS.md)"
            )
        pixels = _dxt_pixels(dds, info)
    else:
        if info.rgb_bits != 32:
            raise DdsError(
                f"uncompressed DDS with {info.rgb_bits} bpp is not supported; "
                f"expecting 32 bpp BGRA"
            )
        pixels = _uncompressed_pixels(dds, info)

    return _png(info.width, info.height, pixels)
