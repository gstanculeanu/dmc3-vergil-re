"""Raw (untagged) PAC chunk payloads.

Some PAC slots carry no ASCII tag: ``pl021.pac`` has nine occupied untagged
slots (0, 5, 6, 7, 9, 10, 11, 21, 22) holding bone transforms, UV tables,
primitive groups and other untagged tables (evidence E-008).  This module
decodes only what is *observed* in real bytes; every field meaning is
[UNKNOWN] until engine ground truth arrives.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Optional

from .pac import f32, u16, u32

SLOT0_HEADER_SIZE = 0x18
"""Size of the decoded header of ``pl021.pac`` slot 0: six u32s."""

SLOT10_PAIR_COUNT = 23
"""Number of u16 pairs in the leading table of ``pl021.pac`` slot 10.

Observed (evidence E-037): the table occupies bytes +0x00..+0x5B (23 pairs,
stride 4) and is followed by a little-endian f32 stream from +0x5C to the end
of the chunk.  Whether the count is stored somewhere in the chunk or is fixed
is [UNKNOWN]; this constant locks the single observed layout.
"""


@dataclass(frozen=True)
class Slot10Table:
    """Leading table of ``pl021.pac`` slot 10 (evidence E-037).

    Observed at file offset 0x077ED0 of ``pl021.pac`` (chunk-relative body
    starts at +0x00)::

        +0x00  u16 pairs, stride 4, ``SLOT10_PAIR_COUNT`` pairs
        +0x5C  little-endian f32 stream to end of chunk

    Every field meaning is [UNKNOWN]: the pairs look like index/offset pairs
    (first element constantly 92 == 0x5C, i.e. the table's byte size, in the
    observed chunk) and the f32 stream holds small magnitude values, but neither
    is established from bytes alone.  The parser reads exactly the observed
    layout and interprets nothing.
    """

    pairs: tuple[tuple[int, int], ...]
    """``SLOT10_PAIR_COUNT`` little-endian u16 pairs, stride 4."""

    floats: tuple[float, ...]
    """Little-endian f32s from +0x5C to the end of the chunk."""

    @classmethod
    def parse(cls, data: bytes) -> "Slot10Table":
        """Parse the slot-10 layout from ``data`` (chunk-relative bytes)."""
        pair_bytes = 4 * SLOT10_PAIR_COUNT
        if len(data) < pair_bytes:
            raise ValueError(
                f"slot-10 table only {len(data)} bytes, need {pair_bytes} "
                f"for {SLOT10_PAIR_COUNT} pairs"
            )
        pairs = tuple(
            (u16(data, 4 * index), u16(data, 4 * index + 2))
            for index in range(SLOT10_PAIR_COUNT)
        )
        remainder = len(data) - pair_bytes
        floats = tuple(
            f32(data, pair_bytes + 4 * index)
            for index in range(remainder // 4)
        )
        return cls(pairs=pairs, floats=floats)


def maybe_slot10_table(data: bytes) -> Optional[Slot10Table]:
    """Like :meth:`Slot10Table.parse` but returns ``None`` on short input."""
    try:
        return Slot10Table.parse(data)
    except ValueError:
        return None


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


SLOT21_SEPARATOR = 0xFFFF
"""u16 value that delimits segments within ``pl021.pac`` slot 21.

