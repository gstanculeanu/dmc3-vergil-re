"""Synthetic fixtures for the GoW3R ``param.bin`` reader (layout from E-018)."""

import os

FIELD_SIZE = 0x80
PARAM_SIZE = 0x530


def _field(text: str) -> bytes:
    raw = text.encode("utf-8")
    if len(raw) > FIELD_SIZE:
        raise ValueError("field too long for the fixture")
    return raw + b"\x00" * (FIELD_SIZE - len(raw))


def param_bytes(
    title: str = "God of War\u00ae III Remastered",
    location: str = "The Depths of Hades",
    difficulty: str = "God (Normal)",
    play_time: str = "0:52:29",
) -> bytes:
    details = f"Difficulty: {difficulty}\nPlay time: {play_time}"
    blob = _field(title) + _field(location) + _field(details)
    return blob + b"\x00" * (PARAM_SIZE - len(blob))


def write_slot(root: str, name: str, **kwargs) -> str:
    """Create a slot folder + ``<name>.sce_sys`` metadata.  Returns the root."""
    os.makedirs(os.path.join(root, name), exist_ok=True)
    with open(os.path.join(root, name, "SAVEDATA"), "wb") as handle:
        handle.write(b"\x00" * 64)
    meta = os.path.join(root, name + ".sce_sys")
    os.makedirs(meta, exist_ok=True)
    with open(os.path.join(meta, "param.bin"), "wb") as handle:
        handle.write(param_bytes(**kwargs))
    with open(os.path.join(meta, "icon0.png"), "wb") as handle:
        handle.write(b"\x89PNG\r\n\x1a\n")
    return root
