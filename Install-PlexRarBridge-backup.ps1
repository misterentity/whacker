# =====================================================================
#  Install‑PlexRarBridge.ps1   v2.1.1  (2025‑07‑15)
#  Robust installer for Plex‑RAR‑Bridge
# =====================================================================

[CmdletBinding()]
param(
    [string]$InstallPath    = "C:\Program Files\PlexRarBridge",
    [string]$ServiceName    = "PlexRarBridge",
    [string]$WatchDirectory = "",
    [string]$TargetDirectory = "",
    [string]$PlexHost       = "",
    [string]$PlexToken      = "",
    [string]$PlexLibraryKey = "",
    [switch]$Uninstall,
    [switch]$Upgrade,
    [switch]$NoGui,
    [ValidateSet("python_vfs","rar2fs","extraction")]
    [string]$ProcessingMode = "python_vfs"
)

# ─── constants ────────────────────────────────────────────────────────
$ErrorActionPreference = 'Stop'
$AppName               = 'Plex RAR Bridge'
$AppVersion            = '2.1.1'
$RequiredPythonVersion = '3.12'
$LogPath               = "$env:TEMP\PlexRarBridge-Install.log"

function Write‑Log { param($Msg,$Lvl='INFO')
    $ts = Get‑Date -Format 'yyyy-MM-dd HH:mm:ss'
    $line = "[$ts] [$Lvl] $Msg"
    Write‑Host $line
    $line | Out‑File $LogPath -Append -Encoding UTF8
}

# ─── prerequisites ────────────────────────────────────────────────────
function Test‑Admin     { (New‑Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator) }
function Has‑Internet   { try { Invoke‑WebRequest 'https://www.microsoft.com' -TimeoutSec 8 | Out‑Null; $true } catch { $false } }
function Get‑PythonVers { try { (& python --version 2>&1) -match 'Python (\d+\.\d+\.\d+)' | Out‑Null; $Matches[1] } catch { $null } }

# ─── python install / deps ────────────────────────────────────────────
function Install‑Python {
    Write‑Log "Installing Python $RequiredPythonVersion …"
    try {
        winget install Python.Python.$RequiredPythonVersion --accept‑package‑agreements --accept‑source‑agreements
        if ($LASTEXITCODE -eq 0) { Write‑Log 'Python installed via winget'; return }
    } catch { Write‑Log 'winget failed – using direct download' 'WARN' }

    $u="https://www.python.org/ftp/python/$RequiredPythonVersion.0/python-$RequiredPythonVersion.0-amd64.exe"
    $e="$env:TEMP\python$RequiredPythonVersion.exe"
    Invoke‑WebRequest $u -OutFile $e
    Start‑Process $e '/quiet InstallAllUsers=1 PrependPath=1' -Wait
    Remove‑Item $e
    Write‑Log 'Python installed via direct download'
}

function Install‑Dependencies {
    Write‑Log 'Installing Python dependencies'
    & python -m pip install --upgrade pip
    & pip install pyyaml requests watchdog pywin32 rarfile pillow
}

# ─── UnRAR ────────────────────────────────────────────────────────────
function Install‑UnRAR {
    $u='https://www.rarlab.com/rar/unrarw32.exe'; $t="$env:TEMP\unrar.exe"
    Write‑Log 'Installing UnRAR'
    Invoke‑WebRequest $u -OutFile $t
    Start‑Process $t '/S' -Wait
    Remove‑Item $t
    Copy‑Item "$env:ProgramFiles\WinRAR\UnRAR.exe" "$InstallPath\UnRAR.exe" -Force
}

# ─── NSSM (safe copy) ────────────────────────────────────────────────
function Install‑NSSM {
    Write‑Log 'Installing NSSM'
    $zip='https://nssm.cc/release/nssm-2.24.zip'; $zf="$env:TEMP\nssm.zip"; $wd="$env:TEMP\nssm"
    $dst="$InstallPath\nssm.exe"

    # kill any nssm.exe running from our folder
    if (Test‑Path $dst) {
        Write‑Log 'Terminating any running nssm.exe instances'
        Get‑CimInstance Win32_Process |
            Where‑Object { $_.Name -eq 'nssm.exe' -and $_.ExecutablePath -eq $dst } |
            ForEach‑Object { try { Stop‑Process -Id $_.ProcessId -Force } catch {} }
        Start‑Sleep 3
    }

    Invoke‑WebRequest $zip -OutFile $zf
    Expand‑Archive $zf -DestinationPath $wd -Force
    $arch = if ([Environment]::Is64BitOperatingSystem) { 'win64' } else { 'win32' }
    $src  = "$wd\nssm-2.24\$arch\nssm.exe"
    if (-not (Test‑Path $src)) { throw 'NSSM exe missing in archive' }

    $max=12; for ($i=1; $i -le $max; $i++) {
        try { Copy‑Item $src $dst -Force; Write‑Log "NSSM copied (attempt $i)"; break }
        catch {
            if ($i -eq $max) { throw "Cannot overwrite nssm.exe after $max attempts: $_" }
            Write‑Log "  nssm.exe locked (attempt $i) – retry in 5 s" 'WARN'; Start‑Sleep 5
        }
    }

    Remove‑Item $zf -Force; Remove‑Item $wd -Recurse -Force
}

