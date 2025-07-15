# Plex RAR Bridge - rar2fs Integration

## Overview

The Plex RAR Bridge now supports **rar2fs** as an alternative to traditional RAR extraction. Instead of extracting RAR files to disk, rar2fs mounts them as virtual file systems, allowing Plex to read files directly from the archives without using additional disk space.

## Key Benefits

### Traditional Extraction Mode
- **Process**: RAR → Extract to temp directory → Move to Plex library → Delete temp files
- **Disk Usage**: Requires space for both archive and extracted files
- **Speed**: Limited by disk I/O for extraction and moving files

### rar2fs Mount Mode
- **Process**: RAR → Mount as virtual filesystem → Plex reads directly from mount
- **Disk Usage**: Only requires space for the original RAR archive
- **Speed**: Faster processing, no extraction time
- **Real-time**: Files appear immediately in Plex library

## Prerequisites

### 1. Install rar2fs for Windows

Follow the [official rar2fs Windows installation guide](https://github.com/hasse69/rar2fs/wiki/Windows-HOWTO):

#### Step 1: Install Cygwin
1. Download Cygwin from [cygwin.com](https://www.cygwin.com/)
2. Install with these packages:
   - `automake`
   - `autoconf`
   - `binutils`
   - `gcc-core`
   - `gcc-g++`
   - `make`
   - `git`
   - `wget`

#### Step 2: Install WinFSP
1. Download WinFSP from [GitHub releases](https://github.com/winfsp/winfsp/releases)
2. Run the installer and select both `fuse` and `core` components
3. Install cygfuse:
   ```bash
   cd /cygdrive/c/Program\ Files\ \(x86\)/WinFsp/opt/cygfuse
   ./install.sh
   ```

#### Step 3: Build rar2fs
1. Clone and build rar2fs:
   ```bash
   git clone https://github.com/hasse69/rar2fs.git
   cd rar2fs
   autoreconf -fi
   
   # Download and build UnRAR library
   wget https://www.rarlab.com/rar/unrarsrc-6.0.3.tar.gz
   tar -zxf unrarsrc-6.0.3.tar.gz
   cd unrar
   make lib
   cd ..
   
   # Build rar2fs
   ./configure --with-fuse=/usr/include/fuse
   make
   make install
   ```

#### Step 4: Enable Windows PATH
Add `C:\cygwin64\bin` to your Windows system PATH environment variable.

## Configuration

### Enable rar2fs Mode

1. Edit `config.yaml`:
   ```yaml
   options:
     processing_mode: rar2fs  # Change from 'extraction' to 'rar2fs'
   
   # Add rar2fs configuration section
   rar2fs:
     enabled: true
     executable: C:/cygwin64/home/User/rar2fs/rar2fs.exe
     mount_base: C:/PlexRarBridge/mounts
     mount_options: 
       - "uid=-1"
       - "gid=-1"
       - "allow_other"
     cleanup_on_exit: true
     winfsp_required: true
   ```

2. Ensure your Plex library can access the mount directory:
   - Add `C:/PlexRarBridge/mounts` to your Plex library paths
   - Or configure symbolic links to your existing library directory

### Configuration Options

#### rar2fs Section
- **enabled**: Enable/disable rar2fs functionality
- **executable**: Path to the rar2fs executable
- **mount_base**: Base directory for mount points
- **mount_options**: FUSE mount options
  - `uid=-1` / `gid=-1`: Use current user credentials
  - `allow_other`: Allow other users to access the mount
- **cleanup_on_exit**: Automatically unmount when application exits
- **winfsp_required**: Require WinFSP service to be running

#### Processing Mode
- **extraction**: Traditional extraction mode (default)
- **rar2fs**: Virtual filesystem mode using rar2fs

## How It Works

### Archive Processing Flow

1. **Detection**: New RAR archive detected in watch directory
2. **Validation**: Archive integrity tested using UnRAR
3. **Mount**: Archive mounted as virtual filesystem using rar2fs
4. **Linking**: Symbolic links created in Plex library directory
5. **Notification**: Plex library refreshed to detect new files
6. **Cleanup**: Original archive moved to archive directory or deleted

### Mount Management

The system maintains active mount information:
- **Mount Point**: Unique directory under `mount_base`
- **Process**: Background rar2fs process
- **Links**: Symbolic links in target directories
- **Cleanup**: Automatic cleanup on application exit

### Directory Structure

```
C:/PlexRarBridge/
├── mounts/                     # Mount points for rar2fs
│   ├── MovieTitle_20250114_143022/
│   │   └── MovieTitle.mkv      # Virtual file from RAR
│   └── AnotherMovie_20250114_143125/
│       └── AnotherMovie.mkv
├── rar_watch/                  # Watch directory for RAR files
│   └── MovieTitle.rar
└── archive/                    # Processed archives (if not deleting)
    └── MovieTitle.rar
```

## Advantages vs. Traditional Extraction

### Disk Space
- **Traditional**: Requires 2x disk space (archive + extracted)
- **rar2fs**: Only requires space for original archive

### Processing Speed
- **Traditional**: Time for extraction + file moving
- **rar2fs**: Almost instantaneous mounting

### Reliability
- **Traditional**: Risk of corruption during extraction/moving
- **rar2fs**: Original archive remains intact

### Flexibility
- **Traditional**: Files are permanently extracted
- **rar2fs**: Can unmount/remount as needed

## Troubleshooting

### Common Issues

#### WinFSP Service Not Running
```
Error: WinFSP is required but not available
```
**Solution**: Start the WinFSP service:
```cmd
net start WinFsp.Launcher
```

#### Mount Permission Errors
```
Error: Mount failed: Permission denied
```
**Solution**: Ensure mount options include proper user permissions:
```yaml
mount_options:
  - "uid=-1"
  - "gid=-1"
  - "allow_other"
```

#### Archive Mount Verification Failed
```
Error: Mount verification failed
```
**Solution**: 
1. Check if rar2fs executable is accessible
2. Verify archive integrity
3. Ensure WinFSP is properly installed

#### Plex Not Detecting Files
1. Verify Plex library paths include mount directories
2. Check symbolic link permissions
3. Ensure `allow_other` mount option is set

### Debugging

Enable debug logging:
```yaml
logging:
  level: DEBUG
```

Check mount status:
```python
# View active mounts
mount_status = bridge.rar2fs_handler.get_mount_status()
print(f"Active mounts: {mount_status['active_mounts']}")
```

### Performance Optimization

1. **Mount Location**: Use fast SSD for mount base directory
2. **Network Storage**: For network archives, ensure good network performance
3. **Concurrent Mounts**: Monitor system resources with multiple mounts

## Migration from Extraction Mode

### Gradual Migration
1. Keep existing extracted files in place
2. Enable rar2fs mode for new archives
3. Test with a few archives before full migration

### Full Migration
1. Backup your current library
2. Switch to rar2fs mode
3. Re-process existing archives if needed

### Rollback
If you need to return to extraction mode:
1. Change `processing_mode` back to `extraction`
2. Restart the service
3. Existing mounts will be automatically cleaned up

## Best Practices

### Archive Management
- Keep original RAR archives in a separate backup location
- Use consistent naming conventions
- Regularly verify archive integrity

### System Maintenance
- Monitor mount points for stale entries
- Periodically restart the service to clean up resources
- Keep WinFSP and rar2fs updated

### Plex Integration
- Create separate library sections for rar2fs content if needed
- Use Plex's "Optimize" feature cautiously with mounted files
- Monitor Plex logs for any access issues

## Support

For issues specific to rar2fs integration:
1. Check the application logs in `logs/bridge.log`
2. Verify WinFSP service status
3. Test rar2fs manually with simple archives
4. Check Plex access to mount directories

For general rar2fs issues, refer to the [official rar2fs documentation](https://github.com/hasse69/rar2fs/wiki).

## Future Enhancements

Planned improvements:
- **Auto-detection**: Automatically detect and install rar2fs
- **GUI Integration**: Mount management through the GUI
- **Performance Monitoring**: Real-time mount performance statistics
- **Advanced Options**: More granular mount configuration options 