import _bootstrap  # noqa: F401
import struct
import unittest

import fixtures
from dmc3 import Chunk, MotError, try_walk_records, walk_records
from dmc3.mot import KEYFRAME_TIME_BASE, RECORD_HEADER_SIZE, keyframe_time


def chunk_of(payload: bytes) -> Chunk:
    return Chunk(index=0, offset=0, span=len(payload), data=payload)


class TestMotRecordWalk(unittest.TestCase):
    def test_walks_every_record(self):
        payload = walk_records(chunk_of(fixtures.motion_chunk_with_records((4, 2, 6))))
        self.assertEqual(payload.record_count, 3)
        self.assertEqual(payload.decoded, 3)
        self.assertEqual([r.groups for r in payload.records], [4, 2, 6])

    def test_sizes_follow_the_documented_relation(self):
        payload = walk_records(chunk_of(fixtures.motion_chunk_with_records((1, 4, 16))))
        for record in payload.records:
            self.assertTrue(record.size_is_consistent)
            self.assertEqual(record.size, 8 * (record.groups + 4))
            self.assertEqual(record.size - RECORD_HEADER_SIZE, 8 * (record.groups + 3))

    def test_eight_byte_groups(self):
        payload = walk_records(chunk_of(fixtures.motion_chunk_with_records((4,))))
        record = payload.records[0]
        self.assertEqual(record.group_count, 7)  # groups + 3
        self.assertEqual(len(record.group_bytes()), 7)
        self.assertTrue(all(len(g) == 8 for g in record.group_bytes()))

    def test_record_offsets_are_chunk_relative_and_contiguous(self):
        payload = walk_records(chunk_of(fixtures.motion_chunk_with_records((4, 2, 6))))
        header_size = fixtures.MOT_HEADER_SIZE
        self.assertEqual(payload.records[0].offset, header_size + 4)
        for first, second in zip(payload.records, payload.records[1:]):
            self.assertEqual(first.offset + first.size, second.offset)

    def test_no_tail_when_there_is_no_padding(self):
        payload = walk_records(chunk_of(fixtures.motion_chunk_with_records((4,), tail=0)))
        self.assertEqual(payload.tail, b"")
        self.assertTrue(payload.complete)

    def test_tail_padding_is_reported_not_an_error(self):
        payload = walk_records(chunk_of(fixtures.motion_chunk_with_records((4,), tail=12)))
        self.assertEqual(len(payload.tail), 12)
        self.assertTrue(payload.complete)

    def test_group_histogram(self):
        payload = walk_records(chunk_of(fixtures.motion_chunk_with_records((4, 4, 2))))
        self.assertEqual(payload.group_histogram(), {4: 2, 2: 1})

    def test_empty_record_list(self):
        payload = walk_records(chunk_of(fixtures.motion_chunk_with_records(())))
        self.assertEqual(payload.record_count, 0)
        self.assertEqual(payload.records, [])
        self.assertTrue(payload.complete)


class TestMotRecordWalkRejects(unittest.TestCase):
    def test_not_a_motion_chunk(self):
        with self.assertRaises(MotError):
            walk_records(chunk_of(fixtures.plain_chunk(b"MOD ")))

    def test_payload_too_short_for_a_count(self):
        # a truncated payload with a non-zero count must fail
        blob = bytearray(fixtures.motion_chunk_with_records((4,)))
        del blob[-8:]
        with self.assertRaises(MotError):
            walk_records(chunk_of(bytes(blob)))

    def test_zero_size_record_rejected(self):
        blob = bytearray(fixtures.motion_chunk_with_records((4,)))
        import struct

        struct.pack_into("<H", blob, fixtures.MOT_HEADER_SIZE + 4, 0)
        with self.assertRaises(MotError):
            walk_records(chunk_of(bytes(blob)))

    def test_helper_returns_none_instead_of_raising(self):
        self.assertIsNone(try_walk_records(chunk_of(fixtures.plain_chunk(b"MOD "))))
        self.assertIsNotNone(
            try_walk_records(chunk_of(fixtures.motion_chunk_with_records((4,))))
        )


class TestMotKeyframeTime(unittest.TestCase):
    """The first u16 of an 8-byte keyframe group is ``0x8000 + frame`` (E-026)."""

    def test_frame_zero(self):
        self.assertEqual(
            keyframe_time(struct.pack("<HHHH", KEYFRAME_TIME_BASE, 0, 0, 0)), 0
        )

    def test_frame_positive(self):
        self.assertEqual(
            keyframe_time(struct.pack("<HHHH", KEYFRAME_TIME_BASE + 23, 0, 0, 0)), 23
        )

    def test_frame_matches_duration_example(self):
        # keyframe[3] of pl021_00_9.pac record 0: u16[0] = 0x8064, duration = 100
        self.assertEqual(
            keyframe_time(struct.pack("<HHHH", KEYFRAME_TIME_BASE + 100, 0, 0, 0)),
            100,
        )


if __name__ == "__main__":
    unittest.main()
