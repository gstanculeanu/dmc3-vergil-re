import _bootstrap  # noqa: F401
import os
import shutil
import tempfile
import unittest

import fixtures_gow3 as fx
from gow3 import SaveDataError, list_slots, parse_param, read_slot
from gow3.savedata import PARAM_SIZE


class TestParseParam(unittest.TestCase):
    def test_fields(self):
        param = parse_param(fx.param_bytes())
        self.assertEqual(param.title, "God of War\u00ae III Remastered")
        self.assertEqual(param.location, "The Depths of Hades")
        self.assertIn("Difficulty: God (Normal)", param.details)

    def test_derived_fields(self):
        param = parse_param(fx.param_bytes())
        self.assertEqual(param.difficulty, "God (Normal)")
        self.assertEqual(param.play_time, "0:52:29")
        self.assertEqual(param.play_seconds, 52 * 60 + 29)

    def test_play_seconds_with_hours(self):
        param = parse_param(fx.param_bytes(play_time="1:19:39"))
        self.assertEqual(param.play_seconds, 1 * 3600 + 19 * 60 + 39)

    def test_detail_lines(self):
        param = parse_param(fx.param_bytes())
        self.assertEqual(
            param.detail_lines, ["Difficulty: God (Normal)", "Play time: 0:52:29"]
        )

    def test_utf8_title_roundtrip(self):
        param = parse_param(fx.param_bytes(title="God of War\u00ae III Remastered"))
        self.assertIn("\u00ae", param.title)

    def test_missing_fields_are_empty(self):
        param = parse_param(fx.param_bytes(location="", difficulty="", play_time=""))
        self.assertEqual(param.location, "")
        self.assertEqual(param.play_time, "")
        self.assertIsNone(param.play_seconds)

    def test_too_small_raises(self):
        with self.assertRaises(SaveDataError):
            parse_param(b"\x00" * 16)

    def test_field_layout_offsets(self):
        # 0x000 title, 0x080 location, 0x100 details
        blob = fx.param_bytes(location="Marker")
        self.assertEqual(len(blob), PARAM_SIZE)
        self.assertEqual(blob[0x080:0x086], b"Marker")
        self.assertTrue(blob[0x100:].startswith(b"Difficulty:"))


class TestSlots(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="gow3-saves-")
        fx.write_slot(self.root, "SD-261013182124", location="Tomb of Ares", play_time="0:14:44")
        fx.write_slot(self.root, "SD-261015185945", location="The Forge", play_time="1:19:39")
        fx.write_slot(self.root, "AUTOSAVE", location="Hephaestus", play_time="1:19:33")
        fx.write_slot(self.root, "USERDATA", location="Preferences", difficulty="", play_time="")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_list_slots_sorted_by_play_time(self):
        slots = list_slots(self.root)
        self.assertEqual(slots[0].name, "AUTOSAVE")
        self.assertEqual(
            [s.name for s in slots[1:]], ["SD-261013182124", "SD-261015185945", "USERDATA"]
        )

    def test_kind_classification(self):
        kinds = {s.name: s.kind for s in list_slots(self.root)}
        self.assertEqual(kinds["AUTOSAVE"], "auto")
        self.assertEqual(kinds["USERDATA"], "userdata")
        self.assertEqual(kinds["SD-261015185945"], "manual")

    def test_location_and_playtime(self):
        slot = read_slot(self.root, "SD-261015185945")
        self.assertEqual(slot.location, "The Forge")
        self.assertEqual(slot.play_time, "1:19:39")
        self.assertEqual(slot.play_seconds, 4779)

    def test_timestamp_from_slot_name(self):
        slot = read_slot(self.root, "SD-261013182124")
        self.assertEqual(slot.timestamp, "2026-10-13 18:21:24")

    def test_autosave_has_no_timestamp(self):
        self.assertIsNone(read_slot(self.root, "AUTOSAVE").timestamp)

    def test_thumbnail_and_payload_detected(self):
        slot = read_slot(self.root, "SD-261015185945")
        self.assertTrue(slot.has_thumbnail)
        self.assertEqual(slot.payload_bytes, 64)

    def test_as_dict_keys(self):
        slot = read_slot(self.root, "SD-261015185945")
        keys = set(slot.as_dict())
        self.assertEqual(
            keys,
            {
                "name", "kind", "location", "play_time", "difficulty",
                "timestamp", "payload_bytes", "thumbnail", "error",
            },
        )

    def test_missing_param_is_reported_not_fatal(self):
        os.remove(os.path.join(self.root, "AUTOSAVE.sce_sys", "param.bin"))
        slot = read_slot(self.root, "AUTOSAVE")
        self.assertIsNone(slot.param)
        self.assertIn("param.bin", slot.error)
        self.assertEqual(slot.location, "")

    def test_list_slots_rejects_missing_dir(self):
        with self.assertRaises(SaveDataError):
            list_slots(os.path.join(self.root, "nope"))


if __name__ == "__main__":
    unittest.main()
