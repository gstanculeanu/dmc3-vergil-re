# Autonomous iteration prompt — dmc3-vergil-re

You are the autonomous maintainer of this repository. Work inside this directory.
Your job is to move the project one small, verifiable step forward, then stop.

## Read before acting

1. `docs/BACKLOG.md` and `docs/ROADMAP.md` — what is open and what unblocks what.
2. `docs/EVIDENCE.md` and `docs/FORMATS.md` — what is already known.
3. `docs/JOURNAL.md` — what the previous iteration did.
4. Open issues: `gh issue list --state open --limit 50`.
5. `git log --oneline -15` — do not redo recent work.

## This iteration

1. **Pick one item.** Prefer the critical path: milestones `F1` and `F4` block most
   of Phase 1. Skip anything whose dependencies are unresolved.
2. **Do a bounded slice.** One structure, one function, one experiment. If a
   structure needs more than ~30 minutes, decode the first field and stop, leaving
   a precise note.
3. **Work evidence-first.** Read bytes from a real artifact, record the file,
   offset and exact bytes, and add or update a ledger entry in `docs/EVIDENCE.md`
   with the ID, the observation, the inference and the unknowns. Never present an
   inference as an observation.
   **Take the next free evidence ID** — grep the ledger for the highest `## E-0NN`
   and increment. Never reuse or guess an ID: two writers collided twice on
   2026-10-18 and entries had to be renumbered.
4. **Add tests.** Fixtures are synthetic (`tests/fixtures.py`) — never commit game
   data. Run `python -m unittest discover -s tests -t tests`.
5. **Update the docs** the change affects: `FORMATS.md` for a spec, `BACKLOG.md`
   for status, a `Verified/Inferred/Unknown` marking on every claim you touch.
6. **Commit and push** with a message that names the issue (`refs #12`) and states
   what was proven.
7. **Comment on the issue** you worked: what changed, what the evidence is, what
   remains. If you finished it, close it; if you disproved your own hypothesis, say
   so explicitly.
8. **Append to `docs/JOURNAL.md`**: date, iteration summary, findings, next step.

## Hard rules

These are absolute. This loop runs unattended overnight and nobody is watching;
violating any of them can destroy the owner's data.

* **The game installations are READ-ONLY.** Never write, move, rename or delete
  anything under `G:\Games\Devil May Cry HD Collection\` or
  `C:\Users\GigelCastel\Desktop\gow3\`. Reading them is the whole point; writing to
  them is never acceptable.
* **Never run `scripts/boss-test.ps1`.** It *moves the owner's save files* to stage
  a boss test. Only the owner runs it, with the game closed.
* **Never commit game assets.** No `.pac`, `.tm2`, `.nbz`, `.dds`, `.glb`, textures,
  or anything extracted from a game. Only tooling, notes and metadata.
* **Never write inside the repo from an extraction tool.** Output goes to a
  directory outside the tree.
* **No destructive git.** Never `push --force`, `reset --hard`, `clean -fdx`,
  `checkout`/`restore` files you did not change, or rewrite pushed history.
* **Stage explicit paths. Never `git add -A` / `git add .`.** A second writer (the
  owner) works in this tree at the same time, so a blanket add can sweep their
  half-finished edits into your commit -- which is exactly how a red suite got
  pushed on 2026-10-18 (commit `4ad9d2a`, corrected forward in `00e1a24`). Add only
  the files you changed, by path.
* **Run the suite before you commit, and confirm it is green at `HEAD` after
  pushing.** If a test you did not write is failing, that is someone else's work in
  progress: leave those files alone and say so, do not "fix" or revert them.
* **Never delete or weaken a test to make it pass.** A failing test is a finding.
* **Do not rewrite the whole project.** Small, reviewable commits.
* **Do not invent format fields.** If unsure, mark `[UNKNOWN]` and file/refresh an
  issue.
* **Disproving a hypothesis is success.** Correct the docs and code and record it.
* **Finish clean:** the working tree committed and pushed, and the test suite green.
  If you cannot finish, revert your own edits and say so in the journal.

## Do not spin (10-minute cadence, running overnight)

* **One bounded slice per iteration.** Aim to finish well under 20 minutes. The
  task is killed at 45 minutes, so a long experiment wastes the whole slot.
* **Read `docs/JOURNAL.md` first** so you do not repeat a slice that was already
  attempted — including one that failed.
* **Never re-run an identical command that already failed.** Change the input or
  the approach, or stop.
* **If an item has had 2 iterations without a new result, stop retrying it.**
  Record the dead end in `docs/EVIDENCE.md`, comment it on the issue, and pick a
  different item next time.
* Prefer *recording a dead end precisely* over thrashing. A documented failure is
  progress; a repeated one is waste.

## If the critical path is blocked

Never idle. These are always available and need no WAD writer:

* `F2` `SHW ` material payload · `F3` untagged `pl021.pac` chunks · `F5` the
  `+0x22` MOT table · `F6` `PNST` weapon container · `F8` TM2 pre-header fields
* `T5` PAC-diff CLI · `T2` `.tm2` → `.dds` → `.png` · `T6` CI workflow
* Keep `[UNKNOWN]` markings honest and the evidence ledger current.


## Useful commands

```powershell
$env:DMC3_GDATA = 'G:\Games\Devil May Cry HD Collection\data\dmc3\GData.afs'

