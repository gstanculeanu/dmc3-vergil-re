# Evidence ledger

Each entry records an **observation** (bytes read from a shipped artifact) and,
separately, any **inference** and remaining **unknown**. Format specs in
`FORMATS.md` cite these IDs. Nothing here is a guess presented as fact.

Methodology follows REA: route the target, work evidence-first, keep observation
and inference apart — <https://github.com/morluto/rea/>

Environment for all entries:

* DMC3 asset root: `G:\Games\Devil May Cry HD Collection\data\dmc3\GData.afs`
  (a **directory** in this install; the retail build uses a packed `.afs`).
* Install note: `GData.afs` has been replaced by loose files and the game is
  modded with **Crimson** (`Crimson.dll`, `Crimson/`, plus overlays inside the
  asset folder). See E-007.

---

## E-001 — PAC container layout

**Observation.** `pl000.pac` and `pl021.pac`:

```
pl021.pac  0x00: 50 41 43 00 1B 00 00 00 80 00 00 00 80 98 03 00
                 "PAC\0"      count=27     off[0]=0x80  off[1]=0x39880
           0x08 + 27*4 = 0x74  ->  align_up(0x74, 0x10) = 0x80 == off[0]
pl000.pac  0x00: 50 41 43 00 0F 00 00 00 50 00 00 00 50 B0 02 00
                 "PAC\0"      count=15     off[0]=0x50  off[1]=0x2B050
           0x08 + 15*4 = 0x44  ->  align_up(0x44, 0x10) = 0x50 == off[0]
```

Also confirmed on `pl021_00_0.pac` (59 entries → 0x100), `pl021_00_2.pac`
(5 → 0x20), `pl021_00_6.pac` (2 → 0x10), `pl021_00_9.pac` (1 → 0x10).

**Inference.** `"PAC\0"`, `u32 entry_count`, then `u32 offset[entry_count]`,
16-byte aligned data start. Zero entries are empty slots.

**Unknown.** Whether the container ever stores explicit chunk lengths. None found
so far, so spans are derived from neighbour distance.

---

## E-002 — Chunk tags and the two framings

**Observation.** `"MOD "` appears at byte 0 of `pl021.pac` offset 0x39880
(`4D 4F 44 20 AE 47 81 3F …`). `"SHW "` at byte 0 of offset 0x75470
(`53 48 57 20 00 00 00 3F …`). `"MOT\0"` appears at byte **4** of
`pl021_00_1.pac` offset 0x50 (`50 00 00 00 4D 4F 54 00 …`) — a `u32` 0x50
precedes it.

**Inference.** Two chunk framings exist: plain (tag at 0) and size-prefixed (tag
at 4, preceded by a `u32` that equals the MOT header size).

**Unknown.** Why MOD/SHW are plain while MOT is size-prefixed.

---

## E-003 — MOT header statistics

**Observation.** Scanned every `.pac` in the asset root with the PAC parser:
**194 files, 840 MOT chunks**. Distributions:

```
u32 +0x00 header size : 80 x839, 96 x1
u32 +0x04 magic       : "MOT\0" x840
f32 +0x0C duration    : identical distribution to +0x14 (61.0 x76, 29.0 x32, 60.0 x22, 115.0 x21, …)
u16 +0x18             : 0 x550, 1 x290
u16 +0x1A             : 0 x452, 24 x378, 23 x10
u16 +0x1C             : 24 x821, 23 x18, 31 x1
u16 +0x1E             : 448 x506, 0 x311, 504 x15, …
u16 +0x20             : 448 x732, 0 x71, 504 x31, …
u16 +0x22 (table[0])  : 56 x810, 504 x28, 58 x2
table length          : header == 0x22 + 2*len(table)
```

**Inference.** `+0x0C`/`+0x14` are a duplicated duration or frame count (integer
valued). `+0x1C` is the bone count (24 dominates). The `+0x22` table is *not* a
per-bone array, because it holds 23 entries while the bone count is 24.

**Disproven.** An earlier claim in this repository was
`header_size == 0x20 + 2 * bone_count`. Observed `header_size` is a constant
`0x50` regardless of the count fields, so the claim is false and was removed
from the code.

**Unknown.** Semantics of `flag_a`, `count_a`, `unknown_1e`, `unknown_20`, the
`+0x22` table, and the keyframe encoding after `header_size`.

