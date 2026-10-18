"""Read the DMC3 HD Collection ``dmc3.exe`` and find code that references a string.

The DMC3 formats (``MOD `` mesh, ``MOT\\0`` motion, ``SHW `` shader) have been
decoded from bytes up to the point where **engine ground truth** is required to
assign field meanings (evidence E-050, E-051). The retail game ships its own
x86-64 code at ``dmc3.exe`` in the install root, so the engine that consumes those
bytes is available locally and can be read read-only.

This module is the DMC3 analogue of :mod:`gow3.eboot`:

* :class:`PeImage` parses a 64-bit PE (PE32+, machine ``0x8664``) and maps **file
  offsets to RVAs** and back through its section table. The image base is recorded
  but does not enter the mapping: a RIP-relative displacement is independent of
  the base, so RVA math is exact.
* :meth:`PeImage.find_all` finds the RVA of every occurrence of a byte string.
* :meth:`PeImage.rip_relative_references` scans the executable sections for
  ``lea``/``mov`` with a RIP-relative memory operand (``(modrm & 0xC7) == 0x05``)
  and returns the instructions that reference a target RVA.
* :meth:`PeImage.reference_context` decodes a **small, documented set of forms**
  (RIP-relative ``lea``/``mov``, ``mov r32, imm32`` / ``mov r64, imm64`` and
  ``call rel32``) starting at a reference site, so the numeric constants passed
  alongside a string can be read without a general disassembler.
* :meth:`PeImage.walk_string_pool` walks the image's NUL-terminated,
  8-byte-aligned name pool (E-076), which is where the engine keeps its asset
  names (``pl021.pac``, ``pl021_00_0.pac``, …).
* :meth:`PeImage.absolute_pointers_to` and :meth:`PeImage.pointer_array` find
  stored **8-byte absolute pointers** (``image_base + rva``) and walk a
  contiguous array of them. Such pointers are invisible to the RIP-relative
  scanner; the engine's asset-name table is one of them (E-077).

Like the ELF scanner this is a **byte-pattern scan, not a disassembler**; a hit is
meaningful when its target is a known string RVA, which is how the tool is used.

Nothing here writes to the game installation, and no game bytes are stored in the
repository.
"""

from __future__ import annotations

import os
import struct
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

MZ_MAGIC = b"MZ"
PE_SIGNATURE = b"PE\x00\x00"
PE32_PLUS_MAGIC = 0x20B
MACHINE_AMD64 = 0x8664

IMAGE_SCN_CNT_CODE = 0x00000020
IMAGE_SCN_CNT_INITIALIZED_DATA = 0x00000040
IMAGE_SCN_MEM_EXECUTE = 0x20000000

LEA = 0x8D
MOV = 0x8B
RIP_RELATIVE_MASK = 0xC7
RIP_RELATIVE_RM = 0x05
REX_PREFIX_MIN = 0x40
REX_PREFIX_MAX = 0x4F
REX_W = 0x08
MOV_R32_IMM32_MIN = 0xB8   # B8+r: mov r32, imm32 (B8+rd with REX.W is imm64)
MOV_R32_IMM32_MAX = 0xBF
CALL_REL32 = 0xE8

# String-pool walking. The engine's `.rdata` name pool is a sequence of
# NUL-terminated printable-ASCII strings, each padded so the next one starts on
# an 8-byte boundary (verified against the real image, E-076).
STRING_ALIGNMENT = 8
STRING_MAX_LENGTH = 0x100
STRING_POOL_LIMIT = 4096
PRINTABLE_MIN = 0x20
PRINTABLE_MAX = 0x7E

# Absolute (base-relocated) pointers. A PE64 image stores a global ``&symbol``
# as an 8-byte little-endian ``image_base + rva``; such a pointer is invisible to
# the RIP-relative scanner because it carries no displacement (E-077).
POINTER_SIZE = 8


class PeError(ValueError):
    """Raised when a file is not a usable 64-bit PE image."""


