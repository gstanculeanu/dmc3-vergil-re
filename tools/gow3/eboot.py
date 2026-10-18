"""Read the GoW3R PS4 image and find code that references a given string.

The WAD **record opcodes are numeric constants in code** (evidence E-053), so the
WAD loader cannot be found by searching the executable for opcode *names*. It can
be found the other way round: locate the address of a string the loader must use
(``WAD_``, ``hfsm``, ``DEPENDENCY``, ``.wad`` …), then scan the executable for
instructions that reference that address.

This module does exactly that, read-only:

* :class:`ElfImage` parses a 64-bit little-endian ELF (the prepared
  ``out/eboot.elf``) and maps **file offsets to virtual addresses** and back
  through its ``PT_LOAD`` program headers. The retail ``eboot.bin`` is the same
  image without headers, so it cannot be mapped on its own; use the prepared ELF.
* :meth:`ElfImage.find_all` finds the virtual addresses of a byte string.
* :meth:`ElfImage.rip_relative_references` scans the executable segments for
  ``lea``/``mov`` with a RIP-relative memory operand and returns the addresses of
  the instructions that reference a given target address.

RIP-relative addressing is ``modrm`` with ``mod == 00`` and ``r/m == 101``,
i.e. ``(modrm & 0xC7) == 0x05`` — **any** destination register, not only the
``modrm == 0x05`` (``rax``) form E-053 first reported. Observed on the real image:
``48 8d 3d 06 04 25 00`` = ``lea rdi, [rip + 0x250406]`` at virtual ``0x100D49``,
whose target is the ``WAD_`` string at ``0x351156`` (E-056).

The scan is a byte-pattern scan, **not a disassembler**: it can in principle
report a coincidental match starting inside another instruction. A hit is
meaningful when its target is a known string address, which is how the tool is
used and validated.
"""

from __future__ import annotations

import os
import struct
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

ELF_MAGIC = b"\x7fELF"
ELFCLASS64 = 2
ELFDATA2LSB = 1
PT_LOAD = 1
PF_X = 1

LEA = 0x8D
MOV = 0x8B
RIP_RELATIVE_MASK = 0xC7
RIP_RELATIVE_RM = 0x05
REX_PREFIX_MIN = 0x40
REX_PREFIX_MAX = 0x4F


class ElfError(ValueError):
    """Raised when a file is not a usable 64-bit little-endian ELF image."""


@dataclass(frozen=True)
class ProgramSegment:
    """One ``PT_LOAD`` (or other) program header, in file order."""

    index: int
    p_type: int
    flags: int
    offset: int
    vaddr: int
    filesz: int
    memsz: int
    align: int

    @property
    def is_load(self) -> bool:
        return self.p_type == PT_LOAD

    @property
    def is_executable(self) -> bool:
        return self.is_load and bool(self.flags & PF_X)

    def contains_offset(self, offset: int) -> bool:
        return self.offset <= offset < self.offset + self.filesz

    def contains_vaddr(self, vaddr: int) -> bool:
        return self.vaddr <= vaddr < self.vaddr + self.filesz


