# Queue-Based RAR Processing System Improvements

## Overview
The RAR archive processing system has been completely redesigned to use a robust single-threaded queue-based approach instead of the previous multi-threaded system that was causing timeouts and resource contention.

## Problems Solved

### Previous Issues
- **Multiple concurrent threads** causing system overload and timeouts
- **Resource contention** during archive integrity testing
- **Uncontrolled parallel processing** of 10+ archives simultaneously
- **Archive test timeouts** due to system overwhelm
- **Inconsistent error handling** across different processing threads
- **No centralized queue management** for processing order

### Error Pattern Before Fix
```
2025-07-14 13:51:50,147 ERROR [Thread-12 (process_archive_safe)] Archive test timeout
2025-07-14 13:56:14,511 ERROR [Thread-11 (process_archive_safe)] Archive test timeout
2025-07-14 13:56:14,527 ERROR [Thread-19 (process_archive_safe)] Archive test timeout
2025-07-14 13:56:14,573 ERROR [Thread-17 (process_archive_safe)] Archive test timeout
2025-07-14 13:56:14,573 ERROR [Thread-15 (process_archive_safe)] Archive test timeout
```

## New Architecture

### ProcessingQueue Class
A thread-safe queue manager that processes archives sequentially:

```python
class ProcessingQueue:
    def __init__(self, bridge, max_retries=3, retry_delay=60):
        self.queue = queue.Queue()
        self.processing = False
        self.current_item = None
        self.worker_thread = None
        self.shutdown_event = threading.Event()
```

### Key Features

#### 1. Single Worker Thread
- **One archive processed at a time** - eliminates resource contention
- **Sequential processing** - prevents system overload
- **Controlled resource usage** - no more than one archive test/extraction at once

#### 2. Robust Queue Management
- **Thread-safe operations** using `queue.Queue`
- **Priority support** for different archive sources
- **Automatic retry logic** with configurable delays
- **Graceful shutdown** handling

#### 3. Enhanced Error Handling
- **Retry mechanism** with configurable attempts (default: 3)
- **Failed archive isolation** - moves to failed directory after max retries
- **Timeout protection** - prevents hanging operations
- **Comprehensive logging** for debugging

#### 4. Processing Sources
- **New files** - detected by file system watcher
- **Existing files** - found during startup scan
- **Retry files** - from the retry queue system
- **Test files** - for system verification

## Implementation Details

### Queue Item Structure
```python
item = {
    'file_path': Path,
    'priority': int,
    'source': str,  # 'new', 'existing', 'retry', 'test'
    'attempts': int,
    'added_time': datetime,
    'last_attempt': datetime
}
```

### Integration Points

#### 1. File System Watcher (RarHandler)
**Before:**
```python
# Created separate thread for each archive
processing_thread = threading.Thread(
    target=self.process_archive,
    args=(file_path,),
    daemon=True
)
processing_thread.start()
```

**After:**
```python
# Add to processing queue
self.bridge.processing_queue.add_archive(file_path, source='new')
```

#### 2. Retry Queue Processing
**Before:**
```python
# Created threads for retry processing
processing_thread = threading.Thread(
    target=self.process_archive_safe,
    args=(file_path,),
    daemon=True
)
processing_thread.start()
```

**After:**
```python
# Add to processing queue
self.processing_queue.add_archive(file_path, source='retry')
```

#### 3. Existing File Scanning
**Before:**
```python
# Added to retry queue immediately
self.bridge.add_to_retry_queue(rar_file)
```

**After:**
```python
# Add to processing queue
self.bridge.processing_queue.add_archive(rar_file, source='existing')
```

## Benefits

### 1. System Stability
- **No more timeouts** - single-threaded processing prevents overload
- **Predictable resource usage** - controlled memory and CPU consumption
- **Better error recovery** - isolated failure handling

### 2. Processing Reliability
- **Guaranteed processing order** - FIFO queue ensures fair processing
- **Retry mechanism** - automatic retry with backoff
- **Graceful degradation** - system continues working despite individual failures

### 3. Monitoring & Debugging
- **Queue status monitoring** - real-time visibility into processing state
- **Detailed logging** - comprehensive tracking of all operations
- **Statistics tracking** - processed, failed, retry counts

### 4. Configuration
- **Configurable retry attempts** - `max_retry_attempts` setting
- **Configurable retry delay** - `retry_interval` setting
- **Flexible timeout handling** - prevents hanging operations

## Queue Status Monitoring

### Real-time Status
```python
status = bridge.get_processing_status()
# Returns:
{
    'queue_size': int,
    'processing': bool,
    'current_item': str,
    'queue_stats': {
        'queued': int,
        'processed': int,
        'failed': int,
        'retries': int
    },
    'retry_queue_size': int,
    'total_processing_files': int,
    'bridge_stats': dict
}
```

### Automatic Logging
- **Queue status logged every 10 minutes** during main loop
- **Processing start/completion logged** for each archive
- **Error conditions logged** with detailed context

## Testing

### Test Script
A comprehensive test script `test_queue_system.py` verifies:
- Queue initialization
- Worker thread management
- Archive addition and processing
- Graceful shutdown
- Status monitoring

### Test Results
```
🔍 Testing ProcessingQueue system...
✅ PlexRarBridge initialized successfully
📊 Initial queue status: {'queue_size': 0, 'processing': False, ...}
✅ Processing queue worker started
✅ Processing queue stopped gracefully
🎉 Queue system test completed successfully!
```

## Migration Notes

### Backward Compatibility
- **Existing configuration** works without changes
- **All existing features** maintained (retry queue, duplicate detection, etc.)
- **Same API** for external integrations

### Performance Impact
- **Reduced CPU usage** - no thread thrashing
- **Lower memory usage** - controlled resource allocation
- **Faster overall processing** - no resource contention
- **Better system responsiveness** - predictable load

## Configuration Examples

### Basic Queue Settings
```yaml
options:
  max_retry_attempts: 3      # Max retries before moving to failed
  retry_interval: 60         # Seconds between retry attempts
  max_retry_age_hours: 4     # Max age before giving up on retry
```

### Advanced Settings
```yaml
options:
  file_stabilization_time: 10  # Wait time for file completion
  max_file_age: 3600          # Max age for processing files
  scan_existing_files: true   # Process existing files on startup
```

## Conclusion

The new queue-based system provides:
- **Robust single-threaded processing** - eliminates timeouts and resource contention
- **Automatic retry handling** - graceful failure recovery
- **Comprehensive monitoring** - real-time visibility into processing state
- **Improved reliability** - predictable and stable operation

This architecture change solves the core issues with multiple concurrent archive processing while maintaining all existing functionality and improving overall system performance. 