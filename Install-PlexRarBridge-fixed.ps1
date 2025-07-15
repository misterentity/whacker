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
    Invoke-WebRequest -Uri $u -OutFile $e
    Write-Log "Running Python installer: $e"
    Start-Process -FilePath $e -ArgumentList '/quiet','InstallAllUsers=1','PrependPath=1' -Wait
    
    if ($LASTEXITCODE -eq 0) { 
        Write-Log 'Python installed successfully'
        # Refresh PATH
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
    } else {
        throw "Python installation failed with exit code $LASTEXITCODE"
    }
}

function Install-Dependencies {
    Write-Log "Installing Python dependencies..."
    
    # Upgrade pip first
    Write-Log "Upgrading pip..."
    & python -m pip install --upgrade pip
    
    # Install required packages
    $packages = @(
        'pyyaml',
        'requests',
        'psutil',
        'watchdog',
        'rarfile',
        'Pillow',
        'pycurl'
    )
    
    foreach ($package in $packages) {
        Write-Log "Installing $package..."
        & python -m pip install $package
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to install $package"
        }
    }
    
    Write-Log "All dependencies installed successfully"
}

# ─── service management ────────────────────────────────────────────────
function Stop-ServiceSafe {
    param([string]$ServiceName)
    
    Write-Log "Stopping service $ServiceName..."
    try {
        $result = & sc.exe stop $ServiceName 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Service $ServiceName stopped successfully"
            Start-Sleep -Seconds 2
        } else {
            Write-Log "Service $ServiceName was not running or failed to stop" 'WARN'
        }
    } catch {
        Write-Log "Error stopping service: $_" 'WARN'
    }
}

function Remove-ServiceSafe {
    param([string]$ServiceName)
    
    Write-Log "Removing service $ServiceName..."
    try {
        $result = & sc.exe delete $ServiceName 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Service $ServiceName removed successfully"
        } else {
            Write-Log "Service $ServiceName was not found or failed to remove" 'WARN'
        }
    } catch {
        Write-Log "Error removing service: $_" 'WARN'
    }
}

# ─── main installation logic ────────────────────────────────────────────
function Install-PlexRarBridge {
    Write-Log "Starting $AppName installation..."
    
    # Check prerequisites
    if (!(Test-Admin)) {
        Write-Log "Administrator privileges required. Please run as administrator." 'ERROR'
        throw "Administrator privileges required"
    }
    
    if (!(Has-Internet)) {
        Write-Log "Internet connection required for installation" 'ERROR'
        throw "Internet connection required"
    }
    
    # Check Python installation
    $pythonVersion = Get-PythonVers
    if (!$pythonVersion) {
        Write-Log "Python not found. Installing Python $RequiredPythonVersion..."
        Install-Python
        $pythonVersion = Get-PythonVers
    }
    
    if (!$pythonVersion) {
        throw "Failed to install or detect Python"
    }
    
    Write-Log "Python version: $pythonVersion"
    
    # Install dependencies
    Install-Dependencies
    
    # Stop and remove existing service if upgrading
    Stop-ServiceSafe -ServiceName $ServiceName
    Remove-ServiceSafe -ServiceName $ServiceName
    
    # Create installation directory
    Write-Log "Creating installation directory: $InstallPath"
    if (!(Test-Path $InstallPath)) {
        New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
    }
    
    # Copy application files
    Write-Log "Copying application files..."
    $filesToCopy = @(
        'plex_rar_bridge.py',
        'gui_monitor.py',
        'enhanced_setup_panel.py',
        'python_rar_vfs.py',
        'rar2fs_handler.py',
        'rar2fs_installer.py',
        'upnp_port_manager.py',
        'ftp_pycurl_handler.py',
        'monitor_service.py',
        'setup.py',
        'UnRAR.exe',
        'requirements.txt',
        'config.yaml',
        'config.yaml.template',
        'config-enhanced.yaml',
        'ftp_config.json',
        'setup_config.json'
    )
    
    foreach ($file in $filesToCopy) {
        if (Test-Path $file) {
            Write-Log "Copying $file..."
            Copy-Item -Path $file -Destination $InstallPath -Force
        } else {
            Write-Log "Warning: $file not found" 'WARN'
        }
    }
    
    # Copy documentation
    if (Test-Path 'docs') {
        Write-Log "Copying documentation..."
        Copy-Item -Path 'docs' -Destination $InstallPath -Recurse -Force
    }
    
    # Install and configure NSSM
    Install-NSSM
    
    # Create and start service
    Create-Service
    
    Write-Log "$AppName installation completed successfully!"
    Write-Log "Service '$ServiceName' has been installed and started"
    Write-Log "Access the GUI monitor by running: python `"$InstallPath\gui_monitor.py`""
    
    # Launch GUI if not in NoGui mode
    if (!$NoGui) {
        Write-Log "Launching GUI monitor..."
        Start-Process -FilePath 'python' -ArgumentList "`"$InstallPath\gui_monitor.py`"" -NoNewWindow
    }
}

