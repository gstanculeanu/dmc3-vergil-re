"""Tests for the DDS -> PNG converter (issue T2).

Fixtures are synthetic; no game bytes are committed.  The real
``i001_90.tm2`` fixture mirrors the observed header bytes (E-034) — its
embedded DDS is DXT3 (compressed), which the converter now decodes per the
public S3TC specification.
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


def build_dxt_block(fourcc, **kw):
    """Build one 4x4 compressed DDS block (8 bytes DXT1, 16 bytes DXT3/DXT5)."""
    if fourcc == b"DXT1":
        c0 = kw.get("c0", (31, 0, 0))        # 5:6:5 red
        c1 = kw.get("c1", (0, 0, 31))        # 5:6:5 blue
        indices = kw.get("indices", [0] * 16)
        def pack565(r, g, b):
            v = (r & 31) << 11 | (g & 63) << 5 | (b & 31)
            return bytes((v & 0xFF, (v >> 8) & 0xFF))
        block = pack565(*c0) + pack565(*c1)
        ind_bytes = bytearray(4)
        for t, index in enumerate(indices):
            ind_bytes[t // 4] |= (index & 3) << (2 * (t % 4))
        return bytes(block + ind_bytes)
    if fourcc in (b"DXT3", b"DXT5"):
        alpha = kw.get("alpha")
        c0 = kw.get("c0", (0, 0, 0))
        c1 = kw.get("c1", (0, 0, 0))
        indices = kw.get("indices", [0] * 16)
        def pack565(r, g, b):
            v = (r & 31) << 11 | (g & 63) << 5 | (b & 31)
            return bytes((v & 0xFF, (v >> 8) & 0xFF))
        block = pack565(*c0) + pack565(*c1)
        ind_bytes = bytearray(4)
        for t, index in enumerate(indices):
            ind_bytes[t // 4] |= (index & 3) << (2 * (t % 4))
        if fourcc == b"DXT3":
            ab_bytes = bytearray(8)
            for t, a in enumerate(alpha):   # 4-bit alpha, 0..15
                nibble = a & 0xF
                if t % 2 == 0:
                    ab_bytes[t // 2] |= nibble
                else:
                    ab_bytes[t // 2] |= nibble << 4
            return bytes(ab_bytes) + block + bytes(ind_bytes)
        # DXT5: a0, a1, then 48 bits of 3-bit indices, texel 0 at the lowest bit
        a0, a1 = kw.get("a0", 255), kw.get("a1", 0)
        bits = 0
        for t, index in enumerate(indices):
            bits |= (index & 7) << (3 * t)
        idx_bytes = bytes((bits >> (8 * i)) & 0xFF for i in range(6))
        return bytes((a0, a1)) + idx_bytes + block + bytes(ind_bytes)
    raise ValueError(f"unsupported fourcc {fourcc!r}")


def build_dxt_dds(width, height, fourcc, blocks):
    """A minimal DDS: 128-byte header + ``blocks`` block payloads."""
    header = bytearray(128)
    header[0:4] = b"DDS "
    struct.pack_into("<I", header, 4, 124)
    struct.pack_into("<I", header, 8, 0x00081007)   # fourCC + size/pitch/etc.
    struct.pack_into("<I", header, 12, height)
    struct.pack_into("<I", header, 16, width)
    block_bytes = {b"DXT1": 8, b"DXT3": 16, b"DXT5": 16}[fourcc]
    struct.pack_into("<I", header, 20, len(blocks) * block_bytes)
    struct.pack_into("<I", header, 28, 1)
    struct.pack_into("<I", header, 76, 32)
    struct.pack_into("<I", header, 80, 0x4)
    header[84:88] = fourcc
    return bytes(header) + b"".join(blocks)


def expected_png_rows(width, height, rgba):
    """The exact filtered (filter 0 = None) row bytes a correct encoder emits."""
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            rows += bytes(rgba[y * width + x])
    return bytes(rows)


def png_rows(png, width, height):
    """Split a converter PNG into per-row bytes (filter byte + texels)."""
    chunks = parse_png(png)
    raw = zlib.decompress(b"".join(data for ch_type, data in chunks if ch_type == b"IDAT"))
    stride = 1 + width * 4
    return [raw[stride * y: stride * (y + 1)] for y in range(height)]


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

    def test_not_a_dds_raises(self):
        with self.assertRaises(Tm2Error):
            dds_to_png(b"\x00" * 64)

    def test_truncated_payload_raises(self):
        dds = build_dds(2, 2, [(0, 0, 0, 0)] * 4)
        truncated = dds[:128]  # header only, no pixel data
        with self.assertRaises(DdsError):
            dds_to_png(truncated)

    # ------------------------------------------------------------------
    # DXT1 (BC1)
    # ------------------------------------------------------------------

    def test_dxt1_picks_endpoint_colors(self):
        block = build_dxt_block(b"DXT1", c0=(31, 0, 0), c1=(0, 0, 31), indices=[0] * 16)
        png = dds_to_png(build_dxt_dds(4, 4, b"DXT1", [block]))
        rows = png_rows(png, 4, 4)
        self.assertEqual(rows, [b"\x00" + b"\xff\x00\x00\xff" * 4] * 4)

    def test_dxt1_uses_second_endpoint(self):
        block = build_dxt_block(b"DXT1", c0=(31, 0, 0), c1=(0, 0, 31), indices=[1] * 16)
        png = dds_to_png(build_dxt_dds(4, 4, b"DXT1", [block]))
        rows = png_rows(png, 4, 4)
        self.assertEqual(rows, [b"\x00" + b"\x00\x00\xff\xff" * 4] * 4)

    def test_dxt1_interpolation(self):
        """c0 > c1: index 2 -> (2*c0 + c1)//3 per 5:6:5 channel, expanded to 8-bit.
        c0 red (31,0,0), c1 blue (0,0,31): lerp3 -> (20, 0, 10) -> (165, 0, 82)."""
        block = build_dxt_block(b"DXT1", c0=(31, 0, 0), c1=(0, 0, 31), indices=[2] * 16)
        png = dds_to_png(build_dxt_dds(4, 4, b"DXT1", [block]))
        rows = png_rows(png, 4, 4)
        self.assertEqual(rows, [b"\x00" + b"\xa5\x00\x52\xff" * 4] * 4)

    def test_dxt1_c0_le_c1_makes_index_3_transparent(self):
        """c0 <= c1: index 3 is transparent black (0, 0, 0, 0)."""
        block = build_dxt_block(b"DXT1", c0=(0, 0, 31), c1=(31, 0, 0), indices=[3] * 16)
        png = dds_to_png(build_dxt_dds(4, 4, b"DXT1", [block]))
        rows = png_rows(png, 4, 4)
        self.assertEqual(rows, [b"\x00" + b"\x00\x00\x00\x00" * 4] * 4)

    def test_dxt1_index_bits_are_lsb_first(self):
        """Only texel 5 (row 1, column 1; byte 1 bits 2-3) selects c1; the rest c0."""
        indices = [0] * 16
        indices[5] = 1
        block = build_dxt_block(b"DXT1", c0=(31, 0, 0), c1=(0, 0, 31), indices=indices)
        png = dds_to_png(build_dxt_dds(4, 4, b"DXT1", [block]))
        rows = png_rows(png, 4, 4)
        red = b"\xff\x00\x00\xff"
        blue = b"\x00\x00\xff\xff"
        self.assertEqual(rows[0], b"\x00" + red * 4)
        self.assertEqual(rows[1], b"\x00" + red + blue + red + red)
        self.assertEqual(rows[2], b"\x00" + red * 4)
        self.assertEqual(rows[3], b"\x00" + red * 4)

    # ------------------------------------------------------------------
    # DXT3 (BC2)
    # ------------------------------------------------------------------

    def test_dxt3_alpha_bitmap_low_nibble_first(self):
        """Byte 0 = 0x0F: texel 0 alpha 15 -> 255, texel 1 alpha 0 -> 0."""
        block = build_dxt_block(b"DXT3", alpha=[15, 0] + [0] * 14,
                                c0=(0, 0, 0), c1=(0, 0, 0), indices=[0] * 16)
        png = dds_to_png(build_dxt_dds(4, 4, b"DXT3", [block]))
        rows = png_rows(png, 4, 4)
        self.assertEqual(rows[0], b"\x00" + b"\x00\x00\x00\xff\x00\x00\x00\x00" + b"\x00\x00\x00\x00" * 2)

    def test_dxt3_alpha_expansion_x17(self):
        """4-bit alpha 10 -> 170 (0xA * 17)."""
        block = build_dxt_block(b"DXT3", alpha=[10] * 16,
                                c0=(0, 0, 0), c1=(0, 0, 0), indices=[0] * 16)
        png = dds_to_png(build_dxt_dds(4, 4, b"DXT3", [block]))
        rows = png_rows(png, 4, 4)
        self.assertEqual(rows, [b"\x00" + b"\x00\x00\x00\xaa" * 4] * 4)

    # ------------------------------------------------------------------
    # DXT5 (BC3)
    # ------------------------------------------------------------------

    def test_dxt5_alpha_interpolation(self):
        """a0 > a1: index 2 -> (6*a0 + a1)//7 = 218, index 7 -> (a0 + 6*a1)//7 = 36."""
        block = build_dxt_block(b"DXT5", a0=255, a1=0,
                                indices=[2] * 8 + [7] * 8,
                                c0=(0, 0, 0), c1=(0, 0, 0))
        png = dds_to_png(build_dxt_dds(4, 4, b"DXT5", [block]))
        rows = png_rows(png, 4, 4)
        self.assertEqual(rows[0], b"\x00" + b"\x00\x00\x00\xda" * 4)
        self.assertEqual(rows[1], b"\x00" + b"\x00\x00\x00\xda" * 4)
        self.assertEqual(rows[2], b"\x00" + b"\x00\x00\x00\x24" * 4)
        self.assertEqual(rows[3], b"\x00" + b"\x00\x00\x00\x24" * 4)

    def test_dxt5_alpha_a0_le_a1_uses_zero_and_255(self):
        """a0 <= a1: index 6 -> 0, index 7 -> 255."""
        block = build_dxt_block(b"DXT5", a0=0, a1=255,
                                indices=[6, 7] * 8,
                                c0=(0, 0, 0), c1=(0, 0, 0))
        png = dds_to_png(build_dxt_dds(4, 4, b"DXT5", [block]))
        rows = png_rows(png, 4, 4)
        row = b"\x00" + b"\x00\x00\x00\x00\x00\x00\x00\xff" * 2
        self.assertEqual(rows, [row] * 4)

    def test_dxt5_three_bit_indices_lsb_first(self):
        """Texel 0 in the lowest 3 bits of byte 2 -> alpha 255; texel 1 -> alpha 0."""
        indices = [0] * 16
        indices[0] = 7
        block = build_dxt_block(b"DXT5", a0=0, a1=255,
                                indices=indices,
                                c0=(0, 0, 0), c1=(0, 0, 0))
        png = dds_to_png(build_dxt_dds(4, 4, b"DXT5", [block]))
        rows = png_rows(png, 4, 4)
        self.assertEqual(rows[0], b"\x00" + b"\x00\x00\x00\xff" + b"\x00\x00\x00\x00" * 3)

    # ------------------------------------------------------------------
    # Unsupported compressed formats
    # ------------------------------------------------------------------

    def test_unsupported_compressed_fourcc_raises(self):
        for fourcc in (b"DXT2", b"DX10", b"ATI1"):
            with self.subTest(fourcc=fourcc):
                dds = fixtures.dds_header(fourcc=fourcc)
                with self.assertRaises(DdsError):
                    dds_to_png(dds)

    # ------------------------------------------------------------------
    # Real-artifact shape (fixture mirrors i001_90.tm2, E-034)
    # ------------------------------------------------------------------

    def test_real_shaped_dxt3_decodes_top_mip(self):
        """``real_tm2()`` is a 256x256 DXT3: the converter produces a valid
        256x256 PNG without truncating the 64 KiB payload.  No game bytes are
        committed; the payload here is synthetic padding, not the real texture.
        """
        # The real payload is 64 KiB (65,536 = 4096 DXT3 blocks x 16 bytes);
        # synthetic padding stands in for the real texture bytes.
        png = dds_to_png(fixtures.real_tm2_dds() + b"\xAB" * 65536)
        chunks = parse_png(png)
        ihdr = struct.unpack(">IIBBBBB", chunks[0][1])
        self.assertEqual((ihdr[0], ihdr[1]), (256, 256))
        idat = b"".join(data for ch_type, data in chunks if ch_type == b"IDAT")
        raw = zlib.decompress(idat)
        # Block 0 of the 0xAB-padded payload: alpha bytes 0xAB -> texel 0 alpha
        # low nibble 0xB -> 187, texel 1 alpha high nibble 0xA -> 170; c0==c1
        # -> index 3 is black (0,0,0) and index 2 is (173,117,90) per the
        # 5:6:5 expansion of 0xABAB (R5=21,G6=29,B5=11).
        self.assertEqual(raw[1: 1 + 4], b"\x00\x00\x00\xbb")            # index 3
        self.assertEqual(raw[1 + 4: 1 + 8], b"\xad\x75\x5a\xaa")        # 173,117,90,170


if __name__ == "__main__":
    unittest.main()
