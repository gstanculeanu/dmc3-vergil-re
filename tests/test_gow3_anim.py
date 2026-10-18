import _bootstrap  # noqa: F401
import struct
import unittest

from gow3 import anim
from gow3.anim import AnimError

# Real layout of R_HADES.WAD (E-058): the blob's data starts at 0xE40 and the clip
# table sits *inside* that region at 0xE78, so base < table.
BASE, TABLE, HEAD = 0xE40, 0xE78, 0xE00
LEAD = 0x100
CLIP_SIZE = 0x200  # size of each synthetic clip record (>= CLIP_HEADER_MIN)
FRAMES = 41


def clip_data_preamble_bytes(count=41, extra_lead=False) -> bytes:
    """A data-section preamble shaped like the real bytes (E-064)."""
    disc = anim.CLIP_DATA_RECORD_DISCRIMINATOR
    if extra_lead:
        lead = [(0x15, 0x38, 0x70), (0x16, 0xB8, 0x350), (0x17, 0x18, 0x8F0),
                (0x18, 0x40, 0xA50), (0x0B, 0x804E, 0xC40)]
    else:
        lead = [(0x15, 0x08, 0x60), (0x16, 0x100, 0x90),
                (0x18, 0x50, 0x870), (0x0B, 0x8039, 0xAF0)]
    out = bytearray()
    for tag, arg, value in lead:
        out += struct.pack("<4H", tag, arg, disc, value)
    out += struct.pack("<3H", 0, 0, count)
    tail = [(0x1B, 0x8039, 0xB30, 0x0), (0x1D, 0x31, 0xFB0, 0xC0),
            (0x1E, 0x01, 0x1140, 0x700), (0x0F, 0x05, 0x1150, 0x0),
            (0x10, 0x33, 0x1160, 0xC0)]
    for tag, arg, value, extra in tail:
        out += struct.pack("<5H", tag, arg, disc, value, extra)
    out += struct.pack("<H", 0)
    return bytes(out)


def anim_wad(names, lead=LEAD, table=TABLE, base=BASE, head=HEAD) -> bytes:
    blob = bytearray(head)
    payload = bytearray(lead)
    offsets = []
    for name in names:
        offsets.append(len(payload))
        record = bytearray(CLIP_SIZE)
        raw = name.encode("latin-1")
        record[0:len(raw)] = raw
        struct.pack_into("<I", record, anim.CLIP_SIZE_OFFSET, CLIP_SIZE)
        struct.pack_into("<I", record, anim.CLIP_FLAGS_OFFSET, 0)
        struct.pack_into("<f", record, anim.CLIP_FRAME_RATE_OFFSET, 1.0 / 30)
        for copy in anim.CLIP_SIZE_COPY_OFFSETS:
            struct.pack_into("<I", record, copy, CLIP_SIZE)
        for copy in anim.CLIP_RATE_COPY_OFFSETS:
            struct.pack_into("<f", record, copy, 1.0 / 30)
        struct.pack_into("<f", record, anim.CLIP_RATE_RECIPROCAL_OFFSET, 30.0)
        struct.pack_into("<f", record, anim.CLIP_SUB_FRAME_RATE_OFFSET, 1.0 / 60)
        # E-060: loop flag, frame count and 1/(frames-1) sample rate
        struct.pack_into("<H", record, anim.CLIP_LOOP_OFFSET, 1)
        struct.pack_into("<H", record, anim.CLIP_FRAME_COUNT_OFFSET, FRAMES)
        struct.pack_into("<f", record, anim.CLIP_SAMPLE_RATE_OFFSET,
                         anim.expected_sample_rate(FRAMES))
        # E-061: the per-clip descriptor tail and the data-section markers
        for field, value in anim.CLIP_TAIL_CONSTANTS:
            struct.pack_into("<I", record, field, value)
        for field in anim.CLIP_TAIL_SENTINEL_OFFSETS:
            struct.pack_into("<I", record, field, anim.CLIP_TAIL_SENTINEL)
        for field, value in zip(anim.CLIP_TAIL_ALIGNED_OFFSETS,
                                (0x12340, 0x1200, 0x34560, 0x1D10, 0x2000)):
            struct.pack_into("<I", record, field, value)
        struct.pack_into("<I", record, 0x140, 0x2A)       # unaligned, as observed
        struct.pack_into("<I", record, 0x148, 0x185)      # unaligned, as observed
        struct.pack_into("<H", record, anim.CLIP_TAIL_END, anim.CLIP_DATA_MARKER)
        struct.pack_into("<H", record, anim.CLIP_TAIL_END + 4,
                         anim.CLIP_DATA_SECOND_MARKER)
        # E-064: the data section's typed record preamble, whose first record's
        # tag and discriminator are exactly the two markers written above.
        preamble = clip_data_preamble_bytes()
        start = anim.CLIP_TAIL_END
        record[start:start + len(preamble)] = preamble
        payload += record
    blob += b"\x00" * (base - len(blob))
    blob += payload
    for i, value in enumerate(offsets):
        struct.pack_into("<I", blob, table + 4 * i, value)
    return bytes(blob)


