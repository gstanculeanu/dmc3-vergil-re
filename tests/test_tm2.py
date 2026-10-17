import _bootstrap  # noqa: F401
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
