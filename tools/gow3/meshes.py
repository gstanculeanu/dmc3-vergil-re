"""Mesh definitions in ``R_*.WAD``: ``MDL_<hash>`` and its ``MG_<hash>_<n>`` groups (E-073).

The front directory's resources (``MDLX_R_Hades``, ``TXRX_R_Hades``, ...) are
**16-byte stubs** -- handles, not payloads. The payloads live in the body, and a
mesh is defined there as a named record::

    0x48F57D8  resource  id=1 flags=0x52 size=128  "MDL_4196b97c"
    0x48F58E0  resource                           "MG_4196b97c_0"    <- mesh groups
    0x48F5920  GroupEnd
    0x48F5960  GroupStart
    0x48F59A0  resource  id=1 flags=0x1F size=148  "gochain"
    ...

``R_HADES.WAD`` carries **19 unique** ``MDL_`` definitions, each exactly 128 bytes
with ``flags = 0x52``, and each followed by one or more ``MG_<hash>_<index>``
records. Every one of them references ``MAT_ubershader1``: the boss renders
through a single ubershader material.

What is *not* established here: where the vertex and index buffers are. A 128-byte
definition cannot hold geometry, and the 4-byte hash is not present as a u32 in
the body (0 hits for the first four), so the definition-to-geometry link is still
[UNKNOWN]. This module only enumerates what is observed.
"""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass
from typing import List, Optional, Tuple

from . import groups

MDL_RE = re.compile(rb"MDL_[0-9a-f]{6,10}")
MG_RE = re.compile(r"^MG_([0-9a-f]{6,10})_(\d+)$")


class MeshError(ValueError):
    """Raised when bytes cannot be read as a mesh definition or group."""

#: ``flags`` observed on every mesh definition.
MESH_FLAGS = 0x52
#: Every observed ``MDL_`` definition is exactly this long.
MESH_DEFINITION_SIZE = 128
#: How far past a definition to look for its ``MG_`` groups.
GROUP_SEARCH_WINDOW = 0x4000


@dataclass(frozen=True)
class MeshDefinition:
    """One ``MDL_<hash>`` record and the mesh groups that follow it."""

    name: str
    offset: int
    size: int
    flags: int
    data: int
    end: int
    groups: Tuple[str, ...] = ()

    @property
    def hash(self) -> str:
        return self.name.split("_", 1)[1]

    def payload(self, data: bytes) -> bytes:
        return data[self.data:self.data + self.size]

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return (f"{self.name} @0x{self.offset:08X} size={self.size} "
                f"groups={list(self.groups)}")


def _group_names(data: bytes, start: int, end: int, hash_: str) -> Tuple[str, ...]:
    """``MG_<hash>_<n>`` names for one mesh hash, in file order."""
    found: List[str] = []
    for match in re.finditer(rb"MG_[0-9a-f]{6,10}_\d+", data[start:end]):
        name = match.group().decode("latin-1")
        parsed = MG_RE.match(name)
        if parsed and parsed.group(1) == hash_ and name not in found:
            found.append(name)
    return tuple(found)


def find_mesh_definitions(data: bytes, limit: int = 4096) -> List[MeshDefinition]:
    """Every ``MDL_<hash>`` definition in a WAD, in file order.

    A name only counts when a valid resource record sits exactly 8 bytes before
    it, which is what makes this an enumeration of definitions rather than of
    string occurrences.
    """
    out: List[MeshDefinition] = []
    seen = set()
    for match in MDL_RE.finditer(data):
        at = match.start() - 8
        if at < groups.RECORD_START:
            continue
        try:
            record = groups.read_record(data, at)
        except groups.LayoutError:
            continue
        name = match.group().decode("latin-1")
        if record.name != name or name in seen:
            continue
        seen.add(name)
        window_end = min(len(data), record.end + GROUP_SEARCH_WINDOW)
        out.append(MeshDefinition(
            name=name, offset=record.offset, size=record.size or 0,
            flags=record.flags, data=record.data or record.end, end=record.end,
            groups=_group_names(data, record.end, window_end, name.split("_", 1)[1]),
        ))
        if len(out) >= limit:
            break
    return out


def materials(data: bytes) -> List[str]:
    """``MAT_*`` material names present anywhere in a WAD, in file order."""
    out: List[str] = []
    for match in re.finditer(rb"MAT_[A-Za-z0-9_:.]{2,60}", data):
        name = match.group().decode("latin-1")
        if name not in out:
            out.append(name)
    return out


