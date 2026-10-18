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
| F2 | Reverse the `SHW ` material payload and its texture binding | E-036, E-038, E-049 | open — header decoded across all four `pl021.pac` `SHW ` chunks (slots 8/14/24/26): tag, f32 0.5 at +0x04, zeros at +0x08/+0x0C/+0x18/+0x1C/+0x24/+0x28/+0x2C, u16 pair at +0x20, varying u32s at +0x10/+0x14 and at +0x30/+0x38/+0x40/+0x48 (each followed by a zero); **+0x38 index buffer (`[u16 i0,i1,i2,0] x count`, count = field_40−field_38 / 8) and +0x40 position buffer (`[f32 x,y,z,1.0] x count`, count = field_48−field_40 / 16) structurally decoded (E-038; pointer-math invariant verified 4/4 chunks); +0x30's 16-byte-block table (`[i0,i1,i2,0]` u32s) in all four chunks. Correction (E-049): slots 24/26 headers match but payloads diverge at body+0x11 (not byte-identical), and +0x48 is not a uniform table (slot 8 triple entries / slot 14 u32 stream / slot 24 `0x01`×40+`0x00`×8 / slot 26 zeros). Every field meaning and the texture binding [UNKNOWN] — engine ground truth needed.** |
| F3 | Reverse the untagged chunks in `pl021.pac` (bone transforms, UV tables, primitive groups) | E-008, E-033, E-037, E-043, E-052, E-062 | open — slot 0 header decoded (E-033); **slot 5 segment stream decoded** (E-052: file offset 0x06B6E0, span 0x4B30; 214 `0xFFFF`-delimited u16 separators → 215 segments, segment 0 verbatim `(6, 0x37D0)`, sizes open 2/1/34/60/5/13…, tail up to 378 u16s, `0x7FFF` appears inside segments as data); **slot 9 flat f32 array decoded** (E-062: file offset 0x077B50, span 0x380 = 224 little-endian f32s, no header/count/separator; head `10.4, -1.2, 10.0, 12.0, -1.2, 15.0, …`; 206 non-zero + 18 trailing zeros, 83 distinct, min −790, max 9000; what it indexes [UNKNOWN]); **slot 10 leading table decoded** (E-037: file offset 0x077ED0, span 0x1E0; 23 u16 pairs at stride 4 `+0x00..+0x5B` — pairs 0-14 `(92, 132+20i)`, pairs 15-22 `(112,432)/(92,432)/(92,132)x6`; f32 stream from `+0x5C` opening `0.3, -0.01, -0.1, 0.0, 0.7`); **slot 21 u16 segment table decoded** (E-043: file offset 0x07FF00, span 0x2E0; 14 `0xFFFF`-delimited u16 segments, sizes 2/6/1/8/10/31/111/34/1/6/8/27/84/26, segment 0 verbatim `(6, 408)`); **pair semantics, count source, f32 stream meaning, slots 6/7/11/22, and all field semantics [UNKNOWN]** — cross-check against prior-art mesh (E-014/E-015) |
| F4 | Recover the MOT keyframe encoding after the header | E-003, E-019, E-026, E-028, E-029 | **record layer decoded** (840/840 chunks, 59,269 records); first field decoded — group u16[0] = offset-binary frame time, frame = u16[0] − 0x8000 (E-026). u16[1..3]: NOT per-record constants; channels vary per keyframe, signed range [-32768, 32767], modal values ±0x3FFF (~±0.5 Q15) (~5,500 hits/channel of 87,662), channel meaning/scale/zero point [UNKNOWN] (E-028/E-029). Preamble: field_a == 3 in 7656/7659 records; each preamble group = pair of finite f32s with |v| ≤ 1e6, 97.4% with both |v| ≤ 10 — [UNKNOWN] semantics (E-029). preamble != first keyframe (0/7659 records) — base-pose hypothesis disproven. Remaining unknowns cannot be established from bytes alone; need engine ground truth. |
| F5 | Determine the 23-entry `+0x22` MOT table's meaning | E-003, E-032 | open — table **structure** decoded (E-032): 23 u16 entries at `+0x22`, `header_size == 0x22 + 2*len(table)` for all 840 chunks; entries constant within a chunk, dominant shape `56 x 22 + 0` (703/840 chunks, incl. every `pl021_*.pac` chunk); variants `504`-based (28), `58 x 22 + 0` (2), mixed 56/0 (71), `56 x 21 + 0 + 0` (18), varying last entry (17), one `0x60`-header chunk with `56 x 31`. **Not per-bone data** (23 vs 24 bones); semantics of `56`/`504`/`58` and the final entry [UNKNOWN] — engine ground truth needed |
| F6 | Reverse the `PNST` weapon container (`plwp_*`) | E-006, E-048 | open — header [VERIFIED]: `PNST` magic, count, offset table at `+0x08` confirmed on both weapon archives; **raw-block header decoded** (E-048: slots 0/3 of both archives share `u32 field_a=1, u32 field_b=17`, then a zero-run and structured tail). Chunk kinds observed (`MOD `, `SHW `, `PAC\0`, `PNST`, text, raw block). Payload semantics and the raw-block tail [UNKNOWN]; deprioritised since Yamato is available via prior art (E-014). |
| F7 | Map `(group, slot)` → human-readable animation names | E-009, E-013, E-035 | in progress — group/slot census confirmed from real bytes (E-035: all 10 pl021_00_*.pac groups, slot counts match E-009 exactly); three overlay anchors [LOCAL] (taunt → group 2 slot 0, Judgement Cut → group 3 slot 13, Yamato High Time → group 5 slots 7–8); move names and the group/slot → global-motion-number mapping remain [EXTERNAL], need engine ground truth |
| F8 | Explain the TM2 pre-header fields | E-005, E-034 | open — all 28 pre-header u32s of the single local TM2 (`i001_90.tm2`, DDS at 0x70) recorded (E-034); **every field [UNKNOWN]**; E-005's "only 0x08/0x0C non-zero" claim falsified (non-zero also at 0x10/0x14/0x20/0x38/0x44/0x48/0x4C/0x64/0x68). Needs more TM2 samples or engine ground truth; extraction itself is already working. |
| F9 | Decompile Vergil's **move set** (clip + timing + hit windows + state transitions) | E-013, E-058, E-059, E-060, E-061 | open — **critical path for the enemy goal**. GoW3R side: the replaced boss's move set is now enumerable and named (E-058: clip directory in `R_*.WAD`, e.g. Hades 77 clips / Hercules 46) and each clip's fixed header is decoded (E-059: 0x38-byte name field, size at +0x38, frame-rate floats; **E-060: the size sits at exactly 4 offsets and the frame rate at exactly 4 plus its reciprocal at +0x10C; `f32@+0x114 == float32(1/(u16@+0xF6 − 1))` on 123/123 clips, so +0xF6 is [INFERRED] the frame count (15..686) and +0xF4 [INFERRED] a loop flag set on 11/123 clips, all `*Idle*`**; **E-061: the descriptor tail at +0x124..+0x148 — five per-clip fields that are 16-byte-aligned and in-file on 123/123 ([INFERRED] offsets into a shared pool, since +0x12C values are reused between clips); three constant u32s and four 0xFFFFFFFF sentinels; the per-clip data section begins at +0x15C with the u16 marker pair 0x0015/0x000C on 123/123**); the clip's **internal** encoding (channels, keyframes, root motion) beyond +0x15C remains [UNKNOWN] — the gap for authoring/retargeting. Vergil's own clip→move-name mapping still needs engine ground truth. |
| F10 | Decompile Vergil's **sounds and voice** | E-010 | open |
| F11 | Decompile Vergil's **VFX** (Yamato trails, DT aura, Judgement Cut) | E-007 | open |
| F12 | Recover Vergil's **enemy behaviour / AI** parameters | — | open |

