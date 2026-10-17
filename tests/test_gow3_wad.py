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

    def test_prefix_flag_is_reported_not_assumed(self):
        # E-022/E-023: the prefix is NOT constant in real files, so the tool must
        # report rather than assume it.
        good = wad.inspect_bytes(fixtures.wad_bytes("WAD_R_Sword00"))
        self.assertTrue(all(m.prefix_matches for m in good.dc_markers))
        bad = wad.inspect_bytes(fixtures.wad_bytes("WAD_R_Sword00", bad_dc_prefix=True))
        self.assertFalse(all(m.prefix_matches for m in bad.dc_markers))

    def test_marker_names_carry_the_banner(self):
        info = wad.inspect_bytes(fixtures.wad_bytes("WAD_R_Hercules"))
        self.assertTrue(all(m.name == "DC_WAD_R_Hercules" for m in info.dc_markers))


class TestClassTable(unittest.TestCase):
    def test_known_ids(self):
        expected = {1: "CXT", 3: "ANMX", 4: "SCRX", 6: "LGTX", 7: "TXRX",
                    8: "MATX", 9: "CAMX", 13: "MDLX", 14: "COLX", 15: "PRTX",
                    16: "WPTX", 18: "BHVX", 19: "SNDX", 20: "root", 21: "FX",
                    24: "OCCX"}
        self.assertEqual(wad.CLASS_NAMES, expected)

    def test_standard_resource_set(self):
        self.assertIn("MDLX", wad.STANDARD_RESOURCE_SET)
        self.assertIn("ANMX", wad.STANDARD_RESOURCE_SET)
        self.assertIn("BHVX", wad.STANDARD_RESOURCE_SET)
        self.assertIn("TXRX", wad.STANDARD_RESOURCE_SET)
        self.assertEqual(len(wad.STANDARD_RESOURCE_SET), 16)


class TestRecordScan(unittest.TestCase):
    def setUp(self):
        self.data = fixtures.wad_records_bytes()
        self.records = wad.scan_records(self.data)

    def test_commands_are_found(self):
        commands = [r.command for r in self.records if r.kind == "command"]
        self.assertIn("GroupStart", commands)
        self.assertIn("GroupEnd", commands)
        self.assertIn("resource", commands)
        self.assertIn("PopHeap", commands)

    def test_root_record_is_the_banner(self):
        roots = [r for r in self.records if r.command == "root"]
        self.assertEqual(len(roots), 1)
        self.assertEqual(roots[0].name, "WAD_R_Sword00")

    def test_markers_carry_a_class_id(self):
        markers = [r for r in self.records if r.kind == "marker"]
        ids = sorted(m.class_id for m in markers if m.class_id)
        self.assertEqual(ids, [7, 13, 18, 20])

    def test_resources_resolve_by_name_prefix(self):
        res = wad.resources(self.records)
        names = {r.class_name: r.name for r in res}
        self.assertIn("MDLX", names)
        self.assertIn("BHVX", names)
        self.assertTrue(names["MDLX"].startswith("MDLX_"))

    def test_resolution_prefers_prefix_over_marker(self):
        # a deliberately lying marker must not override a good prefix
        data = fixtures.wad_records_bytes(
            resource_classes=(("MDLX", 7),)   # TXRX id on an MDLX resource
        )
        recs = wad.scan_records(data)
        res = wad.resources(recs)
        mdls = [r for r in res if r.name.startswith("MDLX_")]
        self.assertEqual(len(mdls), 1)
        self.assertEqual(mdls[0].class_name, "MDLX")

    def test_resource_histogram(self):
        histogram = wad.resource_histogram(self.records)
        self.assertEqual(histogram.get("MDLX"), 1)
        self.assertEqual(histogram.get("BHVX"), 1)

    def test_scan_terminates_on_garbage(self):
        records = wad.scan_records(b"\x00" * 4096)
        self.assertEqual(records, [])

    def test_scan_is_bounded_by_max_unknown_run(self):
        data = fixtures.wad_records_bytes() + b"\x00\x01\x02\x03" * 4096
        records = wad.scan_records(data, max_unknown_run=4)
        self.assertTrue(all(r.offset < len(fixtures.wad_records_bytes()) + 0x100
                            for r in records))


class TestDirectoryAndData(unittest.TestCase):
    def test_parse_directory_is_exact(self):
        data = fixtures.wad_records_bytes()
        records = wad.parse_directory(data)
        self.assertTrue(records)
        self.assertEqual(records[-1].command, "root")
        # directory ends where the data region would start
        end = records[-1].offset + wad.NAMED_RECORD_SIZE
        self.assertEqual(end, len(data))

    def test_marker_size_follows_the_resource_size(self):
        records = wad.parse_directory(fixtures.wad_records_bytes())
        markers = [r for r in records if r.kind == "marker"]
        by_id = {m.class_id: m.size for m in markers}
        # WAD/root declares 0x18 -> marker 0x20; others declare 0x10 -> marker 0x10
        self.assertEqual(by_id[20], 0x20)
        self.assertEqual(by_id[13], 0x10)
        self.assertEqual(by_id[7], 0x10)

    def test_data_chunks_are_found_with_sizes(self):
        data = fixtures.wad_with_data_chunks(sizes=(4, 0x40, 8, 4, 0x30, 0x20))
        chunks = wad.data_chunks(data)
        self.assertEqual(len(chunks), 6)
        self.assertEqual([c.chunk_id for c in chunks], [0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10])
        self.assertEqual([c.size for c in chunks], [4, 0x40, 8, 4, 0x30, 0x20])
        self.assertEqual(chunks[1].marker, 0x0009)

    def test_data_chunk_payload_round_trips(self):
        data = fixtures.wad_with_data_chunks(sizes=(4, 0x40, 8, 4, 0x30, 0x20))
        chunk = wad.data_chunks(data)[1]
        payload = chunk.payload(data)
        self.assertEqual(len(payload), 0x40)
        self.assertEqual(payload, bytes((2,)) * 0x40)

    def test_data_chunk_end_is_inside_the_file(self):
        data = fixtures.wad_with_data_chunks()
        for chunk in wad.data_chunks(data):
            self.assertLessEqual(chunk.end, len(data))

    def test_no_chunks_when_absent(self):
        self.assertEqual(wad.data_chunks(fixtures.wad_records_bytes()), [])


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

    def test_hfsm_detection_and_entity_wad(self):
        ai = wad.inspect_bytes(
            fixtures.wad_bytes("WAD_Hds675AI1Hades", names=("hfsmEnemy1", "hfsmIO_Misc"))
        )
        self.assertEqual(ai.hfsm_names, ["hfsmEnemy1", "hfsmIO_Misc"])
        self.assertTrue(ai.carries_ai)
        entity = wad.inspect_bytes(fixtures.wad_bytes("WAD_R_Hercules", names=("goFire",)))
        self.assertFalse(entity.carries_ai)
        self.assertEqual(entity.summary()["kind"], "entity")

    def test_summary_shape(self):
        info = wad.inspect_bytes(fixtures.wad_bytes("WAD_R_Sword00"))
        self.assertEqual(
            set(info.summary()),
            {"path", "size", "banner", "kind", "dc_markers", "dc_prefixes_ok",
             "hfsm", "name_families"},
        )

    def test_is_wad_probe(self):
        self.assertTrue(wad.is_wad(fixtures.wad_bytes()))
        self.assertFalse(wad.is_wad(b"not a wad at all"))


if __name__ == "__main__":
    unittest.main()
