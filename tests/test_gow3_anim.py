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


SUB_CLIP_OFFSET = 0x40
SUB_CLIP_SIZE = 0x600
SUB_NESTED_REL = 0x40          # nested preamble offset inside the tag-0x10 block
SUB_TAG16_REL = 0x70           # tag-0x16 sub-block offset from the data section
SUB_TAG10_REL = 0x210          # tag-0x10 sub-block offset from the data section


def sub_block_preamble_bytes() -> bytes:
    """A padded preamble naming nine typed sub-blocks (E-066).

    Values are strictly increasing multiples of 16 whose first entry is the
    preamble's own length rounded up, as on the real clips (E-065).
    """
    disc = anim.CLIP_DATA_RECORD_DISCRIMINATOR
    lead = [(0x15, 0x08, 0x60), (0x16, 0x100, SUB_TAG16_REL),
            (0x18, 0x50, 0x180), (0x0B, 0x8039, 0x1A0)]
    tail = [(0x1B, 0x8039, 0x1B0, 0x0), (0x1D, 0x31, 0x1D0, 0xC0),
            (0x1E, 0x01, 0x1F0, 0x700), (0x0F, 0x05, 0x200, 0x0),
            (0x10, 0x33, SUB_TAG10_REL, 0xC0)]
    out = bytearray()
    for tag, arg, value in lead:
        out += struct.pack("<4H", tag, arg, disc, value)
    out += struct.pack("<3H", 0, 0, 41)
    for tag, arg, value, extra in tail:
        out += struct.pack("<5H", tag, arg, disc, value, extra)
    out += struct.pack("<H", 0)
    return bytes(out)


def sub_block_clip(name="subBlockClip") -> tuple:
    """A synthetic clip whose sub-blocks carry the E-066 shapes.

    The tag-0x16 sub-block opens with the 128-entry ``0x30 * k`` table and the
    tag-0x10 sub-block holds a nested preamble at ``+0x40``.
    """
    data = bytearray(SUB_CLIP_OFFSET + SUB_CLIP_SIZE)
    raw = name.encode("latin-1")
    data[SUB_CLIP_OFFSET:SUB_CLIP_OFFSET + len(raw)] = raw
    data_offset = SUB_CLIP_OFFSET + anim.CLIP_TAIL_END
    preamble = sub_block_preamble_bytes()
    data[data_offset:data_offset + len(preamble)] = preamble
    # tag-0x16: exactly the 128 u16 the real clips carry (span 0x1800)
    tag16 = data_offset + SUB_TAG16_REL
    for k in range(anim.CLIP_DATA_TAG16_PREFIX_WORDS):
        struct.pack_into("<H", data, tag16 + 2 * k, anim.CLIP_DATA_TAG16_STEP * k)
    # tag-0x10: a nested preamble of the E-064 shape at +0x40
    nested = clip_data_preamble_bytes(count=33)
    tag10 = data_offset + SUB_TAG10_REL
    data[tag10 + SUB_NESTED_REL:tag10 + SUB_NESTED_REL + len(nested)] = nested
    clip = anim.Clip(index=0, name=name, offset=SUB_CLIP_OFFSET,
                     span=SUB_CLIP_SIZE, size=SUB_CLIP_SIZE)
    return bytes(data), clip


