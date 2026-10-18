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
leading bytes (E-008) — so no single header shape is shared across them:

* **slot 10** [PARTIAL structure / [UNKNOWN] semantics] — at file offset
  `0x077ED0`, span `0x1E0` (480 bytes). Body-relative: 23 little-endian u16
  pairs at stride 4 (`+0x00..+0x5B`), then a little-endian f32 stream
  (`+0x5C..end`). Pair 0 is `(92, 132)`; pairs 0–14 have first element `92`
  (`0x5C`) and second element `132 + 20*i` (`132..412`); pairs 15–22 are
  `(112, 432)`, `(92, 432)`, `(92, 132)×6`. The f32 stream opens
  `0.3, -0.01, -0.1, 0.0, 0.7` (raw `9a 99 99 3e 0a d7 a3 bc cc cc cc bd
  00 00 00 00 66 66 66 3f`). What the pairs index, the pair count's source,
  and the f32 stream's meaning are [UNKNOWN] (evidence E-037).
* **slot 21** — 14 little-endian u16 segments delimited by `0xFFFF`
  separators (13 separators; segment sizes 2/6/1/8/10/31/111/34/1/6/8/27/84/26
  u16s) at file offset `0x07FF00`, span `0x2E0` (evidence E-043). Segment 0 is
  verbatim `(6, 408)`. Segment index 5 ends in an arithmetic run
  `36, 50, 64, …, 232` stepping by 14; segment index 6 repeats a 7-u16
  sub-record `32767, 0, 32767, 1, 1, 0, VALUE` with `VALUE` stepping by 256.
  `0x7FFF` occurs inside segments and is not a delimiter. Segment-internal
  layout and all field meanings [UNKNOWN] (evidence E-043).
* **slots 5, 6, 7, 9, 11, 22** — leading bytes differ per slot; slots 9/11 are
  f32 arrays. Layouts [UNKNOWN].

Every field meaning in this section is [UNKNOWN].

---

## 2. Weapon archives (`.pac` starting with `PNST`) — header [VERIFIED], payload [UNKNOWN]

**Evidence E-006** — verified on both weapon archives
(`plwp_vergilsword.pac`, `plwp_newvergilsword.pac`):

```
0x00  char[4]  "PNST"
0x04  u32      entry_count
0x08  u32      offset[entry_count]   file-relative; 0 == empty slot
...   zero padding to 16-byte alignment
data  chunks at the recorded offsets
```

`align_up(0x08 + 4 * entry_count, 0x10) == offset[0]` holds on both files.
Unlike `PAC`, no size-prefixed chunk framing has been observed: chunk tags,
when present, sit at byte 0. Chunk kinds seen in the wild: `MOD ` mesh,
`SHW ` shader, nested `PAC\0`, nested `PNST`, plain-text cloth config
(`;wp005.clt`), and raw blocks beginning `01 00 00 00 11 00 00 00` whose
meaning is [UNKNOWN].

**Unknown.** The raw-block format, per-chunk payload layouts beyond the
headers already decoded (MOD: E-030/E-031; SHW: E-036/E-038), whether offset
`0` occurs as an empty slot, and the contents of nested containers. Open issue
*"Reverse the PNST weapon container"* continues at the payload level.

`tools/dmc3/pnst.py` exposes `PnstArchive`, decoding exactly the header and
offset table above; exercised by unit tests on synthetic fixtures (no game
data committed).

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

**Status: [VERIFIED] wrapper, [UNKNOWN] pre-header fields** — evidence E-005,
E-034.

In the HD Collection a `.tm2` is a thin platform header followed by an **ordinary
DDS** blob. Extraction is `data[find(b"DDS "):]`.

`i001_90.tm2` (65,776 bytes): `DDS ` at offset **0x70**, `dwSize = 124`, flags
`0x00081007`, `256×256`, fourCC `DXT3`, one mip level, DDS payload runs from
file 0xF0 to EOF (65,536 bytes).

### 4.1 TM2 pre-header — census, all fields [UNKNOWN] (E-034)

The 0x70-byte platform header preceding the embedded DDS blob, read as 28
little-endian u32s in `i001_90.tm2`:

