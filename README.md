# dmc3-vergil-re

Reverse-engineering project that **decompiles Vergil's model out of _Devil May Cry 3_ (HD
Collection)**, exports it to portable interchange formats, and — the end goal — brings it into
**_God of War III Remastered_ (PS4)** through the GoW3 PC port's mod system.

This is a reverse-engineering project first and a port second. Every format claim in `docs/` is
tied to a byte-level observation from a real shipped artifact, and the line between what we
**observed**, what we **infer**, and what we still **do not know** is kept explicit.

## Links, inspiration and prior art

**Supplied by the project owner:**

- **`FelipePrado0/gow3_pc`** — God of War III Remastered PC port. The reference for
  how GoW3 was brought to PC, and the target runtime for the final stage.
  <https://github.com/FelipePrado0/gow3_pc>
- **REA — Reverse Engineer Anything (`morluto/rea`)** — the methodological
  inspiration for this repository: route the target, work evidence-first, separate
  observation from inference, keep a finding ledger.
  <https://github.com/morluto/rea/>
- **Bloodborne — Vergil (Nexus mod 229)** — <https://www.nexusmods.com/bloodborne/mods/229>
  — prior art proving Vergil has **already been decompiled and dropped into a
  different PS4 game** (Bloodborne). The model side is therefore largely solved by
  someone else; per the owner, *"the moves and things are left"*. Bloodborne is
  also the same port lineage as `gow3_pc`, and Bloodborne mods use the same
  `dvdroot` folder-replacement convention GoW3R does — so what is learned there
  transfers.

**Prior art discovered while investigating:**

- **Infernal Works — File ID / Motion Identification thread** —
  <https://infernalwarks.boards.net/thread/248/file-motion-identfication-thread> —
  community mapping of DMC3 PAC motion IDs to move names, including Vergil's
  Yamato Combo, Rapid Slash, Judgement Cut, Judgement Cut Storm, Round Trip, Air
  Trick, Stinger and taunts. Seeds `docs/ANIMATIONS.md` and largely unblocks F7.
- **DDMK (Style Switcher) by serpentiem** — <https://github.com/serpentiem/ddmk> —
  the DMC3 HD mod loader that unpacks `GData.afs` into a folder of loose `.pac`
  files and overlays replacements. Explains this install's layout (E-007, E-011).
- **Devil Sword Vergil Yamato (DMC3 HD, Nexus 25)** —
  <https://www.nexusmods.com/devilmaycryhdcollection/mods/25> — a worked example of
  porting a model *into* DMC3 HD, including the warning that too many / too
  high-vertex model swaps destabilise the game.
- **DMC4SE — DMC3 Vergil moves + Nero Angelo moves** —
  <https://devilmaycry.org/threads/dmc4se-mod-dmc3-vergil-moves-nero-angelo-moves.21869/>
  — prior art for porting DMC3 Vergil's move set to another game.
- **Bloodborne modding (PSX-Place)** —
  <https://www.psx-place.com/threads/bloodborne-modding.35980/> — playable-NPC mods
  with full move sets; the kind of "moves" work Vergil still needs.
- **shadPS4** — <https://github.com/shadps4-emu/shadPS4> ·
  **`cuesta4/shadPS4` (`eltutz`)** —
  <https://github.com/cuesta4/shadPS4/tree/eltutz> ·
  **`Supermedo/bloodborne_pc`** —
  <https://github.com/Supermedo/bloodborne_pc> ·
  **`deadinside28/bloodborne_pc`** —
  <https://github.com/deadinside28/bloodborne_pc>

## Goal

**Vergil as a boss in God of War III Remastered, complete with a boss health bar.**
That is the destination, and it sets the scope: a boss is not just a mesh. It is a
model, a rig, a move set, behaviour, a weapon, voices, effects and a health bar.
All of it has to come out of DMC3 and go back in.

```
                      decompile                        import
 DMC3 HD Collection ─────────────► neutral form ─────────────► God of War III Remastered
 ┌──────────────────┐              ┌──────────────────┐        ┌──────────────────────────┐
 │ pl021.pac        │  mesh/rig    │ glTF 2.0 (.glb)  │        │ mods/Vergil/             │
 │   MOD / SHW      │  materials   │ PNG textures     │        │   dvdroot_ps4/...        │
 │ pl021_00_0..9    │  moves       │ move/hit tables  │        │ (gow3_pc mod system)     │
 │ plwp_vergilsword │  weapon      │ FBX / OBJ (opt)  │        │                          │
 │ Versil_*.ogg     │  audio       │ WAV/OGG          │        │ replaces an existing     │
 │ snd_*.pac        │  sfx         │ effect data      │        │ enemy — see docs/GOW3.md │
 │ *.tm2            │  textures    │ JSON sidecars    │        └──────────────────────────┘
 └──────────────────┘              └──────────────────┘
        phase 1                          phase 2/3
                                             │
                                             └──► re-import into DMC3 as a sanity round-trip
```

Primary goal is **both**: export now, import later. A correct re-import into DMC3 is the cheapest
proof that the decompile is faithful, so it acts as the validation gate before GoW3 work begins.

### What has to be decompiled

