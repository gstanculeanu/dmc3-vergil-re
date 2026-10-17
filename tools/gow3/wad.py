"""Reader for God of War III Remastered ``R_*.WAD`` archives (partial).

Status (evidence E-016, E-022): the **header** and the **naming scheme** are
verified; the record directory that binds a name to its bytes is **not** decoded
yet, so this module deliberately stops at reconnaissance. It never claims to
extract asset payloads.

Verified layout::

    0x00  u32        always 20   (0x14)
    0x04  u32        always 8
    0x08  char[]     banner, zero-padded, e.g. "WAD_R_Hercules"

Inside the file there is a ``DC_<banner>`` marker, present **exactly 6 times** in
every WAD examined, preceded by a fixed prefix::

    00 00 00 00 00 00 00 00  0B 00 09 00  04 00 00 00  "DC_WAD_<name>"

WADs also carry many named objects. Their families are the useful reconnaissance
signal (E-022) — in particular ``hfsm*`` identifies an **AI** WAD, while entity
WADs contain none.
"""

from __future__ import annotations

import os
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional

HEADER_SIZE = 0x40
BANNER_OFFSET = 0x08
MAGIC0 = 20
MAGIC1 = 8

DC_PREFIX_TAIL = b"\x0b\x00\x09\x00\x04\x00\x00\x00"
DC_PREFIX_LEN = 16
EXPECTED_DC_COUNT = 6

_NAME_RE = re.compile(rb"[A-Za-z_][A-Za-z0-9_:.]{3,}")


class WadError(ValueError):
    """Raised when a file does not look like a GoW3R WAD."""


@dataclass(frozen=True)
class WadHeader:
    magic0: int
    magic1: int
    banner: str

    @property
    def looks_valid(self) -> bool:
        return self.magic0 == MAGIC0 and self.magic1 == MAGIC1 and bool(self.banner)

    @property
    def is_ai_wad(self) -> bool:
        """True for ``<LEVEL>AI#<Name>.WAD`` style archives (banner has 'AI')."""
        return bool(re.search(r"AI\d", self.banner))

    @property
    def is_entity_wad(self) -> bool:
        return self.banner.startswith("WAD_R_")


@dataclass(frozen=True)
class DcMarker:
    """A ``DC_<banner>`` marker with its verified 16-byte prefix."""

    offset: int
    name: str
    prefix: bytes

    @property
    def prefix_matches(self) -> bool:
        return self.prefix[:8] == b"\x00" * 8 and self.prefix[8:] == DC_PREFIX_TAIL


@dataclass
class WadInfo:
    path: str
    size: int
    header: WadHeader
    dc_markers: List[DcMarker] = field(default_factory=list)
    name_families: Dict[str, int] = field(default_factory=dict)
    hfsm_names: List[str] = field(default_factory=list)

    @property
    def dc_count_ok(self) -> bool:
        return len(self.dc_markers) == EXPECTED_DC_COUNT

    @property
    def carries_ai(self) -> bool:
        return bool(self.hfsm_names)

    def summary(self) -> dict:
        return {
            "path": self.path,
            "size": self.size,
            "banner": self.header.banner,
            "kind": "ai" if self.carries_ai else (
                "entity" if self.header.is_entity_wad else "other"
            ),
            "dc_markers": [m.offset for m in self.dc_markers],
            "dc_prefixes_ok": all(m.prefix_matches for m in self.dc_markers),
            "hfsm": self.hfsm_names,
            "name_families": self.name_families,
        }


def parse_header(data: bytes) -> WadHeader:
    if len(data) < HEADER_SIZE:
        raise WadError(f"file too small ({len(data)} bytes) for a WAD header")
    magic0 = int.from_bytes(data[0:4], "little")
    magic1 = int.from_bytes(data[4:8], "little")
    end = data.find(b"\x00", BANNER_OFFSET)
    if end < 0:
        end = min(len(data), BANNER_OFFSET + 0x38)
    banner = data[BANNER_OFFSET:end].decode("latin-1", "replace")
    header = WadHeader(magic0=magic0, magic1=magic1, banner=banner)
    if not header.looks_valid:
        raise WadError(
            f"bad WAD header (magic0={magic0}, magic1={magic1}, banner={banner!r})"
        )
    return header


def find_dc_markers(data: bytes, banner: str) -> List[DcMarker]:
    """Locate every ``DC_<banner>`` marker and capture its 16-byte prefix."""
    needle = ("DC_" + banner).encode("latin-1")
    markers: List[DcMarker] = []
    start = 0
    while True:
        index = data.find(needle, start)
        if index < 0:
            break
        prefix = data[max(0, index - DC_PREFIX_LEN):index]
        markers.append(
            DcMarker(
                offset=index,
                name=data[index:index + len(needle)].decode("latin-1", "replace"),
                prefix=prefix,
            )
        )
        start = index + 1
    return markers


def classify_name(name: str) -> str:
    if name.startswith("hfsm"):
        return "hfsm (AI state machine)"
    if name.startswith("tGOPool_"):
        return "tGOPool_N"
    if name.startswith("tMemoryPool_"):
        return "tMemoryPool_N"
    if name.startswith("ms::"):
        return "ms::*"
    if name.startswith("attachment::"):
        return "attachment::*"
    if name.startswith("go"):
        return "go* (object/FX)"
    if name.startswith("t") and name.endswith("System"):
        return "t*System"
    if name.startswith("DC_"):
        return "DC_*"
    if name.startswith("WAD_"):
        return "WAD_* (banner)"
    return "other"


def scan_names(data: bytes) -> Counter:
    counter: Counter = Counter()
    for match in _NAME_RE.finditer(data):
        counter[classify_name(match.group().decode("latin-1"))] += 1
    return counter


def hfsm_names(data: bytes) -> List[str]:
    return sorted({m.group().decode("latin-1") for m in _NAME_RE.finditer(data)
                   if m.group().startswith(b"hfsm")})


def inspect(path: str) -> WadInfo:
    with open(path, "rb") as handle:
        data = handle.read()
    header = parse_header(data)
    families = dict(scan_names(data).most_common())
    return WadInfo(
        path=path,
        size=len(data),
        header=header,
        dc_markers=find_dc_markers(data, header.banner),
        name_families=families,
        hfsm_names=hfsm_names(data),
    )


def inspect_bytes(data: bytes, path: str = "<bytes>") -> WadInfo:
    header = parse_header(data)
    return WadInfo(
        path=path,
        size=len(data),
        header=header,
        dc_markers=find_dc_markers(data, header.banner),
        name_families=dict(scan_names(data).most_common()),
        hfsm_names=hfsm_names(data),
    )


def is_wad(data: bytes) -> bool:
    try:
        return parse_header(data).looks_valid
    except WadError:
        return False
