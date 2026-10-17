<#
.SYNOPSIS
    Fast Vergil-boss test loop for the God of War III Remastered port.

.DESCRIPTION
    Purpose: test a mod change in seconds, without a playthrough.

    Stage a save that sits just before the target boss, install the mod, launch the
    game, press Continue / Load. Every step is reversible and the saves are backed
    up before anything is moved.

    Actions (combine as needed):
        -List                   show saves with their in-game location and play time
        -Isolate <slot>         stash every other save so <slot> is the only entry
        -Restore                put the stashed saves back
        -InstallMod <path>      copy a mod folder (or .zip) into the port's mods\
        -RemoveMod <name>       delete a mod folder from the port's mods\
        -Play                   launch the game

.EXAMPLE
    # the locked Hades test point, with a mod, and launch
    powershell -ExecutionPolicy Bypass -File scripts/boss-test.ps1 -BossTest -InstallMod D:\re\vergil-mod -Play

.EXAMPLE
    # what is available where?
    powershell -ExecutionPolicy Bypass -File scripts/boss-test.ps1 -List

.EXAMPLE
    # test iteration: save at the boss, my mod installed, game launched
    powershell -ExecutionPolicy Bypass -File scripts/boss-test.ps1 `
        -Isolate SD-261013185858 -InstallMod D:\re\vergil-mod -Play

.EXAMPLE
    # put everything back
    powershell -ExecutionPolicy Bypass -File scripts/boss-test.ps1 -Restore
#>
[CmdletBinding()]
param(
    [string] $Gow3Dir = 'C:\Users\GigelCastel\Desktop\gow3\gow3-windows',
    [string] $TitleId = 'CUSA01715',
    [string] $UserId  = '1',

    [switch] $List,
    [string] $Isolate,
    [switch] $Restore,
    [switch] $IncludeAutosave,

    [string] $BossSlot = 'SD-261017161301',
    [switch] $BossTest,

    [string] $InstallMod,
    [string] $RemoveMod,
    [switch] $Play,

    [string] $LogFile,
    [switch] $Force
)

$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------- helpers
function Write-Step($message) { Write-Host "  $message" }

function Assert-GameStopped {
    $proc = Get-Process -Name 'gow3-probe', 'God of War III' -ErrorAction SilentlyContinue
    if ($proc -and -not $Force) {
        throw "the game is running (pid $($proc.Id -join ', ')); close it first, or pass -Force"
    }
}

function Get-SavesRoot { Join-Path $Gow3Dir "user\savedata\$UserId\$TitleId" }
function Get-StashRoot { Join-Path $Gow3Dir "user\savedata_backups\boss-test-stash" }
function Get-ModsRoot  { Join-Path $Gow3Dir 'mods' }

function Write-Log($message) {
    $dir = Join-Path (Split-Path -Parent $PSScriptRoot) 'logs'
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $target = if ($LogFile) { $LogFile } else { Join-Path $dir 'test-loop.log' }
    $stamp = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    Add-Content -LiteralPath $target -Value "[$stamp] $message"
}

function Invoke-SaveList {
    $savesRoot = Get-SavesRoot
    if (-not (Test-Path -LiteralPath $savesRoot)) {
        throw "saves folder not found: $savesRoot"
    }
    $tool = Join-Path (Split-Path -Parent $PSScriptRoot) 'tools\gow3\save_list.py'
    & python $tool --saves-dir $savesRoot
}

function Backup-Saves {
    $savesRoot = Get-SavesRoot
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $dest = Join-Path $Gow3Dir "user\savedata_backups\boss-test-$stamp"
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    Get-ChildItem -LiteralPath $savesRoot -Directory | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $dest -Recurse -Force
    }
    Write-Step "backed up saves -> $dest"
    Write-Log "backup -> $dest"
}

# ---------------------------------------------------------------- actions
function Invoke-Isolate {
    param([string] $SlotName)

    $savesRoot = Get-SavesRoot
    $stashRoot = Get-StashRoot
    $slotPath = Join-Path $savesRoot $SlotName
    if (-not (Test-Path -LiteralPath $slotPath)) {
        throw "save slot not found: $slotPath (use -List)"
    }

    Backup-Saves
    New-Item -ItemType Directory -Force -Path $stashRoot | Out-Null

    $patterns = @('SD-*')
    if ($IncludeAutosave) { $patterns += 'AUTOSAVE' }

    $moved = 0
    foreach ($pattern in $patterns) {
        Get-ChildItem -LiteralPath $savesRoot -Directory -Filter $pattern | ForEach-Object {
            if ($_.Name -eq $SlotName) { return }
            $metaName = $_.Name + '.sce_sys'
            foreach ($item in @($_.Name, $metaName)) {
                $src = Join-Path $savesRoot $item
                if (Test-Path -LiteralPath $src) {
                    Move-Item -LiteralPath $src -Destination $stashRoot -Force
                    $moved++
                }
            }
        }
    }

    Write-Step "stashed $moved item(s); '$SlotName' is now the only manual save"
    Write-Step 'press Continue / Load Game -> you are at the boss'
    Write-Log "isolate $SlotName (stashed $moved)"
}

function Invoke-Restore {
    $savesRoot = Get-SavesRoot
    $stashRoot = Get-StashRoot
    if (-not (Test-Path -LiteralPath $stashRoot)) {
        Write-Step 'nothing stashed'
        return
    }
    $moved = 0
    Get-ChildItem -LiteralPath $stashRoot | ForEach-Object {
        Move-Item -LiteralPath $_.FullName -Destination $savesRoot -Force
        $moved++
    }
    Remove-Item -LiteralPath $stashRoot -Recurse -Force -ErrorAction SilentlyContinue
    Write-Step "restored $moved item(s)"
    Write-Log "restore ($moved)"
}

function Invoke-InstallMod {
    param([string] $Path)
    if (-not (Test-Path -LiteralPath $Path)) { throw "mod path not found: $Path" }

    $modsRoot = Join-Path $Gow3Dir 'mods'
    New-Item -ItemType Directory -Force -Path $modsRoot | Out-Null

    $item = Get-Item -LiteralPath $Path
    $dest = Join-Path $modsRoot $item.BaseName
    if (Test-Path -LiteralPath $dest) { Remove-Item -LiteralPath $dest -Recurse -Force }

    if ($item.PSIsContainer) {
        Copy-Item -LiteralPath $item.FullName -Destination $dest -Recurse -Force
    } else {
        # a .zip is accepted as-is: the port extracts it on launch
        Copy-Item -LiteralPath $item.FullName -Destination $modsRoot -Force
    }
    Write-Step "installed mod -> $dest"
    Write-Log "install mod $Path -> $dest"
}

function Invoke-RemoveMod {
    param([string] $Name)
    $dest = Join-Path (Join-Path $Gow3Dir 'mods') $Name
    if (-not (Test-Path -LiteralPath $dest)) { Write-Step "mod not present: $Name"; return }
    Remove-Item -LiteralPath $dest -Recurse -Force
    Write-Step "removed mod $Name"
    Write-Log "remove mod $Name"
}

function Invoke-Play {
    $exe = Join-Path $Gow3Dir 'Play God of War III.exe'
    if (-not (Test-Path -LiteralPath $exe)) {
        $exe = Join-Path $Gow3Dir 'God of War III.exe'
    }
    if (-not (Test-Path -LiteralPath $exe)) { throw "launcher not found under $Gow3Dir" }
    Write-Step "launching $exe"
    Start-Process -FilePath $exe -WorkingDirectory $Gow3Dir
    Write-Log "play"
}

# ---------------------------------------------------------------- main
if (-not (Test-Path -LiteralPath $Gow3Dir)) { throw "gow3 folder not found: $Gow3Dir" }
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw 'python not found on PATH' }

Assert-GameStopped

$didSomething = $false

if ($Isolate) { Invoke-Isolate -SlotName $Isolate; $didSomething = $true }
if ($BossTest) { Invoke-Isolate -SlotName $BossSlot; $didSomething = $true }
if ($Restore) { Invoke-Restore; $didSomething = $true }
if ($InstallMod) { Invoke-InstallMod -Path $InstallMod; $didSomething = $true }
if ($RemoveMod) { Invoke-RemoveMod -Name $RemoveMod; $didSomething = $true }

if ($List -or -not $didSomething) {
    Write-Host ''
    Write-Host 'Save slots (location + play time come from each save''s param.bin):'
    Invoke-SaveList
    Write-Host ''
    Write-Host 'Typical iteration:'
    Write-Host "  scripts\boss-test.ps1 -Isolate <slot> -InstallMod <mod> -Play"
    Write-Host '  ... test in game ...'
    Write-Host '  scripts\boss-test.ps1 -Restore'
}

if ($Play) { Invoke-Play }
