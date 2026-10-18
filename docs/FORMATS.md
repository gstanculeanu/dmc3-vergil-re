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
leading bytes (E-008) — so no single header shape is shared across them.
Slot 0's header (E-033), slot 5's segment stream (E-052), slot 10's pair
table (E-037) and slot 21's segment table (E-043) are decoded structurally;
every field meaning remains [UNKNOWN]:

* **slot 5** [PARTIAL structure / [UNKNOWN] semantics] — at file offset
  `0x06B6E0`, span `0x4B30` (9,624 u16s): a little-endian u16 stream split
  into **215 segments** by **214** `0xFFFF` separators. Segment 0 is verbatim
  `(6, 0x37D0)`; segment sizes open `2, 1, 34, 60, 5, 13, …` and the tail
  holds segments up to 378 u16s. `0x7FFF` occurs inside segments as data,
  not as a delimiter — the same segment-stream structure as slot 21 (E-043)
  but with different segmentation (evidence E-052). What the segments index
  and what `0x7FFF` means inside them are [UNKNOWN].
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
* **slots 6, 7, 11, 22** — leading bytes differ per slot. Layouts [UNKNOWN].
* **slot 9** [structural / [UNKNOWN] semantics] — at file offset `0x077B50`,
  span `0x380` (896 bytes = **224 little-endian f32s**), no header, no count
  field, no separator (evidence E-062). The first 24 values read `10.4, -1.2,
  10.0, 12.0, -1.2, 15.0, 10.4, -0.8, 6.4, 12.4, -0.8, 12.0, 23.5, -1.2, 0.3,
  40.0, 13.0, -1.5, 25.0, 200.0, 500.0, 150.0, 150.0, 500.0`. 206 values are
  non-zero (indices 0…210) and the last 18 (indices 211…223) are zeros; 83
  distinct values, min `-790.0`, max `9000.0`, most common `0.0` (18), `500.0`
  (15), `150.0` (10), `60.0` (10). What the array indexes (the values are not
  all integer-valued, so it is not an obvious index/offset table) and whether
  the count is stored elsewhere are [UNKNOWN]. **Corrects a stale citation:**
  `Slot9Table` previously cited "E-053", which is the `eboot.bin` ledger entry.

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
(`;wp005.clt`), and raw blocks (evidence E-048).

**Raw block header — [PARTIAL structure / UNKNOWN semantics]** (E-048).
Slots 0 and 3 of both weapon archives carry identical 36,864-byte raw blocks
whose first 8 bytes are little-endian `u32 field_a == 1`, `u32 field_b == 17`
(`0x11`). The body opens with a zero-filled run (first non-zero byte at
body+2049 in every observed block) followed by structured data whose layout
and meaning are not established from bytes alone.

```
raw block (body-relative, little-endian):
+0x00  u32 field_a   observed 1 (all four blocks)
+0x04  u32 field_b   observed 17 / 0x11 (all four blocks)
+0x08  ...           zero run, then structured data; [UNKNOWN layout]
```

**Unknown.** Semantics of `field_a`/`field_b`; whether the body+2049 zero-run
length is significant; the raw-block tail structure; a second, different raw
block appears at slot 9 of `plwp_newvergilsword.pac` (400 bytes, a u16 stream
with `0xFFFF` separators and a `0x7FFF`-patterned tail). Per-chunk payload
layouts beyond the headers already decoded (MOD: E-030/E-031; SHW: E-036/E-038),
whether offset `0` occurs as an empty slot, and the contents of nested
containers. Open issue *"Reverse the PNST weapon container"* continues at the
payload level.

