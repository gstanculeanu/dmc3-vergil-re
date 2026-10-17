<#
.SYNOPSIS
    Register (or re-register) the every-N-minutes agent loop as a Scheduled Task.

.DESCRIPTION
    Uses schtasks.exe so it works per-user without elevation. Each trigger starts
    a brand-new OpenCode session via scripts/agent-loop.ps1.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts/register-loop.ps1
    powershell -ExecutionPolicy Bypass -File scripts/register-loop.ps1 -Minutes 30
    powershell -ExecutionPolicy Bypass -File scripts/register-loop.ps1 -Model 'opencode-go/deepseek-v4.1-flash'
#>
[CmdletBinding()]
param(
    [string] $TaskName = 'dmc3-vergil-re-loop',
    [int]    $Minutes = 10,
    [string] $Model = ''
)

$ErrorActionPreference = 'Stop'

# Resolve the script directory in the body: $PSScriptRoot is not reliable inside
# parameter defaults when launched with `powershell -File`.
$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) { $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }

$RepoDir = (Resolve-Path -LiteralPath (Split-Path -Parent $ScriptDir)).Path
$loopScript = Join-Path $ScriptDir 'agent-loop.ps1'
if (-not (Test-Path -LiteralPath $loopScript)) { throw "missing $loopScript" }

$psArgs = "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$loopScript`""
if ($Model) { $psArgs += " -Model `"$Model`"" }

$action = "powershell.exe $psArgs"

Write-Host "task    : $TaskName"
Write-Host "every   : $Minutes minute(s)"
Write-Host "repo    : $RepoDir"
Write-Host "command : $action"

schtasks /Create /TN $TaskName /TR $action /SC MINUTE /MO $Minutes /F | Out-Host
if ($LASTEXITCODE -ne 0) { throw "schtasks failed with $LASTEXITCODE" }

Write-Host ""
Write-Host "Registered. Inspect with:"
Write-Host "  schtasks /Query /TN $TaskName /V /FO LIST"
Write-Host "Disable / enable:"
Write-Host "  schtasks /Change /TN $TaskName /DISABLE"
Write-Host "  schtasks /Change /TN $TaskName /ENABLE"
