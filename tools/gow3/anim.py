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
header (E-059: name in a 0x38-byte field, then the size at +0x38; E-060: the size
is repeated at three further offsets, the frame rate at three further offsets plus
its reciprocal, and the clip frame count and loop flag; E-061: the descriptor's
per-clip tail at +0x124..+0x148, with five 16-byte-aligned fields, and the data
section beginning at +0x15C). The *internal* clip encoding (bone channels,
keyframes) is [UNKNOWN] and is not interpreted here.
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

# Per-clip header, observed on R_HADES.WAD and R_HERCULES.WAD (E-059, E-060). The
# name is a fixed 0x38-byte, NUL-terminated field, exactly like a WAD directory
# record's; the clip's byte size follows it. Everything past the size is only
# structurally described, so no meaning beyond the verified relations is claimed.
CLIP_HEADER_SIZE = 0x38          # fixed size of the name field
CLIP_SIZE_OFFSET = 0x38          # u32 clip size
CLIP_FLAGS_OFFSET = 0x3C         # u32, 0 on every observed clip
CLIP_FRAME_RATE_OFFSET = 0x6C    # f32, 1/30 or 1/15 observed
CLIP_SUB_FRAME_RATE_OFFSET = 0xA8  # f32, 1/60 on every observed clip
CLIP_SIZE_COPY_OFFSETS = (0x7C, 0x90, 0xA4)  # u32 copies of CLIP_SIZE_OFFSET
CLIP_RATE_COPY_OFFSETS = (0x80, 0x94, 0x110)  # f32 copies of CLIP_FRAME_RATE_OFFSET
CLIP_RATE_RECIPROCAL_OFFSET = 0x10C  # f32 == 1 / f32@CLIP_FRAME_RATE_OFFSET
CLIP_LOOP_OFFSET = 0xF4          # u32; low u16 is 1 on the observed loop clips
CLIP_FRAME_COUNT_OFFSET = 0xF6   # u16; [INFERRED] frame count (E-060)
CLIP_SAMPLE_RATE_OFFSET = 0x114  # f32 == float32(1 / (frames - 1))

# Every offset that carries the clip size / frame rate. The size sits at four
# offsets and the frame rate at four; no other u32 in 0x00..0x123 matches either
# value on the 123 clips censused in E-060.
CLIP_SIZE_OFFSETS = (CLIP_SIZE_OFFSET,) + CLIP_SIZE_COPY_OFFSETS
CLIP_FRAME_RATE_OFFSETS = (CLIP_FRAME_RATE_OFFSET,) + CLIP_RATE_COPY_OFFSETS

CLIP_HEADER_MIN = CLIP_SAMPLE_RATE_OFFSET + 4  # bytes needed to parse the header

# The fixed descriptor continues past CLIP_HEADER_MIN (E-061). Censusing
# 0x120..0x15B on all 123 clips of R_HADES.WAD and R_HERCULES.WAD shows the
# descriptor ends at 0x158 and the per-clip data section begins at 0x15C. Within
# 0x124..0x14B three u32s are constant and seven vary per clip; five of the seven
# are 16-byte aligned and inside the file on 123/123 clips (the other two are
# small, unaligned values).
CLIP_TAIL_END = 0x15C            # first byte of the per-clip data section
CLIP_TAIL_MIN = CLIP_TAIL_END    # bytes needed to read the descriptor tail
CLIP_TAIL_VALUE_OFFSETS = (0x124, 0x12C, 0x134, 0x13C, 0x140, 0x144, 0x148)
CLIP_TAIL_ALIGNED_OFFSETS = (0x124, 0x12C, 0x134, 0x13C, 0x144)
CLIP_TAIL_CONSTANTS = ((0x128, 0x00800000), (0x130, 0x00010001),
                       (0x138, 0x037B0000))
