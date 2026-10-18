import _bootstrap  # noqa: F401
import struct
import unittest

from gow3 import eboot
from gow3.eboot import ElfError

EXEC_OFFSET = 0x200
EXEC_VADDR = 0x1000
DATA_OFFSET = 0x400
DATA_VADDR = 0x2000


def rip_lea(target: int, instruction_vaddr: int, rex: bool = True) -> bytes:
    """``lea``/``mov`` with a RIP-relative operand pointing at ``target``."""
    length = 7 if rex else 6
    disp = target - (instruction_vaddr + length)
    prefix = b"\x48" if rex else b""
    return prefix + b"\x8d\x3d" + struct.pack("<i", disp)


def rip_mov_rax(target: int, instruction_vaddr: int) -> bytes:
    length = 7
    disp = target - (instruction_vaddr + length)
    return b"\x48\x8b\x05" + struct.pack("<i", disp)


def synthetic_elf(code: bytes, payload: bytes = b"MSGS_TXT\x00\x00\x00") -> bytes:
    """Minimal 64-bit little-endian ELF with one exec and one data ``PT_LOAD``."""
    phnum = 2
    phoff = 0x40
    header = bytearray(0x40)
    header[0:4] = eboot.ELF_MAGIC
    header[4] = eboot.ELFCLASS64
    header[5] = eboot.ELFDATA2LSB
    header[6] = 1
    struct.pack_into("<H", header, 0x10, 2)          # e_type
    struct.pack_into("<H", header, 0x12, 0x3E)       # e_machine
    struct.pack_into("<I", header, 0x14, 1)
    struct.pack_into("<Q", header, 0x18, EXEC_VADDR)  # e_entry
    struct.pack_into("<Q", header, 0x20, phoff)
    struct.pack_into("<H", header, 0x34, 0x40)       # e_ehsize
    struct.pack_into("<H", header, 0x36, 56)         # e_phentsize
    struct.pack_into("<H", header, 0x38, phnum)

    def phdr(p_type, flags, offset, vaddr, filesz):
        return struct.pack(
            "<IIQQQQQQ", p_type, flags, offset, vaddr, vaddr, filesz, filesz, 0x1000
        )

    exec_ph = phdr(eboot.PT_LOAD, 0x5, EXEC_OFFSET, EXEC_VADDR, len(code))
    data_ph = phdr(eboot.PT_LOAD, 0x4, DATA_OFFSET, DATA_VADDR, len(payload))

    out = bytearray()
    out += header
    out += exec_ph
    out += data_ph
    out += b"\x00" * (EXEC_OFFSET - len(out))
    out += code
    out += b"\x00" * (DATA_OFFSET - len(out))
    out += payload
    return bytes(out)


class TestElfParsing(unittest.TestCase):
    def test_parses_entry_and_segments(self):
        code = rip_lea(DATA_VADDR, EXEC_VADDR)
        image = eboot.ElfImage.from_bytes(synthetic_elf(code))
        self.assertEqual(image.entry, EXEC_VADDR)
        self.assertEqual(len(image.segments), 2)
        self.assertEqual(len(image.executable_segments), 1)
        self.assertTrue(image.executable_segments[0].is_executable)

    def test_rejects_non_elf(self):
        with self.assertRaises(ElfError):
            eboot.ElfImage.from_bytes(b"not an elf" + b"\x00" * 64)

    def test_rejects_short_file(self):
        with self.assertRaises(ElfError):
            eboot.ElfImage.from_bytes(b"\x7fELF")

    def test_rejects_32_bit(self):
        blob = bytearray(synthetic_elf(b"\x90" * 8))
        blob[4] = 1
        with self.assertRaises(ElfError):
            eboot.ElfImage.from_bytes(bytes(blob))

    def test_rejects_big_endian(self):
        blob = bytearray(synthetic_elf(b"\x90" * 8))
        blob[5] = 2
        with self.assertRaises(ElfError):
            eboot.ElfImage.from_bytes(bytes(blob))


