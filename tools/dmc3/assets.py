"""The DMC3 engine's asset-name table, decoded from ``dmc3.exe`` (E-078).

``dmc3.exe`` resolves a data-driven asset reference to a file name by indexing a
``.data`` table of absolute ``char*`` pointers into the ``.rdata`` name pool of
E-076. The reference is an integer pair and the accessor is a four-way dispatcher
at ``.text`` RVA ``0x33480`` (E-078, raw bytes read-only):

* ``ecx == 0`` -> table base ``0x553050``
* ``ecx == 1`` -> table base ``0x55A920``
* ``ecx == 2`` -> table base ``0x55ADF0``
* ``ecx == 3`` -> table base ``0x55AE90``
* anything else -> ``return 0``

Every case computes ``[module_base + ASSET_POINTER_SIZE * edx + base]``, so the
resolved name is ``tables[ecx][edx]`` and the two registers are a **category**
and an **index**. The four bases are sub-ranges of two contiguous pointer runs
(the first three categories are one run with no NUL between them; category 3 is a
19-entry run after a NUL). ``pl021.pac`` -- Vergil -- sits at category 0, index 8.

The caller that supplies the pair is ``.text`` ``0x2EF790``; it reads 0x88-byte
records from an array and, for a record of type 1, passes ``record + 4`` (u16) as
the category and ``record + 6`` (u16) as the index. The record layout is
[INFERRED] from that one caller and is exposed as :class:`AssetEntry` for that
reason.

Read-only tooling. Nothing here writes to a game installation, and no game bytes
are stored in the repository.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

# The accessor (`.text` RVA 0x33480) and the four table bases it dispatches to.
ASSET_DISPATCH_RVA = 0x33480
CATEGORY_BASES: Tuple[int, ...] = (0x553050, 0x55A920, 0x55ADF0, 0x55AE90)
# The end of each category is the next category's base, except category 2, which
# is terminated by a NULL pointer at 0x55AE88; category 3 ends at 0x55AF28.
CATEGORY_ENDS: Tuple[int, ...] = (0x55A920, 0x55ADF0, 0x55AE88, 0x55AF28)
ASSET_POINTER_SIZE = 8

# Observed shape of each category (the names are data; the descriptions are
# [INFERRED] from them).
CATEGORY_DESCRIPTIONS: Tuple[str, ...] = (
    "asset archives and movies (pl*.pac, id*.pac, endof.afs, *.sfd)",
    "audio banks (Battle_*.adx, Boss_*.adx, Versil_0*.adx, ...)",
    "movies (Title.sfd, GameOver*.sfd, Omake*.sfd, ...)",
    "level movies and directory paths (m*.sfd, GData.afs/, Video/, ...)",
)

# The 0x88-byte record the dispatcher's caller (`.text` 0x2EF790) indexes.
ASSET_ENTRY_SIZE = 0x88
ENTRY_TYPE_OFFSET = 0x00
ENTRY_WORD4_OFFSET = 0x04
ENTRY_WORD6_OFFSET = 0x06
ENTRY_INLINE_NAME_OFFSET = 0x10
ENTRY_TYPE_NAME_REF = 1
ENTRY_TYPE_INLINE_NAME = 2
ENTRY_TYPE_CALLBACK = 3


@dataclass(frozen=True)
class AssetCategory:
    """One category of the engine's asset-name table.

    ``count`` is derived from the neighbouring base offsets, so it is an
    *observation* of the table's extent, not a stored length field.
    """

    index: int
    base_rva: int
    count: int
    description: str = ""

    def address_of(self, index: int) -> int:
        """RVA of the pointer for ``index`` within this category."""
        if not 0 <= index < self.count:
            raise IndexError(
                f"index {index} outside category {self.index} (0..{self.count - 1})"
            )
        return self.base_rva + index * ASSET_POINTER_SIZE


def asset_categories(
    bases: Sequence[int] = CATEGORY_BASES,
    ends: Sequence[int] = CATEGORY_ENDS,
) -> Tuple[AssetCategory, ...]:
    """The engine's asset-name categories (or a caller-supplied layout).

    The optional ``bases``/``ends`` arguments exist so the split can be tested on
    a small synthetic image; the defaults are the addresses observed in
    ``dmc3.exe``.
    """
    if len(bases) != len(ends):
        raise ValueError("bases and ends must be the same length")
    categories = []
    for index, (base, end) in enumerate(zip(bases, ends)):
        if end < base:
            raise ValueError(f"category {index} end precedes its base")
        description = (
            CATEGORY_DESCRIPTIONS[index]
            if index < len(CATEGORY_DESCRIPTIONS)
            else ""
        )
        categories.append(
            AssetCategory(
                index=index,
                base_rva=base,
                count=(end - base) // ASSET_POINTER_SIZE,
                description=description,
            )
        )
    return tuple(categories)


def resolve_name(
    image,
    category: int,
    index: int,
    categories: Optional[Sequence[AssetCategory]] = None,
) -> Optional[str]:
    """The asset name a ``(category, index)`` reference resolves to, or ``None``.

    ``image`` is a :class:`dmc3.pe.PeImage`. Raises ``IndexError`` for a category
    or index outside the table, and returns ``None`` only when the slot holds no
    readable name.
    """
    table = asset_categories() if categories is None else tuple(categories)
    if not 0 <= category < len(table):
        raise IndexError(f"no such asset category: {category}")
    entry = table[category]
    target = image.pointer_at(entry.address_of(index))
    if target is None:
        return None
    raw = image.read_cstring(target)
    return raw.decode("latin-1") if raw else None


@dataclass(frozen=True)
class AssetEntry:
    """One 0x88-byte entry of the engine's data-driven asset list.

    **[INFERRED]** from the single caller ``.text`` ``0x2EF790``: it reads the
    dword at ``+0x00`` as a type and branches on it. Only type 1's meaning
    (``(word_04, word_06)`` = the dispatcher's ``(category, index)``) is
    exercised by that caller; the other offsets are recorded as observations, not
    as field semantics.
    """

    offset: int
    entry_type: int
    word_04: int
    word_06: int

    @property
    def is_name_ref(self) -> bool:
        return self.entry_type == ENTRY_TYPE_NAME_REF

    @property
    def name_ref(self) -> Optional[Tuple[int, int]]:
        """``(category, index)`` for a type-1 entry, else ``None``."""
        if not self.is_name_ref:
            return None
        return (self.word_04, self.word_06)


def parse_asset_entry(data: bytes, offset: int = 0) -> AssetEntry:
    """Read the 0x88-byte entry head at ``offset`` (type and the two u16s)."""
    if offset < 0:
        raise ValueError("offset must be non-negative")
    if offset + ENTRY_WORD6_OFFSET + 2 > len(data):
        raise ValueError("entry head does not fit in the buffer")
    entry_type = struct.unpack_from("<I", data, offset + ENTRY_TYPE_OFFSET)[0]
    word_04 = struct.unpack_from("<H", data, offset + ENTRY_WORD4_OFFSET)[0]
    word_06 = struct.unpack_from("<H", data, offset + ENTRY_WORD6_OFFSET)[0]
    return AssetEntry(offset=offset, entry_type=entry_type, word_04=word_04,
                      word_06=word_06)
