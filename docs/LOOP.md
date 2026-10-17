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
