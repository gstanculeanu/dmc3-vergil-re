import _bootstrap  # noqa: F401  (adds ../tools to sys.path)
import unittest

import fixtures
from dmc3 import PacArchive, build_pac
from pac_diff import diff_pac, report, main


def archive(chunks):
    return PacArchive.from_bytes(build_pac(list(chunks)), name="synthetic.pac")


class TestPacDiff(unittest.TestCase):
    """Slot-by-slot PAC diff (backlog T5 / issue #10). All fixtures synthetic."""

    def test_identical_archives_produce_no_diffs(self):
        chunks = [
            fixtures.plain_chunk(b"MOD ", b"\x01\x02\x03\x04"),
            None,
            fixtures.plain_chunk(b"SHW ", b"\xAA" * 8),
        ]
        self.assertEqual(diff_pac(archive(chunks), archive(chunks)), [])

    def test_modified_payload_in_one_slot(self):
        a = archive([fixtures.plain_chunk(b"MOD ", b"\x01\x02\x03\x04"), None])
        b = archive([fixtures.plain_chunk(b"MOD ", b"\x09\x09\x09\x09"), None])
        diffs = diff_pac(a, b)
        self.assertEqual(len(diffs), 1)
        d = diffs[0]
        self.assertEqual(d.index, 0)
        self.assertEqual(d.status, "modified")
        self.assertFalse(d.data_equal)
        self.assertEqual(d.tag_a, "MOD ")
        self.assertEqual(d.tag_b, "MOD ")

    def test_added_slot(self):
        a = archive([fixtures.plain_chunk(b"MOD ", b"\x01"), None])
        b = archive(
            [fixtures.plain_chunk(b"MOD ", b"\x01"), fixtures.plain_chunk(b"SHW ", b"\xAA")]
        )
        diffs = diff_pac(a, b)
        self.assertEqual(len(diffs), 1)
        d = diffs[0]
        self.assertEqual(d.index, 1)
        self.assertEqual(d.status, "added")
        self.assertEqual(d.kind_b, "shader")
        self.assertEqual(d.tag_b, "SHW ")

    def test_removed_slot(self):
        a = archive(
            [fixtures.plain_chunk(b"MOD ", b"\x01"), fixtures.plain_chunk(b"SHW ", b"\xAA")]
        )
        b = archive([fixtures.plain_chunk(b"MOD ", b"\x01"), None])
        diffs = diff_pac(a, b)
        self.assertEqual(len(diffs), 1)
        d = diffs[0]
        self.assertEqual(d.index, 1)
        self.assertEqual(d.status, "removed")
        self.assertEqual(d.kind_a, "shader")

    def test_different_tag_is_modified(self):
        a = archive([fixtures.plain_chunk(b"MOD ", b"\x01\x02\x03\x04")])
        b = archive([fixtures.plain_chunk(b"SHW ", b"\x01\x02\x03\x04")])
        diffs = diff_pac(a, b)
        self.assertEqual(len(diffs), 1)
        d = diffs[0]
        self.assertEqual(d.status, "modified")
        self.assertEqual(d.tag_a, "MOD ")
        self.assertEqual(d.tag_b, "SHW ")
        self.assertFalse(d.data_equal)  # the tag bytes themselves differ

    def test_different_entry_counts(self):
        a = archive([fixtures.plain_chunk(b"MOD ", b"\x01")])  # 1 entry
        b = archive(
            [
                fixtures.plain_chunk(b"MOD ", b"\x01"),
                None,
                fixtures.plain_chunk(b"SHW ", b"\xAA"),
            ]
        )  # 3 entries
        diffs = diff_pac(a, b)
        statuses = sorted((d.index, d.status) for d in diffs)
        self.assertIn((0, "modified"), statuses)  # table/layout differs per slot
        self.assertIn((2, "added"), statuses)

    def test_report_identical(self):
        chunks = [fixtures.plain_chunk(b"MOD ", b"\x01\x02"), None]
        out = report(diff_pac(archive(chunks), archive(chunks)), "a.pac", "b.pac", 2, 2)
        self.assertIn("slot-identical", out)

    def test_report_lists_diffs(self):
        a = archive([fixtures.plain_chunk(b"MOD ", b"\x01\x02"), None])
        b = archive([fixtures.plain_chunk(b"MOD ", b"\x09\x09"), None])
        out = report(diff_pac(a, b), "a.pac", "b.pac", 2, 2)
        self.assertIn("MODIFIED", out)
        self.assertIn("payload bytes differ", out)

    def test_cli_identical_exits_zero(self):
        import os
        import tempfile
        from contextlib import redirect_stdout
        from io import StringIO

        blob = build_pac([fixtures.plain_chunk(b"MOD ", b"\x01\x02"), None])
        with tempfile.TemporaryDirectory() as td:
            paths = []
            for name in ("a.pac", "b.pac"):
                path = os.path.join(td, name)
                with open(path, "wb") as handle:
                    handle.write(blob)
                paths.append(path)
            out = StringIO()
            with redirect_stdout(out):
                code = main(paths)
            self.assertEqual(code, 0)
            self.assertIn("slot-identical", out.getvalue())

    def test_cli_differing_exits_one(self):
        import os
        import tempfile
        from contextlib import redirect_stdout
        from io import StringIO

        with tempfile.TemporaryDirectory() as td:
            path_a = os.path.join(td, "a.pac")
            path_b = os.path.join(td, "b.pac")
            with open(path_a, "wb") as handle:
                handle.write(build_pac([fixtures.plain_chunk(b"MOD ", b"\x01\x02")]))
            with open(path_b, "wb") as handle:
                handle.write(build_pac([fixtures.plain_chunk(b"MOD ", b"\x09\x09")]))
            out = StringIO()
            with redirect_stdout(out):
                code = main([path_a, path_b])
            self.assertEqual(code, 1)
            self.assertIn("MODIFIED", out.getvalue())


if __name__ == "__main__":
    unittest.main()