---

## E-004 — Vergil is `pl021`

**Observation.** `pl021.pac` slot 13 is plain text:

```
;pl019_02.clt

ClothNum\t1

ClothNo     0
ClothId     0
```

`pl000.pac` slot 13 holds the equivalent `;pl000_02.clt`. The engine's convention
is `pl<NNN>_<variant>.clt`, so `pl000` is Dante and `pl021` is the other
playable character; `pl021.pac` inherits the cloth setup of `pl019`.

**Inference.** `pl021` = Vergil (playable). `pl019` = Vergil (boss).

**Unknown.** No `pl019.pac` is present in this install, so the boss variant could
not be compared. Confirming the mapping against another build is an open task.

---

## E-005 — TM2 textures wrap DDS

**Observation.** `i001_90.tm2` (65,776 bytes) contains `44 44 53 20` (`"DDS "`) at
offset **0x70**, followed by `7C 00 00 00` (`dwSize == 124`), flags `0x00081007`,
`256×256`, and a `DXT3` fourCC.

**Inference.** The HD Collection `.tm2` is a wrapper around a plain DDS blob;
extraction is a single `find`.

**Unknown.** Meaning of the pre-header `u32`s (only 0x08 and 0x0C are non-zero).

---

## E-006 — Weapon archives use a `PNST` container

**Observation.** `plwp_vergilsword.pac` (560,176 bytes) begins:

```
0x00: 50 4E 53 54 09 00 00 00 30 00 00 00 30 90 00 00
      "PNST"      count=9?     0x30        0x9030
```

`PNST` is not `PAC\0`. The offset table layout has not been established.

**Unknown.** Everything about `PNST` beyond the magic. Open issue
*"Reverse the PNST weapon container"*.

---

## E-007 — The install is already modded (Crimson), and mods overlay `pl021`

**Observation.** The asset root contains `newTauntVergilAnims1_pl021_00_2.pac`,
`newTauntVergilAnims2_pl021_00_2.pac`, `newJudgementCut_pl021_00_3.pac`,
`newYamatoHighTime_pl021_00_5.pac`, `plwp_newvergilsword.pac`, plus
`apply_patch.bat`, `xdelta3-3.0.11-x86_64.exe`, and `pl000_00_3.pac.bak`.
Game root has `Crimson.dll` and a `Crimson/` tree with Vergil VFX.

**Inference — this matters for the project.** Third-party tooling already
overlays Vergil's *motions* by dropping replacement `.pac` files with a
`new<Name>_plNNN_00_<slot>.pac` naming convention next to the originals, and the
slot index in the filename picks the animation slot. That is a working, in-the-wild
example of the re-import mechanism this project needs for phase 2.

Comparison of `pl021_00_2.pac` vs `newTauntVergilAnims1_pl021_00_2.pac` shows
slot 0 replaced: both report duration `340.0` and a 24,448-byte payload, while
the other slots differ.

**Unknown.** Whether Crimson is required for the overlay to load, or whether the
engine reads loose files automatically in this build.

**Refinement (E-011).** The loose `GData.afs` folder is almost certainly created by
the mod loader, not by the retail game — see E-011.

---

## E-008 — Untagged chunks in `pl021.pac`

**Observation.** `pl021.pac` has 9 occupied slots whose payloads carry no ASCII
tag. Slot 0 begins `05 00 00 00 2B 00 00 00 16 00 00 00 2B 00 00 00 05 00 00 00
01 00 00 00`, then zero padding, then structured data from ~0x990. Slots 9/11 are
`f32` arrays (`10.4, -1.2, 10.0, 12.0, -1.2, 15.0 …`). Slots 10 is a table of
`u16` pairs increasing by 20. Slot 21 is a `u16` table containing `0xFFFF`
separators.

**Inference.** These are bone transforms, UV/blend tables and primitive grouping
tables. **[UNKNOWN]** — the exact structures are open work.

---

## E-009 — Motion counts per Vergil set

**Observation.** Occupied MOT slot counts:

```
pl021_00_0  23    pl021_00_1  14    pl021_00_2   5    pl021_00_3  16
pl021_00_4  11    pl021_00_5  14    pl021_00_6   2    pl021_00_7  11
pl021_00_8  11    pl021_00_9   1
```

