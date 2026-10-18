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
section beginning at +0x15C; E-064: the data section opens with a typed record
preamble whose first record's tag and constant discriminator are E-061's two
"markers"; E-065: each preamble record's last u16 is a 16-byte-aligned,
strictly increasing **offset** into the clip's data section, and the first one
is the preamble's own length rounded up; E-066: those offsets name **typed
sub-blocks** -- the sub-block a record points at is typed by that record's tag,
the tag-0x16 sub-block always opens with 128 u16 ``0x30 * k``, and the tag-0x10
sub-block contains a *nested* preamble of the same shape; E-067: the nesting is
exactly two levels deep, the level-2 preamble may carry tag 0x19, and its
tag-0x16 table is 122/123 entries rather than 128; E-068: the u16 offset lists
inside the sub-blocks share a 0x30-byte stride -- every tag-0x10 block opens with
a value `== 0x10 (mod 0x30)`, the tag-0x16 `0x30 * k` prefix is residue 0x00, its
continuation is residue 0x20, and the word after that continuation is one of
0x1710/0x1800/0x3C00). The *internal* clip encoding (bone channels, keyframes)
is [UNKNOWN] and is not interpreted here.
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

# The data section opens with a typed record preamble (E-064). E-061's two
# "markers" are simply the first record's tag and its constant discriminator.
# Every record begins with a u16 tag and carries the constant u16 0x000C in its
# third slot; the records split into a *lead* group of 8-byte records
# (tag, arg, 0x000C, value) followed by two zero u16, a u16 ``count``, and a
# *tail* group of 10-byte records (tag, arg, 0x000C, value, extra) followed by a
# zero u16. Observed on all 123 clips of R_HADES.WAD and R_HERCULES.WAD: 115
# clips have four lead records, 8 (all with tag 0x17) have five; the tail carries
# 4, 5 or 7 records. No field is assigned a meaning here; the tags are treated as
# opaque ids.
CLIP_DATA_RECORD_DISCRIMINATOR = 0x000C
CLIP_DATA_LEAD_WORDS = 4
CLIP_DATA_TAIL_WORDS = 5
CLIP_DATA_LEAD_TAGS = (0x15, 0x16, 0x17, 0x18, 0x0B)
CLIP_DATA_TAIL_TAGS = (0x0B, 0x0F, 0x10, 0x1B, 0x1C, 0x1D, 0x1E)
CLIP_DATA_PREAMBLE_LIMIT = 0x100  # bytes read at most when parsing the preamble

# Each preamble record's last u16 is an **offset** into the clip's data section
# (base = clip.offset + CLIP_TAIL_END), not a scalar (E-065). On all 123 clips the
# offsets are strictly increasing, are multiples of 16, and the first one equals
# the preamble's own byte length rounded up to 16 -- so the records form a
# directory of 16-byte-aligned sub-blocks starting immediately after the preamble.
# The meaning of every sub-block is [UNKNOWN]; only the offset relation is claimed.
CLIP_DATA_ALIGNMENT = 0x10
CLIP_DATA_LEAD_TERMINATOR_WORDS = 2  # the two zero u16 between lead and count
CLIP_DATA_COUNT_WORDS = 1            # the u16 ``count``
CLIP_DATA_TAIL_TERMINATOR_WORDS = 1  # the final zero u16


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


@dataclass(frozen=True)
class ClipDataRecord:
    """One tagged record of a clip's data-section preamble (E-064).

    ``tag``, ``arg``, ``value`` (and ``extra`` for tail records) are the observed
    u16 fields. ``discriminator`` is the u16 that sits in the record's third slot;
    it is ``CLIP_DATA_RECORD_DISCRIMINATOR`` on every observed record. No field is
    assigned a meaning.
    """

    tag: int
    arg: int
    value: int
    discriminator: int
    extra: Optional[int] = None   # only tail records carry a fifth u16

    @property
    def discriminator_ok(self) -> bool:
        """The record's third u16 is the observed constant 0x000C (E-064)."""
        return self.discriminator == CLIP_DATA_RECORD_DISCRIMINATOR


