import _bootstrap  # noqa: F401
import struct
import unittest

from dmc3 import pe
from dmc3.pe import PeError

PE_OFFSET = 0x80
TEXT_OFFSET = 0x200
TEXT_RVA = 0x1000
DATA_OFFSET = 0x400
DATA_RVA = 0x2000
IMAGE_BASE = 0x140000000


def rip_lea(target: int, instruction_rva: int, rex: bool = True) -> bytes:
    """``lea``/``mov`` with a RIP-relative operand pointing at ``target``."""
    length = 7 if rex else 6
    disp = target - (instruction_rva + length)
    prefix = b"\x48" if rex else b""
    return prefix + b"\x8d\x3d" + struct.pack("<i", disp)


def rip_mov_rax(target: int, instruction_rva: int) -> bytes:
    length = 7
    disp = target - (instruction_rva + length)
    return b"\x48\x8b\x05" + struct.pack("<i", disp)


def _section(name, va, vsz, raw, rawsz, chars):
    return struct.pack(
        "<8sIIIIIIHHI", name.encode("latin-1"), vsz, va, rawsz, raw, 0, 0, 0, 0,
        chars,
    )


def synthetic_pe(code: bytes, payload: bytes = b"MSGS_TXT\x00\x00\x00") -> bytes:
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
    struct.pack_into("<I", out, optional + 16, TEXT_RVA)      # entry point
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


class TestPeParsing(unittest.TestCase):
    def test_parses_entry_image_base_and_sections(self):
        image = pe.PeImage.from_bytes(synthetic_pe(rip_lea(DATA_RVA, TEXT_RVA)))
        self.assertEqual(image.entry_rva, TEXT_RVA)
        self.assertEqual(image.image_base, IMAGE_BASE)
        self.assertEqual(len(image.sections), 2)
        self.assertEqual([s.name for s in image.sections], [".text", ".rdata"])
        self.assertEqual(len(image.executable_sections), 1)
        self.assertTrue(image.executable_sections[0].is_executable)

    def test_rejects_non_pe(self):
        with self.assertRaises(PeError):
            pe.PeImage.from_bytes(b"not a pe" + b"\x00" * 0x80)

    def test_rejects_short_file(self):
        with self.assertRaises(PeError):
            pe.PeImage.from_bytes(b"MZ")

    def test_rejects_32_bit(self):
        blob = bytearray(synthetic_pe(b"\x90" * 8))
        optional = PE_OFFSET + 4 + 20
        struct.pack_into("<H", blob, optional, 0x10B)
        with self.assertRaises(PeError):
            pe.PeImage.from_bytes(bytes(blob))

    def test_rejects_non_amd64(self):
        blob = bytearray(synthetic_pe(b"\x90" * 8))
        struct.pack_into("<H", blob, PE_OFFSET + 4, 0x14C)
        with self.assertRaises(PeError):
            pe.PeImage.from_bytes(bytes(blob))


class TestAddressMapping(unittest.TestCase):
    def setUp(self):
        self.image = pe.PeImage.from_bytes(synthetic_pe(b"\x90" * 16))

    def test_round_trip(self):
        self.assertEqual(self.image.file_offset_to_rva(DATA_OFFSET), DATA_RVA)
        self.assertEqual(self.image.rva_to_file_offset(DATA_RVA), DATA_OFFSET)
        self.assertEqual(
            self.image.file_offset_to_rva(DATA_OFFSET + 3), DATA_RVA + 3
        )

    def test_unmapped_returns_none(self):
        self.assertIsNone(self.image.file_offset_to_rva(0x10))
        self.assertIsNone(self.image.rva_to_file_offset(0x9999))

    def test_read_at_rva(self):
        self.assertEqual(self.image.read(DATA_RVA, 4), b"MSGS")


class TestStringSearch(unittest.TestCase):
    def setUp(self):
        self.image = pe.PeImage.from_bytes(synthetic_pe(b"\x90" * 16))

    def test_find_all_returns_rvas(self):
        self.assertEqual(self.image.find_all(b"MSGS_TXT"), [DATA_RVA])

    def test_absent_string(self):
        self.assertEqual(self.image.find_all(b"NOPE"), [])


class TestRipRelativeScan(unittest.TestCase):
    def test_rex_lea_found(self):
        image = pe.PeImage.from_bytes(
            synthetic_pe(rip_lea(DATA_RVA, TEXT_RVA))
        )
        self.assertEqual(image.rip_relative_references(DATA_RVA), [TEXT_RVA])

    def test_no_rex_lea_found(self):
        image = pe.PeImage.from_bytes(
            synthetic_pe(rip_lea(DATA_RVA, TEXT_RVA, rex=False))
        )
        self.assertEqual(image.rip_relative_references(DATA_RVA), [TEXT_RVA])

    def test_mov_rax_form_found(self):
        image = pe.PeImage.from_bytes(
            synthetic_pe(rip_mov_rax(DATA_RVA, TEXT_RVA))
        )
        self.assertEqual(image.rip_relative_references(DATA_RVA), [TEXT_RVA])

    def test_non_rip_relative_is_ignored(self):
        code = b"\x8b\x04\x25" + struct.pack("<I", DATA_RVA)
        image = pe.PeImage.from_bytes(synthetic_pe(code))
        self.assertEqual(image.rip_relative_references(DATA_RVA), [])

    def test_only_executable_sections_are_scanned(self):
        payload = rip_lea(DATA_RVA + 8, DATA_RVA) + b"AAAA"
        image = pe.PeImage.from_bytes(synthetic_pe(b"\x90" * 8, payload))
        self.assertEqual(image.rip_relative_references(DATA_RVA + 8), [])

    def test_references_to_string(self):
        image = pe.PeImage.from_bytes(
            synthetic_pe(rip_lea(DATA_RVA, TEXT_RVA))
        )
        self.assertEqual(image.references_to_string(b"MSGS_TXT"), [TEXT_RVA])

    def test_references_to_absent_string(self):
        image = pe.PeImage.from_bytes(
            synthetic_pe(rip_lea(DATA_RVA, TEXT_RVA))
        )
        self.assertEqual(image.references_to_string(b"NOPE"), [])


if __name__ == "__main__":
    unittest.main()
