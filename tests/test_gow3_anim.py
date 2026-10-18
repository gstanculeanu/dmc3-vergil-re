import _bootstrap  # noqa: F401
import struct
import unittest

from gow3 import anim
from gow3.anim import AnimError

# Real layout of R_HADES.WAD (E-058): the blob's data starts at 0xE40 and the clip
# table sits *inside* that region at 0xE78, so base < table.
BASE, TABLE, HEAD = 0xE40, 0xE78, 0xE00
LEAD = 0x100


def anim_wad(names, lead=LEAD, table=TABLE, base=BASE, head=HEAD) -> bytes:
    blob = bytearray(head)
    payload = bytearray(lead)
    offsets = []
    for name in names:
        offsets.append(len(payload))
        payload += name.encode("latin-1") + b"\x00" * 24
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


if __name__ == "__main__":
    unittest.main()
