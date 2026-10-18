#!/usr/bin/env python3
"""Build a localisation-name mod for the GoW3R port, with verification.

Renames one ``*id*`` entry inside a ``R_LANG_*.WAD`` and writes the result to a
**mod** path. Safety rules, all enforced here:

* the **game installation is never written** -- the tool reads it and refuses to
  write anywhere inside it;
* the repository is never written (game assets do not belong in it);
* the source file's SHA-256 is re-checked after the run and must be unchanged;
* the produced file is verified: exactly the expected size delta, the blob's size
  field updated by the same amount, the prefix unchanged apart from that field,
  the suffix a pure shift, and the target entry reading the new name.

Usage::

    python tools/gow3/make_lang_mod.py `
        --wad "<game>\\EXEC\\WAD\\PS4_LE\\R_LANG_EN.WAD" `
        --entry 832 --from Hades --to Vergil `
        --out "<port>\\mods\\VergilNameTest\\dvdroot_ps4\\EXEC\\WAD\\PS4_LE\\R_LANG_EN.WAD"
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gow3 import lang  # noqa: E402

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
BLOB_NAME = "MSGS_TXT"


def sha256(path: str) -> str:
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def guard(source_wad: str, dest: str) -> None:
    dest_abs = os.path.abspath(dest)
    repo = os.path.abspath(REPO_ROOT)
    if dest_abs.startswith(repo + os.sep) or dest_abs == repo:
        raise SystemExit(f"refusing to write into the repository: {dest_abs}")

    # The game installation is identified by the source file's own directory
    # tree: never write anywhere that contains the source .WAD.
    game_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(source_wad)))))
    if dest_abs.startswith(game_root + os.sep):
        raise SystemExit(
            f"refusing to write inside the game installation ({game_root}); "
            "mods must go to the port's mods/ folder"
        )


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wad", required=True, help="source R_LANG_*.WAD (read-only)")
    parser.add_argument("--entry", type=int, required=True, help="entry id, e.g. 832")
    parser.add_argument("--from", dest="old", required=True, help="current text")
    parser.add_argument("--to", dest="new", required=True, help="new text")
    parser.add_argument("--blob", default=BLOB_NAME, help=f"blob name (default {BLOB_NAME})")
    parser.add_argument("--out", required=True, help="destination .WAD inside the mod")
    args = parser.parse_args(argv)

    if not os.path.isfile(args.wad):
        parser.error(f"not a file: {args.wad}")
    guard(args.wad, args.out)

    source_hash = sha256(args.wad)
    data = open(args.wad, "rb").read()
    size_before = len(data)
    print(f"source   {args.wad}")
    print(f"         {size_before:,} bytes  sha256 {source_hash[:16]}…")

    blob = lang.find_blob(data, args.blob)
    if blob is None:
        raise SystemExit(f"blob {args.blob!r} not found in the source")
    print(f"blob     {blob.name}: descriptor @0x{blob.descriptor_offset:X}, "
          f"size {blob.size:,}, data 0x{blob.data_offset:X}..0x{blob.end:X}")

    entry = next((e for e in lang.parse_entries(data) if e.entry_id == args.entry), None)
    if entry is None:
        raise SystemExit(f"entry *{args.entry}* not found")
    if not (blob.data_offset <= entry.start < blob.end):
        raise SystemExit(f"entry *{args.entry}* is not inside {blob.name}")

    out = lang.replace_exact_line_in_blob(data, blob, args.old, args.new)
    if out is None:
        raise SystemExit(f"could not replace {args.old!r} with {args.new!r}")

    # ---- verification -----------------------------------------------------
    delta = len(args.new) - len(args.old)
    new_entry = next((e for e in lang.parse_entries(out) if e.entry_id == args.entry), None)
    if new_entry is None:
        raise SystemExit("verification failed: the entry vanished")
    ins = new_entry.text_offset + new_entry.text.index(args.new)

    prefix_out = bytearray(out[:ins])
    prefix_orig = bytearray(data[:ins])
    prefix_out[blob.size_offset:blob.size_offset + 4] = prefix_orig[blob.size_offset:blob.size_offset + 4]

    checks = {
        "size delta is exact":
            len(out) - size_before == delta,
        "blob size field updated":
            int.from_bytes(out[blob.size_offset:blob.size_offset + 4], "little") == blob.size + delta,
        "prefix unchanged apart from the size field":
            bytes(prefix_out) == bytes(prefix_orig),
        "suffix is a pure shift":
            out[ins + len(args.new):] == data[ins + len(args.old):],
        "entry reads the new text":
            args.new in new_entry.text and args.old not in new_entry.text,
    }
    for label, good in checks.items():
        print(f"  {'PASS' if good else 'FAIL'}  {label}")
    if not all(checks.values()):
        raise SystemExit("verification failed; nothing written")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "wb") as handle:
        handle.write(out)

    if sha256(args.wad) != source_hash:
        raise SystemExit("THE SOURCE FILE CHANGED -- aborting")
    print(f"  PASS  source file untouched (sha256 unchanged)")

    print(f"\nwrote    {args.out}")
    print(f"         {len(out):,} bytes  sha256 {sha256(args.out)[:16]}…")
    print(f"  *{args.entry}*: {args.old!r} -> {args.new!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
