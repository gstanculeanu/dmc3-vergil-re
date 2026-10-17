# Backlog

The live backlog lives in **GitHub Issues**. This file is the human-readable index
and the record of what is *known to be open*; it is updated as issues change.

Labels used: `re`, `tooling`, `format`, `phase-1`, `phase-2`, `phase-3`, `blocked`,
`good-first-issue`.

---

## Format reverse engineering

| # | Title | Evidence | Status |
|---|---|---|---|
| F1 | Reverse the `MOD ` mesh payload (vertices, indices, normals, UVs, skin weights) | E-008, E-014 | open — **cross-check**, mesh already available (E-014) |
| F2 | Reverse the `SHW ` material payload and its texture binding | FORMATS §5 | open |
| F3 | Reverse the untagged chunks in `pl021.pac` (bone transforms, UV tables, primitive groups) | E-008 | open |
| F4 | Recover the MOT keyframe encoding after the header | E-003 | open — **critical path** |
| F5 | Determine the 23-entry `+0x22` MOT table's meaning | E-003 | open |
| F6 | Reverse the `PNST` weapon container (`plwp_*`) | E-006 | open — **deprioritised**, Yamato available via E-014 |
| F7 | Map `(group, slot)` → human-readable animation names | E-009, E-013 | started — `docs/ANIMATIONS.md` seeded from E-013 |
| F8 | Explain the TM2 pre-header fields | E-005 | open |
| F9 | Decompile Vergil's **move set** (clip + timing + hit windows + state transitions) | E-013 | open — **critical path for the enemy goal** |
| F10 | Decompile Vergil's **sounds and voice** | E-010 | open |
| F11 | Decompile Vergil's **VFX** (Yamato trails, DT aura, Judgement Cut) | E-007 | open |
| F12 | Recover Vergil's **enemy behaviour / AI** parameters | — | open |

## Tooling

| # | Title | Status |
|---|---|---|
| T1 | glTF 2.0 exporter (`MOD ` mesh + skeleton + `MOT ` animations) | blocked by F1, F2, F4 |
| T2 | Texture pipeline `.tm2` → `.dds` → `.png` with alpha handling | ready |
| T3 | PAC writer for import (currently `build_pac` is minimal) | ready |
| T4 | Extract/verify `plwp_vergilsword` once F6 lands | blocked by F6 |
| T5 | CLI to diff two PAC files slot-by-slot (mod comparison) | ready |
| T6 | CI running the unit tests on push | ready |

## Phase 2 — round-trip into DMC3

| # | Title | Status |
|---|---|---|
| R1 | Reproduce the `new<Name>_plNNN_00_<slot>.pac` overlay convention (E-007) | open |
| R2 | Re-encode a `MOD ` chunk and load it in-game | blocked by F1 |
| R3 | Re-encode a `MOT ` chunk and load it in-game | blocked by F4 |

## Phase 3 — Vergil as an enemy in God of War III Remastered

| # | Title | Status |
|---|---|---|
| G1 | Locate GoW3R character asset containers in `CUSA01715` | open |
| G2 | Reverse GoW3R's model/material container | blocked by G1 |
| G3 | Decide retarget vs standalone mesh for the replaced enemy's rig | open |
| G4 | Build the GoW3R exporter | blocked by G2, G3 |
| G5 | Package as a `gow3_pc` mod and verify in the port | blocked by G4 |
| G6 | Choose the sword-wielding GoW3R enemy Vergil replaces (mods cannot author AI) | open |

## Research / hygiene

| # | Title | Status |
|---|---|---|
| H1 | Confirm `pl021` = Vergil against a second build (no `pl019.pac` locally) | open |
| H2 | Confirm DDMK/Crimson creates the loose `GData.afs` folder (E-011) | partially answered |
| H3 | Track the retail packed `GData.afs` format (this install is unpacked) | open |
| H4 | Assess the Bloodborne Vergil mod for what is reusable vs merely learnable (E-012) | open |

---

## How the loop uses this file

The 10-minute agent loop (see `LOOP.md`) reads the GitHub issue list, picks the
highest-priority unblocked item, does a bounded slice of work, commits, and updates
the issue. `F1` is on the critical path and blocks most of Phase 1.