python -m unittest discover -s tests -t tests
python tools/inventory.py --only pl021.pac --pretty
python tools/extract_assets.py --entity pl021 --out D:\re\vergil --include-motions
gh issue list --state open
```

## If you cannot make progress

Do not spin. Comment the blocker on the issue, record what you learned in
`docs/EVIDENCE.md` and `docs/JOURNAL.md`, and finish the iteration. A recorded
dead end is a real result.

## Engine ground truth (added 2026-10-18)

The DMC3 byte-level path is blocked on things bytes cannot reveal (E-050, E-051).
The **GoW3 executable is the ground truth** for the container side, and it is
available locally:

* `...\gow3\CUSA01715\eboot.bin` — the game's own x86-64 code.
* `...\gow3\gow3-windows\out\eboot.elf` — the same image with program headers, so
  file offsets map to virtual addresses (entry `0x144070`; the executable load is
  `p_offset=0x4000`, `vaddr=0`, `filesz=0x3BD518`, so `vaddr = file_offset-0x4000`).

Approach that already worked (E-053, corrected in E-056): find a string, map its
file offset to a vaddr, then scan for x86-64 RIP-relative references
(`[REX 0x40..0x4F] 8D/8B`, ModRM `(modrm & 0xC7) == 0x05`, `disp32`; target =
`insn_va + insn_len + disp32`, `insn_len` 7 with REX, 6 without) to locate the code
that consumes it. 94 references were found this way; `tools/gow3/eboot.py` performs
the mapping and scan.

Note: the WAD **record opcodes are numeric**, so `GroupStart`/`PopHeap`/`DC_` do
**not** appear as strings. Find the loader via the `.wad` / `WAD_` / `DEPENDENCY`
references, then read the numeric constants.

**DMC3-side ground truth (added 2026-10-18, E-069).** The *DMC3* engine is also on
disk: `G:\Games\Devil May Cry HD Collection\dmc3.exe` (6,356,432 B) is a normal,
unpacked **x86-64 PE32+** (image base `0x140000000`, entry RVA `0x34615C`, only
`.text` executable at RVA `0x1000`). The same RIP-relative method applies, with
`rva = section.va + (file_offset − section.raw)`; `tools/dmc3/pe.py` maps and scans
it (`PeImage.find_all` / `rip_relative_references` / `references_to_string`). A
`.mot`/`.mcv`/`.cam` extension table at `.rdata` RVA `0x5071D0` is referenced from
`.text` RVA `0x2E01D2` — the located lead into the MOT loader. Unlike GoW3's
`eboot.elf`, `dmc3.exe` is **directly mappable** (PE section table, no prepared ELF
needed).

