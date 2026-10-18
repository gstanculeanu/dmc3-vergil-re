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
body+0x0870 (file offset 0x8F0) the bytes contain a `DDS ` magic — an embedded
DDS-like blob whose presence inside the raw slot is unexplained. **Update
(E-084):** slot 0's DDS is `dwSize = 124`, `dwFlags = 0x000A1007`,
**256×256**, fourCC `DX10`, depth 1, 9 mips; E-033's "256×64" was a misread
dword. The bytes at body+0x808..+0x86F are the shared **texture descriptor**
of §1.4. The remaining ~235 KB of the slot's span is non-zero and structured;
its layout is undecoded.

The other eight untagged slots (5, 6, 7, 9, 10, 11, 21, 22) have different
leading bytes (E-008) — so no single header shape is shared across them.
Slot 0's header (E-033), slot 5's segment stream (E-052), slot 6's record table
(E-086), slot 7's vector-record table (E-089), slot 9's flat f32 array (E-062),
slot 10's pair table (E-037), slot 11's flat f32 array (E-090) and slot 21's
segment table (E-043) are decoded structurally; every field meaning
remains [UNKNOWN]:

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
* **slot 6** [PARTIAL structure / [UNKNOWN] semantics] — at file offset
  `0x070210`, span `0x3F0` (1008 bytes = **252 fixed 4-byte records**), no
  separate header or count field (evidence E-086). Each record is
  `u8 field_a`, `u8 field_b`, `u16 field_c`; the fourth byte is zero in all
  252 records. `field_a` values: `1` ×201, `0` ×32, `4` ×7, `6` ×6, `2` ×5,
  `5` ×1. `field_b` values: `0` ×171, `9` ×29, `13` ×14, `1` ×8, `2` ×5,
  `3`/`4`/`15`/`20` ×3 each, `7`/`14` ×2 each, and `10`, `16`, `17`, `19`,
  `21`–`25` ×1 each. 32 records are all-zero; they sit at indices
  `23, 44, 45, 99, 119, 130, 166–169, 176–179, 182, 199` and `236–251`, so the
  non-zero records form **ten runs** (sizes `23, 20, 53, 19, 10, 35, 6, 2, 16,
  36`). `field_c` equals the record's own index for **209/252** records; the
  exceptions are the all-zero records plus indices `2, 3, 4, 5, 47` and the
  six-record run `93–98` (which all carry `field_c == 81`). Every field
  meaning is [UNKNOWN]; the parser reads exactly the observed layout.
* **slot 7** [PARTIAL structure / [UNKNOWN] semantics] — at file offset
  `0x070600`, span `0x4E70` (20,080 bytes = **251 fixed `0x50`-byte records**),
  no separate header or count field (evidence E-089). Each record is
  `u32 field_00`, three zero u32s, then four `f32[4]` vector slots at
  `+0x10`/`+0x20`/`+0x30`/`+0x40`. `field_00` is `2` ×246, `3` ×4
  (indices `142, 151, 163, 164`) and `4` ×1 (index `143`); the three reserved
  u32s are zero in all 251 records. Vector slot 3 is all-zero in every record.
  The fourth component of vector slot 0 is exactly `1.0` in 247/251 records
  (exceptions are the four `field_00 == 3` records: 0.0, 61.0, 341.0, 0.0).
  Slots at or beyond `field_00` are all-zero in 237/251 records; the 14
  exceptions (all `field_00 == 2`) are indices `10, 78, 79, 114` and
  `152–161`, each with a non-zero first component in vector slot 2.
  `field_00` behaving as a slot count and the slots as `(x, y, z, w)` are
  [INFERRED], not proven; every component meaning is [UNKNOWN].
* **slot 11** [structural / [UNKNOWN] semantics] — at file offset `0x0780B0`,
  span `0x2A0` (672 bytes = **168 little-endian f32s**), no header, no count
  field, no separator (evidence E-090) — the same shape as slot 9 (E-062). The
  first twelve values read `9, 9, 9, 9, 10, 270, 0, 5, 330, 0, 18, 10`. **142**
  values are non-zero; the interior zeros are exactly indices `6`, `9`, `58` and
  the **last 23 values (indices `145`–`167`) are zero**; 67 distinct values, most
  common `9.0` (26×) and `0.0` (26×), max `2000.0`, min `−45.0`. Indices
  `104`–`114` are a period-3 rotation of `400, 350, 1000`. **No record framing is
  recovered:** of every candidate size dividing 168 (`2, 3, 4, 6, 7, 8, 12, 14,
  21, 24, 28, 42, 56`) none has a constant column and no non-zero record of size
  2/3/4/6/7/8 repeats, so the `42 × f32[4]` / `24 × 7` / `21 × 8` readings are
  neither confirmed nor refuted. **Corrects the earlier note** that the array
  opens with `10.0`; the real first value is `9.0`. Layout beyond the flat f32
  reading and every field meaning are [UNKNOWN].
* **slot 22** [PARTIAL] — a **texture slot**: the shared descriptor of §1.4 at
  body+0x808 followed by an embedded `DXT1` DDS at body+0x870 (32×32, 1 mip,
  512-byte payload); the descriptor's relations to the DDS header are
  [VERIFIED] (evidence E-084). Field meanings [UNKNOWN].
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

### 1.4 Texture slots: the shared texture descriptor — structure [VERIFIED] (E-084)

The untagged texture slots (`pl021.pac` 0 and 22) and the HD `.tm2` platform
pre-header carry the **same 0x68-byte descriptor** immediately before an
embedded DDS. In a PAC texture slot it starts at body+0x808 (after eight zero
bytes), DDS at body+0x870; in a `.tm2` it starts at file+0x08, DDS at file+0x70
— a `0x800` offset difference. Fields are relative to the descriptor start `D`
(little-endian):

```
D+0x00 u16          mip count << 8   (0x0900 for 9 mips, 0x0100 for 1) [INFERRED]
D+0x02 u16          2
D+0x04 u32          0x0000AAE4
D+0x08 u16,(u16)    (width, height)          == the DDS dwWidth/dwHeight
D+0x0C u32          1
D+0x18 u32          64
D+0x30 u32          DDS payload byte size
D+0x3C u16,(u16)    (width // 2, height // 2)
D+0x40 f32,(f32)    2 / width                == 1 / (width // 2)
D+0x5C u32          payload size + 128 (the DDS header)
D+0x60 u32          8
D+0x68 DDS          128-byte DDS header ("DDS ")
```

The five relations above hold on **three real chunks with no exception**:
`pl021.pac` slot 0 (256×256 `DX10`, 9 mips, payload 87,428) and slot 22
(32×32 `DXT1`, 1 mip, payload 512), plus `i001_90.tm2` (256×256 `DXT3`,
1 mip, payload 65,536 — exactly `256*256*1`). Both observed PAC slots are
square, so the descriptor's two extents cannot distinguish a width axis from a
height axis. **Every field meaning beyond these relations is [UNKNOWN]**, and
the descriptor is not known to hold more than one surface; the payload's block
format is carried by the DDS fourCC.

Tooling: `TextureChunk` / `maybe_texture_chunk` in `tools/dmc3/raw.py`, with
`PAC_TEXTURE_DESCRIPTOR_OFFSET = 0x808` (default) and
`TM2_TEXTURE_DESCRIPTOR_OFFSET = 0x08`, and the
`dimensions_match` / `half_extent_matches` / `inverse_scale_matches` /
`total_size_matches` / `mips_match` properties.

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

