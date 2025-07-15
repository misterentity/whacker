# Plex RAR Bridge - Enhanced Edition

## 🎯 Overview

**Plex RAR Bridge Enhanced Edition** is a comprehensive Windows service that automatically processes RAR archives for Plex Media Server with **three powerful processing modes**, **per-directory configuration**, and an **enhanced GUI interface**. Choose the perfect processing method for each directory based on your specific needs.

## 🚀 What's New in Enhanced Edition

### **Three Processing Modes**
- **🔥 Python VFS (Recommended)**: Zero-dependency virtual filesystem with instant file access
- **⚡ External rar2fs**: Space-efficient FUSE mounting (advanced users)
- **🗂️ Traditional Extraction**: Classic file extraction (well-tested)

### **Enhanced GUI Features**
- **Per-Directory Configuration**: Different processing modes for different directories
- **Visual Processing Mode Selection**: Easy-to-use interface for complex setups
- **Real-Time Monitoring**: Live status updates and performance metrics
- **Advanced Setup Panel**: Complete configuration management
- **Processing Mode Comparison**: Visual comparison of all modes

### **Intelligent Processing**
- **Automatic Mode Selection**: System suggests optimal processing modes
- **Fallback Support**: Automatic fallback if primary mode fails
- **Performance Optimization**: Mode-specific performance tuning
- **Resource Management**: Efficient CPU and memory usage

## 📋 Processing Modes Comparison

| Feature | Python VFS | rar2fs | Extraction |
|---------|------------|--------|------------|
| **Dependencies** | None | Cygwin + WinFSP | UnRAR only |
| **Setup Complexity** | ✅ Simple | ❌ Complex | ✅ Simple |
| **Disk Space Usage** | ✅ Minimal | ✅ Minimal | ❌ 2x Required |
| **Processing Speed** | ✅ Instant | ✅ Fast | ⚠️ Slow |
| **File Availability** | ✅ Immediate | ✅ Immediate | ⚠️ After extraction |
| **Plex Compatibility** | ✅ HTTP Streaming | ✅ Native | ✅ Native |
| **Windows Support** | ✅ Native | ⚠️ Via Cygwin | ✅ Native |
| **Recommended For** | Most users | Advanced users | Legacy systems |

## 🛠️ Installation

### **Enhanced PowerShell Installer (Recommended)**

1. **Download** the latest release
2. **Run PowerShell as Administrator**
3. **Execute the installer**:
   ```powershell
   .\Install-PlexRarBridge.ps1
   ```

The installer will:
- ✅ Install Python dependencies automatically
- ✅ Auto-detect Plex server and token
- ✅ Guide you through processing mode selection
- ✅ Configure directories and libraries
- ✅ Install Windows service
- ✅ Launch enhanced GUI

### **Installation Options**

```powershell
# Basic installation (Python VFS mode)
.\Install-PlexRarBridge.ps1

# Installation with specific processing mode
.\Install-PlexRarBridge.ps1 -ProcessingMode "python_vfs"

# Silent installation
.\Install-PlexRarBridge.ps1 -NoGui -ProcessingMode "python_vfs"

# Upgrade existing installation
.\Install-PlexRarBridge.ps1 -Upgrade

# Uninstall
.\Install-PlexRarBridge.ps1 -Uninstall
```

### **Manual Installation**

1. **Install Python 3.8+**
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Install UnRAR** (for extraction mode)
4. **Configure** `config.yaml`
5. **Run the application**:
   ```bash
   python plex_rar_bridge.py
   ```

## 🏗️ Project Structure