# ---------------------------------------------------------------------------
# Mesh groups: the geometry (E-075)
# ---------------------------------------------------------------------------
#
# The ``MDL_<hash>`` record is only a definition. The geometry is in the matching
# ``MG_<hash>_<n>`` record, which carries a real size:
#
#     MG_3c8ec52_0   size 1,150,564
#
# and 0x4C8F7B0 + 1,150,564 + 12 bytes of 16-byte padding = 0x4DA8620, exactly
# where ``MDL_3c8ec52`` begins. Its payload opens with a 0x28-byte descriptor,
# then 20-byte vertex records:
#
#     descriptor: u16 0x000D ; u16 1 ; u32 vertex_bytes ; u16 b ; u16 n
#                 ; u32 32 ; u32 0 ; u32 0x10000 ; u32 x4
#     vertex    : u16 skin_index (0xFFFF = unskinned) ; u16 skin_weight
#                 ; f32 x4      e.g. 11.771, -0.2368, 4.5402, -3.1027
#
# On ``MG_3c8ec52_0`` the descriptor's ``vertex_bytes`` is 187,840 and
# 187,840 / 20 = **9,392** vertices; its ``n`` is 155, matching the observed run of
# clean records. The first four floats are model-space on a device-scale boss.
# Which of the four floats is position vs something else is [UNKNOWN].

GROUP_RECORD_RE = re.compile(rb"MG_[0-9a-f]{6,10}_\d+")
VERTEX_STRIDE = 20
SKIN_SENTINEL = 0xFFFF
HEADER_SIZE = 0x28


@dataclass(frozen=True)
class MeshGroup:
    """A ``MG_<hash>_<n>`` record: the geometry for one mesh definition."""

    name: str
    offset: int
    size: int
    flags: int
    data: int

    @property
    def hash(self) -> str:
        return self.name.split("_")[1]

    @property
    def index(self) -> int:
        return int(self.name.rsplit("_", 1)[1])

    @property
    def descriptor(self) -> int:
        """Offset of the 0x28-byte descriptor, which sits in the second header."""
        return self.offset + groups.RECORD_SIZE

    def payload(self, data: bytes) -> bytes:
        return data[self.data:self.data + self.size]

    def header(self, data: bytes) -> "GroupHeader":
        return parse_group_header(data, self.descriptor)

    def vertex_count(self, data: bytes) -> int:
        """``vertex_bytes / 20`` from the descriptor, or 0 if it is absent."""
        return self.header(data).vertex_count

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return f"{self.name} @0x{self.offset:08X} size={self.size:,}"


@dataclass(frozen=True)
class GroupHeader:
    """The 0x28-byte descriptor at the start of a mesh-group payload."""

    ident: int
    flags: int
    vertex_bytes: int
    field8: int
    first_count: int
    field12: int
    field16: int
    field20: int
    offsets: Tuple[int, int, int, int]

    @property
    def vertex_count(self) -> int:
        return self.vertex_bytes // VERTEX_STRIDE


def parse_group_header(data: bytes, at: int) -> GroupHeader:
    """Read the mesh-group descriptor at ``at``.

    Raises :class:`meshes.MeshError` when the bytes cannot hold a descriptor.
    """
    if at < 0 or at + HEADER_SIZE > len(data):
        raise MeshError(f"no room for a {HEADER_SIZE}-byte group header at 0x{at:X}")
    ident, flags, vertex_bytes, field8, first_count, field12, field16, field20 = \
        struct.unpack_from("<HHIHHIII", data, at)
    offsets = struct.unpack_from("<4I", data, at + 0x18)
    return GroupHeader(ident=ident, flags=flags, vertex_bytes=vertex_bytes,
                       field8=field8, first_count=first_count, field12=field12,
                       field16=field16, field20=field20, offsets=offsets)


def find_mesh_groups(data: bytes, limit: int = 4096) -> List[MeshGroup]:
    """Every ``MG_<hash>_<n>`` record that carries geometry, in file order.

    A group appears more than once in a WAD; only the occurrence with a non-zero
    size holds the geometry, and that is the one returned (first per name).
    """
    out: List[MeshGroup] = []
    seen = set()
    for match in GROUP_RECORD_RE.finditer(data):
        at = match.start() - 8
        if at < groups.RECORD_START:
            continue
        try:
            record = groups.read_record(data, at)
        except groups.LayoutError:
            continue
        name = match.group().decode("latin-1")
        if record.name != name or name in seen:
            continue
        if not record.size or record.data is None:
            continue
        seen.add(name)
        out.append(MeshGroup(name=name, offset=record.offset, size=record.size,
                             flags=record.flags, data=record.data))
        if len(out) >= limit:
            break
    return out


def object_names(data: bytes) -> List[str]:
    """``go<name>`` object records (id=1, flags=0x1F, size=148).

    ``gochain`` and ``goevtlevelloaded`` are the observed examples.
    """
    out: List[str] = []
    for match in re.finditer(rb"go[a-z][a-z0-9_]{2,40}", data):
        name = match.group().decode("latin-1")
        if name not in out:
            out.append(name)
    return out
