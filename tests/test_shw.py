import _bootstrap  # noqa: F401  (adds ../tools to sys.path)
import unittest

import fixtures
from dmc3 import Chunk, ShwHeader
from dmc3.shw import HEADER_SIZE, maybe_shw_header


def chunk_of(payload: bytes) -> Chunk:
    return Chunk(index=0, offset=0, span=len(payload), data=payload)


class TestShwHeader(unittest.TestCase):
    """Decoded SHW shader-chunk header (E-036). All meanings [UNKNOWN]; only
    the observed bytes/values are asserted."""

    def test_parses_observed_layout(self):
        # Mirrors pl021.pac slot 8 (E-036).
        header = ShwHeader.parse(chunk_of(fixtures.shw_chunk()))
        self.assertEqual(header.alpha, 0.5)
        self.assertEqual(header.field_08, 0)
        self.assertEqual(header.field_0c, 0)
        self.assertEqual(header.field_10, 0x00011811)
        self.assertEqual(header.field_14, 100)
        self.assertEqual(header.field_18, 0)
        self.assertEqual(header.field_1c, 0)
        self.assertEqual(header.pair_20_0, 0x000A)
        self.assertEqual(header.pair_20_1, 0x0010)
        self.assertEqual(header.field_24, 0)
        self.assertEqual(header.field_28, 0)
        self.assertEqual(header.field_2c, 0)
        self.assertEqual(header.field_30, 0x460)
        self.assertEqual(header.field_34, 0)
        self.assertEqual(header.field_38, 0x560)
        self.assertEqual(header.field_3c, 0)
        self.assertEqual(header.field_40, 0x5E0)
        self.assertEqual(header.field_44, 0)
        self.assertEqual(header.field_48, 0x680)
        self.assertEqual(header.field_4c, 0)

    def test_header_size_is_0x50(self):
        self.assertEqual(HEADER_SIZE, 0x50)

    def test_field_28_is_zero(self):
        # +0x28 is u32 0 in all four real SHW chunks (E-036); the varying
        # neighbor is at +0x30 instead.
        header = ShwHeader.parse(chunk_of(fixtures.shw_chunk()))
        self.assertEqual(header.field_28, 0)
        self.assertEqual(header.field_30, 0x460)

    def test_field_30_varies_per_chunk(self):
        # +0x30 differs per mesh: slot 8 -> 0x460, slot 14 -> 0x1E0, slots
        # 24/26 -> 0x60 (E-036).
        values = (
            fixtures.shw_chunk(field_30=0x460),
            fixtures.shw_chunk(field_30=0x1E0),
            fixtures.shw_chunk(field_30=0x60),
        )
        self.assertEqual(
            [ShwHeader.parse(chunk_of(v)).field_30 for v in values],
            [0x460, 0x1E0, 0x60],
        )

    def test_zero_fields_are_zero(self):
        header = ShwHeader.parse(chunk_of(fixtures.shw_chunk()))
        for name in (
            "field_08", "field_0c", "field_18", "field_1c", "field_24",
            "field_28", "field_2c", "field_34", "field_3c", "field_44",
            "field_4c",
        ):
            self.assertEqual(getattr(header, name), 0, name)

    def test_alpha_constant(self):
        # 0.5 (0x3F000000) in every observed SHW chunk.
        header = ShwHeader.parse(chunk_of(fixtures.shw_chunk(alpha=1.0)))
        self.assertEqual(header.alpha, 1.0)

    def test_rejects_wrong_tag(self):
        blob = fixtures.shw_chunk()
        blob = b"XXXX" + blob[4:]
        with self.assertRaises(ValueError):
            ShwHeader.parse(chunk_of(blob))

    def test_rejects_truncated_chunk(self):
        with self.assertRaises(ValueError):
            ShwHeader.parse(chunk_of(fixtures.shw_chunk()[:HEADER_SIZE - 1]))

    def test_maybe_shw_header_returns_none_on_bad_input(self):
        self.assertIsNone(maybe_shw_header(chunk_of(b"nope" * 8)))
        self.assertIsNone(maybe_shw_header(chunk_of(b"SHW " + b"\x00" * 20)))

    def test_real_slot_14_shape(self):
        # pl021.pac slot 14 (E-036): field_10=0x2707, field_14=102,
        # pair=(0x0016, 0x0028), field_28=0, field_30=0x1E0.
        header = ShwHeader.parse(
            chunk_of(
                fixtures.shw_chunk(
                    field_10=0x2707,
                    field_14=102,
                    pair_20_0=0x0016,
                    pair_20_1=0x0028,
                    field_30=0x1E0,
                    field_38=0x460,
                    field_40=0x5A0,
                    field_48=0x700,
                )
            )
        )
        self.assertEqual(header.field_10, 0x2707)
        self.assertEqual(header.field_14, 102)
        self.assertEqual(header.pair_20_0, 0x0016)
        self.assertEqual(header.pair_20_1, 0x0028)
        self.assertEqual(header.field_28, 0)
        self.assertEqual(header.field_30, 0x1E0)

    def test_real_slot_24_shape(self):
        # pl021.pac slots 24/26 (byte-identical, E-036):
        # field_10=0x20101, field_14=0x315D8, pair=(0x0027, 0x0042),
        # field_28=0, field_30=0x60.
        header = ShwHeader.parse(
            chunk_of(
                fixtures.shw_chunk(
                    field_10=0x00020101,
                    field_14=0x000315D8,
                    pair_20_0=0x0027,
                    pair_20_1=0x0042,
                    field_30=0x60,
                    field_38=0x480,
                    field_40=0x690,
                    field_48=0x900,
                )
            )
        )
        self.assertEqual(header.field_10, 0x00020101)
        self.assertEqual(header.field_14, 0x000315D8)
        self.assertEqual(header.pair_20_0, 0x0027)
        self.assertEqual(header.pair_20_1, 0x0042)
        self.assertEqual(header.field_28, 0)
        self.assertEqual(header.field_30, 0x60)


if __name__ == "__main__":
    unittest.main()
