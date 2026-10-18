<#
.SYNOPSIS
    Install or remove a GoW3R localisation-name mod, with a real backup.

.DESCRIPTION
    Renames one localisation entry (default: *832*, "Hades") inside a copy of
    R_LANG_EN.WAD and drops the copy into the port's mods folder.

    THE GAME INSTALLATION IS NEVER WRITTEN. The port builds a symlink overlay from
    mods/, so the original files are left exactly as they were -- and this script
    proves it: it records the source file's SHA-256 before and re-checks it after,
    and refuses to continue if the file changed. A copy of the original is also kept
    under the backup folder so the mod can be rebuilt or the file restored.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts/vergil-name-mod.ps1 -Status
    powershell -ExecutionPolicy Bypass -File scripts/vergil-name-mod.ps1 -Install
    powershell -ExecutionPolicy Bypass -File scripts/vergil-name-mod.ps1 -Restore
#>
[CmdletBinding()]
param(
    [string] $Gow3Dir = 'C:\Users\GigelCastel\Desktop\gow3\gow3-windows',
    [string] $GameDir = 'C:\Users\GigelCastel\Desktop\gow3\CUSA01715',
    [string] $BackupRoot = 'C:\Users\GigelCastel\Desktop\gow3\_backups',
    [string] $ModName = 'VergilNameTest',
    [int]    $EntryId = 832,
    [string] $From = 'Hades',
    [string] $To = 'Vergil',
    [switch] $Install,
    [switch] $Restore,
    [switch] $Status
)

$ErrorActionPreference = 'Stop'

$RepoDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$RelWad  = 'EXEC\WAD\PS4_LE\R_LANG_EN.WAD'
$SourceWad = Join-Path $GameDir $RelWad
$ModWad    = Join-Path $Gow3Dir "mods\$ModName\dvdroot_ps4\$RelWad"
$ModRoot   = Join-Path $Gow3Dir "mods\$ModName"
$BackupDir = Join-Path $BackupRoot $ModName
$Manifest  = Join-Path $BackupDir 'manifest.json'

function Get-Sha256([string] $Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLower()
}

function Show-Status {
    Write-Host "source (game) : $SourceWad"
    if (Test-Path -LiteralPath $SourceWad) {
        Write-Host ("                {0:N0} bytes  sha256 {1}" -f (Get-Item $SourceWad).Length, (Get-Sha256 $SourceWad).Substring(0,16))
    } else {
        Write-Host "                MISSING"
    }
    Write-Host "backup        : $BackupDir"
    if (Test-Path -LiteralPath $Manifest) {
        $m = Get-Content -LiteralPath $Manifest -Raw | ConvertFrom-Json
        Write-Host ("                backed up {0}  sha256 {1}" -f $m.created, $m.source_sha256.Substring(0,16))
    } else {
        Write-Host "                (none yet)"
    }
    Write-Host "mod           : $ModWad"
    if (Test-Path -LiteralPath $ModWad) {
        Write-Host ("                INSTALLED  {0:N0} bytes  sha256 {1}" -f (Get-Item $ModWad).Length, (Get-Sha256 $ModWad).Substring(0,16))
    } else {
        Write-Host "                not installed"
    }
    if (Test-Path -LiteralPath $Manifest) {
        $m = Get-Content -LiteralPath $Manifest -Raw | ConvertFrom-Json
        $now = Get-Sha256 $SourceWad
        if ($now -eq $m.source_sha256) {
            Write-Host "integrity     : the game file matches the backup -- untouched"
        } else {
            Write-Host "integrity     : !! the game file differs from the backup" -ForegroundColor Red
        }
    }
}

function Invoke-Install {
    if (-not (Test-Path -LiteralPath $SourceWad)) { throw "not found: $SourceWad" }

    $before = Get-Sha256 $SourceWad
    Write-Host "backing up the original first"
    New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
    $backupWad = Join-Path $BackupDir 'R_LANG_EN.WAD'
    if (-not (Test-Path -LiteralPath $backupWad)) {
        Copy-Item -LiteralPath $SourceWad -Destination $backupWad -Force
        Write-Host "  copied the original to $backupWad"
    } elseif ((Get-Sha256 $backupWad) -ne $before) {
        throw "a backup already exists and does not match the current game file; resolve this by hand"
    } else {
        Write-Host "  backup already present and identical"
    }

    Write-Host "building the mod"
    $tool = Join-Path $RepoDir 'tools\gow3\make_lang_mod.py'
    & python $tool --wad $SourceWad --entry $EntryId --from $From --to $To --out $ModWad
    if ($LASTEXITCODE -ne 0) { throw "the builder failed ($LASTEXITCODE)" }

    $after = Get-Sha256 $SourceWad
    if ($after -ne $before) { throw "THE GAME FILE CHANGED -- aborting" }

    @{
        created        = (Get-Date).ToString('o')
        source         = $SourceWad
        source_sha256  = $before
        source_bytes   = (Get-Item $SourceWad).Length
        mod            = $ModWad
        mod_sha256     = (Get-Sha256 $ModWad)
        mod_bytes      = (Get-Item $ModWad).Length
        entry          = $EntryId
        from           = $From
        to             = $To
    } | ConvertTo-Json | Set-Content -LiteralPath $Manifest -Encoding UTF8

    Write-Host ""
    Write-Host "INSTALLED. The game installation was not modified (sha256 unchanged)." -ForegroundColor Green
    Write-Host "  mod file : $ModWad"
    Write-Host "  manifest : $Manifest"
    Write-Host ""
    Write-Host "To test: start the port, load the save just before the Hades fight,"
    Write-Host "and look at the boss name. To undo:"
    Write-Host "  powershell -ExecutionPolicy Bypass -File scripts/vergil-name-mod.ps1 -Restore"
}

function Invoke-Restore {
    if (Test-Path -LiteralPath $ModRoot) {
        Remove-Item -LiteralPath $ModRoot -Recurse -Force
        Write-Host "removed the mod folder: $ModRoot"
    } else {
        Write-Host "no mod folder to remove"
    }
    if (Test-Path -LiteralPath $Manifest) {
        $m = Get-Content -LiteralPath $Manifest -Raw | ConvertFrom-Json
        $now = Get-Sha256 $SourceWad
        if ($now -ne $m.source_sha256) {
            Write-Host "the game file differs from the backup -- restoring it" -ForegroundColor Yellow
            Copy-Item -LiteralPath (Join-Path $BackupDir 'R_LANG_EN.WAD') -Destination $SourceWad -Force
            Write-Host "restored from backup; sha256 now $((Get-Sha256 $SourceWad).Substring(0,16))"
        } else {
            Write-Host "the game file was never changed; nothing to restore"
        }
    }
    Write-Host "Done. The mod is off."
}

if ($Restore)      { Invoke-Restore }
elseif ($Install)  { Invoke-Install }
else               { Show-Status }