**Inference.** The digits after `pl021_00_` select an animation group; the slot
index selects the animation within it. Total ≈ 108 Vergil motions observed.

**Unknown.** The mapping from `(group, slot)` to the action names a player would
recognise (taunt, Judgement Cut, …). Recovering it needs either engine inspection
or a name table.

---

## E-010 — Vergil's audio assets are present and named `Versil_*`

**Observation.** `data/dmc3/afs/sound/` contains 140 loose `.ogg` files in this
install. Three are Vergil-branded:

```
Versil_01.ogg   1,106,594 bytes
Versil_02.ogg   3,089,634 bytes
Versil_03.ogg   3,041,239 bytes
```

By contrast, `Lady.ogg`, `Jester.ogg`, `Nero.ogg`-style single files and
`Staffroll.ogg`, `Result.ogg` exist for other purposes. Sound banks are separate
`*.pac` files (`snd_com*`, `snd_em*`, `snd_wp*`, `snd_sty*`).

**Inference.** `Versil` is this localisation's romanisation of "Vergil", so these
are Vergil's audio. **[UNKNOWN]** whether each is a battle theme, a voice bank, or
a melee of cues; and which `snd_*.pac` banks hold his weapon/voice effects.

**Why it matters.** An enemy needs audio. This maps directly to issue F10.

---

## E-011 — The loose `GData.afs` folder comes from the mod loader (DDMK/Crimson)

**Observation (external documentation, not local bytes).** The install
instructions for DMC3 HD Collection model mods state:

> "After running DMC 3 with DDMK installed it will add a new folder in your game
> directory. Go to Devil May Cry HD Collection/data/dmc3/Gdata.afs … Drop the
> .pacs you want to use into GData.afs and replace the original files."

Sources: `serpentiem/ddmk` (<https://github.com/serpentiem/ddmk>) and the DMC3 HD
model-port mod page (<https://www.nexusmods.com/devilmaycryhdcollection/mods/25>).

**Inference.** The retail game ships a packed `GData.afs`; **DDMK** (and this
install's Crimson, which derives from it) unpacks it into a directory and overlays
replacement `.pac` files by name. This explains the layout observed in this
install (E-007), and it means the extraction tooling here is reading a
*loader-generated* tree, not the retail container.

**Consequence.** Tooling must not assume the folder layout exists on a vanilla
install. Issue H3 tracks decoding the retail packed `.afs`.

**Unknown.** Whether Crimson alone is sufficient, or DDMK must be present.

---

## E-012 — Prior art: Vergil already ported into another PS4 game

**Observation (external).** A public Bloodborne mod adds Vergil from DMC3 to
Bloodborne (another PS4 title):
<https://www.nexusmods.com/bloodborne/mods/229>. The project owner reports that
the **model is done there and "the moves and things are left."**

Bloodborne mods are installed by dropping files into the game's `dvdroot` folder —
the same replacement convention `gow3_pc` uses for GoW3R (`dvdroot_ps4/`, see
`docs/GOW3.md`). Bloodborne is also the same port lineage as `gow3_pc`.

**Inference.** (a) Vergil's mesh has already been extracted and converted to a
PS4-native asset format by a third party, so the *asset-conversion* problem is
demonstrably solvable. (b) The unmet work — moves, and by extension audio and
effects — matches this project's backlog (F9, F10, F11). (c) Because the mod
delivery mechanism is the same family, the approach may transfer, even though
GoW3R's engine differs from Bloodborne's.

**Unknown — important.** Whether the Bloodborne mod's intermediate/asset files are
licensable or reusable at all, and whether Bloodborne's and GoW3R's asset formats
share anything. Do not assume reuse; assume *learn from*.

---

## E-013 — Community motion-ID map exists

**Observation (external).** Infernal Works' *File ID / Motion Identification
thread* documents DMC3 motion slots by name, including Vergil's moves:
<https://infernalwarks.boards.net/thread/248/file-motion-identfication-thread>

**Inference.** Most of issue F7 (naming Vergil's animations) is already answered by
the community. Transcribed into `docs/ANIMATIONS.md`; still needs local
verification by exporting each clip.

**Unknown.** The thread's slot numbering relative to this install's group/slot
pairing is unconfirmed.

