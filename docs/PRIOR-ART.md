# Prior art: Vergil already decompiled into a PS4 game

This document records an existing, third-party **Bloodborne** mod that puts Vergil
in another PS4 title, and what it changes about this project's plan.

> **Never commit these files.** They are third-party game assets living in
> `C:\Users\GigelCastel\Desktop\vergil`, *outside* the repository. This document
> contains only observations about formats and structure.

## What the package is

A FromSoftware PS4 (Bloodborne) mod package. Source: Nexus mod 229
(<https://www.nexusmods.com/bloodborne/mods/229>), downloaded by the project owner
to `C:\Users\GigelCastel\Desktop\vergil`. Evidence: **E-014**.

## Inventory (observed)

| File(s) | Size | Format |
|---|---|---|
| `parts/bd_m_10100-partsbnd-dcx/BD_M_10100.flver` | 467,008 | **FLVER** model (magic `FLVER`) |
| `parts/bd_m_10100-partsbnd-dcx/BD_M_10100.tpf` | 2,190,896 | **TPF** texture package (`TPF\0`), platform `PS4` |
| `parts/bd_m_10100-partsbnd-dcx/BD_M_10100_c.hkx` | 246,832 | **HKX** Havok binary (magic `57 E0 E0 57`) |
| `parts/bd_m_10100-partsbnd-dcx/BD_M_8000_c.clm2` | 176 | **CLM2** cloth |
| `parts/wp_a_1063-partsbnd-dcx/WP_A_10100.flver` | 18,976 | FLVER — weapon |
| `parts/wp_a_1063-partsbnd-dcx/WP_A_10100_1.flver` | 66,832 | FLVER — weapon variant |
| `parts/wp_a_1063-partsbnd-dcx/WP_A_10100_2.flver` | 19,344 | FLVER — weapon variant |
| `parts/wp_a_1063-partsbnd-dcx/WP_A_10100.anibnd` | 10,800 | **BND4** animation binder |
| `parts/wp_a_1063-partsbnd-dcx/WP_A_10100_2.anibnd` | 31,792 | BND4 animation binder |
| `parts/wp_a_1063-partsbnd-dcx/WP_A_10100_1_c.hkx` | 149,840 | HKX |
| **`parts/wp_a_1063-partsbnd-dcx/WP_A_10100.smd`** | **628,257** | **Source SMD** (`version 1`) |
| **`parts/wp_a_1063-partsbnd-dcx/WP_A_10100.ascii`** | **181,648** | **Source ASCII** reference mesh |
| `WP_A_10100_1.smd` / `_1.ascii` / `_2.smd` / `_2.ascii` | — | further Source interchange meshes |
| `parts/wp_a_1063-partsbnd-dcx/WP_A_10100-tpf/*.dds` | — | `WP_A_1063_a/_n/_r/_s.dds` (albedo, normal, roughness, specular) |
| `parts/bd_m_10100-partsbnd-dcx/BD_M_10100-tpf/*.dds` | — | `tex_*_0.dds`, `N.dds`, `M.dds` |
| `menu/common.tpf.dcx` | 10,398,312 | DCX-compressed TPF (UI) |
| `msg/enggb/item.msgbnd.dcx` + `item-msgbnd-dcx/*.fmg` | — | **FMG** text (Japanese names: `防具名` armour, `武器名` weapon, …) |
| `param/gameparam/gameparam.parambnd.dcx` | 1,496,315 | PARAMBND game parameters |
| `_witchy-bnd4.xml`, `_witchy-tpf.xml` | — | **Witchy** (Blender add-on) manifests |

Extension census: 21 `.dds`, 17 `.fmg`, 14 `.dcx`, 11 `.bak`, 6 `.xml`, 4 `.flver`,
3 `.smd`, 3 `.ascii`, 2 `.tpf`, 2 `.hkx`, 2 `.clm2`, 2 `.anibnd`, 3 `.prev`.

## Confirmed identities

* **Weapon = Yamato.** `WP_A_1063` is a katana: 8 nodes
  (`WP_A_1063_Grip`, `Model_Dummy`, `SFX_Dummy`, `WP_A_1063_0`, `B_Root`,
  `B_Blade_00` → `B_Blade_01` → `B_Blade_02`, parent chain 4→5→6→7), 1852
  vertices, material `m0_WP_A_1063`, textures `WP_A_1063_a/_r/_s/_n`.
* **Body = a FullBody part.** `BD_M_10100` is a Bloodborne *FullBody* armour part
  (`parts/FullBody/`) replaced by Vergil's body. Its TPF shrank from 19,929,900
  (`.bak`, original) to 2,190,896 — the mod swaps in Vergil's textures.
* **Items were hidden**, not renamed: `防具名.fmg` (armour names) has every entry
  set to `NOT NEEDED` except Bloodborne's own (`Grey Wolf Cap`, …).
* **Original build paths**, from the Witchy manifests:
  `N:\SPRJ\data\INTERROOT_ps4\parts\FullBody\BD_M_10100`,
  `N:\SPRJ\data\Model\parts\Weapon\WP_A_1063\tex\…` — confirming a PS4 build tree.

## What this means for our plan

### Solved elsewhere (verify, do not redo)

| Our item | Status given this package |
|---|---|
| **F1** `MOD ` mesh payload | **No longer blocking.** Vergil's mesh already exists as FLVER + **Source SMD + ASCII**, plus DDS albedo/normal/roughness/specular. Convert, don't decode. |
| **F6** `PNST` weapon container | **Deprioritised.** Yamato is already available as FLVER/SMD/ASCII. |
| **T2** textures | Easier: DDS albedo/normal/roughness/specular already exported and named. |

The SMD/ASCII files are the decisive find: they are plain-text interchange formats
directly readable by Blender (Source Tools) and trivially convertible to OBJ/glTF.
**Decoding the DMC3 `MOD ` payload is now a cross-check, not a prerequisite.**

### Still ours

| Our item | Why it is still open |
|---|---|
| **F4/F9** animations, **moves** | The `.anibnd`/`.hkx` here are **Bloodborne's** katana animations, not Vergil's DMC3 moves. The owner's summary — *"the moves and things are left"* — matches exactly. |
| **F10** audio | Nothing audio in this package. Vergil's voice is still `Versil_*.ogg` in DMC3 (E-010). |
| **F11** VFX | Nothing here. Still Effekseer in the Crimson tree. |
| **F7** move naming | Still needs the local motion map (E-013). |
| **G1–G5** GoW3R | Untouched: GoW3R is a different engine with its own formats. |

### Strategic consequences

1. **Phase 1 shrinks.** Fetch the mesh and textures from this prior art, keep the
   DMC3 `MOD ` decoder only as a verification path.
2. **The critical path moves to animations** (F4, F9) — which is also what an
   enemy needs most.
3. **Toolchain to learn from:** Witchy (Blender add-on) for FLVER/TPF/DCX/BND4,
   and the SoulsFormats family. Not directly reusable for GoW3R, but it is a
   working template for "PS4 game asset round-trip via Blender".
4. **Precedent for G6.** This mod replaces an existing Bloodborne armour part and
   inherits that game's behaviour rather than authoring new AI — the same
   strategy `docs/GOW3.md` predicts for GoW3R.
5. **Licensing.** Downloaded by the owner from Nexus; permissions live on the mod
   page. Treat as *reference*; never commit. Confirm permissions before reusing
   any file. Tracked by issue #31 (H4).
