import _bootstrap  # noqa: F401
import struct
import unittest

import fixtures
from dmc3 import Chunk, MotError, try_walk_records, walk_records
from dmc3.mot import (
    KEYFRAME_TIME_BASE,
    RECORD_HEADER_SIZE,
    keyframe_groups,
    keyframe_time,
)


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


class TestMotKeyframeSplit(unittest.TestCase):
    """The record splits into ``field_a`` preamble groups + ``groups`` keyframes.

    Verified structure on real data (E-028): ``len(group_bytes()) ==
    field_a + groups`` for 7,656/7,659 walked records; ``field_a == 3`` for
    7,656/7,659.  What the preamble groups encode is unknown (issue F4).
    """

    def test_group_bytes_splits_into_preamble_and_keyframes(self):
        payload = walk_records(chunk_of(fixtures.motion_chunk_with_records((4, 2, 6))))
        self.assertEqual([r.groups for r in payload.records], [4, 2, 6])
        for record in payload.records:
            all_groups = record.group_bytes()
            self.assertEqual(len(all_groups), record.field_a + record.groups)
            self.assertTrue(all(len(g) == 8 for g in all_groups))

    def test_keyframe_groups_skip_the_field_a_preamble(self):
        payload = walk_records(chunk_of(fixtures.motion_chunk_with_records((4, 2, 6))))
        for record in payload.records:
            keyframes = keyframe_groups(record)
            self.assertEqual(len(keyframes), record.groups)
            # every keyframe's first u16 is an offset-binary frame time (E-026)
            for group in keyframes:
                self.assertGreaterEqual(keyframe_time(group), 0)


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


class TestMotKeyframeChannelStructure(unittest.TestCase):
    """Structure checks on the keyframe group's remaining three u16s.

    Real-data finding (E-029): u16[1..3] vary per keyframe — they are NOT
    per-record constants — and the preamble is NOT a stored base pose
    (preamble == first keyframe groups in 0/7,659 real records).  These tests
    lock the structure so a future decoder can target the right fields.
    """

    def _chunk_with_records(self, record_groups, preamble_values):
        """Build a MOT chunk whose payload holds one record per entry.

        ``record_groups`` is the per-record ``groups`` value; ``preamble_values``
        is the per-record list of ``field_a`` 8-byte preamble groups.  Each
        keyframe group is ``(0x8000 + k, k, 100 + k, 0x3FFF)`` so u16[1] and
        u16[2] vary per keyframe within a record.
        """
        records = bytearray(struct.pack("<I", len(record_groups)))
        for groups in record_groups:
            size = 8 * (groups + 4)
            records += struct.pack("<HHHH", size, groups, 3, 0)
            # field_a == 3 preamble groups, then ``groups`` keyframes
            for group in preamble_values:
                records += group
            for k in range(groups):
                records += struct.pack("<HHHH", 0x8000 + k, k, 100 + k, 0x3FFF)
        header_size = fixtures.MOT_TABLE_OFFSET + 2 * fixtures.MOT_TABLE_LEN
        blob = bytearray(header_size)
        struct.pack_into("<I", blob, 0x00, header_size)
        blob[0x04:0x08] = b"MOT\x00"
        struct.pack_into("<f", blob, 0x0C, 100.0)
        struct.pack_into("<f", blob, 0x14, 100.0)
        struct.pack_into("<H", blob, 0x18, 1)
        struct.pack_into("<H", blob, 0x1A, 23)
        struct.pack_into("<H", blob, 0x1C, 24)
        struct.pack_into("<H", blob, 0x1E, 0)
        struct.pack_into("<H", blob, 0x20, 448)
        for index in range(fixtures.MOT_TABLE_LEN):
            struct.pack_into("<H", blob, fixtures.MOT_TABLE_OFFSET + 2 * index, 56)
        return chunk_of(bytes(blob) + records)

    def test_preamble_groups_are_positions_zero_to_field_a_minus_one(self):
        preamble = [
            struct.pack("<HHHH", 1, 2, 3, 4),
            struct.pack("<HHHH", 5, 6, 7, 8),
            struct.pack("<HHHH", 9, 10, 11, 12),
        ]
        payload = walk_records(self._chunk_with_records((3,), preamble))
        record = payload.records[0]
        all_groups = record.group_bytes()
        self.assertEqual(len(all_groups), record.field_a + record.groups)
        self.assertEqual(all_groups[: record.field_a], preamble)
        self.assertEqual(len(keyframe_groups(record)), record.groups)

    def test_u16_channels_vary_per_keyframe_not_per_record(self):
        # u16[1] = k and u16[2] = 100 + k differ across keyframes within a record
        preamble = [struct.pack("<HHHH", 0, 0, 0, 0)] * 3
        payload = walk_records(self._chunk_with_records((4,), preamble))
        record = payload.records[0]
        keyframes = keyframe_groups(record)
        self.assertEqual(len(keyframes), 4)
        ch1 = [struct.unpack("<H", g[2:4])[0] for g in keyframes]
        ch2 = [struct.unpack("<H", g[4:6])[0] for g in keyframes]
        self.assertEqual(ch1, [0, 1, 2, 3])
        self.assertEqual(ch2, [100, 101, 102, 103])
        self.assertEqual(len(set(ch1)), 4)
        self.assertEqual(len(set(ch2)), 4)

    def test_preamble_is_not_the_first_keyframe_group(self):
        preamble = [struct.pack("<HHHH", 0, 0, 0, 0)] * 3
        payload = walk_records(self._chunk_with_records((2,), preamble))
        record = payload.records[0]
        keyframes = keyframe_groups(record)
        self.assertNotEqual(record.group_bytes()[: record.field_a], keyframes[: len(preamble)])


if __name__ == "__main__":
    unittest.main()
