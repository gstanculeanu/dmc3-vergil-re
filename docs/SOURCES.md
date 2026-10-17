# Sources and links

## Supplied by the project owner

* **`FelipePrado0/gow3_pc`** — God of War III Remastered PC port; the reference for
  how GoW3 was ported to PC (Phase 3 target and mod-system definition).
  <https://github.com/FelipePrado0/gow3_pc>
* **REA — Reverse Engineer Anything (`morluto/rea`)** — methodological inspiration
  for this repository: route the target, work evidence-first, keep observation
  apart from inference, and maintain a finding ledger.
  <https://github.com/morluto/rea/>
* **Bloodborne — Vergil (Nexus mod 229)** — Vergil already decompiled and ported
  into a different PS4 game. The model side is solved elsewhere; per the owner,
  "the moves and things are left". <https://www.nexusmods.com/bloodborne/mods/229>

## DMC3 reverse-engineering and modding references

* **Infernal Works — File ID / Motion Identification thread** —
  <https://infernalwarks.boards.net/thread/248/file-motion-identfication-thread>
  (community motion-ID → move-name map; feeds `docs/ANIMATIONS.md`)
* **DDMK (Style Switcher) by serpentiem** — <https://github.com/serpentiem/ddmk>
  (DMC3 HD mod loader; explains the loose `GData.afs` folder, E-011)
* **Devil Sword Vergil Yamato — DMC3 HD Collection (Nexus 25)** —
  <https://www.nexusmods.com/devilmaycryhdcollection/mods/25>
  (worked model port *into* DMC3 HD; notes a vertex/file-size stability budget)
* **DMC4SE — DMC3 Vergil moves + Nero Angelo moves** —
  <https://devilmaycry.org/threads/dmc4se-mod-dmc3-vergil-moves-nero-angelo-moves.21869/>
  (prior art for moving Vergil's move set between games)
* **Bloodborne modding (PSX-Place)** —
  <https://www.psx-place.com/threads/bloodborne-modding.35980/>
  (playable-NPC mods with full move sets)

## Referenced by `gow3_pc` and the GoW3 port

* **shadPS4** — PS4 emulator; its Vulkan video core renders GoW III in the port.
  <https://github.com/shadps4-emu/shadPS4>
* **`cuesta4/shadPS4`, branch `eltutz`** — God of War III rendering fixes.
  <https://github.com/cuesta4/shadPS4/tree/eltutz>
* **`Supermedo/bloodborne_pc`** — the Windows port lineage `gow3_pc` forks.
  <https://github.com/Supermedo/bloodborne_pc>
* **`deadinside28/bloodborne_pc`** — the original native port.
  <https://github.com/deadinside28/bloodborne_pc>
* **`gow3_pc` mod documentation** — mod folder layout used by Phase 3.
  <https://github.com/FelipePrado0/gow3_pc/blob/main/docs/MODS.md>
* **shadPS4 GoW III cheats/patches PR** (resolution, texture fix, 120 FPS, skip
  videos; built on illusion0001's PS3 patches) — <https://github.com/shadps4-emu/ps4_cheats/pull/145>
* **GoldHEN Cheat Repository** — source of the port's cheats.
  <https://github.com/GoldHEN/GoldHEN_Cheat_Repository>

## Local paths for this workspace

* DMC3 HD Collection: `G:\Games\Devil May Cry HD Collection`
* DMC3 asset root (unpacked): `G:\Games\Devil May Cry HD Collection\data\dmc3\GData.afs`
* GoW3 Remastered dump (CUSA01715, EU): `C:\Users\GigelCastel\Desktop\gow3\CUSA01715`
* GoW3 PC port working copy: `C:\Users\GigelCastel\Desktop\gow3\gow3-windows`

## Third-party tools worth knowing about

* **Blender** (glTF importer) — verification for Phase 1 exports.
* **Noesis / texconv / GIMP** — DDS inspection for the texture pipeline.
* **xdelta3** — present in the DMC3 install; used by the mods already applied.

> No links to redistributed game assets are included, by design.
