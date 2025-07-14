# Plex RAR Bridge Setup Panel

The Setup Panel provides a comprehensive GUI interface for configuring multiple source/target directory pairs with associated Plex libraries. All settings are automatically saved and persist across system reboots.

## Quick Start

### Launch Setup Panel
```bash
# Start GUI with setup tab open
python gui_monitor.py setup
# OR
double-click setup_gui.bat
# OR
python gui_monitor.py  # then click "Setup Panel" tab
```

## Features

### 1. Plex Server Connection
- **Auto-Detection**: Automatically discover Plex server URL and authentication token
- **Manual Configuration**: Enter server details manually if auto-detection fails  
- **Connection Testing**: Verify connectivity and load available libraries
- **Library Discovery**: Automatically list all Plex libraries with type indicators (📽️ Movies, 📺 TV Shows, 📁 Other)

### 2. Multiple Directory Pairs
Configure unlimited source → target directory pairs:
- **Source Directory**: Where RAR files are dropped/monitored
- **Target Directory**: Where extracted files are moved
- **Plex Library Association**: Link each pair to a specific Plex library
- **Enable/Disable**: Toggle monitoring for individual pairs
- **Directory Testing**: Verify permissions and accessibility

### 3. Configuration Management
- **Persistent Storage**: Settings saved to `setup_config.json`
- **Auto-Reload**: Configuration loaded automatically on service start
- **Backup Integration**: Updates main `config.yaml` for compatibility
- **Service Integration**: Apply settings and restart service with one click

## Configuration Process

### Step 1: Plex Connection
1. Click **Auto-Detect** for server URL (or enter manually)
2. Click **Auto-Detect** for token (or enter manually)  
3. Click **Test Connection** to verify and load libraries
4. Confirm libraries appear in the list

### Step 2: Directory Pairs
1. Click **Add Pair** to create new source/target mapping
2. Browse or type source directory (where RAR files arrive)
3. Browse or type target directory (where files should go)
4. Select associated Plex library from dropdown
5. Enable/disable the pair as needed
6. Click **Save**

### Step 3: Apply Configuration
1. Review all directory pairs in the table
2. Test individual pairs with **Test Selected**
3. Click **Save Configuration** to persist settings
4. Click **Apply & Restart Service** to activate changes

## File Structure

### Configuration Files
```
setup_config.json          # Main setup configuration
config.yaml                # Legacy/fallback configuration  
logs/bridge.log            # Service logs
```

### Setup Configuration Format
```json
{
  "plex": {
    "host": "http://localhost:32400",
    "token": "your-plex-token",
    "libraries": [
      {"key": "1", "title": "Movies", "type": "movie"},
      {"key": "2", "title": "TV Shows", "type": "show"}
    ]
  },
  "directory_pairs": [
    {
      "source": "D:/Downloads/Movies",
      "target": "D:/Media/Movies", 
      "library_key": "1",
      "library_title": "Movies",
      "enabled": true
    },
    {
      "source": "D:/Downloads/TV",
      "target": "D:/Media/TV Shows",
      "library_key": "2", 
      "library_title": "TV Shows",
      "enabled": true
    }
  ],
  "options": {
    "recursive_monitoring": true,
    "auto_start_service": true
  }
}
```

## Advanced Options

### Recursive Monitoring
- **Enabled**: Monitor all subdirectories within source directories
- **Disabled**: Only monitor root level of source directories

### Auto-Start Service  
- **Enabled**: Service starts automatically on system boot
- **Disabled**: Manual service startup required

## Service Integration

### Automatic Service Management
The setup panel integrates directly with the Windows service:

1. **Configuration Updates**: Changes are saved to persistent storage
2. **Service Restart**: Service automatically reloads new configuration  
3. **Multi-Directory Monitoring**: Service monitors all enabled directory pairs
4. **Library-Specific Processing**: Files moved to correct target and Plex library refreshed

### Service Startup Process
1. Service reads `setup_config.json` on startup
2. Falls back to `config.yaml` if setup config unavailable
3. Creates file system watchers for each enabled directory pair
4. Processes files according to their source directory configuration

## Troubleshooting

### Common Issues

**Plex Connection Failed**
- Verify Plex server is running
- Check firewall settings
- Ensure token has proper permissions
- Try manual URL entry (include port, e.g., `:32400`)

**Directory Access Errors**
- Verify directory permissions 
- Check paths exist and are accessible
- Ensure service account has read/write access
- Test with **Test Selected** button

**Service Not Applying Changes**
- Check service is running in Services panel
- Review logs in `logs/bridge.log`
- Try manual service restart via Windows Services
- Verify `setup_config.json` file was created

**Libraries Not Loading**
- Confirm Plex token is valid
- Check library permissions in Plex
- Verify server URL is accessible
- Try re-authenticating in Plex

### Log Analysis
Monitor service logs for configuration loading:
```
INFO - Loaded setup configuration with 2 directory pairs
INFO - Directory pair: D:/Downloads/Movies -> D:/Media/Movies (Library: 1)  
INFO - Directory pair: D:/Downloads/TV -> D:/Media/TV Shows (Library: 2)
INFO - Started monitoring: D:/Downloads/Movies -> D:/Media/Movies (Library: 1, Recursive: True)
```

## Migration from Single Directory

If upgrading from single-directory configuration:

1. **Automatic Migration**: Setup panel loads existing `config.yaml` settings
2. **Create First Pair**: Current watch/target directories become first pair
3. **Add More Pairs**: Configure additional source/target combinations
4. **Save Configuration**: Apply changes to activate multi-directory monitoring

The system maintains backward compatibility with existing configurations while providing the flexibility of multiple directory pairs. 