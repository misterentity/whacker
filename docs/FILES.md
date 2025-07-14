# Plex RAR Bridge - File Overview

This document describes all the files in the Plex RAR Bridge application.

## Core Application Files

### `plex_rar_bridge.py`
**Main application file** - The core service that monitors for RAR files and processes them.

**Features:**
- File system monitoring with watchdog
- Multi-volume RAR extraction
- SHA-256 duplicate detection
- Encrypted archive handling
- H.265 re-encoding support
- System tray GUI (optional)
- Plex library integration
- Comprehensive logging

### `config.yaml`
**Configuration file** - All application settings and paths.

**Sections:**
- `plex`: Server connection and library settings
- `paths`: Directory locations for watch, work, target, etc.
- `options`: Feature toggles and behavior settings
- `handbrake`: H.265 encoding configuration
- `logging`: Log rotation and level settings

### `requirements.txt`
**Python dependencies** - Required packages for the application.

**Core dependencies:**
- `watchdog` - File system monitoring
- `PyYAML` - Configuration parsing
- `requests` - HTTP requests to Plex
- `rarfile` - RAR file handling
- `tqdm` - Progress bars

**Optional dependencies:**
- `pystray` - System tray GUI
- `Pillow` - Image processing for tray icon

## Setup and Installation

### `setup.py`
**Enhanced automated setup script** - Guides users through initial configuration with smart detection.

**Functions:**
- Creates directory structure
- Installs Python dependencies
- Downloads UnRAR if needed
- **🖥️ Automatic Plex server discovery** from multiple sources:
  - Windows Registry (installation and port info)
  - Running Plex processes
  - Configuration files
  - Network scanning on common ports
- **🔍 Enhanced Plex token detection** from multiple sources:
  - Windows Registry (multiple locations)
  - Plex Media Server preferences
  - Browser cookies (Chrome/Edge/Firefox)
  - Plex databases
  - App data files
- **📚 Automatic library discovery** and selection:
  - Connects to Plex server
  - Lists all available libraries by type
  - Interactive library selection
- Interactive configuration wizard
- Installation testing

### `test_installation.py`
**Installation validation** - Tests all components are working correctly.

**Tests:**
- Python dependency verification
- UnRAR availability
- Configuration file validation
- Directory permissions
- Plex connectivity
- HandBrake availability (if enabled)

### `install_service.bat`
**Windows service manager** - Batch script for managing the Windows service.

**Features:**
- Service installation with NSSM
- Service start/stop/restart
- Service status monitoring
- Log file access
- Administrator privilege checking

### `install_service_improved.py`
**Enhanced Python-based service installer**
- Automatic NSSM download and installation
- Intelligent service configuration
- Interactive management menu
- Better error handling and user feedback

### `install_service_easy.bat`
**Simple service installer launcher**
- One-click service installation
- Calls the improved Python installer
- Administrator privilege handling

## Monitoring Tools

### `gui_monitor.py`
**Real-time GUI monitoring application**
- **Thread monitoring** - See active processing threads and their status
- **Retry queue management** - Monitor files waiting for completion
- **Live log streaming** - Real-time log display with filtering
- **Service dashboard** - Health status and statistics
- **Configuration viewer** - Current settings and quick file access
- **Interactive controls** - Service management and testing tools

### `launch_gui.bat`
**GUI monitor launcher**
- Simple double-click launcher for the GUI monitor
- No command line needed

### `monitor_service.py`
**Command-line service monitoring script**
- Check service status
- View recent activity
- Analyze log files
- Display processing statistics

## Documentation

### `README.md`
**Comprehensive documentation** - Complete installation and usage guide.

**Contents:**
- Feature overview
- Installation instructions
- Configuration guide
- Usage examples
- Troubleshooting
- Advanced features

### `QUICKSTART.md`
**Quick start guide** - Get running in 5 minutes.

**Contents:**
- Minimal setup steps
- Essential configuration
- Common issues
- Basic testing

### `FILES.md` (this file)
**File overview** - Description of all application components.

## Directory Structure

When deployed, the application creates this structure:

```
PlexRarBridge/
├── plex_rar_bridge.py          # Main application
├── config.yaml                 # Configuration
├── requirements.txt            # Dependencies
├── setup.py                   # Setup script
├── test_installation.py       # Test script
├── test_plex_detection.py     # Plex integration test
├── install_service.bat        # Legacy service manager
├── install_service_improved.py # Enhanced service installer
├── install_service_easy.bat   # Simple service launcher
├── gui_monitor.py             # Real-time GUI monitor
├── launch_gui.bat             # GUI launcher
├── monitor_service.py         # Command-line monitor
├── fix_installation.py       # Installation fixer
├── README.md                  # Documentation
├── QUICKSTART.md              # Quick start
├── SERVICE_INSTALLATION.md    # Service setup guide
├── FILES.md                   # This file
├── rar_watch/             # RAR drop zone
├── work/                  # Temporary extraction
├── failed/                # Encrypted/failed archives
├── archive/               # Processed archives (optional)
├── logs/                  # Application logs
└── data/                  # SQLite database
```

## Key Features by File

### Security & Reliability
- **Duplicate Detection**: SHA-256 hashing in main application
- **Encrypted Archive Handling**: Automatic detection and quarantine
- **Atomic Operations**: File completion checking before processing
- **Comprehensive Logging**: Detailed logs with rotation

### User Experience
- **Automated Setup**: `setup.py` handles installation
- **Service Integration**: `install_service_easy.bat` for Windows service
- **Real-time Monitoring**: `gui_monitor.py` comprehensive monitoring GUI
- **Command-line Tools**: `monitor_service.py` for status checking
- **System Tray GUI**: Optional visual monitoring
- **Progress Feedback**: Real-time status updates

### Advanced Features
- **H.265 Re-encoding**: HandBrake integration for space savings
- **File Sanitization**: Plex-friendly filename conversion
- **Multi-volume Support**: Handles all RAR archive formats
- **Configurable Behavior**: Extensive options in config.yaml

## Maintenance Files

### Log Files (Created at runtime)
- `logs/bridge.log` - Main application log
- `logs/service_stdout.log` - Service output (if installed)
- `logs/service_stderr.log` - Service errors (if installed)

### Database Files (Created at runtime)
- `data/hashes.db` - SQLite database for duplicate detection

## Development Notes

### Code Organization
- **Object-oriented design**: Main functionality in `PlexRarBridge` class
- **Threaded processing**: Separate threads for file processing
- **Error handling**: Comprehensive exception handling throughout
- **Configuration-driven**: Behavior controlled by config.yaml

### Testing Strategy
- **Installation validation**: `test_installation.py` checks all components
- **Configuration validation**: YAML structure and required fields
- **Connectivity testing**: Plex server and HandBrake availability
- **Permission testing**: Directory access and write permissions

### Service Integration
- **NSSM compatibility**: Designed to work with NSSM service manager
- **Log rotation**: Automatic log file management
- **Graceful shutdown**: Proper cleanup on service stop
- **Auto-restart**: Service configured for automatic restart on failure

---

This complete package provides a robust, feature-rich RAR extraction service specifically designed for Plex Media Server integration. 