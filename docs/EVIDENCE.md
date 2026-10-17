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

**Consequence.** G9 is larger than "unzip and repack": the container is an object
graph. But the naming is legible and the entity/AI split is exactly the seam a
boss port needs.