class TestClipSubBlocks(unittest.TestCase):
    """E-066: the preamble names typed sub-blocks with two verified relations."""

    def setUp(self):
        self.data, self.clip = sub_block_clip()
        self.blocks = anim.parse_clip_sub_blocks(self.data, self.clip)
        self.preamble = anim.parse_clip_data_preamble(
            self.data, self.clip.offset + anim.CLIP_TAIL_END)

    def test_blocks_match_the_preamble_records(self):
        self.assertIsNotNone(self.blocks)
        self.assertEqual(self.blocks.tags, self.preamble.lead_tags
                         + self.preamble.tail_tags)
        self.assertEqual(tuple(b.offset for b in self.blocks.blocks),
                         self.preamble.data_targets(self.blocks.offset))
        self.assertEqual(anim.CLIP_DATA_TAG16, 0x16)
        self.assertEqual(anim.CLIP_DATA_TAG10, 0x10)

    def test_sizes_reach_the_next_target_and_the_clip_end(self):
        for first, second in zip(self.blocks.blocks, self.blocks.blocks[1:]):
            self.assertEqual(first.offset + first.size, second.offset)
        last = self.blocks.blocks[-1]
        self.assertEqual(last.offset + last.size, self.clip.end)

    def test_tag16_sub_block_opens_with_the_128_entry_table(self):
        self.assertEqual(anim.CLIP_DATA_TAG16_PREFIX_WORDS, 128)
        self.assertEqual(anim.CLIP_DATA_TAG16_STEP, 0x30)
        block = self.blocks.of_tag(anim.CLIP_DATA_TAG16)[0]
        self.assertEqual(block.tag16_prefix_length, 128)
        self.assertTrue(self.blocks.tag16_prefix_ok)
        # the table spans 0x30 * 128 == 0x1800
        self.assertEqual(anim.CLIP_DATA_TAG16_STEP
                         * anim.CLIP_DATA_TAG16_PREFIX_WORDS, 0x1800)

    def test_tag10_sub_block_holds_a_nested_preamble(self):
        self.assertEqual(anim.CLIP_DATA_NESTED_MIN_RECORDS, 3)
        found = self.blocks.nested_preamble()
        self.assertIsNotNone(found)
        offset, nested = found
        self.assertEqual(offset, SUB_NESTED_REL)
        self.assertEqual(nested.count, 33)
        self.assertTrue(self.blocks.nested_ok)
        self.assertEqual(anim.CLIP_DATA_TAG10, 0x10)

    def test_invariants_report_both_relations(self):
        self.assertEqual(self.blocks.invariants(),
                         {"tag16_prefix": True, "nested_preamble": True})

    def test_tag16_prefix_length_stops_at_a_deviation(self):
        table = b"".join(struct.pack("<H", 0x30 * k) for k in range(5))
        self.assertEqual(anim.tag16_prefix_length(table), 5)
        self.assertEqual(anim.tag16_prefix_length(table + struct.pack("<H", 1)), 5)

    def test_nested_search_skips_a_degenerate_zero_start(self):
        self.assertIsNone(anim.find_nested_preamble(b"\x00" * 64))
        self.assertIsNone(anim.find_nested_preamble(b""))
        # a real nested preamble is still found behind zero fill (the strict
        # parser needs a few bytes of lookahead past the terminator)
        nested = clip_data_preamble_bytes(count=41)
        payload = b"\x00" * 32 + nested + b"\x00" * 16
        found = anim.find_nested_preamble(payload)
        self.assertIsNotNone(found)
        self.assertEqual(found[0], 32)

    def test_a_broken_relation_is_reported_not_raised(self):
        blob = bytearray(self.data)
        tag16 = self.blocks.offset + SUB_TAG16_REL
        struct.pack_into("<H", blob, tag16 + 2, 0x1234)   # break the table
        tag10 = self.blocks.offset + SUB_TAG10_REL
        blob[tag10 + SUB_NESTED_REL:] = b"\x00" * (len(blob) - tag10 - SUB_NESTED_REL)
        blocks = anim.parse_clip_sub_blocks(bytes(blob), self.clip)
        self.assertFalse(blocks.tag16_prefix_ok)
        self.assertFalse(blocks.nested_ok)
        self.assertEqual(blocks.invariants(),
                         {"tag16_prefix": False, "nested_preamble": False})

    def test_no_preamble_returns_none(self):
        blob = b"\x00" * (SUB_CLIP_OFFSET + SUB_CLIP_SIZE)
        self.assertIsNone(anim.parse_clip_sub_blocks(blob, self.clip))

    def test_a_target_beyond_the_buffer_yields_an_empty_payload(self):
        data, _ = sub_block_clip()
        truncated = data[:SUB_CLIP_OFFSET + 0x200]
        blocks = anim.parse_clip_sub_blocks(truncated, self.clip)
        self.assertIsNotNone(blocks)
        last = blocks.blocks[-1]
        self.assertEqual(last.tag, anim.CLIP_DATA_TAG10)
        self.assertEqual(last.size, 0)
        self.assertEqual(last.payload, b"")


# E-067: two-level recursion. These offsets are relative to the synthetic clip.
NEST_OFFSET = 0x40             # clip offset (name field)
NEST_SIZE = 0x940              # clip byte size (>= every target)
NEST_TAG16_REL = 0x90          # outer tag-0x16 sub-block, from the data section
NEST_TAG10_REL = 0x2A0         # outer tag-0x10 sub-block, from the data section
NESTED_REL = 0x40              # nested preamble inside the outer tag-0x10 block
NEST_TAG16_WORDS = 123         # nested tag-0x16 table length (E-067)


