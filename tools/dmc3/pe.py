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