```
PlexRarBridge/
├── 📁 Core Application
│   ├── plex_rar_bridge.py          # Main application
│   ├── monitor_service.py          # Service monitoring
│   └── config.yaml                 # Enhanced configuration
│
├── 📁 Enhanced GUI
│   ├── gui_monitor.py              # Main GUI application
│   ├── enhanced_setup_panel.py    # Advanced configuration panel
│   └── ftp_pycurl_handler.py      # FTP download manager
│
├── 📁 Processing Modes
│   ├── python_rar_vfs.py          # Python VFS handler
│   ├── rar2fs_handler.py          # rar2fs integration
│   └── rar2fs_installer.py        # Automated rar2fs installer
│
├── 📁 Configuration Examples
│   ├── config-enhanced.yaml       # Enhanced configuration
│   ├── config-rar2fs-example.yaml # rar2fs configuration
│   └── ftp_config.json            # FTP settings
│
├── 📁 Documentation
│   ├── docs/PROCESSING_MODES.md   # Processing mode guide
│   ├── docs/ENHANCED_GUI_FEATURES.md # GUI feature guide
│   ├── docs/RAR2FS_INTEGRATION.md # rar2fs setup guide
│   └── docs/...                   # Additional documentation
│
├── 📁 Installation
│   ├── Install-PlexRarBridge.ps1  # Enhanced PowerShell installer
│   ├── install_service_easy.bat   # Legacy installer
│   └── requirements.txt           # Python dependencies
│
└── 📁 Runtime Directories
    ├── logs/                       # Application logs
    ├── data/                       # SQLite database
    ├── work/                       # Temporary extraction
    ├── failed/                     # Failed archives
    ├── archive/                    # Processed archives
    ├── mounts/                     # VFS mount points
    └── thumbnails_cache/           # GUI thumbnails
```

## 🎮 Enhanced GUI Interface

Launch the enhanced GUI:
```bash
python gui_monitor.py
```

### **Tab Overview**

1. **🔄 Active Threads**: Monitor processing threads in real-time
2. **📋 Retry Queue**: View failed processing attempts
3. **📊 Live Logs**: Real-time logging with filtering
4. **📈 Statistics**: Processing metrics and performance
5. **🌐 FTP Downloads**: FTP SSL download management
6. **⚙️ Setup Panel**: Basic configuration (legacy)
7. **🎯 Enhanced Setup**: **NEW** - Advanced per-directory configuration
8. **📝 Raw Configuration**: Direct config file editing

### **Enhanced Setup Panel Features**

- **🎨 Visual Processing Mode Selection**: Easy comparison and selection
- **📂 Per-Directory Configuration**: Different modes for different directories
- **🔗 Plex Integration**: Auto-detect server and libraries
- **🧪 Real-Time Testing**: Test configurations before applying
- **💾 Configuration Management**: Save, load, and apply settings
- **📊 Performance Tuning**: Mode-specific optimization

## 📝 Configuration

### **Per-Directory Configuration**

Configure different processing modes for different directories:

```yaml
# Enhanced Configuration Example
options:
  global_processing_mode: "python_vfs"  # Default mode

# Per-Directory Processing
directory_pairs:
  # High-performance for new releases
  - source: "C:/Downloads/Movies"
    target: "D:/Plex/Movies"
    processing_mode: "python_vfs"
    plex_library: "Movies"
    enabled: true
    
  # Space-efficient for TV shows
  - source: "C:/Downloads/TV"
    target: "D:/Plex/TV"
    processing_mode: "python_vfs"
    plex_library: "TV Shows"
    enabled: true
    
  # Traditional extraction for compatibility
  - source: "C:/Downloads/Archive"
    target: "D:/Plex/Archive"
    processing_mode: "extraction"
    plex_library: "Movies"
    enabled: true

# Processing Mode Configurations
processing_modes:
  python_vfs:
    enabled: true
    port_range: [8765, 8865]
    mount_base: "C:/PlexRarBridge/mounts"
    
  rar2fs:
    enabled: false
    executable: "C:/cygwin64/home/User/rar2fs/rar2fs.exe"
    mount_base: "C:/PlexRarBridge/rar2fs_mounts"
    
  extraction:
    enabled: true
    work_dir: "C:/PlexRarBridge/work"
    delete_archives: true
```

### **Processing Mode Details**

#### **🔥 Python VFS (Recommended)**
- **Zero Dependencies**: No external tools required
- **Instant Access**: Files available immediately via HTTP streaming
- **Space Efficient**: No disk space for extraction
- **HTTP Streaming**: Plex accesses files via HTTP
- **Cross-Platform**: Works on any Python-supported OS

```yaml
processing_modes:
  python_vfs:
    enabled: true
    port_range: [8765, 8865]        # HTTP server port range
    mount_base: "C:/PlexRarBridge/mounts"
    stream_chunk_size: 8192
    max_concurrent_streams: 10
    cache_headers: true
```

#### **⚡ External rar2fs**
- **Space Efficient**: Minimal disk usage
- **Native Integration**: Files appear as regular files
- **Complex Setup**: Requires Cygwin + WinFSP
- **Advanced Users**: Technical knowledge required

