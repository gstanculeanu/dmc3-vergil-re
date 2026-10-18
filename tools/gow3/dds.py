"""DDS reader and an in-place DXT "tint" for GoW3R texture blobs.

GoW3R stores its textures as plain DDS blobs inside a ``R_*.WAD`` (E-055). Verified
on ``R_HADES.WAD``: 143 DDS headers, BC1 (DXT1) and BC3 (DXT5), up to 2048x2048
with 11 mip levels.

Because a texture's *data* size is computable from its own header, a byte-for-byte
**same-size** edit is possible: overwrite colour endpoints inside the pixel data and
nothing else. No container size changes, so no writer is needed -- the same trick as
the localisation rename (E-054).

The tint sets both RGB565 endpoints of every DXT colour block to the same colour.
With ``colour0 == colour1`` the four index bits select between two identical values,
so the block renders as that solid colour regardless of its original content.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Iterator, List, Optional

DDS_MAGIC = b"DDS "
DDS_HEADER_SIZE = 128

#: bytes per 4x4 block for the formats seen in GoW3R textures
BLOCK_BYTES = {b"DXT1": 8, b"DXT3": 16, b"DXT5": 16, b"ATI1": 8, b"BC4U": 8,
               b"ATI2": 16, b"BC5U": 16}

#: formats whose 8-byte *colour* half sits after an 8-byte alpha half
ALPHA_FIRST = {b"DXT3": True, b"DXT5": True, b"ATI2": True, b"BC5U": True}


class DdsError(ValueError):
    """Raised for a DDS blob that does not match the expected header."""


@dataclass(frozen=True)
class DdsTexture:
    offset: int          # file offset of the 'DDS ' magic
    width: int
    height: int
    mips: int
    fourcc: bytes

    @property
    def block_bytes(self) -> Optional[int]:
        return BLOCK_BYTES.get(self.fourcc)

    @property
    def is_block_compressed(self) -> bool:
        return self.block_bytes is not None

    @property
    def data_offset(self) -> int:
        return self.offset + DDS_HEADER_SIZE

    def level_size(self, level: int) -> int:
        block = self.block_bytes
        if block is None:
            raise DdsError(f"unsupported format {self.fourcc!r}")
        w = max(1, self.width >> level)
        h = max(1, self.height >> level)
        return max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * block

    @property
    def data_size(self) -> int:
        return sum(self.level_size(l) for l in range(self.mips))

    @property
    def end(self) -> int:
        return self.data_offset + self.data_size

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        fmt = self.fourcc.decode("latin-1", "replace").strip("\x00") or "?"
        return (f"@0x{self.offset:08X} {self.width}x{self.height} "
                f"mips={self.mips} {fmt} data={self.data_size:,}")


def parse_at(data: bytes, offset: int) -> DdsTexture:
    if data[offset:offset + 4] != DDS_MAGIC:
        raise DdsError(f"no DDS magic at 0x{offset:X}")
    if offset + DDS_HEADER_SIZE > len(data):
        raise DdsError("truncated DDS header")
    dw_size = struct.unpack_from("<I", data, offset + 4)[0]
    if dw_size != 124:
        raise DdsError(f"unexpected DDS header size {dw_size}")
    height = struct.unpack_from("<I", data, offset + 12)[0]
    width = struct.unpack_from("<I", data, offset + 16)[0]
    mips = struct.unpack_from("<I", data, offset + 28)[0] or 1
    fourcc = data[offset + 84:offset + 88]
    if not (0 < width <= 8192 and 0 < height <= 8192):
        raise DdsError(f"implausible dimensions {width}x{height}")
    return DdsTexture(offset, width, height, mips, fourcc)


def find_textures(data: bytes, require_known_format: bool = True) -> List[DdsTexture]:
    """Every DDS header in ``data``, in file order."""
    out: List[DdsTexture] = []
    start = 0
    while True:
        index = data.find(DDS_MAGIC, start)
        if index < 0:
            break
        start = index + 1
        try:
            texture = parse_at(data, index)
        except DdsError:
            continue
        if require_known_format and not texture.is_block_compressed:
            continue
        out.append(texture)
    return out


def rgb565(red: int, green: int, blue: int) -> int:
    """Pack 5/6/5-bit channels."""
    return ((red & 0x1F) << 11) | ((green & 0x3F) << 5) | (blue & 0x1F)


def colour_blocks(data: bytes, texture: DdsTexture) -> Iterator[int]:
    """Yield the file offset of every DXT colour block of ``texture``."""
    alpha_first = ALPHA_FIRST.get(texture.fourcc, False)
    pos = texture.data_offset
    for level in range(texture.mips):
        size = texture.level_size(level)
        for block in range(size // texture.block_bytes):
            base = pos + block * texture.block_bytes
            yield base + 8 if alpha_first else base
        pos += size


def tint_in_place(data: bytes, texture: DdsTexture,
                  colour: int = 0xF800) -> bytes:
    """Return a copy of ``data`` with ``texture``'s DXT colour blocks set to ``colour``.

    Only bytes inside ``[texture.data_offset, texture.end)`` are touched, and the
    length never changes. Raises :class:`DdsError` for non-block formats.
    """
    if not texture.is_block_compressed:
        raise DdsError(f"tint supports block formats only, not {texture.fourcc!r}")
    if texture.end > len(data):
        raise DdsError(f"texture runs past the end of the file ({texture})")

    blob = bytearray(data)
    packed = struct.pack("<H", colour)
    for offset in colour_blocks(data, texture):
        blob[offset:offset + 2] = packed        # colour0
        blob[offset + 2:offset + 4] = packed    # colour1
    return bytes(blob)


def changed_ranges(before: bytes, after: bytes) -> List[tuple]:
    """Contiguous (start, end) ranges where two equal-length buffers differ."""
    if len(before) != len(after):
        raise DdsError("buffers differ in length")
    out: List[tuple] = []
    start = None
    for i in range(len(before)):
        if before[i] != after[i]:
            if start is None:
                start = i
        elif start is not None:
            out.append((start, i))
            start = None
    if start is not None:
        out.append((start, len(before)))
    return out
