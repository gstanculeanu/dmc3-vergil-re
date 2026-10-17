#!/usr/bin/env python3
"""Convert prior-art Source meshes (``.smd`` / ``.ascii``) to Wavefront OBJ.

Input is Vergil's mesh from the third-party Bloodborne mod package
(``docs/PRIOR-ART.md``, E-014). It is third-party game data: output must go
**outside** this repository, and the tool refuses otherwise.

Usage::

    python tools/priorart/convert.py "<path>\\WP_A_10100.smd"   --out D:\\re\\yamato.obj
    python tools/priorart/convert.py "<path>\\WP_A_10100.ascii" --out D:\\re\\yamato.obj --stats
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from priorart import parse_ascii, parse_smd  # noqa: E402

REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)


def guard_output(out_path: str) -> None:
    out_abs = os.path.abspath(out_path)
    if out_abs == REPO_ROOT or out_abs.startswith(REPO_ROOT + os.sep):
        raise SystemExit(
            "refusing to write converted game assets into the repository "
            f"({out_abs}); choose a path outside {REPO_ROOT}"
        )


def load(path: str):
    """Return (kind, parsed) for a supported extension."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".smd":
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return "smd", parse_smd(handle.read())
    if ext == ".ascii":
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return "ascii", parse_ascii(handle.read())
    raise SystemExit(f"unsupported input extension {ext!r} (expected .smd or .ascii)")


def _short(items, limit: int = 6) -> str:
    items = list(items)
    if len(items) <= limit:
        return str(items)
    return f"{items[:limit]} ... (+{len(items) - limit} more)"


def summarise(kind: str, parsed) -> str:
    if kind == "smd":
        materials = [name for name, _ in parsed.groups]
        return (
            f"smd: version={parsed.version} nodes={len(parsed.nodes)} "
            f"bones={len(parsed.bones)} materials={len(parsed.groups)} "
            f"vertices={parsed.vertex_count} triangles={parsed.triangle_count}\n"
            f"     node names: {_short([n.name for n in parsed.nodes], 12)}\n"
            f"     materials:  {_short(materials)}"
        )
    names = [m.name for m in parsed.meshes]
    tex = [
        t.path.replace("\\", "/").rsplit("/", 1)[-1]
        for m in parsed.meshes
        for t in m.textures
    ]
    return (
        f"ascii: bones={len(parsed.bones)} meshes={len(parsed.meshes)} "
        f"vertices={parsed.vertex_count} triangles={parsed.triangle_count}\n"
        f"     bone names: {_short([b.name for b in parsed.bones], 12)}\n"
        f"     meshes:     {_short(names)}\n"
        f"     textures:   {_short(tex, 10)}"
    )


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help=".smd or .ascii file (third-party, outside the repo)")
    parser.add_argument("--out", required=True, help="Output .obj path (outside the repo)")
    parser.add_argument("--object-name", default=None, help="OBJ object name (default: file stem)")
    parser.add_argument("--stats", action="store_true", help="Print a summary and exit")
    args = parser.parse_args(argv)

    kind, parsed = load(args.input)
    summary = summarise(kind, parsed)
    print(summary)

    if args.stats:
        return 0

    guard_output(args.out)
    object_name = args.object_name or os.path.splitext(os.path.basename(args.input))[0]
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(parsed.to_obj(object_name=object_name))

    print(f"wrote {args.out} ({kind} -> obj)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
