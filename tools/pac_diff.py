#!/usr/bin/env python3
"""Slot-by-slot diff of two DMC3 PAC archives.

Read-only tooling: loads two ``.pac`` containers and compares them by logical
slot index, reporting per-slot differences (tag, kind, offset, span, payload
bytes). Useful for comparing an original archive against a Crimson overlay
(``new<Name>_plNNN_00_<slot>.pac``) during Phase 2 mod comparison.

Nothing here reads from or writes into a game installation; both inputs are
ordinary files supplied on the command line.

Usage::

    python tools/pac_diff.py pl021.pac newTauntVergilAnims1_pl021_00_2.pac

Exit status: 0 when the archives are slot-identical, 1 when they differ, 2 on
error.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dmc3 import PacArchive  # noqa: E402


@dataclass(frozen=True)
class SlotDiff:
    """The difference observed at one logical slot index."""

    index: int
    status: str
    # "identical" | "added" | "removed" | "modified"

    tag_a: Optional[str]
    tag_b: Optional[str]
    kind_a: Optional[str]
    kind_b: Optional[str]
    offset_a: Optional[int]
    offset_b: Optional[int]
    span_a: Optional[int]
    span_b: Optional[int]
    data_equal: Optional[bool]


def _tag(chunk) -> Optional[str]:
    return chunk.tag_text or None


def diff_pac(a: PacArchive, b: PacArchive) -> List[SlotDiff]:
    """Compare two archives by logical slot index.

    Returns a list of :class:`SlotDiff`, one per slot that differs, plus one
    entry per differing slot count when the entry tables differ in length.
    Identical slots are omitted from the result.
    """
    count_a = len(a)
    count_b = len(b)
    total = max(count_a, count_b)
    diffs: List[SlotDiff] = []

    for index in range(total):
        chunk_a = a.chunk(index) if index < count_a else None
        chunk_b = b.chunk(index) if index < count_b else None

        if chunk_a is None and chunk_b is None:
            continue  # both empty

        if chunk_a is None:
            diffs.append(
                SlotDiff(
                    index=index,
                    status="added",
                    tag_a=None,
                    tag_b=_tag(chunk_b),
                    kind_a=None,
                    kind_b=chunk_b.kind,
                    offset_a=None,
                    offset_b=chunk_b.offset,
                    span_a=None,
                    span_b=chunk_b.span,
                    data_equal=None,
                )
            )
            continue

        if chunk_b is None:
            diffs.append(
                SlotDiff(
                    index=index,
                    status="removed",
                    tag_a=_tag(chunk_a),
                    tag_b=None,
                    kind_a=chunk_a.kind,
                    kind_b=None,
                    offset_a=chunk_a.offset,
                    offset_b=None,
                    span_a=chunk_a.span,
                    span_b=None,
                    data_equal=None,
                )
            )
            continue

        # Both occupied.
        tag_a, tag_b = _tag(chunk_a), _tag(chunk_b)
        data_equal = chunk_a.data == chunk_b.data
        modified = (
            tag_a != tag_b
            or chunk_a.kind != chunk_b.kind
            or chunk_a.offset != chunk_b.offset
            or chunk_a.span != chunk_b.span
            or not data_equal
        )
        if not modified:
            continue

        diffs.append(
            SlotDiff(
                index=index,
                status="modified",
                tag_a=tag_a,
                tag_b=tag_b,
                kind_a=chunk_a.kind,
                kind_b=chunk_b.kind,
                offset_a=chunk_a.offset,
                offset_b=chunk_b.offset,
                span_a=chunk_a.span,
                span_b=chunk_b.span,
                data_equal=data_equal,
            )
        )

    return diffs


def _fmt(value: Optional[int]) -> str:
    return "—" if value is None else f"0x{value:X}"


def report(diffs: List[SlotDiff], name_a: str, name_b: str, count_a: int, count_b: int) -> str:
    lines: List[str] = []
    lines.append(f"PAC diff: {name_a} ({count_a} slots) vs {name_b} ({count_b} slots)")
    if not diffs:
        lines.append("  no differences: archives are slot-identical")
        return "\n".join(lines)

    for d in diffs:
        if d.status == "added":
            lines.append(
                f"  slot {d.index:02d}: ADDED     kind={d.kind_b} tag={d.tag_b!r} "
                f"offset={_fmt(d.offset_b)} span={_fmt(d.span_b)}"
            )
        elif d.status == "removed":
            lines.append(
                f"  slot {d.index:02d}: REMOVED   kind={d.kind_a} tag={d.tag_a!r} "
                f"offset={_fmt(d.offset_a)} span={_fmt(d.span_a)}"
            )
        else:
            parts = [f"slot {d.index:02d}: MODIFIED"]
            if d.tag_a != d.tag_b:
                parts.append(f"tag {d.tag_a!r} -> {d.tag_b!r}")
            if d.kind_a != d.kind_b:
                parts.append(f"kind {d.kind_a} -> {d.kind_b}")
            if d.offset_a != d.offset_b:
                parts.append(f"offset {_fmt(d.offset_a)} -> {_fmt(d.offset_b)}")
            if d.span_a != d.span_b:
                parts.append(f"span {_fmt(d.span_a)} -> {_fmt(d.span_b)}")
            if not d.data_equal:
                parts.append("payload bytes differ")
            lines.append("  " + " ".join(parts))

    lines.append(f"  {len(diffs)} differing slot(s) out of {max(count_a, count_b)}")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, prog="pac_diff"
    )
    parser.add_argument("pac_a", help="First PAC archive")
    parser.add_argument("pac_b", help="Second PAC archive")
    args = parser.parse_args(argv)

    try:
        archive_a = PacArchive.from_path(args.pac_a)
        archive_b = PacArchive.from_path(args.pac_b)
    except (OSError, ValueError) as exc:  # noqa: BLE001 - CLI reports and exits
        print(f"error: {exc}", file=sys.stderr)
        return 2

    diffs = diff_pac(archive_a, archive_b)
    print(
        report(
            diffs,
            os.path.basename(args.pac_a),
            os.path.basename(args.pac_b),
            len(archive_a),
            len(archive_b),
        )
    )
    return 1 if diffs else 0


if __name__ == "__main__":
    raise SystemExit(main())
