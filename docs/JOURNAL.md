# Journal

Append-only log of autonomous and human iterations. Newest last.

Format per entry:

```
## YYYY-MM-DD — <short title>
- Did: ...
- Found: ... (evidence IDs)
- Next: ...
```

---

## 2026-10-17 — Phase 0: foundation committed

- Did: stood up the repository. Decoded the DMC3 PAC container and its two chunk
  framings, the MOT motion header, and the HD-Collection TM2→DDS wrapping.
  Implemented `tools/dmc3/{pac,mot,tm2,entities}.py`, the `inventory` and
  `extract_assets` CLIs, and 36 unit tests on synthetic fixtures.
- Found:
  - **E-001** PAC container: `"PAC\0"`, `u32 entry_count`, `u32 offset[]`,
    16-byte aligned data start. Verified on six archives.
  - **E-002** tags `MOD `, `SHW ` (plain) and `MOT\0` (size-prefixed).
  - **E-004** Vergil is `pl021` (cloth config `;pl019_02.clt` inside `pl021.pac`).
  - **E-005** HD `.tm2` wraps a plain DDS blob (`i001_90.tm2` → DDS at 0x70).
  - **E-003** MOT header statistics over 840 chunks / 194 files; `header_size` is
    a constant `0x50`, `+0x0C`/`+0x14` are a duplicated integer duration,
    `+0x1C` is very likely the 24-bone count.
  - **E-007** the install is Crimson-modded and mods overlay Vergil's motions via
    `new<Name>_pl021_00_<slot>.pac` — a working template for Phase 2.
  - **E-006** weapon archives use a different `PNST` container.
- **Self-correction:** the first MOT spec asserted
  `header_size == 0x20 + 2 * bone_count`. Running it over the whole install
  disproved it (header is constant 0x50) and the code and docs were corrected.
  Recorded because it is the exact failure mode the evidence discipline exists for.
- Next: **F1** — decode the `MOD ` mesh payload (critical path). Start with the
  header fields at `+0x0C`, `+0x10` and `+0x1C` across the four `MOD ` chunks in
  `pl021.pac`, then look for the vertex stride.

---

## 2026-10-17 — Scope clarified: Vergil is an **enemy**, not just a model

The owner clarified the destination: Vergil must appear in God of War III
Remastered **as an enemy**, so his **move set, weapon, sounds and effects** are
part of the deliverable, not optional extras.

- Did: expanded the roadmap (Phase 1 milestones 1.8–1.10 for moves/audio/VFX;
  Phase 3 reframed as an enemy port), added `docs/ANIMATIONS.md`, filed issues
  **F9** (move set), **F10** (audio), **F11** (VFX), **F12** (enemy AI) and
  **G6** (choose the enemy Vergil replaces), and recorded the mod-system
  constraint that shapes all of Phase 3.
- Found:
  - **E-010** Vergil's audio is present as `Versil_01..03.ogg` in
    `data/dmc3/afs/sound/`; ownership of the `snd_*.pac` banks is still unknown.
  - **E-011** the loose `GData.afs` **folder** is created by the mod loader
    (DDMK/Crimson), not by the retail game. Our tooling reads a loader-generated
    tree; H3 tracks the retail packed `.afs`.
  - **E-012** prior art: Vergil has already been decompiled and ported into
    **Bloodborne**, another PS4 game, via the same `dvdroot` replacement
    convention GoW3R uses. Per the owner, the model is done there and "the moves
    and things are left" — which matches our F9/F10/F11 backlog.
  - **E-013** the community has already named most of Vergil's motion slots
    (Infernal Works motion-ID thread). Transcribed into `docs/ANIMATIONS.md`;
    needs local verification (F7).
  - The DMC3 HD model-port community warns that too many / too high-vertex model
    swaps destabilise the game — relevant to Phase 2's import budget.
- **Key constraint recorded:** `gow3_pc` mods may replace data files under
  `dvdroot_ps4/` but may not replace `eboot.bin`, nor use DLL injectors or script
  plugins. A mod therefore **cannot author new AI**: Vergil must replace an
  existing sword-wielding GoW3R enemy and inherit its behaviour (G6). This is on
  the critical path because it decides what "Vergil as an enemy" can mean.
- Next: **F1** (mesh) and **F4** (MOT keyframes) remain the technical critical
  path. In parallel, **H4** (assess the Bloodborne mod) and **G6** (pick the
  replaced enemy) are cheap and de-risk the plan.

