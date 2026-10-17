<#
.SYNOPSIS
    One iteration of the dmc3-vergil-re autonomous agent loop.

.DESCRIPTION
    Starts a NEW OpenCode session (fresh context) with the prompt in
    scripts/agent-prompt.md and tees the session to logs/loop-<stamp>.log.

    A PID-based lock file prevents overlapping iterations; a lock whose owning
    process no longer exists is treated as stale and reclaimed.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts/agent-loop.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts/agent-loop.ps1 -Iters 3 -IntervalSeconds 600
#>
[CmdletBinding()]
param(
    [string] $RepoDir  = (Split-Path -Parent $PSScriptRoot),
    [string] $PromptFile = (Join-Path $PSScriptRoot 'agent-prompt.md'),
    [string] $Model = '',
    [int]    $Iterations = 1,
    [int]    $IntervalSeconds = 600
)

$ErrorActionPreference = 'Stop'

$RepoDir = (Resolve-Path -LiteralPath $RepoDir).Path
$lockPath = Join-Path $RepoDir '.agent-loop.lock'
$logDir = Join-Path $RepoDir 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Test-StaleLock {
    if (-not (Test-Path -LiteralPath $lockPath)) { return $true }
    try {
        $info = Get-Content -LiteralPath $lockPath -Raw | ConvertFrom-Json
    } catch {
        return $true   # unreadable lock == stale
    }
    if (-not $info.pid) { return $true }
    $proc = Get-Process -Id ([int]$info.pid) -ErrorAction SilentlyContinue
    if (-not $proc) { return $true }
    Write-Host "iteration already running (pid $($info.pid), started $($info.started))"
    return $false
}

if (-not (Test-Path -LiteralPath $PromptFile)) {
    throw "prompt file not found: $PromptFile"
}
$prompt = Get-Content -LiteralPath $PromptFile -Raw

for ($i = 1; $i -le $Iterations; $i++) {
    if (-not (Test-StaleLock)) { exit 0 }

    Remove-Item -LiteralPath $lockPath -Force -ErrorAction SilentlyContinue
    $lockHandle = [System.IO.File]::Open(
        $lockPath, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
    $payload = @{ pid = $PID; started = (Get-Date).ToString('o'); iteration = $i } | ConvertTo-Json -Compress
    $writer = New-Object System.IO.StreamWriter($lockHandle)
    $writer.Write($payload)
    $writer.Flush()

    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $log = Join-Path $logDir "loop-$stamp.log"

    try {
        $cliArgs = @('run', '--auto')
        if ($Model) { $cliArgs += @('--model', $Model) }
        $cliArgs += $prompt

        Write-Host "[$stamp] starting iteration $i (log: $log)"
        Push-Location -LiteralPath $RepoDir
        try {
            & opencode @cliArgs 2>&1 | Tee-Object -FilePath $log
        } finally {
            Pop-Location
        }
        Write-Host "[$stamp] iteration $i finished (exit $LASTEXITCODE)"
    } finally {
        $writer.Dispose()
        $lockHandle.Dispose()
        Remove-Item -LiteralPath $lockPath -Force -ErrorAction SilentlyContinue
    }

    if ($i -lt $Iterations) {
        Start-Sleep -Seconds $IntervalSeconds
    }
}