> **Engine cross-check (E-075).** `dmc3.exe` has a 16-bit angle unit: one full
> turn is `0x10000`, `0x4000` is a quarter turn and `0x8000` a half turn, via the
> `cosf`/`sinf` wrappers at RVA `0x32D9C0`/`0x32D9F0` and the `f32` constant
> `2*pi/0x10000` at RVA `0x508834`. The modal channel value `0x3FFF` is
> `89.9945 deg` — "a bone at 90 deg". **[INFERRED]** the three channels may use
> this unit, but no MOT byte has been traced into the helpers, so their meaning
> is still **[UNKNOWN]**.

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

### 4.1 TM2 pre-header — the shared texture descriptor (E-034, E-084)

The 0x70-byte platform header preceding the embedded DDS blob, read as 28
little-endian u32s in `i001_90.tm2`. **Update (E-084):** `+0x08..+0x6F` is not
an anonymous census — it is the **same 0x68-byte texture descriptor** the
untagged `pl021.pac` texture slots carry at body+0x808 (§1.4), verified
field-for-field on all three real artifacts. The relations in §1.4
(dimensions, half-extents, `2/width`, `payload+128`, mip count at `+0x08`) hold
here too: `+0x10` = (256, 256), `+0x38` = 65,536 = the DXT3 payload
(`256*256*1`), `+0x44` = (128, 128), `+0x48`/`+0x4C` = `0.0078125`, `+0x64` =
`65536 + 128`. The leading eight bytes (+0x00..+0x07) are zero. The `+0x38 ==
pitch` observation E-034 flagged is thereby explained as the DDS payload size,
not a coincidence. Every remaining field meaning is [UNKNOWN]; the one
caveat stands — only one `.tm2` file exists locally, so the format's generality
rests on the two PAC slots that agree with it.

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

All remaining fields are **[UNKNOWN]** beyond the §1.4 relations: the
descriptor census above is retained for reference, but `+0x08`/`+0x0C`/`+0x10`/
`+0x14`/`+0x20`/`+0x38`/`+0x44`/`+0x48`/`+0x4C`/`+0x64`/`+0x68` are now the
shared descriptor fields `D+0x00`/`D+0x04`/`D+0x08`/`D+0x0C`/`D+0x18`/`D+0x30`/
`D+0x3C`/`D+0x40`/`D+0x44`/`D+0x5C`/`D+0x60` (E-084).

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

### 5.1 `MOD ` payload body prefix — first decoded fields [E-031, E-091, E-092, E-093, E-094, E-095, E-096, E-097]

**Status: [PARTIAL]** — evidence E-031 (pl021.pac), E-091 (all 286 install
`MOD ` chunks). The body begins at `+0x24` (immediately after the header). Its
first decoded prefix, body-relative (all little-endian):

```
body +0x00..+0x1B  zero bytes (28 bytes)
body +0x1C  u32    tagged count  (count << 16) | tag
                   tag in 0x8000..0x8FFF on 286/286 chunks  [E-091; what it selects UNKNOWN]
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

* **The `+0x1C` field is one tagged u32, not two `u16`s (E-091).** E-031 read the
  `u16` at `+0x1C` as a "marker" (`0x8001`) and the `u16` at `+0x1E` as a "count".
  The four bytes are a single little-endian u32 whose **low half is a tag** and
  whose **high half is the count**. Across all **286** `MOD ` chunks in the
  install the tag is `0x8001` x279, `0x8002` x4, `0x8201` x2, `0x8005` x1 —
  every one in the `0x8000` namespace, so the tag is per-chunk data (likely a MOD
  subtype), not a magic.
* `body +0x1E` (the high half) reappears verbatim at `body +0x5C` for the two
  byte-identical slots 23/25, which supports reading it as a stored count; what
  it counts is an inference, not an observation.
* The tag shares the `0x8000` base with MOT frame times (E-026); any relationship
  is [UNKNOWN].
* `body +0x5C` and `body +0x9C` carry the same tagged shape (`0x8000`-namespace
  low `u16`) in 188/286 and 170/286 chunks respectively (E-091); whether they are
  further tagged records is [UNKNOWN].
* `tools/dmc3/mod.py` exposes `ModBodyPrefix` (with `tag_word`, `tag`, `count`,
  `tag_in_namespace`) decoding exactly this prefix; the
  vertex/index/normal/UV/skin-weight layout beyond it remains the remainder of
  issue F1.

The payload body layout beyond `+0x5C` is **not** decoded — that is the
remainder of issue F1 (vertex/index/normal/UV/skin-weight layout). The body is
**heterogeneous** across the four `pl021.pac` chunks: slots 23/25 (the
byte-identical pair) carry a strictly increasing, 16-byte-aligned u32
section-offset table at body `+0x6C` (`0xD0, 0x960, 0x11F0, 0x14D0, 0x17B0,
0x18F0`), while slots 1/12 do not (E-091).
* `+0x14 == 0xF4240` (1,000,000) in 187/286 chunks suggests one field may be a
  byte size or vertex count, but that is an inference, not an observation.

#### E-092 update: the body opens with a fixed-size descriptor array — structure [VERIFIED]

E-031/E-091 read only the first 0x40 bytes and called them a "prefix". Reading
the whole body (all **286** install `MOD ` chunks) shows those bytes are the
first record of an **array of fixed 0x40-byte descriptors** that opens the body:

```
descriptor +0x00  u32     0 where observed
descriptor +0x0C  4x f32  vector-like values                      [meaning UNKNOWN]
descriptor +0x1C  u32    tagged count (count << 16) | tag, 0x8000 namespace
descriptor +0x20  u32     0 where observed
descriptor +0x24  u32     a body-relative byte offset -> data block (E-093)
descriptor +0x28  u32     0 where observed
descriptor +0x2C  u32     varies (0x00100001 in many records)     [meaning UNKNOWN]
```

* The array's **byte size** is the u32 at body `+0x24` — descriptor 0's own
  `+0x24`. It is a multiple of `0x40` in **279/286** chunks; the other seven
  (all in `id430.pac` / `id470.pac`) add `0x10`.
* `count = array_size // 0x40` (range 2..42). Verified **286/286**: exactly
  `count - 1` descriptors carry a `0x8000`-namespace tag and the last (the
  **footer**) does not.
* **`ModBodyPrefix` re-interpreted.** Its `tag_word`/`field_24`/`field_2c` are
  descriptor 0's own fields; its `vector` and `repeat` actually belong to
  descriptor 1 (`0x4C = 0x40 + 0x0C`, `0x5C = 0x40 + 0x1C`). This explains
  E-091's "the same tagged shape recurs at body +0x5C in 188/286": body +0x5C
  is descriptor 1's tag, present unless `count == 2` (98 chunks), and
  `286 − 98 = 188`. Body +0x9C is descriptor 2's tag, present when `count ≥ 4`
  (`286 − 98 − 17 = 171`; E-091 observed 170).
* Descriptor `+0x24` is 16-byte aligned in **284/286** chunks and strictly
  increasing across the tagged `records` in **282/286**. The array-size field is
  descriptor 0's `+0x24`, so descriptor 0's data begins exactly at the array end
  (`count * 0x40`) — the descriptor data follows the array.
* Descriptor-tag census over all tagged `records`: `0x8001` x1519, `0x8002` x26,
  `0x8008` x8, `0x8201` x3, `0x8601` x2, `0x8004` x2, `0x8005` x1 — three tag
  values (`0x8008`, `0x8601`, `0x8004`) are new relative to E-091's first-field
  census.
