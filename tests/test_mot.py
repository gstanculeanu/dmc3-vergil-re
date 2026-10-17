import _bootstrap  # noqa: F401
import struct
import unittest

import fixtures
from dmc3 import Chunk, MotError, parse_mot, parse_mot_from_bytes
from dmc3.mot import TABLE_MAX, maybe_track_payload


def chunk_of(payload: bytes) -> Chunk:
    return Chunk(index=0, offset=0, span=len(payload), data=payload)


class TestMotHeader(unittest.TestCase):
    def test_parses_observed_layout(self):
        header = parse_mot(chunk_of(fixtures.motion_chunk()))
        self.assertEqual(header.header_size, fixtures.MOT_HEADER_SIZE)
        self.assertEqual(header.header_size, 0x50)
        self.assertEqual(header.count_b, fixtures.MOT_BONES)
        self.assertEqual(header.table, [fixtures.MOT_STRIDE] * TABLE_MAX)
        self.assertAlmostEqual(header.duration, 50.0, places=4)

    def test_table_length_relation_is_exact(self):
        # Verified invariant: header_size == 0x22 + 2 * len(table).
        header = parse_mot(chunk_of(fixtures.motion_chunk()))
        self.assertEqual(header.header_size, 0x22 + 2 * len(header.table))
        self.assertTrue(header.is_common_shape())

    def test_duration_is_duplicated(self):
        header = parse_mot(chunk_of(fixtures.motion_chunk(duration=61.0)))
        self.assertAlmostEqual(header.duration, 61.0, places=4)
        self.assertAlmostEqual(header.duration_dup, 61.0, places=4)
        self.assertTrue(header.durations_match)

    def test_inferred_bone_count_is_unproven_but_exposed(self):
        header = parse_mot(chunk_of(fixtures.motion_chunk(bones=23)))
        self.assertEqual(header.likely_bone_count, 23)
        self.assertEqual(header.count_a, 23)

    def test_flag_and_unknowns(self):
        header = parse_mot_from_bytes(fixtures.motion_chunk(flag_a=1))
        self.assertEqual(header.flag_a, 1)
        self.assertEqual(header.unknown_1e, 0x01C0)

    def test_track_payload_is_remainder_after_header(self):
        payload = fixtures.motion_chunk(track_bytes=128)
        track = maybe_track_payload(chunk_of(payload))
        self.assertIsNotNone(track)
        self.assertEqual(len(track), 128)

    def test_smaller_table_is_tolerated(self):
        # A 0x50-header chunk whose table is shorter must not crash the parser.
        blob = bytearray(fixtures.motion_chunk())
        blob[0:4] = (0x2E).to_bytes(4, "little")  # 0x22 + 2*6 = 0x2E
        header = parse_mot(chunk_of(bytes(blob)))
        self.assertEqual(len(header.table), 6)


class TestMotRejectsBadInput(unittest.TestCase):
    def test_wrong_tag(self):
        with self.assertRaises(MotError):
            parse_mot(chunk_of(b"MOD " + b"\x00" * 96))

    def test_truncated(self):
        with self.assertRaises(MotError):
            parse_mot(chunk_of(b"\x50\x00\x00\x00MOT\x00"))

    def test_odd_header_size(self):
        blob = bytearray(fixtures.motion_chunk())
        blob[0:4] = (0x51).to_bytes(4, "little")
        with self.assertRaises(MotError):
            parse_mot(chunk_of(bytes(blob)))

    def test_header_past_end(self):
        blob = bytearray(fixtures.motion_chunk())
        blob[0:4] = (0x7FFF).to_bytes(4, "little")
        with self.assertRaises(MotError):
            parse_mot(chunk_of(bytes(blob)))

    def test_invalid_returns_none_from_helper(self):
        self.assertIsNone(maybe_track_payload(chunk_of(b"nope" + b"\x00" * 96)))


def _mot_chunk(table: list[int]) -> bytes:
    """A MOT chunk whose +0x22 table is written verbatim.

    All other header fields mirror the common real shape (0x50 header,
    duration 50, cb 24), so only the table differs.
    """
    blob = bytearray(fixtures.motion_chunk(table_value=0))
    assert len(table) == fixtures.MOT_TABLE_LEN
    for index, value in enumerate(table):
        struct.pack_into("<H", blob, fixtures.MOT_TABLE_OFFSET + 2 * index, value)
    return bytes(blob)


class TestMotTableRealShapes(unittest.TestCase):
    """The +0x22 table shapes observed across all 840 real MOT chunks (E-032).

    The table's meaning is [UNKNOWN]; these tests only lock the observed
    structures and the parser's handling of them.
    """

    def test_dominant_shape_56_times_22_then_0(self):
        # pl021_00_9.pac slot 0 and 702 other chunks: 22 x 56 (0x38), then 0.
        table = [56] * fixtures.MOT_TABLE_LEN
        table[-1] = 0
        header = parse_mot(chunk_of(_mot_chunk(table)))
        self.assertEqual(header.table, table)
        self.assertEqual(header.header_size, fixtures.MOT_HEADER_SIZE)
        self.assertEqual(header.header_size, 0x22 + 2 * len(header.table))

    def test_real_variant_shapes_parse(self):
        for table in (
            [504] * 22 + [0],        # Crimson overlay mods (newJudgementCut_*, …)
            [58] * 22 + [0],         # pl000_00_20.pac slot 2, pl000_00_9.pac slot 6
            [56] * 21 + [0, 0],      # pl002_00_0.pac (there +0x1C == 23)
        ):
            header = parse_mot(chunk_of(_mot_chunk(table)))
            self.assertEqual(header.table, list(table))
            self.assertEqual(header.header_size, 0x22 + 2 * len(header.table))

    def test_table_entries_span_full_u16_range(self):
        header = parse_mot(chunk_of(_mot_chunk([0xFFFF, 0x8000, 0x7FFF] + [0] * 20)))
        self.assertEqual(header.table[:3], [0xFFFF, 0x8000, 0x7FFF])


if __name__ == "__main__":
    unittest.main()
