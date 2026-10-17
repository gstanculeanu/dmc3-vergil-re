# dmc3-vergil-re

Reverse-engineering project that **decompiles Vergil's model out of _Devil May Cry 3_ (HD
Collection)**, exports it to portable interchange formats, and — the end goal — brings it into
**_God of War III Remastered_ (PS4)** through the GoW3 PC port's mod system.

This is a reverse-engineering project first and a port second. Every format claim in `docs/` is
tied to a byte-level observation from a real shipped artifact, and the line between what we
**observed**, what we **infer**, and what we still **do not know** is kept explicit.

## Reference links

Given by the project owner:

- **`FelipePrado0/gow3_pc`** — God of War III Remastered PC port. The reference for how GoW3 was
  brought to PC, and the target runtime for the final stage of this project.
  <https://github.com/FelipePrado0/gow3_pc>
- **REA — Reverse Engineer Anything (`morluto/rea`)** — the methodological inspiration for this
  repository: route the target, work evidence-first, separate observation from inference, and keep
  a finding ledger. <https://github.com/morluto/rea/>

Referenced by the above (not supplied directly, listed for completeness):

- **shadPS4** — PS4 emulator whose Vulkan video core the GoW3 port uses.
  <https://github.com/shadps4-emu/shadPS4>
- **`cuesta4/shadPS4` (`eltutz` branch)** — God of War III rendering fixes used by the port.
  <https://github.com/cuesta4/shadPS4/tree/eltutz>
- **`Supermedo/bloodborne_pc`**, **`deadinside28/bloodborne_pc`** — lineage of the GoW3 port.

## Goal

```
 DMC3 HD Collection                neutral interchange              God of War III Remastered
 ┌──────────────────┐   decompile   ┌──────────────────┐  import   ┌────────────────────────┐
 │ pl021.pac        │ ────────────► │ glTF 2.0 + PNG   │ ────────► │ mods/<Vergil>/         │
 │ plwp_vergilsword │               │ FBX (optional)   │           │   dvdroot_ps4/...      │
 │ *.tm2 textures   │               │ JSON sidecars    │           │ (gow3_pc mod system)   │
 └──────────────────┘               └──────────────────┘           └────────────────────────┘
        phase 1                          phase 2                        phase 3
                                              │
                                              └──► re-import into DMC3 as a sanity round-trip
```

Primary goal is **both**: export now, import later. A correct re-import into DMC3 is the cheapest
proof that the decompile is faithful, so it acts as the validation gate before GoW3 work begins.

## Status

| Area | State | Notes |
|---|---|---|
| DMC3 PAC container format | **Decoded** | Verified against `pl000.pac` and `pl021.pac` |
| Chunk tagging (`MOD `, `SHW `, `MOT\0`) | **Decoded** | Tag + observed header fields |
| Vergil asset map (`pl021`, `pl019`, weapons) | **Decoded** | See `docs/ENTITIES.md` |
| TM2 texture → DDS | **Decoded** | HD-era TM2 wraps a plain DDS blob |
| `MOT` animation payload | **Partial** | Header parsed; frame encoding open |
| `MOD ` mesh payload | **Open** | Header fields known, vertex/index layout open |
| `SHW ` material payload | **Open** | Header fields known, texture binding open |
| Export to glTF | **Not started** | Blocked on `MOD ` payload RE |
| Import to DMC3 | **Not started** | Validation gate for phase 2 |
| Import to GoW3 Remastered | **Not started** | Blocked on GoW3 model-format RE |

## Repository layout

```
docs/           Reverse-engineering notes, format specs, evidence ledger, roadmap
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
