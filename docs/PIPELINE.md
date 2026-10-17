# Pipeline: DMC3 → GoW3 Remastered

The full chain, with the tool/file responsible for each hop.

```
┌─ SOURCE ────────────────────────────────────────────────────────────────┐
│ Devil May Cry 3 HD Collection                                           │
│   data/dmc3/GData.afs/               (this install: an unpacked folder) │
│     pl021.pac            4 MOD, 4 SHW, 1 .clt, 9 raw                    │
│     pl021_00_0..9.pac    ~108 MOT animations                            │
│     plwp_vergilsword.pac Yamato (PNST container)                        │
│     i001_90.tm2, id440.pac  textures (TM2 → DDS)                        │
└─────────────────────────────────────────────────────────────────────────┘
                 │  tools/dmc3/pac.py, mot.py, tm2.py
                 ▼
┌─ DERIVED (outside the repo) ────────────────────────────────────────────┐
│  <out>/pl021/*.mod  <out>/pl021/*.shw  <out>/pl021/*.mot               │
│  <out>/textures/*.dds                                                  │
│  manifest.json                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                 │  [Phase 1] tools/export_gltf.py  (to build)
                 ▼
┌─ NEUTRAL INTERCHANGE ───────────────────────────────────────────────────┐
│  vergil.glb    mesh + skin (24 bones) + N animations                   │
│  textures/*.png                                                        │
└─────────────────────────────────────────────────────────────────────────┘
                 │  [Phase 2] tools/import_pac.py  → DMC3 mod (validation)
                 │  [Phase 3] tools/export_gow3.py → GoW3R mod
                 ▼
┌─ TARGET ────────────────────────────────────────────────────────────────┐
│ God of War III Remastered (CUSA01715) via gow3_pc                       │
│   mods/Vergil/dvdroot_ps4/…                                             │
└─────────────────────────────────────────────────────────────────────────┘
```

Reference for the final hop: `FelipePrado0/gow3_pc`, specifically its
`docs/MODS.md`, which defines the mod folder layout
(`mods/<Name>/dvdroot_ps4/...`), the load order, and the fact that mods may carry
game patches but may **not** replace `eboot.bin`, `sce_module` or `sce_sys`.

## Why Phase 2 exists

The GoW3 exporter is a large, unverifiable leap if the DMC3 decompile is wrong
anywhere. Re-importing a `MOD ` and a `MOT ` chunk back into DMC3 exercises the
exact encoders in reverse and gives a binary pass/fail signal. The wild already
does this by dropping `new<Name>_plNNN_00_<slot>.pac` files (E-007), so the
convention is known to work.

## Data-handling rules

* The repository never stores game assets. `extract_assets.py` refuses to write
  inside the repo tree; `.gitignore` also blocks the common extensions.
* Only *metadata* (offsets, tags, spans, header fields, statistics) is committed.
* Any file that a human would call "the model" stays on the operator's disk.
