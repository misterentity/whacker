# Enhanced GUI Features for Plex RAR Bridge

## Overview

The Plex RAR Bridge now includes an enhanced GUI with detailed configuration options for processing modes and per-directory settings. This allows users to optimize their setup based on specific needs and requirements.

## Features

### 1. Enhanced Setup Panel

The new Enhanced Setup Panel (`Enhanced Setup` tab) provides:

- **Processing Mode Information**: Detailed explanations of each processing mode
- **Per-Directory Configuration**: Different processing modes for different directories
- **Visual Configuration**: Easy-to-use interface for complex setups
- **Real-time Testing**: Test configurations before applying

### 2. Processing Mode Selection

#### Available Processing Modes

| Mode | Description | Dependencies | Complexity | Use Case |
|------|-------------|--------------|------------|----------|
| **Python VFS** | Pure Python virtual filesystem | None | Simple | ✅ **Recommended** - Fast, no dependencies |
| **Traditional Extraction** | Extract files to disk | UnRAR only | Simple | Well-tested, requires 2x space |
| **External rar2fs** | Mount using external rar2fs | Cygwin + WinFSP + rar2fs | Very Complex | Advanced users, space efficient |

#### Processing Mode Details

**Python VFS (Recommended)**
- ✅ Zero external dependencies
- ✅ Instant file availability
- ✅ Space efficient (no extraction)
- ✅ HTTP streaming support
- ✅ Cross-platform compatibility
- ✅ Fast processing

**Traditional Extraction**
- ✅ Simple setup
- ✅ Well-tested approach
- ✅ Compatible with all media servers
- ❌ Requires 2x disk space
- ❌ Slower processing
- ❌ Temporary files on disk

**External rar2fs**
- ✅ Space efficient
- ✅ Fast processing
- ✅ Native filesystem integration
- ❌ Complex setup required
- ❌ Windows-specific dependencies
- ❌ Requires Cygwin + WinFSP

### 3. Per-Directory Configuration

#### Directory Pair Setup

Each directory pair can be configured with:

- **Source Directory**: Where RAR files are placed
- **Target Directory**: Where processed files appear
- **Processing Mode**: Individual mode for this directory
- **Plex Library**: Associated Plex library
- **Status**: Real-time status monitoring

#### Example Configuration

```yaml
directory_pairs:
  # High-frequency downloads - use Python VFS
  - source: "C:/Downloads/Movies"
    target: "C:/Plex/Movies"
    processing_mode: "python_vfs"
    plex_library: "Movies"
    enabled: true
    
  # Archive content - use extraction
  - source: "C:/Downloads/Archive"
    target: "C:/Plex/Archive"
    processing_mode: "extraction"
    plex_library: "Movies"
    enabled: true
    
  # Special setup - use rar2fs
  - source: "C:/Downloads/Special"
    target: "C:/Plex/Special"
    processing_mode: "rar2fs"
    plex_library: "Movies"
    enabled: false
```

### 4. Configuration Management

#### Global Settings

- **Global Processing Mode**: Default mode for new directory pairs
- **Processing Mode Configurations**: Mode-specific settings
- **Advanced Options**: Performance tuning per mode

#### Mode-Specific Configuration

**Python VFS Configuration**
- HTTP Server Port Range: `8765-8865`
- Mount Base Directory: `C:/PlexRarBridge/mounts`
- Stream Chunk Size: `8192`
- Max Concurrent Streams: `10`
- Cache Headers: `true`

**rar2fs Configuration**
- Executable Path: `C:/cygwin64/home/User/rar2fs/rar2fs.exe`
- Mount Base Directory: `C:/PlexRarBridge/rar2fs_mounts`
- Mount Options: `uid=-1, gid=-1, allow_other`
- Auto-Install: Available

**Extraction Configuration**
- Work Directory: `C:/PlexRarBridge/work`
- Delete Archives: `true`
- Duplicate Check: `true`
- Verify Extraction: `true`

### 5. GUI Navigation

#### Tab Structure

1. **Active Threads**: Monitor processing threads
2. **Retry Queue**: View failed processing attempts
3. **Live Logs**: Real-time logging output
4. **Statistics**: Processing statistics and metrics
5. **FTP Downloads**: FTP SSL download management
6. **Setup Panel**: Basic configuration (legacy)
7. **Enhanced Setup**: ✨ **NEW** - Advanced configuration with processing modes
8. **Raw Configuration**: Direct config file editing

#### Enhanced Setup Panel Sections

1. **Processing Mode Information**
   - Detailed mode explanations
   - Comparison table
   - Recommendations

2. **Global Processing Mode**
   - Default mode selection
   - Mode-specific information
   - Visual indicators

3. **Plex Server Connection**
   - Auto-detection features
   - Connection testing
   - Library discovery

4. **Directory Pairs with Processing Modes**
   - Add/Edit/Remove pairs
   - Per-directory mode selection
   - Real-time status

5. **Processing Mode Configuration**
   - Python VFS settings
   - rar2fs configuration
   - Extraction options

6. **Configuration Controls**
   - Save/Load configurations
   - Test all settings
   - Apply and restart

### 6. Advanced Features

#### Automatic Mode Detection

