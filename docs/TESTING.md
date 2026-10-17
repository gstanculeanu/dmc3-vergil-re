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

## Smoke test before the real work

Do **not** start by porting Vergil. First prove the loop end-to-end with a change
so trivial it cannot fail for asset reasons:

1. Unpack the target boss's `R_<Boss>.WAD`.
2. Change one obvious pixel — e.g. tint a texture bright green.
3. Repack, drop it in `mods\`, `-Isolate` the save before that boss, `-Play`.
4. Expected: **the game loads, the boss still spawns, the health bar still
   appears, and the tint is visible.**

That single test validates mod install, WAD replacement, the save shortcut and the
boss health bar all at once. Only then is it worth feeding Vergil's mesh through.

## Open decision: which boss

The replacement target must be reachable quickly. Candidates from the WAD
inventory (E-016):

| Boss | Archive(s) | Reachable from the saves above? |
|---|---|---|
| Zeus | `R_ZEUS00..60` — **six** variants | final boss; not reachable at 1:19 |
| Hades | `R_HADES`, `R_HADESBIG` | near `Realm of Hades` / `The Depths of Hades` |
| Hercules | `R_HERCULES`, `R_HERCULES10` | mid-game |
| Cronos | `R_*` — level `CRN###` | mid-game |
| Poseidon | `R_POSEIDON00`, `R_POSMAIN00` | prologue; needs a new game |
| Helios / Hermes | `R_HELIOS`, `R_HERMES` | mid-game |

**This needs the owner's knowledge:** which of the observed saves is *immediately*
before a boss? That save becomes the standing test point and decides the target.

Note that a boss with **multiple variants** (Zeus has six; Hercules two) is
attractive because it implies multi-phase data — but it is not testable until it
is reachable.

## Why this matters beyond convenience

A tight loop is what makes the remaining Phase 3 work tractable at all:

* the WAD container can be iterated on against the *running game* rather than
  inferred in the abstract;
* a wrong guess about the mesh format shows up as a visibly broken boss within a
  minute;
* the health bar requirement (G7) can be confirmed or refuted with one test.
