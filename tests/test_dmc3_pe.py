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


class TestReferenceContext(unittest.TestCase):
    CALL_TARGET = 0x1234

    def _mov_edx(self, imm):
        return b"\xba" + struct.pack("<I", imm)

    def _call(self, at_rva, target):
        rel = target - (at_rva + 5)
        return b"\xe8" + struct.pack("<i", rel)

    def test_decodes_length_argument_and_call(self):
        # The shape observed at the real `.mot` reference site: load the
        # string, then pass an argument and call a helper.
        lea = rip_lea(DATA_RVA, TEXT_RVA)              # 7 bytes
        mov_at = TEXT_RVA + len(lea)
        call_at = mov_at + 5
        code = lea + self._mov_edx(4) + self._call(call_at, self.CALL_TARGET)
        image = pe.PeImage.from_bytes(synthetic_pe(code))

        context = image.reference_context(TEXT_RVA)
        self.assertEqual([d.mnemonic for d in context], ["lea", "mov", "call"])
        self.assertEqual(context[0].operand, DATA_RVA)
        self.assertEqual(context[0].length, 7)
        self.assertEqual(context[1].operand, 4)
        self.assertEqual(context[1].length, 5)
        self.assertEqual(context[2].operand, self.CALL_TARGET)
        self.assertEqual(context[2].length, 5)

    def test_context_stops_at_unknown_instruction(self):
        lea = rip_lea(DATA_RVA, TEXT_RVA)
        # `4c 89 f7` = mov rdi, r14 — outside the tiny decoded set, so stop.
        code = lea + b"\x4c\x89\xf7"
        image = pe.PeImage.from_bytes(synthetic_pe(code))
        context = image.reference_context(TEXT_RVA)
        self.assertEqual(len(context), 1)
        self.assertEqual(context[0].mnemonic, "lea")

    def test_no_rex_lea_context(self):
        lea = rip_lea(DATA_RVA, TEXT_RVA, rex=False)   # 6 bytes
        image = pe.PeImage.from_bytes(synthetic_pe(lea + self._mov_edx(8)))
        context = image.reference_context(TEXT_RVA)
        self.assertEqual(context[0].length, 6)
        self.assertEqual(context[0].operand, DATA_RVA)
        self.assertEqual(context[1].operand, 8)

    def test_mov_r64_imm64_is_ten_bytes(self):
        imm = 0x1122334455667788
        code = b"\x48\xb8" + struct.pack("<Q", imm)
        image = pe.PeImage.from_bytes(synthetic_pe(code))
        context = image.reference_context(TEXT_RVA)
        self.assertEqual(len(context), 1)
        self.assertEqual(context[0].length, 10)
        self.assertEqual(context[0].operand, imm)

    def test_non_rip_lea_is_not_decoded(self):
        # `lea eax, [0x2000]` (SIB absolute addressing) is outside the decoded
        # RIP-relative form.
        code = b"\x8d\x04\x25" + struct.pack("<I", DATA_RVA)
        image = pe.PeImage.from_bytes(synthetic_pe(code))
        self.assertEqual(image.reference_context(TEXT_RVA), ())

    def test_context_empty_for_non_executable_address(self):
        image = pe.PeImage.from_bytes(synthetic_pe(b"\x90" * 8))
        self.assertEqual(image.reference_context(DATA_RVA), ())

    def test_string_reference_contexts(self):
        lea = rip_lea(DATA_RVA, TEXT_RVA)
        code = lea + self._mov_edx(4)
        image = pe.PeImage.from_bytes(synthetic_pe(code))
        contexts = image.string_reference_contexts(b"MSGS_TXT")
        self.assertEqual(len(contexts), 1)
        self.assertEqual(contexts[0][1].operand, 4)

    def test_decoder_and_scanner_agree_on_rip_relative(self):
        # Guard against the decoder and the reference scanner diverging.
        for rex in (True, False):
            lea = rip_lea(DATA_RVA, TEXT_RVA, rex=rex)
            image = pe.PeImage.from_bytes(synthetic_pe(lea))
            self.assertEqual(image.rip_relative_references(DATA_RVA),
                             [TEXT_RVA])
            context = image.reference_context(TEXT_RVA)
            self.assertEqual(len(context), 1)
            self.assertEqual(context[0].operand, DATA_RVA)


