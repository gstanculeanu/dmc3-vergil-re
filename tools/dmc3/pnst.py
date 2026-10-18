"""DMC3 ``PNST`` weapon container reader.

Weapon archives (``plwp_*.pac``, e.g. Yamato's ``plwp_vergilsword.pac``) use
the ``PNST`` container instead of the ``PAC\0`` container used for character
data (evidence E-006).  Like ``PAC`` it is a flat table of file-relative
offsets followed by chunks; unlike ``PAC`` no size-prefixed chunk framing has
been observed, so chunk tags, when present, sit at byte 0.

Layout (all integers little-endian) as observed on both weapon archives
(E-006)::

    0x00  char[4]  "PNST"
    0x04  u32      entry_count
    0x08  u32      offset[entry_count]   file-relative; 0 == empty slot
    ...   zero padding to 16-byte alignment
    data  chunks at the recorded offsets

`align_up(0x08 + 4 * entry_count, 0x10) == offset[0]` held on both files
checked.  Chunks carry their own structure: ``MOD `` mesh headers (E-030),
``SHW `` shader headers (E-036/E-038), nested ``PAC\0`` and ``PNST``
containers, plain-text cloth configs (``;wp005.clt``, like E-004), and raw
blocks (see :class:`PnstRawBlock`, evidence E-048).

Because the container stores no chunk length, a chunk's span is derived as the
distance to the next occupied entry — an upper bound, like ``PAC``.

This module never writes into a game installation; it is read-only.
"""

from __future__ import annotations

import os
import struct
from dataclasses import dataclass
from typing import Iterator, List, Optional

MAGIC = b"PNST"
"""Container magic, observed at byte 0 of every ``plwp_*.pac`` archive."""

TABLE_START = 0x08
"""Byte at which the offset table begins."""

ALIGNMENT = 0x10
"""Alignment of the table size and of chunks within the data region."""

TAG_MODEL = b"MOD "
TAG_SHADER = b"SHW "
TAG_CONTAINER = b"PAC\x00"
TAG_PNST = b"PNST"

_KIND_BY_TAG = {
    TAG_MODEL: "model",
    TAG_SHADER: "shader",
    TAG_CONTAINER: "container",
    TAG_PNST: "nested",
}


def align_up(value: int, alignment: int = ALIGNMENT) -> int:
    """Round ``value`` up to the next multiple of ``alignment``."""
    if alignment <= 0:
        raise ValueError("alignment must be positive")
    return (value + alignment - 1) & ~(alignment - 1)


def u32(buf: bytes, offset: int) -> int:
    return struct.unpack_from("<I", buf, offset)[0]


def u16(buf: bytes, offset: int) -> int:
    return struct.unpack_from("<H", buf, offset)[0]


def _ascii_tag(data: bytes, offset: int) -> Optional[bytes]:
    """Return a plausible 4-byte chunk tag at ``offset``, else ``None``.

    The same rule as the ``PAC`` container: three ASCII letters/digits followed
    by a printable character or NUL.  ``PNST`` chunks are plain-framed, so only
    byte 0 is checked.
    """
    if len(data) < offset + 4:
        return None
    tag = data[offset:offset + 4]
    head, tail = tag[:3], tag[3]
    if not all(48 <= b <= 57 or 65 <= b <= 90 or 97 <= b <= 122 for b in head):
        return None
    if tail != 0 and not (32 <= tail < 127):
        return None
    return tag


def _looks_like_text(data: bytes) -> bool:
    sample = data[:64]
    if not sample:
        return False
    printable = sum(1 for b in sample if 32 <= b < 127 or b in (9, 10, 13))
    return printable >= (len(sample) * 9) // 10


@dataclass(frozen=True)
class PnstChunk:
    """One occupied entry of a PNST archive."""

    index: int
    """Slot number in the offset table (a file's logical identifier)."""

    offset: int
    """File-relative byte offset of the chunk."""

    span: int
    """Upper bound on the chunk size: distance to the next occupied entry."""

    data: bytes
    """Raw chunk bytes (``span`` bytes, starting at ``offset``)."""

    @property
    def tag_offset(self) -> int:
        """Byte position of the tag: ``0`` (PNST chunks are plain-framed)."""
        return 0

    @property
    def tag(self) -> bytes:
        tag = _ascii_tag(self.data, 0)
        return tag if tag is not None else b""

    @property
    def tag_text(self) -> str:
        """Tag as text with a trailing NUL removed (``MOD ``, ``SHW ``, …)."""
        return self.tag.decode("latin-1").rstrip("\x00")

    @property
    def kind(self) -> str:
        """Coarse classification: model / shader / container / nested / text / raw."""
        known = _KIND_BY_TAG.get(self.tag)
        if known:
            return known
        if _looks_like_text(self.data):
            return "text"
        return "raw"

    @property
    def trimmed(self) -> bytes:
        """Trailing zero padding removed (best effort, for text payloads)."""
        return self.data.rstrip(b"\x00")