function Install-NSSM {
    Write-Log "Installing NSSM (Non-Sucking Service Manager)..."
    
    $nssmPath = "$InstallPath\nssm.exe"
    $nssmUrl = "https://nssm.cc/release/nssm-2.24.zip"
    $nssmZip = "$env:TEMP\nssm.zip"
    
    try {
        # Download NSSM
        Write-Log "Downloading NSSM from $nssmUrl..."
        Invoke-WebRequest -Uri $nssmUrl -OutFile $nssmZip
        
        # Extract NSSM
        Write-Log "Extracting NSSM..."
        $extractPath = "$env:TEMP\nssm_extract"
        if (Test-Path $extractPath) {
            Remove-Item -Path $extractPath -Recurse -Force
        }
        
        Expand-Archive -Path $nssmZip -DestinationPath $extractPath -Force
        
        # Copy the appropriate NSSM executable
        $nssmExe = "$extractPath\nssm-2.24\win64\nssm.exe"
        if (Test-Path $nssmExe) {
            Copy-Item -Path $nssmExe -Destination $nssmPath -Force
            Write-Log "NSSM installed successfully"
        } else {
            throw "NSSM executable not found in extracted archive"
        }
        
        # Clean up
        Remove-Item -Path $nssmZip -Force -ErrorAction SilentlyContinue
        Remove-Item -Path $extractPath -Recurse -Force -ErrorAction SilentlyContinue
        
    } catch {
        Write-Log "Failed to install NSSM: $_" 'ERROR'
        throw "NSSM installation failed: $_"
    }
}

function Create-Service {
    Write-Log "Creating Windows service..."
    
    $nssmPath = "$InstallPath\nssm.exe"
    $pythonPath = (Get-Command python).Source
    $scriptPath = "$InstallPath\plex_rar_bridge.py"
    
    try {
        # Install service
        Write-Log "Installing service with NSSM..."
        & $nssmPath install $ServiceName $pythonPath $scriptPath
        
        if ($LASTEXITCODE -ne 0) {
            throw "NSSM install failed with exit code $LASTEXITCODE"
        }
        
        # Configure service
        Write-Log "Configuring service..."
        & $nssmPath set $ServiceName DisplayName "$AppName Service"
        & $nssmPath set $ServiceName Description "Plex RAR Bridge - Automated RAR extraction and Plex integration"
        & $nssmPath set $ServiceName Start SERVICE_AUTO_START
        & $nssmPath set $ServiceName AppDirectory $InstallPath
        
        # Start service
        Write-Log "Starting service..."
        & sc.exe start $ServiceName
        
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Service started successfully"
        } else {
            Write-Log "Service failed to start - check configuration" 'WARN'
        }
        
    } catch {
        Write-Log "Failed to create service: $_" 'ERROR'
        throw "Service creation failed: $_"
    }
}

# ─── main execution ────────────────────────────────────────────────────
try {
    Write-Log "=== $AppName Installer v$AppVersion ==="
    Install-PlexRarBridge
} catch {
    Write-Log "Installation failed: $_" 'ERROR'
    Write-Host "Installation failed. Check the log at: $LogPath" -ForegroundColor Red
    exit 1
}
