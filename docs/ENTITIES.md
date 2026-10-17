# Entity map

DMC3 (and the HD Collection) names player resources `pl<NNN>` and weapon resources
`plwp_<name>`. This table records what is **verified** from the artifacts versus
what is **inferred** from convention.

## Primary target

**`pl021` — Vergil** — `[VERIFIED]` (E-004).

* `pl021.pac` — model package: 4 `MOD `, 4 `SHW `, 1 `.clt` cloth config, 9 raw.
* `pl021_00_0.pac` … `pl021_00_9.pac` — motion packages, ~108 animations (E-009).
* Cloth config inside `pl021.pac` is `;pl019_02.clt` (inherits `pl019`'s cloth).

## Players

| Id | Label | Confidence | Basis |
|---|---|---|---|
| `pl000` | Dante | [VERIFIED] | `;pl000_02.clt` in `pl000.pac` |
| `pl001` | ? | [UNKNOWN] | present, similar layout to `pl000` |
| `pl002` | ? (Lady?) | [INFERRED] | notable size, no evidence yet |
| `pl019` | Vergil (boss / Nelo Angelo) | [INFERRED] | referenced by `pl021.pac`'s cloth config |
| `pl021` | Vergil (playable) | [VERIFIED] | E-004 |

Also present on disk: `pl005`–`pl018`, `pl023`, `pl025`, `pl026`. All unlabelled.

## Weapons (`plwp_*`) — all use the `PNST` container (E-006)

| Archive | Label | Confidence |
|---|---|---|
| `plwp_vergilsword` | Yamato | [VERIFIED] name |
| `plwp_newvergilsword` | Yamato (SE/HD variant) | [INFERRED] |
| `plwp_newvergilfight` | Beowulf (Vergil) | [INFERRED] |
| `plwp_forceedge` | Force Edge | [INFERRED] |
| `plwp_sword`, `plwp_sword2`, `plwp_sword3` | Rebellion / Sparda / … | [UNKNOWN] |
| `plwp_gun`, `plwp_shotgun`, `plwp_rifle`, `plwp_laser` | Ebony&Ivory / Shotgun / Spiral / Artemis | [INFERRED] |
| `plwp_nunchaku`, `plwp_2sword`, `plwp_guitar` | Cerberus / Agni&Rudra / Nevan | [INFERRED] |
| `plwp_ladygun` | Kalina Ann | [INFERRED] |
| `plwp_nerosword` | (DMC4 leftover?) | [UNKNOWN] |

## Mods present in this install

`[VERIFIED]` (E-007). Third-party **Crimson** content overlays Vergil's data:

```
newTauntVergilAnims1_pl021_00_2.pac
newTauntVergilAnims2_pl021_00_2.pac
newJudgementCut_pl021_00_3.pac
newJudgementCutAir_pl021_00_3.pac
newJudgementCutAirJF_pl021_00_3.pac
newRisingStar_pl021_00_4.pac
newYamatoHighTime_pl021_00_5.pac
newBaseDanteAnims_pl000_00_0.pac
...
plwp_newvergilfight.pac, plwp_newvergilsword.pac
```

**This is the single most useful artefact for Phase 2**: it demonstrates the
overlay naming convention and that the engine accepts a replaced `.pac` at a
given slot index.

## Naming convention

```
pl<NNN>.pac              model package for player NNN
pl<NNN>_00_<G>.pac       motion group G for player NNN
plwp_<name>.pac          weapon <name> (PNST container)
id<NNN>.pac              UI / HUD resources
em<NNN>.pac              enemy models
st<NNN>.pac              stage / scene data
i<NNN>_<MM>.tm2          UI texture (TM2 → DDS)
<name>_msg_eng.txt       localisation
```
