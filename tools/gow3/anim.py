"""Reader for the GoW3R animation clip directory inside ``R_*.WAD`` (E-058).

Verified on ``R_HADES.WAD``::

    0xD80  descriptor table (0x40-byte entries)
    0xDC0    id=1 flags=0x34 size=2106384  "ANM_hero_Hades"   <- the animation blob
    0xE00    a record naming the character ("Hades")
    0xE78    u32 clip offsets, strictly increasing, relative to 0xE40
    0xE40    the ANM blob's data; clip i starts at 0xE40 + offsets[i]
             and its name is the ASCII run right there

On this file the table has **77 entries and every entry lands exactly on a named
clip**, e.g. ``hadesKnifeAttLhigh``, ``hadesKnifeAttRlow``,
``hadesKnifeAttShortRound``, ``hadesKnifeBlockEnter``, ``cshadesRip01Stab01``..
``06``, ``csHadesKnifeKill``. So a boss's move set is enumerable, and each move has
a known offset and span.

Only what is observed is exposed: clip names, offsets, spans and the fixed clip
header (E-059: name in a 0x38-byte field, then the size at +0x38). The *internal*
clip encoding (bone channels, keyframes) is [UNKNOWN] and is not interpreted here.
"""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass
from typing import List, Optional

TABLE_DEFAULT = 0xE78
BASE_DEFAULT = 0xE40
MAX_CLIP_OFFSET = 8 * 1024 * 1024
_NAME = re.compile(rb"[A-Za-z][A-Za-z0-9_]{2,60}")
COMMAND_NAMES = {1, 2, 3, 0x12, 0x15}

# Per-clip header, observed on R_HADES.WAD and R_HERCULES.WAD (E-059). The name is
# a fixed 0x38-byte, NUL-terminated field, exactly like a WAD directory record's;
# the clip's byte size follows it. Everything past the size is only structurally
# described, so no meaning beyond the offsets is claimed.
CLIP_HEADER_SIZE = 0x38          # fixed size of the name field
CLIP_SIZE_OFFSET = 0x38          # u32 clip size
CLIP_FLAGS_OFFSET = 0x3C         # u32, 0 on every observed clip
CLIP_FRAME_RATE_OFFSET = 0x6C    # f32, 1/30 or 1/15 observed
CLIP_SUB_FRAME_RATE_OFFSET = 0xA8  # f32, 1/60 on every observed clip
CLIP_SIZE_COPY_OFFSETS = (0x7C, 0x90, 0xA4)  # u32 copies of CLIP_SIZE_OFFSET
CLIP_HEADER_MIN = CLIP_SUB_FRAME_RATE_OFFSET + 4  # bytes needed to parse the header


class AnimError(ValueError):
    """Raised when a WAD's animation directory does not match the observed layout."""


@dataclass(frozen=True)
class Clip:
    """One animation clip: a name, its byte size and the directory span."""

    index: int
    name: str
    offset: int          # file offset of the clip's name
    span: int            # bytes to the next clip (upper bound for the last one)
    size: int = 0        # clip size from its header (+0x38); 0 when unreadable

    @property
    def end(self) -> int:
        return self.offset + self.size if self.size else self.offset + self.span

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return (f"[{self.index:>3}] 0x{self.offset:08X} size={self.size:>9,} "
                f"span={self.span:>9,}  {self.name}")


@dataclass(frozen=True)
class ClipHeader:
    """The fixed header of one animation clip (E-059).

    Only the name and the size are semantically verified. ``flags``,
    ``frame_rate`` and ``sub_frame_rate`` are recorded exactly as observed;
    ``size_copies`` holds the three redundant copies of the size.
    """

    offset: int          # file offset of the clip (its name field)
    name: str
    size: int            # u32 at +0x38
    flags: int           # u32 at +0x3C, 0 on every observed clip
    frame_rate: float    # f32 at +0x6C, 1/30 or 1/15 observed
    sub_frame_rate: float  # f32 at +0xA8, 1/60 on every observed clip
    size_copies: tuple   # u32s at +0x7C, +0x90, +0xA4 (equal the size)


def _read_u32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        return 0
    return struct.unpack_from("<I", data, offset)[0]


def _read_f32(data: bytes, offset: int) -> float:
    if offset < 0 or offset + 4 > len(data):
        return 0.0
    return struct.unpack_from("<f", data, offset)[0]