class TestClipDirectory(unittest.TestCase):
    def setUp(self):
        self.names = ["csHadesIntro", "csHadesKnifeKill", "hadesKnifeAttLhigh"]
        self.data = anim_wad(self.names)

    def test_reads_increasing_offsets(self):
        offsets = anim.read_clip_offsets(self.data)
        self.assertEqual(len(offsets), 3)
        self.assertEqual(offsets, sorted(offsets))
        self.assertEqual(offsets[0], LEAD)

    def test_parses_named_clips(self):
        clips = anim.parse_clips(self.data)
        self.assertEqual([c.name for c in clips], self.names)
        self.assertEqual(clips[0].offset, BASE + LEAD)
        self.assertEqual(clips[0].index, 0)

    def test_spans_reach_the_next_clip(self):
        clips = anim.parse_clips(self.data)
        for first, second in zip(clips, clips[1:]):
            self.assertEqual(first.offset + first.span, second.offset)
        self.assertGreater(clips[-1].span, 0)

    def test_find_table_locates_a_validated_table(self):
        self.assertEqual(anim.find_table(self.data, min_entries=3), TABLE)

    def test_find_table_rejects_a_bare_increasing_run(self):
        blob = bytearray(HEAD)
        blob += b"\x00" * (TABLE - len(blob))
        for i in range(40):
            blob += struct.pack("<I", (i + 1) * 0x1000)
        blob += b"\x00" * 0x4000            # no clip names anywhere
        self.assertIsNone(anim.find_table(bytes(blob), min_entries=20))

    def test_missing_table_raises(self):
        with self.assertRaises(AnimError):
            anim.parse_clips(b"\x00" * 0x1000)

    def test_offsets_stop_at_a_non_increasing_value(self):
        blob = bytearray(TABLE)
        for value in (0x10, 0x20, 0x10, 0x40):
            blob += struct.pack("<I", value)
        self.assertEqual(anim.read_clip_offsets(bytes(blob)), [0x10, 0x20])

    def test_offsets_stop_at_an_absurd_value(self):
        blob = bytearray(TABLE)
        for value in (0x10, 0x20, 0xFFFFFFF0):
            blob += struct.pack("<I", value)
        self.assertEqual(anim.read_clip_offsets(bytes(blob)), [0x10, 0x20])

    def test_zero_terminates_the_table(self):
        # a real table ends with zeros, so a 0 entry must not be read as an offset
        blob = bytearray(TABLE)
        for value in (0x40, 0x80, 0):
            blob += struct.pack("<I", value)
        self.assertEqual(anim.read_clip_offsets(bytes(blob)), [0x40, 0x80])

    def test_names_must_be_at_least_three_characters(self):
        fits = anim_wad(["abc", "longerNameHere"])
        clips = anim.parse_clips(fits)
        self.assertEqual([c.name for c in clips], ["abc", "longerNameHere"])

    def test_unnamed_entries_are_skipped(self):
        data = anim_wad([])
        blob = bytearray(data)
        struct.pack_into("<I", blob, TABLE, LEAD)
        struct.pack_into("<I", blob, TABLE + 4, LEAD + 0x40)
        struct.pack_into("<I", blob, TABLE + 8, 0)
        # make the clip region non-text so nothing is recognised
        for i in range(BASE + LEAD, min(len(blob), BASE + LEAD + 0x80)):
            blob[i] = 0x00
        self.assertEqual(anim.parse_clips(bytes(blob)), [])