```
+0x00  u32  0                +0x18  u32  0
+0x04  u32  0                +0x1C  u32  0
+0x08  u32  131328 (0x00020100)  +0x20  u32  64
+0x0C  u32  43748 (0x0000AAE4)   +0x24  u32  0
+0x10  u32  16777472 (0x01000100) +0x28  u32  0
+0x14  u32  1                +0x2C  u32  0
+0x30  u32  0                +0x48  u32  0x3C000000
+0x34  u32  0                +0x4C  u32  0x3C000000
+0x38  u32  65536 (0x00010000)   +0x50  u32  0
+0x3C  u32  0                +0x54  u32  0
+0x40  u32  0                +0x58  u32  0
+0x44  u32  0x00800080        +0x5C  u32  0
+0x60  u32  0                +0x64  u32  65664 (0x00010080)
+0x68  u32  8                 +0x6C  u32  0
```

All 28 fields are **[UNKNOWN]**: no semantics established. An observed
correlation in this single file — +0x38 == 65,536 equals the DDS pitch — is
not a rule (only one TM2 file exists in this install, so no cross-file
confirmation is possible).

**Correction history.** E-005 reported "only 0x08 and 0x0C are non-zero" among
the pre-header u32s; E-034's full census falsifies that — non-zero u32s also
appear at +0x10, +0x14, +0x20, +0x38, +0x44, +0x48, +0x4C, +0x64, +0x68. The
wrapper-is-DDS conclusion stands; only the pre-header census was incomplete.

**[UNKNOWN]** the PS2/PS3 TIM2 variant — this project targets the HD
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

`SHW ` chunk header (verified bytes across all four `pl021.pac` `SHW `
chunks; evidence E-036), all little-endian:

```
+0x00  char[4]  "SHW "
+0x04  f32      0.5 (0x3F000000) x4/4 observed
+0x08  u32      0 x4/4
+0x0C  u32      0 x4/4   ([UNKNOWN] purpose)
+0x10  u32      varies   (0x00011811, 0x00002707, 0x00020101, 0x00010101)
+0x14  u32      varies   (100, 102, 0x000315D8, 103)
+0x18  u32      0 x4/4
+0x1C  u32      0 x4/4   ([UNKNOWN] purpose)
+0x20  u16      varies   (0x000A, 0x0016, 0x0027, 0x0027)
+0x22  u16      varies   (0x0010, 0x0028, 0x0042, 0x0042)
+0x24  u32      0 x4/4
+0x28  u32      0 x4/4
+0x2C  u32      0 x4/4
+0x30  u32      varies   (0x460, 0x1E0, 0x60, 0x60) — offsets a 16-byte-block
                       index table in all four chunks   [table layout UNKNOWN]
+0x34  u32      0 x4/4
+0x38  u32      varies   (0x560, 0x460, 0x480, 0x480) — offsets an index
                        buffer `[u16 i0,i1,i2,0] x count` (structure [PARTIAL];
                        see §5.1.1, evidence E-038)
+0x3C  u32      0 x4/4
+0x40  u32      varies   (0x5E0, 0x5A0, 0x690, 0x690) — offsets a position
                        buffer `[f32 x,y,z,1.0] x count` (structure [PARTIAL];
                        see §5.1.1, evidence E-038)
+0x44  u32      0 x4/4
+0x48  u32      varies   (0x680, 0x700, 0x900, 0x900) — offsets a further
                        sub-table (constant-byte run, then a u32 stream; layout
                        [UNKNOWN]; see §5.1.1, evidence E-038)
+0x4C  u32      0 x4/4
+0x50  zero bytes x16
```

* Slots 24 and 26 are byte-identical `SHW ` chunks (a duplicated shader pair,
  like the MOD slots 23/25).
* The four varying fields at +0x30/+0x38/+0x40/+0x48 each point at a sub-table
  inside the chunk; +0x30's table holds three small u32 indices plus a zero
  per 16-byte entry in all four chunks (E-036). The +0x38 index buffer and
  +0x40 position buffer are structurally decoded (§5.1.1, evidence E-038);
  the +0x48 table's layout and all field meanings are [UNKNOWN]; the texture
  binding that issue F2 asks for is not yet decoded.
