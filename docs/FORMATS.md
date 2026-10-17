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

### 1.3 Raw (untagged) chunks — [UNKNOWN]

**Evidence E-033.** `pl021.pac` slot 0 sits at file offset 0x80 (span up to slot
1 at 0x39880, a 0x39800-byte upper bound) and begins with six little-endian
u32s:

```
+0x00 u32  5   [UNKNOWN]
+0x04 u32  43  [UNKNOWN]
+0x08 u32  22  [UNKNOWN]
+0x0C u32  43  [UNKNOWN]
+0x10 u32  5   [UNKNOWN]
+0x14 u32  1   [UNKNOWN]
```

followed by zero bytes until body+0x0800, where small sub-fields appear. At
body+0x0870 (file offset 0x8F0) the bytes contain a `DDS ` magic
(`dwSize = 124`, `dwFlags = 0x000A1007`, 256×64) — an embedded DDS-like blob
whose presence inside the raw slot is unexplained. The remaining ~235 KB of
the slot's span is non-zero and structured; its layout is undecoded.

The other eight untagged slots (5, 6, 7, 9, 10, 11, 21, 22) have different
leading bytes — slot 10 is a table of u16 pairs `(0x5C, x)` with `x`
increasing by 20, slot 21 is a u16 table with `0xFFFF` separators, slots 9/11
are f32 arrays (E-008) — so no single header shape is shared across the
untagged slots. Every field in this section is [UNKNOWN].

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

**[INFERRED]** each 8-byte keyframe group's first u16 is an offset-binary frame
count: ``frame = u16[0] - 0x8000`` (evidence E-026).  Times are monotonic within a
record and bounded by the header duration; the unit is animation frames, matching
the `+0x0C`/`+0x14` duration.  Verified on every Vergil `pl021_*.pac` chunk
(thousands of keyframes, 0 violations) and present in all 840 install chunks.
`0x8000` is the encoding's zero point.

**[UNKNOWN]** the group's remaining three u16s (u16[1..3]), the per-record
preamble groups at positions 0..field_a-1, the value scale and zero point, and
whether `0x8000` is a base offset or a flag bit.  (Semantics per E-029.)

The preamble groups were bounded further (evidence E-029): each of the 22,974
preamble groups across the ten `pl021_*.pac` files reads as a pair of finite
little-endian f32s with |v| ≤ 1e6; 97.4% have both |v| ≤ 10 and 99.6% both
|v| ≤ 100 (max |v| ≈ 999.6).  Small magnitude values consistent with
translation/scale/rotation-like per-record parameters; *which* parameters is
unknown.  The preamble is **not** a stored base pose: preamble == first keyframe
groups in 0/7,659 records.

Observations on u16[1..3] across every `pl021_*.pac` MOT chunk (evidence
E-028/E-029): read as signed 16-bit they span the full `[-32768, 32767]` range
(max abs 32768) and differ from keyframe to keyframe within a record — they are
**not constant per record** (only 458/269/258 records have u16[1]/u16[2]/u16[3]
constant across keyframes, dominated by trivial single-keyframe records).
Frequency of the most common values, out of 87,662 values per channel: `0x3FFF`
(+16,383 ≈ +0.5 in Q15) and `0xBFFF` (−16,383 ≈ −0.5 in Q15) about 5,500 hits
each; `0x0000` about 2,400–2,800 hits; `0xFFFF` (−1) about 950–1,100 hits.
Only ~5% of values are near zero (|v| < 256).  This is consistent with three
quantized float channels per keyframe (position or rotation components in Q15
fixed point), but channel assignment, scale and zero point are not established
from bytes alone.  A bit-packed stream rather than plain channels remains
possible.

**[DISPROVEN]** `record_count == 3 × bone_count` (suggested by 69 = 3 × 23 in
`pl021_00_9.pac`). Across the install the ratio is 3.0 in only 193/840 chunks.

**[DISPROVEN]** "u16[1..3] is constant per record" — the channels vary per
keyframe (E-029).

**[DISPROVEN]** "the preamble encodes the first keyframe / base pose" —
preamble == first keyframe groups in 0/7,659 records (E-029).

**[DISPROVEN]** `record_count == 3 × bone_count` (suggested by 69 = 3 × 23 in
`pl021_00_9.pac`). Across the install the ratio is 3.0 in only 193/840 chunks.


### 3.2 MOT header: the `+0x22` table

**Status: [PARTIAL] structure, [UNKNOWN] semantics.** Evidence E-032 — a census
of the table over all 840 MOT chunks in the install.

```
+0x22  u16[len] table        len == (header_size - 0x22) / 2; 23 entries for the
                              common 0x50 header, 31 for the single 0x60 header
```

* `len(table)` is exactly `(header_size - 0x22) / 2` in all 840 chunks
  (E-003, E-032).
