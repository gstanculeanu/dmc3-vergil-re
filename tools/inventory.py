#!/usr/bin/env python3
"""Inventory every PAC/TM2 file in a DMC3 install and emit metadata as JSON.

Only *metadata* is produced (sizes, slot tables, chunk tags, MOT headers).  No
game payload is copied, so the result is safe to commit and to diff between
builds or regions.

Usage::

    python tools/inventory.py --gdata "G:\\...\\data\\dmc3\\GData.afs" --out inventory.json
    python tools/inventory.py --gdata "..." --only pl021
    set DMC3_GDATA=... & python tools/inventory.py --out inventory.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, Iterable, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dmc3 import PacArchive, load_tm2, parse_mot  # noqa: E402
from dmc3 import entities, mot as mot_mod, tm2 as tm2_mod  # noqa: E402

PAC_SUFFIXES = (".pac",)
TM2_SUFFIXES = (".tm2",)


def iter_inputs(root: str, only: Optional[str]) -> Iterable[str]:
    for dirpath, _dirnames, filenames in os.walk(root):
        for filename in sorted(filenames):
            lower = filename.lower()
            if not lower.endswith(PAC_SUFFIXES + TM2_SUFFIXES):
                continue
            if only and only.lower() not in lower:
                continue
            yield os.path.join(dirpath, filename)


def describe_motion(chunk) -> Optional[Dict[str, Any]]:
    if chunk.kind != "motion":
        return None
    try:
        header = parse_mot(chunk)
    except mot_mod.MotError as exc:
        return {"error": str(exc)}
    return {
        "header_size": header.header_size,
        "duration": round(header.duration, 4),
        "durations_match": header.durations_match,
        "flag_a": header.flag_a,
        "count_a": header.count_a,
        "count_b": header.count_b,
        "unknown_1e": header.unknown_1e,
        "unknown_20": header.unknown_20,
        "table_len": len(header.table),
        "table_values": sorted(set(header.table)),
        "payload_bytes": max(0, len(chunk.data) - header.payload_offset),
    }


def describe_pac(path: str) -> Dict[str, Any]:
    archive = PacArchive.from_path(path)
    summary = archive.summary()
    summary["entity"] = entities.label_for(os.path.splitext(summary["name"])[0])
    chunks: List[Dict[str, Any]] = []
    for chunk in archive.chunks():
        entry: Dict[str, Any] = {
            "slot": chunk.index,
            "offset": chunk.offset,
            "span": chunk.span,
            "kind": chunk.kind,
            "tag": chunk.tag_text if chunk.kind != "text" else "text",
        }
        motion = describe_motion(chunk)
        if motion is not None:
            entry["motion"] = motion
        chunks.append(entry)
    summary["chunks"] = chunks
    return summary


def describe_tm2(path: str) -> Dict[str, Any]:
    texture = load_tm2(path)
    result: Dict[str, Any] = {"name": texture.name, "size": len(texture.raw)}
    try:
        info = texture.info()
    except tm2_mod.Tm2Error as exc:
        result["error"] = str(exc)
        return result
    result.update(
        {
            "dds_offset": texture.dds_offset,
            "width": info.width,
            "height": info.height,
            "mipmaps": info.mipmaps,
            "pixel_format": info.pixel_format,
            "fourcc": info.fourcc.decode("latin-1", "replace").strip("\x00"),
        }
    )
    return result


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gdata",
        default=os.environ.get("DMC3_GDATA"),
        help="Path to the DMC3 data folder (env: DMC3_GDATA)",
    )
    parser.add_argument("--out", help="Write JSON here (default: stdout)")
    parser.add_argument("--only", help="Only files whose name contains this substring")
    parser.add_argument("--pretty", action="store_true", help="Indent the JSON")
    args = parser.parse_args(argv)

    if not args.gdata:
        parser.error("no --gdata given and DMC3_GDATA is not set")
    if not os.path.isdir(args.gdata):
        parser.error(f"--gdata is not a directory: {args.gdata}")

    files: Dict[str, Any] = {}
    errors: Dict[str, str] = {}
    for path in iter_inputs(args.gdata, args.only):
        rel = os.path.relpath(path, args.gdata).replace("\\", "/")
        try:
            if path.lower().endswith(PAC_SUFFIXES):
                files[rel] = describe_pac(path)
            else:
                files[rel] = describe_tm2(path)
        except Exception as exc:  # noqa: BLE001 - inventory must never abort
            errors[rel] = f"{type(exc).__name__}: {exc}"

    document = {
        "source": os.path.abspath(args.gdata),
        "file_count": len(files),
        "error_count": len(errors),
        "files": files,
        "errors": errors,
    }

    text = json.dumps(document, indent=2 if args.pretty else None, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text)
        print(f"wrote {args.out}: {len(files)} files, {len(errors)} errors")
    else:
        print(text)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
