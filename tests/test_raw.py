import _bootstrap  # noqa: F401  (adds ../tools to sys.path)
import struct
import unittest

import fixtures
from dmc3 import RawHeader
from dmc3.raw import (
    PAC_TEXTURE_DESCRIPTOR_OFFSET,
    SLOT0_HEADER_SIZE,
    SLOT10_PAIR_COUNT,
    SLOT21_SEPARATOR,
    SLOT5_SEGMENT_COUNT,
    SLOT9_FLOAT_COUNT,
    TEXTURE_DESCRIPTOR_SIZE,
    TEXTURE_DDS_OFFSET,
    TM2_TEXTURE_DESCRIPTOR_OFFSET,
    maybe_raw_header,
    maybe_slot10_table,
    maybe_slot21_table,
    maybe_slot5_table,
    maybe_slot9_table,
    maybe_texture_chunk,
    RawHeader,
    Slot10Table,
    Slot21Table,
    Slot5Table,
    Slot9Table,
    TextureChunk,
)


def chunk_data() -> bytes:
    return fixtures.raw_chunk_slot0()


def slot10_data() -> bytes:
    return fixtures.raw_chunk_slot10()


def slot21_data() -> bytes:
    return fixtures.raw_chunk_slot21()


def slot5_data() -> bytes:
    return fixtures.raw_chunk_slot5()


def slot9_data() -> bytes:
    return fixtures.raw_chunk_slot9()


class TestRawHeader(unittest.TestCase):
    """Decoded raw-chunk header (E-033). All values are verbatim observations
    from pl021.pac slot 0; every field meaning is [UNKNOWN] and is only
    asserted, never interpreted."""

    def test_parses_slot_0_header(self):
        header = RawHeader.parse(chunk_data())
        self.assertEqual(header.field_00, 5)
        self.assertEqual(header.field_04, 43)
        self.assertEqual(header.field_08, 22)
        self.assertEqual(header.field_0c, 43)
        self.assertEqual(header.field_10, 5)
        self.assertEqual(header.field_14, 1)

    def test_header_size(self):
        self.assertEqual(SLOT0_HEADER_SIZE, 0x18)

    def test_rejects_short_input(self):
        with self.assertRaises(ValueError):
            RawHeader.parse(chunk_data()[:SLOT0_HEADER_SIZE - 1])
        self.assertIsNone(maybe_raw_header(b"\x00" * 10))

    def test_fields_match_real_bytes(self):
        # Verbatim from pl021.pac slot 0, file offset 0x80 (E-033).
        header = RawHeader.parse(chunk_data())
        self.assertEqual(
            (header.field_00, header.field_04, header.field_08,
             header.field_0c, header.field_10, header.field_14),
            (5, 43, 22, 43, 5, 1),
        )


class TestSlot10Table(unittest.TestCase):
    """Decoded slot-10 table layout (E-037). All values are verbatim
    observations from pl021.pac slot 10; every field meaning is [UNKNOWN] and
    is only asserted, never interpreted."""

    def expected_pairs(self) -> tuple[tuple[int, int], ...]:
        pairs = tuple((92, 132 + 20 * i) for i in range(15))
        pairs += ((112, 432), (92, 432))
        pairs += ((92, 132),) * 6
        self.assertEqual(len(pairs), SLOT10_PAIR_COUNT)
        return pairs

    def test_parses_slot_10_table(self):
        table = Slot10Table.parse(slot10_data())
        self.assertEqual(table.pairs, self.expected_pairs())
        self.assertEqual(len(table.pairs), SLOT10_PAIR_COUNT)

    REAL_FLOAT_PREFIX = bytes.fromhex("9a99993e0ad7a3bccdccccbd000000006666663f")
    """Verbatim f32s from pl021.pac slot 10 at body+0x5C (E-037)."""

    def test_reads_float_stream(self):
        import struct

        expected = struct.unpack("<5f", self.REAL_FLOAT_PREFIX)
        table = Slot10Table.parse(slot10_data())
        for observed, want in zip(table.floats[:5], expected):
            self.assertAlmostEqual(observed, want, places=6)
        self.assertTrue(all(v == 0.0 for v in table.floats[5:]))

    def test_pairs_match_real_bytes(self):
        # Verbatim u16 pairs from pl021.pac slot 10, file offset 0x077ED0
        # (E-037): pairs 0-14 have first element 92, second rising by 20.
        table = Slot10Table.parse(slot10_data())
        self.assertEqual(table.pairs[:3], ((92, 132), (92, 152), (92, 172)))
        self.assertEqual(table.pairs[14], (92, 412))
        self.assertEqual(table.pairs[15], (112, 432))
        self.assertEqual(table.pairs[16], (92, 432))
        self.assertEqual(table.pairs[17:], ((92, 132),) * 6)

    def test_rejects_short_input(self):
        with self.assertRaises(ValueError):
            Slot10Table.parse(slot10_data()[:4 * SLOT10_PAIR_COUNT - 1])
        self.assertIsNone(maybe_slot10_table(b"\x00" * 10))