def pool_entry(name: bytes, alignment: int = 8) -> bytes:
    """One pool entry: the name, a NUL, then padding to ``alignment``."""
    raw = name + b"\x00"
    step = (len(raw) + alignment - 1) // alignment * alignment
    return raw + b"\x00" * (step - len(raw))


class TestStringPool(unittest.TestCase):
    def test_read_cstring_stops_at_nul(self):
        payload = pool_entry(b"pl021.pac") + pool_entry(b"id516.pac")
        image = pe.PeImage.from_bytes(synthetic_pe(b"\x90" * 8, payload))
        self.assertEqual(image.read_cstring(DATA_RVA), b"pl021.pac")

    def test_read_cstring_none_without_nul(self):
        image = pe.PeImage.from_bytes(synthetic_pe(b"\x90" * 8, b"AAAA"))
        self.assertIsNone(image.read_cstring(DATA_RVA, limit=4))

    def test_read_cstring_none_for_unmapped_rva(self):
        image = pe.PeImage.from_bytes(synthetic_pe(b"\x90" * 8))
        self.assertIsNone(image.read_cstring(0x10))

    def test_walk_returns_names_and_rvas(self):
        payload = (pool_entry(b"pl021.pac")
                   + pool_entry(b"id516.pac")
                   + pool_entry(b"msg_eng.txt"))
        image = pe.PeImage.from_bytes(synthetic_pe(b"\x90" * 8, payload))
        entries = image.walk_string_pool(DATA_RVA)
        self.assertEqual(
            entries,
            ((DATA_RVA, "pl021.pac"),
             (DATA_RVA + 16, "id516.pac"),
             (DATA_RVA + 32, "msg_eng.txt")),
        )

    def test_long_name_advances_by_24_not_32(self):
        # A 16-char name (+NUL = 17 bytes) pads to 24, i.e. the pool aligns to
        # 8, not 16 -- the rule verified on the real image (E-076).
        payload = pool_entry(b"aa.pac") + pool_entry(b"m05_b00_msg_eng.txt") \
            + pool_entry(b"cc.pac")
        image = pe.PeImage.from_bytes(synthetic_pe(b"\x90" * 8, payload))
        entries = image.walk_string_pool(DATA_RVA)
        self.assertEqual([rva for rva, _ in entries],
                         [DATA_RVA, DATA_RVA + 8, DATA_RVA + 32])
        self.assertEqual(entries[1][1], "m05_b00_msg_eng.txt")

    def test_walk_stops_at_non_printable_byte(self):
        payload = pool_entry(b"aa.pac") + b"\x01\x00\x00\x00\x00\x00\x00\x00"
        image = pe.PeImage.from_bytes(synthetic_pe(b"\x90" * 8, payload))
        self.assertEqual(image.walk_string_pool(DATA_RVA),
                         ((DATA_RVA, "aa.pac"),))

    def test_walk_stops_at_zero_run(self):
        payload = pool_entry(b"aa.pac") + b"\x00" * 8
        image = pe.PeImage.from_bytes(synthetic_pe(b"\x90" * 8, payload))
        self.assertEqual(image.walk_string_pool(DATA_RVA),
                         ((DATA_RVA, "aa.pac"),))

    def test_walk_stops_at_section_end(self):
        payload = pool_entry(b"aa.pac")
        image = pe.PeImage.from_bytes(synthetic_pe(b"\x90" * 8, payload))
        self.assertEqual(image.walk_string_pool(DATA_RVA),
                         ((DATA_RVA, "aa.pac"),))

    def test_walk_honours_limit(self):
        payload = pool_entry(b"aa.pac") + pool_entry(b"bb.pac")
        image = pe.PeImage.from_bytes(synthetic_pe(b"\x90" * 8, payload))
        self.assertEqual(len(image.walk_string_pool(DATA_RVA, limit=1)), 1)

    def test_walk_rejects_zero_alignment(self):
        image = pe.PeImage.from_bytes(synthetic_pe(b"\x90" * 8))
        with self.assertRaises(PeError):
            image.walk_string_pool(DATA_RVA, alignment=0)