CLIP_TAIL_SENTINEL_OFFSETS = (0x14C, 0x150, 0x154, 0x158)
CLIP_TAIL_SENTINEL = 0xFFFFFFFF
CLIP_DATA_MARKER = 0x15          # u16 at 0x15C (21) on 123/123 clips
CLIP_DATA_SECOND_MARKER = 0x0C   # u16 at 0x160 (12) on 123/123 clips


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
    """The fixed header of one animation clip (E-059, E-060).

    Only the name, the size and the relations verified in E-060 are semantic:
    ``size`` is repeated at three further offsets, ``frame_rate`` at three further
    offsets, ``frame_count_rate`` is its reciprocal, and ``sample_rate`` equals
    ``float32(1 / (frames - 1))``. ``frames`` is [INFERRED] to be the clip's frame
    count from that relation; ``loop_flag`` is 1 on the eleven observed looping
    clips and 0 elsewhere, also [INFERRED].
    """

    offset: int          # file offset of the clip (its name field)
    name: str
    size: int            # u32 at +0x38, repeated at +0x7C/+0x90/+0xA4
    flags: int           # u32 at +0x3C, 0 on every observed clip
    frame_rate: float    # f32 at +0x6C, repeated at +0x80/+0x94/+0x110
    sub_frame_rate: float  # f32 at +0xA8, 1/60 on every observed clip
    size_copies: tuple   # u32s at +0x7C, +0x90, +0xA4 (equal the size)
    frame_count_rate: float = 0.0  # f32 at +0x10C, the reciprocal of frame_rate
    frames: int = 0      # u16 at +0xF6 ([INFERRED] frame count)
    loop_flag: int = 0   # low u16 of the u32 at +0xF4 ([INFERRED] loop flag)
    sample_rate: float = 0.0  # f32 at +0x114, float32(1 / (frames - 1))
    rate_copies: tuple = ()   # f32s at +0x6C, +0x80, +0x94, +0x110

    @property
    def size_repeat_ok(self) -> bool:
        """All four size offsets hold the same value (E-060, 123/123 clips)."""
        return self.size != 0 and all(c == self.size for c in self.size_copies)

    @property
    def rate_repeat_ok(self) -> bool:
        """All four frame-rate offsets hold the same value (E-060)."""
        return bool(self.rate_copies) and all(r == self.frame_rate
                                              for r in self.rate_copies)

    @property
    def reciprocal_ok(self) -> bool:
        """``frame_count_rate * frame_rate == 1`` (E-060, 123/123 clips).

        The stored pair is ``(30.0, float32(1/30))``, whose product is 1 to
        within binary32 rounding (observed worst case ~5.3e-8), so the relation
        is checked with a 1e-6 absolute tolerance.
        """
        return (self.frame_rate > 0
                and abs(self.frame_count_rate * self.frame_rate - 1.0) <= 1e-6)

    @property
    def sample_rate_ok(self) -> bool:
        """``sample_rate == float32(1 / (frames - 1))`` (E-060, 123/123 clips)."""
        return self.frames > 1 and self.sample_rate == expected_sample_rate(self.frames)

    def invariants(self) -> dict:
        """The E-060 relations, each as a name -> bool. Evidence, not a verdict."""
        return {
            "size_repeat": self.size_repeat_ok,
            "rate_repeat": self.rate_repeat_ok,
            "rate_reciprocal": self.reciprocal_ok,
            "sample_rate": self.sample_rate_ok,
        }


def float32(value: float) -> float:
    """``value`` rounded to the nearest IEEE-754 binary32, as a Python float."""
    return struct.unpack("<f", struct.pack("<f", value))[0]


def expected_sample_rate(frames: int) -> float:
    """``float32(1 / (frames - 1))`` -- the value observed at +0x114 (E-060)."""
    if frames <= 1:
        return 0.0
    return float32(1.0 / (frames - 1))


