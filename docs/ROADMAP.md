# Roadmap

Four phases. Each has a **gate**: a check that must pass before the next phase is
worth starting. Gates exist so the project cannot build a GoW3 exporter on an
unverified decompile.

---

## Phase 0 — Foundation ✅ (this commit)

* PAC container decoded (E-001) and implemented (`tools/dmc3/pac.py`).
* Chunk tagging + two framings (E-002).
* MOT header decoded with statistics over 840 chunks (E-003).
* TM2→DDS extraction (E-005).
* Vergil identified as `pl021` (E-004).
* Inventory + extraction CLIs, 36 unit tests, no game files in the repo.

**Gate:** `python -m unittest discover -s tests` passes and
`tools/inventory.py` runs against a real install without errors. ✅

---

## Phase 1 — Decompile Vergil (mesh + skeleton + materials + animations)

Deliverable: Vergil's mesh, skeleton, materials and every animation, in neutral
interchange formats, plus a written spec of each DMC3 structure.

| Milestone | Depends on | Gate |
|---|---|---|
| 1.1 `MOD ` mesh payload → vertices/indices/normals/UVs | E-008 work | a mesh loads in Blender and looks like Vergil |
| 1.2 Skeleton + bind pose | 1.1 | 24 bones recovered, hierarchy matches the MOT bone count |
| 1.3 `SHW ` material/shader → texture binding | 1.1 | every submesh maps to a named `.tm2` texture |
| 1.4 Texture export `.tm2` → `.dds` → `.png` | E-005 ✅ | correct colour/alpha when decoded |
| 1.5 MOT keyframes → per-bone TRS tracks | E-003 work | an animation replays on the skeleton without drift |
| 1.6 glTF 2.0 exporter | 1.1–1.5 | one `.glb` with mesh + skin + all animations |
| 1.7 `plwp_vergilsword` (Yamato) | E-006 work | weapon mesh exported too |

**Gate:** exported `.glb` opens in Blender and a third party can recognise Vergil,
with animations that loop cleanly.

---

## Phase 2 — Round-trip back into DMC3 *(validation)*

Deliverable: an importer that writes `.pac` files the engine accepts, plus a mod
that swaps a model. This is the cheapest proof the decompile is faithful.

* Reuse the naming/layout convention already used in the wild (E-007):
  `new<Name>_plNNN_00_<slot>.pac`.
* Re-encode one `MOD ` chunk and one `MOT ` chunk and confirm the game loads them.

**Gate:** the game starts and renders the re-imported asset. If this fails, the
Phase 1 specs are wrong and Phase 3 must not begin.

---

## Phase 3 — Close the gap to God of War III Remastered

Deliverable: Vergil's model running inside GoW3 Remastered through the
`FelipePrado0/gow3_pc` mod system.

| Milestone | Notes |
|---|---|
| 3.1 Locate GoW3's character assets inside `CUSA01715` | see `GOW3.md` |
| 3.2 Reverse GoW3's model/material container | geometry + skin + texture formats |
| 3.3 Map DMC3 skeleton → GoW3 skeleton | Kratos's rig differs; decide between retargeting and a standalone skinned mesh |
| 3.4 Build the exporter to GoW3's format | |
| 3.5 Package as a `gow3_pc` mod | `mods/<name>/dvdroot_ps4/…`, per `gow3_pc` `docs/MODS.md` |
| 3.6 Verify in the port | load the mod, see Vergil, no crash |

**Gate:** Vergil appears in GoW3R on PC via the mod folder.

---

## Non-goals

* Distributing any Capcom or Sony asset. The repo holds tooling and notes only.
* Supporting the PS2/PS3 TIM2 variant or the non-HD DMC3 release.
* Emulation or PS4 firmware work — that is `gow3_pc` / shadPS4 territory.
