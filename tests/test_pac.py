import _bootstrap  # noqa: F401  (adds ../tools to sys.path)
import unittest

import fixtures
from dmc3 import PacArchive, align_up, build_pac
from dmc3.pac import TAG_MODEL, TAG_MOTION


class TestPacContainer(unittest.TestCase):
    def setUp(self):
        payloads = [
            fixtures.plain_chunk(b"MOD ", b"\x01\x02\x03\x04"),
            None,  # empty slot
            fixtures.motion_chunk(),
            fixtures.cloth_text(),
        ]
        self.archive = PacArchive.from_bytes(build_pac(payloads), name="synthetic.pac")

    def test_entry_table(self):
        self.assertEqual(len(self.archive), 4)
        self.assertEqual(self.archive.entries[1], 0)
        self.assertEqual(self.archive.empty_slots, [1])

    def test_data_begins_after_aligned_table(self):
        self.assertEqual(self.archive.table_end, 0x08 + 4 * 4)
        self.assertEqual(self.archive.data_offset, align_up(self.archive.table_end))
        self.assertEqual(self.archive.entries[0], self.archive.data_offset)

    def test_empty_slot_has_no_chunk(self):
        self.assertIsNone(self.archive.chunk(1))

    def test_kinds_are_classified(self):
        self.assertEqual(
            [c.kind for c in self.archive.chunks()], ["model", "motion", "text"]
        )

    def test_plain_tag_offset(self):
        model = self.archive.chunk(0)
        self.assertEqual(model.tag_offset, 0)
        self.assertEqual(model.tag, TAG_MODEL)
        self.assertEqual(model.tag_text, "MOD ")

    def test_size_prefixed_tag_offset(self):
        motion = self.archive.chunk(2)
        self.assertEqual(motion.tag_offset, 4)
        self.assertEqual(motion.tag, TAG_MOTION)
        self.assertEqual(motion.tag_text, "MOT")

    def test_spans_are_contiguous(self):
        chunks = list(self.archive.chunks())
        for first, second in zip(chunks, chunks[1:]):
            self.assertEqual(first.offset + first.span, second.offset)

    def test_summary(self):
        summary = self.archive.summary()
        self.assertEqual(summary["entries"], 4)
        self.assertEqual(summary["occupied"], 3)
        self.assertEqual(summary["kinds"], {"model": 1, "motion": 1, "text": 1})

    def test_round_trip_preserves_payload_bytes(self):
        original = [fixtures.plain_chunk(b"SHW ", b"\xAA" * 20), None, b"MOD " + b"\xBB" * 12]
        rebuilt = build_pac(original)
        archive = PacArchive.from_bytes(rebuilt)
        self.assertEqual(archive.chunk(0).data[:4], b"SHW ")
        self.assertTrue(archive.chunk(0).data.startswith(original[0]))
        self.assertEqual(archive.chunk(2).data[:4], b"MOD ")


class TestPacRejectsBadInput(unittest.TestCase):
    def test_bad_magic(self):
        with self.assertRaises(ValueError):
            PacArchive.from_bytes(b"nope" + b"\x00" * 32)

    def test_truncated_table(self):
        blob = b"PAC\x00" + (16).to_bytes(4, "little")
        with self.assertRaises(ValueError):
            PacArchive.from_bytes(blob)

    def test_alignment_helper(self):
        self.assertEqual(align_up(0x74), 0x80)
        self.assertEqual(align_up(0x80), 0x80)
        self.assertEqual(align_up(0x81), 0x90)


if __name__ == "__main__":
    unittest.main()