* What the array describes, what `count` counts, the footer's role and the data
  layout are all **[UNKNOWN]**.
* `tools/dmc3/mod.py` exposes `ModBodyDescriptor`, `ModBodyDirectory`,
  `descriptor_count`, `maybe_mod_body_directory` and the `BODY_DESCRIPTOR_*`
  constants.

#### E-093 update: each descriptor's `+0x24` names a data block with a fixed 0x2C-byte prefix — structure [VERIFIED]

Reading the bytes descriptor `+0x24` points at (all **286** install `MOD `
chunks) shows the referent is a **data block**, and the blocks are consecutive:

* Descriptor 0's `+0x24` equals the array-size field on **286/286** chunks, so the
  first block begins exactly at the array end; each block runs to the next
  record's `+0x24`, and the last runs to the body end (descriptor offsets are
  strictly increasing on 282/286 chunks).
* A block opens with a **fixed 0x2C-byte prefix**, all-zero except **three u32s
  at `+0x04`, `+0x0C`, `+0x1C`**; the payload begins at `+0x2C`:

```
block +0x00  u32  0
block +0x04  u32  offset_a  body-relative, 16-byte aligned
block +0x08  u32  0
block +0x0C  u32  offset_b  body-relative, 16-byte aligned
block +0x10  u32  0
block +0x14  u32  0
block +0x18  u32  0
block +0x1C  u32  offset_c  body-relative (often leaves the block)  [meaning UNKNOWN]
block +0x20  u32  0
block +0x24  u32  0
block +0x28  u32  0
block +0x2C       payload                                            [layout UNKNOWN]
```

* Verified on **1,542/1,556** readable blocks (14 non-conforming blocks, all in
  `em035.pac`/`pl001.pac`/`pl015.pac`/`pl016.pac`, where the prefix bytes read as
  `f32`/other content). `data_offset < offset_a < offset_b` on 1,544/1,556 and
  `offset_a`/`offset_b` fall inside the block on 1,540/1,556; all three offsets
  are 16-byte aligned on 1,503/1,556.
* **[INFERRED]** where the ordered/in-block relation holds the two interior
  offsets split the payload into three consecutive regions
  `[+0x2C, offset_a)`, `[offset_a, offset_b)`, `[offset_b, end)`; their contents
  look different (f32, then mostly `0x1F`/`0x801F` words) but **no region is
  assigned a format or meaning**.
  **E-094 correction:** the offsets are **not** boundaries between arrays — in
  `em013.pac` slot 2 a uniform run of 230 u32 `0x400` straddles `offset_a`. The
  `regions` property is arithmetic on the two offsets, not a content claim.
* `offset_c` leaves the block in 708/1,561 — [UNKNOWN].
* `tools/dmc3/mod.py` exposes `ModBodyBlock`, `body_blocks`, the `blocks` field
  on `ModBodyDirectory` and the `BODY_BLOCK_*` constants.

#### E-094 update: the payload opens with `count` positions then `count` normals — structure [PARTIAL]

Reading a block's payload (`+0x2C`) as little-endian `f32[3]` triples, with
`count` taken from the descriptor (E-091/E-092), shows a leading vertex array:

```
payload + 0x00            count x f32[3]   coordinates        [INFERRED: positions]
payload + 0x0C*count      count x f32[3]   unit length        [INFERRED: normals]
```

* `em013.pac` slot 8 (block `@body+0x80`, descriptor `count = 36`): the first 36
  triples are arbitrary (`2.3638, -0.0, 0.0454`; `0.0, -1.7709, -0.7894`), the
  next 36 are unit length (`0.2224, 0.0, 0.9750`; `0.0, 0.7315-, 0.6818-`), and a
  run of 36 u32 `0x400` begins at `payload + 1008 = 28 * count` bytes.
* Census over **1,535** `ordered and in_block` record descriptors: 502 contain a
  run of >= 8 consecutive unit triples; 305 have it start at exactly `count`, 431
  within `count` ± 1, 418 with run length equal to `count`. The **689** blocks
  whose descriptor `count == 4` contain **no** such run — a different shape.