* `tools/dmc3/shw.py` exposes `ShwHeader`, `ShwIndexTable`, `ShwPositionTable`,
  `ShwSubTables` and `parse_shw_sub_tables` / `maybe_shw_sub_tables`, decoding
  exactly the observed sub-table structure from real bytes, exercised by unit
  tests on synthetic fixtures.

### 5.1.1 `SHW ` sub-tables — index buffer (+0x38) and position buffer (+0x40)

**[PARTIAL structure / [UNKNOWN] semantics]** — evidence E-038. The `field_38`
(+0x38) and `field_40` (+0x40) header fields are chunk-relative offsets, and
`field_48` (+0x48) is the offset of the next table. Buffer sizes come from the
consecutive-pointer differences, verified as an invariant across all four
chunks:

* index count   = `(field_40 - field_38) / 8`,  layout `[u16 i0, u16 i1, u16 i2, u16 0]`
* position count = `(field_48 - field_40) / 16`, layout `[f32 x, f32 y, f32 z, f32 1.0]`

The index table occupies `[field_38, field_40)` and the position table
`[field_40, field_48)`; the two are contiguous in all four chunks:

| Slot | field_38 | index count | field_40 | position count | field_48 |
|------|----------|-------------|----------|----------------|----------|
| 8 | 0x560 | 16 tris | 0x5E0 | 10 positions | 0x680 |
| 14 | 0x460 | 40 tris | 0x5A0 | 22 positions | 0x700 |
| 24/26 | 0x480 | 66 tris | 0x690 | 39 positions | 0x900 |

Worked example — slot 8 (file base 0x75470), raw bytes little-endian:

```
file 0x759d0 (+0x38): 06 00 0e 00 07 00 00 00   -> index (6, 14, 7)
                       06 00 05 00 0a 00 00 00   -> index (6, 5, 10)
file 0x75a50 (+0x40): ce c4 8a c1 9d f7 08 43   -> position x=-17.3461
                       a7 36 12 c1 00 00 80 3f   -> y=+136.9672 z=-9.1383 w=+1.0
```

Position values show left/right symmetry (e.g. slot 14 `(-14.87,+4.02,+7.75)`
/ `(+15.30,+4.02,+7.75)`) and w is exactly 1.0 in every entry — consistent with
vertex coordinates, but object-space vs world-space is [UNKNOWN].

**Cross-reference [UNKNOWN]:** whether the index buffer references the position
buffer is not established. It holds for slots 24/26 (max index 28 < 39
positions) but not for slots 8/14 (slot 8 max index 15 > 10 positions; slot 14
max index 30 > 22 positions), suggesting additional vertex buffers or separate
sub-meshes. The +0x48 table's layout and all field meanings are [UNKNOWN];
the texture binding issue F2 asks for remains [UNKNOWN].

> **Correction.** An earlier revision of this section listed the varying values
> `0x460, 0x1E0, 0x60` at `+0x28`. Real bytes show `+0x28` is `0` in all four
> chunks and those values live at `+0x30`; the spec above reflects the
> corrected offsets. See `docs/EVIDENCE.md` E-036 for the raw bytes.

Notable: **`pl021.pac` slots 23 and 25 are byte-identical `MOD ` chunks**, as are
slots 24 and 26 (`SHW `) — a duplicated mesh/shader pair. **[INFERRED]** these are
the two Vergil render variants (with/without the Devil Trigger / coat layers).

> **Correction.** Earlier revisions of this section placed varying values
> (e.g. `0x0003180B`, `0x00029B30`) at `+0x0C`/`+0x1C`. Real bytes show
> `+0x0C` and `+0x1C` are `0` in every `MOD ` chunk checked (286/286), and
> those values actually appear at `+0x10`/`+0x20`. The spec above reflects the
> corrected offsets; see `docs/EVIDENCE.md` E-030 for the raw bytes.

Open issues: mesh vertex/index layout, material→texture binding, skeleton.

## 6. FLVER model header (prior art, FromSoftware) — header [VERIFIED], body [UNKNOWN]

**Evidence E-039** — `BD_M_10100.flver` (467,008 bytes), the body mesh of
Vergil from the third-party Bloodborne Vergil package (E-014). The weapon was
already obtained via Source .smd/.ascii (E-015); the body exists only as FLVER.