class TestSlot21Table(unittest.TestCase):
    """Decoded slot-21 u16 segment table (E-043). All values are verbatim
    observations from pl021.pac slot 21; every field meaning is [UNKNOWN] and
    is only asserted, never interpreted."""

    REAL_SEGMENT_SIZES = (2, 6, 1, 8, 10, 31, 111, 34, 1, 6, 8, 27, 84, 26)
    """Segment sizes (u16s each) observed in pl021.pac slot 21 (E-043)."""

    def test_parses_slot_21_segments(self):
        table = Slot21Table.parse(slot21_data())
        self.assertEqual(len(table.segments), len(self.REAL_SEGMENT_SIZES))
        self.assertEqual(
            [len(seg) for seg in table.segments], list(self.REAL_SEGMENT_SIZES)
        )
        # Segment 0 is verbatim from pl021.pac slot 21 (E-043).
        self.assertEqual(table.segments[0], (6, 408))

    def test_separators_are_not_segment_data(self):
        table = Slot21Table.parse(slot21_data())
        self.assertFalse(
            any(SLOT21_SEPARATOR in segment for segment in table.segments)
        )

    def test_rejects_odd_length(self):
        with self.assertRaises(ValueError):
            Slot21Table.parse(b"\x00" * 5)
        self.assertIsNone(maybe_slot21_table(b"\x00" * 5))

    def test_empty_input_yields_one_empty_segment(self):
        table = Slot21Table.parse(b"")
        self.assertEqual(table.segments, ((),))


class TestSlot5Table(unittest.TestCase):
    """Decoded slot-5 segment stream (E-052). All values are verbatim
    observations from pl021.pac slot 5 where noted; every field meaning is
    [UNKNOWN] and is only asserted, never interpreted."""

    REAL_SEGMENT_0 = (6, 0x37D0)
    """Verbatim segment 0 from pl021.pac slot 5, file offset 0x06B6E0 (E-052)."""

    REAL_SEGMENT_2_PREFIX = (
        70, 0x7AC, 0xD4E, 0xEBE, 0x15E2, 0x1D54, 0x2636,
        0x26A4, 0x2DC0, 0x335A,
    )
    """Verbatim opening of segment 2 from pl021.pac slot 5 (E-052)."""

    def test_parses_slot_5_segments(self):
        table = Slot5Table.parse(slot5_data())
        self.assertEqual(len(table.segments), 6)
        self.assertEqual(table.segments[0], self.REAL_SEGMENT_0)
        self.assertEqual(table.segments[1], (4,))
        self.assertEqual(table.segments[2][: len(self.REAL_SEGMENT_2_PREFIX)],
                         self.REAL_SEGMENT_2_PREFIX)
        self.assertEqual(len(table.segments[2]), 34)
        # 0x7FFF is data, not a delimiter: it stays inside its segment.
        self.assertEqual(table.segments[5], (0x7FFF, 0xABCD))

    def test_separators_are_not_segment_data(self):
        table = Slot5Table.parse(slot5_data())
        self.assertFalse(
            any(0xFFFF in segment for segment in table.segments)
        )

    def test_segment_count_matches_observation(self):
        # The real chunk was observed to split into 215 segments (E-052); the
        # constant locks that observation without requiring every chunk to
        # match it.
        self.assertEqual(SLOT5_SEGMENT_COUNT, 215)

    def test_rejects_odd_length(self):
        with self.assertRaises(ValueError):
            Slot5Table.parse(slot5_data()[:-1])
        self.assertIsNone(maybe_slot5_table(b"\x00" * 3))


class TestSlot9Table(unittest.TestCase):
    """Decoded slot-9 flat f32 array (E-062). All values are verbatim
    observations from pl021.pac slot 9; every field meaning is [UNKNOWN] and is
    only asserted, never interpreted."""

    REAL_HEAD_HEX = (
        "666626419a9999bf0000204100004041"
        "9a9999bf0000704166662641cdcc4cbf"
        "cdcccc4066664641cdcc4cbf00004041"
    )
    """The first 12 f32s (48 bytes) at pl021.pac file offset 0x077B50 (E-062)."""

    def expected_head(self) -> tuple[float, ...]:
        return struct.unpack("<12f", bytes.fromhex(self.REAL_HEAD_HEX))

    def test_parses_slot_9_array(self):
        table = Slot9Table.parse(slot9_data())
        self.assertEqual(len(table.floats), SLOT9_FLOAT_COUNT)

    def test_float_count_constant(self):
        # The real chunk's span is 896 bytes = 224 f32s (E-062); the constant
        # locks that observation without requiring every chunk to match it.
        self.assertEqual(SLOT9_FLOAT_COUNT, 224)

    def test_head_matches_real_bytes(self):
        table = Slot9Table.parse(slot9_data())
        for observed, want in zip(table.floats, self.expected_head()):
            self.assertAlmostEqual(observed, want, places=6)

    def test_rejects_wrong_length(self):
        # The parser requires exactly 4 * SLOT9_FLOAT_COUNT bytes.
        with self.assertRaises(ValueError):
            Slot9Table.parse(slot9_data()[:-4])
        with self.assertRaises(ValueError):
            Slot9Table.parse(slot9_data() + b"\x00\x00\x00\x00")
        self.assertIsNone(maybe_slot9_table(b"\x00" * 8))


