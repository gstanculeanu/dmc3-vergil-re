"""Source studiomdl ``.smd`` parser (``version 1``).

Layout::

    version 1
    nodes
    <index> "<name>" <parent>
    end
    skeleton
    time <t>
    <index> <px> <py> <pz> <rx> <ry> <rz>
    end
    triangles
    <material>
    <bone> <px> <py> <pz> <nx> <ny> <nz> <u> <v> <links> [<bone> <weight>]*
    ...
    end

Observed on the prior-art package (docs/PRIOR-ART.md, E-014): 8 nodes, one
``time 0`` skeleton frame, 1852 triangles in a single material group.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from .obj import ObjBuilder

Vec3 = Tuple[float, float, float]
Vec2 = Tuple[float, float]


class SmdError(ValueError):
    """Raised when an SMD payload does not match the documented layout."""


@dataclass(frozen=True)
class SmdNode:
    index: int
    name: str
    parent: int


@dataclass(frozen=True)
class SmdBone:
    index: int
    position: Vec3
    rotation: Vec3


@dataclass(frozen=True)
class SmdVertex:
    bone: int
    position: Vec3
    normal: Vec3
    uv: Vec2
    links: Tuple[Tuple[int, float], ...] = ()


@dataclass
class SmdFile:
    version: int = 1
    nodes: List[SmdNode] = field(default_factory=list)
    bones: List[SmdBone] = field(default_factory=list)
    groups: List[Tuple[str, List[SmdVertex]]] = field(default_factory=list)

    @property
    def triangle_count(self) -> int:
        return sum(len(v) // 3 for _name, v in self.groups)

    @property
    def vertex_count(self) -> int:
        return sum(len(v) for _name, v in self.groups)

    def to_obj(self, object_name: str = "smd") -> str:
        builder = ObjBuilder()
        for material, verts in self.groups:
            group = material_name(material)
            pending = []
            for vertex in verts:
                pending.append(builder.vertex(vertex.position, vertex.uv, vertex.normal))
                if len(pending) == 3:
                    builder.face(group, pending)
                    pending = []
        return builder.to_obj(object_name=object_name)


def material_name(raw: str) -> str:
    """Reduce an SMD material string to a readable name.

    Exporters sometimes write ``MaterialName\\full\\source\\path\\texture.tif``;
    the material is the part before the first separator.
    """
    for separator in ("\\", "/"):
        if separator in raw:
            head = raw.split(separator, 1)[0].strip()
            if head:
                return head
    return raw.strip() or "default"


def _is_number(token: str) -> bool:
    try:
        float(token)
        return True
    except ValueError:
        return False


def parse_smd(text: str) -> SmdFile:
    """Parse an SMD document."""
    # Strip a UTF-8 BOM if present.
    text = text.lstrip("\ufeff")
    raw_lines = [line.rstrip("\r\n") for line in text.splitlines()]

    result = SmdFile()
    section: Optional[str] = None
    current_material: Optional[str] = None
    current_vertices: List[SmdVertex] = []

    def flush_material() -> None:
        nonlocal current_material, current_vertices
        if current_material is not None and current_vertices:
            result.groups.append((current_material, current_vertices))
        current_material = None
        current_vertices = []

    for lineno, line in enumerate(raw_lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue

        lowered = stripped.lower()

        if lowered.startswith("version"):
            parts = stripped.split()
            if len(parts) >= 2 and parts[1].isdigit():
                result.version = int(parts[1])
            section = None
            continue

        if lowered in ("nodes", "skeleton", "triangles"):
            if lowered == "triangles":
                flush_material()
            section = lowered
            continue

        if lowered == "end":
            if section == "triangles":
                flush_material()
            section = None
            continue

        if section == "nodes":
            tokens = stripped.split()
            if len(tokens) < 3:
                raise SmdError(f"line {lineno}: malformed node: {stripped!r}")
            result.nodes.append(
                SmdNode(
                    index=int(tokens[0]),
                    name=tokens[1].strip('"'),
                    parent=int(tokens[2]),
                )
            )
            continue

        if section == "skeleton":
            if lowered.startswith("time"):
                continue
            tokens = stripped.split()
            if len(tokens) < 7:
                raise SmdError(f"line {lineno}: malformed bone: {stripped!r}")
            values = [float(t) for t in tokens[1:7]]
            result.bones.append(
                SmdBone(
                    index=int(tokens[0]),
                    position=(values[0], values[1], values[2]),
                    rotation=(values[3], values[4], values[5]),
                )
            )
            continue

        if section == "triangles":
            tokens = stripped.split()
            if len(tokens) < 9 or not _is_number(tokens[0]):
                # A non-numeric line opens (or repeats) a material group. Many
                # exporters re-emit the same material name before every
                # triangle; only a *change* starts a new group.
                if current_material is None:
                    current_material = stripped
                elif stripped != current_material:
                    flush_material()
                    current_material = stripped
                continue
            if current_material is None:
                # Some writers omit the material line; synthesise one.
                current_material = "default"
            bone = int(float(tokens[0]))
            nums = [float(t) for t in tokens[1:9]]
            links: List[Tuple[int, float]] = []
            if len(tokens) > 9:
                count = int(float(tokens[9]))
                cursor = 10
                for _ in range(count):
                    if cursor + 1 >= len(tokens) + 1 and cursor + 1 > len(tokens):
                        break
                    try:
                        links.append((int(float(tokens[cursor])), float(tokens[cursor + 1])))
                    except (IndexError, ValueError):
                        break
                    cursor += 2
            current_vertices.append(
                SmdVertex(
                    bone=bone,
                    position=(nums[0], nums[1], nums[2]),
                    normal=(nums[3], nums[4], nums[5]),
                    uv=(nums[6], nums[7]),
                    links=tuple(links),
                )
            )
            continue

    return result


def parse_smd_file(path: str) -> SmdFile:
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return parse_smd(handle.read())
