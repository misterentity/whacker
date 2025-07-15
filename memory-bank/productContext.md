# Product Context: Plex RAR Bridge Enhanced Edition

## Why This Project Exists

### The Problem
- Many media files are distributed as RAR archives
- Plex Media Server cannot directly read files inside RAR archives
- Manual extraction is time-consuming and requires 2x disk space
- Users need different processing strategies for different content types

### The Solution
Plex RAR Bridge Enhanced Edition provides:
- **Automatic Processing**: Watch directories for new RAR files
- **Multiple Processing Modes**: Choose optimal method for each directory
- **Space Efficiency**: Virtual filesystem modes avoid disk space doubling
- **Plex Integration**: Seamless library refreshing after processing

## How It Should Work

### User Experience
1. **Setup**: Configure watch directories and processing modes through GUI
2. **Drop Files**: Place RAR files in configured watch directories
3. **Automatic Processing**: System detects and processes archives automatically
4. **Plex Access**: Media files become available in Plex immediately
5. **Archive Management**: Processed archives are organized in archive directory

### Processing Flow
1. **Detection**: File system watcher detects new RAR files
2. **Validation**: Check archive integrity and detect encryption
3. **Processing**: Use configured mode (Python VFS, rar2fs, or extraction)
4. **Availability**: Make media files accessible to Plex
5. **Cleanup**: Move archive to organized archive directory or delete
6. **Notification**: Refresh Plex library to detect new content

## Archive Organization
The system maintains organized archive storage:
- **Archive Directory**: `C:\PlexRarBridge\archive`
- **Subdirectory Structure**: Archives organized by release type
- **Example Structure**: `/archive/x264-hd/6.Bullets.2012.1080p.BluRay.x264-UNVEiL`
- **Preservation**: Original folder structure maintained for organization

## Key Features
- **Per-Directory Configuration**: Different processing modes for different directories
- **Real-Time Monitoring**: Live status updates and performance metrics
- **Enhanced GUI**: Advanced configuration and monitoring interface
- **Intelligent Processing**: Automatic mode selection and fallback support
- **Error Handling**: Retry logic and failed archive isolation
- **Performance Optimization**: Mode-specific performance tuning 