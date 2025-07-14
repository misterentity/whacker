#!/usr/bin/env powershell
<#
.SYNOPSIS
    Professional Installation Script for Plex RAR Bridge
.DESCRIPTION
    Installs Plex RAR Bridge to Program Files with proper configuration and service setup.
    Auto-detects Plex settings and guides users through essential configuration.
.PARAMETER InstallPath
    Custom installation path (default: C:\Program Files\PlexRarBridge)
.PARAMETER ServiceName
    Custom service name (default: PlexRarBridge)
.PARAMETER WatchDirectory
    Directory to monitor for RAR files
.PARAMETER TargetDirectory
    Directory where extracted files will be moved
.PARAMETER PlexHost
    Plex server URL (auto-detected if running)
.PARAMETER PlexToken
    Plex authentication token (auto-detected if possible)
.PARAMETER PlexLibraryKey
    Plex library section key (auto-detected if possible)
.PARAMETER Uninstall
    Uninstall the application and service
.PARAMETER NoGui
    Skip launching the GUI monitor after installation
.EXAMPLE
    .\Install-PlexRarBridge.ps1
.EXAMPLE
    .\Install-PlexRarBridge.ps1 -InstallPath "C:\Custom\Path" -ServiceName "CustomRarBridge"
.EXAMPLE
    .\Install-PlexRarBridge.ps1 -Uninstall
.EXAMPLE
    .\Install-PlexRarBridge.ps1 -NoGui
#>

[CmdletBinding()]
param(
    [string]$InstallPath = "C:\Program Files\PlexRarBridge",
    [string]$ServiceName = "PlexRarBridge",
    [string]$WatchDirectory = "",
    [string]$TargetDirectory = "",
    [string]$PlexHost = "",
    [string]$PlexToken = "",
    [string]$PlexLibraryKey = "",
    [switch]$Uninstall,
    [switch]$NoGui
)

# Script configuration
$ErrorActionPreference = "Stop"
$ProgressPreference = "Continue"

# Application metadata
$AppName = "Plex RAR Bridge"
$AppVersion = "2.0.0"
$GitHubRepo = "https://github.com/user/plex-rar-bridge"
$RequiredPythonVersion = "3.8"

# Logging setup
$LogPath = "$env:TEMP\PlexRarBridge-Install.log"
$StartTime = Get-Date

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    Write-Host $logEntry
    $logEntry | Out-File -FilePath $LogPath -Append -Encoding UTF8
}

function Test-AdminPrivileges {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Test-InternetConnection {
    try {
        $null = Invoke-WebRequest -Uri "https://www.google.com" -UseBasicParsing -TimeoutSec 10
        return $true
    } catch {
        return $false
    }
}

function Get-PythonVersion {
    try {
        $pythonVersion = & python --version 2>&1
        if ($pythonVersion -match "Python (\d+\.\d+\.\d+)") {
            return $matches[1]
        }
        return $null
    } catch {
        return $null
    }
}

function Install-Python {
    Write-Log "Installing Python $RequiredPythonVersion..." "INFO"
    
    # Try winget first
    try {
        $result = & winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Python installed successfully via winget" "INFO"
            return
        }
    } catch {
        Write-Log "Winget installation failed, trying direct download..." "WARN"
    }
    
    # Fallback to direct download
    try {
        $pythonUrl = "https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe"
        $pythonInstaller = "$env:TEMP\python-installer.exe"
        
        Write-Log "Downloading Python installer..." "INFO"
        Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonInstaller
        
        Write-Log "Installing Python..." "INFO"
        Start-Process -FilePath $pythonInstaller -ArgumentList "/quiet", "InstallAllUsers=1", "PrependPath=1" -Wait
        
        Remove-Item $pythonInstaller -Force
        Write-Log "Python installed successfully" "INFO"
    } catch {
        throw "Failed to install Python: $_"
    }
}

function Install-Dependencies {
    Write-Log "Installing Python dependencies..." "INFO"
    
    try {
        # Install required packages
        Write-Log "Upgrading pip..." "INFO"
        & pip install --upgrade pip
        
        Write-Log "Installing Python packages..." "INFO"
        & pip install pyyaml requests watchdog pywin32
        
        # Test that key dependencies are available
        Write-Log "Verifying dependencies..." "INFO"
        & python -c "import yaml, requests, watchdog; print('All dependencies verified')"
        
        Write-Log "Dependencies installed successfully" "INFO"
    } catch {
        throw "Failed to install dependencies: $_"
    }
}

function Install-UnRAR {
    Write-Log "Installing UnRAR..." "INFO"
    
    try {
        $unrarUrl = "https://www.rarlab.com/rar/unrarw32.exe"
        $unrarInstaller = "$env:TEMP\unrar-installer.exe"
        
        # Download and install UnRAR
        Invoke-WebRequest -Uri $unrarUrl -OutFile $unrarInstaller
        Start-Process -FilePath $unrarInstaller -ArgumentList "/S" -Wait
        Remove-Item $unrarInstaller -Force
        
        # Copy UnRAR.exe to installation directory
        $unrarPath = "${env:ProgramFiles}\WinRAR\UnRAR.exe"
        if (Test-Path $unrarPath) {
            Copy-Item $unrarPath "$InstallPath\UnRAR.exe" -Force
            Write-Log "UnRAR installed and copied to installation directory" "INFO"
        } else {
            throw "UnRAR installation failed - executable not found"
        }
    } catch {
        throw "Failed to install UnRAR: $_"
    }
}

