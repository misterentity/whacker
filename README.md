# Plex RAR Bridge

## Enhanced Setup Panel (NEW!)

**🎉 Configure multiple directories with ease!** The new Setup Panel provides a comprehensive GUI for:

- **Multiple Source/Target Pairs**: Monitor unlimited directories, each with its own target and Plex library
- **Auto-Detection**: Automatically discover Plex server and authentication token  
- **Library Association**: Link each directory pair to specific Plex libraries (Movies, TV Shows, etc.)
- **Persistent Configuration**: Settings automatically saved and restored on reboot
- **One-Click Service Management**: Apply changes and restart service from the GUI

### Quick Access
```bash
# Launch directly to setup panel
python gui_monitor.py setup
# OR
double-click setup_gui.bat
```

📖 **[Complete Setup Panel Documentation →](SETUP_PANEL.md)**

---

## Overview

A comprehensive Windows service that automatically extracts RAR archives and integrates them with Plex Media Server. Features intelligent duplicate detection, H.265 re-encoding, retry mechanisms, and real-time GUI monitoring.

## Features

- **Automatic RAR Processing**: Monitors a folder for RAR archives and processes them automatically
- **Multi-volume Support**: Handles `.rar`, `.r00`, `.r01`, etc. and `.part1.rar`, `.part2.rar`, etc.
- **SHA-256 Duplicate Detection**: Prevents duplicate files from being processed
- **Encrypted Archive Handling**: Moves encrypted archives to a failed folder for manual intervention
- **H.265 Re-encoding**: Optional re-encoding with HandBrake for space savings
- **File Sanitization**: Cleans up filenames for Plex compatibility
- **System Tray GUI**: Optional system tray interface for monitoring
- **Comprehensive Logging**: Detailed logging with rotation
- **Atomic Operations**: Ensures files are completely copied before processing
- **Plex Integration**: Automatically refreshes Plex library after processing

## Prerequisites

### Windows 11 Requirements

