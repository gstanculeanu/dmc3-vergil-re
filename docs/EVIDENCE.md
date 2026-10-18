# Evidence ledger

Each entry records an **observation** (bytes read from a shipped artifact) and,
separately, any **inference** and remaining **unknown**. Format specs in
`FORMATS.md` cite these IDs. Nothing here is a guess presented as fact.

Methodology follows REA: route the target, work evidence-first, keep observation
and inference apart — <https://github.com/morluto/rea/>

## ID allocation (read this before adding an entry)

**Take the next free ID. Never reuse or guess one.** Two writers added entries
independently on 2026-10-18 and collided twice (`E-052` and `E-056` each ended up
with two entries in different sections); both were renumbered, the later one losing:

* the autonomous loop's `E-052` (`pl021.pac` slot 5) and `E-056` (`eboot.elf`
  reference scanner) came first and kept their numbers;
* the human-authored localisation table entry became **E-057** and the animation
  clip directory became **E-058**.

To avoid a repeat: grep the ledger for the highest `## E-0NN` heading and increment
it. Renumbering a shipped ID is worse than picking a high one.


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

**Observation.** Both weapon archives on disk (`plwp_vergilsword.pac`,
560,176 bytes; `plwp_newvergilsword.pac`, 561,328 bytes) begin:

```
plwp_vergilsword.pac   0x00: 50 4E 53 54 09 00 00 00 30 00 00 00 30 90 00 00
                       "PNST"      count=9       0x30           0x9030
plwp_newvergilsword.pac 0x00: 50 4E 53 54 0A 00 00 00 30 00 00 00 30 90 00 00
                         "PNST"      count=10      0x30           0x9030
```

The `u32` at +0x08 starts an offset table of `count` file-relative u32s.
Reading every entry on both files:

| Slot | `plwp_vergilsword.pac` (count=9) | `plwp_newvergilsword.pac` (count=10) |
|------|----------------------------------|--------------------------------------|
| 0 | 0x0030 → raw block `01 00 00 00 11 00 00 00 …` | same |
| 1 | 0x9030 → `MOD ` | same |
| 2 | 0xAC00 → `SHW ` | same |
| 3 | 0xB3A0 → raw block `01 00 00 00 11 00 00 00 …` | same |
| 4 | 0x143A0 → `MOD ` | same |
| 5 | 0x16370 → `;wp005.clt` cloth-config text | same |
| 6 | 0x164D0 → `SHW ` | same |
| 7 | 0x177B0 → `PNST` nested container | same |
| 8 | 0x88600 → `PAC\0` nested container | same |
| 9 | — | 0x88F20 → `06 00 DA 00 FF FF …` data |

**Inference.** The `PNST` container mirrors the `PAC` container (E-001): magic,
`u32 entry_count`, then `u32 offset[entry_count]` at +0x08 with `0` as the
empty-slot sentinel (no zero entry observed yet). Data start is
`align_up(0x08 + 4 * count, 0x10)` and equals `offset[0]` on both files.
Unlike `PAC`, no size-prefixed chunk framing has been observed — chunk tags,
when present, sit at byte 0. Chunks carry their own structure: `MOD ` mesh
headers (E-030), `SHW ` shader headers (E-036/E-038), nested `PAC\0` and
`PNST` containers, plain-text cloth configs (`;wp005.clt`, like E-004), and
unidentified raw blocks whose leading `01 00 00 00 11 00 00 00` repeats at
slots 0 and 3 in both files. The nested `PNST` at 0x177B0 holds a 2-entry
table whose second entry points at a further `PNST` (0x17DB0).

**Unknown.** Semantics of the raw blocks (`01 … 11 …`), per-chunk payload
layouts beyond the headers already decoded, whether an offset of `0` is ever
used as an empty slot, and the contents of the nested containers. Chunk
payload semantics remain [UNKNOWN]; the open issue
*"Reverse the PNST weapon container"* continues at the payload level.

**Consequence.** `tools/dmc3/pnst.py` exposes `PnstArchive` (header + offset
table, chunk accessors, tag classification), verified against both real weapon
archives and exercised by unit tests on synthetic fixtures (no game data
committed).

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

## E-057 - The localisation table is plain ASCII with `*id*` markers (G7)

**Observation.** `R_LANG_EN.WAD` (456,432 bytes) carries a **plain-text** table,
4,132 entries, ids `100..2222`, first marker at `0x11E5`, the last entry ending at
`0x5BF34`. Every entry is::

    *<id>*\r\n<body lines>\r\n

`*20001*` for example reads `1`, `FALSE`, `Fear Kratos`, `heroImage01`, then a
description. The file is ASCII only (no UTF-16) — confirmed earlier in E-020.

**The character-name block is ids 818..842**, a contiguous run of single-line
names (read directly with `tools/gow3/lang_list.py --around 830`):

```
*818* Tartarus      *826* Gates of Tisiphone   *834* Hermes
*819* The Pit of…   *827* Poseidon             *835* Poseidon Princess
*820* The Forum     *828* Challenge Complete   *836* Daedalus
*821* Hera's Garden *829* Athena               *837* Pandora
*822* The Labyrinth *830* Peirithous           *838* Cronos
*823* Heart of Gaia *831* Hephaestus           *839* Zeus
*824* Hera          *832* Hades                *840..* (further entries)
*825* Hercules      *833* Helios
```

`*832*` is `"Hades"` at file offset **0x0000C4B3**, body `\r\nHades\r\n` — 9 bytes.

**Inference.** The boss/character display name is a single text entry, so
renaming the bar is a text edit, not a model edit. **But the length matters:**
"Hades" is 5 bytes and "Vergil" is 6, so the body grows by one byte and the
container's stored sizes (the `DC_` chunk size and everything after it) would need
updating — **which needs the WAD writer**. A same-length swap (e.g. `Helios` →
`Vergil`, both 6) *can* be done in place with no writer, and would validate the
whole mod-delivery path.

`lang.replace_exact_line()` implements exactly that: it refuses any replacement
whose byte length differs, returning `None`, so it cannot silently corrupt sizes.

**Unknown.** Whether the game reads this entry for the boss health bar (as opposed
to a menu or bestiary label) — needs one in-game look.

**Tooling.** `tools/gow3/lang.py` (`parse_entries`, `search`, `replace_exact_line`)
and `tools/gow3/lang_list.py` (CLI); 15 unit tests on a synthetic table.

---

## E-053 — `eboot.bin` references the WAD/asset names; the record opcodes are numeric

**Observation.** The command strings used inside a WAD — `GroupStart`, `GroupEnd`,
`PopHeap`, `DC_`, `MDLX`, `TXRX` — are **not present in the executable** at all.
But these are:

```
eboot.bin   WAD_ 0x2ED340   hfsm 0x3538AD   ms::tMove 0x352AA4
            attachment:: 0x35150C   DEPENDENCY 0x332C56   .wad 0x35FD97
```

Mapping file offsets to virtual addresses through the prepared ELF's program
headers (`out/eboot.elf`, entry `0x144070`, one executable `PT_LOAD` at
`vaddr=0`, `filesz=0x3BD518`) and scanning for x86-64 RIP-relative references
gives **94 cross-references**, including a contiguous cluster:

| code address | references |
|---|---|
| `0x00100D49`, `0x00101F10`, `0x00101F33`, `0x001061D5`, `0x00108A74`, `0x00108B53` | `WAD_*` names |
| **`0x0010BB24` … `0x0010D2B4`** (9 sites) | **`hfsm*`** |
| `0x000ED578` | `ms::tMove` |
| `0x000D0D94`, `0x000D0DCE`, `0x000DBF14` | `attachment::` |
| `0x0011B576` … `0x0011C5B6` | `WAD_` |

**Inference.** Two things follow. (1) The **record opcodes are numeric constants in
code**, not strings, which is why the command names are absent — so a
disassembler, not a string search, is the route to the exact record framing.
(2) The nine `hfsm` references confirm independently that the **AI state machines
are instantiated by name from data** (E-022), rather than compiled.

**Unknown.** The actual parsing logic. Locating it means finding the numeric
opcode constants in the code, which is the "engine ground truth" the DMC3
byte-level work (E-050/E-051) was blocked on.

**Note.** The `.wad`/`WAD_` string references are a promising entry point for
finding the file loader, hence the container format.

**Correction (E-056).** The scan pattern is `(modrm & 0xC7) == 0x05`
(any RIP-relative `lea`/`mov`), not `modrm == 0x05`; and inside the executable
segment `vaddr = file_offset - 0x4000`. `tools/gow3/eboot.py` implements the
corrected scan and reproduces the 94 references above.

---

## E-054 — Named-blob descriptor table, and a **verified** length-changing rename

**Observation.** `R_LANG_EN.WAD` has a descriptor table starting at `0xD80`, and a
descriptor is 0x40 bytes::

    +0x00  u32   id
    +0x04  u32   size of the blob
    +0x08  char  name[0x38], NUL padded
    +0x40  the blob's data begins here

The first (and in this file only parsed) descriptor is::

    @0xD80  id=7  size=318,537 (0x4DC49)  "MSGS_TXT"
    data  0xDC0 .. 0x4EA09

So `MSGS_TXT` is the localisation text, **data at 0xDC0**, and the `*832* "Hades"`
entry at `0xC4B3` lies inside it.

**Correction to E-057.** The marker regex first used demanded 3+ digits, so entry
ids `1`–`99` were skipped and the "first entry" was reported as `*100*` at `0x11E5`.
In fact the text begins at `0xDC0` with `*1*` (`Spartan (Easy)`). Fixed; a
regression test now covers 1- and 2-digit ids.

**Observation — the edit, verified byte-for-byte.** Renaming `*832*` from `Hades`
(5 bytes) to `Vergil` (6) was performed and checked:

| Check | Result |
|---|---|
| file size | 456,432 → 456,433 (+1) |
| `MSGS_TXT` size field | 318,537 → **318,538** |
| bytes before the insertion | identical apart from that 4-byte size field |
| bytes after the insertion | a pure 1-byte shift |
| `*832*` | reads `Vergil`, no longer `Hades` |
| **source file sha256** | **unchanged** |

**Inference.** A blob's only bookkeeping is its `size` field; the container stores
no offset or size that covers a blob's *interior*. So a length-changing edit is
safe when the blob's size field is updated by the same delta and the blob is the
text itself — entries are located by scanning `*id*` markers, so the shift is
harmless. This is a **narrow writer** that needs no understanding of the record
directory, and it is what made the Hades → Vergil rename possible ahead of the
full WAD writer.

**Unknown.** Whether the game reads entry `*832*` for the boss health bar (rather
than a menu or bestiary label) — one in-game look settles it. Also unknown is
whether a *second* blob follows `MSGS_TXT` at `0x4EA09` and what it is.

**Tooling.** `lang.find_blob()`, `lang.replace_exact_line_in_blob()`,
`tools/gow3/make_lang_mod.py` (verifies all six checks, refuses to write inside the
game install or the repo) and `scripts/vergil-name-mod.ps1` (`-Install` / `-Restore`
/ `-Status`, with a SHA-256-verified backup). 7 further tests (278 total).

---

## E-055 — Textures are plain DDS, and a same-size in-place tint reaches the boss

**Observation.** Scanning `R_HADES.WAD` (85,727,632 bytes) for valid DDS headers
(dwSize == 124, plausible dimensions) finds **142 textures**: **75 BC1 (DXT1)** and
**67 BC3 (DXT5)**, up to 2048×2048 with 11 mip levels. The descriptor table at
`0xD80` names them in the same style, e.g. `R_HERCULES10.WAD`'s first blob is
`TXF2B7124B.67BE49FB.dds` (2,796,412 bytes).

**Texture data size is computable from the texture's own header.** Checking the
distance between consecutive textures confirmed it: the computed size is short by
exactly **144 bytes** every time, i.e. a constant per-texture overhead of 144 bytes
sits outside the DDS blob. That constant is unexplained, but it does not matter for
an in-place edit: the *pixel data* boundary is known.

**Observation — the edit, verified.** The largest texture (2048×2048, DXT5, 11 mips,
5,592,416 bytes at `0x01ABCDBC`) had both RGB565 colour endpoints of every DXT
colour block flattened to pure red (`0xF800`). Because `colour0 == colour1`, the
four index bits select between two identical values and the block renders that solid
colour whatever it originally held.

| Check | Result |
|---|---|
| file size | **unchanged** (85,727,632 bytes) |
| every changed byte inside the chosen texture | **yes** |
| only colour-endpoint bytes changed | **yes** |
| every colour endpoint now holds the tint | **yes** |
| texture header untouched | **yes** |
| blocks tinted | 349,526; 1,317,870 of 1,398,104 endpoint bytes changed (the rest already held it) |
| source `R_HADES.WAD` sha256 | **unchanged** |

**Inference.** GoW3R textures are plain DDS and can be replaced **in place** at
identical size, so *texture* replacement needs no container writer at all — only a
mesh swap does. Widening the endpoints to a solid colour is a deliberately crude
"tint" chosen to be unmistakable on screen: it proves the mod pipeline reaches the
boss model, independently of the localisation change.

**Unknown.** The 144-byte per-texture overhead. Which texture is albedo vs normal
map (tinting a normal map gives odd shading but is still visible). Whether the game
verifies texture hashes.

**Tooling.** `tools/gow3/dds.py` (`parse_at`, `find_textures`, `level_size`,
`data_size`, `colour_blocks`, `rgb565`, `tint_in_place`, `changed_ranges`),
`tools/gow3/make_boss_mod.py` (builds both files, verifies every changed byte) and
`scripts/vergil-boss-mod.ps1`. 20 further tests (317 total).

---

## E-058 - The animation clip directory: a boss's move set is enumerable

**Observation.** In `R_HADES.WAD` (85,727,632 bytes) the descriptor table's first
real entry is an animation blob:

```
0xD80  id=2 flags=0    size=0        "GroupStart"
0xDC0  id=1 flags=0x34 size=2,106,384 "ANM_hero_Hades"
0xE00  a record naming the character: "Hades"
0xE78  u32 clip offsets, strictly increasing, **relative to 0xE40**
0xE40  the blob's data; clip i is at 0xE40 + offsets[i] and its name is right there
```

Note the table (0xE78) sits **inside** the blob region (which starts at 0xE40).

**Verified.** 77 entries, every one landing exactly on a named clip, with a
constant base — the relationship held to the byte on all of them:

| relative | file offset | clip |
|---|---|---|
| 0x4C34 | 0x5A74 | `angryKratosWalk` |
| 0x8874 | 0x96B4 | `csHadesIntro` |
| 0x12E74 | 0x13CB4 | `csHadesIntroStruggle` |
| 0x2EA74 | 0x2F8B4 | `csHadesKnifeEnter` |
| 0x52074 | 0x52EB4 | `csHadesKnifeKill` |
| 0x12B0F4 | 0x12BF34 | `hadesKnifeAttLhigh` |
| 0x1300F4 | 0x130F34 | `hadesKnifeAttLlow` |
| 0x1351B4 | 0x135FF4 | `hadesKnifeAttRHigh` |
| 0x13A274 | 0x13B0B4 | `hadesKnifeAttRlow` |
| 0x13F234 | 0x140074 | `hadesKnifeAttShortRound` |
| 0x1455B4 | 0x1463F4 | `hadesKnifeBlock01` |

**A boss's move set is therefore enumerable, named and addressable.** For
`R_HADES.WAD` the 77 clips group as: `cshadesRip01` ×12, `cshadesRip02` ×11,
`csHadesKnife` ×6, `hadesKnifeAtt*` ×5, `csHadesHelme*` ×5, `csHadesIntro` ×4,
`cshadesSoulRip*` ×4, `hadesKnifeBlock*` ×4, and the rest. `R_HERCULES.WAD` yields
**46** at the same table offset (`csHercules*`, `csMiscHercBe*`, `hitWallStuck`, …).

The clip *span* (offsets[i+1] − offsets[i]) is an upper bound on each clip's size,
so every move has a known, bounded byte range in the file.

**Inference.** The container's animation side is a directory of **named clips with
known offsets and spans**, which is the structure a move-set replacement needs.
Combined with E-055 (same-size in-place edits work on this container) it means a
*clip-level* change is mechanically reachable without a full writer — what is
missing is the clip's *internal* encoding, not its location.

**Unknown (this is the remaining gap for "moves").** The internal encoding of a
clip: bone channels, keyframe format, frame count, root motion. Without it a clip
can be located and copied but not authored or retargeted. Note also that this side
of the work does **not** depend on the DMC3 dead end (E-051) — the GoW3R encoding is
in the file and in `eboot.bin`, so it is decodable.

**Tooling.** `tools/gow3/anim.py` (`read_clip_offsets`, `clip_name_at`,
`parse_clips`, `find_table`, `Clip`). `find_table` **validates**: a merely
increasing run is not accepted, because an earlier version mis-fired on
`R_HERCULES.WAD` and returned a table of 1 clip; it now requires ≥80% of a
candidate's offsets to land on clip names. 11 tests (328 total).

**Two bugs of my own, found by those tests:** the last clip's span used
`len(data) - base` instead of `len(data)`, and base detection demanded 12 sample
hits so small tables were rejected — both fixed before commit.



---

## E-056 — `eboot.elf`: file↔vaddr mapping and a reusable RIP-relative reference scanner

**Observation.** `C:\Users\GigelCastel\Desktop\gow3\gow3-windows\out\eboot.elf`
(4,597,471 bytes) is a 64-bit little-endian ELF: `e_entry = 0x144070`, program
header table at `0x40`, 10 headers of 56 bytes. Exactly one `PT_LOAD` is
executable: `p_offset = 0x4000`, `p_vaddr = 0`, `p_filesz = 0x3BD518`, flags
`R|X`. So inside the code segment `vaddr = file_offset - 0x4000` — **not**
`vaddr == file_offset`. The string tables live in a read-only `PT_LOAD` at
`p_offset 0x3C4000` / `p_vaddr 0x3C0000`.

A byte-pattern scan of the executable segment for `lea`/`mov` with a RIP-relative
memory operand — optional REX (`0x40..0x4F`), then `8D`/`8B`, then a ModRM byte
with `(modrm & 0xC7) == 0x05`, then `disp32` — finds **26,706** references.
Requiring the target to equal the vaddr of one of the loader strings reproduces
E-053 exactly:

| target | string vaddrs | instruction refs |
|---|---|---|
| `WAD_` | 21 | 81 |
| `hfsm` | 18 | **9** |
| `ms::tMove` | 2 | 1 (`0xED578`) |
| `attachment::` | 6 | 3 (`0xD0D94`, `0xD0DCE`, `0xDBF14`) |
| `DEPENDENCY` / `.wad` | 1 / 1 | 0 / 0 |
| **total to those 49 string starts** | | **94** |

The nine `hfsm` references are at `0x10BB24, 0x10BD7B, 0x10BFF4, 0x10C5A4,
0x10C7B4, 0x10CAC4, 0x10CD54, 0x10D044, 0x10D2B4` — the same cluster E-053
recorded, an independent confirmation that the AI state machines are named from
data rather than compiled.

**Correction to E-053.** E-053 described the pattern as `modrm = 0x05`. The real
bytes use **any** RIP-relative ModRM (`mod == 00, r/m == 101`), i.e.
`(modrm & 0xC7) == 0x05`. The first `WAD_` reference E-053 listed, `0x100D49`, is
`48 8d 3d 06 04 25 00` = `lea rdi, [rip + 0x250406]` (ModRM `0x3D`, rdi), whose
target is the `WAD_` string at `0x351156`. A `modrm == 0x05` scan misses it.

**Inference.** The mapping plus the scanner locate the code that consumes any
named loader string, which is where the numeric record opcodes live. The scan is a
byte pattern, not a disassembler, so a hit is only meaningful when its target is a
real string address.

**Unknown.** The loader logic itself: the numeric record opcode constants and the
directory→bulk binding (G9/G10) remain [UNKNOWN].

**Tooling.** `tools/gow3/eboot.py` (`ElfImage`, `ProgramSegment`, `from_path`,
`file_offset_to_vaddr`, `vaddr_to_file_offset`, `read`, `find_all`,
`rip_relative_references`, `references_to_string`); 17 unit tests on a synthetic
ELF (no game data committed).

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



