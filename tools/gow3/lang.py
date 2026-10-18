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

MARKER = re.compile(rb"\*(\d{3,6})\*")


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
