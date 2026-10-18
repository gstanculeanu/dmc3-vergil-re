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


