import _bootstrap  # noqa: F401  (adds ../tools to sys.path)
import struct
import unittest

import fixtures
from dmc3 import Chunk, ModBodyPrefix, ModHeader
from dmc3.mod import (
    BODY_PREFIX_SIZE,
    HEADER_SIZE,
    maybe_mod_body_prefix,
    maybe_mod_header,
)


def chunk_of(payload: bytes) -> Chunk:
    return Chunk(index=0, offset=0, span=len(payload), data=payload)


class TestModHeader(unittest.TestCase):
    def test_parses_observed_layout(self):
        header = ModHeader.parse(chunk_of(fixtures.mod_chunk()))
        self.assertEqual(header.scale, fixtures.mod_chunk.__defaults__[0])
        self.assertEqual(header.field_08, 0)
        self.assertEqual(header.field_0c, 0)
        self.assertEqual(header.field_10, 0x10101)
        self.assertEqual(header.field_14, 0xAF258)
        self.assertEqual(header.field_18, 0)
        self.assertEqual(header.field_1c, 0)
        self.assertEqual(header.field_20, 0x160)

    def test_header_size_is_0x24(self):
        self.assertEqual(HEADER_SIZE, 0x24)

    def test_scale_constant(self):
        # 285/286 real MOD chunks carry 1.0099… (0x3F8147AE); one carries 1.0.
        header = ModHeader.parse(chunk_of(fixtures.mod_chunk(scale=1.0)))
        self.assertEqual(header.scale, 1.0)

    def test_rejects_wrong_tag(self):
        blob = fixtures.mod_chunk()
        blob = b"XXXX" + blob[4:]
        with self.assertRaises(ValueError):
            ModHeader.parse(chunk_of(blob))

    def test_rejects_truncated_chunk(self):
        blob = fixtures.mod_chunk(body=b"\x00" * 100)
        with self.assertRaises(ValueError):
            ModHeader.parse(chunk_of(blob[:HEADER_SIZE - 1]))

    def test_maybe_mod_header_returns_none_on_bad_input(self):
        self.assertIsNone(maybe_mod_header(chunk_of(b"nope" * 8)))
        self.assertIsNone(maybe_mod_header(chunk_of(b"MOD " + b"\x00" * 20)))

    def test_body_follows_header(self):
        body = bytes(range(32))
        header = ModHeader.parse(chunk_of(fixtures.mod_chunk(body=body)))
        raw = chunk_of(fixtures.mod_chunk(body=body)).data
        self.assertEqual(raw[HEADER_SIZE:HEADER_SIZE + len(body)], body)

    def test_default_fields_match_real_chunks(self):
        # Observed values on pl021.pac slots 1/12/23/25 (E-030):
        # slot 1: +0x10=0x103180B, +0x14=0xAFE12, +0x20=0x29B30
        header = ModHeader.parse(
            chunk_of(
                fixtures.mod_chunk(
                    field_10=0x103180B, field_14=0xAFE12, field_20=0x29B30
                )
            )
        )
        self.assertEqual(header.field_10, 0x103180B)
        self.assertEqual(header.field_14, 0xAFE12)
        self.assertEqual(header.field_20, 0x29B30)


class TestModBodyPrefix(unittest.TestCase):
    """Decoded MOD payload body prefix (E-031). All meanings [UNKNOWN]; only the
    observed bytes/values are asserted."""

    def test_parses_slot_23_shape(self):
        # pl021.pac slot 23: marker=0x8001, count=182, field_24=128,
        # field_2c=0x00120002, vector≈(-0.196, 0, 42.07, 73.57), repeat=182
        prefix = ModBodyPrefix.parse(fixtures.mod_body())
        self.assertEqual(prefix.marker, 0x8001)
        self.assertEqual(prefix.count, 182)
        self.assertEqual(prefix.field_24, 128)
        self.assertEqual(prefix.field_2c, 0x00120002)
        self.assertAlmostEqual(prefix.vector[0], -0.196165, places=5)
        self.assertAlmostEqual(prefix.vector[1], 0.0, places=5)
        self.assertAlmostEqual(prefix.vector[2], 42.0706, places=4)
        self.assertAlmostEqual(prefix.vector[3], 73.5689, places=4)
        self.assertEqual(prefix.repeat, 182)

    def test_repeat_equals_count_for_duplicated_mesh(self):
        # Slots 23/25 are byte-identical and repeat == count there (E-031).
        prefix = ModBodyPrefix.parse(fixtures.mod_body(count=182, repeat=182))
        self.assertEqual(prefix.repeat, prefix.count)

    def test_repeat_independent_of_count(self):
        # Slot 1: count=474 but body+0x5C reads 0x01418002 (E-031).
        prefix = ModBodyPrefix.parse(
            fixtures.mod_body(count=474, repeat=0x01418002)
        )
        self.assertEqual(prefix.count, 474)
        self.assertEqual(prefix.repeat, 0x01418002)

    def test_slot_1_shape(self):
        # pl021.pac slot 1: marker=0x8001, count=474, field_24=768.
        prefix = ModBodyPrefix.parse(
            fixtures.mod_body(count=474, field_24=768, repeat=0x01418002)
        )
        self.assertEqual(prefix.marker, 0x8001)
        self.assertEqual(prefix.count, 474)
        self.assertEqual(prefix.field_24, 768)

    def test_marker_constant(self):
        # 0x8001 observed in all four pl021.pac MOD chunks (E-031).
        for count in (474, 300, 182):
            self.assertEqual(
                ModBodyPrefix.parse(fixtures.mod_body(count=count)).marker,
                0x8001,
            )

    def test_prefix_size(self):
        self.assertEqual(BODY_PREFIX_SIZE, 0x60)

    def test_rejects_short_body(self):
        with self.assertRaises(ValueError):
            ModBodyPrefix.parse(fixtures.mod_body()[:BODY_PREFIX_SIZE - 1])
        self.assertIsNone(maybe_mod_body_prefix(b"\x00" * 10))


if __name__ == "__main__":
    unittest.main()
