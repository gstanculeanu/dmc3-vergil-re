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

## Phase 1 — Decompile Vergil (mesh + rig + moves + weapon + audio + VFX)

Deliverable: everything that makes Vergil a character, in neutral interchange
formats, plus a written spec of each DMC3 structure. Because the goal is an
**enemy**, the move set is a first-class deliverable, not a nice-to-have.

| Milestone | Depends on | Gate |
|---|---|---|
| 1.1 `MOD ` mesh payload → vertices/indices/normals/UVs | E-008 work | a mesh loads in Blender and looks like Vergil |
| 1.2 Skeleton + bind pose | 1.1 | 24 bones recovered, hierarchy matches the MOT bone count |
| 1.3 `SHW ` material/shader → texture binding | 1.1 | every submesh maps to a named `.tm2` texture |
| 1.4 Texture export `.tm2` → `.dds` → `.png` | E-005 ✅ | correct colour/alpha when decoded |
| 1.5 MOT keyframes → per-bone TRS tracks | E-003 work | an animation replays on the skeleton without drift |
| 1.6 glTF 2.0 exporter | 1.1–1.5 | one `.glb` with mesh + skin + all animations |
| 1.7 `plwp_vergilsword` (Yamato) | E-006 work | weapon mesh exported too |
| 1.8 **Move set** — clip + timing + hit windows + state transitions | 1.5 | every named move (Judgement Cut, High Time, …) is described |
| 1.9 **Audio** — Vergil's voice/SFX extracted and labelled | — | `docs/AUDIO.md` map, assets on disk |
| 1.10 **VFX** — effects inventoried and format-identified | — | `docs/VFX.md`, conversion path stated |

**Gate:** exported `.glb` opens in Blender with mesh, rig and animations, and the
move list in `docs/MOVES.md` covers a usable enemy move set.

---

## Phase 2 — Round-trip back into DMC3 *(validation)*

Deliverable: an importer that writes `.pac` files the engine accepts, plus a mod
that swaps a model and a motion. This is the cheapest proof the decompile is
faithful.

* Reuse the naming/layout convention already used in the wild (E-007):
  `new<Name>_plNNN_00_<slot>.pac`.
* Re-encode one `MOD ` chunk and one `MOT ` chunk and confirm the game loads them.

**Gate:** the game starts and renders the re-imported asset. If this fails, the
Phase 1 specs are wrong and Phase 3 must not begin.

---

## Phase 3 — Vergil as an enemy in God of War III Remastered

Deliverable: Vergil, with his moves, weapon, voice and effects, acting as an enemy
inside GoW3R on PC through the `FelipePrado0/gow3_pc` mod system.

**Constraint (see `GOW3.md`):** a mod may replace data files under `dvdroot_ps4/`
but may not replace `eboot.bin`, nor use DLL injectors or script plugins. New AI
cannot be authored by a mod.

| Milestone | Notes |
|---|---|
| 3.1 Locate GoW3R character assets inside `CUSA01715` | issue G1 |
| 3.2 Reverse GoW3R's model/material container | issue G2 |
| 3.3 **Choose the sword-wielding enemy Vergil replaces** | issue G6 — decides what AI Vergil inherits |
| 3.4 Map Vergil's rig/moves onto that enemy's slots | issue G3 |
| 3.5 Build the exporter to GoW3R's format | issue G4 |
| 3.6 Port audio and VFX (Effekseer → GoW3R effects) | issues F10, F11 |
| 3.7 Package as a `gow3_pc` mod | issue G5 |
| 3.8 Verify in game: encounter Vergil, fight him | issue G5 |

**Gate:** an encounter in GoW3R where Vergil looks, sounds and fights like Vergil.

---

## Non-goals

* Distributing any Capcom or Sony asset. The repo holds tooling and notes only.
* Supporting the PS2/PS3 TIM2 variant or the non-HD DMC3 release.
* Emulation or PS4 firmware work — that is `gow3_pc` / shadPS4 territory.
* Writing new AI inside the GoW3R executable (impossible via mods — see G6).