function Install-NSSM {
    Write-Log "Installing NSSM (Non-Sucking Service Manager)..." "INFO"
    
    try {
        $nssmUrl = "https://nssm.cc/release/nssm-2.24.zip"
        $nssmZip = "$env:TEMP\nssm.zip"
        $nssmExtract = "$env:TEMP\nssm"
        
        # Download and extract NSSM
        Invoke-WebRequest -Uri $nssmUrl -OutFile $nssmZip
        Expand-Archive -Path $nssmZip -DestinationPath $nssmExtract -Force
        
        # Copy appropriate architecture version
        $architecture = if ([Environment]::Is64BitOperatingSystem) { "win64" } else { "win32" }
        $nssmExe = "$nssmExtract\nssm-2.24\$architecture\nssm.exe"
        
        if (Test-Path $nssmExe) {
            Copy-Item $nssmExe "$InstallPath\nssm.exe" -Force
            Write-Log "NSSM installed successfully" "INFO"
        } else {
            throw "NSSM executable not found after extraction"
        }
        
        # Cleanup
        Remove-Item $nssmZip -Force
        Remove-Item $nssmExtract -Recurse -Force
    } catch {
        throw "Failed to install NSSM: $_"
    }
}

function Find-PlexToken {
    Write-Log "Attempting to auto-detect Plex token..." "INFO"
    
    try {
        # Common Plex data locations with more comprehensive paths
        $plexDataPaths = @(
            "$env:LOCALAPPDATA\Plex Media Server",
            "$env:APPDATA\Plex Media Server", 
            "${env:ProgramFiles}\Plex\Plex Media Server\Data",
            "${env:ProgramFiles(x86)}\Plex\Plex Media Server\Data",
            "${env:ProgramFiles}\Plex Media Server\Data",
            "${env:ProgramFiles(x86)}\Plex Media Server\Data",
            "C:\ProgramData\Plex Media Server\Data",
            "$env:USERPROFILE\AppData\Local\Plex Media Server",
            "$env:USERPROFILE\AppData\Roaming\Plex Media Server"
        )
        
        Write-Log "Searching for Plex token in $($plexDataPaths.Count) potential locations..." "INFO"
        
        foreach ($dataPath in $plexDataPaths) {
            Write-Log "Checking path: $dataPath" "INFO"
            
            if (Test-Path $dataPath) {
                Write-Log "Path exists: $dataPath" "INFO"
                
                $prefsPath = Join-Path $dataPath "Preferences.xml"
                Write-Log "Looking for preferences file: $prefsPath" "INFO"
                
                if (Test-Path $prefsPath) {
                    Write-Log "Found Plex preferences file at: $prefsPath" "INFO"
                    
                    try {
                        $prefsContent = Get-Content $prefsPath -Raw -ErrorAction Stop
                        Write-Log "Successfully read preferences file (length: $($prefsContent.Length) characters)" "INFO"
                        
                        # Multiple token patterns to try
                        $tokenPatterns = @(
                            'PlexOnlineToken="([^"]+)"',
                            'PlexOnlineToken=''([^'']+)''',
                            'PlexOnlineToken=([A-Za-z0-9_-]+)',
                            'token="([^"]+)"',
                            'token=''([^'']+)''',
                            'X-Plex-Token="([^"]+)"',
                            'X-Plex-Token=''([^'']+)'''
                        )
                        
                        foreach ($pattern in $tokenPatterns) {
                            if ($prefsContent -match $pattern) {
                                $token = $matches[1]
                                if ($token -and $token.Length -gt 10) {
                                    Write-Log "Auto-detected Plex token using pattern: $pattern" "INFO"
                                    Write-Log "Token length: $($token.Length) characters" "INFO"
                                    return $token
                                }
                            }
                        }
                        
                        Write-Log "No token patterns matched in preferences file" "WARN"
                        
                        # Debug: Show first 500 characters of prefs file
                        $debugContent = if ($prefsContent.Length -gt 500) { $prefsContent.Substring(0, 500) } else { $prefsContent }
                        Write-Log "Preferences file content preview: $debugContent" "INFO"
                        
                    } catch {
                        Write-Log "Error reading preferences file: $_" "WARN"
                    }
                } else {
                    Write-Log "Preferences file not found at: $prefsPath" "INFO"
                }
            } else {
                Write-Log "Path does not exist: $dataPath" "INFO"
            }
        }
        
        # Try alternative method - check registry
        Write-Log "Trying registry-based token detection..." "INFO"
        try {
            $regPaths = @(
                "HKCU:\Software\Plex, Inc.\Plex Media Server",
                "HKLM:\Software\Plex, Inc.\Plex Media Server",
                "HKCU:\Software\Plex",
                "HKLM:\Software\Plex"
            )
            
            foreach ($regPath in $regPaths) {
                if (Test-Path $regPath) {
                    Write-Log "Checking registry path: $regPath" "INFO"
                    $regKeys = Get-ItemProperty -Path $regPath -ErrorAction SilentlyContinue
                    if ($regKeys) {
                        foreach ($key in $regKeys.PSObject.Properties) {
                            if ($key.Name -like "*token*" -or $key.Name -like "*Token*") {
                                Write-Log "Found potential token in registry: $($key.Name)" "INFO"
                                if ($key.Value -and $key.Value.Length -gt 10) {
                                    Write-Log "Auto-detected Plex token from registry" "INFO"
                                    return $key.Value
                                }
                            }
                        }
                    }
                }
            }
        } catch {
            Write-Log "Registry token detection failed: $_" "WARN"
        }
        
        # Try finding token in Plex database files
        Write-Log "Trying database-based token detection..." "INFO"
        foreach ($dataPath in $plexDataPaths) {
            if (Test-Path $dataPath) {
                $dbPath = Join-Path $dataPath "Plug-in Support\Databases\com.plexapp.plugins.library.db"
                if (Test-Path $dbPath) {
                    Write-Log "Found Plex database at: $dbPath" "INFO"
                    # Note: This would require SQLite tools to query properly
                    # For now, just note that we found the database
                }
            }
        }
        
        Write-Log "Could not auto-detect Plex token from any source" "WARN"
        return $null
        
    } catch {
        Write-Log "Error during Plex token detection: $_" "WARN"
        return $null
    }
}

