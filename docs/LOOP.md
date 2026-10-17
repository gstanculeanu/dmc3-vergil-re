# Autonomous agent loop

The project runs a **fresh agent every 10 minutes**, each starting a new OpenCode
session, to make bounded progress without a human in the loop.

## What it does

A Windows Scheduled Task named **`dmc3-vergil-re-loop`** runs
`scripts/agent-loop.ps1` every 10 minutes. That script:

1. Takes an exclusive lock so two iterations never overlap (a stale lock from a
   killed run is detected and cleared).
2. Starts a **new** OpenCode session with `opencode run --auto` and the prompt in
   `scripts/agent-prompt.md`.
3. Tees the whole session to `logs/loop-<timestamp>.log`.

Because each invocation omits `--continue`, every iteration is a brand-new agent
with fresh context — as requested.

## Install

```powershell
# register (every 10 minutes, runs as the current user, no admin needed)
powershell -ExecutionPolicy Bypass -File scripts/register-loop.ps1

# check
schtasks /Query /TN dmc3-vergil-re-loop /V /FO LIST

# run one iteration by hand
powershell -ExecutionPolicy Bypass -File scripts/agent-loop.ps1

# remove
powershell -ExecutionPolicy Bypass -File scripts/unregister-loop.ps1
```

## Tuning

| Want | Do |
|---|---|
| different cadence | `scripts/register-loop.ps1 -Minutes 30` |
| a specific model | `scripts/register-loop.ps1 -Model 'opencode-go/deepseek-v4.1-flash'` |
| different instructions | edit `scripts/agent-prompt.md` (picked up on the next tick) |
| pause without removing | `schtasks /Change /TN dmc3-vergil-re-loop /DISABLE` |
| resume | `schtasks /Change /TN dmc3-vergil-re-loop /ENABLE` |
| several iterations back to back | `scripts/agent-loop.ps1 -Iterations 3` |

## Overnight hardening (2026-10-18)

Two changes so an unattended night is safe and productive.

**Task settings** (applied with `Set-ScheduledTask`):

