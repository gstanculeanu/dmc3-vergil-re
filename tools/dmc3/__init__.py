"""Parsers for DMC3 game data (PAC / MOT / TM2).

Read-only tooling.  Nothing here writes to a game installation.
"""

from .pac import (
    ALIGNMENT,
    MAGIC,
    TAG_MODEL,
    TAG_MOTION,
    TAG_SHADER,
    Chunk,
    PacArchive,
    align_up,
    build_pac,
)
from .mot import MotError, MotHeader, is_mot, parse_mot, parse_mot_from_bytes
from .tm2 import (
    DdsInfo,
    Tm2Error,
    Tm2File,
    extract_dds,
    find_dds,
    is_hd_tm2,
    load_tm2,
    parse_dds_header,
)
from .entities import DEFAULT_PLAYER_IDS, Entity, KNOWN_PLAYER_IDS, label_for, lookup

__all__ = [
    "ALIGNMENT",
    "MAGIC",
    "TAG_MODEL",
    "TAG_MOTION",
    "TAG_SHADER",
    "Chunk",
    "PacArchive",
    "align_up",
    "build_pac",
    "MotError",
    "MotHeader",
    "is_mot",
    "parse_mot",
    "parse_mot_from_bytes",
    "DdsInfo",
    "Tm2Error",
    "Tm2File",
    "extract_dds",
    "find_dds",
    "is_hd_tm2",
    "load_tm2",
    "parse_dds_header",
    "DEFAULT_PLAYER_IDS",
    "Entity",
    "KNOWN_PLAYER_IDS",
    "label_for",
    "lookup",
]

__version__ = "0.1.0"
