"""DMC3 ``MOD `` chunk header reader.

``MOD `` chunks are the plain-tagged model/mesh payloads inside a PAC
container (evidence E-002).  Only the header fields that are **observed**
across real archives are exposed here; the vertex/index/weight/layout
semantics of the payload body remain open (issue F1).

Header layout as read from real files, all integers little-endian::

    +0x00  char[4]  "MOD "
    +0x04  f32      scale-like constant (1.0099… in every observed chunk)
    +0x08  u32      0 in every observed chunk
    +0x0C  u32      0 in every observed chunk   ([UNKNOWN] purpose)
    +0x10  u32      varies per mesh             (e.g. 0x10101, 0x103180b)
    +0x14  u32      varies per mesh             (e.g. 0xAF258; 0xF4240 in 187/286)
    +0x18  u32      0 in every observed chunk
    +0x1C  u32      0 in every observed chunk   ([UNKNOWN] purpose)
    +0x20  u32      varies per mesh             (e.g. 0x160, 0x29B30)
    +0x24..  payload body                      [UNKNOWN] layout

See docs/EVIDENCE.md E-030 for the raw-byte observations and docs/FORMATS.md
§5 for the spec.  This module never writes into a game installation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .pac import ALIGNMENT, Chunk, align_up, f32, u16, u32

TAG_MODEL = b"MOD "
"""The plain chunk tag that identifies a ``MOD `` chunk."""

HEADER_SIZE = 0x24
"""Header size covered by this reader (the body beyond it is uninterpreted)."""


@dataclass(frozen=True)
class ModHeader:
    """Fields of a ``MOD `` chunk header backed by evidence (E-030).

    All u32 fields below are **verified bytes**; only the constant-ness of
    some of them (285/286 chunks for ``scale``) reaches [INFERRED].
    The varying fields' meanings are [UNKNOWN] and deliberately not named
    beyond their offset.
    """

    scale: float
    """``+0x04`` — 1.0099… in 285/286 chunks; 1.0 in the remaining one."""

    field_08: int
    """``+0x08`` — 0 in every observed chunk."""

    field_0c: int
    """``+0x0C`` — 0 in every observed chunk. Purpose [UNKNOWN]."""

    field_10: int
    """``+0x10`` — varies per mesh (e.g. 0x10101, 0x103180B). Meaning [UNKNOWN]."""

    field_14: int
    """``+0x14`` — varies per mesh (e.g. 0xAF258; 0xF4240 x187). Meaning [UNKNOWN]."""

    field_18: int
    """``+0x18`` — 0 in every observed chunk."""

    field_1c: int
    """``+0x1C`` — 0 in every observed chunk. Purpose [UNKNOWN]."""

    field_20: int
    """``+0x20`` — varies per mesh (e.g. 0x160, 0x29B30). Meaning [UNKNOWN]."""

    @classmethod
    def parse(cls, chunk: Chunk) -> "ModHeader":
        """Parse the header of a plain-tagged ``MOD `` chunk."""
        if chunk.tag != TAG_MODEL:
            raise ValueError(
                f"chunk is not a MOD payload (tag={chunk.tag!r})"
            )
        data = chunk.data
        if len(data) < HEADER_SIZE:
            raise ValueError(
                f"MOD chunk only {len(data)} bytes, need {HEADER_SIZE} for the header"
            )
        return cls(
            scale=f32(data, 0x04),
            field_08=u32(data, 0x08),
            field_0c=u32(data, 0x0C),
            field_10=u32(data, 0x10),
            field_14=u32(data, 0x14),
            field_18=u32(data, 0x18),
            field_1c=u32(data, 0x1C),
            field_20=u32(data, 0x20),
        )


def maybe_mod_header(chunk: Chunk) -> Optional[ModHeader]:
    """Like :meth:`ModHeader.parse` but returns ``None`` for invalid chunks."""
    try:
        return ModHeader.parse(chunk)
    except (ValueError, IndexError):
        return None


# ---------------------------------------------------------------------------
# Payload body (the part of issue F1 that is still [UNKNOWN])
# ---------------------------------------------------------------------------

BODY_PREFIX_SIZE = 0x60
"""Size of the decoded body prefix (through ``repeat`` at body +0x5C)."""

BODY_TAG_OFFSET = 0x1C
"""Body-relative offset of the leading **tagged count** u32 (evidence E-091)."""

BODY_TAG_NAMESPACE = 0x8000
"""High nibble of every observed tag at :data:`BODY_TAG_OFFSET` (E-091)."""

BODY_TAG_MASK = 0xF000
"""Mask selecting the tag's namespace nibble."""


