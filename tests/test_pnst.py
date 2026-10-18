import _bootstrap  # noqa: F401  (adds ../tools to sys.path)
import struct
import unittest

import fixtures
from dmc3 import PnstArchive, align_up
from dmc3.pnst import (
    MAGIC,
    PnstRawBlock,
    TAG_CONTAINER,
    TAG_MODEL,
    TAG_PNST,
    TAG_SHADER,
    maybe_pnst_raw_block,
    parse_pnst_raw_block,
)


class TestPnstContainer(unittest.TestCase):
    def setUp(self):
        self.archive = PnstArchive.from_bytes(
            fixtures.pnst_archive(), name="synthetic.pnst"
        )

    def test_magic_and_entry_count(self):
        self.assertEqual(len(self.archive), 5)
        self.assertEqual(self.archive.entry_count, 5)

    def test_data_begins_after_aligned_table(self):
        self.assertEqual(self.archive.table_end, 0x08 + 4 * 5)
        self.assertEqual(self.archive.data_offset, align_up(self.archive.table_end))
        # Like PAC, the first occupied offset equals the aligned data start.
        self.assertEqual(self.archive.entries[0], self.archive.data_offset)

    def test_empty_slot_has_no_chunk(self):
        self.assertEqual(self.archive.empty_slots, [2])
        self.assertIsNone(self.archive.chunk(2))

    def test_kinds_are_classified(self):
        self.assertEqual(
            [c.kind for c in self.archive.chunks()], ["model", "shader", "text", "raw"]
        )

    def test_tags(self):
        model = self.archive.chunk(0)
        self.assertEqual(model.tag_offset, 0)
        self.assertEqual(model.tag, TAG_MODEL)
        self.assertEqual(model.tag_text, "MOD ")
        shader = self.archive.chunk(1)
        self.assertEqual(shader.tag, TAG_SHADER)
        raw = self.archive.chunk(4)
        self.assertEqual(raw.tag, b"")
        self.assertEqual(raw.kind, "raw")

    def test_text_chunk_is_detected_without_a_tag(self):
        text = self.archive.chunk(3)
        self.assertEqual(text.tag, b"")
        self.assertEqual(text.kind, "text")
        self.assertEqual(text.trimmed[:10], b";wp005.clt")

    def test_spans_are_contiguous(self):
        chunks = list(self.archive.chunks())
        for first, second in zip(chunks, chunks[1:]):
            self.assertEqual(first.offset + first.span, second.offset)

    def test_summary(self):
        summary = self.archive.summary()
        self.assertEqual(summary["entries"], 5)
        self.assertEqual(summary["occupied"], 4)
        self.assertEqual(summary["empty"], 1)
        self.assertEqual(
            summary["kinds"], {"model": 1, "shader": 1, "text": 1, "raw": 1}
        )

    def test_observed_header_layout_from_both_archives(self):
        # Offsets observed verbatim from the two real weapon archives (E-006).
        # plwp_vergilsword.pac (count=9):
        offsets = [
            0x0030, 0x9030, 0xAC00, 0xB3A0, 0x143A0, 0x16370,
            0x164D0, 0x177B0, 0x88600,
        ]
        blob = bytearray(b"PNST")
        blob += struct.pack("<I", len(offsets))
        for off in offsets:
            blob += struct.pack("<I", off)
        blob += b"\x00" * ((-len(blob)) & 15)
        blob += b"\x00" * 16  # payload at the first offset
        archive = PnstArchive.from_bytes(bytes(blob), name="observed-layout.pnst")
        self.assertEqual(archive.entries, offsets)
        self.assertEqual(archive.table_end, 0x08 + 4 * len(offsets))
        self.assertEqual(archive.data_offset, align_up(archive.table_end))
        self.assertEqual(archive.entries[0], archive.data_offset)

    def test_overlay_adds_a_tenth_slot(self):
        # plwp_newvergilsword.pac (count=10) adds 0x88F20 as its last entry.
        offsets = [
            0x0030, 0x9030, 0xAC00, 0xB3A0, 0x143A0, 0x16370,
            0x164D0, 0x177B0, 0x88600, 0x88F20,
        ]
        blob = bytearray(b"PNST")
        blob += struct.pack("<I", len(offsets))
        for off in offsets:
            blob += struct.pack("<I", off)
        blob += b"\x00" * ((-len(blob)) & 15)
        blob += b"\x00" * 16
        archive = PnstArchive.from_bytes(bytes(blob), name="overlay-layout.pnst")
        self.assertEqual(len(archive), 10)
        self.assertEqual(archive.entries[-1], 0x88F20)
        self.assertFalse(archive.empty_slots)


