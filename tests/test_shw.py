import _bootstrap  # noqa: F401  (adds ../tools to sys.path)
import struct
import unittest

import fixtures
from dmc3 import Chunk, ShwHeader
from dmc3.shw import (
    HEADER_SIZE,
    maybe_shw_header,
    maybe_shw_sub_tables,
    parse_shw_sub_tables,
)


def chunk_of(payload: bytes) -> Chunk:
    return Chunk(index=0, offset=0, span=len(payload), data=payload)


class TestShwHeader(unittest.TestCase):
    """Decoded SHW shader-chunk header (E-036). All meanings [UNKNOWN]; only
    the observed bytes/values are asserted."""

    def test_parses_observed_layout(self):
        # Mirrors pl021.pac slot 8 (E-036).
        header = ShwHeader.parse(chunk_of(fixtures.shw_chunk()))
        self.assertEqual(header.alpha, 0.5)
        self.assertEqual(header.field_08, 0)
        self.assertEqual(header.field_0c, 0)
        self.assertEqual(header.field_10, 0x00011811)
        self.assertEqual(header.field_14, 100)
        self.assertEqual(header.field_18, 0)
        self.assertEqual(header.field_1c, 0)
        self.assertEqual(header.pair_20_0, 0x000A)
        self.assertEqual(header.pair_20_1, 0x0010)
        self.assertEqual(header.field_24, 0)
        self.assertEqual(header.field_28, 0)
        self.assertEqual(header.field_2c, 0)
        self.assertEqual(header.field_30, 0x460)
        self.assertEqual(header.field_34, 0)
        self.assertEqual(header.field_38, 0x560)
        self.assertEqual(header.field_3c, 0)
        self.assertEqual(header.field_40, 0x5E0)
        self.assertEqual(header.field_44, 0)
        self.assertEqual(header.field_48, 0x680)
        self.assertEqual(header.field_4c, 0)

    def test_header_size_is_0x50(self):
        self.assertEqual(HEADER_SIZE, 0x50)

    def test_field_28_is_zero(self):
        # +0x28 is u32 0 in all four real SHW chunks (E-036); the varying
        # neighbor is at +0x30 instead.
        header = ShwHeader.parse(chunk_of(fixtures.shw_chunk()))
        self.assertEqual(header.field_28, 0)
        self.assertEqual(header.field_30, 0x460)

    def test_field_30_varies_per_chunk(self):
        # +0x30 differs per mesh: slot 8 -> 0x460, slot 14 -> 0x1E0, slots
        # 24/26 -> 0x60 (E-036).
        values = (
            fixtures.shw_chunk(field_30=0x460),
            fixtures.shw_chunk(field_30=0x1E0),
            fixtures.shw_chunk(field_30=0x60),
        )
        self.assertEqual(
            [ShwHeader.parse(chunk_of(v)).field_30 for v in values],
            [0x460, 0x1E0, 0x60],
        )

    def test_zero_fields_are_zero(self):
        header = ShwHeader.parse(chunk_of(fixtures.shw_chunk()))
        for name in (
            "field_08", "field_0c", "field_18", "field_1c", "field_24",
            "field_28", "field_2c", "field_34", "field_3c", "field_44",
            "field_4c",
        ):
            self.assertEqual(getattr(header, name), 0, name)

    def test_alpha_constant(self):
        # 0.5 (0x3F000000) in every observed SHW chunk.
        header = ShwHeader.parse(chunk_of(fixtures.shw_chunk(alpha=1.0)))
        self.assertEqual(header.alpha, 1.0)

    def test_rejects_wrong_tag(self):
        blob = fixtures.shw_chunk()
        blob = b"XXXX" + blob[4:]
        with self.assertRaises(ValueError):
            ShwHeader.parse(chunk_of(blob))

    def test_rejects_truncated_chunk(self):
        with self.assertRaises(ValueError):
            ShwHeader.parse(chunk_of(fixtures.shw_chunk()[:HEADER_SIZE - 1]))

    def test_maybe_shw_header_returns_none_on_bad_input(self):
        self.assertIsNone(maybe_shw_header(chunk_of(b"nope" * 8)))
        self.assertIsNone(maybe_shw_header(chunk_of(b"SHW " + b"\x00" * 20)))

    def test_real_slot_14_shape(self):
        # pl021.pac slot 14 (E-036): field_10=0x2707, field_14=102,
        # pair=(0x0016, 0x0028), field_28=0, field_30=0x1E0.
        header = ShwHeader.parse(
            chunk_of(
                fixtures.shw_chunk(
                    field_10=0x2707,
                    field_14=102,
                    pair_20_0=0x0016,
                    pair_20_1=0x0028,
                    field_30=0x1E0,
                    field_38=0x460,
                    field_40=0x5A0,
                    field_48=0x700,
                )
            )
        )
        self.assertEqual(header.field_10, 0x2707)
        self.assertEqual(header.field_14, 102)
        self.assertEqual(header.pair_20_0, 0x0016)
        self.assertEqual(header.pair_20_1, 0x0028)
        self.assertEqual(header.field_28, 0)
        self.assertEqual(header.field_30, 0x1E0)

    def test_real_slot_24_shape(self):
        # pl021.pac slots 24/26 (byte-identical, E-036):
        # field_10=0x20101, field_14=0x315D8, pair=(0x0027, 0x0042),
        # field_28=0, field_30=0x60.
        header = ShwHeader.parse(
            chunk_of(
                fixtures.shw_chunk(
                    field_10=0x00020101,
                    field_14=0x000315D8,
                    pair_20_0=0x0027,
                    pair_20_1=0x0042,
                    field_30=0x60,
                    field_38=0x480,
                    field_40=0x690,
                    field_48=0x900,
                )
            )
        )
        self.assertEqual(header.field_10, 0x00020101)
        self.assertEqual(header.field_14, 0x000315D8)
        self.assertEqual(header.pair_20_0, 0x0027)
        self.assertEqual(header.pair_20_1, 0x0042)
        self.assertEqual(header.field_28, 0)
        self.assertEqual(header.field_30, 0x60)