def parse_clip_header(data: bytes, offset: int) -> Optional[ClipHeader]:
    """Read the fixed per-clip header at ``offset``, or ``None`` if not one.

    Returns only observed values (E-059); no field meaning is asserted beyond the
    name and the size.
    """
    if offset < 0 or offset + CLIP_HEADER_MIN > len(data):
        return None
    name = clip_name_at(data, offset)
    if name is None:
        return None

    return ClipHeader(
        offset=offset,
        name=name,
        size=_read_u32(data, offset + CLIP_SIZE_OFFSET),
        flags=_read_u32(data, offset + CLIP_FLAGS_OFFSET),
        frame_rate=_read_f32(data, offset + CLIP_FRAME_RATE_OFFSET),
        sub_frame_rate=_read_f32(data, offset + CLIP_SUB_FRAME_RATE_OFFSET),
        size_copies=tuple(_read_u32(data, offset + o)
                          for o in CLIP_SIZE_COPY_OFFSETS),
    )


def read_clip_offsets(data: bytes, table: int = TABLE_DEFAULT) -> List[int]:
    """The strictly increasing u32 offsets of the clip directory."""
    offsets: List[int] = []
    at = table
    while at + 4 <= len(data):
        value = struct.unpack_from("<I", data, at)[0]
        if value == 0 or value > MAX_CLIP_OFFSET:
            break
        if offsets and value <= offsets[-1]:
            break
        offsets.append(value)
        at += 4
    return offsets


def clip_name_at(data: bytes, offset: int) -> Optional[str]:
    match = _NAME.match(data, offset)
    if not match:
        return None
    return match.group().decode("latin-1")


def parse_clips(data: bytes, table: int = TABLE_DEFAULT,
                base: int = BASE_DEFAULT) -> List[Clip]:
    """Every named clip in a WAD's animation directory, in file order."""
    offsets = read_clip_offsets(data, table)
    if not offsets:
        raise AnimError(f"no clip offsets found at 0x{table:X}")

    clips: List[Clip] = []
    for index, relative in enumerate(offsets):
        absolute = base + relative
        name = clip_name_at(data, absolute)
        if name is None:
            continue
        nxt = base + offsets[index + 1] if index + 1 < len(offsets) else len(data)
        span = max(0, nxt - absolute)
        # The header's own size is authoritative; fall back to the span when it is
        # absent (synthetic fixtures) or unreadable. For every non-final clip in
        # the two sampled WADs the two are equal (E-059).
        size = _read_u32(data, absolute + CLIP_SIZE_OFFSET)
        clips.append(Clip(index=index, name=name, offset=absolute,
                          span=span, size=size or span))
    return clips


def find_table(data: bytes, min_entries: int = 20) -> Optional[int]:
    """Locate the clip directory by signature **and validate it**.

    A candidate is only accepted when a good fraction of its offsets land exactly
    on a plausible clip name; a long increasing run on its own is not evidence (that
    is how an earlier version mis-fired on ``R_HERCULES.WAD``). Returns the offset of
    the first entry, or ``None``.
    """
    runs: List[tuple] = []
    run_start, run = None, 0
    at = 0x400
    limit = min(len(data) - 8, 0x400000)
    while at + 4 <= limit:
        value = struct.unpack_from("<I", data, at)[0]
        previous = struct.unpack_from("<I", data, at - 4)[0]
        if 0 < value <= MAX_CLIP_OFFSET and value > previous:
            if run == 0:
                run_start = at
            run += 1
        else:
            if run >= min_entries:
                runs.append((run_start, run))
            run = 0
        at += 4
    if run >= min_entries:
        runs.append((run_start, run))

    best, best_score = None, 0.0
    for start, _length in runs:
        offsets = read_clip_offsets(data, start)
        if len(offsets) < min_entries:
            continue
        # work out this candidate's base: the first entry must name a clip
        base = None
        for base_try in (BASE_DEFAULT, 0, 0x40, 0x80, 0x100):
            sample = offsets[:16]
            hits = sum(1 for rel in sample
                       if clip_name_at(data, base_try + rel) is not None)
            if hits >= max(2, int(0.8 * len(sample))):
                base = base_try
                break
        if base is None:
            continue
        named = sum(1 for rel in offsets if clip_name_at(data, base + rel) is not None)
        score = named / len(offsets)
        if score > best_score:
            best, best_score = start, score
    return best if best_score >= 0.8 else None
