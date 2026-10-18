import _bootstrap  # noqa: F401  (adds ../tools to sys.path)
import struct
import unittest

import fixtures
from dmc3 import Chunk, ModBodyBlock, ModBodyDirectory, ModBodyPrefix, ModHeader
from dmc3.mod import (
    BODY_BLOCK_ATTRIBUTE_SIZE,
    BODY_BLOCK_ATTRIBUTE_UNIT,
    BODY_BLOCK_NORMAL_MIN_RUN,
    BODY_BLOCK_NORMAL_TOLERANCE,
    BODY_BLOCK_OFFSET_A,
    BODY_BLOCK_OFFSET_B,
    BODY_BLOCK_OFFSET_C,
    BODY_BLOCK_PREFIX_SIZE,
    BODY_BLOCK_TUPLE_SIZE,
    BODY_BLOCK_ZERO_OFFSETS,
    BODY_DESCRIPTOR_ARRAY_OFFSET,
    BODY_DESCRIPTOR_AUX_OFFSET,
    BODY_DESCRIPTOR_SIZE,
    BODY_DESCRIPTOR_SLACK,
    BODY_DESCRIPTOR_TAG_OFFSET,
    BODY_DESCRIPTOR_VECTOR_OFFSET,
    BODY_PREFIX_SIZE,
    BODY_TAG_MASK,
    BODY_TAG_NAMESPACE,
    BODY_TAG_OFFSET,
    HEADER_SIZE,
    block_attributes,
    block_normals,
    block_positions,
    descriptor_count,
    maybe_mod_body_directory,
    maybe_mod_body_prefix,
    maybe_mod_header,
    normal_run,
    unit_triple,
)


def chunk_of(payload: bytes) -> Chunk:
    return Chunk(index=0, offset=0, span=len(payload), data=payload)


class TestModHeader(unittest.TestCase):
    def test_parses_observed_layout(self):
        header = ModHeader.parse(chunk_of(fixtures.mod_chunk()))
        self.assertEqual(header.scale, fixtures.mod_chunk.__defaults__[0])
        self.assertEqual(header.field_08, 0)
        self.assertEqual(header.field_0c, 0)
        self.assertEqual(header.field_10, 0x10101)
        self.assertEqual(header.field_14, 0xAF258)
        self.assertEqual(header.field_18, 0)
        self.assertEqual(header.field_1c, 0)
        self.assertEqual(header.field_20, 0x160)

    def test_header_size_is_0x24(self):
        self.assertEqual(HEADER_SIZE, 0x24)

    def test_scale_constant(self):
        # 285/286 real MOD chunks carry 1.0099… (0x3F8147AE); one carries 1.0.
        header = ModHeader.parse(chunk_of(fixtures.mod_chunk(scale=1.0)))
        self.assertEqual(header.scale, 1.0)

    def test_rejects_wrong_tag(self):
        blob = fixtures.mod_chunk()
        blob = b"XXXX" + blob[4:]
        with self.assertRaises(ValueError):
            ModHeader.parse(chunk_of(blob))

    def test_rejects_truncated_chunk(self):
        blob = fixtures.mod_chunk(body=b"\x00" * 100)
        with self.assertRaises(ValueError):
            ModHeader.parse(chunk_of(blob[:HEADER_SIZE - 1]))

    def test_maybe_mod_header_returns_none_on_bad_input(self):
        self.assertIsNone(maybe_mod_header(chunk_of(b"nope" * 8)))
        self.assertIsNone(maybe_mod_header(chunk_of(b"MOD " + b"\x00" * 20)))

    def test_body_follows_header(self):
        body = bytes(range(32))
        header = ModHeader.parse(chunk_of(fixtures.mod_chunk(body=body)))
        raw = chunk_of(fixtures.mod_chunk(body=body)).data
        self.assertEqual(raw[HEADER_SIZE:HEADER_SIZE + len(body)], body)

    def test_default_fields_match_real_chunks(self):
        # Observed values on pl021.pac slots 1/12/23/25 (E-030):
        # slot 1: +0x10=0x103180B, +0x14=0xAFE12, +0x20=0x29B30
        header = ModHeader.parse(
            chunk_of(
                fixtures.mod_chunk(
                    field_10=0x103180B, field_14=0xAFE12, field_20=0x29B30
                )
            )
        )
        self.assertEqual(header.field_10, 0x103180B)
        self.assertEqual(header.field_14, 0xAFE12)
        self.assertEqual(header.field_20, 0x29B30)


