# God of War III Remastered — target notes

Phase 3 target. Everything here is context for the *final* hop; no GoW3 reverse
engineering has been performed yet, so nothing below is an observation — it is a
plan of attack, sourced from public documentation.

## The port

`FelipePrado0/gow3_pc` — <https://github.com/FelipePrado0/gow3_pc>

* A **PC port** of GoW III Remastered (PS4). The original x86-64 game code runs
  natively on the CPU; a custom runtime replaces the PS4 system libraries. No CPU
  emulation.
* Graphics run on **shadPS4**'s Vulkan video core with `cuesta4`'s GoW III fixes
  (branch `eltutz`).
* Tested title IDs: **CUSA01623** (US) and **CUSA01715** (EU).
* Local dump for this project: `C:\Users\GigelCastel\Desktop\gow3\CUSA01715`.

## How mods are delivered (from `gow3_pc` `docs/MODS.md`)

This is the interface the Phase 3 exporter must target.

```
mods/
  Vergil/
    dvdroot_ps4/...          <- files that replace game files, path-for-path
```

Rules that constrain the design:

* A mod is a folder under `mods/`, or a `.zip` dropped there (auto-extracted).
  `mods/<Name>/app0/dvdroot_ps4/...` and one extra nesting level are also accepted.
* Case-insensitive path matching against the game's own paths.
* Files are **never** modified in place: the launcher builds a symlink tree
  (`out/mod-game-*`) and `/app0` is read-only.
* A mod **cannot** replace `eboot.bin`, `sce_module` or `sce_sys`; DLL injectors
  and script plugins are unsupported. Symlinks inside a mod are refused.
* Two mods replacing the same file are not merged — the last one wins whole.
* A mod may also ship **code patches** as XML in its `patches/` folder using
  `Pattern`/`At` signatures. A patch named `Resolution Patch - <w>x<h>` becomes a
  render-resolution option.
* `<game folder>-mods/dvdroot_ps4/...` (the shadPS4 convention) is also honoured
  and takes precedence over the mods list.

**Consequence for this project:** replacing Vergil-for-Kratos means finding the
GoW3R character asset files that live under `dvdroot_ps4/` inside the game dump,
reproducing their format, and shipping them as a mod folder. Nothing about the
executable is touched.

## Correction: AI *is* data (E-022)

An earlier version of this document argued that because a mod cannot use DLL
injectors or script plugins, "a mod cannot author new AI". That is **too
pessimistic**, and the evidence now says so.

`R_*.WAD` files are named-object archives. A `R_<Name>.WAD` (the entity) holds the
model, textures, animation and object pools, while the small per-enemy
`<LEVEL>AI#<Name>.WAD` files hold **`hfsm*` — the behaviour state machines**:

| WAD | `hfsm*` state-machine names |
|---|---|
| `HDS675AI1HADES.WAD` (47,136 bytes) | `hfsmBreakable`, `hfsmEnemy1`, `hfsmIO_Misc` |
| `R_SWORD00.WAD`, `R_HERCULES.WAD`, `R_HERCULES10.WAD` | **none** |

So behaviour is **data in a replaceable file**, not compiled logic. The entity/AI
split is exactly the seam a boss port wants: Vergil's **model** can come from one
WAD while the **behaviour** comes from the existing boss's AI WAD — or from an
authored one.

What remains genuinely impossible via mods is adding **new UI** (the health bar
widget itself) — which is precisely why replacing an existing boss is still the
right first target: it inherits the bar.

## The health bar, and why Vergil must replace a boss

You asked for Vergil to be a boss **with a health bar**. That single requirement
decides the whole Phase 3 strategy, because of how `gow3_pc` mods work:

* A mod replaces data files under `dvdroot_ps4/`, path for path.
* A mod **cannot** replace `eboot.bin`, `sce_module` or `sce_sys`, and cannot use
  DLL injectors or script plugins.

A health bar is not a data file you can drop in — it is UI owned by the game's
code, driven by the encounter. **Therefore a mod cannot create a new boss with a
new health bar.** It can only replace the *content* of an existing one.

GoW3R already ships boss encounters, and each brings:

| Comes free with the replaced boss | Consequence for us |
|---|---|
| Boss health bar (with its own styling and name plate) | The requirement is met by inheritance |
| Intro / outro cinematics and arena trigger | No new scripting needed |
| Phase logic (health thresholds, enrage) | Vergil can keep multi-phase behaviour |
| Camera work and lock-on rules | Reads as a real boss fight |
| Spawn data, collision, hurtboxes | No new gameplay code |