---

## E-032 — MOT `+0x22` table: 23 u16 entries, dominated by a constant (F5, bounded slice)

**Observation.** Scanned every MOT chunk in all 161 PAC containers in the asset
root (840 chunks total) and read the `u16` table at header `+0x22`, whose length
is `(header_size - 0x22) / 2` — 23 entries for the common `0x50` header, 31 for
the single `0x60`-header chunk (`pl000_00_8.pac` slot 1). The length relation
held for all 840 chunks.

Raw bytes, `pl021_00_9.pac` slot 0 (file offset `0x10`; chunk-relative `+0x22`,
the worked example from E-026/E-029):

```
file +0x32  38 00 38 00 38 00  ... (22 x u16 = 56 / 0x38) ...  00 00
            chunk +0x22 .. +0x4D: twenty-two 56s, then a 0
```

Install-wide table census over all 840 chunks:

| Table shape | Chunks | Examples |
|---|---|---|
| `56 x 22, then 0` (dominant) | **703** | every `pl021_*.pac` chunk (Vergil), `pl000_00_0/1`, `demo_pl000_00_3.pac` slot 0 |
| `56 x 12, 0 x 10, 56, 0` | 71 | `pl000_00_8.pac` slots 8-29, `pl000_00_9.pac`, `pl000_00_10.pac`, `pl000_00_11.pac` |
| 504-based (`504 x 22 + 0`, `504 x 21 + 0 + 0`, one `480` variant) | 28 | Crimson overlays: `newJudgementCut_*`, `newYamatoHighTime_*`, `newBackslide_*`, `newTaunt*`, `newStyleSwitching*`, `newBaseDanteAnims_*`, `newDrivePart*` |
| `58 x 22, then 0` | 2 | `pl000_00_20.pac` slot 2, `pl000_00_9.pac` slot 6 |
| `56 x 21, then 0, 0` | 18 | `pl002_00_0.pac`, `pl002_00_2.pac` (these chunks have `+0x1C == 23`) |
| `56 x 22, then N` (N varies: 29 … 26755) | 17 | `demo_pl000_00_3.pac` slots 2,3,5-9,15-21,23,29,31 |
| `56 x 31` (header `0x60`) | 1 | `pl000_00_8.pac` slot 1 |

Notes: `504 == 56 * 9`. Within any one chunk the table entries are constant —
nothing varies per table index. For 751/840 chunks the count of non-zero
entries equals `+0x1C - 2` (e.g. `+0x1C == 24` → 22 non-zero entries), but the
mixed 56/0 chunks (71) and the `demo_pl000_00_3.pac` family (17) break that
relation, so it is an observation, not a rule.

**Inference.** The table is **not** per-bone data: the inferred bone count
`+0x1C` (24 in 821/840 chunks) does not match 23 entries, and no entry varies
per index, so the entries cannot be per-bone indices, flags, or offsets. A
per-chunk constant plus a final zero looks like reserved/padded space or a
per-chunk default; `56` was also tested as a record size (`8 * (groups + 4)` for
`groups == 3`) but `pl021_00_9.pac` slot 0 has zero size-56 records, so that
reading fails on real data. The correlation `unknown_1e`/`unknown_20` ∈ {0,
448 = 56 × 8, 504 = 56 × 9} is noted but unexplained.

**Unknown.** What the table denotes; what `56` / `504` / `58` denote; what the
final entry (usually `0`, sometimes a larger value) denotes. Not decodable from
bytes alone — marked [UNKNOWN] in `docs/FORMATS.md` §3.

**Consequence.** `tools/dmc3/mot.py` `parse_mot` already returns the table
(`MotHeader.table`) and enforces `header_size == 0x22 + 2 * len(table)`; no code
change is needed beyond unit tests locking the observed shapes.

---

## E-033 — `pl021.pac` slot 0: six-u32 raw header (F3, bounded slice)

**Observation.** `pl021.pac` (27 entries, data start 0x80). Slot 0 is occupied
at **file offset 0x80**; its span runs to slot 1 (0x39880), a 0x39800-byte
upper bound on the chunk size (E-001). The payload carries no ASCII tag, so
`pac.py` classifies it as "raw" (E-002). First 24 bytes (body-relative,
little-endian):

```
file +0x000080: 05 00 00 00 2B 00 00 00 16 00 00 00 2B 00 00 00 05 00 00 00 01 00 00 00
                 u32=5             u32=43            u32=22             u32=43
                 u32=5             u32=1
```

Bytes body+0x18..~0x0807 are zero; small non-zero fields resume around
body+0x0808. At **body+0x0870 (file offset 0x0008F0)** the bytes read

```
44 44 53 20 7C 00 00 00 07 10 0A 00 00 01 00 00 40 00 00 00
"DDS "          dwSize=0x7C   dwFlags=0x000A1007  dwHeight=256  dwWidth=64
```

an embedded DDS-like blob (dwSize 124 matches a standard DDS header). The
remainder of the ~0x39800-byte span is non-zero and structured; its layout is
undecoded.

Slot 0 is one of nine occupied untagged slots in `pl021.pac` (0, 5, 6, 7,
9, 10, 11, 21, 22; E-008). Their leading bytes differ: slot 10 is a table
of u16 pairs `(0x5C, x)` with `x` increasing by 20; slot 21 is a u16 table
with `0xFFFF` separators; slots 9/11 are f32 arrays. No single header shape
is shared across them.

**Inference.** The six leading u32s of slot 0 look like a small header, but
which fields they are (counts, sizes, offsets, flags) is not established from
these bytes alone; the repeated `43` and `5` are coincidences, not a pattern.
The embedded `DDS ` is an observation, not an identification of the chunk as
a texture.

**Unknown.** Meaning of field_00..field_14 (5/43/22/43/5/1); the body layout
beyond the header; the role of the embedded `DDS ` at body+0x0870; whether any
of the other untagged slots shares slot 0's header shape.

**Consequence.** `tools/dmc3/raw.py` decodes exactly the observed six-u32
header (`RawHeader`, `maybe_raw_header`) and nothing more; exercised by
`tests/test_raw.py` on a synthetic fixture. F3 remains open: this slice
decodes slot 0's header only.


---
## E-034 — `i001_90.tm2` pre-header: all 28 u32s recorded; E-005 claim corrected (F8, bounded slice)

**Observation.** `i001_90.tm2` (65,776 bytes) in
`G:\Games\Devil May Cry HD Collection\data\dmc3\GData.afs\`. The ``DDS `` magic
begins at file offset **0x70**; the preceding 0x70-byte platform header, read as
28 little-endian u32s:

| Offset | u32 value | Hex | Offset | u32 value | Hex |
|---|---|---|---|---|---|
| +0x00 | 0 | 0x00000000 | +0x18 | 0 | 0x00000000 |
| +0x04 | 0 | 0x00000000 | +0x1C | 0 | 0x00000000 |
| +0x08 | 131,328 | 0x00020100 | +0x20 | 64 | 0x00000040 |
| +0x0C | 43,748 | 0x0000AAE4 | +0x24 | 0 | 0x00000000 |
| +0x10 | 16,777,472 | 0x01000100 | +0x28 | 0 | 0x00000000 |
| +0x14 | 1 | 0x00000001 | +0x2C | 0 | 0x00000000 |
| +0x30 | 0 | 0x00000000 | +0x48 | 1,006,632,960 | 0x3C000000 |
| +0x34 | 0 | 0x00000000 | +0x4C | 1,006,632,960 | 0x3C000000 |
| +0x38 | 65,536 | 0x00010000 | +0x50 | 0 | 0x00000000 |
| +0x3C | 0 | 0x00000000 | +0x54 | 0 | 0x00000000 |
| +0x40 | 0 | 0x00000000 | +0x58 | 0 | 0x00000000 |
| +0x44 | 8,388,736 | 0x00800080 | +0x5C | 0 | 0x00000000 |
| +0x60 | 0 | 0x00000000 | +0x64 | 65,664 | 0x00010080 |
| +0x68 | 8 | 0x00000008 | +0x6C | 0 | 0x00000000 |

The DDS blob itself (verified in E-005): `dwSize = 124`, flags `0x00081007`,
256×256, fourCC `DXT3`, one mip level, payload begins at file 0xF0 and runs to
EOF (65,536 payload bytes).

**Correction of E-005.** E-005 reported "only 0x08 and 0x0C are non-zero" among
the pre-header u32s. That is **falsified** by these bytes: non-zero u32s also
appear at +0x10, +0x14, +0x20, +0x38, +0x44, +0x48, +0x4C, +0x64, +0x68. The
wrapper-is-DDS conclusion of E-005 stands; only the pre-header census was
incomplete.

**Observed correlation (not a rule).** +0x38 == 65,536 equals this file's DDS
pitch (`dwPitchOrLinearSize`-adjacent field). With a single TM2 file available
in this install, cross-file correlation to confirm any field's meaning is not
possible from local bytes alone.

**Inference.** None beyond the wrapper structure. Every pre-header field is
**[UNKNOWN]**: +0x08 (0x00020100), +0x0C (0x0000AAE4), +0x10 (0x01000100),
+0x14 (1), +0x20 (64), +0x38 (65,536), +0x44 (0x00800080), +0x48/+0x4C
(0x3C000000 each), +0x64 (65,664), +0x68 (8). Whether any is a version, type,
format hint, dimension, or reserved padding is not established.

**Unknown.** All pre-header field semantics; whether other TM2 files (none
present in this install) share this layout; whether the pre-header varies by
texture format/dimensions. Needs more TM2 samples or engine ground truth.

**Consequence.** No code change is required to extract textures
(`find_dds` / `extract_dds` already work). `docs/FORMATS.md` §4 is updated with
the pre-header census, all fields marked [UNKNOWN], and E-005's pre-header
claim corrected. A synthetic fixture locking the observed bytes is added to
`tests/fixtures.py` with a matching test in `tests/test_tm2.py`.


---
## E-035 — Vergil motion-slot census from real bytes (F7, bounded slice)

**Observation.** Enumerated every MOT chunk in all ten real
`pl021_00_*.pac` files on the install
(`G:\Games\Devil May Cry HD Collection\data\dmc3\GData.afs\`), reading each
chunk's header duration (`+0x0C`/``+0x14``) and the stored record count (u32 at
the track payload start) via `mot_summary()`, then validating the record layer
with `try_walk_records()`. All 108 occupied MOT slots walk cleanly
(0 walk failures). Per group (file → occupied `slot: duration`):

| Group | File | Occupied slots (duration in frames) | Count |
|---|---|---|---|
| 0 | `pl021_00_0.pac` | 0:105 1:61 2:48 3:350 4:69 5:69 6:15 7:60 8:60 9:69 14:103 16:6 17:5 18:4 19:115 20:61 21:61 22:61 30:26 31:105 50:45 51:26 58:60 | 23 |
| 1 | `pl021_00_1.pac` | 0:50 1:45 2:95 3:74 4:81 5:104 6:102 7:80 9:90 11:154 13:50 14:77 15:50 16:115 | 14 |
| 2 | `pl021_00_2.pac` | 0:340 1:200 2:250 3:72 4:110 | 5 |
| 3 | `pl021_00_3.pac` | 0:105 1:115 3:83 4:122 5:131 6:70 7:110 8:29 9:37 10:125 11:152 12:174 13:65 14:90 15:152 16:189 | 16 |
| 4 | `pl021_00_4.pac` | 0:62 1:115 3:98 4:106 5:149 6:25 7:79 8:24 9:36 10:117 11:85 | 11 |
| 5 | `pl021_00_5.pac` | 0:180 1:123 3:83 4:122 5:252 6:82 7:54 8:45 9:10 10:19 11:99 12:165 13:83 14:135 | 14 |
| 6 | `pl021_00_6.pac` | 0:10 1:10 | 2 |
| 7 | `pl021_00_7.pac` | 0:150 1:123 3:94 4:110 5:145 6:82 7:54 8:45 9:119 10:95 11:71 | 11 |
| 8 | `pl021_00_8.pac` | 0:150 1:115 3:98 4:106 5:136 6:25 7:79 8:77 9:99 10:95 11:71 | 11 |
| 9 | `pl021_00_9.pac` | 0:100 | 1 |

Worked example — `pl021_00_9.pac`, slot 0 at file offset **0x10** (the same
chunk E-026/E-029 used): size-prefixed `MOT\0`, `header_size` `0x50`, duration
`100.0`, `+0x1C` bone count `24`, stored `record_count` `69`; all 69 records
walk and the stored count is reached (consistent with E-026).

**Inference.** E-009's group → occupied-slot-count table is confirmed against
real bytes for all ten groups (23/14/5/16/11/14/2/11/11/1). The census above is
**LOCAL evidence**: durations and counts come from shipped bytes, not from the
community thread.

**Overlay anchors (locally confirmed slot targeting).** Comparing the Crimson
overlay `.pac` files to their base files (E-007):

* `newTauntVergilAnims1_pl021_00_2.pac` vs `pl021_00_2.pac`: only slot 1's
  duration differs (200 → 211); slot 0 is 340.0 in both. Overlay filename
  "Taunt" targets **group 2, slot 0** (340 frames).
* `newJudgementCut_pl021_00_3.pac` (and the `Air`/`AirJF` variants) vs
  `pl021_00_3.pac`: the *only* slot whose duration differs is slot 13
  (base 65 → overlay 5 / 11 / 3 across the three variants). The Judgement Cut
  overlays target **group 3, slot 13**.
* `newYamatoHighTime_pl021_00_5.pac` vs `pl021_00_5.pac`: slots 7 (54 → 150)
  and 8 (45 → 51) differ. Targets **group 5, slots 7–8**.

**Unknown.** The mapping from group-local slots to the community thread's
global motion numbers (000–044) and to human-readable move names; every move
name in `docs/ANIMATIONS.md` remains **[EXTERNAL]** (not verified here) until
a clip is exported and compared to in-game footage — that is the F9 move-set
work, which needs the MOT keyframe encoding (F4, blocked on engine ground
truth).

**Consequence.** `tools/dmc3/mot.py` gains `mot_summary()` (duration +
record_count from real bytes) with a unit test on a synthetic fixture; no game
data is read by the test suite. The full census is recorded here as E-035.


---
## E-036 — `SHW ` shader-chunk header: verified bytes across all four chunks (F2, bounded slice)

**Observation.** Read the four `SHW ` chunks of `pl021.pac` (slots 8, 14, 24,
26; slots 24/26 byte-identical) from the real artifact
(`G:\Games\Devil May Cry HD Collection\data\dmc3\GData.afs\pl021.pac`).
Header fields, body-relative, little-endian:

| Offset | Slot 8 (0x75470) | Slot 14 (0x7EB80) | Slot 24 (0x82F90) | Slot 26 (0x85670) |
|---|---|---|---|---|
| +0x00 | char[4] `"SHW "` | `"SHW "` | `"SHW "` | `"SHW "` |
| +0x04 | f32 0.5 | f32 0.5 | f32 0.5 | f32 0.5 |
| +0x08 | u32 0 | u32 0 | u32 0 | u32 0 |
| +0x0C | u32 0 | u32 0 | u32 0 | u32 0 |
| +0x10 | u32 0x00011811 | u32 0x00002707 | u32 0x00020101 | u32 0x00010101 |
| +0x14 | u32 100 | u32 102 | u32 0x000315D8 | u32 103 |
| +0x18 | u32 0 | u32 0 | u32 0 | u32 0 |
| +0x1C | u32 0 | u32 0 | u32 0 | u32 0 |
| +0x20 | u16 0x000A | u16 0x0016 | u16 0x0027 | u16 0x0027 |
| +0x22 | u16 0x0010 | u16 0x0028 | u16 0x0042 | u16 0x0042 |
| +0x24 | u32 0 | u32 0 | u32 0 | u32 0 |
| +0x28 | u32 0 | u32 0 | u32 0 | u32 0 |
| +0x2C | u32 0 | u32 0 | u32 0 | u32 0 |
| +0x30 | u32 0x460 | u32 0x1E0 | u32 0x60 | u32 0x60 |
| +0x34 | u32 0 | u32 0 | u32 0 | u32 0 |
| +0x38 | u32 0x560 | u32 0x460 | u32 0x480 | u32 0x480 |
| +0x3C | u32 0 | u32 0 | u32 0 | u32 0 |
| +0x40 | u32 0x5E0 | u32 0x5A0 | u32 0x690 | u32 0x690 |
| +0x44 | u32 0 | u32 0 | u32 0 | u32 0 |
| +0x48 | u32 0x680 | u32 0x700 | u32 0x900 | u32 0x900 |
| +0x4C | u32 0 | u32 0 | u32 0 | u32 0 |
| +0x50 | zero ×16 | zero ×16 | zero ×16 | zero ×16 |
| +0x60 | table begins | table begins | table begins | table begins |

Worked example — slot 8 raw bytes (file offset 0x75470):

```
+0x00: 53 48 57 20 00 00 00 3f  "SHW "  f32=0.5
+0x08: 00 00 00 00 00 00 00 00  u32=0   u32=0
+0x10: 11 18 01 00 64 00 00 00  u32=0x00011811  u32=100
+0x18: 00 00 00 00 00 00 00 00  u32=0   u32=0
+0x20: 0a 00 10 00 00 00 00 00  u16=0x000A  u16=0x0010  u32=0
+0x28: 00 00 00 00 00 00 00 00  u32=0   u32=0
+0x30: 60 04 00 00 00 00 00 00  u32=0x460  u32=0   (sub-table offset)
+0x38: 60 05 00 00 00 00 00 00  u32=0x560  u32=0   (sub-table offset)
+0x40: e0 05 00 00 00 00 00 00  u32=0x5E0  u32=0   (sub-table offset)
+0x48: 80 06 00 00 00 00 00 00  u32=0x680  u32=0   (sub-table offset)
```

At +0x30's target (chunk+0x460 for slot 8; chunk+0x1E0 for slot 14;
chunk+0x60 for slots 24/26) the bytes read as 16-byte entries of three
small u32 indices plus a zero, e.g. slot 8:

```
chunk+0x460: 00 00 00 00 01 00 00 00 02 00 00 00 00 00 00 00   [0, 1, 2, 0]
chunk+0x470: 03 00 00 00 00 00 00 00 04 00 00 00 00 00 00 00   [3, 0, 4, 0]
chunk+0x480: 05 00 00 00 06 00 00 00 07 00 00 00 00 00 00 00   [5, 6, 7, 0]
chunk+0x490: 05 00 00 00 07 00 00 00 08 00 00 00 00 00 00 00   [5, 7, 8, 0]
```

Slot 14's table at chunk+0x1E0 reads `[0, 1, 2, 0 / 3, 4, 5, 0 / 6, 7, 4, 0 /
8, 9, 10, 0]`; slots 24/26's at chunk+0x60 read `[0, 1, 2, 0 / 3, 0, 2, 0 /
4, 3, 2, 0 / 1, 4, 2, 0 / 5, 6, 7, 0 / 5, 7, 8, 0]`. The sub-table layout
(indices into which buffer, u16 vs u32 per index) is not established from
these bytes alone.

**Inference.** The `SHW ` header is a fixed 0x50-byte block: an f32 0.5 at
+0x04 (4/4 chunks), zero u32s at +0x08/+0x0C/+0x18/+0x1C/+0x24/+0x28/+0x2C/
+0x34/+0x3C/+0x44/+0x4C, varying u32s at +0x10/+0x14, a varying u16 pair at
+0x20/+0x22, and four varying u32s at +0x30/+0x38/+0x40/+0x48 each followed
by a zero u32.  The value at +0x30 points at a sub-table of 16-byte entries
(three small u32 indices plus a zero) inside the chunk in all four observed
chunks — e.g. slot 8's +0x30 == 0x460 lands on `[0, 1, 2, 0 / 3, 0, 4, 0 /
5, 6, 7, 0 / 5, 7, 8, 0]`.  The other three fields (+0x38, +0x40, +0x48)
also point at sub-tables (slot 8: 0x560, 0x5E0, 0x680) whose contents look
like i16 pairs, f32 data (1.0f appears at regular spots) and byte data
respectively; none of the sub-tables' semantics is established.

**Unknown.** The meaning of every header field; what buffer the +0x30 index
table indexes; the layouts and semantics of the +0x38/+0x40/+0x48 sub-tables;
and how the chunk binds materials to textures — the texture-binding half of
issue F2.

**Consequence.** `tools/dmc3/shw.py` exposes `ShwHeader` decoding exactly this
header from real bytes, exercised by unit tests on synthetic fixtures. The
payload beyond the header remains [UNKNOWN]; F2 stays open.


---
## E-037 — `pl021.pac` slot 10: u16 pair table + f32 stream (F3, bounded slice)

**Observation.** `pl021.pac` slot 10 is an untagged (raw) chunk at **file offset
0x077ED0** with span **0x1E0 (480 bytes)** (distance to slot 11 at 0x0780B0).
Its body, chunk-relative (little-endian):

```
+0x00  u16 pairs, stride 4, 23 pairs (bytes +0x00..+0x5B):
pair  0: (92, 132)   pair  1: (92, 152)   pair  2: (92, 172)
pair  3: (92, 192)   pair  4: (92, 212)   pair  5: (92, 232)
pair  6: (92, 252)   pair  7: (92, 272)   pair  8: (92, 292)
pair  9: (92, 312)   pair 10: (92, 332)   pair 11: (92, 352)
pair 12: (92, 372)   pair 13: (92, 392)   pair 14: (92, 412)
pair 15: (112, 432)  pair 16: (92, 432)
pair 17: (92, 132)   pair 18: (92, 132)   pair 19: (92, 132)
pair 20: (92, 132)   pair 21: (92, 132)   pair 22: (92, 132)

