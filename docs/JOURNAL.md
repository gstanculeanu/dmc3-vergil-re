# Journal

Append-only log of autonomous and human iterations. Newest last.

Format per entry:

```
## YYYY-MM-DD — <short title>
- Did: ...
- Found: ... (evidence IDs)
- Next: ...
```

---

## 2026-10-17 — Phase 0: foundation committed

- Did: stood up the repository. Decoded the DMC3 PAC container and its two chunk
  framings, the MOT motion header, and the HD-Collection TM2→DDS wrapping.
  Implemented `tools/dmc3/{pac,mot,tm2,entities}.py`, the `inventory` and
  `extract_assets` CLIs, and 36 unit tests on synthetic fixtures.
- Found:
  - **E-001** PAC container: `"PAC\0"`, `u32 entry_count`, `u32 offset[]`,
    16-byte aligned data start. Verified on six archives.
  - **E-002** tags `MOD `, `SHW ` (plain) and `MOT\0` (size-prefixed).
  - **E-004** Vergil is `pl021` (cloth config `;pl019_02.clt` inside `pl021.pac`).
  - **E-005** HD `.tm2` wraps a plain DDS blob (`i001_90.tm2` → DDS at 0x70).
  - **E-003** MOT header statistics over 840 chunks / 194 files; `header_size` is
    a constant `0x50`, `+0x0C`/`+0x14` are a duplicated integer duration,
    `+0x1C` is very likely the 24-bone count.
  - **E-007** the install is Crimson-modded and mods overlay Vergil's motions via
    `new<Name>_pl021_00_<slot>.pac` — a working template for Phase 2.
  - **E-006** weapon archives use a different `PNST` container.
- **Self-correction:** the first MOT spec asserted
  `header_size == 0x20 + 2 * bone_count`. Running it over the whole install
  disproved it (header is constant 0x50) and the code and docs were corrected.
  Recorded because it is the exact failure mode the evidence discipline exists for.
- Next: **F1** — decode the `MOD ` mesh payload (critical path). Start with the
  header fields at `+0x0C`, `+0x10` and `+0x1C` across the four `MOD ` chunks in
  `pl021.pac`, then look for the vertex stride.