class TestTextureChunk(unittest.TestCase):
    """The DMC3 HD texture descriptor shared by the untagged PAC texture slots
    and the ``.tm2`` platform pre-header (E-084). All values are verbatim
    observations; relations are verified on the real artifacts, field meanings
    stay [UNKNOWN]."""

    def test_parses_pac_texture_slot(self):
        chunk = TextureChunk.parse(fixtures.raw_chunk_texture())
        self.assertEqual(chunk.descriptor_offset, PAC_TEXTURE_DESCRIPTOR_OFFSET)
        self.assertEqual(chunk.descriptor_offset, 0x808)
        self.assertEqual(chunk.dds_offset, TEXTURE_DDS_OFFSET)
        self.assertEqual(chunk.dds_offset, 0x870)
        self.assertEqual(TEXTURE_DESCRIPTOR_SIZE, 0x68)
        self.assertEqual((chunk.width, chunk.height), (32, 32))
        self.assertEqual(chunk.mips, 1)
        self.assertEqual(chunk.fourcc, b"DXT1")
        self.assertEqual(chunk.extent, (32, 32))
        self.assertEqual(chunk.half_extent, (16, 16))
        self.assertEqual(chunk.payload_size, 512)
        self.assertEqual(chunk.total_size, 640)
        self.assertEqual(chunk.field_00, 0x0100)
        self.assertEqual(chunk.field_02, 2)
        self.assertEqual(chunk.field_04, 0x0000AAE4)
        self.assertEqual(chunk.field_0c, 1)
        self.assertEqual(chunk.field_18, 64)
        self.assertEqual(chunk.field_60, 8)

    def test_relations_hold(self):
        chunk = TextureChunk.parse(fixtures.raw_chunk_texture())
        self.assertTrue(chunk.dimensions_match)
        self.assertTrue(chunk.half_extent_matches)
        self.assertTrue(chunk.inverse_scale_matches)
        self.assertTrue(chunk.total_size_matches)
        self.assertTrue(chunk.mips_match)

    def test_256x256_dx10_mirrors_slot_0(self):
        # pl021.pac slot 0: 256x256 DX10, 9 mips, 87428-byte payload (E-084).
        chunk = TextureChunk.parse(fixtures.raw_chunk_texture(
            width=256, height=256, mips=9, fourcc=b"DX10", payload_size=87428))
        self.assertEqual(chunk.fourcc, b"DX10")
        self.assertEqual(chunk.mips, 9)
        self.assertEqual(chunk.inverse_scale, (0.0078125, 0.0078125))
        self.assertTrue(chunk.mips_match)
        self.assertTrue(chunk.dimensions_match)
        self.assertTrue(chunk.half_extent_matches)
        self.assertTrue(chunk.inverse_scale_matches)
        self.assertTrue(chunk.total_size_matches)

    def test_tm2_descriptor_offset(self):
        # i001_90.tm2: the same descriptor at +0x08, DDS at +0x70 (E-084/E-034).
        chunk = TextureChunk.parse(
            fixtures.real_tm2(), TM2_TEXTURE_DESCRIPTOR_OFFSET)
        self.assertEqual(chunk.descriptor_offset, 0x08)
        self.assertEqual(chunk.dds_offset, 0x70)
        self.assertEqual((chunk.width, chunk.height), (256, 256))
        self.assertEqual(chunk.fourcc, b"DXT3")
        self.assertEqual(chunk.payload_size, 65536)
        self.assertTrue(chunk.dimensions_match)
        self.assertTrue(chunk.half_extent_matches)
        self.assertTrue(chunk.inverse_scale_matches)
        self.assertTrue(chunk.total_size_matches)
        self.assertTrue(chunk.mips_match)

    def test_default_offset_rejects_tm2(self):
        # A .tm2's descriptor is at +0x08, not the PAC default +0x808.
        self.assertIsNone(maybe_texture_chunk(fixtures.real_tm2()))

    def test_maybe_returns_none_without_dds(self):
        self.assertIsNone(maybe_texture_chunk(fixtures.raw_chunk_slot0()))
        self.assertIsNone(maybe_texture_chunk(b"\x00" * 0x900))

    def test_rejects_short_input(self):
        with self.assertRaises(ValueError):
            TextureChunk.parse(fixtures.raw_chunk_texture()[:0x870])


if __name__ == "__main__":
    unittest.main()