@dataclass(frozen=True)
class ClipDataPreamble:
    """The typed record preamble at the start of a clip's data section (E-064).

    ``lead`` holds the 8-byte records before the two-zero terminator, ``count``
    the u16 that follows it, and ``tail`` the 10-byte records up to the final
    zero u16. Only observed values are exposed; the meaning of ``count`` and of
    every tag is [UNKNOWN]. Each record's last u16 is an **offset** into the
    clip's data section (E-065): strictly increasing, 16-byte aligned, and the
    first equals the preamble's byte length rounded up to 16.
    """

    offset: int
    lead: tuple
    count: int
    tail: tuple

    @property
    def lead_tags(self) -> tuple:
        return tuple(record.tag for record in self.lead)

    @property
    def tail_tags(self) -> tuple:
        return tuple(record.tag for record in self.tail)

    @property
    def discriminated_ok(self) -> bool:
        """Every record carries ``CLIP_DATA_RECORD_DISCRIMINATOR`` (E-064)."""
        return all(record.discriminator_ok
                   for record in self.lead + self.tail)

    @property
    def tags_known_ok(self) -> bool:
        """Every tag is one of the observed lead/tail tag ids (E-064)."""
        return (all(tag in CLIP_DATA_LEAD_TAGS for tag in self.lead_tags)
                and all(tag in CLIP_DATA_TAIL_TAGS for tag in self.tail_tags))

    @property
    def values(self) -> tuple:
        """Every record's last u16, lead records first (E-065).

        On all 123 censused clips these are strictly increasing offsets into the
        clip's data section; see :pyattr:`increasing_ok`.
        """
        return tuple(record.value for record in self.lead) \
            + tuple(record.value for record in self.tail)

    @property
    def word_count(self) -> int:
        """Number of u16 the preamble occupies, from its record counts (E-064)."""
        return (CLIP_DATA_LEAD_WORDS * len(self.lead)
                + CLIP_DATA_LEAD_TERMINATOR_WORDS
                + CLIP_DATA_COUNT_WORDS
                + CLIP_DATA_TAIL_WORDS * len(self.tail)
                + CLIP_DATA_TAIL_TERMINATOR_WORDS)

    @property
    def byte_length(self) -> int:
        """Bytes the preamble occupies (``2 * word_count``)."""
        return 2 * self.word_count

    @property
    def increasing_ok(self) -> bool:
        """The record offsets strictly increase in file order (E-065, 123/123)."""
        values = self.values
        return (len(values) >= 2
                and all(values[i] < values[i + 1] for i in range(len(values) - 1)))

    @property
    def aligned_ok(self) -> bool:
        """Every record offset is a multiple of 16 (E-065, 123/123 clips)."""
        values = self.values
        return bool(values) and all(value % CLIP_DATA_ALIGNMENT == 0
                                    for value in values)

    @property
    def first_offset_ok(self) -> bool:
        """``values[0]`` is the preamble's length rounded up to 16 (E-065)."""
        values = self.values
        if not values:
            return False
        rounded = (self.byte_length + CLIP_DATA_ALIGNMENT - 1) \
            & ~(CLIP_DATA_ALIGNMENT - 1)
        return values[0] == rounded

    def data_targets(self, data_offset: int = 0) -> tuple:
        """Absolute file offsets of the record targets (E-065).

        ``data_offset`` is the clip's data-section start (``clip.offset +
        CLIP_TAIL_END``); each target is ``data_offset + value``.
        """
        return tuple(data_offset + value for value in self.values)

    def invariants(self) -> dict:
        """The E-064/E-065 relations, each as a name -> bool. Evidence, not a verdict."""
        return {
            "discriminated": self.discriminated_ok,
            "tags_known": self.tags_known_ok,
            "increasing": self.increasing_ok,
            "aligned": self.aligned_ok,
            "first_offset": self.first_offset_ok,
        }