@dataclass(frozen=True)
class ModBodyPrefix:
    """Decoded prefix of a ``MOD `` payload body (evidence E-031, E-091).

    The body starts at chunk +0x24, immediately after the :class:`ModHeader`.
    Every field below is an **observation**: its bytes are consistent across the
    ``MOD `` chunks in the install, but its *meaning* is [UNKNOWN] and is
    deliberately not named beyond its offset.  This is the first decoded field
    of the payload body; the vertex/index/weight layout beyond it remains open
    (issue F1).

    **E-091 correction to E-031.** The ``u16`` "marker" at body +0x1C and the
    ``u16`` "count" at body +0x1E are not two adjacent fields: they are the two
    halves of **one little-endian u32** ``(count << 16) | tag``.  Across all
    **286** ``MOD `` chunks in the install the low half (``tag``) is a
    ``0x8000``-namespace value — ``0x8001`` x279, ``0x8002`` x4, ``0x8201`` x2,
    ``0x8005`` x1 — and the high half is exactly the count E-031 recorded.

    **E-092 supersedes the "prefix" framing.** These bytes are not a bespoke
    prefix: they are the first 0x40-byte descriptor of the body's descriptor
    array (see :class:`ModBodyDirectory`).  ``tag_word``/``field_24``/
    ``field_2c`` are descriptor 0's fields, and ``vector``/``repeat`` actually
    belong to descriptor 1 (body +0x4C = 0x40 + 0x0C, body +0x5C = 0x40 + 0x1C).
    """

    tag_word: int
    """Body +0x1C (chunk +0x40): u32, ``(count << 16) | tag``.  See :attr:`tag`
    and :attr:`count`.  Meaning of the tag beyond its ``0x8000`` namespace is
    [UNKNOWN]."""

    field_24: int
    """Body +0x24 (chunk +0x48): u32, varies per mesh (768, 192, 128, 128).
    A multiple of 64 in 375/623 tagged records; meaning [UNKNOWN]."""

    field_2c: int
    """Body +0x2C (chunk +0x50): u32, varies per mesh.  In slot 23 the bytes
    read as ``02 00 12 00`` (either one u32 or two u16s); meaning [UNKNOWN]."""

    vector: tuple[float, float, float, float]
    """Body +0x4C (chunk +0x70): four little-endian f32s, vector/quaternion-like
    (e.g. slot 23: -0.196, 0.0, 42.07, 73.57).  Meaning [UNKNOWN]."""

    repeat: int
    """Body +0x5C (chunk +0x80): u32.  Equals ``count`` for slots 23/25 but not
    for slot 1 (0x01418002) or slot 12 (0x012D8001), so it is an independent
    field.  Meaning [UNKNOWN]."""

    @property
    def tag(self) -> int:
        """Low u16 of :attr:`tag_word` — the leading tag (E-091)."""
        return self.tag_word & 0xFFFF

    @property
    def marker(self) -> int:
        """Alias for :attr:`tag`, kept for the E-031 name."""
        return self.tag_word & 0xFFFF

    @property
    def count(self) -> int:
        """High u16 of :attr:`tag_word` — the E-031 count."""
        return (self.tag_word >> 16) & 0xFFFF

    @property
    def tag_in_namespace(self) -> bool:
        """True when :attr:`tag`'s high nibble is ``0x8`` (286/286 chunks, E-091)."""
        return (self.tag & BODY_TAG_MASK) == BODY_TAG_NAMESPACE

    @classmethod
    def parse(cls, body: bytes) -> "ModBodyPrefix":
        """Parse the body prefix of a ``MOD `` chunk.

        ``body`` is the payload starting at chunk +0x24
        (``chunk.data[ModHeader.HEADER_SIZE:]``).
        """
        if len(body) < BODY_PREFIX_SIZE:
            raise ValueError(
                f"MOD body only {len(body)} bytes, need {BODY_PREFIX_SIZE} for the prefix"
            )
        return cls(
            tag_word=u32(body, BODY_TAG_OFFSET),
            field_24=u32(body, 0x24),
            field_2c=u32(body, 0x2C),
            vector=(
                f32(body, 0x4C),
                f32(body, 0x50),
                f32(body, 0x54),
                f32(body, 0x58),
            ),
            repeat=u32(body, 0x5C),
        )


def maybe_mod_body_prefix(body: bytes) -> Optional[ModBodyPrefix]:
    """Like :meth:`ModBodyPrefix.parse` but returns ``None`` on short input."""
    try:
        return ModBodyPrefix.parse(body)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Payload body: the leading fixed-size descriptor array (E-092)
# ---------------------------------------------------------------------------
#
# E-031/E-091 read the *first* record only, at body +0x00..+0x5F.  Reading the
# whole body shows those bytes are not a bespoke prefix: the body opens with an
# **array of 0x40-byte descriptors**.  ``ModBodyPrefix``'s fields are simply
# descriptor 0 (``tag_word`` at +0x1C, ``field_24`` at +0x24, ``field_2c`` at
# +0x2C) and the *vector* of descriptor 1 (+0x4C = 0x40 + 0x0C) plus
# descriptor 1's ``tag_word`` (+0x5C = 0x40 + 0x1C), which is why E-091 saw the
# tagged shape again at body +0x5C in 188/286 chunks (= every chunk with more
# than two descriptors).

BODY_DESCRIPTOR_SIZE = 0x40
"""Byte size of one ``MOD `` body descriptor (E-092)."""

BODY_DESCRIPTOR_ARRAY_OFFSET = 0x24
"""Body offset of the u32 that holds the descriptor array's byte size (E-092).
For 279/286 chunks this is exactly ``count * 0x40``; seven chunks (all in
``id430.pac`` / ``id470.pac``) carry an extra :data:`BODY_DESCRIPTOR_SLACK`."""

BODY_DESCRIPTOR_TAG_OFFSET = 0x1C
"""Offset of the tagged u32 inside each descriptor (E-092)."""

BODY_DESCRIPTOR_VECTOR_OFFSET = 0x0C
"""Offset of the four f32s inside each descriptor (E-092)."""

BODY_DESCRIPTOR_AUX_OFFSET = 0x2C
"""Offset of the trailing u32 inside each descriptor (E-092)."""

BODY_DESCRIPTOR_SLACK = 0x10
"""Extra bytes over ``count * 0x40`` seen in the array-size field (E-092)."""