* The reading of the triples as *positions*/*normals* and the `0x400` run
  (a likely Q10 `1.0`, unproven) are **[INFERRED]**; the array lengths are exact
  on only 418/1,535 blocks, so the framing is [PARTIAL].
* `tools/dmc3/mod.py` exposes `unit_triple`, `block_positions`, `block_normals`,
  `normal_run`, `ModBodyBlock.normal_offset` and the `BODY_BLOCK_TUPLE_SIZE` /
  `BODY_BLOCK_NORMAL_*` constants. See **E-094**.

#### E-095 update: the 4-byte-per-vertex field after the normals is two u16s; the `0x400` run is not general — structure [PARTIAL]

E-094 read the four bytes per vertex after the normal array as one u32 and the
following array as `count` u32 `0x400` ("28 bytes per vertex"). Reading the bytes
as little-endian u16s gives, for `em013.pac` slot 8 `count = 36`, an attribute
array starting at `payload + 24*count`:

```
payload + 0x00            count x f32[3]   [INFERRED: positions]
payload + 0x0C*count      count x f32[3]   [INFERRED: normals]
payload + 0x18*count      count x u16[2]   per-vertex attribute  (this entry)
payload + 0x1C*count      count x u32      constant per block in 202/303
```

* Worked bytes at `body+0x40C`: `de 06 f1 05` → one u32 `0x05F106DE`, but the
  pair `(0x06DE, 0x05F1)`; then `(0x06DE, 0x0630)`, `(0x0783, 0x0634)`.
* Census (303 blocks with `normal_run == (count, count)`): the attribute
  u16-pair array is constant in only **3/303** (so it is per-vertex); low u16
  `< 0x1000` in 299/303, high u16 `< 0x1000` in 259/303. The next array
  (`payload + 0x1C*count`) is constant per block in 202/303, all-zero in 115/303
  and all-`0x400` in **2/303**.
* **[INFERRED]/[UNKNOWN]** the attribute pair is a per-vertex attribute
  (UV-consistent values, unproven); the next array's meaning is unassigned.
* **Correction to E-094:** the `0x400` run is a per-block value, not a format
  constant. `tools/dmc3/mod.py` exposes `block_attributes`,
  `ModBodyBlock.attribute_offset` and the `BODY_BLOCK_ATTRIBUTE_UNIT = 0x18` /
  `BODY_BLOCK_ATTRIBUTE_SIZE = 0x04` constants. See **E-095**.

#### E-096 update: the per-vertex record is 32 bytes and the descriptor's interior offsets are computed from `count` — structure [PARTIAL]

Reading the whole block tail on the **303** blocks with
`normal_run == (count, count)` (E-094) shows the E-095 "next array" is a
**4-byte-per-vertex value array**, and the descriptor's two interior offsets name
nothing at all — they are `count` arithmetic:

```
payload + 0x00            count x f32[3]   [INFERRED: positions]   (E-094)
payload + 0x0C*count      count x f32[3]   [INFERRED: normals]     (E-094)
payload + 0x18*count      count x u16[2]   per-vertex attribute    (E-095)
payload + 0x1C*count      count x u32      value array; single-valued per block in 202/303  [INFERRED]
payload + 0x20*count      fill tail        0x001F001F / 0x801F801F words  [UNKNOWN]
```

* **The record is 32 bytes.** No `0x1F`-fill word occurs before
  `payload + 32*count` on any of the 303 blocks (258 start the fill exactly
  there, 36 later, 9 carry no fill word). So `payload + 32*count` is a lower
  bound on the per-vertex data.
* **The interior offsets are count-derived [VERIFIED].**
  `descriptor +0x04 == payload + 28*count + 0x24` on **303/303**, and
  `descriptor +0x0C - descriptor +0x04 == 4*count` on **303/303**. `offset_a` is
  `0x24` bytes into the value array and `offset_b` is `0x24` bytes *past* the
  record — neither marks an array boundary.
* **Correction to E-093/E-094:** "the two interior offsets split the payload into
  three consecutive regions" (E-093) is wrong; E-094's `0x400` run is the value
  array. Why the `0x24` slack exists is **[UNKNOWN]**.
* Worked example `em013.pac` slot 1 (`count = 44`): positions `(14.2878, 165.8537,
  -7.5560)`, normals `(0.5088, -0.0501, -0.8594)`, attributes `(3719, 2370)`,
  value array `0x0C040800` x44, fill `0x801F801F 0x001F001F …`; the reader
  reproduces `value_offset = 0xF7C`, `offset_a = 0xFA0`, `offset_b = 0x1050`.
* `tools/dmc3/mod.py` exposes `block_values`, `fill_start`,
  `ModBodyBlock.value_offset` / `tail_offset` / `offset_slack` and the
  `BODY_BLOCK_RECORD_SIZE = 0x20`, `BODY_BLOCK_VALUE_UNIT = 0x1C`,
  `BODY_BLOCK_VALUE_SIZE = 0x04`, `BODY_BLOCK_OFFSET_SLACK = 0x24`,
  `BODY_BLOCK_FILL_WORDS` constants. See **E-096**.

#### E-097 update: the block tail ends with a `(body-offset, 0)` table; no u16 index buffer — structure [PARTIAL]

The bytes after the 32-byte-per-vertex record (`payload + 32*count`) are **not**
pure fill and hold no index buffer. On the **286** `MOD ` chunks (1,657
non-empty tails):

```
payload + 0x20*count      fill words (0x001F001F / 0x801F801F)      [UNKNOWN]
payload + 0x20*count + …  zeros, a small word (e.g. 0x36, 0x08)     [UNKNOWN]
… then an 8-byte-aligned table of (u32 body-offset, u32 0) entries  [UNKNOWN meaning]
```

* The tail is pure `0x1F` fill in **0 / 1,657** blocks. **1,305 / 1,657** carry a
  run of ≥ 2 `(offset, 0)` entries — a non-zero, 16-byte-aligned body offset
  followed by a zero u32 — with **2,619 / 2,619** targets landing inside a data
  block. [INFERRED] a block-level cross-reference table; what it references is
  **[UNKNOWN]**.
* The `0x40`-byte descriptor has no free index field: `+0x00`/`+0x20`/`+0x28`
  are zero on **1,665 / 1,665** records, and `+0x04`/`+0x08` are non-zero only on
  the E-093 anomaly records (17 and 37).
* No block payload read as `u16` is an index run bounded by `count`
  (**0 / 1,660**), and `offset_c` does not point at one (it reads as `f32`/vertex
  bytes). So block connectivity is **not** stored in-block as u16 indices.
  A sequential-triple winding test was inconclusive (237 / 313 clean blocks at
  ~50 % sign agreement; strips alternate winding) and is recorded in E-097 so it
  is not re-run.
* Worked example — `em013.pac` slot 1 descriptor 0 (`count = 44`), block
  `@body+0xA80`: the 132-byte tail ends `… 0x36, 0, 0, 0, (0x1100, 0),
  (0x1390, 0)`; both targets are inside block 1 (`@body+0x10B0`).
* `tools/dmc3/mod.py` exposes `block_tail`, `tail_entries` and the
  `BODY_BLOCK_TAIL_ENTRY_SIZE = 0x08`, `BODY_BLOCK_TAIL_MIN_VALUES = 2`
  constants. See **E-097**.


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
+0x15C  u16  0x0015 (21) on 123/123 — the first data record's tag (E-064)
+0x160  u16  0x000C — that record's discriminator, a per-record constant (E-064)
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

#### Data-section record preamble — [PARTIAL] (E-064)

The bytes at `+0x15C` are not a marker pair but the first of a stream of **tagged
u16 records**. Every record carries the constant `u16 0x000C` in its **third
slot**; verified on all 123 clips the section is laid out as:

```
lead records     4 u16: tag, arg, 0x000C, value          x 4 or 5
terminator       2 u16: 0x0000, 0x0000
count            u16                                    15..272, 81 values
tail records     5 u16: tag, arg, 0x000C, value, extra   x 4, 5 or 7
terminator       u16:   0x0000
```

| field | observation |
|---|---|
| lead tags | `0x15, 0x16, 0x18, 0x0B` (115 clips) or `0x15, 0x16, 0x17, 0x18, 0x0B` (8) |
| tail tags | from `{0x0B, 0x0F, 0x10, 0x1B, 0x1C, 0x1D, 0x1E}`; `0x0F`/`0x10` once each per clip |
| discriminator | `0x000C` in the third slot of every record, 123/123 |

`count` is **not** the frame count (`csHadesIntro` is 141 frames, `count` 72).
Every tag, `arg`, `extra` and `count` is **[UNKNOWN]**; the `0x8000 | n`
ids that recur in `lead[0x0B].arg` and `tail[0x1B].arg` are noted only. `[INFERRED]`
the discriminator is a per-record type/kind field, and the lead/tail shapes are two
groups of typed properties — unproven. The keyframe data that follows is the
remaining F9 gap; `eboot.bin`/`eboot.elf` is the route.

##### Record `value` fields are sub-block offsets — [VERIFIED] (E-065)

The last u16 of every lead and tail record (E-064's `value`) is an **offset
relative to the clip's data-section start** (`clip.offset + 0x15C`). Censused on
all 123 clips:

```
values strictly increase in file order                    123/123
every value is a multiple of 16                            123/123
values[0] == round_up(preamble byte length, 16)            123/123
data_start + value  <  clip.offset + clip.size             123/123
```

so the preamble is a directory of 16-byte-aligned sub-blocks starting
immediately after the preamble (the first value is the preamble's own byte length,
rounded up). Worked example `angryKratosWalk`: preamble length `0x5A` → first
value `0x60`; values `0x60 0x90 0x870 0xAF0 0xB30 0xFB0 0x1140 0x1150 0x1160`;
targets `0x5C30 … 0x6D30`, all below the clip's `end` (`0x96B4`). The largest
value stays inside the clip's `size` on all 123 clips. The meaning of every
sub-block, tag, `arg`, `extra` and `count` remains **[UNKNOWN]** — this fixes
where the sub-blocks are, not what they hold.

The reader is `ClipDataRecord` / `ClipDataPreamble` /
`parse_clip_data_preamble()` / `maybe_clip_data_preamble()` with
`discriminated_ok`, `tags_known_ok`, `values`, `word_count`, `byte_length`,
`increasing_ok`, `aligned_ok`, `first_offset_ok`, `data_targets()` and
`invariants()`; it is strict (returns `None` on a wrong discriminator, a missing
terminator or a truncated buffer) and asserts no field meaning.

##### The offsets name **typed sub-blocks** — [PARTIAL] (E-066)

Each offset names a sub-block, and the record's **tag types it**. Censused on all
123 clips (read-only), two relations hold:

| relation | result | note |
|---|---|---|
| tag-`0x16` sub-block opens with 128 u16 `0x30 * k` (`k = 0..127`, span `0x1800`) | **123/123** | the run stops exactly at index 128 every time |
| tag-`0x10` sub-block contains a *nested* preamble of the E-064 shape | **122/123** | exception `attCestusCrush` (`R_HERCULES.WAD`); nested offset 64..208 B, 16-byte aligned |

The tag-`0x16` sub-block is the only tag with a single 8-byte head across all clips
(`00 00 30 00 60 00 90 00`). The tag-`0x10` block is the last one (it runs to the
clip's `end`) and the largest; its nested preamble parses under E-064's strict
rules with at least 3 lead *and* 3 tail records. Worked example `angryKratosWalk`,
nested at `+0x90`: lead `(0x15,0x10,0x70) (0x16,0xD8,0x130) (0x18,0x78,0x7D0)
(0x19,0x08,0xB70) (0x0B,0x8022,0xB90)`, `count` `0x75`, five tail records.

**Meaning of every tag, and everything inside a sub-block, is [UNKNOWN]**, as is
why `attCestusCrush` differs. The reader is `ClipSubBlock` / `ClipSubBlocks` /
`parse_clip_sub_blocks()`, `tag16_prefix_length()`, `find_nested_preamble()` and
the `CLIP_DATA_TAG16` / `CLIP_DATA_TAG16_PREFIX_WORDS` (128) /
`CLIP_DATA_TAG16_STEP` (0x30) / `CLIP_DATA_TAG10` / `CLIP_DATA_NESTED_MIN_RECORDS`
(3) constants; `ClipSubBlocks` reports `tag16_prefix_ok` / `nested_ok` as evidence
only. The leaf keyframe/curve encoding is still the F9 gap.

##### The recursion is exactly two levels — [VERIFIED] (E-067)

Splitting the *nested* preamble with the same reader (E-064/E-065) shows the
nesting is shallow and bounded:

| quantity | result |
|---|---|
| data-section chains of length 1 | 1 (`attCestusCrush`) |
| chains of length 2 | **122/123** |
| chains of length ≥ 3 | **0** |

The level-2 preamble satisfies every E-065 offset invariant on 122/122 (strictly
increasing, 16-byte aligned, `values[0] == round_up(length, 16)`). Its tag
vocabulary differs from the outer level in two measured ways (both 123 clips):

* a lead tag **`0x19`** appears only at level 2 (`101/122` clips; shapes
  `0x15 0x16 0x18 0x19 0x0B` and `0x15 0x16 0x17 0x18 0x19 0x0B`);
* the level-2 tag-`0x16` sub-block opens with a `0x30 * k` run of **123** entries
  (114 clips) or **122** (8 clips), **never 128** — E-066's "128" is the outer
  level only.

Each tag-`0x16` sub-block, at either level, also carries a second table
immediately after the `0x30 * k` run: u16 values that strictly increase, are all
multiples of 16, and start at `0x20` in every outer block (123/123). The run
reaches `0x1800` (= `0x30 * 128`) or `0x3C00` before constant fill; its length
and meaning are [UNKNOWN].

The reader is `parse_data_section()` (the general form of
`parse_clip_sub_blocks()`), `ClipSubBlocks.end` / `ClipSubBlocks.nested_data_section()`,
`clip_data_sections()`, `tag16_offset_table()` /
`ClipSubBlock.tag16_offset_table`, and the constants
`CLIP_DATA_NESTED_LEAD_TAG` (0x19) / `CLIP_DATA_NESTED_LEAD_TAGS` /
`CLIP_DATA_NESTED_TAIL_TAGS` / `CLIP_DATA_MAX_DEPTH` /
`CLIP_DATA_SECOND_TABLE_FIRST` (0x20). Tag meaning and the leaf encoding remain
[UNKNOWN].

##### The u16 offset lists share a **0x30-byte stride** — [PARTIAL] (E-068)

Censusing the arithmetic residue of every u16 in the data-section sub-blocks on all
123 clips (read-only) shows the stored offsets all step by `0x30` (48 bytes):

| relation | result | note |
|---|---|---|
| every tag-`0x10` sub-block's **first** u16 `== 0x10 (mod 0x30)` | **245/245** | 154 `R_HADES.WAD` + 91 `R_HERCULES.WAD`; only the first word, the run is not uniform |
| the word after the tag-`0x16` continuation run `== 0x00 (mod 0x30)` | **245/245** | and is one of exactly `0x1710` / `0x1800` / `0x3C00` = `0x30 * {123,128,320}` |
| the tag-`0x16` `0x30 * k` prefix | residue `0x00` | by construction (E-066) |
| the tag-`0x16` post-prefix continuation | residue `0x20` | first value `0x20` (E-067) |

The three residues (`0x00`, `0x10`, `0x20`) are consistent with a **single
0x30-byte record stride** whose fields sit at `+0x00` / `+0x10` / `+0x20` —
**[INFERRED], unproven**; no field is assigned a meaning. The tag-`0x16`
continuation is the **first** residue-`0x20` run, not the whole set: 87/245
blocks carry further residue-`0x20` values later, so that remains [UNKNOWN].

The helpers are `stride_residue()` / `stride_offset_run()` and the constants
`CLIP_DATA_STRIDE` (0x30) / `CLIP_DATA_STRIDE_FIELDS` /
`CLIP_DATA_TAG10_RESIDUE` (0x10) / `CLIP_DATA_TAG16_CONTINUATION_RESIDUE` (0x20) /
`CLIP_DATA_CONTINUATION_TERMINATORS`, exposed through
`ClipSubBlock.first_word` / `first_word_residue` / `tag16_continuation` /
`tag16_continuation_terminator` / `tag10_residue_ok` / `tag16_terminator_ok` and
`ClipSubBlocks.tag10_residue_ok` / `tag16_continuation_ok`. The leaf keyframe
encoding is still the F9 gap.

##### The tag-`0x0F` sub-block is a channel offset table — [PARTIAL] (E-079)

Every one of `R_HADES.WAD`'s 77 clips carries **exactly one** tag-`0x0F` sub-block,
and its payload is a little-endian u16 **offset list** (8 / 24 / 32 / 40 entries,
i.e. 8..40 channels per clip). Censused read-only:

| relation | result |
|---|---|
| every entry `<= 0x1800` | **77/77** |
| every entry is the `0x1800` sentinel or `== 0x20 (mod 0x30)` | **77/77** |
| list is non-decreasing | 74/77 |
| last entry is `0x1800` | 76/77 |

`0x1800` is `0x30 * 128` — the span of the tag-`0x16` ramp (E-066) — and `0x20` is
one of E-068's three `0x30` residues, so the list reads as channel positions in the
shared 48-byte record array, `0x1800` acting as its end sentinel. The entry count is
a per-clip channel count and not a header field. Worked example `cshadesRip02IdleL`
at file `0xF0C60`, `50 00 00 18 00 18 ...` = `(80, 6144 x7)`.

##### Leaf payloads carry `0xCC` fill, so a size is a capacity — [PARTIAL] (E-079)

A run of two or more `0xCC` bytes (the MSVC uninitialised fill) occurs in **227 of
the 714** sub-block payloads; in **148** of those the run reaches the block's end.
Those blocks are exactly the **leaves**: tag-`0x0B` **62/77**, tag-`0x1B` **64/87**,
tag-`0x1C` **22/23**. The tag-`0x10` container holds `0xCC` in **76/77** clips but
never at its end — there the fill belongs to the blocks nested inside it. So the
size a preamble record implies for a **leaf** is a *capacity* and the live bytes end
at the fill; the same offset is not a data length for a tag-`0x10` container.

Two bounded negatives from the same census: the E-064 `count` field is **not** the
clip's frame count (equal on 1/77), and no tag-`0x1B` payload is a zlib/gzip, lzma
or bz2 stream (87/87), so the leaf is not simply compressed data.

The helpers are `u16_values()` / `fill_run_start()` / `channel_offset_list()` /
`channel_offset_ok()` and the constants `CLIP_DATA_CHANNEL_TAG` (0x0F) /
`CLIP_DATA_CHANNEL_RESIDUE` (0x20) / `CLIP_DATA_CHANNEL_LIMIT` (0x1800) /
`CLIP_DATA_FILL` (0xCC) / `CLIP_DATA_FILL_MIN_RUN` (2), exposed through
`ClipSubBlock.fill_run_start` / `live_length` / `offset_list` / `channel_offset_ok`
and `ClipSubBlocks.channel_blocks` / `channel_count` / `channel_offset_ok`. The leaf
keyframe encoding is still the F9 gap.

##### A channel entry is `0x20 + 0x30*k`, and `0x1800` pads the tail — [VERIFIED] (E-080)

E-080 re-censused the same list over **123** clips (77 `R_HADES.WAD` + 46
`R_HERCULES.WAD`), which corrects three E-079 numbers and fixes the arithmetic:

| relation | result |
|---|---|
| every non-sentinel entry is exactly `0x20 + 0x30*k`, `k` in 1..126 | **123/123**, 0 violations |
| list carries a non-terminal `0x1800` (tail padding) | 116/123 |
| list length (capacity) is 8 / 16 / 24 / 32 / 40 | 18 / 2 / 8 / 71 / 24 clips |
| *live* entry count (below the sentinel) | 1..36, modes 27 (28), 26 (19) |
| list is non-decreasing | 120/123 |
| live count is odd (so never a start/end pair table) | 65/123 |

So E-079's "**8..40 channels per clip**" is the list's **capacity**; the live
channel count is `channel_live_count`, and `k = 0` / `k = 127` are never
referenced. Over all 123 clips only **36 distinct `k`** occur —
`{1, 8, 10..12, 16..30, 39..45, 52, 59..64, 89, 126}` — most used by ~100 clips,
so a clip's channels are a **subset of a fixed 36-slot universe** (the clusters
`16..30` and `39..45` are [INFERRED] bone ranges). The `(start, end)` pair reading
is **[DISPROVEN]** (odd live counts) and "non-decreasing" is **[DISPROVEN]** as a
rule (three lists begin out of order: `csHadesIntroStruggle`, `csHadesIntroFail`,
`csHadesKnifeKillTug2`).

The helpers are `channel_index()` / `channel_live_values()` / `channel_index_set()`
and the constants `CLIP_DATA_CHANNEL_FIELD_OFFSET` (0x20) /
`CLIP_DATA_CHANNEL_LAST_INDEX` (126) / `CLIP_DATA_CHANNEL_CAPACITIES`
(`(8, 16, 24, 32, 40)`), exposed through `ClipSubBlock.channel_live_values` /
`channel_indices` and `ClipSubBlocks.channel_live_count` / `channel_indices`.

---

## 8. DMC3 HD `dmc3.exe` — PE file↔RVA mapping and reference scanning (E-069, E-070)

The DMC3 formats were decoded from bytes up to the point where engine ground truth
is required (E-050/E-051). That ground truth is on disk: `dmc3.exe` (6,356,432 B)
in the install root is a normal, unpacked x86-64 PE.

```
MZ;  e_lfanew 0x138;  "PE\0\0";  machine 0x8664;  8 sections
PE32+ optional magic 0x20B;  image_base 0x140000000
AddressOfEntryPoint (RVA) 0x34615C
.text  RVA 0x1000  vsz 0x34DD4E  raw 0x400    rawsz 0x34DE00  ch 0x60000020
.rdata RVA 0x34F000 vsz 0x203368 raw 0x34E200 rawsz 0x203400 ch 0x40000040
.data  RVA 0x553000 vsz 0x81F1B8 raw 0x551600 rawsz 0x86000  ch 0xC0000040
.pdata .gfids .tls .rsrc .reloc follow
```

Only `.text` is executable. File↔RVA mapping is
`rva = section.virtual_address + (offset − section.raw_offset)`; the image base
does not enter it, because a RIP-relative displacement is base-independent.

The reference method is the one E-056 used for `eboot.elf`, applied to PE
sections: a RIP-relative `lea`/`mov` operand is `[REX 0x40..0x4F]` `8D|8B`, a
ModRM with `(modrm & 0xC7) == 0x05`, then `disp32`; the target RVA is
`insn_rva + insn_len + disp32` (`insn_len` 7 with a REX prefix, 6 without). On
this image the scan finds 19,648 such instructions targeting 4,482 distinct RVAs.

**Verified result (E-069).** A resource-extension table sits at `.rdata` RVA
`0x5071D0` (`.mot .MOT .mcv .MCV .cam .CAM`), each string referenced once by a
`lea` from a tight `.text` cluster (`0x2E01D2`, `0x2E01EB`, `0x2E0204`,
`0x2E0236`). `0x2E01D2` is `48 8D 15 F7 6F 22 00` = `lea rdx, [rip + 0x226FF7]`
→ `0x5071D0`, immediately followed by a `call`. **Negative:** `.pac`, `.tm2`,
`pl021.pac`, `GDataX360.afs` and `endof.afs` occur in the image but have **zero**
RIP-relative references — file names are table data, as with GoW3's `.wad` (E-063).

`[INFERRED]`: the cluster is an extension→handler dispatch and the MOT handler is
reachable from it. `[UNKNOWN]`: what the code does past the `lea`/`call`, and every
F1/F4 field it would settle. Reader: `tools/dmc3/pe.py` (`PeImage`, `PeSection`,
`PeError`, `find_all()`, `rip_relative_references()`, `references_to_string()`).

### 8.1 What the extension cluster really is (E-070) — the [INFERRED] dispatch is **corrected**

Reading the code at `0x2E01D2` (read-only) shows the cluster is **not** an
extension→MOT-handler dispatch. `0x2E01D2` is inside a function at `0x2E01A0`
that **classifies and registers files by extension**: for each candidate string it
`strstr`s the extension (the import at IAT `0x34F3D0` resolves to `strstr`), and on
a hit copies two 32-byte names into a 1024-entry registry and stores a numeric
**type id**. The extension families and their ids:

| extension (any case) | type id | insert handler RVA |
|---|---|---|
| `.mot` / `.MOT` | 0 | `0x2E0598` |
| `.mcv` / `.MCV` | 1 | `0x2E051B` |
| `.cam` / `.CAM` | 2 | `0x2E049B` |
| `.hid` / `.HID` | 3 | `0x2E041B` |
| `.clt` / `.CLT` | 4 | `0x2E039A` |
| `.tsc` / `.TSC` | 5 | `0x2E02FA` |

Every extension is tested by `strstr`, so the case variants are redundant
(`.MOT` matches the `.mot` test). The registry context block is:

```
+0x0000  u32              entry count (cap 0x400 = 1024)
+0x8008  char nameA[1024][0x20]
+0x10008 char nameB[1024][0x20]
+0x18008 u8   flags[1024]
+0x18408 u32  type[1024]          (0..5 per the table above)
```

`0x2E0150` resets it (`count = 0`, `type[i] = 0xFFFFFFFF`, name/flags zeroed);
`0x2E0060` looks an entry up by **both** names (`strcmp` on `nameA` and `nameB`,
returning the index or `-1`); `0x2E0020` is the insert-with-dedup wrapper
(`lookup`, else `0x2E01A0`); `0x2E0130` returns `&nameA[index]`. Consumers that
look a name up and then resolve a resource are at `.text` `0x2D6933`, `0x2D77A2`,
`0x2DA173`, `0x2DA263`, `0x2DA336`.

**Consequence for F4/F1.** This cluster is a *file registry*, not the byte-level
decoder, exactly as GoW3's `WAD_` references reached name registration rather than
the record dispatcher (E-063). The MOT decoder itself is still `[UNKNOWN]`; the new
lead is to follow the **type id** (`0` for `.mot`) from this registry into its
consumer.

### 8.2 Limited instruction decoding (E-070)

`PeImage.reference_context(rva, max_instructions=4)` decodes the small set of
forms a string-reference site uses — RIP-relative `lea`/`mov`, `mov r32, imm32` /
`mov r64, imm64`, `call rel32` — and stops at the first unrecognised byte, so it
returns a *prefix* rather than a guess. `string_reference_contexts(needle)` applies
it to every reference of a string. This mirrors `gow3.eboot` (E-063). Worked
example on the real image: `string_reference_contexts(b".mot\0")` returns one
context at `0x2E01D2` (`lea rdx, [rip+0x226FF7]`, target `0x5071D0`); the following
`49 8B C8` (`mov rcx, r8`) is outside the set, so the context is length 1 — the
numeric constants of the registry are set a few bytes further in, at the handler
targets above.

### 8.3 The PAC chunk tags are absent from the engine; the asset-name pool (E-076)

**Negative [VERIFIED] (E-076).** The four-byte chunk tags of section 1.1 occur
**zero** times in the whole 6,356,432-byte image, as data or as `.text`
immediates: `MOD `, `SHW `, `PAC\0`, `PNST`, `;RID`. `MOT\0` occurs once, at
`.rdata` `0x5071D9` — the tail of the uppercase extension `.MOT` in the
E-069/E-070 table, not a chunk tag. **Consequence:** the engine cannot be locating
chunks by comparing these ASCII tags; the strongest remaining candidates are the
**PAC slot id** (section 1, "a slot is a logical id") and the asset **name**.

**The asset-name pool [PARTIAL] (E-076).** `.rdata` RVA `0x35D640` begins a pool of
NUL-terminated printable-ASCII names, each padded to the next **8-byte** boundary.
A full walk yields 4,056 entries (last `st240_effect.pac` at `0x36E7A0`), 3,397 of
them `.pac`; the `name+NUL → next` gaps are `{16: 3409, 24: 642, 8: 4}`. It holds
this project's own names verbatim:

```
0x363098  pl021.pac
0x3645F0  pl021_00_0.pac … 0x364870  pl021_00_9.pac
          (interleaved with id4516..id4525.pac, id516..id525.pac,
           m05_b00_msg_eng.txt, m05_c00_msg_frn.txt, …)
```

Exactly five RIP-relative `lea`/`mov` targets land in the pool and four are entry
starts — `icon.sys`, `icon00.ico`, `icon01.ico`, `icon02.ico` (memory-card icons);
**no `.pac` pool entry is referenced this way**, so the pool base is resolved
indirectly. Reader: `PeImage.walk_string_pool(rva, alignment=8)` /
`read_cstring(rva)` / `section_of_rva(rva)`. The pool's record framing beyond the
string alignment, and the second name cluster at `0x4EB36B..0x505031`, stay
[UNKNOWN].

### 8.4 The name pool is consumed by an indexed `.data` pointer table (E-077)

**Negative, correcting E-076's "indirect pool base" framing [VERIFIED] (E-077).**
There is **no dedicated pool-base global**: exactly one 8-byte absolute pointer to
the pool base `0x14035D640` exists in the whole image, at `.data` `0x55A570`, and
it is merely *one element of the table below* — not a `g_pool` variable. So the
pool is not reached through a stored base pointer.

**The table [VERIFIED] (E-077).** `.data` RVA `0x553050` begins a contiguous run
of **8-byte absolute pointers** (``image_base + rva``), each to a string in the
E-076 pool. `PeImage.pointer_array(0x553050)` walks **4,039** entries and stops at
the first NULL (`.data` `0x55AE88`); a second run of 19 entries continues at
`0x55AE90`; the block ends at `0x55AF28`, after which non-pointer data (UTF-8
text) begins. Verbatim head (slot index → name):

```
0  pl000.pac      1  pl011.pac    2  pl013.pac    3  pl015.pac
4  pl016.pac      5  pl018.pac    6  pl001.pac    7  pl002.pac
8  pl021.pac      9  pl023.pac   10  pl026.pac   11  pl005.pac
```

Of the 4,059 non-null slots, **4,055 are E-076 pool entry starts**; the four
exceptions are `at.ptx` (`0x3679E4`), `Video/` (`0x3631DC`), a `.data` pointer
(`0x5D9DC0`) and `0x36C355`. The block is a near-permutation of the pool, ordered
by some engine id rather than by address.

**The consumer [VERIFIED] (E-077).** The literal `0x553050` occurs **exactly once**
in the image — as the `disp32` at `.text` `0x334F1`
(`PeImage.find_all(b"\x50\x30\x55\x00") == [0x334F1]`). The surrounding code is a
tail-callable accessor:

```
0x334E1  48 63 CA              movsxd rcx, edx
0x334E4  48 8D 05 15 CB FC FF  lea    rax, [rip-0x334EB]   ; -> RVA 0 = module base
0x334EB  33 D2                 xor    edx, edx             ; clear the id for the next call
0x334ED  48 8B 8C C8 50 30 55 00  mov  rcx, [rax + rcx*8 + 0x553050]
0x334F5  E9 F6 FE FF FF        jmp    ...
```

So the engine addresses the pool as
``[image_base + 0x553050 + 8*index]`` and returns the ``char*`` name for
``index``. This is why the RIP-relative scanner missed it: the base is an
**addressing displacement**, not a RIP-relative operand — the same shape as
E-069/E-076's "file names are table data". Reader:
`PeImage.absolute_pointers_to(rva)` / `PeImage.pointer_array(rva)`.

**Inference (marked, unproven).** The `.data` block is an **asset-name table
indexed by an integer id**; `0x334E1` is its resolver `name(id)`. Whether `index`
is the PAC slot id of section 1, or a separate asset id, is open.

**Correction recorded.** The `.data` globals at `0x553000..0x55304F` are an
**unrelated** state block (u32 counters/flags: `0x2AC78` reads `[0x553000]`,
`0x2ACA9` writes `[0x553004]` and `[0x553000]=-1`), **not** the table's base — a
working hypothesis of this slice that the bytes refute.

**Unknown.** The index semantics and its caller; the meaning of the four non-pool
targets and of `0x55AF28` (→ `0x1405D9DC0`); whether the block is one array or
several concatenated (NULL at `0x55AE88`, 19-entry run at `0x55AE90`). The
byte-level MOD/MOT decoders (F1/F4) are unchanged.

### 8.5 The table is four categories indexed by a u16 pair (E-078)

**Supersedes part of §8.4.** E-077's "index semantics … [UNKNOWN]" is resolved:
the accessor is one arm of a **four-way category dispatcher** and the reference is
a `(category, index)` pair, not a single id.

**The dispatcher [VERIFIED] (E-078).** `.text` RVA `0x33480` switches on `ecx`
(0 → `0x553050`, 1 → `0x55A920`, 2 → `0x55ADF0`, 3 → `0x55AE90`; anything else
returns 0) and every arm loads `[module_base + 8*edx + base]`, i.e.
`name = table[ecx][edx]` with `edx` (u16) the index.

**The categories [VERIFIED] (E-078).** The bases divide the pointer runs as

| category | base | count | names (head → tail) |
|---|---|---|---|
| 0 | `0x553050` | 3866 | `pl000.pac`, …, `pl021.pac` (index 8), …, `endof.afs` |
| 1 | `0x55A920` | 154 | `Battle_00.adx`, …, `Versil_01..03.adx`, `ZZZ.adx` |
| 2 | `0x55ADF0` | 19 | `Title.sfd`, …, `ZZZ.sfd` |
| 3 | `0x55AE90` | 19 | `m99_s00.sfd`, …, `GData.afs/`, `Video/`, `afs/sound/`, `SAVEDATA/` |

Category 2 ends at the NULL at `0x55AE88`; category 3 is the 19-entry run after it
and ends at `0x55AF28`. Reader: `dmc3.assets.resolve_name(image, category, index)`.

**The index source [VERIFIED for one caller] (E-078).** The dispatcher's single
direct caller is `.text` `0x2EF7F7` in `0x2EF790`, which indexes an array of
**0x88-byte records** and, for a record with dword type `1`, passes
`[record+4]` (u16 category) and `[record+6]` (u16 index). Types `2`/`3` branch to
an inline name (`record+0x10`) and a function-pointer dispatch (`record+8`),
[INFERRED] — read from that one caller only.

**Unknown.** Where the 0x88-byte record array is and who builds it; whether
category 0's index is the PAC/`plNNN` id or a separate asset id; and the
byte-level MOD/MOT decoders (F1/F4), which this resource-loader route does not
itself reach.

### 8.6 The dispatcher opens the resolved name; the loader cluster is file I/O (E-082)

**Corrects E-078 (dispatcher return type) and closes the E-078/E-081 load-path
lead.** `.text` `0x33480` does not return a `char*` name: all four arms
`jmp 0x333F0`, which **opens** the resolved name and returns a **0x50-byte handle
struct** (`+0x01` open flag, `+0x08` file size u32, `+0x2C` underlying handle,
`+0x30` base offset) [VERIFIED]. So `0x33480` reads as
`open_asset(category, index)`. `dmc3.assets.resolve_name` (the table read) is
unchanged.

The surrounding primitives are the engine's **file I/O** layer [VERIFIED]:

| RVA | role |
|---|---|
| `0x333F0` | `open(name)` -> handle (32-bit size via `0x2F9F0`, handle via `0x2FCA0`) |
| `0x333C0` | `blocks(handle)` = `ceil([handle+8] / 0x800)` |
| `0x33500` | async read of `edx*0x800` bytes at `[handle+0x30]+[handle+0xC]`; sets the shared `.data` state word to 2 then 3/4 |
| `0x335A0` | read callback: `[handle+0xC] += bytes`, sets state 3/4 |
| `0x33390` | `close(handle)`: `0x2FC80([handle+0x2C])` then free |
| `0x333E0` | returns the shared state word (2 = in flight, 3 = done, 4 = error) |

`PeImage.call_sites` shows the whole direct-call consumer set is one cluster at
`.text` `0x2EF620..0x2EF9C7`: `0x2EF620` `file_size(name)` (no direct caller ->
indirect), `0x2EF750`/`0x2EF790` the multi-state streaming worker of E-078, and
`0x2EF920` `load_file(name, dst)` (synchronous). `load_file`'s two direct callers
(`0x1B80AC`, `0x1B871F`) hand the loaded buffer to a content parser at
`0x1B7C70`/`0x1B7D10` -- the next engine lead.

**Inference (marked).** The `(category,index)` route ends at an open file handle;
the MOD/MOT byte decoders are downstream of the loaded buffer and are still
**[UNKNOWN]**.

### 8.7 `load_file`'s consumers are text parsers; a `.lst` name resolves to a `.pac` (E-083)

**Corrects E-082's "content parser".** The two functions E-082 named as the
file-content parser at `0x1B7C70`/`0x1B7D10` are **text tokenizers**, not binary
container parsers [VERIFIED]:

* `.text` `0x1B7C70..0x1B7D04` (`_type_token`): a 3-state scan over a
  NUL-terminated string. State 0 treats `/` (`0x2F`) and CR (`0x0D`) as line
  markers and `#` (`0x23`) as the start of a comment; for **any other** byte it
  writes the literal **`"PAC"`** (`50 41 43`) into a 4-byte output buffer.
  State 1 clears on LF (`0x0A`); state 2 (entered on `#`) copies the following
  bytes into the same output, up to 4 or until LF. An input with no such byte
  also yields `"PAC"`. The literal and the state transitions are [VERIFIED];
  what consumes the 4-byte token is [UNKNOWN].
* `.text` `0x1B7D10..0x1B7E5C` (`_count_tokens`): scans the same buffer, counts
  line/word breaks (separator bitmask `0x800800002000` = CR, ESC, `#`) and
  copies one token of up to `0x100` bytes onto the stack; returns the count.

**The surrounding cluster is a `.lst` -> `.pac` name resolver** [VERIFIED].
`0x1B7FD0..0x1B82B5` (and the parallel `0x1B85C0..0x1B8C98`) load a named text
file through the synchronous `load_file` (`0x2EF920`), tokenize it, and per
token:

* a token exactly equal to `"dummy"` (string RVA `0x4DC4D8`) is skipped;
* a token whose extension is exactly `"lst"` (string RVA `0x4DC4E0`) has the
  extension overwritten **in place** with `"pac"` (`0x1B81F9 mov dword
  [..], 0x636170` = `70 61 63 00`) to form `<base>.pac`, which is then probed
  with `file_size` (`0x2EF620`);
* the resulting size (rounded up to 64) is accumulated into the return value;
  the alternative parser `0x1B7FD0` runs on the `.lst` text when the `.pac`
  is absent (`file_size` <= 0).

`0x1B7E60..0x1B7F4E` is a third parser the two functions share; `"%s%s"`
(`0x36F4B0`) builds a name. `.pdata` fixes every function boundary above.

**Refinement of E-082 [VERIFIED].** `0x2EF620`'s name argument is **`rdx`**, not
`rcx`: the prologue (`0x2EF640 mov r9, rdx`, `0x2EF646 mov rcx, rdx`) strcpies
from `rdx`. E-082's `file_size(name)` did not name the register.

**Consequence for F1/F4.** The synchronous `load_file` route serves **text**
files, so it does not reach the binary MOD/MOT payload decoders. E-082's
[INFERRED] "content parser ... the container-parse step ahead of the MOD/MOT
decoders" is therefore **falsified**. The `.lst` -> `.pac` substitution is the
engine's *name resolution* for these references (consistent with E-078's
`(category,index)` open path), not a payload decoder; the MOD/MOT decoders
remain [UNKNOWN].

**Tooling.** `PeImage.functions()` / `PeImage.function_containing(rva)` read the
`.pdata` `RUNTIME_FUNCTION` table (12-byte `(begin, end, unwind)` entries,
`[start, end)` RVAs; **12,235** entries on the real image) so a reference site
is attributed to its function without a disassembler. `dmc3.pe.PeFunction` is
exported from `dmc3`.