class TestModBodyPrefix(unittest.TestCase):
    """Decoded MOD payload body prefix (E-031). All meanings [UNKNOWN]; only the
    observed bytes/values are asserted."""

    def test_parses_slot_23_shape(self):
        # pl021.pac slot 23: marker=0x8001, count=182, field_24=128,
        # field_2c=0x00120002, vector≈(-0.196, 0, 42.07, 73.57), repeat=182
        prefix = ModBodyPrefix.parse(fixtures.mod_body())
        self.assertEqual(prefix.marker, 0x8001)
        self.assertEqual(prefix.count, 182)
        self.assertEqual(prefix.field_24, 128)
        self.assertEqual(prefix.field_2c, 0x00120002)
        self.assertAlmostEqual(prefix.vector[0], -0.196165, places=5)
        self.assertAlmostEqual(prefix.vector[1], 0.0, places=5)
        self.assertAlmostEqual(prefix.vector[2], 42.0706, places=4)
        self.assertAlmostEqual(prefix.vector[3], 73.5689, places=4)
        self.assertEqual(prefix.repeat, 182)

    def test_repeat_equals_count_for_duplicated_mesh(self):
        # Slots 23/25 are byte-identical and repeat == count there (E-031).
        prefix = ModBodyPrefix.parse(fixtures.mod_body(count=182, repeat=182))
        self.assertEqual(prefix.repeat, prefix.count)

    def test_repeat_independent_of_count(self):
        # Slot 1: count=474 but body+0x5C reads 0x01418002 (E-031).
        prefix = ModBodyPrefix.parse(
            fixtures.mod_body(count=474, repeat=0x01418002)
        )
        self.assertEqual(prefix.count, 474)
        self.assertEqual(prefix.repeat, 0x01418002)

    def test_slot_1_shape(self):
        # pl021.pac slot 1: marker=0x8001, count=474, field_24=768.
        prefix = ModBodyPrefix.parse(
            fixtures.mod_body(count=474, field_24=768, repeat=0x01418002)
        )
        self.assertEqual(prefix.marker, 0x8001)
        self.assertEqual(prefix.count, 474)
        self.assertEqual(prefix.field_24, 768)

    def test_marker_constant(self):
        # 0x8001 observed in all four pl021.pac MOD chunks (E-031).
        for count in (474, 300, 182):
            self.assertEqual(
                ModBodyPrefix.parse(fixtures.mod_body(count=count)).marker,
                0x8001,
            )

    def test_prefix_size(self):
        self.assertEqual(BODY_PREFIX_SIZE, 0x60)

    def test_rejects_short_body(self):
        with self.assertRaises(ValueError):
            ModBodyPrefix.parse(fixtures.mod_body()[:BODY_PREFIX_SIZE - 1])
        self.assertIsNone(maybe_mod_body_prefix(b"\x00" * 10))


