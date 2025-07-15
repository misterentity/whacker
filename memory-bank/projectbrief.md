# Project Brief: Plex RAR Bridge Enhanced Edition

## Core Purpose
A comprehensive Windows service that automatically processes RAR archives for Plex Media Server with three different processing modes, per-directory configuration, and an enhanced GUI interface.

## Key Requirements
- **Three Processing Modes**: Python VFS (recommended), rar2fs, and traditional extraction
- **Per-Directory Configuration**: Different processing modes for different directories  
- **Enhanced GUI**: Real-time monitoring and advanced configuration panels
- **Automatic Processing**: Watch directories for new RAR files and process them
- **Plex Integration**: Automatically refresh Plex libraries after processing
- **Archive Management**: Move processed archives to organized archive directory or delete them

## Processing Modes
1. **Python VFS**: Zero-dependency virtual filesystem with instant HTTP streaming access
2. **rar2fs**: Space-efficient FUSE mounting using external rar2fs executable
3. **Traditional Extraction**: Classic file extraction with physical file moving

## Core Workflow
1. Monitor watch directories for new RAR files
2. Process archives using configured processing mode
3. Make media files available to Plex
4. Move processed archives to archive directory or delete them
5. Refresh Plex libraries to detect new content

## Target Users
- Home users wanting simple RAR processing for Plex
- Power users needing different processing modes for different directories
- Enterprise users with complex multi-directory setups

## Success Criteria
- Seamless integration with Plex Media Server
- Efficient processing with minimal disk space usage
- Reliable handling of different RAR archive formats
- Easy configuration through GUI interface
- Proper organization of processed archives 