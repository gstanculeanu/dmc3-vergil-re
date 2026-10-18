#!/usr/bin/env python3
"""Query the GoW3R localisation table inside ``R_LANG_*.WAD``.

The table is plain ASCII with ``*<id>*`` markers, so it can be listed and
searched directly. See docs/EVIDENCE.md E-052.

Usage::

    python tools/gow3/lang_list.py --wad "<dump>\\...\\R_LANG_EN.WAD" --around 832
    python tools/gow3/lang_list.py --wad "..." --find Hades
    python tools/gow3/lang_list.py --wad "..." --exact Hades
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gow3 import lang  # noqa: E402


def show(entry: lang.LangEntry, limit: int = 4) -> None:
    lines = [l for l in entry.text.splitlines() if l.strip()]
    head = " | ".join(lines[:limit])
    print(f"*{entry.entry_id}*  @0x{entry.start:08X}  len={len(entry.text):<6} {head[:110]}")


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wad", required=True, help="path to R_LANG_*.WAD")
    parser.add_argument("--find", help="entries whose text contains this (case-insensitive)")
    parser.add_argument("--exact", help="entries with a line exactly equal to this")
    parser.add_argument("--around", type=int, help="show entries with ids near this value")
    parser.add_argument("--span", type=int, default=6, help="half-width for --around")
    parser.add_argument("--limit", type=int, default=60)
    args = parser.parse_args(argv)

    if not os.path.isfile(args.wad):
        parser.error(f"not a file: {args.wad}")

    entries = lang.load(args.wad)
    print(f"{os.path.basename(args.wad)}: {len(entries)} entries, "
          f"ids {entries[0].entry_id}..{entries[-1].entry_id}")

    if args.exact:
        hits = lang.search(entries, args.exact, exact_line=True)
        print(f"\nentries with a line exactly {args.exact!r}: {len(hits)}")
        for entry in hits[:args.limit]:
            show(entry)

    if args.find:
        hits = lang.search(entries, args.find)
        print(f"\nentries containing {args.find!r}: {len(hits)}")
        for entry in hits[:args.limit]:
            show(entry)

    if args.around is not None:
        lo, hi = args.around - args.span, args.around + args.span
        near = [e for e in entries if lo <= e.entry_id <= hi]
        print(f"\nentries with ids {lo}..{hi}: {len(near)}")
        for entry in near:
            show(entry)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
