#!/usr/bin/env python3
"""Build the Vergil-as-Hades mod: a tinted boss model + the "Vergil" name.

Two same-size, in-place edits, so no container size changes and no WAD writer is
needed:

* ``R_HADES.WAD``  -- the RGB565 endpoints of every DXT colour block of one large
  texture are flattened to a single colour, making the boss render that colour;
* ``R_LANG_EN.WAD`` -- entry ``*832*`` "Hades" is renamed (E-057/E-054).

Safety: the game installation and the repository are never written, the source
files' SHA-256 values are re-checked afterwards, and every changed byte is verified
to lie inside the intended region.

Usage::

    python tools/gow3/make_boss_mod.py `
        --game "<dump>\\CUSA01715" --mods "<port>\\mods\\VergilHades" `
        [--tint 0xF800] [--texture-index 0]
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gow3 import dds, lang  # noqa: E402

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
REL_DIR = os.path.join("EXEC", "WAD", "PS4_LE")
BOSS = "R_HADES.WAD"
LANG = "R_LANG_EN.WAD"


def sha256(path: str) -> str:
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def guard(game_dir: str, dest: str) -> None:
    dest_abs = os.path.abspath(dest)
    if dest_abs.startswith(os.path.abspath(REPO_ROOT) + os.sep):
        raise SystemExit(f"refusing to write into the repository: {dest_abs}")
    if dest_abs.startswith(os.path.abspath(game_dir) + os.sep):
        raise SystemExit(f"refusing to write inside the game installation: {dest_abs}")


def build_texture(source: str, dest: str, colour: int, index: int) -> dict:
    before_hash = sha256(source)
    data = open(source, "rb").read()
    textures = dds.find_textures(data)
    if not textures:
        raise SystemExit(f"no block-compressed DDS textures found in {source}")

    # largest by pixel area -> most visible on screen
    ordered = sorted(textures, key=lambda t: -(t.width * t.height))
    chosen = ordered[min(index, len(ordered) - 1)]
    print(f"{BOSS}: {len(textures)} textures; tinting {chosen}")

    out = dds.tint_in_place(data, chosen, colour)
    if len(out) != len(data):
        raise SystemExit("length changed -- refusing to write")

    ranges = dds.changed_ranges(data, out)
    lo = ranges[0][0] if ranges else 0
    hi = ranges[-1][1] if ranges else 0
    inside = chosen.data_offset <= lo and hi <= chosen.end
    blocks = list(dds.colour_blocks(data, chosen))
    changed_bytes = sum(b - a for a, b in ranges)

    # the only bytes allowed to change are the four endpoint bytes of a colour
    # block; a block whose endpoints already held the target colour changes
    # nothing, so counting "4 per block" would be wrong.
    endpoint = set()
    for base in blocks:
        endpoint.update(range(base, base + 4))
    changed_offsets = set()
    for a, b in ranges:
        changed_offsets.update(range(a, b))
    packed = __import__("struct").pack("<H", colour)

    checks = {
        "length unchanged": len(out) == len(data),
        "every changed byte is inside the chosen texture": inside,
        "only colour-endpoint bytes changed":
            changed_offsets.issubset(endpoint),
        "every colour endpoint now holds the tint":
            all(out[base:base + 4] == packed * 2 for base in blocks),
        "texture header itself untouched":
            data[chosen.offset:chosen.data_offset] == out[chosen.offset:chosen.data_offset],
    }
    for label, good in checks.items():
        print(f"  {'PASS' if good else 'FAIL'}  {label}")
    if not all(checks.values()):
        raise SystemExit("verification failed; nothing written")
    print(f"  tinted {len(blocks):,} blocks; {changed_bytes:,} bytes changed "
          f"(of {4 * len(blocks):,} endpoint bytes), range 0x{lo:X}..0x{hi:X}")

    guard(os.path.dirname(source), dest)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as handle:
        handle.write(out)
    if sha256(source) != before_hash:
        raise SystemExit("THE SOURCE FILE CHANGED -- aborting")
    print(f"  PASS  source untouched (sha256 unchanged)")
    print(f"  wrote {dest}  ({len(out):,} bytes)")
    return {"source": source, "dest": dest, "texture": str(chosen),
            "blocks": blocks, "changed_bytes": changed_bytes}


def build_lang(source: str, dest: str, entry: int, old: str, new: str) -> dict:
    before_hash = sha256(source)
    data = open(source, "rb").read()
    blob = lang.find_blob(data, "MSGS_TXT")
    if blob is None:
        raise SystemExit("MSGS_TXT not found")
    out = lang.replace_exact_line_in_blob(data, blob, old, new)
    if out is None:
        raise SystemExit(f"could not rename {old!r} to {new!r}")
    got = next((e for e in lang.parse_entries(out) if e.entry_id == entry), None)
    if got is None or new not in got.text:
        raise SystemExit("rename verification failed")
    delta = len(out) - len(data)
    print(f"{LANG}: *{entry}* {old!r} -> {new!r}  ({len(data):,} -> {len(out):,}, "
          f"delta {delta:+d}, size field {blob.size:,} -> {blob.size + delta:,})")

    guard(os.path.dirname(source), dest)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as handle:
        handle.write(out)
    if sha256(source) != before_hash:
        raise SystemExit("THE SOURCE FILE CHANGED -- aborting")
    print(f"  PASS  source untouched (sha256 unchanged)")
    print(f"  wrote {dest}  ({len(out):,} bytes)")
    return {"source": source, "dest": dest, "entry": entry, "from": old, "to": new}


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", required=True, help="game dump folder (read-only)")
    parser.add_argument("--mods", required=True, help="mod folder to create")
    parser.add_argument("--tint", default="0xF800", help="RGB565 colour (default F800 = red)")
    parser.add_argument("--texture-index", type=int, default=0,
                        help="which texture by descending area (0 = largest)")
    parser.add_argument("--entry", type=int, default=832)
    parser.add_argument("--from", dest="old", default="Hades")
    parser.add_argument("--to", dest="new", default="Vergil")
    args = parser.parse_args(argv)

    colour = int(args.tint, 16)
    if not os.path.isdir(args.game):
        parser.error(f"not a folder: {args.game}")
    guard(args.game, args.mods)

    target = os.path.join(args.mods, "dvdroot_ps4", REL_DIR)
    print(f"mod root: {os.path.join(args.mods, 'dvdroot_ps4')}\n")

    results = []
    results.append(build_texture(os.path.join(args.game, REL_DIR, BOSS),
                                 os.path.join(target, BOSS),
                                 colour, args.texture_index))
    print()
    results.append(build_lang(os.path.join(args.game, REL_DIR, LANG),
                              os.path.join(target, LANG),
                              args.entry, args.old, args.new))
    print("\nOK: both files written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
