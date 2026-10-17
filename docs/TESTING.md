# Testing: iterate on the boss without replaying the game

Requirement (owner): *"I want it testable each time I enter the game — don't want
to play through the game."*

So the test loop must be: **launch → one click to load → you are standing in front
of the boss → quit.** No chapters, no walking, no cutscenes.

## The mechanism

Every save carries a machine-readable label, so we can pick one that sits right
before a boss and jump straight to it.

`user/savedata/<user>/<TITLE_ID>/<SLOT>.sce_sys/param.bin` holds three fixed
0x80-byte UTF-8 fields (evidence **E-018**):

| Offset | Field | Example |
|---|---|---|
| `0x000` | title | `God of War® III Remastered` |
| `0x080` | **location** | `The Depths of Hades` |
| `0x100` | **details** | `Difficulty: God (Normal)` / `Play time: 0:52:29` |

`tools/gow3/savedata.py` reads that, so the harness can label every save
automatically instead of guessing:

```
SLOT                    KIND       PLAY TIME  PLAYED AT           LOCATION
AUTOSAVE                auto         1:19:33  -                   (Auto Save) Hephaestus
SD-261013182124         manual       0:14:44  2026-10-13 18:21:24 Tomb of Ares
SD-261013183736         manual       0:31:09  2026-10-13 18:37:36 Entrance to Ares Tomb
SD-261013184508         manual       0:38:30  2026-10-13 18:45:08 Realm of Hades
SD-261013185858         manual       0:52:29  2026-10-13 18:58:58 The Depths of Hades
SD-261015184106         manual       1:00:50  2026-10-15 18:41:06 The Three Judges
SD-261015185945         manual       1:19:39  2026-10-15 18:59:45 The Forge
```

**Stashing, not renaming.** To make loading one click, the harness *moves the other
slots out of the way* rather than renaming the target. Renaming would rely on the
game's load order being driven by the folder name, which is unverified — moving the
others out is correct regardless of how the game sorts.

## The tool

```
scripts/boss-test.ps1
```

| Action | What it does |
|---|---|
| `-List` | print the save table above (read-only) |
| `-Isolate <slot>` | back up the saves, then stash every other slot so `<slot>` is the only entry |
| `-Restore` | move the stashed slots back |
| `-InstallMod <path>` | copy a mod folder (or `.zip`) into the port's `mods\` |
| `-RemoveMod <name>` | delete a mod folder from `mods\` |
| `-Play` | launch `Play God of War III.exe` |
| `-IncludeAutosave` | also stash `AUTOSAVE` |
| `-Force` | proceed even if the game is running |

### Typical iteration

```powershell
# once, at the start of a session: pick the slot nearest the boss
powershell -ExecutionPolicy Bypass -File scripts/boss-test.ps1 -List

# every iteration
powershell -ExecutionPolicy Bypass -File scripts/boss-test.ps1 `
    -Isolate SD-261013185858 -InstallMod D:\re\vergil-mod -Play
#   -> press Continue / Load Game; you are at the boss; look at it; close the game

# when finished testing
powershell -ExecutionPolicy Bypass -File scripts/boss-test.ps1 -Restore
```

Each action is appended to `logs/test-loop.log` with a timestamp, so an iteration
can be tied to what was installed.

## Safety

* **The game must be closed.** The script refuses to run while `gow3-probe` or
  `God of War III` is running (override with `-Force`) — moving saves under a
  running game corrupts them.
* **Saves are backed up first.** `-Isolate` copies every slot to
  `user\savedata_backups\boss-test-<timestamp>\` before moving anything.
* **`-Restore` is the undo.** Stashed slots live in
  `user\savedata_backups\boss-test-stash\` until restored.
* Nothing here writes to the game dump. Only the port's own `user\` and `mods\`
  folders are touched.

## The test point is locked: Hades

Owner confirmed a save sits immediately before the **Hades** fight.

| | |
|---|---|
| **Slot folder** | `SD-261017161301` |
| **In-game location** | `Hades' Palace` |
| **Play time** | 1:43:35 |
| **Save time** | 2026-10-17 20:13:02 (local) |
| **Target boss** | **Hades** |
| **Entity WAD** | `R_HADES.WAD` — 85,727,632 bytes, banner `WAD_R_Hades`, **no** AI state machines |
| **AI WAD** | `HDS675AI1HADES.WAD` — 47,136 bytes, `hfsmBreakable`, `hfsmEnemy1`, `hfsmIO_Misc` |
| **Health-bar name** | `R_LANG_EN.WAD` (the string `Hades`) |

Note on timestamps: **slot folder names are UTC, file times are local** (here a
4-hour offset). `SD-261017161301` encodes 16:13 UTC and the file was written at
20:13 local. This matters when matching a slot to a moment the owner describes.

So the loop is now:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/boss-test.ps1 -List
powershell -ExecutionPolicy Bypass -File scripts/boss-test.ps1 `
    -BossTest -InstallMod D:\re\vergil-mod -Play
# -> press Continue / Load Game; you are in Hades' Palace; the fight starts
powershell -ExecutionPolicy Bypass -File scripts/boss-test.ps1 -Restore
```

`-BossTest` isolates `SD-261017161301` for you, so no slot name is needed.

## The staged test plan

Only the last stage needs the boss; earlier stages are testable from any save, and
stage 1 still needs no WAD writer (see G9/G10) — which is the current blocker.

### Stage 1 — "does a mod swap land at all?" (no boss needed)

Replace a texture inside **`R_UI.WAD`** (27.8 MB, the HUD's art) — tint an orb or
meter icon. The HUD is on screen the moment any save loads, so the result is
visible **within two seconds of loading, standing still**.

Validates: mod folder is picked up → a replaced `R_*.WAD` really loads → the game
still runs. No boss, no walking, no enemies.

### Stage 2 — "can we change a character?" (no boss needed)

Replace a **common enemy** — `R_GRUNT00`, `R_SOLDIER00`, `R_SIREN00`,
`R_CYCLOPS00`. Load any combat save and look at the enemy in front of you.

### Stage 3 — Hades (locked above)

Tint `R_HADES.WAD` green (or scale a submesh) and confirm four things:
**loads → boss spawns → health bar appears → the change is visible.**

Then rename the bar to "Vergil" by editing the `Hades` string in `R_LANG_EN.WAD`.

### Stage 4 — Vergil

Only after Stages 1–3 pass is it worth feeding Vergil's mesh through the converters.

## Why this matters beyond convenience

A tight loop is what makes the remaining Phase 3 work tractable at all:

* the WAD container can be iterated on against the *running game* rather than
  inferred in the abstract;
* a wrong guess about the mesh format shows up as a visibly broken character
  within a minute;
* the health bar requirement (G7) can be confirmed or refuted with one test.