class TestClipHeader(unittest.TestCase):
    """E-059: the fixed per-clip header (name field, size, frame rates)."""

    def setUp(self):
        self.names = ["csHadesIntro", "hadesKnifeAttLhigh"]
        self.data = anim_wad(self.names)

    def test_parses_observed_header_fields(self):
        clips = anim.parse_clips(self.data)
        header = anim.parse_clip_header(self.data, clips[0].offset)
        self.assertIsNotNone(header)
        self.assertEqual(header.name, "csHadesIntro")
        self.assertEqual(header.size, CLIP_SIZE)
        self.assertEqual(header.flags, 0)
        self.assertAlmostEqual(header.frame_rate, 1.0 / 30, places=6)
        self.assertAlmostEqual(header.sub_frame_rate, 1.0 / 60, places=6)
        self.assertEqual(header.size_copies, (CLIP_SIZE,) * 3)

    def test_clip_offsets_land_on_a_fixed_name_field(self):
        # the name field is 0x38 bytes, so the size is at a constant offset
        clips = anim.parse_clips(self.data)
        for clip in clips:
            self.assertEqual(clip.size, CLIP_SIZE)

    def test_header_is_none_on_a_non_clip_region(self):
        self.assertIsNone(anim.parse_clip_header(self.data, TABLE))
        self.assertIsNone(anim.parse_clip_header(self.data, len(self.data) - 2))

    def test_clip_size_is_authoritative_over_the_directory_span(self):
        # a trailing region beyond the last clip makes its span an over-estimate;
        # the header size must win (E-058 correction).
        data = anim_wad(self.names) + b"\x00" * 0x1000
        last = anim.parse_clips(data)[-1]
        self.assertEqual(last.size, CLIP_SIZE)
        self.assertGreater(last.span, last.size)
        self.assertEqual(last.end, last.offset + CLIP_SIZE)


class TestClipHeaderRelations(unittest.TestCase):
    """E-060: the four-fold size/frame-rate repetition and the derived fields."""

    def setUp(self):
        self.data = anim_wad(["csHadesIntro", "hadesKnifeBlockEnter"])
        self.header = anim.parse_clip_header(
            self.data, anim.parse_clips(self.data)[0].offset)

    def test_size_is_repeated_at_four_offsets(self):
        self.assertEqual(anim.CLIP_SIZE_OFFSETS, (0x38, 0x7C, 0x90, 0xA4))
        self.assertEqual(self.header.size, CLIP_SIZE)
        self.assertTrue(self.header.size_repeat_ok)

    def test_frame_rate_is_repeated_at_four_offsets(self):
        self.assertEqual(anim.CLIP_FRAME_RATE_OFFSETS, (0x6C, 0x80, 0x94, 0x110))
        self.assertEqual(self.header.rate_copies, (anim.float32(1.0 / 30),) * 4)
        self.assertTrue(self.header.rate_repeat_ok)

    def test_rate_reciprocal_is_stored(self):
        self.assertEqual(self.header.frame_count_rate, 30.0)
        self.assertTrue(self.header.reciprocal_ok)

    def test_frame_count_and_sample_rate_relation(self):
        self.assertEqual(self.header.frames, FRAMES)
        self.assertEqual(self.header.sample_rate, anim.expected_sample_rate(FRAMES))
        self.assertEqual(anim.expected_sample_rate(FRAMES),
                         anim.float32(1.0 / (FRAMES - 1)))
        self.assertTrue(self.header.sample_rate_ok)

    def test_loop_flag_is_read(self):
        self.assertEqual(self.header.loop_flag, 1)

    def test_invariants_report_every_relation(self):
        self.assertEqual(self.header.invariants(),
                         {"size_repeat": True, "rate_repeat": True,
                          "rate_reciprocal": True, "sample_rate": True})

    def test_a_broken_relation_is_reported_not_raised(self):
        blob = bytearray(self.data)
        offset = anim.parse_clips(self.data)[0].offset
        struct.pack_into("<I", blob, offset + 0x90, CLIP_SIZE + 0x10)
        header = anim.parse_clip_header(bytes(blob), offset)
        self.assertFalse(header.size_repeat_ok)
        self.assertFalse(header.invariants()["size_repeat"])
        self.assertTrue(header.invariants()["rate_repeat"])

    def test_expected_sample_rate_is_undefined_below_two_frames(self):
        self.assertEqual(anim.expected_sample_rate(1), 0.0)
        self.assertEqual(anim.expected_sample_rate(0), 0.0)
        self.assertFalse(anim.ClipHeader(
            offset=0, name="x", size=1, flags=0, frame_rate=1.0 / 30,
            sub_frame_rate=1.0 / 60, size_copies=(1, 1, 1),
            frames=1, sample_rate=0.0).sample_rate_ok)

    def test_header_needs_the_full_block(self):
        # CLIP_HEADER_MIN must cover the last field the parser reads
        self.assertEqual(anim.CLIP_HEADER_MIN,
                         anim.CLIP_SAMPLE_RATE_OFFSET + 4)
        self.assertGreater(anim.CLIP_HEADER_MIN, anim.CLIP_FRAME_COUNT_OFFSET)

    def test_float32_rounds_like_the_format(self):
        self.assertEqual(anim.float32(1.0 / 30),
                         struct.unpack("<f", struct.pack("<f", 1.0 / 30))[0])
        self.assertNotEqual(anim.float32(1.0 / 30), 1.0 / 30)


