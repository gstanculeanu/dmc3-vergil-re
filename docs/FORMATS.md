# Format notes

Everything here is derived from artifacts on disk. Every claim carries an
evidence ID linking to `EVIDENCE.md`. Confidence is stated per claim:

- **[VERIFIED]** reproduced on ≥1 shipped file, with the raw bytes recorded.
- **[INFERRED]** a conclusion drawn from verified observations; reasoning given.
- **[UNKNOWN]** explicitly not established.

---

## 1. DMC3 PAC container (`.pac`)

**Status: [VERIFIED]** — evidence E-001, E-002.

All integers little-endian.

```
0x00  char[4]  "PAC\0"
0x04  u32      entry_count
0x08  u32      offset[entry_count]     file-relative; 0 == empty slot
...            zero padding
data  align_up(0x08 + 4 * entry_count, 0x10)
```

* Entries are a fixed-size slot table. A slot is a *logical id*, not an index
  into physical order; empty slots are common (`pl021.pac` has 9 of 27).
* `align_up(0x08 + 4*entry_count, 0x10) == offset[0]` holds for every archive
  checked: `pl000.pac` (0x50), `pl000_00_0.pac` (0x100), `pl021.pac` (0x80),
  `pl021_00_2.pac` (0x20), `pl021_00_6.pac` (0x10), `pl021_00_9.pac` (0x10).
* The container stores **no chunk length**. This project derives a chunk's span
  from the distance to the next occupied slot — an *upper bound*, since a chunk
  may end earlier and leave padding.

### 1.1 Chunk tags and the two framings

**[VERIFIED]** (E-002). A chunk's tag sits either at byte 0 or byte 4:

| Framing | Tag at | Seen in | Example |
|---|---|---|---|
| plain | 0 | `pl021.pac`, `pl000.pac` | `MOD `, `SHW ` |
| size-prefixed | 4 (after a `u32`) | `pl021_00_*.pac` | `MOT\0` |

| Tag | Meaning | Confidence |
|---|---|---|
| `MOD ` | mesh / model data | [VERIFIED] tag, [UNKNOWN] payload |
| `SHW ` | shader / material binding | [VERIFIED] tag, [UNKNOWN] payload |
| `MOT\0` | motion (animation) | [VERIFIED] tag + header, [UNKNOWN] encoding |
| — | `;plNNN_MM.clt` cloth config, plain text | [VERIFIED] |

A tag is only accepted when its first three bytes are ASCII alphanumerics and the
fourth is printable or NUL. This rejects stray numeric fields that would
otherwise look like tags.

`pl021.pac` decomposes as **4 `MOD `, 4 `SHW `, 1 text, 9 untagged** (E-008).

---

## 2. Weapon archives (`.pac` starting with `PNST`) — [UNKNOWN]

**Evidence E-006.** `plwp_vergilsword.pac` begins with the magic `PNST`, not
`PAC\0`:

```
0x00  "PNST"
0x04  u32   9          (entry count?)
0x08  u32   0x30
0x0C  u32   0x9030
...
```

It is **not** the same container as a character `.pac`; the offset table layout
is not yet established. All `plwp_*` weapon archives in the install use it.
Open issue: *"Reverse the PNST weapon container"*.

---

## 3. MOT motion header

**Status: [VERIFIED] fields, [INFERRED] semantics, [UNKNOWN] encoding.**
Evidence E-003 — statistics over **840 MOT chunks in 194 PAC files**.

```
+0x00  u32     header_size           0x50 in 839/840 chunks; one is 0x60
+0x04  char[4] "MOT\0"               840/840
+0x08  u32     observed 0
+0x0C  f32     duration_a             equals +0x14 in 840/840
+0x10  u32     observed 0
+0x14  f32     duration_b
+0x18  u16     flag_a                 0 (550) or 1 (290)
+0x1A  u16     count_a                0 (452), 24 (378), 23 (10)
+0x1C  u16     count_b                24 (821), 23 (18), 31 (1)
+0x1E  u16     unknown_1e             448 (506), 0 (311), 504 (15)
+0x20  u16     unknown_20             448 (732), 0 (71), 504 (31)
+0x22  u16[len] table                len == (header_size - 0x22) / 2
```

Verified invariants:

