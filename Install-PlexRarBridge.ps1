# =====================================================================
#  Install-PlexRarBridge.ps1   v2.2.0  (2025-07-15)
#  Robust installer for Plex-RAR-Bridge with proper file deployment
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
$AppVersion            = '2.2.0'
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
    $tempNssmPath = '.\nssm\nssm.exe'
    
    if (!(Test-Path $tempNssmPath)) {
        $url = 'https://nssm.cc/release/nssm-2.24.zip'
        $zipPath = "$env:TEMP\nssm.zip"
        
        Write-Log "Downloading NSSM from $url"
        Invoke-WebRequest -Uri $url -OutFile $zipPath
        
        Write-Log "Extracting NSSM"
        Expand-Archive -Path $zipPath -DestinationPath $env:TEMP -Force
        
        New-Item -ItemType Directory -Path '.\nssm' -Force | Out-Null
        Copy-Item -Path "$env:TEMP\nssm-2.24\win64\nssm.exe" -Destination $tempNssmPath
        
        Remove-Item -Path $zipPath -Force
        Remove-Item -Path "$env:TEMP\nssm-2.24" -Recurse -Force
        
        Write-Log "NSSM downloaded and prepared for deployment"
    }
}

function Install-Service {
    Write-Log 'Installing Windows Service'
    $nssmPath = Join-Path $InstallPath 'nssm\nssm.exe'
    $pythonPath = (Get-Command python).Source
    $scriptPath = Join-Path $InstallPath 'plex_rar_bridge.py'
    
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
    & $nssmPath set $ServiceName AppDirectory $InstallPath
    & $nssmPath set $ServiceName AppStdout "$InstallPath\logs\service.log"
    & $nssmPath set $ServiceName AppStderr "$InstallPath\logs\service-error.log"
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
        $guiScriptPath = Join-Path $InstallPath 'gui_monitor.py'
        Start-Process -FilePath 'python' -ArgumentList $guiScriptPath -WindowStyle Hidden -WorkingDirectory $InstallPath
        Write-Log 'GUI monitor started successfully'
    } catch { Write-Log "GUI startup failed: $_" 'WARN' }
}