| Setting | Value | Why |
|---|---|---|
| `StartWhenAvailable` | `True` | a missed trigger is caught up instead of skipped |
| `ExecutionTimeLimit` | `PT45M` | **was `PT72H`** — one hung iteration would have held the lock and blocked *every* tick for the rest of the night |
| `MultipleInstances` | `IgnoreNew` | no overlap (the script's own lock is the second layer) |
| trigger | repeat every `PT10M` | unchanged |

Sleep is already disabled on this machine (`STANDBYIDLE`/`HIBERNATEIDLE` = 0 on both
AC and DC), so no wake setting is needed.

**Prompt hardening** in `scripts/agent-prompt.md`, because the loop has repo write
access and nobody is watching:

* the game installations are **read-only** — never write to
  `G:\Games\Devil May Cry HD Collection\` or `...\Desktop\gow3\`;
* **never run `scripts/boss-test.ps1`** — it moves the owner's save files, so only
  the owner runs it;
* no destructive git (`push --force`, `reset --hard`, `clean -fdx`, rewriting
  pushed history);
* never delete or weaken a test to make it pass;
* must finish committed, pushed and green, or revert its own edits and say so.

**Anti-spin rules**, because a 10-minute cadence overnight will happily repeat a
failed approach forever:

* read `docs/JOURNAL.md` first so an already-attempted slice is not repeated;
* never re-run an identical command that already failed;
* **if an item has had 2 iterations without a new result, stop retrying it** —
  record the dead end and move on;
* a documented dead end is progress; a repeated one is waste.

A "if the critical path is blocked" list was added too, so there is always
available work (`F2`, `F3`, `F5`, `F6`, `F8`, `T2`, `T5`, `T6`) that needs no WAD
writer.

## Fixed: the loop exited 1 and never ran (2026-10-17)

**Symptom.** The scheduled task fired every 10 minutes but reported `Last Result: 1`
and never created `logs/` — so no agent ever ran and no commits were produced.

**Root cause.** `agent-loop.ps1` used `$PSScriptRoot` **inside its parameter
defaults**:

```powershell
param(
    [string] $RepoDir    = (Split-Path -Parent $PSScriptRoot),   # <-- empty!
    [string] $PromptFile = (Join-Path $PSScriptRoot 'agent-prompt.md')
)
```

When a script is launched with `powershell -File` — which is exactly what Task
Scheduler does — `$PSScriptRoot` is **not yet populated while parameter defaults
are being evaluated**. `Split-Path -Parent ''` therefore threw
`Cannot bind argument to parameter 'Path' because it is an empty string`, before
line 32 (which creates `logs/`) could run. The failure was instant, which is why
there was no partial log either.

**Fix.** Defaults are now empty and the script directory is resolved in the
**body**, after binding:

```powershell
$scriptDir = $PSScriptRoot
if (-not $scriptDir) { $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }
```

The same guard was applied to `boss-test.ps1` and `register-loop.ps1`, which used
`Split-Path -Parent $PSScriptRoot` inside functions and in the body.

**Verification.**

```powershell
# must exit 0 and create logs/
powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File scripts/agent-loop.ps1 -Iterations 0

# the headless call the loop makes must work
powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "& opencode run --auto 'Reply with exactly: LOOP-OK'"
```

Lesson recorded because it is easy to reintroduce: **never use `$PSScriptRoot` in a
parameter default in a script that Task Scheduler will run.**

## Second failure mode: the agent outlives the pipeline (2026-10-17)

After the `$PSScriptRoot` fix the script ran but still exited 1 with a **0-byte log**:

```
opencode.exe : [0m
  + FullyQualifiedErrorId : NativeCommandError
```

**Cause.** Windows PowerShell 5.1 wraps a native command's **stderr** as a
`NativeCommandError`. With `$ErrorActionPreference = 'Stop'` plus `2>&1` that
becomes a *terminating* error — so the harmless ANSI escape `opencode` emits on
stderr killed the pipeline, and `Tee-Object` never wrote a byte.

**Fix.** Relax the preference only around that call, then restore it. The script
also now always `exit 0` once its iterations have been attempted, logging the
agent's exit code instead — the task's job is to *run* an iteration, not to
guarantee the agent had a good round. Otherwise a bad agent round flags the
scheduled task as broken (exactly the confusion this whole episode was).

**The subtle consequence, worth knowing.** Terminating the *pipeline* does not
kill the `opencode` child process. The very first "failed" run therefore **kept
working and committed** — `7db7de4` (MOT keyframe frame-time, E-026) exists in the
history even though that iteration reported failure and wrote no log. So:

> A failed loop iteration may still have produced a commit. Check `git log`
> before concluding nothing happened.

Verify the loop with:

```powershell
powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File scripts/agent-loop.ps1 -Iterations 0
# -> exit 0, logs/ created

powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File scripts/agent-loop.ps1
# -> an iteration that commits and writes logs/loop-<stamp>.log
```



## Guardrails

* **One iteration at a time.** The lock file `.agent-loop.lock` holds the owning
  PID; if that process is gone the lock is treated as stale and reclaimed.
* **No game assets, ever.** The prompt forbids it and `extract_assets.py` refuses
  to write inside the repo; `.gitignore` blocks the extensions too.
* **Bounded work.** The prompt asks for one small, testable slice per iteration,
  committed and pushed, so a bad iteration is a small revert.
* **Human review.** Read `logs/` and the GitHub issue comments. The loop is not
  silent: every iteration must comment on the issue it touched.
* **Cost.** `--auto` auto-approves tool use. Disable the task when the workstation
  should not run it.

## Why a scheduled task rather than a background job

A background PowerShell job dies with the session. The scheduled task survives
logoff, restarts cleanly, is visible in Task Scheduler, and is trivially disabled.

## Failure modes to watch

| Symptom | Cause | Fix |
|---|---|---|
| `another iteration is running` forever | lock file left by a hard kill **and** the PID was reused | delete `.agent-loop.lock` |
| iterations stack up | an agent runs longer than 10 minutes | the lock makes the next tick skip; keep work small |
| nothing commits | agent is blocked | read the newest `logs/loop-*.log` |
| task not firing | machine asleep / task disabled | check Task Scheduler history |