def parse_clip_data_preamble(data: bytes, offset: int,
                             limit: int = CLIP_DATA_PREAMBLE_LIMIT
                             ) -> Optional[ClipDataPreamble]:
    """Read the data-section preamble at ``offset``, or ``None`` if not one.

    ``offset`` is ``clip.offset + CLIP_TAIL_END``. The parse is strict: a record
    whose third u16 is not ``CLIP_DATA_RECORD_DISCRIMINATOR``, a missing
    terminator, or a truncated buffer returns ``None``. Returns observed values
    only (E-064); ``count`` and the tags have [UNKNOWN] meaning.
    """
    end = min(len(data), offset + limit)
    if offset < 0 or offset + 2 * (CLIP_DATA_LEAD_WORDS + 2) > end:
        return None

    def word(index: int) -> int:
        return struct.unpack_from("<H", data, offset + 2 * index)[0]

    lead: List[ClipDataRecord] = []
    index = 0
    while True:
        if offset + 2 * (index + CLIP_DATA_LEAD_WORDS) > end:
            return None
        tag, arg, disc, value = (word(index), word(index + 1),
                                 word(index + 2), word(index + 3))
        if tag == 0 and arg == 0:
            break
        if disc != CLIP_DATA_RECORD_DISCRIMINATOR:
            return None
        lead.append(ClipDataRecord(tag=tag, arg=arg, value=value,
                                   discriminator=disc))
        index += CLIP_DATA_LEAD_WORDS

    count = word(index + 2)
    index += 3
    tail: List[ClipDataRecord] = []
    while True:
        if offset + 2 * (index + CLIP_DATA_TAIL_WORDS) > end:
            return None
        tag, arg, disc, value, extra = (word(index), word(index + 1),
                                        word(index + 2), word(index + 3),
                                        word(index + 4))
        if tag == 0:
            break
        if disc != CLIP_DATA_RECORD_DISCRIMINATOR:
            return None
        tail.append(ClipDataRecord(tag=tag, arg=arg, value=value,
                                   discriminator=disc, extra=extra))
        index += CLIP_DATA_TAIL_WORDS

    return ClipDataPreamble(offset=offset, lead=tuple(lead), count=count,
                            tail=tuple(tail))


def maybe_clip_data_preamble(data: bytes,
                             offset: int) -> Optional[ClipDataPreamble]:
    """Like :func:`parse_clip_data_preamble` but forgiving of short input."""
    try:
        return parse_clip_data_preamble(data, offset)
    except (struct.error, ValueError):
        return None


# The sub-blocks a preamble record points at are **typed by the record's tag**
# (E-066). Two relations are verified on the 123 clips of R_HADES.WAD and
# R_HERCULES.WAD (read-only):
#   * the sub-block named by a tag-0x16 record always opens with exactly 128 u16
#     `0x30 * k` (k = 0..127) -- a 256-byte table spanning 0x1800 (123/123);
#   * the sub-block named by the last tail record (tag 0x10) contains a *nested*
#     data-section preamble of E-064/E-065's shape, at a 16-byte-aligned offset
#     64..208 bytes in (122/123; the exception is `attCestusCrush` in
#     R_HERCULES.WAD).
# Only those observed relations are exposed; the meaning of every tag and every
# sub-block payload stays [UNKNOWN].
CLIP_DATA_TAG16 = 0x16              # tag whose sub-block opens with the 128-entry table
CLIP_DATA_TAG16_PREFIX_WORDS = 128  # u16 entries in that table, 123/123 clips
CLIP_DATA_TAG16_STEP = 0x30         # the table's value at index k is step * k
CLIP_DATA_TAG10 = 0x10              # tag whose sub-block holds the nested preamble
CLIP_DATA_NESTED_MIN_RECORDS = 3    # min lead/tail for a nested parse (E-066)

