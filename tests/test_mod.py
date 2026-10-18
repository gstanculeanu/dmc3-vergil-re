import _bootstrap  # noqa: F401  (adds ../tools to sys.path)
import struct
import unittest

import fixtures
from dmc3 import Chunk, ModBodyDirectory, ModBodyPrefix, ModHeader
from dmc3.mod import (
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
    descriptor_count,
    maybe_mod_body_directory,
    maybe_mod_body_prefix,
    maybe_mod_header,
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


if __name__ == "__main__":
    unittest.main()
