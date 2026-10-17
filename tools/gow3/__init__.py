"""God of War III Remastered (PS4) tooling.

Read-only helpers for the local dump and the ``gow3_pc`` port's data folders.
No game asset is written into this repository.
"""

from .savedata import (
    FIELD_OFFSETS,
    FIELD_SIZE,
    PARAM_SIZE,
    SaveDataError,
    SaveParam,
    SaveSlot,
    list_slots,
    parse_param,
    read_slot,
)

__all__ = [
    "FIELD_OFFSETS",
    "FIELD_SIZE",
    "PARAM_SIZE",
    "SaveDataError",
    "SaveParam",
    "SaveSlot",
    "list_slots",
    "parse_param",
    "read_slot",
]

__version__ = "0.1.0"
