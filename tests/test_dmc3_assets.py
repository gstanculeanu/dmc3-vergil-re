import _bootstrap  # noqa: F401
import struct
import unittest

from dmc3 import assets, pe


PE_OFFSET = 0x80
TEXT_OFFSET = 0x200
TEXT_RVA = 0x1000
DATA_OFFSET = 0x400
DATA_RVA = 0x2000
IMAGE_BASE = 0x140000000


def _section(name, va, vsz, raw, rawsz, chars):
    return struct.pack(
        "<8sIIIIIIHHI", name.encode("latin-1"), vsz, va, rawsz, raw, 0, 0, 0, 0,
        chars,
    )


def synthetic_pe(code: bytes, payload: bytes) -> bytes:
    """Minimal 64-bit PE with one executable and one read-only section."""
    out = bytearray(0x400 + len(payload))
    out[0:2] = pe.MZ_MAGIC
    struct.pack_into("<I", out, 0x3C, PE_OFFSET)
    out[PE_OFFSET:PE_OFFSET + 4] = pe.PE_SIGNATURE
    coff = PE_OFFSET + 4
    struct.pack_into("<HHIIIHH", out, coff, pe.MACHINE_AMD64, 2, 0, 0, 0, 0xF0,
                     0x22)
    optional = coff + 20
    struct.pack_into("<H", out, optional, pe.PE32_PLUS_MAGIC)
    struct.pack_into("<I", out, optional + 16, TEXT_RVA)
    struct.pack_into("<Q", out, optional + 24, IMAGE_BASE)
    table = optional + 0xF0
    out[table:table + 40] = _section(
        ".text", TEXT_RVA, len(code), TEXT_OFFSET, len(code),
        pe.IMAGE_SCN_CNT_CODE | pe.IMAGE_SCN_MEM_EXECUTE)
    out[table + 40:table + 80] = _section(
        ".rdata", DATA_RVA, len(payload), DATA_OFFSET, len(payload),
        pe.IMAGE_SCN_CNT_INITIALIZED_DATA)
    out[TEXT_OFFSET:TEXT_OFFSET + len(code)] = code
    out[DATA_OFFSET:DATA_OFFSET + len(payload)] = payload
    return bytes(out)


def name_table_payload(names) -> bytes:
    """A pointer array at DATA_RVA followed by the NUL-terminated names."""
    count = len(names)
    strings = b""
    offsets = []
    for name in names:
        offsets.append(count * 8 + len(strings))
        strings += name.encode("ascii") + b"\x00"
    table = b"".join(
        struct.pack("<Q", IMAGE_BASE + DATA_RVA + offset) for offset in offsets
    )
    return table + strings


class TestAssetCategories(unittest.TestCase):
    """E-078: the engine's four name categories, split by their base offsets."""

    def test_default_layout_matches_the_engine(self):
        categories = assets.asset_categories()
        self.assertEqual(len(categories), 4)
        self.assertEqual(
            [category.base_rva for category in categories],
            list(assets.CATEGORY_BASES),
        )
        self.assertEqual(
            [category.count for category in categories], [3866, 154, 19, 19]
        )
        self.assertEqual(assets.ASSET_DISPATCH_RVA, 0x33480)

    def test_counts_are_derived_from_the_extent(self):
        categories = assets.asset_categories(
            bases=(0x2000,), ends=(0x2000 + 3 * 8,)
        )
        self.assertEqual(categories[0].count, 3)

    def test_address_of_is_pointer_sized(self):
        categories = assets.asset_categories(
            bases=(0x2000,), ends=(0x2000 + 3 * 8,)
        )
        self.assertEqual(categories[0].address_of(2), 0x2000 + 16)
        with self.assertRaises(IndexError):
            categories[0].address_of(3)

    def test_rejects_mismatched_layout(self):
        with self.assertRaises(ValueError):
            assets.asset_categories(bases=(0x2000,), ends=(0x2008, 0x2010))

    def test_rejects_reversed_extent(self):
        with self.assertRaises(ValueError):
            assets.asset_categories(bases=(0x2000,), ends=(0x1000,))


class TestResolveName(unittest.TestCase):
    def setUp(self):
        self.names = ["pl021.pac", "id4516.pac", "endof.afs"]
        payload = name_table_payload(self.names)
        self.image = pe.PeImage.from_bytes(
            synthetic_pe(b"\x90" * 8, payload)
        )
        self.categories = assets.asset_categories(
            bases=(DATA_RVA,), ends=(DATA_RVA + len(self.names) * 8,)
        )

    def test_resolves_each_slot(self):
        for index, expected in enumerate(self.names):
            self.assertEqual(
                assets.resolve_name(self.image, 0, index, self.categories),
                expected,
            )

    def test_slot_of_zero_pointer_resolves_to_none(self):
        payload = b"\x00" * 8 + b"id4516.pac\x00"
        image = pe.PeImage.from_bytes(synthetic_pe(b"\x90" * 8, payload))
        categories = assets.asset_categories(bases=(DATA_RVA,), ends=(DATA_RVA + 8,))
        self.assertIsNone(assets.resolve_name(image, 0, 0, categories))

    def test_rejects_out_of_range_category(self):
        with self.assertRaises(IndexError):
            assets.resolve_name(self.image, 9, 0, self.categories)

    def test_rejects_out_of_range_index(self):
        with self.assertRaises(IndexError):
            assets.resolve_name(self.image, 0, 3, self.categories)


class TestAssetEntry(unittest.TestCase):
    """E-078: the 0x88-byte head the dispatcher's caller reads."""

    @staticmethod
    def _entry(entry_type, word_04, word_06) -> bytes:
        raw = bytearray(assets.ASSET_ENTRY_SIZE)
        struct.pack_into("<I", raw, assets.ENTRY_TYPE_OFFSET, entry_type)
        struct.pack_into("<H", raw, assets.ENTRY_WORD4_OFFSET, word_04)
        struct.pack_into("<H", raw, assets.ENTRY_WORD6_OFFSET, word_06)
        return bytes(raw)

    def test_type_one_yields_a_name_reference(self):
        entry = assets.parse_asset_entry(self._entry(1, 0, 8))
        self.assertTrue(entry.is_name_ref)
        self.assertEqual(entry.name_ref, (0, 8))

    def test_other_types_are_not_name_references(self):
        for entry_type in (2, 3, 0):
            entry = assets.parse_asset_entry(self._entry(entry_type, 5, 6))
            self.assertFalse(entry.is_name_ref)
            self.assertIsNone(entry.name_ref)

    def test_reads_at_an_offset(self):
        blob = b"\xAA" * 16 + self._entry(1, 1, 2)
        entry = assets.parse_asset_entry(blob, offset=16)
        self.assertEqual(entry.name_ref, (1, 2))

    def test_rejects_a_short_buffer(self):
        with self.assertRaises(ValueError):
            assets.parse_asset_entry(b"\x00" * 4)


if __name__ == "__main__":
    unittest.main()
