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

---

## E-014 — Vergil's mesh already exists, decompiled, in a Bloodborne mod package

**Observation.** `C:\Users\GigelCastel\Desktop\vergil` is a FromSoftware **PS4**
(Bloodborne) mod package for Vergil, downloaded from Nexus mod 229. Direct
inspection of its files:

| Observation | Detail |
|---|---|
| Magics present | `FLVER` (model), `TPF\0` (textures, platform header says `PS4`), `BND4` (binders), `DCX\0` (compression), HKX binary `57 E0 E0 57` (Havok), `CLM2` (cloth), `DDS ` (textures), `version 1` (Source **SMD**) |
| Source interchange meshes | `WP_A_10100.smd` (628,257 B), `WP_A_10100.ascii` (181,648 B), plus `_1`, `_2` variants |
| Weapon identity | `WP_A_1063`: 8 nodes — `WP_A_1063_Grip`, `Model_Dummy`, `SFX_Dummy`, `WP_A_1063_0`, `B_Root`, `B_Blade_00/01/02` (parents 4→5→6→7); 1852 verts; material `m0_WP_A_1063`; textures `WP_A_1063_a/_r/_s/_n` |
| Body identity | `BD_M_10100`, a Bloodborne **FullBody** part, replaced by Vergil's body; its TPF shrank 19,929,900 → 2,190,896 bytes versus the `.bak` original |
| Build paths in manifests | `N:\SPRJ\data\INTERROOT_ps4\parts\FullBody\BD_M_10100`, `N:\SPRJ\data\Model\parts\Weapon\WP_A_1063\tex\…` |
| Toolchain manifests | `_witchy-bnd4.xml`, `_witchy-tpf.xml` — Witchy (Blender add-on) |
| Text | `msg/enggb/item-msgbnd-dcx/*.fmg` with Japanese names (`防具名` armour, `武器名` weapon); the armour-name file sets entries to `NOT NEEDED` rather than renaming |
| Extension census | 21 `.dds`, 17 `.fmg`, 14 `.dcx`, 11 `.bak`, 6 `.xml`, 4 `.flver`, 3 `.smd`, 3 `.ascii`, 2 `.tpf`, 2 `.hkx`, 2 `.clm2`, 2 `.anibnd`, 3 `.prev` |

**Inference.** Vergil's **mesh and textures have already been extracted and
converted** — the model problem is solved, in an interchange format (SMD/ASCII)
that Blender reads natively. Decoding DMC3's `MOD ` payload (F1) is therefore a
*cross-check*, not a prerequisite.

The animation data present (`.anibnd`, `.hkx`) is **Bloodborne's**, not Vergil's
DMC3 moves, which matches the owner's description that "the moves and things are
left".

**Unknown.** Whether the package's files are licensed for reuse (permissions live
on the mod page); whether Bloodborne's and GoW3R's asset formats share anything.
Assume *learn from*, not *reuse*, until #31 (H4) resolves it.

**Consequence.** The Phase 1 critical path shifts from mesh decoding to
**animations/moves** (F4, F9) — which is also what an enemy needs most.
See `docs/PRIOR-ART.md`.

---

## E-015 — The prior-art interchange meshes are decoded and the Yamato exports correctly

**Observation.** `tools/priorart/` parses the two Source formats in the package and
was run against the real files.

ASCII layout, read field by field from `WP_A_10100.ascii`:

```
<bone_count = 8>
  per bone (3 lines): name / parent / "px py pz  rx ry rz rw"
<mesh_count = 1>
  <mesh name = m0_WP_A_1063>
  <unknown = 2>
  <texture_count = 7>
    per texture (2 lines): path / flags
  <vertex_count = 1176>
    per vertex (7 lines): pos / normal / rgba / uv / uv2 / bone_indices[4] / weights[4]
  <face_count = 1852>
    per face (1 line): "i0 i1 i2"
```

Line-budget check: `1 + 8*3 + 1 + 1 + 1 + 1 + 7*2 + 1 + 1176*7 + 1 + 1852` matches
the file's 10129 lines exactly.

The bone index/weight ordering is confirmed against the sibling `.smd`, where the
same corner reads `links=1 bone=4 weight=0.996078` — matching the ASCII vertex's
`bones = 4 0 0 0`, `weights = 1 0 0 0`.

**Results on real data:**

| Input | Result |
|---|---|
| `WP_A_10100.ascii` | 8 bones, 1 mesh, **1176 vertices**, **1852 triangles** |
| `WP_A_10100.smd` | 8 nodes, 8 bones, 1 material, 5556 vertices, **1852 triangles** |

Both OBJ exports have identical bounding boxes:
`extent (x,y,z) = (0.163, 1.260, 0.053)`, longest axis 1.260.