Raw bytes +0x00..+0x5B:
5C 00 84 00 5C 00 98 00 5C 00 AC 00 5C 00 C0 00
5C 00 D4 00 5C 00 E8 00 5C 00 FC 00 5C 00 10 01
5C 00 24 01 5C 00 38 01 5C 00 4C 01 5C 00 60 01
5C 00 74 01 5C 00 88 01 5C 00 9C 01 70 00 B0 01
5C 00 B0 01 5C 00 84 00 5C 00 84 00 5C 00 84 00
5C 00 84 00 5C 00 84 00 5C 00 84 00

+0x5C  little-endian f32 stream to end of chunk (first 5 groups):
+0x5C  9A 99 99 3E   -> f32 0.29999998 (~0.3)
+0x60  0A D7 A3 BC   -> f32 -1.0006e-02 (~-0.01)
+0x64  CD CC CC BD   -> f32 -0.10000000 (-0.1)
+0x68  00 00 00 00   -> f32 0.0
+0x6C  66 66 66 3F   -> f32 0.69999999 (~0.7)
```
The remainder of the stream (+0x70..+0x1DF) is zero runs interspersed with
further small-magnitude f32s; no terminator or count field was observed.

Raw bytes at +0x5C:
`9a 99 99 3e 0a d7 a3 bc cc cc cc bd 00 00 00 00 66 66 66 3f ...`

**Inference.** The slot has a clean two-part structure: a fixed u16 pair table
(23 pairs = 92 bytes = 0x5C) followed by an f32 stream. The first u16 of every
pair is 92 (0x5C, equal to the table's byte size in the observed chunk) and the
second element rises by 20 across pairs 0–14 (132..412); pairs 15–22 deviate
((112,432), (92,432), then (92,132)×6). Whether the pair count is stored
somewhere or fixed, what the pairs index, and what the f32 stream encodes are
**not** established.

**Inference (marked [INFERRED], not observation).** 0x5C == 92 equals both the
table's byte size and the constant first element of each pair; this may be a
stride/size field or a coincidence. Not relied on.

**Unknown.** Meaning of the pairs (indices, offsets, UV pairs, …), the pair
count's source, the f32 stream's meaning, and whether this layout recurs in any
other slot (all other untagged slots have different leading bytes, E-008). Not
decodable from bytes alone; engine ground truth needed.

**Consequence.** `tools/dmc3/raw.py` exposes `Slot10Table` (with
`SLOT10_PAIR_COUNT`) decoding exactly this observed layout, exercised by unit
tests on a synthetic fixture. F3 remains open: this slice decodes slot 10's
leading table only; slot 10's f32 stream and all other untagged slots are still
[UNKNOWN].


---
## E-038 — `SHW ` sub-tables: +0x38 index buffer, +0x40 position buffer (F2, bounded slice)

**Observation.** Read the four `SHW ` chunks of `pl021.pac` (slots 8/14/24/26;
slots 24/26 byte-identical) from the real artifact
(`G:\Games\Devil May Cry HD Collection\data\dmc3\GData.afs\pl021.pac`).
The header fields `field_38` (+0x38) and `field_40` (+0x40) are chunk-relative
offsets, and `field_48` (+0x48) is the offset of the next table. For every
chunk the pointer differences exactly equal the sub-table byte sizes:

| Slot | file base | field_38 -> index table | field_40 -> position table | field_48 -> next table | pointer math |
|------|-----------|-------------------------|----------------------------|------------------------|--------------|
| 8 | 0x75470 | 0x560 -> file 0x759d0, 16 tris | 0x5E0 -> file 0x75a50, 10 positions | 0x680 -> file 0x75af0 | `0x5E0-0x560=0x80=16*8`; `0x680-0x5E0=0xA0=10*16` |
| 14 | 0x7EB80 | 0x460 -> 40 tris | 0x5A0 -> 22 positions | 0x700 | `0x5A0-0x460=0x140=40*8`; `0x700-0x5A0=0x160=22*16` |
| 24 | 0x82F90 | 0x480 -> 66 tris | 0x690 -> 39 positions | 0x900 | `0x690-0x480=0x210=66*8`; `0x900-0x690=0x270=39*16` |
| 26 | 0x85670 | 0x480 -> 66 tris | 0x690 -> 39 positions | 0x900 | identical to slot 24 (byte-identical chunks) |

The index table occupies `[field_38, field_40)` and the position table
`[field_40, field_48)` — the two tables are contiguous in all four chunks.

Worked example — slot 8 raw bytes (little-endian):

```
file 0x759d0 (+0x38 table, [u16 i0,i1,i2,u16 0]):
  06 00 0e 00 07 00 00 00   -> (6, 14, 7, 0)
  06 00 05 00 0a 00 00 00   -> (6, 5, 10, 0)
  ...
file 0x75a50 (+0x40 table, [f32 x,y,z,f32 1.0]):
  ce c4 8a c1 9d f7 08 43 a7 36 12 c1 00 00 80 3f   -> (-17.3461, +136.9672, -9.1383, +1.0)
  f2 ec d3 3d 10 5c 0a 43 05 01 6d c1 00 00 80 3f   -> (+0.1035, +138.3596, -14.8127, +1.0)
```

The position values show left/right symmetry across entries (e.g. slot 14:
`(-14.87, +4.02, +7.75, 1.0)` / `(+15.30, +4.02, +7.75, 1.0)`), consistent
with vertex coordinates. The w component is exactly 1.0 in every entry of all
four chunks. The fourth u16 of every index entry is 0 in all four chunks.

The table at `field_48` (+0x48) begins with a run of a constant byte
(slot 8: ten `0x03` bytes; slots 24/26: ten `0x01` bytes; slot 14: zeros)
followed by a u32 stream; its layout is not decoded.

**Inference.** `field_38` points at an index (triangle) buffer of
`[u16 i0, u16 i1, u16 i2, u16 0]` entries; `field_40` points at a vertex
position buffer of `[f32 x, f32 y, f32 z, f32 1.0]` entries. Buffer counts are
derived from consecutive-pointer differences (index count = `(field_40 -
field_38) / 8`, position count = `(field_48 - field_40) / 16`), a verified
invariant across all four chunks. Structure is [PARTIAL]; semantics are
[UNKNOWN].

**Unknown.** Whether the index buffer references the position buffer: the
cross-reference does *not* hold for slots 8/14 (slot 8 max index 15 exceeds its
10 positions; slot 14 max index 30 exceeds its 22 positions), so additional
vertex buffers or separate sub-meshes may be involved — it holds only for slots
24/26 (max index 28 < 39 positions). The layout and meaning of the +0x48 table
are [UNKNOWN]. The texture binding that issue F2 asks for remains [UNKNOWN];
this slice decodes the sub-table structure, not the binding.

**Consequence.** `tools/dmc3/shw.py` gains `ShwIndexTable`, `ShwPositionTable`,
`ShwSubTables` and `parse_shw_sub_tables` / `maybe_shw_sub_tables`, decoding
exactly the observed sub-table structure from real bytes, exercised by 9 new
unit tests on synthetic fixtures (no game data committed). `docs/FORMATS.md`
§5 and `docs/BACKLOG.md` F2 are updated below. F2 stays open: texture binding
and field semantics need engine ground truth.


---
## E-039 — FLVER header of Vergil's body (BD_M_10100) (T7b, bounded slice)

**Observation.** `BD_M_10100.flver` (467,008 bytes) in the prior-art package at
`C:\Users\GigelCastel\Desktop\vergil\parts\bd_m_10100-partsbnd-dcx\BD_M_10100.flver`
(the Bloodborne Vergil mod, E-014). This is the **body** mesh; the weapon was
already obtained via Source .smd/.ascii (E-015). File offset 0x00, little-endian:

```
0x00  46 4C 56 45 52 00  "FLVER\0"                      [VERIFIED magic]
0x06  4C 00                u16 76                        [UNKNOWN]
0x08  14 00                u16 20                        [UNKNOWN]
0x0A  02 00                u16 2                         [UNKNOWN]
0x0C  30 F0 00 00          u32 61488                     [UNKNOWN]
0x10  10 30 06 00          u32 405520                    [UNKNOWN]
0x14  00 00 00 00          u32 0                         [UNKNOWN]
0x18  06 00 00 00          u32 6                         [UNKNOWN]
0x1C  4E 01 00 00          u32 334                       [UNKNOWN]
0x20  06 00 00 00          u32 6                         [UNKNOWN]
0x24  0C 00 00 00          u32 12                        [UNKNOWN]
0x28  4A 36 37 BF          f32 -0.7157   <- six f32s   [UNKNOWN semantics]
0x2C  00 00 00 00          f32 0.0                       [UNKNOWN semantics]
0x30  5D CB 4A BE          f32 -0.1980                   [UNKNOWN semantics]
0x34  47 D0 37 3F          f32 0.7180                    [UNKNOWN semantics]
0x38  7A 3D E5 3F          f32 1.7909                    [UNKNOWN semantics]
0x3C  1E 41 76 3E          f32 0.2405                    [UNKNOWN semantics]
0x40  9E 6D 00 00          u32 28062                     [UNKNOWN]
0x44  9E 6D 00 00          u32 28062                     [UNKNOWN]
0x48  00 01 00 00          u32 256                       [UNKNOWN]
0x4C  00 00 00 00          u32 0                         [UNKNOWN]
0x50  24 00 00 00          u32 36                        [UNKNOWN]
0x54  0A 00 00 00          u32 10                        [UNKNOWN]
0x58  2A 00 00 00          u32 42                        [UNKNOWN]
0x5C..0x7F zero bytes (padding to the 128-byte header block)
```

The six floats at 0x28–0x3F plausibly form a bounding box (E-017 read them as
a box with a 1.79 m vertical extent, consistent with a humanoid body), but that
is an inference, not an observation; every field is [UNKNOWN] here.

From 0x80 onward the file contains 16-byte records grouped into six 32-byte
section entries (e.g. at 0x80: `[49600, 49616, 7, 0]`, `[366, 48160, 0, 0]`);
their layout is recorded in E-040 and every field meaning is [UNKNOWN].

**Inference.** None beyond: the file is a FromSoftware FLVER model whose header
is a fixed 128-byte block; `u32_1c == 334` and `u32_40 == u32_44 == 28062` are
candidates for counts (bones? vertex count?) but are not established.

**Unknown.** Every field meaning except the magic; whether 0x1C/0x40/0x44 are
counts; the bounding-box interpretation; the 16-byte record structure from 0x80;
the vertex declaration, bone table, mesh and index-buffer layout. Not decodable
from this one file alone — engine ground truth or a FLVER spec needed.

**Consequence.** `tools/priorart/flver.py` exposes `FlverHeader` and
`parse_flver_header()` decoding exactly this header from real bytes, exercised
by unit tests on a synthetic fixture mirroring the observed bytes (no game data
committed). The body mesh beyond the header remains [UNKNOWN]; T7b is advanced
but not complete.

## E-040 — FLVER section table: six 32-byte entries at 0x80 (T7b, bounded slice)

**Observation.** `BD_M_10100.flver` (467,008 bytes), same file as E-039, at
`C:\Users\GigelCastel\Desktop\vergil\parts\bd_m_10100-partsbnd-dcx\BD_M_10100.flver`.
From file offset 0x80 to 0x140 the file holds six 32-byte section entries
(each two 16-byte records), little-endian u32s. Verified bytes (offset | u32s):

```
0x0080  49600, 49616, 7, 0        |   366, 48160, 0, 0
0x00A0  49966, 49976, 7, 7        |   360, 48400, 1, 0
0x00C0  50326, 50338, 7, 14       |   362, 48640, 2, 0
0x00E0  50688, 50700, 7, 21       |   370, 48880, 3, 0
0x0100  51058, 51082, 7, 28       |   374, 49120, 4, 0
0x0120  51432, 51442, 7, 35       |   334, 49360, 5, 0
```
Non-pattern data (float/u16 streams) resumes at 0x140, so the table is exactly
these six entries.

**Observed structure (all field meanings [UNKNOWN]):**
- Entry = u32_00, u32_04, u32_08, u32_0c, u32_10, u32_14, u32_18, u32_1c.
- u32_08 == 7 in all six entries; u32_0c == 7 * entry_index (0, 7, …, 35);
  u32_1c == 0 in all six entries; u32_18 takes 0, 1, 2, 3, 4, 5.
- u32_14 = 48160 + 240 * index for all six entries.
- u32_00 forms a running offset: each entry's u32_00 = previous u32_00 +
  previous u32_10 (49600, +366 = 49966, +360 = 50326, +362 = 50688, +370 =
  51058, +374 = 51432). u32_10 values: 366, 360, 362, 370, 374, 334.
- u32_10 of the last entry (334) equals header +0x1C — whether related is not
  established. Count source [UNKNOWN]: header +0x18 == 6 matches the entry
  count; header +0x24 == 12 matches 2 * 6.

**Referenced data (verified locations, meanings [UNKNOWN]):**
- Entry u32_14 points at a "GX**" magic block: exact at 0xBC20 (entry 0),
  0xBE00 (entry 2), 0xBFE0 (entry 4), 0xC0D0 (entry 5); within 4 bytes for
  entries 1 (0xBCD0 → "GX26" at 0xBCD4) and 3 (0xBEE0 → "GX00" at 0xBEE4).
  Block layout (verified at 0xBC20): `"GXNN"`, u32 100, u32 44/64/24,
  u32 0; GX04 at 0xBC44 is additionally followed by u32 0 and f32 data
  (5, 1, 0.5, 0 / 5, 0.5, 1, 0). The same block sequence recurs at 0xBEF0,
  0xBFE0, 0xC0D0; groups end with an f32 0x7FFFFFFF sentinel.
- The u32_14 pointer is exact (delta 0) for entries 0, 2, 4, 5, +4 for entry
  1 and +16 for entry 3; the discrepancy is not explained.
- Entry 0's u32_00 = 49600 = 0xC1C0 opens a UTF-16LE name string:
  `costume_parsn_...`
- Header +0x0C = 61488 = 0xF030 points at u16 index-like data
  (25, 39, 0 / 25, 40, 39 / 25, 1, 2 …). Header +0x10 = 405520 = 0x63010
  points at record data beginning 0, 0x7F7F7F7F, 0x004B0039 …
  Header +0x10 + header +0x0C == file size (405520 + 61488 == 467008) — an
  inference about layout, not an observation of intent.

**Inference.** None beyond raw structure.

**Unknown.** Every field's meaning; whether entries are 32 bytes (count from
+0x18) or 16-byte records (count candidate +0x24 == 12); whether u32_00 is a
name-string offset and u32_10 a size; what the "GX**" blocks encode.

**Correction (superseded by E-041).** E-040 claimed u32_14 is "+4/+16 off" for
sections 1 and 3; re-reading the bytes shows all six sections point exactly at
a GX00 block at 48160 + 240*index. E-041 records the corrected reading.

---

## E-041 — FLVER GX blocks: seven tagged blocks + sentinel per 240-byte group (T7b)

**Observation.** ``BD_M_10100.flver`` (467,008 bytes). Each section's
``u32_14`` (48160 + 240 * index: 0xBC20, 0xBD10, 0xBE00, 0xBEF0, 0xBFE0,
0xC0D0) points exactly at a 240-byte group of eight blocks. Every block opens
with a 4-byte tag, then u32 100 (0x64), then u32 block size, then
``size - 12`` payload bytes:

| Block | Tag | Size | Payload (observed) |
|---|---|---|---|
| 0 | ``GX00`` | 44 | 32 zero bytes |
| 1 | ``GX04`` | 64 | 12 zeros; f32s 5.0, 1.0, 0.5, 0.0, 5.0, 0.5, 1.0, 0.0; 8 zeros |
| 2-6 | ``GX20``/``GX22``/``GX24``/``GX26``/``GX30`` | 24 each | 12 zero bytes each |
| 7 | sentinel u32 0x7FFFFFFF | 12 | empty |

44 + 64 + 5*24 + 12 == 240, matching the section-stride delta
(u32_14 increases by 240 per section). All six groups are byte-identical.
What follows group 5 at 0xC1C0 is the UTF-16 name string opened by section 0's
u32_00 ("costume..."); no seventh group exists (the last "GX" magic in the
file is at 0xC19C).

Worked example — group 0 at 0xBC20 (all values little-endian):

```
0xBC20  47 58 30 30 64 00 00 00 2C 00 00 00   "GX00"  const=100  size=44
        00 * 32                                payload: 32 zero bytes
0xBC4C  47 58 30 34 64 00 00 00 40 00 00 00   "GX04"  const=100  size=64
        00 00 00 00 00 00 00 00 00 00 00 00    payload: 12 zeros
        00 00 A0 40 00 00 80 3F 00 00 00 3F    f32s: 5.0, 1.0, 0.5, 0.0
        00 00 00 00 00 00 A0 40 00 00 00 3F    f32s: 5.0, 0.5, 1.0, 0.0
        00 * 8                                 payload: 8 zeros
0xBC8C  47 58 32 30 64 00 00 00 18 00 00 00   "GX20"  const=100  size=24
        00 * 12                                payload: 12 zero bytes