function Get-PlexLibraries {
    param([string]$PlexHost, [string]$PlexToken)
    
    Write-Log "Fetching Plex libraries from $PlexHost..." "INFO"
    
    if (-not $PlexToken) {
        Write-Log "No Plex token provided - cannot fetch libraries" "WARN"
        return @()
    }
    
    try {
        # Test connection first
        Write-Log "Testing Plex server connection..." "INFO"
        $testUrl = "$PlexHost/identity"
        $testResponse = Invoke-WebRequest -Uri $testUrl -UseBasicParsing -TimeoutSec 5
        Write-Log "Plex server connection test: HTTP $($testResponse.StatusCode)" "INFO"
        
        # Try to get libraries
        $headers = @{
            'X-Plex-Token' = $PlexToken
            'Accept' = 'application/json'
        }
        
        $libraryUrl = "$PlexHost/library/sections"
        Write-Log "Requesting libraries from: $libraryUrl" "INFO"
        
        $response = Invoke-RestMethod -Uri $libraryUrl -Headers $headers -TimeoutSec 15
        Write-Log "Successfully received response from Plex API" "INFO"
        
        $libraries = @()
        
        # Handle different response formats
        if ($response.MediaContainer -and $response.MediaContainer.Directory) {
            Write-Log "Processing MediaContainer.Directory format" "INFO"
            foreach ($section in $response.MediaContainer.Directory) {
                $locations = @()
                if ($section.Location) {
                    if ($section.Location -is [array]) {
                        $locations = $section.Location | ForEach-Object { $_.path }
                    } else {
                        $locations = @($section.Location.path)
                    }
                }
                
                $libraries += @{
                    Key = $section.key
                    Title = $section.title
                    Type = $section.type
                    Location = $locations -join ', '
                }
                
                Write-Log "Found library: $($section.title) (Type: $($section.type), Key: $($section.key))" "INFO"
            }
        } elseif ($response -is [array]) {
            Write-Log "Processing array format response" "INFO"
            foreach ($section in $response) {
                $libraries += @{
                    Key = $section.key
                    Title = $section.title
                    Type = $section.type
                    Location = $section.Location.path -join ', '
                }
            }
        } else {
            Write-Log "Unknown response format from Plex API" "WARN"
            Write-Log "Response type: $($response.GetType().Name)" "INFO"
        }
        
        Write-Log "Found $($libraries.Count) Plex libraries total" "INFO"
        return $libraries
        
    } catch {
        Write-Log "Could not fetch Plex libraries: $_" "WARN"
        Write-Log "Error details: $($_.Exception.Message)" "WARN"
        
        # Try alternative API endpoints
        try {
            Write-Log "Trying alternative Plex API endpoint..." "INFO"
            $altUrl = "$PlexHost/library/sections.json"
            $altResponse = Invoke-RestMethod -Uri $altUrl -Headers $headers -TimeoutSec 10
            Write-Log "Alternative endpoint succeeded" "INFO"
            
            # Process alternative response format
            if ($altResponse.MediaContainer -and $altResponse.MediaContainer.Directory) {
                $libraries = @()
                foreach ($section in $altResponse.MediaContainer.Directory) {
                    $libraries += @{
                        Key = $section.key
                        Title = $section.title
                        Type = $section.type
                        Location = $section.Location.path -join ', '
                    }
                }
                Write-Log "Found $($libraries.Count) libraries from alternative endpoint" "INFO"
                return $libraries
            }
        } catch {
            Write-Log "Alternative endpoint also failed: $_" "WARN"
        }
        
        return @()
    }
}

