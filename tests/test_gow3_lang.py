import _bootstrap  # noqa: F401
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


if __name__ == "__main__":
    unittest.main()