... GX22/GX24/GX26/GX30 identical, each size 24 ...
0xBD04  FF FF FF 7F 64 00 00 00 0C 00 00 00   sentinel const=100 size=12
```

**Inference.** The section table's ``u32_14`` entries point at GX groups
exactly (all six sections; E-040's "+4/+16 off" claim was imprecise and is
corrected above). The 0x7FFFFFFF tag terminates a group. Tags are ASCII digit
suffixes; their meaning is not established.

**Unknown.** Meaning of every tag (GX00/GX04/GX20/GX22/GX24/GX26/GX30), of
the constant 100, of every size field, and of every payload. The f32 run in
GX04 is vector-like in magnitude but its meaning is not established. This is
raw structure from one file, not a format spec.

**Consequence.** `tools/priorart/flver.py` exposes `FlverGxBlock`,
`FlverGxGroup`, `parse_flver_gx_block`, `parse_flver_gx_group` and
`parse_flver_gx_groups`, decoding exactly this structure from real bytes;
exercised by unit tests on synthetic fixtures (no game data committed). The
body mesh layout beyond the GX groups remains [UNKNOWN]; T7b is advanced but
not complete.

---

## E-042 — TM2 sample census exhausted: all local TM2s share one pre-header (F8 dead end)

**Observation.** Scanned `G:\Games\Devil May Cry HD Collection\data\dmc3\GData.afs\`
for `*.tm2`. Three files exist:

| File | Size | MD5 |
|---|---|---|
| `i001_90.tm2` | 65,776 | 98F463AD02152AC4F96EBB51E4D9CC58 |
| `XboxButtons\i001_90.tm2` | 65,776 | 98F463AD02152AC4F96EBB51E4D9CC58 |
| `PlaystationButtons\i001_90.tm2` | 65,776 | 133F9CA28FE1AF8DEEBDB2783E08C84F |

The root and Xbox copies are byte-identical. The PlayStation copy differs only
in MD5 but its **28-u32 pre-header is byte-identical** to the other two (all
fields from E-034 match: `0x00020100` at +0x08, `0x0000AAE4` at +0x0C,
`0x01000100` at +0x10, `1` at +0x14, `64` at +0x20, `0x00010000` at +0x38,
`0x00800080` at +0x44, `0x3C000000` at +0x48/+0x4C, `0x00010080` at +0x64,
`8` at +0x68). All three embed a `DDS ` blob at file 0x70 (`dwSize=124`,
256×256, fourCC `DXT3`).

**Inference.** There is effectively **one TM2 sample** available locally, so
cross-referencing pre-header fields against varying dimensions/formats is not
possible. The E-034 observation "+0x38 == 65,536 equals the DDS pitch" holds
for all three files but is not a rule — all three are 256×256 DXT3.

**Dead end.** F8's remaining pre-header field semantics cannot be established
from local bytes: more TM2 samples do not exist in this install, and engine
ground truth (or a genuinely different-dimension/format TM2 sample) is
required. F8 stays [UNKNOWN] and is not retried from bytes alone.


---
## E-043 — `pl021.pac` slot 21: u16 segments delimited by `0xFFFF` (F3, bounded slice)

**Observation.** `pl021.pac` slot 21 at file offset `0x07FF00`, span `0x2E0`
(736 bytes = 368 u16s; the next occupied slot is 22 at `0x0801E0`). The
payload carries no ASCII tag, so `pac.py` classifies it as "raw" (E-002). It
is a little-endian u16 stream split into **14 segments** by `0xFFFF`
separators (13 separators). Segment sizes, in u16s:
2, 6, 1, 8, 10, 31, 111, 34, 1, 6, 8, 27, 84, 26 (sum 355 data values + 13
separators = 368 u16s).

Segment 0 verbatim: `(6, 408)`. Separators sit at u16 indices
2, 9, 11, 20, 31, 63, 175, 210, 212, 219, 228, 256, 341.

Two internal regularities are observed (not relied on, not interpreted):

* segment index 5 (size 31) ends in an arithmetic run
  `36, 50, 64, …, 232` stepping by 14, i.e. `36, 36, 36, 50, 64, …, 232`;
* segment index 6 (size 111) repeats a 7-u16 sub-record
  `32767, 0, 32767, 1, 1, 0, VALUE` fourteen times with `VALUE` stepping by
  256 from `771` to `4099`, followed by a tail
  `32767, 0, 32767, 1, 14, 14, 14, 28, 42, 56`.

`0x7FFF` occurs inside segments (e.g. as part of the repeating sub-record)
and is *not* a delimiter.

**Inference.** None beyond structure: the top-level layout of slot 21 is
`0xFFFF`-delimited u16 segments. What each segment indexes, and the meaning of
`0x7FFF` and of the arithmetic runs / repeating sub-records, are [UNKNOWN].

**Unknown.** Segment semantics; whether `0x7FFF` is a sub-delimiter or a data
value (-1 as a signed u16); what the arithmetic runs and repeating
sub-records encode; whether this layout recurs in any other untagged slot.
Not decodable from bytes alone; engine ground truth needed.

**Consequence.** `tools/dmc3/raw.py` gains `Slot21Table` (with
`SLOT21_SEPARATOR`) decoding exactly the observed segmentation, exercised by
unit tests on a synthetic fixture (no game data committed). `docs/FORMATS.md`
§1.3 and `docs/BACKLOG.md` F3 are updated below. F3 remains open: segment
internal layout and all field meanings are [UNKNOWN].


---
## E-044 — WAD bulk header and `DC_` id `0x10` table (G9, bounded slice)

**Observation.** Read-only from two real assets:
`C:\Users\GigelCastel\Desktop\gow3\CUSA01715\EXEC\WAD\PS4_LE\R_SWORD00.WAD`
(87,840 bytes) and `GAZ650.WAD` (13,152 bytes). In both files the record
directory ends at `0xD80` and the bulk data region begins at `0xD80`. The bulk
header is byte-identical except for the u32 at +0x4 and the 16-byte name:

```
file 0xD80: 01 00 77 00   u16 1, u16 0x77
file 0xD84: 69 0d 00 00   u32 3433 (R_SWORD00); GAZ650.WAD: 59 0d 00 00 -> u32 3417
file 0xD88: 30 33 35 32 41 35 38 42   "0352A58B" (R_SWORD00);
            37 32 31 46 42 46 42 32   "721FBFB2" (GAZ650.WAD)
file 0xD90: 5f 46 46 46 46 46 46 46 46   "_FFFFFFFF"
file 0xD98..0xDBF   zero bytes
file 0xDC0: 08 00 01 00 00 00 00 00 01 00 00 00 10 00 00 00   u32s 8, 1, 1, 16
file 0xDD0: 01 00 00 00 00 00 00 00                             u32 1, u32 0
file 0xDE0: 18 00 00 00 00 00 00 00                             u32 24 (R_SWORD00);
            GAZ650.WAD: 20 00 00 00 -> u32 32
file 0xDE8: 69 67 68 74 69 6e 67 20   "ighting " (R_SWORD00)
            b8 06 00 00 00 00 00 00                             (GAZ650.WAD: u32 1720)
```

**The `DC_` id `0x10` chunk** — `R_SWORD00.WAD`: chunk prefix at file `0x14AD8`,
id `0x10`, size 3064, payload at `0x14B1C`. The 3064-byte payload reads as 766
little-endian u32s:

```
idx 0-3   header u32s            0, 0x77 (119), 0, 0x598 (1432)
idx 4-357 118 entries            (u32 flag, u32 offset, u32 value)
idx 358   u32                    0xA4
idx 359+  NUL strings            "CRT_Sword00", "FX", "Bubbles", "Ripples",
                                  "Freezing", "Stoned", "ShatterSystem",
                                  "BasePhysicalAttributes", "Light", "Tint",
                                  "Fire", "Joints", "tSoldier_0",
                                  "PushableMinSpeed", ... ("MOV_*", "BRA_*",
                                  "tActionSetFlags_*", … script object names)
```

All 118 entries carry small u32s. Offsets ascend overall from `0x20` to `0x1654`;
entries at `>= 0xD80` point into the bulk region and land on real object data:
file `0xD84` begins `69 0d 00 00 "0352A58B_FFFFFFFF"` (bulk header + 4);
file `0xDE4` begins `00 00 00 00 "ighting "`; file `0xE44` reads as u16s
`90, 88, 84, 96, …`; file `0x15BC` reads f32 `50.0`; file `0x1654` reads
`54, f32 2.5078, …`. Values ascend overall from `0x5A4` to `0xBED`. Flags are
small u32s (observed `0x18`, `0x21`, `0x30`, `0x97`, `0x143`-`0x153`,
`0x9F`, `0xA4`; early entries use `0x143`-`0x153`, later ones alternate
`0x9F`/`0xA4`). `GAZ650.WAD`'s id `0x10` chunk is degenerate: six u32s
`(0, 1, 0, 0x10, 0x15D, "WAD_")`, no entries, no strings.

**Inference.** The id `0x10` chunk describes named objects: the triplets pair a
flag with a file offset and a value, and the trailing string pool holds object
names (script/FX objects: "CRT_Sword00", "MOV_SwordPickupWalk",
"tActionSetFlags_86", "BRA_SwordPickupWalk", "NB_SwordBank"). The entry count
(~118) is of the same order as the string count (~100 visible), consistent with
one entry per named object — **not proven**.

**Unknown.** The exact meaning of `flag`, `offset` (reference frame — file
offsets match object data at 0xD84+, but early entries point at the directory
and header regions) and `value`; whether each entry binds to one directory
resource name, one string, or one bulk object; whether the layout generalizes
beyond `R_SWORD00.WAD` (single sample). The entry → directory-resource binding
is therefore still **[UNKNOWN]** and a WAD writer remains blocked.

**Consequence.** `tools/gow3/wad.py` gains `parse_dc10_table()` — a face-value
parser returning exactly the observed layout (header, entries, strings), with no
semantic claims, exercised by unit tests on synthetic fixtures (no game data
committed). `docs/FORMATS.md` §7 records this structure as
[PARTIAL structure / UNKNOWN semantics]. Binding entries to resources and the
`WadGraph` name→WAD binding stay open (issues G9/G10).

---

## E-045 — WadGraph registry structure: header and 32-byte name records (G10, bounded slice)

**Observation.** Read-only from
`C:\Users\GigelCastel\Desktop\gow3\CUSA01715\EXEC\WAD\PS4_LE\DEPENDENCYGRAPH.IFF`
(265,776 bytes; read only — no writes to the install). The banner `"WadGraph"` sits
at offset 0x08 (E-021). Header, all little-endian:

```
file 0x00: 17 00 01 00 f0 0d 04 00   u16=23   u16=1   u32=265712 (0x00040DF0)
file 0x08: "WadGraph" + zero padding to 0x3F   (banner field, 0x38 bytes)
```

`u32 265712 == file_size - 0x40` on this single sample — [UNKNOWN] whether it is
a size, an end offset, or a coincidence.

From `0x40` the file holds **32-byte records at stride 0x20**; non-matching
windows are skipped, so the record list is non-contiguous (388 breaks). Every
matching record, verified on all **2,617 records** spanning `0x40`..`0x2D440`:

```
+0x00  u32 name_offset   correlates with the NUL-terminated name strings stored
                          later in the file (~0x2C000..EOF): observed to point
                          exactly at a name start for 198/2617 records, and
                          within a few bytes of one for 2,337/2,617 (the
                          remainder land on non-printable bytes). Relation
                          [UNKNOWN].
+0x04  u32 0                             [VERIFIED zero on all records]
+0x08  u32 field_b                       varies (0 in many records; 2,151 distinct
                          values overall, max 99,604,228)                 [UNKNOWN]
+0x0C  u32 field_d                       0 in 2,472/2,617 records; scattered
                          large values otherwise                         [UNKNOWN]
+0x10  u16 field_c                       0..65,535                       [UNKNOWN]
+0x12  u64 0xFFFFFFFFFFFFFFFF (-1)       constant sentinel               [VERIFIED]
+0x1A  u8  0                             [VERIFIED zero on all records]
+0x1B  u8  pad_byte                      observed 0x00/0x01/0x02/0x24/0x2C/0x34/0x3C [UNKNOWN]
+0x1C  u32 0x55555555                    constant trailer                [VERIFIED]
```

Worked example — record at file `0x1C7E0`:

```
2e af 03 00 00 00 00 00 00 00 00 00 00 00 00 00   name_offset=241454 (0x0003AF2E)
53 08 ff ff ff ff ff ff ff ff 00 02 55 55 55 55   field_c=0x0853, sentinel=-1,
                                                    pad=0x02, trailer=0x55555555
```

`name_offset == 241454` lands exactly on the NUL-terminated string
`"Stub_1472"` at file `0x3AF2E` (`53 74 75 62 5f 31 34 37 32 00`). Other records
resolve to names such as `ARArcher01`, `R_GP_055.xvag`; `record_name()` in
`tools/gow3/wadgraph.py` is a best-effort heuristic (marked as such) because the
exact `name_offset` → string relation is not established.

**Inference.** None beyond structure: the registry is a header plus name records
referencing the file's embedded NUL-separated name table (which E-021 sampled as
~3,693 names incl. entities `R_*`, actors `AR*`, levels, 2,109 `.xvag` audio
names and ~3,344 `Stub_*` placeholders).

**Unknown.** Exact `name_offset` → string relation; semantics of `field_b`,
`field_d`, `field_c`, `pad_byte`; and — the binding G10 asks for — how a
registry name maps to a physical WAD (no WAD name table or index observed in
this file). `field_b` is not a small WAD index (values up to ~10^8), so it is
probably not a direct binding; engine ground truth or a second WadGraph sample
is needed. **A registry writer is not possible from these bytes.**

**Consequence.** `tools/gow3/wadgraph.py` exposes `WadGraphHeader`,
`WadGraphRecord`, `parse()`, `parse_records()` and `record_name()`, decoding
exactly the observed layout from real bytes, exercised by unit tests on
synthetic fixtures (no game data committed). Issue G10 stays open: the name→WAD
binding remains [UNKNOWN].


## E-046 — DDS → PNG conversion: uncompressed BGRA32 verified, compressed DXT documented as unsupported (T2)

**Observation.** `tools/dmc3/dds.py` (`dds_to_png`) converts an uncompressed
BGRA32 DDS payload to PNG:
- Synthetic uncompressed BGRA32 DDS: output parses as a valid PNG (signature,
  IHDR = RGBA 8-bit, per-chunk CRC32 valid, IDAT is one zlib stream whose
  decompressed rows equal the input pixel bytes exactly with filter type 0,
  IEND terminator). Alpha is preserved byte-for-byte via the BGRA → RGBA
  reorder. Verified by 8 unit tests in tests/test_dds.py on synthetic data;
  no game bytes are committed.
- The real `i001_90.tm2` embedded DDS (E-005/E-034): DXT3, 256×256, compressed
  → `dds_to_png` raises `DdsError` with a message pointing at an external DXT
  decoder. All three local TM2s are DXT3 (E-042).

**Inference.** The uncompressed DDS → PNG path is correct on synthetic data.
Compressed textures cannot be converted by this tool yet.

**Unknown.** Whether any DDS in this install is uncompressed (all three local
TM2s are DXT3, so the converter currently converts no local texture). A DXT1/
DXT3/DXT5 decoder or an external tool (texconv) is needed for the compressed
path; that path is deliberately left undecoded rather than guessed, since a
from-memory DXT decoder cannot be verified against engine ground truth.

**Consequence.** `tests/test_dds.py` (8 tests) locks the converter's structural
behaviour; `docs/FORMATS.md` §4.2 records [PARTIAL] coverage; `docs/BACKLOG.md`
T2 row updated. Issue #9 stays open until the compressed path is resolved.

**Superseded by E-047:** the compressed DXT path is now implemented and verified
on synthetic blocks plus the real `i001_90.tm2` payload; this entry's
"cannot be converted yet" conclusion no longer holds.

## E-047 — Real DXT3 payload decoded from `i001_90.tm2` (T2, bounded slice)

**Observation.** `G:\Games\Devil May Cry HD Collection\data\dmc3\GData.afs\i001_90.tm2`
(65,776 bytes), read only:

```
0x70:  44 44 53 20 7C 00 00 00 07 10 08 00 00 01 00 00   "DDS " dwSize=124, dwFlags=0x00081007
0x80:  00 01 00 00 00 01 00 00 00 00 00 00 01 00 00 00   w=256, h=256, pitch=65536, depth=0, mipmaps=1
0x90:  47 49 4D 50 2D 44 44 53 5D 09 03 00 00 00 00 00   reserved1 begins "GIMP-DDS" (file re-saved by GIMP)
...
0xBC:  20 00 00 00 04 00 00 00 44 58 54 33                ddspf.dwSize=32, dwFlags=0x4 (fourCC), fourCC="DXT3"
0xC8:  00 00 00 00 ...                                      RGB bit count and masks = 0
0xDC:  ... 10 00 00 00                                       dwCaps = 0x1000
```

The DDS payload runs from file offset **0xF0 to EOF**: exactly 65,536 bytes
= 4,096 DXT3 blocks × 16 bytes = one 256×256 image at one mip level.
Payload block 0 (file 0xF0–0xFF):
`00 00 00 00 00 00 00 00 00 00 00 00 AA AA AA AA`
(alpha bitmap all zero; colour endpoints c0=c1=0x0000; all texel indices 2).

**Inference.** Decoded per the public S3TC rules (4-bit alpha expanded ×17;
c0=c1 → index 2 selects the endpoint colour, here black), block 0's texels are
all `(0, 0, 0, 0)`. Running `dds_to_png` end-to-end on the real file yields a
valid PNG: signature + IHDR (256×256, color type 6 = RGBA) + one IDAT zlib
stream (18,400 compressed bytes) + IEND, all chunk CRCs valid. Image row 0's
texels 8–15 carry alpha 17, 17, 51, 51, 68, 85, 85, 119 from blocks 2–3's
alpha bytes (file 0x110–0x127); blocks 0–1 contribute zero alpha for texels
0–7. This PNG output is **tool output**, not engine ground truth; the decode
itself follows the public specification and is locked by synthetic-block tests
in tests/test_dds.py.

**Unknown.** The in-game semantic of the alpha channel (transparency, gloss,
…) is not established from bytes alone; neither is whether the GIMP re-save
altered the payload relative to a retail image. DX10 extended headers and
other fourCCs are not decoded (documented `DdsError`); none occur locally.


## E-048 — PNST raw-block header decoded (F6, bounded slice)

**Observation.** Read-only from both weapon archives
(`plwp_vergilsword.pac`, `plwp_newvergilsword.pac`). Slots 0 and 3 of each
file are raw blocks (no ASCII tag) of identical size 36,864 bytes
(0x30..0x9030 and 0xB3A0..0x143A0). Every one of the four blocks begins with
the same 8-byte little-endian header:

```
plwp_vergilsword.pac slot 0 (file 0x30): 01 00 00 00 11 00 00 00
                                         u32 field_a = 1
                                         u32 field_b = 17 (0x11)