Observed (evidence E-043): slot 21's payload is a little-endian u16 stream
split into 14 segments by ``0xFFFF`` separators. ``0x7FFF`` also appears
inside segments and is *not* a delimiter. Every field meaning is [UNKNOWN].
"""


def _split_u16_segments(data: bytes) -> tuple[tuple[int, ...], ...]:
    """Split a little-endian u16 stream on every ``0xFFFF`` separator.

    Shared by the slot-5 and slot-21 segment tables of ``pl021.pac`` (evidence
    E-043 and E-052). ``0xFFFF`` separators are not included in any segment;
    ``0x7FFF`` is data, never a delimiter. Raises :exc:`ValueError` if
    ``data`` has an odd length (incomplete trailing u16).
    """
    if len(data) % 2 != 0:
        raise ValueError(
            f"data is {len(data)} bytes, need an even number of bytes for u16s"
        )
    count = len(data) // 2
    values = [u16(data, 2 * index) for index in range(count)]
    segments: list[list[int]] = [[]]
    for value in values:
        if value == SLOT21_SEPARATOR:
            segments.append([])
        else:
            segments[-1].append(value)
    return tuple(tuple(seg) for seg in segments)


@dataclass(frozen=True)
class Slot21Table:
    """``pl021.pac`` slot 21 as ``0xFFFF``-delimited u16 segments (E-043).

    Observed at file offset `0x07FF00` of ``pl021.pac`` (span `0x2E0`,
    368 u16s) — the payload splits into 14 segments of sizes
    2, 6, 1, 8, 10, 31, 111, 34, 1, 6, 8, 27, 84, 26 u16s, separated by
    ``0xFFFF``. Segment 0 is verbatim ``(6, 408)``; segment index 5 ends in an
    arithmetic run ``36, 50, 64, …, 232`` stepping by 14; segment index 6
    repeats a 7-u16 sub-record ``32767, 0, 32767, 1, 1, 0, VALUE`` with
    ``VALUE`` stepping by 256. All segment-internal semantics are [UNKNOWN];
    the parser reads exactly the observed segmentation and interprets nothing.
    """

    segments: tuple[tuple[int, ...], ...]
    """Tuple of u16 segments; the ``0xFFFF`` separators are not included."""

    @classmethod
    def parse(cls, data: bytes) -> "Slot21Table":
        """Parse the slot-21 segmentation from ``data`` (chunk-relative bytes).

        Interprets ``data`` as a little-endian u16 stream and splits it on
        every ``0xFFFF`` separator. Delegates to :func:`_split_u16_segments`,
        so behavior is unchanged from the slot-21-specific implementation.
        """
        return cls(segments=_split_u16_segments(data))


def maybe_slot21_table(data: bytes) -> Optional[Slot21Table]:
    """Like :meth:`Slot21Table.parse` but returns ``None`` on bad input."""
    try:
        return Slot21Table.parse(data)
    except ValueError:
        return None


SLOT5_SEGMENT_COUNT = 215
"""Number of segments observed in ``pl021.pac`` slot 5 (evidence E-052).

The count comes from the single observed chunk and is not known to be stored
anywhere in the payload; it locks the observed layout, not a rule.
"""


@dataclass(frozen=True)
class Slot5Table:
    """``pl021.pac`` slot 5 as ``0xFFFF``-delimited u16 segments (E-052).

    Observed at file offset 0x06B6E0 of ``pl021.pac`` (span 0x4B30,
    9,624 u16s): the payload splits into **215 segments** (214 ``0xFFFF``
    separators). Segment 0 is verbatim ``(6, 0x37D0)``; segment sizes open
    2, 1, 34, 60, 5, 13, 13, 13, 13, 15, … and the tail holds much larger
    segments (up to 378 u16s). Non-zero bytes run from offset 0x0000 to
    0x4B2B, essentially the whole span. ``0x7FFF`` occurs inside segments and
    is *not* a delimiter — exactly as in slot 21 (E-043).

    Slot 5 shares slot 21's segment-stream structure but its segmentation
    differs (215 segments vs 14), so the two are decoded separately. All
    segment-internal semantics are [UNKNOWN]; the parser reads exactly the
    observed segmentation and interprets nothing.
    """

    segments: tuple[tuple[int, ...], ...]
    """Tuple of u16 segments; the ``0xFFFF`` separators are not included."""

    @classmethod
    def parse(cls, data: bytes) -> "Slot5Table":
        """Parse the slot-5 segmentation from ``data`` (chunk-relative bytes).

        Delegates to :func:`_split_u16_segments`.
        """
        return cls(segments=_split_u16_segments(data))


def maybe_slot5_table(data: bytes) -> Optional[Slot5Table]:
    """Like :meth:`Slot5Table.parse` but returns ``None`` on bad input."""
    try:
        return Slot5Table.parse(data)
    except ValueError:
        return None


SLOT9_FLOAT_COUNT = 224
"""Number of little-endian f32s observed in ``pl021.pac`` slot 9 (evidence E-062).

The count comes from the single observed chunk (896 bytes / 4) and locks the
observed layout, not a rule. Every field meaning is [UNKNOWN].
"""


@dataclass(frozen=True)
class Slot9Table:
    """``pl021.pac`` slot 9 as a little-endian f32 array (evidence E-062).

    Observed at file offset 0x077B50 of ``pl021.pac`` (span 0x380, 896 bytes):
    the entire span is ``SLOT9_FLOAT_COUNT`` little-endian f32s with no header,
    no count field and no separators. The first values read ``10.4, -1.2,
    10.0, 12.0, -1.2, 15.0, ...``; 206 values are non-zero (indices 0..210) and
    the last 18 (indices 211..223) are zeros. Whether the count is stored
    anywhere in the chunk, and what the array indexes (UVs, vertices, colours,
    …), are [UNKNOWN]; the parser reads exactly the observed layout and
    interprets nothing.
    """

    floats: tuple[float, ...]
    """``SLOT9_FLOAT_COUNT`` little-endian f32s."""

    @classmethod
    def parse(cls, data: bytes) -> "Slot9Table":
        """Parse the slot-9 f32 array from ``data`` (chunk-relative bytes)."""
        want = 4 * SLOT9_FLOAT_COUNT
        if len(data) != want:
            raise ValueError(
                f"slot-9 array only {len(data)} bytes, need {want} "
                f"({SLOT9_FLOAT_COUNT} f32s)"
            )
        floats = tuple(f32(data, 4 * index) for index in range(SLOT9_FLOAT_COUNT))
        return cls(floats=floats)


def maybe_slot9_table(data: bytes) -> Optional[Slot9Table]:
    """Like :meth:`Slot9Table.parse` but returns ``None`` on bad input."""
    try:
        return Slot9Table.parse(data)
    except ValueError:
        return None


DDS_MAGIC = b"DDS "
"""Magic of the embedded DDS blobs carried by the texture containers."""

TEXTURE_DESCRIPTOR_SIZE = 0x68
"""Size of the DMC3 HD texture descriptor (evidence E-084).