```
0x00  char[6]  "FLVER\0"                    [VERIFIED magic]
0x06  u16      76                           [UNKNOWN]
0x08  u16      20                           [UNKNOWN]
0x0A  u16      2                            [UNKNOWN]
0x0C  u32      61488                        [UNKNOWN]
0x10  u32      405520                       [UNKNOWN]
0x14  u32      0                            [UNKNOWN]
0x18  u32      6                            [UNKNOWN]
0x1C  u32      334                          [UNKNOWN]
0x20  u32      6                            [UNKNOWN]
0x24  u32      12                           [UNKNOWN]
0x28  f32 x6   -0.7157, 0.0, -0.1980,       [UNKNOWN semantics]
           0.7180, 1.7909, 0.2405           <- six floats, plausibly a bounding box
0x40  u32      28062                        [UNKNOWN]
0x44  u32      28062                        [UNKNOWN]
0x48  u32      256                          [UNKNOWN]
0x4C  u32      0                            [UNKNOWN]
0x50  u32      36                           [UNKNOWN]
0x54  u32      10                           [UNKNOWN]
0x58  u32      42                           [UNKNOWN]
0x5C..0x7F zero bytes                      (padding to the 128-byte header block)
```

* All integers little-endian. Every field except the magic is [UNKNOWN].
* The six floats at 0x28–0x3F plausibly form a bounding box (E-017 read a
  1.79 m vertical extent, consistent with a humanoid body) — that is an
  inference, not an observation.
* From 0x80 to 0x140 the file contains six 32-byte section entries (E-040),
  each eight little-endian u32s: `u32_00, u32_04, u32_08 == 7, u32_0c ==
  7 * entry_index, u32_10, u32_14 = 48160 + 240 * index, u32_18 in 0..5,
  u32_1c == 0`. Verified on this file; every field meaning is [UNKNOWN].
  `u32_00` is a running offset whose step equals the previous entry's `u32_10`;
  `u32_14` points at a `"GX**"` magic block which starts a 240-byte GX group
  (eight blocks: GX00, GX04, GX20, GX22, GX24, GX26, GX30, then a
  0x7FFFFFFF sentinel — see §6.1, evidence E-041); exact for all six sections
  in this file. Entry 0's `u32_00` (0xC1C0, immediately after group 5) opens a
  UTF-16LE name string (`costume_parsn_...`).
* Header +0x0C (61488 = 0xF030) points at u16 index-like data
  (25, 39, 0 / 25, 40, 39 …); header +0x10 (405520 = 0x63010) points at
  further record data. Whether header +0x18 (== 6) is the section count or
  header +0x24 (== 12) is the record count is [UNKNOWN].
### 6.1 FLVER GX blocks — [PARTIAL structure / [UNKNOWN] semantics] (E-041)

Each section's `u32_14` (48160 + 240 * section index in this file) points at a
240-byte group of eight blocks. Every block is `u32 tag; u32 constant 100;
u32 size; bytes payload` where the payload is `size - 12` bytes:

| Block | Tag | Size | Payload (observed) |
|---|---|---|---|
| 0 | `GX00` | 44 | 32 zero bytes |
| 1 | `GX04` | 64 | 12 zeros; f32s 5.0, 1.0, 0.5, 0.0, 5.0, 0.5, 1.0, 0.0; 8 zeros |
| 2-6 | `GX20` … `GX30` | 24 each | 12 zero bytes each |
| 7 | sentinel u32 0x7FFFFFFF | 12 | empty |

44 + 64 + 5*24 + 12 == 240, matching the section-stride delta. All six groups
in `BD_M_10100.flver` are byte-identical; what follows group 5 at 0xC1C0 is
the UTF-16LE name string from section 0's `u32_00`, not another group. Every
field meaning is [UNKNOWN]; the sentinel tag terminates the group. See
E-041 for the raw bytes and the correction to E-040's imprecise
"+4/+16 off" reading. `tools/priorart/flver.py` decodes this structure via
`parse_flver_gx_groups()` (unit-tested on synthetic fixtures, no game data
committed).

`tools/priorart/flver.py` exposes `FlverHeader` / `parse_flver_header()`
and `FlverSection` / `parse_flver_sections()`, decoding exactly this header
and table from real bytes, exercised by unit tests on synthetic fixtures
(no game data committed). The body mesh beyond the table remains [UNKNOWN];
T7b is advanced but not complete.