class TestModBodyTaggedCount(unittest.TestCase):
    """E-091: body +0x1C is one tagged u32 ``(count << 16) | tag``."""

    def test_tag_word_packs_tag_and_count(self):
        prefix = ModBodyPrefix.parse(fixtures.mod_body(tag=0x8001, count=474))
        self.assertEqual(prefix.tag_word, (474 << 16) | 0x8001)
        self.assertEqual(prefix.tag, 0x8001)
        self.assertEqual(prefix.marker, 0x8001)  # E-031 alias
        self.assertEqual(prefix.count, 474)

    def test_tag_offset_constant(self):
        self.assertEqual(BODY_TAG_OFFSET, 0x1C)
        self.assertEqual(BODY_TAG_NAMESPACE, 0x8000)
        self.assertEqual(BODY_TAG_MASK, 0xF000)

    def test_all_four_observed_tags_are_in_namespace(self):
        # 286/286 real MOD chunks carry a 0x8000-namespace tag (E-091):
        # 0x8001 x279, 0x8002 x4, 0x8201 x2, 0x8005 x1.
        for tag in (0x8001, 0x8002, 0x8201, 0x8005):
            prefix = ModBodyPrefix.parse(fixtures.mod_body(tag=tag, count=182))
            self.assertEqual(prefix.tag, tag)
            self.assertTrue(prefix.tag_in_namespace, hex(tag))

    def test_tag_outside_namespace_is_detected(self):
        prefix = ModBodyPrefix.parse(fixtures.mod_body(tag=0x0001, count=182))
        self.assertFalse(prefix.tag_in_namespace)


class TestModBodyDirectory(unittest.TestCase):
    """E-092: the body opens with a 0x40-byte descriptor array whose count is
    the body's own +0x24 field. Only observed structure is asserted."""

    def test_layout_constants(self):
        self.assertEqual(BODY_DESCRIPTOR_SIZE, 0x40)
        self.assertEqual(BODY_DESCRIPTOR_ARRAY_OFFSET, 0x24)
        self.assertEqual(BODY_DESCRIPTOR_TAG_OFFSET, 0x1C)
        self.assertEqual(BODY_DESCRIPTOR_VECTOR_OFFSET, 0x0C)
        self.assertEqual(BODY_DESCRIPTOR_AUX_OFFSET, 0x2C)
        self.assertEqual(BODY_DESCRIPTOR_SLACK, 0x10)

    def test_count_comes_from_array_size(self):
        body = fixtures.mod_directory_body(tagged=3)
        directory = ModBodyDirectory.parse(body)
        self.assertEqual(directory.count, 4)
        self.assertEqual(directory.array_size, 4 * 0x40)
        self.assertEqual(directory.slack, 0)

    def test_last_descriptor_is_the_untagged_footer(self):
        directory = ModBodyDirectory.parse(fixtures.mod_directory_body(tagged=3))
        self.assertEqual(len(directory.records), 3)
        self.assertTrue(all(d.tagged for d in directory.records))
        self.assertFalse(directory.footer.tagged)
        self.assertTrue(directory.header_ok)

    def test_tags_and_counts_round_trip(self):
        directory = ModBodyDirectory.parse(
            fixtures.mod_directory_body(
                tagged=2, tags=(0x8002, 0x8601), counts=(298, 7)
            )
        )
        self.assertEqual(directory.tags, (0x8002, 0x8601))
        self.assertEqual([d.count for d in directory.records], [298, 7])

    def test_descriptor_zero_matches_the_body_prefix_fields(self):
        # E-031/E-091's "prefix" fields are descriptor 0's own fields (E-092).
        body = fixtures.mod_directory_body(tagged=3, counts=(182, 0, 0))
        directory = ModBodyDirectory.parse(body)
        prefix = ModBodyPrefix.parse(body)
        self.assertEqual(directory.descriptors[0].tag_word, prefix.tag_word)
        self.assertEqual(directory.descriptors[0].data_offset, prefix.field_24)
        self.assertEqual(directory.descriptors[0].aux, prefix.field_2c)
        # The prefix's vector/repeat are descriptor 1's vector/tag_word.
        self.assertEqual(
            tuple(directory.descriptors[1].vector), tuple(prefix.vector)
        )
        self.assertEqual(directory.descriptors[1].tag_word, prefix.repeat)

    def test_data_offsets_are_aligned_and_increasing(self):
        directory = ModBodyDirectory.parse(fixtures.mod_directory_body(tagged=4))
        offsets = [d.data_offset for d in directory.records]
        self.assertTrue(all(o % 0x10 == 0 for o in offsets), offsets)
        self.assertEqual(offsets, sorted(set(offsets)), offsets)
        # array end == descriptor 0's data offset (array is followed by data)
        self.assertEqual(offsets[0], directory.array_size)

    def test_slack_remainder_is_tolerated(self):
        # 7/286 real chunks carry +0x10 in the array-size field (id430/id470).
        directory = ModBodyDirectory.parse(
            fixtures.mod_directory_body(tagged=4, slack=0x10)
        )
        self.assertEqual(directory.count, 5)
        self.assertEqual(directory.slack, 0x10)

    def test_descriptor_count_rejects_other_remainders(self):
        self.assertEqual(descriptor_count(0x80), 2)
        self.assertEqual(descriptor_count(0x90), 2 + 0)  # 0x10 slack, floor
        with self.assertRaises(ValueError):
            descriptor_count(0x85)
        with self.assertRaises(ValueError):
            descriptor_count(0)

    def test_rejects_short_body(self):
        with self.assertRaises(ValueError):
            ModBodyDirectory.parse(b"\x00" * 8)
        # array-size says 4 descriptors but the body is truncated
        truncated = fixtures.mod_directory_body(tagged=3)[:0x80]
        with self.assertRaises(ValueError):
            ModBodyDirectory.parse(truncated)
        self.assertIsNone(maybe_mod_body_directory(b"\x00" * 4))


