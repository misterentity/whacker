# Quick Start Guide

Get Plex RAR Bridge running in 5 minutes!

## Prerequisites

1. **Windows 11** (or Windows 10)
2. **Python 3.8+**: `winget install Python.Python.3.12`
3. **Plex Media Server** running

## 1. Quick Setup

Run the automated setup script:

```bash
python setup.py
```

This will:
- Install Python dependencies
- Create directories
- **🔍 Automatically detect your Plex token**
- **📚 List your Plex libraries for selection**
- Guide you through configuration
- Download UnRAR if needed
- Test the installation

**Example setup output:**
```
--- Plex Server Discovery ---
Searching for Plex server...
  ✓ Found server from Process Detection: http://127.0.0.1:32400
Found server: http://127.0.0.1:32400
Use discovered server? (y/n) [y]: 

--- Plex Token Detection ---
Searching for Plex token...
  ✓ Found token from Plex Server Preferences
Found token: xHj8sK2mN3pQ4rT5u6V7w8...
Use discovered token? (y/n) [y]: 

--- Plex Library Selection ---
Testing Plex connection...
✓ Connected to Plex server

Available Plex Libraries:
==================================================

📽️  MOVIE LIBRARIES:
  [1] Movies (Key: 1)
  [2] 4K Movies (Key: 3)

📺 TV SHOW LIBRARIES:
  [3] TV Shows (Key: 2)

  [0] Enter library key manually
==================================================

Select library (1-3, or 0 for manual): 1

Selected: Movies (Key: 1)
```

## 2. Automatic Server Discovery & Token Detection

The setup script will now automatically:
- 🖥️ **Detect your Plex server** location and port from:
  - Windows Registry
  - Running processes
  - Configuration files
  - Network scanning
- 🔍 **Detect your Plex token** from 6 enhanced sources:
  - **Windows Registry** - Plex installation settings
  - **Preferences Files** - Plex Media Server configuration
  - **Browser Cookies** - Chrome/Edge saved tokens
  - **Plex Databases** - Library database files
  - **Process Memory** - Running Plex processes
  - **Web Interface** - Direct web interface scraping
- 📚 **List all your Plex libraries** with their types (Movies, TV Shows, etc.)
- 🎯 **Let you select** the library you want to use

### 🔧 Token Validation Tool

If token detection fails, you can use the included validation tool:

```powershell
.\test_plex_token.ps1
```

This tool will:
- Guide you through manual token retrieval
- Test your token for validity
- Provide detailed connection information
- Verify library access

**Manual token method** (if auto-detection fails):
1. Open your Plex web interface
2. Go to any movie and click "Get Info"
3. Click "View XML" 
4. Copy the `X-Plex-Token` from the URL
5. Enter it when prompted by the setup script

## 3. Quick Configuration

Edit `config.yaml`:

```yaml
plex:
  host: "http://127.0.0.1:32400"
  token: "YOUR-ACTUAL-PLEX-TOKEN-HERE"  # ← Change this!
  library_key: 2                       # ← Your Movies library number

paths:
  target: "D:/Media/Movies"             # ← Your Plex movies folder
```

## 4. Test Installation

```bash
python test_installation.py
```

## 5. Test Plex Detection (Recommended)

Before processing real files, test that Plex can detect files in your target directory:

```bash
python test_plex_detection.py
```

This will:
- Create a test video file in your target directory
- Trigger a Plex library scan  
- Check if the file appears in your Plex library
- Clean up the test file

If this test fails, your target directory may not be properly configured in Plex.

## 6. Start the Service

### Option A: Run Directly
```bash
python plex_rar_bridge.py
```

### Option B: Install as Windows Service
1. Right-click `install_service_easy.bat`
2. Choose "Run as administrator"
3. Follow the automated installer (downloads NSSM if needed)
4. Select option 1 to install, then option 2 to start

**For detailed service installation instructions, see [SERVICE_INSTALLATION.md](SERVICE_INSTALLATION.md)**

## 7. Monitor the Service

### Option A: Real-time GUI Monitor
```bash
python gui_monitor.py
# Or double-click: launch_gui.bat
```

**Features:**
- Real-time thread monitoring
- Live log streaming
- Retry queue status  
- Service statistics
- Processing activity

### Option B: Command-line Monitor
```bash
python monitor_service.py
```

## 8. Test with Sample Archive

Drop a RAR file into the `D:\x265` folder and watch it get processed in the GUI monitor!

## Common Issues

### "UnRAR not found"
- Download from: https://www.rarlab.com/rar_add.htm
- Extract and add to PATH

### "Plex connection failed"
- Check your Plex token is correct
- Verify Plex server is running
- Check firewall settings

### "Permission denied"
- Run as administrator
- Check folder permissions

### "Files not appearing in Plex"
- Run `python test_plex_detection.py` to diagnose
- Check target directory is monitored by Plex
- Verify library scanning is enabled

## What Happens Next?

1. **Drop RAR files** into `D:\x265`
2. **Monitor logs** in `logs/bridge.log`
3. **Check Plex** - new movies appear automatically
4. **View statistics** - check the logs for processing stats

## Advanced Features

Once basic setup works:

### Enable System Tray GUI
```yaml
options:
  enable_gui: true
```

### Enable Duplicate Detection
```yaml
options:
  duplicate_check: true
```

### Enable H.265 Re-encoding
```yaml
options:
  enable_reencoding: true
  
handbrake:
  enabled: true
  executable: "C:/Program Files/HandBrake/HandBrakeCLI.exe"
```

## Support

- Check `logs/bridge.log` for detailed information
- Run `python test_installation.py` to diagnose issues
- Run `python test_plex_detection.py` to test Plex integration
- Read the full `README.md` for comprehensive documentation

---

**That's it!** Your Plex RAR Bridge is now ready to automatically process RAR archives.