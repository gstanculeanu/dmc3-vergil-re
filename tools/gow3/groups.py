"""Stream the record layout of ``R_*.WAD`` (E-060).

The container is **not** a header plus a table plus one bulk region. It is a
stream of 0x40-byte records that begins at 0x50, in which ``GroupStart`` /
``GroupEnd`` records bracket groups of resources and *each resource's data sits
inline, immediately after its descriptor*::

    0x50  GroupStart
    0x90  resource  "WAD_R_Hades"   size 24
    0xF0  GroupStart
    0x130 resource  "TXRX_R_Hades"  size 16
    0x180 GroupEnd
    ...

Record shape (little endian)::

    +0x00  u16 id     1 = sized resource, 2 = GroupStart, 3 = GroupEnd,
                      0x12 = root, 0x15 = PopHeap, 7 = unsized resource
    +0x02  u16 flags  for a sized resource: the resource class
    +0x04  u32        size, for a sized resource only
    +0x08  char[]     name (at +0x04 for an unsized resource)

A sized resource's data begins ``0x40`` bytes after the record, plus another
``0x40`` when ``flags != 0`` (such resources carry a second header), and is
``size`` bytes long, padded up to 0x10.

The layout is **verified by an exact boundary** rather than by trusting the
rule: in ``R_HADES.WAD`` ``ANM_hero_Hades`` is at 0xDC0 with size 2,106,384 and
``flags = 0x34``, so its data starts at 0xE40 and ends at 0x203250 -- which is
precisely where the next ``GroupEnd`` record begins (E-060).

This walker is deliberately **partial and self-reporting**: it stops at the first
record whose shape it does not model and says why, instead of resynchronising.
That is how ``ANM_camera_Hades`` (127,416 B at 0x203350) and ``SBP_HADES``
(3,428,663 B at 0x222590, a *sound* bank) were found.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, List, Optional, Tuple

RECORD_START = 0x50
RECORD_SIZE = 0x40
ALIGNMENT = 0x10
EXTRA_HEADER_SIZE = 0x40

ID_RESOURCE = 1
ID_UNSIZED = 7
GROUP_START = 2
GROUP_END = 3
ROOT = 0x12
POP_HEAP = 0x15

SIMPLE_IDS = {
    GROUP_START: "GroupStart",
    GROUP_END: "GroupEnd",
    ROOT: "root",
    POP_HEAP: "PopHeap",
}

# Resource class ids seen on sized resources (flags field).
CLASS_NAMES = {
    0x00: "?",
    0x0D: "texture",
    0x13: "audio-db",
    0x34: "animation",
}


class LayoutError(ValueError):
    """Raised when a WAD stops matching the modelled record shapes."""


@dataclass(frozen=True)
class Record:
    """One record of the stream."""

    offset: int
    end: int
    id: int
    flags: int
    size: Optional[int]
    name: str
    data: Optional[int] = None

    @property
    def kind(self) -> str:
        if self.id == ID_RESOURCE:
            return "resource"
        if self.id == ID_UNSIZED:
            return "unsized"
        return SIMPLE_IDS.get(self.id, f"id{self.id}")

    @property
    def class_name(self) -> str:
        return CLASS_NAMES.get(self.flags, f"class0x{self.flags:02X}")

    def text(self, data: bytes) -> Optional[bytes]:
        if self.data is None or self.size is None:
            return None
        return data[self.data:self.data + self.size]

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        size = f"{self.size:,}" if self.size is not None else "-"
        return (f"+0x{self.offset:08X} {self.kind:<10} cls=0x{self.flags:02X} "
                f"size={size:>12} {self.name!r}")


def _name(data: bytes, at: int, limit: int = 0x38) -> str:
    raw = data[at:at + limit].split(b"\x00", 1)[0]
    if not raw or not all(32 <= b < 127 for b in raw):
        return ""
    return raw.decode("latin-1")


def read_record(data: bytes, offset: int) -> Record:
    """Read one record at ``offset``, or raise :class:`LayoutError`."""
    if offset + RECORD_SIZE > len(data):
        raise LayoutError(f"0x{offset:X}: past the end of the file")
    ident = int.from_bytes(data[offset:offset + 2], "little")
    flags = int.from_bytes(data[offset + 2:offset + 4], "little")

    if ident == ID_RESOURCE:
        size = int.from_bytes(data[offset + 4:offset + 8], "little")
        name = _name(data, offset + 8)
        if not name:
            raise LayoutError(f"0x{offset:X}: sized resource with no name")
        header = RECORD_SIZE + (EXTRA_HEADER_SIZE if flags else 0)
        begin = offset + header
        end = begin + ((size + ALIGNMENT - 1) & ~(ALIGNMENT - 1))
        if end > len(data):
            raise LayoutError(
                f"0x{offset:X}: resource {name!r} of {size:,} bytes overruns")
        return Record(offset=offset, end=end, id=ident, flags=flags, size=size,
                      name=name, data=begin)

    if ident == ID_UNSIZED:
        name = _name(data, offset + 4)
        if not name:
            raise LayoutError(f"0x{offset:X}: unsized record with no name")
        return Record(offset=offset, end=offset + RECORD_SIZE, id=ident,
                      flags=flags, size=None, name=name)

    if ident in SIMPLE_IDS:
        return Record(offset=offset, end=offset + RECORD_SIZE, id=ident,
                      flags=flags, size=None, name=_name(data, offset + 8))

    raise LayoutError(f"0x{offset:X}: unmodelled record id {ident} "
                      f"(flags 0x{flags:04X})")


def walk(data: bytes, start: int = RECORD_START) -> Iterator[Record]:
    """Yield records until the shapes stop matching, then stop.

    Partial by design: this is reconnaissance, not a repacker. Use
    :func:`inventory` to get the records *and* the reason it stopped.
    """
    offset = start
    while offset + RECORD_SIZE <= len(data):
        record = read_record(data, offset)          # may raise
        yield record
        if record.end <= offset:
            return
        offset = record.end


def inventory(data: bytes, start: int = RECORD_START
              ) -> Tuple[List[Record], Optional[str]]:
    """Every record up to the first unmodelled one, plus why it stopped."""
    records: List[Record] = []
    offset = start
    while offset + RECORD_SIZE <= len(data):
        try:
            record = read_record(data, offset)
        except LayoutError as error:
            return records, str(error)
        if record.end <= offset:
            return records, f"0x{offset:X}: a record did not advance"
        records.append(record)
        offset = record.end
    return records, None if offset == len(data) else f"stopped at 0x{offset:X}"


def resources(records: List[Record]) -> List[Record]:
    """The sized resources of an inventory, in file order."""
    return [r for r in records if r.id == ID_RESOURCE]