plwp_vergilsword.pac slot 3 (file 0xB3A0): 01 00 00 00 11 00 00 00  (identical)
plwp_newvergilsword.pac slot 0 (file 0x30): 01 00 00 00 11 00 00 00  (identical)
plwp_newvergilsword.pac slot 3 (file 0xB3A0): 01 00 00 00 11 00 00 00  (identical)
```

After the header the body opens with a zero-filled run: in every block the
first non-zero byte is at **body+2049** (`01 02 00 e4 aa 00 00 00 01 80 00 01
00 00 00 00 …`), and 32,233 of the 36,856 body bytes are non-zero, so the
tail is structured data, not padding. The header's field meanings and the tail
layout are not established from bytes alone.

A second raw block appears only in `plwp_newvergilsword.pac` (slot 9,
0x88F20..0x890B0, 400 bytes): a u16 stream beginning `06 00 da 00 ff ff 04 00
ff ff`, heavy on `0x0052` ('R') values, with `0xFFFF` separators at u16
indices 2, 4, 45, 110, 151 and a `0x7FFF`/`-1`-patterned tail — superficially
reminiscent of pl021.pac slot 21's segments (E-043) but not the same layout.

**Inference.** `u32 1, u32 17` is a shared raw-block header across the four
slots in both archives; `field_b == 17` (0x11) is constant, not per-slot. The
tail's meaning (and whether field_b is a type, version, count, or size)
requires engine ground truth. No raw block's payload is decoded.

**Unknown.** Semantics of `field_a`/`field_b`; the tail structure; whether the
body+2049 zero-run length is significant; slot 9's u16 stream; whether any raw
block corresponds to a known weapon sub-structure.

**Consequence.** `tools/dmc3/pnst.py` gains `PnstRawBlock` (field_a, field_b),
`parse_pnst_raw_block()` and `maybe_pnst_raw_block()`, decoding exactly the
8-byte header from real bytes; `tests/test_pnst.py` gains `TestPnstRawBlock`
(5 tests) on synthetic fixtures (no game data committed). `docs/FORMATS.md`
§2 records the header as [PARTIAL]; `docs/BACKLOG.md` F6 row updated. F6
remains open: payload semantics need engine ground truth.


## E-049 — SHW `+0x48` region is not a uniform table; slots 24/26 are not byte-identical (F2 correction)

**Observation.** Re-reading the four real `SHW ` chunks of `pl021.pac`
(slots 8/14/24/26) shows the **headers are byte-identical** (every field at
+0x00..+0x50 matches between slots 24 and 26), but the **payloads diverge at
body+0x11**: slot 24 continues `02 00 00 d8 15 03 ...` while slot 26 continues
`01 00 00 67 00 00 00 ...`, and their tails differ (slot 24 ends
`0x01`×40+`0x00`×8 immediately before the next chunk; slot 26 ends in zeros).
So slots 24/26 share a header but are **not** byte-identical chunks.

The `+0x48` region likewise has no uniform structure across the four chunks:
slot 8 holds a 16-byte preamble (`0x03`×10 + zeros) followed by
`[u32,u32,u32,u32=0]` triple entries with indices 0–9; slot 14 holds a
32-byte zero preamble followed by a mixed u32 stream (values 0–11); slot 24
holds `0x01`×40+`0x00`×8 (48 bytes, then the chunk ends); slot 26 is all
zeros across its `+0x48` region. All four regions were read to each chunk's
exact span (derived from the PAC offset table).

**Correction.** E-036's claim that "slots 24 and 26 are byte-identical `SHW `
chunks" and E-038's table row "identical to slot 24 (byte-identical chunks)"
hold for the header only and are falsified for the payload.

**Inference.** None beyond structure: the `+0x48` sub-table (the texture-binding
lead that issue F2 asks about) is not a spec-able uniform table from these
bytes.

**Unknown.** What the `+0x48` region encodes; why slots 24/26 differ; the
texture binding. Not retried from bytes alone — engine ground truth needed.

---

## E-050 — F1 dead end: `MOD ` payload body beyond +0x5C needs engine ground truth

**Observation.** Scanned all 286 `MOD ` chunks across the install (E-030)
and decoded the body prefix for all four `pl021.pac` `MOD ` chunks (E-031):

| Offset | Field | Observation |
|---|---|---|
| body +0x00..+0x1B | zero bytes | 28 bytes, all chunks |
| body +0x1C | u16 marker | `0x8001`, constant across all chunks |
| body +0x1E | u16 count | varies per mesh: 474/300/182/182 |
| body +0x24 | u32 | varies per mesh: 768/192/128/128 |
| body +0x4C..+0x5B | four f32s | vector-like magnitudes (tens to ~113) |
| body +0x5C | u32 repeat | equals count only for byte-identical slots 23/25 |

**Inference.** The `MOD ` header is a fixed 0x24-byte block and the body
prefix is a fixed 0x60-byte block, both fully decoded. The payload body
layout **beyond** body +0x60 (vertices, indices, normals, UVs, skin weights)
remains entirely undecoded.

**Dead end.** Cross-referencing against the prior-art FLVER body
(E-014/E-015, T7b) was considered: the FLVER header, section table, and GX
blocks are decoded (E-039/E-040/E-041), but the FLVER vertex/index buffer
layout beyond the GX groups is itself undecoded and needs a FromSoftware
FLVER spec or engine ground truth. The MOD `count` field's referent
(vertices? primitives? bones?) and the vertex declaration cannot be
established from DMC3 bytes alone.

**Status.** F1 is **not retried from bytes alone**. Engine ground truth
(disassembly of the mesh vertex loader, or an in-game frame capture
correlated with decoded vertex data) is required. This is a recorded dead
end, not an abandoned item — it is unblocked the moment engine ground truth
becomes available.

**Update (E-069).** The DMC3 engine itself is available locally: `dmc3.exe` in
the install root is a normal, unpacked x86-64 PE. `tools/dmc3/pe.py` maps its
sections and scans its code for string references, so the ground truth F1 was
waiting for is now **present on disk** — F1 is blocked on decoding work, not on
evidence acquisition.

---

## E-051 — F4 dead end: MOT keyframe u16[1..3] semantics need engine ground truth

**Observation.** Walked every MOT chunk in all ten `pl021_*.pac` files
(7,659 records, ~87,700 keyframe groups, 0 walk failures):

* Record layer fully decoded (E-019): `u32 record_count` followed by
  self-describing records `(u16 size, u16 groups, u16 field_a, u16 field_b,
  data)`.
* Keyframe group first u16 decoded (E-026): `frame = u16[0] − 0x8000`,
  monotonic and bounded by header duration, verified on all 840 install
  chunks (623,060 keyframes, 0 violations on Vergil chunks).
* Preamble/keyframe split bounded (E-028/E-029): each record = `field_a`
  preamble groups (3 f32 pairs each, |v| typically ≤ 10) followed by
  `groups` keyframe groups. `field_a == 3` in 7,656/7,659 records. Preamble
  is **not** a stored base pose (0/7,659 matches).
* u16[1..3] census (E-028): per-keyframe signed u16 values spanning
  [−32768, 32767], modal values ±0x3FFF (~±0.5 Q15, ~5,500 hits/channel of
  87,662), varying per keyframe within a record (not constant).

**Inference.** Each keyframe group = offset-binary frame time + three
quantized 16-bit channels, consistent with per-bone position or rotation
components in Q15 fixed point — but **channel assignment, scale, and zero
point are not established from bytes alone**. No record→bone mapping exists
in the bytes (no field matches a bone index 0–23, no field varies as a bone
selector). field_b is always 0 observed.

**Dead end.** The u16[1..3] channel semantics, scale, zero point, preamble
group semantics, and record→bone mapping cannot be established from DMC3
bytes alone. Engine ground truth (disassembly of the animation player, or
comparing a decoded clip against an in-game capture) is required.

**Status.** F4 is **not retried from bytes alone**. This is a recorded dead
end; unblocked the moment engine ground truth becomes available.

**Update (E-069).** The DMC3 engine (`dmc3.exe`, install root) is a normal,
unpacked x86-64 PE and is readable with `tools/dmc3/pe.py`; the extension
dispatch near `.mot` at `.text` RVA `0x2E01D2` is the lead to the motion loader.
The ground truth F4 was waiting for is now locally available.


---
## E-052 — `pl021.pac` slot 5: `0xFFFF`-delimited u16 segment stream (F3, bounded slice)

**Observation.** `pl021.pac` slot 5 at **file offset 0x06B6E0**, span **0x4B30**
(19,248 bytes = 9,624 u16s; the next occupied slot is 6 at 0x070210). The
payload carries no ASCII tag, so `pac.py` classifies it as "raw" (E-002). Read
as a little-endian u16 stream:

```
file +0x06B6E0: 06 00 d0 37 ff ff 04 00 ff ff 46 00 ac 07 4e 0d be 0e
                 u16=6        u16=0x37D0   sep       u16=4   sep
                 u16=70       u16=0x07AC   u16=0x0D4E u16=0x0EBE ...
file +0x06B6F0: e2 15 54 1d 36 26 a4 26 c0 2d 5a 33 be 0e be 0e
                 u16=0x15E2   u16=0x1D54   u16=0x2636 u16=0x26A4
                 u16=0x2DC0   u16=0x335A   u16=0x0EBE   u16=0x0EBE ...
```

It splits into **215 segments** delimited by **214** `0xFFFF` separators.
Segment sizes (u16s) open `2, 1, 34, 60, 5, 13, 13, 13, 13, 15, …`; the tail
holds much larger segments (the largest observed is 378 u16s). Non-zero bytes
number 8,952 / 19,248 and run from offset 0x0000 to 0x4B2B — essentially the
whole span. `0x7FFF` (308 occurrences) appears **inside** segments and is
**not** a delimiter — exactly as in slot 21 (E-043). Most common u16 values:
0 (3,062), 1 (568), 3 (524), 32767 (308), 2 (267), 4 (235). Segment 0 is
verbatim `(6, 0x37D0)` — like slot 21's segment 0 `(6, 408)`, both open with
`6`, but slot 5's segmentation (215 segments) differs from slot 21's (14),
so they are decoded separately.

**Inference.** Slot 5 shares slot 21's segment-stream structure: a
`0xFFFF`-delimited u16 table in which small opening segments look like
headers/indexes and larger tail segments look like data blocks. That is a
structural observation only; what the segments index, what `(6, 0x37D0)` at
segment 0 means, and what `0x7FFF` means inside segments are [UNKNOWN].

**Unknown.** Segment semantics; whether the segment count (215) is stored
anywhere in the chunk; the large tail segments; how slot 5 relates to slot 21
beyond sharing the delimiter. Not decodable from bytes alone; engine ground
truth needed.

**Consequence.** `tools/dmc3/raw.py` gains a shared `_split_u16_segments`
helper plus `Slot5Table` / `maybe_slot5_table` (slot 21's `Slot21Table` now
delegates to the same helper with unchanged behavior), decoding exactly the
observed segmentation from real bytes and exercised by unit tests on
synthetic fixtures (no game data committed). `docs/FORMATS.md` §1.3 and
`docs/BACKLOG.md` F3 are updated below. F3 remains open: slots 6, 7, 9, 11,
22 and all field meanings are still [UNKNOWN].


---
## E-059 — GoW3R animation clip header: a fixed 0x38-byte name field, then the size (G9/F9, bounded slice)

**Observation.** `R_HADES.WAD` (85,727,632 bytes), read-only. The clip directory of
E-058 points `base + offsets[i]` at each clip; reading that byte range shows a
**fixed per-clip header**. `clip[0]` (`angryKratosWalk`, file `0x5A74`):

```
0x5A74 (+0x000)  61 6e 67 72 79 4b 72 61 74 6f 73 57 61 6c 6b 00  angryKratosWalk.
0x5A84 (+0x010)  cd cd cd cd cd cd cd cd cd cd cd cd cd cd cd cd
0x5A94 (+0x020)  cd cd cd cd cd cd cd cd cd cd cd cd cd cd cd cd
0x5AA4 (+0x030)  cd cd cd cd cd cd cd cd 40 3c 00 00 00 00 00 00  ........@<......
0x5AB4 (+0x040)  cd cd cd cd cd cd cd cd cd cd cd cd cd cd cd cd
0x5AC4 (+0x050)  cd cd cd cd cd cd cd cd cd cd cd cd 00 cd 00 00
0x5AD4 (+0x060)  01 00 00 00 01 00 cd cd 00 01 00 00 89 88 08 3d
0x5AE4 (+0x070)  00 cd 00 00 00 00 00 00 01 00 cd cd 40 3c 00 00
0x5AF4 (+0x080)  89 88 08 3d 00 cd 00 00 00 00 00 00 01 00 cd cd
0x5B04 (+0x090)  40 3c 00 00 89 88 08 3d 0b cd 00 00 00 00 00 00
0x5B14 (+0x0A0)  01 00 cd cd 40 3c 00 00 89 88 88 3c 00 00 00 00
```

Fields, verified on **every** clip of two WADs (`R_HADES.WAD` 77 clips,
`R_HERCULES.WAD` 46 clips):

| offset | type | observation | status |
|---|---|---|---|
| `+0x00` | char[0x38] | NUL-terminated clip name; the name is a **fixed 0x38-byte field**, because the size below lands at `+0x38` whatever the name's length | [VERIFIED] |
| `+0x38` | u32 | **clip size** — equals `offsets[i+1] − offsets[i]` for 76/77 (Hades) and 45/46 (Hercules) clips; the one mismatch each is the *final* clip, whose directory span is instead `len(file) − offset` (83,651,932 for `csHadesFlickL`), so the stored value (34,304) is the real bound | [VERIFIED] |
| `+0x3C` | u32 | `0` on 123/123 clips | [VERIFIED] |
| `+0x6C` | f32 | `1/30` on 114 clips, `1/15` on 9 | [VERIFIED] |
| `+0x7C`, `+0x90`, `+0xA4` | u32 | equal `+0x38` on 123/123 clips | [VERIFIED] |
| `+0xA8` | f32 | `1/60` on 123/123 clips | [VERIFIED] |

The remaining bytes are `0xCD`-filled or repeat values like `0x0000CD00`,
`0xCDCD0001`, `0xCCCCCCCC` (the MSVC uninitialized-memory patterns) and pointer-like
u32s (`0x43440106`, `0xD3EFBBA7`), so no further field is assigned a meaning.

For context, the ANM blob head (E-058's descriptor says data starts at `0xE00`)
holds the character name and the table base:

```
0xE00 (+0x000)  03 00 01 00 00 00 00 00 00 00 00 00 00 00 00 00
0xE10 (+0x010)  6b 0f 5b b7 00 00 00 00 00 00 00 00 88 00 00 00
0xE20 (+0x020)  00 00 00 00 80 04 00 00 40 00 10 00 4e 00 00 00   u32 0xE2C = 78
0xE30 (+0x030)  04 00 00 00 48 61 64 65 73 00 00 00 00 00 00 00   "Hades" at 0xE34
0xE40 (+0x040)  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
0xE60 (+0x060)  00 00 00 00 00 00 00 00 00 00 00 00 3e e3 60 13
0xE70 (+0x070)  c0 8f a0 00 b4 01 00 00 34 4c 00 00 74 88 00 00   u32 0xB4=436, then offsets
```

**Inference.** The ANM clip record is framed like a WAD directory record's *name*
part: a 0x38-byte name field, then integers. The stored size is the authoritative
clip bound, so the last clip is the only one whose E-058 span is an over-estimate.
Equalling `+0x38`, the three copies at `+0x7C/+0x90/+0xA4` look like three
per-track sizes, and the `1/30 … 1/60` floats like sampling rates, but that is a
structural analogy, **not** a decoded meaning.

**Unknown.** The semantics of `flags`, the three size copies and the two frame
rates; the `0xCD`/`0xCC` fill (uninitialized memory carried into the file?); the
clip's *internal* encoding (channels, keyframes, root motion); and whether a
same-size in-place replacement of a clip is safe (E-055 makes same-size edits
mechanically possible). Engine ground truth (`eboot.bin`) or an authored-vs-stock
comparison is the route.

**Consequence.** `tools/gow3/anim.py` gains `ClipHeader`, `parse_clip_header()` and
the `CLIP_*` offset constants; `Clip` gains a `size` field read from the header
(the directory span is retained as the upper bound), so `Clip.end` is now correct
for the final clip. All values are read straight from the bytes; no field meaning
is asserted beyond the name and size. Unit-tested on a synthetic clip record
(no game data committed). `docs/FORMATS.md` §7.7 and `docs/BACKLOG.md` F9 updated.

---

## E-060 — GoW3R animation clip header: size ×4, frame rate ×4 + reciprocal, frame count and loop flag (G9/F9, bounded slice)

**Observation.** The same two archives read read-only in E-059 —
`R_HADES.WAD` (85,727,632 B) and `R_HERCULES.WAD` (63,144,480 B) under
`C:\Users\GigelCastel\Desktop\gow3\CUSA01715\EXEC\WAD\PS4_LE\` — clipped by E-058's
directory. **All 123 clips** (77 + 46) were censused: every u32-aligned offset in
`+0x00..+0x123` of every clip.

Four relations hold on **all 123 clips**, with no exception:

| relation | result |
|---|---|
| `u32 @ clip_size` at exactly four offsets `+0x38`, `+0x7C`, `+0x90`, `+0xA4` | 123/123; no fifth offset in `+0x00..+0x123` carries the size |
| `f32 == f32@+0x6C` at exactly four offsets `+0x6C`, `+0x80`, `+0x94`, `+0x110` | 123/123; no fifth offset carries the rate |
| `f32@+0x10C × f32@+0x6C == 1` | 123/123; worst \|product − 1\| = **5.215e-08** (binary32 rounding only) |
| `f32@+0x114 == float32(1 / (u16@+0xF6 − 1))` | 123/123, **exact binary32 equality** |

`u16@+0xF6` takes 44 distinct values in `15..686` — `angryKratosWalk` 41,
`csHadesIntro` 141, `hadesKnifeBlockEnter` 15, `cshadesRip01Stab01` 31,
`csHadesKnifeEnter` 396, `csHadesFlickL` 686.

`u16@+0xF4` is `1` on **11/123** clips and `0` on the other 112. The eleven are,
verbatim: `csHadesKnifeKillIdle`, `cshadesRip01Idle`, `cshadesRip01IdleL`,
`cshadesRip01IdleR`, `csHadesRip02Idle`, `cshadesRip02IdleL`, `cshadesRip02IdleR`,
`hadesKnifeIdle`, `csHadesHelmetRipIdle`, `hadesKnifeStrafeIdle`,
`csMiscHercBeatingIdle`. Two further clips whose names contain "Idle"
(`hadesKnifeIdleB`, 51 frames; `hadesKnifeIdleF`, 81 frames) hold `0`.

Every other u32 in `+0x00..+0x123` is **constant on 123/123 clips**, including the
`0xCD`/`0xCC` uninitialized-memory bytes — e.g. `+0x3C` = 0, `+0x5C` = 0x0000CD00,
`+0x60` = 1, `+0x64` = 0xCDCD0001, `+0x68` = 0x100, `+0x70` = 0x0000CD00,
`+0x74` = 0, `+0x78` = 0xCDCD0001, `+0x84` = 0x0000CD00, `+0x88` = 0,
`+0x8C` = 0xCDCD0001, `+0x98` = 0x0000CD0B, `+0x9C` = 0, `+0xA0` = 0xCDCD0001,
`+0xA8` = float32(1/60), `+0xAC` = 0, `+0xB0` = 0, `+0xE4` = 0x00100000,
`+0xE8` = 0xCCCCCCCC, `+0xEC` = 0x43440106, `+0xF0` = 0xD3EFBBA7,
`+0xF8` = 0x00020002, `+0xFC` = 0, `+0x100` = 0, `+0x104` = 0x30,
`+0x108` = 0x50, `+0x118` = 0, `+0x11C` = 0x60, `+0x120` = 0x00010000,
`+0x128` = 0x00800000, `+0x130` = 0x00010001, `+0x138` = 0x037B0000,
`+0x14C..+0x158` = 0xFFFFFFFF. (`+0x15C` and `+0x17C` are constant within each
file but differ between the two, so they are not claimed as global constants.)

Within `+0x00..+0x123` the only per-clip-varying u32s are therefore `+0x38`,
`+0x6C`, `+0x7C`, `+0x80`, `+0x90`, `+0x94`, `+0xA4`, `+0x10C`, `+0x110`,
`+0xF4` and `+0x114`; from `+0x124` onward the u32s are pointer-like and differ
per clip (e.g. `0x003612A0`, `0x000890F3`, `0x00341230`).

**Inference.** `u16@+0xF6` is **[INFERRED]** the clip's frame count: the 44
values in `15..686` read as counts, and `+0x114 == float32(1/(N−1))` is then the
sample spacing of an `N`-point curve normalised to `[0,1]` — the standard
encoding for a keyframe track, which is why the relation is *exact*. `u16@+0xF4`
is **[INFERRED]** a loop flag, because all 11 clips that set it are `*Idle*`
clips; the two `Idle`-named clips that do not set it mean the flag is **not**
identical to "the name says Idle", so this one stays unproven. The four-fold size
and four-fold frame-rate repetition, and the separately-stored reciprocal at
`+0x10C`, look like redundant per-track copies written by a serializer — a
structural analogy, **not** a decoded meaning.

**Unknown.** The meaning of every value not listed above; what the four copies
index; why `hadesKnifeIdleB`/`hadesKnifeIdleF` do not set the `+0xF4` flag; the
`0xCD`/`0xCC` fill; and the clip's internal encoding (channels, keyframes, root
motion), which remains the gap for F9/"moves".

**Consequence.** `tools/gow3/anim.py` gains `CLIP_RATE_COPY_OFFSETS`,
`CLIP_RATE_RECIPROCAL_OFFSET`, `CLIP_LOOP_OFFSET`, `CLIP_FRAME_COUNT_OFFSET`,
`CLIP_SAMPLE_RATE_OFFSET`, `CLIP_SIZE_OFFSETS`, `CLIP_FRAME_RATE_OFFSETS`,
`float32()`, `expected_sample_rate()`, and a `ClipHeader` carrying `frames`,
`loop_flag`, `sample_rate`, `frame_count_rate` and `rate_copies` with the four
E-060 relations exposed as `size_repeat_ok` / `rate_repeat_ok` / `reciprocal_ok`
/ `sample_rate_ok` and `header.invariants()`. `CLIP_HEADER_MIN` grows to `0x118`
(the last field read). All values are read straight from the bytes; a relation
that fails is reported, never silently raised. Unit-tested on a synthetic clip
record (no game data committed). `docs/FORMATS.md` §7.7 and `docs/BACKLOG.md`
F9/G9 updated.


## E-061 — GoW3R clip descriptor tail: five 16-byte-aligned fields and a data-section marker (G9/F9, bounded slice)

**Observation.** E-060 censused `+0x00..+0x123`; this slice censuses
`+0x120..+0x15B` on **all 123 clips** (77 `R_HADES.WAD`, 46 `R_HERCULES.WAD`,
read-only from `C:\Users\GigelCastel\Desktop\gow3\CUSA01715\EXEC\WAD\PS4_LE\`).

The fixed descriptor does **not** stop at `+0x123`. In `+0x120..+0x15B`:

| offset | observation across 123/123 clips |
|---|---|
| `+0x124`, `+0x12C`, `+0x134`, `+0x13C`, `+0x144` | 16-byte aligned (`value % 16 == 0`) **and** `0 < value < file_size` |
| `+0x140`, `+0x148` | small unaligned values (`+0x140` 6/77 aligned, `+0x148` 6/77) |
| `+0x128` = `0x00800000`, `+0x130` = `0x00010001`, `+0x138` = `0x037B0000` | constant |
| `+0x14C`, `+0x150`, `+0x154`, `+0x158` | constant `0xFFFFFFFF` |
| `+0x15C` | u16 = `0x0015` (21) on 123/123 |
| `+0x160` | u16 = `0x000C` (12) on 123/123 |

That is five per-clip aligned fields, two per-clip unaligned fields, three
constant u32s and four sentinels, then the data section opens with the marker pair
`u16 0x15, u16 0x0C`. Censusing `+0x15C` and `+0x160` across the 123 clips gives
only three and four distinct u32 values respectively, all sharing those low u16s.

The `+0x12C` values are shared between clips. In `R_HADES.WAD`, 18 of 77 clips
reuse another clip's `+0x12C`; the groups are semantically coherent — e.g.
`0x14F0`: `hadesKnifeAttLhigh`, `hadesKnifeAttLlow`, `hadesKnifeAttRHigh`;
`0x1350`: `angryKratosTaunt1`, `angryKratosTaunt2`; `0x12D0`:
`cshadesRip01Stab03`, `cshadesRip01Stab04`, `cshadesRip02Stab01`,
`cshadesRip02Stab04`, `hadesKnifeBlockEnter`. In one Hades pair the `+0x124`
values differ by exactly 16 (`hadesKnifeYankTug` `0x431350`, `cshadesRip02Win`
`0x431360`), i.e. two clips reference overlapping byte ranges.

**Inference.** The five aligned fields are **[INFERRED]** to be file offsets into
a **shared** data pool — alignment, in-file range and cross-clip sharing all fit
offsets, and none fits an ordinary numeric parameter. Whether they are pointers,
offsets relative to some base, or counts-of-16 cannot be settled from these bytes,
so the reader exposes raw values and an `aligned_ok` property only. The fixed
descriptor block ends at `+0x158` and the per-clip data section begins at
`+0x15C`; E-060's "from `+0x124` onward the u32s are pointer-like and per-clip" is
imprecise for `+0x128`/`+0x130`/`+0x138` (constant) and `+0x14C..+0x158`
(sentinel).

**Unknown.** What the five aligned fields and the two unaligned fields index;
whether the pool is separate from the ANM blob; the meaning of the three
constants and the `+0x15C`/`+0x160` marker pair; and the clip's internal encoding
(channels, keyframes, root motion) after `+0x15C`. Engine ground truth
(`eboot.bin`/`eboot.elf`) is the route.

**Consequence.** `tools/gow3/anim.py` gains `ClipDescriptorTail`,
`parse_clip_descriptor_tail()` / `maybe_clip_descriptor_tail()`, the
`CLIP_TAIL_*` / `CLIP_DATA_*` constants, and `ClipDescriptorTail.invariants()`.
All 123 real clips satisfy `aligned`/`constants`/`sentinel`/`markers` when parsed
against the archives (read-only); the parser is unit-tested on a synthetic clip
record (no game data committed). `docs/FORMATS.md` §7.7 and `docs/BACKLOG.md`
F9/G9 updated.


---
## E-062 — `pl021.pac` slot 9: a flat 224-f32 array, and the stale `E-053` citation corrected (F3, bounded slice)

**Observation.** `pl021.pac` slot 9 (read-only, `G:\Games\Devil May Cry HD
Collection\data\dmc3\GData.afs\pl021.pac`) is an untagged ("raw") chunk at **file
offset `0x077B50`** (490,320), span **896 bytes** (the next occupied slot is 10 at
`0x077ED0`). The whole span is exactly **224 little-endian f32s** — no ASCII tag,
no count field, no separator. Raw bytes at the head:

```
file +0x077B50: 66 66 26 41 9a 99 99 bf 00 00 20 41 00 00 40 41
                 f32=10.4     f32=-1.2     f32=10.0     f32=12.0
