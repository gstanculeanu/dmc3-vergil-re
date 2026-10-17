"""Raw (untagged) PAC chunk payloads.

Some PAC slots carry no ASCII tag: ``pl021.pac`` has nine occupied untagged
slots (0, 5, 6, 7, 9, 10, 11, 21, 22) holding bone transforms, UV tables,
primitive groups and other untagged tables (evidence E-008).  This module
decodes only what is *observed* in real bytes; every field meaning is
[UNKNOWN] until engine ground truth arrives.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .pac import u32

SLOT0_HEADER_SIZE = 0x18
"""Size of the decoded header of ``pl021.pac`` slot 0: six u32s."""


@dataclass(frozen=True)
class RawHeader:
    """Leading header of a raw chunk, as observed in ``pl021.pac`` slot 0.

    Observed at file offset 0x80 of ``pl021.pac`` (evidence E-033): six
    little-endian u32s (5, 43, 22, 43, 5, 1), then zero bytes until
    body+0x0800 where small sub-fields appear; an embedded ``DDS `` magic is
    present at body+0x0870 (file offset 0x8F0).  Every field's meaning is
    [UNKNOWN] and is deliberately not named beyond its offset.  The rest of
    the slot's ~235 KB body is undecoded (issue F3).
    """

    field_00: int
    field_04: int
    field_08: int
    field_0c: int
    field_10: int
    field_14: int

    @classmethod
    def parse(cls, data: bytes) -> "RawHeader":
        """Parse the first 24 bytes of a raw chunk payload."""
        if len(data) < SLOT0_HEADER_SIZE:
            raise ValueError(
                f"raw chunk only {len(data)} bytes, need {SLOT0_HEADER_SIZE} for the header"
            )
        return cls(*(u32(data, 4 * index) for index in range(6)))


def maybe_raw_header(data: bytes) -> Optional[RawHeader]:
    """Like :meth:`RawHeader.parse` but returns ``None`` on short input."""
    try:
        return RawHeader.parse(data)
    except ValueError:
        return None