# The clip data section recurses: the tag-0x10 sub-block holds a *nested* data
# section of the same shape, and its tag-0x10 sub-block holds none further, so the
# nesting is exactly two levels deep (E-067). The nested preamble keeps the
# E-064/E-065 shape with two additions: tag 0x19 is a lead tag seen *only* at the
# nested level, and the nested level's tag-0x16 sub-block opens with a `0x30 * k`
# table whose length is 123 (114 clips) or 122 (8 clips), not 128. Immediately
# after a `0x30 * k` table comes a second, strictly increasing, 16-byte-aligned
# u16 offset table beginning at 0x20 (E-067).
CLIP_DATA_NESTED_LEAD_TAG = 0x19    # lead tag observed only in the nested preamble
CLIP_DATA_NESTED_LEAD_TAGS = (0x0B, 0x15, 0x16, 0x17, 0x18, 0x19)
CLIP_DATA_NESTED_TAIL_TAGS = (0x0B, 0x0F, 0x10, 0x1B, 0x1C, 0x1D, 0x1E)
CLIP_DATA_MAX_DEPTH = 4             # recursion cap for clip_data_sections()
CLIP_DATA_SECOND_TABLE_FIRST = 0x20  # first value of the table after `0x30 * k`

# The u16 offset lists inside every data-section sub-block share a **0x30-byte
# (48-byte) stride** (E-068). Censused read-only on all 123 clips of R_HADES.WAD
# (77) and R_HERCULES.WAD (46), i.e. 245 tag-0x10 sub-blocks and 245 tag-0x16
# sub-blocks: every tag-0x10 sub-block opens with a u16 `== 0x10 (mod 0x30)`
# (245/245), the tag-0x16 `0x30 * k` prefix is residue 0x00, the continuation that
# follows it is residue 0x20, and the word after that continuation is one of
# 0x1710 / 0x1800 / 0x3C00 -- residue 0x00 (245/245). This is consistent with
# [INFERRED] 48-byte records whose fields sit at +0x00/+0x10/+0x20; the stride and
# the field meaning remain otherwise unproven. On 87/245 tag-0x16 blocks further
# residue-0x20 values occur later in the block, so the continuation is a first run,
# not always the whole set -- recorded honestly.
CLIP_DATA_STRIDE = 0x30                     # 48-byte stride of the offset lists
CLIP_DATA_STRIDE_FIELDS = (0x00, 0x10, 0x20)  # observed field residues
CLIP_DATA_TAG10_RESIDUE = 0x10              # every tag-0x10 opens with this residue
CLIP_DATA_TAG16_CONTINUATION_RESIDUE = 0x20  # residue of the post-`0x30 * k` run
CLIP_DATA_CONTINUATION_TERMINATORS = (0x1710, 0x1800, 0x3C00)  # == 0x30 * {123,128,320}


def tag16_prefix_length(payload: bytes) -> int:
    """Count leading u16 where ``payload`` equals ``0x30 * k`` (E-066).

    Scans from the sub-block's first byte and stops at the first u16 that differs
    from ``CLIP_DATA_TAG16_STEP * k`` (or at a trailing odd byte). On all 123 real
    clips the tag-0x16 sub-block yields exactly ``CLIP_DATA_TAG16_PREFIX_WORDS``.
    """
    length = 0
    while 2 * (length + 1) <= len(payload):
        value = struct.unpack_from("<H", payload, 2 * length)[0]
        if value != CLIP_DATA_TAG16_STEP * length:
            break
        length += 1
    return length


