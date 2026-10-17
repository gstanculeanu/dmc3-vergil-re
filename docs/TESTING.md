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

## The staged test plan (no save sits before a boss)

Owner's answer: **none of the existing saves is immediately before a boss.** So the
loop is built in stages, each testable from where the game already is. Only the
last stage needs a boss.

### Stage 1 — "does a mod swap land at all?" (no boss, no enemy hunting)

Replace a texture inside **`R_UI.WAD`** (27.8 MB, the HUD's art) — for example tint
an orb or meter icon. The HUD is on screen the moment any save loads, so the result
is visible **within two seconds of loading, standing still, from any save.**

Validates: mod folder is picked up → a replaced `R_*.WAD` really loads → the game
still runs. No boss, no walking, no enemies.

### Stage 2 — "can we change a character?" (no boss)

Replace a **common enemy** — `R_GRUNT00` (grunts appear in many levels),
`R_SOLDIER00`, `R_SIREN00`, `R_CYCLOPS00`. Load any combat save and look at the
enemy in front of you. This proves mesh/texture replacement on a *character* rather
than on UI.

### Stage 3 — the boss and its health bar (needs a pre-boss save)

**This is the one-time cost the owner must pay once:** when next playing, save
*immediately before a boss* and tell me the slot name. From then on every iteration
is a single click. Until that save exists, the boss health bar requirement (G7)
cannot be verified — but nothing else is blocked by it.

Then: tint the boss green (`R_HERCULES`, `R_HADES`, …) and confirm the four
checks — loads, boss spawns, **health bar appears**, change is visible.

### Stage 4 — Vergil

Only after Stages 1–3 pass is it worth feeding Vergil's mesh through the converters.

## Choosing the boss (deferred)

Since the target is "whichever is reachable", the boss is chosen once the pre-boss
save exists. Candidates (E-016):

| Boss | Archive(s) | Note |
|---|---|---|
| Zeus | `R_ZEUS00..60` — **six** variants | the only boss with a real sword; likely multi-phase |
| Hercules | `R_HERCULES`, `R_HERCULES10` | humanoid, two variants |
| Hades | `R_HADES`, `R_HADESBIG` | owner has saves in his realm |
| Chronos | level `CRN###` | the `CRN` levels are his |
| Poseidon | `R_POSEIDON00`, `R_POSMAIN00` | prologue; needs a new game |

The user's saves sit in the **Hades** section (`Realm of Hades`, `The Depths of
Hades`, `The Three Judges`), and `HDS675AI1HADES.WAD` places the Hades encounter at
level `HDS675`. If the next save lands near `HDS675`, **Hades is the natural
target**; otherwise the boss nearest wherever the pre-boss save is taken wins.

## Why this matters beyond convenience

A tight loop is what makes the remaining Phase 3 work tractable at all:

* the WAD container can be iterated on against the *running game* rather than
  inferred in the abstract;
* a wrong guess about the mesh format shows up as a visibly broken character
  within a minute;
* the health bar requirement (G7) can be confirmed or refuted with one test.