The system can automatically suggest processing modes based on:
- Directory usage patterns
- Available system resources
- File types and sizes
- Performance requirements

#### Intelligent Fallback

If a processing mode fails, the system can automatically fall back to:
1. Python VFS (if available)
2. Traditional Extraction (always available)
3. Manual intervention required

#### Performance Optimization

Mode-specific optimizations:
- **Python VFS**: Memory caching, connection pooling
- **rar2fs**: Mount timeout, retry logic
- **Extraction**: Parallel processing, cleanup intervals

### 7. Configuration Examples

#### Home User Setup

```yaml
directory_pairs:
  - source: "C:/Downloads"
    target: "C:/Plex/Media"
    processing_mode: "python_vfs"  # Recommended for home use
    plex_library: "Movies"
    enabled: true
```

#### Power User Setup

```yaml
directory_pairs:
  # Fast access for new content
  - source: "C:/Downloads/New"
    target: "C:/Plex/New"
    processing_mode: "python_vfs"
    plex_library: "Movies"
    enabled: true
    
  # Archive with space efficiency
  - source: "C:/Downloads/Archive"
    target: "C:/Plex/Archive"
    processing_mode: "rar2fs"
    plex_library: "Movies"
    enabled: true
    
  # Backup with traditional method
  - source: "C:/Downloads/Backup"
    target: "C:/Plex/Backup"
    processing_mode: "extraction"
    plex_library: "Movies"
    enabled: true
```

#### Enterprise Setup

```yaml
directory_pairs:
  # High-volume ingestion
  - source: "\\\\server\\incoming\\movies"
    target: "\\\\plex\\media\\movies"
    processing_mode: "python_vfs"
    plex_library: "Movies"
    enabled: true
    
  # TV shows with space optimization
  - source: "\\\\server\\incoming\\tv"
    target: "\\\\plex\\media\\tv"
    processing_mode: "rar2fs"
    plex_library: "TV Shows"
    enabled: true
    
  # Archive storage
  - source: "\\\\server\\incoming\\archive"
    target: "\\\\plex\\archive"
    processing_mode: "extraction"
    plex_library: "Archive"
    enabled: true
```

### 8. Troubleshooting

#### Common Issues

**Python VFS Issues**
- Port conflicts: Change port range in configuration
- Mount directory permissions: Check directory access
- Memory usage: Adjust cache settings

**rar2fs Issues**
- Executable not found: Use auto-install or manual setup
- Mount failures: Check WinFSP installation
- Permission errors: Verify mount options

**Extraction Issues**
- UnRAR not found: Install UnRAR or check PATH
- Disk space: Ensure sufficient free space
- Permissions: Check directory write access

#### Diagnostic Tools

1. **Test All Configurations**: Built-in testing for all modes
2. **Per-Directory Testing**: Test individual directory pairs
3. **Real-time Monitoring**: Live status updates
4. **Detailed Logging**: Per-directory log files

### 9. Migration Guide

#### From Single Mode to Per-Directory

1. **Backup Current Configuration**
   ```bash
   copy config.yaml config.yaml.backup
   ```

2. **Use Enhanced Setup Panel**
   - Open Enhanced Setup tab
   - Load existing configuration
   - Add directory pairs with modes
   - Save enhanced configuration

3. **Test Configuration**
   - Use "Test All Configurations" button
   - Verify each directory pair
   - Check processing modes

4. **Apply Changes**
   - Use "Apply & Restart Service" button
   - Monitor logs for successful startup
   - Verify processing with test files

### 10. Performance Tuning

#### Optimization by Use Case

**High-Volume Processing**
- Use Python VFS for maximum throughput
- Increase port range for concurrent processing
- Enable connection pooling
- Adjust memory cache settings

**Space-Constrained Systems**
- Use rar2fs for minimal disk usage
- Configure aggressive cleanup
- Enable intelligent fallback
- Monitor storage usage

**Legacy Compatibility**
- Use traditional extraction
- Enable verification
- Configure extensive logging
- Regular cleanup scheduling

### 11. Security Considerations

#### Network Security

- Python VFS uses local HTTP servers
- Configure firewall rules for port range
- Restrict access to local network only
- Use API keys for external access

#### File System Security

- Set appropriate directory permissions
- Use dedicated service accounts
- Regular security audits
- Monitor file access patterns

### 12. Support and Maintenance

#### Regular Maintenance

1. **Monthly**: Review processing statistics
2. **Quarterly**: Update processing mode configurations
3. **Semi-annually**: Review and optimize directory pairs
4. **Annually**: Full system health check

#### Support Resources

- **Built-in Help**: Available in GUI
- **Log Analysis**: Detailed error reporting
- **Community Support**: User forums and discussions
- **Professional Support**: Available for enterprise users

## Conclusion

The Enhanced GUI Features provide unprecedented flexibility and control over RAR archive processing. By combining multiple processing modes with per-directory configuration, users can optimize their setup for specific needs while maintaining simplicity for common use cases.

The Python VFS mode offers the best balance of performance, reliability, and ease of use, making it the recommended choice for most users. Advanced users can leverage rar2fs for space efficiency or traditional extraction for maximum compatibility.

The enhanced GUI ensures that both novice and expert users can configure and maintain their Plex RAR Bridge installation with confidence and precision. 