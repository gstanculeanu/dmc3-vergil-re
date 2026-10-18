import struct
import unittest

from gow3 import wadgraph
from gow3.wadgraph import WadGraphError, RECORD_SIZE, RECORD_START, TRAILER_CONSTANT, RECORD_SENTINEL

RECORD_FMT = "<IIIIHQBBI"  # name_offset, 0, field_b, field_d, field_c, -1, 0, pad, trailer
assert struct.calcsize(RECORD_FMT) == RECORD_SIZE == 0x20


def wadgraph_byte(records, banner="WadGraph", field_00=23, field_02=1,
                  size_field=0x00040DF0):
    """Synthetic WadGraph file mirroring the observed layout (E-045).

    Header (0x40 bytes): u16 field_00, u16 field_02, u32 size_field,
    char[0x38] banner. Records (0x20 bytes, stride 0x20 from 0x40):
    u32 name_offset; u32 0; u32 field_b; u32 field_d; u16 field_c;
    u64 -1; u8 0; u8 pad_byte; u32 0x55555555. Name strings are NUL
    terminated and appended after the records; each matching record's
    name_offset targets its string exactly, mirroring the observed real
    records. No game data is committed.
    """
    header = bytearray(RECORD_START)
    struct.pack_into("<HHI", header, 0x00, field_00, field_02, size_field)
    banner_bytes = banner.encode("latin-1")
    header[0x08:0x08 + len(banner_bytes)] = banner_bytes

    pool_start = RECORD_START + RECORD_SIZE * len(records)
    strings = bytearray()
    offsets = []
    for record in records:
        if record["name"] is None:
            offsets.append(None)
            continue
        encoded = record["name"].encode("latin-1") + b"\x00"
        offsets.append(pool_start + len(strings))
        strings += encoded

    records_blob = bytearray(RECORD_SIZE * len(records))
    for index, record in enumerate(records):
        if record["name"] is None:
            continue  # gap window: all zeros, does not match the record pattern
        off = RECORD_SIZE * index
        struct.pack_into(RECORD_FMT, records_blob, off,
                         offsets[index], 0,
                         record.get("field_b", 0),
                         record.get("field_d", 0),
                         record.get("field_c", 0),
                         RECORD_SENTINEL,
                         0,
                         record.get("pad", 0x00),
                         TRAILER_CONSTANT)
    return bytes(header) + bytes(records_blob) + bytes(strings)


class TestWadGraphHeader(unittest.TestCase):
    def test_parses_observed_header_fields(self):
        data = wadgraph_byte([{"name": "R_TestBoss"}])
        header = wadgraph.parse_header(data)
        self.assertEqual(header.field_00, 23)
        self.assertEqual(header.field_02, 1)
        self.assertEqual(header.size_field, 0x00040DF0)
        self.assertEqual(header.banner, "WadGraph")
        self.assertTrue(header.looks_valid)

    def test_rejects_short_file(self):
        with self.assertRaises(WadGraphError):
            wadgraph.parse_header(b"\x17\x00")

    def test_rejects_unknown_banner(self):
        self.assertFalse(wadgraph.is_wadgraph(
            b"\x17\x00\x01\x00\xf0\x0d\x04\x00NotWadGraphRegistry"))


class TestWadGraphRecords(unittest.TestCase):
    def setUp(self):
        self.data = wadgraph_byte([
            {"name": "R_TestBoss", "field_b": 0x001C0630, "field_d": 0,
             "field_c": 21, "pad": 0x34},
            {"name": "Stub_0000", "field_b": 0, "field_d": 0x00F00000,
             "field_c": 4, "pad": 0x00},
            {"name": None},                                    # gap window
            {"name": "ARArcher00", "field_b": 0, "field_d": 0,
             "field_c": 1609, "pad": 0x02},
        ])

    def test_parses_matching_records_and_skips_gaps(self):
        graph = wadgraph.parse(self.data)
        self.assertEqual(len(graph.records), 3)
        self.assertEqual([r.offset for r in graph.records], [0x40, 0x60, 0xA0])

    def test_record_fields_match_observed_layout(self):
        graph = wadgraph.parse(self.data)
        first = graph.records[0]
        self.assertEqual(first.name_offset, 0xC0)
        self.assertEqual(first.field_b, 0x001C0630)
        self.assertEqual(first.field_d, 0)
        self.assertEqual(first.field_c, 21)
        self.assertEqual(first.pad_byte, 0x34)
        self.assertEqual(first.trailer, TRAILER_CONSTANT)
        last = graph.records[2]
        self.assertEqual(last.field_d, 0)
        self.assertEqual(last.pad_byte, 0x02)

    def test_record_name_resolves_exact_offset(self):
        graph = wadgraph.parse(self.data)
        self.assertEqual(
            [wadgraph.record_name(self.data, r) for r in graph.records],
            ["R_TestBoss", "Stub_0000", "ARArcher00"])

    def test_name_offset_carries_no_wad_binding(self):
        # name_offset resolves to name-string bytes only; field_b remains
        # [UNKNOWN] and this parser asserts no WAD binding.
        graph = wadgraph.parse(self.data)
        self.assertTrue(all(r.field_b in (0, 0x001C0630) for r in graph.records))


class TestRecordNameHeuristic(unittest.TestCase):
    def test_returns_none_for_binary_offset(self):
        data = wadgraph_byte([{"name": "x"}])
        # point record 0's name_offset at the banner region (zeros) and re-parse
        blob = bytearray(data)
        struct.pack_into("<I", blob, 0x40, 0x10)
        graph = wadgraph.parse(bytes(blob))
        self.assertEqual(graph.records[0].name_offset, 0x10)
        self.assertIsNone(wadgraph.record_name(bytes(blob), graph.records[0]))


if __name__ == "__main__":
    unittest.main()