function Get-PlexServerInfo {
    Write-Log "Discovering Plex server information..." "INFO"
    
    # Try to discover Plex server automatically
    try {
        $plexProcesses = Get-Process -Name "*Plex*" -ErrorAction SilentlyContinue
        if ($plexProcesses) {
            Write-Log "Found Plex processes running" "INFO"
            
            # Test common ports
            $testPorts = @(32400, 32401, 32402)
            foreach ($port in $testPorts) {
                try {
                    $testUrl = "http://127.0.0.1:$port"
                    $response = Invoke-WebRequest -Uri "$testUrl/identity" -UseBasicParsing -TimeoutSec 5
                    if ($response.StatusCode -eq 200) {
                        Write-Log "Found Plex server at $testUrl" "INFO"
                        return @{
                            Host = $testUrl
                            Port = $port
                            Status = "Running"
                        }
                    }
                } catch {
                    # Continue testing other ports
                }
            }
        }
    } catch {
        Write-Log "Plex server discovery failed: $_" "WARN"
    }
    
    # Return default if discovery fails
    return @{
        Host = "http://127.0.0.1:32400"
        Port = 32400
        Status = "Unknown"
    }
}

function Get-UserConfiguration {
    Write-Log "Collecting user configuration..." "INFO"
    
    # Get Plex server info
    $plexInfo = Get-PlexServerInfo
    
    # Auto-detect Plex token
    $detectedToken = Find-PlexToken
    
    Write-Host "`n" -NoNewline
    Write-Host "===================================================================================" -ForegroundColor Cyan
    Write-Host "                                                                                   " -ForegroundColor Cyan
    Write-Host "                            Configuration Wizard                                  " -ForegroundColor Cyan
    Write-Host "                                                                                   " -ForegroundColor Cyan
    Write-Host "===================================================================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Directory configuration
    Write-Host "Directory Configuration:" -ForegroundColor Yellow
    Write-Host "--------------------------------------------------------------------------------"
    
    if (-not $WatchDirectory) {
        Write-Host "Enter the directory where RAR files will arrive (watch directory):"
        $WatchDirectory = Read-Host "Watch Directory"
        while (-not $WatchDirectory -or -not (Test-Path $WatchDirectory -IsValid)) {
            Write-Host "Invalid directory path. Please try again." -ForegroundColor Red
            $WatchDirectory = Read-Host "Watch Directory"
        }
    }
    
    if (-not $TargetDirectory) {
        Write-Host "`nEnter the directory where extracted files should go (usually your Plex library folder):"
        $TargetDirectory = Read-Host "Target Directory"
        while (-not $TargetDirectory -or -not (Test-Path $TargetDirectory -IsValid)) {
            Write-Host "Invalid directory path. Please try again." -ForegroundColor Red
            $TargetDirectory = Read-Host "Target Directory"
        }
    }
    
    # Plex configuration
    Write-Host "`nPlex Configuration:" -ForegroundColor Yellow
    Write-Host "--------------------------------------------------------------------------------"
    
    if (-not $PlexHost) {
        Write-Host "Plex server URL (detected: $($plexInfo.Host)):"
        $input = Read-Host "Press Enter to use detected, or enter custom URL"
        $PlexHost = if ($input) { $input } else { $plexInfo.Host }
    }
    
    if (-not $PlexToken) {
        if ($detectedToken) {
            Write-Host "Plex token auto-detected!" -ForegroundColor Green
            Write-Host "Token found: $($detectedToken.Substring(0, 8))..." -ForegroundColor Gray
            $PlexToken = $detectedToken
        } else {
            Write-Host ""
            Write-Host "Could not auto-detect Plex token. Manual configuration required." -ForegroundColor Red
            Write-Host ""
            Write-Host "Token detection checked:" -ForegroundColor Yellow
            Write-Host "  - Multiple Plex data directories"
            Write-Host "  - Preferences.xml files"
            Write-Host "  - Windows registry entries"
            Write-Host "  - Various token formats"
            Write-Host ""
            Write-Host "How to find your Plex token manually:" -ForegroundColor Cyan
            Write-Host "  1. Open Plex web interface ($PlexHost)"
            Write-Host "  2. Go to Settings -> General -> Network"
            Write-Host "  3. Click 'Show Advanced' at the top"
            Write-Host "  4. Copy the 'Plex Token' value"
            Write-Host "  5. Alternative: https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/" -ForegroundColor Gray
            Write-Host ""
            Write-Host "Troubleshooting tips:" -ForegroundColor Yellow
            Write-Host "  - Make sure Plex Media Server is running"
            Write-Host "  - Check that you're signed in to Plex"
            Write-Host "  - Token should be 20+ characters long"
            Write-Host "  - Check the installation log for detailed search results"
            Write-Host ""
            do {
                $PlexToken = Read-Host "Enter Plex Token"
                if (-not $PlexToken) {
                    Write-Host "Token is required to continue. Please enter your Plex token." -ForegroundColor Red
                } elseif ($PlexToken.Length -lt 10) {
                    Write-Host "Token seems too short. Please verify you copied the complete token." -ForegroundColor Red
                    $PlexToken = $null
                }
            } while (-not $PlexToken)
        }
    }
    
    # Get libraries and let user choose
    if (-not $PlexLibraryKey) {
        $libraries = Get-PlexLibraries -PlexHost $PlexHost -PlexToken $PlexToken
        
        if ($libraries.Count -gt 0) {
            Write-Host "`nAvailable Plex Libraries:" -ForegroundColor Green
            for ($i = 0; $i -lt $libraries.Count; $i++) {
                $lib = $libraries[$i]
                Write-Host "  $($i + 1). $($lib.Title) (Type: $($lib.Type), Key: $($lib.Key))"
                if ($lib.Location) {
                    Write-Host "     Location: $($lib.Location)" -ForegroundColor Gray
                }
            }
            
            Write-Host ""
            $choice = Read-Host "Select library number (1-$($libraries.Count)) or press Enter for library key 1"
            
            if ($choice -and $choice -match '^\d+$' -and [int]$choice -ge 1 -and [int]$choice -le $libraries.Count) {
                $selectedLib = $libraries[[int]$choice - 1]
                $PlexLibraryKey = $selectedLib.Key
                Write-Host "Selected: $($selectedLib.Title) (Key: $PlexLibraryKey)" -ForegroundColor Green
            } else {
                $PlexLibraryKey = "1"
                Write-Host "Using default library key: 1" -ForegroundColor Yellow
            }
        } else {
            Write-Host "Could not fetch Plex libraries. Using default library key: 1" -ForegroundColor Yellow
            $PlexLibraryKey = "1"
        }
    }
    
    # OMDB API Key guidance
    Write-Host "`nOMDB API Configuration (Optional):" -ForegroundColor Yellow
    Write-Host "--------------------------------------------------------------------------------"
    Write-Host "OMDB API key is used for movie poster downloads in the FTP panel." -ForegroundColor Cyan
    Write-Host "This can be configured later in the GUI - not required for installation." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "To get a free OMDB API key:" -ForegroundColor Green
    Write-Host "  1. Visit: https://www.omdbapi.com/apikey.aspx"
    Write-Host "  2. Select FREE plan (1,000 requests/day)"
    Write-Host "  3. Enter your email and verify"
    Write-Host "  4. Configure in GUI: FTP Downloads -> IMDB Settings"
    Write-Host ""
    
    # Additional configuration info
    Write-Host "`nAdditional Configuration:" -ForegroundColor Yellow
    Write-Host "--------------------------------------------------------------------------------"
    Write-Host "FTP server configuration: Available in GUI FTP Downloads tab" -ForegroundColor Green
    Write-Host "Archive processing options: Available in GUI Settings" -ForegroundColor Green
    Write-Host "Logging levels: Available in GUI Settings" -ForegroundColor Green
    Write-Host "Retry settings: Available in GUI Settings" -ForegroundColor Green
    Write-Host ""
    
    return @{
        WatchDirectory = $WatchDirectory
        TargetDirectory = $TargetDirectory
        PlexHost = $PlexHost
        PlexToken = $PlexToken
        PlexLibraryKey = $PlexLibraryKey
    }
}

