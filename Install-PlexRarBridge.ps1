# =====================================================================
#  Install-PlexRarBridge.ps1   v2.1.1  (2025-07-15)
#  Robust installer for Plex-RAR-Bridge
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

function Write-Log { param($Msg,$Lvl='INFO')
    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $line = "[$ts] [$Lvl] $Msg"
    Write-Host $line
    $line | Out-File $LogPath -Append -Encoding UTF8
}

# ─── prerequisites ────────────────────────────────────────────────────
function Test-Admin     { (New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator) }
function Has-Internet   { try { Invoke-WebRequest 'https://www.microsoft.com' -TimeoutSec 8 | Out-Null; $true } catch { $false } }
function Get-PythonVers { try { (& python --version 2>&1) -match 'Python (\d+\.\d+\.\d+)' | Out-Null; $Matches[1] } catch { $null } }

# ─── python install / deps ────────────────────────────────────────────
function Install-Python {
    Write-Log "Installing Python $RequiredPythonVersion …"
    try {
        winget install Python.Python.$RequiredPythonVersion --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -eq 0) { Write-Log 'Python installed via winget'; return }
    } catch { Write-Log 'winget failed – using direct download' 'WARN' }

    $u="https://www.python.org/ftp/python/$RequiredPythonVersion.0/python-$RequiredPythonVersion.0-amd64.exe"
    $e="$env:TEMP\python$RequiredPythonVersion.exe"
    Write-Log "Downloading Python installer from $u"
    try {
        Invoke-WebRequest -Uri $u -OutFile $e
        Write-Log "Installing Python from $e"
        Start-Process -FilePath $e -ArgumentList '/quiet','InstallAllUsers=1','PrependPath=1' -Wait
        if ($LASTEXITCODE -eq 0) { Write-Log 'Python installed successfully' }
        else { throw "Python installation failed with exit code $LASTEXITCODE" }
    } catch { Write-Log "Python installation failed: $_" 'ERROR'; throw }
}

function Install-Dependencies {
    Write-Log 'Installing Python dependencies'
    try {
        & python -m pip install --upgrade pip
        & python -m pip install -r requirements.txt
        if ($LASTEXITCODE -eq 0) { Write-Log 'Dependencies installed successfully' }
        else { throw "Dependency installation failed with exit code $LASTEXITCODE" }
    } catch { Write-Log "Dependency installation failed: $_" 'ERROR'; throw }
}

# ─── service management ────────────────────────────────────────────────
function Install-UnRAR {
    Write-Log 'Installing UnRAR'
    $url = 'https://www.rarlab.com/rar/unrarw64.exe'
    $installer = "$env:TEMP\unrar-installer.exe"
    
    if (!(Test-Path 'UnRAR.exe')) {
        Write-Log "Downloading UnRAR from $url"
        Invoke-WebRequest -Uri $url -OutFile $installer
        Write-Log "Installing UnRAR"
        Start-Process -FilePath $installer -ArgumentList '/S' -Wait
    }
}

function Install-NSSM {
    Write-Log 'Installing NSSM'
    $nssmPath = '.\nssm\nssm.exe'
    
    if (!(Test-Path $nssmPath)) {
        $url = 'https://nssm.cc/release/nssm-2.24.zip'
        $zipPath = "$env:TEMP\nssm.zip"
        
        Write-Log "Downloading NSSM from $url"
        Invoke-WebRequest -Uri $url -OutFile $zipPath
        
        Write-Log "Extracting NSSM"
        Expand-Archive -Path $zipPath -DestinationPath $env:TEMP -Force
        
        New-Item -ItemType Directory -Path '.\nssm' -Force | Out-Null
        Copy-Item -Path "$env:TEMP\nssm-2.24\win64\nssm.exe" -Destination $nssmPath
        
        Remove-Item -Path $zipPath -Force
        Remove-Item -Path "$env:TEMP\nssm-2.24" -Recurse -Force
    }
}

