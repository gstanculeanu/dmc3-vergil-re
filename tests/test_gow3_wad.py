import _bootstrap  # noqa: F401
import unittest

import fixtures
from gow3 import wad
from gow3.wad import WadError


class TestWadHeader(unittest.TestCase):
    def test_parses_banner_and_magics(self):
        header = wad.parse_header(fixtures.wad_bytes(banner="WAD_R_Hercules"))
        self.assertEqual(header.magic0, 20)
        self.assertEqual(header.magic1, 8)
        self.assertEqual(header.banner, "WAD_R_Hercules")
        self.assertTrue(header.looks_valid)

    def test_entity_and_ai_classification(self):
        self.assertTrue(wad.parse_header(fixtures.wad_bytes("WAD_R_Sword00")).is_entity_wad)
        self.assertTrue(
            wad.parse_header(fixtures.wad_bytes("WAD_Hds675AI1Hades")).is_ai_wad
        )
        self.assertFalse(
            wad.parse_header(fixtures.wad_bytes("WAD_R_Sword00")).is_ai_wad
        )

    def test_rejects_bad_magic(self):
        blob = bytearray(fixtures.wad_bytes())
        blob[0:4] = (99).to_bytes(4, "little")
        with self.assertRaises(WadError):
            wad.parse_header(bytes(blob))

    def test_rejects_short_file(self):
        with self.assertRaises(WadError):
            wad.parse_header(b"\x14\x00")


class TestDcMarkers(unittest.TestCase):
    def test_finds_six_markers(self):
        info = wad.inspect_bytes(fixtures.wad_bytes("WAD_R_Sword00"))
        self.assertEqual(len(info.dc_markers), 6)
        self.assertTrue(info.dc_count_ok)

    def test_prefix_matches_the_verified_bytes(self):
        info = wad.inspect_bytes(fixtures.wad_bytes("WAD_R_Sword00"))
        self.assertTrue(all(m.prefix_matches for m in info.dc_markers))

    def test_bad_prefix_is_reported_not_hidden(self):
        info = wad.inspect_bytes(
            fixtures.wad_bytes("WAD_R_Sword00", bad_dc_prefix=True)
        )
        self.assertEqual(len(info.dc_markers), 6)
        self.assertFalse(all(m.prefix_matches for m in info.dc_markers))

    def test_marker_names_carry_the_banner(self):
        info = wad.inspect_bytes(fixtures.wad_bytes("WAD_R_Hercules"))
        self.assertTrue(all(m.name == "DC_WAD_R_Hercules" for m in info.dc_markers))


class TestNameFamilies(unittest.TestCase):
    def test_classification(self):
        cases = {
            "hfsmEnemy1": "hfsm (AI state machine)",
            "tGOPool_12": "tGOPool_N",
            "tMemoryPool_7": "tMemoryPool_N",
            "ms::tMove": "ms::*",
            "attachment::tSys": "attachment::*",
            "goFireTrail": "go* (object/FX)",
            "tAnimSystem": "t*System",
            "WAD_R_Sword00": "WAD_* (banner)",
            "randomThing": "other",
        }
        for name, expected in cases.items():
            self.assertEqual(wad.classify_name(name), expected, name)

    def test_hfsm_detection(self):
        blob = fixtures.wad_bytes("WAD_Hds675AI1Hades", names=("hfsmEnemy1", "hfsmIO_Misc"))
        info = wad.inspect_bytes(blob)
        self.assertEqual(info.hfsm_names, ["hfsmEnemy1", "hfsmIO_Misc"])
        self.assertTrue(info.carries_ai)

    def test_entity_wad_carries_no_ai(self):
        info = wad.inspect_bytes(fixtures.wad_bytes("WAD_R_Hercules", names=("goFireTrail",)))
        self.assertEqual(info.hfsm_names, [])
        self.assertFalse(info.carries_ai)
        self.assertEqual(info.summary()["kind"], "entity")

    def test_summary_shape(self):
        info = wad.inspect_bytes(fixtures.wad_bytes("WAD_R_Sword00"))
        summary = info.summary()
        self.assertEqual(
            set(summary),
            {"path", "size", "banner", "kind", "dc_markers", "dc_prefixes_ok",
             "hfsm", "name_families"},
        )
        self.assertEqual(summary["banner"], "WAD_R_Sword00")

    def test_is_wad_probe(self):
        self.assertTrue(wad.is_wad(fixtures.wad_bytes()))
        self.assertFalse(wad.is_wad(b"not a wad at all"))


if __name__ == "__main__":
    unittest.main()