class PnstArchive:
    """Read-only view over a ``PNST`` weapon container."""

    def __init__(self, data: bytes, name: str = "") -> None:
        if len(data) < TABLE_START:
            raise ValueError("file too small to be a PNST container")
        if data[:4] != MAGIC:
            raise ValueError(
                f"bad magic {data[:4]!r} (expected {MAGIC!r})"
            )
        self.data = data
        self.name = name
        self.entry_count = u32(data, 4)
        table_end = TABLE_START + 4 * self.entry_count
        if table_end > len(data):
            raise ValueError(
                f"offset table ({self.entry_count} entries) runs past end of file"
            )
        self.entries: List[int] = [
            u32(data, TABLE_START + 4 * i) for i in range(self.entry_count)
        ]
        self.table_end = table_end
        self.data_offset = align_up(table_end)

    # -- construction ---------------------------------------------------
    @classmethod
    def from_path(cls, path: str | os.PathLike[str]) -> "PnstArchive":
        with open(path, "rb") as handle:
            return cls(handle.read(), name=os.path.basename(os.fspath(path)))

    @classmethod
    def from_bytes(cls, data: bytes, name: str = "") -> "PnstArchive":
        return cls(data, name=name)

    # -- queries --------------------------------------------------------
    @property
    def occupied_offsets(self) -> List[int]:
        """Distinct, non-zero entry offsets in ascending order."""
        return sorted({o for o in self.entries if o})

    @property
    def empty_slots(self) -> List[int]:
        return [i for i, o in enumerate(self.entries) if o == 0]

    def span_for(self, offset: int) -> int:
        if offset >= len(self.data):
            raise ValueError(f"offset 0x{offset:X} is past end of file")
        successors = [o for o in self.occupied_offsets if o > offset]
        end = min(successors) if successors else len(self.data)
        return end - offset

    def chunk(self, index: int) -> Optional[PnstChunk]:
        """Return the chunk in slot ``index``, or ``None`` for an empty slot."""
        offset = self.entries[index]
        if offset == 0:
            return None
        span = self.span_for(offset)
        return PnstChunk(
            index=index,
            offset=offset,
            span=span,
            data=self.data[offset:offset + span],
        )

    def chunks(self) -> Iterator[PnstChunk]:
        """Iterate occupied chunks in table order."""
        for index in range(self.entry_count):
            chunk = self.chunk(index)
            if chunk is not None:
                yield chunk

    def chunks_of_kind(self, kind: str) -> List[PnstChunk]:
        return [c for c in self.chunks() if c.kind == kind]

    def summary(self) -> dict:
        kinds: dict[str, int] = {}
        for chunk in self.chunks():
            kinds[chunk.kind] = kinds.get(chunk.kind, 0) + 1
        return {
            "name": self.name,
            "size": len(self.data),
            "entries": self.entry_count,
            "occupied": len(self.occupied_offsets),
            "empty": len(self.empty_slots),
            "table_end": self.table_end,
            "data_offset": self.data_offset,
            "kinds": kinds,
        }

    def __len__(self) -> int:
        return self.entry_count

    def __iter__(self) -> Iterator[PnstChunk]:
        return self.chunks()

    def __repr__(self) -> str:
        return f"<PnstArchive {self.name!r} entries={self.entry_count}>"


@dataclass(frozen=True)
class PnstRawBlock:
    """The raw (untagged) blocks found in PNST weapon archives.

    Slots 0 and 3 of both ``plwp_vergilsword.pac`` and
    ``plwp_newvergilsword.pac`` begin with an identical 8-byte header
    (evidence E-048), body-relative and little-endian::

        +0x00 u32 field_a   observed 1
        +0x04 u32 field_b   observed 17 (0x11)

    Everything after the header is [UNKNOWN]: in the observed blocks it opens
    with a zero-filled run (the first non-zero byte sits at body+2049) and
    then structured data whose meaning requires engine ground truth.  This
    reader decodes the header only and makes no claim about the tail.

    Slots carrying other raw payloads (e.g. slot 9 of
    ``plwp_newvergilsword.pac``) do not match this header and remain wholly
    [UNKNOWN].
    """

    HEADER_SIZE = 8
    """Size of the decoded raw-block header, in bytes."""

    field_a: int
    field_b: int


def parse_pnst_raw_block(data: bytes) -> PnstRawBlock:
    """Read the 8-byte header of a raw PNST block (``field_a``, ``field_b``).

    Raises ``ValueError`` if ``data`` holds fewer than 8 bytes.  No semantic
    claim is made about the values or about the bytes that follow the header.
    """
    if len(data) < PnstRawBlock.HEADER_SIZE:
        raise ValueError(
            f"raw block too small for an {PnstRawBlock.HEADER_SIZE}-byte header"
        )
    return PnstRawBlock(field_a=u32(data, 0), field_b=u32(data, 4))


def maybe_pnst_raw_block(data: bytes) -> Optional[PnstRawBlock]:
    """Parse a raw-block header, or ``None`` if there are fewer than 8 bytes.

    Unlike :func:`parse_pnst_raw_block` this never raises; it is handy for
    classifying raw chunks without over-claiming about their contents.
    """
    if len(data) < PnstRawBlock.HEADER_SIZE:
        return None
    return parse_pnst_raw_block(data)