file +0x077B60: 9a 99 99 bf 00 00 70 41 66 66 26 41 cd cc 4c bf
                 f32=-1.2     f32=15.0     f32=10.4     f32=-0.8
file +0x077B70: cd cc cc 40 66 66 46 41 cd cc 4c bf 00 00 40 41
                 f32=6.4      f32=12.4     f32=-0.8     f32=12.0
file +0x077B80: 00 00 bc 41 9a 99 99 bf 9a 99 99 3e 00 00 20 42
                 f32=23.5     f32=-1.2     f32=0.3      f32=40.0
```

First 24 values: `10.4, -1.2, 10.0, 12.0, -1.2, 15.0, 10.4, -0.8, 6.4, 12.4,
-0.8, 12.0, 23.5, -1.2, 0.3, 40.0, 13.0, -1.5, 25.0, 200.0, 500.0, 150.0, 150.0,
500.0`.

Census over all 224 values: **206 non-zero** (indices 0…210) and **18 trailing
zeros** (indices 211…223); **83 distinct** values; min `-790.0` (index 202), max
`9000.0` (index 138). Most common: `0.0` (18), `500.0` (15), `150.0` (10),
`60.0` (10), `10.0` (8), `20.0` (8), `120.0` (7), `5.0` (7), `12.0` (6),
`300.0` (6). Values are not all integer-valued (e.g. `23.5`, `13.75`, `0.3`).

**Inference.** The array length is exactly the chunk span (`896 = 4 × 224`), which
is consistent with a **self-delimiting flat array** — but whether the count is
stored anywhere (e.g. in another slot or in code) is not established from slot 9's
bytes. None of the values look like byte offsets or primitive indices (they are
non-integer and include negative magnitudes), so the array is probably **not** an
index/offset table; what it is (UVs, collision/camera/parameter data, …) is not
decidable from these bytes.

**Unknown.** What the 224 values index; why the array is 224 long; the meaning of
the trailing zero run; whether slot 9 pairs with any other slot (e.g. slot 10's
f32 stream, E-037). Engine ground truth needed.

**Citation correction.** `tools/dmc3/raw.py` and `tests/fixtures.py` carried the
slot-9 layout under "evidence E-053", but the ledger's E-053 is the `eboot.bin`
reference scan — wrong. Slot 9's array is recorded here as **E-062**; both
citations now read E-062. The parser (`Slot9Table` / `maybe_slot9_table`) already
read the observed layout; this slice adds the missing ledger entry, the first
`TestSlot9Table` unit tests, and the spec text in `docs/FORMATS.md` §1.3.

**Consequence.** No parser logic changed. `tests/test_raw.py` gains
`TestSlot9Table` (length, count constant, verbatim real head, rejection of
wrong-length input) on the existing synthetic `raw_chunk_slot9()` fixture (no game
data committed). `docs/FORMATS.md` §1.3 and `docs/BACKLOG.md` F3 updated. F3 stays
open: slots 6, 7, 11, 22 and all field meanings are still [UNKNOWN].


---

## E-063 — `eboot.elf`: the `WAD_` references and the two loader strings that are not referenced (G9/G10, bounded slice)

**Observation.** Read-only from
`C:\Users\GigelCastel\Desktop\gow3\gow3-windows\out\eboot.elf` (4,597,471 B),
using the corrected RIP-relative scanner (E-056) plus a new **limited
instruction decoder** (`ElfImage.reference_context` /
`string_reference_contexts` in `tools/gow3/eboot.py`), cross-checked against
capstone 5.0.9 (a local recon tool, **not** a repository dependency).

1. **The strings `.wad` (`vaddr 0x35D7C7`) and `DEPENDENCY` (`vaddr 0x330686`)
   each occur once but have ZERO RIP-relative references.** The standing route
   *"find the loader via the `.wad` / `DEPENDENCY` references"* therefore finds
   nothing. Only `WAD_` (21 occurrences, **81** references) and `hfsm`
   (18 occurrences, 9 references) are reachable this way.

2. **Every `WAD_` reference loads the string with a RIP-relative `lea`** and then
   either compares it or passes it to a helper. Decoded prefixes (address:
   instruction, with the resolved operand):

   * `0x10FCB: lea rsi, [rip+0x2DF5C0]` → target `0x2F0592`, then
     `0x10FD2: mov edx, 4`. Exact bytes:
     `48 8d 35 c0 f5 2d 00 | ba 04 00 00 00`. So the banner prefix `"WAD_"` is
     handed to the following call with an explicit **length 4**. This is the only
     `WAD_` site that supplies a length immediate.
   * Of the 81 sites, the first directly-following call is `0x1F7200` at **25**,
     `0x1AAC30` at **15**, `0x1AAC80` at **7**, `0x2E9D70` at 2, `0x1AACF0` at 2,
     `0x2E9E00`/`0x1011A0`/`0x15BB30` at 1 each; the remainder are followed by a
     second `lea` or a non-decoded instruction.
   * `0x100D49: lea rdi, [rip+0x250406]` → target `0x351156`, then
     `call 0x1011A0`. Disassembling `0x1011A0` shows an **object
     registration/lookup routine**: it derives a kind via `0x1F7200`, calls
     virtual methods through `[rax+0x80]` / `[rax+0x88]`, and iterates a
     `(u32 id, u16 field)` table (`movsxd rax,[r12]; add rax,r12;
     mov edi,[rax+r14*8]; movzx edx,word[rax+r14*8+4]`) with count `[r12+0xC]`.

3. **False lead recorded.** A whole-image disassembly finds **42**
   `and eax, 0x80000000` sites in `0x40187..0x43C5B`; each is paired with
   `or eax, 0x3F800000` and `vsqrtss`/`vmulss` — a **float sign-bit / reciprocal
   routine**, not marker handling. Recorded so the `0x80000000` marker
   hypothesis is not re-tried against that region.

**Inference.** The `WAD_`-reference route reaches **object/asset name
registration and lookup** code (helpers `0x1F7200`, `0x1011A0`, `0x1AAC30`),
**not** the byte-level directory-record dispatcher: no site references the
numeric record opcodes (`1`, `2`, `3`, `0x12`, `0x15`, `0x80000000 | n`). The one
site that passes an explicit constant (`0x10FCB`) uses **4**, matching the
four-character `"WAD_"` prefix — the banner is matched by a **4-byte prefix
comparison**, not by whole-string equality.

**Unknown.** The directory-record dispatcher that reads the numeric opcodes; the
entry → resource binding (E-044) and the `WadGraph` name → WAD binding (E-045).
The semantics of `0x1F7200` / `0x1011A0` / `0x1AAC30` beyond "name → object" are
unproven. The reference scanner sees only RIP-relative `lea`/`mov`; a string
moved as an immediate or through an offset table is invisible to it, which is why
`.wad`/`DEPENDENCY` show zero hits.

**Tooling.** `tools/gow3/eboot.py` gains `DecodedInstruction` and
`_decode_instruction` — a deliberately tiny decoder for exactly the forms a
string-reference site uses (RIP-relative `lea`/`mov`, `mov r32, imm32` /
`mov r64, imm64`, `call rel32`) — plus `ElfImage.reference_context` and
`string_reference_contexts`, so a site's trailing constants and callee are
readable without a general disassembler. Decoding stops at the first unrecognised
byte, so the result is always a prefix, never a guess. 8 unit tests on a
synthetic ELF (no game data committed); the module stays stdlib-only.


---

## E-064 — GoW3R clip data section: a typed record preamble, and E-061's "markers" explained (G9/F9, bounded slice)

**Observation.** E-061 stopped at the data section's first bytes at `+0x15C`.
This slice reads the opening records there on **all 123 clips** (77 `R_HADES.WAD`
+ 46 `R_HERCULES.WAD`, read-only from
`C:\Users\GigelCastel\Desktop\gow3\CUSA01715\EXEC\WAD\PS4_LE\`).

The data section opens with a stream of **tagged u16 records**. Every record
carries the constant u16 `0x000C` in its **third slot**; the records come in two
word-lengths and the section is laid out as:

```
lead records     4 u16 each:  tag, arg, 0x000C, value      (4 or 5 of them)
terminator       2 u16:       0x0000, 0x0000
count            u16
tail records     5 u16 each:  tag, arg, 0x000C, value, extra   (4, 5 or 7)
terminator       u16:         0x0000
```

Measured on 123/123 clips:

| quantity | values |
|---|---|
| lead record count | 4 (115 clips) or 5 (8 clips) |
| lead tags (in order) | `0x15, 0x16, 0x18, 0x0B` — or `0x15, 0x16, 0x17, 0x18, 0x0B` for the 5-record variant |
| tail record count | 5 (98), 7 (14) or 4 (11) |
| tail tags | drawn from `{0x0B, 0x0F, 0x10, 0x1B, 0x1C, 0x1D, 0x1E}`; `0x0F` and `0x10` occur once each in every clip |
| `count` | u16, range **15..272**, 81 distinct values; `angryKratosWalk` 41, `csHadesIntro` 72, `csHadesKnifeKill` 188 |
| discriminator | `0x000C` in the third slot of **every** record, 123/123 |

Worked example, `angryKratosWalk` (`R_HADES.WAD`, data section at `0x5BD0`, raw
bytes verbatim):

```
file +0x5BD0: 15 00 08 00 0c 00 60 00 16 00 00 01 0c 00 90 00
file +0x5BE0: 18 00 50 00 0c 00 70 08 0b 00 39 80 0c 00 f0 0a
file +0x5BF0: 00 00 00 00 29 00 1b 00 39 80 0c 00 30 0b 00 00
file +0x5C00: 1d 00 31 00 0c 00 b0 0f c0 00 1e 00 01 00 0c 00
file +0x5C10: 40 11 00 07 0f 00 05 00 0c 00 50 11 00 00 10 00
file +0x5C20: 33 00 0c 00 60 11 c0 00 00 00 cc cc ...
```

which parses as lead `(0x15,0x08,0x60) (0x16,0x100,0x90) (0x18,0x50,0x870)
(0x0B,0x8039,0xAF0)`, terminator, `count = 0x29 = 41`, then tail
`(0x1B,0x8039,0xB30,0x0000) (0x1D,0x0031,0xFB0,0x00C0) (0x1E,0x0001,0x1140,0x0700)
(0x0F,0x0005,0x1150,0x0000) (0x10,0x0033,0x1160,0x00C0)`, terminator. The `0x0B`
lead record's `arg` (`0x8039`) is repeated as the first tail record's `arg`; both
belong to the `0x8000 | n` family seen in the WAD directory (`n` = `0x39` = 57).
After the tail terminator the region is `0xCC` fill, then further u16 tables.

**Inference.** E-061's "two data-section markers" are **not** separate markers:
`u16 0x0015` at `+0x15C` is the first record's **tag** and `u16 0x000C` at
`+0x160` is that record's **discriminator**, which the same constant occupies in
every record. The recurring `0x000C` reads as a per-record type/kind field, and
the fixed `lead`/`tail` shapes as two groups of typed properties, but that is not
proven.

**Unknown.** The `count` semantics (not the frame count — `csHadesIntro` is 141
frames but `count` 72), the meaning of every tag and every `arg`/`value`/`extra`,
and how the records relate to the keyframe data that follows (`+0x15C`-onward).
The `0x8000 | n` ids may be class/type ids as in the WAD directory, but that is
[INFERRED] only. Engine ground truth (`eboot.bin`/`eboot.elf`) is the route.

**Consequence.** `tools/gow3/anim.py` gains `ClipDataRecord`,
`ClipDataPreamble`, `parse_clip_data_preamble()` / `maybe_clip_data_preamble()`
and the `CLIP_DATA_*` constants; the reader is strict (a wrong discriminator, a
missing terminator or a truncated buffer returns `None`) and exposes only observed
values plus `discriminated_ok` / `tags_known_ok`. All 123 real clips parse; 9 new
unit tests run on a synthetic clip record (no game data committed).
`docs/FORMATS.md` §7.7 and `docs/BACKLOG.md` F9/G9 updated.


## E-065 — GoW3R clip data section: each preamble record's last u16 is a 16-byte-aligned offset to a sub-block (G9/F9, bounded slice)

**Observation.** E-064 decoded the record shapes at the start of a clip's data
section but left every `value` field [UNKNOWN]. This slice rereads the preamble
on **all 123 clips** (77 `R_HADES.WAD` + 46 `R_HERCULES.WAD`, read-only from
`C:\Users\GigelCastel\Desktop\gow3\CUSA01715\EXEC\WAD\PS4_LE\`) and censuses the
last u16 of every lead and tail record (the field E-064 called `value`):

| relation | result |
|---|---|
| the record values strictly increase in file order | **123/123** |
| every value is a multiple of 16 | **123/123** |
| `values[0] == round_up(preamble byte length, 16)` | **123/123** |
| every `data_start + value` is inside the clip (`< clip.offset + clip.size`) | **123/123** |

The preamble byte length is `2 * (4·lead + 2 + 1 + 5·tail + 1)`
(E-064's shape: 4 u16 per lead record, a two-u16 terminator, the `count`, 5 u16
per tail record, a one-u16 terminator). Worked examples, raw bytes verbatim
(`data_start` = the clip's `+0x15C`):

```
angryKratosWalk      lead 4 tail 5  preamble  90 B -> round_up 0x60  first value 0x60
  values 0x60 0x90 0x870 0xAF0 0xB30 0xFB0 0x1140 0x1150 0x1160
  data_at_0x5BD0: 15 00 08 00 0c 00 60 00 16 00 00 01 0c 00 90 00 ...
csHadesIntroStruggle lead 5 tail 5  preamble  98 B -> round_up 0x70  first value 0x70
  values 0x70 0x350 0x8F0 0xA50 0xC40 0xC90 0x12A0 0x1410 0x1460 0x14A0
  raw: 15 00 38 00 0c 00 70 00 16 00 b8 00 0c 00 50 03 17 00 18 00 ...
