<#
.SYNOPSIS
    Remove the agent-loop Scheduled Task.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts/unregister-loop.ps1
#>
[CmdletBinding()]
param(
    [string] $TaskName = 'dmc3-vergil-re-loop'
)

$ErrorActionPreference = 'Stop'

schtasks /Delete /TN $TaskName /F | Out-Host
if ($LASTEXITCODE -ne 0) {
    Write-Warning "schtasks delete returned $LASTEXITCODE (task absent?)"
} else {
    Write-Host "Removed task '$TaskName'."
}
