# Plex RAR Bridge Installation Guide

Plex RAR Bridge automatically monitors directories for RAR files, extracts them, and integrates with your Plex Media Server. This guide provides multiple installation methods to suit your needs.

## 🚀 Quick Start (Recommended)

### Method 1: PowerShell Installer (Recommended)
**Features**: Auto-detects Plex settings, handles all dependencies, creates Windows service

1. **Download** the latest release from GitHub
2. **Right-click** on `Install-PlexRarBridge.ps1` → **Run with PowerShell**
3. **Follow the interactive wizard** - it will auto-detect:
   - ✅ Plex server URL and status
   - ✅ Plex authentication token (from preferences)
   - ✅ Available Plex libraries with selection menu
   - ✅ Python installation status
   - ✅ System requirements

**What you'll need to provide:**
- Watch directory (where RAR files arrive)
- Target directory (your Plex library folder)
- Plex library selection (from auto-detected list)

**Optional (configured later in GUI):**
- FTP server settings
- OMDB API key for movie posters
- Processing options and retry settings

```powershell
# Run as Administrator
.\Install-PlexRarBridge.ps1
```

### Method 2: Python Setup Script
**Features**: Cross-platform, configurable, good for development

1. **Clone or download** the repository
2. **Install Python 3.8+** if not already installed
3. **Run setup script:**

```bash
# Install dependencies
pip install -r requirements.txt

# Run setup wizard
python setup.py
```

### Method 3: Manual Installation
**Features**: Full control, custom configurations

1. **Install dependencies manually**
2. **Configure `config.yaml`** from template
3. **Set up as Windows service** or run directly

---

## 📋 System Requirements

- **Windows 10/11** (PowerShell installer)
- **Python 3.8+** (auto-installed if missing)
- **Plex Media Server** (running and accessible)
- **Internet connection** (for dependency downloads)
- **Administrator privileges** (for service installation)

---

## 🎯 Auto-Detection Features

The PowerShell installer automatically detects:

### ✅ Plex Configuration
- **Server URL**: Tests common ports (32400, 32401, 32402)
- **Authentication Token**: Enhanced detection from 6 sources:
  - Windows Registry (Plex installation settings)
  - Preferences Files (Plex Media Server configuration)
  - Browser Cookies (Chrome/Edge saved tokens)
  - Plex Databases (Library database files)
  - Process Memory (Running Plex processes)
  - Web Interface (Direct web interface scraping)
- **Libraries**: Fetches available libraries via API
- **Installation Status**: Verifies Plex is running

### ✅ System Dependencies
- **Python Installation**: Checks version and installs if needed
- **Required Packages**: Installs watchdog, PyYAML, requests, etc.
- **UnRAR Utility**: Downloads and configures extraction tool
- **NSSM Service Manager**: Sets up Windows service

### ✅ Directory Structure
- Creates all required directories
- Sets up logging infrastructure
- Configures work and archive folders

---

## 🔧 Configuration Guide

### Core Settings (Required)
These are configured during installation:

```yaml
paths:
  watch: "C:\Downloads\RAR"          # Where RAR files arrive
  target: "D:\Media\Movies"          # Your Plex library folder
  work: "C:\PlexRarBridge\work"      # Temporary extraction
  failed: "C:\PlexRarBridge\failed"  # Failed extractions
  archive: "C:\PlexRarBridge\archive" # Processed archives

plex:
  host: "http://127.0.0.1:32400"     # Auto-detected
  token: "your-plex-token"           # Auto-detected
  library_key: "1"                   # Auto-detected from selection
```

### Optional Settings (GUI Configuration)
These are configured later in the GUI:

#### FTP Downloads
- Server connections and credentials
- SSL/TLS settings
- Download directories and filters
- Content discovery and filtering

#### OMDB Integration
- API key for movie posters
- Poster download settings
- Cache configuration

#### Processing Options
- Archive handling (delete/keep)
- Retry attempts and intervals
- File filters and extensions
- Logging levels

---

## 🎬 OMDB API Configuration

The installer provides guidance for obtaining an OMDB API key:

