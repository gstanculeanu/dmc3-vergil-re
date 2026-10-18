<#
.SYNOPSIS
    Install / verify / remove the "Vergil as Hades" mod, with a real backup.

.DESCRIPTION
    One mod folder holding two edited game files:
      * R_HADES.WAD    -- the boss renders a solid colour (proves texture replacement)
      * R_LANG_EN.WAD  -- the boss name reads "Vergil" (proves text replacement)

    THE GAME INSTALLATION IS NEVER WRITTEN. The port builds a symlink overlay from
    mods/, so this script copies the originals into a backup folder first, records
    their SHA-256 values, and re-checks them after building -- refusing to continue
    if either game file changed.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts/vergil-boss-mod.ps1 -Install
    powershell -ExecutionPolicy Bypass -File scripts/vergil-boss-mod.ps1 -Status
    powershell -ExecutionPolicy Bypass -File scripts/vergil-boss-mod.ps1 -Restore
#>
[CmdletBinding()]
param(
    [string] $Gow3Dir = 'C:\Users\GigelCastel\Desktop\gow3\gow3-windows',
    [string] $GameDir = 'C:\Users\GigelCastel\Desktop\gow3\CUSA01715',
    [string] $BackupRoot = 'C:\Users\GigelCastel\Desktop\gow3\_backups',
    [string] $ModName = 'VergilHades',
    [string] $Tint = '0xF800',
    [int]    $TextureIndex = 0,
    [switch] $Install,
    [switch] $Restore,
    [switch] $Status
)

$ErrorActionPreference = 'Stop'

$RepoDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$RelDir  = 'EXEC\WAD\PS4_LE'
$Files   = @('R_HADES.WAD', 'R_LANG_EN.WAD')

$ModRoot    = Join-Path $Gow3Dir "mods\$ModName"
$ModContent = Join-Path $ModRoot 'dvdroot_ps4'
$BackupDir  = Join-Path $BackupRoot $ModName
$Manifest   = Join-Path $BackupDir 'manifest.json'
$OldMod     = Join-Path $Gow3Dir 'mods\VergilNameTest'

function Get-Sha256([string] $Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLower()
}
function GameFile([string] $Name) { Join-Path $GameDir "$RelDir\$Name" }

function Show-Status {
    Write-Host "mod          : $ModRoot"
    if (Test-Path -LiteralPath $Manifest) {
        $m = Get-Content -LiteralPath $Manifest -Raw | ConvertFrom-Json
        Write-Host "               built $($m.created)"
        $allGood = $true
        foreach ($f in $Files) {
            $g = GameFile $f
            $now = Get-Sha256 $g
            $want = $m.files.$f.source_sha256
            $state = if ($now -eq $want) { 'untouched' } else { '!! CHANGED' }
            if ($now -ne $want) { $allGood = $false }
            $installed = Test-Path -LiteralPath (Join-Path $ModContent "$RelDir\$f")
            Write-Host ("  {0,-15} game={1,-10} mod={2}" -f $f, $state,
                        $(if ($installed) { 'present' } else { 'absent' }))
        }
        if ($allGood) {
            Write-Host "integrity    : both game files match the backup" -ForegroundColor Green
        } else {
            Write-Host "integrity    : !! a game file differs from the backup" -ForegroundColor Red
        }
    } else {
        Write-Host "               not built yet"
    }
}

function Invoke-Install {
    foreach ($f in $Files) {
        if (-not (Test-Path -LiteralPath (GameFile $f))) { throw "not found: $(GameFile $f)" }
    }

    Write-Host "backing up the originals first"
    New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
    $record = @{}
    foreach ($f in $Files) {
        $g = GameFile $f
        $b = Join-Path $BackupDir $f
        $hash = Get-Sha256 $g
        if (-not (Test-Path -LiteralPath $b)) {
            Copy-Item -LiteralPath $g -Destination $b -Force
            Write-Host "  copied $f"
        } elseif ((Get-Sha256 $b) -ne $hash) {
            throw "$f already has a backup that does not match the game file"
        } else {
            Write-Host "  $f backup already present and identical"
        }
        $record[$f] = @{ source_sha256 = $hash; source_bytes = (Get-Item $g).Length }
    }

    if (Test-Path -LiteralPath $OldMod) {
        Remove-Item -LiteralPath $OldMod -Recurse -Force
        Write-Host "removed the earlier name-only mod (VergilNameTest) to avoid a conflict"
    }
    if (Test-Path -LiteralPath $ModRoot) { Remove-Item -LiteralPath $ModRoot -Recurse -Force }

    Write-Host "building the mod"
    $tool = Join-Path $RepoDir 'tools\gow3\make_boss_mod.py'
    & python $tool --game $GameDir --mods $ModRoot --tint $Tint --texture-index $TextureIndex
    if ($LASTEXITCODE -ne 0) { throw "the builder failed ($LASTEXITCODE)" }

    foreach ($f in $Files) {
        $now = Get-Sha256 (GameFile $f)
        if ($now -ne $record[$f].source_sha256) { throw "$f CHANGED -- aborting" }
    }
    Write-Host "  both game files verified unchanged" -ForegroundColor Green

    @{ created = (Get-Date).ToString('o'); files = $record } |
        ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $Manifest -Encoding UTF8

    Write-Host ""
    Write-Host "INSTALLED. The game installation was not modified." -ForegroundColor Green
    Write-Host "  mod     : $ModContent"
    Write-Host "  backup  : $BackupDir"
    Write-Host ""
    Write-Host "Test: start the port, load the save just before the Hades fight."
    Write-Host "      Expect the boss to render a solid colour and the name to read Vergil."
    Write-Host "Undo: powershell -ExecutionPolicy Bypass -File scripts/vergil-boss-mod.ps1 -Restore"
}

function Invoke-Restore {
    foreach ($d in @($ModRoot, $OldMod)) {
        if (Test-Path -LiteralPath $d) {
            Remove-Item -LiteralPath $d -Recurse -Force
            Write-Host "removed $d"
        }
    }
    if (Test-Path -LiteralPath $Manifest) {
        $m = Get-Content -LiteralPath $Manifest -Raw | ConvertFrom-Json
        foreach ($f in $Files) {
            $now = Get-Sha256 (GameFile $f)
            $want = $m.files.$f.source_sha256
            if ($now -ne $want) {
                Write-Host "$f differs from the backup -- restoring" -ForegroundColor Yellow
                Copy-Item -LiteralPath (Join-Path $BackupDir $f) -Destination (GameFile $f) -Force
            }
        }
        Write-Host "game files verified against the backup"
    }
    Write-Host "Done. The mod is off."
}

if ($Restore)     { Invoke-Restore }
elseif ($Install) { Invoke-Install }
else              { Show-Status }