---

## 2026-10-17 — Prior art located on disk: Vergil's mesh is already decompiled

The owner pointed at `C:\Users\GigelCastel\Desktop\vergil`, the downloaded Nexus
(Bloodborne) Vergil mod, and asked for it to be taken into account.

- Did: inspected the package directly and wrote `docs/PRIOR-ART.md`. Recorded
  evidence **E-014**. Updated the README (mesh status + prior-art callout),
  the roadmap (new milestone 1.0; 1.1/1.7/1.3 demoted to cross-checks) and the
  backlog (F1/F6 restated).
- Found (E-014):
  - It is a **FromSoftware PS4** mod package. Magics observed: `FLVER`, `TPF\0`
    (platform header `PS4`), `BND4`, `DCX\0`, HKX `57 E0 E0 57`, `CLM2`, `DDS `,
    and Source **`version 1` SMD**.
  - **Vergil's mesh exists in interchange format.** `WP_A_10100.smd` (628 KB) and
    `WP_A_10100.ascii` (181 KB), plus `_1`/`_2` variants — Blender-readable.
  - Weapon identity is **Yamato**: `WP_A_1063`, 8 nodes with `B_Root` →
    `B_Blade_00/01/02`, 1852 verts, material `m0_WP_A_1063`, textures
    `WP_A_1063_a/_r/_s/_n`.
  - Body is a Bloodborne **FullBody** part `BD_M_10100`, whose TPF shrank
    19,929,900 → 2,190,896 vs its `.bak` — Vergil's textures replaced the original.
  - Manifests (Witchy) expose the original PS4 build tree:
    `N:\SPRJ\data\INTERROOT_ps4\parts\FullBody\BD_M_10100`.
  - Nothing in the text files says "Vergil"/"Yamato" — the armour-name FMG just
    sets entries to `NOT NEEDED`.
- **Strategic consequence:** decoding the DMC3 `MOD ` mesh (F1) and `PNST`
  weapon container (F6) is no longer on the critical path; they become
  cross-checks. The critical path is **animations and moves** (F4, F9) — the
  package's `.anibnd`/`.hkx` are Bloodborne's, not Vergil's. This matches the
  owner's "the moves and things are left".
- **Licensing:** third-party assets, kept outside the repo, never committed.
  Reuse is gated on the mod page's permissions (H4).
- Next: **T7** — convert the prior-art mesh to glTF/OBJ and verify it renders.
  Then **F4** — MOT keyframes, now the top technical risk.

---

## 2026-10-17 — Boss requirement, and the Yamato is exported and verified

Owner: *"continue until done. vergil should be a boss and have a health bar in
gow3."*

- Did: reframed Phases 1 and 3 around **Vergil as a boss with a health bar**;
  implemented `tools/priorart/` (Source `.ascii` + `.smd` parsers, OBJ writer,
  converter CLI) and ran it against the real prior-art package. 52 tests green.
- Found:
  - **E-015** — both interchange formats are fully decoded. ASCII:
    8 bones / 1 mesh / **1176 verts** / **1852 faces**; the line budget
    (`1 + 24 + 6 + 14 + 1 + 1176*7 + 1 + 1852`) matches the file exactly.
    SMD: 8 nodes / 8 bones / 1 material / **5556 verts** / **1852 tris**.
  - Both OBJ exports give an **identical bounding box**:
    `extent (x,y,z) = 0.163 × 1.260 × 0.053 m`, longest axis 1.260 — a thin,
    1.26 m blade. **Vergil's Yamato is exported and verified.**
  - Two independent formats agreeing on triangle count *and* bounding box is
    mutual verification of both parsers; this also independently confirms
    `WP_A_1063` = Yamato.
- **Design decision recorded:** a `gow3_pc` mod cannot add UI, so a boss health
  bar cannot be created — it must be **inherited by replacing an existing boss**.
  This turns the mod constraint into the mechanism that satisfies the
  requirement. Phases 1/3, `README`, `ROADMAP`, `GOW3.md` and the backlog were
  all updated; new issue **G7** filed.
- Still open: the **body** (`BD_M_10100`) is FLVER-only, so it needs a FLVER
  parser or an external tool; and **F4** (MOT keyframes) remains the top
  technical risk.
- Next: **T7b** — parse FLVER (or drive an external tool) for Vergil's body, and
  **F4** — MOT keyframes.



