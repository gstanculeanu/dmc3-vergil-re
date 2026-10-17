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
from .wad import (
    ALIGNMENT,
    CLASS_NAMES,
    COMMAND_NAMES,
    DIRECTORY_RECORDS_STANDARD,
    RECORD_START,
    STANDARD_RESOURCE_SET,
    DataChunk,
    WadError,
    WadHeader,
    WadInfo,
    WadRecord,
    data_chunks,
    inspect,
    inspect_bytes,
    is_wad,
    parse_directory,
    parse_header,
    resource_histogram,
    resources,
    scan_records,
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
    "ALIGNMENT",
    "CLASS_NAMES",
    "COMMAND_NAMES",
    "DIRECTORY_RECORDS_STANDARD",
    "RECORD_START",
    "STANDARD_RESOURCE_SET",
    "DataChunk",
    "WadError",
    "WadHeader",
    "WadInfo",
    "WadRecord",
    "data_chunks",
    "inspect",
    "inspect_bytes",
    "is_wad",
    "parse_directory",
    "parse_header",
    "resource_histogram",
    "resources",
    "scan_records",
]

__version__ = "0.1.0"