The descriptor is the fixed block that immediately precedes the embedded DDS
in both the ``.tm2`` platform pre-header and the untagged ``pl021.pac`` texture
slots. Its own host-format prefix (8 bytes) lies before it; the 128-byte DDS
header begins at ``descriptor_start + TEXTURE_DESCRIPTOR_SIZE``.
"""

PAC_TEXTURE_DESCRIPTOR_OFFSET = 0x808
"""Body-relative descriptor offset in the untagged ``pl021.pac`` texture slots."""

TM2_TEXTURE_DESCRIPTOR_OFFSET = 0x08
"""File-relative descriptor offset in an HD-Collection ``.tm2`` (E-084/E-034)."""

TEXTURE_DDS_OFFSET = PAC_TEXTURE_DESCRIPTOR_OFFSET + TEXTURE_DESCRIPTOR_SIZE
"""Body-relative DDS offset in a ``pl021.pac`` texture slot (observed 0x870)."""

TEXTURE_DDS_HEADER_SIZE = 128
"""Size of the standard DDS header that follows the descriptor (E-084)."""


def _float32(value: float) -> float:
    """Round ``value`` to the nearest binary32 and return it as a float."""
    return struct.unpack("<f", struct.pack("<f", value))[0]


@dataclass(frozen=True)
class TextureChunk:
    """A DMC3 HD texture descriptor together with its embedded DDS (E-084).

    The same 0x68-byte descriptor precedes the DDS in **two** container types.
    In the untagged ``pl021.pac`` texture slots it starts at body+0x808 (after
    eight zero bytes); in an HD-Collection ``.tm2`` it starts at file+0x08. The
    two differ by exactly 0x800, and the 128-byte DDS header follows the
    descriptor in both. Field offsets below are relative to the descriptor
    start ``D`` (little-endian)::

        D+0x00 u16          mip count << 8  (0x0900 for 9, 0x0100 for 1)
        D+0x02 u16          2
        D+0x04 u32          0x0000AAE4
        D+0x08 u16,(u16)    (width, height)
        D+0x0C u32          1
        D+0x18 u32          64
        D+0x30 u32          DDS payload byte size
        D+0x3C u16,(u16)    (width // 2, height // 2)
        D+0x40 f32,(f32)    2 / width  (== 1 / (width // 2))
        D+0x5C u32          payload size + 128 (the DDS header)
        D+0x60 u32          8
        D+0x68 DDS          128-byte DDS header ("DDS ")

    Verified on three real artifacts: ``pl021.pac`` slot 0 (256x256 ``DX10``,
    9 mips), ``pl021.pac`` slot 22 (32x32 ``DXT1``, 1 mip) and ``i001_90.tm2``
    (256x256 ``DXT3``, 1 mip). All observed chunks are **square**, so the two
    descriptor extents cannot distinguish a width axis from a height axis.

    Only the relations between the descriptor and the DDS header are verified;
    every field's *meaning* is [UNKNOWN] and is deliberately not named beyond
    its offset. The parser reads exactly the observed layout and exposes the
    relations as ``*_ok`` properties.
    """

    descriptor_offset: int
    """Offset the descriptor starts at (0x808 for a PAC slot, 0x08 for a .tm2)."""

    dds_offset: int
    """Offset of the embedded DDS header (``descriptor_offset + 0x68``)."""

    dds_header: bytes
    """The 128-byte DDS header, verbatim."""

    width: int
    """DDS ``dwWidth`` (header +0x10)."""

    height: int
    """DDS ``dwHeight`` (header +0x0C)."""

    mips: int
    """DDS ``dwMipMapCount`` (header +0x1C), 0 when absent."""

    fourcc: bytes
    """DDS ``dwFourCC`` (header +0x54); ``b"DX10"`` for an extended header."""

    field_00: int
    """u16 at ``D+0x00`` (high byte equals :attr:`mips` on the three chunks)."""

    field_02: int
    """u16 at ``D+0x02`` (observed 2 on the three chunks)."""

    field_04: int
    """u32 at ``D+0x04`` (observed ``0x0000AAE4`` on the three chunks)."""

    extent: tuple[int, int]
    """u16 pair at ``D+0x08`` (observed ``(width, height)``)."""

    field_0c: int
    """u32 at ``D+0x0C`` (observed 1 on the three chunks)."""

    field_18: int
    """u32 at ``D+0x18`` (observed 64 on the three chunks)."""

    payload_size: int
    """u32 at ``D+0x30`` (observed DDS payload byte size)."""

    half_extent: tuple[int, int]
    """u16 pair at ``D+0x3C`` (observed ``(width // 2, height // 2)``)."""

    inverse_scale: tuple[float, float]
    """f32 pair at ``D+0x40``/``D+0x44`` (observed ``2 / width``)."""

    total_size: int
    """u32 at ``D+0x5C`` (observed :attr:`payload_size` + 128)."""

    field_60: int
    """u32 at ``D+0x60`` (observed 8 on the three chunks)."""

    @classmethod
    def parse(
        cls,
        data: bytes,
        descriptor_offset: int = PAC_TEXTURE_DESCRIPTOR_OFFSET,
    ) -> "TextureChunk":
        """Parse the texture descriptor and embedded DDS header.

        ``descriptor_offset`` selects the container: the default is the
        ``pl021.pac`` texture-slot body offset (0x808); pass
        :data:`TM2_TEXTURE_DESCRIPTOR_OFFSET` (0x08) for an HD ``.tm2``.
        """
        dds_offset = descriptor_offset + TEXTURE_DESCRIPTOR_SIZE
        end = dds_offset + TEXTURE_DDS_HEADER_SIZE
        if descriptor_offset < 0 or len(data) < end:
            raise ValueError(
                f"texture chunk only {len(data)} bytes, need {end} for the "
                f"descriptor at +{descriptor_offset:#x} and the DDS header"
            )
        d = descriptor_offset
        header = data[dds_offset:end]
        if header[:4] != DDS_MAGIC:
            raise ValueError(
                f"no DDS magic at +{dds_offset:#x}: {header[:4]!r}"
            )
        return cls(
            descriptor_offset=d,
            dds_offset=dds_offset,
            dds_header=header,
            width=u32(header, 16),
            height=u32(header, 12),
            mips=u32(header, 28),
            fourcc=header[84:88],
            field_00=u16(data, d + 0x00),
            field_02=u16(data, d + 0x02),
            field_04=u32(data, d + 0x04),
            extent=(u16(data, d + 0x08), u16(data, d + 0x0A)),
            field_0c=u32(data, d + 0x0C),
            field_18=u32(data, d + 0x18),
            payload_size=u32(data, d + 0x30),
            half_extent=(u16(data, d + 0x3C), u16(data, d + 0x3E)),
            inverse_scale=(f32(data, d + 0x40), f32(data, d + 0x44)),
            total_size=u32(data, d + 0x5C),
            field_60=u32(data, d + 0x60),
        )

    @property
    def dimensions_match(self) -> bool:
        """``extent == (width, height)`` — verified on all three chunks."""
        return self.extent == (self.width, self.height)

    @property
    def half_extent_matches(self) -> bool:
        """``half_extent == (width // 2, height // 2)`` — all three chunks."""
        return self.half_extent == (self.width // 2, self.height // 2)

    @property
    def inverse_scale_matches(self) -> bool:
        """The f32 pair equals ``2 / width`` (all chunks are square)."""
        if not self.width:
            return False
        expected = _float32(2.0 / self.width)
        return self.inverse_scale[0] == self.inverse_scale[1] == expected

    @property
    def total_size_matches(self) -> bool:
        """``total_size == payload_size + 128`` — verified on all three."""
        return self.total_size == self.payload_size + TEXTURE_DDS_HEADER_SIZE

    @property
    def mips_match(self) -> bool:
        """``field_00 >> 8 == mips`` — [INFERRED] on the three chunks."""
        return (self.field_00 >> 8) == self.mips


def maybe_texture_chunk(
    data: bytes,
    descriptor_offset: int = PAC_TEXTURE_DESCRIPTOR_OFFSET,
) -> Optional[TextureChunk]:
    """Like :meth:`TextureChunk.parse` but returns ``None`` when no DDS."""
    try:
        return TextureChunk.parse(data, descriptor_offset)
    except ValueError:
        return None
