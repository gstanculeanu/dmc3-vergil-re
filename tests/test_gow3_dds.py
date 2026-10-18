import _bootstrap  # noqa: F401
import struct
import unittest

from gow3 import dds
from gow3.dds import DdsError


def dds_header(width: int, height: int, fourcc: bytes, mips: int = 1) -> bytes:
    blob = bytearray(128)
    blob[0:4] = b"DDS "
    struct.pack_into("<I", blob, 4, 124)
    struct.pack_into("<I", blob, 8, 0x00081007)
    struct.pack_into("<I", blob, 12, height)
    struct.pack_into("<I", blob, 16, width)
    struct.pack_into("<I", blob, 28, mips)
    struct.pack_into("<I", blob, 76, 32)
    struct.pack_into("<I", blob, 80, 0x4)          # DDPF_FOURCC
    blob[84:88] = fourcc
    return bytes(blob)


def blocks(w: int, h: int, size: int) -> int:
    return max(1, (w + 3) // 4) * max(1, (h + 3) // 4)


class TestParse(unittest.TestCase):
    def test_parses_dimensions_and_format(self):
        data = dds_header(64, 32, b"DXT5", mips=3)
        texture = dds.parse_at(data, 0)
        self.assertEqual((texture.width, texture.height, texture.mips), (64, 32, 3))
        self.assertEqual(texture.fourcc, b"DXT5")
        self.assertTrue(texture.is_block_compressed)

    def test_rejects_non_dds(self):
        with self.assertRaises(DdsError):
            dds.parse_at(b"not a dds" + b"\x00" * 200, 0)

    def test_rejects_bad_header_size(self):
        blob = bytearray(dds_header(8, 8, b"DXT1"))
        struct.pack_into("<I", blob, 4, 100)
        with self.assertRaises(DdsError):
            dds.parse_at(bytes(blob), 0)

    def test_rejects_implausible_dimensions(self):
        blob = bytearray(dds_header(8, 8, b"DXT1"))
        struct.pack_into("<I", blob, 16, 0)
        with self.assertRaises(DdsError):
            dds.parse_at(bytes(blob), 0)


class TestSizes(unittest.TestCase):
    def test_dxt1_block_size(self):
        # 8x8 DXT1, one mip: 4 blocks * 8 bytes
        data = dds_header(8, 8, b"DXT1", mips=1) + b"\x00" * 32
        texture = dds.parse_at(data, 0)
        self.assertEqual(texture.data_size, 32)
        self.assertEqual(texture.end, 160)

    def test_dxt5_block_size(self):
        data = dds_header(8, 8, b"DXT5", mips=1) + b"\x00" * 64
        texture = dds.parse_at(data, 0)
        self.assertEqual(texture.data_size, 64)

    def test_mips_add_up(self):
        # 8x8 -> 4x4 -> 2x2 -> 1x1, DXT1 = 4+1+1+1 = 7 blocks * 8
        data = dds_header(8, 8, b"DXT1", mips=4)
        texture = dds.parse_at(data, 0)
        self.assertEqual(texture.data_size, 7 * 8)

    def test_minimum_block_for_tiny_levels(self):
        data = dds_header(2, 2, b"DXT1", mips=1)
        texture = dds.parse_at(data, 0)
        self.assertEqual(texture.data_size, 8)


class TestFind(unittest.TestCase):
    def test_finds_all_textures(self):
        one = dds_header(8, 8, b"DXT1") + b"\x00" * 32
        two = dds_header(8, 8, b"DXT5") + b"\x00" * 64
        data = b"\xAA" * 16 + one + b"\xBB" * 16 + two
        found = dds.find_textures(data)
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0].offset, 16)
        self.assertEqual(found[1].fourcc, b"DXT5")

    def test_unknown_formats_are_skipped_by_default(self):
        data = dds_header(8, 8, b"ABCD") + b"\x00" * 32
        self.assertEqual(dds.find_textures(data), [])
        self.assertEqual(len(dds.find_textures(data, require_known_format=False)), 1)