class TestClipDescriptorTail(unittest.TestCase):
    """E-061: the per-clip tail at +0x124..+0x148 and the data-section markers."""

    def setUp(self):
        self.data = anim_wad(["csHadesIntro", "hadesKnifeBlockEnter"])
        self.offset = anim.parse_clips(self.data)[0].offset
        self.tail = anim.parse_clip_descriptor_tail(self.data, self.offset)

    def test_reads_the_seven_per_clip_fields(self):
        self.assertEqual(anim.CLIP_TAIL_VALUE_OFFSETS,
                         (0x124, 0x12C, 0x134, 0x13C, 0x140, 0x144, 0x148))
        self.assertEqual([field for field, _ in self.tail.fields],
                         list(anim.CLIP_TAIL_VALUE_OFFSETS))

    def test_five_fields_are_sixteen_byte_aligned(self):
        self.assertEqual(anim.CLIP_TAIL_ALIGNED_OFFSETS,
                         (0x124, 0x12C, 0x134, 0x13C, 0x144))
        self.assertTrue(self.tail.aligned_ok)
        self.assertEqual(len(self.tail.aligned_values), 5)
        for value in self.tail.aligned_values:
            self.assertEqual(value % 16, 0)

    def test_constants_match_evidence(self):
        self.assertEqual(anim.CLIP_TAIL_CONSTANTS,
                         ((0x128, 0x00800000), (0x130, 0x00010001),
                          (0x138, 0x037B0000)))
        self.assertTrue(self.tail.constants_ok)

    def test_sentinel_and_data_markers(self):
        self.assertTrue(self.tail.sentinel_ok)
        self.assertEqual(anim.CLIP_TAIL_SENTINEL, 0xFFFFFFFF)
        self.assertEqual(self.tail.data_marker, anim.CLIP_DATA_MARKER)
        self.assertEqual(self.tail.second_marker, anim.CLIP_DATA_SECOND_MARKER)
        self.assertTrue(self.tail.markers_ok)

    def test_tail_extends_the_header_to_the_data_section(self):
        self.assertEqual(anim.CLIP_TAIL_MIN, 0x15C)
        self.assertGreater(anim.CLIP_TAIL_MIN, anim.CLIP_HEADER_MIN)

    def test_invariants_report_every_relation(self):
        self.assertEqual(self.tail.invariants(),
                         {"aligned": True, "constants": True,
                          "sentinel": True, "markers": True})

    def test_a_broken_field_is_reported_not_raised(self):
        blob = bytearray(self.data)
        struct.pack_into("<I", blob, self.offset + 0x134, 0x12345)  # not aligned
        tail = anim.parse_clip_descriptor_tail(bytes(blob), self.offset)
        self.assertFalse(tail.aligned_ok)
        self.assertFalse(tail.invariants()["aligned"])
        self.assertTrue(tail.constants_ok)

    def test_broken_constants_and_sentinel_are_reported(self):
        blob = bytearray(self.data)
        struct.pack_into("<I", blob, self.offset + 0x130, 0)
        struct.pack_into("<I", blob, self.offset + 0x150, 0)
        tail = anim.parse_clip_descriptor_tail(bytes(blob), self.offset)
        self.assertFalse(tail.constants_ok)
        self.assertFalse(tail.sentinel_ok)

    def test_tail_is_none_when_the_clip_is_too_short(self):
        self.assertIsNone(anim.parse_clip_descriptor_tail(self.data[:0x100], 0))
        self.assertIsNone(anim.parse_clip_descriptor_tail(
            self.data, len(self.data) - 8))
        self.assertIsNone(anim.maybe_clip_descriptor_tail(b"\x00" * 8, 0))


