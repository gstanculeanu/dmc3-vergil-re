import _bootstrap  # noqa: F401
import struct
import unittest

from gow3 import groups
from gow3.groups import ALIGNMENT, EXTRA_HEADER_SIZE, RECORD_SIZE, RECORD_START, LayoutError

HEADER = 0x50


def record(ident, flags=0, size=0, name=""):
    """One 0x40-byte record: u16 id, u16 flags, u32 size, name, pad."""
    buf = bytearray(RECORD_SIZE)
    struct.pack_into("<HHI", buf, 0, ident, flags, size)
    buf[8:8 + len(name)] = name.encode("latin-1")
    return bytes(buf)


def res(name, payload, flags=0):
    """A sized resource: record, optional second header, data, 16-byte padding."""
    extra = b"\x00" * EXTRA_HEADER_SIZE if flags else b""
    pad = b"\x00" * ((-len(payload)) % ALIGNMENT)
    return record(groups.ID_RESOURCE, flags, len(payload), name) + extra + payload + pad


def unsized(name):
    buf = bytearray(RECORD_SIZE)
    struct.pack_into("<HH", buf, 0, groups.ID_UNSIZED, 1)
    buf[4:4 + len(name)] = name.encode("latin-1")
    return bytes(buf)


def group(name):
    ident = groups.GROUP_START if name == "GroupStart" else groups.GROUP_END
    return record(ident, name=name)


def wad(*parts, tail=b""):
    return b"\x00" * HEADER + b"".join(parts) + tail


class TestRecords(unittest.TestCase):
    def test_group_records_are_one_slot(self):
        rec = groups.read_record(wad(group("GroupStart")), RECORD_START)
        self.assertEqual(rec.kind, "GroupStart")
        self.assertEqual(rec.end, RECORD_START + RECORD_SIZE)
        self.assertIsNone(rec.data)

    def test_sized_resource_points_at_its_data(self):
        data = wad(res("TXRX_R_X", b"x" * 16))
        rec = groups.read_record(data, RECORD_START)
        self.assertEqual(rec.name, "TXRX_R_X")
        self.assertEqual(rec.size, 16)
        self.assertEqual(rec.data, RECORD_START + RECORD_SIZE)

    def test_flags_add_a_second_header(self):
        data = wad(res("ANM_x", b"x" * 16, flags=0x34))
        rec = groups.read_record(data, RECORD_START)
        self.assertEqual(rec.data, RECORD_START + RECORD_SIZE + EXTRA_HEADER_SIZE)

    def test_data_is_padded_to_16_bytes(self):
        data = wad(res("A_B", b"x" * 20))
        rec = groups.read_record(data, RECORD_START)
        self.assertEqual(rec.size, 20)
        self.assertEqual(rec.end, RECORD_START + RECORD_SIZE + 32)   # 20 -> 32

    def test_unsized_record_names_at_plus_four(self):
        data = wad(unsized("TX12345678.AABBCCDD.dds"))
        rec = groups.read_record(data, RECORD_START)
        self.assertEqual(rec.kind, "unsized")
        self.assertEqual(rec.name, "TX12345678.AABBCCDD.dds")
        self.assertIsNone(rec.size)

    def test_class_name_is_resolved_from_flags(self):
        data = wad(res("ANM_x", b"x" * 16, flags=0x34))
        self.assertEqual(groups.read_record(data, RECORD_START).class_name, "animation")

    def test_unnamed_sized_resource_is_rejected(self):
        data = wad(record(groups.ID_RESOURCE, 0, 16, ""))
        with self.assertRaises(LayoutError):
            groups.read_record(data, RECORD_START)

    def test_overrunning_resource_is_rejected(self):
        data = wad(record(groups.ID_RESOURCE, 0, 0x10000, "A_B"))
        with self.assertRaises(LayoutError):
            groups.read_record(data, RECORD_START)

    def test_unmodelled_id_is_rejected(self):
        data = wad(record(9, 0, 0, ""))
        with self.assertRaises(LayoutError):
            groups.read_record(data, RECORD_START)


class TestWalking(unittest.TestCase):
    def test_walks_groups_and_resources_in_order(self):
        data = wad(
            group("GroupStart"),
            res("WAD_R_X", b"x" * 24),
            group("GroupEnd"),
            group("GroupStart"),
            res("TXRX_R_X", b"x" * 16),
            group("GroupEnd"),
        )
        records, why = groups.inventory(data)
        self.assertIsNone(why)
        self.assertEqual([r.kind for r in records],
                         ["GroupStart", "resource", "GroupEnd",
                          "GroupStart", "resource", "GroupEnd"])
        self.assertEqual([r.name for r in groups.resources(records)],
                         ["WAD_R_X", "TXRX_R_X"])

    def test_data_regions_do_not_overlap_and_cover_the_stream(self):
        data = wad(
            group("GroupStart"),
            res("WAD_R_X", b"x" * 40),
            group("GroupEnd"),
        )
        records, why = groups.inventory(data)
        self.assertIsNone(why)
        for first, second in zip(records, records[1:]):
            self.assertEqual(first.end, second.offset)
        self.assertEqual(records[-1].end, len(data))

    def test_resource_text_matches_the_bytes_at_its_data_offset(self):
        payload = b"PAYLOAD!"
        data = wad(res("A_B", payload))
        rec = groups.read_record(data, RECORD_START)
        self.assertEqual(rec.text(data), payload)

    def test_inventory_reports_where_and_why_it_stopped(self):
        data = wad(group("GroupStart"), record(9, 0, 0, ""))
        records, why = groups.inventory(data)
        self.assertEqual(len(records), 1)
        self.assertIsNotNone(why)
        self.assertIn("unmodelled record id 9", why)

    def test_inventory_handles_an_empty_stream(self):
        records, why = groups.inventory(b"\x00" * HEADER)
        self.assertEqual(records, [])
        self.assertIsNone(why)

    def test_exact_boundary_is_how_the_layout_was_verified(self):
        # Mirror R_HADES.WAD: an animation resource whose size lands exactly on
        # the next record. This is the property that proved the model.
        data = wad(
            res("ANM_hero_Hades", b"x" * 4096, flags=0x34),
            group("GroupEnd"),
        )
        records, why = groups.inventory(data)
        self.assertIsNone(why)
        self.assertEqual(records[0].name, "ANM_hero_Hades")
        self.assertEqual(records[0].end, records[1].offset)
        self.assertEqual(records[1].kind, "GroupEnd")

    def test_alignment_is_sixteen(self):
        self.assertEqual(ALIGNMENT, 0x10)


if __name__ == "__main__":
    unittest.main()
