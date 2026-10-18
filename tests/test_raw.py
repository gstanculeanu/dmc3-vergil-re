import _bootstrap  # noqa: F401  (adds ../tools to sys.path)
import struct
import unittest

import fixtures
from dmc3 import RawHeader
from dmc3.raw import (
    SLOT0_HEADER_SIZE,
    SLOT10_PAIR_COUNT,
    SLOT21_SEPARATOR,
    maybe_raw_header,
    maybe_slot10_table,
    maybe_slot21_table,
    RawHeader,
    Slot10Table,
    Slot21Table,
)


def chunk_data() -> bytes:
    return fixtures.raw_chunk_slot0()


def slot10_data() -> bytes:
    return fixtures.raw_chunk_slot10()


def slot21_data() -> bytes:
    return fixtures.raw_chunk_slot21()


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


class TestSlot10Table(unittest.TestCase):
    """Decoded slot-10 table layout (E-037). All values are verbatim
    observations from pl021.pac slot 10; every field meaning is [UNKNOWN] and
    is only asserted, never interpreted."""

    def expected_pairs(self) -> tuple[tuple[int, int], ...]:
        pairs = tuple((92, 132 + 20 * i) for i in range(15))
        pairs += ((112, 432), (92, 432))
        pairs += ((92, 132),) * 6
        self.assertEqual(len(pairs), SLOT10_PAIR_COUNT)
        return pairs

    def test_parses_slot_10_table(self):
        table = Slot10Table.parse(slot10_data())
        self.assertEqual(table.pairs, self.expected_pairs())
        self.assertEqual(len(table.pairs), SLOT10_PAIR_COUNT)

    REAL_FLOAT_PREFIX = bytes.fromhex("9a99993e0ad7a3bccdccccbd000000006666663f")
    """Verbatim f32s from pl021.pac slot 10 at body+0x5C (E-037)."""

    def test_reads_float_stream(self):
        import struct

        expected = struct.unpack("<5f", self.REAL_FLOAT_PREFIX)
        table = Slot10Table.parse(slot10_data())
        for observed, want in zip(table.floats[:5], expected):
            self.assertAlmostEqual(observed, want, places=6)
        self.assertTrue(all(v == 0.0 for v in table.floats[5:]))

    def test_pairs_match_real_bytes(self):
        # Verbatim u16 pairs from pl021.pac slot 10, file offset 0x077ED0
        # (E-037): pairs 0-14 have first element 92, second rising by 20.
        table = Slot10Table.parse(slot10_data())
        self.assertEqual(table.pairs[:3], ((92, 132), (92, 152), (92, 172)))
        self.assertEqual(table.pairs[14], (92, 412))
        self.assertEqual(table.pairs[15], (112, 432))
        self.assertEqual(table.pairs[16], (92, 432))
        self.assertEqual(table.pairs[17:], ((92, 132),) * 6)

    def test_rejects_short_input(self):
        with self.assertRaises(ValueError):
            Slot10Table.parse(slot10_data()[:4 * SLOT10_PAIR_COUNT - 1])
        self.assertIsNone(maybe_slot10_table(b"\x00" * 10))


class TestSlot21Table(unittest.TestCase):
    """Decoded slot-21 u16 segment table (E-043). All values are verbatim
    observations from pl021.pac slot 21; every field meaning is [UNKNOWN] and
    is only asserted, never interpreted."""

    REAL_SEGMENT_SIZES = (2, 6, 1, 8, 10, 31, 111, 34, 1, 6, 8, 27, 84, 26)
    """Segment sizes (u16s each) observed in pl021.pac slot 21 (E-043)."""

    def test_parses_slot_21_segments(self):
        table = Slot21Table.parse(slot21_data())
        self.assertEqual(len(table.segments), len(self.REAL_SEGMENT_SIZES))
        self.assertEqual(
            [len(seg) for seg in table.segments], list(self.REAL_SEGMENT_SIZES)
        )
        # Segment 0 is verbatim from pl021.pac slot 21 (E-043).
        self.assertEqual(table.segments[0], (6, 408))

    def test_separators_are_not_segment_data(self):
        table = Slot21Table.parse(slot21_data())
        self.assertFalse(
            any(SLOT21_SEPARATOR in segment for segment in table.segments)
        )

    def test_rejects_odd_length(self):
        with self.assertRaises(ValueError):
            Slot21Table.parse(b"\x00" * 5)
        self.assertIsNone(maybe_slot21_table(b"\x00" * 5))

    def test_empty_input_yields_one_empty_segment(self):
        table = Slot21Table.parse(b"")
        self.assertEqual(table.segments, ((),))


if __name__ == "__main__":
    unittest.main()