# ─── file deployment ────────────────────────────────────────────────────
function Deploy-ApplicationFiles {
    Write-Log "Deploying application files to $InstallPath"
    
    # Create installation directory
    if (!(Test-Path $InstallPath)) {
        New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
        Write-Log "Created installation directory: $InstallPath"
    }
    
    # List of files and directories to copy
    $filesToCopy = @(
        'plex_rar_bridge.py',
        'python_rar_vfs.py', 
        'enhanced_setup_panel.py',
        'gui_monitor.py',
        'upnp_port_manager.py',
        'rar2fs_handler.py',
        'ftp_pycurl_handler.py',
        'monitor_service.py',
        'config.yaml',
        'setup_config.json',
        'enhanced_setup_config.json',
        'ftp_config.json',
        'config.yaml.template',
        'requirements.txt',
        'UnRAR.exe',
        'README.md',
        'license.txt'
    )
    
    $directoriesToCopy = @(
        'docs',
        'nssm'
    )
    
    # Copy files
    foreach ($file in $filesToCopy) {
        if (Test-Path $file) {
            $destPath = Join-Path $InstallPath $file
            Copy-Item -Path $file -Destination $destPath -Force
            Write-Log "Copied: $file"
        } else {
            Write-Log "Warning: File not found: $file" 'WARN'
        }
    }
    
    # Copy directories
    foreach ($dir in $directoriesToCopy) {
        if (Test-Path $dir) {
            $destPath = Join-Path $InstallPath $dir
            Copy-Item -Path $dir -Destination $destPath -Recurse -Force
            Write-Log "Copied directory: $dir"
        } else {
            Write-Log "Warning: Directory not found: $dir" 'WARN'
        }
    }
    
    # Create required directories
    $requiredDirs = @('logs', 'data', 'work', 'failed', 'archive', 'thumbnails_cache')
    foreach ($dir in $requiredDirs) {
        $dirPath = Join-Path $InstallPath $dir
        if (!(Test-Path $dirPath)) {
            New-Item -ItemType Directory -Path $dirPath -Force | Out-Null
            Write-Log "Created directory: $dir"
        }
    }
    
    Write-Log "Application files deployed successfully"
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

function Install-Phase3-Deploy {
    Write-Log "=== PHASE 3: Application Deployment ==="
    
    Deploy-ApplicationFiles
    
    Write-Log "Phase 3 completed successfully"
}

function Install-Phase4-Service {
    Write-Log "=== PHASE 4: Windows Service ==="
    
    Install-Service
    
    Write-Log "Phase 4 completed successfully"
}

function Install-Phase5-GUI {
    Write-Log "=== PHASE 5: GUI Monitor ==="
    
    if (!$NoGui) {
        Start-GUI
    } else {
        Write-Log "GUI disabled via -NoGui parameter"
    }
    
    Write-Log "Phase 5 completed successfully"
}

# ─── uninstall management ──────────────────────────────────────────────
function Uninstall-Service {
    Write-Log "Uninstalling $ServiceName service"
    
    try {
        # Try to use NSSM from installation directory first
        $nssmPath = Join-Path $InstallPath 'nssm\nssm.exe'
        if (!(Test-Path $nssmPath)) {
            # Fallback to current directory
            $nssmPath = '.\nssm\nssm.exe'
        }
        
        if (Test-Path $nssmPath) {
            & $nssmPath stop $ServiceName 2>$null
            & $nssmPath remove $ServiceName confirm 2>$null
            Write-Log "Service removed using NSSM"
        } else {
            # Try using SC command as fallback
            & sc.exe stop $ServiceName 2>$null
            & sc.exe delete $ServiceName 2>$null
            Write-Log "Service removed using SC command"
        }
    } catch {
        Write-Log "Error removing service: $_" 'WARN'
    }
}

function Remove-InstallationFiles {
    Write-Log "Removing installation files from $InstallPath"
    
    if (Test-Path $InstallPath) {
        try {
            # Stop any running processes first
            Get-Process | Where-Object { $_.Path -like "$InstallPath\*" } | Stop-Process -Force -ErrorAction SilentlyContinue
            
            # Remove the installation directory
            Remove-Item -Path $InstallPath -Recurse -Force
            Write-Log "Installation directory removed successfully"
        } catch {
            Write-Log "Error removing installation directory: $_" 'WARN'
            Write-Log "You may need to manually remove: $InstallPath" 'WARN'
        }
    } else {
        Write-Log "Installation directory not found: $InstallPath"
    }
}

function Uninstall-Application {
    Write-Log "Starting $AppName uninstallation"
    
    try {
        Uninstall-Service
        Remove-InstallationFiles
        
        Write-Log "=== UNINSTALLATION COMPLETE ==="
        Write-Log "$AppName has been removed successfully"
        return 0
        
    } catch {
        Write-Log "Uninstallation failed: $_" 'ERROR'
        return 1
    }
}

# ─── main execution ────────────────────────────────────────────────────
function Main {
    Write-Log "Starting $AppName v$AppVersion installation"
    Write-Log "Installation Path: $InstallPath"
    Write-Log "Log file: $LogPath"
    
    # Handle uninstall
    if ($Uninstall) {
        return (Uninstall-Application)
    }
    
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
        Install-Phase3-Deploy
        Install-Phase4-Service
        Install-Phase5-GUI
        
        Write-Log "=== INSTALLATION COMPLETE ==="
        Write-Log "Successfully installed $AppName v$AppVersion"
        Write-Log "Installation Path: $InstallPath"
        Write-Log "Service: $ServiceName"
        Write-Log "Processing Mode: $ProcessingMode"
        Write-Log "Enhanced UPnP support included"
        Write-Log "Log file: $LogPath"
        Write-Log ""
        Write-Log "The service is now running from: $InstallPath"
        Write-Log "All configuration files are located in the installation directory"
        
        return 0
        
    } catch {
        Write-Log "Installation failed: $_" 'ERROR'
        Write-Log "Check log file for details: $LogPath" 'ERROR'
        return 1
    }
}

# Run main installation
exit (Main)