def tag16_offset_table(payload: bytes) -> tuple:
    """The offset table that follows a tag-0x16 sub-block's ``0x30 * k`` table (E-067).

    On the real clips the ``0x30 * k`` table is immediately followed by a second
    table of u16 values that strictly increase and are all multiples of 16,
    beginning at ``CLIP_DATA_SECOND_TABLE_FIRST`` (0x20). This returns the leading
    run of such values; it stops at the first value that is zero, misaligned or
    not greater than its predecessor. The meaning of the values is [UNKNOWN] — only
    the run is observed.
    """
    start = tag16_prefix_length(payload)
    values = []
    at = 2 * start
    while at + 2 <= len(payload):
        value = struct.unpack_from("<H", payload, at)[0]
        if value == 0 or value % CLIP_DATA_ALIGNMENT != 0:
            break
        if values and value <= values[-1]:
            break
        values.append(value)
        at += 2
    return tuple(values)


def stride_residue(value: int) -> int:
    """``value`` modulo the observed 0x30-byte stride (E-068)."""
    return value % CLIP_DATA_STRIDE


def stride_offset_run(payload: bytes, start_word: int = 0,
                      residue: int = CLIP_DATA_TAG16_CONTINUATION_RESIDUE
                      ) -> tuple:
    """The leading run of u16 equal to ``residue`` mod 0x30 and strictly increasing (E-068).

    Starts at u16 index ``start_word`` and stops at the first value whose
    ``% CLIP_DATA_STRIDE`` differs from ``residue`` or that does not exceed its
    predecessor. With the observed residues (0x10/0x20) every value in the result
    is a multiple of 16. As with :func:`tag16_offset_table`, only the run is
    observed; the values are [UNKNOWN] offsets.
    """
    values = []
    prev = None
    at = 2 * start_word
    while at + 2 <= len(payload):
        value = struct.unpack_from("<H", payload, at)[0]
        if value % CLIP_DATA_STRIDE != residue:
            break
        if prev is not None and value <= prev:
            break
        values.append(value)
        prev = value
        at += 2
    return tuple(values)


def find_nested_preamble(payload: bytes,
                         min_records: int = CLIP_DATA_NESTED_MIN_RECORDS
                         ) -> Optional[tuple]:
    """First nested data-section preamble in ``payload`` as ``(offset, preamble)``.

    A candidate counts only when it parses strictly under E-064's rules *and* holds
    at least ``min_records`` lead and tail records; the degenerate all-zero start
    of a sub-block therefore cannot match. Returns ``None`` when nothing qualifies
    (E-066: the tag-0x10 sub-block qualifies on 122/123 clips).
    """
    span = 2 * (CLIP_DATA_LEAD_WORDS * min_records + 3)
    for offset in range(0, max(0, len(payload) - span), 2):
        preamble = parse_clip_data_preamble(payload, offset)
        if preamble is None:
            continue
        if (len(preamble.lead) >= min_records
                and len(preamble.tail) >= min_records):
            return offset, preamble
    return None


