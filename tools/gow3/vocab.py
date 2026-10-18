"""Mine the GoW3 engine's own vocabulary out of its executable (E-059).

The eboot carries the engine's class, object-type, script-command and
vertex-attribute tables as plain string runs. They name the *pieces* of the
formats we need to write, which is far cheaper than reading the code:

    vertex attributes   PS3_Pos, PS3_Normal, PS3_Tangent, PS3_SkinWeights0/1,
                        PS3_SkinIndices0/1, Generic_UV0..UV5, PS3_F32VertexAlpha,
                        PS3_SkinningFlipFactor, PS3_PrevFramePosition, ...
    mesh pipeline       MeshProc::RenderMeshes, FinalizePrims, MeshBounds, Cull
    script commands     SCR_SetPhase, SCR_PlayReplace, SCR_MaterialAnim,
                        SCR_VisJoint, SCR_SwitchNavBanks, SCR_ShaderSwap, ...
    behaviours          hfsmArrowEmitter, hfsmBalanceGeom, hfsmBreakable,
                        hfsmEnemy1, hfsmHeroBreak, hfsmReactive, hfsmSavePoint
    move system         ms::tMove, ms::tSys, ms::tCollisionInfo, ms::tSynchPartner
    small type table    float, bool, byte, color3, color4, matrix44
    animation blob name format string  ANM_%s

Everything here is *observed* strings, nothing more: this module makes no claim
about the binary layout of a vertex or a clip.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

_RUN = re.compile(rb"[\x20-\x7e]{2,120}")

SCRIPT_PREFIX = "SCR_"
HFSM_PREFIX = "hfsm"
CLASS_PREFIXES = ("ms::", "rs::", "ft::", "fx::", "go::", "gr::",
                  "ia::", "id::", "wl::")
VERTEX_PREFIXES = ("PS3_", "PS4_", "Generic_")

MESH_WORDS = ("Mesh", "mesh", "Prim", "prim", "Skin", "skin", "Vertex", "vertex",
              "Bone", "bone", "Geom", "geom", "Dma", "dma")

#: Attribute semantics that describe a *vertex*, as opposed to a shader uniform.
#: Drawn from the observed run; kept explicit so a caller can rely on the set.
VERTEX_SEMANTICS = (
    "PS3_Pos", "PS3_Normal", "PS3_DisplacementNormal", "PS3_Tangent",
    "PS3_BiTangent", "PS3_Diffuse", "PS3_Specular",
    "PS3_SkinWeights0", "PS3_SkinWeights1",
    "PS3_SkinIndices0", "PS3_SkinIndices1",
    "PS3_F32Diffuse", "PS3_F32Specular", "PS3_F32VertexAlpha",
    "PS3_SkinningFlipFactor", "PS3_PrevFramePosition", "PS3_VertexLightPos",
    " PS3_F32VertexAO".strip(), "PS3_F32ExtraDiffuse", "PS3_F32SimpleDiffuse",
    "PS3_NMblendData", "PS3_Emissive", "PS3_Shininess",
    "Generic_UV0", "Generic_UV1", "Generic_UV2", "Generic_UV3",
    "Generic_UV4", "Generic_UV5",
)

#: Mesh kinds observed as a type run in the binary.
MESH_TYPES = ("1UNUSED_MESH_TYPE", "Skinned")


@dataclass(frozen=True)
class Vocabulary:
    """The engine's named pieces, as extracted from one executable."""

    script_commands: List[str] = field(default_factory=list)
    vertex_semantics: List[str] = field(default_factory=list)
    mesh_names: List[str] = field(default_factory=list)
    hfsm_types: List[str] = field(default_factory=list)
    class_names: List[str] = field(default_factory=list)
    format_strings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, List[str]]:
        return {
            "script_commands": self.script_commands,
            "vertex_semantics": self.vertex_semantics,
            "mesh_names": self.mesh_names,
            "hfsm_types": self.hfsm_types,
            "class_names": self.class_names,
            "format_strings": self.format_strings,
        }


def read_strings(data: bytes) -> List[Tuple[int, str]]:
    """Every printable run of 2..120 bytes, as ``(offset, text)``."""
    return [(m.start(), m.group().decode("latin-1"))
            for m in _RUN.finditer(data)]


def _unique(items):
    seen, out = set(), []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def read_vocabulary(data: bytes) -> Vocabulary:
    """Extract the engine vocabulary from an executable image."""
    strings = read_strings(data)
    texts = [s for _o, s in strings]

    script = _unique(s for s in texts if s.startswith(SCRIPT_PREFIX))
    vertex = _unique(s for s in texts if s.startswith(VERTEX_PREFIXES)
                     and len(s) > 6)
    hfsm = _unique(s for s in texts if s.startswith(HFSM_PREFIX))
    classes = _unique(s for s in texts if s.startswith(CLASS_PREFIXES))
    mesh = _unique(s for s in texts
                   if any(word in s for word in MESH_WORDS) and len(s) < 90)
    formats = _unique(s for s in texts if "%s" in s and len(s) < 40)

    return Vocabulary(
        script_commands=script,
        vertex_semantics=vertex,
        mesh_names=mesh,
        hfsm_types=hfsm,
        class_names=classes,
        format_strings=formats,
    )


def vertex_attributes(vocabulary: Vocabulary) -> List[str]:
    """The subset of the vertex semantics that really are vertex attributes."""
    wanted = set(VERTEX_SEMANTICS)
    return [s for s in vocabulary.vertex_semantics if s in wanted]


def describe(vocabulary: Vocabulary) -> str:  # pragma: no cover - cosmetic
    return (f"{len(vocabulary.script_commands)} script commands, "
            f"{len(vocabulary.vertex_semantics)} PS3_/Generic_ names, "
            f"{len(vocabulary.hfsm_types)} hfsm types")
