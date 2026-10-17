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