@dataclass(frozen=True)
class ElfImage:
    """A parsed 64-bit little-endian ELF with file<->virtual address mapping."""

    data: bytes
    entry: int
    segments: Tuple[ProgramSegment, ...]

    # -- construction ---------------------------------------------------
    @classmethod
    def from_bytes(cls, data: bytes) -> "ElfImage":
        if len(data) < 64:
            raise ElfError(f"file too small ({len(data)} bytes) for an ELF header")
        if data[:4] != ELF_MAGIC:
            raise ElfError(f"bad ELF magic {data[:4]!r}")
        if data[4] != ELFCLASS64:
            raise ElfError(f"not a 64-bit ELF (class {data[4]})")
        if data[5] != ELFDATA2LSB:
            raise ElfError(f"not little-endian (data {data[5]})")

        entry = struct.unpack_from("<Q", data, 0x18)[0]
        phoff = struct.unpack_from("<Q", data, 0x20)[0]
        phentsize = struct.unpack_from("<H", data, 0x36)[0]
        phnum = struct.unpack_from("<H", data, 0x38)[0]
        if phentsize < 56:
            raise ElfError(f"program header entry too small ({phentsize})")
        if phoff + phentsize * phnum > len(data):
            raise ElfError("program header table runs past end of file")

        segments: List[ProgramSegment] = []
        for index in range(phnum):
            at = phoff + index * phentsize
            (p_type, p_flags) = struct.unpack_from("<II", data, at)
            (p_offset, p_vaddr, _p_paddr, p_filesz, p_memsz, p_align) = (
                struct.unpack_from("<QQQQQQ", data, at + 8)
            )
            segments.append(
                ProgramSegment(
                    index=index, p_type=p_type, flags=p_flags, offset=p_offset,
                    vaddr=p_vaddr, filesz=p_filesz, memsz=p_memsz, align=p_align,
                )
            )
        return cls(data=data, entry=entry, segments=tuple(segments))

    @classmethod
    def from_path(cls, path: str | os.PathLike[str]) -> "ElfImage":
        with open(path, "rb") as handle:
            return cls.from_bytes(handle.read())

    # -- address mapping ------------------------------------------------
    @property
    def executable_segments(self) -> Tuple[ProgramSegment, ...]:
        return tuple(s for s in self.segments if s.is_executable)

    def file_offset_to_vaddr(self, offset: int) -> Optional[int]:
        """Virtual address of a **file offset**, or ``None`` if not in a load."""
        for segment in self.segments:
            if segment.is_load and segment.contains_offset(offset):
                return segment.vaddr + (offset - segment.offset)
        return None

    def vaddr_to_file_offset(self, vaddr: int) -> Optional[int]:
        """File offset of a **virtual address**, or ``None`` if not in a load."""
        for segment in self.segments:
            if segment.is_load and segment.contains_vaddr(vaddr):
                return segment.offset + (vaddr - segment.vaddr)
        return None

    def read(self, vaddr: int, size: int) -> bytes:
        """Bytes at a virtual address (from the file image)."""
        offset = self.vaddr_to_file_offset(vaddr)
        if offset is None:
            raise ElfError(f"vaddr 0x{vaddr:X} is not mapped")
        return self.data[offset:offset + size]

    # -- string and reference search ------------------------------------
    def find_all(self, needle: bytes) -> List[int]:
        """Virtual addresses of every occurrence of ``needle`` in loaded data."""
        found: List[int] = []
        start = 0
        while True:
            at = self.data.find(needle, start)
            if at < 0:
                break
            vaddr = self.file_offset_to_vaddr(at)
            if vaddr is not None:
                found.append(vaddr)
            start = at + 1
        return found

    def _scan_rip_relative(self) -> Dict[int, int]:
        """Map every ``lea``/``mov`` instruction address to its target address."""
        references: Dict[int, int] = {}
        for segment in self.executable_segments:
            code = self.data[segment.offset:segment.offset + segment.filesz]
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
                    instruction = segment.vaddr + index
                    references[instruction] = instruction + insn_len + disp
                    index += insn_len
                    continue
                index += 1
        return references

    def rip_relative_references(self, target_vaddr: int) -> List[int]:
        """Instruction addresses whose RIP-relative operand is ``target_vaddr``."""
        return sorted(
            instruction
            for instruction, target in self._scan_rip_relative().items()
            if target == target_vaddr
        )

    def references_to_string(self, needle: bytes) -> List[int]:
        """Instruction addresses that reference any occurrence of ``needle``."""
        targets = set(self.find_all(needle))
        if not targets:
            return []
        return sorted(
            instruction
            for instruction, target in self._scan_rip_relative().items()
            if target in targets
        )