# ─── service helpers (sc.exe) ─────────────────────────────────────────
function Get‑SvcState { param($n) (& sc.exe query $n 2>&1) -match 'STATE\s+:\s+\d+\s+(\w+)' | Out‑Null; $Matches[1] }
function Stop‑Svc     { param($n) & sc.exe stop   $n | Out‑Null }
function Del‑Svc      { param($n) & sc.exe delete $n | Out‑Null }

function Remove‑ExistingService {
    $s = Get‑SvcState $ServiceName
    if ($s) {
        Write‑Log "Found existing service ($s) – deleting"
        if ($s -eq 'RUNNING') { Stop‑Svc $ServiceName; Start‑Sleep 5 }
        Del‑Svc  $ServiceName; Start‑Sleep 2
    }
}

# ─── copy program files ───────────────────────────────────────────────
function Copy‑ProgramFiles {
    $dirs=@('logs','data','work','failed','archive','thumb_cache','docs','mounts')
    foreach ($d in $dirs) { New‑Item -Force -ItemType Directory -Path "$InstallPath\$d" | Out‑Null }
    foreach ($f in Get‑ChildItem -File) { Copy‑Item $f.FullName "$InstallPath\$($f.Name)" -Force }
}

# ─── service install ─────────────────────────────────────────────────-
function Install‑Service {
    param($Cfg)
    & "$InstallPath\nssm.exe" install $ServiceName (Get‑Command python).Source "$InstallPath\plex_rar_bridge.py"
    & "$InstallPath\nssm.exe" set $ServiceName AppDirectory $InstallPath
    & "$InstallPath\nssm.exe" set $ServiceName Start        SERVICE_AUTO_START
    & "$InstallPath\nssm.exe" set $ServiceName AppStdout    "$InstallPath\logs\stdout.log"
    & "$InstallPath\nssm.exe" set $ServiceName AppStderr    "$InstallPath\logs\stderr.log"
    & "$InstallPath\nssm.exe" set $ServiceName AppEnvironmentExtra `
        "PLEXRARBRIDGE_ENHANCED=1" "PLEXRARBRIDGE_MODE=$($Cfg.ProcessingMode)"
    & "$InstallPath\nssm.exe" start $ServiceName
}

function Smoke‑Test { & python -c "import yaml,requests,watchdog,rarfile" | Out‑Null }

# ─── main workflows ───────────────────────────────────────────────────
function Do‑Install {
    if (-not (Test‑Admin))   { throw 'Run PowerShell as Administrator.' }
    if (-not (Has‑Internet)) { throw 'No internet connection.'          }

    if (-not (Get‑PythonVers)) {
        Install‑Python
        $env:PATH = [Environment]::GetEnvironmentVariable('PATH','Machine') + ';' +
                    [Environment]::GetEnvironmentVariable('PATH','User')
    }

    # always stop existing service – prevents nssm lock
    Remove‑ExistingService

    New‑Item -Force -ItemType Directory -Path $InstallPath | Out‑Null
    Install‑Dependencies
    Install‑UnRAR
    Install‑NSSM
    Copy‑ProgramFiles

    $cfg = @{ ProcessingMode = $ProcessingMode }
    Install‑Service $cfg
    Smoke‑Test
    Write‑Log 'Install done'; Write‑Host "`n$AppName $AppVersion installed."
}

function Do‑Uninstall {
    Remove‑ExistingService
    if (Test‑Path $InstallPath) { Remove‑Item $InstallPath -Recurse -Force }
    Write‑Log 'Uninstall done';  Write‑Host "$AppName removed."
}

# ─── entry point ──────────────────────────────────────────────────────
try {
    Write‑Host "=== $AppName $AppVersion Installer ===`n"
    if     ($Uninstall) { Do‑Uninstall }
    else                { Do‑Install  }
}
catch {
    Write‑Log $_.Exception.Message 'ERROR'
    throw
}