function Install-Service {
    Write-Log 'Installing Windows Service'
    $nssmPath = '.\nssm\nssm.exe'
    $pythonPath = (Get-Command python).Source
    $scriptPath = Join-Path $PWD 'plex_rar_bridge.py'
    
    # Remove existing service if it exists
    try {
        & $nssmPath stop $ServiceName 2>$null
        & $nssmPath remove $ServiceName confirm 2>$null
    } catch { }
    
    # Install new service
    & $nssmPath install $ServiceName $pythonPath $scriptPath
    & $nssmPath set $ServiceName DisplayName "Plex RAR Bridge Service"
    & $nssmPath set $ServiceName Description "Automatic RAR extraction service for Plex Media Server"
    & $nssmPath set $ServiceName Start SERVICE_AUTO_START
    & $nssmPath set $ServiceName AppDirectory $PWD
    & $nssmPath set $ServiceName AppStdout "$PWD\logs\service.log"
    & $nssmPath set $ServiceName AppStderr "$PWD\logs\service-error.log"
    & $nssmPath set $ServiceName AppRotateFiles 1
    & $nssmPath set $ServiceName AppRotateOnline 1
    & $nssmPath set $ServiceName AppRotateSeconds 86400
    & $nssmPath set $ServiceName AppRotateBytes 10485760
    
    Write-Log 'Starting service'
    & $nssmPath start $ServiceName
    
    if ($LASTEXITCODE -eq 0) { Write-Log 'Service installed and started successfully' }
    else { throw "Service installation failed with exit code $LASTEXITCODE" }
}

# ─── GUI management ────────────────────────────────────────────────────
function Start-GUI {
    Write-Log 'Starting GUI monitor'
    try {
        Start-Process -FilePath 'python' -ArgumentList 'gui_monitor.py' -WindowStyle Hidden
        Write-Log 'GUI monitor started successfully'
    } catch { Write-Log "GUI startup failed: $_" 'WARN' }
}

# ─── main installation phases ──────────────────────────────────────────
function Install-Phase1-Python {
    Write-Log "=== PHASE 1: Python & Dependencies ==="
    
    $pythonVer = Get-PythonVers
    if ($pythonVer) {
        Write-Log "Python $pythonVer is installed"
        if ([version]$pythonVer -lt [version]"$RequiredPythonVersion.0") {
            Write-Log "Python version $pythonVer is too old, installing $RequiredPythonVersion"
            Install-Python
        }
    } else {
        Write-Log "Python not found, installing $RequiredPythonVersion"
        Install-Python
    }
    
    Install-Dependencies
    Write-Log "Phase 1 completed successfully"
}

function Install-Phase2-Tools {
    Write-Log "=== PHASE 2: Tools & Service Manager ==="
    
    Install-UnRAR
    Install-NSSM
    
    Write-Log "Phase 2 completed successfully"
}

function Install-Phase3-Service {
    Write-Log "=== PHASE 3: Windows Service ==="
    
    Install-Service
    
    Write-Log "Phase 3 completed successfully"
}

function Install-Phase4-GUI {
    Write-Log "=== PHASE 4: GUI Monitor ==="
    
    if (!$NoGui) {
        Start-GUI
    } else {
        Write-Log "GUI disabled via -NoGui parameter"
    }
    
    Write-Log "Phase 4 completed successfully"
}

# ─── main execution ────────────────────────────────────────────────────
function Main {
    Write-Log "Starting $AppName v$AppVersion installation"
    Write-Log "Log file: $LogPath"
    
    # Check prerequisites
    if (!(Test-Admin)) {
        Write-Log 'ERROR: This script requires administrator privileges' 'ERROR'
        throw 'Run as Administrator'
    }
    
    if (!(Has-Internet)) {
        Write-Log 'ERROR: Internet connection required for installation' 'ERROR'
        throw 'No internet connection'
    }
    
    try {
        Install-Phase1-Python
        Install-Phase2-Tools
        Install-Phase3-Service
        Install-Phase4-GUI
        
        Write-Log "=== INSTALLATION COMPLETE ==="
        Write-Log "Successfully installed $AppName v$AppVersion"
        Write-Log "Service: $ServiceName"
        Write-Log "Processing Mode: $ProcessingMode"
        Write-Log "Enhanced UPnP support included"
        Write-Log "Log file: $LogPath"
        
        return 0
        
    } catch {
        Write-Log "Installation failed: $_" 'ERROR'
        Write-Log "Check log file for details: $LogPath" 'ERROR'
        return 1
    }
}

# Run main installation
exit (Main)