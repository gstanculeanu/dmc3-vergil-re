"""Reader for the GoW3R port's save metadata (``param.bin``).

Why this matters for the project
--------------------------------
Fast iteration needs a **known starting point** in the game: load a save, be at
the boss, test, quit.  Each save folder next to ``God of War III.exe`` carries a
sibling ``<slot>.sce_sys/param.bin`` that names the location and the play time,
so a save list can be labelled automatically instead of guessed at.

Layout (evidence E-018).  ``param.bin`` is 1,328 bytes with three fixed
0x80-byte NUL-padded UTF-8 fields::

    0x000  char[0x80]  title      "God of War\\u00ae III Remastered"
    0x080  char[0x80]  location   "The Depths of Hades"
    0x100  char[0x80]  details    "Difficulty: God (Normal)\\nPlay time: 0:52:29"
    0x180  ...         0x3B0 bytes, zero in every sample seen

This is **not** the standard PS3/PS4 SFO format (whose magic is ``\\0PSF``); it is
the game's own layout.  Only the three fields above are relied upon.

Folder layout::

    user/savedata/1/CUSA01715/
        AUTOSAVE/SAVEDATA              <- slot payload
        AUTOSAVE.sce_sys/param.bin     <- slot metadata
        AUTOSAVE.sce_sys/icon0.png     <- thumbnail
        SD-yymmddhhmmss/...            <- manual slots
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

FIELD_SIZE = 0x80
PARAM_SIZE = 0x530
FIELD_OFFSETS: Dict[str, int] = {"title": 0x000, "location": 0x080, "details": 0x100}

_DIFFICULTY_RE = re.compile(r"Difficulty:\s*(.+)", re.IGNORECASE)
_PLAYTIME_RE = re.compile(r"Play time:\s*([0-9:]+)", re.IGNORECASE)
_SLOT_NAME_RE = re.compile(r"^SD-(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})$")


class SaveDataError(ValueError):
    """Raised when a ``param.bin`` does not match the observed layout."""


def _read_field(data: bytes, offset: int, size: int = FIELD_SIZE) -> str:
    raw = data[offset:offset + size]
    text = raw.split(b"\x00", 1)[0]
    return text.decode("utf-8", "replace").strip()


@dataclass(frozen=True)
class SaveParam:
    """Contents of one ``param.bin``."""

    title: str = ""
    location: str = ""
    details: str = ""

    @property
    def difficulty(self) -> str:
        match = _DIFFICULTY_RE.search(self.details)
        return match.group(1).strip() if match else ""

    @property
    def play_time(self) -> str:
        match = _PLAYTIME_RE.search(self.details)
        return match.group(1).strip() if match else ""

    @property
    def play_seconds(self) -> Optional[int]:
        """Play time as seconds, or ``None`` when it cannot be parsed."""
        text = self.play_time
        if not text:
            return None
        parts = [p for p in text.split(":") if p != ""]
        try:
            numbers = [int(p) for p in parts]
        except ValueError:
            return None
        seconds = 0
        for value in numbers:
            seconds = seconds * 60 + value
        return seconds

    @property
    def detail_lines(self) -> List[str]:
        return [line.strip() for line in self.details.splitlines() if line.strip()]


def parse_param(data: bytes) -> SaveParam:
    """Parse a ``param.bin`` payload."""
    if len(data) < FIELD_OFFSETS["details"] + FIELD_SIZE:
        raise SaveDataError(
            f"param.bin too small ({len(data)} bytes); expected at least "
            f"{FIELD_OFFSETS['details'] + FIELD_SIZE}"
        )
    return SaveParam(
        title=_read_field(data, FIELD_OFFSETS["title"]),
        location=_read_field(data, FIELD_OFFSETS["location"]),
        details=_read_field(data, FIELD_OFFSETS["details"]),
    )


def parse_param_file(path: str) -> SaveParam:
    with open(path, "rb") as handle:
        return parse_param(handle.read())


@dataclass
class SaveSlot:
    """One save folder and its metadata."""

    name: str
    directory: str
    param: Optional[SaveParam] = None
    payload_bytes: int = 0
    mtime: float = 0.0
    has_thumbnail: bool = False
    error: str = ""

    @property
    def is_autosave(self) -> bool:
        return self.name.upper().startswith("AUTOSAVE")

    @property
    def is_userdata(self) -> bool:
        return self.name.upper().startswith("USERDATA")

    @property
    def kind(self) -> str:
        if self.is_autosave:
            return "auto"
        if self.is_userdata:
            return "userdata"
        return "manual"

    @property
    def location(self) -> str:
        return self.param.location if self.param else ""

    @property
    def play_time(self) -> str:
        return self.param.play_time if self.param else ""

    @property
    def play_seconds(self) -> int:
        if not self.param:
            return -1
        value = self.param.play_seconds
        return -1 if value is None else value

    @property
    def timestamp(self) -> Optional[str]:
        """The ``yymmddhhmmss`` stamp from a manual slot name, if present."""
        match = _SLOT_NAME_RE.match(self.name)
        if not match:
            return None
        year, month, day, hour, minute, second = match.groups()
        return f"20{year}-{month}-{day} {hour}:{minute}:{second}"

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": self.kind,
            "location": self.location,
            "play_time": self.play_time,
            "difficulty": self.param.difficulty if self.param else "",
            "timestamp": self.timestamp,
            "payload_bytes": self.payload_bytes,
            "thumbnail": self.has_thumbnail,
            "error": self.error,
        }

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        label = self.location or self.error or "?"
        return f"{self.name:<22} {self.play_time or '-':>9}  {label}"


def read_slot(root: str, name: str) -> SaveSlot:
    """Build a :class:`SaveSlot` for slot folder ``root/<name>``."""
    directory = os.path.join(root, name)
    slot = SaveSlot(name=name, directory=directory)

    payload = os.path.join(directory, "SAVEDATA")
    if os.path.isfile(payload):
        slot.payload_bytes = os.path.getsize(payload)

    meta_dir = os.path.join(root, name + ".sce_sys")
    param_path = os.path.join(meta_dir, "param.bin")
    icon_path = os.path.join(meta_dir, "icon0.png")
    slot.has_thumbnail = os.path.isfile(icon_path)

    if os.path.isfile(param_path):
        try:
            slot.param = parse_param_file(param_path)
            slot.mtime = os.path.getmtime(param_path)
        except (OSError, SaveDataError) as exc:
            slot.error = str(exc)
    else:
        slot.error = "no param.bin"

    return slot


def list_slots(root: str) -> List[SaveSlot]:
    """List every save slot under ``root``, oldest first."""
    if not os.path.isdir(root):
        raise SaveDataError(f"not a directory: {root}")
    names = [
        entry
        for entry in os.listdir(root)
        if os.path.isdir(os.path.join(root, entry))
        and not entry.endswith(".sce_sys")
        and os.path.isdir(os.path.join(root, entry + ".sce_sys"))
    ]
    slots = [read_slot(root, name) for name in names]

    def sort_key(slot: SaveSlot):
        if slot.is_autosave:
            return (0, slot.play_seconds, slot.name)
        if slot.is_userdata:
            return (2, slot.play_seconds, slot.name)
        return (1, slot.play_seconds, slot.name)

    return sorted(slots, key=sort_key)