class TestTint(unittest.TestCase):
    def test_rgb565_packing(self):
        self.assertEqual(dds.rgb565(31, 0, 0), 0xF800)   # pure red
        self.assertEqual(dds.rgb565(0, 63, 0), 0x07E0)   # pure green
        self.assertEqual(dds.rgb565(0, 0, 31), 0x001F)   # pure blue

    def test_dxt1_colour_blocks_are_at_block_starts(self):
        data = dds_header(8, 8, b"DXT1") + b"\x00" * 32
        texture = dds.parse_at(data, 0)
        got = list(dds.colour_blocks(data, texture))
        self.assertEqual(got, [128, 136, 144, 152])

    def test_dxt5_colour_blocks_skip_the_alpha_half(self):
        data = dds_header(8, 8, b"DXT5") + b"\x00" * 64
        texture = dds.parse_at(data, 0)
        got = list(dds.colour_blocks(data, texture))
        self.assertEqual(got, [136, 152, 168, 184])

    def test_tint_sets_both_endpoints_and_keeps_length(self):
        data = dds_header(8, 8, b"DXT1") + b"\x11" * 32
        texture = dds.parse_at(data, 0)
        out = dds.tint_in_place(data, texture, 0xF800)
        self.assertEqual(len(out), len(data))
        for base in dds.colour_blocks(data, texture):
            self.assertEqual(out[base:base + 4], b"\x00\xf8\x00\xf8")

    def test_tint_does_not_touch_headers_or_indices(self):
        data = dds_header(8, 8, b"DXT1") + b"\x11" * 32
        texture = dds.parse_at(data, 0)
        out = dds.tint_in_place(data, texture, 0xF800)
        self.assertEqual(out[:texture.data_offset], data[:texture.data_offset])
        for base in dds.colour_blocks(data, texture):
            self.assertEqual(out[base + 4:base + 8], data[base + 4:base + 8])

    def test_only_endpoint_bytes_change(self):
        data = dds_header(8, 8, b"DXT5") + bytes(range(64))
        texture = dds.parse_at(data, 0)
        out = dds.tint_in_place(data, texture, 0xF800)
        allowed = set()
        for base in dds.colour_blocks(data, texture):
            allowed.update(range(base, base + 4))
        for start, end in dds.changed_ranges(data, out):
            for offset in range(start, end):
                self.assertIn(offset, allowed)

    def test_unchanged_when_already_that_colour(self):
        # four 8-byte DXT1 blocks whose endpoints already hold 0xF800
        data = dds_header(8, 8, b"DXT1") + (b"\x00\xf8\x00\xf8" + b"\x11" * 4) * 4
        texture = dds.parse_at(data, 0)
        out = dds.tint_in_place(data, texture, 0xF800)
        self.assertEqual(out, data)

    def test_truncated_texture_is_refused(self):
        data = dds_header(8, 8, b"DXT1") + b"\x00" * 8      # needs 32
        texture = dds.parse_at(data, 0)
        with self.assertRaises(DdsError):
            dds.tint_in_place(data, texture)

    def test_non_block_format_is_refused(self):
        blob = bytearray(dds_header(8, 8, b"\x00\x00\x00\x00"))
        struct.pack_into("<I", blob, 80, 0x40)              # not FOURCC
        texture = dds.parse_at(bytes(blob), 0)
        self.assertFalse(texture.is_block_compressed)
        with self.assertRaises(DdsError):
            dds.tint_in_place(bytes(blob), texture)


class TestChangedRanges(unittest.TestCase):
    def test_reports_contiguous_runs(self):
        self.assertEqual(dds.changed_ranges(b"aaXaaYYa", b"aaZaaWWa"),
                         [(2, 3), (5, 7)])

    def test_reports_nothing_when_equal(self):
        self.assertEqual(dds.changed_ranges(b"abc", b"abc"), [])

    def test_length_mismatch_is_refused(self):
        with self.assertRaises(DdsError):
            dds.changed_ranges(b"ab", b"abc")


if __name__ == "__main__":
    unittest.main()