function Copy-ApplicationFiles {
    Write-Log "Copying application files..." "INFO"
    
    # Create directory structure
    $directories = @(
        "$InstallPath",
        "$InstallPath\logs",
        "$InstallPath\data",
        "$InstallPath\work",
        "$InstallPath\failed",
        "$InstallPath\archive",
        "$InstallPath\thumbnails_cache"
    )
    
    foreach ($dir in $directories) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            Write-Log "Created directory: $dir" "INFO"
        }
    }
    
    # Copy application files
    $filesToCopy = @(
        "plex_rar_bridge.py",
        "gui_monitor.py",
        "monitor_service.py",
        "ftp_pycurl_handler.py",
        "requirements.txt",
        "README.md",
        "LICENSE.txt",
        "INSTALLATION.md",
        "config.yaml.template"
    )
    
    foreach ($file in $filesToCopy) {
        if (Test-Path $file) {
            Copy-Item $file "$InstallPath\$file" -Force
            Write-Log "Copied: $file" "INFO"
        } else {
            Write-Log "Warning: $file not found in source directory" "WARN"
        }
    }
    
    Write-Log "Application files copied successfully" "INFO"
}

function Create-Configuration {
    param($config)
    
    Write-Log "Creating configuration files..." "INFO"
    
    # Create main configuration file content
    $configLines = @(
        "# Plex RAR Bridge Configuration",
        "# Generated by installer on $(Get-Date)",
        "",
        "handbrake:",
        "  enabled: false",
        "  executable: ""C:/Program Files/HandBrake/HandBrakeCLI.exe""",
        "  preset: ""Fast 1080p30""",
        "  quality: 22",
        "",
        "logging:",
        "  level: INFO",
        "  max_log_size: 10485760",
        "  backup_count: 5",
        "",
        "options:",
        "  delete_archives: true",
        "  duplicate_check: true",
        "  enable_gui: false",
        "  enable_reencoding: false",
        "  file_stabilization_time: 10",
        "  max_file_age: 3600",
        "  max_retry_attempts: 20",
        "  retry_interval: 60",
        "  scan_existing_files: true",
        "  extensions:",
        "    - .rar",
        "    - .r00",
        "    - .r01",
        "    - .r02",
        "    - .r03",
        "    - .r04",
        "    - .r05",
        "    - .r06",
        "    - .r07",
        "    - .r08",
        "    - .r09",
        "",
        "paths:",
        "  watch: ""$($config.WatchDirectory -replace '\\','/')""",
        "  work: ""$($InstallPath -replace '\\','/')/work""",
        "  target: ""$($config.TargetDirectory -replace '\\','/')""",
        "  failed: ""$($InstallPath -replace '\\','/')/failed""",
        "  archive: ""$($InstallPath -replace '\\','/')/archive""",
        "",
        "plex:",
        "  host: ""$($config.PlexHost)""",
        "  token: ""$($config.PlexToken)""",
        "  library_key: ""$($config.PlexLibraryKey)"""
    )
    
    $configPath = "$InstallPath\config.yaml"
    $configLines | Out-File -FilePath $configPath -Encoding UTF8
    Write-Log "Created configuration file: $configPath" "INFO"
    
    # Create FTP config template
    $ftpConfig = @{
        connections = @()
        last_used = ""
        settings = @{
            auto_connect = $false
            auto_download_rar = $true
            transfer_mode = "Binary"
            max_concurrent_downloads = 3
        }
        imdb = @{
            api_key = ""
            enable_posters = $true
            cache_days = 7
            api_url = "http://www.omdbapi.com/"
        }
    }
    
    $ftpConfigPath = "$InstallPath\ftp_config.json"
    $ftpConfig | ConvertTo-Json -Depth 10 | Out-File -FilePath $ftpConfigPath -Encoding UTF8
    Write-Log "Created FTP configuration template: $ftpConfigPath" "INFO"
}