1. **Python 3.12**: Install via `winget install Python.Python.3.12`
2. **UnRAR Command-Line Tool**: Download from [rarlab.com](https://www.rarlab.com/rar_add.htm) and add to PATH
3. **HandBrake CLI** (optional): For H.265 re-encoding
4. **Plex Media Server**: With API token

### Getting Your Plex Token

**Automatic Detection (Recommended):**
The setup script will automatically detect your Plex server and token from:

**Server Discovery:**
- Windows Registry (installation and port info)
- Running Plex processes
- Configuration files
- Network scanning on common ports

**Token Detection:**
- Windows Registry (multiple locations)
- Plex Media Server preferences
- Browser cookies (Chrome/Edge/Firefox)
- Plex databases
- App data files

**Manual Method:**
1. Sign in to your Plex account
2. Visit: `http://<your-plex-server>:32400/?X-Plex-Token=<token>`
3. Copy the token from the URL

## Installation

1. Clone or download this repository
2. Run the enhanced setup script:
   ```bash
   python setup.py
   ```
   This will automatically:
   - Install Python dependencies
   - Detect your Plex server and port
   - Find your Plex token
   - List your libraries for selection
   - Create directories
   - Test the installation

**Alternative manual installation:**
1. Install Python dependencies: `pip install -r requirements.txt`
2. Install UnRAR and add to PATH
3. Configure the application (see Configuration section)

## Directory Structure

```
C:\PlexRarBridge\
├── plex_rar_bridge.py     # Main application
├── config.yaml            # Configuration file
├── requirements.txt       # Python dependencies
├── README.md              # This file
├── rar_watch\             # Drop zone for RAR files
├── work\                  # Temporary extraction directory
├── failed\                # Encrypted/failed archives
├── archive\               # Processed archives (if not deleting)
├── logs\                  # Application logs
└── data\                  # SQLite database for hash tracking
```

## Configuration

Edit `config.yaml` to match your setup:

```yaml
plex:
  host: "http://127.0.0.1:32400"
  token: "YOUR-PLEX-TOKEN-HERE"
  library_key: 2            # Your movie library section number

paths:
  watch:  "C:/PlexRarBridge/rar_watch"
  work:   "C:/PlexRarBridge/work"
  target: "D:/Media/Movies"
  failed: "C:/PlexRarBridge/failed"
  archive: "C:/PlexRarBridge/archive"

options:
  delete_archives: true     # Delete archives after processing
  duplicate_check: true     # Enable SHA-256 duplicate detection
  enable_gui: false         # Enable system tray GUI
  enable_reencoding: false  # Enable H.265 re-encoding
```

### Finding Your Library Key

**Automatic Selection (Recommended):**
The setup script will automatically:
- Connect to your Plex server
- List all available libraries with their types
- Let you select the library you want to use

**Manual Method:**
1. Go to your Plex web interface
2. Navigate to your Movies library
3. Look at the URL: `http://localhost:32400/web/index.html#!/server/.../details?key=%2Flibrary%2Fsections%2F2`
4. The number after `sections/` is your library key

## Usage

### Running the Application

```bash
python plex_rar_bridge.py
```

### Installing as a Windows Service

Use the improved automated installer:

1. **Right-click** on `install_service_easy.bat` and select **"Run as administrator"**
2. The installer will automatically:
   - Download NSSM (Non-Sucking Service Manager) if needed
   - Install the service with proper configuration
   - Provide a menu for service management

**For detailed service installation instructions, see [SERVICE_INSTALLATION.md](SERVICE_INSTALLATION.md)**

### System Tray GUI

Enable the system tray GUI by setting `enable_gui: true` in config.yaml. The tray icon provides:
- Status information
- Statistics
- Quick access to logs
- Clean shutdown

## Processing Workflow

1. **File Detection**: Monitors the watch folder for new RAR files
2. **Completion Check**: Waits for file copy to complete using size stabilization
3. **Archive Validation**: Tests archive integrity and checks for encryption
4. **Extraction**: Extracts to temporary work directory
5. **Duplicate Check**: Compares SHA-256 hashes against database
6. **File Sanitization**: Cleans filenames for Plex compatibility
7. **Re-encoding** (optional): Converts to H.265 using HandBrake
8. **Atomic Move**: Moves files to Plex library directory
9. **Cleanup**: Removes temporary files and optionally archive files
10. **Plex Refresh**: Triggers library scan

## Monitoring

### Real-time GUI Monitor
```bash
python gui_monitor.py
# Or simply double-click: launch_gui.bat
```

**Features:**
- **Real-time thread monitoring** - See what each processing thread is doing
- **Retry queue status** - Monitor files waiting for completion
- **Live log streaming** - Watch logs in real-time with filtering
- **Service status** - Check if service is running and healthy
- **Statistics dashboard** - Processing rates, errors, uptime
- **Configuration viewer** - Current settings and quick access to files

### Command-line Monitoring
```bash
python monitor_service.py
```

## Testing

### Test Installation
```bash
python test_installation.py
```

### Test Plex Detection
```bash
python test_plex_detection.py
```

This specialized test creates a dummy video file in your target directory and verifies that Plex can detect and add it to your library. It helps diagnose:
- Whether your target directory is monitored by Plex
- If Plex library scanning is working
- Token and library configuration issues

### Create Test RAR Archive
Create a test RAR archive:

```bash
# Create a multi-volume RAR
rar a -v10m test.part1.rar "sample-movie.mkv"

# Copy all volumes to watch folder
copy test.part*.rar D:\x265\
```

Monitor the logs at `logs/bridge.log` for processing status.

## Advanced Features

### Duplicate Detection

The application maintains a SQLite database of file hashes to prevent duplicate processing:
- SHA-256 hashes are calculated for all processed files
- Duplicates are automatically skipped
- Database is stored in `data/hashes.db`

### Encrypted Archive Handling

Encrypted archives are automatically detected and moved to the `failed` folder for manual intervention.

### H.265 Re-encoding

**Automatic Detection & Installation:**
The setup script will automatically:
- Detect existing HandBrake installations
- Offer to download and install HandBrake if not found
- Auto-enable H.265 re-encoding if HandBrake is available

**Manual Configuration:**
Enable re-encoding in config.yaml:

```yaml
options:
  enable_reencoding: true

handbrake:
  enabled: true
  executable: "C:/Program Files/HandBrake/HandBrakeCLI.exe"
  preset: "Fast 1080p30"
  quality: 22
```

### File Sanitization

Filenames are automatically cleaned for Plex compatibility:
- Removes problematic characters
- Converts dot-separated names to proper format
- Extracts year information when possible
- Example: `Movie.Title.2024.1080p.BluRay.x264-GROUP.mkv` → `Movie Title (2024).mkv`

## Troubleshooting

### Common Issues

1. **Permission Errors**: Ensure the application has read/write access to all configured directories
2. **UnRAR Not Found**: Verify UnRAR is installed and in PATH
3. **Plex Token Invalid**: Regenerate your Plex token
4. **Archive Test Failures**: Check if RAR files are corrupted or encrypted

### Log Analysis

Check `logs/bridge.log` for detailed information:
- File detection events
- Processing steps
- Error messages
- Performance metrics

### Performance Tuning

- Adjust `file_stabilization_time` for faster/slower networks
- Increase `max_file_age` for large file transfers
- Enable SSD for work directory for faster extraction

## Security Considerations

- Keep your Plex token secure
- Run with minimal required permissions
- Regularly clean up the failed directory
- Monitor logs for unauthorized access attempts

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is released under the MIT License.

## Support

For issues and questions:
1. Check the logs first
2. Review this README
3. Search existing issues
4. Create a new issue with detailed information

---

*Note: This application is designed for Windows 11 but can be adapted for other operating systems with minor modifications.* 