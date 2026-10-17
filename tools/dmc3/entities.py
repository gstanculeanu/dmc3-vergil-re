"""Entity map for DMC3 character and weapon archives.

DMC3 names player resources ``pl<NNN>`` and weapon resources ``plwp_<name>``.
The mapping below separates what is **verified** from what is **inferred**; see
docs/ENTITIES.md for the full evidence table.

Verified (label appears verbatim inside the archive, or the asset is the direct
counterpart of an explicitly named file):

    pl000  Dante
    pl019  Vergil (boss / Nelo Angelo lineage; ``pl019_02.clt`` cloth config)
    pl021  Vergil (playable)             <- PRIMARY TARGET
    plwp_vergilsword   Yamato
    plwp_newvergilsword, plwp_newvergilfight   Vergil weapon variants (HD/SE)
    plwp_forceedge     Force Edge

Inferred (by convention / pairing, not yet proven): pl001, pl002, ...
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Entity:
    id: str
    label: str
    confidence: str  # "verified" | "inferred"
    note: str = ""

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return f"{self.id} = {self.label} ({self.confidence})"


def _e(id_: str, label: str, confidence: str, note: str = "") -> Entity:
    return Entity(id=id_, label=label, confidence=confidence, note=note)


PLAYER_ENTITIES: Dict[str, Entity] = {
    "pl000": _e("pl000", "Dante", "verified", "cloth config ';pl000_02.clt' in pl000.pac"),
    "pl019": _e(
        "pl019",
        "Vergil (boss / Nelo Angelo)",
        "verified",
        "referenced by pl021.pac's cloth config ';pl019_02.clt'",
    ),
    "pl021": _e(
        "pl021",
        "Vergil (playable)",
        "verified",
        "primary target; motion sets pl021_00_0..9",
    ),
}

WEAPON_ENTITIES: Dict[str, Entity] = {
    "plwp_vergilsword": _e("plwp_vergilsword", "Yamato", "verified"),
    "plwp_newvergilsword": _e("plwp_newvergilsword", "Yamato (SE/HD variant)", "inferred"),
    "plwp_newvergilfight": _e("plwp_newvergilfight", "Beowulf (Vergil)", "inferred"),
    "plwp_forceedge": _e("plwp_forceedge", "Force Edge", "verified"),
}

#: Every ``plNNN`` identifier the tooling should look for by default.
DEFAULT_PLAYER_IDS: List[str] = ["pl021"]

#: Player archives to inventory when mapping a whole install.
KNOWN_PLAYER_IDS: List[str] = [
    f"pl{index:03d}" for index in (0, 1, 2, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 17, 18, 19, 21, 23, 25, 26)
]


def lookup(entity_id: str) -> Optional[Entity]:
    return PLAYER_ENTITIES.get(entity_id) or WEAPON_ENTITIES.get(entity_id)


def label_for(entity_id: str) -> str:
    entity = lookup(entity_id)
    return entity.label if entity else entity_id


def is_primary_target(entity_id: str) -> bool:
    return entity_id in DEFAULT_PLAYER_IDS
