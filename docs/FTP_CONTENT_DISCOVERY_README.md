# FTP Content Discovery & Smart Routing System

## 🚀 Overview

Advanced content discovery and intelligent routing system for the FTP panel, providing automatic detection and categorization of movie and TV show content with smart destination folder routing.

## ✨ Key Features

### 🧠 Intelligent Content Detection
- **Advanced Pattern Recognition**: Detects movies vs TV shows using comprehensive pattern analysis
- **Multi-Factor Analysis**: Combines year patterns, quality indicators, season/episode patterns, and keywords
- **High Accuracy**: Achieves excellent detection rates on real-world content

### 🎯 Smart Destination Routing  
- **Content-Aware Downloads**: Automatically routes content to appropriate destination folders
- **Multiple Destinations**: Support for multiple movie and TV show destination directories
- **Fallback Protection**: General download directory for unclassified content

### 📁 Bulk Folder Operations
- **Entire Folder Downloads**: Download complete folders with one click
- **Content-Type Detection**: Automatically detects folder content type before download
- **Smart Routing**: Routes folder contents to appropriate destinations based on content type

### 🔍 Advanced Content Scanning
- **Server-Wide Scanning**: Scan entire FTP server structure for content
- **Content Classification**: Automatically categorize discovered folders
- **View Filtering**: Filter views to show only movies, TV shows, or other content

## 🎬 Content Detection Patterns

### Movie Detection
- **Year Patterns**: 1900-2099 (e.g., "Movie.2023.1080p")
- **Quality Indicators**: 720p, 1080p, 2160p, 4K, BluRay, WEBRip, etc.
- **Codec Patterns**: x264, x265, H.264, H.265, HEVC, XviD
- **Keywords**: movie, film, cinema, theatrical, remux

### TV Show Detection
- **Episode Patterns**: S01E01, 1x01, Season 1, Episode 1
- **Series Keywords**: series, seasons, episodes, complete series
- **TV-Specific Terms**: tvshow, tv.show, television

### Smart Analysis
- **Context-Aware**: Analyzes folder contents when folder names are ambiguous
- **Multi-Pattern Scoring**: Uses weighted scoring system for accurate classification
- **Special Handling**: Smart detection for common folders like "recent", "x265", etc.

## 🗂️ Destination Management

### Multiple Destination Support
```
🎬 Movie Destinations: D:\Movies;D:\x265;D:\Cinema
📺 TV Show Destinations: D:\TV Shows;D:\Series;D:\Television  
📁 General Downloads: D:\Downloads
```

### Smart Routing Logic
1. **Content Detection**: Analyze folder name and contents
2. **Destination Selection**: Choose appropriate destination based on content type
3. **Fallback Handling**: Use general directory if specific destination not configured
4. **Path Creation**: Automatically create local folder structure

## 🔧 GUI Enhancements

### Content Discovery Panel
- **🔍 Scan Content**: Button to scan entire server for content
- **Content Filter**: Dropdown to filter view by content type
- **🎬 Movie Folders**: Quick access to movie content
- **📺 TV Folders**: Quick access to TV show content

### Enhanced File Browser
- **Content Column**: Shows detected content type for each folder
- **Visual Indicators**: Emoji indicators for movies (🎬), TV shows (📺), other (📁)
- **Smart Highlighting**: Different styling for different content types

### Advanced Download Options
- **📁⬇ Download Folder**: Download entire folders with smart routing
- **Smart Confirmation**: Shows detected content type and destination before download
- **Bulk Operations**: Download multiple folders with batch processing

### Destination Configuration
- **Multiple Paths**: Support semicolon-separated destination lists
- **Browse Integration**: Easy folder selection with browse dialogs
- **Configuration Persistence**: Save destination preferences with connection presets

## 🛠️ Technical Implementation

### Content Detection Algorithm
```python
def detect_content_type(self, folder_name, folder_path=""):
    """Intelligent content type detection"""
    - TV Show pattern matching (S01E01, seasons, series)
    - Movie pattern scoring (year, quality, codec indicators)
    - Context analysis for ambiguous folders
    - Weighted decision making
```

### Smart Routing System
```python
def get_destination_folder(self, content_type, folder_name=""):
    """Content-aware destination selection"""
    - Map content types to configured destinations
    - Support multiple destination directories
    - Graceful fallback to general directory
```

