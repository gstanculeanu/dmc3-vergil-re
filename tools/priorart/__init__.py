"""Parsers for third-party interchange meshes found in the prior-art package.

The Bloodborne Vergil mod (see docs/PRIOR-ART.md, evidence E-014) ships Vergil's
mesh in Source-engine text formats:

* ``.smd``   — studiomdl ``version 1`` (nodes / skeleton / triangles)
* ``.ascii`` — Source reference mesh (bones, materials, vertices, faces)

Both are read-only. Nothing here writes a game asset into the repository; OBJ
output goes wherever the caller asks.
"""

from .obj import ObjBuilder
from .sourceascii import AsciiFile, AsciiMesh, AsciiVertex, parse_ascii
from .sourcesmd import SmdFile, SmdVertex, parse_smd

__all__ = [
    "ObjBuilder",
    "AsciiFile",
    "AsciiMesh",
    "AsciiVertex",
    "parse_ascii",
    "SmdFile",
    "SmdVertex",
    "parse_smd",
]