@dataclass(frozen=True)
class ModBodyDescriptor:
    """One 0x40-byte record at the head of a ``MOD `` payload body (E-092).

    Every field is an **observation**: the layout is consistent across the
    install and the tag namespace is 285/286, but no field is assigned a
    *meaning*.  The first ``count - 1`` descriptors of a body carry a
    ``0x8000``-namespace :attr:`tag`; the final descriptor is untagged.
    """

    index: int
    """Zero-based position in the array."""

    tag_word: int
    """Descriptor +0x1C: u32 ``(count << 16) | tag`` (see :attr:`tag`)."""

    vector: tuple[float, float, float, float]
    """Descriptor +0x0C: four little-endian f32s.  Meaning [UNKNOWN]."""

    data_offset: int
    """Descriptor +0x24: a body-relative byte offset.  For descriptor 0 this is
    the array's byte size; for the tagged records it is the start of that
    descriptor's **data block** (E-093).  Meaning of the block's contents
    [UNKNOWN]."""

    aux: int
    """Descriptor +0x2C: u32 (``0x00100001`` in many tagged records).  Meaning
    [UNKNOWN]."""

    @property
    def tag(self) -> int:
        """Low u16 of :attr:`tag_word`."""
        return self.tag_word & 0xFFFF

    @property
    def count(self) -> int:
        """High u16 of :attr:`tag_word` — the E-031/E-091 "count" field."""
        return (self.tag_word >> 16) & 0xFFFF

    @property
    def tagged(self) -> bool:
        """True when :attr:`tag` is in the ``0x8000`` namespace (E-091/E-092)."""
        return (self.tag & BODY_TAG_MASK) == BODY_TAG_NAMESPACE

    @classmethod
    def parse(cls, body: bytes, index: int) -> "ModBodyDescriptor":
        """Read descriptor ``index`` from the body."""
        base = index * BODY_DESCRIPTOR_SIZE
        if base + BODY_DESCRIPTOR_SIZE > len(body):
            raise ValueError(
                f"body only {len(body)} bytes, need {base + BODY_DESCRIPTOR_SIZE} "
                f"for descriptor {index}"
            )
        return cls(
            index=index,
            tag_word=u32(body, base + BODY_DESCRIPTOR_TAG_OFFSET),
            vector=(
                f32(body, base + BODY_DESCRIPTOR_VECTOR_OFFSET),
                f32(body, base + BODY_DESCRIPTOR_VECTOR_OFFSET + 4),
                f32(body, base + BODY_DESCRIPTOR_VECTOR_OFFSET + 8),
                f32(body, base + BODY_DESCRIPTOR_VECTOR_OFFSET + 12),
            ),
            data_offset=u32(body, base + BODY_DESCRIPTOR_ARRAY_OFFSET),
            aux=u32(body, base + BODY_DESCRIPTOR_AUX_OFFSET),
        )


def descriptor_count(array_size: int) -> int:
    """Descriptor count implied by the body's array-size field (E-092).

    ``array_size`` is a multiple of :data:`BODY_DESCRIPTOR_SIZE` in 279/286
    chunks; the other seven add :data:`BODY_DESCRIPTOR_SLACK`.  Both floor to
    the same count.  Any other remainder raises :class:`ValueError`.
    """
    if array_size <= 0:
        raise ValueError(f"array size {array_size} is not positive")
    remainder = array_size % BODY_DESCRIPTOR_SIZE
    if remainder not in (0, BODY_DESCRIPTOR_SLACK):
        raise ValueError(
            f"array size 0x{array_size:X} is not a descriptor multiple "
            f"(remainder 0x{remainder:X})"
        )
    return array_size // BODY_DESCRIPTOR_SIZE


@dataclass(frozen=True)
class ModBodyDirectory:
    """The ``MOD `` body's leading descriptor array (E-092).

    ``count`` is derived from the body's own ``+0x24`` field, not from a scan:
    across the install exactly ``count - 1`` descriptors carry a
    ``0x8000``-namespace tag and the last (:attr:`footer`) does not, which is
    what makes the count self-consistent.
    """

    array_size: int
    """The raw ``u32`` at body +0x24 (the descriptor array's byte size)."""

    descriptors: tuple[ModBodyDescriptor, ...]
    """All ``count`` descriptors, in body order."""

    blocks: tuple["ModBodyBlock", ...] = ()
    """The data blocks named by :attr:`records` (E-093), in body order."""

    @property
    def count(self) -> int:
        """Number of descriptors (``array_size // 0x40``)."""
        return len(self.descriptors)

    @property
    def records(self) -> tuple[ModBodyDescriptor, ...]:
        """Every descriptor except the untagged :attr:`footer`."""
        return self.descriptors[:-1]

    @property
    def footer(self) -> ModBodyDescriptor:
        """The last descriptor — the one *not* in the tag namespace."""
        return self.descriptors[-1]

    @property
    def tags(self) -> tuple[int, ...]:
        """Tags of :attr:`records`, in body order."""
        return tuple(d.tag for d in self.records)

    @property
    def slack(self) -> int:
        """Bytes the array-size field exceeds ``count * 0x40`` by (0 or 0x10)."""
        return self.array_size - self.count * BODY_DESCRIPTOR_SIZE

    @property
    def header_ok(self) -> bool:
        """True when every :attr:`records` descriptor is tagged and the
        :attr:`footer` is not (holds on the install)."""
        return all(d.tagged for d in self.records) and not self.footer.tagged

    @classmethod
    def parse(cls, body: bytes) -> "ModBodyDirectory":
        """Parse the descriptor array at the head of a ``MOD `` body."""
        if len(body) < BODY_DESCRIPTOR_ARRAY_OFFSET + 4:
            raise ValueError(
                f"body only {len(body)} bytes, need 4 at +0x{BODY_DESCRIPTOR_ARRAY_OFFSET:X}"
            )
        array_size = u32(body, BODY_DESCRIPTOR_ARRAY_OFFSET)
        count = descriptor_count(array_size)
        if len(body) < count * BODY_DESCRIPTOR_SIZE:
            raise ValueError(
                f"body only {len(body)} bytes, need {count * BODY_DESCRIPTOR_SIZE} "
                f"for {count} descriptors"
            )
        descriptors = tuple(
            ModBodyDescriptor.parse(body, i) for i in range(count)
        )
        directory = cls(array_size=array_size, descriptors=descriptors)
        return cls(
            array_size=array_size,
            descriptors=descriptors,
            blocks=body_blocks(body, directory),
        )


def maybe_mod_body_directory(body: bytes) -> Optional[ModBodyDirectory]:
    """Like :meth:`ModBodyDirectory.parse` but returns ``None`` on bad input."""
    try:
        return ModBodyDirectory.parse(body)
    except (ValueError, IndexError):
        return None