@dataclass(frozen=True)
class ClipSubBlock:
    """One sub-block named by a preamble record (E-065), typed by its tag (E-066).

    ``payload`` holds the sub-block's bytes; ``size`` is its length in the file.
    The tag/content relations are exposed as helpers, not as semantics: no field
    of any sub-block is assigned a meaning.
    """

    tag: int        # the preamble record's tag that names this sub-block
    offset: int     # absolute file offset of the sub-block
    size: int       # bytes to the next sub-block, or to the clip end for the last
    payload: bytes  # the sub-block's bytes

    @property
    def tag16_prefix_length(self) -> int:
        """Leading ``0x30 * k`` run length (E-066)."""
        return tag16_prefix_length(self.payload)

    @property
    def tag16_offset_table(self) -> tuple:
        """The increasing 16-byte-aligned table after the ``0x30 * k`` run (E-067)."""
        return tag16_offset_table(self.payload)

    @property
    def first_word(self) -> int:
        """The sub-block's first u16, or 0 when it is empty (E-068)."""
        return _read_u16(self.payload, 0)

    @property
    def first_word_residue(self) -> int:
        """First u16 modulo the 0x30 stride; a tag-0x10 block is always 0x10 (E-068)."""
        return self.first_word % CLIP_DATA_STRIDE

    @property
    def tag16_continuation(self) -> tuple:
        """The residue-0x20 run after a tag-0x16 ``0x30 * k`` prefix (E-068)."""
        return stride_offset_run(self.payload, self.tag16_prefix_length,
                                 CLIP_DATA_TAG16_CONTINUATION_RESIDUE)

    @property
    def tag16_continuation_terminator(self) -> Optional[int]:
        """The u16 right after a tag-0x16 continuation run, or ``None`` (E-068)."""
        at = 2 * (self.tag16_prefix_length + len(self.tag16_continuation))
        if at + 2 > len(self.payload):
            return None
        return struct.unpack_from("<H", self.payload, at)[0]

    @property
    def tag10_residue_ok(self) -> bool:
        """A tag-0x10 block opens with a u16 ``== 0x10 (mod 0x30)`` (E-068, 245/245)."""
        return (self.tag == CLIP_DATA_TAG10
                and self.first_word_residue == CLIP_DATA_TAG10_RESIDUE)

    @property
    def tag16_terminator_ok(self) -> bool:
        """A tag-0x16 continuation ends in one of the three observed words (E-068)."""
        return self.tag16_continuation_terminator in CLIP_DATA_CONTINUATION_TERMINATORS

    def nested_preamble(self, min_records: int = CLIP_DATA_NESTED_MIN_RECORDS):
        """The nested preamble inside this sub-block, or ``None`` (E-066)."""
        return find_nested_preamble(self.payload, min_records)


@dataclass(frozen=True)
class ClipSubBlocks:
    """A clip's data section split into the sub-blocks its preamble names (E-066).

    ``blocks`` is in file order and one entry per preamble record, so its tags
    match ``ClipDataPreamble``'s records. The two verified relations are reported
    as evidence: ``tag16_prefix_ok`` and ``nested_ok``. ``end`` is the bound the
    last block runs to; it is needed to recurse into the tag-0x10 sub-block (E-067).
    """

    offset: int      # the clip's data-section start
    blocks: tuple    # ClipSubBlock, in file order
    end: int = 0     # bytes bound of the data section (last block's stop)

    @property
    def tags(self) -> tuple:
        return tuple(block.tag for block in self.blocks)

    def of_tag(self, tag: int) -> tuple:
        """Every sub-block named by a record carrying ``tag`` (E-066)."""
        return tuple(block for block in self.blocks if block.tag == tag)

    @property
    def tag16_prefix_ok(self) -> bool:
        """The tag-0x16 sub-block opens with the 128-entry table (E-066, 123/123)."""
        return any(block.tag == CLIP_DATA_TAG16
                   and block.tag16_prefix_length >= CLIP_DATA_TAG16_PREFIX_WORDS
                   for block in self.blocks)

    @property
    def tag10_residue_ok(self) -> bool:
        """Every tag-0x10 sub-block opens with a u16 ``== 0x10 (mod 0x30)`` (E-068)."""
        blocks = self.of_tag(CLIP_DATA_TAG10)
        return bool(blocks) and all(block.tag10_residue_ok for block in blocks)

    @property
    def tag16_continuation_ok(self) -> bool:
        """Every tag-0x16 continuation ends in an observed terminator (E-068)."""
        blocks = self.of_tag(CLIP_DATA_TAG16)
        return bool(blocks) and all(block.tag16_terminator_ok for block in blocks)

    def nested_preamble(self, min_records: int = CLIP_DATA_NESTED_MIN_RECORDS):
        """The nested preamble inside the tag-0x10 sub-block, or ``None`` (E-066)."""
        for block in self.of_tag(CLIP_DATA_TAG10):
            found = block.nested_preamble(min_records)
            if found is not None:
                return found
        return None

    def nested_data_section(self, data: bytes,
                            min_records: int = CLIP_DATA_NESTED_MIN_RECORDS
                            ) -> Optional["ClipSubBlocks"]:
        """The data section nested inside the tag-0x10 sub-block, or ``None`` (E-067).

        Finds the nested preamble (E-066) and splits it with the same reader as the
        outer data section, bounded by the tag-0x10 sub-block. Returns ``None`` when
        there is no nested preamble, so recursion terminates exactly where the real
        clips stop (E-067: two levels).
        """
        for block in self.of_tag(CLIP_DATA_TAG10):
            found = block.nested_preamble(min_records)
            if found is None:
                continue
            relative, _preamble = found
            return parse_data_section(data, block.offset + relative,
                                      block.offset + block.size)
        return None

    @property
    def nested_ok(self) -> bool:
        """A nested preamble sits in the tag-0x10 sub-block (E-066, 122/123)."""
        return self.nested_preamble() is not None

    def invariants(self) -> dict:
        """The E-066 relations, each as a name -> bool. Evidence, not a verdict."""
        return {"tag16_prefix": self.tag16_prefix_ok,
                "nested_preamble": self.nested_ok}