@dataclass(frozen=True)
class ClipDescriptorTail:
    """The per-clip fields at the end of a clip's fixed descriptor (E-061).

    ``fields`` holds the seven per-clip u32s of ``CLIP_TAIL_VALUE_OFFSETS`` as
    ``(offset, value)`` pairs. Five of those offsets are 16-byte aligned on all
    123 censused clips; ``aligned_ok`` reports that, not a meaning. ``constants``
    and ``sentinel`` are the three constant u32s and the four ``0xFFFFFFFF``
    sentinels; ``markers_ok`` checks the two u16 values that open the data
    section. No semantics are asserted: the aligned values behave like offsets
    into a shared pool (clips share ``+0x12C`` values) but that is [INFERRED].
    """

    offset: int                    # file offset of the clip (its name field)
    fields: tuple                  # ((field offset, value), ...) per CLIP_TAIL_VALUE_OFFSETS
    constants: tuple               # the three u32s of CLIP_TAIL_CONSTANTS
    sentinel: tuple                # the four u32s of CLIP_TAIL_SENTINEL_OFFSETS
    data_marker: int               # u16 at CLIP_TAIL_END
    second_marker: int             # u16 at CLIP_TAIL_END + 4

    @property
    def aligned_values(self) -> tuple:
        """Values of the five offsets that are 16-byte aligned on 123/123 clips."""
        return tuple(value for field, value in self.fields
                     if field in CLIP_TAIL_ALIGNED_OFFSETS)

    @property
    def aligned_ok(self) -> bool:
        """Every ``CLIP_TAIL_ALIGNED_OFFSETS`` value is a multiple of 16 (E-061)."""
        aligned = [value for field, value in self.fields
                   if field in CLIP_TAIL_ALIGNED_OFFSETS]
        return bool(aligned) and all(value % 16 == 0 for value in aligned)

    @property
    def constants_ok(self) -> bool:
        """The three interleaved constants match E-061 (123/123 clips)."""
        return tuple(self.constants) == tuple(value for _, value in CLIP_TAIL_CONSTANTS)

    @property
    def sentinel_ok(self) -> bool:
        """All four sentinel u32s are ``CLIP_TAIL_SENTINEL`` (E-061)."""
        return bool(self.sentinel) and all(value == CLIP_TAIL_SENTINEL
                                           for value in self.sentinel)

    @property
    def markers_ok(self) -> bool:
        """The data section opens with the two observed u16 markers (E-061)."""
        return (self.data_marker == CLIP_DATA_MARKER
                and self.second_marker == CLIP_DATA_SECOND_MARKER)

    def invariants(self) -> dict:
        """The E-061 relations, each as a name -> bool. Evidence, not a verdict."""
        return {
            "aligned": self.aligned_ok,
            "constants": self.constants_ok,
            "sentinel": self.sentinel_ok,
            "markers": self.markers_ok,
        }


def parse_clip_descriptor_tail(data: bytes, offset: int) -> Optional[ClipDescriptorTail]:
    """Read the descriptor tail at ``offset``, or ``None`` if not readable.

    Returns only observed values (E-061); the alignment of five fields is
    reported as a property, and no field is assigned a meaning.
    """
    if offset < 0 or offset + CLIP_TAIL_MIN > len(data):
        return None
    return ClipDescriptorTail(
        offset=offset,
        fields=tuple((field, _read_u32(data, offset + field))
                     for field in CLIP_TAIL_VALUE_OFFSETS),
        constants=tuple(_read_u32(data, offset + field)
                        for field, _ in CLIP_TAIL_CONSTANTS),
        sentinel=tuple(_read_u32(data, offset + field)
                       for field in CLIP_TAIL_SENTINEL_OFFSETS),
        data_marker=_read_u16(data, offset + CLIP_TAIL_END),
        second_marker=_read_u16(data, offset + CLIP_TAIL_END + 4),
    )


def maybe_clip_descriptor_tail(data: bytes,
                               offset: int) -> Optional[ClipDescriptorTail]:
    """Like :func:`parse_clip_descriptor_tail` but forgiving of short input."""
    try:
        return parse_clip_descriptor_tail(data, offset)
    except (struct.error, ValueError):
        return None


def _read_u32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        return 0
    return struct.unpack_from("<I", data, offset)[0]


def _read_u16(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 2 > len(data):
        return 0
    return struct.unpack_from("<H", data, offset)[0]


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
        frame_count_rate=_read_f32(data, offset + CLIP_RATE_RECIPROCAL_OFFSET),
        frames=struct.unpack_from("<H", data, offset + CLIP_FRAME_COUNT_OFFSET)[0],
        loop_flag=struct.unpack_from("<H", data, offset + CLIP_LOOP_OFFSET)[0],
        sample_rate=_read_f32(data, offset + CLIP_SAMPLE_RATE_OFFSET),
        rate_copies=tuple(_read_f32(data, offset + o)
                          for o in CLIP_FRAME_RATE_OFFSETS),
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