```yaml
processing_modes:
  rar2fs:
    enabled: true
    executable: "C:/cygwin64/home/User/rar2fs/rar2fs.exe"
    mount_base: "C:/PlexRarBridge/rar2fs_mounts"
    mount_options:
      - "uid=-1"
      - "gid=-1"
      - "allow_other"
```

#### **🗂️ Traditional Extraction**
- **Well-Tested**: Proven approach
- **Full Compatibility**: Works with all media servers
- **Disk Space**: Requires 2x space (original + extracted)
- **Slower Processing**: Files available after extraction

```yaml
processing_modes:
  extraction:
    enabled: true
    work_dir: "C:/PlexRarBridge/work"
    delete_archives: true
    duplicate_check: true
    verify_extraction: true
```

## 🚀 Usage Examples

### **Quick Start**

1. **Install**: Run `Install-PlexRarBridge.ps1` (automatically detects Plex token)
2. **Configure**: Use Enhanced Setup tab in GUI
3. **Drop Files**: Place RAR files in configured directories
4. **Monitor**: Watch processing in real-time via GUI

#### **🔍 Enhanced Token Detection**

The installer now automatically detects your Plex token from multiple sources:
- **Windows Registry** - Plex installation settings
- **Preferences Files** - Plex Media Server configuration  
- **Browser Cookies** - Chrome/Edge saved tokens
- **Plex Databases** - Library database files
- **Process Memory** - Running Plex processes
- **Web Interface** - Direct web interface scraping

**Token Validation Tool**: Use `test_plex_token.ps1` to verify your token works correctly.

### **Different Use Cases**

#### **Home User (Simple Setup)**
```yaml
directory_pairs:
  - source: "C:/Downloads"
    target: "D:/Plex/Media"
    processing_mode: "python_vfs"
    plex_library: "Movies"
```

#### **Power User (Multi-Directory)**
```yaml
directory_pairs:
  - source: "C:/Downloads/Movies"
    target: "D:/Plex/Movies"
    processing_mode: "python_vfs"
    
  - source: "C:/Downloads/TV"
    target: "D:/Plex/TV"
    processing_mode: "python_vfs"
    
  - source: "C:/Downloads/Archive"
    target: "D:/Plex/Archive"
    processing_mode: "extraction"
```

#### **Enterprise (Advanced Setup)**
```yaml
directory_pairs:
  - source: "\\\\server\\incoming\\movies"
    target: "\\\\plex\\media\\movies"
    processing_mode: "python_vfs"
    
  - source: "\\\\server\\incoming\\tv"
    target: "\\\\plex\\media\\tv"
    processing_mode: "rar2fs"
    
  - source: "\\\\server\\archive"
    target: "\\\\plex\\archive"
    processing_mode: "extraction"
```

## 🔧 Advanced Features

### **Intelligent Processing**
- **Automatic Mode Selection**: System suggests optimal modes
- **Fallback Support**: Automatic fallback if primary mode fails
- **Performance Optimization**: Mode-specific performance tuning
- **Resource Management**: Efficient CPU and memory usage

### **Enhanced Monitoring**
- **Real-Time Status**: Live processing updates
- **Performance Metrics**: Processing speed and efficiency
- **Error Tracking**: Detailed error analysis
- **Health Monitoring**: System health checks

### **FTP Integration**
- **SSL/TLS Support**: Secure FTP downloads
- **Content Discovery**: IMDb integration for posters
- **Automated Downloads**: Schedule and manage downloads
- **Progress Tracking**: Real-time download progress

### **Duplicate Detection**
- **SHA-256 Hashing**: Prevents duplicate processing
- **Database Tracking**: SQLite database for hash storage
- **Cross-Directory**: Detects duplicates across all directories
- **Performance Optimized**: Fast hash calculations

## 🛠️ Troubleshooting

### **Common Issues**

#### **Python VFS Issues**
- **Port Conflicts**: Change port range in configuration
- **Memory Usage**: Adjust cache settings
- **Firewall**: Allow HTTP ports through firewall

#### **rar2fs Issues**
- **Executable Not Found**: Use auto-installer or manual setup
- **Mount Failures**: Check WinFSP installation
- **Permission Errors**: Verify mount options

#### **Extraction Issues**
- **UnRAR Not Found**: Install UnRAR or check PATH
- **Disk Space**: Ensure sufficient free space
- **Permissions**: Check directory write access

### **Diagnostic Tools**

