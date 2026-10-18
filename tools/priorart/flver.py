"""FromSoftware FLVER header reader for the prior-art package.

Reads the fixed header block of ``BD_M_10100.flver`` (Vergil's body) from the
third-party Bloodborne Vergil mod package (docs/PRIOR-ART.md, E-014). This is a
*bounded* decoder: it reads the 128-byte header and reports the raw field
values, marking every field's meaning [UNKNOWN] until engine ground truth or a
format spec confirms it. The section records that begin at offset 0x80 are left
for a later slice.

Nothing here writes a game asset into the repository; output goes wherever the
caller asks.

Real bytes observed in ``BD_M_10100.flver`` (467,008 bytes), file offset 0x00::

    0x00  46 4C 56 45 52 00  "FLVER\0"
    0x06  4C 00              u16 76
    0x08  14 00              u16 20
    0x0A  02 00              u16 2
    0x0C  30 F0 00 00        u32 61488
    0x10  10 30 06 00        u32 405520
    0x14  00 00 00 00        u32 0
    0x18  06 00 00 00        u32 6
    0x1C  4E 01 00 00        u32 334
    0x20  06 00 00 00        u32 6
    0x24  0C 00 00 00        u32 12
    0x28  4A 36 37 BF        f32 -0.7157...      <- six f32s, 0x28..0x3F
    0x2C  00 00 00 00        f32 0.0
    0x30  5D CB 4A BE        f32 -0.1980...
    0x34  47 D0 37 3F        f32 0.7180...
    0x38  7A 3D E5 3F        f32 1.7909...
    0x3C  1E 41 76 3E        f32 0.2405...
    0x40  9E 6D 00 00        u32 28062
    0x44  9E 6D 00 00        u32 28062
    0x48  00 01 00 00        u32 256
    0x4C  00 00 00 00        u32 0
    0x50  24 00 00 00        u32 36
    0x54  0A 00 00 00        u32 10
    0x58  2A 00 00 00        u32 42
    0x5C..0x7F zero bytes
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Tuple

HEADER_SIZE = 0x80  # fixed 128-byte header block, zero-padded


class FlverError(ValueError):
    """Raised when a FLVER payload does not match the observed header layout."""


@dataclass(frozen=True)
class FlverHeader:
    """Raw 128-byte FLVER header fields.

    Every field below is a verbatim observation from
    ``BD_M_10100.flver``; none of the field meanings is established.
    """

    magic: bytes                      # 0x00  b"FLVER\0"  [VERIFIED]
    u16_06: int                       # 0x06  76          [UNKNOWN]
    u16_08: int                       # 0x08  20          [UNKNOWN]
    u16_0a: int                       # 0x0A  2           [UNKNOWN]
    u32_0c: int                       # 0x0C  61488       [UNKNOWN]
    u32_10: int                       # 0x10  405520      [UNKNOWN]
    u32_14: int                       # 0x14  0           [UNKNOWN]
    u32_18: int                       # 0x18  6           [UNKNOWN]
    u32_1c: int                       # 0x1C  334         [UNKNOWN]
    u32_20: int                       # 0x20  6           [UNKNOWN]
    u32_24: int                       # 0x24  12          [UNKNOWN]
    bbox: Tuple[float, float, float, float, float, float]  # 0x28..0x3F six f32 [UNKNOWN]
    u32_40: int                       # 0x40  28062       [UNKNOWN]
    u32_44: int                       # 0x44  28062       [UNKNOWN]
    u32_48: int                       # 0x48  256         [UNKNOWN]
    u32_4c: int                       # 0x4C  0           [UNKNOWN]
    u32_50: int                       # 0x50  36          [UNKNOWN]
    u32_54: int                       # 0x54  10          [UNKNOWN]
    u32_58: int                       # 0x58  42          [UNKNOWN]


def parse_flver_header(data: bytes) -> FlverHeader:
    """Parse the 128-byte FLVER header from ``data``.

    Only the magic and the raw field values are checked; no field is assigned a
    meaning. Raises :class:`FlverError` on truncation or a bad magic.
    """
    if len(data) < HEADER_SIZE:
        raise FlverError(
            f"FLVER header needs {HEADER_SIZE} bytes, got {len(data)}"
        )
    magic = data[0x00:0x06]
    if magic != b"FLVER\x00":
        raise FlverError(f"bad FLVER magic: {magic!r}")

    bbox = struct.unpack_from("<6f", data, 0x28)
    return FlverHeader(
        magic=magic,
        u16_06=struct.unpack_from("<H", data, 0x06)[0],
        u16_08=struct.unpack_from("<H", data, 0x08)[0],
        u16_0a=struct.unpack_from("<H", data, 0x0A)[0],
        u32_0c=struct.unpack_from("<I", data, 0x0C)[0],
        u32_10=struct.unpack_from("<I", data, 0x10)[0],
        u32_14=struct.unpack_from("<I", data, 0x14)[0],
        u32_18=struct.unpack_from("<I", data, 0x18)[0],
        u32_1c=struct.unpack_from("<I", data, 0x1C)[0],
        u32_20=struct.unpack_from("<I", data, 0x20)[0],
        u32_24=struct.unpack_from("<I", data, 0x24)[0],
        bbox=bbox,
        u32_40=struct.unpack_from("<I", data, 0x40)[0],
        u32_44=struct.unpack_from("<I", data, 0x44)[0],
        u32_48=struct.unpack_from("<I", data, 0x48)[0],
        u32_4c=struct.unpack_from("<I", data, 0x4C)[0],
        u32_50=struct.unpack_from("<I", data, 0x50)[0],
        u32_54=struct.unpack_from("<I", data, 0x54)[0],
        u32_58=struct.unpack_from("<I", data, 0x58)[0],
    )