| Asset class | Source in DMC3 | Status | Issue |
|---|---|---|---|
| Mesh + rig + materials | `pl021.pac` (`MOD `, `SHW `, 9 raw chunks) | container decoded, payloads open | F1, F2, F3 |
| Animations (poses) | `pl021_00_0..9.pac` (~108 MOT chunks) | header decoded, encoding open | F4, F5 |
| **Move set** (attack/state definitions) | `pl021.pac` tables + MOT clips | not started | F7, F9 |
| **Enemy behaviour / AI** | unknown — may not be data-driven | not started | F12, G6 |
| Weapon (Yamato) | `plwp_vergilsword.pac` (`PNST`) | **exported** via prior art (E-015) | F6 |
| **Sounds / voice** | `afs/sound/Versil_01..03.ogg`, `snd_*.pac` | located only | F10 |
| **VFX** (Judgement Cut, trails, DT) | `Crimson/vfx/*.efkefc` (Effekseer) | located only | F11 |
| Textures | `*.tm2` (wraps DDS) | decoded | F8, T2 |

### Prior art: the mesh is already decompiled

Someone has already decompiled Vergil and ported him into **Bloodborne** (another
PS4 game). The package sits in `C:\Users\GigelCastel\Desktop\vergil` and contains
Vergil's **body** and **Yamato** as FLVER models **plus Source `.smd`/`.ascii`
interchange meshes** and DDS albedo/normal/roughness/specular textures — details
in `docs/PRIOR-ART.md` (evidence E-014).

Consequences, stated plainly:

* Vergil's **mesh and textures are solved**; they do not need to be decoded out of
  the DMC3 `MOD ` payload. Blender reads SMD/ASCII directly.
* Decoding `MOD ` (F1) and `PNST` (F6) is now a **cross-check**, not a blocker.
* The package's animation data is **Bloodborne's**, not Vergil's moves — which is
  exactly why the owner says *"the moves and things are left"*.
* The critical path therefore moves to **animations and moves** (F4, F9).
* Those files are third-party assets: **never committed here**, and only reusable
  if the mod's permissions allow it (issue H4).


### A constraint that shapes Phase 3

`gow3_pc` mods replace data files under `dvdroot_ps4/` and **may not** replace
`eboot.bin`, `sce_module` or `sce_sys`, nor use DLL injectors or script plugins.
So a mod cannot author new AI or a new UI element.

A **boss with a health bar is exactly the case where this is a gift rather than a
limitation**: GoW3R already contains boss encounters, each with its own health bar,
intro, arena trigger, phase logic and camera work. Replacing an existing
**sword-wielding boss** gives Vergil all of that for free — including the health
bar — while the mesh, animations, audio and VFX are Vergil's.

This is why the target is a *boss replacement*, not a from-scratch enemy. See
`docs/GOW3.md` and issues G6/G7.


## Status

| Area | State | Notes |
|---|---|---|
| DMC3 PAC container format | **Decoded** | Verified against `pl000.pac` and `pl021.pac` |
| Chunk tagging (`MOD `, `SHW `, `MOT\0`) | **Decoded** | Tag + observed header fields |
| Vergil asset map (`pl021`, `pl019`, weapons) | **Decoded** | See `docs/ENTITIES.md` |
| TM2 texture → DDS | **Decoded** | HD-era TM2 wraps a plain DDS blob |
| Vergil's audio location | **Located** | `Versil_01..03.ogg`; ownership unconfirmed |
| Vergil's VFX location | **Located** | Effekseer `.efkefc` in the Crimson tree |
| Vergil's mesh (prior art) | **Available** | Already decompiled into a Bloodborne mod: FLVER + SMD/ASCII + DDS. See `docs/PRIOR-ART.md` |
| Yamato (weapon) export | **Verified** | `tools/priorart/` converts SMD/ASCII → OBJ; 1852 tris, 1.26 m blade (E-015) |
| `MOT` animation payload | **Partial** | Header parsed; frame encoding open |
| `MOD ` mesh payload | **Open** | Header fields known, vertex/index layout open |
| `SHW ` material payload | **Open** | Header fields known, texture binding open |
| Move set / enemy behaviour | **Not started** | Moves are as important as the mesh for an enemy |
| Export to glTF | **Not started** | Blocked on `MOD ` payload RE |
| Import to DMC3 | **Not started** | Validation gate for phase 2 |
| Import to GoW3 Remastered | **Not started** | Blocked on GoW3 model-format RE |

## Repository layout

```
docs/           RE notes, format specs, evidence ledger, roadmap, prior art, animation map
tools/dmc3/     Library: PAC/MOT/TM2 parsers, entity table
tools/          CLI: inventory + extract
tests/          Unit tests (run on synthetic fixtures — no game files needed)
scripts/        The 10-minute autonomous agent loop
```

## Quick start

```powershell
# Parse every PAC/TM2 in a DMC3 install and emit a metadata inventory (no game data stored)
$env:DMC3_GDATA = 'G:\Games\Devil May Cry HD Collection\data\dmc3\GData.afs'
python tools/inventory.py --out inventory.json

# Extract Vergil's assets to a scratch folder (kept out of the repo)
python tools/extract_assets.py --entity pl021 --out D:\re\vergil

# Tests
python -m unittest discover -s tests
```

## Evidence discipline

Adapted from REA:

- **Observation** — a byte pattern read from a shipped artifact, with the file, offset and length.
- **Inference** — a conclusion drawn from observations, with the reasoning stated.
- **Unknown** — an explicit open question. Unknowns become GitHub issues, never silent guesses.

`docs/EVIDENCE.md` is the finding ledger. Format specs in `docs/FORMATS.md` cite ledger IDs.

## Legal

This repository contains **only original tooling and reverse-engineering notes**. No Devil May Cry
or God of War game assets are stored, committed or distributed. `tools/` reads assets from a game
installation you already own and writes derived output to a directory *you* choose, outside the
repository. `.gitignore` refuses common asset extensions as a second line of defence.

Devil May Cry is a trademark of Capcom. God of War is a trademark of Sony Interactive
Entertainment. This project is not affiliated with either.

Tooling in this repository is MIT licensed (see `LICENSE`).