class TestClipDataPreamble(unittest.TestCase):
    """E-064: the typed record preamble at the start of the data section."""

    def setUp(self):
        self.data = anim_wad(["csHadesIntro", "hadesKnifeBlockEnter"])
        self.offset = anim.parse_clips(self.data)[0].offset + anim.CLIP_TAIL_END
        self.preamble = anim.parse_clip_data_preamble(self.data, self.offset)

    def test_the_two_e061_markers_are_the_first_record_fields(self):
        # E-061's "marker pair" is the first record's tag and discriminator.
        self.assertEqual(self.preamble.lead[0].tag, anim.CLIP_DATA_MARKER)
        self.assertEqual(self.preamble.lead[0].discriminator,
                         anim.CLIP_DATA_SECOND_MARKER)
        self.assertEqual(anim.CLIP_DATA_RECORD_DISCRIMINATOR, 0x000C)

    def test_reads_four_lead_records_and_the_count(self):
        self.assertEqual(self.preamble.lead_tags, (0x15, 0x16, 0x18, 0x0B))
        self.assertEqual(self.preamble.count, FRAMES)
        self.assertEqual(len(self.preamble.lead), 4)

    def test_reads_five_tail_records_with_an_extra_word(self):
        self.assertEqual(self.preamble.tail_tags, (0x1B, 0x1D, 0x1E, 0x0F, 0x10))
        self.assertEqual(len(self.preamble.tail), 5)
        for record in self.preamble.lead:
            self.assertIsNone(record.extra)
        for record in self.preamble.tail:
            self.assertIsNotNone(record.extra)

    def test_every_record_carries_the_constant_discriminator(self):
        self.assertTrue(self.preamble.discriminated_ok)
        self.assertTrue(self.preamble.tags_known_ok)
        self.assertEqual(self.preamble.invariants(),
                         {"discriminated": True, "tags_known": True,
                          "increasing": True, "aligned": True,
                          "first_offset": True})
        for record in self.preamble.lead + self.preamble.tail:
            self.assertEqual(record.discriminator,
                             anim.CLIP_DATA_RECORD_DISCRIMINATOR)

    def test_lead_may_carry_a_fifth_record(self):
        data = anim_wad(["csHadesIntroStruggle"])
        offset = anim.parse_clips(data)[0].offset + anim.CLIP_TAIL_END
        # patch in the variant shape (a 0x17 record before the 0x0B one)
        blob = bytearray(data)
        preamble = clip_data_preamble_bytes(count=117, extra_lead=True)
        blob[offset:offset + len(preamble)] = preamble
        parsed = anim.parse_clip_data_preamble(bytes(blob), offset)
        self.assertEqual(len(parsed.lead), 5)
        self.assertIn(0x17, parsed.lead_tags)
        self.assertEqual(parsed.count, 117)

    def test_a_broken_discriminator_returns_none(self):
        blob = bytearray(self.data)
        struct.pack_into("<H", blob, self.offset + 4, 0x000D)  # was 0x000C
        self.assertIsNone(anim.parse_clip_data_preamble(bytes(blob), self.offset))

    def test_a_missing_terminator_returns_none(self):
        blob = bytearray(self.data)
        # overwrite the two-zero terminator (word 16, after four 4-word records)
        term = self.offset + 2 * (anim.CLIP_DATA_LEAD_WORDS * 4)
        struct.pack_into("<2H", blob, term, 0x1234, 0x5678)
        self.assertIsNone(anim.parse_clip_data_preamble(bytes(blob), self.offset))

    def test_short_or_absent_input_is_handled(self):
        self.assertIsNone(anim.parse_clip_data_preamble(b"\x00" * 4, 0))
        self.assertIsNone(anim.parse_clip_data_preamble(self.data, len(self.data) - 2))
        self.assertIsNone(anim.maybe_clip_data_preamble(b"\x00" * 4, 0))

    def test_unknown_tag_is_reported_not_raised(self):
        blob = bytearray(self.data)
        struct.pack_into("<H", blob, self.offset + 2 * 8, 0x55)  # third lead tag
        parsed = anim.parse_clip_data_preamble(bytes(blob), self.offset)
        self.assertIsNotNone(parsed)
        self.assertFalse(parsed.tags_known_ok)
        self.assertTrue(parsed.discriminated_ok)


