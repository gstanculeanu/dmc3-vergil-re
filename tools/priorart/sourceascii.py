"""Source reference-mesh ``.ascii`` parser.

Layout, as observed in the prior-art package (docs/PRIOR-ART.md, E-014)::

    <bone_count>
    <bone name>
    <bone parent>
    <px> <py> <pz> <rx> <ry> <rz> <rw>          # repeated bone_count times
    ...
    <mesh_count>
    <mesh name>
    <unknown int>                                # 2 in the sample
    <texture_count>
    <texture path>
    <texture flags>
    ...                                          # repeated texture_count times
    <vertex_count>
    <px> <py> <pz>
    <nx> <ny> <nz>
    <r> <g> <b> <a>
    <u> <v>
    <u2> <v2>
    <b0> <b1> <b2> <b3>                          # bone indices
    <w0> <w1> <w2> <w3>                          # bone weights
    ...                                          # repeated vertex_count times
    <face_count>
    <i0> <i1> <i2>
    ...                                          # repeated face_count times

Every field above was read from the file:
``WP_A_10100.ascii`` has 8 bones, 1 mesh, 7 textures, 1176 vertices and 1852
faces, and ``1176 * 7 + 1852`` lines after the header matches the file length
exactly. The bone index/weight order is confirmed against the sibling ``.smd``,
where the same corner reads ``links=1 bone=4 weight=0.996078``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from .obj import ObjBuilder

Vec3 = Tuple[float, float, float]
Vec2 = Tuple[float, float]

VERTEX_LINES = 7


class AsciiError(ValueError):
    """Raised when an ``.ascii`` payload does not match the documented layout."""


@dataclass(frozen=True)
class AsciiBone:
    name: str
    parent: int
    position: Vec3
    rotation: Tuple[float, float, float, float]


@dataclass(frozen=True)
class AsciiTexture:
    path: str
    flags: int


@dataclass(frozen=True)
class AsciiVertex:
    position: Vec3
    normal: Vec3
    color: Tuple[float, float, float, float]
    uv: Vec2
    uv2: Vec2
    bones: Tuple[int, int, int, int]
    weights: Tuple[float, float, float, float]


@dataclass
class AsciiMesh:
    name: str
    unknown: int
    textures: List[AsciiTexture] = field(default_factory=list)
    vertices: List[AsciiVertex] = field(default_factory=list)
    faces: List[Tuple[int, int, int]] = field(default_factory=list)


@dataclass
class AsciiFile:
    bones: List[AsciiBone] = field(default_factory=list)
    meshes: List[AsciiMesh] = field(default_factory=list)

    @property
    def vertex_count(self) -> int:
        return sum(len(m.vertices) for m in self.meshes)

    @property
    def triangle_count(self) -> int:
        return sum(len(m.faces) for m in self.meshes)

    def to_obj(self, object_name: str = "ascii") -> str:
        builder = ObjBuilder()
        for mesh in self.meshes:
            group = mesh.name or "mesh"
            corners = [
                builder.vertex(v.position, v.uv, v.normal) for v in mesh.vertices
            ]
            for a, b, c in mesh.faces:
                try:
                    builder.face(group, [corners[a], corners[b], corners[c]])
                except IndexError as exc:  # pragma: no cover - guarded by parser
                    raise AsciiError(
                        f"face references vertex {max(a, b, c)} "
                        f"but mesh has {len(corners)}"
                    ) from exc
        return builder.to_obj(object_name=object_name)


def _floats(line: str, count: int, what: str) -> Sequence[float]:
    tokens = line.split()
    if len(tokens) < count:
        raise AsciiError(f"expected {count} values for {what}, got {tokens!r}")
    return [float(t) for t in tokens[:count]]


def parse_ascii(text: str) -> AsciiFile:
    """Parse a Source reference-mesh ``.ascii`` document."""
    text = text.lstrip("\ufeff")
    lines = [line.rstrip("\r\n") for line in text.splitlines()]
    cursor = 0
    total = len(lines)

    def take(what: str) -> str:
        nonlocal cursor
        while cursor < total and not lines[cursor].strip():
            cursor += 1
        if cursor >= total:
            raise AsciiError(f"unexpected end of file while reading {what}")
        line = lines[cursor]
        cursor += 1
        return line

    def take_int(what: str) -> int:
        return int(take(what).strip())

    result = AsciiFile()

    bone_count = take_int("bone count")
    for _ in range(bone_count):
        name = take("bone name").strip()
        parent = int(take("bone parent").strip())
        values = _floats(take("bone transform"), 7, "bone transform")
        result.bones.append(
            AsciiBone(
                name=name,
                parent=parent,
                position=(values[0], values[1], values[2]),
                rotation=(values[3], values[4], values[5], values[6]),
            )
        )

    mesh_count = take_int("mesh count")
    for _ in range(mesh_count):
        name = take("mesh name").strip()
        unknown = int(take("mesh unknown").strip())
        texture_count = take_int("texture count")
        mesh = AsciiMesh(name=name, unknown=unknown)
        for _ in range(texture_count):
            path = take("texture path").strip()
            flags = int(take("texture flags").strip())
            mesh.textures.append(AsciiTexture(path=path, flags=flags))

        vertex_count = take_int("vertex count")
        for _ in range(vertex_count):
            position = _floats(take("vertex position"), 3, "vertex position")
            normal = _floats(take("vertex normal"), 3, "vertex normal")
            color = _floats(take("vertex color"), 4, "vertex color")
            uv = _floats(take("vertex uv"), 2, "vertex uv")
            uv2 = _floats(take("vertex uv2"), 2, "vertex uv2")
            bones = [int(float(t)) for t in take("vertex bones").split()[:4]]
            weights = _floats(take("vertex weights"), 4, "vertex weights")
            padded_bones = (bones + [0, 0, 0, 0])[:4]
            mesh.vertices.append(
                AsciiVertex(
                    position=(position[0], position[1], position[2]),
                    normal=(normal[0], normal[1], normal[2]),
                    color=(color[0], color[1], color[2], color[3]),
                    uv=(uv[0], uv[1]),
                    uv2=(uv2[0], uv2[1]),
                    bones=(padded_bones[0], padded_bones[1], padded_bones[2], padded_bones[3]),
                    weights=(weights[0], weights[1], weights[2], weights[3]),
                )
            )

        if cursor >= total:
            result.meshes.append(mesh)
            continue
        face_count = take_int("face count")
        for _ in range(face_count):
            tokens = take("face").split()
            if len(tokens) < 3:
                raise AsciiError(f"malformed face: {tokens!r}")
            mesh.faces.append((int(tokens[0]), int(tokens[1]), int(tokens[2])))
        result.meshes.append(mesh)

    return result


def parse_ascii_file(path: str) -> AsciiFile:
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return parse_ascii(handle.read())
