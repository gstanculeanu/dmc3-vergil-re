import _bootstrap  # noqa: F401
import struct
import unittest

import fixtures
from dmc3 import Tm2Error, extract_dds, find_dds, is_hd_tm2, parse_dds_header


class TestTm2(unittest.TestCase):
    def setUp(self):
        self.raw = fixtures.tm2_file()

    def test_finds_embedded_dds(self):
        self.assertEqual(find_dds(self.raw), 0x70)

    def test_extract_starts_with_magic(self):
        dds = extract_dds(self.raw)
        self.assertTrue(dds.startswith(b"DDS "))
        self.assertEqual(len(dds), len(self.raw) - 0x70)

    def test_header_fields(self):
        info = parse_dds_header(extract_dds(self.raw))
        self.assertEqual(info.width, 256)
        self.assertEqual(info.height, 256)
        self.assertEqual(info.mipmaps, 8)
        self.assertEqual(info.fourcc, b"DXT5")
        self.assertEqual(info.pixel_format, "BC3/DXT5")
        self.assertTrue(info.is_compressed)
        self.assertEqual(info.data_offset, 128)

    def test_probe(self):
        self.assertTrue(is_hd_tm2(self.raw))
        self.assertFalse(is_hd_tm2(b"\x00" * 512))

    def test_real_tm2_finds_dds_at_0x70(self):
        """The real i001_90.tm2 pre-header must not hide the DDS magic (E-034)."""
        raw = fixtures.real_tm2()
        self.assertEqual(find_dds(raw), 0x70)
        dds = extract_dds(raw)
        self.assertTrue(dds.startswith(b"DDS "))
        self.assertEqual(len(dds), len(raw) - 0x70)

    def test_real_tm2_preheader_matches_observed_bytes(self):
        """Lock in every pre-header u32 observed in i001_90.tm2 (E-034)."""
        raw = fixtures.real_tm2()
        expected = {
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
        for off, val in expected.items():
            with self.subTest(offset=off):
                self.assertEqual(struct.unpack_from("<I", raw, off)[0], val)
        # every other pre-header offset is zero
        nonzero = {
            off for off in range(0, 0x70, 4)
            if struct.unpack_from("<I", raw, off)[0] != 0
        }
        self.assertEqual(nonzero, set(expected))

    def test_real_tm2_parses_dds_header(self):
        info = parse_dds_header(fixtures.real_tm2()[0x70:])
        self.assertEqual(info.width, 256)
        self.assertEqual(info.height, 256)
        self.assertEqual(info.mipmaps, 1)
        self.assertEqual(info.fourcc, b"DXT3")
        self.assertEqual(info.data_offset, 128)

    def test_missing_payload_raises(self):
        with self.assertRaises(Tm2Error):
            find_dds(b"\x00" * 512)

    def test_bad_header_size_raises(self):
        blob = bytearray(extract_dds(self.raw))
        blob[4:8] = (100).to_bytes(4, "little")
        with self.assertRaises(Tm2Error):
            parse_dds_header(bytes(blob))

    def test_uncompressed_variant(self):
        dds = fixtures.dds_header(fourcc=b"\x00\x00\x00\x00")
        info = parse_dds_header(dds)
        self.assertFalse(info.is_compressed)
        self.assertIn("uncompressed", info.pixel_format)


if __name__ == "__main__":
    unittest.main()
