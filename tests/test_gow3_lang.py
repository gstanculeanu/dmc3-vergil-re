import _bootstrap  # noqa: F401
import struct
import unittest

from gow3 import lang


def table_bytes(entries) -> bytes:
    """Build a synthetic ``*id*``-delimited localisation table."""
    blob = bytearray()
    for eid, body in entries:
        blob += f"*{eid}*\r\n".encode("latin-1") + body.encode("latin-1")
    return bytes(blob)


class TestParseEntries(unittest.TestCase):
    def setUp(self):
        self.data = table_bytes([
            (20000, "0\r\nTRUE\r\nKratos\r\nheroImage00\r\n"),
            (832, "Hades\r\n"),
            (839, "Zeus\r\n"),
        ])
        self.entries = lang.parse_entries(self.data)

    def test_all_entries_found(self):
        self.assertEqual([e.entry_id for e in self.entries], [20000, 832, 839])

    def test_entry_bodies(self):
        # the body begins immediately after the closing '*', so it keeps the
        # newline that follows the marker (real data reads "\r\nHades\r\n")
        self.assertEqual(self.entries[1].text, "\r\nHades\r\n")
        self.assertEqual(self.entries[2].text, "\r\nZeus\r\n")

    def test_offsets_are_consistent(self):
        for entry in self.entries:
            self.assertEqual(self.data[entry.start:entry.start + 1], b"*")
            self.assertTrue(self.data[entry.start:entry.end].endswith(b"*"))
            self.assertEqual(entry.text_offset, entry.end)

    def test_bodies_are_contiguous(self):
        for first, second in zip(self.entries, self.entries[1:]):
            self.assertEqual(first.text_offset + len(first.text), second.start)

    def test_no_markers_means_no_entries(self):
        self.assertEqual(lang.parse_entries(b"no markers here"), [])


class TestSearch(unittest.TestCase):
    def setUp(self):
        self.entries = lang.parse_entries(table_bytes([
            (832, "Hades\r\n"),
            (900, "You have acquired the Claws of Hades.\r\n"),
            (839, "Zeus\r\n"),
        ]))

    def test_exact_line_finds_only_the_standalone_name(self):
        hits = lang.search(self.entries, "hades", exact_line=True)
        self.assertEqual([h.entry_id for h in hits], [832])

    def test_substring_finds_the_sentence_too(self):
        hits = lang.search(self.entries, "hades")
        self.assertEqual([h.entry_id for h in hits], [832, 900])

    def test_case_insensitive(self):
        self.assertEqual(len(lang.search(self.entries, "ZEUS")), 1)

    def test_no_match(self):
        self.assertEqual(lang.search(self.entries, "vergil"), [])


class TestReplaceExactLine(unittest.TestCase):
    def setUp(self):
        self.entries = lang.parse_entries(table_bytes([
            (832, "Hades\r\n"),
            (839, "Zeus\r\n"),
        ]))

    def test_equal_length_replacement_is_allowed_and_in_place(self):
        before = table_bytes([(832, "Hades\r\n"), (839, "Zeus\r\n")])
        out = lang.replace_exact_line(before, self.entries[0], "Hades", "Virgi")
        self.assertIsNotNone(out)
        self.assertEqual(len(out), len(before))          # no size change
        self.assertIn(b"*832*\r\nVirgi\r\n", out)        # replaced
        self.assertIn(b"*839*\r\nZeus\r\n", out)         # untouched

    def test_longer_replacement_is_refused(self):
        # "Hades" -> "Vergil" grows by one byte, so the container's stored sizes
        # would need updating; the tool must refuse rather than corrupt the file.
        before = table_bytes([(832, "Hades\r\n")])
        self.assertIsNone(
            lang.replace_exact_line(before, self.entries[0], "Hades", "Vergil")
        )

    def test_wrong_length_and_missing_line(self):
        before = table_bytes([(832, "Hades\r\n")])
        self.assertIsNone(lang.replace_exact_line(before, self.entries[0], "Nope", "X"))

    def test_real_boss_name_lengths_documented(self):
        # The observation that drove this: Hades is 5, Vergil is 6 -> needs a writer.
        self.assertEqual(len("Hades"), 5)
        self.assertEqual(len("Vergil"), 6)
        self.assertEqual(len("Helios"), len("Vergil"))   # a same-length swap exists


class TestBlobAndWriter(unittest.TestCase):
    """The named-blob descriptor and the length-changing writer (E-054)."""

    def setUp(self):
        body = b"*1*\r\nA\r\n*832*\r\nHades\r\n*833*\r\nHelios\r\n"
        blob = bytearray()
        blob += b"\x00" * 0xD80                      # header + directory + padding
        descriptor = bytearray(0x40)
        struct.pack_into("<I", descriptor, 0, 7)               # id
        struct.pack_into("<I", descriptor, 4, len(body))       # size
        descriptor[8:8 + len(b"MSGS_TXT")] = b"MSGS_TXT"
        blob += descriptor
        data_start = len(blob)                        # == 0xDC0
        blob += body
        self.data = bytes(blob)
        self.data_start = data_start

    def test_blob_found_with_correct_size_and_offset(self):
        blob = lang.find_blob(self.data, "MSGS_TXT")
        self.assertIsNotNone(blob)
        self.assertEqual(blob.size, len(self.data) - self.data_start)
        self.assertEqual(blob.data_offset, self.data_start)
        self.assertEqual(blob.end, len(self.data))

    def test_unknown_blob_is_none(self):
        self.assertIsNone(lang.find_blob(self.data, "NOPE_TXT"))

    def test_one_and_two_digit_ids_are_parsed(self):
        # regression: the marker regex used to demand 3+ digits, so *1* and *10*
        # were silently skipped and the first entry appeared to be *100*.
        ids = [e.entry_id for e in lang.parse_entries(self.data)]
        self.assertIn(1, ids)
        self.assertIn(832, ids)

    def test_length_changing_replace_updates_only_the_size_field(self):
        blob = lang.find_blob(self.data, "MSGS_TXT")
        out = lang.replace_exact_line_in_blob(self.data, blob, "Hades", "Vergil")
        self.assertIsNotNone(out)
        self.assertEqual(len(out), len(self.data) + 1)
        new_size = struct.unpack_from("<I", out, blob.size_offset)[0]
        self.assertEqual(new_size, blob.size + 1)
        entry = next(e for e in lang.parse_entries(out) if e.entry_id == 832)
        self.assertIn("Vergil", entry.text)
        self.assertNotIn("Hades", entry.text)

    def test_other_entries_are_untouched(self):
        blob = lang.find_blob(self.data, "MSGS_TXT")
        out = lang.replace_exact_line_in_blob(self.data, blob, "Hades", "Vergil")
        helios = next(e for e in lang.parse_entries(out) if e.entry_id == 833)
        self.assertIn("Helios", helios.text)

    def test_missing_line_returns_none(self):
        blob = lang.find_blob(self.data, "MSGS_TXT")
        self.assertIsNone(lang.replace_exact_line_in_blob(self.data, blob, "Nope", "X"))

    def test_entry_outside_the_blob_is_refused(self):
        blob = lang.find_blob(self.data, "MSGS_TXT")
        blob = lang.Blob(name=blob.name, descriptor_offset=blob.descriptor_offset,
                         size_offset=blob.size_offset, size=0, data_offset=0)
        self.assertIsNone(lang.replace_exact_line_in_blob(self.data, blob, "Hades", "Vergil"))


if __name__ == "__main__":
    unittest.main()