def nested_preamble_bytes() -> bytes:
    """A nested preamble whose lead tags include 0x19 (E-067)."""
    disc = anim.CLIP_DATA_RECORD_DISCRIMINATOR
    lead = [(0x15, 0x10, 0x70), (0x16, 0xD8, 0x130), (0x18, 0x78, 0x280),
            (0x19, 0x08, 0x300), (0x0B, 0x8022, 0x310)]
    tail = [(0x1B, 0x8022, 0x320, 0x0), (0x1D, 0x04, 0x330, 0x0),
            (0x1E, 0x01, 0x340, 0x0), (0x0F, 0x05, 0x350, 0x0),
            (0x10, 0x33, 0x370, 0x0)]
    out = bytearray()
    for tag, arg, value in lead:
        out += struct.pack("<4H", tag, arg, disc, value)
    out += struct.pack("<3H", 0, 0, 117)
    for tag, arg, value, extra in tail:
        out += struct.pack("<5H", tag, arg, disc, value, extra)
    out += struct.pack("<H", 0)
    return bytes(out)


def outer_preamble_bytes() -> bytes:
    """An outer preamble naming the E-067 sub-block layout (values relative)."""
    disc = anim.CLIP_DATA_RECORD_DISCRIMINATOR
    lead = [(0x15, 0x08, 0x60), (0x16, 0x100, NEST_TAG16_REL),
            (0x18, 0x50, 0x200), (0x0B, 0x8039, 0x220)]
    tail = [(0x1B, 0x8039, 0x230, 0x0), (0x1D, 0x31, 0x250, 0xC0),
            (0x1E, 0x01, 0x270, 0x700), (0x0F, 0x05, 0x290, 0x0),
            (0x10, 0x33, NEST_TAG10_REL, 0xC0)]
    out = bytearray()
    for tag, arg, value in lead:
        out += struct.pack("<4H", tag, arg, disc, value)
    out += struct.pack("<3H", 0, 0, 41)
    for tag, arg, value, extra in tail:
        out += struct.pack("<5H", tag, arg, disc, value, extra)
    out += struct.pack("<H", 0)
    return bytes(out)


def nested_clip(name="nestedClip") -> tuple:
    """A clip whose data section recurses exactly two levels (E-067).

    The outer tag-0x10 sub-block holds a nested preamble that carries tag 0x19 and
    whose own tag-0x16 sub-block opens with a 123-entry ``0x30 * k`` table; the
    nested tag-0x10 sub-block holds no further preamble.
    """
    data = bytearray(NEST_OFFSET + NEST_SIZE)
    raw = name.encode("latin-1")
    data[NEST_OFFSET:NEST_OFFSET + len(raw)] = raw
    data_offset = NEST_OFFSET + anim.CLIP_TAIL_END

    outer = outer_preamble_bytes()
    data[data_offset:data_offset + len(outer)] = outer
    # outer tag-0x16: the 128-entry table, then a short second offset table
    outer16 = data_offset + NEST_TAG16_REL
    for k in range(anim.CLIP_DATA_TAG16_PREFIX_WORDS):
        struct.pack_into("<H", data, outer16 + 2 * k,
                         anim.CLIP_DATA_TAG16_STEP * k)
    for i, value in enumerate((0x20, 0x80, 0xB0, 0x140)):
        struct.pack_into("<H", data, outer16 + 2 * anim.CLIP_DATA_TAG16_PREFIX_WORDS + 2 * i,
                         value)
    # outer tag-0x10: a nested preamble at +NESTED_REL
    outer10 = data_offset + NEST_TAG10_REL
    nested = nested_preamble_bytes()
    data[outer10 + NESTED_REL:outer10 + NESTED_REL + len(nested)] = nested
    # nested tag-0x16: a shorter `0x30 * k` table (123 entries) then a second table
    n_data = outer10 + NESTED_REL
    nested16 = n_data + 0x130
    for k in range(NEST_TAG16_WORDS):
        struct.pack_into("<H", data, nested16 + 2 * k,
                         anim.CLIP_DATA_TAG16_STEP * k)
    for i, value in enumerate((0x20, 0x50, 0x80)):
        struct.pack_into("<H", data, nested16 + 2 * NEST_TAG16_WORDS + 2 * i, value)
    # nested tag-0x10 (at n_data+0x370) holds no preamble: fill with 0xCC
    nested10 = n_data + 0x370
    filler = (((NEST_OFFSET + NEST_SIZE) - nested10) + 1) // 2 * 2
    data[nested10:nested10 + filler] = b"\xcc" * filler
    clip = anim.Clip(index=0, name=name, offset=NEST_OFFSET,
                     span=NEST_SIZE, size=NEST_SIZE)
    return bytes(data), clip


