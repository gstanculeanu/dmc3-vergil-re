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

## Dump layout observed locally

`C:\Users\GigelCastel\Desktop\gow3\CUSA01715`:

```
eboot.bin            4,581,119 bytes
sce_discmap.plt       3,288,792 bytes
sce_module/
sce_sys/
DUTCH/ ENGLISH/ FRENCH/ GERMAN/ ITALIAN/ POLISH/ PORTUGUESE/ RUSSIAN/ SPANISH/
```

The language folders are the only bulky payload at the top level, so the game's
art assets are almost certainly **inside `eboot.bin`** or in a container the port
mounts as `dvdroot_ps4`. Locating them is issue **G1**.

## Open questions (tracked as issues)

1. **G1** — Where do GoW3R character meshes/materials live, and in what container?
2. **G2** — What is that container's format (geometry, skinning, textures)?
3. **G3** — Kratos's rig is not Vergil's rig. Retarget Vergil's animations onto
   Kratos's skeleton, or replace the whole skinned mesh and keep the animation
   set? Trade-offs are unknown until G1/G2 land.
4. **G5** — Does the port accept an added (not replaced) asset, and how are
   in-game references made? If not, a mod must replace an existing character.

## Method

Do not guess. When Phase 3 starts, apply the same loop used for DMC3: locate the
container, record bytes, decode the header, validate against multiple files, then
write the spec before writing the exporter. See `FORMATS.md` for the template and
`EVIDENCE.md` for the ledger format.