function Install-Service {
    param($config)
    
    Write-Log "Installing Windows service..." "INFO"
    
    $pythonPath = (Get-Command python).Source
    $scriptPath = "$InstallPath\plex_rar_bridge.py"
    $nssmPath = "$InstallPath\nssm.exe"
    
    # Remove existing service if it exists
    try {
        $existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
        if ($existingService) {
            Write-Log "Stopping existing service..." "INFO"
            & $nssmPath stop $ServiceName
            Write-Log "Removing existing service..." "INFO"
            & $nssmPath remove $ServiceName confirm
        }
    } catch {
        Write-Log "No existing service to remove" "INFO"
    }
    
    # Install new service
    try {
        Write-Log "Installing service '$ServiceName'..." "INFO"
        & $nssmPath install $ServiceName $pythonPath $scriptPath
        
        # Configure service
        & $nssmPath set $ServiceName AppDirectory $InstallPath
        & $nssmPath set $ServiceName DisplayName "Plex RAR Bridge Service"
        & $nssmPath set $ServiceName Description "Monitors directories for RAR files and extracts them for Plex"
        & $nssmPath set $ServiceName Start SERVICE_AUTO_START
        & $nssmPath set $ServiceName AppStdout "$InstallPath\logs\service_stdout.log"
        & $nssmPath set $ServiceName AppStderr "$InstallPath\logs\service_stderr.log"
        & $nssmPath set $ServiceName AppRotateFiles 1
        & $nssmPath set $ServiceName AppRotateSeconds 86400
        & $nssmPath set $ServiceName AppRotateBytes 1048576
        
        Write-Log "Service configured successfully" "INFO"
        
        # Start service
        Write-Log "Starting service..." "INFO"
        & $nssmPath start $ServiceName
        
        # Verify service is running
        Start-Sleep 5
        $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
        if ($service) {
            if ($service.Status -eq 'Running') {
                Write-Log "Service started successfully" "INFO"
            } elseif ($service.Status -eq 'StartPending') {
                Write-Log "Service is starting..." "INFO"
                Start-Sleep 5
                $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
                if ($service -and $service.Status -eq 'Running') {
                    Write-Log "Service started successfully after delay" "INFO"
                } else {
                    Write-Log "Service may not have started properly. Status: $($service.Status). Check logs." "WARN"
                }
            } else {
                Write-Log "Service status: $($service.Status). Check logs if not running." "WARN"
            }
        } else {
            Write-Log "Service not found after installation" "WARN"
        }
        
    } catch {
        throw "Failed to install service: $_"
    }
}