# ---------------------------------------------------------------------------
# Payload body: the per-descriptor data blocks (E-093)
# ---------------------------------------------------------------------------
#
# E-092 read the descriptor array's ``+0x24`` field as a body-relative byte
# offset.  Reading the bytes it points at shows that every *record* descriptor
# names a **data block**, and the blocks of a body are consecutive: they start
# at the array end and the last one runs to the end of the body.  A block opens
# with a fixed 0x2C-byte prefix that is all-zero except for three u32 values at
# +0x04, +0x0C and +0x1C; the payload then begins at +0x2C.  The two interior
# values (``offset_a``/``offset_b``) are usually 16-byte aligned and fall inside
# the block, so they split the payload into three consecutive regions.  The third
# value (``offset_c``) is a body-relative offset that often leaves the block.

BODY_BLOCK_PREFIX_SIZE = 0x2C
"""Size of the fixed prefix at the start of a ``MOD `` data block (E-093)."""

BODY_BLOCK_OFFSET_A = 0x04
"""Prefix offset of the first interior u32 (E-093)."""

BODY_BLOCK_OFFSET_B = 0x0C
"""Prefix offset of the second interior u32 (E-093)."""

BODY_BLOCK_OFFSET_C = 0x1C
"""Prefix offset of the third u32, a body-relative offset (E-093)."""

BODY_BLOCK_ZERO_OFFSETS = (0x00, 0x08, 0x10, 0x14, 0x18, 0x20, 0x24, 0x28)
"""Prefix offsets observed zero on 1542/1556 readable install blocks (E-093)."""


@dataclass(frozen=True)
class ModBodyBlock:
    """One data block named by a record descriptor's ``+0x24`` (E-093).

    Every field is an **observation**: the prefix shape and the relation
    ``block < offset_a < offset_b <= block_end`` hold on most of the install
    (1,540/1,556 readable blocks), but no field is assigned a *meaning* and the
    payload's contents (vertex/index/UV/weight) remain [UNKNOWN].
    """

    index: int
    """Zero-based position in the directory's :attr:`ModBodyDirectory.records`."""

    data_offset: int
    """Body-relative start of the block (the descriptor's ``+0x24``)."""

    span: int
    """Block length in bytes: the distance to the next block, or to the body
    end for the last block."""

    offset_a: int
    """Block +0x04: a body-relative offset, 16-byte aligned, inside the block."""

    offset_b: int
    """Block +0x0C: a body-relative offset, 16-byte aligned, inside the block."""

    offset_c: int
    """Block +0x1C: a body-relative offset (16-byte aligned in 1544/1561
    blocks).  It leaves the block in 708/1561 blocks; meaning [UNKNOWN]."""

    prefix_clear: bool
    """True when the eight :data:`BODY_BLOCK_ZERO_OFFSETS` prefix words are
    zero (1542/1556 readable install blocks)."""

    @property
    def payload_offset(self) -> int:
        """Body-relative start of the payload (``data_offset`` + 0x2C)."""
        return self.data_offset + BODY_BLOCK_PREFIX_SIZE

    @property
    def end(self) -> int:
        """Body-relative end of the block (exclusive)."""
        return self.data_offset + self.span

    @property
    def ordered(self) -> bool:
        """True when ``data_offset < offset_a < offset_b`` (1546/1561 blocks)."""
        return self.data_offset < self.offset_a < self.offset_b

    @property
    def in_block(self) -> bool:
        """True when both interior offsets are inside the payload."""
        return (
            self.payload_offset <= self.offset_a
            and self.offset_b <= self.end
        )

    @property
    def regions(self) -> tuple[tuple[int, int], ...]:
        """The three consecutive payload spans split by ``offset_a``/``offset_b``.

        Only meaningful when :attr:`ordered` and :attr:`in_block` hold; nothing
        is asserted about what each region holds.

        **E-094 correction:** the payload is *not* actually laid out as three
        arrays at these points — in ``em013.pac`` slot 2 a uniform data run
        straddles ``offset_a``.  This property is pure ``offset_a``/``offset_b``
        arithmetic, not a claim about content.
        """
        return (
            (self.payload_offset, self.offset_a),
            (self.offset_a, self.offset_b),
            (self.offset_b, self.end),
        )

    def normal_offset(self, count: int) -> int:
        """Body offset of the normal array for a ``count``-vertex block (E-094)."""
        return self.payload_offset + count * BODY_BLOCK_TUPLE_SIZE

    def attribute_offset(self, count: int) -> int:
        """Body offset of the per-vertex attribute array (E-095).

        The array follows the ``count`` position and ``count`` normal triples and
        holds :data:`BODY_BLOCK_ATTRIBUTE_SIZE` bytes (two u16s) per vertex.
        """
        return self.payload_offset + count * BODY_BLOCK_ATTRIBUTE_UNIT

    def value_offset(self, count: int) -> int:
        """Body offset of the trailing 4-byte-per-vertex value array (E-096)."""
        return self.payload_offset + count * BODY_BLOCK_VALUE_UNIT

    def tail_offset(self, count: int) -> int:
        """Body offset where a clean block's fill tail begins (E-096).

        The vertex record is :data:`BODY_BLOCK_RECORD_SIZE` bytes per vertex, so
        the data ends here.  On the 303 clean blocks no ``0x1F``-fill word occurs
        before this offset.
        """
        return self.payload_offset + count * BODY_BLOCK_RECORD_SIZE

    def offset_slack(self, count: int) -> int:
        """``offset_a`` minus the start of the value array — ``0x24`` when clean.

        On the 303 clean blocks :attr:`offset_a` is exactly
        ``value_offset(count) + BODY_BLOCK_OFFSET_SLACK`` (E-096).
        """
        return self.offset_a - self.value_offset(count)

    @property
    def tail_next_target(self) -> int:
        """The offset the first forward tail entry names when it is derived (E-098).

        ``block.end + BODY_BLOCK_TAIL_NEXT_DELTA``.  Since :attr:`end` is the
        next block's ``data_offset``, this is that block's ``payload + 0x24``.
        This is the [VERIFIED] structural value on 1,210/1,251 install blocks;
        what lives there is [UNKNOWN].
        """
        return self.end + BODY_BLOCK_TAIL_NEXT_DELTA

    @classmethod
    def parse(
        cls, body: bytes, index: int, data_offset: int, span: int
    ) -> "ModBodyBlock":
        """Read the block starting at ``data_offset`` from the body."""
        if data_offset < 0 or span < 0:
            raise ValueError("data_offset and span must be non-negative")
        if data_offset + BODY_BLOCK_PREFIX_SIZE > len(body):
            raise ValueError(
                f"body only {len(body)} bytes, need "
                f"{data_offset + BODY_BLOCK_PREFIX_SIZE} for the block prefix"
            )
        return cls(
            index=index,
            data_offset=data_offset,
            span=span,
            offset_a=u32(body, data_offset + BODY_BLOCK_OFFSET_A),
            offset_b=u32(body, data_offset + BODY_BLOCK_OFFSET_B),
            offset_c=u32(body, data_offset + BODY_BLOCK_OFFSET_C),
            prefix_clear=all(
                u32(body, data_offset + offset) == 0
                for offset in BODY_BLOCK_ZERO_OFFSETS
            ),
        )


