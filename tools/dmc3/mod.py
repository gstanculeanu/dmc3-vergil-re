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

from .pac import Chunk, f32, u32

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
