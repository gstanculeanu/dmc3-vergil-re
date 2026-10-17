#!/usr/bin/env python3
"""Extract Vergil's (or any entity's) chunks and textures out of a DMC3 install.

Extraction writes *derived game data* to an output directory that must live
**outside this repository**.  The tool refuses to write inside the repo tree so an
accidental commit of copyrighted payloads is impossible.

Usage::

    python tools/extract_assets.py --gdata "G:\\...\\GData.afs" --entity pl021 --out D:\\re\\vergil
    python tools/extract_assets.py --gdata "..." --entity pl021 --out D:\\re\\vergil --include-motions
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dmc3 import PacArchive, load_tm2  # noqa: E402
from dmc3 import entities  # noqa: E402

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

_EXT_BY_KIND = {
    "model": "mod",
    "shader": "shw",
    "motion": "mot",
    "text": "txt",
    "raw": "raw",
}


def guard_output(out_dir: str) -> None:
    out_abs = os.path.abspath(out_dir)
    if out_abs == REPO_ROOT or out_abs.startswith(REPO_ROOT + os.sep):
        raise SystemExit(
            "refusing to extract into the repository "
            f"({out_abs}); choose a directory outside {REPO_ROOT}"
        )


def collect_source_files(gdata: str, entity: str, include_motions: bool) -> List[str]:
    """Return the archive paths that make up ``entity``."""
    wanted: List[str] = []
    for dirpath, _dirs, filenames in os.walk(gdata):
        for filename in sorted(filenames):
            lower = filename.lower()
            if not lower.endswith(".pac"):
                continue
            stem = os.path.splitext(filename)[0]
            if stem == entity:
                wanted.append(os.path.join(dirpath, filename))
            elif include_motions and stem.startswith(entity + "_"):
                wanted.append(os.path.join(dirpath, filename))
    return wanted


def extract_archive(path: str, out_dir: str) -> Dict[str, object]:
    archive = PacArchive.from_path(path)
    stem = os.path.splitext(os.path.basename(path))[0]
    target = os.path.join(out_dir, stem)
    os.makedirs(target, exist_ok=True)

    manifest: Dict[str, object] = {
        "source": os.path.basename(path),
        "entries": archive.entry_count,
        "chunks": [],
    }
    for chunk in archive.chunks():
        ext = _EXT_BY_KIND.get(chunk.kind, "raw")
        name = f"{stem}__slot{chunk.index:03d}.{ext}"
        with open(os.path.join(target, name), "wb") as handle:
            handle.write(chunk.trimmed if chunk.kind == "text" else chunk.data)
        manifest["chunks"].append(  # type: ignore[attr-defined]
            {
                "slot": chunk.index,
                "kind": chunk.kind,
                "offset": chunk.offset,
                "span": chunk.span,
                "file": name,
            }
        )

    # Textures live beside the model archives as standalone .tm2 files.
    return manifest


def extract_textures(gdata: str, out_dir: str, patterns: List[str]) -> List[str]:
    written: List[str] = []
    textures_dir = os.path.join(out_dir, "textures")
    os.makedirs(textures_dir, exist_ok=True)
    for dirpath, _dirs, filenames in os.walk(gdata):
        for filename in sorted(filenames):
            if not filename.lower().endswith(".tm2"):
                continue
            stem = os.path.splitext(filename)[0]
            if patterns and not any(p.lower() in stem.lower() for p in patterns):
                continue
            texture = load_tm2(os.path.join(dirpath, filename))
            try:
                dds = texture.dds()
            except Exception:  # noqa: BLE001
                continue
            name = f"{stem}.dds"
            with open(os.path.join(textures_dir, name), "wb") as handle:
                handle.write(dds)
            written.append(name)
    return written


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gdata", default=os.environ.get("DMC3_GDATA"),
        help="DMC3 data folder (env: DMC3_GDATA)",
    )
    parser.add_argument("--entity", default="pl021", help="Entity id, e.g. pl021 (Vergil)")
    parser.add_argument("--out", required=True, help="Output directory (outside the repo)")
    parser.add_argument("--include-motions", action="store_true", help="Also extract plNNN_00_* motion sets")
    parser.add_argument("--textures", nargs="*", default=[], help="TM2 name substrings to export as DDS")
    args = parser.parse_args(argv)

    if not args.gdata or not os.path.isdir(args.gdata):
        parser.error("--gdata must point at an existing DMC3 data folder")

    guard_output(args.out)
    os.makedirs(args.out, exist_ok=True)

    sources = collect_source_files(args.gdata, args.entity, args.include_motions)
    if not sources:
        print(f"no archives found for entity {args.entity!r}", file=sys.stderr)
        return 1

    manifests: List[Dict[str, object]] = []
    for path in sources:
        label = entities.label_for(os.path.splitext(os.path.basename(path))[0])
        print(f"extracting {os.path.basename(path)} ({label})")
        manifests.append(extract_archive(path, args.out))

    textures = extract_textures(args.gdata, args.out, args.textures)
    if textures:
        print(f"exported {len(textures)} texture(s) as DDS")

    with open(os.path.join(args.out, "manifest.json"), "w", encoding="utf-8") as handle:
        json.dump(
            {
                "entity": args.entity,
                "label": entities.label_for(args.entity),
                "archives": manifests,
                "textures": textures,
            },
            handle,
            indent=2,
            sort_keys=True,
        )

    print(f"done -> {os.path.abspath(args.out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