class TestAddressMapping(unittest.TestCase):
    def setUp(self):
        self.image = eboot.ElfImage.from_bytes(synthetic_elf(b"\x90" * 16))

    def test_round_trip(self):
        self.assertEqual(self.image.file_offset_to_vaddr(DATA_OFFSET), DATA_VADDR)
        self.assertEqual(self.image.vaddr_to_file_offset(DATA_VADDR), DATA_OFFSET)
        self.assertEqual(
            self.image.file_offset_to_vaddr(DATA_OFFSET + 3), DATA_VADDR + 3
        )

    def test_unmapped_returns_none(self):
        self.assertIsNone(self.image.file_offset_to_vaddr(0x10))
        self.assertIsNone(self.image.vaddr_to_file_offset(0x9999))

    def test_read_at_vaddr(self):
        self.assertEqual(self.image.read(DATA_VADDR, 4), b"MSGS")


class TestStringSearch(unittest.TestCase):
    def setUp(self):
        self.image = eboot.ElfImage.from_bytes(synthetic_elf(b"\x90" * 16))

    def test_find_all_returns_vaddrs(self):
        self.assertEqual(self.image.find_all(b"MSGS_TXT"), [DATA_VADDR])

    def test_absent_string(self):
        self.assertEqual(self.image.find_all(b"NOPE"), [])


class TestRipRelativeScan(unittest.TestCase):
    def test_rex_lea_found(self):
        image = eboot.ElfImage.from_bytes(
            synthetic_elf(rip_lea(DATA_VADDR, EXEC_VADDR))
        )
        self.assertEqual(image.rip_relative_references(DATA_VADDR), [EXEC_VADDR])

    def test_no_rex_lea_found(self):
        image = eboot.ElfImage.from_bytes(
            synthetic_elf(rip_lea(DATA_VADDR, EXEC_VADDR, rex=False))
        )
        self.assertEqual(image.rip_relative_references(DATA_VADDR), [EXEC_VADDR])

    def test_mov_rax_form_found(self):
        image = eboot.ElfImage.from_bytes(
            synthetic_elf(rip_mov_rax(DATA_VADDR, EXEC_VADDR))
        )
        self.assertEqual(image.rip_relative_references(DATA_VADDR), [EXEC_VADDR])

    def test_non_rip_relative_is_ignored(self):
        # `mov eax, [0x2000]` is absolute, not RIP-relative: ModRM 0x04/0x25.
        code = b"\x8b\x04\x25" + struct.pack("<I", DATA_VADDR)
        image = eboot.ElfImage.from_bytes(synthetic_elf(code))
        self.assertEqual(image.rip_relative_references(DATA_VADDR), [])

    def test_only_executable_segments_are_scanned(self):
        # The same instruction placed in the read-only data segment is not code.
        payload = rip_lea(DATA_VADDR + 8, DATA_VADDR) + b"AAAA"
        image = eboot.ElfImage.from_bytes(synthetic_elf(b"\x90" * 8, payload))
        self.assertEqual(image.rip_relative_references(DATA_VADDR + 8), [])

    def test_references_to_string(self):
        image = eboot.ElfImage.from_bytes(
            synthetic_elf(rip_lea(DATA_VADDR, EXEC_VADDR))
        )
        self.assertEqual(image.references_to_string(b"MSGS_TXT"), [EXEC_VADDR])

    def test_references_to_absent_string(self):
        image = eboot.ElfImage.from_bytes(
            synthetic_elf(rip_lea(DATA_VADDR, EXEC_VADDR))
        )
        self.assertEqual(image.references_to_string(b"NOPE"), [])