## Tooling

| # | Title | Status |
|---|---|---|
| T1 | glTF 2.0 exporter (`MOD ` mesh + skeleton + `MOT ` animations) | blocked by F1, F2, F4 |
| T2 | Texture pipeline `.tm2` → `.dds` → `.png` with alpha handling | **done** — `.tm2` → `.dds` verified (E-005/E-034); `.dds` → PNG implemented for uncompressed BGRA32 and DXT1/DXT3/DXT5 with alpha preserved (E-047: the real `i001_90.tm2` DXT3 payload decodes end-to-end to a valid 256×256 RGBA PNG; exact-pixel tests on synthetic blocks in tests/test_dds.py, refs #9); DX10 extended headers and other fourCCs raise a documented `DdsError` (not present locally). In-game channel semantics [UNKNOWN]. |
| T3 | PAC writer for import (currently `build_pac` is minimal) | ready — `build_pac` hardened (rejects non-bytes payloads) and byte-exact round-trip test added (refs #11) |
| T4 | Extract/verify `plwp_vergilsword` once F6 lands | blocked by F6 |
| T5 | CLI to diff two PAC files slot-by-slot (mod comparison) | done — `tools/pac_diff.py` (issue #10): slot-level diff report (tags, kinds, offsets, spans, payload bytes) with exit codes 0/1/2; 10 unit tests on synthetic fixtures; smoke-tested against real `pl021.pac`/`pl000.pac` |
| T6 | CI running the unit tests on push | done — `.github/workflows/test.yml` runs `python -m unittest discover -s tests -t tests` on push and pull_request (refs #12) |
| T7 | Prior-art mesh → OBJ/glTF conversion | **done for the weapon** (E-015); **body FLVER header, section table and GX block structure decoded** (E-039: header, magic `FLVER\0` [VERIFIED]; E-040: six 32-byte section entries at 0x80; E-041: GX groups — GX00/GX04/GX20/GX22/GX24/GX26/GX30 + sentinel, 240 bytes each, all six byte-identical); body mesh layout beyond the GX groups still open; every field meaning [UNKNOWN] |

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
| G9 | Decode the `R_*.WAD` container and the `WadGraph` manifest | E-016, E-022–E-025, E-044, E-056, E-058, E-059, E-060, E-061 | open — directory structure decoded (record stream; 16 typed resource groups in fixed order; `DC_` footer chunks 0 or 6; marker length resolved via `round_up(resource size, 16)`, E-025); **bulk header at `0xD80` decoded**; **`DC_` id `0x10` table structure decoded** (header u32s + `(flag, offset, value)` triplets + NUL string pool of script/FX object names — E-044 on `R_SWORD00.WAD`); **named-blob descriptors** now decoded on `R_LANG_EN.WAD` (E-054); **animation clip directory decoded** (E-058: named clips with offsets/spans), each clip's **fixed header** (E-059: 0x38-byte name field, size at +0x38, frame rates) and its **derived fields** (E-060: frame count +0xF6, loop flag +0xF4, sample rate +0x114 == float32(1/(frames−1)), size/rate each stored at four offsets, and its **descriptor tail** (E-061: five 16-byte-aligned in-file per-clip fields [INFERRED] offsets into a shared pool, three constant u32s, four `0xFFFFFFFF` sentinels; the per-clip data section opens at +0x15C with u16 `0x0015`/`0x000C`)); entry→resource/object binding, `flag`/`offset`/`value` semantics, the clip's internal encoding, and the `WadGraph` name→WAD binding [UNKNOWN]; **eboot ground-truth scanner available** (`tools/gow3/eboot.py`, E-056) to locate the numeric record opcodes / loader — no writer yet — **critical path** |
| G8 | Can a **new** entity be added, or must Vergil replace a boss? | open — **critical path** |
| G2 | Reverse GoW3R's model/material container | blocked by G9 |
| G3 | Decide retarget vs standalone mesh for the replaced boss's rig | open |
| G4 | Build the GoW3R exporter | blocked by G2, G3 |
| G5 | Package as a `gow3_pc` mod and verify the encounter in the port | blocked by G4 |
| G6 | Choose the sword-wielding **boss** Vergil replaces (inherits the health bar) | **ANSWERED: Hades** — save `SD-261017161301` (`Hades' Palace`, 1:43:35) sits immediately before the fight. `R_HADES.WAD` (85,727,632 B) + AI `HDS675AI1HADES.WAD` (47,136 B) |
| G7 | Confirm the boss health bar, and try to rename it to "Vergil" | **mechanism confirmed** (E-020): the name is the string `Hades` in `R_LANG_EN.WAD`; needs one in-game check at the locked save |
| G10 | Decode the `WadGraph` registry: bind names to WADs; test a `Stub_` slot | E-021, E-045, E-056 | open — **critical path for a *new* boss** (E-021, E-045: registry structure decoded — 2,617 name records, header, constant sentinel/trailer; `name_offset`→string relation [UNKNOWN]; name→WAD binding still [UNKNOWN]); the eboot reference scanner (`tools/gow3/eboot.py`, E-056) is the ground-truth route to the loader that consumes the registry |

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