* Table entries are constant within a chunk. The dominant shape — 703/840
  chunks, including every `pl021_*.pac` (Vergil) chunk — is twenty-two `u16`
  values of `56` (`0x38`) followed by a single `0`. Other shapes: `504`-based
  (`504 × 22 + 0`, or `504 × 21 + 0 + 0`, one `480` variant; 28 chunks, the
  Crimson overlay mods), `58 × 22 + 0` (2 chunks), `56 × 12 + 0 × 10 + 56 + 0`
  (71 chunks), `56 × 21 + 0 + 0` (18 chunks; these have `+0x1C == 23`), and a
  `demo_pl000_00_3.pac` family whose final entry varies (29 … 26755; 17
  chunks). The single `0x60`-header chunk has 31 × 56.
* `504 == 56 * 9`; where non-zero, `unknown_1e`/`unknown_20` are multiples of
  56 (0, 448 = 56 × 8, 504 = 56 × 9). For 751/840 chunks the non-zero entry
  count equals `+0x1C - 2`; the remaining 89 chunks break that relation.

**[UNKNOWN]** what the table denotes. It is **not** per-bone data: the inferred
bone count `+0x1C` (24 in 821/840 chunks) does not match 23 entries, and no
entry varies per index, so the entries cannot be per-bone indices, flags, or
offsets. Whether `56` is a stride, a default record size, or reserved padding,
and what the final entry (usually `0`) marks, is not established from bytes
alone.

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

## 5. Model / shader payloads — header [VERIFIED], payload [UNKNOWN]

`MOD ` chunk header (verified bytes across **286 `MOD ` chunks in 194 PAC
files**; evidence E-030), all little-endian:

```
+0x00  char[4] "MOD "
+0x04  f32     scale-like constant: 1.0099… (0x3F8147AE) x285, 1.0 x1
+0x08  u32     0 where observed (pl021.pac)
+0x0C  u32     0 x286           [purpose UNKNOWN]
+0x10  u32     varies per mesh  e.g. 0x10101 x59, 0x103180B x2, 0x30101 x5  [meaning UNKNOWN]
+0x14  u32     varies per mesh  e.g. 0xF4240 (1,000,000) x187, 0xAF258 x7   [meaning UNKNOWN]
+0x18  u32     0 where observed (pl021.pac)
+0x1C  u32     0 x286           [purpose UNKNOWN]
+0x20  u32     varies per mesh  e.g. 0x160 x61, 0x29B30 x2, 0x1920 x6        [meaning UNKNOWN]
+0x24  ...     payload body (vertices, indices, normals, UVs, skin weights)  [UNKNOWN layout]
```

### 5.1 `MOD ` payload body prefix — first decoded fields [E-031]

**Status: [PARTIAL]** — evidence E-031. The body begins at `+0x24` (immediately
after the header). Its first decoded prefix, body-relative (all little-endian):

```
body +0x00..+0x1B  zero bytes (28 bytes)
body +0x1C  u16    marker            0x8001 in all four pl021.pac MOD chunks  [UNKNOWN]
body +0x1E  u16    count            varies per mesh (474/300/182/182)        [UNKNOWN what it counts]
body +0x20  u32    0 in all observed chunks                                   [UNKNOWN]
body +0x24  u32    varies per mesh (768/192/128/128)                          [UNKNOWN]
body +0x28  u32    0 in all observed chunks                                   [UNKNOWN]
body +0x2C  u32    varies per mesh                                            [UNKNOWN]
body +0x30..+0x4B zero bytes
body +0x4C  f32    vector-like (tens to ~113)                                [UNKNOWN]
body +0x50  f32    vector-like                                                [UNKNOWN]
body +0x54  f32    vector-like                                                [UNKNOWN]
body +0x58  f32    vector-like                                                [UNKNOWN]
body +0x5C  u32    equals ``count`` for the duplicated slots 23/25 only       [UNKNOWN]
```

* `body +0x1E` (the count) reappears verbatim at `body +0x5C` for the two
  byte-identical slots 23/25, which supports reading it as a stored count; what
  it counts is an inference, not an observation.
* `marker == 0x8001` coincides with the `0x8000` zero base used for MOT frame
  times (E-026); any relationship is [UNKNOWN].
* `tools/dmc3/mod.py` exposes `ModBodyPrefix` decoding exactly this prefix;
  the vertex/index/normal/UV/skin-weight layout beyond it remains the remainder
  of issue F1.

The payload body layout beyond `+0x5C` is **not** decoded — that is the
remainder of issue F1 (vertex/index/normal/UV/skin-weight layout).
* `+0x14 == 0xF4240` (1,000,000) in 187/286 chunks suggests one field may be a
  byte size or vertex count, but that is an inference, not an observation.

`SHW ` chunk header (verified bytes, unknown semantics) — unchanged from prior
observations:

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

> **Correction.** Earlier revisions of this section placed varying values
> (e.g. `0x0003180B`, `0x00029B30`) at `+0x0C`/`+0x1C`. Real bytes show
> `+0x0C` and `+0x1C` are `0` in every `MOD ` chunk checked (286/286), and
> those values actually appear at `+0x10`/`+0x20`. The spec above reflects the
> corrected offsets; see `docs/EVIDENCE.md` E-030 for the raw bytes.

Open issues: mesh vertex/index layout, material→texture binding, skeleton.