1. **Enhanced GUI**: Built-in diagnostic tools
2. **Log Analysis**: Detailed error reporting
3. **Configuration Testing**: Test all modes
4. **Performance Monitoring**: Real-time metrics

### **Getting Help**

1. **Check Logs**: Review detailed logs in `logs/` directory
2. **Documentation**: Read mode-specific documentation
3. **Test Configuration**: Use built-in testing tools
4. **GUI Diagnostics**: Use Enhanced Setup panel diagnostics

## 📚 Documentation

### **Complete Documentation**
- **[Processing Modes Guide](docs/PROCESSING_MODES.md)** - Detailed comparison of all modes
- **[Enhanced GUI Features](docs/ENHANCED_GUI_FEATURES.md)** - Complete GUI guide
- **[rar2fs Integration](docs/RAR2FS_INTEGRATION.md)** - rar2fs setup guide
- **[FTP Panel Guide](docs/FTP_PANEL_README.md)** - FTP download management
- **[Service Installation](docs/SERVICE_INSTALLATION.md)** - Windows service setup
- **[Setup Panel Guide](docs/SETUP_PANEL.md)** - Configuration panel usage

### **Quick Reference**
- **[Quick Start](QUICKSTART.md)** - Get started in 5 minutes
- **[Installation Guide](INSTALLATION.md)** - Detailed installation steps
- **[Configuration Examples](config-enhanced.yaml)** - Sample configurations

## 🔄 Migration from Previous Versions

### **Automatic Migration**
The enhanced installer automatically:
- ✅ Detects existing installations
- ✅ Preserves current configuration
- ✅ Upgrades to enhanced features
- ✅ Maintains service continuity

### **Manual Migration**
1. **Backup**: Copy existing `config.yaml`
2. **Upgrade**: Run installer with `-Upgrade` flag
3. **Configure**: Use Enhanced Setup panel
4. **Test**: Verify processing modes work correctly

### **Migration Command**
```powershell
# Upgrade existing installation
.\Install-PlexRarBridge.ps1 -Upgrade -ProcessingMode "python_vfs"
```

## 🏆 Performance Optimization

### **Mode-Specific Optimization**

#### **Python VFS**
```yaml
processing_modes:
  python_vfs:
    max_memory_cache: 100        # MB
    preload_headers: true
    connection_pool_size: 5
    stream_chunk_size: 8192
```

#### **rar2fs**
```yaml
processing_modes:
  rar2fs:
    mount_timeout: 60
    retry_mount: 3
    unmount_timeout: 30
```

#### **Extraction**
```yaml
processing_modes:
  extraction:
    parallel_extraction: true
    temp_cleanup_interval: 300
    verify_extraction: true
```

## 🔒 Security

### **Security Features**
- **Token Protection**: Secure Plex token storage
- **Network Security**: Configurable network access
- **File Permissions**: Proper directory permissions
- **Audit Logging**: Security event logging

### **Best Practices**
- **Regular Updates**: Keep software updated
- **Access Control**: Limit user access
- **Network Isolation**: Use firewalls
- **Log Monitoring**: Regular log analysis

## 🤝 Contributing

We welcome contributions! Please see our contribution guidelines:

1. **Fork** the repository
2. **Create** a feature branch
3. **Implement** your changes
4. **Test** thoroughly
5. **Submit** a pull request

### **Development Setup**
```bash
# Clone repository
git clone https://github.com/user/plex-rar-bridge.git

# Install development dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/

# Start development server
python plex_rar_bridge.py
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE.txt) file for details.

## 🆘 Support

### **Getting Help**
- **📖 Documentation**: Complete guides in `docs/` directory
- **🐛 Issues**: Report bugs on GitHub Issues
- **💬 Discussions**: Community discussions on GitHub
- **📧 Email**: Contact for enterprise support

### **Support Channels**
- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Community support
- **Documentation**: Comprehensive guides
- **GUI Help**: Built-in help system

## 🎉 Acknowledgments

- **Plex Media Server**: For the excellent media server platform
- **Python Community**: For the amazing ecosystem
- **Contributors**: All contributors to this project
- **Users**: For feedback and suggestions

---

**🚀 Ready to get started?** Run the enhanced installer and experience the future of RAR processing for Plex!

```powershell
.\Install-PlexRarBridge.ps1
```

---

*Plex RAR Bridge Enhanced Edition - The ultimate RAR processing solution for Plex Media Server* 