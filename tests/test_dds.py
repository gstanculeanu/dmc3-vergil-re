"""Tests for the DDS -> PNG converter (issue T2).

Fixtures are synthetic; no game bytes are committed.  The real ``i001_90.tm2``
fixture mirrors the observed bytes (E-034) but its embedded DDS is DXT3
(compressed), which this converter deliberately does not decode.
"""

import _bootstrap  # noqa: F401
import struct
import unittest
import zlib
from binascii import crc32

import fixtures
from dmc3 import DdsError, Tm2Error, dds_to_png, find_dds, parse_dds_header

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def build_dds(width, height, rgba, pitch=None, fourcc=b"\x00\x00\x00\x00"):
    """Build a legacy uncompressed BGRA32 DDS blob from RGBA pixels."""
    if pitch is None:
        pitch = width * 4
    header = bytearray(128)
    header[0:4] = b"DDS "
    struct.pack_into("<I", header, 4, 124)                      # dwSize
    struct.pack_into("<I", header, 8, 0x40)                     # dwFlags: DDPF_RGB
    struct.pack_into("<I", header, 12, height)                  # dwHeight
    struct.pack_into("<I", header, 16, width)                   # dwWidth
    struct.pack_into("<I", header, 20, pitch)                   # dwPitchOrLinearSize
    struct.pack_into("<I", header, 24, 0)                       # dwDepth
    struct.pack_into("<I", header, 28, 1)                       # dwMipMapCount
    # ddspf, starting at header offset 76
    struct.pack_into("<I", header, 76, 32)                      # ddspf.dwSize
    struct.pack_into("<I", header, 80, 0x40)                    # ddspf.dwFlags (RGB)
    header[84:88] = fourcc                                      # ddspf.dwFourCC
    struct.pack_into("<I", header, 88, 32)                      # ddspf.dwRGBBitCount
    struct.pack_into("<I", header, 92, 0x00FF0000)              # R mask
    struct.pack_into("<I", header, 96, 0x0000FF00)              # G mask
    struct.pack_into("<I", header, 100, 0x000000FF)             # B mask
    struct.pack_into("<I", header, 104, 0xFF000000)             # A mask
    data = bytearray()
    for y in range(height):
        for x in range(width):
            r, g, b, a = rgba[y * width + x]
            data += bytes((b, g, r, a))                         # DDS is BGRA
        data += b"\x00" * (pitch - width * 4)
    return bytes(header) + bytes(data)


def expected_png_rows(width, height, rgba):
    """The exact filtered (filter 0 = None) row bytes a correct encoder emits."""
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            rows += bytes(rgba[y * width + x])
    return bytes(rows)


def parse_png(png):
    """Structurally parse a PNG: signature, chunks, per-chunk CRC32."""
    assert png[:8] == _PNG_SIGNATURE, "not a PNG"
    pos = 8
    chunks = []
    while pos < len(png):
        (length,) = struct.unpack_from(">I", png, pos)
        pos += 4
        ch_type = png[pos:pos + 4]
        pos += 4
        data = png[pos:pos + length]
        pos += length
        (crc,) = struct.unpack_from(">I", png, pos)
        pos += 4
        assert crc == crc32(ch_type + data) & 0xFFFFFFFF, f"bad CRC in {ch_type!r}"
        chunks.append((ch_type, data))
    return chunks


class TestDdsToPng(unittest.TestCase):
    def test_uncompressed_round_trip_is_exact(self):
        width, height = 2, 2
        rgba = [
            (255, 0, 0, 255),    (0, 255, 0, 128),
            (0, 0, 255, 255),    (255, 255, 0, 0),
        ]
        dds = build_dds(width, height, rgba)
        info = parse_dds_header(dds)
        self.assertEqual((info.width, info.height), (2, 2))
        self.assertFalse(info.is_compressed)
        self.assertEqual(info.rgb_bits, 32)

        png = dds_to_png(dds)
        chunks = parse_png(png)
        types = [ch_type for ch_type, _ in chunks]
        self.assertEqual(types[0], b"IHDR")
        self.assertEqual(types[-1], b"IEND")
        self.assertTrue(all(t == b"IDAT" for t in types[1:-1]))

        w, h, depth, ctype, comp, filt, interlace = struct.unpack(">IIBBBBB", chunks[0][1])
        self.assertEqual((w, h), (width, height))
        self.assertEqual((depth, ctype, comp, filt, interlace), (8, 6, 0, 0, 0))

        idat = b"".join(data for ch_type, data in chunks if ch_type == b"IDAT")
        raw = zlib.decompress(idat)
        self.assertEqual(raw, expected_png_rows(width, height, rgba))

    def test_alpha_is_preserved_byte_for_byte(self):
        rgba = [(10, 20, 30, 40), (50, 60, 70, 80), (90, 100, 110, 128), (130, 140, 150, 1)]
        dds = build_dds(2, 2, rgba)
        png = dds_to_png(dds)
        chunks = parse_png(png)
        idat = b"".join(data for ch_type, data in chunks if ch_type == b"IDAT")
        raw = zlib.decompress(idat)
        # Row 0: filter byte + BGRA->RGBA reordered pixels, alpha untouched.
        self.assertEqual(
            raw,
            b"\x00" + b"\n\x14\x1e\x28" + b"2<\x46\x50" + b"\x00" + b"\x5a\x64\x6e\x80" + b"\x82\x8c\x96\x01",
        )

    def test_row_pitch_padding_is_skipped(self):
        rgba = [(255, 0, 0, 255), (0, 255, 0, 255)]
        dds = build_dds(2, 1, rgba, pitch=16)  # 8 bytes of padding after the row
        png = dds_to_png(dds)
        chunks = parse_png(png)
        idat = b"".join(data for ch_type, data in chunks if ch_type == b"IDAT")
        self.assertEqual(zlib.decompress(idat), b"\x00\xff\x00\x00\xff\x00\xff\x00\xff")

    def test_compressed_dxt3_raises(self):
        dds = fixtures.dds_header(fourcc=b"DXT3")
        with self.assertRaises(DdsError):
            dds_to_png(dds)

    def test_compressed_dxt1_and_dxt5_raise(self):
        for fourcc in (b"DXT1", b"DXT5"):
            with self.subTest(fourcc=fourcc):
                with self.assertRaises(DdsError):
                    dds_to_png(fixtures.dds_header(fourcc=fourcc))

    def test_not_a_dds_raises(self):
        with self.assertRaises(Tm2Error):
            dds_to_png(b"\x00" * 64)

    def test_truncated_payload_raises(self):
        dds = build_dds(2, 2, [(0, 0, 0, 0)] * 4)
        truncated = dds[:128]  # header only, no pixel data
        with self.assertRaises(DdsError):
            dds_to_png(truncated)

    def test_real_tm2_embedded_dds_is_compressed_dxt3(self):
        """i001_90.tm2's embedded DDS (E-034) is DXT3 -> documented unsupported path."""
        raw = fixtures.real_tm2()
        self.assertEqual(find_dds(raw), 0x70)
        dds = raw[0x70:]
        info = parse_dds_header(dds)
        self.assertEqual((info.width, info.height), (256, 256))
        self.assertEqual(info.fourcc, b"DXT3")
        self.assertTrue(info.is_compressed)
        with self.assertRaises(DdsError):
            dds_to_png(dds)


if __name__ == "__main__":
    unittest.main()