def parse_data_section(data: bytes, offset: int,
                       end: int) -> Optional[ClipSubBlocks]:
    """Split the data section whose preamble sits at ``offset``, bounded by ``end``.

    This is the general form of :func:`parse_clip_sub_blocks`: the preamble at
    ``offset`` names one sub-block per record (E-064/E-065), each running to the
    next record's target or to ``end`` for the last. It is used both for a clip's
    outer data section and for the nested one inside a tag-0x10 sub-block (E-067).
    Returns ``None`` when the preamble cannot be parsed or names no records.
    """
    preamble = parse_clip_data_preamble(data, offset)
    if preamble is None or not (preamble.lead or preamble.tail):
        return None
    records = tuple(preamble.lead) + tuple(preamble.tail)
    targets = preamble.data_targets(offset)
    stop_bound = min(end, len(data)) if end else len(data)

    blocks = []
    for index, (record, start) in enumerate(zip(records, targets)):
        stop = targets[index + 1] if index + 1 < len(targets) else stop_bound
        stop = min(stop, stop_bound)
        payload = data[start:stop] if 0 <= start <= stop else b""
        blocks.append(ClipSubBlock(tag=record.tag, offset=start,
                                   size=max(0, stop - start), payload=payload))
    return ClipSubBlocks(offset=offset, blocks=tuple(blocks), end=stop_bound)


def parse_clip_sub_blocks(data: bytes, clip) -> Optional[ClipSubBlocks]:
    """Split a clip's data section into the sub-blocks its preamble names (E-066).

    Reads the preamble at ``clip.offset + CLIP_TAIL_END`` (E-064/E-065) and returns
    one :class:`ClipSubBlock` per record, in file order. A block runs to the next
    record's target, or to the clip's end (``clip.end``) for the last one. Returns
    ``None`` when the preamble cannot be parsed or names no records; a target
    outside the buffer yields an empty payload rather than raising.
    """
    return parse_data_section(data, clip.offset + CLIP_TAIL_END, clip.end)


def clip_data_sections(data: bytes, clip,
                       max_depth: int = CLIP_DATA_MAX_DEPTH) -> tuple:
    """A clip's data section and its nested ones, outermost first (E-067).

    Follows the tag-0x10 nesting (E-066/E-067) up to ``max_depth`` sections. On the
    real clips the chain is exactly two long on 122/123 clips and one long for
    ``attCestusCrush``; the walk stops there rather than on the cap. Returns an empty
    tuple when the clip has no parseable data section.
    """
    sections = []
    current = parse_clip_sub_blocks(data, clip)
    while current is not None and len(sections) < max_depth:
        sections.append(current)
        current = current.nested_data_section(data)
    return tuple(sections)


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
