"""Reader/writer for the GoW3R localisation table (``R_LANG_*.WAD``).

Observed (evidence E-052): the archive carries a plain-text table whose entries
are delimited by ``*<digits>*`` markers::

    *20001*
    1
    FALSE
    Fear Kratos
    heroImage01
    ...

Everything is ASCII, so entries can be found and (if the byte length is kept
identical) replaced in place -- no container rebuild needed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterator, List, Optional

MARKER = re.compile(rb"\*(\d{1,6})\*")


@dataclass(frozen=True)
class Blob:
    """A named blob described by the table after a WAD's directory (E-054)."""

    name: str
    descriptor_offset: int   # offset of the descriptor's id field
    size_offset: int         # offset of its u32 size
    size: int
    data_offset: int         # descriptor_offset + 0x40

    @property
    def end(self) -> int:
        return self.data_offset + self.size


def find_blob(data: bytes, name: str) -> Optional[Blob]:
    """Locate ``name`` in a WAD's named-blob descriptor table.

    Observed layout of a descriptor (0x40 bytes)::

        +0x00  u32   id
        +0x04  u32   size of the blob
        +0x08  char  name[0x38], NUL padded
        +0x40  the blob's data begins here

    Only a descriptor whose name field *exactly* matches is accepted, so the many
    incidental occurrences of a name inside the text are not mistaken for it.
    """
    needle = name.encode("latin-1")
    at = data.find(needle)
    while at >= 0:
        descriptor = at - 8
        if descriptor >= 0 and descriptor % 4 == 0:
            raw = data[at:at + 0x38]
            head = raw.split(b"\x00", 1)[0]
            if head.decode("latin-1", "replace") == name:
                size = int.from_bytes(data[descriptor + 4:descriptor + 8], "little")
                return Blob(name=name, descriptor_offset=descriptor,
                            size_offset=descriptor + 4, size=size,
                            data_offset=descriptor + 0x40)
        at = data.find(needle, at + 1)
    return None


def replace_exact_line_in_blob(
    data: bytes, blob: Blob, old: str, new: str
) -> Optional[bytes]:
    """Rename ``old`` to ``new`` inside ``blob``, keeping the container valid.

    Unlike :func:`replace_exact_line`, this permits a change of length: it inserts
    the bytes and adds the difference to the blob's stored size, which is the only
    bookkeeping the container appears to carry (E-054 -- the file stores no offset
    or size that covers the blob's interior). Everything after the insertion point
    shifts, which is harmless for a text blob whose entries are found by scanning
    ``*id*`` markers.

    Returns ``None`` if the entry cannot be located, or is not inside ``blob``.
    """
    entries = parse_entries(data)
    target = None
    line_offset = None
    for entry in entries:
        if not (blob.data_offset <= entry.start < blob.end):
            continue
        body = entry.text
        for line in body.splitlines():
            stripped = line.strip()
            if stripped == old:
                target = entry
                line_offset = body.index(line) + line.index(stripped)
                break
        if target is not None:
            break
    if target is None or line_offset is None:
        return None

    absolute = target.text_offset + line_offset
    delta = len(new) - len(old)
    out = bytearray()
    out += data[:absolute]
    out += new.encode("latin-1")
    out += data[absolute + len(old):]
    new_size = blob.size + delta
    if new_size < 0:
        return None
    out[blob.size_offset:blob.size_offset + 4] = new_size.to_bytes(4, "little")
    return bytes(out)


@dataclass(frozen=True)
class LangEntry:
    entry_id: int
    start: int          # offset of the '*'
    end: int            # offset just past the closing '*'
    text: str           # the body that follows, up to the next marker
    raw: bytes

    @property
    def text_offset(self) -> int:
        """Offset of the first body byte (just past the ``*id*`` marker)."""
        return self.end

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        first = self.text.strip().splitlines()[0] if self.text.strip() else ""
        return f"*{self.entry_id}* @0x{self.start:08X} {first[:70]!r}"


def parse_entries(data: bytes) -> List[LangEntry]:
    """All ``*id*``-delimited entries in file order."""
    marks = [(m.start(), m.end(), int(m.group(1))) for m in MARKER.finditer(data)]
    out: List[LangEntry] = []
    for i, (s, e, eid) in enumerate(marks):
        nxt = marks[i + 1][0] if i + 1 < len(marks) else len(data)
        out.append(
            LangEntry(entry_id=eid, start=s, end=e, text=data[e:nxt].decode("latin-1", "replace"),
                      raw=data[s:nxt])
        )
    return out


def search(entries: List[LangEntry], needle: str, exact_line: bool = False) -> List[LangEntry]:
    """Entries whose text contains ``needle`` (case-insensitive)."""
    want = needle.lower()
    hits = []
    for entry in entries:
        for line in entry.text.splitlines():
            line = line.strip()
            if not line:
                continue
            if (line.lower() == want) if exact_line else (want in line.lower()):
                hits.append(entry)
                break
    return hits


def load(path: str) -> List[LangEntry]:
    with open(path, "rb") as handle:
        return parse_entries(handle.read())


def replace_exact_line(data: bytes, entry: LangEntry, old: str,
                       new: str) -> Optional[bytes]:
    """Replace a whole line inside ``entry`` with an equal-length ``new``.

    Returns ``None`` when the replacement would change the byte length -- the
    container stores sizes, so a length change needs a real writer.
    """
    body = entry.text
    for line in body.splitlines():
        stripped = line.strip()
        if stripped == old:
            if len(new) != len(stripped):
                return None
            idx = body.index(line)
            abs_at = entry.text_offset + idx + line.index(stripped)
            blob = bytearray(data)
            blob[abs_at:abs_at + len(old)] = new.encode("latin-1")
            return bytes(blob)
    return None