function Test-Installation {
    Write-Log "Testing installation..." "INFO"
    
    try {
        # Test Python dependencies
        $testResult = & python -c "import yaml, requests, watchdog; print('Dependencies OK')" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Python dependencies test passed" "INFO"
        } else {
            Write-Log "Python dependencies test failed: $testResult" "WARN"
        }
        
        # Test Python script syntax
        $testResult = & python -m py_compile "$InstallPath\plex_rar_bridge.py" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Python script syntax test passed" "INFO"
        } else {
            Write-Log "Python script syntax test failed: $testResult" "WARN"
        }
        
        # Test configuration file
        if (Test-Path "$InstallPath\config.yaml") {
            Write-Log "Configuration file exists" "INFO"
            
            # Test YAML syntax
            $testScript = @"
import yaml
import sys
try:
    with open(r'$InstallPath\config.yaml', 'r') as f:
        yaml.safe_load(f)
    print('YAML syntax valid')
except Exception as e:
    print(f'YAML syntax error: {e}')
    sys.exit(1)
"@
            $testScript | Out-File -FilePath "$env:TEMP\test_yaml.py" -Encoding UTF8
            $testResult = & python "$env:TEMP\test_yaml.py" 2>&1
            Remove-Item "$env:TEMP\test_yaml.py" -Force -ErrorAction SilentlyContinue
            
            if ($LASTEXITCODE -eq 0) {
                Write-Log "Configuration file syntax valid" "INFO"
            } else {
                Write-Log "Configuration file syntax invalid: $testResult" "WARN"
            }
        } else {
            Write-Log "Configuration file missing" "WARN"
        }
        
        # Test service
        $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
        if ($service) {
            Write-Log "Service '$ServiceName' status: $($service.Status)" "INFO"
        } else {
            Write-Log "Service '$ServiceName' not found" "WARN"
        }
        
        # Test UnRAR
        if (Test-Path "$InstallPath\UnRAR.exe") {
            Write-Log "UnRAR executable found" "INFO"
        } else {
            Write-Log "UnRAR executable missing" "WARN"
        }
        
        # Test directories
        $requiredDirs = @("$InstallPath\logs", "$InstallPath\work", "$InstallPath\failed", "$InstallPath\archive")
        foreach ($dir in $requiredDirs) {
            if (Test-Path $dir) {
                Write-Log "Directory exists: $dir" "INFO"
            } else {
                Write-Log "Directory missing: $dir" "WARN"
            }
        }
        
    } catch {
        throw "Installation test failed: $_"
    }
}

function Uninstall-Application {
    Write-Log "Starting uninstallation..." "INFO"
    
    try {
        # Stop and remove service
        $nssmPath = "$InstallPath\nssm.exe"
        if (Test-Path $nssmPath) {
            Write-Log "Stopping service..." "INFO"
            & $nssmPath stop $ServiceName
            Write-Log "Removing service..." "INFO"
            & $nssmPath remove $ServiceName confirm
        }
        
        # Remove installation directory
        if (Test-Path $InstallPath) {
            Write-Log "Removing installation directory..." "INFO"
            Remove-Item $InstallPath -Recurse -Force
        }
        
        Write-Log "Uninstallation completed successfully" "INFO"
        Write-Host "$AppName has been uninstalled successfully" -ForegroundColor Green
        
    } catch {
        throw "Uninstallation failed: $_"
    }
}

