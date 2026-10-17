# Sources and links

## Supplied by the project owner

* **`FelipePrado0/gow3_pc`** — God of War III Remastered PC port; the reference for
  how GoW3 was ported to PC (Phase 3 target and mod-system definition).
  <https://github.com/FelipePrado0/gow3_pc>
* **REA — Reverse Engineer Anything (`morluto/rea`)** — methodological inspiration
  for this repository: route the target, work evidence-first, keep observation
  apart from inference, maintain a finding ledger.
  <https://github.com/morluto/rea/>

## Referenced by the above

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
