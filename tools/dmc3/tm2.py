"""TM2 texture reader for the DMC3 HD Collection.

In the HD Collection a ``.tm2`` file is a thin wrapper: a small platform header
followed by a complete, ordinary **DDS** blob.  Extracting the texture is
therefore a matter of locating the ``DDS `` magic and handing the remainder to any
DDS-capable tool or GPU API.

Evidence: docs/EVIDENCE.md (E-005).  In ``i001_90.tm2`` the ``DDS `` magic begins
at file offset 0x70, followed by ``dwSize == 124`` and a plausible
height/width/mip count.

Note: this covers the *HD Collection* build.  The original PS2/PS3 ``.tm2`` is a
Capcom TIM2 container and is **not** handled here — see docs/FORMATS.md.
"""

from __future__ import annotations

import os
import struct
from dataclasses import dataclass
from typing import Optional

DDS_MAGIC = b"DDS "

_DDS_FOURCC_NAMES = {
    b"DXT1": "BC1/DXT1",
    b"DXT2": "DXT2",
    b"DXT3": "BC2/DXT3",
    b"DXT4": "DXT4",
    b"DXT5": "BC3/DXT5",
    b"ATI1": "BC4U",
    b"BC4U": "BC4U",
    b"BC4S": "BC4S",
    b"ATI2": "BC5U",
    b"BC5U": "BC5U",
    b"BC5S": "BC5S",
    b"DX10": "DX10 (extended header)",
    b"\x00\x00\x00\x00": "uncompressed BGRA/RGBA",
}

_DDPF_FOURCC = 0x4


class Tm2Error(ValueError):
    """Raised when a TM2/DDS payload cannot be interpreted."""


@dataclass(frozen=True)
class DdsInfo:
    """Fields of a legacy (non-DX10) DDS header."""

    width: int
    height: int
    data_offset: int
    """Offset of the payload after the header, relative to the DDS magic."""

    mipmaps: int
    fourcc: bytes
    pixel_format: str
    rgb_bits: int
    depth: int

    @property
    def is_compressed(self) -> bool:
        return self.fourcc not in (b"\x00\x00\x00\x00",) and self.fourcc != b""


def find_dds(data: bytes, start: int = 0) -> int:
    """Return the offset of the first ``DDS `` magic at or after ``start``."""
    index = data.find(DDS_MAGIC, start)
    if index < 0:
        raise Tm2Error("no DDS payload found (not an HD-Collection TM2?)")
    return index


def extract_dds(data: bytes, start: int = 0) -> bytes:
    """Return the embedded DDS blob (magic onward)."""
    return data[find_dds(data, start):]


def parse_dds_header(dds: bytes) -> DdsInfo:
    """Parse a legacy DDS header.  ``dds`` must begin with the DDS magic."""
    if dds[:4] != DDS_MAGIC:
        raise Tm2Error("payload does not start with the DDS magic")
    if len(dds) < 128:
        raise Tm2Error("DDS blob shorter than a 128-byte header")

    dw_size = struct.unpack_from("<I", dds, 4)[0]
    if dw_size != 124:
        raise Tm2Error(f"unexpected DDS header size {dw_size} (expected 124)")

    height = struct.unpack_from("<I", dds, 12)[0]
    width = struct.unpack_from("<I", dds, 16)[0]
    depth = struct.unpack_from("<I", dds, 24)[0]
    mipmaps = struct.unpack_from("<I", dds, 28)[0]

    pf_flags = struct.unpack_from("<I", dds, 80)[0]
    fourcc = dds[84:88]
    rgb_bits = struct.unpack_from("<I", dds, 88)[0]

    if pf_flags & _DDPF_FOURCC or fourcc == b"\x00\x00\x00\x00":
        name = _DDS_FOURCC_NAMES.get(fourcc, fourcc.decode("latin-1", "replace"))
    else:
        name = f"uncompressed {rgb_bits}bpp"

    data_offset = 128
    if fourcc == b"DX10":
        data_offset = 148  # 20-byte DXT10 header

    return DdsInfo(
        width=width,
        height=height,
        data_offset=data_offset,
        mipmaps=max(1, mipmaps),
        fourcc=fourcc,
        pixel_format=name,
        rgb_bits=rgb_bits,
        depth=depth,
    )


@dataclass(frozen=True)
class Tm2File:
    """An HD-Collection ``.tm2`` texture."""

    name: str
    raw: bytes

    @property
    def dds_offset(self) -> int:
        return find_dds(self.raw)

    def dds(self) -> bytes:
        return self.raw[self.dds_offset:]

    def info(self) -> DdsInfo:
        return parse_dds_header(self.dds())

    @property
    def suggested_name(self) -> str:
        stem = os.path.splitext(self.name)[0]
        return f"{stem}.dds"


def is_hd_tm2(data: bytes) -> bool:
    """Cheap probe: does this ``.tm2`` carry an embedded DDS blob?"""
    try:
        find_dds(data)
        return True
    except Tm2Error:
        return False


def load_tm2(path: str | os.PathLike[str]) -> Tm2File:
    with open(path, "rb") as handle:
        data = handle.read()
    return Tm2File(name=os.path.basename(os.fspath(path)), raw=data)