# ---------------------------------------------------------------------------
# Payload body: the vertex arrays inside a data block (E-094)
# ---------------------------------------------------------------------------
#
# E-093 read a block's payload as three consecutive regions split by
# ``offset_a``/``offset_b``.  Reading the payload as ``f32[3]`` triples does not
# support that: in ``em013.pac`` slot 2 the interior offsets fall *inside* a
# uniform data run (the ``0x400`` run below), so the offsets are not array
# boundaries.  What *is* consistent is the leading array: with ``count`` taken
# from the descriptor, the first ``count`` triples read as coordinates and the
# next ``count`` triples are unit length (normals).

BODY_BLOCK_TUPLE_SIZE = 0x0C
"""Byte size of one ``f32[3]`` vertex/normal triple (E-094)."""

BODY_BLOCK_NORMAL_TOLERANCE = 2e-3
"""Maximum deviation from 1.0 of a triple's length to count as a normal (E-094)."""

BODY_BLOCK_NORMAL_MIN_RUN = 8
"""Shortest run of consecutive unit triples treated as the normal array (E-094)."""

BODY_BLOCK_ATTRIBUTE_UNIT = 2 * BODY_BLOCK_TUPLE_SIZE
"""``0x18`` — position + normal bytes per vertex before the attribute array (E-095).

The attribute array starts ``count * BODY_BLOCK_ATTRIBUTE_UNIT`` bytes into the
payload, i.e. just past the position and normal arrays.
"""

BODY_BLOCK_ATTRIBUTE_SIZE = 0x04
"""``4`` — bytes per vertex in the attribute array: two little-endian u16s (E-095).

E-094 read these bytes as one u32 per vertex (the "4-byte field").  Reading the
same bytes as two u16s gives small per-vertex values; the u16 reading is the
observation, the values' meaning is [UNKNOWN].
"""

BODY_BLOCK_RECORD_SIZE = 0x20
"""``32`` — bytes per vertex in a clean block: position (0x0C) + normal (0x0C) +
attribute pair (:data:`BODY_BLOCK_ATTRIBUTE_SIZE`) + value
(:data:`BODY_BLOCK_VALUE_SIZE`).

[INFERRED] from E-096: on the 303 blocks whose unit-normal run is exactly
``(count, count)``, **no** ``0x1F``-fill word occurs before
``payload + 32*count`` — 258 blocks start the fill exactly there, 36 later — so
``payload + 32*count`` is a lower bound on the per-vertex record's extent.
The 32-byte split is the reading, not a proven meaning.
"""

BODY_BLOCK_VALUE_UNIT = 0x1C
"""``28`` — bytes per vertex before the trailing 4-byte value array (E-096).

Position + normal (E-094) + attribute pair (E-095) = 28 bytes.
"""

BODY_BLOCK_VALUE_SIZE = 0x04
"""``4`` — bytes per vertex in the trailing value array (E-096).

The array is *single-valued* per block in 202/303 clean blocks, so a per-vertex
reading is [INFERRED]; the values' meaning is [UNKNOWN].
"""

BODY_BLOCK_OFFSET_SLACK = 0x24
"""``36`` — the descriptor's ``offset_a`` minus the value-array start (E-096).

On the 303 clean blocks ``descriptor +0x04 == payload + 28*count + 0x24`` exactly
(303/303) and ``descriptor +0x0C - descriptor +0x04 == 4*count`` exactly
(303/303), so the two interior offsets are *computed from* ``count`` rather than
naming array boundaries.  This corrects E-093's "the two interior offsets split
the payload into three regions" — ``offset_b`` is 0x24 bytes *past* the end of
the 32-byte-per-vertex data.  Why the 0x24 slack exists is [UNKNOWN].
"""

BODY_BLOCK_FILL_WORDS = (0x001F001F, 0x801F801F, 0x001F801F, 0x801F001F)
"""The ``0x1F``-word fill values observed after a clean block's record (E-096)."""


def unit_triple(
    body: bytes, offset: int, tolerance: float = BODY_BLOCK_NORMAL_TOLERANCE
) -> bool:
    """True when the ``f32[3]`` triple at ``offset`` has unit length (E-094).

    Used as the *test* that separates the position array from the normal array:
    positions are arbitrary, normals are unit length.
    """
    if offset < 0 or offset + BODY_BLOCK_TUPLE_SIZE > len(body):
        return False
    x, y, z = f32(body, offset), f32(body, offset + 4), f32(body, offset + 8)
    length_sq = x * x + y * y + z * z
    if length_sq != length_sq or length_sq in (float("inf"), float("-inf")):
        return False  # NaN / inf never counts
    length = length_sq ** 0.5
    return abs(length - 1.0) < tolerance


