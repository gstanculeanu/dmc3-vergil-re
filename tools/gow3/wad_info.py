#!/usr/bin/env python3
"""Report on a GoW3R ``R_*.WAD`` archive: header, DC_ markers, name families, AI.

Reconnaissance only -- the record directory that binds names to bytes is not yet
decoded (see docs/EVIDENCE.md E-016/E-022), so this prints structure, not assets.

Usage::

    python tools/gow3/wad_info.py --wad-dir "<dump>\\EXEC\\WAD\\PS4_LE" --limit 12
    python tools/gow3/wad_info.py --file "<dump>\\...\\R_HERCULES.WAD" --json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gow3 import wad  # noqa: E402
from gow3.wad import WadError  # noqa: E402


def show(info: wad.WadInfo, verbose: bool) -> None:
    kind = "AI" if info.carries_ai else ("entity" if info.header.is_entity_wad else "other")
    print(f"\n{os.path.basename(info.path)}  [{kind}]")
    print(f"  size            {info.size:,}")
    print(f"  banner          {info.header.banner!r}  (magic {info.header.magic0}/{info.header.magic1})")
    print(f"  DC_ markers     {len(info.dc_markers)}"
          f"{' (as expected)' if info.dc_count_ok else ''}"
          f"  prefixes_ok={all(m.prefix_matches for m in info.dc_markers)}")
    if verbose:
        for marker in info.dc_markers:
            print(f"      +0x{marker.offset:08X}  {marker.name}")
        families = ", ".join(f"{k}={v}" for k, v in info.name_families.items())
        print(f"  name families   {families}")
    if info.hfsm_names:
        print(f"  AI state machines  {info.hfsm_names}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wad-dir", help="folder of *.WAD files")
    parser.add_argument("--file", help="a single *.WAD file")
    parser.add_argument("--limit", type=int, default=8, help="max files in --wad-dir")
    parser.add_argument("--ai-only", action="store_true", help="only report AI WADs")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    paths: List[str] = []
    if args.file:
        paths = [args.file]
    elif args.wad_dir:
        if not os.path.isdir(args.wad_dir):
            parser.error(f"not a directory: {args.wad_dir}")
        names = sorted(f for f in os.listdir(args.wad_dir) if f.upper().endswith(".WAD"))
        names.sort(key=lambda n: os.path.getsize(os.path.join(args.wad_dir, n)))
        paths = [os.path.join(args.wad_dir, n) for n in names[:args.limit]]
    else:
        parser.error("give --file or --wad-dir")

    infos = []
    for path in paths:
        try:
            info = wad.inspect(path)
        except (OSError, WadError) as exc:
            print(f"skip {os.path.basename(path)}: {exc}", file=sys.stderr)
            continue
        if args.ai_only and not info.carries_ai:
            continue
        infos.append(info)
        if not args.json and not args.quiet:
            show(info, verbose=not args.quiet)

    if args.json:
        print(json.dumps([i.summary() for i in infos], indent=2))
    elif not args.quiet:
        ai = [i for i in infos if i.carries_ai]
        print(f"\n{len(infos)} archive(s) inspected; {len(ai)} carry AI state machines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