`tools/dmc3/pnst.py` exposes `PnstArchive` (header + offset table) and
`PnstRawBlock` / `parse_pnst_raw_block` / `maybe_pnst_raw_block` (the 8-byte
raw-block header only), exercised by unit tests on synthetic fixtures (no game
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

### 4.2 DDS → PNG (issue T2)

**Status: [VERIFIED] uncompressed BGRA32 and DXT1/DXT3/DXT5** — evidence
E-005, E-034, E-047. `tools/dmc3/dds.py` (`dds_to_png`) decodes the top mip
level of a legacy DDS blob to a PNG with alpha preserved:

* uncompressed 32 bpp BGRA: BGRA → RGBA reordered byte-for-byte; a structural
  round-trip test (tests/test_dds.py) checks the PNG structure, per-chunk
  CRC32, and exact decompressed rows;
* DXT1 (BC1): 8-byte blocks — two 5:6:5 colour endpoints plus 2-bit texel
  indices; `c0 > c1` gives two interpolated colours, all alphas 255; `c0 <= c1`
  makes index 3 transparent black `(0, 0, 0, 0)`;
* DXT3 (BC2): 16-byte blocks — a 64-bit explicit alpha bitmap (4 bits per
  texel, low nibble first, expanded ×17) plus a DXT1 colour block;
* DXT5 (BC3): 16-byte blocks — two alpha endpoints plus 3-bit texel indices
  (`alpha0 > alpha1` → a 7-step ramp; otherwise a 5-step ramp with 0 and 255)
  plus a DXT1 colour block.

Per-channel interpolation uses integer (floor) arithmetic; a hardware decoder
may differ by ±1, which is not claimed. DX10 extended headers and other
fourCCs raise `DdsError` (none occur in the local install). The in-game
semantic of the alpha channel (transparency, gloss, …) is [UNKNOWN].

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

---
## 7. GoW3R `R_*.WAD` container — header, directory, data region [PARTIAL]

**Status: [PARTIAL]** — evidence E-016, E-022, E-023, E-024, E-025, E-044.
Read-only from `C:\Users\GigelCastel\Desktop\gow3\CUSA01715\EXEC\WAD\PS4_LE\`.
All integers little-endian.

### 7.1 Header

```
0x00  u32  20
0x04  u32  8
0x08  char[]  banner, zero-padded ("WAD_R_Hades", "WAD_R_Sword00", …)
```

### 7.2 Record directory [VERIFIED structure]

From `0x40`: a record stream (E-023/E-025). Named records are 0x40 bytes:
`u32 type; u32 size; char name[0x38]`. Commands: `1` resource,
`2` GroupStart, `3` GroupEnd, `0x12` root (repeats the banner at the
directory end), `0x15` PopHeap. Typed markers `0x80000000 | class_id`
follow each resource and take `round_up(preceding resource size, 16)` bytes
(E-025 — marker length resolved on 87 small WADs). The stream ends where the
next u32 is not a valid type — `0xD80` for standard WADs, `0xDC0` for
`R_HADES.WAD` (65 records).

Every WAD examined carries the same 16 typed resource groups in fixed order:
`root TXRX WPTX CXT ANMX LGTX SCRX BHVX MDLX PRTX CAMX SNDX COLX FX OCCX MATX`.
The class id resolved from the name prefix agreed with the following marker's
id on every occurrence (E-024). Class ids: `CXT` 1, `ANMX` 3, `SCRX` 4,
`LGTX` 6, `TXRX` 7, `MATX` 8, `CAMX` 9, `MDLX` 13, `COLX` 14, `PRTX` 15,
`WPTX` 16, `BHVX` 18, `SNDX` 19, root 20, `FX` 21, `OCCX` 24.

### 7.3 Bulk data region and `DC_` footer [PARTIAL / UNKNOWN]

The bulk region starts where the directory ends (`0xD80` standard). It begins
with a small header whose fields are all **[UNKNOWN]** (verified byte-identical
on `R_SWORD00.WAD` and `GAZ650.WAD`): `u16 1`, `u16 0x77`, u32 (`0x0D69` /
`0x0D59`), a 16-byte NUL name (`"0352A58B_FFFFFFFFF"` /
`"721FBFB2_…"`), then zero padding and small u32s (see E-044 for the raw
bytes).

Near the end of the file sit six `DC_<banner>` footer chunks (ids `0x0B`..`0x10`;
0 or 6 per file — E-025), each with a 16-byte prefix
(`u64 0`, `u16 id`, `u16 0x0009`, `u32 size`) and a 0x34-byte name field.

### 7.4 `DC_` id `0x10` table [PARTIAL structure / UNKNOWN semantics] (E-044)

The id `0x10` chunk payload of `R_SWORD00.WAD` (file `0x14AD8`, size 3064,
payload at `0x14B1C`) reads as 766 little-endian u32s:

```
header u32s:   (0, 0x77, 0, 0x598)
entries:       (u32 flag, u32 offset, u32 value) x N — 118 entries observed,
               offsets ascending overall from 0x20 into the bulk region
               (>= 0xD80), values ascending overall from 0x5A4
u32 0xA4
NUL strings:   "CRT_Sword00", "FX", "Bubbles", "Ripples", "Freezing", "Stoned",
               "ShatterSystem", "BasePhysicalAttributes", "Light", "Tint",
               "Fire", "Joints", "tSoldier_0", "PushableMinSpeed", …
```

The trailing strings are object names — script/FX objects such as
`"MOV_SwordPickupWalk"`, `"tActionSetFlags_86"`, `"BRA_SwordPickupWalk"`,
`"NB_SwordBank"`. Entry offsets `>= 0xD80` land on bulk object data (verified
at file `0xD84`, `0xDE4`, `0xE44`, `0x15BC`, `0x1654`), but early entries
point at the directory/header regions, so `offset`'s reference frame is
[UNKNOWN]. What `flag` and `value` mean, whether one entry binds one directory
resource name / one string / one bulk object, and whether the layout
generalizes beyond `R_SWORD00.WAD` (single sample) are **[UNKNOWN]**.
On `GAZ650.WAD` the id `0x10` chunk is degenerate: six u32s, no entries, no
strings.

`tools/gow3/wad.py` parses exactly this layout via `parse_dc10_table()` and
claims no semantics; a WAD writer remains blocked (the entry → resource
binding and the `WadGraph` name→WAD binding are open — issues G9/G10).

### 7.5 `DEPENDENCYGRAPH.IFF` WadGraph registry — [PARTIAL structure / UNKNOWN semantics]

**Evidence E-021, E-045** — read-only from
`C:\Users\GigelCastel\Desktop\gow3\CUSA01715\EXEC\WAD\PS4_LE\DEPENDENCYGRAPH.IFF`
(265,776 bytes). All integers little-endian.

```
0x00  u16  field_00          23 on the sample                              [UNKNOWN]
0x02  u16  field_02          1                                             [UNKNOWN]
0x04  u32  size_field        265712 == file_size - 0x40                    [UNKNOWN]
0x08  char[0x38] banner      "WadGraph", zero-padded                       [VERIFIED]
0x40  u32  name_offset                                      [UNKNOWN relation]
0x04  u32  0                                              [VERIFIED on all records]
0x08  u32  field_b                                        [UNKNOWN]
0x0C  u32  field_d                                        [UNKNOWN]
0x10  u16  field_c                                        [UNKNOWN]
0x12  u64  0xFFFFFFFFFFFFFFFF (-1) constant sentinel      [VERIFIED]
0x1A  u8   0                                              [VERIFIED]
0x1B  u8   pad_byte                                       [UNKNOWN]
0x1C  u32  0x55555555 constant trailer                    [VERIFIED]
```

Records are 32 bytes at stride 0x20 starting at 0x40; windows that do not match
the pattern are skipped, so the record list is non-contiguous. On the single
sample **2,617 records** were observed spanning `0x40`..`0x2D440`, with
`name_offset` values in `185404..265667` — inside the file's NUL-separated name
table region (~0x2C000..EOF). `name_offset` correlates with the name strings:
observed to point exactly at a name start for 198/2,617 records and within a
few bytes of one for 2,337/2,617 (e.g. record at `0x1C7E0` has `name_offset
== 241454`, which is exactly the string `"Stub_1472"` at file `0x3AF2E`).
The exact relation is [UNKNOWN].

`field_b` (up to ~10^8), `field_d` (0 in 2,472/2,617 records), `field_c`
(0..65,535) and `pad_byte` are all [UNKNOWN]. **No name → WAD binding is
decoded**: `field_b` is not a small WAD index, and no WAD name table or index
is present in the file. Engine ground truth or a second WadGraph sample is
needed; issue G10 stays open.

`tools/gow3/wadgraph.py` exposes `WadGraphHeader`, `WadGraphRecord`,
`parse()`, `parse_records()` and a best-effort, explicitly heuristic
`record_name()`, decoding exactly the observed layout from real bytes and
claiming no semantics (unit-tested on synthetic fixtures, no game data
committed).

### 7.6 The `eboot.elf` image: file↔vaddr mapping and reference scanning (E-056)

`out/eboot.elf` (4,597,471 B) is a 64-bit little-endian ELF with `e_entry
0x144070` and one executable `PT_LOAD`: `p_offset 0x4000`, `p_vaddr 0`,
`p_filesz 0x3BD518`, flags `R|X`. Inside that segment `vaddr = file_offset −
0x4000`; the string tables sit in a read-only `PT_LOAD` at `p_offset 0x3C4000` /
`p_vaddr 0x3C0000`. A RIP-relative `lea`/`mov` operand is `[REX 0x40..0x4F]`
`8D|8B`, then a ModRM with `(modrm & 0xC7) == 0x05`, then `disp32`, and targets
`insn_va + insn_len + disp32` (`insn_len` 7 with a REX prefix, 6 without).

The WAD **record opcodes are numeric** (E-053), so the loader is not findable by
opcode name. `tools/gow3/eboot.py` maps addresses and lists the code that
references a named string (`WAD_`, `hfsm`, `DEPENDENCY`, `.wad`), and — using a
small limited instruction decoder (`reference_context` /
`string_reference_contexts`, E-063) — reports the constants passed alongside a
reference.

E-063 result: the `.wad` and `DEPENDENCY` strings have **zero** RIP-relative
references, so that route finds nothing; only `WAD_` (81 refs) and `hfsm` (9 refs)
are reachable. The `WAD_` sites feed object/asset **name registration** helpers
(`0x1F7200` at 25 sites, `0x1AAC30` at 15, `0x1011A0`, …), not the directory
dispatcher, and the only explicit length passed is **4** — the banner is matched
by a 4-byte `"WAD_"` prefix. The 42 `and eax, 0x80000000` sites in
`0x40187..0x43C5B` are a float sign-bit routine, not marker handling.

`[UNKNOWN]`: the directory-record dispatcher that reads the numeric opcodes, and
the directory→bulk binding (G9/G10).

### 7.7 Animation clip header — [PARTIAL] (E-058, E-059, E-060)

The clip directory of E-058 points `base + offsets[i]` at each clip. At that
offset is a **fixed per-clip header** (E-059, extended by E-060), verified on
every clip of `R_HADES.WAD` (77) and `R_HERCULES.WAD` (46). All integers
little-endian; the header is at least `0x118` bytes.

```
+0x00  char[0x38]  clip name, NUL-terminated            [VERIFIED]
+0x38  u32         clip size                            [VERIFIED]
+0x3C  u32         0 on 123/123 clips                   [VERIFIED]
+0x6C  f32         frame rate: 1/30 (114) or 1/15 (9)   [VERIFIED]
+0x7C  u32         == the +0x38 size (123/123)          [VERIFIED]
+0x80  f32         == f32@+0x6C (123/123)               [VERIFIED]
+0x90  u32         == the +0x38 size (123/123)          [VERIFIED]
+0x94  f32         == f32@+0x6C (123/123)               [VERIFIED]
+0xA4  u32         == the +0x38 size (123/123)          [VERIFIED]
+0xA8  f32         1/60 on 123/123 clips                 [VERIFIED]
+0x10C f32         reciprocal of f32@+0x6C (123/123)     [VERIFIED]
+0x110 f32         == f32@+0x6C (123/123)                [VERIFIED]
+0xF4  u32         low u16 = 1 on 11/123 clips           [VERIFIED values]
+0xF6  u16         frame count, 15..686, 44 values       [INFERRED]
+0x114 f32         == float32(1 / (frames - 1)) (123/123) [VERIFIED relation]
```

The size at `+0x38` is the authoritative clip bound: it equals the directory
offset delta for every non-final clip, and for the **final** clip it is the true
size while the directory span (`len(file) − offset`) is an over-estimate. This
corrects E-058's "the clip span bounds each move": only the header size does.

E-060's census adds the relations and the two derived fields:

* the size appears at **exactly four** offsets and the frame rate at **exactly
  four**; no fifth offset in `+0x00..+0x123` carries either value;
* `f32@+0x10C × f32@+0x6C == 1` on 123/123 (worst deviation 5.215e-08, i.e.
  binary32 rounding only);
* `f32@+0x114 == float32(1 / (u16@+0xF6 − 1))` on 123/123, **exact binary32
  equality**, so `+0xF6` is [INFERRED] the clip's **frame count** and `+0x114`
  the sample spacing of a curve normalised to `[0,1]`;
* `u16@+0xF4 == 1` on 11/123 clips, all `*Idle*`; [INFERRED] loop flag, **not
  proven** because `hadesKnifeIdleB`/`hadesKnifeIdleF` are `Idle`-named and hold
  `0`.

Every other u32 in `+0x00..+0x123` is constant on all 123 clips (the full list is
in E-060), including the `0xCD`/`0xCC` uninitialized-memory fill — so the region
is a fixed, mostly-redundant descriptor block, not a track table. The meaning of
the four copies, the remaining constants, the `0xCD`/`0xCC` fill and the clip's
*internal* encoding (channels, keyframes, root motion) remain **[UNKNOWN]** — the
latter is the remaining gap for F9/"moves".

#### Descriptor tail and data-section start — [PARTIAL] (E-061)

The descriptor does not stop at `+0x123`. Censusing `+0x120..+0x15B` on the same
123 clips shows the tail below, with the per-clip data section opening at
`+0x15C`:

```
+0x124  u32  per-clip, 16-byte aligned, in-file on 123/123   [INFERRED offset]
+0x128  u32  0x00800000 (constant)                            [VERIFIED value]
+0x12C  u32  per-clip, 16-byte aligned, in-file on 123/123   [INFERRED offset]
+0x130  u32  0x00010001 (constant)                            [VERIFIED value]
+0x134  u32  per-clip, 16-byte aligned, in-file on 123/123   [INFERRED offset]
+0x138  u32  0x037B0000 (constant)                            [VERIFIED value]
+0x13C  u32  per-clip, 16-byte aligned, in-file on 123/123   [INFERRED offset]
+0x140  u32  per-clip, small, not aligned                     [UNKNOWN]
+0x144  u32  per-clip, 16-byte aligned, in-file on 123/123   [INFERRED offset]
+0x148  u32  per-clip, small, not aligned                     [UNKNOWN]
+0x14C  u32  0xFFFFFFFF (×4: +0x14C/+0x150/+0x154/+0x158)     [VERIFIED value]
+0x15C  u16  0x0015 (21) on 123/123; then u16 0x000C at +0x160 [VERIFIED value]
```

So the fixed descriptor ends at `+0x158`; E-060's "from `+0x124` onward the u32s
are pointer-like and per-clip" holds only for the seven fields above, not for the
interleaved constants or the sentinel run. The five aligned fields are
**[INFERRED]** file offsets into a shared pool: `+0x12C` values are reused
between clips (18/77 in `R_HADES.WAD`, in coherent groups), and one Hades pair's
`+0x124` values differ by exactly 16. Pointer/offset semantics, the two unaligned
fields, the constants and the marker pair remain **[UNKNOWN]**.

`tools/gow3/anim.py`: `ClipHeader` (with `frames`, `loop_flag`, `sample_rate`,
`frame_count_rate`, `rate_copies` and the four `*_ok` relations / `invariants()`),
`parse_clip_header()`, `ClipDescriptorTail` (`fields`, `constants`, `sentinel`,
`data_marker`, `second_marker`, `aligned_ok` / `constants_ok` / `sentinel_ok` /
`markers_ok` / `invariants()`), `parse_clip_descriptor_tail()`,
`maybe_clip_descriptor_tail()`, `float32()`, `expected_sample_rate()`, the
`CLIP_*` / `CLIP_TAIL_*` / `CLIP_DATA_*` constants; `Clip.size` is read from
`+0x38` (`Clip.end` uses it), the directory span is retained as the upper bound.