def block_positions(
    body: bytes, block: ModBodyBlock, count: int
) -> tuple[tuple[float, float, float], ...]:
    """The ``count`` ``f32[3]`` triples at a block's payload start (E-094).

    Each triple is an observation; the reading that they are *vertex positions*
    is [INFERRED].  ``count`` is the descriptor's own count field.
    """
    return _block_triples(body, block.payload_offset, count)


def block_normals(
    body: bytes, block: ModBodyBlock, count: int
) -> tuple[tuple[float, float, float], ...]:
    """The ``count`` ``f32[3]`` triples following the positions (E-094).

    The reading that these are *normals* is supported by their unit length
    (E-094) and remains [INFERRED] as to meaning.
    """
    start = block.payload_offset + count * BODY_BLOCK_TUPLE_SIZE
    return _block_triples(body, start, count)


def _block_triples(
    body: bytes, start: int, count: int
) -> tuple[tuple[float, float, float], ...]:
    triples = []
    for k in range(count):
        offset = start + k * BODY_BLOCK_TUPLE_SIZE
        if offset + BODY_BLOCK_TUPLE_SIZE > len(body):
            break
        triples.append((f32(body, offset), f32(body, offset + 4), f32(body, offset + 8)))
    return tuple(triples)


def block_attributes(
    body: bytes, block: ModBodyBlock, count: int
) -> tuple[tuple[int, int], ...]:
    """The ``count`` little-endian u16 pairs following the normals (E-095).

    E-094 read the four bytes per vertex between the normal array and the next
    array as one u32.  Reading them as **two u16s** gives small values that vary
    per vertex (the pair array is constant in only a handful of blocks), so the
    two-u16 reading is the observation; the values' *meaning* (e.g. a UV pair) is
    **[INFERRED]** and not asserted.
    """
    start = block.attribute_offset(count)
    pairs = []
    for k in range(count):
        offset = start + k * BODY_BLOCK_ATTRIBUTE_SIZE
        if offset + BODY_BLOCK_ATTRIBUTE_SIZE > len(body):
            break
        pairs.append((u16(body, offset), u16(body, offset + 2)))
    return tuple(pairs)


def block_values(
    body: bytes, block: ModBodyBlock, count: int
) -> tuple[int, ...]:
    """The ``count`` little-endian u32 records of a block's value array (E-096).

    The array follows the ``count`` position and normal triples and the ``count``
    u16 pairs of :func:`block_attributes`.  The array is *single-valued* per block
    in 202/303 clean blocks, so the per-vertex reading is [INFERRED]; the values'
    meaning is [UNKNOWN].
    """
    start = block.value_offset(count)
    values = []
    for k in range(count):
        offset = start + k * BODY_BLOCK_VALUE_SIZE
        if offset + BODY_BLOCK_VALUE_SIZE > len(body):
            break
        values.append(u32(body, offset))
    return tuple(values)


def fill_start(body: bytes, block: ModBodyBlock) -> Optional[int]:
    """Body offset of the first ``0x1F``-fill word in a block, or ``None`` (E-096).

    Scans the block payload in 4-byte steps for a word in
    :data:`BODY_BLOCK_FILL_WORDS`.  On the 303 clean blocks the first fill word is
    never before ``payload + 32*count`` (258 blocks start exactly there, 36 start
    later, and 9 carry no fill word at all), which is what makes
    :data:`BODY_BLOCK_RECORD_SIZE` a lower bound on the vertex record.
    """
    end = min(block.end, len(body))
    offset = block.payload_offset
    while offset + 4 <= end:
        if u32(body, offset) in BODY_BLOCK_FILL_WORDS:
            return offset
        offset += 4
    return None


BODY_BLOCK_TAIL_ENTRY_SIZE = 0x08
"""``8`` — size of one ``(body-offset, 0)`` entry in a block's tail (E-097).

The bytes after the 32-byte-per-vertex record (:data:`BODY_BLOCK_RECORD_SIZE`)
end in a table of little-endian pairs: a 16-byte-aligned body-relative offset
followed by a zero word.  On the install 1,305/1,657 non-empty tails carry a run
of at least two such entries and every target lands inside another block; the
*meaning* of the entries is [UNKNOWN] and is not asserted.
"""

BODY_BLOCK_TAIL_MIN_VALUES = 2
"""Fewest consecutive entries :func:`tail_entries` treats as a recovered table."""

BODY_BLOCK_TAIL_NEXT_DELTA = 0x50
"""``80`` — the first forward tail entry is ``block.end + 0x50`` on 1,210/1,251
install blocks (E-098).

``block.end`` is the next block's ``data_offset`` (:func:`body_blocks`), so the
entry is the next block's ``data_offset + BODY_BLOCK_PREFIX_SIZE +
BODY_BLOCK_OFFSET_SLACK`` (i.e. its ``payload_offset + 0x24``).  The first entry
is therefore a *derived* constant offset, not an arbitrary cross-reference — a
refinement of E-097's "cross-reference table" reading.  The *meaning* of the
pointed-at location is [UNKNOWN].
"""


def block_tail(body: bytes, block: ModBodyBlock, count: int) -> bytes:
    """The bytes of a block *after* its 32-byte-per-vertex record (E-097).

    That is ``body[block.tail_offset(count) : min(block.end, len(body))]`` — the
    region E-096's ``fill_start`` scans.  E-097 shows it is **not** pure fill:
    it is a fill/zero region followed by a table of ``(body-offset, 0)`` entries.
    """
    start = block.tail_offset(count)
    if start >= len(body):
        return b""
    return body[start:min(block.end, len(body))]