class TestShwSubTables(unittest.TestCase):
    """Decoded SHW sub-tables (E-038): the +0x38 index buffer and the +0x40
    position buffer.  Only the observed structure is asserted; every field
    meaning remains [UNKNOWN]."""

    def _chunk(self, **kw) -> Chunk:
        return chunk_of(fixtures.shw_chunk_with_tables(**kw))

    def test_counts_derived_from_pointer_differences(self):
        # Default fixture: 4 indices, 3 positions; field_38=0x50, field_40=0x70,
        # field_48=0xA0 -> index bytes 0x20 = 4*8, position bytes 0x30 = 3*16.
        chunk = self._chunk()
        header = ShwHeader.parse(chunk)
        sub = parse_shw_sub_tables(chunk.data, header)
        self.assertEqual(header.field_40 - header.field_38, 4 * 8)
        self.assertEqual(header.field_48 - header.field_40, 3 * 16)
        self.assertEqual(sub.index_table.count, 4)
        self.assertEqual(sub.position_table.count, 3)

    def test_index_entries_strip_trailing_zero(self):
        chunk = self._chunk(indices=((10, 20, 30), (40, 50, 60)))
        header = ShwHeader.parse(chunk)
        sub = parse_shw_sub_tables(chunk.data, header)
        self.assertEqual(sub.index_table.indices, ((10, 20, 30), (40, 50, 60)))

    def test_position_entries_keep_w(self):
        chunk = self._chunk(positions=((1.5, -2.5, 3.5, 1.0),))
        header = ShwHeader.parse(chunk)
        sub = parse_shw_sub_tables(chunk.data, header)
        self.assertEqual(sub.position_table.positions, ((1.5, -2.5, 3.5, 1.0),))

    def test_rejects_index_size_not_multiple_of_8(self):
        # field_40 - field_38 = 0x54 - 0x48 = 12, not divisible by 8.
        chunk = self._chunk(field_38=0x48, field_40=0x54, indices=((1, 2, 3),))
        header = ShwHeader.parse(chunk)
        with self.assertRaises(ValueError):
            parse_shw_sub_tables(chunk.data, header)

    def test_rejects_position_size_not_multiple_of_16(self):
        # field_48 - field_40 = 0x60 - 0x50 = 16 -> 1 position OK; use 24.
        chunk = self._chunk(
            field_40=0x50,
            field_48=0x68,
            positions=((1.0, 2.0, 3.0, 1.0), (4.0, 5.0, 6.0, 1.0)),
        )
        header = ShwHeader.parse(chunk)
        with self.assertRaises(ValueError):
            parse_shw_sub_tables(chunk.data, header)

    def test_rejects_table_past_end_of_data(self):
        # The header-only fixture is 96 bytes of data but field_48 == 0x680.
        chunk = chunk_of(fixtures.shw_chunk())
        header = ShwHeader.parse(chunk)
        with self.assertRaises(ValueError):
            parse_shw_sub_tables(chunk.data, header)

    def test_rejects_nonzero_fourth_u16_in_index_entry(self):
        chunk = self._chunk(indices=((1, 2, 3), (4, 5, 6)))
        data = bytearray(chunk.data)
        struct.pack_into("<H", data, 0x50 + 6, 0x0001)  # corrupt entry 0's pad
        header = ShwHeader.parse(chunk_of(bytes(data)))
        with self.assertRaises(ValueError):
            parse_shw_sub_tables(bytes(data), header)

    def test_maybe_returns_none_on_bad_input(self):
        header = ShwHeader.parse(chunk_of(fixtures.shw_chunk()))
        # field_48 == 0x680 runs past 40 bytes of data.
        self.assertIsNone(maybe_shw_sub_tables(b"\x00" * 40, header))

    def test_slot_8_shape_mirrors_real_pointer_structure(self):
        # Mirrors pl021.pac slot 8 (E-036/E-038): field_38=0x560, field_40=0x5E0,
        # field_48=0x680 -> 16 indices, 10 positions; synthetic data values.
        indices = tuple((i % 10, (i + 1) % 10, (i + 2) % 10) for i in range(16))
        positions = tuple(
            (float(i), float(i + 1), float(i + 2), 1.0) for i in range(10)
        )
        chunk = self._chunk(
            field_38=0x560,
            field_40=0x5E0,
            field_48=0x680,
            indices=indices,
            positions=positions,
        )
        header = ShwHeader.parse(chunk)
        sub = parse_shw_sub_tables(chunk.data, header)
        self.assertEqual(sub.index_table.count, 16)
        self.assertEqual(sub.position_table.count, 10)
        self.assertEqual(sub.index_table.indices, indices)
        self.assertEqual(sub.position_table.positions, positions)


if __name__ == "__main__":
    unittest.main()