@dataclass(frozen=True)
class PeSection:
    """One PE section header, in file order.

    ``virtual_address`` is an RVA (relative to the image base), not a VA.
    ``virtual_size`` is the in-memory size; ``raw_size`` the bytes on disk. The
    two differ, e.g. the uninitialised tail of ``.data`` is not stored.
    """

    index: int
    name: str
    virtual_address: int
    virtual_size: int
    raw_offset: int
    raw_size: int
    characteristics: int

    @property
    def is_executable(self) -> bool:
        return bool(self.characteristics & IMAGE_SCN_MEM_EXECUTE)

    @property
    def is_code(self) -> bool:
        return bool(self.characteristics & IMAGE_SCN_CNT_CODE)

    def contains_offset(self, offset: int) -> bool:
        """True when a **file offset** has stored bytes in this section."""
        return self.raw_offset <= offset < self.raw_offset + self.raw_size

    def contains_rva(self, rva: int) -> bool:
        """True when an **RVA** is stored in this section's raw bytes."""
        return 0 <= rva - self.virtual_address < self.raw_size


@dataclass(frozen=True)
class DecodedInstruction:
    """One instruction decoded in the limited set of forms a string reference
    site uses (see :func:`_decode_instruction`).

    ``operand`` is the instruction's absolute operand: an immediate for
    ``mov r32, imm32`` / ``mov r64, imm64``, or the resolved target RVA for a
    RIP-relative ``lea``/``mov`` and for a ``call rel32``. Only the instruction
    *length* is trusted to keep stepping; no general disassembly is claimed.
    """

    address: int
    length: int
    mnemonic: str
    operand: int