class TestModBodyBlocks(unittest.TestCase):
    """E-093: each record descriptor's +0x24 names a consecutive data block that
    opens with a 0x2C-byte prefix of three offsets. Only observed structure is
    asserted."""

    def test_layout_constants(self):
        self.assertEqual(BODY_BLOCK_PREFIX_SIZE, 0x2C)
        self.assertEqual(BODY_BLOCK_OFFSET_A, 0x04)
        self.assertEqual(BODY_BLOCK_OFFSET_B, 0x0C)
        self.assertEqual(BODY_BLOCK_OFFSET_C, 0x1C)
        self.assertEqual(
            BODY_BLOCK_ZERO_OFFSETS, (0x00, 0x08, 0x10, 0x14, 0x18, 0x20, 0x24, 0x28)
        )

    def test_one_block_per_record(self):
        directory = ModBodyDirectory.parse(fixtures.mod_directory_body(tagged=3))
        self.assertEqual(len(directory.blocks), 3)

    def test_blocks_are_consecutive_and_run_to_the_body_end(self):
        body = fixtures.mod_directory_body(tagged=3)
        directory = ModBodyDirectory.parse(body)
        blocks = directory.blocks
        for current, following in zip(blocks, blocks[1:]):
            self.assertEqual(current.end, following.data_offset)
        self.assertEqual(blocks[-1].end, len(body))
        # the first block starts where the descriptor array ends (descriptor 0)
        self.assertEqual(blocks[0].data_offset, directory.array_size)

    def test_prefix_is_clear_and_offsets_ordered(self):
        directory = ModBodyDirectory.parse(fixtures.mod_directory_body(tagged=3))
        for block in directory.blocks:
            self.assertTrue(block.prefix_clear, block)
            self.assertTrue(block.ordered, block)
            self.assertTrue(block.in_block, block)

    def test_regions_are_the_three_payload_spans(self):
        directory = ModBodyDirectory.parse(fixtures.mod_directory_body(tagged=3))
        block = directory.blocks[0]
        self.assertEqual(block.payload_offset, block.data_offset + 0x2C)
        regions = block.regions
        self.assertEqual(len(regions), 3)
        self.assertEqual(regions[0][0], block.payload_offset)
        self.assertEqual(regions[0][1], block.offset_a)
        self.assertEqual(regions[1], (block.offset_a, block.offset_b))
        self.assertEqual(regions[2], (block.offset_b, block.end))
        # the regions are consecutive and cover the payload
        self.assertEqual(regions[2][1], block.end)

    def test_block_parse_rejects_short_input(self):
        with self.assertRaises(ValueError):
            ModBodyBlock.parse(b"\x00" * 0x10, 0, 0, 0x10)

    def test_body_blocks_skips_a_truncated_prefix(self):
        # descriptor says data starts at 0x100 but the body ends at 0x110
        body = fixtures.mod_directory_body(tagged=1)
        directory = ModBodyDirectory.parse(body)
        truncated = body[: directory.blocks[0].data_offset + 8]
        directory = ModBodyDirectory.parse(truncated)
        self.assertEqual(directory.blocks, ())