class TestClipDataOffsets(unittest.TestCase):
    """E-065: each record's last u16 is an offset to a 16-byte-aligned sub-block."""

    def setUp(self):
        self.data = anim_wad(["csHadesIntro", "hadesKnifeBlockEnter"])
        self.clip = anim.parse_clips(self.data)[0]
        self.offset = self.clip.offset + anim.CLIP_TAIL_END
        self.preamble = anim.parse_clip_data_preamble(self.data, self.offset)

    def test_values_are_all_record_tails_in_file_order(self):
        self.assertEqual(self.preamble.values,
                         (0x60, 0x90, 0x870, 0xAF0,
                          0xB30, 0xFB0, 0x1140, 0x1150, 0x1160))
        self.assertEqual(self.preamble.values,
                         tuple(r.value for r in self.preamble.lead)
                         + tuple(r.value for r in self.preamble.tail))

    def test_byte_length_counts_every_word(self):
        # 4 lead * 4 + 2 terminator + 1 count + 5 tail * 5 + 1 terminator = 45 u16
        self.assertEqual(self.preamble.word_count, 45)
        self.assertEqual(self.preamble.byte_length, 90)
        self.assertEqual(anim.CLIP_DATA_ALIGNMENT, 0x10)

    def test_offsets_are_increasing_and_sixteen_byte_aligned(self):
        self.assertTrue(self.preamble.increasing_ok)
        self.assertTrue(self.preamble.aligned_ok)
        for value in self.preamble.values:
            self.assertEqual(value % anim.CLIP_DATA_ALIGNMENT, 0)

    def test_first_offset_is_the_rounded_up_preamble_length(self):
        # 90 bytes rounds up to 96 == 0x60, exactly the first record's offset
        self.assertTrue(self.preamble.first_offset_ok)
        self.assertEqual(self.preamble.values[0], 0x60)

    def test_data_targets_are_relative_to_the_data_section(self):
        targets = self.preamble.data_targets(self.offset)
        self.assertEqual(targets,
                         tuple(self.offset + v for v in self.preamble.values))
        # the first target lands immediately after the preamble, 16-byte aligned
        self.assertEqual(targets[0], self.offset + 0x60)
        self.assertEqual(targets[0], self.offset + 96)

    def test_a_non_increasing_offset_is_reported_not_raised(self):
        blob = bytearray(self.data)
        # overwrite the second record's offset (word 7) with a smaller one
        struct.pack_into("<H", blob, self.offset + 2 * 7, 0x20)
        parsed = anim.parse_clip_data_preamble(bytes(blob), self.offset)
        self.assertIsNotNone(parsed)
        self.assertFalse(parsed.increasing_ok)
        self.assertFalse(parsed.invariants()["increasing"])
        self.assertTrue(parsed.discriminated_ok)

    def test_a_misaligned_offset_is_reported_not_raised(self):
        blob = bytearray(self.data)
        struct.pack_into("<H", blob, self.offset + 2 * 7, 0x21)  # not a multiple of 16
        parsed = anim.parse_clip_data_preamble(bytes(blob), self.offset)
        self.assertIsNotNone(parsed)
        self.assertFalse(parsed.aligned_ok)


if __name__ == "__main__":
    unittest.main()