1. `header_size == 0x22 + 2 * len(table)`.
2. `duration_a == duration_b` in every sample.
3. Values seen in `+0x0C`: 29, 60, 61, 69, 105, 115 … all exactly representable
   as `f32`, which is what an **integer frame count** looks like, not a wall-clock
   duration. **[INFERRED]** `+0x0C` is a frame count. E.g. `pl021_00_2.pac` slot 0
   is `340.0`.

**[INFERRED]** `+0x1C` is the skeleton bone count (24 dominates, matching Vergil's
24-node skeleton). Note the table has 23 entries, i.e. *one fewer* than the bone
count, so the table is **not** a naive per-bone array. **[UNKNOWN]** what the
table indexes.

> Correction history: an earlier revision of this project claimed
> `header_size == 0x20 + 2 * bone_count`. That was **wrong** and was disproven by
> running the parser over the whole install (840 chunks). The code no longer
> asserts it. See `JOURNAL.md`.

### 3.1 MOT payload: the record table

**Status: [VERIFIED]** — evidence E-019. Decoded over **all 840 motion chunks in
the install** (0 failures, 59,269 records, record count reached every time).

```
payload:
  u32  record_count
  record_count x {
      u16 size          total record size in bytes (header included)
      u16 groups
      u16 field_a       observed 3
      u16 field_b       observed 0
      (size - 8) bytes  data
  }
  tail                  0 / 4 / 8 / 12 bytes of zero padding
```

* `size == 8 * (groups + 4)` holds for every record in 796/840 chunks.
* Data is therefore `8 * (groups + 3)` bytes: `groups + 3` eight-byte groups.
* `groups` observed 1…181; most commonly 2 (12,407 of 59,269 records).

**[UNKNOWN]** the encoding of the 8-byte groups. Their `u16` quadruples cluster
near `0x8000`, `0x3FFF` and `0xBFFF` — values near ±1.0 in Q15, which is plausible
for quantised rotation but unproven; high bytes varying by ±3 point at a
bit-packed stream rather than a plain quaternion array.

**[DISPROVEN]** `record_count == 3 × bone_count` (suggested by 69 = 3 × 23 in
`pl021_00_9.pac`). Across the install the ratio is 3.0 in only 193/840 chunks.


---

## 4. TM2 textures (`.tm2`) — HD Collection

**Status: [VERIFIED]** — evidence E-005.

In the HD Collection a `.tm2` is a thin platform header followed by an **ordinary
DDS** blob. Extraction is `data[find(b"DDS "):]`.

`i001_90.tm2`: `DDS ` at offset **0x70**, `dwSize = 124`, flags `0x00081007`,
`256×256`, fourCC `DXT3`.

**[UNKNOWN]** the meaning of the TM2 pre-header fields (only two non-zero `u32`s
observed). **[UNKNOWN]** the PS2/PS3 TIM2 variant — this project targets the HD
Collection build only.

---

## 5. Model / shader payloads — [UNKNOWN]

`MOD ` chunk header (verified bytes, unknown semantics):

```
+0x00  char[4] "MOD "
+0x04  f32     constant 1.0099… (0x3F8147AE) in every observed MOD chunk
+0x08  u32     0
+0x0C  u32     varies   e.g. 0x0003180B, 0x00032702, 0x00010103
+0x10  u32     varies   e.g. 0x000AFE12, 0x000000D9
+0x1C  u32     varies   e.g. 0x00029B30, 0x00005140, 0x00001920
```

`SHW ` chunk header (verified bytes, unknown semantics):

```
+0x00  char[4] "SHW "
+0x04  f32     0.5 (0x3F000000) in every observed SHW chunk
+0x10  u32     varies   e.g. 0x00011811, 0x00002707, 0x00020101
+0x14  u32     varies   e.g. 100, 102, 0x000315D8
+0x20  u16,u16 varies   e.g. (0x0A,0x10), (0x16,0x28), (0x27,0x42)
+0x28  u32     varies   e.g. 0x460, 0x1E0, 0x60
```

Notable: **`pl021.pac` slots 23 and 25 are byte-identical `MOD ` chunks**, as are
slots 24 and 26 (`SHW `) — a duplicated mesh/shader pair. **[INFERRED]** these are
the two Vergil render variants (with/without the Devil Trigger / coat layers).

Open issues: mesh vertex/index layout, material→texture binding, skeleton.
