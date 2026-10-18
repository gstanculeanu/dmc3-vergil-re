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

---

## 2026-10-17 — Scope clarified: Vergil is an **enemy**, not just a model

The owner clarified the destination: Vergil must appear in God of War III
Remastered **as an enemy**, so his **move set, weapon, sounds and effects** are
part of the deliverable, not optional extras.

- Did: expanded the roadmap (Phase 1 milestones 1.8–1.10 for moves/audio/VFX;
  Phase 3 reframed as an enemy port), added `docs/ANIMATIONS.md`, filed issues
  **F9** (move set), **F10** (audio), **F11** (VFX), **F12** (enemy AI) and
  **G6** (choose the enemy Vergil replaces), and recorded the mod-system
  constraint that shapes all of Phase 3.
- Found:
  - **E-010** Vergil's audio is present as `Versil_01..03.ogg` in
    `data/dmc3/afs/sound/`; ownership of the `snd_*.pac` banks is still unknown.
  - **E-011** the loose `GData.afs` **folder** is created by the mod loader
    (DDMK/Crimson), not by the retail game. Our tooling reads a loader-generated
    tree; H3 tracks the retail packed `.afs`.
  - **E-012** prior art: Vergil has already been decompiled and ported into
    **Bloodborne**, another PS4 game, via the same `dvdroot` replacement
    convention GoW3R uses. Per the owner, the model is done there and "the moves
    and things are left" — which matches our F9/F10/F11 backlog.
  - **E-013** the community has already named most of Vergil's motion slots
    (Infernal Works motion-ID thread). Transcribed into `docs/ANIMATIONS.md`;
    needs local verification (F7).
  - The DMC3 HD model-port community warns that too many / too high-vertex model
    swaps destabilise the game — relevant to Phase 2's import budget.
- **Key constraint recorded:** `gow3_pc` mods may replace data files under
  `dvdroot_ps4/` but may not replace `eboot.bin`, nor use DLL injectors or script
  plugins. A mod therefore **cannot author new AI**: Vergil must replace an
  existing sword-wielding GoW3R enemy and inherit its behaviour (G6). This is on
  the critical path because it decides what "Vergil as an enemy" can mean.
- Next: **F1** (mesh) and **F4** (MOT keyframes) remain the technical critical
  path. In parallel, **H4** (assess the Bloodborne mod) and **G6** (pick the
  replaced enemy) are cheap and de-risk the plan.

---

## 2026-10-17 — Prior art located on disk: Vergil's mesh is already decompiled

The owner pointed at `C:\Users\GigelCastel\Desktop\vergil`, the downloaded Nexus
(Bloodborne) Vergil mod, and asked for it to be taken into account.

- Did: inspected the package directly and wrote `docs/PRIOR-ART.md`. Recorded
  evidence **E-014**. Updated the README (mesh status + prior-art callout),
  the roadmap (new milestone 1.0; 1.1/1.7/1.3 demoted to cross-checks) and the
  backlog (F1/F6 restated).
- Found (E-014):
  - It is a **FromSoftware PS4** mod package. Magics observed: `FLVER`, `TPF\0`
    (platform header `PS4`), `BND4`, `DCX\0`, HKX `57 E0 E0 57`, `CLM2`, `DDS `,
    and Source **`version 1` SMD**.
  - **Vergil's mesh exists in interchange format.** `WP_A_10100.smd` (628 KB) and
    `WP_A_10100.ascii` (181 KB), plus `_1`/`_2` variants — Blender-readable.
  - Weapon identity is **Yamato**: `WP_A_1063`, 8 nodes with `B_Root` →
    `B_Blade_00/01/02`, 1852 verts, material `m0_WP_A_1063`, textures
    `WP_A_1063_a/_r/_s/_n`.
  - Body is a Bloodborne **FullBody** part `BD_M_10100`, whose TPF shrank
    19,929,900 → 2,190,896 vs its `.bak` — Vergil's textures replaced the original.
  - Manifests (Witchy) expose the original PS4 build tree:
    `N:\SPRJ\data\INTERROOT_ps4\parts\FullBody\BD_M_10100`.
  - Nothing in the text files says "Vergil"/"Yamato" — the armour-name FMG just
    sets entries to `NOT NEEDED`.
- **Strategic consequence:** decoding the DMC3 `MOD ` mesh (F1) and `PNST`
  weapon container (F6) is no longer on the critical path; they become
  cross-checks. The critical path is **animations and moves** (F4, F9) — the
  package's `.anibnd`/`.hkx` are Bloodborne's, not Vergil's. This matches the
  owner's "the moves and things are left".
- **Licensing:** third-party assets, kept outside the repo, never committed.
  Reuse is gated on the mod page's permissions (H4).
- Next: **T7** — convert the prior-art mesh to glTF/OBJ and verify it renders.
  Then **F4** — MOT keyframes, now the top technical risk.

---

## 2026-10-17 — Boss requirement, and the Yamato is exported and verified

Owner: *"continue until done. vergil should be a boss and have a health bar in
gow3."*

- Did: reframed Phases 1 and 3 around **Vergil as a boss with a health bar**;
  implemented `tools/priorart/` (Source `.ascii` + `.smd` parsers, OBJ writer,
  converter CLI) and ran it against the real prior-art package. 52 tests green.
- Found:
  - **E-015** — both interchange formats are fully decoded. ASCII:
    8 bones / 1 mesh / **1176 verts** / **1852 faces**; the line budget
    (`1 + 24 + 6 + 14 + 1 + 1176*7 + 1 + 1852`) matches the file exactly.
    SMD: 8 nodes / 8 bones / 1 material / **5556 verts** / **1852 tris**.
  - Both OBJ exports give an **identical bounding box**:
    `extent (x,y,z) = 0.163 × 1.260 × 0.053 m`, longest axis 1.260 — a thin,
    1.26 m blade. **Vergil's Yamato is exported and verified.**
  - Two independent formats agreeing on triangle count *and* bounding box is
    mutual verification of both parsers; this also independently confirms
    `WP_A_1063` = Yamato.
- **Design decision recorded:** a `gow3_pc` mod cannot add UI, so a boss health
  bar cannot be created — it must be **inherited by replacing an existing boss**.
  This turns the mod constraint into the mechanism that satisfies the
  requirement. Phases 1/3, `README`, `ROADMAP`, `GOW3.md` and the backlog were
  all updated; new issue **G7** filed.
- Still open: the **body** (`BD_M_10100`) is FLVER-only, so it needs a FLVER
  parser or an external tool; and **F4** (MOT keyframes) remains the top
  technical risk.
- Next: **T7b** — parse FLVER (or drive an external tool) for Vergil's body, and
  **F4** — MOT keyframes.

---

## 2026-10-17 — G1 answered: found every GoW3R asset container