class TestPnstRawBlock(unittest.TestCase):
    def test_header_matches_observed_values(self):
        # Slots 0 and 3 of both weapon archives share the header u32s (1, 17)
        # (evidence E-048).
        block = fixtures.pnst_raw_block()
        parsed = parse_pnst_raw_block(block)
        self.assertEqual(PnstRawBlock.HEADER_SIZE, 8)
        self.assertEqual(len(block), 8)
        self.assertEqual(parsed.field_a, 1)
        self.assertEqual(parsed.field_b, 17)

    def test_header_fields_are_read_verbatim(self):
        block = fixtures.pnst_raw_block(field_a=7, field_b=42, tail=b"\x00" * 8)
        parsed = parse_pnst_raw_block(block)
        self.assertEqual(parsed.field_a, 7)
        self.assertEqual(parsed.field_b, 42)

    def test_parse_rejects_short_data(self):
        with self.assertRaises(ValueError):
            parse_pnst_raw_block(b"\x01\x00\x00\x00")  # only 4 bytes

    def test_maybe_returns_none_for_short_data(self):
        self.assertIsNone(maybe_pnst_raw_block(b"\x01\x00\x00\x00"))

    def test_maybe_parses_header(self):
        block = fixtures.pnst_raw_block(field_a=1, field_b=17)
        self.assertIsInstance(maybe_pnst_raw_block(block), PnstRawBlock)
        self.assertEqual(maybe_pnst_raw_block(block).field_b, 17)


class TestPnstChunkTagging(unittest.TestCase):
    def test_pac_and_pnst_nested_tags(self):
        nested = fixtures.plain_chunk(b"PAC\x00") + b"\x00" * 12
        # offset[0] == 0x20 must point exactly at where ``nested`` begins.
        blob = (
            b"PNST"
            + struct.pack("<I", 1)
            + struct.pack("<I", 0x20)
            + b"\x00" * (0x20 - 12)
            + nested
        )
        archive = PnstArchive.from_bytes(blob, name="nested.pnst")
        chunk = archive.chunk(0)
        self.assertEqual(chunk.tag, TAG_CONTAINER)
        self.assertEqual(chunk.kind, "container")

    def test_nested_pnst_tag(self):
        blob = (
            b"PNST"
            + struct.pack("<I", 1)
            + struct.pack("<I", 0x20)
            + b"\x00" * (0x20 - 12)
            + b"PNST"
            + b"\x00" * 12
        )
        archive = PnstArchive.from_bytes(blob, name="nested-pnst.pnst")
        chunk = archive.chunk(0)
        self.assertEqual(chunk.tag, TAG_PNST)
        self.assertEqual(chunk.kind, "nested")


class TestPnstRejectsBadInput(unittest.TestCase):
    def test_bad_magic(self):
        with self.assertRaises(ValueError):
            PnstArchive.from_bytes(b"nope" + b"\x00" * 32)

    def test_truncated_table(self):
        blob = b"PNST" + (10).to_bytes(4, "little")  # claims 10 entries, no table
        with self.assertRaises(ValueError):
            PnstArchive.from_bytes(blob)

    def test_chunk_past_end_of_file(self):
        archive = PnstArchive.from_bytes(
            b"PNST" + struct.pack("<I", 1) + struct.pack("<I", 0x30)
        )
        with self.assertRaises(ValueError):
            archive.chunk(0)


if __name__ == "__main__":
    unittest.main()
