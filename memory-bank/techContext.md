# Technology Context: Plex RAR Bridge Enhanced Edition

## Core Technologies

### Python 3.8+
- **Main Language**: All core functionality implemented in Python
- **GUI Framework**: tkinter with ttk for enhanced widgets
- **Threading**: Multi-threaded processing and monitoring
- **HTTP Server**: Built-in HTTP server for Python VFS mode

### Key Dependencies
```
watchdog          # File system monitoring
requests          # HTTP requests for Plex API
pycurl           # FTP SSL support
psutil           # System process monitoring
patool           # Archive handling
```

### Windows Integration
- **Service Management**: NSSM (Non-Sucking Service Manager)
- **WinFSP**: Windows File System Proxy for rar2fs mode
- **PowerShell**: Installation and configuration scripts
- **Registry**: Plex token detection from Windows registry

## Processing Mode Technologies

### 1. Python VFS (Recommended)
- **Technology**: Pure Python HTTP server
- **Dependencies**: None (built-in)
- **Protocol**: HTTP streaming for Plex access
- **Storage**: Virtual filesystem in memory

### 2. rar2fs Mode
- **Technology**: External rar2fs executable
- **Dependencies**: Cygwin + WinFSP
- **Protocol**: FUSE filesystem mounting
- **Storage**: Virtual filesystem via mount points

### 3. Traditional Extraction
- **Technology**: UnRAR.exe
- **Dependencies**: UnRAR executable
- **Protocol**: File system operations
- **Storage**: Physical file extraction

## Development Environment

### Required Tools
- **Python**: 3.8 or higher
- **Git**: Version control
- **Visual Studio Code**: Recommended IDE
- **PowerShell**: Windows administration

### Optional Tools
- **Cygwin**: For rar2fs mode development
- **WinFSP**: For rar2fs mode testing
- **NSSM**: For Windows service testing

## Configuration Management
- **YAML**: Configuration file format
- **JSON**: FTP and setup configurations
- **SQLite**: Database for duplicate detection
- **Registry**: Windows-specific settings

## Networking
- **HTTP**: Python VFS serving (ports 8765-8865)
- **UPnP**: Automatic port forwarding
- **Plex API**: HTTP/HTTPS communication with Plex server
- **FTP**: SSL/TLS support for downloads

## File System
- **Monitoring**: Real-time file system watching
- **Permissions**: Windows file system permissions
- **Symbolic Links**: For rar2fs mode
- **Mount Points**: Virtual filesystem mounting

## Error Handling
- **Logging**: Rotating log files
- **Exceptions**: Comprehensive exception handling
- **Retry Logic**: Configurable retry mechanisms
- **Timeouts**: Protection against hanging operations

## Performance Considerations
- **Memory**: Streaming vs. extraction trade-offs
- **CPU**: Multi-threading for parallel processing
- **Disk I/O**: Minimized through virtual filesystem modes
- **Network**: Efficient Plex API communication

## Security
- **Tokens**: Secure Plex token storage
- **Permissions**: Proper file system permissions
- **Network**: Configurable network access
- **SSL/TLS**: Secure FTP connections 