- Did: checked whether the GoW3 dump even contains the art assets, then mapped
  them. Recorded E-016 (WAD layout) and E-017 (FLVER header, partial). Updated
  `GOW3.md` with the real asset map and a new "new boss vs replacement" section.
  Filed **G8** (#35) and **G9** (#36); commented the answer onto **G1** (#17).
- Found:
  - **The dump is complete: 50.5 GB**, of which `EXEC/` is 45.9 GB. The art is
    **not** in `eboot.bin`.
  - **All assets are per-entity WADs**: 417 files, 21.5 GB, in
    `EXEC/WAD/PS4_LE/`. Each begins `u32 0x14 / u32 8 / "WAD_<Name>"`.
  - Bosses are named files: `R_HERCULES`, `R_ZEUS00..60`, `R_HADES`, `R_HELIOS`,
    `R_HERMES`, `R_POSEIDON00`. Weapons: `R_SWORD00` (87 KB), `R_SHIELD00`,
    `R_SPEAR00`, `R_AXE00`. UI: `R_UI.WAD`. Text: `R_LANG_*.WAD` (16 languages).
    Effects: `R_FX.WAD`, `R_W_*`. Manifest: `DEPENDENCYGRAPH.IFF` (`"WadGraph"`).
  - **Per-enemy `*AI*.WAD` files exist** (e.g. `HDS675AI1HADES`,
    `BAS400AI4HELI`) — evidence that enemy behaviour is *data-driven*, which is
    the single most encouraging result for the boss goal.
  - `BD_M_10100.flver` header: floats at 0x28–0x3F give a box with a **1.79 m
    vertical extent** — the height of a humanoid, so the body file is the right
    one. Full FLVER decoding remains open (T7b).
- **Answer to the owner's question ("new boss instead of replacement?"):**
  *plausible, more than expected, but strictly harder and gated on three unknowns.*
  Mods may **add** files (the loader logs "N replaced, M added"), and entities are
  individually addressable, so a new `R_VERGIL.WAD` could in principle be dropped
  in. But it additionally needs the runtime to load it (`WadGraph`), something to
  spawn it (level/encounter data), and the game to treat it as a boss (health bar,
  intro, phases) — none of which is understood yet. Replacement needs none of
  that. **Recommendation: replacement first, investigate new-boss in parallel via
  G8.** The Vergil assets are identical for both routes, so nothing is wasted.
- Next: **G9** — decode the `R_*.WAD` container starting from the small ones
  (`R_SWORD00.WAD` 87,840 B; `HDS675AI1HADES.WAD` 47,136 B), then `WadGraph`.

---

## 2026-10-17 — Fast boss test loop (no playthrough)

Owner: *"replacement first, but I want it testable each time I enter the game —
don't want to play through the game."*

- Did: built the harness. `tools/gow3/savedata.py` + `save_list.py` read save
  labels; `scripts/boss-test.ps1` stages a pre-boss save, installs a mod and
  launches; `docs/TESTING.md` documents the loop. 17 new tests (69 total).
- Found:
  - **E-018** — `param.bin` (1,328 bytes) has three fixed 0x80-byte UTF-8 fields:
    `0x000` title, `0x080` **location**, `0x100` **`Difficulty:` + `Play time:`**.
    It is *not* the standard SFO format.
  - The seven local saves now label themselves, so the boss test point can be
    chosen by location instead of guessed: `Tomb of Ares` (0:14), `Entrance to
    Ares Tomb` (0:31), `Realm of Hades` (0:38), `The Depths of Hades` (0:52),
    `The Three Judges` (1:00), `The Forge` (1:19), `AUTOSAVE` Hephaestus.
  - Save thumbnails (`icon0.png`) are too dark/generic to identify arenas, so the
    text field is the reliable route.
- **Design choice:** the harness **stashes** the other slots rather than renaming
  the target, because whether the load list sorts by folder name or payload is
  unverified. Stashing is correct either way. Saves are backed up first and
  `-Restore` reverses it.
- **Next, and it needs the owner:** which of the observed saves is *immediately*
  before a boss? That decides the replacement target (G6) and makes the loop
  one click. Then run the **retexture smoke test** (tint the boss green) to prove
  mod install + WAD replacement + the boss health bar before feeding Vergil's mesh
  through.

---

## 2026-10-17 — Owner: no save is pre-boss → staged test plan

- Owner answers: **none** of the seven saves is immediately before a boss; the
  target boss is "whichever is reachable from my save".
- Did: rewrote the smoke test into a **staged plan** in `docs/TESTING.md` so that
  work can proceed *now* without a boss, and recorded the reasoning on #37 (T9)
  and #28 (G6).
  1. **Stage 1** — tint a texture in `R_UI.WAD` (HUD art). Visible within two
     seconds of loading **any** save, standing still. Proves mod install + WAD
     replacement + "the game still runs".
  2. **Stage 2** — swap a common enemy (`R_GRUNT00`, `R_SOLDIER00`, …). Proves
     *character* replacement without a boss.
  3. **Stage 3** — the one-time cost: save immediately before a boss once, then
     every iteration is one click. Confirms the boss health bar (G7).
  4. **Stage 4** — Vergil's mesh.
- Reasoned about the boss target from existing evidence: the owner's saves sit in
  the Hades section (`HDS###`), and `HDS675AI1HADES.WAD` places the Hades
  encounter at level `HDS675`, so **Hades is the natural target** if the next
  pre-boss save lands there. Noted that **Zeus** (`R_ZEUS00..60`, six variants) is
  the only GoW3 boss with a real sword, and Hercules the next best humanoid fit.
- Stages 1–2 are blocked only on **G9** (unpack/repack a `R_*.WAD`); the harness
  itself is ready.

---

## 2026-10-17 — F4 record layer decoded; health-bar name found; WadGraph registry

Owner: focus on **F4/F9** (Vergil's move set from the MOT bitstream) and the
**boss/health-bar confirmation**.

- Did: decoded the MOT payload structure and shipped it; found the boss-name
  strings and the asset registry. 12 new tests (81 total).
- **F4 — the record layer is solved (E-019).** After the header:
  `u32 record_count`, then `record_count` records of
  `(u16 size, u16 groups, u16 a, u16 b)` + `size-8` bytes, then 0–12 bytes of
  padding. Validated on **all 840 motion chunks: 0 walk failures, 59,269 records,
  the stored count reached in every case.** `size == 8*(groups+4)` holds for every
  record in 796/840 chunks. New API: `walk_records()` / `try_walk_records()`.
  - **Disproved** `record_count == 3 × bones` (69 = 3 × 23 was a coincidence):
    the ratio is 3.0 in only 193/840 chunks.
  - Also learned the `+0x22` table is **23 entries in all 840 chunks**.
  - Still open: what the 8-byte groups encode (their `u16`s cluster near `0x8000`
    / `0x3FFF` / `0xBFFF`, i.e. ±1.0 in Q15 — plausible quantised rotation,
    unproven).
- **Health bar (G7) — the mechanism is confirmed (E-020).** `R_LANG_EN.WAD` is
  **plain ASCII** (14,801 runs, zero UTF-16) and contains boss names as exact
  standalone strings: `Hades`, `Helios`, `Hermes`, `Hercules`, `Zeus`, `Cronos`,
  `Poseidon`, `Athena`, `Gaia`, `Pandora`, `Kratos`. The file is a normal mod
  target, so the bar's name should be editable to "Vergil". `R_LANG_DE.WAD` has
  the same shape in German.
- **`WadGraph` decoded (E-021).** `DEPENDENCYGRAPH.IFF` is a NUL-separated name
  registry: 3,693 names — entities (`R_Hercules`), actors/AI (`ARGrunt00`,
  `ARGrunt00X22`), levels (`Hds675`), **2,109 `.xvag` audio names**, and
  **3,344 `Stub_NNNN` placeholder slots**. Names match disk WADs
  **case-insensitively**.
  - The thousands of stubs are the best evidence yet that a **new** entity could
    be added (G8) instead of replacing one.
  - Audio being registered by name means Vergil's voice needs a registry entry too.
  - Filed **G10** to decode the name→WAD binding and test a stub.
- Next: **G10** (registry binding) and the 8-byte MOT group encoding; the loop
  should also decode the `R_*.WAD` container (G9) to unblock the staged tests.

---

## 2026-10-17 — G9 advanced: the WAD is a named-object archive, and AI is a separate data file

- Did: characterised the `R_*.WAD` container by dumping and comparing four WADs
  ranging from 47 KB to 63 MB, then checked the entity/AI split. Recorded **E-022**
  and corrected a too-pessimistic claim in `docs/GOW3.md`.
- Found:
  - Header: `u32 20`, `u32 8`, then a zero-padded banner (`"WAD_R_Hercules"`).
  - Records of the shape `u32, u32, char name[<=0x38]`, e.g.
    `(2, 0, "GroupStart")`, `(1, 0x18, "WAD_R_Sword00")`.
  - **A `DC_<banner>` marker, exactly 6 times per WAD**, preceded by a fixed
    16-byte prefix `00*8, u16 0x0B, u16 0x09, u32 4`.
  - Name families: `go*` game objects/FX, `tGOPool_N`, `tMemoryPool_N`,
    `t*System` (`tAnimSystem`, `tFightSystem`, `tHandleSystem`,
    `tStandardEffectSystem`), `ms::*` (`ms::tMove`, `ms::tCollisionInfo`),
    `attachment::*`, and **`hfsm*`**.
  - **The decisive one:** `hfsm*` AI state machines (`hfsmEnemy1`,
    `hfsmBreakable`, `hfsmIO_Misc`) appear in **`HDS675AI1HADES.WAD`** — an AI WAD —
    and in **none** of the entity WADs (`R_HERCULES`, `R_HERCULES10`, `R_SWORD00`).
- **Consequence — this changes the plan for the better.** AI is a **data file**,
  not compiled logic. Entity WADs hold model/textures/animation; AI WADs hold the
  behaviour state machines. So Vergil's model can come from one WAD while the
  behaviour comes from the replaced boss's AI WAD, or from an authored one. The
  earlier "a mod cannot author new AI" claim in `docs/GOW3.md` was corrected.
  What genuinely cannot be added by a mod is **new UI** — which is exactly why
  inheriting an existing boss's health bar remains the right first target.
- Also noted: the container is a **serialized object graph**, not a zip of named
  files, so G9 is bigger than first assumed — but the naming is legible and the
  entity/AI seam is the one a boss port needs.
- Next: **G10/G9** — the record directory that binds a name to its bytes; then
  Stage 1 of the test plan (tint `R_UI.WAD`) needs a WAD reader/writer.

---

## 2026-10-17 — WAD reconnaissance tool + census (two of my own claims falsified)

- Did: shipped `tools/gow3/wad.py` and `wad_info.py` implementing only the
  *verified* parts of the container, then censused the 90 smallest WADs. 13 new
  tests (94 total).
- Found — and corrected two of the claims I filed an hour earlier:
  - **`DC_` is not always 6 times.** Measured `{0 markers: 17, 6 markers: 73}`.
  - **The 16-byte prefix is not constant.** It matched the four files I had
    hand-dumped but fails on the other 73. The tool now reports `prefix_matches`
    instead of asserting it, so the assumption stays falsifiable.
  - **Banner is not unique per file**: 76 distinct banners across 90 files;
    `WAD_R_Lang` is shared by 13, `WAD_R_I_Ice` by 3.
  - **Entity/AI split confirmed and common**: 54 of 90 small WADs carry AI
    (`hfsm*`), 28 are entity WADs, 8 other.
  - **The `hfsm*` vocabulary is small and legible**: `hfsmEnemy1`,
    `hfsmReactive`, `hfsmBreakable`, `hfsmHeroBreak`, `hfsmSavePoint`,
    `hfsmIO_Misc`, combined in 7 distinct sets. Enemy behaviour is assembled from
    named modules.
- Note on method: the census had to be limited to WADs under 2 MB — scanning all
  408 (21.5 GB) exceeds a reasonable command timeout. Worth a streaming pass
  later.
- Next: the record directory (G9/G10). This is the last unknown before a WAD
  reader/writer, which Stage 1 of the test plan needs.

---

## 2026-10-17 — Test point locked: Hades

Owner: *"save at 20:13 is just before the hades fight"*.

- Did: resolved the slot, locked the Phase 3 target, and wired a default into the
  harness. Recorded the timestamp subtlety in E-018; updated `TESTING.md`,
  `GOW3.md`, `BACKLOG.md`.
- Found: **slot folder names are UTC while file times are local** (4-hour offset
  here). `SD-261017161301` encodes 16:13 UTC and its files were written at
  **20:13:02 local** — an exact match for the owner's description. So the slot is
  `SD-261017161301`, location **`Hades' Palace`**, play time **1:43:35**.
- **Target boss locked: Hades.**
  - `R_HADES.WAD` — 85,727,632 B, banner `WAD_R_Hades`, 6 `DC_` markers, **no** AI
    state machines (an entity WAD, as predicted).
  - `R_HADESBIG.WAD` 82,873,312 B; `R_HADESBIGSOUL.WAD` 13,649,648 B.
  - `HDS675AI1HADES.WAD` — 47,136 B, `hfsmEnemy1` / `hfsmBreakable` / `hfsmIO_Misc`
    (the behaviour, a separate replaceable file).
  - The health-bar name is the string `Hades` in `R_LANG_EN.WAD`.
- The shape is exactly what the plan wants: **model**, **behaviour** and **name**
  are three separate replaceable files, and all three are reachable from one save
  one click away from the fight.
- Harness: added `-BossTest` (isolates `SD-261017161301` with no slot argument).
- Blocked on: **G9/G10** — the WAD record directory. Without a WAD reader/writer,
  Stage 1 (tint `R_UI.WAD`) cannot be run.

---

## 2026-10-17 — G9: found the DC_ id 0x10 offset table (name→bytes binding lead)

- Did: read real bytes from `R_SWORD00.WAD` (87,840 B) and `BAS500AI3ARG00.WAD`
  (13,040 B). Found that the `DC_` footer chunk with id `0x10` holds a sorted
  table of bulk file offsets (47 entries in `R_SWORD00.WAD`: `0xD84, 0xDAC,
  0xDE4, …, 0x1654`) followed by ASCII strings (`CRT_`, `Sword00`, `FX_…`).
  Also proved `DC_` marker count is 0 or 6 per WAD, not always 6. Recorded as
  **E-027**. Fixed stale `wad.py`/`wad_info.py` docstrings (directory IS decoded;
  `DC_` count is 0 or 6). Added unit test asserting `DC_` count can be zero.
  Committed as `fac6b82` (refs #36). 112 tests green.
- Found: **E-027** — `DC_` id `0x10` is the directory→bulk offset table, the
  missing name→bytes binding. Entry structure (`0x9F`/`0xA4` alternating field,
  ascending third field) and the mapping from table entries to the 16 directory
  resource names are unknown. 47 entries vs 16 resources means one entry ≠ one
  resource. A WAD writer remains blocked.
- Next: resolve the table entry → resource name mapping (best lead: check how
  entry offsets align with the directory's resource order, or compare against a
  larger entity WAD such as `R_HADES.WAD`). Until then, Stage 1 of the boss
  test loop (tint `R_UI.WAD`) is blocked on G9/G10.

## 2026-10-17 — G9: resource taxonomy decoded; two of my own measurements discarded

Owner: *"re-iterate until done; I want Hades phase 1 to be Vergil, with his own
moves and health bar and everything."*

- Did: attacked the WAD record directory from the smallest possible file. Recorded
  **E-023**.
- **Discarded two failed measurements** (recorded so they are not repeated):
  - uniform **0x40-byte stride** — invalid; unnamed records are 0x10/0x20, so the
    stride is not constant (32 bytes left over, garbage type fields).
  - a **regex** scan for the resource pattern — invalid; it matched the byte
    pattern inside payloads and produced nonsense like `"iving"`, `"hortcut"`.
    Not treated as evidence.
- **Solid result — the resource class table.** From a complete dump of
  `R_I_ICE0.WAD` (3,456 bytes, readable end to end), the `0x80000000|n` marker
  following each resource is constant per 4-letter prefix:

  `MDLX`=13 model · `TXRX`=7 texture · `MATX`=8 material · `ANMX`=3 animation ·
  `BHVX`=18 behaviour · `COLX`=14 collision · `SNDX`=19 sound · `CAMX`=9 camera ·
  `SCRX`=4 script · `LGTX`=6 light · `PRTX`=15 particle · `FX`=21 · `OCCX`=24 ·
  `WPTX`=16 · `CXT`=1 · root=20

  Commands: `1`=resource(name,size), `2`=GroupStart, `3`=GroupEnd,
  `0x12`=root, `0x15`=PopHeap. Named records are 0x40 bytes.

  So a WAD is a **nested group tree of typed, named resources** — exactly the map
  needed to know which records to replace for Vergil's mesh/animations.
- **Big find on the behaviour side.** The AI WAD contains a **readable logic graph**
  with English descriptions ("Detecting the player is in the air", "Spawning wave
  11", "Telling the brutes and his grunts to chase the player"), `CI*` logic nodes,
  sensors, event transmitters, and — directly relevant — **per-weapon nav profiles
  `navWalkSword`, `navWalkShield`, `navWalkSpear`, `navWalkStone`**. Vergil wields
  a sword and a `navWalkSword` profile already exists.
- Still blocking: the exact **per-record framing** (how a length is determined for a
  record with no name). No reader/writer → no repack → no test iteration.
- Next: settle the framing. Best lead: dump the region immediately after a resource
  record (e.g. 0x0D0..0x0F0 in `R_I_ICE0.WAD`) and work out what the 0x18/0x08
  payload bytes encode, then check whether the following record is at a
  16-byte-aligned boundary.

---

## 2026-10-17 — G9: the WAD is 16 typed resource groups; scanner validates itself

- Did: built a resynchronising record scanner and validated it across the 87 WADs
  under 1.5 MB. Shipped `scan_records` / `resources` / `resource_histogram` and
  `wad_info.py --resources`. Recorded **E-024**. 8 new tests (102 total).
- Found — and this is the strongest result so far:
  - **Every WAD carries the same 16 resource groups**, one per type, in a fixed
    order: `root TXRX WPTX CXT ANMX LGTX SCRX BHVX MDLX PRTX CAMX SNDX COLX FX
    OCCX MATX`.
  - **The name prefix and the marker's class id agreed on every occurrence**
    (87/87 for `WAD`/`TXRX`/`WPTX`/`MATX`; 95 each for the rest). Two independent
    derivations never disagreeing mutually validates the class table (E-023) *and*
    the scanner.
  - Confirmed on the real target: `R_HADES.WAD` (85,727,632 B) exposes
    `MDLX_R_Hades`, `ANMX_R_Hades`, `TXRX_R_Hades`, `BHVX_R_Hades`, `MATX_R_Hades`, …
- **So "which records do I replace?" is now answered**: `MDLX_` (mesh), `TXRX_`/
  `WPTX_`/`MATX_` (textures/materials), `ANMX_` (animations), optionally `BHVX_`
  (behaviour — Hades's, or authored, since the AI graph is readable).
- **Not claimed:** marker record *length* is still undetermined (observed 0x10 and
  0x20), so the scanner resynchronises and is an **inventory** tool, **not a
  writer**. Repacking stays blocked. Also recorded three false class ids from float
  data (`class1065353216` = 1.0f) and the unconfirmed prefixes `ESC`, `WYP`, `ENV`.
- Next: the marker length. With it, the writer becomes possible and Stage 1 of the
  test plan can finally run.

---

## 2026-10-17 — F4 keyframe census: preamble/keyframe split recorded, u16[1..3] left [UNKNOWN]

- Did: bounded slice on F4. Read real bytes from all ten `pl021_*.pac` files
  (G:\Games\...\GData.afs) and walked every MOT chunk: 7,659 records, 110,639
  eight-byte groups, 87,662 keyframe groups, 0 record-layer failures.
- Found:
  - **E-028** — each record = `field_a` preamble groups + `groups` keyframe
    groups: `len(group_bytes()) == field_a + groups` for 7,656/7,659 records;
    `field_a == 3` for 7,656/7,659 (3 exceptions break the size relation).
    Keyframe group u16[0] = offset-binary frame time reconfirmed on real bytes
    (`frame = u16[0] - 0x8000`). u16[1..3] as signed 16-bit span [-32768,
    32767], vary per keyframe, cluster at +/-0x3FFF (~0.5 Q15), 0, 0xFFFF;
    only ~5% near zero. Channel meaning, scale and zero point are NOT
    established from bytes alone — recorded as [UNKNOWN], not inference.
  - Committed 6d49d88 (refs #2): `keyframe_groups()` in
    `tools/dmc3/mot.py` (re-exported from `dmc3.__init__`), 2 new unit tests,
    E-028 in docs/EVIDENCE.md, docs/FORMATS.md §3.1 and docs/BACKLOG.md F4
    updated. 114 tests, all green. Pushed to origin main.
  - Commented issue #2 with findings and what remains; issue left open.
- Next: file a follow-up issue for the u16[1..3] encoding (scale, zero point,
  channel assignment, preamble contents) or continue F4 via the +0x22 table;
  F1/F5 remain alternatives on the Phase 1 critical path.


## 2026-10-17 — F4 first field decoded: keyframe group u16[0] = frame time

- Did: bounded slice on F4 (MOT keyframe encoding). Read real bytes from
  `pl021_00_9.pac` (slot 0, file +0x10) and walked every record; confirmed the
  first u16 of each 8-byte keyframe group is an offset-binary frame count,
  `frame = u16[0] - 0x8000`, monotonic and bounded by the header duration.
- Found (E-026): verified on all 840 MOT chunks / 59,269 records / 623,060
  keyframes; 0 violations on every Vergil `pl021_*.pac` chunk. A small non-Vergil
  minority (29 non-monotonic, 1,073 out-of-range) is recorded as an edge case.
- Added: `keyframe_time()` / `KEYFRAME_TIME_BASE` to `tools/dmc3/mot.py`, 3 unit
  tests in `tests/test_mot_records.py` (111 total, all green).
- Updated: `docs/FORMATS.md` §3.1 ([INFERRED] first field, [UNKNOWN] the rest),
  `docs/BACKLOG.md` (F4 first field decoded).
- Next: the remaining three u16s per keyframe group and the per-record header
  groups (positions 0–2) — file a follow-up issue for those.

## 2026-10-17 — F4 keyframe remainder bounded (issue #2)

- Did: walked every MOT chunk in all ten real `pl021_*.pac` files (7,659
  records, ~87.7k keyframe groups, 0 walk failures) and ran three bounded
  byte-level hypotheses: preamble-group content, per-record channel constancy,
  and preamble-as-base-pose.
- Found:
  - **E-029** — each record = `field_a` preamble groups + `groups` keyframe
    groups; `field_a == 3` in 7,656/7,659 records. Every preamble group reads as
    a pair of finite little-endian f32s with |v| ≤ 1e6 (22,974/22,974 groups;
    97.4% with both |v| ≤ 10; worked example recorded: pl021_00_9.pac record 0
    preamble `(6.446631, 0.993246)`, `(-0.023649, 0.089923)`,
    `(-0.234987, 0.939949)`). Preamble semantics unknown.
  - u16[1..3] vary per keyframe — NOT per-record constants (only 458/269/258 of
    7,659 records have a channel constant, dominated by trivial single-keyframe
    records). Modal values ±0x3FFF (~5,500 hits/channel of 87,662); full signed
    range [-32768, 32767].
  - Preamble is NOT a stored base pose: preamble == first keyframe groups in
    0/7,659 records.
  - Channel meaning, scale, zero point, record→bone mapping cannot be
    established from bytes alone → marked **[UNKNOWN]** in E-029 /
    FORMATS.md §3.1 so they are not retried; both disproven hypotheses marked
    **[DISPROVEN]**.
- Committed `9d60b66` (refs #2), pushed to origin main. 117 unit tests, all
  green. Commented issue #2; issue left open (engine ground truth needed).
- Next: F1 (MOD mesh payload) is the remaining Phase 1 critical-path decoder,
  or file a dedicated follow-up issue for the u16[1..3] encoding.


---

## 2026-10-18 — F1 bounded slice: MOD header decoded from real bytes

- Did: read every `MOD ` chunk in `pl021.pac` (slots 1/12/23/25) and scanned all
  286 `MOD ` chunks across the install; implemented `tools/dmc3/mod.py`
  (`ModHeader` reader), a synthetic `mod_chunk` fixture, and `tests/test_mod.py`
  (8 new tests). Full suite: **125 tests, all green**. Committed as 3a8ceb4.
- Found (**E-030**): header is a fixed 0x24-byte block — `+0x04` f32 =
  1.0099999904632568 (`0x3F8147AE`) in 285/286 chunks (one is 1.0); `+0x0C` and
  `+0x1C` are `0` in all 286; `+0x08`/`+0x18` are `0` in the pl021.pac samples;
  varying u32s at `+0x10`/`+0x14`/`+0x20` (e.g. `+0x14 == 0xF4240` = 1,000,000
  in 187/286 — an inference, not an observation). Payload body at `+0x24`
  remains **[UNKNOWN]**.
- Docs corrected: `docs/FORMATS.md` §5 — an earlier revision wrongly placed the
  varying values at `+0x0C`/`+0x1C`; real bytes show those offsets are `0` and
  the values live at `+0x10`/`+0x20`. `docs/EVIDENCE.md` gained E-030 with the
  raw bytes and distributions; `docs/BACKLOG.md` F1 marked open with header
  decoded, payload [UNKNOWN], cross-check vs prior art (E-014/E-015).

## 2026-10-18 — F1 bounded slice: MOD payload body prefix decoded

- Did: read real bytes from `pl021.pac` (G:\Games\...\GData.afs\pl021.pac),
  slots 1/12/23/25, at file offsets 0x039880 / 0x078350 / 0x811E0 / 0x838C0;
  implemented `ModBodyPrefix` in `tools/dmc3/mod.py`, extended `mod_body()`
  fixture and `tests/test_mod.py` (7 new tests). Full suite: **132 tests, all
  green**.
- Found (**E-031**): body prefix (chunk +0x24) = 28 zero bytes, then body+0x1C
  u16 marker `0x8001` (constant), body+0x1E u16 count (474/300/182/182),
  body+0x24 u32 (768/192/128/128), four f32s at body+0x4C..+0x58, body+0x5C u32
  which equals count only for the byte-identical slots 23/25. All field
  meanings are [UNKNOWN]. Verified `body+0x5C == count` for slots 23/25 and
  `!= count` for slots 1/12 on real bytes.
- Docs: `docs/EVIDENCE.md` E-031 (raw bytes + table); `docs/FORMATS.md` §5.1
  (body prefix spec, [PARTIAL]/[UNKNOWN] marking); `docs/BACKLOG.md` F1 row
  updated to E-030/E-031 with payload body beyond +0x5C [UNKNOWN].
- Next: the vertex/index/normal/UV/weight layout beyond body+0x5C is the
  remainder of F1; this slice stops at the decoded prefix per the bounded-slice
  rule. F4's remaining unknowns (u16[1..3] scale/zero point) need engine ground
  truth and are not decodable from bytes alone.

---

## 2026-10-18 — F5 bounded slice: +0x22 MOT table structure decoded from real bytes

- Did: read the +0x22 u16 table from every MOT chunk in all 161 PAC files
  (840 chunks) via the installed GData.afs tree; recorded the census as E-032;
  added FORMATS.md §3.2 ([PARTIAL] structure / [UNKNOWN] semantics); updated
  BACKLOG.md F5 row; added `TestMotTableRealShapes` to tests/test_mot.py;
  full suite **135 tests, all green**; committed as 9394b4f, pushed to origin
  main; commented issue #5 (left open).
- Found (**E-032**):
  - `len(table) == (header_size - 0x22) / 2` holds for all 840 chunks (23
    entries for the 0x50 header; 31 for the single 0x60 header,
    `pl000_00_8.pac` slot 1).
  - Dominant shape: 22 x u16 56 (0x38) then 0 — 703/840 chunks, including
    every Vergil `pl021_00_*.pac` chunk. Variants: 504-based (28, Crimson
    overlays), `58 x 22 + 0` (2), mixed 56/0 (71), `56 x 21 + 0 + 0` (18),
    varying last entry 29..26755 in `demo_pl000_00_3.pac` (17).
  - Key negative: the table is **not** per-bone data — 23 entries vs 24
    bones, and no entry varies per index. Semantics of 56/504/58 and the
    final entry remain [UNKNOWN]; engine ground truth needed.
- Next: nothing left on F5 from bytes alone. F1 (MOD payload beyond +0x5C)
  and F4 (keyframe u16[1..3] / preamble semantics) remain stopped at their
  bounded-slice boundaries for the same reason. Candidates for the next
  iteration: F3 (untagged pl021.pac chunks), F7 (animation name map), F8
  (TM2 pre-header), or tooling T3 (PAC writer round-trip test) — all have
  resolved dependencies.


---

## 2026-10-18 — F3 bounded slice: pl021.pac slot 0 raw header decoded from real bytes

- Did: bounded slice on F3 (untagged pl021.pac chunks, issue #4). Read all
  27 slots of the real pl021.pac (G:\Games\Devil May Cry HD Collection\data\dmc3\GData.afs\pl021.pac): 18 occupied slots, nine untagged (0, 5, 6, 7, 9, 10, 11, 21, 22). Added tools/dmc3/raw.py (RawHeader / maybe_raw_header), the raw_chunk_slot0() fixture, and tests/test_raw.py (4 new tests). Full suite: 139 tests, all green. Committed ba51c75, pushed to origin main; commented issue #4.
- Found (E-033): slot 0 at file offset 0x80 (span upper bound 0x39800 to slot 1 at 0x39880) begins with six u32s 5, 43, 22, 43, 5, 1, then zeros until body+0x0800; an embedded DDS magic (dwSize 124, 256x64) at body+0x0870 / file offset 0x8F0. All field meanings [UNKNOWN]; no shared header shape across the untagged slots.
- Docs: EVIDENCE.md E-033; FORMATS.md §1.3 ([UNKNOWN]); BACKLOG.md F3 open — header decoded, body layout [UNKNOWN].
- Next: F3 body layouts (slot 10 u16 pairs, slot 21 0xFFFF-separated table are the clearest tables) need engine ground truth; F1 and F4 remain blocked on engine ground truth as well.

---

## 2026-10-18 — F8 bounded slice: TM2 pre-header census from real bytes

- Did: bounded slice on F8 (TM2 pre-header fields, issue #8). Read the single local TM2,
  `G:\Games\Devil May Cry HD Collection\data\dmc3\GData.afs\i001_90.tm2` (65,776 bytes),
  and recorded all 28 pre-header u32s as E-034. Added fixtures
  (real_tm2_preheader / real_tm2_dds / real_tm2) and 3 unit tests in tests/test_tm2.py.
  Full suite: 142 tests, all green. Committed acc29ce, pushed to origin main; commented issue #8.
- Found (E-034): DDS magic at file 0x70; all 28 platform-header u32s are [UNKNOWN]
  (non-zero at 0x08/0x0C/0x10/0x14/0x20/0x38/0x44/0x48/0x4C/0x64/0x68). E-005's claim
  that "only 0x08 and 0x0C are non-zero" is falsified; the wrapper-is-DDS extraction
  conclusion stands.
- Docs: FORMATS.md §4 updated with the pre-header census and E-005 correction; BACKLOG.md
  F8 row updated (E-005/E-034, every field [UNKNOWN], extraction already working).
- Next: F1 (MOD payload beyond +0x5C), F4 (keyframe u16[1..3] / preamble semantics) and
  F3 body layouts all remain blocked on engine ground truth; nothing further is
  decodable from bytes alone on those. F8 needs more TM2 samples or engine ground truth
  before any field can be assigned meaning.


## 2026-10-18 — F7 bounded slice: Vergil motion-slot census from real bytes

- Did: bounded slice on F7 (map (group, slot) to human-readable animation names,
  issue #7). Added mot_summary() to tools/dmc3/mot.py (duration + record_count read
  straight from a MOT chunk's real bytes), exported it from dmc3/__init__, and added
  a unit test on a synthetic fixture (tests/test_mot.py). Recorded E-035 from the ten
  real pl021_00_*.pac files. Updated docs/ANIMATIONS.md ([LOCAL] group table plus
  three Crimson-overlay anchors) and docs/BACKLOG.md (F7 row). Full suite: 143 tests,
  all green. Committed as 98386af, pushed to origin main; commented issue #7.
- Found (E-035):
  - Slot counts match E-009 exactly for all ten groups (23/14/5/16/11/14/2/11/11/1);
    all 108 occupied MOT slots walk cleanly with the stored record count reached.
  - Overlay anchors [LOCAL]: taunt -> group 2 slot 0 (340 frames), Judgement Cut ->
    group 3 slot 13, Yamato High Time -> group 5 slots 7-8 (overlay-vs-base byte
    diffs on the real Crimson overlay .pac files).
- Remaining: move names and the group/slot -> global-motion-number (000-044) mapping
  are [EXTERNAL]/[UNKNOWN]; confirming them needs exported clips compared to in-game
  footage (F9) and the MOT keyframe encoding (F4, blocked on engine ground truth).
- Issue #7 left open (not decodable from bytes alone).
- Next: pick the next bounded slice whose dependencies are resolved (e.g. T3 PAC
  writer round-trip test, or H1/H2/H3 research); F1/F4/F3 remain blocked on engine
  ground truth.

## 2026-10-18 — T3 PAC writer hardened; byte-exact round-trip test added (issue #11)

- Did: hardened `build_pac` in `tools/dmc3/pac.py` (rejects non-bytes payloads with a
  clear `TypeError`) and added `test_build_pac_round_trip_is_byte_exact` plus
  `test_build_pac_rejects_non_bytes_payload` in `tests/test_pac.py`. The round-trip
  test rebuilds a PAC from each chunk's full span (payload + 16-byte inter-chunk and
  trailing padding) and asserts byte-exact reproduction of the whole file and
  identical re-parsed chunks (entries, offsets, spans, data, tags). Updated
  `docs/BACKLOG.md` T3 row. Committed 6d6a85d, pushed to origin main; closed issue
  #11 with a comment summarizing findings.
- Found: 145 tests, all green (143 baseline + 2 new). `build_pac` is verified as the
  inverse of `PacArchive` for self-describing chunks on synthetic fixtures; no game
  data committed. This is the property Phase 2 re-encoding of MOD/MOT chunks relies on.
- Next: F1/F4 remain blocked on engine ground truth (per earlier slices). With the
  critical path blocked, pick another resolved-dependency slice such as H1/H2/H3
  research, or revisit WAD record length (G9/G10).

---

## 2026-10-18 — F2 bounded slice: SHW shader-chunk header decoded from real bytes

- Did: decoded the `SHW ` chunk header from all four real `SHW ` chunks in
  `pl021.pac` (slots 8/14/24/26; slots 24/26 byte-identical), added
  `tools/dmc3/shw.py` (`ShwHeader` reader), synthetic fixture `shw_chunk()`,
  and `tests/test_shw.py` (11 new tests asserting only observed values).
  Committed as d319ab4, pushed to origin main; commented issue #3 (left open).
- Found (**E-036**): header layout verified on real bytes — tag `SHW `, f32
  0.5 at +0x04 (4/4 chunks), zero u32s at +0x08/+0x0C/+0x18/+0x1C/+0x24/
  +0x28/+0x2C, varying u32s at +0x10/+0x14, varying u16 pair at +0x20/+0x22,
  and four varying u32s at +0x30/+0x38/+0x40/+0x48 each followed by a zero
  u32. **+0x30 is verified as a sub-table offset** (slot 8: 0x460, slot 14:
  0x1E0, slots 24/26: 0x60) landing on 16-byte entries `[i0, i1, i2, 0]` of
  small u32 indices in all four chunks; +0x38/+0x40/+0x48 point at further
  sub-tables (i16 pairs, f32 data, byte data). Every field meaning and the
  texture binding itself remain **[UNKNOWN]**; F2 stays open.
- Correction: an earlier draft placed the 0x460/0x1E0/0x60 values at +0x28;
  real bytes show +0x28 is 0 in all four chunks and the values live at +0x30.
  Code, E-036, FORMATS.md §5 and BACKLOG.md F2 all reflect the corrected
  offsets.
- Next: F1/F4 remain blocked on engine ground truth; pick another
  resolved-dependency slice (H1/H2/H3 research, or similar).

---

## 2026-10-18 — F3 bounded slice: pl021.pac slot 10 u16 pair table decoded from real bytes

- Did: read real bytes from pl021.pac slot 10 (file offset 0x077ED0, span
  0x1E0) on the installed GData.afs tree; added Slot10Table / SLOT10_PAIR_COUNT
  to tools/dmc3/raw.py, a synthetic raw_chunk_slot10() fixture, and 3 unit
  tests asserting verbatim observations; updated EVIDENCE.md (E-037),
  FORMATS.md §1.3 and BACKLOG.md F3 row. Committed as d34b0ef, pushed to
  origin main; commented issue #4 (left open). Full suite: 160 tests, all
  green.
- Found (E-037): slot 10 is an untagged raw chunk with a two-part structure:
  +0x00..+0x5B holds 23 u16 pairs at stride 4 (pairs 0-14 are (92,
  132+20*i); pairs 15-22 are (112,432), (92,432), (92,132)x6); +0x5C..end is
  a little-endian f32 stream opening 0.3, -0.01, -0.1, 0.0, 0.7. All field
  meanings are [UNKNOWN]; the pair count's source, what the pairs index, and
  the f32 stream's meaning are not established from bytes alone.
- Next: F1/F4 remain blocked on engine ground truth and are not retried;
  pick another resolved-dependency slice (H1/H2/H3 research, F2 sub-tables,
  or similar).

---

## 2026-10-18 — F2 bounded slice: SHW sub-tables decoded from real bytes

- Did: picked F2 (issue #3) from the always-available list since F1/F4 remain
  blocked on engine ground truth and are not re-spun. Read real bytes from all
  four `SHW ` chunks of `pl021.pac` (slots 8/14/24/26); implemented
  `ShwIndexTable`, `ShwPositionTable`, `ShwSubTables` and
  `parse_shw_sub_tables`/`maybe_shw_sub_tables` in `tools/dmc3/shw.py`, a
  `shw_chunk_with_tables` fixture, and 9 unit tests on synthetic fixtures.
  Committed as f898a3f, pushed to origin main; commented issue #3 (left open).
  Full suite: 169 tests, all green.
- Found (**E-038**): `field_38` (+0x38) → index buffer `[u16 i0,i1,i2,u16 0] x
  count`, `field_40` (+0x40) → position buffer `[f32 x,y,z,f32 1.0] x count`;
  counts derived from consecutive-pointer differences, a verified invariant
  across all 4 chunks (slot 8: 16 tris/10 positions at file 0x759d0/0x75a50;
  slot 14: 40 tris/22 positions; slots 24/26: 66 tris/39 positions); tables
  contiguous. Position values show L/R symmetry with w==1.0 (vertex-like).
- Unknown (recorded honestly): field semantics; index↔position cross-reference
  fails for slots 8/14 (max index exceeds position count), holds only for
  slots 24/26; layout/meaning of the +0x48 table; the texture binding.
- Docs: `docs/EVIDENCE.md` E-038, `docs/FORMATS.md` §5.1.1, `docs/BACKLOG.md`
  F2 row updated. F2 stays open — needs engine ground truth for the binding.
- Next: another resolved-dependency slice (F3 slot-10 f32 stream / other
  untagged slots, or F8 pending more TM2 samples).

---

## 2026-10-18 — F6 bounded slice: PNST weapon-container header decoded from real bytes

- Did: implemented `tools/dmc3/pnst.py` (`PnstArchive` reader), the synthetic
  `pnst_archive()` fixture, and 15 unit tests in `tests/test_pnst.py`; exported
  `PnstArchive`/`PnstChunk`/`PNST_TAG_*` from `dmc3/__init__.py`. Updated
  `docs/EVIDENCE.md` E-006, `docs/FORMATS.md` §2, `docs/BACKLOG.md` F6 row.
  Committed as 01b08ec, pushed to origin main; commented issue #6 (left open).
  Full suite: **184 tests, all green**. Parser exercised read-only against both
  real weapon archives — all 9/10 slots resolve to real chunk starts.
- Found (**E-006**): `PNST` = `u32` magic `"PNST"`, `u32 count`, then `u32
  offset[count]` at `+0x08`; `align_up(0x08 + 4*count, 0x10) == offset[0]`
  holds on both `plwp_vergilsword.pac` (count=9) and
  `plwp_newvergilsword.pac` (count=10). Chunk kinds observed: `MOD ` mesh,
  `SHW ` shader, nested `PAC\0`, nested `PNST` (which itself contains a
  further `PNST` at `0x17DB0`), `;wp005.clt` cloth-config text, and
  unidentified raw blocks opening `01 00 00 00 11 00 00 00` at slots 0 and 3
  in both files.
- Next: F6 payload semantics remain [UNKNOWN] (raw blocks, nested containers,
  empty-slot sentinel). F1/F4 remain blocked on engine ground truth and are not
  re-spun.

---

## 2026-10-18 — T7b bounded slice: FLVER header of Vergil's body decoded

- Did: picked T7b (issue #34, tooling, phase-1, critical-path — roadmap
  milestone 1.0 lists "body FLVER still open"). F1/F4/F5 are blocked on engine
  ground truth and not re-spun; F8 needs more TM2 samples; F2/F3 need engine
  ground truth for their remaining unknowns, so T7b is the available
  critical-path slice. Read real bytes from
  `C:\Users\GigelCastel\Desktop\vergil\parts\bd_m_10100-partsbnd-dcx\BD_M_10100.flver`
  (467,008 bytes — reading only, outside the two forbidden game-install paths).
  Added `tools/priorart/flver.py` (`FlverHeader`, `parse_flver_header()`),
  exported from `priorart/__init__.py`, a synthetic `flver_header()` fixture in
  `tests/fixtures_priorart.py`, and `TestFlverHeader` (6 tests) in
  `tests/test_priorart.py`.
- Found (**E-039**): header is a fixed 128-byte block. Magic `FLVER\0`
  [VERIFIED]. u16 76/20/2, u32 61488/405520/0/6/334/6/12, six f32s
  (-0.7157, 0.0, -0.1980, 0.7180, 1.7909, 0.2405), u32 28062/28062/256/0/36/10/42
  — every field meaning [UNKNOWN]; only the magic is verified. The six f32s are
  plausibly a bounding box (E-017's 1.79 m vertical extent is an inference,
  not an observation). 16-byte records begin at 0x80; not decoded.
- Docs: E-039 in EVIDENCE.md; FORMATS.md §6 (FLVER header, [UNKNOWN] marking);
  BACKLOG.md T7 row updated (header decoded, body layout open).
- Next: T7b is advanced, not complete — the 0x80+ record structure and the
  body mesh layout remain. F1/F4 still blocked on engine ground truth.
- Tests: full suite **190 tests, all green**. Commented issue #34.

## 2026-10-18 — T7b: FLVER section table decoded from real bytes

- Did: decoded the section table of ``BD_M_10100.flver`` (Vergil's body from
  the prior-art Bloodborne package): six 32-byte section entries at file
  offset 0x80..0x140, each eight u32s. Added ``FlverSection`` /
  ``parse_flver_sections()`` to ``tools/priorart/flver.py``, exported them
  from ``priorart/__init__.py``, added a synthetic fixture mirroring the real
  bytes and 5 unit tests. Full suite: **195 tests, all green**. Committed as
  8851ee5, pushed to origin main.
- Found (**E-040**): verified structure — u32_08 == 7, u32_0c == 7 * entry
  index, u32_1c == 0, u32_18 in 0..5, u32_14 = 48160 + 240 * index; u32_00
  is a running offset stepping by the previous entry's u32_10 (49600, +366,
  +360, +362, +370, +374). u32_14 points at "GX**" magic blocks; entry 0's
  u32_00 (0xC1C0) opens a UTF-16LE name string ("costume_parsn_..."); header
  +0x0C (0xF030) points at u16 index data; header +0x10 (0x63010) points at
  further record data. Also corrected E-039's example record values, which did
  not match the verified bytes.
- Next: all field meanings remain [UNKNOWN]; count source (header +0x18 vs
  +0x24) and the "GX**" block semantics are open — engine ground truth or a
  FLVER spec needed, same as F1/F4. GX block internals are the natural next
  T7b slice.

## 2026-10-18 — T7b: FLVER GX block structure decoded from real bytes

- Did: decoded the GX block groups referenced by each FLVER section's u32_14
  in ``BD_M_10100.flver`` (Vergil's body, prior-art package). Added
  ``FlverGxBlock``/``FlverGxGroup`` and ``parse_flver_gx_block()``/
  ``parse_flver_gx_group()``/``parse_flver_gx_groups()`` to
  ``tools/priorart/flver.py``, exported them, added synthetic fixtures and 12
  unit tests. Full suite: **207 tests, all green**. Committed as fa349fb,
  pushed to origin main; commented issue #34.
- Found (**E-041**): each section's u32_14 (48160 + 240*i for i in 0..5)
  points exactly at a 240-byte group: GX00(44), GX04(64),
  GX20/GX22/GX24/GX26/GX30 (24 each), sentinel u32 0x7FFFFFFF(12); every
  block = u32 tag, u32 constant 100, u32 size, size-12 payload; all six
  groups byte-identical; last GX magic at 0xC19C, then UTF-16 name strings.
- Correction: E-040's "+4/+16 off" claim for sections 1/3 was imprecise — all
  six sections point exactly at GX00; E-040 carries a correction note to E-041.
- Remaining [UNKNOWN]: meaning of every tag, the constant 100, every size
  field, every payload; body mesh layout beyond the GX groups (vertex/index
  buffers, declaration). Engine ground truth or FLVER spec needed; not
  decodable from bytes alone. F1/F4 remain blocked on engine ground truth and
  are not re-spun.
- Next: pick another resolved-dependency slice (F2 sub-tables / F3 slot-10 f32
  stream / F8 pending more TM2 samples) or record F1/F4 as dead ends needing
  engine ground truth.

## 2026-10-18 — T5 PAC-diff CLI implemented (issue #10)

- Did: implemented `tools/pac_diff.py` (read-only CLI comparing two `.pac`
  archives by logical slot index; reports tag/kind/offset/span/payload per
  slot; exit codes 0 identical / 1 differ / 2 error), added
  `tests/test_pac_diff.py` (10 synthetic-case tests), marked BACKLOG.md T5
  done, recorded the F8 TM2 sample-exhaustion dead end as E-042.
  Smoke-verified on real artifacts (read-only): `pl021.pac` vs itself →
  slot-identical (exit 0); `pl021.pac` vs `pl000.pac` → 18 differing slots
  (exit 1). Closed issue #10 with a summary comment.
- Found: full suite **217 tests, all green**. The format critical path
  (F1/F4/F2/F3/F5/F8) remains blocked on engine ground truth; F8's "needs
  more TM2 samples" blocker is answered negatively — all three local TM2s
  (`i001_90.tm2` root/Xbox/PlaystationButtons) share one byte-identical
  pre-header, so no field can be cross-decoded from local bytes.
- Next: T6 (CI workflow, issue #12) is the next available tooling item; the
  format critical path stays idle until engine ground truth is available.

## 2026-10-18 — F3 bounded slice: pl021.pac slot 21 u16 segment table decoded from real bytes

- Did: bounded slice on F3 (issue #4). Read real bytes from pl021.pac slot 21
  (G:\Games\Devil May Cry HD Collection\data\dmc3\GData.afs\pl021.pac) at file
  offset 0x07FF00, span 0x2E0 (368 u16s). Added Slot21Table /
  SLOT21_SEPARATOR (0xFFFF) to tools/dmc3/raw.py, a synthetic
  raw_chunk_slot21() fixture in tests/fixtures.py, and TestSlot21Table (4
  tests) in tests/test_raw.py. Exported from dmc3/__init__.py. Committed as
  5684450, pushed to origin main; commented issue #4.
- Found (E-043): slot 21 is 14 little-endian u16 segments delimited by 0xFFFF
  separators (13 separators at u16 indices 2, 9, 11, 20, 31, 63, 175, 210,
  212, 219, 228, 256, 341); segment sizes 2/6/1/8/10/31/111/34/1/6/8/27/84/26;
  segment 0 verbatim (6, 408). Two internal regularities recorded as
  observations only: segment index 5 ends in arithmetic run 36,50,64,...,232
  stepping by 14; segment index 6 repeats a 7-u16 sub-record
  32767,0,32767,1,1,0,VALUE with VALUE stepping by 256 from 771 to 4099.
  0x7FFF occurs inside segments and is not a delimiter.
- Next: F3 remains open — segment-internal layout and all field meanings are
  [UNKNOWN] and need engine ground truth; slot 10's f32 stream and untagged
  slots 5/6/7/9/11/22 are still undecoded. F1/F4/F2/F5/F8 remain blocked on
  engine ground truth and are not re-spun.

---

## 2026-10-18 — G9: WAD bulk header and DC_ id 0x10 table decoded from real bytes

- Did: picked G9 (issue #36) from the resolved-dependency list because the Phase 1
  format critical path (F1/F4/F2/F3/F5/F8) stays blocked on engine ground truth.
  Read real bytes from two WADs (R_SWORD00.WAD 87,840 B and GAZ650.WAD 13,152 B)
  under C:\Users\GigelCastel\Desktop\gow3\CUSA01715\EXEC\WAD\PS4_LE\ — read only,
  no writes to the install.
- Found (E-044): in both files the record directory ends at 0xD80 and the bulk
  region opens with an identical header (`01 00 77 00`, u32 0x0D69/0x0D59,
  16-byte name "NNNNNNNN_FFFFFFFFF", then u32s 8/1/1/16, 1/0, 0x18/0x20, …).
  The `DC_` id `0x10` chunk payload of R_SWORD00.WAD (file 0x14AD8, size 3064)
  decodes as header u32s `(0, 0x77, 0, 0x598)`, 118 triplets
  `(u32 flag, u32 offset, u32 value)` with ascending offsets (0x20 → 0x1654;
  entries >= 0xD80 land on bulk object data, byte-verified at 0xD84, 0xDE4,
  0xE44, 0x15BC, 0x1654), then a NUL string pool ("CRT_Sword00", "FX",
  "Bubbles", "MOV_*", "BRA_*", "tActionSetFlags_86" …). GAZ650.WAD's id 0x10
  chunk is degenerate (6 u32s, no entries, no strings).
- Added: `Dc10Entry` / `Dc10Table` / `parse_dc10_table()` in
  `tools/gow3/wad.py` — face-value parse only, no semantic claims — exported
  from `gow3/__init__.py`; `TestDc10Table` (3 tests) in
  `tests/test_gow3_wad.py` on synthetic fixtures. Full suite: **224 tests, all
  green**.
- Unknown (recorded, not inferred): flag/offset/value semantics, the offset
  reference frame, and the entry → directory-resource binding — so a WAD writer
  remains blocked; G9/G10 stay open.
- Docs: E-044 in docs/EVIDENCE.md; new §7 in docs/FORMATS.md; BACKLOG.md G9 row
  updated (marker length now resolved per E-025).
- Next: WadGraph name→WAD binding (G10, #39), or retry the G9 entry binding on
  a larger entity WAD (e.g. R_HADES.WAD).

## 2026-10-18 — WadGraph registry structure decoded from real bytes (G10 bounded slice)

- Did: picked G10 (#39) from the always-available list since the Phase 1 format
  critical path (F1/F4/F2/F3/F6) stays blocked on engine ground truth and is not
  re-spun, and F8 is a recorded dead end (E-042). Read real bytes from
  `DEPENDENCYGRAPH.IFF` (read-only, outside the repo); implemented
  `tools/gow3/wadgraph.py` (`WadGraphHeader`, `WadGraphRecord`, `parse()`,
  `parse_records()`, best-effort heuristic `record_name()`) and
  `tests/test_gow3_wadgraph.py` (7 new tests on synthetic fixtures). Full suite:
  **232 tests, all green**. Committed and pushed; commenting issue #39 (left
  open).
- Found (**E-045**): header = u16 23, u16 1, u32 265712 (== file_size − 0x40),
  banner `"WadGraph"` at 0x08. Records are 32 bytes at stride 0x20 from 0x40:
  u32 name_offset, u32 0, u32 field_b, u32 field_d, u16 field_c, u64 −1
  sentinel, u8 0, u8 pad_byte, u32 0x55555555 trailer. 2,617 matching records
  observed spanning `0x40`..`0x2D440`; sentinel and trailer constant on every
  record. `name_offset` points at or within a few bytes of NUL-terminated name
  strings (exact start for 198/2,617; e.g. record@0x1C7E0 name_offset=241454 →
  `"Stub_1472"` at file `0x3AF2E`).
- Unknown: exact name_offset → string relation; field_b/field_c/field_d/pad_byte
  semantics; no name→WAD binding resolved, so G10 stays open (engine ground
  truth or a second WadGraph sample needed; **no writer possible from these
  bytes**).
- Docs: E-045 in docs/EVIDENCE.md; new docs/FORMATS.md §7.5; docs/BACKLOG.md
  G10 row updated.
- Next: pick another resolved-dependency slice (G9 entry→resource binding on a
  larger WAD such as `R_HADES.WAD`, or H1/H2/H3 research); F1/F4 remain blocked
  on engine ground truth.

---

## 2026-10-18 — T6: CI workflow runs the unit tests on push (issue #12)

- Did: added `.github/workflows/test.yml` (Python 3.13, ubuntu-latest) that runs
  `python -m unittest discover -s tests -t tests` on push and pull_request to
  `main`; marked BACKLOG.md T6 done. Committed as 18fb0b2 and pushed to origin
  main; commented and closed issue #12.
- Found: no code change was needed to make CI pass — the suite was already green
  (221 tests, stdlib-only, no game data, no engine ground truth). CI now gates
  every push. Phase 1's format critical path (F1 MOD payload, F4 MOT keyframes)
  stays blocked on engine ground truth and is deliberately not re-spun.
- Next: when engine ground truth becomes available, pick F1 or F4; otherwise
  take another resolved-dependency slice (F2/F3/F6 payloads, F9 move set, G9/G10
  WAD directory).

---

## 2026-10-18 — T2 bounded slice: DDS → PNG conversion for uncompressed BGRA32 (issue #9)

- Did: implemented `tools/dmc3/dds.py` (`dds_to_png`) converting uncompressed
  BGRA32 DDS payloads to PNG with alpha preserved byte-for-byte (BGRA → RGBA),
  exported it from `dmc3/__init__.py`, and added `tests/test_dds.py` (8 tests)
  that structurally verify PNG output (signature, IHDR RGBA 8-bit, per-chunk
  CRC32, zlib-decompressed IDAT rows equal input exactly, IEND terminator) plus
  exact pixel/alpha equality. Compressed DXT1/DXT3/DXT5 raises a documented
  `DdsError`. Full suite: **240 tests, all green**.
- Found (E-046): the real `i001_90.tm2` embedded DDS is DXT3 256×256
  (compressed) → hits the documented unsupported path; all three local TM2s are
  DXT3 (E-042), so no local texture is converted yet. A DXT decoder or an
  external tool (texconv) is needed for the compressed path; recorded [UNKNOWN]
  rather than guessed.
- Docs: `docs/BACKLOG.md` T2 row, `docs/FORMATS.md` §4.2, `docs/EVIDENCE.md`
  E-046.
- Next: comment on issue #9 (left open — compressed path unresolved).

## 2026-10-18 — T2: DXT1/DXT3/DXT5 decoded in the DDS -> PNG pipeline

- Did: implemented block-level S3TC decoding in `tools/dmc3/dds.py`
  (DXT1/BC1, DXT3/BC2 explicit alpha bitmap, DXT5/BC3 alpha interpolation,
  integer floor arithmetic per channel, all documented) and extended
  `dds_to_png` so compressed payloads decode to RGBA PNG with alpha
  preserved; DX10 extended headers and other fourCCs keep raising a
  documented `DdsError`. Replaced the "compressed raises DdsError" tests
  with 9 new exact-pixel tests on synthetic fixtures (endpoint selection,
  DXT1 interpolation, c0<=c1 transparent black, 2-bit/3-bit index LSB
  ordering, DXT3 alpha x17, DXT5 ramps both endpoint orderings) plus a
  top-mip smoke test on the real-shape fixture; fixed `real_tm2_dds()` to
  a proper 128-byte header. Full suite: **249 tests, all green**.
  Committed as 0bc5c6a and pushed to origin main.
- Found (**E-047**, read-only real bytes from
  `G:\Games\Devil May Cry HD Collection\data\dmc3\GData.afs\i001_90.tm2`):
  embedded DDS at file 0x70, fourCC `DXT3`, 256×256, pitch 65,536, payload
  0xF0..EOF = exactly 65,536 bytes = one 256×256 DXT3 image; payload block 0
  is `00*12 AA AA AA AA` (all-alpha-zero, endpoints 0x0000, all indices 2).
  End-to-end decode yields a valid 256×256 RGBA PNG; block 0's texels are all
  (0,0,0,0) and row-0 texels 8–15 carry alpha 17, 17, 51, 51, 68, 85, 85, 119
  matching blocks 2–3's alpha bytes (tool output, not engine ground truth).
  Also observed: reserved1 contains a "GIMP-DDS" marker (the installed file
  was re-saved by GIMP).
- Docs: `docs/FORMATS.md` §4.2 marked [VERIFIED] for DXT1/DXT3/DXT5 with the
  block formats recorded; `docs/EVIDENCE.md` gains E-047 and notes E-046 as
  superseded; `docs/BACKLOG.md` T2 marked done.
- Next: comment on and close issue #9 (done); the format critical path
  (F1/F4) remains blocked on engine ground truth and is deliberately not
  re-spun.

---

## 2026-10-18 — F6 PNST raw-block header decoded; F2 +0x48 correction recorded

- Did: bounded slice on issue #6 (F6 PNST weapon container). Read raw bytes from both
  weapon archives (plwp_vergilsword.pac, plwp_newvergilsword.pac) under G:\... (read
  only). Slots 0 and 3 of each file are identical 36,864-byte raw blocks opening with
  u32 field_a = 1, u32 field_b = 17 (0x11), then a zero-filled run (first non-zero byte
  at body+2049) and a structured tail. Added PnstRawBlock / parse_pnst_raw_block /
  maybe_pnst_raw_block to tools/dmc3/pnst.py, a pnst_raw_block() fixture, and
  TestPnstRawBlock (5 tests) on synthetic fixtures. Full suite: 254 tests, all green.
  Committed a3c8a31 and pushed to origin main.
- Found: E-048 records the raw-block header and tail observations (file offsets 0x30 and
  0xB3A0 in both archives; slot 9's separate u16 stream at 0x88F20..0x890B0 in the
  overlay archive). Also recorded E-049: re-reading the real SHW bytes falsifies the
  "slots 24/26 byte-identical" claim (headers match, payloads diverge at body+0x11) and
  shows +0x48 is not a uniform table across the four chunks — F2's texture-binding lead
  stays [UNKNOWN] and is not retried from bytes alone.
- Docs: E-048/E-049 in docs/EVIDENCE.md; docs/FORMATS.md sec.2 (raw-block header
  [PARTIAL]) and sec.5 (F2 correction); docs/BACKLOG.md F6/F2 rows updated.
- Commented issue #6 with findings; issue left open (tail semantics need engine ground
  truth). Issue #9 (T2) was already closed; comment posted summarizing completion.
- Next: the Phase 1 format critical path (F1 MOD payload, F4 MOT keyframe u16[1..3])
  stays blocked on engine ground truth and is not re-spun. Pick another resolved-dependency
  slice (F3 remaining untagged slots, G9 entry->resource binding on a larger WAD, or
  H1/H2/H3 research) if the loop continues.

---

## 2026-10-18 — F1 and F4 recorded as dead ends needing engine ground truth

- Did: reviewed the full backlog, open issues, and all evidence ledger entries.
  Confirmed that every Phase 1 format critical-path item (F1 MOD mesh payload,
  F4 MOT keyframe encoding) has had multiple bounded slices with no new result
  possible from bytes alone. All remaining unknowns in F1/F4/F2/F3/F5/F6/F7/F8
  require engine ground truth (disassembly or in-game capture), which this
  project cannot produce by rule (read-only installs, no DLL injectors, no
  script plugins). G9/G10 WAD directory binding and name→WAD binding are also
  unknown and block the WAD writer / boss test loop.
- Found:
  - **E-050** (new): F1 dead end — `MOD ` header (E-030) and body prefix (E-031)
    fully decoded, but payload body beyond body +0x60 (vertices, indices,
    normals, UVs, skin weights) needs engine ground truth. Prior-art FLVER
    cross-check (E-014/E-015, T7b) is itself undecoded beyond GX blocks.
  - **E-051** (new): F4 dead end — record layer (E-019), frame-time field
    (E-026), preamble/keyframe split (E-028/E-029), and u16[1..3] census
    (E-028) all decoded, but channel assignment/scale/zero point and the
    record→bone mapping need engine ground truth.
- Docs: added E-050 and E-051 to docs/EVIDENCE.md as recorded dead ends;
  commented on issues #1 (F1) and #2 (F4) with findings and what remains;
  both issues left open.
- Tests: full suite **254 tests, all green**; no code changes this iteration.
- Next: nothing available from bytes alone. When engine ground truth becomes
  available, F1 and F4 are the unblocked critical-path items. Otherwise, pick
  any resolved-dependency research item (H1/H2/H3) or document a new dead end.

---

## 2026-10-18 — F3 bounded slice: pl021.pac slot 5 segment stream decoded from real bytes

- Did: bounded slice on F3 (issue #4). Read real bytes from pl021.pac slot 5
  (`G:\Games\Devil May Cry HD Collection\data\dmc3\GData.afs\pl021.pac`) at
  file offset 0x06B6E0, span 0x4B30; generalized the u16 segment splitter in
  `tools/dmc3/raw.py` (`_split_u16_segments`, now shared by `Slot21Table`
  and the new `Slot5Table`); added `raw_chunk_slot5()` fixture and
  `TestSlot5Table` (4 tests) in `tests/test_raw.py`; exported
  `SLOT5_SEGMENT_COUNT`/`Slot5Table`/`maybe_slot5_table` from `dmc3/__init__`.
  Full suite: **258 tests, all green**. Committed as a99504d, pushed to
  origin main; commented issue #4 (left open).
- Found (E-052): slot 5 is a little-endian u16 stream split into 215
  segments by 214 `0xFFFF` separators; segment 0 verbatim `(6, 0x37D0)`;
  segment sizes open `2, 1, 34, 60, 5, 13…`; tail segments up to 378 u16s;
  `0x7FFF` occurs inside segments as data (not a delimiter), exactly as in
  slot 21 (E-043). Segment semantics [UNKNOWN].
- Docs: E-052 in docs/EVIDENCE.md; docs/FORMATS.md §1.3 and docs/BACKLOG.md
  F3 row updated (evidence E-008/E-033/E-037/E-043/E-052).
- Next: F3 slots 6/7/9/11/22 remain undecoded; every Phase 1 format
  critical-path item (F1/F4/F2/F5/F6/F8) stays blocked on engine ground
  truth and is deliberately not re-spun.

---

## 2026-10-18 — G9/G10: eboot ground-truth scanner shipped (E-056)

- Did: codified E-053's ad-hoc method as `tools/gow3/eboot.py` — 64-bit ELF
  program-header parsing, file↔vaddr mapping, string lookup, and a RIP-relative
  `lea`/`mov` reference scanner — with `tests/test_gow3_eboot.py` (17 tests on a
  synthetic ELF, no game data committed). Validated read-only against
  `C:\Users\GigelCastel\Desktop\gow3\gow3-windows\out\eboot.elf` (4,597,471 B).
  Full suite: **295 tests, all green**.
- Found (**E-056**): exactly one executable `PT_LOAD` (`p_offset 0x4000`,
  `p_vaddr 0`, `p_filesz 0x3BD518`, `R|X`), so inside the code segment
  `vaddr = file_offset − 0x4000` — *not* `vaddr == file_offset`; the string
  tables sit in a read-only load at `p_offset 0x3C4000` / `vaddr 0x3C0000`.
  Scanning with the correct RIP-relative form (`(modrm & 0xC7) == 0x05`) finds
  26,706 references and reproduces E-053 exactly: **94** refs to the 49
  loader-string vaddrs — 9 `hfsm` (same cluster `0x10BB24…0x10D2B4`),
  `ms::tMove` at `0xED578`, 3 `attachment::`.
- **Correction to E-053:** the operand pattern is not `modrm == 0x05`. The first
  `WAD_` reference E-053 listed, `0x100D49`, is `48 8d 3d 06 04 25 00` =
  `lea rdi, [rip + 0x250406]` (ModRM `0x3D`), targeting the `WAD_` string at
  `0x351156`; a literal `modrm == 0x05` scan misses it. Also corrected the
  `eboot.elf` path and the pattern in `scripts/agent-prompt.md`.
- Docs: E-056 in `docs/EVIDENCE.md` plus a correction note at the end of E-053;
  `docs/FORMATS.md` §7.6; `docs/GOW3.md` Method → "Engine ground truth";
  `docs/BACKLOG.md` G9/G10 rows; `scripts/agent-prompt.md`.
- Next: read the code the `WAD_` / `hfsm` references point at to recover the
  **numeric record opcodes** and the directory→bulk binding (G9/G10) — the loader
  is now locatable. F1/F4 stay blocked on DMC3-side engine ground truth.

---

## 2026-10-18 — F9/G9 bounded slice: GoW3R animation clip header decoded

- Did: continued the GoW3R "moves" work from E-058 (clip directory). Read real
  bytes (read-only) from `R_HADES.WAD` and `R_HERCULES.WAD` under
  `C:\Users\GigelCastel\Desktop\gow3\CUSA01715\EXEC\WAD\PS4_LE\`; implemented
  `ClipHeader` / `parse_clip_header()` and the `CLIP_*` offset constants in
  `tools/gow3/anim.py`, gave `Clip` a header-derived `size`, and added
  `TestClipHeader` (4 tests) on a realistic synthetic clip record. Full suite:
  **332 tests, all green**.
- Found (**E-059**): the ANM clip record has a **fixed header**.
  - The name is a **fixed 0x38-byte field**: the u32 at `+0x38` is the clip size
    in all 123 clips (77 Hades + 46 Hercules), whatever the name's length.
  - `+0x3C` = 0 (123/123); `+0x7C`/`+0x90`/`+0xA4` equal `+0x38` (123/123);
    `+0x6C` = 1/30 (114) or 1/15 (9); `+0xA8` = 1/60 (123/123).
  - **E-058 correction**: the directory *span* over-estimates the final clip
    (83,651,932 for `csHadesFlickL`); the header size (34,304) is the true bound.
    `Clip.size` now carries it and `Clip.end` uses it.
  - The rest of the header is `0xCD`/`0xCC`-filled (MSVC uninitialized-memory
    patterns) with pointer-like u32s; no field meaning is claimed beyond the name
    and size, and the clip's internal encoding stays [UNKNOWN].
- Docs: `docs/EVIDENCE.md` E-059; `docs/FORMATS.md` §7.7; `docs/BACKLOG.md`
  F9/G9 rows updated. No game data committed; all fixtures synthetic.
- Next: the clip's internal encoding (channels/keyframes/root motion) is the
  remaining "moves" gap and is decodable from the file and `eboot.bin`; the
  `+0x7C`/`+0x90`/`+0xA4` structural analogy (three tracks + a 60 Hz track) is a
  hypothesis to test. F1/F4 remain blocked on DMC3-side engine ground truth.

---

## 2026-10-18 — F9/G9 bounded slice: clip frame count and loop flag decoded (E-060)

- Did: continued E-059's "what is the rest of the clip header?" question on the
  GoW3R side, which is where the "moves" ground truth lives. Censused **every
  u32-aligned offset in `+0x00..+0x123` of all 123 clips** (77 `R_HADES.WAD` +
  46 `R_HERCULES.WAD`, read-only) instead of the four chunks E-059 sampled.
  Extended `tools/gow3/anim.py` — `CLIP_RATE_COPY_OFFSETS`,
  `CLIP_RATE_RECIPROCAL_OFFSET`, `CLIP_LOOP_OFFSET`, `CLIP_FRAME_COUNT_OFFSET`,
  `CLIP_SAMPLE_RATE_OFFSET`, `CLIP_SIZE_OFFSETS`, `CLIP_FRAME_RATE_OFFSETS`,
  `float32()`, `expected_sample_rate()`, and `ClipHeader` now carries `frames`,
  `loop_flag`, `sample_rate`, `frame_count_rate`, `rate_copies` plus the four
  relations as `*_ok` properties and `invariants()`. `CLIP_HEADER_MIN` → `0x118`.
  The E-059 synthetic fixture grew to `0x180` bytes; `TestClipHeaderRelations`
  (9 tests) exercises the relations on synthetic bytes. Full suite: **342 tests,
  all green**. Committed and pushed; commented issues #24 and #36.
- Found (**E-060**), all four relations **123/123 clips with no exception**:
  - the clip size sits at **exactly four** offsets (`+0x38`, `+0x7C`, `+0x90`,
    `+0xA4`) and the frame rate at **exactly four** (`+0x6C`, `+0x80`, `+0x94`,
    `+0x110`); no fifth offset in `+0x00..+0x123` carries either value. E-059's
    "three copies" are one field written four times.
  - `f32@+0x10C × f32@+0x6C == 1`, worst deviation **5.215e-08** (binary32
    rounding only) — the reciprocal is stored explicitly.
  - **`f32@+0x114 == float32(1 / (u16@+0xF6 − 1))`, exact binary32 equality, on
    123/123.** So `+0xF6` is [INFERRED] the clip's **frame count** (44 values,
    15..686; `angryKratosWalk` 41, `csHadesIntro` 141, `csHadesKnifeEnter` 396)
    and `+0x114` the sample spacing of a curve normalised to `[0,1]`.
  - `u16@+0xF4 == 1` on **11/123** clips, and all eleven are `*Idle*` loops
    ([INFERRED] loop flag). Recorded honestly: `hadesKnifeIdleB` and
    `hadesKnifeIdleF` are `Idle`-named and hold `0`, so the flag is **not**
    "the name says Idle" and the inference is unproven.
  - Everything else in `+0x00..+0x123` is constant on all 123 clips, `0xCD`/`0xCC`
    fill included; the only per-clip-varying u32s in that range are the four size
    slots, the four rate slots, the reciprocal, `+0xF4`, `+0x114`; from `+0x124`
    the u32s are pointer-like and per-clip.
- Docs: `docs/EVIDENCE.md` E-060; `docs/FORMATS.md` §7.7 rewritten with the
  relation table and `[VERIFIED]`/`[INFERRED]` markings; `docs/BACKLOG.md` F9/G9
  rows updated.
- Next: the clip's **internal** encoding (channels, keyframes, root motion) is
  still the F9 "moves" gap; `+0x124`-onward pointer-like data is the lead. F1/F4
  remain blocked on DMC3-side engine ground truth and are not re-spun.

---

## 2026-10-18 — F9/G9 bounded slice: clip descriptor tail and data-section start (E-061)

- Did: continued the GoW3R clip work after E-060 by censusing the region *past*
  E-060's boundary (`+0x120..+0x15B`) on all 123 clips of `R_HADES.WAD` (77) and
  `R_HERCULES.WAD` (46), read-only. Added `ClipDescriptorTail`,
  `parse_clip_descriptor_tail()` / `maybe_clip_descriptor_tail()` and the
  `CLIP_TAIL_*` / `CLIP_DATA_*` constants to `tools/gow3/anim.py`; extended the
  synthetic `anim_wad` fixture and added `TestClipDescriptorTail` (9 tests).
  Full suite: **351 tests, all green** (342 baseline + 9). Validated read-only
  against both real archives: all 123 clips satisfy all four invariants.
- Found (**E-061**):
  - The fixed descriptor ends at `+0x158`, not `+0x123`: `+0x128` = `0x00800000`,
    `+0x130` = `0x00010001`, `+0x138` = `0x037B0000` and `+0x14C..+0x158` =
    `0xFFFFFFFF` are constant on 123/123 clips.
  - The **seven** per-clip u32s are `+0x124`, `+0x12C`, `+0x134`, `+0x13C`,
    `+0x140`, `+0x144`, `+0x148`. Five of them are **16-byte aligned and
    in-file on 123/123** (`+0x124/+0x12C/+0x134/+0x13C/+0x144`); the other two
    are small and unaligned.
  - **Correction to E-060:** "from `+0x124` onward the u32s are pointer-like and
    per-clip" holds only for those seven fields, not for the interleaved
    constants or the sentinel run.
  - The per-clip data section begins at **`+0x15C`**, opening with the u16 marker
    pair `0x0015` / `0x000C` on 123/123 clips.
  - **[INFERRED]** the five aligned fields are file offsets into a *shared* pool:
    `+0x12C` values are reused between clips (18/77 in `R_HADES.WAD`, in coherent
    groups — `hadesKnifeAttLhigh/Llow/RHigh` share `0x14F0`, both taunts share
    `0x1350`), and one Hades pair's `+0x124` values differ by exactly 16. Pointer
    semantics remain unproven, so the reader exposes values plus `aligned_ok`
    only — no field meaning is asserted.
- Docs: E-061 in `docs/EVIDENCE.md`; `docs/FORMATS.md` §7.7 gains the descriptor
  tail ([PARTIAL]/[INFERRED] marked); `docs/BACKLOG.md` F9/G9 rows updated.
- Next: the clip's internal encoding beyond `+0x15C` is the remaining F9 "moves"
  gap and is decodable from `eboot.bin`/`eboot.elf`; the `+0x15C` marker pair is
  the lead. F1/F4 remain blocked on DMC3-side engine ground truth and are not
  re-spun.
- Note (housekeeping, not fixed this iteration): `tools/dmc3/raw.py`'s
  `Slot9Table` cites "evidence E-053", but the ledger's E-053 is the eboot entry
  — the pl021.pac slot-9 f32 array still has **no ledger entry**. Next free ID is
  **E-062**; a future slice should re-read slot 9 and record it, then correct the
  stale citation.

---

## 2026-10-18 — F3 boundable housekeeping: slot-9 f32 array recorded as E-062; stale E-053 citation fixed

- Did: closed the journal's own open housekeeping note. Re-read real bytes from
  `pl021.pac` slot 9 (read-only, `G:\Games\Devil May Cry HD Collection\data\dmc3\GData.afs`)
  and recorded the missing ledger entry **E-062**. Corrected the stale "evidence
  E-053" citations in `tools/dmc3/raw.py` (twice) and `tests/fixtures.py` to
  E-062. Added the previously absent `TestSlot9Table` (4 tests) in
  `tests/test_raw.py` on the existing synthetic `raw_chunk_slot9()` fixture;
  added the slot-9 spec to `docs/FORMATS.md` §1.3 and the E-062 evidence to
  `docs/BACKLOG.md` F3. Full suite: **355 tests, all green** (351 baseline + 4).
- Found (**E-062**): `pl021.pac` slot 9 is an untagged chunk at **file offset
  0x077B50**, span **896 bytes = 224 little-endian f32s** with no header, no count
  field and no separator. Head verbatim: `10.4, -1.2, 10.0, 12.0, -1.2, 15.0,
  10.4, -0.8, 6.4, 12.4, -0.8, 12.0, 23.5, -1.2, 0.3, 40.0, 13.0, -1.5, 25.0,
  200.0, 500.0, 150.0, 150.0, 500.0`. Census: 206 non-zero (indices 0..210) + 18
  trailing zeros (211..223), 83 distinct values, min `-790.0` (index 202), max
  `9000.0` (index 138); most common `0.0` (18), `500.0` (15), `150.0` (10),
  `60.0` (10). Not all values are integers, so the array is not an obvious
  index/offset table; what it indexes remains [UNKNOWN].
- **Citation correction recorded:** the earlier `Slot9Table` docstrings pointed
  at E-053, which is the `eboot.bin` reference scan — wrong ID for this data.
  E-062 is now the ledger's home for the slot-9 array, and the code/fixtures cite
  it.
- No parser logic changed (the parse was already correct; the ledger entry and
  the tests were missing).
- Docs: E-062 in docs/EVIDENCE.md; §1.3 slot-9 bullet in docs/FORMATS.md;
  BACKLOG.md F3 row now lists E-008/E-033/E-037/E-043/E-052/E-062.
- Next: F3 slots 6/7/11/22 remain undecoded; the Phase 1 format critical path
  (F1/F4/F2/F5/F6/F8) stays blocked on engine ground truth and is not re-spun.

---

## 2026-10-18 — G9/G10 bounded slice: the `WAD_` references lead to name registration, not the directory dispatcher (E-063)

- Did: followed the standing prompt's engine-ground-truth route — use
  `tools/gow3/eboot.py` to locate the WAD loader from the `.wad` / `WAD_` /
  `DEPENDENCY` string references, then read the numeric constants. Added a
  **limited instruction decoder** to `tools/gow3/eboot.py`
  (`DecodedInstruction`, `_decode_instruction`, `ElfImage.reference_context`,
  `ElfImage.string_reference_contexts`) covering exactly the forms a string
  reference site uses (RIP-relative `lea`/`mov`, `mov r32, imm32` /
  `mov r64, imm64`, `call rel32`); it stops at the first unrecognised byte.
  Exported `EbootDecodedInstruction` from `gow3/__init__`. 8 new tests in
  `tests/test_gow3_eboot.py`. Full suite: **363 tests, all green**.
- Found (**E-063**, read-only from `out/eboot.elf`; cross-checked with capstone
  5.0.9, which is a local recon tool, **not** a repo dependency):
  - **The prompt's route is partially disproven.** `.wad` (`0x35D7C7`) and
    `DEPENDENCY` (`0x330686`) each occur once but have **zero** RIP-relative
    references. Only `WAD_` (81 refs) and `hfsm` (9 refs) are reachable this way.
  - The `WAD_` sites load the string with `lea` and hand it to **name
    registration/lookup** helpers — `0x1F7200` (25 sites), `0x1AAC30` (15),
    `0x1AAC80` (7), `0x1011A0`, `0x2E9D70`, `0x1AACF0`, … — none of which
    references the record opcodes (`1`, `2`, `3`, `0x12`, `0x15`,
    `0x80000000|n`). The `WAD_` route reaches object/asset registration, not the
    directory dispatcher.
  - The one site that passes an explicit length is `0x10FCB`:
    `48 8d 35 c0 f5 2d 00` (`lea rsi,[rip+0x2DF5C0]` → `0x2F0592`) then
    `ba 04 00 00 00` (`mov edx, 4`). So the banner is matched by a **4-byte
    `"WAD_"` prefix comparison**, not whole-string equality.
  - **False lead recorded:** the 42 `and eax, 0x80000000` sites in
    `0x40187..0x43C5B` are a float sign-bit/reciprocal routine (paired with
    `or eax, 0x3F800000` + `vsqrtss`), not `0x80000000|class` marker handling.
- Unknown (recorded, not guessed): the directory-record dispatcher and its
  numeric opcodes; the entry → resource binding (E-044) and the `WadGraph`
  name → WAD binding (E-045). The scanner sees only RIP-relative `lea`/`mov`, so
  a string moved as an immediate or through an offset table stays invisible.
- Docs: E-063 in `docs/EVIDENCE.md`; `docs/FORMATS.md` §7.6 updated;
  `docs/BACKLOG.md` G9/G10 rows updated; `tools/gow3/eboot.py` module docstring.
- Next: the directory dispatcher is not reachable by string reference under the
  current scanner; the remaining G9/G10 route is to find the record `type`
  dispatch structurally (e.g. a jump table indexed by the numeric opcode) or to
  decode the `DC_` id `0x10` table's entry→resource binding on a second WAD
  (E-044). F1/F4 stay blocked on DMC3-side engine ground truth and are not
  re-spun; F3 slots 6/7/11/22 and the clip internal encoding remain open.

## 2026-10-18 — F9/G9 bounded slice: the clip data section's typed record preamble (E-064)

- Did: continued the GoW3R "moves" work that E-061 stopped at `+0x15C`. Read
  real bytes (read-only) from `R_HADES.WAD` (77 clips) and `R_HERCULES.WAD`
  (46) under `C:\Users\GigelCastel\Desktop\gow3\CUSA01715\EXEC\WAD\PS4_LE\`;
  censused the opening records of the per-clip data section on all 123 clips.
  Added `ClipDataRecord`, `ClipDataPreamble`,
  `parse_clip_data_preamble()` / `maybe_clip_data_preamble()` and the
  `CLIP_DATA_*` constants to `tools/gow3/anim.py`; extended the synthetic
  `anim_wad` fixture to write a realistic preamble and added
  `TestClipDataPreamble` (9 tests). Full suite: **372 tests, all green**
  (363 baseline + 9).
- Found (**E-064**): the data section is a stream of tagged u16 records; every
  record carries the constant `0x000C` in its third slot. Layout, 123/123:
  - `lead` records of 4 u16 (`tag, arg, 0x000C, value`) — 4 records normally,
    5 when a `0x17` record is present (8 clips); tags `0x15,0x16,0x18,0x0B`
    (or `0x15,0x16,0x17,0x18,0x0B`);
  - two zero u16, then a u16 `count` (15..272, 81 distinct; not the frame
    count — `csHadesIntro` is 141 frames but `count` 72);
  - `tail` records of 5 u16 (`tag, arg, 0x000C, value, extra`) — 4, 5 or 7 of
    them; tags from `{0x0B,0x0F,0x10,0x1B,0x1C,0x1D,0x1E}`, with `0x0F` and
    `0x10` once each per clip;
  - a zero u16 terminator, then `0xCC` fill and further tables.
  - **E-061 harmonised:** its "`+0x15C` marker pair `0x0015`/`0x000C`" is simply
    the first record's tag and its discriminator; there are no separate markers.
  - The `0x0B` lead record's `arg` (`0x8000|n`) is repeated as the first tail
    record's `arg`; both `0x8000|n` ids may be class/type ids as in the WAD
    directory, [INFERRED] only.
- Unknown (recorded, not guessed): `count` semantics; the meaning of every tag,
  `arg`, `value`, `extra`; and the keyframe data that follows the preamble — the
  remaining F9 "moves" gap. Engine ground truth (`eboot.bin`/`eboot.elf`) is the
  route; the parser asserts no field meaning.
- Docs: E-064 in `docs/EVIDENCE.md`; `docs/FORMATS.md` §7.7 gains the
  "Data-section record preamble" subsection and the corrected `+0x15C`/`+0x160`
  annotation; `docs/BACKLOG.md` F9/G9 rows updated. No game data committed.
- Next: the keyframe/curve encoding after the preamble is the remaining F9 gap
  (decodable from `eboot.elf`); otherwise F3 slots 6/7/11/22 and the G9/G10
  directory binding. F1/F4 remain blocked on DMC3-side engine ground truth and
  are not re-spun.

---

## 2026-10-18 — F9/G9 bounded slice: the clip preamble is a directory of sub-block offsets (E-065)

- Did: followed the E-064 lead ("every field meaning [UNKNOWN]") and tested
  whether the record `value` fields are offsets. Read real bytes (read-only) from
  `R_HADES.WAD` (77 clips) and `R_HERCULES.WAD` (46) under
  `C:\Users\GigelCastel\Desktop\gow3\CUSA01715\EXEC\WAD\PS4_LE\` and censused the
  last u16 of every lead/tail record on all 123 clips. Added `values`,
  `word_count`, `byte_length`, `increasing_ok`, `aligned_ok`, `first_offset_ok`,
  `data_targets()` and the extended `invariants()` to `ClipDataPreamble` in
  `tools/gow3/anim.py`; added the `CLIP_DATA_ALIGNMENT` /
  `CLIP_DATA_*_TERMINATOR_WORDS` / `CLIP_DATA_COUNT_WORDS` constants and 7 tests
  (`TestClipDataOffsets`). Full suite: **379 tests, all green** (372 baseline + 7).
- Found (**E-065**), 123/123 clips with no exception:
  - the record values **strictly increase** in file order and every one is a
    **multiple of 16**;
  - `values[0] == round_up(preamble byte length, 16)`, where the length is
    `2·(4·lead + 2 + 1 + 5·tail + 1)` — so the first sub-block begins immediately
    after the preamble (`angryKratosWalk`: 90 B used → first offset 96 = 0x60);
  - every `data_start + value` is inside the clip's own `size` (123/123);
  - worked examples on every shape: 4/5 lead, 4/5/7 tail, e.g.
    `csHadesIntroStruggle` (5 lead, 98 B → 0x70) and `csHadesIntroWin`
    (7 tail, 118 B → 0x80).
- **Inference:** each record's last u16 is an **offset from the clip's
  data-section start** (`+0x15C`), so the preamble is a directory of 16-byte-aligned
  sub-blocks. The base is fixed by the alignment rule — a clip-relative base would
  put `values[0]` inside the fixed header. E-064's `value = [UNKNOWN]` is
  superseded for the offset relation.
- Unknown (recorded, not guessed): the content of each sub-block and the meaning
  of `count`, every tag, `arg` and `extra`; the keyframe/curve encoding inside the
  sub-blocks remains the F9 gap. No pointer/type claim beyond "offset".
- Docs: E-065 in `docs/EVIDENCE.md`; `docs/FORMATS.md` §7.7 gains a
  "Record `value` fields are sub-block offsets — [VERIFIED]" subsection;
  `docs/BACKLOG.md` F9/G9 rows updated. No game data committed.
- Next: the sub-block contents (keyframe/curve encoding) are now addressable and
  are the remaining F9 gap, decodable from `eboot.elf`; otherwise F3 slots
  6/7/11/22 and the G9/G10 directory binding. F1/F4 remain blocked on DMC3-side
  engine ground truth and are not re-spun.

---

## 2026-10-18 — F9/G9 bounded slice: the record offsets name typed sub-blocks, one nesting a preamble (E-066)

- Did: followed E-065's open question ("sub-block contents [UNKNOWN]") and read
  the sub-blocks the preamble names, on all 123 clips of `R_HADES.WAD` (77) and
  `R_HERCULES.WAD` (46), read-only from
  `C:\Users\GigelCastel\Desktop\gow3\CUSA01715\EXEC\WAD\PS4_LE\`. Censused each
  sub-block's 8-byte head by tag and scanned the tag-`0x10` block for a nested
  E-064 preamble. Added `tag16_prefix_length()`, `find_nested_preamble()`,
  `ClipSubBlock`, `ClipSubBlocks` and `parse_clip_sub_blocks()` plus the
  `CLIP_DATA_TAG16` / `CLIP_DATA_TAG16_PREFIX_WORDS` / `CLIP_DATA_TAG16_STEP` /
  `CLIP_DATA_TAG10` / `CLIP_DATA_NESTED_MIN_RECORDS` constants to
  `tools/gow3/anim.py`; a purpose-built synthetic fixture and 10 tests
  (`TestClipSubBlocks`) in `tests/test_gow3_anim.py`. Full suite: **389 tests,
  all green** (379 baseline + 10).
- Found (**E-066**):
  - Each sub-block is addressed by exactly one preamble record, so the record's
    **tag types the block**. The tag census separates them cleanly; the
    tag-`0x16` sub-block has a **single** 8-byte head `00 00 30 00 60 00 90 00`
    on 123/123 clips (every other tag has 8..130 distinct heads).
  - The tag-`0x16` sub-block opens with exactly **128 u16 `0x30 * k`**
    (`k = 0..127`, a 256-byte table spanning `0x1800`) on 123/123, the run
    stopping at index 128 every time.
  - The tag-`0x10` sub-block (the last, running to the clip's `end`, and the
    largest at 4,676..244,068 B) contains a **nested data-section preamble** of
    E-064's shape at a 16-byte-aligned offset 64..208 B in, on **122/123** clips.
    Nested shapes observed: (5,5)×73, (5,7)×15, (4,5)×15, (6,5)×7, (5,4)×5,
    (4,4)×5, (6,7), (4,7). Worked example `angryKratosWalk` nested at `+0x90`.
  - **Exception recorded:** `attCestusCrush` (`R_HERCULES.WAD`, offset `0x76C34`)
    has no qualifying nested preamble — an observation, not explained.
- **Inference (marked):** the clip data section is **recursive** — E-065's offsets
  are a directory of typed sub-blocks and the tag-`0x10` block nests the same
  structure, so the leaf keyframe/curve encoding is reached by recursing into
  these blocks rather than read off an opaque stream. Tag *meaning* stays
  [UNKNOWN]; the tag→block typing is structural.
- Validated read-only against both real archives: **123/123** `tag16_prefix_ok`,
  **122/123** `nested_ok`. No game data committed (all fixtures synthetic).
- Docs: E-066 in `docs/EVIDENCE.md`; `docs/FORMATS.md` §7.7 gains a "typed
  sub-blocks — [PARTIAL] (E-066)" subsection; `docs/BACKLOG.md` F9/G9 rows
  updated. Committed and pushed; commented issues #24 and #36.
- Next: recurse into the sub-blocks — the tag-`0x16` table's continuation past
  index 128 and the nested preamble's own sub-blocks are the remaining F9 gap;
  otherwise F3 slots 6/7/11/22 and the G9/G10 directory binding. F1/F4 remain
  blocked on DMC3-side engine ground truth and are not re-spun.

---

## 2026-10-18 — F9/G9 bounded slice: the clip data-section recursion is exactly two levels (E-067)

- Did: followed E-066's own Next ("recurse into the sub-blocks — the tag-`0x16`
  table's continuation past index 128 and the nested preamble's own sub-blocks").
  Read real bytes (read-only) from `R_HADES.WAD` (77 clips) and `R_HERCULES.WAD`
  (46) under `C:\Users\GigelCastel\Desktop\gow3\CUSA01715\EXEC\WAD\PS4_LE\` and
  walked the nested structure with one reader. Generalised the sub-block splitter
  in `tools/gow3/anim.py` — new `parse_data_section(data, offset, end)` (the
  general form of `parse_clip_sub_blocks`), `ClipSubBlocks.end` and
  `ClipSubBlocks.nested_data_section()`, `clip_data_sections()`, and
  `tag16_offset_table()` / `ClipSubBlock.tag16_offset_table`; new constants
  `CLIP_DATA_NESTED_LEAD_TAG` = 0x19, `CLIP_DATA_NESTED_LEAD_TAGS`,
  `CLIP_DATA_NESTED_TAIL_TAGS`, `CLIP_DATA_MAX_DEPTH`,
  `CLIP_DATA_SECOND_TABLE_FIRST` = 0x20. 9 new tests (`TestClipDataRecursion`)
  on a synthetic two-level clip. Full suite: **398 tests, all green**.
- Found (**E-067**):
  - **The data-section recursion is exactly two levels.** 122/123 clips have a
    two-long chain of preambles; none has three; `attCestusCrush` has one. The
    level-2 preamble keeps every E-065 offset invariant on 122/122
    (increasing, 16-byte aligned, `values[0] == round_up(length, 16)`).
  - **The nested level adds lead tag `0x19`** (`101/122` clips; shapes
    `0x15 0x16 0x18 0x19 0x0B` and `0x15 0x16 0x17 0x18 0x19 0x0B`). `0x19` is
    never an outer lead tag, so the two levels are not identical.
  - **The level-2 tag-`0x16` table is 122/123 entries, never 128.** E-066's
    "128 on 123/123" is the outer level only; the nested block opens with 123
    entries (114 clips) or 122 (8).
  - **Every tag-`0x16` block continues past the `0x30 * k` table with a second
    offset table**: u16 values strictly increasing, all multiples of 16, first
    value `0x20` in every outer block (123/123). It reaches `0x1800`
    (`0x30 * 128`) or `0x3C00` before constant fill; length/meaning [UNKNOWN].
- Docs: E-067 in `docs/EVIDENCE.md`; `docs/FORMATS.md` §7.7 gains "the recursion
  is exactly two levels — [VERIFIED] (E-067)"; `docs/BACKLOG.md` F9/G9 rows
  updated (evidence cells now list E-067). No game data committed.
- Next: the leaf keyframe/curve encoding inside the level-2 sub-blocks is the
  remaining F9 gap, decodable from `eboot.elf`; otherwise F3 slots 6/7/11/22 and
  the G9/G10 directory binding. F1/F4 remain blocked on DMC3-side engine ground
  truth and are not re-spun.

---

## 2026-10-18 — F9/G9 bounded slice: the u16 offset lists share a 0x30-byte stride (E-068)

- Did: followed E-067's open item ("the tag-`0x16` table's continuation past index
  128 ... length/meaning [UNKNOWN]") by measuring the **arithmetic residue** of
  every u16 in the data-section sub-blocks, on all 123 clips of `R_HADES.WAD` (77)
  and `R_HERCULES.WAD` (46), read-only from
  `C:\Users\GigelCastel\Desktop\gow3\CUSA01715\EXEC\WAD\PS4_LE\`. Added
  `stride_residue()` / `stride_offset_run()` and the `CLIP_DATA_STRIDE` /
  `CLIP_DATA_STRIDE_FIELDS` / `CLIP_DATA_TAG10_RESIDUE` /
  `CLIP_DATA_TAG16_CONTINUATION_RESIDUE` / `CLIP_DATA_CONTINUATION_TERMINATORS`
  constants to `tools/gow3/anim.py`, the `ClipSubBlock.first_word` /
  `first_word_residue` / `tag16_continuation` / `tag16_continuation_terminator` /
  `tag10_residue_ok` / `tag16_terminator_ok` and `ClipSubBlocks.tag10_residue_ok` /
  `tag16_continuation_ok` accessors, and 7 tests (`TestStrideResidues`) in
  `tests/test_gow3_anim.py`. Full suite: **405 tests, all green** (398 baseline + 7).
  Read-only validation reproduced **245/245** tag-`0x10` and **245/245** tag-`0x16`
  relations.
- Found (**E-068**), all read-only on 245 tag-`0x10` and 245 tag-`0x16` sub-blocks:
  - **Every tag-`0x10` sub-block opens with a u16 `== 0x10 (mod 0x30)`** —
    245/245 (Hades 154, Hercules 91), i.e. `0x10 + 0x30 * k`. Only the first word:
    the leading run is not uniform and breaks after 1..35 entries.
  - **The word right after the tag-`0x16` continuation run is one of exactly
    `0x1710` / `0x1800` / `0x3C00`** (`0x30 * {123,128,320}`, all residue `0x00`) —
    245/245, no other value, no truncation.
  - The `0x30 * k` prefix is residue `0x00` and the continuation residue `0x20`.
  - **Recorded honestly:** the continuation is the *first* residue-`0x20` run, not
    the whole set — 87/245 tag-`0x16` blocks carry further residue-`0x20` values
    later (126/154 Hades but only 32/91 Hercules). So E-067's "second table" is a
    first run; the later values stay [UNKNOWN].
- **Inference (marked, unproven):** residues `0x00`/`0x10`/`0x20` are consistent
  with a single **0x30-byte (48-byte) record stride** whose fields sit at
  `+0x00`/`+0x10`/`+0x20`. No field is assigned a meaning.
- Docs: E-068 in `docs/EVIDENCE.md`; `docs/FORMATS.md` §7.7 gains "the u16 offset
  lists share a 0x30-byte stride — [PARTIAL] (E-068)"; `docs/BACKLOG.md` F9/G9 rows
  updated (evidence cells now list E-068). No game data committed.
- Next: the leaf keyframe/curve encoding inside the level-2 sub-blocks is still the
  F9 gap (decodable from `eboot.elf`); otherwise F3 slots 6/7/11/22 and the G9/G10
  directory binding. F1/F4 remain blocked on DMC3-side engine ground truth and are
  not re-spun.

---

## 2026-10-18 — F1/F4 unblocked: the DMC3 engine (`dmc3.exe`) is on disk and is a plain x86-64 PE (E-069)

- Did: noticed during reconnaissance that the DMC3 install root ships **its own
  executable**, `G:\Games\Devil May Cry HD Collection\dmc3.exe`
  (6,356,432 bytes) — the DMC3-side engine ground truth that F1/F4/F5 have been
  "blocked on" for many iterations and that **no prior doc or issue mentions**.
  Read it read-only and ported the GoW3 `eboot.elf` method (E-056) to PE:
  new `tools/dmc3/pe.py` (`PeImage`, `PeSection`, `PeError`, section-based
  `file_offset_to_rva`/`rva_to_file_offset`/`read`, `find_all()`,
  `rip_relative_references()`, `references_to_string()`), the DMC3 analogue of
  `tools/gow3/eboot.py`. Exported from `dmc3/__init__.py`; 17 unit tests in
  `tests/test_dmc3_pe.py` on a synthetic PE (no game data committed). Full suite:
  **422 tests, all green**.
- Found (**E-069**, read-only from `dmc3.exe`):
  - `dmc3.exe` is a normal, unpacked **x86-64 PE32+**: machine `0x8664`, magic
    `0x20B`, image base `0x140000000`, entry RVA `0x34615C`, 8 sections; only
    `.text` (`RVA 0x1000`, `vs=0x34DD4E`, `raw=0x400`, `rawsz=0x34DE00`, ch
    `0x60000020`) is executable and holds ~3.4 MB of code (15.6% zeros).
  - File↔RVA mapping is `rva = section.va + (offset − section.raw)`; the image
    base does not enter it (RIP-relative displacement is base-independent).
  - The scanner finds **19,648** RIP-relative `lea`/`mov` sites (`(modrm & 0xC7)
    == 0x05`) targeting **4,482** distinct RVAs.
  - **A `.mot`/`.mcv`/`.cam` extension table** in `.rdata` at RVA `0x5071D0` is
    referenced **once each** from a tight `.text` cluster. `.mot` @ `0x5071D0` ←
    instruction `0x2E01D2` = `48 8D 15 F7 6F 22 00` = `lea rdx,[rip+0x226FF7]`
    (decoded target `0x5071D0`, verified) followed by `mov rcx,r8` and a `call`.
    This is the located lead into the MOT loader.
  - **Negative (recorded):** `.pac` (7,118 occurrences), `.tm2`, `pl021.pac`,
    `GDataX360.afs` and `endof.afs` have **zero** RIP-relative references — file
    names are table data, exactly as GoW3's `.wad` (E-063).
- Docs: E-069 in `docs/EVIDENCE.md`; E-050 and E-051 each gain an "Update
  (E-069)" note (the blocker is now decoding, not evidence acquisition);
  new `docs/FORMATS.md` §8; `docs/BACKLOG.md` F1/F4 evidence cells add E-069 and
  a new tooling row **T10**. No game data committed.
- Next: mirror `gow3.eboot`'s **limited instruction decoder** (`reference_context`
  / `string_reference_contexts`) onto `PeImage`, then read the code at
  `0x2E01D2` to find the MOT handler and its numeric constants — that is the
  route into F4's u16[1..3] semantics and, by extension, F1/F5. F9's leaf
  keyframe encoding and the G9/G10 directory binding remain open too.

---

## 2026-10-18 — F4/F1 bounded slice: the `.mot` extension cluster is a file-type registry, not the MOT decoder (E-070)

- Did: followed E-069's stated route — mirror `gow3.eboot`'s limited instruction
  decoder onto `PeImage`, then read the code at `.text` RVA `0x2E01D2`. Added
  `DecodedInstruction`, `_decode_instruction`, `PeImage._code_window`,
  `reference_context` and `string_reference_contexts` to `tools/dmc3/pe.py`,
  exported `DecodedInstruction` from `dmc3/__init__`, and added 8 tests to
  `tests/test_dmc3_pe.py` on the synthetic PE. Full suite: **430 tests, all
  green**. Read the real `dmc3.exe` read-only (only its bytes; nothing written).
- Found (**E-070**):
  - The `.mot` string at `.rdata` `0x5071D0` is referenced once, by `0x2E01D2`,
    but that is inside a function at `0x2E01A0` that **classifies files by
    extension**: a chain of `strstr` tests (the IAT slot `0x34F3D0` → RVA
    `0x551CA8` = `"strstr"`), each copying two 32-byte names and storing a type
    id. **E-069's `[INFERRED]` "extension→handler dispatch" is corrected.**
  - Type ids, verified from the store sites: `.mot`=0, `.mcv`=1, `.cam`=2,
    `.hid`=3, `.clt`=4, `.tsc`=5 (case variants are redundant under `strstr`).
  - The registry context is now decoded: `+0x0000` count (cap `0x400`),
    `+0x8008` `nameA[1024][0x20]`, `+0x10008` `nameB[1024][0x20]`, `+0x18008`
    `flags[1024]`, `+0x18408` `type[1024]`; reset at `0x2E0150`, pair-lookup at
    `0x2E0060`, insert-wrapper at `0x2E0020`, nameA getter at `0x2E0130`;
    consumers at `0x2D6933`/`0x2D77A2`/`0x2DA173`/`0x2DA263`/`0x2DA336`.
  - Worked example with the new decoder: `string_reference_contexts(b".mot\0")`
    gives one context at `0x2E01D2` (`lea operand=0x5071D0`, length 7); the next
    instruction `49 8B C8` is outside the documented set, so the prefix stops.
  - Negative/recorded: the MOT **byte-level decoder** is still `[UNKNOWN]`; this
    mirrors GoW3, where `WAD_` reached name registration, not the loader (E-063).
- Docs: E-070 in `docs/EVIDENCE.md`; `docs/FORMATS.md` §8 gains §8.1 (the
  correction + type-id table + registry layout) and §8.2 (the decoder);
  `docs/BACKLOG.md` F1/F4/T10 rows updated. No game data committed.
- Next: follow the registry's **type id 0 (`.mot`)** into its consumer to find the
  real MOT loader and read its numeric constants — that is the route into F4's
  u16[1..3] semantics and F1/F5. F9's leaf keyframe encoding and the G9/G10
  directory binding remain open too.



## 2026-10-18 -- F4 bounded slice: the engine's 16-bit angle unit (E-075)

- Did: followed E-070's stated next step (follow the registry's `.mot` type id
  into its consumer) read-only through `dmc3.exe`. The registry route did not
  reach the MOT loader, but it led through the engine's motion/animation cluster
  and yielded a hard engine constant. Added `ANGLE_UNITS_PER_TURN`,
  `RADIANS_PER_ANGLE_UNIT`, `ANGLE_UNIT_COS_ZERO`, `ANGLE_UNIT_SIN_ZERO`,
  `angle_units_to_radians` / `angle_units_to_degrees` to `tools/dmc3/mot.py`
  (exported from `dmc3`) and 5 tests (`TestMotKeyframeAngleUnit`) to
  `tests/test_mot_records.py`. Full suite: **475 tests, all green**. Nothing
  written to the game; no game data committed.
- Found (**E-075**, read-only from `dmc3.exe`):
  - The two helpers at RVA `0x32D9C0`/`0x32D9F0` convert a **16-bit value to
    cos/sin** and tail-call the CRT: IAT slots `0x551DDA`/`0x551DE2` hold
    `"cosf"`/`"sinf"`. Both multiply by the **same `f32` at `.rdata` RVA
    `0x508834`** = `9.587379463482648e-05` = `float32(2*pi/0x10000)`, so **one
    full turn = `0x10000`, `0x4000` = 90 deg, `0x8000` = 180 deg**.
  - The helpers special-case the quarter/half turns (`0x4000`/`0xC000` for
    cosine, `0x8000` for sine) to return exact `0.0` -- hence those literals.
  - The animation evaluator (function containing `0x68200`) reads a runtime
    u16 (`[struct+0x60]`), calls these helpers and accumulates into
    `f32 [struct+0x20/0x24/0x28]` -- runtime pose angles are 16-bit in this unit.
  - **[INFERRED]** E-028's modal MOT channel `�0x3FFF` is `�89.99 deg`, i.e. a
    bone at 90 deg; the three keyframe channels are *candidates* for this unit.
    **Not proven** -- no MOT byte has been traced into the helpers.
  - **Negative (recorded):** the motion-cluster string table at `0x506808`..
    `0x506B80` (`Gravity`, `Bone`, `Motion`, `Clip`, `SetFrame`, `LMotorSt`,
    `SpTrackNo`, `RefMotion`, ...) is the **`/demo/%s` text event-script command
    vocabulary** (parser at `0x2D9F60`/`0x2DA0C0` is a chain of `strcmp`), not
    the MOT decoder. So neither the E-070 registry nor this table is the loader.
- Docs: **E-075** in `docs/EVIDENCE.md`; `docs/FORMATS.md` section 3.1 gains the
  engine cross-check note; `docs/BACKLOG.md` F4 row updated. No game data.
- **Coordination:** the ID range E-071..E-074 was taken by a parallel GoW3 writer
  *while this slice was in progress*; that writer's commit also swept the
  in-progress `dmc3/mot.py`/`__init__.py`/test edits into its own commit, leaving
  the intermediate version in HEAD (and a failing 2-pi assertion). This iteration
  takes **E-075** and commits the corrected constant + docs. All edits were
  re-verified against the working tree before committing.
- Next: F4's real gap is still the **MOT byte-level loader**. The registry
  (E-070) and the demo-script table (E-075) are both excluded; the remaining
  ground-truth route is to find the code that reads the MOT header/records
  (e.g. the `u16 groups`/`field_a == 3` record loop) directly in the motion
  cluster, or to find the animation *builder* that turns MOT bytes into the
  runtime struct with the 16-bit angles at `+0x60`. F1 and F3 slots 6/7/11/22
  stay available and are not blocked.

---

## 2026-10-18 — F1/F4 bounded slice: the PAC chunk tags are absent from `dmc3.exe` (E-076)

- Did: bounded slice on the F1/F4 engine route. The first move — locate the PAC
  chunk dispatcher by its tags — **disproved its own premise**, and that negative
  plus the alternative it exposes is this iteration's result. Read-only from
  `G:\Games\Devil May Cry HD Collection\dmc3.exe` (6,356,432 B). Added
  `PeImage.section_of_rva`, `PeImage.read_cstring`,
  `PeImage.walk_string_pool` and the `STRING_*`/`PRINTABLE_*` constants to
  `tools/dmc3/pe.py` (no new exported names, so `dmc3/__init__` is unchanged) and
  `TestStringPool` + a `pool_entry` helper (10 tests) to `tests/test_dmc3_pe.py`.
  Full suite: **485 tests, all green** (475 baseline + 10). Nothing written to the
  game; no game data committed.
- Found (**E-076**):
  - **The chunk tags are not in the engine.** `MOD `, `SHW `, `PAC\0`, `PNST`,
    `;RID` occur **0** times in the whole image (all sections, and as `.text`
    immediates); `MOT\0` occurs once, at `.rdata` `0x5071D9` — the tail of the
    uppercase `.MOT` extension in the E-069/E-070 table, not a chunk tag. So
    E-002's tag framing is a *container* fact the engine does not compare against;
    the remaining candidates are the **PAC slot id** (E-001) or the asset name
    [INFERRED].
  - **The engine's asset names are one `.rdata` pool.** `walk_string_pool(0x35D640)`
    yields **4,056** NUL-terminated printable-ASCII names, each padded to the next
    **8-byte** boundary (gap histogram `{16: 3409, 24: 642, 8: 4}`, and the names
    are of mixed length, so this is real padding); **3,397** end `.pac`. It holds
    `pl021.pac` at `0x363098` and all ten `pl021_00_0..9.pac` at
    `0x3645F0`..`0x364870`, interleaved with `id4516..id4525.pac`,
    `id516..id525.pac` and `m05_*_msg_*.txt`.
  - **No `.pac` pool entry is referenced by a RIP-relative `lea`/`mov`.** Of 19,648
    sites / 4,482 distinct targets, five land in the pool; only four are entry
    starts, all memory-card icons (`icon.sys`, `icon00.ico`, `icon01.ico`,
    `icon02.ico`) — so the pool base is resolved indirectly, as in E-069/E-063.
  - **Recorded honestly:** the fifth in-pool target (`0x36C355`) lands on padding
    inside the `st205cfg.pac` record; the pool's record framing beyond string
    alignment and the second, larger name cluster at `0x4EB36B..0x505031`
    (3,720 `.pac` occurrences) stay [UNKNOWN].
- Docs: E-076 in `docs/EVIDENCE.md`; `docs/FORMATS.md` gains §8.3 (the tag
  negative + the pool, [VERIFIED]/[PARTIAL]/[UNKNOWN] marked); `docs/BACKLOG.md`
  F1/F4/T10 rows updated. No game data committed.
- Next: on the engine route, stop looking for tag literals — go after the PAC
  **slot id** dispatch or the pool's **consumer** (the pool base is an indirect
  pointer, so the next lead is a `.data` absolute pointer / the code that indexes
  the pool). F1's remaining MOD body and F4's MOT loader are unchanged; F3 slots
  6/7/11/22 remain available.

---

## 2026-10-18 � F1/F4 bounded slice: the asset-name pool has an indexed `.data` consumer (E-077)

- Did: followed E-076's stated next step ("the pool base is an indirect pointer, so
  the next lead is a `.data` absolute pointer / the code that indexes the pool")
  read-only through `G:\Games\Devil May Cry HD Collection\dmc3.exe` (6,356,432 B).
  Added `PeImage.absolute_pointers_to` and `PeImage.pointer_array` (plus
  `POINTER_SIZE`) to `tools/dmc3/pe.py` and `TestAbsolutePointers` +
  `TestPointerArray` (9 tests) to `tests/test_dmc3_pe.py`. Full suite: **494 tests,
  all green** (485 baseline + 9). Nothing written to the game; no game data
  committed.
- Found (**E-077**):
  - **No dedicated pool-base global.** `absolute_pointers_to(0x35D640)` returns
    exactly one RVA, `.data` `0x55A570` � and that word is a **member of the table
    below**, not a `g_pool` variable. E-076's "indirect base" framing is refined:
    the pool is reached by *indexing a table*.
  - **The table.** `.data` `0x553050` is a contiguous run of 8-byte absolute
    `char*` pointers into the E-076 pool: `pointer_array(0x553050)` walks **4,039**
    entries to the first NULL (`.data` `0x55AE88`, file `0x559488`), a second run
    of 19 resumes at `0x55AE90`, and the block ends at `0x55AF28`. Of the 4,059
    non-null slots, **4,055 are pool entry starts**; the four exceptions are
    `at.ptx` (0x3679E4), `Video/` (0x3631DC), a `.data` pointer (0x5D9DC0) and
    0x36C355. Head: `[0] pl000.pac`, `[1] pl011.pac`, �, `[8] pl021.pac`,
    `[9] pl023.pac`. The block is a near-permutation of the 4,056-string pool, in
    an order that is neither pool order nor sorted.
  - **The single consumer.** The literal `0x553050` occurs **exactly once** in the
    whole image � as the `disp32` at `.text` `0x334F1` � inside a tail-callable
    accessor: `0x334E1 48 63 CA` (`movsxd rcx, edx`), `0x334E4 48 8D 05 15 CB FC
    FF` (`lea rax,[rip-0x334EB]` ? RVA 0 = module base), `0x334EB 33 D2`
    (`xor edx, edx`), `0x334ED 48 8B 8C C8 50 30 55 00`
    (`mov rcx,[rax + rcx*8 + 0x553050]`). So the engine resolves a name as
    `[image_base + 0x553050 + 8*index]` � a **displacement**, which is why the
    RIP-relative scanner missed it.
  - **Correction recorded:** the adjacent `.data` globals `0x553000..0x55304F` are
    an unrelated u32 state block (read at `0x2AC78`/`0x2ACA9`), **not** the table's
    struct base � a working hypothesis of this slice that the bytes refute.
- **Inference (marked, unproven):** the block is an **asset-name table indexed by
  an integer id**; whether that id is the PAC slot id (E-001) or a separate asset
  id, and who calls `0x334E1`, are [UNKNOWN]. The byte-level MOD/MOT decoders
  (F1/F4) are unchanged.
- Docs: E-077 in `docs/EVIDENCE.md`; `docs/FORMATS.md` gains �8.4; `docs/BACKLOG.md`
  F1/F4/T10 rows updated. Committed and pushed; commented issues #1 and #2.
- Next: find the caller of the accessor `0x334E1` and what supplies `edx` (the
  index) � that is the "PAC slot id dispatch" the engine route needs; then follow
  the indexed asset into its loader. F3 slots 6/7/11/22 and the GoW3R clip
  keyframe encoding remain available.

---

## 2026-10-18 - F1/F4 bounded slice: the asset-name table is four categories indexed by a u16 pair (E-078)

- Did: followed E-077's stated next step (find the caller of the accessor
  `0x334E1` and what supplies `edx`) read-only through
  `G:\Games\Devil May Cry HD Collection\dmc3.exe` (6,356,432 B). Used the
  `.pdata` exception directory to locate the functions, disassembled the region
  with a local recon tool (capstone, not a repo dependency), and validated the
  result read-only through the new resolver. Added `tools/dmc3/assets.py`
  (`AssetCategory`, `AssetEntry`, `asset_categories`, `resolve_name`,
  `parse_asset_entry`, `CATEGORY_*`/`ASSET_*` constants), exported from `dmc3`;
  added `PeImage.pointer_at` to `tools/dmc3/pe.py`; new
  `tests/test_dmc3_assets.py` (13 tests) and `TestPointerAt` (4 tests) on
  synthetic fixtures. Full suite: **511 tests, all green** (494 baseline + 17).
  Nothing written to the game; no game data committed.
- Found (**E-078**):
  - The accessor is **one arm of a four-way category dispatcher** at `.text`
    `0x33480`: `ecx` 0/1/2/3 select bases `0x553050` / `0x55A920` / `0x55ADF0` /
    `0x55AE90`, each indexing `[module_base + 8*edx + base]`. So the asset
    reference is a `(category, index)` pair with a u16 index, not a single id.
  - The bases split the E-077 pointer runs into **3866 / 154 / 19 / 19** names.
    Category 0 is the archive/movie list (`pl000.pac` .. `endof.afs`,
    **`pl021.pac` at index 8**); category 1 is audio (`Battle_*.adx` ..
    **`Versil_01/02/03.adx` at indices 150-152**, `ZZZ.adx`); category 2 is
    `Title.sfd` .. `ZZZ.sfd`; category 3 is `m99_s00.sfd` .. `SAVEDATA/`.
  - The dispatcher's **single direct caller** is `.text` `0x2EF7F7` in
    `0x2EF790`, which walks an array of **0x88-byte records** and, for a
    type-`1` record, takes `[record+4]` as the category and `[record+6]` as the
    index. Types `2`/`3` use an inline name (`record+0x10`) and a
    function-pointer dispatch (`record+8`) respectively (read from that one
    caller, [INFERRED]).
  - Read-only validation through `dmc3.assets.resolve_name` reproduced every
    anchor above on the real image; category 3's last slot is the E-077 padding
    target `0x36C355` (no name), as expected.
- **Correction recorded:** E-077's "the index semantics and its caller remain
  [UNKNOWN]" is resolved for the caller and refined for the index (a u16 within a
  category). E-077's "near-permutation of the pool" is now understood as four
  sub-ranges of two contiguous pointer runs.
- Unknown (recorded, not guessed): where the 0x88-byte record array lives and who
  builds it; whether category 0's index is the PAC/`plNNN` id or a separate asset
  id; the byte-level MOD/MOT decoders (F1/F4), which this resource-loader route
  does not reach.
- Docs: E-078 in `docs/EVIDENCE.md`; `docs/FORMATS.md` gains section 8.5;
  `docs/BACKLOG.md` F1/F4/T10 rows updated. No game data committed.
- Next: follow the record array to its builder (find who writes the 0x88-byte
  entries) or follow `0x333F0`/`0x33500` (the load path) to the container reader;
  F3 slots 6/7/11/22 and the GoW3R clip keyframe encoding remain available.

---

## 2026-10-18 — F9/G9 bounded slice: the clip's tag-`0x0F` leaf is a channel offset list; leaf payloads carry `0xCC` fill (E-079)

- Did: picked up the GoW3R clip leaf (F9/G9) rather than a fifth DMC3-engine step.
  Before the slice I spent a bounded look at the engine route E-078 named (the
  accessor's caller, the registry's type-id consumer, the file open/read pair
  `0x333F0`/`0x33500`) and **stopped**: the registry's type array (`ctx+0x18408`)
  has **no reader** with that displacement anywhere in `.text` (all seven imm32
  hits are the registrar's own writes), so the loader dispatch is not reachable by
  the string/displacement routes used so far. Recorded here, not as a doc claim.
  Then censused the clip leaf read-only from `R_HADES.WAD` (85,727,632 B): 77 clips,
  714 sub-blocks.
- Found (**E-079**):
  - **The tag-`0x0F` sub-block is a per-clip u16 offset list.** Exactly one per
    clip; 8/24/32/40 entries (8..40 channels). Every entry is `<= 0x1800` and
    either the `0x1800` sentinel or `== 0x20 (mod 0x30)` — **77/77**; non-decreasing
    74/77; last entry `0x1800` 76/77. `0x1800 = 0x30 * 128` is the tag-`0x16` ramp
    span (E-066) and `0x20` is one of E-068's residues, so this is the **channel
    table** over the shared 48-byte record array.
  - **Leaf payloads are partially filled with `0xCC`.** A `>= 2`-byte `0xCC` run
    occurs in 227/714 payloads and reaches the block end in 148; those are exactly
    the leaves (0x0B 62/77, 0x1B 64/87, 0x1C 22/23). The tag-`0x10` container has
    `0xCC` in 76/77 clips but **never at its end** — the fill there belongs to the
    nested blocks. So a **leaf size is a capacity**, not a data length.
  - **Two negatives:** the E-064 `count` is **not** the frame count (equal on 1/77;
    ratios 0.5..3.0), and **no** tag-`0x1B` payload is zlib/gzip/lzma/bz2 on 87/87
    (one raw-deflate 0xA0->5-byte degenerate hit, not evidence) — so the leaf is not
    simply compressed animation data.
- Docs: E-079 in `docs/EVIDENCE.md`; `docs/FORMATS.md` gains two §7.7 subsections;
  `docs/BACKLOG.md` F9 row updated. Code: `tools/gow3/anim.py` gains
  `u16_values` / `fill_run_start` / `channel_offset_list` / `channel_offset_ok` and
  the `ClipSubBlock`/`ClipSubBlocks` accessors; `tests/test_gow3_anim.py` gains
  `TestClipLeafBlocks` (8 tests). Nothing written to any game install; no game data
  committed.
- Next: fix the *meaning* of a tag-`0x0F` entry — the 48-byte-strided record array
  it indexes is the next target, and it is the same array the tag-`0x16` ramp and
  the tag-`0x10` residue point at; the leaf keyframe encoding follows from it.
  `F3` slots 6/7/11/22 remain the always-available DMC3 fallback.

---

## 2026-10-18 — F9/G9 bounded slice: a channel entry is `0x20 + 0x30*k`, and `0x1800` pads the tail (E-080); two DMC3 engine signatures disproved (E-081)

- Did: picked F9/G9 (issues #24/#36) after first spending a bounded look at the
  DMC3 engine route E-078 named (the F4 critical path) and **recording that look as
  a dead end** rather than thrashing. Then re-censused the tag-`0x0F` channel list
  — which E-079 had measured on `R_HADES.WAD` alone — over **123** clips
  (77 `R_HADES.WAD` + 46 `R_HERCULES.WAD`), read-only. Added
  `CLIP_DATA_CHANNEL_FIELD_OFFSET` / `CLIP_DATA_CHANNEL_LAST_INDEX` /
  `CLIP_DATA_CHANNEL_CAPACITIES`, the functions `channel_index` /
  `channel_live_values` / `channel_index_set`, the `ClipSubBlock` properties
  `channel_live_values` / `channel_indices` and the `ClipSubBlocks` properties
  `channel_live_count` / `channel_indices` to `tools/gow3/anim.py`; 7 tests
  (`TestClipChannelIndices`) in `tests/test_gow3_anim.py`. Full suite:
  **526 tests, all green**. Nothing written to any game install; no game data
  committed.
- Found:
  - **E-080.** Every non-sentinel entry is exactly `0x20 + 0x30*k`, `k` in
    1..126 (**123/123**, 0 violations), so the entry names the `+0x20` field of a
    record in the shared 48-byte array. `0x1800` (= `0x30 * 128`, one past the
    128-entry tag-`0x16` ramp, E-066) is a **tail sentinel**: 116/123 lists carry
    it before their end, so E-079's "8..40 channels" is a **capacity** and the live
    count is 1..36 (modes 27/26/34/28). Corrected three E-079 numbers on the larger
    sample: non-decreasing is 120/123 (not 74/77) and list lengths include **16**
    (2 clips). **Disproved my own "(start, end) pair" hypothesis** — 65/123 clips
    have an odd live count — and "sorted" as a rule (3 clips begin out of order:
    `csHadesIntroStruggle`, `csHadesIntroFail`, `csHadesKnifeKillTug2`). Over all
    123 clips only **36 distinct `k`** occur (`{1, 8, 10..12, 16..30, 39..45, 52,
    59..64, 89, 126}`), most used by ~100 clips, so a clip's channels are a subset
    of a fixed 36-slot universe. Which record field a channel names, and the leaf
    keyframe encoding, remain **[UNKNOWN]**.
  - **E-081 (DMC3 engine, recorded dead ends).** Before the GoW3R slice I tried to
    reach F4's MOT byte decoder by its two most distinctive signatures; both are
    generic code. (a) `and eax, 0x7FFF` (the `u16 - 0x8000` frame bias) has 3 hits
    in `.text`; the two in near-identical functions (`0x2F7A90`, `0x2FE3B0`) are a
    **pointer-relocation walker** over 0x40/0x50-byte records (fields rebased with
    `add rax, [rbp+0x90]`), not the keyframe decoder. (b) E-070's four registry
    consumers all call `0x2E0060` with a name from the `0x506BC8` **`/demo/`
    script vocabulary** E-075 excluded, so that route still does not reach the MOT
    loader — consistent with the type array having no reader. Recorded so they are
    not re-walked.
- Docs: E-080/E-081 in `docs/EVIDENCE.md`; `docs/FORMATS.md` §7.7 gains "A channel
  entry is `0x20 + 0x30*k`, and `0x1800` pads the tail — [VERIFIED] (E-080)";
  `docs/BACKLOG.md` F1/F4 (E-081) and F9/G9 (E-079/E-080) rows updated.
- Next: the leaf keyframe encoding is still the F9 gap — the 36-slot channel array
  the tag-`0x0F` list indexes (the same 0x30-strided array the tag-`0x16` ramp and
  the tag-0x10 residue point at) is the next target; on the DMC3 side, reach F4/F1
  via the load path (`0x333F0`/`0x33500`) or `.pdata`, not the two signatures now
  disproved. `F3` slots 6/7/11/22 remain the always-available fallback.

---

## 2026-10-18 — F1/F4 bounded slice: the `(category,index)` dispatcher *opens*; the loader cluster is file I/O (E-082)

- Did: followed E-078/E-081's named next step — the load path `0x333F0`/`0x33500`
  — read-only through `G:\Games\Devil May Cry HD Collection\dmc3.exe`
  (6,356,432 B). Disassembled the loader cluster (capstone, a local recon tool,
  not a repo dependency) and censused its callers. Added
  `PeImage.call_sites` (direct `call rel32` caller census, the call-side analogue
  of `rip_relative_references`) to `tools/dmc3/pe.py` and `TestCallSites`
  (5 tests) to `tests/test_dmc3_pe.py`. Full suite: **531 tests, all green**
  (526 baseline + 5). Nothing written to the game; no game data committed.
- Found (**E-082**):
  - `0x333F0` = `open(name)`: calls `0x2FCA0(name,1)`, `0x2F9F0(handle,&u32)`,
    allocates **0x50 bytes** and returns a handle struct (`+0x01` open flag,
    `+0x08` size, `+0x2C` underlying handle, `+0x30` base offset). `0x333C0` =
    `ceil([handle+8]/0x800)` blocks; `0x33500`/`0x335A0` = async block read with a
    polled `.data` state word (2/3/4); `0x33390` = close; `0x333E0` = state read.
  - **Correction of E-078 [VERIFIED]:** all four arms of the `(category,index)`
    dispatcher `jmp 0x333F0`, so `0x33480` **opens** the resolved name and the
    stored `[rsi]` is a handle, not a `char*`. `dmc3.assets.resolve_name` (the
    table read) is unaffected; only the dispatcher's *return type* changes.
  - The whole direct-call consumer set is one cluster, `.text`
    `0x2EF620..0x2EF9C7`: `file_size` (`0x2EF620`, no direct caller -> indirect),
    the E-078 streaming worker, and `load_file` (`0x2EF920`, synchronous).
    `load_file`'s two callers (`0x1B80AC`, `0x1B871F`) feed the loaded buffer to a
    content parser at `0x1B7C70`/`0x1B7D10` — the next engine lead.
  - **Consequence:** the `(category,index)` route reaches *bytes*, not the
    MOD/MOT decoder; the byte decoders are downstream of the loaded buffer and
    remain [UNKNOWN]. This closes E-078/E-081's named load-path step rather than
    re-walking it.
- Docs: E-082 in `docs/EVIDENCE.md`; `docs/FORMATS.md` gains 8.6; `docs/BACKLOG.md`
  F1/F4/T10 rows updated.
- Next: read the content parser `0x1B7C70`/`0x1B7D10` (what its buffer is; caller
  B writes the bytes `"PAC"` at `0x1B7CCD`) — that is the container-parse step
  ahead of the MOD/MOT decoders. The GoW3R clip channel array (E-079/E-080) and
  F3 slots 6/7/11/22 remain available.

## 2026-10-18 — F1/F4 bounded slice: `load_file`'s consumers are text tokenizers, not the container parser (E-083)

- Did: followed E-082's stated next step — read the "content parser"
  `0x1B7C70`/`0x1B7D10` — read-only through
  `G:\Games\Devil May Cry HD Collection\dmc3.exe` (6,356,432 B), decoding with a
  local recon disassembler (capstone, **not** a repo dependency). The step
  **disproved its own premise**. Added `.pdata` function-table reading to
  `tools/dmc3/pe.py` (`PeFunction`, `PeImage.pdata_section`,
  `PeImage.functions()`, `PeImage.function_containing(rva)`), exported
  `PeFunction` from `dmc3`, and added `TestFunctionTable` (7 tests) on a
  synthetic three-section PE. Full suite: **538 tests, all green** (531 baseline
  + 7). Nothing written to the game; no game data committed.
- Found (**E-083**):
  - `0x1B7C70..0x1B7D04` is a **3-state text tokenizer**: state 0 treats `/` and
    CR as line markers and `#` as a comment and otherwise writes the literal
    **`"PAC"`** (`66 41 C7 00 50 41` / `41 C6 40 02 43`) into a 4-byte output;
    the empty-input default is the same `"PAC"`. `0x1B7D10..0x1B7E5C` is a
    line/word **counter** (separator mask `0x800800002000` = CR / ESC / `#`).
  - The two functions containing the synchronous `load_file` (`0x2EF920`) call
    sites are **`.lst` -> `.pac` name resolvers**: a token equal to `"dummy"`
    (`0x4DC4D8`) is skipped; a token whose extension is `"lst"` (`0x4DC4E0`) has
    the extension overwritten in place with `"pac"` (`0x1B81F9 mov dword [..],
    0x636170`) and the `<base>.pac` is probed with `file_size` (`0x2EF620`).
  - **Correction to E-082:** its [INFERRED] "content parser ... the
    container-parse step ahead of the MOD/MOT decoders" is **falsified** — the
    synchronous route serves text lists, not the binary payloads. Also refined:
    `file_size`'s name argument is **`rdx`**, not `rcx`.
  - The `.pdata` table holds **12,235** `RUNTIME_FUNCTION` entries on the real
    image; the new reader reproduces every boundary used here
    (`0x1B7C70 -> [0x1B7C70,0x1B7D04)`, `0x1B7D10 -> [0x1B7D10,0x1B7E5C)`,
    `0x1B7FD0 -> [0x1B7FD0,0x1B82B5)`, `0x1B85C0 -> [0x1B85C0,0x1B8C98)`).
- Docs: E-083 in `docs/EVIDENCE.md`; `docs/FORMATS.md` gains §8.7;
  `docs/BACKLOG.md` F1/F4/T10 rows updated. No game data committed.
- Next: the MOD/MOT byte decoders (F1/F4) stay [UNKNOWN] and the synchronous
  `load_file` route is now closed as a lead; reach them via the async streaming
  worker (`0x2EF790`) or the now-readable `.pdata` table rather than the
  string/tag signatures. F3 slots 6/7/11/22 remain available.

---

## 2026-10-18 — F3/F8 bounded slice: the `.tm2` pre-header and the PAC texture slots are the same descriptor (E-084); three F4 engine leads closed (E-085)

- Did: picked the Phase-1 format path (F1/F4 stay blocked on the engine route,
  which was first probed and closed as E-085). Read real bytes (read-only) from
  `pl021.pac` slots 0 and 22 and `i001_90.tm2` under
  `G:\Games\Devil May Cry HD Collection\data\dmc3\GData.afs\`, and found the
  untagged texture slots and the `.tm2` platform pre-header carry **one and the
  same 0x68-byte texture descriptor** immediately before an embedded DDS.
  Added `TextureChunk` / `maybe_texture_chunk` and the
  `TEXTURE_DESCRIPTOR_SIZE` / `PAC_TEXTURE_DESCRIPTOR_OFFSET` /
  `TM2_TEXTURE_DESCRIPTOR_OFFSET` / `TEXTURE_DDS_OFFSET` / `DDS_MAGIC`
  constants to `tools/dmc3/raw.py`, exported from `dmc3`,
  `raw_chunk_texture(...)` to `tests/fixtures.py`, and `TestTextureChunk`
  (7 tests) to `tests/test_raw.py`. Full suite: **545 tests, all green**
  (538 baseline + 7). Nothing written to the game; no game data committed.
- Found:
  - **E-084.** The descriptor is at **body+0x808** in a `pl021.pac` texture slot
    (after 8 zero bytes) and at **file+0x08** in a `.tm2` — a `0x800` offset
    difference — with the 128-byte DDS header immediately after it in both
    (`body+0x870` / `file+0x70`). Relations **verified 3/3 chunks**: `D+0x08 ==
    (width, height)`; `D+0x3C == (width//2, height//2)`; `D+0x40 == D+0x44 ==
    float32(2/width)`; `D+0x5C == D+0x30 + 128`. `D+0x00 >> 8 == mips` is
    [INFERRED] (9/1/1). The three instances are `pl021.pac` slot 0 (256×256
    `DX10`, 9 mips, payload 87,428) and slot 22 (32×32 `DXT1`, 1 mip, payload
    512), plus `i001_90.tm2` (256×256 `DXT3`, 1 mip, payload 65,536).
  - **Corrections.** E-033's slot-0 DDS was recorded as `256×64`; the real bytes
    at body+0x880 are `00 01 00 00` (256), so it is **256×256 `DX10`, depth 1,
    9 mips** (E-033's hex had one wrong dword). **E-034's "all 28 TM2 pre-header
    fields [UNKNOWN]" is superseded** — `+0x08..+0x6F` is the same descriptor,
    so F8's fields gain the §1.4 relations a format away.
  - **E-085 (bounded negative, DMC3 `dmc3.exe`).** The three engine leads tried
    first are all dead ends: (a) E-075's "animation evaluator" (`0x68200`) is a
    single object's runtime spin integrator (`[0x681B0, 0x68316)`, reads
    `[r9+0x60]`, integrates into `[rax+0x20/0x24/0x28]`; never touches MOT
    bytes); (b) E-078/E-082's `0x2EF790` walks a **runtime job queue** passed via
    `[rdx+0x10]` (record type at `[rbx]`: 1 = `(category,index)`, 2 = inline
    name, 3 = callback), not a static array — and has no direct callers; (c) the
    MOD header's `f32@+0x04` `1.01` constant is inert `.rdata` (`0x4C6134`,
    zero RIP-relative references), like the MOT frame bias (`sub eax,0x8000`)
    which has no `.text` hit.
- Docs: E-084 and E-085 in `docs/EVIDENCE.md`; `docs/FORMATS.md` gains §1.4
  (texture descriptor) and rewrites §4.1 (TM2 pre-header = the descriptor) plus
  the §1.3 slot-0/slot-22 corrections; `docs/BACKLOG.md` F3 and F8 rows updated
  (evidence cells now list E-084). Committed and pushed; commented issues #4
  and #8.
- Next: the descriptor's remaining field meanings (`0x0000AAE4`, `64`, `8`, the
  `+0x02 == 2`) need engine ground truth or more texture samples — but the
  structure is now shared across two formats. F3 slots 6/7/11 remain; F1/F4's
  byte decoders are still the critical path and the next engine lead is the
  `.pdata`/call-graph route (E-083/E-085), not the string/tag signatures.

---

## 2026-10-18 — F3 bounded slice: `pl021.pac` slot 6 is a 252-record four-byte table, grouped by zero terminators (E-086)

- Did: picked F3 (issue #4) from the always-available list — the Phase-1 format
  critical path (F1/F4) stays blocked on engine ground truth and is not re-spun,
  and the last DMC3 engine slice (E-085) closed three leads without reaching the
  MOD/MOT decoders. Read real bytes (read-only) from
  `pl021.pac` slot 6 (`G:\Games\Devil May Cry HD Collection\data\dmc3\GData.afs\
  pl021.pac`, file offset `0x070210`, span `0x3F0`). Added `Slot6Record` /
  `Slot6Table` / `maybe_slot6_table` and the `SLOT6_RECORD_SIZE` /
  `SLOT6_RECORD_COUNT` / `SLOT6_CHUNK_SPAN` constants to `tools/dmc3/raw.py`,
  exported from `dmc3`, added the `raw_chunk_slot6()` fixture and
  `TestSlot6Table` (8 tests) to `tests/test_raw.py`. Full suite: **553 tests,
  all green** (545 baseline + 8). Nothing written to the game; no game data
  committed.
- Found (**E-086**): slot 6 is **252 fixed 4-byte records** (`u8 field_a`,
  `u8 field_b`, `u16 field_c`) with no header or count field; the fourth byte is
  zero in all 252. `field_a` = 1×201, 0×32, 4×7, 6×6, 2×5, 5×1; `field_b` = 0×171,
  9×29, 13×14, 1×8, 2×5, then singletons/small groups. **32 all-zero records** at
  indices `23, 44, 45, 99, 119, 130, 166–169, 176–179, 182, 199, 236–251` split
  the non-zero records into **ten runs** (sizes `23, 20, 53, 19, 10, 35, 6, 2,
  16, 36`). `field_c` equals the record's own index for **209/252**; the 43
  exceptions are the zero records plus indices `2, 3, 4, 5`, `47`, and the
  six-record run `93–98` (all `field_c == 81`). Slots 7 and 11 do **not** share
  the shape (`field_c == index` for 1/5,020 and 0/168), so the framing is
  slot-specific. Every field meaning is [UNKNOWN]; the parser interprets
  nothing. Verified read-only against the real chunk (all counts reproduced).
- Docs: E-086 in `docs/EVIDENCE.md`; `docs/FORMATS.md` §1.3 gains the slot-6
  bullet and narrows the remaining unknown slots to 7/11; `docs/BACKLOG.md` F3
  row updated. Commented issue #4 (left open).
- Next: F3 slots 7/11 remain; every Phase-1 format critical-path item (F1/F4/
  F2/F5/F6/F8) stays blocked on engine ground truth and is not re-spun. F1's MOD
  body is heterogeneous across the four chunks (slots 1/12/23/25 have different
  bodies at body+0x60), so its payload is harder than a header fix — the next
  engine lead remains the `.pdata`/call-graph route. F9's clip leaf keyframe
  encoding (GoW3R) is also open and decodable from the file.


---

## 2026-10-18 — F3 bounded slice: `pl021.pac` slot 7 is 251 fixed `0x50`-byte records (E-089)

- Did: picked F3 (issue #4) from the always-available list; the Phase-1 format
  critical path (F1/F4) stays blocked and is not re-spun. Read real bytes
  (read-only) from `pl021.pac` slot 7
  (`G:\Games\Devil May Cry HD Collection\data\dmc3\GData.afs\pl021.pac`, file
  offset `0x070600`, span `0x4E70` = 20,080 bytes). Added `Slot7Record` /
  `Slot7Table` / `maybe_slot7_table` and the `SLOT7_*` constants to
  `tools/dmc3/raw.py`, exported them from `dmc3`, added the synthetic
  `raw_chunk_slot7()` fixture and `TestSlot7Table` (9 tests). Full suite:
  **581 tests, all green** (572 baseline + 9). Nothing written to the game; no
  game data committed.
- Found (**E-089**): slot 7 is **251 fixed `0x50`-byte records** with no header
  or count field. Each record = `u32 field_00` (2 x246, 3 x4 at indices
  142/151/163/164, 4 x1 at index 143), three zero u32s, then four `f32[4]`
  slots at `+0x10/+0x20/+0x30/+0x40`. Verified: the three reserved u32s are
  zero on all 251; vector slot 3 is all-zero on all 251; slot0[3] == `1.0f` on
  247/251 (exceptions are the four `field_00 == 3` records); slots at or beyond
  `field_00` are all-zero on 237/251, with 14 `field_00 == 2` exceptions
  (indices 10, 78, 79, 114, 152-161) each carrying a non-zero first component
  in vector slot 2. Read-only validation reproduced every count; a bitwise
  check confirmed the 14 trailing exceptions are exactly 14 words at `+0x30`.
  `field_00` as a slot count and the slots as `(x, y, z, w)` are [INFERRED];
  every component meaning remains [UNKNOWN].
- Note: `tools/gow3/meshes.py` and `tests/test_gow3_meshes.py` were already
  modified in the working tree by another writer (E-087 follow-up). They were
  left untouched and not staged; only this slice's paths were committed.
- Docs: E-089 in `docs/EVIDENCE.md`; `docs/FORMATS.md` §1.3 gains the slot-7
  layout and narrows the undecoded slots to **slot 11**; `docs/BACKLOG.md` F3
  row updated (evidence cell adds E-089).
- Next: **slot 11** is the last untagged `pl021.pac` slot with no decoded
  framing (672 bytes = 168 f32s, opening `10.0`); a bounded slice should test
  whether it is 42 x `f32[4]`, 24 x 7, or a headerless list. F1/F4 remain
  blocked on the engine route and are not re-spun.

---

## 2026-10-18 — F3 bounded slice: `pl021.pac` slot 11 is a flat 168-f32 array; no record framing recovered (E-090)

- Did: picked up the previous journal's own "Next" — F3 slot 11, the last
  untagged `pl021.pac` slot without a decoded framing (the Phase-1 critical path
  F1/F4 stays blocked on the engine route and is not re-spun). Read real bytes
  (read-only) from `pl021.pac` (`G:\Games\Devil May Cry HD Collection\data\dmc3\
  GData.afs\pl021.pac`, 548,768 B): entry table puts slot 11 at file offset
  `0x0780B0`, span `0x2A0` = 672 bytes. Added `Slot11Table` /
  `maybe_slot11_table` and `SLOT11_FLOAT_COUNT` to `tools/dmc3/raw.py`, exported
  from `dmc3`, added the synthetic `raw_chunk_slot11()` fixture and
  `TestSlot11Table` (6 tests) in `tests/test_raw.py`. Full suite: **587 tests,
  all green** (581 baseline + 6). Nothing written to the game; no game data
  committed.
- Found (**E-090**): the whole span is **168 little-endian f32s**, no header, no
  count field, no separator — the same shape as slot 9 (E-062). Head verbatim
  `9, 9, 9, 9, 10, 270, 0, 5, 330, 0, 18, 10`. **142/168 non-zero**; interior
  zeros exactly at indices `6`, `9`, `58`; the **last 23 values (145..167) are
  zero**; 67 distinct values (most common `9.0` 26x and `0.0` 26x, max `2000.0`,
  min `−45.0`); indices `104..114` are the period-3 rotation `400, 350, 1000`.
  **The framing is not recovered:** for every candidate record size dividing 168
  (`2, 3, 4, 6, 7, 8, 12, 14, 21, 24, 28, 42, 56`) no column is constant and no
  non-zero record of size 2/3/4/6/7/8 repeats, so the `42 × f32[4]`, `24 × 7`
  and `21 × 8` readings are neither confirmed nor refuted — recorded honestly as
  **[UNKNOWN]** rather than asserted.
- **Correction recorded:** the previous journal's forward note said slot 11 opens
  with `10.0`; the real first value is `9.0` (`0x41100000`, not `0x41200000`).
- Docs: E-090 in `docs/EVIDENCE.md`; `docs/FORMATS.md` §1.3 slot-11 bullet
  rewritten (and the "corrects 10.0" note) and the decoded-slot summary updated;
  `docs/BACKLOG.md` F3 row evidence cell adds E-090 and drops slot 11 from the
  undecoded list (framing/meaning remain [UNKNOWN]).
- Next: all nine untagged `pl021.pac` slots now have a decoded framing (0, 5, 6,
  7, 9, 10, 11, 21, 22); what remains everywhere is **meaning**, which needs
  engine ground truth (`dmc3.exe`) or a decoded peer artifact. F1/F4 stay blocked
  on the engine route and are not re-spun; the GoW3R clip leaf keyframe encoding
  (F9) is available and decodable from the file.

---

## 2026-10-18 — F1 bounded slice: the `MOD ` body's `+0x1C` field is one tagged u32 (E-091)

- Did: picked the critical path **F1** (issue #1) after re-reading the journal
  (F1/F4 are the stated preferred path; F3 untagged slots are now all framed).
  Read all 194 `*.pac` files under
  `G:\Games\Devil May Cry HD Collection\data\dmc3\GData.afs\` (read-only) and
  censused the four bytes at `MOD ` body `+0x1C` across all **286** `MOD `
  chunks. Changed `ModBodyPrefix` in `tools/dmc3/mod.py` to carry the u32
  `tag_word` with `tag` / `count` / `marker` / `tag_in_namespace` accessors,
  added `BODY_TAG_OFFSET` / `BODY_TAG_NAMESPACE` / `BODY_TAG_MASK` (exported from
  `dmc3`), rewrote `tests/fixtures.py::mod_body` to write the single tagged u32
  (`tag` keyword), and added `TestModBodyTaggedCount` (4 tests). Full suite:
  **591 tests, all green** (587 baseline + 4). Nothing written to the game; no
  game data committed.
- Found (**E-091**), and this **corrects E-031**:
  - The `u16` "marker" at body `+0x1C` and the `u16` "count" at body `+0x1E`
    are the two halves of **one little-endian u32** `(count << 16) | tag`, not
    two fields. Verified on `pl021.pac`: `0x01DA8001` (slot 1, count 474),
    `0x012A8001` (slot 12, count 298), `0x00B68001` (slots 23/25, count 182).
  - The low half (**tag**) is in the `0x8000` namespace on **286/286** install
    `MOD ` chunks: `0x8001` x279, `0x8002` x4, `0x8201` x2, `0x8005` x1. So
    `0x8001` is a per-chunk tag (likely a MOD subtype), **not a magic**, and
    E-031's "marker constant" is only the modal value.
  - The same tagged shape recurs at body `+0x5C` (188/286) and body `+0x9C`
    (170/286) — recorded as observations, not claimed as a record framing.
  - `body +0x24` is a multiple of `64` in 375/623 tagged records; [UNKNOWN].
  - Confirmed the body is **heterogeneous**: slots 23/25 (the byte-identical
    pair) carry a strictly increasing, 16-byte-aligned u32 section-offset table
    at body `+0x6C` (`0xD0, 0x960, 0x11F0, 0x14D0, 0x17B0, 0x18F0`, cumulative
    start offsets, last section to the body end); slots 1/12 do not. So no
    single body layout generalises yet.
- Evidence: **E-091** in `docs/EVIDENCE.md` (raw bytes + the 286-chunk census);
  `docs/FORMATS.md` §5.1 rewritten with the tagged-u32 spec and the E-031
  correction; `docs/BACKLOG.md` F1 row updated (evidence cell adds E-091).
- Next: the tag's meaning is the fresh lead — it is per-chunk data, so
  correlating tag values with the chunk's headers (`+0x10`/`+0x14`/`+0x20`) or
  with the PAC slot may name a MOD subtype. Beyond that, the vertex layout past
  `+0x5C` is still F1's gap (engine route via `.pdata`, or a decoded peer). F4
  stays blocked on the engine route and is not re-spun; the GoW3R clip leaf
  keyframe encoding (F9) remains available.

## 2026-10-18 — F1 bounded slice: the `MOD ` body opens with a 0x40-byte descriptor array (E-092)

- Did: picked the critical path **F1** (issue #1) after re-reading the journal;
  E-091's own "Next" said the tag was the lead, but reading the *whole* body
  showed the first 0x40 bytes are one record of an array, which reframes the
  tag question. Read all 194 `*.pac` files under
  `G:\Games\Devil May Cry HD Collection\data\dmc3\GData.afs\` (read-only; 32
  `PNST` files skipped) and censused the **286** `MOD ` chunks. Added
  `ModBodyDescriptor`, `ModBodyDirectory`, `descriptor_count` /
  `maybe_mod_body_directory` and the `BODY_DESCRIPTOR_*` constants to
  `tools/dmc3/mod.py`, exported from `dmc3`; added the synthetic
  `mod_descriptor()` / `mod_directory_body()` fixtures and
  `TestModBodyDirectory` (9 tests). Full suite: **600 tests, all green**
  (591 baseline + 9). Nothing written to the game; no game data committed.
- Found (**E-092**), read-only on **286/286** install `MOD ` chunks:
  - The body opens with a fixed **0x40-byte descriptor array**. Its byte size is
    the body's own `+0x24` field (descriptor 0's `+0x24`); `count = array_size //
    0x40` = 2..42. The size is a multiple of `0x40` in **279/286** chunks; the
    other seven (all in `id430.pac`/`id470.pac`) add `0x10`.
  - **Exactly `count-1` descriptors carry a `0x8000`-namespace tag at `+0x1C` and
    the last is an untagged footer — 286/286.** Descriptor `+0x24` is 16-byte
    aligned in 284/286 and strictly increasing across `records` in 282/286.
  - Descriptor-tag census over every tagged record: `0x8001` x1519, `0x8002` x26,
    **`0x8008` x8**, `0x8201` x3, **`0x8601` x2**, **`0x8004` x2**, `0x8005` x1
    (three new tags vs E-091's first-field census).
  - **Correction to E-031/E-091's framing:** `ModBodyPrefix.tag_word`/
    `field_24`/`field_2c` are descriptor 0's own fields, and its `vector`/
    `repeat` belong to **descriptor 1** (`0x4C = 0x40 + 0x0C`, `0x5C = 0x40 +
    0x1C`). That explains E-091's body+0x5C "tagged shape in 188/286": it is
    descriptor 1's tag, present unless `count == 2` (98 chunks; `286 − 98 =
    188`). Body+0x9C is descriptor 2's tag (`count ≥ 4` → 171; E-091 measured
    170).
  - **[UNKNOWN]:** what the array describes, what `count` counts, the footer's
    role, and the data layout. The descriptor array names mesh data; it is not
    the mesh payload.
- Docs: E-092 in `docs/EVIDENCE.md`; `docs/FORMATS.md` §5.1 gains the
  "E-092 update: the body opens with a fixed-size descriptor array" subsection
  and the title gains E-092; `docs/BACKLOG.md` F1 row updated (evidence cell
  adds E-092, status rewritten). No game data committed.
- Next: the descriptor array is now the *addressable* structure — the descriptor
  tags (`0x8001`/`0x8002`/`0x8008`/`0x8201`/`0x8601`/`0x8004`/`0x8005`) and each
  descriptor's `+0x24` data offset are the fresh lead into the vertex/index
  layout. F4 stays blocked on the engine route and is not re-spun; the GoW3R
  clip leaf keyframe encoding (F9) remains available.

## 2026-10-18 — F1 bounded slice: `+0x24` names a data block with a fixed 0x2C-byte prefix of three offsets (E-093)

- Did: picked the critical path **F1** (issue #1) and followed E-092's own stated
  next step — "each descriptor's `+0x24` data offset" — by reading the bytes it
  points at, read-only, across all 194 `*.pac` files under
  `G:\Games\Devil May Cry HD Collection\data\dmc3\GData.afs\` (32 `PNST` files
  skipped; **286** `MOD ` chunks, 1,561 record descriptors). Added
  `ModBodyBlock`, `body_blocks`, the `blocks` field on `ModBodyDirectory` and the
  `BODY_BLOCK_*` constants to `tools/dmc3/mod.py`, exported from `dmc3`; added the
  `mod_block()` fixture and a block-laying `mod_directory_body()`;
  `TestModBodyBlocks` (7 tests). Full suite: **607 tests, all green** (600
  baseline + 7). Nothing written to the game; no game data committed.
- Found (**E-093**), read-only on the install:
  - A record descriptor's `+0x24` names a **body-relative data block**; the
    blocks are **consecutive**. Descriptor 0's `+0x24` equals the array-size
    field on **286/286** chunks (so the first block starts at the array end) and
    the last block runs to the body end (descriptor offsets strictly increasing
    on 282/286).
  - A block opens with a **fixed 0x2C-byte prefix**, all-zero except **three u32s
    at `+0x04`, `+0x0C`, `+0x1C`**; the payload starts at `+0x2C`. Verified on
    **1,542/1,556** readable blocks. The 14 non-conforming blocks are all in
    `em035.pac`/`pl001.pac`/`pl015.pac`/`pl016.pac`, where the prefix bytes read
    as `f32`/other content — recorded as an anomaly, not explained.
  - `data_offset < offset_a < offset_b` on **1,544/1,556**; both interior offsets
    fall inside the block on **1,540/1,556**; all three 16-byte aligned on
    **1,503/1,556**.
  - **[INFERRED]** where ordered+in-block hold, the interior offsets split the
    payload into three consecutive regions; their contents differ (f32, then
    mostly `0x1F`/`0x801F` words) but **no region is assigned a format**. The
    third offset `offset_c` leaves the block in 708/1,561 — [UNKNOWN].
  - This turns E-092's "data layout [UNKNOWN]" into an addressable 3-region
    block per descriptor; the leaves' contents (positions/normals/UVs/indices/
    weights) remain the open question.
- Docs: E-093 in `docs/EVIDENCE.md`; `docs/FORMATS.md` §5.1 gains the "E-093
  update" subsection and the title gains E-093; `docs/BACKLOG.md` F1 row updated
  (evidence cell adds E-093). No game data committed.
- Next: within each block, the three regions are the next lead — test whether the
  first region is an `f32` position array (stride 12) and whether the second is a
  `u16` index buffer, using a chunk where `count` is small. F4 stays blocked on
  the engine route and is not re-spun; F2/F3/F5/F6/F8 and the GoW3R clip leaf
  encoding (F9) remain available.

## 2026-10-18 � F1 bounded slice: a `MOD ` data block's payload opens with `count` positions then `count` normals (E-094)

- Did: picked the critical path **F1** (issue #1) and followed E-093's own stated
  next step � "within each block, the three regions are the next lead". Read the
  block payloads read-only across all `*.pac` files under
  `G:\Games\Devil May Cry HD Collection\data\dmc3\GData.afs\` (1,535
  ordered+in_block record descriptors). Added `unit_triple`, `block_positions`,
  `block_normals`, `normal_run`, `ModBodyBlock.normal_offset` and the
  `BODY_BLOCK_TUPLE_SIZE` / `BODY_BLOCK_NORMAL_TOLERANCE` /
  `BODY_BLOCK_NORMAL_MIN_RUN` constants to `tools/dmc3/mod.py`, exported from
  `dmc3`; added `mod_vertex_block()` / `mod_vertex_directory_body()` fixtures and
  `TestModBodyVertices` (9 tests). Full suite: **616 tests, all green**
  (607 baseline + 9). Nothing written to the game; no game data committed.
- Found (**E-094**), read-only on the install:
  - **The payload opens with a vertex array.** Reading `f32[3]` triples from the
    block payload (`+0x2C`) shows the first `count` triples (the descriptor's own
    count field) read as coordinates and the next `count` triples are
    **unit length**. Worked example `em013.pac` slot 8 (`count = 36`): positions
    `(2.3638, -0.0, 0.0454)` � `(0.0, -1.7709, -0.7894)` at payload+0x00, unit
    triples `(0.2224, 0.0, 0.9750)` � `(0.0, -0.7315, -0.6818)` at payload+0x1B0,
    then a run of 36 u32 `0x400` at payload+0x3F0 = **28 bytes per vertex**.
  - **Census (1,535 blocks):** 502 contain a run of >= 8 unit triples; 305 start
    at exactly `count`, 431 within `count` � 1, 418 have run length == `count`.
    The **689** blocks with `count == 4` (all tag `0x8001`) contain **none** � a
    different shape, recorded not explained.
  - **Correction to E-093:** the interior offsets are **not** array boundaries.
    In `em013.pac` slot 2 (`count = 230`) a uniform run of 230 u32 `0x400`
    (body+0x19EC..0x1D84) **straddles `offset_a = 0x1A10`**, so E-093's
    [INFERRED] "three consecutive regions" split is not supported by the bytes;
    `ModBodyBlock.regions` is now documented as arithmetic, not a content claim.
  - **[INFERRED]/[UNKNOWN]:** positions/normals *meaning* and the `0x400` run
    (a likely Q10 `1.0`, unproven) stay marked; the position array's length is
    not always exactly `count` (slot 2's triple at k=230 is `(0,0,-0.8774)`).
- Docs: E-094 in `docs/EVIDENCE.md`; `docs/FORMATS.md` �5.1 gains the
  "E-094 update" subsection and the E-093 correction; `docs/BACKLOG.md` F1 row
  updated (evidence cell adds E-094, status rewritten).
- Next: the block's **residual arrays** � the 4-byte field between the normals
  and the `0x400` run, and the `0x1F`/`0x12` words after it � are the fresh lead,
  alongside the descriptor tag (`0x8001`/`0x8002`/`0x8008`�). F4 stays blocked on
  the engine route and is not re-spun; F2/F3/F5/F6/F8 and the GoW3R clip leaf
  encoding (F9) remain available.

---

## 2026-10-18 — F1 bounded slice: the 4-byte-per-vertex field is two u16s; the `0x400` run is not general (E-095)

- Did: picked the critical path **F1** (issue #1) and followed E-094's own stated
  next step — "the 4-byte field between the normals and the `0x400` run". Read the
  residual arrays read-only across all `*.pac` files under
  `G:\Games\Devil May Cry HD Collection\data\dmc3\GData.afs\` (286 `MOD ` chunks).
  Added `block_attributes()` and `ModBodyBlock.attribute_offset()` plus the
  `BODY_BLOCK_ATTRIBUTE_UNIT = 0x18` / `BODY_BLOCK_ATTRIBUTE_SIZE = 0x04`
  constants to `tools/dmc3/mod.py`, exported from `dmc3`; gave
  `tests/fixtures.py`'s `mod_vertex_block()` / `mod_vertex_directory_body()` an
  `attributes` parameter; added `TestModBodyAttributes` (6 tests). Full suite:
  **622 tests, all green** (616 baseline + 6). Nothing written to the game; no
  game data committed. Validated read-only through the new API against the real
  `em013.pac` chunk at file offset 0xFB6E0 (reproduces `(0x06DE, 0x05F1)` ...).
- Found (**E-095**):
  - The four bytes per vertex that E-094 read as one u32 are **two little-endian
    u16s**. Worked example `em013.pac` slot 8 (`count = 36`): bytes at
    `body+0x40C` are `de 06 f1 05` -> u32 `0x05F106DE`, but the pair
    `(0x06DE=1758, 0x05F1=1521)`; then `(0x06DE, 0x0630)`, `(0x0783, 0x0634)`;
    all 72 u16s in `[0x53C, 0x783]`.
  - Census over the **303** blocks whose unit normal run starts exactly at `count`
    and is exactly `count` long: the attribute u16-pair array is constant in only
    **3/303** (so it is genuinely per-vertex); low u16 `< 0x1000` in 299/303, high
    u16 `< 0x1000` in 259/303.
  - **Correction to E-094:** its "run of `count` u32 `0x400` at 28 bytes per
    vertex" is a property of the worked chunk, not the format — on the 303 clean
    blocks only **2** carry an all-`0x400` array at `payload + 28`*count; **115**
    carry all-zero and the modal value is neither. The next array is constant per
    block in 202/303.
  - **[INFERRED]/[UNKNOWN]:** the pair is a per-vertex attribute (UV-consistent
    values, unproven); the next array's meaning and the descriptor tag stay
    unassigned.
- Docs: E-095 in `docs/EVIDENCE.md`; `docs/FORMATS.md` §5.1 gains the "E-095
  update" subsection (and the E-094 correction) and the title gains E-095;
  `docs/BACKLOG.md` F1 row updated (evidence cell adds E-095, status rewritten).
- Next: the next array (`payload + 0x1C*count`, constant per block in 202/303)
  and the `u16 0x1F`/`0x12` fill after it are the remaining residual arrays; the
  attribute values still need engine ground truth or a decoded peer to be named.
  F4 stays blocked on the engine route and is not re-spun; F2/F3/F5/F6/F8 and the
  GoW3R clip leaf encoding (F9) remain available.

---

## 2026-10-18 — F1 bounded slice: the per-vertex record is 32 bytes; the interior offsets are `count` arithmetic (E-096)

- Did: picked the critical path **F1** (issue #1) and followed E-095's own stated
  next step — "the next array (`payload + 0x1C*count`) and the `u16 0x1F`/`0x12`
  fill after it". Read the whole block tail read-only across all `*.pac` files
  under `G:\Games\Devil May Cry HD Collection\data\dmc3\GData.afs\` (the 303
  blocks whose unit-normal run is exactly `(count, count)`). Added
  `block_values()`, `fill_start()`, `ModBodyBlock.value_offset()` /
  `tail_offset()` / `offset_slack()` and the `BODY_BLOCK_RECORD_SIZE = 0x20`,
  `BODY_BLOCK_VALUE_UNIT = 0x1C`, `BODY_BLOCK_VALUE_SIZE = 0x04`,
  `BODY_BLOCK_OFFSET_SLACK = 0x24`, `BODY_BLOCK_FILL_WORDS` constants to
  `tools/dmc3/mod.py`, exported from `dmc3`; added `mod_record_block()` /
  `mod_record_directory_body()` fixtures and `TestModBodyRecord` (8 tests). Full
  suite: **630 tests, all green** (622 baseline + 8). Nothing written to the game;
  no game data committed.
- Found (**E-096**), read-only on the install:
  - **The record is 32 bytes**: position (`0x0C`) + normal (`0x0C`) +
    E-095 u16-pair attribute (`0x04`) + a 4-byte **value** (`0x04`). No
    `0x1F`-fill word occurs before `payload + 32*count` on **303/303** blocks
    (258 start the fill exactly there, 36 later, 9 carry none), so
    `payload + 32*count` is a lower bound on the data.
  - **The descriptor's interior offsets are count arithmetic**, not boundaries:
    `descriptor +0x04 == payload + 28*count + 0x24` on **303/303** and
    `descriptor +0x0C - descriptor +0x04 == 4*count` on **303/303**. This
    **disproves E-093's** "the two interior offsets split the payload into three
    consecutive regions"; `offset_a` is `0x24` bytes into the value array and
    `offset_b` is `0x24` bytes past the record. E-094's `0x400` run is the value
    array.
  - Worked example `em013.pac` slot 1 (`count = 44`): positions
    `(14.2878, 165.8537, -7.5560)`, normals `(0.5088, -0.0501, -0.8594)`,
    attributes `(3719, 2370)`, value array `0x0C040800` x44, fill
    `0x801F801F 0x001F001F …` at `body+0x102C`; validated read-only through the
    new API (`value_offset = 0xF7C`, `offset_a = 0xFA0`, `offset_b = 0x1050`,
    `offset_slack = 0x24`).
  - **[INFERRED]/[UNKNOWN]:** the value array is single-valued per block in
    202/303 (so the per-vertex reading is inferred); the value's meaning, the
    attribute pair, the fill words and why the `0x24` slack exists stay unknown.
- Docs: E-096 in `docs/EVIDENCE.md`; `docs/FORMATS.md` §5.1 gains the "E-096
  update" subsection and the E-093/E-094 correction; `docs/BACKLOG.md` F1 row
  updated (evidence cell adds E-096, status rewritten).
- Next: with positions, normals, the u16-pair attribute and the value array all
  located, the block's remaining unknown is **connectivity** — no index buffer has
  been located, so test the triangle-strip hypothesis (positions ordered as a
  strip, `count - 2` triangles) against a block whose `count` and tail length
  agree, and/or take the 4-byte value / attribute pair to the engine. F4 stays
  blocked on the engine route and is not re-spun; F2/F3/F5/F6/F8 and the GoW3R
  clip leaf encoding (F9) remain available.

---

## 2026-10-18 — F1 bounded slice: the block tail is a `(body-offset, 0)` table, not an index buffer (E-097)

- Did: picked the critical path **F1** (issue #1) and followed E-096's own stated
  next step — "the block's remaining unknown is **connectivity**". Read the bytes
  after the 32-byte-per-vertex record read-only across all `*.pac` files under
  `G:\Games\Devil May Cry HD Collection\data\dmc3\GData.afs\` (286 `MOD ` chunks,
  1,657 non-empty block tails) and censused the descriptor's undecoded fields and
  every block's `offset_c`. Added `BODY_BLOCK_TAIL_ENTRY_SIZE`,
  `BODY_BLOCK_TAIL_MIN_VALUES`, `block_tail()` and `tail_entries()` to
  `tools/dmc3/mod.py`, exported from `dmc3`; added the `mod_tail_block()` /
  `mod_tail_directory_body()` fixtures and `TestModBodyTailEntries` (8 tests).
  Full suite: **638 tests, all green** (630 baseline + 8). Nothing written to the
  game; no game data committed.
- Found (**E-097**), read-only on the install:
  - **The tail is not fill.** After `payload + 32·count` the bytes are pure
    `0x1F` fill in **0/1,657** blocks; **1,305/1,657** carry a run of ≥ 2
    8-byte `(u32 body-offset, u32 0)` entries whose offsets are non-zero,
    16-byte aligned and in-body. **2,619/2,619** targets land inside a data
    block, so the tail is [INFERRED] a block-level cross-reference table; what it
    references is **[UNKNOWN]**.
  - **No index buffer is in the descriptor.** `+0x00`/`+0x20`/`+0x28` are zero
    on **1,665/1,665** records; `+0x04`/`+0x08` are non-zero only on the E-093
    anomaly records (17 and 37). And no block payload read as `u16` is a run of
    valid indices (**0/1,660**); `offset_c` reads as `f32`/vertex bytes, not a
    u16 run.
  - **Recorded inconclusive test:** treating `p[i], p[i+1], p[i+2]` as
    consecutive triangles, the geometric normal agrees with the vertex normal in
    ~50 % of triangles for **237/313** clean blocks (only 23/313 at > 90 %).
    Triangle strips alternate winding, so this neither proves nor disproves strip
    order — recorded so it is not re-run.
  - Worked example `em013.pac` slot 1 descriptor 0 (`count = 44`): the 132-byte
    tail ends `… 0x36, 0, 0, 0, (0x1100, 0), (0x1390, 0)`, both targets inside
    block 1; reproduced read-only through `tail_entries(..., min_offset=block.end)`.
- Docs: E-097 in `docs/EVIDENCE.md`; `docs/FORMATS.md` §5.1 gains the "E-097
  update" subsection and the title gains E-097; `docs/BACKLOG.md` F1 row updated
  (evidence cell adds E-097, status rewritten).
- Next: connectivity is still locatable — the tail's cross-reference table is the
  fresh lead (what does a `(offset, 0)` entry name?), and the `0x36`/`0x08` word
  before it is unexplained; the GoW3R clip leaf keyframe encoding (F9) and
  F3 slots 6/7/11/22 remain available. F4 stays blocked on the engine route and
  is not re-spun.

---

## 2026-10-18 — F1 bounded slice: the first *forward* block-tail entry is the derived `end + 0x50` (E-098)

- Did: picked the critical path **F1** (issue #1) and followed E-097's own stated
  next step — "what does a `(offset, 0)` entry name?". Read block tails
  read-only across all `*.pac` files under
  `G:\Games\Devil May Cry HD Collection\data\dmc3\GData.afs\` (286 `MOD ` chunks,
  1,556 blocks) and split the entries into backward vs **forward** (target `>=`
  `block.end`). Added `BODY_BLOCK_TAIL_NEXT_DELTA = 0x50`,
  `ModBodyBlock.tail_next_target`, `tail_forward_entries()` and `tail_next_ok()`
  to `tools/dmc3/mod.py`, exported from `dmc3`; added the
  `mod_two_block_tail_body()` fixture (16-byte-aligned so a block's end is
  aligned like the install) and `TestModBodyTailNext` (6 tests). Full suite:
  **644 tests, all green** (638 baseline + 6). Nothing written to the game; no
  game data committed. Committed as 09a2073, pushed to origin main; commented
  issue #1 (left open).
- Found (**E-098**):
  - **The first forward tail entry is `block.end + 0x50` on 1,210/1,251 blocks**
    (22 are `+0xA0`, 19 other deltas). `body_blocks()` sets `block.end` to the
    *next* block's `data_offset`, so `end + 0x50` is that block's
    `data_offset + 0x2C + 0x24` = its `payload_offset + 0x24`
    (`0x50 = BODY_BLOCK_PREFIX_SIZE + BODY_BLOCK_OFFSET_SLACK`). The first tail
    entry is therefore a **structural constant offset into the next block**, not
    a free cross-reference — this **narrows E-097's "cross-reference table"**
    reading (only the second entry can be a free reference).
  - **Forward-entry counts per block: 0/1/2/3 = 305 / 38 / 1,204 / 9.**
  - Recorded negatives: the first entry is **not** the next block's
    `offset_a`/`offset_b`/`value_offset`/`tail_offset` (checked on
    `em013.pac` slot 1, where the entry `0x1100` is `next.payload + 0x24` while
    `offset_a`/`offset_b` are `0x1700`/`0x17E0`). Validated read-only through the
    new API: it reproduces 1,556 blocks / 1,251 with a forward entry / 1,210
    `tail_next_ok`.
  - **[UNKNOWN]:** what lives at the target; the second entry's meaning; the
    missing connectivity. E-097's inconclusive winding test is not re-run.
- Docs: E-098 in `docs/EVIDENCE.md`; `docs/FORMATS.md` §5.1 gains the
  "E-098 update" subsection (and the §5.1 title gains E-098);
  `docs/BACKLOG.md` F1 row updated (evidence cell adds E-098, status rewritten).
- Next: the **second** tail entry is now the only non-derived tail value and the
  fresh lead for connectivity — is it a free reference into another block (a
  child/sibling/hierarchy pointer)? Otherwise F3 slots 6/7/11/22 and the GoW3R
  clip leaf keyframe encoding (F9) remain available; F4 stays blocked on the
  engine route and is not re-spun.

---

## 2026-10-18 — F1 bounded slice: the block tail's last 36 bytes are a 3-offset descriptor (E-100)

- Did: picked the critical path **F1** (issue #1) and followed E-098's own stated
  next step — "what does the second tail entry name?" — by reading the **last 36
  bytes of each block**, read-only across all 194 `*.pac` files under
  `G:\Games\Devil May Cry HD Collection\data\dmc3\GData.afs\` (286 `MOD ` chunks,
  1,556 blocks). Added `BODY_BLOCK_TAIL_TAG_GAP` (0x10),
  `BODY_BLOCK_TAIL_OFFSET_COUNT` (3), `BODY_BLOCK_TAIL_RECORD_UNIT` (0x0C),
  `ModBodyTailDescriptor` and `tail_descriptor()` to `tools/dmc3/mod.py`, exported
  from `dmc3`; added the `mod_tail_descriptor_body()` fixture and
  `TestModBodyTailDescriptor` (7 tests). Full suite: **651 tests, all green**
  (644 baseline + 7). Nothing written to the game; no game data committed.
- Found (**E-100**):
  - The tail ends with a fixed descriptor `[tag][0][0][0][v1][0][v2][0][v3]`.
    On **1,210/1,210** blocks with a derived `v1` (`block.end + 0x50`, E-098) the
    tag word sits exactly 16 bytes before `v1`, the three words after it are zero,
    and `v3` is the block's **final u32** — so its trailing zero word is the
    *next* block's first prefix word.
  - `v2 == v1 + stride` and `v3 == v1 + 2*stride` where
    `stride = align_up(12*n, 16)` and `n = tag & 0xFFFF`, on **1,131/1,210**
    (93.5 %). The tag word's high u16 is a small class id (0..6). `n` equals the
    next record descriptor's `count` on 1,142/1,210 (94.4 %).
  - Worked example `em013.pac` slot 1 block 0 (`count = 44`, `end = 0x10B0`):
    last 36 bytes `36 00 00 00 | 00 x12 | 00 11 00 00 | 00 00 00 00 |
    90 13 00 00 | 00 00 00 00 | 20 16 00 00` = tag `0x36`, `v1=0x1100`,
    `v2=0x1390`, `v3=0x1620`, `stride=0x290`.
  - **So E-098's open question is answered structurally:** the "second entry" is
    `v1 + align_up(12*n, 16)`, not a free cross-reference, and E-097 could only
    ever see two in-tail entries because `v3` straddles the block boundary.
  - **[UNKNOWN]:** the meaning of `n`, the class id and the three target regions.
    The regions do **not** read consistently as positions/normals (region-1
    unit-length fraction is bimodal 0.0/0.8), so no content semantics are claimed.
- **ID collision handled:** the entry was drafted as E-099 but a parallel writer
  committed E-099 (a GoW3 mesh-group finding, `c9d2af2`) mid-slice; this entry
  takes the next free id, **E-100**, and all code/doc references were renumbered.
- Docs: E-100 in `docs/EVIDENCE.md`; `docs/FORMATS.md` §5.1 gains the "E-100
  update" subsection and the title gains E-100; `docs/BACKLOG.md` F1 row updated
  (evidence cell adds E-100, status rewritten). No game data committed.
- Next: `n` and the class id are the fresh lead — correlate `n`/`class_id` with
  the next block's descriptor (`count`, tag) to name the descriptor, and trace
  the three targets. F4 stays blocked on the engine route and is not re-spun;
  F3 slots 6/7/11/22 and the GoW3R clip leaf keyframe encoding (F9) remain
  available.

---

## 2026-10-18 — F1 bounded slice: tail descriptors are forward references inside the next block at a fixed `+0x24` (E-101)

- Did: picked the critical path **F1** (issue #1) and followed E-100's own stated
  next step — "correlate `n`/`class_id` with the next block's descriptor and trace
  the three targets". Read the block tails read-only across all 194 `*.pac` files
  under `G:\Games\Devil May Cry HD Collection\data\dmc3\GData.afs\` (286 `MOD `
  chunks, paired each accepted descriptor with the block that follows). Added
  `BODY_BLOCK_TAIL_TARGET_SHIFT` (0x24), `tail_descriptor_spacing(count)` and
  `ModBodyTailDescriptor.spacing_ok_for(count)` / `expected_offsets_for(count)` to
  `tools/dmc3/mod.py`, exported from `dmc3`; added
  `TestModBodyTailForwardReference` (6 tests) to `tests/test_mod.py`. Full suite:
  **657 tests, all green** (651 baseline + 6). Nothing written to the game; no game
  data committed.
- Found (**E-101**), read-only on the install (1,210 accepted descriptors):
  - **`v1 - next.payload_offset == 0x24` on 1,210/1,210** and **`v3 <= next.end`
    on 1,210/1,210** — all three targets sit inside the *immediately following*
    block at a fixed `+0x24` (`= BODY_BLOCK_TAIL_NEXT_DELTA 0x50 − prefix 0x2C`,
    the same `BODY_BLOCK_OFFSET_SLACK` of E-096). So the descriptor is a forward
    reference *within the next block*, refining E-097/E-098's "cross-reference".
  - **Refinement of E-100:** the spacing is better predicted by the **next
    block's count** — `align_up(12 * next.count, 16)` fits **1,148/1,210**
    (94.9 %) vs E-100's own-`n` `align_up(12 * n, 16)` at 1,131/1,210 (93.5 %).
    `n == next.count` on 1,142/1,210; the 62 that match neither spacing are all
    still equally spaced at another stride. Meaning of either count [UNKNOWN].
  - **Disproved hypothesis:** the `+0x24` is **not** a three-`f32[3]` payload
    prefix — on the 511 blocks with a unit run the normals still start at triple
    index `count` (305) / `count±1` (126), not `count+3` (3), and the payload's
    first three triples are unit on 0/511. E-094/E-096's "positions start at
    `payload + 0`" stands, so the descriptor's regions are *not* the next block's
    positions/normals at their starts; what they name is [UNKNOWN].
  - **Negative:** the class id (0..6; `0`×940, `1`×161, `2`×70, `3`×27, `4`×9,
    `5`×2, `6`×1) is **not** the block's own or the next block's record tag (both
    mostly `0x8001`); `next.count - n` is 0 for 928/940 of class 0 and 0/1/2 for
    classes 1–3.
- Docs: E-101 in `docs/EVIDENCE.md`; `docs/FORMATS.md` §5.1 gains the "E-101
  update" subsection (and the §5.1 title gains E-101); `docs/BACKLOG.md` F1 row
  updated (evidence cell adds E-101, status rewritten).
- Next: what the three regions *name* is still the F1 gap and is not decodable by
  correlation alone; the class id and `n` remain unnamed. F4 stays blocked on the
  engine route and is not re-spun; F3 slots 6/7/11/22 and the GoW3R clip leaf
  keyframe encoding (F9) remain available.