def tail_entries(
    body: bytes,
    block: ModBodyBlock,
    count: int,
    min_offset: Optional[int] = None,
) -> tuple[int, ...]:
    """The body offsets of the ``(offset, 0)`` entries at the end of a tail (E-097).

    Scans the block tail (:func:`block_tail`) in :data:`BODY_BLOCK_TAIL_ENTRY_SIZE`
    steps and keeps every pair whose value is non-zero and 16-byte aligned, whose
    second word is zero and which lies inside ``body``.  When ``min_offset`` is
    given, only values ``>= min_offset`` are kept (pass ``block.end`` to keep the
    forward references the E-097 census counted).

    This is a **face-value parse**: the values read exactly like body-relative
    offsets and the census shows every one lands inside a block, but what they
    reference is [UNKNOWN].
    """
    tail = block_tail(body, block, count)
    limit = len(body)
    entries = []
    for offset in range(0, len(tail) - BODY_BLOCK_TAIL_ENTRY_SIZE + 1, BODY_BLOCK_TAIL_ENTRY_SIZE):
        value = u32(tail, offset)
        zero = u32(tail, offset + 4)
        if value == 0 or zero != 0 or value % 16 != 0 or value >= limit:
            continue
        if min_offset is not None and value < min_offset:
            continue
        entries.append(value)
    return tuple(entries)


def tail_forward_entries(
    body: bytes, block: ModBodyBlock, count: int
) -> tuple[int, ...]:
    """The tail's **forward** entries — targets at or after ``block.end`` (E-098).

    Shorthand for :func:`tail_entries` with ``min_offset=block.end``.  Backward
    values (which :func:`tail_entries` can also return) are excluded, because a
    block's own ``data_offset`` lies before its :attr:`ModBodyBlock.end`.
    """
    return tail_entries(body, block, count, min_offset=block.end)


def tail_next_ok(body: bytes, block: ModBodyBlock, count: int) -> bool:
    """True when the first forward tail entry names the derived ``end + 0x50`` (E-098).

    Reproduces the install census: the first forward entry equals
    :attr:`ModBodyBlock.tail_next_target` on 1,210/1,251 blocks.  A block with no
    forward entry returns ``False``.  This is a structural test only — nothing is
    asserted about what the target location holds.
    """
    entries = tail_forward_entries(body, block, count)
    return bool(entries) and entries[0] == block.tail_next_target


BODY_BLOCK_TAIL_TARGET_SHIFT = 0x24
"""``36`` — fixed distance from the *next* block's payload start to the tail
descriptor's first offset (E-101, 1,210/1,210 install blocks).

Because ``body_blocks`` sets ``block.end`` to the next block's ``data_offset``
and a block's payload begins :data:`BODY_BLOCK_PREFIX_SIZE` later, E-098's
``+0x50`` forward delta decomposes as ``BODY_BLOCK_PREFIX_SIZE +
BODY_BLOCK_TAIL_TARGET_SHIFT``; the value equals :data:`BODY_BLOCK_OFFSET_SLACK`.
So ``v1 == next.payload_offset + 0x24`` exactly, and all three offsets land inside
the next block (``v3 <= next.end``, E-101).
"""

BODY_BLOCK_TAIL_TAG_GAP = 0x10
"""``16`` — bytes between the tail descriptor's tag word and its first offset (E-100).

The descriptor's last 36 bytes read as ``[tag][0][0][0][v1][0][v2][0][v3]``, so the
tag word sits three zero words before the first offset.
"""

BODY_BLOCK_TAIL_OFFSET_COUNT = 3
"""Number of body offsets in a tail descriptor (E-100)."""

BODY_BLOCK_TAIL_RECORD_UNIT = 0x0C
"""``12`` — bytes per recorded element used to derive the descriptor's spacing (E-100).

On the install the three offsets are equally spaced by
``align_up(12 * n, 16)`` where ``n`` is the low u16 of the descriptor's tag word.
"""


@dataclass(frozen=True)
class ModBodyTailDescriptor:
    """The 36-byte descriptor at the very end of a ``MOD `` block's tail (E-100).

    Layout, read from real bytes::

        [tag u32][0][0][0][v1 u32][0][v2 u32][0][v3 u32]

    ``v1`` equals :attr:`ModBodyBlock.tail_next_target` (``block.end + 0x50``) and
    ``v2``/``v3`` are ``v1 + k * align_up(12 * n, 16)`` for ``k = 1, 2`` on
    1,148/1,210 install blocks, where ``n`` is the low u16 of the tag word.  The
    tag word's high u16 is a small class id (0..6).  What the three offsets name
    and what ``n`` counts are **[UNKNOWN]**; only the arithmetic is claimed.

    **E-101.** ``v1`` is exactly ``next.payload_offset +
    :data:`BODY_BLOCK_TAIL_TARGET_SHIFT``` on 1,210/1,210 blocks and ``v3 <=
    next.end`` on 1,210/1,210, so the descriptor is a forward reference *inside the
    immediately following block*, not an arbitrary cross-block pointer.  The
    spacing is better predicted by the next block's count (1,148/1,210) than by
    ``n`` (1,131/1,210) — see :meth:`spacing_ok_for`.

    The offset count is fixed at :data:`BODY_BLOCK_TAIL_OFFSET_COUNT`.  ``v3`` is
    always the block's final u32, so its trailing zero word is the *next* block's
    first prefix word — which is why E-097 counted at most two entries inside a
    tail even though the descriptor names three targets.
    """

    tag_word: int
    """The u32 16 bytes before the first offset."""

    offsets: tuple[int, ...]
    """The ``BODY_BLOCK_TAIL_OFFSET_COUNT`` body offsets, in order."""

    stride: int
    """``align_up(12 * count, 16)`` — the spacing the offsets are expected to have."""

    @property
    def count(self) -> int:
        """Low u16 of :attr:`tag_word` — the descriptor's own count field (E-100)."""
        return self.tag_word & 0xFFFF

    @property
    def class_id(self) -> int:
        """High u16 of :attr:`tag_word` — a small id (0..6 on the install) (E-100)."""
        return (self.tag_word >> 16) & 0xFFFF

    @property
    def expected_offsets(self) -> tuple[int, ...]:
        """The offsets implied by ``offsets[0]`` and :attr:`stride`."""
        if not self.offsets:
            return ()
        base = self.offsets[0]
        return tuple(base + k * self.stride for k in range(len(self.offsets)))

    @property
    def spacing_ok(self) -> bool:
        """True when the offsets are equally spaced by :attr:`stride` (E-100)."""
        return bool(self.offsets) and self.offsets == self.expected_offsets

    def expected_offsets_for(self, count: int) -> tuple[int, ...]:
        """The offsets implied by ``offsets[0]`` and the spacing for ``count`` (E-101).

        Uses :func:`tail_descriptor_spacing` — the *aligned* per-vertex size — rather
        than :attr:`stride`, which E-100 derived from the descriptor's own low u16.
        """
        if not self.offsets:
            return ()
        base = self.offsets[0]
        step = tail_descriptor_spacing(count)
        return tuple(base + k * step for k in range(len(self.offsets)))

    def spacing_ok_for(self, count: int) -> bool:
        """True when the offsets are equally spaced for an explicit ``count`` (E-101).

        On the install ``align_up(12 * next.count, 16)`` reproduces the spacing on
        1,148/1,210 blocks, better than :attr:`spacing_ok`'s
        ``align_up(12 * n, 16)`` (1,131/1,210), so the *next block's* vertex count
        is the driver of the spacing and the descriptor's ``n`` only usually tracks
        it.  Recorded, not proven: the meaning of either count is [UNKNOWN].
        """
        return bool(self.offsets) and self.offsets == self.expected_offsets_for(count)