So the plan is: **pick an existing sword-wielding GoW3R boss, and replace its
mesh, skeleton/animations, materials, audio and VFX with Vergil's.** The health
bar, the arena and the phases come along automatically.

Open questions that follow, tracked as issues **G6**, **G7** and **G10**:

1. Which bosses exist in GoW3R, and which wield a blade? → **answered** by E-016
   (`R_HERCULES`, `R_HADES`, `R_HELIOS`, `R_HERMES`, `R_POSEIDON00`, `R_ZEUS00..60`).
2. Which one has a rig and an animation budget that can accept Vergil's mesh and
   move set? → **target chosen: Hades** (G6 answered). The owner has a save
   immediately before that fight, so it is testable in one click, and Hades is a
   large humanoid.

## Target locked: Hades

| | |
|---|---|
| Pre-fight save | `SD-261017161301` — `Hades' Palace`, play time 1:43:35 |
| Entity WAD (model) | `R_HADES.WAD` — 85,727,632 B, banner `WAD_R_Hades`, 6 `DC_` markers, **no AI** |
| Big variant | `R_HADESBIG.WAD` — 82,873,312 B; `R_HADESBIGSOUL.WAD` — 13,649,648 B |
| AI WAD (behaviour) | `HDS675AI1HADES.WAD` — 47,136 B, `hfsmEnemy1`, `hfsmBreakable`, `hfsmIO_Misc` |
| Health-bar name | the string `Hades` in `R_LANG_EN.WAD` |

This is the ideal shape for the plan: the **model** is one file, the **behaviour**
is another, and the **name** is a third — all replaceable, and all testable from
one save one click from the fight.

## The asset registry: `WadGraph` (E-021)

`DEPENDENCYGRAPH.IFF` contains a NUL-separated **name registry** — 3,693 names,
matching the on-disk WADs case-insensitively:

| Group | Count | Examples |
|---|---|---|
| Entities | 100 `R_*` | `R_Hercules`, `R_Hades`, `R_Zeus50`, `R_KratosFear` |
| Actors / AI | ~50 `AR*` | `ARGrunt00`, `ARGrunt00X22`, `ARCerberus00`, `ARMedusa00` |
| Levels | ~200 | `Bas100`, `Hds675`, `Oly200`, `Cav300`, `Crn100` |
| **Audio** | 2,109 `.xvag` | `Amb_Cronos_v1.xvag`, `Bas400TitanHeliosBattle01A.xvag` |
| **Placeholders** | **3,344 `Stub_NNNN`** | `Stub_0000` … `Stub_3343` |

Two things matter here:

* **Audio is registered by name**, so Vergil's voice (F10) needs a registry entry
  as well as a file.
* **Thousands of `Stub_` slots exist.** That is the strongest evidence so far that
  a genuinely **new** entity could be added rather than only replacing one (G8).
  Whether a stub can be renamed and pointed at a new WAD is the open question in
  **G10**.

## Dump layout — assets located (G1 answered, E-016)

`C:\Users\GigelCastel\Desktop\gow3\CUSA01715` is **complete: 50.5 GB**.

```
eboot.bin            4,581,119 bytes     (code only — no art)
sce_discmap.plt       3,288,792 bytes
sce_module/  sce_sys/
ENGLISH/ DUTCH/ FRENCH/ GERMAN/ ITALIAN/ POLISH/ PORTUGUESE/ RUSSIAN/ SPANISH/   ~640 MB each
EXEC/               45.9 GB
  ├─ WAD\PS4_LE\    417 *.WAD, 21.5 GB   <-- ALL game asset archives
  ├─ CINEMATICS\    *.BSF (bonus videos, up to 4.1 GB each)
  ├─ SOUNDS\  ICONS\  INTRO\  photomode\  DEV\  DLC\
```

Every WAD begins with a banner like `"WAD_R_Hercules"`. The layout is
**per-entity**:

| What | Archive(s) |
|---|---|
| Bosses | `R_HERCULES`, `R_ZEUS00..60`, `R_HADES`, `R_HELIOS`, `R_HERMES`, `R_POSEIDON00`, `R_POSMAIN00` |
| Regular enemies | `R_GRUNT00..20`, `R_CYCLOPS00..40`, `R_MINOTAUR00..20`, `R_SIREN00`, … |
| Kratos | `R_KRATOSFEAR`, `R_SOULKRATOS` |
| **Weapons** | `R_SWORD00`, `R_SHIELD00`, `R_SPEAR00`, `R_AXE00`, `R_CESTUS0..4` |
| **UI** (health bar art) | `R_UI.WAD` |
| **Text**, 16 languages | `R_LANG_EN.WAD`, `R_LANG_DE.WAD`, … |
| Effects | `R_FX.WAD`, `R_W_*` |
| Levels | `HDS###`, `OLY###`, `CAV###`, `BAS###`, `GAZ###`, `POS###` |
| **Per-enemy AI/encounter** | `<LEVEL>AI#<Name>.WAD` — e.g. `HDS675AI1HADES`, `BAS400AI4HELI`, `GAZ100AI1PANDZEUS` |
| Manifest | `DEPENDENCYGRAPH.IFF` (contains `"WadGraph"`) |