csHadesIntroWin      lead 5 tail 7  preamble 118 B -> round_up 0x80  first value 0x80
cshadesRip01IdleR    lead 4 tail 4  preamble  80 B -> round_up 0x50  first value 0x50
hitWallStuckWin1     lead 4 tail 7  preamble 110 B -> round_up 0x70  first value 0x70
```

The first value lands immediately after the preamble (90 B used, 96 reached), the
last three `angryKratosWalk` values differ by exactly 16, and the largest value on
every clip stays inside the clip's own `size`.

**Inference.** The last u16 of a preamble record is an **offset relative to the
clip's data-section start** (`clip.offset + CLIP_TAIL_END`), not a scalar: the
preamble is a directory of 16-byte-aligned sub-blocks that begin right after it.
The base is fixed by the alignment rule — only the data-section start makes
`values[0] == round_up(preamble length, 16)` hold on all 123 clips; a clip-relative
base would put `values[0]` inside the fixed header. This supersedes E-064's
[UNKNOWN] verdict on the `value` field.

**Unknown.** What each sub-block contains and what the tags, `arg`, `extra` and
`count` mean. The keyframe/curve encoding inside the sub-blocks is **still the F9
gap** — this slice proves where the sub-blocks are, not what they hold. The
`value` fields are structurally offsets, but no pointer/type semantics are claimed
beyond "offset from the data-section start".

**Consequence.** `tools/gow3/anim.py`'s `ClipDataPreamble` gains `values`,
`word_count`, `byte_length`, `increasing_ok`, `aligned_ok`, `first_offset_ok`,
`data_targets()` and the extended `invariants()` (`increasing`, `aligned`,
`first_offset`); the constants `CLIP_DATA_ALIGNMENT = 0x10`,
`CLIP_DATA_LEAD_TERMINATOR_WORDS`, `CLIP_DATA_COUNT_WORDS`,
`CLIP_DATA_TAIL_TERMINATOR_WORDS` are added. 7 new unit tests
(`TestClipDataOffsets`) run on a synthetic clip record (no game data committed);
the full suite is **379 tests, all green**. `docs/FORMATS.md` §7.7 and
`docs/BACKLOG.md` F9/G9 are updated.


## E-066 — GoW3R clip data section: the record offsets name **typed sub-blocks**, one of which nests a preamble (G9/F9, bounded slice)

**Observation.** E-065 proved each preamble record's last u16 is a 16-byte-aligned
offset into the clip's data section, but left the sub-block *contents* unknown.
This slice reads those sub-blocks on **all 123 clips** (77 `R_HADES.WAD` + 46
`R_HERCULES.WAD`, read-only from
`C:\Users\GigelCastel\Desktop\gow3\CUSA01715\EXEC\WAD\PS4_LE\`) and censuses them.

**A. The tag names the sub-block's kind.** Each sub-block is addressed by exactly
one preamble record, so the record's tag types the block. The tag census (first
eight bytes of every sub-block) separates the tags cleanly:

| tag | n | distinct 8-byte heads | head (most common) |
|---|---|---|---|
| `0x15` | 123 | 8 | `10 01 c0 11 80 12 00 18` |
| `0x16` | 123 | **1** | `00 00 30 00 60 00 90 00` |
| `0x18` | 123 | 9 | `10 00 60 01 c0 01 f0 01` |
| `0x0F` | 123 | 13 | `50 00 a0 01 20 03 50 03` |
| `0x10` | 123 | 82 | `c0 0a 00 0a 10 09 b0 08` |
| `0x0B` | 123 | 95 | `28 00 00 00 00 00 00 00` |

The tag-`0x16` sub-block has a **single** head on 123/123 clips.

**B. The tag-`0x16` sub-block opens with a fixed 128-entry table.** Its first
128 u16 are exactly `0x30 * k` for `k = 0..127` — a 256-byte table spanning
`0x1800` — on **123/123 clips**, with the run stopping at index 128 on every one
of them. Raw head, `angryKratosWalk` (`R_HADES.WAD`, sub-block at `0x5C60`):

```
00 00 30 00 60 00 90 00 c0 00 f0 00 20 01 50 01   k=0..3
...
80 17 b0 17 e0 17 00 18 ...                        k=126,127 (0x17A0, 0x17D0)
```

(`0x1800 = 0x30 * 128` is the span the `00 18` fill values seen elsewhere carry.)

**C. The tag-`0x10` sub-block contains a *nested* data-section preamble.** The
tag-`0x10` block is the last one (it runs to the clip's `end`) and is the largest
(4,676..244,068 bytes). Searching it with E-064's **strict** parser, requiring at
least 3 lead *and* 3 tail records so a degenerate all-zero start cannot match,
finds exactly one nested preamble at a **16-byte-aligned offset 64..208 bytes in,
on 122/123 clips**. Worked example, `angryKratosWalk` (block at `0x6D30`, nested
at `+0x90`):

```
file +0x6DC0: 15 00 10 00 0c 00 70 00 16 00 d8 00 0c 00 30 01
             18 00 78 00 0c 00 d0 07 19 00 08 00 0c 00 70 0b
             0b 00 22 80 0c 00 90 0b 00 00 00 00 75 00 1b 00
             22 80 0c 00 c0 0b 00 00 1d 00 04 00 0c 00 70 0e ...
```

lead `(0x15,0x10,0x70) (0x16,0xD8,0x130) (0x18,0x78,0x7D0) (0x19,0x08,0xB70)
(0x0B,0x8022,0xB90)` (`0x19` is a lead tag not seen at the outer level), terminator,
`count = 0x75 = 117`, then five tail records — the same E-064 shape. The nested
shapes observed are `(5,5)` (73), `(5,7)` (15), `(4,5)` (15), `(6,5)` (7),
`(5,4)` (5), `(4,4)` (5), `(6,7)` (1), `(4,7)` (1).

**The single exception:** `attCestusCrush` (`R_HERCULES.WAD`, offset `0x76C34`)
has no qualifying nested preamble in its tag-`0x10` sub-block. Recorded as an
observation, not explained.

**Inference.** The clip data section is **recursive**: E-065's offsets are a
directory of typed sub-blocks, and the tag-`0x10` sub-block is (or contains) a
nested data section of the same kind. That makes the keyframe/curve encoding a
matter of recursing into these sub-blocks rather than an opaque byte stream. The
tag→block typing is structural (tag `0x16`'s one head on 123/123 is the strong
form) but the *meaning* of every tag is still unproven.

**Unknown.** What any sub-block holds; what the tags, `arg`, `extra` and `count`
mean; why `attCestusCrush` differs; and the leaf keyframe/curve encoding, which is
still the F9 gap. No pointer or type semantics beyond "offset" (E-065) and "typed
by tag" (this entry) are claimed.

**Consequence.** `tools/gow3/anim.py` gains `tag16_prefix_length()`,
`find_nested_preamble()`, `ClipSubBlock`, `ClipSubBlocks` and
`parse_clip_sub_blocks()`, plus `CLIP_DATA_TAG16` / `CLIP_DATA_TAG16_PREFIX_WORDS`
= 128 / `CLIP_DATA_TAG16_STEP` = 0x30 / `CLIP_DATA_TAG10` /
`CLIP_DATA_NESTED_MIN_RECORDS` = 3. `ClipSubBlocks` reports the two relations as
`tag16_prefix_ok` / `nested_ok` (evidence, not a verdict). 10 new unit tests
(`TestClipSubBlocks`) run on a synthetic clip whose sub-blocks carry the observed
shapes; no game data is committed. The reader exercised read-only against both
real archives gives **123/123** `tag16_prefix_ok` and **122/123** `nested_ok`.
The full suite is **389 tests, all green**. `docs/FORMATS.md` §7.7 and
`docs/BACKLOG.md` F9/G9 are updated.


## E-067 — GoW3R clip data section: the recursion is exactly two levels, and each tag-0x16 block carries a second offset table (G9/F9, bounded slice)

**Observation.** E-066 left two questions open: the tag-`0x16` table's
"continuation past index 128" and "the nested preamble's own sub-blocks". This
slice answers both, read-only from `R_HADES.WAD` (77 clips) and `R_HERCULES.WAD`
(46 clips) under `C:\Users\GigelCastel\Desktop\gow3\CUSA01715\EXEC\WAD\PS4_LE\`.

**A. The data section recurses exactly two levels.** Splitting the nested preamble
inside the outer tag-`0x10` sub-block with the same reader (E-064/E-065), on all
123 clips:

| quantity | result |
|---|---|
| clips with a data section | 123/123 |
| data-section chains of length 1 | **1** (`attCestusCrush`, `R_HERCULES.WAD`) |
| chains of length 2 | **122** |
| chains of length 3 or more | **0** |

So the nested preamble, in turn, has a tag-`0x10` sub-block that holds **no**
further preamble — the structure is recursive but shallow, and the leaf data sits
inside the level-2 sub-blocks. The nested preamble keeps every E-065 offset
invariant on 122/122: strictly increasing, 16-byte aligned, and
`values[0] == round_up(preamble byte length, 16)`.

**B. The nested preamble adds tag `0x19` to the vocabulary.** The outer lead tags
are exactly `{0x0B, 0x15, 0x16, 0x17, 0x18}` (E-064) and the outer tail tags
`{0x0B, 0x0F, 0x10, 0x1B, 0x1C, 0x1D, 0x1E}`. At the nested level the lead tags may
also carry `0x19` (`101/122` clips), in three observed shapes:

```
0x15 0x16 0x18 0x0B            21 clips   (no 0x19)
0x15 0x16 0x18 0x19 0x0B      93 clips
0x15 0x16 0x17 0x18 0x19 0x0B  8 clips
```

Tail shapes at the nested level: `0x1B 0x1D 0x1E 0x0F 0x10` (82),
`0x1B 0x1C 0x1B 0x1D 0x1E 0x0F 0x10` (17), `0x1B 0x1C 0x1D 0x0F 0x10` (13),
`0x1B 0x1D 0x0F 0x10` (6), `0x1B 0x1D 0x1E 0x10` (3), `0x1B 0x1E 0x0F 0x10` (1).
`0x19` is **not** an outer lead tag on any clip and **not** in E-064's tag sets.

**C. Every tag-`0x16` sub-block continues past the `0x30 * k` table with a second
offset table.** Both at the outer level and at the nested level, the `0x30 * k`
run is immediately followed by a u16 table whose values strictly increase and are
all multiples of 16, starting at `0x20` in every outer tag-`0x16` block
(123/123). Raw bytes, `angryKratosWalk` (`R_HADES.WAD`, outer tag-`0x16` block at
`0x5C60`), from table index 126:

```
[126] 17a0 17d0 0020 0080 00b0 00e0 0140 0170 01a0 01d0 0200 0230   <- 0x17d0 = 0x30*127, then 0x20 ...
```

The table's values reach `0x1800` (= `0x30 * 128`) before a run of constant
`0x1800` fill; on other clips it reaches `0x3C00`. The *length* of the run is
variable and its meaning is [UNKNOWN]; only "increasing, 16-byte aligned, first
value `0x20`" is claimed.

**D. The level-2 tag-`0x16` table is shorter than the outer one.** E-066 measured
128 `0x30 * k` entries on 123/123, but that is the **outer** level. At the nested
level the tag-`0x16` sub-block opens with a `0x30 * k` run of **123** entries on
114 clips and **122** on 8 clips — never 128. Raw bytes, `angryKratosWalk` nested
tag-`0x16` block at `0x6EF0`, from table index 120:

```
[120] 1680 16b0 16e0 0020 0050 0080 00b0 00e0 0140 0170 0200 0230   <- 122 entries, then 0x20 ...
```

**Inference.** The clip data section is a two-level directory tree: the outer
preamble names typed sub-blocks, the tag-`0x10` block nests a second preamble of
the same shape, and the level-2 sub-blocks hold the leaf data. `0x19` is a
level-2-only lead tag, which is consistent with the levels not being identical.
The tag-`0x16` sub-block is a two-table structure (a fixed-stride `0x30 * k`
table plus an increasing 16-byte-aligned table), but no field meaning is proven.

**Unknown.** The meaning of every tag, `arg`, `extra` and sub-block payload; why
`attCestusCrush` has no nested preamble; whether the nested level-2 tag-`0x16`
table length (122/123) is a count; and the leaf keyframe/curve encoding, which is
still the F9 gap. No pointer or type semantics beyond "offset" (E-065), "typed by
tag" (E-066) and "two levels" (this entry) are claimed.

**Consequence.** `tools/gow3/anim.py` gains `parse_data_section()` (the general
form of `parse_clip_sub_blocks()`), `ClipSubBlocks.end` and
`ClipSubBlocks.nested_data_section()`, `clip_data_sections()`, and
`tag16_offset_table()` / `ClipSubBlock.tag16_offset_table`, plus the constants
`CLIP_DATA_NESTED_LEAD_TAG` = 0x19, `CLIP_DATA_NESTED_LEAD_TAGS`,
`CLIP_DATA_NESTED_TAIL_TAGS`, `CLIP_DATA_MAX_DEPTH` and
`CLIP_DATA_SECOND_TABLE_FIRST` = 0x20. 9 new unit tests (`TestClipDataRecursion`)
run on a synthetic two-level clip (no game data committed); the full suite is
**398 tests, all green**. `docs/FORMATS.md` §7.7 and `docs/BACKLOG.md` F9/G9 are
updated.


---

## E-068 — GoW3R clip data section: the u16 offset lists share a 0x30-byte stride (G9/F9, bounded slice)

**Observation.** Followed E-067's open question ("the tag-`0x16` table's
continuation past index 128 ... length/meaning [UNKNOWN]") by measuring the
**arithmetic residue** of every u16 in the data-section sub-blocks, read-only from
`R_HADES.WAD` (77 clips) and `R_HERCULES.WAD` (46 clips) under
`C:\Users\GigelCastel\Desktop\gow3\CUSA01715\EXEC\WAD\PS4_LE\`. A module-level
census over every sub-block at every recursion level of all 123 clips:

**A. Every tag-`0x10` sub-block opens with a u16 `== 0x10 (mod 0x30)`.**

| archive | tag-`0x10` sub-blocks | first word `== 0x10 (mod 0x30)` |
|---|---|---|
| `R_HADES.WAD` | 154 (77 clips × 2 levels) | **154/154** |
| `R_HERCULES.WAD` | 91 (45 clips × 2 levels + 1) | **91/91** |
| total | **245** | **245/245** |

Worked examples (verbatim first u16): `angryKratosWalk` `0x01C0` (448),
`csHadesIntro` `0x01C0`, `csHadesIntroStruggle` `0x0190` (400),
`hitWallStuckWin2` `0x1690` (5776), `hitWallStuckStruggle1` `0x0190`. Every value
satisfies `value % 0x30 == 0x10`, i.e. `0x10 + 0x30 * k` (observed `k` 7..120).
The *whole* leading run is not all residue-`0x10` (it breaks after 1..35 entries),
so only the **first** word is claimed.

**B. The word right after the tag-`0x16` continuation run is always residue
`0x00`, and in fact one of exactly three values.** Starting after the `0x30 * k`
prefix (E-066/E-067), the run of strictly increasing u16 whose value is
`== 0x20 (mod 0x30)` was measured; the next word after it is, on **245/245**
tag-`0x16` sub-blocks, one of:

```
0x1710 = 0x30 * 123      (nested prefix length)
0x1800 = 0x30 * 128      (outer prefix length)
0x3C00 = 0x30 * 320
```

`R_HADES.WAD` boundary counts `{0x1800: 73, 0x1710: 59, 0x3C00: 22}`;
`R_HERCULES.WAD` `{0x1800: 44, 0x1710: 44, 0x3C00: 3}`; no other value and no
truncation. Raw bytes, `angryKratosWalk` outer tag-`0x16` block (`0x5C60`),
from word index 126 (E-067's own example, re-read here):

```
[126] 17a0 17d0 0020 0080 00b0 00e0 0140 0170 01a0 01d0 ...  <- 0x17d0=0x30*127, then 0x20...
```

**C. Not claimed: the continuation is not always one contiguous table.** Counting
*all* residue-`0x20` words in each tag-`0x16` block and comparing to the leading
run: they are equal on 126/154 `R_HADES.WAD` blocks but only 32/91
`R_HERCULES.WAD` blocks — 87/245 blocks carry further residue-`0x20` values later.
So the "second table" of E-067 is the **first** residue-`0x20` run, not the whole
set of such values; the later ones are [UNKNOWN].

**Inference.** The three measured residues — the `0x30 * k` prefix is `0x00`, the
tag-`0x16` continuation is `0x20`, and every tag-`0x10` opening word is `0x10` —
are consistent with a single **0x30-byte (48-byte) record stride** whose fields sit
at `+0x00`, `+0x10` and `+0x20`. **This inference is unproven**; the stride is an
arithmetic regularity in the stored values, not a decoded record layout, and no
field is assigned a meaning.

**Unknown.** What a 0x30-byte record holds; why 87 tag-`0x16` blocks carry a
second residue-`0x20` run and the other 158 do not; the meaning of every tag,
`arg`, `value`, `extra` and of the three terminators; and the leaf keyframe/curve
encoding, which remains the F9 gap.

**Consequence.** `tools/gow3/anim.py` gains `CLIP_DATA_STRIDE` (0x30),
`CLIP_DATA_STRIDE_FIELDS`, `CLIP_DATA_TAG10_RESIDUE` (0x10),
`CLIP_DATA_TAG16_CONTINUATION_RESIDUE` (0x20),
`CLIP_DATA_CONTINUATION_TERMINATORS`, `stride_residue()` and
`stride_offset_run()`, plus `ClipSubBlock.first_word` / `first_word_residue` /
`tag16_continuation` / `tag16_continuation_terminator` / `tag10_residue_ok` /
`tag16_terminator_ok` and `ClipSubBlocks.tag10_residue_ok` /
`tag16_continuation_ok`. 7 new unit tests (`TestStrideResidues`) run on synthetic
fixtures (no game data committed); the full suite is **405 tests, all green**. The
read-only validation reproduced **245/245** tag-`0x10` and **245/245** tag-`0x16`
relations. `docs/FORMATS.md` §7.7 and `docs/BACKLOG.md` F9/G9 are updated.


---

## E-069 — DMC3 HD `dmc3.exe`: a 64-bit PE whose `.text` references a resource-extension table (F1/F4/F5 route, bounded slice)

**Observation.** The DMC3 HD install contains its own executable at
`G:\Games\Devil May Cry HD Collection\dmc3.exe` — **6,356,432 bytes** — read-only,
outside the repo. It is a normal, unpacked x86-64 PE:

```
0x00   "MZ";  e_lfanew (0x3C) = 0x138
0x138  "PE\0\0"; machine 0x8664; 8 sections; PE32+ optional magic 0x20B
       image_base 0x140000000;  AddressOfEntryPoint (RVA) 0x34615C