def tail_descriptor_spacing(count: int) -> int:
    """The tail descriptor's offset spacing for ``count`` vertices (E-101).

    ``align_up(12 * count, 16)`` — the 16-byte-aligned size of ``count``
    :data:`BODY_BLOCK_TUPLE_SIZE`-byte triples.  This is the spacing that fits
    1,148/1,210 install blocks when ``count`` is the *next* block's vertex count.
    Whether the triples are positions, normals or something else is [UNKNOWN].
    """
    return align_up(BODY_BLOCK_TAIL_RECORD_UNIT * count, ALIGNMENT)


def tail_descriptor(
    body: bytes, block: ModBodyBlock, count: int
) -> Optional[ModBodyTailDescriptor]:
    """Recover a block's tail descriptor, or ``None`` (E-100).

    Requires the block's first forward tail entry to be the derived
    :attr:`ModBodyBlock.tail_next_target` (E-098) and the three words between the
    tag word and that offset to be zero.  This is a **face-value parse**: the
    arithmetic is verified on the install, every field meaning stays [UNKNOWN].
    """
    entries = tail_forward_entries(body, block, count)
    if not entries or entries[0] != block.tail_next_target:
        return None
    first = entries[0]
    start = block.tail_offset(count)
    end = min(block.end, len(body))
    offset = None
    scan = start
    while scan + BODY_BLOCK_TAIL_ENTRY_SIZE <= end:
        if u32(body, scan) == first and u32(body, scan + 4) == 0:
            offset = scan
            break
        scan += BODY_BLOCK_TAIL_ENTRY_SIZE
    if offset is None or offset - start < BODY_BLOCK_TAIL_TAG_GAP:
        return None
    tag_offset = offset - BODY_BLOCK_TAIL_TAG_GAP
    tag_word = u32(body, tag_offset)
    for k in range(1, 4):
        if u32(body, tag_offset + 4 * k) != 0:
            return None
    offsets = []
    for k in range(BODY_BLOCK_TAIL_OFFSET_COUNT):
        word = offset + 8 * k
        if word + 4 > len(body):
            break
        offsets.append(u32(body, word))
    stride = align_up(BODY_BLOCK_TAIL_RECORD_UNIT * (tag_word & 0xFFFF), ALIGNMENT)
    return ModBodyTailDescriptor(
        tag_word=tag_word, offsets=tuple(offsets), stride=stride
    )


def normal_run(
    body: bytes, block: ModBodyBlock, min_run: int = BODY_BLOCK_NORMAL_MIN_RUN
) -> Optional[tuple[int, int]]:
    """Locate the first run of unit-length triples in a block (E-094).

    Returns ``(start_index, length)`` — the triple index (from the payload start)
    and the number of consecutive unit triples — or ``None`` when no run of at
    least ``min_run`` exists.  The run is *evidence*, not an assertion: its start
    index is ``count`` or ``count ± 1`` on most blocks where it exists, and 689
    blocks (mostly ``count == 4``) have no run at all.
    """
    body_end = min(block.end, len(body))
    start = block.payload_offset
    maximum = (body_end - start) // BODY_BLOCK_TUPLE_SIZE
    index = 0
    while index < maximum:
        if not unit_triple(body, start + index * BODY_BLOCK_TUPLE_SIZE):
            index += 1
            continue
        end = index
        while end < maximum and unit_triple(body, start + end * BODY_BLOCK_TUPLE_SIZE):
            end += 1
        if end - index >= min_run:
            return index, end - index
        index = end
    return None


def body_blocks(
    body: bytes, directory: ModBodyDirectory
) -> tuple[ModBodyBlock, ...]:
    """The data blocks named by a directory's record descriptors (E-093).

    Each record's ``+0x24`` is a block start; the block runs to the next
    record's ``+0x24`` and the last runs to the end of the body.  Records with a
    zero ``+0x24`` are skipped (the array is only followed by data in 279/286
    chunks, so a zero offset is not expected among the records).
    """
    records = directory.records
    offsets = [r.data_offset for r in records]
    blocks = []
    for i, record in enumerate(records):
        start = record.data_offset
        if start == 0:
            continue
        end = offsets[i + 1] if i + 1 < len(offsets) else len(body)
        if end < start or start + BODY_BLOCK_PREFIX_SIZE > len(body):
            # Offsets are not strictly increasing in 4/286 chunks, and a block
            # prefix can run past a truncated body.  Leave those blocks out
            # rather than failing the whole directory or inventing a block.
            continue
        blocks.append(ModBodyBlock.parse(body, i, start, end - start))
    return tuple(blocks)
