import _bootstrap  # noqa: F401  (adds ../tools to sys.path)
import struct
import unittest

import fixtures
from dmc3 import Chunk, ShwHeader
from dmc3.shw import (
    HEADER_SIZE,
    RECORD_ALIGNMENT,
    maybe_shw_header,
    maybe_shw_records,
    maybe_shw_sub_tables,
    parse_shw_records,
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
    """Decoded SHW sub-tables (E-038, E-102): the +0x30 triangle table, the
    +0x38 per-triangle adjacency table and the +0x40 position table.  Only the
    observed structure is asserted; every field meaning remains [UNKNOWN]."""

    def _chunk(self, **kw) -> Chunk:
        return chunk_of(fixtures.shw_chunk_with_tables(**kw))

    def test_counts_derived_from_pointer_differences(self):
        # Default fixture: 4 triangles, 4 adjacency rows, 4 positions;
        # field_30=0x50, field_38=0x90, field_40=0xB0, field_48=0xF0.
        chunk = self._chunk()
        header = ShwHeader.parse(chunk)
        sub = parse_shw_sub_tables(chunk.data, header)
        self.assertEqual(header.field_38 - header.field_30, 4 * 16)
        self.assertEqual(header.field_40 - header.field_38, 4 * 8)
        self.assertEqual(header.field_48 - header.field_40, 4 * 16)
        self.assertEqual(sub.triangle_table.count, 4)
        self.assertEqual(sub.adjacency_table.count, 4)
        self.assertEqual(sub.position_table.count, 4)

    def test_triangle_entries_strip_trailing_zero(self):
        chunk = self._chunk(triangles=((10, 20, 30), (40, 50, 60)))
        header = ShwHeader.parse(chunk)
        sub = parse_shw_sub_tables(chunk.data, header)
        self.assertEqual(sub.triangle_table.triangles, ((10, 20, 30), (40, 50, 60)))

    def test_adjacency_entries_strip_trailing_zero(self):
        chunk = self._chunk(
            triangles=((0, 1, 2), (1, 2, 3)),
            neighbours=((1, 1, 1), (0, 0, 0)),
        )
        header = ShwHeader.parse(chunk)
        sub = parse_shw_sub_tables(chunk.data, header)
        self.assertEqual(sub.adjacency_table.neighbours, ((1, 1, 1), (0, 0, 0)))

    def test_position_entries_keep_w(self):
        chunk = self._chunk(positions=((1.5, -2.5, 3.5, 1.0),))
        header = ShwHeader.parse(chunk)
        sub = parse_shw_sub_tables(chunk.data, header)
        self.assertEqual(sub.position_table.positions, ((1.5, -2.5, 3.5, 1.0),))

    def test_default_fixture_satisfies_every_e102_invariant(self):
        # A closed tetrahedron: the triangles index the positions, the
        # adjacency is symmetric and three-regular, neighbours share an edge.
        chunk = self._chunk()
        header = ShwHeader.parse(chunk)
        sub = parse_shw_sub_tables(chunk.data, header)
        self.assertTrue(sub.triangle_table.references(sub.position_table.count))
        self.assertTrue(sub.adjacency_table.symmetric())
        self.assertTrue(sub.adjacency_table.three_regular())
        self.assertTrue(sub.shared_edges())
        self.assertTrue(sub.consistent)

    def test_consistent_rejects_triangle_out_of_position_range(self):
        # E-102: every triangle index is inside the position table on 58/58.
        chunk = self._chunk(
            triangles=((0, 1, 4),), neighbours=((0, 0, 0),)
        )
        header = ShwHeader.parse(chunk)
        sub = parse_shw_sub_tables(chunk.data, header)
        self.assertFalse(sub.triangle_table.references(sub.position_table.count))
        self.assertFalse(sub.consistent)

    def test_consistent_rejects_asymmetric_adjacency(self):
        # E-102: k appears in the row of every triangle that names it.
        chunk = self._chunk(
            triangles=((0, 1, 2), (1, 2, 3)),
            neighbours=((1, 1, 1), (1, 1, 1)),
        )
        header = ShwHeader.parse(chunk)
        sub = parse_shw_sub_tables(chunk.data, header)
        self.assertFalse(sub.adjacency_table.symmetric())
        self.assertFalse(sub.consistent)

    def test_consistent_rejects_non_three_regular_adjacency(self):
        # E-102: the multiset of neighbour values is 3 copies of 0..N-1.
        chunk = self._chunk(
            triangles=((0, 1, 2), (1, 2, 3)),
            neighbours=((0, 0, 0), (0, 0, 0)),
        )
        header = ShwHeader.parse(chunk)
        sub = parse_shw_sub_tables(chunk.data, header)
        self.assertFalse(sub.adjacency_table.three_regular())
        self.assertFalse(sub.consistent)

    def test_rejects_triangle_count_differing_from_adjacency_count(self):
        # E-102: the two +0x30/+0x38 table counts are always equal.
        chunk = self._chunk(
            field_38=0x50 + 16 * 2,
            triangles=((0, 1, 2), (1, 2, 0)),
            neighbours=((0, 0, 0),),
        )
        header = ShwHeader.parse(chunk)
        with self.assertRaises(ValueError):
            parse_shw_sub_tables(chunk.data, header)

    def test_rejects_triangle_size_not_multiple_of_16(self):
        # field_38 - field_30 = 0x5C - 0x50 = 12, not divisible by 16.
        chunk = self._chunk(field_38=0x5C, triangles=((0, 1, 2),))
        header = ShwHeader.parse(chunk)
        with self.assertRaises(ValueError):
            parse_shw_sub_tables(chunk.data, header)

    def test_rejects_adjacency_size_not_multiple_of_8(self):
        # field_40 - field_38 = 0x82 - 0x60 = 0x22 = 34, not divisible by 8.
        chunk = self._chunk(field_40=0x82, triangles=((0, 1, 2),))
        header = ShwHeader.parse(chunk)
        with self.assertRaises(ValueError):
            parse_shw_sub_tables(chunk.data, header)

    def test_rejects_position_size_not_multiple_of_16(self):
        # field_48 - field_40 = 0xB8 - 0xB0 = 8, not divisible by 16.
        chunk = self._chunk(field_48=0xB8, positions=())
        header = ShwHeader.parse(chunk)
        with self.assertRaises(ValueError):
            parse_shw_sub_tables(chunk.data, header)

    def test_rejects_non_increasing_offsets(self):
        # E-102: field_30 < field_38 <= field_40 <= field_48 on 58/58.
        chunk = self._chunk(field_38=0x50)
        header = ShwHeader.parse(chunk)
        with self.assertRaises(ValueError):
            parse_shw_sub_tables(chunk.data, header)

    def test_rejects_table_past_end_of_data(self):
        # The header-only fixture is 96 bytes of data but field_48 == 0x680.
        chunk = chunk_of(fixtures.shw_chunk())
        header = ShwHeader.parse(chunk)
        with self.assertRaises(ValueError):
            parse_shw_sub_tables(chunk.data, header)

    def test_rejects_nonzero_fourth_u32_in_triangle_entry(self):
        chunk = self._chunk()
        data = bytearray(chunk.data)
        struct.pack_into("<I", data, 0x50 + 12, 0x00000001)  # corrupt entry 0's pad
        header = ShwHeader.parse(chunk_of(bytes(data)))
        with self.assertRaises(ValueError):
            parse_shw_sub_tables(bytes(data), header)

    def test_rejects_nonzero_fourth_u16_in_adjacency_entry(self):
        chunk = self._chunk()
        data = bytearray(chunk.data)
        struct.pack_into("<H", data, 0x90 + 6, 0x0001)  # corrupt entry 0's pad
        header = ShwHeader.parse(chunk_of(bytes(data)))
        with self.assertRaises(ValueError):
            parse_shw_sub_tables(bytes(data), header)

    def test_maybe_returns_none_on_bad_input(self):
        header = ShwHeader.parse(chunk_of(fixtures.shw_chunk()))
        # field_48 == 0x680 runs past 40 bytes of data.
        self.assertIsNone(maybe_shw_sub_tables(b"\x00" * 40, header))

    def test_slot_8_shape_mirrors_real_pointer_structure(self):
        # Mirrors pl021.pac slot 8 (E-036/E-102): field_30=0x460, field_38=0x560,
        # field_40=0x5E0, field_48=0x680 -> 16 triangles, 16 adjacency rows,
        # 10 positions.  Synthetic data values.
        positions = tuple(
            (float(i), float(i + 1), float(i + 2), 1.0) for i in range(10)
        )
        triangles = tuple(
            (i % 10, (i + 1) % 10, (i + 2) % 10) for i in range(16)
        )
        neighbours = tuple(
            ((i + 1) % 16, (i + 2) % 16, (i + 3) % 16) for i in range(16)
        )
        chunk = self._chunk(
            field_30=0x460,
            field_38=0x560,
            field_40=0x5E0,
            field_48=0x680,
            triangles=triangles,
            neighbours=neighbours,
            positions=positions,
        )
        header = ShwHeader.parse(chunk)
        sub = parse_shw_sub_tables(chunk.data, header)
        self.assertEqual(sub.triangle_table.count, 16)
        self.assertEqual(sub.adjacency_table.count, 16)
        self.assertEqual(sub.position_table.count, 10)
        self.assertEqual(sub.triangle_table.triangles, triangles)
        self.assertEqual(sub.adjacency_table.neighbours, neighbours)
        self.assertEqual(sub.position_table.positions, positions)


class TestShwRecords(unittest.TestCase):
    """Decoded SHW record stream (E-103).  A chunk is a sequence of closed
    meshes, each ending in a per-position byte array; only the observed
    structure is asserted and the byte value's meaning stays [UNKNOWN]."""

    def _chunk(self, **kw) -> Chunk:
        return chunk_of(fixtures.shw_chunk_with_records(**kw))

    def test_parses_every_record_in_order(self):
        chunk = self._chunk()
        records = parse_shw_records(chunk.data, ShwHeader.parse(chunk))
        self.assertEqual([r.index for r in records], [0, 1, 2])
        self.assertEqual([r.value for r in records], [0x03, 0x02, 0x0E])

    def test_records_tile_without_gaps(self):
        # E-103: each record starts where the previous record's padded byte
        # array ends; record 0 starts at the header's +0x30 offset.
        chunk = self._chunk()
        header = ShwHeader.parse(chunk)
        records = parse_shw_records(chunk.data, header)
        self.assertEqual(records[0].triangle_offset, header.field_30)
        for previous, current in zip(records, records[1:]):
            self.assertEqual(current.triangle_offset, previous.end)
            self.assertEqual(current.triangle_offset % RECORD_ALIGNMENT, 0)

    def test_record_offsets_match_header_pointers(self):
        # E-103: +0x30/+0x38/+0x40/+0x48 name record 0's four sections.
        chunk = self._chunk()
        header = ShwHeader.parse(chunk)
        first = parse_shw_records(chunk.data, header)[0]
        self.assertEqual(first.triangle_offset, header.field_30)
        self.assertEqual(first.position_offset, header.field_40)
        self.assertEqual(first.array_offset, header.field_48)
        self.assertEqual(
            first.position_offset - first.triangle_offset,
            24 * first.tables.triangle_table.count,
        )

    def test_header_pair20_is_record0_counts(self):
        # E-103: +0x20 / +0x22 equal record 0's position / triangle counts on
        # 58/58 real chunks.
        chunk = self._chunk()
        header = ShwHeader.parse(chunk)
        first = parse_shw_records(chunk.data, header)[0]
        self.assertEqual(header.pair_20_0, first.tables.position_table.count)
        self.assertEqual(header.pair_20_1, first.tables.triangle_table.count)

    def test_record0_tables_match_parse_shw_sub_tables(self):
        chunk = self._chunk()
        header = ShwHeader.parse(chunk)
        records = parse_shw_records(chunk.data, header)
        self.assertEqual(records[0].tables, parse_shw_sub_tables(chunk.data, header))

    def test_vertex_bytes_are_one_constant_per_position(self):
        # E-103: 591/591 real records carry one constant byte per position and
        # the array length equals the position count.
        chunk = self._chunk()
        records = parse_shw_records(chunk.data, ShwHeader.parse(chunk))
        for record in records:
            self.assertEqual(
                len(record.vertex_bytes), record.tables.position_table.count
            )
            self.assertEqual(set(record.vertex_bytes), {record.value})

    def test_records_are_consistent_closed_meshes(self):
        chunk = self._chunk()
        records = parse_shw_records(chunk.data, ShwHeader.parse(chunk))
        for record in records:
            self.assertTrue(record.consistent, record.index)
            self.assertTrue(record.tables.shared_edges(), record.index)

    def test_trailing_zero_padding_is_ignored(self):
        chunk = self._chunk()
        padded = chunk.data + b"\x00" * 64
        header = ShwHeader.parse(chunk)
        self.assertEqual(len(parse_shw_records(padded, header)), 3)

    def test_rejects_nonconstant_vertex_byte_array(self):
        chunk = self._chunk()
        header = ShwHeader.parse(chunk)
        first = parse_shw_records(chunk.data, header)[0]
        data = bytearray(chunk.data)
        data[first.array_offset + 1] ^= 0xFF
        with self.assertRaises(ValueError):
            parse_shw_records(bytes(data), header)

    def test_rejects_nonzero_array_padding(self):
        chunk = self._chunk()
        header = ShwHeader.parse(chunk)
        first = parse_shw_records(chunk.data, header)[0]
        data = bytearray(chunk.data)
        # The 4-position array occupies 4 bytes; +4..+15 must be NUL.
        data[first.array_offset + 4] = 0xFF
        with self.assertRaises(ValueError):
            parse_shw_records(bytes(data), header)

    def test_rejects_truncated_stream(self):
        chunk = self._chunk()
        header = ShwHeader.parse(chunk)
        records = parse_shw_records(chunk.data, header)
        cut = chunk.data[:records[1].triangle_offset + 24]
        with self.assertRaises(ValueError):
            parse_shw_records(cut, header)

    def test_maybe_records_returns_none_on_bad_input(self):
        chunk = self._chunk()
        header = ShwHeader.parse(chunk)
        self.assertEqual(len(maybe_shw_records(chunk.data, header)), 3)
        self.assertIsNone(maybe_shw_records(b"\x00" * 40, header))

    def test_single_record_chunk_matches_slots_24_26_shape(self):
        # Slots 24/26 of pl021.pac carry exactly one record: +0x48 points at
        # its byte array and nothing follows (E-103).  Build that shape.
        positions = tuple((float(i), 0.0, 0.0, 1.0) for i in range(8))
        triangles = ((0, 1, 2), (1, 2, 3), (0, 2, 3), (0, 1, 3))
        neighbours = ((1, 2, 3), (0, 2, 3), (0, 1, 3), (0, 1, 2))
        chunk = self._chunk(
            records=((0x01, triangles, neighbours, positions),)
        )
        header = ShwHeader.parse(chunk)
        records = parse_shw_records(chunk.data, header)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].value, 0x01)
        self.assertEqual(records[0].end, len(chunk.data) - 16)


if __name__ == "__main__":
    unittest.main()