function Launch-GuiMonitor {
    Write-Log "Launching GUI monitor..." "INFO"
    
    # Skip GUI launch if NoGui parameter is set
    if ($NoGui) {
        Write-Log "GUI launch skipped due to -NoGui parameter" "INFO"
        Write-Host "GUI launch skipped. You can start it manually later:" -ForegroundColor Yellow
        Write-Host "  cd `"$InstallPath`"" -ForegroundColor Gray
        Write-Host "  python gui_monitor.py" -ForegroundColor Gray
        return
    }
    
    try {
        # Ask user if they want to launch the GUI
        Write-Host ""
        Write-Host "===================================================================================`n" -ForegroundColor Green
        $launchGui = Read-Host "Launch GUI monitor now? (Y/n)"
        
        if ($launchGui -eq '' -or $launchGui -match '^[Yy]') {
            Write-Log "Starting GUI monitor..." "INFO"
            
            # Launch GUI in a new PowerShell window
            $guiPath = "$InstallPath\gui_monitor.py"
            if (Test-Path $guiPath) {
                Write-Host "Starting GUI monitor in new window..." -ForegroundColor Green
                
                # Create a batch file to launch the GUI
                $batchContent = @"
@echo off
cd /d "$InstallPath"
python gui_monitor.py
pause
"@
                $batchFile = "$env:TEMP\launch_gui.bat"
                $batchContent | Out-File -FilePath $batchFile -Encoding ASCII
                
                # Start the batch file in a new window
                Start-Process -FilePath $batchFile -WindowStyle Normal
                
                Write-Host "GUI monitor launched successfully!" -ForegroundColor Green
                Write-Host "You can close this installation window now." -ForegroundColor Yellow
                Write-Log "GUI monitor launched successfully" "INFO"
                
                # Wait a moment for the GUI to start
                Start-Sleep 2
            } else {
                Write-Log "GUI monitor script not found at: $guiPath" "WARN"
                Write-Host "GUI monitor script not found. You can launch it manually later." -ForegroundColor Yellow
            }
        } else {
            Write-Host "GUI monitor not launched. You can start it later with:" -ForegroundColor Yellow
            Write-Host "  cd `"$InstallPath`"" -ForegroundColor Gray
            Write-Host "  python gui_monitor.py" -ForegroundColor Gray
        }
    } catch {
        Write-Log "Failed to launch GUI monitor: $_" "WARN"
        Write-Host "Could not launch GUI monitor automatically. You can start it manually:" -ForegroundColor Yellow
        Write-Host "  cd `"$InstallPath`"" -ForegroundColor Gray
        Write-Host "  python gui_monitor.py" -ForegroundColor Gray
    }
}

function Show-InstallationSummary {
    param($config)
    
    Write-Host "`n" -NoNewline
    Write-Host "===================================================================================" -ForegroundColor Green
    Write-Host "                                                                                   " -ForegroundColor Green
    Write-Host "                        $AppName v$AppVersion - Installation Complete            " -ForegroundColor Green
    Write-Host "                                                                                   " -ForegroundColor Green
    Write-Host "===================================================================================" -ForegroundColor Green
    Write-Host "                                                                                   " -ForegroundColor Green
    Write-Host "  Installation Path: $InstallPath                                                 " -ForegroundColor Green
    Write-Host "  Service Name: $ServiceName                                                      " -ForegroundColor Green
    Write-Host "  Watch Directory: $($config.WatchDirectory)                                     " -ForegroundColor Green
    Write-Host "  Target Directory: $($config.TargetDirectory)                                   " -ForegroundColor Green
    Write-Host "  Plex Server: $($config.PlexHost)                                               " -ForegroundColor Green
    Write-Host "  Library Key: $($config.PlexLibraryKey)                                         " -ForegroundColor Green
    Write-Host "                                                                                   " -ForegroundColor Green
    Write-Host "===================================================================================" -ForegroundColor Green
    Write-Host "                                                                                   " -ForegroundColor Green
    Write-Host "  Next Steps:                                                                     " -ForegroundColor Green
    if ($NoGui) {
        Write-Host "     1. Launch GUI: python $InstallPath\gui_monitor.py                          " -ForegroundColor Green
    } else {
        Write-Host "     1. GUI monitor will launch automatically after this summary                " -ForegroundColor Green
    }
    Write-Host "     2. Place RAR files in: $($config.WatchDirectory)                           " -ForegroundColor Green
    Write-Host "     3. Configure FTP: Use GUI FTP Downloads tab                                 " -ForegroundColor Green
    Write-Host "     4. Configure OMDB: Use GUI FTP Downloads -> IMDB Settings                  " -ForegroundColor Green
    Write-Host "     5. Check logs: $InstallPath\logs\                                           " -ForegroundColor Green
    Write-Host "                                                                                   " -ForegroundColor Green
    Write-Host "  Documentation: $InstallPath\README.md                                          " -ForegroundColor Green
    Write-Host "  Issues: $GitHubRepo/issues                                                     " -ForegroundColor Green
    Write-Host "                                                                                   " -ForegroundColor Green
    Write-Host "===================================================================================" -ForegroundColor Green
    Write-Host ""
}

# Main installation function
function Install-Application {
    Write-Log "Starting $AppName v$AppVersion installation..." "INFO"
    Write-Log "Installation log: $LogPath" "INFO"
    
    try {
        # Check prerequisites
        if (-not (Test-AdminPrivileges)) {
            throw "Administrator privileges required. Please run as Administrator."
        }
        
        if (-not (Test-InternetConnection)) {
            throw "Internet connection required for installation."
        }
        
        # Check/Install Python
        $pythonVersion = Get-PythonVersion
        if (-not $pythonVersion) {
            Write-Log "Python not found. Installing Python..." "INFO"
            Install-Python
            # Refresh PATH
            $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
        } else {
            Write-Log "Python $pythonVersion detected" "INFO"
        }
        
        # Get user configuration
        $config = Get-UserConfiguration
        
        # Create installation directory
        if (-not (Test-Path $InstallPath)) {
            New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
            Write-Log "Created installation directory: $InstallPath" "INFO"
        }
        
        # Install dependencies
        Install-Dependencies
        Install-UnRAR
        Install-NSSM
        
        # Copy application files
        Copy-ApplicationFiles
        
        # Create configuration
        Create-Configuration -config $config
        
        # Install and start service
        Install-Service -config $config
        
        # Test installation
        Test-Installation
        
        # Show summary
        Show-InstallationSummary -config $config
        
        # Launch GUI monitor
        Launch-GuiMonitor
        
        Write-Log "Installation completed successfully!" "INFO"
        
    } catch {
        Write-Log "Installation failed: $_" "ERROR"
        Write-Host "Installation failed. Check log file: $LogPath" -ForegroundColor Red
        throw
    }
}

# Main execution
try {
    Write-Host "===================================================================================" -ForegroundColor Cyan
    Write-Host "                                                                                   " -ForegroundColor Cyan
    Write-Host "                        $AppName v$AppVersion - Professional Installer           " -ForegroundColor Cyan
    Write-Host "                                                                                   " -ForegroundColor Cyan
    Write-Host "===================================================================================" -ForegroundColor Cyan
    Write-Host ""
    
    if ($Uninstall) {
        Uninstall-Application
    } else {
        Install-Application
    }
    
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host "Installation log: $LogPath" -ForegroundColor Yellow
    exit 1
}

Write-Log "Script completed in $([int]((Get-Date) - $StartTime).TotalSeconds) seconds" "INFO" 