class TestReferenceContext(unittest.TestCase):
    CALL_TARGET = 0x1234

    def _mov_edx(self, imm):
        return b"\xba" + struct.pack("<I", imm)

    def _call(self, at_vaddr, target):
        rel = target - (at_vaddr + 5)
        return b"\xe8" + struct.pack("<i", rel)

    def test_decodes_length_argument_and_call(self):
        # The real shape observed at a `WAD_` reference: load the string, then
        # pass an explicit length (4) to a compare helper.
        lea = rip_lea(DATA_VADDR, EXEC_VADDR)          # 7 bytes
        mov_at = EXEC_VADDR + len(lea)
        call_at = mov_at + 5
        code = lea + self._mov_edx(4) + self._call(call_at, self.CALL_TARGET)
        image = eboot.ElfImage.from_bytes(synthetic_elf(code))

        context = image.reference_context(EXEC_VADDR)
        self.assertEqual([d.mnemonic for d in context], ["lea", "mov", "call"])
        self.assertEqual(context[0].operand, DATA_VADDR)
        self.assertEqual(context[0].length, 7)
        self.assertEqual(context[1].operand, 4)
        self.assertEqual(context[1].length, 5)
        self.assertEqual(context[2].operand, self.CALL_TARGET)
        self.assertEqual(context[2].length, 5)

    def test_context_stops_at_unknown_instruction(self):
        lea = rip_lea(DATA_VADDR, EXEC_VADDR)
        # `4c 89 f7` = mov rdi, r14 — outside the tiny decoded set, so stop.
        code = lea + b"\x4c\x89\xf7"
        image = eboot.ElfImage.from_bytes(synthetic_elf(code))
        context = image.reference_context(EXEC_VADDR)
        self.assertEqual(len(context), 1)
        self.assertEqual(context[0].mnemonic, "lea")

    def test_no_rex_lea_context(self):
        lea = rip_lea(DATA_VADDR, EXEC_VADDR, rex=False)  # 6 bytes
        image = eboot.ElfImage.from_bytes(
            synthetic_elf(lea + self._mov_edx(8))
        )
        context = image.reference_context(EXEC_VADDR)
        self.assertEqual(context[0].length, 6)
        self.assertEqual(context[0].operand, DATA_VADDR)
        self.assertEqual(context[1].operand, 8)

    def test_mov_r64_imm64_is_ten_bytes(self):
        imm = 0x1122334455667788
        code = b"\x48\xb8" + struct.pack("<Q", imm)
        image = eboot.ElfImage.from_bytes(synthetic_elf(code))
        context = image.reference_context(EXEC_VADDR)
        self.assertEqual(len(context), 1)
        self.assertEqual(context[0].length, 10)
        self.assertEqual(context[0].operand, imm)

    def test_non_rip_lea_is_not_decoded(self):
        # `lea eax, [0x2000]` (ModRM 0x05 without mod==00... here 0x04/0x25):
        # absolute addressing, outside the decoded RIP-relative form.
        code = b"\x8d\x04\x25" + struct.pack("<I", DATA_VADDR)
        image = eboot.ElfImage.from_bytes(synthetic_elf(code))
        self.assertEqual(image.reference_context(EXEC_VADDR), ())

    def test_context_empty_for_non_executable_address(self):
        image = eboot.ElfImage.from_bytes(synthetic_elf(b"\x90" * 8))
        self.assertEqual(image.reference_context(DATA_VADDR), ())

    def test_string_reference_contexts(self):
        lea = rip_lea(DATA_VADDR, EXEC_VADDR)
        code = lea + self._mov_edx(4)
        image = eboot.ElfImage.from_bytes(synthetic_elf(code))
        contexts = image.string_reference_contexts(b"MSGS_TXT")
        self.assertEqual(len(contexts), 1)
        self.assertEqual(contexts[0][1].operand, 4)

    def test_decoder_and_scanner_agree_on_rip_relative(self):
        # Guard against the decoder and the reference scanner diverging.
        for rex in (True, False):
            lea = rip_lea(DATA_VADDR, EXEC_VADDR, rex=rex)
            image = eboot.ElfImage.from_bytes(synthetic_elf(lea))
            self.assertEqual(image.rip_relative_references(DATA_VADDR),
                             [EXEC_VADDR])
            context = image.reference_context(EXEC_VADDR)
            self.assertEqual(len(context), 1)
            self.assertEqual(context[0].operand, DATA_VADDR)


if __name__ == "__main__":
    unittest.main()
