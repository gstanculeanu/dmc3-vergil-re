# Backlog

The live backlog lives in **GitHub Issues**. This file is the human-readable index
and the record of what is *known to be open*; it is updated as issues change.

Labels used: `re`, `tooling`, `format`, `phase-1`, `phase-2`, `phase-3`, `blocked`,
`good-first-issue`.

---

## Format reverse engineering

| # | Title | Evidence | Status |
|---|---|---|---|
| F1 | Reverse the `MOD ` mesh payload (vertices, indices, normals, UVs, skin weights) | E-008, E-014, E-030, E-031 | open — header decoded (E-030); body prefix decoded (E-031: body+0x1C u16 marker 0x8001 constant, body+0x1E u16 count varies 474/300/182/182, body+0x24 u32 varies, four f32s at body+0x4C, body+0x5C u32 equals count for the duplicated slots 23/25); **payload body beyond +0x5C [UNKNOWN]** — cross-check against prior-art mesh (E-014/E-015) |
| F2 | Reverse the `SHW ` material payload and its texture binding | FORMATS §5 | open |
| F3 | Reverse the untagged chunks in `pl021.pac` (bone transforms, UV tables, primitive groups) | E-008 | open |
| F4 | Recover the MOT keyframe encoding after the header | E-003, E-019, E-026, E-028, E-029 | **record layer decoded** (840/840 chunks, 59,269 records); first field decoded — group u16[0] = offset-binary frame time, frame = u16[0] − 0x8000 (E-026). u16[1..3]: NOT per-record constants; channels vary per keyframe, signed range [-32768, 32767], modal values ±0x3FFF (~±0.5 Q15) (~5,500 hits/channel of 87,662), channel meaning/scale/zero point [UNKNOWN] (E-028/E-029). Preamble: field_a == 3 in 7656/7659 records; each preamble group = pair of finite f32s with |v| ≤ 1e6, 97.4% with both |v| ≤ 10 — [UNKNOWN] semantics (E-029). preamble != first keyframe (0/7659 records) — base-pose hypothesis disproven. Remaining unknowns cannot be established from bytes alone; need engine ground truth. |
| F5 | Determine the 23-entry `+0x22` MOT table's meaning | E-003, E-032 | open — table **structure** decoded (E-032): 23 u16 entries at `+0x22`, `header_size == 0x22 + 2*len(table)` for all 840 chunks; entries constant within a chunk, dominant shape `56 x 22 + 0` (703/840 chunks, incl. every `pl021_*.pac` chunk); variants `504`-based (28), `58 x 22 + 0` (2), mixed 56/0 (71), `56 x 21 + 0 + 0` (18), varying last entry (17), one `0x60`-header chunk with `56 x 31`. **Not per-bone data** (23 vs 24 bones); semantics of `56`/`504`/`58` and the final entry [UNKNOWN] — engine ground truth needed |
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
| T7 | Prior-art mesh → OBJ/glTF conversion | **done for the weapon** (E-015); body FLVER open |

## Phase 2 — round-trip into DMC3

| # | Title | Status |
|---|---|---|
| R1 | Reproduce the `new<Name>_plNNN_00_<slot>.pac` overlay convention (E-007) | open |
| R2 | Re-encode a `MOD ` chunk and load it in-game | blocked by F1 |
| R3 | Re-encode a `MOT ` chunk and load it in-game | blocked by F4 |

## Phase 3 — Vergil as a boss with a health bar in God of War III Remastered

| # | Title | Status |
|---|---|---|
| G1 | Locate GoW3R character asset containers in `CUSA01715` | **answered** (E-016): per-entity `R_*.WAD` in `EXEC/WAD/PS4_LE/` |
| G9 | Decode the `R_*.WAD` container and the `WadGraph` manifest | **taxonomy decoded** (E-023/E-024): every WAD = the same 16 typed resource groups (MDLX/TXRX/ANMX/BHVX/...). Marker *length* still open → no writer yet — **critical path** |
| G8 | Can a **new** entity be added, or must Vergil replace a boss? | open — **critical path** |
| G2 | Reverse GoW3R's model/material container | blocked by G9 |
| G3 | Decide retarget vs standalone mesh for the replaced boss's rig | open |
| G4 | Build the GoW3R exporter | blocked by G2, G3 |
| G5 | Package as a `gow3_pc` mod and verify the encounter in the port | blocked by G4 |
| G6 | Choose the sword-wielding **boss** Vergil replaces (inherits the health bar) | **ANSWERED: Hades** — save `SD-261017161301` (`Hades' Palace`, 1:43:35) sits immediately before the fight. `R_HADES.WAD` (85,727,632 B) + AI `HDS675AI1HADES.WAD` (47,136 B) |
| G7 | Confirm the boss health bar, and try to rename it to "Vergil" | **mechanism confirmed** (E-020): the name is the string `Hades` in `R_LANG_EN.WAD`; needs one in-game check at the locked save |
| G10 | Decode the `WadGraph` registry: bind names to WADs; test a `Stub_` slot | open — **critical path for a *new* boss** (E-021) |

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