**Inference.** The object is a ~1.26 m long, 16 cm wide, 5 cm thick blade — a
**katana**. Two independent source formats agreeing on triangle count and on the
bounding box is strong mutual verification of both parsers, and independently
confirms that `WP_A_1063` is Yamato (E-014's bone names already suggested it).

**Consequence.** T7 is done for the **weapon**. The **body** (`BD_M_10100`) exists
only as FLVER and still needs a parser or an external tool. Assets stay outside the
repository, enforced by `tools/priorart/convert.py`.

---

## E-016 — G1 answered: GoW3R assets are per-entity `R_*.WAD` files

**Observation.** The local dump `C:\Users\GigelCastel\Desktop\gow3\CUSA01715` is
**complete**: 50.5 GB total, of which `EXEC\` is 45.9 GB. Character art is not in
`eboot.bin` at all; it lives in

```
EXEC\WAD\PS4_LE\     417 *.WAD files, 21.5 GB
```

Each WAD begins with a name banner:

```
R_HERCULES.WAD     63,144,480  14 00 00 00 08 00 00 00  "WAD_R_Hercules"
R_HERCULES10.WAD   15,315,776  14 00 00 00 08 00 00 00  "WAD_R_Hercules10"
R_ZEUS00.WAD       57,315,616  14 00 00 00 08 00 00 00  "WAD_R_Zeus00"
R_KRATOSFEAR.WAD   38,703,104  14 00 00 00 08 00 00 00  "WAD_R_KratosFear"
R_SWORD00.WAD          87,840  14 00 00 00 08 00 00 00  "WAD_R_Sword00"
R_LANG_EN.WAD         456,432  14 00 00 00 08 00 00 00  "WAD_R_Lang"
R_UI.WAD           27,792,080  14 00 00 00 08 00 00 00  "WAD_R_UI"
HDS675AI1HADES.WAD     47,136  14 00 00 00 08 00 00 00  "WAD_Hds675AI1Hades"
```

So a WAD is a container with `u32` 0x14 / `u32` 8 / a zero-padded name string at
0x08. (The internal directory format is not yet decoded — issue G9.)

**The naming scheme** (417 files):

| Prefix | Meaning | Examples |
|---|---|---|
| `R_<Name>.WAD` | **one per entity / resource** | `R_KRATOSFEAR`, `R_GRUNT00`, `R_CYCLOPS00` |
| `R_<Boss>.WAD` | **bosses are named entities** | `R_HERCULES`, `R_ZEUS00..60`, `R_HADES`, `R_HELIOS`, `R_HERMES`, `R_POSEIDON00`, `R_POSMAIN00` |
| `R_SWORD00`, `R_SHIELD00`, `R_SPEAR00`, `R_AXE00`, `R_CESTUS` | **weapon meshes** — `R_Sword00` is only 87,840 bytes | |
| `R_UI.WAD` | UI (the boss health bar's art lives here) | |
| `R_FX.WAD`, `R_W_*` | effects | |
| `R_LANG_<CC>.WAD` | **16 languages of text** | `R_LANG_EN`, `R_LANG_DE`, … |
| `<LVL>###.WAD` | level / region | `HDS###`, `OLY###`, `CAV###`, `BAS###`, `GAZ###`, `POS###` |
| `<LVL>###AI#<Name>.WAD` | **per-enemy AI/encounter data** | `HDS675AI1HADES`, `GAZ100AI1PANDZEUS`, `BAS400AI4HELI` |
| `DEPENDENCYGRAPH.IFF` | 265,776 bytes, contains `"WadGraph"` at 0x08 | the WAD manifest |
| `REGION.TXT` | 12 bytes: `BCES00510` | region code (the PS3 disc ID) |

**Inference.** G1 is answered. Entities are individually addressable WADs, weapons
are separated from characters, UI and text are separate, and **enemy AI lives in
its own small `*AI*.WAD` files** — strong evidence that enemy behaviour is
**data-driven rather than compiled into `eboot.bin`**.

**Consequences.**

* The target of a mod is a specific `R_<Entity>.WAD` — replacement is concrete.
* Because entity, weapon, UI, text and AI are separate WADs, a port can mix and
  match: Vergil's mesh from one file, an existing boss's AI from another.
* `R_LANG_*.WAD` is where a boss's displayed **name** most likely lives, which is
  where "Vergil" would go on the health bar (issue G7).
* Whether a **new** entity can be added depends on `WadGraph` and level spawn data
  — issue G8.

**Unknown.** The internal WAD directory format; whether `DEPENDENCYGRAPH.IFF` is
read at runtime; whether level spawn/encounter data is editable.

---

## E-017 — FLVER header of Vergil's body (partial)

**Observation.** `BD_M_10100.flver` (467,008 bytes), first 128 bytes:

```
0x00  "FLVER\0"
0x0C  u32 0x0000F030 (61,488)
0x10  u32 0x00063010 (405,520)
0x18  u32 6          0x1C u32 334        0x20 u32 6        0x24 u32 12
0x28  f32 -0.7157    0x2C f32 0.0000
0x30  f32 -0.1980    0x34 f32  0.7180
0x38  f32  1.7909    0x3C f32  0.2405
0x40  u32 28,062     0x44 u32 28,062     0x48 u32 256      0x4C u32 0
0x50  u32 36         0x54 u32 10
```

**Inference.** Bytes 0x28–0x3F read as six floats in the range
`(-0.72, 0.00, -0.20)` … `(0.72, 1.79, 0.24)`, which has a **vertical extent of
1.79 m** — the expected height of a humanoid. That is a plausible bounding box and
a strong sanity signal that this is Vergil's body and not a prop. `28,062` appears
twice at 0x40/0x44 and is consistent with a vertex count in the tens of thousands.

**Unknown.** The version field, the meaning of the counts, the vertex declaration
layout and the buffer offsets. Full decoding is issue **T7b**.

**Why partial is fine.** The weapon was obtained through the Source interchange
formats instead (E-015); the body has no such shortcut, so FLVER must be read
directly. This entry records the starting point.

---

## E-018 — `param.bin` names each save's location, enabling a no-playthrough test loop

**Observation.** Each save in the port's savedata folder has a sibling
`<slot>.sce_sys/param.bin`, 1,328 bytes, with three fixed 0x80-byte NUL-padded
UTF-8 fields:

```
0x000  char[0x80]  title      "God of War\u00ae III Remastered"
0x080  char[0x80]  location   "The Depths of Hades"
0x100  char[0x80]  details    "Difficulty: God (Normal)\nPlay time: 0:52:29"
0x180  ...         0x3B0 bytes, zero in every sample
```

Read from `SD-261013185858.sce_sys/param.bin` (magic is the title text itself —
this is **not** the standard PS3/PS4 SFO, whose magic is `\0PSF`).

The seven slots present locally resolve to:

| Slot | Location | Play time |
|---|---|---|
| `AUTOSAVE` | `(Auto Save) Hephaestus` | 1:19:33 |
| `SD-261013182124` | `Tomb of Ares` | 0:14:44 |
| `SD-261013183736` | `Entrance to Ares Tomb` | 0:31:09 |
| `SD-261013184508` | `Realm of Hades` | 0:38:30 |
| `SD-261013185858` | `The Depths of Hades` | 0:52:29 |
| `SD-261015184106` | `The Three Judges` | 1:00:50 |
| `SD-261015185945` | `The Forge` | 1:19:39 |

**Inference.** Save slots are self-labelling, so tooling can pick the save that
sits just before the target boss automatically. Combined with *stashing* the other
slots (rather than renaming, which would assume an unverified load order), loading
a boss fight becomes one click — satisfying the owner's "testable each time I
enter the game, don't want to play through it".

**Unknown.** Whether the load list is ordered by folder name or by payload
contents (hence stashing, which is order-independent). Whether `SAVEDATA` carries
a checksum that would reject a hand-edited save — relevant later, since a
hand-authored "boss test" save would be ideal.

**Refinement — timestamps are UTC in the folder, local in the files.** Slot names
encode UTC while file mtimes are local: `SD-261017161301` says 16:13 and its files
were written at 20:13 local (a 4-hour offset on this machine). Matching a slot to
a moment the owner describes therefore needs the offset, not the folder string
alone. This is how the owner's "save at 20:13" resolved to `SD-261017161301`
(`Hades' Palace`, play time 1:43:35) — the save immediately before the Hades
fight, which locked the Phase 3 target boss.

**Consequence.** `tools/gow3/savedata.py` + `tools/gow3/save_list.py` read the
labels; `scripts/boss-test.ps1` drives the loop;
`docs/TESTING.md` documents it. No game asset is copied into the repository.

---

## E-019 — MOT payload decoded: a record table (F4, record layer)

**Observation.** Every MOT payload (from `header_size`, always `0x50`) begins with
a `u32` record count followed by that many records:

```
u32  record_count
record_count x {
    u16 size          total record size, header included
    u16 groups
    u16 field_a       observed 3
    u16 field_b       observed 0
    (size - 8) bytes  data
}
tail                  0..16 bytes of zero padding
```

Measured over **every motion chunk in the install: 840/840 walked with zero
errors, 59,269 records decoded, and `record_count` was reached in all 840.**

Evidence lines from `pl021_00_9.pac` (payload 4,512 bytes):

* stored `record_count` = **69**; walking 69 records consumes the payload exactly
  leaving **12** bytes of zero padding;
* the first records read `+0x0004 size=64 groups=4 a=3 b=0`,
  `+0x0044 size=64 groups=4`, `+0x0084 size=64 groups=4`, `+0x00C4 size=64`,
  `+0x0104 size=48 groups=2`, `+0x0134 size=48 groups=2`,
  `+0x0164 size=64`, `+0x01A4 size=80 groups=6`, … — offsets are contiguous.

Two relations hold:

1. **`size == 8 * (groups + 4)`** — true for every record in **796/840** chunks.
   Equivalently `size - 8 == 8 * (groups + 3)`.
2. The tail is 0, 4, 8 or 12 bytes — i.e. padding to a 4-byte boundary.

**`groups` histogram** over all 59,269 records: 2 → 12,407; 3 → 2,239; 4 → 2,480;
5 → 2,964; 6..20 → ~2,000–3,000 each; 1 → 421; maximum **181**.

**Bone count vs record count — a disproved hypothesis.** The header's `+0x22`
table is **23 entries in all 840 chunks**, and it was tempting to read
`record_count == 3 × bones` (69 = 3 × 23 in the sample). Measured across the
install, `record_count / count_a` is 3.0 in only 193 chunks and 2.875 in 165, with
many other ratios. **The hypothesis is false** and is recorded so it is not
retried.

**Inference.** The MOT payload is a flat table of self-describing records, each
carrying `groups + 3` 8-byte groups. Because `groups` is redundant with `size`
(relation 1) in 95% of records, one of the two fields carries something else; the
44 inconsistent chunks are the place to look.

**Still unknown (F4 remainder).** What the 8-byte groups *mean*. Observed group
values read as `u16` quadruples cluster near `0x8000` (=-32768 as `s16`),
`0x3FFF` (=16383) and `0xBFFF` (=-16383), i.e. values near ±1.0 in Q15 — plausible
for quantised rotation, but **not proven**, and the widely-varying `214..217`
high bytes suggest a bit-packed stream rather than a plain quaternion array.

**Consequence.** `tools/dmc3/mot.py` now exposes `walk_records()` /
`try_walk_records()` returning `MotPayload` / `MotRecord`, exercised by 8 unit
tests and validated against all 840 real chunks.

---

## E-020 — The boss health-bar name is plain ASCII in `R_LANG_EN.WAD` (G7)

**Observation.** `R_LANG_EN.WAD` (456,432 bytes) contains **14,801 printable ASCII
runs and no UTF-16 at all** — the game's English text is stored as plain ASCII.
Searching it for boss names finds them as **exact standalone strings**:

```
Hades   Helios   Hermes   Hercules   Zeus   Cronos   Poseidon
Athena  Gaia     Pandora  Kratos     Ares
```

along with locality labels (`Tomb of Ares`, `Realm of Hades`, `Hades' Palace`),
item names (`Claws of Hades`, `Head of Helios`, `Hades' Helm`, `Helios' Shield`,
`Hermes' Coin`, `Zeus' Eagle`), and descriptive prose
(`"Condemned by his son Zeus, Cronos wanders the Desert of Tartarus for eternity."`).

`R_LANG_DE.WAD` is the same shape (17,065 ASCII runs, German text, **no UTF-16**).

**Inference.** The strings a boss health bar would display live in
`R_LANG_*.WAD` as plain ASCII. A `gow3_pc` mod **can** replace `R_LANG_EN.WAD`, so
the displayed name is expected to be editable — Vergil's bar could read
`Vergil`. This is the mechanism behind requirement G7.

**Unknown.** Which of the several occurrences of e.g. `Hades` is the specific
health-bar string (there are many: locality, item, prose, dialogue). Confirming
which index the bar reads needs one in-game test (Stage 3 of `docs/TESTING.md`).

**Consequence.** G7 is no longer speculative: the name is in a replaceable,
human-editable file. What remains is (a) locating the exact entry and (b) one
in-game confirmation.

---

## E-021 — `WadGraph` is a readable name registry with ~3,344 free `Stub_` slots (G8/G9)

**Observation.** `DEPENDENCYGRAPH.IFF` (265,776 bytes) has the banner `"WadGraph"`
at 0x08, then a large **NUL-separated ASCII name table**: **3,693 names, 3,688
distinct**.

The entries are logical asset names in **CamelCase**:

* **entities** — `R_Hercules`, `R_Hercules10`, `R_Hades`, `R_Zeus50`, `R_Hermes`,
  `R_KratosFear`, … (100 `R_*` names). The WADs on disk use **uppercase**
  (`R_HERCULES.WAD`), so the two match **case-insensitively**.
* **actors / AI** — `ARGrunt00`, `ARGrunt00X22`, `ARArcher00`, `ARCerberus00`,
  `ARCyclops10`, `ARHarpy00`, `ARMedusa00`, `ARMinotaur00`, `ARSatyr00`,
  `ARSiren00`, `ARBrute00`, `ARChimera00`, `ARArgus00`, …
* **levels** — `Bas100`, `Hds675`, `Oly200`, `Cav300`, `Gaz100`, `Crn100`,
  `Lab100`, `Ica100`, `Pos200`, and their `*AI*` sub-wads (`Bas400AI4Heli`,
  `Hds675AI1Hades`).
* **audio** — **2,109 `.xvag` names**, e.g. `Amb_Cronos_v1.xvag`,
  `Amb_Hades666.xvag`, `Bas400TitanHeliosBattle01A.xvag`, `Rabbid_Dog_Distant.xvag`.
* **placeholders** — **3,344 names of the form `Stub_0000` … `Stub_3343`.**

Weapons, UI and text (`R_Sword00`, `R_UI`, `R_Lang`) are **absent** from the graph,
so the registry covers entities, actors, levels and audio specifically.

**Inference.** `WadGraph` looks like a fixed-size registry that maps a logical asset
name to the archive that provides it. Two consequences:

1. **Audio is registered by name**, so Vergil's voice lines (F10) would need a
   registry entry as well as a file.
2. The **~3,344 `Stub_` slots are the strongest evidence yet that a *new* entity
   could be added** rather than only replacing one (G8): the engine may already
   have thousands of unused, nameable asset slots.

**Unknown.** How a registry name is bound to a physical WAD (an index table after
the name block?), and whether a `Stub_` slot can be renamed and pointed at a new
file without breaking the graph's integrity. Decoding the table that follows the
names is issue **G10**.

**Note on case.** Matching manifest names to disk WADs must be case-insensitive.
An earlier check in this journal that compared `R_Hercules` to `R_HERCULES`
case-sensitively reported a false "0 matches".

---

## E-022 — A `R_*.WAD` is a named-object archive, and AI lives in a **different** WAD

**Observation.** Dumping the printable names of four WADs of very different sizes.

Each WAD begins `u32 20, u32 8, char banner[]` (zero-padded), then repeated
records of the shape `u32, u32, char name[≤0x38]`, e.g. from `R_SWORD00.WAD`:

```
+0x50  02 00 00 00  00 00 00 00  "GroupStart"
+0x90  01 00 00 00  18 00 00 00  "WAD_R_Sword00"
+0xF0  02 00 00 00  00 00 00 00  "GroupStart"
```

Every WAD also contains a **`DC_<banner>`** marker, exactly **6 times per file**,
preceded by a fixed 16-byte prefix:

```
00 00 00 00 00 00 00 00  0B 00 09 00  04 00 00 00  "DC_WAD_R_Sword00"
```

Name families across the four files:

| Family | Meaning | `HDS675AI1HADES` | `R_SWORD00` | `R_HERCULES10` | `R_HERCULES` |
|---|---|---|---|---|---|
| `go*` | game objects / effects (`goFireTrail`, `goSoulKratos`) | 372 | 5 | 153 | 342 |
| `tGOPool_N` | object pools | 367 | – | – | – |
| `tMemoryPool_N` | memory pools | 92 | – | – | – |
| `t*System` | `tAnimSystem`, `tFightSystem`, `tHandleSystem`, `tStandardEffectSystem` | 5 | – | – | – |
| `ms::*` | mob system (`ms::tMove`, `ms::tCollisionInfo`, `ms::tSynchPartner`) | 4 | – | – | – |
| `attachment::*` | `attachment::tSys`, `attachment::tChained` | 2 | – | – | – |
| **`hfsm*`** | **AI state machines** | **3** | 0 | **0** | **0** |

The `hfsm*` names in the AI WAD are `hfsmBreakable`, `hfsmEnemy1`,
`hfsmIO_Misc`. Entity WADs contain **none**.

**Inference — and this one changes the plan.** A WAD is a **serialized object
graph**, not an archive of named files. More importantly, the split is:

* **entity WAD** (`R_<Name>.WAD`) — model, textures, animation, object pools;
* **AI WAD** (`<LEVEL>AI#<Name>.WAD`) — the `hfsm*` behaviour state machines.

Therefore **Vergil's behaviour is a data file, not code**. That materially
improves the outlook recorded in `GOW3.md`: the earlier worry that "a mod cannot
author new AI" is too pessimistic — the state machines are data and the AI WADs
are small (47,136 bytes for `HDS675AI1HADES`) and separable. A boss port could
combine *Vergil's model* from one WAD with *an existing or authored AI* from
another.

**Unknown.** The full record/directory structure that binds a name to its bytes
(G9/G10); what the `0x000B / 0x0009 / 4` triple before `DC_` means; whether the
`hfsm*` definitions can be re-authored safely.

**Corrections after a census of the 90 smallest WADs** (all under 2 MB; the full
set is 408 WADs / 21.5 GB and reads too slowly to scan end to end):

| Claim | Measured |
|---|---|
| "`DC_` appears exactly 6 times" | **False.** Distribution is `{0 markers: 17, 6 markers: 73}`. |
| "the 16-byte prefix is `00*8, 0B 00 09 00, 04 00 00 00`" | **False as a constant.** It matched the four hand-picked samples but fails on the other 73. The prefix varies (likely a size/offset), so tooling must report it rather than assume it. |
| entity vs AI split | **Confirmed and common:** of 90 files, **54 carry AI**, 28 are entity WADs, 8 other. |
| banner is unique per file | **False.** 76 distinct banners for 90 files: `WAD_R_Lang` is shared by 13 files and `WAD_R_I_Ice` by 3. |

**The `hfsm*` vocabulary** (a fixed set of behaviour modules, by frequency):

```
20x  hfsmBreakable, hfsmEnemy1, hfsmIO_Misc
18x  the above + hfsmReactive
10x  the above + hfsmReactive, hfsmSavePoint
 2x  hfsmBreakable, hfsmEnemy1, hfsmHeroBreak, hfsmIO_Misc
 2x  the above + hfsmReactive
 1x  hfsmReactive                  (OLY115.WAD)
 1x  the above + hfsmHeroBreak, hfsmReactive, hfsmSavePoint
```

So enemy behaviour is assembled from named modules — `hfsmEnemy1` (the enemy
loop), `hfsmReactive`, `hfsmHeroBreak`, `hfsmSavePoint`, `hfsmIO_Misc`,
`hfsmBreakable`. That is a promising, legible structure for authoring Vergil's
behaviour later.

**Tooling.** `tools/gow3/wad.py` + `tools/gow3/wad_info.py` implement exactly the
verified parts — header, `DC_<banner>` markers (with a `prefix_matches` flag so
the variable prefix is *reported*, not assumed), name-family classification and
`hfsm` detection — and never claim to extract payloads. 13 unit tests.

**Consequence.** G9 is larger than "unzip and repack": the container is an object
graph. But the naming is legible, the entity/AI split is exactly the seam a boss
port needs, and the AI side is a small set of named behaviour modules.

---

## E-023 — WAD record stream partial; the AI WAD is a *readable* logic graph

**Method note first.** Two measurements were attempted and are recorded here as
**failed**, so they are not repeated:

* a **uniform 0x40-byte stride** walk from 0x40 — invalid. Records without a name
  are 0x10 or 0x20 bytes, so the stride is not constant; the walk left 32 bytes
  over and produced garbage type fields.
* a **regex scan** for `\x01\x00\x00\x00` + name — invalid. It matched that byte
  pattern inside arbitrary payload and yielded thousands of nonsense "resource
  names" (e.g. `"iving"`, `"hortcut"`). Those results are noise and are discarded.

**What is solid: a complete dump of the smallest WAD**
(`R_I_ICE0.WAD`, 3,456 bytes — small enough to read end to end). From 0x40 there is
a stream of records shaped ``u32 type; u32 size; char name[0x38]``, and named
records are 0x40 bytes:

```
0x050  type=2  size=0     "GroupStart"
0x090  type=1  size=0x18  "WAD_R_I_Ice"
0x0D0  type=0x80000014             <- no name; 0x20 bytes
0x0F0  type=2  size=0     "GroupStart"
0x130  type=1  size=0x10  "TXRX_R_I_Ice"
0x170  type=0x80000007             <- no name; 0x10 bytes
0x180  type=3  size=0     "GroupEnd"
...
0x0D00 type=0x15 size=0   "PopHeap"
0x0D40 type=0x12 size=0   "WAD_R_I_Ice"
```

Command types observed: **1** = resource definition (`name` + `size`),
**2** = `GroupStart`, **3** = `GroupEnd`, **0x12** = root (the banner again),
**0x15** = `PopHeap`, and **`0x80000000 | n`** = a typed marker where `n` is a
resource class id.

Resource names use a 4-letter class prefix, and the `n` of the following
`0x80000000|n` marker is **constant per prefix**. Read directly off the dump:

| `n` | prefix | meaning |
|---|---|---|
| 1 | `CXT` | context |
| 3 | `ANMX` | **animation** |
| 4 | `SCRX` | script |
| 6 | `LGTX` | light |
| 7 | `TXRX` | **texture** |
| 8 | `MATX` | **material** |
| 9 | `CAMX` | camera |
| 13 | `MDLX` | **model** |
| 14 | `COLX` | collision |
| 15 | `PRTX` | particle |
| 16 | `WPTX` | weapon texture |
| 18 | `BHVX` | **behaviour** |
| 19 | `SNDX` | sound |
| 20 | — | the WAD itself (root) |
| 21 | `FX` | effects |
| 24 | `OCCX` | occlusion |

So a WAD is a **nested group tree of typed, named resources**: `MDLX` = model,
`TXRX` = texture, `MATX` = material, `ANMX` = animation, `BHVX` = behaviour.
That is exactly the map needed to know *which records to replace*.

**The AI WAD is a readable logic graph.** While dumping, the AI WAD
(`HDS675AI1HADES.WAD`) turned out to contain a **named logic/script graph with
human-readable descriptions**, e.g.:

```
CILevelDataHds675AI2Souls        HadesHandLogic-ListenHadesHandSpawn1..6
goevttrans2693spawnbighades      gobighades      godestructbighades
gohadesbigsouls                  gohighmiphades  gosethighmitmaphadesbig
"Detecting the player is in the air"    "Telling the brutes and his grunts
"Setting Cerb to wander"                 to chase the player"
navWalk  navWalkShield  navWalkSpear  navWalkStone  navWalkSword
```

Two things stand out:

* **`navWalkSword`** — there are **per-weapon navigation/behaviour profiles**
  (`navWalkShield`, `navWalkSpear`, `navWalkStone`, `navWalkSword`). A sword
  profile already existing is directly useful for Vergil.
* The nodes carry **English descriptions of their own behaviour**, plus
  `CI*` (logic), `*Sensor*`, `*EventTransmitter*`, `go*` object names and
  `attacks` / `Reactions` / `Damage` groups. Authoring Vergil's behaviour is
  therefore editing a legible graph, not writing machine code.

**Unknown (blocking).** The exact per-record framing — specifically how a record's
length is determined when it has no name. Until that is settled there can be no
WAD reader/writer, and therefore no repack, and therefore no test iteration.

**Consequence.** The container is closer than it looked: its *taxonomy* (which
record is a model, a texture, an animation, a behaviour) is decoded and the
behaviour side is human-readable. The remaining gap is mechanical record framing.

---

## E-024 — Every WAD is the same 16 typed resource groups; the scanner validates

**Observation.** A resynchronising record scanner (`wad.scan_records`) was run over
the **87 WADs under 1.5 MB**. Two independent facts came out of it:

1. **EVERY WAD carries the same 16 resource groups**, one group per resource type,
   in a fixed order:

```
root  TXRX  WPTX  CXT  ANMX  LGTX  SCRX  BHVX  MDLX  PRTX  CAMX  SNDX  COLX  FX  OCCX  MATX
```

2. **The name prefix and the marker's class id agreed on every single occurrence**
   — a 100% consistent cross-check:

| prefix | resolved class | count (of 87 WADs) |
|---|---|---|
| `WAD` | root | 87 |
| `TXRX` `WPTX` `MATX` | TXRX / WPTX / MATX | 87 each |
| `CXT` `ANMX` `LGTX` `SCRX` `BHVX` `MDLX` `PRTX` `CAMX` `SNDX` `COLX` `FX` `OCCX` | same as the prefix | 95 each |

Because the two derivations (name prefix vs following `0x80000000|n` marker) never
disagreed, the class table in E-023 and the scanner are mutually validating. This
is the strongest evidence in the project so far for the WAD layout.

Worked example — the target boss's own archive, `R_HADES.WAD` (85,727,632 bytes):

```
root  size=24  WAD_R_Hades        TXRX size=16 TXRX_R_Hades   WPTX size=16 ...
...
MDLX  size=16  MDLX_R_Hades       ANMX size=16 ANMX_R_Hades   BHVX size=16 BHVX_R_Hades
MATX  size=24  MATX_R_Hades       ... (16 groups total)
```

**Inference.** The WAD is a nested group tree with **one group per resource type**,
so *which* records to replace is now unambiguous. To stand Vergil in Hades'
phase 1, the groups to swap are:

| group | content | Vergil's replacement |
|---|---|---|
| `MDLX_` | **model** | Vergil's mesh |
| `TXRX_` `WPTX_` `MATX_` | textures / weapon textures / materials | Vergil's DDS set |
| `ANMX_` | **animations** | Vergil's move clips |
| `BHVX_` | behaviour | keep Hades's, or author (the AI graph is readable, E-023) |
| `COLX_` | collision | adjust to Vergil's proportions |
| others | lights, cameras, sounds, FX, occlusion | mostly keep |

**Still unknown / deliberately not claimed.** The marker records' *length* is not
determined (observed 0x10 and 0x20), so the scanner resynchronises rather than
computing exact record boundaries. It is therefore a reliable **inventory** tool
and **not yet a writer** — repacking is still blocked. `resources()` resolves the
class from the name prefix first, exactly because that is the more reliable of the
two signals.

**Errors seen (honest limits).** Three resource names resolved to a bogus class id
drawn from float data (`class1065353216` = `0x3F800000` = 1.0f), and the prefixes
`ESC`, `WYP`, `ENV` appear in names but have no confirmed numeric id. These are
recorded rather than hidden.

**Tooling.** `wad.scan_records`, `wad.resources`, `wad.resource_histogram`,
`wad.CLASS_NAMES`, `wad.STANDARD_RESOURCE_SET`, and `wad_info.py --resources`.
15 tests cover the scanner and the class table.

---

## E-025 — The directory is decoded exactly; `DC_` chunks are a footer, not the data

**Observation.** A walk using the rule
``marker record size = round_up(the preceding resource's size, 16)`` was run over
the 90 WADs under 2 MB.

| Measurement | Result |
|---|---|
| Files scanned | **90** |
| DC chunks overrunning their file | **0** |
| Directory record count | **64** (82 files) or **65** (8 files) |
| Directory end offset | **0xD80** (82 files) or **0xDC0** (8 files) |
| `DC_` chunk count | **0** (17 files) or **6** (73 files) |

So the directory is a **variable-length record stream** that ends where the next
u32 is no longer a valid record type. In the standard layout it is exactly
**64 records / 3,456 bytes**, which is why `R_I_ICE0/1/2.WAD` are 3,456 bytes
exactly — they are *pure directories* with no data at all.

`R_HADES.WAD` has **65** records, ending at 0xDC0.

**The `DC_` chunks are a footer.** Correcting an earlier reading of this evidence:

| Region in `R_HADES.WAD` (85,727,632 B) | Extent |
|---|---|
| header + directory | `0x0000 .. 0x0DC0` |
| **bulk data** | `0x0DC0 .. 0x5184D28` (~85.6 MB) |
| **`DC_` footer** | `0x5184D28 .. 0x51C198C` (~249 KB) — the six chunks |
| tail | to `0x51C0A90` |

So the six `DC_` chunks hold only ~249 KB of an 85 MB file. They are **not** the
data region; the bulk sits *between* the directory and this footer.

The chunk prefix format is confirmed:

```
00*8  |  u16 id  |  u16 0x0009  |  u32 size  |  "DC_<banner>"  |  size bytes
```

with ids consecutive `0x0B 0x0C 0x0D 0x0E 0x0F 0x10` and sizes, e.g. for
`R_SWORD00.WAD`: `4, 5756, 44, 4, 788, 3064`; for `R_HADES.WAD`:
`4, 111216, 228, 5914, 15330, 115824`. Every chunk's computed `end` lands inside
its file.

**Inference.** The container is:

```
0x0000  u32 20 ; u32 8 ; char banner[0x38]
0x0050  record stream (directory): named 0x40, markers round_up(declared,16)
        ends at 0xD80 (64 records) or later (R_HADES: 0xDC0)
        -> 16 typed resource groups: root TXRX WPTX CXT ANMX LGTX SCRX BHVX
           MDLX PRTX CAMX SNDX COLX FX OCCX MATX
then    bulk data
then    six DC_ footer chunks (ids 0x0B..0x10) with explicit sizes
```

**Still unknown (the remaining blocker).** How the directory binds to the bulk
data — the resource records declare only 16/24/32, far too small to be byte sizes
of a model, so the offsets or the binding must live in the bulk or in the footer.
Until that is resolved a **writer** is not possible.

**Tooling.** `parse_directory()` (exact), `data_chunks()`, `DataChunk`,
`DIRECTORY_RECORDS_STANDARD`; `scan_records()` now delegates to the exact walk.
6 further tests (108 total).

---

## E-026 — MOT keyframe group: first u16 is an offset-binary frame time (F4, first field)

**Observation.** `pl021_00_9.pac`, slot 0 at file offset 0x10, size-prefixed `MOT\0`
chunk (`header_size` `0x50`, duration `100.0`, `bone_count` `24`). Payload begins at
file +0x60:

```
file +0x60  record_count u32 = 69
file +0x64  record 0 header: 40 00 04 00 03 00  -> size=64 groups=4 a=3 b=0
file +0x6C  record 0 data, 56 bytes = 7 groups:
  cd 4a ce 40 60 45 7e 3f   <- group 0 (record header)
  e9 ba c1 bc 51 29 b8 3d   <- group 1 (record header)
  83 a0 70 be 83 a0 70 3f   <- group 2 (record header)
  00 80 ff 3f 53 43 ff bf   <- group 3 = keyframe[0], u16[0] = 0x8000
  0c 80 3c 40 ff bf 7e 40   <- group 4 = keyframe[1], u16[0] = 0x800C
  33 80 ff bf 53 43 ff 3f   <- group 5 = keyframe[2], u16[0] = 0x8033
  64 80 26 40 ff 3f ff 3f   <- group 6 = keyframe[3], u16[0] = 0x8064
```

Groups 0–2 appear once per record; groups 3+ are the record's `groups` keyframes.
keyframe[0].u16[0] = `0x8000`, keyframe[1].u16[0] = `0x800C`, keyframe[2].u16[0] =
`0x8033`, keyframe[3].u16[0] = `0x8064` = `0x8000 + 100` (the duration).

**Cross-check.** The same rule was applied to every keyframe group in every MOT chunk
of the install: **840 chunks, 59,269 records, 623,060 keyframes**. On all Vergil
`pl021_*.pac` chunks the times are monotonic within each record and bounded by the
header duration — **0 violations**. Across the whole install (enemies, demo content,
…) a small minority deviates: 29 records non-monotonic, 1,073 records with a time
outside `[0, duration + 2]`; these are recorded as edge cases, not allowed to falsify
the rule.

**Inference.** The first u16 of each 8-byte keyframe group is an offset-binary frame
count: ``frame = u16[0] - 0x8000``, in animation frames (matching the `+0x0C`/`+0x14`
duration, an integer frame count). `0x8000` is the encoding's zero point.

**Unknown.** The group's remaining three u16s (position/rotation values), the per-record
groups at positions 0–2 that precede the keyframes, the value scale, and whether
`0x8000` is a base offset or a flag bit. The non-Vergil minority is a candidate
follow-up issue.

---

## E-027 — `DC_` id `0x10` chunk holds a sorted bulk-offset table (G9 name→bytes binding)

**Observation.** In `R_SWORD00.WAD` (87,840 bytes), the `DC_` footer chunk with id
`0x10` sits at offset 0x14AE8, size 3064 (0xBF8). Its payload (766 u32s)
contains, from array index ~226 to ~364 in steps of 3, 47 entries of the shape
`[0x9F|0xA4, bulk_offset, ascending_value]` where each `bulk_offset` is a sorted
file offset into the bulk region (0xD80..0x12FA8):
`0xD84, 0xDAC, 0xDE4, 0xE0C, …, 0x1654`. After the table the payload transitions
into ASCII strings (`CRT_`, `Sword00`, `FX_…`). The same chunk exists in
`BAS500AI3ARG00.WAD` (13,040 bytes, id `0x10` size 1611) with a similarly
non-zero payload. Pure-directory WADs (`R_I_ICE0/1/2`, 3,456 bytes) have no `DC_`
chunks at all (0 markers), while data WADs have 6.

**Inference.** `DC_` id `0x10` is an offset/index table that binds directory
resources to their bulk data offsets — the missing name→bytes binding for the WAD
directory. The alternating `0x9F`/`0xA4` field and the ascending third field are
not yet understood. The 47 entries exceed the 16 typed resources, so one entry does
not simply equal one resource (a resource may span multiple blocks, or the table
covers non-resource structures too).

**Unknown.** Exact entry alignment and field meanings; how entries map to directory
resource names; whether the table is complete and consistent across all WADs; how
to update it when repacking. A WAD writer remains blocked until the name→offset
mapping is resolved.

**Tooling impact.** `wad.parse_directory()` (exact), `data_chunks()`, `DataChunk`,
`DIRECTORY_RECORDS_STANDARD` are unchanged and correct. No writer function is added
yet, because the mapping is unknown.

---

## E-028 — MOT keyframe groups: the preamble/keyframe split and a u16[1..3] census (F4 remainder)

**Observation.** Read every MOT chunk in all ten `pl021_*.pac` files in the
install and walked the record layer with `walk_records()` (0 walk failures;
7,659 records, 110,639 eight-byte groups, 87,662 keyframe groups):

* Each record's data splits into `field_a` preamble groups followed by
  `groups` keyframe groups: `len(group_bytes()) == field_a + groups` for
  7,656/7,659 records; `field_a == 3` for 7,656/7,659 (the other 3 records have
  `field_a == 2`). The three exceptions are records whose declared size breaks
  the `size == 8 * (groups + 4)` relation from E-019.
* The keyframe group's first u16 is the offset-binary frame time (E-026).
* Its remaining three u16s, read as signed 16-bit, span the full
  `[-32768, 32767]` range (max absolute 32768) and differ from keyframe to
  keyframe within a record. Frequency of the most common values, out of
  87,662 values per channel: 0x3FFF (+16,383 ≈ +0.5 Q15) ~5,500–5,600 hits;
  0xBFFF (−16,383 ≈ −0.5 Q15) ~5,500–5,600 hits; 0x0000 ~2,400–2,800 hits;
  0xFFFF (−1) ~950–1,100 hits. Only ~5% of values are near zero (|v| < 256).
* The preamble groups carry similarly ranged values; no field in them matches a
  bone index (0–23) directly.

**Inference.** u16[1..3] are three quantized 16-bit channels per keyframe —
consistent with per-bone position or rotation components in Q15 fixed point,
given the ±0x3FFF/+0x4000 clustering — but channel assignment, scale and zero
point are not established from bytes alone. The preamble (field_a groups) is
per-record header data whose contents are unknown.

**Unknown.** Semantics of u16[1..3] (which axis/channel, position vs rotation),
their scale and zero point, the preamble group contents, field_b (0 observed
everywhere), and how a record maps to a skeleton bone (no bone index found in
the bytes read so far).


---
## E-029 — MOT keyframe remainder: preamble groups are f32 pairs; u16[1..3] not decodable from bytes alone (F4 remainder)

**Observation.** Re-walked every MOT chunk in all ten `pl021_*.pac` files with
`walk_records()`: 7,659 records, ~87.7k keyframe groups, 0 walk failures,
tails small — consistent with E-019/E-028 over all 840 install chunks.

Per record, the data splits into `field_a` preamble groups followed by
`groups` keyframe groups: `len(group_bytes()) == field_a + groups` for
7,656/7,659 records and `field_a == 3` for 7,656/7,659 (the 3 exceptions are
records whose declared size breaks the `size == 8 * (groups + 4)` relation from
E-019).

**Worked example** — `pl021_00_9.pac`, slot 0, record 0. The record header sits
at chunk +0x54 (`40 00 04 00 03 00`: size=64, groups=4, field_a=3, field_b=0);
its 56-byte data begins at chunk +0x5C:

```
chunk +0x5C  cd 4a ce 40 60 45 7e 3f   <- preamble group 0: f32 pair (6.446631, 0.993246)
chunk +0x64  e9 ba c1 bc 51 29 b8 3d   <- preamble group 1: f32 pair (-0.023649, 0.089923)
chunk +0x6C  83 a0 70 be 83 a0 70 3f   <- preamble group 2: f32 pair (-0.234987, 0.939949)
chunk +0x74  00 80 ff 3f 53 43 ff bf   <- keyframe[0]: u16[0] = 0x8000 -> frame 0
chunk +0x7C  0c 80 3c 40 ff bf 7e 40   <- keyframe[1]: u16[0] = 0x800C -> frame 12
chunk +0x84  33 80 ff bf 53 43 ff 3f   <- keyframe[2]: u16[0] = 0x8033 -> frame 51
chunk +0x8C  64 80 26 40 ff 3f ff 3f   <- keyframe[3]: u16[0] = 0x8064 -> frame 100 (= the header duration)
```

This matches E-026's byte dump of the same record (file +0x64 header, file +0x6C
data; keyframe[3].u16[0] = 0x8064 = 0x8000 + 100 = duration 100).

**Preamble statistics** (all 22,974 preamble groups across the ten files):
every group reads as two little-endian f32s that are finite with |v| ≤ 1e6;
97.4% have both |v| ≤ 10; 99.6% have both |v| ≤ 100; max |v| ≈ 999.6.
Small-magnitude floats (translation/scale/rotation-like magnitude); meaning
unknown.

**u16[1..3] statistics:** not constant within a record — only 458/269/258 of the
7,659 records have u16[1]/u16[2]/u16[3] constant across their keyframes, and
those are dominated by trivial single-keyframe records; the channels vary per
keyframe. The preamble is **not** a stored base pose: preamble == first keyframe
groups in 0/7,659 records. The u16[1..3] distribution (E-028) spans the full
signed range [-32768, 32767] with modal values ±0x3FFF (~±0.5 Q15, ~5,500 hits
per channel), 0x0000 ~2,400–2,800 hits, 0xFFFF (−1) ~950–1,100 hits; only ~5%
of values are near zero (|v| < 256).

No record→bone mapping appears anywhere in the bytes: no field matches a bone
index (0–23), and no field varies as a bone selector across records.

**Inference.** Structure (not semantics): each record =
`field_a` preamble groups of three f32 pairs (per-record parameters, |v|
typically ≤ 10) followed by `groups` keyframes; each keyframe = offset-binary
frame time (`u16[0] − 0x8000`, decoded in E-026) plus three per-keyframe
16-bit channels. The tight f32 magnitude bound supports reading the preamble as
real parameters rather than bit-packed noise, but *which* parameters is unknown.
The keyframe channels' meaning, scale, zero point, and channel assignment are
unknown.

**Unknown.** Channel semantics of u16[1..3] (position vs rotation, axis
assignment), their scale and zero point, preamble group semantics, field_b
(always 0 observed), and how a record maps to a skeleton bone. These cannot be
established from bytes alone — they need engine ground truth (e.g., comparing a
decoded clip against an in-game capture, or disassembly of the animation
player). **Not decodable from bytes alone; recorded as [UNKNOWN] so this is not
retried.**

**Disproven.** (a) "u16[1..3] is constant per record" — false: the channels
vary per keyframe. (b) "the preamble encodes the first keyframe / base pose" —
false: 0/7,659 records match.


---
## E-030 — `MOD ` mesh-chunk header: verified bytes, unknown payload layout (F1, bounded slice)

**Observation.** Read every `MOD ` chunk in `pl021.pac` (4 occupied slots:
1, 12, 23, 25) and then every `MOD ` chunk across the install (286 chunks in
194 PAC files). Slot 1 of `pl021.pac` at file offset `0x039880` (span
204,384 bytes):

```
file +0x039880  4d 4f 44 20 ae 47 81 3f  "MOD "  f32=1.0099999904632568
file +0x039888  00 00 00 00 00 00 00 00  u32=0  u32=0
file +0x039890  0b 18 03 01 12 fe 0a 00  u32=0x0103180B  u32=0x000AFE12
file +0x039898  00 00 00 00 00 00 00 00  u32=0  u32=0
file +0x0398A0  30 9b 02 00 00 00 00 00  u32=0x00029B30  u32=0
file +0x0398A8  ...                       (payload body begins at +0x24)
```

The other `pl021.pac` `MOD ` chunks:
- slot 12: `+0x10 = 0x00032702`, `+0x14 = 0x000AFE12`, `+0x20 = 0x00005140`
- slot 23: `+0x10 = 0x00030101`, `+0x14 = 0x000AFE12`, `+0x20 = 0x00001920`
- slot 25: byte-identical to slot 23 (a duplicated mesh, consistent with E-005's
  inference of two render variants)

Install-wide statistics over **286 `MOD ` chunks** (all PAC files in the asset
root, non-`PAC\0` archives such as `PNST` weapon containers skipped):

| Offset | Field | Value distribution |
|---|---|---|
| `+0x04` | f32 scale | `1.0099999904632568` x285, `1.0` x1 |
| `+0x08` | u32 | `0` (observed in all 4 pl021.pac MOD chunks; not scanned install-wide) |
| `+0x0C` | u32 | `0` x286 |
| `+0x10` | u32 | varies per mesh (e.g. `0x10101` x59, `0x103180B` x2, `0x30101` x5, …) |
| `+0x14` | u32 | varies per mesh (`0xF4240` x187, `0xAF258` x7, `0x384` x7, …) |
| `+0x18` | u32 | `0` (observed in all 4 pl021.pac MOD chunks; not scanned install-wide) |
| `+0x1C` | u32 | `0` x286 |
| `+0x20` | u32 | varies per mesh (e.g. `0x160` x61, `0x29B30` x2, `0x1920` x6, …) |

**Inference.** The `MOD ` header is a fixed 0x24-byte block: a scale-like f32
(`1.0099…`, i.e. `0x3F8147AE`, in 285/286 chunks), u32 fields that are always
zero where observed (`+0x0C`, `+0x1C` install-wide; `+0x08`, `+0x18` in the
pl021.pac samples), and three varying u32s at `+0x10`, `+0x14`, `+0x20` whose
meanings are not established. `+0x14 == 0xF4240`
(1,000,000) in 187/286 chunks suggests one field may be a byte size or vertex
count, but that is an inference, not an observation.

**Unknown.** The payload body layout starting at `+0x24` (vertices, indices,
normals, UVs, skin weights — issue F1). The semantics of the varying fields
`+0x10`/`+0x14`/`+0x20`. Whether the single `scale == 1.0` chunk is a different
mesh variant or a parsing edge case.

**Correction.** Earlier revisions of `docs/FORMATS.md` §5 placed the varying
values (e.g. `0x0003180B`, `0x00029B30`) at `+0x0C`/`+0x1C`; real bytes show
`+0x0C` and `+0x1C` are `0` in every `MOD ` chunk checked, and those values
actually appear at `+0x10`/`+0x20`. The spec is corrected below.


---
## E-031 — `MOD ` payload body prefix: first decoded fields (F1, bounded slice)

**Observation.** Read the body (chunk +0x24 onward) of every `MOD ` chunk in
`pl021.pac` (slots 1, 12, 23, 25). Slot 1 at file offset `0x039880` (span
204,384 bytes); header bytes as recorded in E-030. Body prefix, body-relative
(all little-endian):

```
file +0x0398A4 (chunk +0x24): 00 00 00 00 00 00 00 00   body +0x00..+0x07: zero
file +0x0398AC (chunk +0x2C): 00 00 00 00 00 00 00 00   body +0x08..+0x0F: zero
file +0x0398B4 (chunk +0x34): 00 00 00 00 00 00 00 00   body +0x10..+0x17: zero
file +0x0398BC (chunk +0x3C): 00 00 00 00                body +0x18..+0x1B: zero
file +0x0398C0 (chunk +0x40): 01 80 da 01                body +0x1C: u16=0x8001
                                                           body +0x1E: u16=474
file +0x0398C4 (chunk +0x44): 00 00 00 00                body +0x20: u32=0
file +0x0398C8 (chunk +0x48): 00 03 00 00                body +0x24: u32=768
file +0x0398CC (chunk +0x4C): 00 00 00 00                body +0x28: u32=0
...
file +0x0398F0 (chunk +0x70): 00 00 40 b8                body +0x4C: f32=-4.58e-05 (~0)
file +0x0398F4 (chunk +0x74): 68 fe e2 42                body +0x50: f32=113.497
file +0x0398F8 (chunk +0x78): 80 1e e1 3d                body +0x54: f32=0.1099
file +0x0398FC (chunk +0x7C): 2d 94 68 42                body +0x58: f32=58.1447
file +0x039900 (chunk +0x80): 02 80 41 01                body +0x5C: u32=0x01418002
```

The other `pl021.pac` `MOD ` chunks (body-relative):

| slot | file offset | body+0x1C u16 | body+0x1E u16 count | body+0x24 u32 | body+0x4C f32 | body+0x50 f32 | body+0x54 f32 | body+0x58 f32 | body+0x5C u32 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 0x039880 | 0x8001 | 474 | 768 | -4.58e-05 | 113.497 | 0.1099 | 58.1447 | 0x01418002 |
| 12 | 0x078350 | 0x8001 | 300 | 192 | -0.0440 | -55.273 | -9.947 | 80.069 | 0x012D8001 |
| 23 | 0x811E0 | 0x8001 | 182 | 128 | -0.1962 | ~0.0 | 42.071 | 73.569 | 182 |
| 25 | 0x838C0 | 0x8001 | 182 | 128 | -0.1962 | ~0.0 | 42.071 | 73.569 | 182 |

Slots 23 and 25 are byte-identical (E-030), including `body+0x5C == count`.

**Inference.** The payload body begins with a fixed prefix: twenty-eight zero
bytes, then a `u16` marker that is constantly `0x8001`, then a `u16` count that
varies per mesh. The count's reappearance at `body+0x5C` for the two identical
small meshes supports reading `body+0x1E` as a stored count; what it counts
(vertices, primitives, bones, …) is not established. `body+0x4C..+0x5B` reads as
four f32s with a vector-like magnitude (tens to ~113) but its meaning is not
established. The `0x8001` marker coincides with the `0x8000` zero base used for
MOT frame times (E-026); any relationship is [UNKNOWN].

**Unknown.** The payload body layout beyond this prefix (vertices, indices,
normals, UVs, skin weights — the remainder of issue F1); the semantics of the
marker, the count, `body+0x24`/`body+0x2C`, the four f32s, and `body+0x5C`.
Whether `body+0x1E` is a vertex count is an inference, not an observation.

**Consequence.** `tools/dmc3/mod.py` now exposes `ModBodyPrefix` (with
`BODY_PREFIX_SIZE`) decoding exactly this prefix from real bytes, exercised by
unit tests on synthetic fixtures.





