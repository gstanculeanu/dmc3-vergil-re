"""DMC3 PAC container reader.

DMC3 (and the HD Collection re-release) stores most character data in ``.pac``
containers.  The container is a flat table of file-relative offsets followed by a
set of tagged chunks.

Layout (all integers little-endian)::

    0x00  char[4]  "PAC\\0"
    0x04  u32      entry_count
    0x08  u32      offset[entry_count]   file-relative; 0 == empty slot
    ...   padding to 16-byte alignment
    data  begin

Each occupied entry points at a chunk.  The first four bytes of a chunk are its
tag.  Because the container does not always store an explicit chunk length, the
length of chunk *i* is taken to be the distance to the next occupied entry (or to
end-of-file for the last one).  That distance is an *upper bound*: a chunk may
end before the next one begins, leaving padding, and validation is the caller's
problem.  See docs/EVIDENCE.md (E-001) and docs/FORMATS.md.

Observed chunk tags:

    b"MOD "  mesh / model data
    b"SHW "  shader / material binding
    b"MOT\\0" motion (animation) data
    other    raw or text payload (e.g. a ``.clt`` cloth-config text file)

Two chunk framings are observed, and :class:`Chunk` detects which one applies:

* **plain** — the tag is the first four bytes of the chunk (``MOD ``, ``SHW ``).
* **size-prefixed** — a ``u32`` header size precedes the tag, so the tag starts at
  byte 4 (``MOT\\0``).  In samples that ``u32`` equals the MOT header size.

Because the container rarely stores an explicit chunk length, a chunk's size is
derived from the distance to the next occupied slot.  A tag is only accepted when
all four bytes are printable ASCII; otherwise the chunk is classified as raw.

This module never writes into a game installation; it is read-only.
"""

from __future__ import annotations

import os
import struct
from dataclasses import dataclass
from typing import Iterator, List, Optional, Sequence

MAGIC = b"PAC\x00"
TABLE_START = 0x08
ALIGNMENT = 0x10

TAG_MODEL = b"MOD "
TAG_SHADER = b"SHW "
TAG_MOTION = b"MOT\x00"

_KIND_BY_TAG = {
    TAG_MODEL: "model",
    TAG_SHADER: "shader",
    TAG_MOTION: "motion",
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


def f32(buf: bytes, offset: int) -> float:
    return struct.unpack_from("<f", buf, offset)[0]


def _looks_like_text(data: bytes) -> bool:
    sample = data[:64]
    if not sample:
        return False
    printable = sum(1 for b in sample if 32 <= b < 127 or b in (9, 10, 13))
    return printable >= (len(sample) * 9) // 10


def _ascii_tag(data: bytes, offset: int) -> Optional[bytes]:
    """Return a plausible 4-byte chunk tag at ``offset``, else ``None``.

    A tag is three ASCII letters/digits followed by a printable character or a
    NUL (``MOD `` and ``SHW `` end in a space; ``MOT`` ends in NUL).  Requiring
    alphanumerics in the first three bytes keeps stray numeric fields from being
    mistaken for tags.
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


@dataclass(frozen=True)
class Chunk:
    """One occupied entry of a PAC archive."""

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
        """Byte position of the ASCII tag: 0 for plain, 4 for size-prefixed."""
        if _ascii_tag(self.data, 0) is not None:
            return 0
        if _ascii_tag(self.data, 4) is not None:
            return 4
        return 0

    @property
    def tag(self) -> bytes:
        return self.data[self.tag_offset:self.tag_offset + 4]

    @property
    def tag_text(self) -> str:
        """Tag as text with a trailing NUL removed (``MOD ``, ``SHW ``, ``MOT``)."""
        tag = _ascii_tag(self.data, self.tag_offset)
        if tag is None:
            return ""
        return tag.decode("latin-1").rstrip("\x00")

    @property
    def kind(self) -> str:
        """Coarse classification: model / shader / motion / text / raw."""
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


class PacArchive:
    """Read-only view over a ``.pac`` container."""

    def __init__(self, data: bytes, name: str = "") -> None:
        if len(data) < TABLE_START:
            raise ValueError("file too small to be a PAC container")
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
    def from_path(cls, path: str | os.PathLike[str]) -> "PacArchive":
        with open(path, "rb") as handle:
            return cls(handle.read(), name=os.path.basename(os.fspath(path)))

    @classmethod
    def from_bytes(cls, data: bytes, name: str = "") -> "PacArchive":
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

    def chunk(self, index: int) -> Optional[Chunk]:
        """Return the chunk in slot ``index``, or ``None`` for an empty slot."""
        offset = self.entries[index]
        if offset == 0:
            return None
        span = self.span_for(offset)
        return Chunk(
            index=index,
            offset=offset,
            span=span,
            data=self.data[offset:offset + span],
        )

    def chunks(self) -> Iterator[Chunk]:
        """Iterate occupied chunks in table order."""
        for index in range(self.entry_count):
            chunk = self.chunk(index)
            if chunk is not None:
                yield chunk

    def chunks_of_kind(self, kind: str) -> List[Chunk]:
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

    def __iter__(self) -> Iterator[Chunk]:
        return self.chunks()

    def __repr__(self) -> str:
        return f"<PacArchive {self.name!r} entries={self.entry_count}>"


# ---------------------------------------------------------------------------
# Writer (used by the re-import milestone; not needed to read a game install)
# ---------------------------------------------------------------------------

def build_pac(chunks: Sequence[Optional[bytes]], alignment: int = ALIGNMENT) -> bytes:
    """Build a PAC container from a slot sequence.

    ``chunks[i]`` is the raw payload for slot ``i`` or ``None`` for an empty
    slot.  Payloads are stored verbatim; callers are responsible for any tag
    their payload requires.  This is the inverse of :class:`PacArchive` for
    containers whose chunks are self-describing.
    """
    entry_count = len(chunks)
    table_end = TABLE_START + 4 * entry_count
    data_start = align_up(table_end, alignment)

    offsets = [0] * entry_count
    body = bytearray()
    cursor = data_start
    for index, payload in enumerate(chunks):
        if payload is None:
            continue
        if not isinstance(payload, (bytes, bytearray)):
            raise TypeError(
                f"chunks[{index}] must be bytes or None, "
                f"got {type(payload).__name__}"
            )
        offsets[index] = cursor
        body += payload
        cursor += len(payload)
        pad = (-cursor) % alignment
        body += b"\x00" * pad
        cursor += pad

    header = bytearray()
    header += MAGIC
    header += struct.pack("<I", entry_count)
    for off in offsets:
        header += struct.pack("<I", off)
    header += b"\x00" * (data_start - len(header))
    return bytes(header) + bytes(body)
