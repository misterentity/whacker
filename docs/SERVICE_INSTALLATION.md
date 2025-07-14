# Plex RAR Bridge - Service Installation Guide

## Overview

The Plex RAR Bridge can be installed as a Windows service to run automatically in the background. This guide provides multiple installation methods.

## Prerequisites

- Windows 10/11 or Windows Server
- Administrator privileges
- Python 3.7+ installed
- Completed initial setup (run `python setup.py`)

## Installation Methods

### Method 1: Automatic Installation (Recommended)

This method automatically downloads and configures everything needed.

1. **Right-click** on `install_service_easy.bat` and select **"Run as administrator"**
2. The installer will:
   - Download NSSM (Non-Sucking Service Manager) if needed
   - Install the service
   - Configure it to start automatically
   - Provide a menu for service management

### Method 2: Python Installer

If you prefer to use Python directly:

1. **Open PowerShell as Administrator**
2. Navigate to the project directory
3. Run: `python install_service_improved.py`

### Method 3: Manual Installation (Advanced)

If you need more control or troubleshooting:

1. **Download NSSM manually**:
   - Go to https://nssm.cc/download
   - Download the ZIP file
   - Extract and copy `nssm.exe` to your project directory

2. **Install the service**:
   ```cmd
   nssm install PlexRarBridge python "C:\path\to\plex_rar_bridge.py"
   nssm set PlexRarBridge AppDirectory "C:\path\to\project"
   nssm set PlexRarBridge DisplayName "Plex RAR Bridge"
   nssm set PlexRarBridge Start SERVICE_AUTO_START
   ```

## Service Management

Once installed, you can manage the service using:

### Option 1: Service Installer Menu
Run `install_service_improved.py` as administrator for an interactive menu.

### Option 2: Windows Services
1. Press `Win + R`, type `services.msc`
2. Find "Plex RAR Bridge" in the list
3. Right-click for options (Start, Stop, Restart, etc.)

### Option 3: Command Line
```cmd
# Start service
nssm start PlexRarBridge

# Stop service
nssm stop PlexRarBridge

# Restart service
nssm restart PlexRarBridge

# Check status
sc query PlexRarBridge
```

## Service Configuration

The service is configured to:
- **Start automatically** when Windows boots
- **Run in background** without user interaction
- **Log to files** in the `logs/` directory
- **Restart automatically** if it crashes
- **Rotate log files** to prevent disk space issues

## Troubleshooting

### Service Won't Start

1. **Check logs**: Look in `logs/service_stderr.log` for error messages
2. **Test manually**: Try running `python plex_rar_bridge.py` directly
3. **Check permissions**: Ensure the service has access to all configured directories
4. **Verify configuration**: Run `python test_installation.py`

### Service Starts but Doesn't Work

1. **Check application logs**: Look in `logs/bridge.log`
2. **Verify paths**: Ensure watch, work, and target directories are accessible
3. **Test Plex connection**: Verify Plex server is running and accessible
4. **Check dependencies**: Ensure all Python packages are installed

### Common Issues

**"NSSM not found"**
- The installer should download NSSM automatically
- If it fails, download manually from https://nssm.cc/download

**"Access denied"**
- Ensure you're running as Administrator
- Check that the service account has proper permissions

**"Service exists"**
- Remove the existing service first: `nssm remove PlexRarBridge confirm`
- Then reinstall using the installer

**"Python not found"**
- Ensure Python is installed and in PATH
- The installer should detect Python automatically

## Service Logs

The service creates several log files:

- `logs/bridge.log` - Main application logs
- `logs/service_stdout.log` - Service standard output
- `logs/service_stderr.log` - Service error output

These logs are automatically rotated to prevent disk space issues.

## Uninstalling the Service

To remove the service:

1. **Using the installer**:
   - Run `install_service_improved.py` as administrator
   - Choose option 5 (Remove service)

2. **Using command line**:
   ```cmd
   nssm stop PlexRarBridge
   nssm remove PlexRarBridge confirm
   ```

## Performance Considerations

The service is designed to be lightweight and efficient:
- Uses minimal CPU when idle
- Processes files using separate threads
- Implements retry mechanisms for busy files
- Automatically manages memory usage

## Security

The service runs with:
- Standard user privileges (not SYSTEM)
- Access only to configured directories
- No network listening ports
- Local-only Plex API access

## Support

If you encounter issues:
1. Check the logs in `logs/` directory
2. Run `python test_installation.py` for diagnostics
3. Review this guide for common solutions
4. Check the main README.md for general troubleshooting 