```

The section table, verbatim (name, RVA, virtual size, raw offset, raw size,
characteristics):

| name | RVA | vsize | raw | rawsz | chars |
|---|---|---|---|---|---|
| `.text` | `0x00001000` | `0x0034DD4E` | `0x00000400` | `0x0034DE00` | `0x60000020` |
| `.rdata` | `0x0034F000` | `0x00203368` | `0x0034E200` | `0x00203400` | `0x40000040` |
| `.data` | `0x00553000` | `0x0081F1B8` | `0x00551600` | `0x00086000` | `0xC0000040` |
| `.pdata` | `0x00D73000` | `0x00023D84` | `0x005D7600` | `0x00023E00` | `0x40000040` |
| `.gfids` | `0x00D97000` | `0x00000050` | `0x005FB400` | `0x00000200` | `0x40000040` |
| `.tls` | `0x00D98000` | `0x00000009` | `0x005FB600` | `0x00000200` | `0xC0000040` |
| `.rsrc` | `0x00D99000` | `0x00000F30` | `0x005FB800` | `0x00001000` | `0x40000040` |
| `.reloc` | `0x00D9A000` | `0x00011DB0` | `0x005FC800` | `0x00011E00` | `0x42000040` |

Only `.text` is executable (`0x60000020` = `CNT_CODE | MEM_EXECUTE`); it holds
`0x34DD4E` bytes of code (15.6% zero bytes, i.e. not packed). File↔RVA mapping is
`rva = section.virtual_address + (offset − section.raw_offset)`.

**A. A resource-extension table is referenced by a tight `.text` cluster.** In
`.rdata` at RVA `0x5071D0` sits a run of NUL-terminated extension strings —
`.mot\0 .MOT\0 .mcv\0 .MCV\0 .cam\0 .CAM\0` — each referenced **once** by a
RIP-relative `lea`:

| string | RVA | referencing instruction RVA |
|---|---|---|
| `.mot` | `0x5071D0` | `0x2E01D2` |
| `.MOT` | `0x5071D8` | `0x2E01EB` |
| `.mcv` | `0x5071E0` | `0x2E0204` |
| `.cam` | `0x5071F0` | `0x2E0236` |

Worked example, `.mot`: instruction `0x2E01D2` is `48 8D 15 F7 6F 22 00` =
`lea rdx, [rip + 0x226FF7]`, whose decoded target is `0x2E01D2 + 7 + 0x226FF7 =
0x5071D0` — the `.mot` string. The instruction is followed by `49 8B C8` (`mov
rcx, r8`) and `FF 15 EE F1 06 00` (`call qword [rip + 0x6F1EE]`), i.e. a call
that receives the extension string.

The scanner finds **19,648** RIP-relative `lea`/`mov` instructions in `.text`
targeting **4,482** distinct RVAs, so the reference route used for GoW3's
`eboot.elf` (E-056) works identically on this image.

**B. Negative result — file-name strings are not referenced this way.** `.pac`
occurs 7,118 times (a packed extension table, none referenced), and
`pl021.pac\0` (2 occurrences), `.tm2\0` (9), `GDataX360.afs` (1) and `endof.afs`
(1) have **zero** RIP-relative references. This mirrors GoW3's `.wad` /
`DEPENDENCY` result (E-063): file names are held as table/registry data, not
loaded with a `lea`.

**Inference (marked).** `dmc3.exe` *is* the engine that consumes the decoded
`MOD `/`MOT `/`SHW ` bytes, so it is the DMC3-side engine ground truth E-050 and
E-051 named as missing. The four-instruction cluster around `0x2E01D2` is
[INFERRED] an extension→handler dispatch; the MOT handler is reachable from it.

**Unknown.** What the code at `0x2E01D2` does beyond the `lea`/`call` (the
limited instruction decoder of `gow3.eboot` has not been mirrored, and no caller/
callee constant has been read); whether the MOT vertex-/keyframe-decoding logic
is reached from this cluster; and every F1/F4 field meaning that only the code can
settle. The install is Crimson-modded, so `dmc3.exe` may be a patched build —
recorded, not a blocker (the section map and code density are that of a normal
PE, and `__new_diff_dmc3.exe.bin` alongside is the patcher's diff).

**Consequence.** New module `tools/dmc3/pe.py`: `PeImage` (PE32+ parsing,
`image_base`/`entry_rva`, section table), `PeSection`, `PeError`, section-based
`file_offset_to_rva`/`rva_to_file_offset`/`read`, `find_all()`,
`rip_relative_references()` and `references_to_string()` — the DMC3 analogue of
`tools/gow3/eboot.py`. 17 unit tests (`tests/test_dmc3_pe.py`) run on a synthetic
PE (no game data committed); the full suite is **422 tests, all green**. The
read-only validation above was produced with this module.


## E-070 — DMC3 `dmc3.exe`: the extension cluster is a file-type registry, not the MOT decoder (F4/F1 route, bounded slice)

**Observation (read-only from `G:\Games\Devil May Cry HD Collection\dmc3.exe`,
6,356,432 B).** E-069 inferred that the `.mot`/`.mcv`/`.cam` extension table at
`.rdata` RVA `0x5071D0` is an "extension→handler dispatch" and that the MOT handler
is reachable from it. Reading the code corrects that.

The string `".mot"` is still at `0x5071D0` and still referenced once, by
`0x2E01D2` (`48 8D 15 F7 6F 22 00` = `lea rdx,[rip+0x226FF7]`). But that
instruction is inside a function beginning at `0x2E01A0`, and the sequence is a
chain of **`strstr` tests**, one per extension. The IAT slot used by the calls
(`0x34F3D0`, via `FF 15 EE F1 06 00` at `0x2E01DC`) holds RVA `0x551CA8`, whose
`IMAGE_IMPORT_BY_NAME` is hint `0x0042` + `"strstr"`. So the code tests the input
string for each extension in turn.

Each test, on a hit, jumps to an insert block that copies two 32-byte names and
stores a numeric type id. The two names come from the callback's arguments
(`rdi ← r8`, `rsi ← rdx`). The blocks and their stores to
`[rbx + rax*4 + 0x18408]`, verbatim:

| extension tested | block entered | type id store |
|---|---|---|
| `.mot` (`0x2E01D2`), `.MOT` (`0x2E01EB`) | `0x2E0598` | `0x2E060B` → **0** |
| `.mcv` (`0x2E0204`), `.MCV` (`0x2E021D`) | `0x2E051B` | `0x2E058B` → **1** |
| `.cam` (`0x2E0236`), `.CAM` (`0x2E024F`) | `0x2E049B` | `0x2E050B` → **2** |
| `.hid` (`0x2E0268`), `.HID` (`0x2E0281`) | `0x2E041B` | `0x2E048B` → **3** |
| `.clt` (`0x2E029A`), `.CLT` (`0x2E02B3`) | `0x2E039A` | `0x2E040B` → **4** |
| `.tsc` (`0x2E02CC`), `.TSC` (`0x2E02E1`) | `0x2E02FA` | `0x2E0377` → **5** |

Because every test is `strstr`, the uppercase variants are matched by the lowercase
test; the `.hid`/`.tsc` strings sit at `0x507200`/`0x507210`, and a companion
family (`.ptx`/`.clt`/`.c1d` at `0x507070`–`0x5070B8`, plus attribute-name strings
and `"%s/%s"`) shows the table is larger than E-069's six strings.

The function caps the table at `0x400` (`cmp dword ptr [rcx], 0x400`), and the
surrounding helpers give the whole registry context its layout — all verified by
reading the code:

```
0x2E0150  reset: for i in 0..0x3FF: nameA[i][0]=0; flags[i]=0; type[i]=0xFFFFFFFF
          (lea r8,[rcx+0x8008], lea rdx,[rcx+0x18408], mov byte [rcx+i+0x18008],0)
0x2E0060  lookup(rcx=ctx, rdx=str1, r8=str2): linear scan i < [ctx]; match when
          strcmp(nameA[i], str2)==0 && strcmp(nameB[i], str1)==0; return i else -1
0x2E0020  wrapper: call lookup; if -1 call 0x2E01A0 (insert)
0x2E0130  nameA_getter(ctx, i) = ctx + 0x8008 + (i << 5); ret
```

So the context block is:

```
+0x0000  u32              entry count        (cap 1024)
+0x8008  char nameA[1024][0x20]   (32-byte NUL-padded name)
+0x10008 char nameB[1024][0x20]
+0x18008 u8   flags[1024]
+0x18408 u32  type[1024]          0..5 per the table above
```

Consumers that call the lookup and then resolve something by index are at `.text`
`0x2D6933`, `0x2D77A2`, `0x2DA173`, `0x2DA263`, `0x2DA336` (each:
`sprintf` a name, `call 0x2E0060`, `test eax,eax; js <skip>`, `call 0x2DB340`,
`call 0x2E0130`, store the result into a struct field). Insert-with-dedup callers
are `0x2D50C4`, `0x2D5414`, `0x2D5854`; the reset is called from `0x23EBB6` and
`0x2D4D9D`; the registry context is `[r14 + 0xB4B0]` / `[rdi + 0xB4B0]`.

**Inference (marked).** `0x2E01A0` is a **file-type classifier/registrar** keyed by
a (nameA, nameB) pair with the six extension type ids above; it is not a byte-level
format decoder. This mirrors GoW3, where the `WAD_` string route reached name
registration rather than the record dispatcher (E-063). E-069's
`[INFERRED]` "extension→handler dispatch … the MOT handler is reachable from it" is
**corrected**: the MOT *decoder* is not reached directly from this cluster.

**Also observed.** Four of the six `.mot`-family instructions reference the
lowercase string only once each; `0x2E01D2`'s decoded context via the mirrored
decoder is exactly one instruction (`PeImage.string_reference_contexts(b".mot\0")`
→ `0x2E01D2 lea operand=0x5071D0`, length 7), because the following `49 8B C8`
(`mov rcx, r8`) is outside the decoder's documented set.

**Unknown.** Where the per-entry type id is consumed to select a decoder; the
real MOT byte-level loader; every F1/F4 field meaning. The named
(language/localisation) table E-057 and the earlier `.pac` negatives (E-069) are
untouched.

**Consequence.** `tools/dmc3/pe.py` gains the limited instruction decoder
`DecodedInstruction` / `_decode_instruction` / `PeImage._code_window` /
`reference_context` / `string_reference_contexts`, mirroring `gow3.eboot` (E-063);
8 new tests in `tests/test_dmc3_pe.py` (synthetic PE, no game data). Full suite
**430 tests, all green**.





---

## E-071 - The engine's own vocabulary in `eboot.bin`: the vertex attributes by name (G9/G10)

**Observation.** `CUSA01715\eboot.bin` (4,581,119 bytes) carries the engine's
class, object-type, script-command and shader-semantic tables as **plain string
runs**, 179,961 of them. The ones that name the pieces of the formats we are
trying to write:

**Vertex attributes** (the mesh-side names, 29 of them after filtering):

```
PS3_Pos   PS3_Normal   PS3_DisplacementNormal   PS3_Tangent   PS3_BiTangent
PS3_Diffuse   PS3_Specular   PS3_F32Diffuse   PS3_F32Specular
PS3_SkinWeights0  PS3_SkinWeights1  PS3_SkinIndices0  PS3_SkinIndices1
PS3_SkinningFlipFactor   PS3_PrevFramePosition   PS3_VertexLightPos
PS3_F32VertexAlpha   PS3_F32VertexAO   PS3_NMblendData
Generic_UV0  Generic_UV1  Generic_UV2  Generic_UV3  Generic_UV4  Generic_UV5
```

Next to them sits the **mesh kind run** `Skinned` and `1UNUSED_MESH_TYPE`, and
the mesh pipeline functions `MeshProc::RenderMeshes`, `FinalizePrims`,
`MeshBounds`, `Cull`. `pDmaData != nullptr` confirms DMA-style vertex buffers.
The full `PS3_*` run is 286 entries and is mostly **shader uniforms** — the 29
above are the ones that describe a *vertex*.

**Script / object commands** — 151 `SCR_*` names, and several are exactly what a
boss needs:

```
SCR_SetPhase        SCR_PlayReplace     SCR_MaterialAnim   SCR_VisJoint
SCR_ShaderSwap      SCR_SwitchNavBanks  SCR_ForceCameraTarget
SCR_MotionBlurMultiplier   SCR_FadeAlpha   SCR_FrozenPose
SCR_IgnoreHitResponse      SCR_AttachToHero   SCR_Spawn  SCR_ActivateSoul
```

`SCR_SetPhase` is a **phase** command (`Hades` is a multi-phase fight), and
`SCR_PlayReplace` is an animation-replacement command.

**Behaviours and the move system.** `hfsmArrowEmitter`, `hfsmBalanceGeom`,
`hfsmBreakable`, `hfsmEnemy1`, `hfsmHeroBreak`, `hfsmIO_Misc`, `hfsmReactive`,
`hfsmSavePoint`; `ms::tMove`, `ms::tSys`, `ms::tCollisionInfo`,
`ms::tSynchPartner`; `fxBoneData`; a small type table `float bool byte color3
color4 matrix44`; and the format string **`ANM_%s`**, which is how the animation
blob in E-058 got the name `ANM_hero_Hades`.

**Inference.** The mesh is a skinned, DMA-fed vertex buffer described by named
attribute streams (`Pos`, `Normal`, `Tangent/BiTangent`, `UV0..UV5`,
`SkinWeights0/1` with matching `SkinIndices0/1`). Those names are the field list a
`MDLX` reader or writer has to satisfy, so this is the cheapest possible ground
truth for the format: the engine names its own pieces. Nothing here is a layout
claim — the names are observed, the binary encoding is still [UNKNOWN].

**Tooling.** `tools/gow3/vocab.py` (`read_strings`, `read_vocabulary`,
`vertex_attributes`, `Vocabulary`, the `VERTEX_SEMANTICS` / `MESH_TYPES`
constants); 12 tests in `tests/test_gow3_vocab.py` over synthetic string blobs.

---

## E-072 - The container is a stream of groups with inline resource data; verified by an exact boundary (G9)

**Observation.** `R_*.WAD` is **not** a header plus a directory plus one bulk
region. From 0x50 it is a stream of 0x40-byte records in which `GroupStart` /
`GroupEnd` bracket groups of resources, and **each resource's data sits inline,
immediately after its descriptor**:

```
0x50  GroupStart
0x90  resource "WAD_R_Hades"    size 24
0xF0  GroupStart
0x130 resource "TXRX_R_Hades"   size 16
0x180 GroupEnd
0x1C0 GroupStart
0x200 resource "WPTX_R_Hades"   size 16
0x250 GroupEnd
```

Record shape, little endian: `u16 id; u16 flags; u32 size; char name[]`, where
id `1` = sized resource, `2`/`3` = GroupStart/GroupEnd, `0x12` = root,
`0x15` = PopHeap, `7` = unsized resource (name at +0x04 instead of +0x08). A
sized resource's data begins 0x40 bytes after the record, **plus another 0x40 when
`flags != 0`**, and is `size` bytes padded up to 0x10.

**Verified by an exact boundary, not by trusting the rule.** In `R_HADES.WAD`:

```
0xDC0  resource "ANM_hero_Hades"  id=1 flags=0x34 size=2,106,384
0xE40  its data begins                (0xDC0 + 0x40 + 0x40)
0x203250  the next record -- and it is exactly "GroupEnd"
```

`0xE40 + 2,106,384 = 0x203250`. The length lands byte-exactly on the next record,
which is what establishes the binding the writer was missing. The same rule then
walks the ANM section onward and lands on valid records every time:

```
0x203250  GroupEnd
0x203290  GroupStart
0x2032D0  resource "ANM_camera_Hades"  flags=0x34 size=127,416  -> data 0x203350
0x222510  GroupEnd
0x222550  resource "SBP_HADES"         flags=0x00 size=3,428,663 -> data 0x222590
0x5676D0  the next resource begins here -- "TX129D488F.28AD5052.dds"
```

**`ANM_camera_Hades`** (127,416 B) is a second animation blob, the cutscene
camera. **`SBP_HADES`** is *not* geometry: its first 0x20000 bytes carry
`SND_HDS_CHAINSNAP`, `SND_HDS_BEAM_LP`, `SND_HDS_BODYSLAM`,
`HADES_WHOOSHLOW_F_A`, `Chd_HAD_GROUND_HIT_SINGLE`, `FOLEY_MOVE_MED`, `Flesh_Rip`
- it is a **sound bank**, 3.4 MB of it. That corrects an earlier assumption that a
large non-texture blob between the animations and the textures would be the mesh.

**Inference.** The container's structural side is now resolvable for sized
resources: name, class, size and byte range are all recoverable, and the ranges
are contiguous and non-overlapping. This removes the "how does the directory bind
to the bulk" blocker for the resources that have a size, and the walk was
verified by a boundary rather than by self-consistency.

**Unknown.** The richer record shapes past the standard 16-group directory: the
walk stops at `0x1ABCDB0` in `R_HADES.WAD` on a `0xFFFF` record after a texture,
at `0x1B70` in `R_SWORD00.WAD` on id `8` (`"ubershader.fx"`, seen with a 0x54 size
and a name at +0x0C), and at `0xD80` in `R_LANG_EN.WAD` on an unnamed unsized
record. So the material/shader objects use at least one more record shape that is
not yet modelled.

**Tooling.** `tools/gow3/groups.py` (`read_record`, `walk`, `inventory`,
`resources`, `Record`, `LayoutError`). The walker is deliberately **partial and
self-reporting**: it stops at the first shape it does not model and says where and
why, instead of resynchronising — which is how `ANM_camera_Hades` and `SBP_HADES`
were found. 17 tests in `tests/test_gow3_groups.py` build synthetic streams and
assert the record shapes, the data offsets, the 0x10 padding, the
flags-add-a-header rule, and the exact-boundary property.

**Suite:** 459 tests, all green.

---

## E-073 - The boss is 19 `MDL_<hash>` mesh definitions, one per body part, on one ubershader (G9/G10)

**Observation.** The front directory's resources are **16-byte stubs** -- handles,
not payloads:

```
0x6B0  MDLX_R_Hades   flags=0x00 size=16   data 0x6F0..0x700
0x780  PRTX_R_Hades   flags=0x00 size=16
0x9F0  COLX_R_Hades   flags=0x00 size=16
```

The payloads live in the body as named records. A mesh is one of them, and it is
followed by its mesh groups:

```
0x48F57D8  resource id=1 flags=0x52 size=128  "MDL_4196b97c"
0x48F58E0  resource                          "MG_4196b97c_0"
0x48F5920  GroupEnd
0x48F5960  GroupStart
0x48F59A0  resource id=1 flags=0x1F size=148  "gochain"
```

`R_HADES.WAD` carries **19 unique `MDL_` definitions**, every one exactly **128
bytes** with **flags `0x52`**, each with one `MG_<hash>_0` group:

```
MDL_4196b97c  @0x48F57E0   MDL_9d29aa5d  @0x4EFEC00   MDL_921b8c0d  @0x50E5DE0
MDL_c13cd430  @0x48F5F80   MDL_1fcb5836  @0x4FEE050   MDL_175ac067  @0x5132980
MDL_3c8ec52   @0x4DA8620   MDL_1a3b8d09  @0x4FFE280   MDL_33c43b9c  @0x5157760
MDL_a865ab18  @0x4DFE970   MDL_8779a9ca  @0x500E530   MDL_c9a3c9b3  @0x517EAA0
MDL_82ce541b  @0x4E45100   MDL_7a54ff    @0x504B940      (19 total)
MDL_db637f4f  @0x4E9F6F0   MDL_18c19a85  @0x5080730
MDL_bc314285  @0x4EB3380   MDL_c21a0097  @0x5091A50
MDL_b2501477  @0x4ECAB80
```

**The materials name the anatomy.** `R_HADES.WAD` holds 119 `MAT_*` names and they
are body parts:

```
MAT_templatens:chest_m_lightingfeatures1     MAT_templatens:helmet_m_lightingfeatures1
MAT_templatens:legs_m_lightingfeatures1      MAT_templatens:skirt_m_lightingfeatures1
MAT_templatens:cloth_m_lightingfeatures1     MAT_templatens:hadesembers
MAT_templatens:hadesash                      MAT_templatens:fire2
MAT_ubershader1
```

So the 19 meshes are the boss's **body parts**, each with an anatomy-named
material. `MAT_ubershader1` is the fallback/umbrella material for the first
definition. `R_HERCULES10.WAD` is the same shape with **1** mesh
(`MDL_de64bce5` @0xE53E60) and 15 materials; `R_SWORD00.WAD` has 1
(`MDL_c916bacd` @0x12730) and 1.

**Inference.** The boss's geometry is addressable: every mesh definition has a
name, an offset, a 128-byte record and a known mesh group, and its material is
identified by an anatomy name. That is the inventory a mesh replacement needs --
*which* meshes exist and *which part* each one is.

**Unknown (the remaining gap for the model).** Where the **vertex and index
buffers** are. A 128-byte definition cannot hold geometry, and the 4-byte hash is
not present as a u32 anywhere in the body (0 hits for each of the first four), so
the definition-to-geometry link is not a simple in-file pointer by that hash. The
buffer must be reached through the mesh group or through the runtime, which is the
next thing to decode. Note this is now a *bounded* question: the mesh side of
GoW3R is an inventory of 19 named definitions, not an unknown blob in an 85 MB
file.

**Also observed in the same region** (not yet decoded, recorded for routing): the
tail contains large families of `tAction*` (2065), `PEM` (1188), `MAT` (1119),
`PDF` (846), `PTS`/`PTC` (796 each), `MOV` (376), `TweenIn`/`TweenOut` (334 each),
`tBranch` (274), `OrbShdr` (270), `groupH` (490), `HdRip` (440), `HR` (531),
`ANM` (404) and `gochain` / `goevtlevelloaded` object records. `MOV` and
`tAction` are where the move set is expected to live.

**Tooling.** `tools/gow3/meshes.py` (`find_mesh_definitions`, `materials`,
`MeshDefinition`, `MESH_FLAGS`, `MESH_DEFINITION_SIZE`). A name only counts when a
valid resource record sits exactly 8 bytes before it, so it enumerates
*definitions* rather than string occurrences. 11 tests in
`tests/test_gow3_meshes.py`. One of them caught a real imprecision before commit:
the mesh-group window initially collected the *next* mesh's groups, so groups are
now filtered by their own hash.

**Suite:** 470 tests, all green.