@dataclass(frozen=True)
class PeImage:
    """A parsed 64-bit PE with file-offset <-> RVA mapping."""

    data: bytes
    image_base: int
    entry_rva: int
    sections: Tuple[PeSection, ...]

    # -- construction ---------------------------------------------------
    @classmethod
    def from_bytes(cls, data: bytes) -> "PeImage":
        if len(data) < 0x40 or data[:2] != MZ_MAGIC:
            raise PeError("not a PE (missing MZ signature)")
        pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
        if pe_offset + 24 > len(data) or data[pe_offset:pe_offset + 4] != PE_SIGNATURE:
            raise PeError("not a PE (missing PE\\0\\0 signature)")

        coff = pe_offset + 4
        machine, section_count = struct.unpack_from("<HH", data, coff)
        if machine != MACHINE_AMD64:
            raise PeError(f"not a 64-bit x86-64 PE (machine 0x{machine:04X})")
        size_of_optional = struct.unpack_from("<H", data, coff + 16)[0]
        optional = coff + 20
        if optional + size_of_optional > len(data):
            raise PeError("optional header runs past end of file")
        magic = struct.unpack_from("<H", data, optional)[0]
        if magic != PE32_PLUS_MAGIC:
            raise PeError(f"not a PE32+ image (magic 0x{magic:04X})")

        entry_rva = struct.unpack_from("<I", data, optional + 16)[0]
        image_base = struct.unpack_from("<Q", data, optional + 24)[0]

        table = optional + size_of_optional
        if table + section_count * 40 > len(data):
            raise PeError("section table runs past end of file")
        sections: List[PeSection] = []
        for index in range(section_count):
            at = table + index * 40
            name = data[at:at + 8].rstrip(b"\x00").decode("latin-1")
            (virtual_size, virtual_address, raw_size, raw_offset) = (
                struct.unpack_from("<IIII", data, at + 8)
            )
            characteristics = struct.unpack_from("<I", data, at + 36)[0]
            sections.append(
                PeSection(
                    index=index, name=name, virtual_address=virtual_address,
                    virtual_size=virtual_size, raw_offset=raw_offset,
                    raw_size=raw_size, characteristics=characteristics,
                )
            )
        return cls(data=data, image_base=image_base, entry_rva=entry_rva,
                   sections=tuple(sections))

    @classmethod
    def from_path(cls, path: str | os.PathLike[str]) -> "PeImage":
        with open(path, "rb") as handle:
            return cls.from_bytes(handle.read())

    # -- address mapping ------------------------------------------------
    @property
    def executable_sections(self) -> Tuple[PeSection, ...]:
        return tuple(section for section in self.sections if section.is_executable)

    def file_offset_to_rva(self, offset: int) -> Optional[int]:
        """RVA of a **file offset**, or ``None`` when no section stores it."""
        for section in self.sections:
            if section.contains_offset(offset):
                return section.virtual_address + (offset - section.raw_offset)
        return None

    def rva_to_file_offset(self, rva: int) -> Optional[int]:
        """File offset of a stored **RVA**, or ``None`` when it is uninitialised."""
        for section in self.sections:
            if section.contains_rva(rva):
                return section.raw_offset + (rva - section.virtual_address)
        return None

    def read(self, rva: int, size: int) -> bytes:
        """Bytes at an RVA (from the file image)."""
        offset = self.rva_to_file_offset(rva)
        if offset is None:
            raise PeError(f"rva 0x{rva:X} is not stored in the image")
        return self.data[offset:offset + size]

    # -- string pools ---------------------------------------------------
    def section_of_rva(self, rva: int) -> Optional[PeSection]:
        """The section whose stored bytes contain ``rva``, or ``None``."""
        for section in self.sections:
            if section.contains_rva(rva):
                return section
        return None

    def read_cstring(self, rva: int,
                     limit: int = STRING_MAX_LENGTH) -> Optional[bytes]:
        """A NUL-terminated string at ``rva``, without its NUL.

        Returns ``None`` when ``rva`` is not stored, when no NUL is found within
        ``limit`` bytes, or when the read would leave the containing section.
        """
        section = self.section_of_rva(rva)
        if section is None or limit <= 0:
            return None
        offset = section.raw_offset + (rva - section.virtual_address)
        available = min(limit, section.raw_offset + section.raw_size - offset)
        if available <= 0:
            return None
        raw = self.data[offset:offset + available]
        nul = raw.find(b"\x00")
        if nul < 0:
            return None
        return raw[:nul]

    def walk_string_pool(self, rva: int, alignment: int = STRING_ALIGNMENT,
                         limit: int = STRING_POOL_LIMIT
                         ) -> Tuple[Tuple[int, str], ...]:
        """Walk a string pool as ``(rva, name)`` pairs.

        Each entry is a NUL-terminated **printable ASCII** string, padded so the
        next entry begins on an ``alignment``-byte boundary. The walk stops at
        the first entry that is empty, holds a byte outside printable ASCII, or
        starts outside the mapped sections — so it is a *prefix* of the pool, not
        a guess. This is the shape of the engine's asset-name pool (E-076).
        """
        if alignment <= 0:
            raise PeError("alignment must be positive")
        entries: List[Tuple[int, str]] = []
        at = rva
        while len(entries) < limit:
            if self.section_of_rva(at) is None:
                break
            raw = self.read_cstring(at)
            if not raw:
                break
            if any(byte < PRINTABLE_MIN or byte > PRINTABLE_MAX for byte in raw):
                break
            entries.append((at, raw.decode("ascii")))
            step = len(raw) + 1
            step = (step + alignment - 1) // alignment * alignment
            if step <= 0:
                break
            at += step
        return tuple(entries)

    # -- absolute pointer tables ----------------------------------------
    def absolute_pointers_to(self, target_rva: int) -> List[int]:
        """RVAs of every stored 8-byte absolute pointer to ``target_rva``.

        A PE64 image writes a global ``&symbol`` as a little-endian absolute
        virtual address (``image_base + rva``). That form is **invisible to**
        :meth:`rip_relative_references`, which only sees RIP-relative operands,
        so a table of ``char*`` into the string pool (E-077) has to be found by
        scanning stored section bytes for the value.
        """
        needle = struct.pack("<Q", self.image_base + target_rva)
        found: List[int] = []
        for section in self.sections:
            chunk = self.data[section.raw_offset:
                             section.raw_offset + section.raw_size]
            start = 0
            while True:
                at = chunk.find(needle, start)
                if at < 0:
                    break
                found.append(section.virtual_address + at)
                start = at + 1
        return sorted(found)

    def pointer_array(self, rva: int, limit: int = STRING_POOL_LIMIT,
                      stride: int = POINTER_SIZE) -> Tuple[int, ...]:
        """Walk a contiguous run of 8-byte absolute pointers, return targets.

        Returns the **target RVAs** of the run. The walk stops at the first word
        that is not an in-image absolute pointer — a zero, an out-of-image
        value, or an unmapped start — so it is a *prefix*, never a guess. This is
        the shape of the engine's asset-name table at ``.data`` ``0x553050``
        (E-077): each entry is a ``char*`` into the E-076 name pool.
        """
        if stride <= 0:
            raise PeError("stride must be positive")
        targets: List[int] = []
        at = rva
        while len(targets) < limit:
            if self.section_of_rva(at) is None:
                break
            value = struct.unpack("<Q", self.read(at, POINTER_SIZE))[0]
            target = value - self.image_base
            if self.section_of_rva(target) is None:
                break
            targets.append(target)
            at += stride
        return tuple(targets)

    # -- string and reference search ------------------------------------
    def find_all(self, needle: bytes) -> List[int]:
        """RVAs of every occurrence of ``needle`` in stored section bytes."""
        found: List[int] = []
        start = 0
        while True:
            at = self.data.find(needle, start)
            if at < 0:
                break
            rva = self.file_offset_to_rva(at)
            if rva is not None:
                found.append(rva)
            start = at + 1
        return found

    def _scan_rip_relative(self) -> Dict[int, int]:
        """Map every ``lea``/``mov`` instruction RVA to its target RVA."""
        references: Dict[int, int] = {}
        for section in self.executable_sections:
            code = self.data[section.raw_offset:
                             section.raw_offset + section.raw_size]
            limit = len(code) - 6
            index = 0
            while index <= limit:
                cursor = index
                if REX_PREFIX_MIN <= code[cursor] <= REX_PREFIX_MAX:
                    cursor += 1
                if cursor + 6 > len(code):
                    index += 1
                    continue
                if (
                    code[cursor] in (LEA, MOV)
                    and (code[cursor + 1] & RIP_RELATIVE_MASK) == RIP_RELATIVE_RM
                ):
                    disp = struct.unpack_from("<i", code, cursor + 2)[0]
                    insn_len = (cursor - index) + 6
                    instruction = section.virtual_address + index
                    references[instruction] = instruction + insn_len + disp
                    index += insn_len
                    continue
                index += 1
        return references

    def rip_relative_references(self, target_rva: int) -> List[int]:
        """Instruction RVAs whose RIP-relative operand is ``target_rva``."""
        return sorted(
            instruction
            for instruction, target in self._scan_rip_relative().items()
            if target == target_rva
        )

    def references_to_string(self, needle: bytes) -> List[int]:
        """Instruction RVAs that reference any occurrence of ``needle``."""
        targets = set(self.find_all(needle))
        if not targets:
            return []
        return sorted(
            instruction
            for instruction, target in self._scan_rip_relative().items()
            if target in targets
        )

    # -- limited instruction decoding -----------------------------------
    def _code_window(self, rva: int, size: int):
        """``(section, bytes)`` starting at ``rva``, or ``(None, None)``.

        Only executable sections are returned, and the slice is clamped to the
        section's stored bytes, so a decode never steps past the image.
        """
        section = None
        for candidate in self.executable_sections:
            if candidate.contains_rva(rva):
                section = candidate
                break
        if section is None:
            return None, None
        start = section.raw_offset + (rva - section.virtual_address)
        available = section.raw_offset + section.raw_size - start
        return section, self.data[start:start + max(0, min(size, available))]

    def reference_context(self, instruction: int,
                          max_instructions: int = 4
                          ) -> Tuple[DecodedInstruction, ...]:
        """Decode the instruction at ``instruction`` and the few that follow it.

        Decoding stops at the first byte sequence outside the small, documented
        set of forms (a RIP-relative ``lea``/``mov``, ``mov r32, imm32`` /
        ``mov r64, imm64`` and ``call rel32``), so the result is a *prefix*,
        never a guess. This is how the numeric constants passed alongside a
        loader string are read without a full disassembler.
        """
        _section, code = self._code_window(instruction, max_instructions * 16 + 16)
        if code is None:
            return ()
        decoded: List[DecodedInstruction] = []
        at = instruction
        for _ in range(max_instructions):
            item = _decode_instruction(code, at - instruction, instruction)
            if item is None:
                break
            decoded.append(item)
            at += item.length
        return tuple(decoded)

    def string_reference_contexts(
        self, needle: bytes, max_instructions: int = 4
    ) -> Tuple[Tuple[DecodedInstruction, ...], ...]:
        """For every reference to ``needle``, the decoded instruction prefix.

        The first item of each tuple is always the ``lea``/``mov`` that loads
        the string's address; the later items are the instructions that consume
        it.
        """
        return tuple(
            self.reference_context(site, max_instructions)
            for site in self.references_to_string(needle)
        )