### Bulk Download Engine
```python
def _download_folder_contents(self, folder_name, destination, content_type):
    """Download entire folders with smart routing"""
    - Navigate to remote folder
    - Create local destination structure
    - Apply file filters (*.rar, etc.)
    - Queue all matching files
    - Track content type and source folder
```

## 📊 Content Analysis Features

### Server-Wide Scanning
- **Comprehensive Discovery**: Scan multiple common directories (/recent, /movies, /tv, etc.)
- **Real-Time Analysis**: Immediate content type detection during scan
- **Statistics Reporting**: Show counts of movies, TV shows, and other content
- **Progress Tracking**: Visual feedback during scanning process

### View Filtering
- **Content-Based Views**: Filter to show only specific content types
- **Dynamic Updates**: Real-time filtering without re-scanning
- **Quick Access**: Direct navigation to content categories

## 🔒 Configuration Management

### Enhanced Presets
- **Extended Settings**: Include movie/TV destinations in connection presets
- **Backward Compatibility**: Graceful handling of older presets
- **Smart Defaults**: Intelligent default values for new installations

### Persistent Storage
```json
{
  "name": "Connection Name",
  "host": "server.example.com",
  "movie_dirs": "D:\\Movies;D:\\x265",
  "tv_dirs": "D:\\TV Shows;D:\\Series",
  "download_dir": "D:\\Downloads"
}
```

## 🎯 Usage Workflow

### Initial Setup
1. **Configure Destinations**: Set movie, TV, and general download folders
2. **Save Connection**: Store settings in connection preset
3. **Connect to Server**: Establish FTP connection

### Content Discovery
1. **Scan Content**: Click "🔍 Scan Content" to discover all content
2. **Review Results**: View categorized content in summary dialog
3. **Filter View**: Use content filter to focus on specific types

### Smart Downloads
1. **Browse Content**: Navigate server directories
2. **Select Folders**: Choose movie/TV show folders for download
3. **Confirm Download**: Review detected type and destination
4. **Bulk Download**: System automatically downloads to correct destination

### Advanced Operations
1. **Multiple Destinations**: Configure multiple paths for each content type
2. **Custom Filters**: Set file filters (*.rar, *.mkv, etc.)
3. **Queue Management**: Monitor downloads with enhanced status tracking

## 🔧 Advanced Configuration

### Content Detection Tuning
- **Pattern Customization**: Modify detection patterns for specific servers
- **Threshold Adjustment**: Fine-tune scoring thresholds for better accuracy
- **Server-Specific Rules**: Custom rules for particular FTP server layouts

### Performance Optimization
- **Concurrent Downloads**: Configurable maximum concurrent transfers
- **Smart Caching**: Cache content analysis results
- **Efficient Scanning**: Optimized directory traversal algorithms

## 🏆 Benefits

### User Experience
- **One-Click Operations**: Download entire folders with single click
- **Automatic Organization**: Content automatically goes to correct locations
- **Visual Clarity**: Clear content type indicators throughout interface

### Efficiency Gains
- **Bulk Operations**: Download complete seasons/movie collections efficiently
- **Smart Routing**: Eliminates manual sorting and moving of downloads
- **Server Discovery**: Quickly find and categorize all available content

### Professional Features
- **FlashFXP-Level Compatibility**: Full professional FTP client functionality
- **Enterprise-Grade SSL**: Manual AUTH TLS for maximum server compatibility
- **Intelligent Analysis**: Advanced content detection rivaling commercial software

## 🚀 Future Enhancements

### Planned Features
- **Machine Learning**: ML-based content detection for even higher accuracy
- **Custom Rules**: User-defined content detection rules
- **Batch Processing**: Queue multiple folder downloads with prioritization
- **Integration**: Direct integration with media servers (Plex, Emby, Jellyfin)

### Advanced Routing
- **Quality-Based Routing**: Route based on quality indicators (4K → 4K folder)
- **Genre Detection**: Route by detected genre or category
- **Release Group Handling**: Special handling for specific release groups

This system transforms the FTP panel into an intelligent content management platform, providing professional-grade functionality with automated content discovery and smart routing capabilities. 