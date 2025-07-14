# FTP SSL Download Panel

The FTP SSL Download Panel provides secure file downloading capabilities directly integrated with your Plex RAR Bridge workflow.

## Features

### 🔐 **Secure FTP Connections**
- **SSL Explicit (FTPS)** - Secure command channel, explicit data protection
- **SSL Implicit (FTPS)** - Fully encrypted connection on secure port
- **Plain FTP** - Traditional unencrypted FTP (not recommended)

### 📁 **File Browser**
- Navigate FTP directories with intuitive interface
- File type recognition (directories vs files)
- File size display in human-readable format
- Date/time information
- Double-click navigation

### ⬇️ **Download Management**
- **Smart RAR Detection** - Automatically finds RAR files and related volumes
- **Download Queue** - Queue multiple files for batch downloading
- **Progress Tracking** - Real-time status updates
- **Resume Support** - Handle interrupted downloads
- **Direct Integration** - Downloads go directly to your watch directory

### 💾 **Connection Presets**
- Save multiple FTP server configurations
- Encrypted password storage
- Quick connection switching
- Auto-load last used connection

## Quick Start

### 1. Launch FTP Panel
```bash
# Open GUI directly to FTP tab
python gui_monitor.py ftp
# OR
double-click launch_gui_ftp.bat
# OR
Open GUI normally and click "FTP Downloads" tab
```

### 2. Configure Connection
1. **Enter server details:**
   - Server: `ftp.example.com`
   - Port: `21` (or `990` for implicit SSL)
   - Username: `your_username`
   - Password: `your_password`
   - SSL Mode: `Explicit` (recommended)

2. **Save connection:**
   - Click "Save" button
   - Enter a name for this connection
   - Settings will be remembered for future use

3. **Set download directory:**
   - Defaults to your RAR watch directory
   - Files downloaded here will be automatically processed
   - Click "Browse" to select different folder

### 3. Connect and Browse
1. Click **"Connect"** button
2. Status will show "✅ Connected"
3. Browse directories using:
   - **⬆ Up** - Go to parent directory
   - **🏠 Root** - Go to root directory
   - **🔄 Refresh** - Refresh current directory
   - **Double-click** directories to enter them

### 4. Download Files

**Individual Files:**
- Select files → Click **"⬇ Download Selected"**
- Or double-click files to add to queue

**RAR Archives:**
- Click **"⬇ Download All RAR"** to find and queue all RAR files
- Automatically detects: `.rar`, `.r00`, `.r01`, `.r02`, etc.

**Queue Management:**
- **Start Queue** - Begin downloading queued files
- **Pause Queue** - Pause current downloads
- **Clear Queue** - Remove all queued files

## Security Notes

### SSL Explicit vs Implicit
- **Explicit (Recommended)**: Uses standard port 21, upgrades to SSL
- **Implicit**: Uses secure port (usually 990), fully encrypted from start
- **Plain FTP**: No encryption - only use on trusted networks

### Password Storage
- Passwords are stored in `ftp_config.json`
- Consider using dedicated FTP accounts with limited permissions
- Regularly rotate passwords for security

## Integration with RAR Bridge

### Automatic Processing
Files downloaded to the watch directory are **automatically processed**:

1. **FTP Download** → Watch Directory (`D:/x265`)
2. **RAR Detection** → Bridge detects new RAR files
3. **Extraction** → Bridge extracts to work directory
4. **Processing** → Files moved to Plex library
5. **Plex Refresh** → Library updated automatically

### Recommended Workflow
1. **Browse FTP server** for new content
2. **Download RAR archives** to watch directory
3. **Let Bridge process** automatically
4. **Watch logs** for processing status
5. **Enjoy content** in Plex

## File Operations

### Supported File Types
- **RAR Archives**: `.rar`, `.r00`-`.r99`, `.part1.rar`, etc.
- **All Files**: Any file type can be downloaded
- **Filtering**: Use file filter to show only specific types

### Navigation
- **Enter Directory**: Double-click or select + "📁 Enter Directory"
- **Download File**: Double-click or select + "⬇ Download Selected"
- **Bulk RAR Download**: "⬇ Download All RAR" button

### Queue Status
- **Queued**: File added to download queue
- **Downloading**: Currently downloading
- **Completed**: Download finished successfully
- **Error**: Download failed (see error message)

## Troubleshooting

### Connection Issues
- **SSL Certificate Errors**: Try different SSL mode
- **Port Issues**: Check if firewall blocks FTP ports
- **Authentication Failed**: Verify username/password
- **Timeout**: Check server address and network connectivity

### Download Problems
- **Permission Denied**: Check local directory permissions
- **Disk Space**: Ensure sufficient space in download directory
- **Network Interruption**: Downloads will show error status
- **File Already Exists**: Downloads skip existing files

### Integration Issues
- **Files Not Processing**: Check if download directory matches watch directory
- **Bridge Not Running**: Ensure Plex RAR Bridge service is active
- **Wrong Target**: Verify Plex library paths in configuration

## Configuration Files

### `ftp_config.json`
Stores FTP connection settings and preferences:
```json
{
  "connections": [
    {
      "name": "My Server",
      "host": "ftp.example.com",
      "port": 21,
      "username": "user",
      "password": "pass",
      "ssl_mode": "Explicit",
      "download_dir": "D:/x265",
      "file_filter": "*.rar"
    }
  ],
  "last_used": "My Server",
  "settings": {
    "auto_connect": false,
    "auto_download_rar": true,
    "transfer_mode": "Binary",
    "max_concurrent_downloads": 3
  }
}
```

## Tips & Best Practices

### Performance
- **Use Binary mode** for RAR files (default)
- **Close unnecessary connections** to improve speed
- **Download during off-peak hours** for better speeds

### Organization
- **Create descriptive connection names** for easy identification
- **Use consistent download directories** for automated processing
- **Regular cleanup** of old download queues

### Security
- **Use SSL when possible** for secure transfers
- **Limit FTP account permissions** to necessary directories only
- **Monitor connection logs** for suspicious activity
- **Use strong passwords** and rotate them regularly

---

## Advanced Features

### Custom File Filters
Use wildcards to filter file display:
- `*.rar` - Only RAR files
- `*.mkv` - Only MKV video files
- `*2024*` - Files containing "2024"
- `*.r??` - RAR volumes (.r00, .r01, etc.)

### Batch Operations
- **Select multiple files** with Ctrl+Click
- **Download entire directories** of RAR files
- **Queue management** for large downloads
- **Auto-retry** failed downloads

The FTP SSL Download Panel seamlessly integrates with your existing Plex RAR Bridge workflow, providing a secure and efficient way to download content directly for automatic processing. 