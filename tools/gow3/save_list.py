#!/usr/bin/env python3
"""List the GoW3R port's save slots with their in-game location and play time.

Used by the boss test loop: pick the save that sits just before the target boss,
then load it and test without a playthrough.

Usage::

    python tools/gow3/save_list.py --saves-dir "<port>\\user\\savedata\\1\\CUSA01715"
    set GOW3_SAVES=<...> & python tools/gow3/save_list.py --json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gow3 import SaveDataError, list_slots  # noqa: E402


def format_table(slots) -> str:
    header = f"{'SLOT':<24}{'KIND':<10}{'PLAY TIME':>10}  {'PLAYED AT':<20}LOCATION"
    lines = [header, "-" * len(header)]
    for slot in slots:
        lines.append(
            f"{slot.name:<24}{slot.kind:<10}{slot.play_time or '-':>10}  "
            f"{slot.timestamp or '-':<20}{slot.location or slot.error or '?'}"
        )
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--saves-dir",
        default=os.environ.get("GOW3_SAVES"),
        help="The port's savedata/<user>/<TITLE_ID> folder (env: GOW3_SAVES)",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a table")
    parser.add_argument("--near", help="Show only slots whose location contains this text")
    args = parser.parse_args(argv)

    if not args.saves_dir:
        parser.error("no --saves-dir given and GOW3_SAVES is not set")

    try:
        slots = list_slots(args.saves_dir)
    except SaveDataError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.near:
        needle = args.near.lower()
        slots = [s for s in slots if needle in s.location.lower()]

    if args.json:
        print(json.dumps([s.as_dict() for s in slots], indent=2))
    else:
        print(format_table(slots))
        if not slots:
            print("(no save slots found)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
