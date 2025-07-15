# System Patterns: Plex RAR Bridge Enhanced Edition

## Architecture Overview
The system follows a modular architecture with clear separation of concerns:

### Core Components
1. **PlexRarBridge**: Main application class managing the overall system
2. **ProcessingQueue**: Queue-based processing system for archives
3. **Processing Modes**: Three different handlers for archive processing
4. **GUI Monitor**: Real-time monitoring and configuration interface
5. **File System Watcher**: Automatic detection of new RAR files

### Processing Mode Architecture
```
PlexRarBridge
├── Python VFS Handler (python_rar_vfs.py)
├── rar2fs Handler (rar2fs_handler.py)
└── Traditional Extraction (built-in)
```

### Configuration System
- **Main Config**: `config.yaml` for basic settings
- **Enhanced Config**: `config-enhanced.yaml` for per-directory settings
- **Runtime Config**: GUI-based configuration management

## Key Design Patterns

### 1. Strategy Pattern
Different processing modes implement the same interface:
- `_process_archive_python_vfs()`
- `_process_archive_rar2fs()`
- `_process_archive_extraction()`

### 2. Observer Pattern
File system watcher observes directory changes and triggers processing

### 3. Queue Pattern
ProcessingQueue manages archive processing with retry logic

### 4. Factory Pattern
Processing mode selection based on configuration

## Archive Management Pattern
```
Processing Flow:
1. Detect RAR file
2. Test archive integrity
3. Process using configured mode
4. Handle archive based on settings:
   - Delete if delete_archives: true
   - Move to archive directory if delete_archives: false
```

## Directory Structure Pattern
```
C:/PlexRarBridge/
├── archive/                 # Processed archives (organized by type)
│   ├── x264-hd/
│   │   └── Movie.Title.2012.1080p.BluRay.x264-GROUP/
│   └── x265-4k/
├── failed/                  # Failed/encrypted archives
├── work/                    # Temporary extraction (extraction mode)
├── mounts/                  # Mount points (Python VFS mode)
├── rar_watch/              # Watch directory for new RAR files
└── logs/                   # Application logs
```

## Error Handling Pattern
1. **Validation**: Test archive integrity before processing
2. **Retry Logic**: ProcessingQueue handles failed attempts
3. **Isolation**: Failed archives moved to failed directory
4. **Logging**: Comprehensive logging for debugging

## Threading Pattern
- **Main Thread**: GUI and main application loop
- **Worker Thread**: ProcessingQueue worker for archive processing
- **Watcher Thread**: File system monitoring
- **HTTP Server Thread**: Python VFS HTTP serving

## Configuration Pattern
Per-directory configuration allows different processing modes:
```yaml
directory_pairs:
  - source: "C:/Downloads/Movies"
    target: "C:/Plex/Movies"
    processing_mode: "python_vfs"
    plex_library: "Movies"
```

## Integration Pattern
- **Plex API**: Library refresh after processing
- **UPnP**: Automatic port forwarding for Python VFS
- **Windows Service**: Background service integration 