class TestModBodyVertices(unittest.TestCase):
    """E-094: a data block's payload opens with `count` f32[3] triples reading as
    positions, then `count` unit-length triples (normals). Position/normal
    *meaning* is [INFERRED]; only the byte reading is asserted."""

    def test_layout_constants(self):
        self.assertEqual(BODY_BLOCK_TUPLE_SIZE, 0x0C)
        self.assertEqual(BODY_BLOCK_NORMAL_MIN_RUN, 8)
        self.assertAlmostEqual(BODY_BLOCK_NORMAL_TOLERANCE, 2e-3)

    def test_positions_are_read_back(self):
        body = fixtures.mod_vertex_directory_body(count=5)
        block = ModBodyDirectory.parse(body).blocks[0]
        positions = block_positions(body, block, 5)
        self.assertEqual(len(positions), 5)
        self.assertEqual(positions[0], (0.5, -0.25, 0.0))
        self.assertEqual(positions[4], (4.5, -4.25, 0.5))

    def test_normals_follow_the_positions(self):
        body = fixtures.mod_vertex_directory_body(count=5)
        block = ModBodyDirectory.parse(body).blocks[0]
        normals = block_normals(body, block, 5)
        self.assertEqual(normals, ((0.0, 0.0, 1.0),) * 5)
        self.assertEqual(block.normal_offset(5), block.payload_offset + 5 * 12)

    def test_unit_triple_separates_normals_from_positions(self):
        body = fixtures.mod_vertex_directory_body(count=4)
        block = ModBodyDirectory.parse(body).blocks[0]
        for k in range(4):
            # positions are arbitrary, normals are unit length
            self.assertFalse(unit_triple(body, block.payload_offset + 12 * k))
            self.assertTrue(unit_triple(body, block.normal_offset(4) + 12 * k))
        # a zero triple and an arbitrary triple are not unit length
        self.assertFalse(unit_triple(b"\x00" * 12, 0))
        self.assertFalse(unit_triple(struct.pack("<3f", 9.0, 3.0, -2.0), 0))
        # a u32 0x400 run (E-093's fill) is not a normal triple
        self.assertFalse(unit_triple(struct.pack("<3I", 0x400, 0x400, 0x400), 0))
        self.assertFalse(unit_triple(b"\x00" * 12, 4))  # out of range

    def test_normal_run_locates_the_unit_array(self):
        body = fixtures.mod_vertex_directory_body(count=9)
        block = ModBodyDirectory.parse(body).blocks[0]
        # positions (0.5, ...) are not unit length, so the run starts at index 9
        start, length = normal_run(body, block)
        self.assertEqual((start, length), (9, 9))

    def test_normal_run_absent_without_unit_triples(self):
        body = fixtures.mod_vertex_directory_body(
            count=9, normals=[(9.0, 0.0, 0.0)] * 9
        )
        block = ModBodyDirectory.parse(body).blocks[0]
        self.assertIsNone(normal_run(body, block))

    def test_normal_run_needs_min_length(self):
        # a run of 7 unit triples is below the documented minimum of 8
        count = 7
        body = fixtures.mod_vertex_directory_body(count=count)
        block = ModBodyDirectory.parse(body).blocks[0]
        self.assertIsNone(normal_run(body, block))
        self.assertEqual(normal_run(body, block, min_run=count)[1], count)

    def test_triples_stop_at_the_body_end(self):
        body = fixtures.mod_vertex_directory_body(count=4)
        block = ModBodyDirectory.parse(body).blocks[0]
        # asking for more triples than the body holds yields only what fits
        self.assertLessEqual(len(block_positions(body, block, 10_000)), len(body) // 12)

    def test_regions_are_not_content_boundaries(self):
        # E-094 correction: the E-093 "three regions" split is pure arithmetic and
        # does not separate the vertex arrays.  In this fixture `offset_a` == the
        # end of the positions, so the first region already contains all of them.
        body = fixtures.mod_vertex_directory_body(count=9)
        block = ModBodyDirectory.parse(body).blocks[0]
        regions = block.regions
        self.assertEqual(regions[0][0], block.payload_offset)
        self.assertEqual(regions[0][1], block.offset_a)
        self.assertEqual(block.offset_a, block.payload_offset + 12 * 9)
        # the normal array starts exactly at offset_a here, but nothing in the
        # offsets tells the reader so -- normal_run finds it from the bytes.
        self.assertEqual(normal_run(body, block), (9, 9))


class TestModBodyAttributes(unittest.TestCase):
    """E-095: the four bytes per vertex after the normal array read as two u16s
    (an attribute array), not one u32.  The reading is asserted; the values'
    *meaning* is [INFERRED]/[UNKNOWN]."""

    def test_layout_constants(self):
        self.assertEqual(BODY_BLOCK_ATTRIBUTE_UNIT, 0x18)
        self.assertEqual(BODY_BLOCK_ATTRIBUTE_SIZE, 0x04)

    def test_attribute_offset_follows_the_normals(self):
        body = fixtures.mod_vertex_directory_body(count=5)
        block = ModBodyDirectory.parse(body).blocks[0]
        self.assertEqual(
            block.attribute_offset(5), block.payload_offset + 5 * 0x18
        )
        self.assertEqual(block.attribute_offset(5), block.normal_offset(5) + 5 * 12)

    def test_attributes_are_read_back_as_u16_pairs(self):
        body = fixtures.mod_vertex_directory_body(count=5)
        block = ModBodyDirectory.parse(body).blocks[0]
        attrs = block_attributes(body, block, 5)
        self.assertEqual(len(attrs), 5)
        self.assertEqual(attrs[0], (0x0100, 0x0200))
        self.assertEqual(attrs[4], (0x0104, 0x0204))

    def test_explicit_attribute_pairs_round_trip(self):
        pairs = [(0x0100 + k, 0x0200 + k) for k in range(8)]
        body = fixtures.mod_vertex_directory_body(count=8, attributes=pairs)
        block = ModBodyDirectory.parse(body).blocks[0]
        # the normal array is unchanged by the attributes
        self.assertEqual(normal_run(body, block), (8, 8))
        self.assertEqual(block_attributes(body, block, 8), tuple(pairs))

    def test_attributes_stop_at_the_body_end(self):
        body = fixtures.mod_vertex_directory_body(count=3)
        block = ModBodyDirectory.parse(body).blocks[0]
        # asking for more pairs than the body holds yields only what fits
        self.assertLessEqual(
            len(block_attributes(body, block, 10_000)), len(body) // 4
        )

    def test_u16_reading_differs_from_a_u32_reading(self):
        # the worked example's first four bytes are DE 06 F1 05 -- one u32
        # 0x05F106DE but the pair (0x06DE, 0x05F1); this locks the two-u16 view
        pairs = [(0x06DE, 0x05F1), (0x06DE, 0x0630), (0x0783, 0x0634)]
        body = fixtures.mod_vertex_directory_body(count=3, attributes=pairs)
        block = ModBodyDirectory.parse(body).blocks[0]
        self.assertEqual(block_attributes(body, block, 3), tuple(pairs))
        raw = body[block.attribute_offset(3):block.attribute_offset(3) + 4]
        self.assertEqual(raw, b"\xde\x06\xf1\x05")
        self.assertEqual(struct.unpack("<I", raw)[0], 0x05F106DE)


if __name__ == "__main__":
    unittest.main()
