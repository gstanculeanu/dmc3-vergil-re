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

from .pac import Chunk, f32, u16, u32

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
    the array's byte size; for the tagged records it names their data.  Meaning
    of the referent [UNKNOWN]."""

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
        return cls(
            array_size=array_size,
            descriptors=tuple(
                ModBodyDescriptor.parse(body, i) for i in range(count)
            ),
        )


def maybe_mod_body_directory(body: bytes) -> Optional[ModBodyDirectory]:
    """Like :meth:`ModBodyDirectory.parse` but returns ``None`` on bad input."""
    try:
        return ModBodyDirectory.parse(body)
    except (ValueError, IndexError):
        return None