def _decode_instruction(code: bytes, index: int, base_rva: int
                        ) -> Optional[DecodedInstruction]:
    """Decode one instruction of the limited forms used after a string load.

    Recognises an optional REX prefix followed by:

    * ``8D`` (``lea``) or ``8B`` (``mov``) with a RIP-relative ModRM
      (``(modrm & 0xC7) == 0x05``); ``operand`` is the resolved target RVA;
    * ``B8+r`` (``mov r32, imm32``); with ``REX.W`` it is the 10-byte
      ``mov r64, imm64`` form, and ``operand`` is the full 64-bit immediate;
    * ``E8`` (``call rel32``); ``operand`` is the resolved call target.

    Any other opcode returns ``None`` so callers stop rather than mis-step. The
    decoder is intentionally *not* a general x86-64 disassembler.
    """
    if index < 0 or index >= len(code):
        return None
    start = index
    cursor = index
    rex = 0
    if REX_PREFIX_MIN <= code[cursor] <= REX_PREFIX_MAX:
        rex = code[cursor]
        cursor += 1
    if cursor >= len(code):
        return None
    opcode = code[cursor]

    if opcode in (LEA, MOV):
        if cursor + 6 > len(code):
            return None
        modrm = code[cursor + 1]
        if (modrm & RIP_RELATIVE_MASK) != RIP_RELATIVE_RM:
            return None
        disp = struct.unpack_from("<i", code, cursor + 2)[0]
        length = (cursor - start) + 6
        address = base_rva + start
        return DecodedInstruction(
            address=address, length=length,
            mnemonic="lea" if opcode == LEA else "mov",
            operand=address + length + disp,
        )

    if MOV_R32_IMM32_MIN <= opcode <= MOV_R32_IMM32_MAX:
        address = base_rva + start
        if rex & REX_W:
            if cursor + 9 > len(code):
                return None
            imm = struct.unpack_from("<q", code, cursor + 1)[0]
            length = (cursor - start) + 9
        else:
            if cursor + 5 > len(code):
                return None
            imm = struct.unpack_from("<I", code, cursor + 1)[0]
            length = (cursor - start) + 5
        return DecodedInstruction(address=address, length=length,
                                  mnemonic="mov", operand=imm)

    if opcode == CALL_REL32:
        if cursor + 5 > len(code):
            return None
        rel = struct.unpack_from("<i", code, cursor + 1)[0]
        address = base_rva + start
        length = (cursor - start) + 5
        return DecodedInstruction(address=address, length=length,
                                  mnemonic="call",
                                  operand=address + length + rel)

    return None