The existence of tiny per-enemy `*AI*.WAD` files is the single most encouraging
finding for this project: it suggests **enemy behaviour is data-driven**, not
compiled into `eboot.bin`.

## New boss, or replacement?

The owner asked whether Vergil could be an entirely **new** boss rather than a
replacement. Evidence-based answer: **plausible, and more plausible than it first
looked — but strictly harder, and it hinges on three unknowns.**

What the mod system allows (from `gow3_pc` `docs/MODS.md`):

* Mods may **replace** game files *and* **add** files — the load log reports
  `"Mods: N game files replaced, M added"`. So dropping a new `R_VERGIL.WAD` is
  not blocked by the loader.
* Mods **may not** replace `eboot.bin`, `sce_module` or `sce_sys`, and may not use
  DLL injectors or script plugins. (In-memory *patches* to `eboot.bin` are
  possible via signature-matched XML, but authoring new behaviour in machine code
  is not realistic.)

What a new boss additionally needs, and what is unknown:

| Requirement | Known? | Where it would live |
|---|---|---|
| The game loads the new WAD | **Unknown** | `DEPENDENCYGRAPH.IFF` (`WadGraph`). If the runtime enumerates WADs from it, a mod can register one. Issue G8. |
| Something spawns the entity in a level | **Unknown** | level WAD (`HDS###`, …) spawn/encounter data. Issue G8. |
| The game treats it as a **boss** (health bar, intro, phases) | **Unknown** | either a flag in encounter/AI data, or hardcoded. Issue G8/G7. |
| Its name shows on the bar | **Likely yes** | `R_LANG_*.WAD` — a text file a mod can replace (G7). |
| Arena / camera / intro | **Unknown** | level + encounter data |

By contrast, **replacement** needs none of those: the existing boss already has the
health bar, arena, phases, camera and spawn. It only needs the entity's WAD
contents swapped.

**Recommendation.** Do **replacement first** — it is the shortest path to exactly
what was asked (Vergil, as a boss, with a health bar on screen). Investigate the
new-boss route in parallel (G8); if `WadGraph` and the spawn data turn out to be
editable, promoting to a new boss later costs nothing extra, because the Vergil
assets and converters are identical either way.

## Open questions (tracked as issues)

1. ~~**G1** — Where do GoW3R character meshes/materials live?~~ **ANSWERED**
   (E-016): per-entity `R_*.WAD` in `EXEC/WAD/PS4_LE/`.
2. **G2** — What is the internal format of a `R_*.WAD` (directory, mesh, texture)?
3. **G9** — Decode the WAD container and the `WadGraph` manifest.
4. **G8** — Can a *new* entity be added: does `WadGraph` register WADs at runtime,
   and is level spawn/encounter data editable?
5. **G7** — Does the boss health bar read its name from `R_LANG_*.WAD`, and can it
   read "Vergil"?
6. **G3** — Kratos's rig is not Vergil's rig. Retarget, or replace the whole
   skinned mesh? (Bosses like `R_HERCULES` are humanoid, which helps.)


## Method

Do not guess. When Phase 3 starts, apply the same loop used for DMC3: locate the
container, record bytes, decode the header, validate against multiple files, then
write the spec before writing the exporter. See `FORMATS.md` for the template and
`EVIDENCE.md` for the ledger format.

### Engine ground truth (E-053, E-056)

The WAD **record opcodes are numeric constants in code** (E-053), so the container
loader cannot be found by searching the executable for opcode names. The route is
the reverse: the prepared image `out/eboot.elf` carries program headers that map
file offsets to virtual addresses (`vaddr = file_offset − 0x4000` in the
executable segment), and `tools/gow3/eboot.py` lists the code that references a
named loader string (`WAD_`, `hfsm`, `DEPENDENCY`, `.wad`). That code is where the
numeric opcodes and the directory→bulk binding live — the remaining [UNKNOWN] for
G9/G10.
