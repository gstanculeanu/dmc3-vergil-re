import _bootstrap  # noqa: F401  (adds ../tools to sys.path)
import unittest

import fixtures
from dmc3 import RawHeader
from dmc3.raw import SLOT0_HEADER_SIZE, maybe_raw_header


def chunk_data() -> bytes:
    return fixtures.raw_chunk_slot0()


class TestRawHeader(unittest.TestCase):
    """Decoded raw-chunk header (E-033). All values are verbatim observations
    from pl021.pac slot 0; every field meaning is [UNKNOWN] and is only
    asserted, never interpreted."""

    def test_parses_slot_0_header(self):
        header = RawHeader.parse(chunk_data())
        self.assertEqual(header.field_00, 5)
        self.assertEqual(header.field_04, 43)
        self.assertEqual(header.field_08, 22)
        self.assertEqual(header.field_0c, 43)
        self.assertEqual(header.field_10, 5)
        self.assertEqual(header.field_14, 1)

    def test_header_size(self):
        self.assertEqual(SLOT0_HEADER_SIZE, 0x18)

    def test_rejects_short_input(self):
        with self.assertRaises(ValueError):
            RawHeader.parse(chunk_data()[:SLOT0_HEADER_SIZE - 1])
        self.assertIsNone(maybe_raw_header(b"\x00" * 10))

    def test_fields_match_real_bytes(self):
        # Verbatim from pl021.pac slot 0, file offset 0x80 (E-033).
        header = RawHeader.parse(chunk_data())
        self.assertEqual(
            (header.field_00, header.field_04, header.field_08,
             header.field_0c, header.field_10, header.field_14),
            (5, 43, 22, 43, 5, 1),
        )


if __name__ == "__main__":
    unittest.main()