class TestAbsolutePointers(unittest.TestCase):
    """E-077: the engine reaches its asset-name table through stored absolute
    pointers, which the RIP-relative scanner cannot see."""

    @staticmethod
    def _ptr(target_rva: int) -> bytes:
        return struct.pack("<Q", IMAGE_BASE + target_rva)

    def test_finds_a_stored_absolute_pointer(self):
        image = pe.PeImage.from_bytes(synthetic_pe(b"\x90" * 8, self._ptr(DATA_RVA)))
        self.assertEqual(image.absolute_pointers_to(DATA_RVA), [DATA_RVA])

    def test_reports_every_occurrence(self):
        payload = self._ptr(DATA_RVA) + b"\x00" * 8 + self._ptr(DATA_RVA)
        image = pe.PeImage.from_bytes(synthetic_pe(b"\x90" * 8, payload))
        self.assertEqual(image.absolute_pointers_to(DATA_RVA),
                         [DATA_RVA, DATA_RVA + 16])

    def test_absent_pointer_returns_empty(self):
        image = pe.PeImage.from_bytes(synthetic_pe(b"\x90" * 8))
        self.assertEqual(image.absolute_pointers_to(DATA_RVA), [])

    def test_bare_rva_literal_is_not_an_absolute_pointer(self):
        # The form the engine uses as an addressing displacement is a 4-byte
        # RVA, not an 8-byte absolute pointer, and must not be reported as one.
        payload = struct.pack("<I", DATA_RVA) + b"\x00" * 4
        image = pe.PeImage.from_bytes(synthetic_pe(b"\x90" * 8, payload))
        self.assertEqual(image.absolute_pointers_to(DATA_RVA), [])


class TestPointerArray(unittest.TestCase):
    def test_walk_returns_target_rvas_until_non_pointer(self):
        targets = [DATA_RVA + 0x40, DATA_RVA + 0x48]
        payload = (b"".join(struct.pack("<Q", IMAGE_BASE + t) for t in targets)
                   + b"\x00" * 8 + b"\x00" * 0x40)
        image = pe.PeImage.from_bytes(synthetic_pe(b"\x90" * 8, payload))
        self.assertEqual(image.pointer_array(DATA_RVA), tuple(targets))

    def test_walk_stops_at_out_of_image_value(self):
        payload = struct.pack("<Q", IMAGE_BASE + DATA_RVA) + struct.pack("<Q", 0x1234)
        image = pe.PeImage.from_bytes(synthetic_pe(b"\x90" * 8, payload))
        self.assertEqual(image.pointer_array(DATA_RVA), (DATA_RVA,))

    def test_walk_honours_limit(self):
        payload = struct.pack("<Q", IMAGE_BASE + DATA_RVA) * 3
        image = pe.PeImage.from_bytes(synthetic_pe(b"\x90" * 8, payload))
        self.assertEqual(len(image.pointer_array(DATA_RVA, limit=2)), 2)

    def test_walk_stops_at_unmapped_start(self):
        image = pe.PeImage.from_bytes(synthetic_pe(b"\x90" * 8))
        self.assertEqual(image.pointer_array(0x10), ())

    def test_rejects_non_positive_stride(self):
        image = pe.PeImage.from_bytes(synthetic_pe(b"\x90" * 8))
        with self.assertRaises(PeError):
            image.pointer_array(DATA_RVA, stride=0)


class TestPointerAt(unittest.TestCase):
    """E-078: a single absolute pointer, as the asset dispatcher reads it."""

    @staticmethod
    def _ptr(target_rva: int) -> bytes:
        return struct.pack("<Q", IMAGE_BASE + target_rva)

    def test_reads_a_single_pointer(self):
        image = pe.PeImage.from_bytes(synthetic_pe(b"\x90" * 8, self._ptr(DATA_RVA)))
        self.assertEqual(image.pointer_at(DATA_RVA), DATA_RVA)

    def test_reads_at_a_stride(self):
        payload = b"".join(
            self._ptr(DATA_RVA + 0x18 + 8 * i) for i in range(3)
        ) + b"\x00" * 0x40
        image = pe.PeImage.from_bytes(synthetic_pe(b"\x90" * 8, payload))
        self.assertEqual(image.pointer_at(DATA_RVA + 16), DATA_RVA + 0x28)

    def test_zero_word_is_not_a_pointer(self):
        image = pe.PeImage.from_bytes(synthetic_pe(b"\x90" * 8, b"\x00" * 8))
        self.assertIsNone(image.pointer_at(DATA_RVA))

    def test_unmapped_rva_is_none(self):
        image = pe.PeImage.from_bytes(synthetic_pe(b"\x90" * 8))
        self.assertIsNone(image.pointer_at(0x10))


if __name__ == "__main__":
    unittest.main()