### Getting Your Free API Key
1. **Visit**: https://www.omdbapi.com/apikey.aspx
2. **Select**: FREE plan (1,000 requests/day)
3. **Enter**: Your email address
4. **Verify**: Check email and activate
5. **Configure**: In GUI → FTP Downloads → IMDB Settings

### Usage in Application
- **Movie Posters**: Downloaded for FTP content
- **Metadata**: Enhanced movie information
- **Caching**: Reduces API calls with 7-day cache
- **Optional**: Not required for core functionality

---

## 📁 Directory Structure

After installation, your directory structure will be:

```
C:\Program Files\PlexRarBridge\
├── plex_rar_bridge.py          # Main service script
├── gui_monitor.py              # GUI management interface
├── ftp_pycurl_handler.py       # FTP download handler
├── config.yaml                 # Main configuration
├── ftp_config.json             # FTP settings (GUI managed)
├── UnRAR.exe                   # Extraction utility
├── nssm.exe                    # Service manager
├── logs\                       # Log files
│   ├── bridge.log              # Main application logs
│   ├── ftp.log                 # FTP operation logs
│   ├── service_stdout.log      # Service output
│   └── service_stderr.log      # Service errors
├── work\                       # Temporary extraction
├── failed\                     # Failed extractions
├── archive\                    # Processed archives
└── thumbnails_cache\           # FTP poster cache
```

---

## 🔄 Service Management

The installer creates a Windows service for automatic operation:

### Service Control
```powershell
# Start service
Start-Service PlexRarBridge

# Stop service
Stop-Service PlexRarBridge

# Restart service
Restart-Service PlexRarBridge

# Check status
Get-Service PlexRarBridge
```

### GUI Management
Launch the GUI for monitoring and configuration:

```powershell
cd "C:\Program Files\PlexRarBridge"
python gui_monitor.py
```

### Manual Operation
Run directly without service:

```powershell
cd "C:\Program Files\PlexRarBridge"
python plex_rar_bridge.py
```

---

## 🔍 Troubleshooting

### Common Issues

#### Plex Token Not Detected
**Problem**: Installer can't find Plex token automatically
**Solution**: 
1. Ensure Plex is running and accessible
2. Check Plex preferences file locations
3. Manually configure following the installer prompts

#### Service Won't Start
**Problem**: Windows service fails to start
**Solution**:
1. Check service logs in `logs\service_stderr.log`
2. Verify Python path and dependencies
3. Ensure config.yaml is valid

#### Archive Processing Fails
**Problem**: RAR files aren't being extracted
**Solution**:
1. Check UnRAR.exe is in installation directory
2. Verify watch directory permissions
3. Review main application logs

### Log Files
- **bridge.log**: Main application events
- **ftp.log**: FTP download operations
- **service_stdout.log**: Service output
- **service_stderr.log**: Service errors

### Getting Help
1. **Check logs** for error messages
2. **Review configuration** in GUI
3. **Test components** individually
4. **Report issues** on GitHub with logs

---

## 🔧 Advanced Configuration

### Custom Installation Path
```powershell
.\Install-PlexRarBridge.ps1 -InstallPath "C:\Custom\Path"
```

### Custom Service Name
```powershell
.\Install-PlexRarBridge.ps1 -ServiceName "MyRarBridge"
```

### Uninstall
```powershell
.\Install-PlexRarBridge.ps1 -Uninstall
```

### Development Mode
For development or testing:
```bash
# Install in development mode
pip install -e .

# Run with debug logging
python plex_rar_bridge.py --debug
```

---

## 📚 Next Steps

After installation:

1. **Place RAR files** in your configured watch directory
2. **Monitor processing** via GUI or logs
3. **Configure FTP downloads** if needed
4. **Set up OMDB API** for enhanced metadata
5. **Customize processing options** in GUI

The application will automatically:
- Monitor watch directory for new RAR files
- Extract archives to work directory
- Move completed extractions to target directory
- Update Plex library
- Handle failures and retries
- Maintain detailed logs

For additional features like FTP downloads and content discovery, use the GUI interface which provides full configuration options not covered in the installer. 