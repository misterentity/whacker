# FTP Panel IMDb Integration (On-Demand)

## Overview
The FTP Panel now includes **on-demand** IMDb information and poster thumbnails for movie and TV show releases. This enhancement provides rich metadata when you need it, without slowing down directory browsing.

## ⚡ Performance Focused Design
- **Fast Directory Loading**: Basic file listings load instantly without API delays
- **On-Demand IMDb**: Only fetches information when specifically requested
- **Efficient API Usage**: Reduces unnecessary API calls and respects rate limits
- **Cached Results**: Once fetched, IMDb data and posters are cached locally

## 🎬 How to Use

### Basic Browsing (Fast)
1. Connect to your FTP server
2. Navigate directories normally - listings load instantly
3. Content is automatically identified as 🎬 Movie, 📺 TV Show, or 📁 Other

### Getting IMDb Information
1. **Right-click** any movie or TV show folder
2. Select **"🎬 Show IMDb Info"** from context menu
3. Wait for the API lookup (shows loading dialog)
4. View detailed information in popup window

### Context Menu Options
**Right-click on any item for:**
- **🎬 Show IMDb Info** - Fetch and display full IMDb details (movies/TV only)
- **🖼️ Show Poster** - Display poster if already downloaded
- **📁 Enter Directory** - Navigate into folder
- **⬇ Download** - Add file to download queue
- **📁⬇ Download Folder** - Download entire folder

## Features

### 📊 IMDb Information Window
When you request IMDb info, you get:
- **Movie Title** (cleaned from release name)
- **Year** and **Runtime**
- **⭐ IMDb Rating** out of 10
- **🎭 Genres** 
- **🎬 Director**
- **👥 Cast** list
- **📖 Plot** summary
- **🖼️ Poster** (if available)

### 🖼️ Poster Display
- **Automatic Download**: Posters download when IMDb info is fetched
- **High Quality**: Original resolution cached, thumbnails for display
- **Popup Preview**: Dedicated poster window with larger view
- **Local Storage**: Cached in `thumbnails_cache/` folder

### 🔍 Smart Content Detection
- **Clean Title Extraction**: Removes quality indicators, release groups, technical jargon
- **Year Detection**: Extracts year from folder names for accurate matching
- **Type Recognition**: Automatically detects movies vs TV shows
- **No False Positives**: Only enables IMDb options for actual content

## 🚀 Performance Benefits

### Before (Automatic Loading)
- ❌ 8,461 movies × API calls = Massive delays
- ❌ Directory listing took minutes
- ❌ Wasted API quota on content you don't view
- ❌ Network timeouts and errors

### After (On-Demand)
- ✅ Directory listings load in seconds
- ✅ API calls only when you want them
- ✅ Efficient bandwidth usage
- ✅ No timeout issues during browsing

## Usage Patterns

### Quick Browsing
```
Navigate → Browse → Download
(No API calls, maximum speed)
```

### Detailed Investigation
```
Navigate → Right-click → Show IMDb Info → Download
(API call only when needed)
```

### Poster Collection
```
1. Right-click → Show IMDb Info (downloads poster)
2. Right-click → Show Poster (view cached poster)
```

## Configuration

### API Settings
Edit `ftp_config.json`:
```json
{
  "imdb": {
    "api_key": "your_api_key_here",
    "enable_posters": true,
    "cache_days": 7,
    "api_url": "http://www.omdbapi.com/"
  }
}
```

### Cache Management
- **Location**: `thumbnails_cache/` folder
- **Cleanup**: Delete folder to clear all cached posters
- **Size**: Each poster ~10-20KB compressed

## API Usage

### Free Tier Limits
- **1000 requests/day** with default key
- **Get your own key**: [OMDb API](http://www.omdbapi.com/apikey.aspx)
- **Paid tiers**: Higher limits available

### Efficient Usage
- Only requests info when you right-click
- Caches results to avoid duplicate calls
- No automatic scanning that wastes quota

## Troubleshooting

### IMDb Options Disabled
- Ensure the folder is detected as 🎬 Movie or 📺 TV Show
- Generic folders won't have IMDb options available

### No Results Found
- Release names with unusual formatting may not match
- Try editing the folder name to be more standard
- Foreign films may have limited English data

### Slow API Responses
- Free API can be slower during peak times
- Consider upgrading to paid tier for faster responses
- Loading dialog shows progress

### Connection Issues
- Check internet connection
- Verify API key in config
- Check console for detailed error messages

## Technical Details

### Smart Title Extraction
Removes these patterns for better matching:
- Quality: 720p, 1080p, 2160p, 4K, BluRay, WEB-DL
- Codecs: x264, x265, H265, HEVC, DTS
- Groups: Release group names after dashes
- Extras: Director's Cut, Extended, Remastered

### Caching Strategy
- **Memory**: LRU cache for API responses (500 items)
- **Disk**: Poster images with hash-based filenames
- **Persistence**: Survives application restarts

### Error Handling
- Graceful API failures (shows "No Results")
- Network timeouts handled properly
- Malformed responses logged for debugging

## Best Practices

### Efficient Workflow
1. Browse normally for speed
2. Only fetch IMDb info for content you're interested in
3. Use poster preview after fetching IMDb data

### API Conservation
- Don't spam-click Show IMDb Info
- Results are cached - subsequent clicks are instant
- Use your own API key for heavy usage

---

**Note**: This on-demand approach provides the best of both worlds - fast browsing when you need speed, detailed information when you want it, and efficient API usage that respects rate limits. 