class TestClipDataRecursion(unittest.TestCase):
    """E-067: the data section recurses exactly two levels."""

    def setUp(self):
        self.data, self.clip = nested_clip()
        self.sections = anim.clip_data_sections(self.data, self.clip)

    def test_two_sections_are_returned(self):
        self.assertEqual(len(self.sections), 2)
        outer, nested = self.sections
        self.assertEqual(outer.offset, self.clip.offset + anim.CLIP_TAIL_END)
        self.assertEqual(nested.offset, outer.offset + NEST_TAG10_REL + NESTED_REL)
        self.assertEqual(outer.end, self.clip.end)
        self.assertEqual(nested.end, self.clip.end)

    def test_nested_section_is_a_sub_block_of_the_outer(self):
        outer, nested = self.sections
        self.assertEqual(
            nested, outer.nested_data_section(self.data))
        self.assertTrue(outer.nested_ok)

    def test_nested_lead_carries_the_extra_tag_0x19(self):
        self.assertEqual(anim.CLIP_DATA_NESTED_LEAD_TAG, 0x19)
        _, nested = self.sections
        lead_tags = anim.parse_clip_data_preamble(
            self.data, nested.offset).lead_tags
        self.assertIn(anim.CLIP_DATA_NESTED_LEAD_TAG, lead_tags)
        self.assertNotIn(anim.CLIP_DATA_NESTED_LEAD_TAG, anim.CLIP_DATA_LEAD_TAGS)
        self.assertTrue(set(lead_tags) <= set(anim.CLIP_DATA_NESTED_LEAD_TAGS))

    def test_nested_tag16_table_is_123_words_not_128(self):
        _, nested = self.sections
        block = nested.of_tag(anim.CLIP_DATA_TAG16)[0]
        self.assertEqual(block.tag16_prefix_length, NEST_TAG16_WORDS)
        self.assertEqual(NEST_TAG16_WORDS, 123)
        self.assertNotEqual(NEST_TAG16_WORDS, anim.CLIP_DATA_TAG16_PREFIX_WORDS)
        # the outer level still opens with the full 128-entry table (E-066)
        outer, _ = self.sections
        self.assertTrue(outer.tag16_prefix_ok)

    def test_recursion_terminates_at_the_second_level(self):
        _, nested = self.sections
        self.assertIsNone(nested.nested_data_section(self.data))
        self.assertFalse(nested.nested_ok)

    def test_max_depth_caps_the_walk(self):
        self.assertEqual(len(anim.clip_data_sections(self.data, self.clip,
                                                     max_depth=1)), 1)

    def test_empty_when_the_clip_has_no_data_section(self):
        blob = b"\x00" * (NEST_OFFSET + NEST_SIZE)
        self.assertEqual(anim.clip_data_sections(blob, self.clip), ())

    def test_second_offset_table_follows_the_0x30k_table(self):
        outer, nested = self.sections
        block = outer.of_tag(anim.CLIP_DATA_TAG16)[0]
        self.assertEqual(block.tag16_offset_table, (0x20, 0x80, 0xB0, 0x140))
        self.assertEqual(anim.CLIP_DATA_SECOND_TABLE_FIRST, 0x20)
        nblock = nested.of_tag(anim.CLIP_DATA_TAG16)[0]
        self.assertEqual(nblock.tag16_offset_table, (0x20, 0x50, 0x80))

    def test_tag16_offset_table_stops_on_a_bad_value(self):
        table = b"".join(struct.pack("<H", 0x30 * k) for k in range(2))
        # 0x20, 0x30, then 0x31 (misaligned) stops the run
        tail = struct.pack("<3H", 0x20, 0x30, 0x31)
        self.assertEqual(anim.tag16_offset_table(table + tail), (0x20, 0x30))
        # a repeat / non-increase also stops it
        self.assertEqual(anim.tag16_offset_table(table + struct.pack("<2H", 0x20, 0x20)),
                         (0x20,))


if __name__ == "__main__":
    unittest.main()
