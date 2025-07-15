"""
plex_rar_bridge.py – Enhanced RAR extraction bridge for Plex Media Server

Features:
- Monitors folder for RAR sets, extracts, and moves media into Plex library
- SHA-256 duplicate detection
- H.265 re-encoding with HandBrake
- Encrypted archive handling
- System tray GUI (optional)
- Comprehensive logging and error handling
- Atomic file operations

Run with:  python plex_rar_bridge.py
Register as a service via NSSM if desired.
"""

import os
import sys
import time
import shutil
import subprocess
import logging
import yaml
import hashlib
import json
import threading
import sqlite3
import queue
from pathlib import Path
from datetime import datetime, timedelta
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from logging.handlers import RotatingFileHandler
import rarfile
import requests
from tqdm import tqdm
import functools

# Optional GUI imports
try:
    import pystray
    from PIL import Image, ImageDraw
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

# Optional rar2fs imports
try:
    from rar2fs_handler import Rar2fsHandler
    RAR2FS_AVAILABLE = True
except ImportError:
    RAR2FS_AVAILABLE = False

# Python RAR VFS imports (always available)
try:
    from python_rar_vfs import PythonRarVfsHandler
    PYTHON_RAR_VFS_AVAILABLE = True
except ImportError:
    PYTHON_RAR_VFS_AVAILABLE = False

class ProcessingQueue:
    """Thread-safe queue for processing RAR archives one at a time"""
    
    def __init__(self, bridge, max_retries=3, retry_delay=60):
        self.bridge = bridge
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.queue = queue.Queue()
        self.processing = False
        self.current_item = None
        self.worker_thread = None
        self.shutdown_event = threading.Event()
        self.stats = {
            'queued': 0,
            'processed': 0,
            'failed': 0,
            'retries': 0
        }
        
    def start(self):
        """Start the processing worker thread"""
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.shutdown_event.clear()
            self.worker_thread = threading.Thread(target=self._worker, daemon=True)
            self.worker_thread.start()
            self.bridge.logger.info("Processing queue worker started")
    
    def stop(self):
        """Stop the processing worker thread"""
        self.shutdown_event.set()
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)
            self.bridge.logger.info("Processing queue worker stopped")
    
    def add_archive(self, file_path, priority=0, source='new'):
        """Add archive to processing queue"""
        if not file_path.exists():
            self.bridge.logger.warning(f"Archive file does not exist: {file_path}")
            return False
        
        # Check if already in queue or processing
        if self.current_item and self.current_item['file_path'] == file_path:
            self.bridge.logger.debug(f"Archive already being processed: {file_path.name}")
            return False
        
        # Add to queue
        item = {
            'file_path': file_path,
            'priority': priority,
            'source': source,
            'attempts': 0,
            'added_time': datetime.now(),
            'last_attempt': None
        }
        
        self.queue.put(item)
        self.stats['queued'] += 1
        self.bridge.logger.info(f"Added to processing queue ({source}): {file_path.name} (queue size: {self.queue.qsize()})")
        return True
    
    def get_queue_status(self):
        """Get current queue status"""
        return {
            'queue_size': self.queue.qsize(),
            'processing': self.processing,
            'current_item': self.current_item['file_path'].name if self.current_item else None,
            'stats': self.stats.copy()
        }
    
    def _worker(self):
        """Worker thread that processes archives sequentially"""
        self.bridge.logger.info("Archive processing worker thread started")
        
        while not self.shutdown_event.is_set():
            try:
                # Get next item from queue
                try:
                    item = self.queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                self.current_item = item
                self.processing = True
                file_path = item['file_path']
                
                try:
                    # Check if file still exists
                    if not file_path.exists():
                        self.bridge.logger.warning(f"Archive file no longer exists: {file_path.name}")
                        continue
                    
                    # Update attempt info
                    item['attempts'] += 1
                    item['last_attempt'] = datetime.now()
                    
                    self.bridge.logger.info(f"Processing archive (attempt {item['attempts']}): {file_path.name}")
                    
                    # Process the archive
                    success = self._process_archive_with_retry(item)
                    
                    if success:
                        self.stats['processed'] += 1
                        self.bridge.logger.info(f"Successfully processed: {file_path.name}")
                    else:
                        # Handle retry logic
                        if item['attempts'] < self.max_retries:
                            self.stats['retries'] += 1
                            self.bridge.logger.warning(f"Processing failed, will retry: {file_path.name} (attempt {item['attempts']}/{self.max_retries})")
                            
                            # Add back to queue with delay
                            retry_item = item.copy()
                            retry_item['source'] = 'retry'
                            
                            # Use a separate thread to add back after delay
                            def delayed_retry():
                                time.sleep(self.retry_delay)
                                if not self.shutdown_event.is_set():
                                    self.queue.put(retry_item)
                                    self.bridge.logger.info(f"Re-queued for retry: {file_path.name}")
                            
                            threading.Thread(target=delayed_retry, daemon=True).start()
                        else:
                            self.stats['failed'] += 1
                            self.bridge.logger.error(f"Max retry attempts reached for: {file_path.name}")
                            
                            # Move to failed directory
                            self._move_to_failed_directory(file_path)
                
                except Exception as e:
                    self.bridge.logger.exception(f"Unexpected error processing {file_path.name}: {e}")
                    self.stats['failed'] += 1
                
                finally:
                    self.processing = False
                    self.current_item = None
                    self.queue.task_done()
                    
                    # Small delay between processing items
                    time.sleep(1)
                    
            except Exception as e:
                self.bridge.logger.exception(f"Worker thread error: {e}")
                time.sleep(5)  # Wait before retrying
        
        self.bridge.logger.info("Archive processing worker thread stopped")
    
    def _process_archive_with_retry(self, item):
        """Process archive with enhanced error handling"""
        file_path = item['file_path']
        
        try:
            # Remove from processing_files set (legacy support)
            self.bridge.processing_files.discard(str(file_path))
            self.bridge.processing_files.add(str(file_path))
            
            # Call the existing extract_archive method
            self.bridge.extract_archive(file_path)
            return True
            
        except subprocess.TimeoutExpired:
            self.bridge.logger.error(f"Archive processing timeout: {file_path.name}")
            return False
        except Exception as e:
            self.bridge.logger.exception(f"Archive processing error: {file_path.name}: {e}")
            return False
        finally:
            # Clean up processing_files set
            self.bridge.processing_files.discard(str(file_path))
    
    def _move_to_failed_directory(self, file_path):
        """Move failed archive to failed directory"""
        try:
            failed_dir = Path(self.bridge.config['paths']['failed'])
            failed_dir.mkdir(parents=True, exist_ok=True)
            
            # Get all volumes for this archive
            volumes = self.bridge.get_archive_volumes(file_path)
            
            for vol in volumes:
                if vol.exists():
                    failed_path = failed_dir / vol.name
                    if not failed_path.exists():
                        shutil.move(vol, failed_path)
                        self.bridge.logger.info(f"Moved failed archive to: {failed_path}")
                    else:
                        self.bridge.logger.warning(f"Failed archive already exists: {failed_path}")
                        
        except Exception as e:
            self.bridge.logger.exception(f"Error moving failed archive: {e}")

class PlexRarBridge:
    def __init__(self, config_path="config.yaml"):
        self.config = self._load_config(config_path)
        self.setup_logging()
        self.setup_config = self._load_setup_config()
        self.setup_directories()
        self.setup_database()
        self.observers = []  # Multiple observers for multiple directories
        self.tray_icon = None
        self.processing_files = set()
        self.retry_queue = {}  # {file_path: {'attempts': count, 'last_attempt': datetime, 'first_seen': datetime}}
        self.directory_pairs = {}  # {source_path: {'target': target_path, 'library_key': key}}
        self.stats = {
            'processed': 0,
            'duplicates': 0,
            'errors': 0,
            'retries': 0,
            'start_time': datetime.now()
        }
        
        # Initialize processing queue
        max_retries = self.config.get('options', {}).get('max_retry_attempts', 3)
        retry_delay = self.config.get('options', {}).get('retry_interval', 60)
        self.processing_queue = ProcessingQueue(self, max_retries=max_retries, retry_delay=retry_delay)
        
        # Initialize virtual filesystem handler based on processing mode
        self.rar2fs_handler = None
        processing_mode = self.config.get('options', {}).get('processing_mode', 'extraction')
        
        if processing_mode == 'rar2fs':
            self._setup_rar2fs_handler()
        elif processing_mode == 'python_vfs':
            self._setup_python_vfs_handler()
        
        # Setup directory pairs
        self._setup_directory_pairs()
        
    def _load_config(self, config_path):
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            sys.exit(1)
    
    def _load_setup_config(self):
        """Load setup configuration from JSON file"""
        try:
            setup_config_path = Path("setup_config.json")
            if setup_config_path.exists():
                import json
                with open(setup_config_path, 'r') as f:
                    setup_config = json.load(f)
                self.logger.info(f"Loaded setup configuration with {len(setup_config.get('directory_pairs', []))} directory pairs")
                return setup_config
        except Exception as e:
            self.logger.warning(f"Could not load setup config: {e}")
        return None
    
    def _setup_directory_pairs(self):
        """Setup directory pairs from setup configuration with per-directory processing modes"""
        if not self.setup_config or not self.setup_config.get('directory_pairs'):
            # Fallback to main config
            watch_path = self.config.get('paths', {}).get('watch')
            target_path = self.config.get('paths', {}).get('target')
            if watch_path and target_path:
                library_key = self.config.get('plex', {}).get('library_key', 1)
                processing_mode = self.config.get('options', {}).get('processing_mode', 'python_vfs')
                self.directory_pairs[watch_path] = {
                    'target': target_path,
                    'library_key': library_key,
                    'processing_mode': processing_mode,
                    'enabled': True
                }
                self.logger.info(f"Using main config: {watch_path} -> {target_path} (Mode: {processing_mode})")
        else:
            # Use setup config directory pairs
            for pair in self.setup_config['directory_pairs']:
                if pair.get('enabled', True):
                    source = pair['source']
                    target = pair['target']
                    library_key = pair.get('library_key', '1')
                    processing_mode = pair.get('processing_mode', self.config.get('options', {}).get('global_processing_mode', 'python_vfs'))
                    
                    self.directory_pairs[source] = {
                        'target': target,
                        'library_key': int(library_key) if library_key.isdigit() else 1,
                        'processing_mode': processing_mode,
                        'enabled': True
                    }
                    self.logger.info(f"Directory pair: {source} -> {target} (Library: {library_key}, Mode: {processing_mode})")
        
                    self.logger.info(f"Configured {len(self.directory_pairs)} directory pairs for monitoring")
    
    def _get_target_info_for_file(self, file_path):
        """Get target directory, library key, and processing mode for a file based on its source directory"""
        file_path = Path(file_path)
        
        # Find the matching source directory
        for source_dir, info in self.directory_pairs.items():
            source_path = Path(source_dir)
            try:
                # Check if file is under this source directory
                file_path.relative_to(source_path)
                return {
                    'target': info['target'],
                    'library_key': info['library_key'],
                    'processing_mode': info.get('processing_mode', 'python_vfs')
                }
            except ValueError:
                continue
        
        # Fallback to main config if no match found
        return {
            'target': self.config.get('paths', {}).get('target', 'D:/Media/Movies'),
            'library_key': self.config.get('plex', {}).get('library_key', 1)
        }
    
    def setup_logging(self):
        """Setup rotating log handler"""
        log_level = getattr(logging, self.config['logging']['level'].upper())
        
        # Create logs directory
        os.makedirs('logs', exist_ok=True)
        
        # Setup rotating file handler
        handler = RotatingFileHandler(
            'logs/bridge.log',
            maxBytes=self.config['logging']['max_log_size'],
            backupCount=self.config['logging']['backup_count']
        )
        
        formatter = logging.Formatter(
            '%(asctime)s %(levelname)s [%(threadName)s] %(message)s'
        )
        handler.setFormatter(formatter)
        
        # Setup logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)
        self.logger.addHandler(handler)
        
        # Also log to console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
    def setup_directories(self):
        """Create required directories"""
        for path_key in ['watch', 'work', 'target', 'failed', 'archive']:
            if path_key in self.config['paths']:
                path = Path(self.config['paths'][path_key])
                path.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"Created/verified directory: {path}")
    
    def setup_database(self):
        """Setup SQLite database for hash tracking"""
        if not self.config['options']['duplicate_check']:
            return
            
        self.db_path = Path('data/hashes.db')
        self.db_path.parent.mkdir(exist_ok=True)
        
        conn = sqlite3.connect(str(self.db_path))
        conn.execute('''
            CREATE TABLE IF NOT EXISTS file_hashes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                sha256_hash TEXT NOT NULL UNIQUE,
                file_size INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    
    def calculate_file_hash(self, file_path):
        """Calculate SHA-256 hash of a file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def is_duplicate(self, file_path):
        """Check if file is a duplicate based on SHA-256 hash"""
        if not self.config['options']['duplicate_check']:
            return False
            
        file_hash = self.calculate_file_hash(file_path)
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.execute(
            'SELECT filename, file_path FROM file_hashes WHERE sha256_hash = ?',
            (file_hash,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if result:
            self.logger.info(f"Duplicate detected: {file_path.name} matches {result[0]}")
            return True
        else:
            # Add to database
            conn = sqlite3.connect(str(self.db_path))
            conn.execute(
                'INSERT INTO file_hashes (filename, file_path, sha256_hash, file_size) VALUES (?, ?, ?, ?)',
                (file_path.name, str(file_path), file_hash, file_path.stat().st_size)
            )
            conn.commit()
            conn.close()
            return False
    
    def _setup_rar2fs_handler(self):
        """Setup rar2fs handler for virtual file system operations"""
        if not RAR2FS_AVAILABLE:
            self.logger.error("rar2fs_handler module not available")
            raise Exception("rar2fs_handler module not available")
        
        try:
            self.rar2fs_handler = Rar2fsHandler(self.config, self.logger)
            self.logger.info("rar2fs handler initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize rar2fs handler: {e}")
            raise e
    
    def _setup_python_vfs_handler(self):
        """Setup Python VFS handler for virtual file system operations"""
        if not PYTHON_RAR_VFS_AVAILABLE:
            self.logger.error("python_rar_vfs module not available")
            raise Exception("python_rar_vfs module not available")
        
        try:
            self.rar2fs_handler = PythonRarVfsHandler(self.config, self.logger)
            self.logger.info("Python RAR VFS handler initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Python RAR VFS handler: {e}")
            raise e
    
    def plex_refresh(self, library_key=None):
        """Trigger Plex library refresh with enhanced detection"""
        # Use provided library_key or fall back to config
        if library_key is None:
            library_key = self.config['plex']['library_key']
        
        # Use setup config for host/token if available
        plex_host = self.config['plex']['host']
        plex_token = self.config['plex']['token']
        
        if self.setup_config and self.setup_config.get('plex'):
            plex_host = self.setup_config['plex'].get('host', plex_host)
            plex_token = self.setup_config['plex'].get('token', plex_token)
        
        url = f"{plex_host.rstrip('/')}/library/sections/{library_key}/refresh"
        params = {'X-Plex-Token': plex_token}
        
        try:
            # First, try a forced refresh
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            self.logger.info(f"Triggered Plex library refresh for library {library_key}")
            
            # Wait a moment, then force a scan
            time.sleep(2)
            scan_url = f"{plex_host.rstrip('/')}/library/sections/{library_key}/refresh?force=1"
            response = requests.get(scan_url, params=params, timeout=10)
            response.raise_for_status()
            self.logger.info(f"Triggered forced Plex library scan for library {library_key}")
            
        except Exception as e:
            self.logger.error(f"Plex refresh failed for library {library_key}: {e}")
    
    def create_plex_detection_test(self):
        """Create a test file to verify Plex can detect files in target directory"""
        try:
            target_dir = Path(self.config['paths']['target'])
            test_file = target_dir / "plex_test_detection.txt"
            
            with open(test_file, 'w') as f:
                f.write(f"Plex RAR Bridge test file - Created: {datetime.now()}\n")
                f.write("If you see this file in your Plex library, detection is working!\n")
            
            self.logger.info(f"Created Plex detection test file: {test_file}")
            
            # Trigger scan and wait
            self.plex_refresh()
            time.sleep(5)
            
            # Clean up test file
            if test_file.exists():
                test_file.unlink()
                self.logger.info("Cleaned up Plex detection test file")
                
        except Exception as e:
            self.logger.error(f"Failed to create Plex detection test: {e}")
    
    def verify_plex_target_directory(self):
        """Verify that the target directory is actually monitored by Plex"""
        try:
            # Get library details
            url = f"{self.config['plex']['host'].rstrip('/')}/library/sections/{self.config['plex']['library_key']}"
            params = {'X-Plex-Token': self.config['plex']['token']}
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            # Parse XML to get library paths
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)
            
            library_paths = []
            for directory in root.findall('.//Directory'):
                path = directory.get('path')
                if path:
                    library_paths.append(Path(path).resolve())
            
            target_path = Path(self.config['paths']['target']).resolve()
            
            # Check if target is in library paths or subdirectory
            path_match = False
            for lib_path in library_paths:
                try:
                    target_path.relative_to(lib_path)
                    path_match = True
                    break
                except ValueError:
                    continue
            
            if path_match:
                self.logger.info(f"Target directory {target_path} is monitored by Plex")
                return True
            else:
                self.logger.warning(f"Target directory {target_path} may not be monitored by Plex")
                self.logger.warning(f"Plex library paths: {library_paths}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to verify Plex target directory: {e}")
            return False
    
    def add_to_retry_queue(self, file_path):
        """Add file to retry queue for later processing"""
        file_str = str(file_path)
        current_time = datetime.now()
        
        if file_str in self.retry_queue:
            # Update existing entry
            self.retry_queue[file_str]['attempts'] += 1
            self.retry_queue[file_str]['last_attempt'] = current_time
        else:
            # New entry
            self.retry_queue[file_str] = {
                'attempts': 1,
                'last_attempt': current_time,
                'first_seen': current_time
            }
        
        attempts = self.retry_queue[file_str]['attempts']
        self.logger.info(f"Added to retry queue (attempt {attempts}): {file_path.name}")
    
    def process_retry_queue(self):
        """Process files in retry queue that might now be complete"""
        if not self.retry_queue:
            return
        
        current_time = datetime.now()
        retry_interval = self.config['options'].get('retry_interval', 60)
        max_attempts = self.config['options'].get('max_retry_attempts', 20)
        max_age_hours = self.config['options'].get('max_retry_age_hours', 4)
        
        files_to_remove = []
        files_to_process = []
        
        for file_str, info in self.retry_queue.items():
            file_path = Path(file_str)
            
            # Check if file still exists
            if not file_path.exists():
                self.logger.info(f"File no longer exists, removing from retry queue: {file_path.name}")
                files_to_remove.append(file_str)
                continue
            
            # Check age limit
            age = current_time - info['first_seen']
            if age.total_seconds() > (max_age_hours * 3600):
                self.logger.warning(f"File too old ({age}), removing from retry queue: {file_path.name}")
                files_to_remove.append(file_str)
                continue
            
            # Check attempt limit
            if info['attempts'] >= max_attempts:
                self.logger.warning(f"Too many attempts ({info['attempts']}), removing from retry queue: {file_path.name}")
                files_to_remove.append(file_str)
                continue
            
            # Check if enough time has passed since last attempt
            time_since_last = current_time - info['last_attempt']
            if time_since_last.total_seconds() < retry_interval:
                continue
            
            # Check if file is now complete
            if self.is_file_complete(file_path):
                # Only process first volumes
                if self.is_first_volume_static(file_path):
                    files_to_process.append(file_path)
                files_to_remove.append(file_str)
            else:
                # Update attempt info
                info['attempts'] += 1
                info['last_attempt'] = current_time
                self.stats['retries'] += 1
                self.logger.debug(f"File still incomplete (attempt {info['attempts']}): {file_path.name}")
        
        # Remove processed/expired files from queue
        for file_str in files_to_remove:
            self.retry_queue.pop(file_str, None)
        
        # Process ready files using the new queue system
        for file_path in files_to_process:
            if str(file_path) not in self.processing_files:
                self.logger.info(f"Retry successful, adding to processing queue: {file_path.name}")
                self.processing_queue.add_archive(file_path, source='retry')
    
    def process_archive_safe(self, file_path):
        """Safely process archive with error handling"""
        try:
            self.extract_archive(file_path)
        except Exception as e:
            self.logger.exception(f"Error processing {file_path}: {e}")
            self.stats['errors'] += 1
        finally:
            self.processing_files.discard(str(file_path))
    
    def get_processing_status(self):
        """Get current processing status including queue information"""
        queue_status = self.processing_queue.get_queue_status()
        return {
            'queue_size': queue_status['queue_size'],
            'processing': queue_status['processing'],
            'current_item': queue_status['current_item'],
            'queue_stats': queue_status['stats'],
            'retry_queue_size': len(self.retry_queue),
            'total_processing_files': len(self.processing_files),
            'bridge_stats': self.stats.copy()
        }
    
    def is_first_volume_static(self, file_path):
        """Static method to check if file is first volume (for retry queue)"""
        name = file_path.name.lower()
        
        # Check for .part1.rar or .part01.rar
        if '.part' in name:
            return '.part1.rar' in name or '.part01.rar' in name
        
        # Check for .rar extension (first volume)
        return name.endswith('.rar')
    
    def is_file_complete(self, file_path):
        """Check if file is completely copied using size stabilization"""
        if not file_path.exists():
            return False
            
        stabilization_time = self.config['options']['file_stabilization_time']
        
        try:
            initial_size = file_path.stat().st_size
            time.sleep(stabilization_time)
            
            if not file_path.exists():
                return False
                
            final_size = file_path.stat().st_size
            return initial_size == final_size and final_size > 0
        except Exception as e:
            self.logger.error(f"Error checking file completion for {file_path}: {e}")
            return False
    
    def get_archive_volumes(self, first_volume):
        """Get all volumes in a RAR archive set"""
        volumes = []
        base_path = first_volume.parent
        
        # Handle different naming conventions
        if '.part' in first_volume.name:
            # part1.rar, part2.rar, etc.
            stem = first_volume.name.split('.part')[0]
            pattern = f"{stem}.part*.rar"
        else:
            # .rar, .r00, .r01, etc.
            stem = first_volume.stem
            extensions = ['.rar'] + [f'.r{i:02d}' for i in range(100)]
            volumes = [base_path / f"{stem}{ext}" for ext in extensions if (base_path / f"{stem}{ext}").exists()]
            return sorted(volumes)
        
        # Find all matching volumes
        for vol in sorted(base_path.glob(pattern)):
            if vol.exists():
                volumes.append(vol)
        
        return volumes
    
    def test_archive_integrity(self, first_volume):
        """Test RAR archive integrity and check for encryption"""
        try:
            # Test with unrar command
            result = subprocess.run(
                ["unrar", "t", "-idp", str(first_volume)],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                if "password" in result.stderr.lower() or "encrypted" in result.stderr.lower():
                    self.logger.warning(f"Archive is encrypted: {first_volume.name}")
                    return "encrypted"
                else:
                    self.logger.error(f"Archive integrity test failed: {first_volume.name}")
                    self.logger.error(f"Error output: {result.stderr}")
                    return "corrupted"
            
            return "ok"
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"Archive test timeout for {first_volume.name}")
            return "timeout"
        except Exception as e:
            self.logger.error(f"Archive test error for {first_volume.name}: {e}")
            return "error"
    
    def sanitize_filename(self, filename):
        """Sanitize filename for Plex compatibility"""
        # Remove/replace problematic characters
        problematic_chars = ['<', '>', ':', '"', '|', '?', '*']
        for char in problematic_chars:
            filename = filename.replace(char, '_')
        
        # Handle common naming patterns
        # Example: convert "Movie.Title.2024.1080p.BluRay.x264-GROUP" to "Movie Title (2024).mkv"
        name_parts = filename.split('.')
        if len(name_parts) > 2:
            # Try to identify year
            year = None
            clean_parts = []
            
            for part in name_parts:
                if part.isdigit() and len(part) == 4 and 1900 <= int(part) <= 2030:
                    year = part
                    break
                elif part.lower() in ['1080p', '720p', '480p', 'bluray', 'webrip', 'hdtv']:
                    break
                else:
                    clean_parts.append(part)
            
            if clean_parts:
                title = ' '.join(clean_parts)
                if year:
                    return f"{title} ({year}){Path(filename).suffix}"
        
        return filename
    
    def reencode_with_handbrake(self, input_file, output_file):
        """Re-encode video file using HandBrake"""
        if not self.config['options']['enable_reencoding'] or not self.config['handbrake']['enabled']:
            return str(input_file)
        
        handbrake_cmd = [
            self.config['handbrake']['executable'],
            '-i', str(input_file),
            '-o', str(output_file),
            '--preset', self.config['handbrake']['preset'],
            '--quality', str(self.config['handbrake']['quality']),
            '--verbose=1'
        ]
        
        try:
            self.logger.info(f"Starting H.265 re-encoding: {input_file.name}")
            result = subprocess.run(
                handbrake_cmd,
                capture_output=True,
                text=True,
                timeout=7200  # 2 hours timeout
            )
            
            if result.returncode == 0:
                self.logger.info(f"Re-encoding completed: {output_file.name}")
                # Remove original file
                input_file.unlink()
                return str(output_file)
            else:
                self.logger.error(f"HandBrake encoding failed: {result.stderr}")
                return str(input_file)
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"HandBrake encoding timeout for {input_file.name}")
            return str(input_file)
        except Exception as e:
            self.logger.error(f"HandBrake encoding error: {e}")
            return str(input_file)
    
    def extract_archive(self, first_volume):
        """Process RAR archive using configured processing mode (per-directory)"""
        # Get target info including processing mode for this specific directory
        target_info = self._get_target_info_for_file(first_volume)
        processing_mode = target_info.get('processing_mode', 'extraction')
        
        # Smart processing mode selection for large multi-volume archives
        if processing_mode == 'python_vfs':
            archive_size, volume_count = self._analyze_archive_complexity(first_volume)
            
            # Auto-fallback to extraction for very large multi-volume archives
            # Python VFS struggles with files >8GB across >15 volumes due to rarfile library limitations
            if archive_size > 8 * 1024**3 and volume_count > 15:  # >8GB and >15 volumes
                self.logger.warning(f"Large multi-volume archive detected: {archive_size / (1024**3):.1f}GB across {volume_count} volumes")
                self.logger.warning(f"Auto-switching to extraction mode for better reliability: {first_volume.name}")
                processing_mode = 'extraction'
            elif archive_size > 15 * 1024**3:  # >15GB regardless of volume count
                self.logger.warning(f"Very large archive detected: {archive_size / (1024**3):.1f}GB")
                self.logger.warning(f"Auto-switching to extraction mode for better reliability: {first_volume.name}")
                processing_mode = 'extraction'
        
        self.logger.info(f"Processing {first_volume.name} using mode: {processing_mode}")
        
        if processing_mode == 'rar2fs':
            return self._process_archive_rar2fs(first_volume)
        elif processing_mode == 'python_vfs':
            return self._process_archive_python_vfs(first_volume)
        else:
            return self._process_archive_extraction(first_volume)
    
    def _analyze_archive_complexity(self, first_volume):
        """Analyze RAR archive to determine size and volume count"""
        try:
            import rarfile
            
            # Get all volumes in the archive set
            volumes = self.get_archive_volumes(first_volume)
            volume_count = len(volumes)
            
            # Calculate total archive size
            total_size = 0
            for volume in volumes:
                if volume.exists():
                    total_size += volume.stat().st_size
            
            # Try to get actual content size from RAR file
            try:
                with rarfile.RarFile(first_volume) as rf:
                    content_size = sum(info.file_size for info in rf.infolist() if not info.is_dir())
                    # Use the larger of archive size or content size
                    total_size = max(total_size, content_size)
            except Exception as e:
                self.logger.debug(f"Could not read RAR content size: {e}")
            
            return total_size, volume_count
            
        except Exception as e:
            self.logger.error(f"Error analyzing archive complexity: {e}")
            return 0, 1
    
    def _process_archive_rar2fs(self, first_volume):
        """Process RAR archive using rar2fs virtual file system"""
        if not self.rar2fs_handler:
            raise Exception("rar2fs handler not initialized")
        
        try:
            # Determine target directory and library key based on source
            target_info = self._get_target_info_for_file(first_volume)
            
            self.logger.info(f"Starting rar2fs mount: {first_volume.name}")
            
            # Test archive integrity first
            test_result = self.test_archive_integrity(first_volume)
            
            if test_result == "encrypted":
                # Move to failed directory
                self._move_archive_to_failed(first_volume)
                return
            elif test_result != "ok":
                self.logger.error(f"Archive test failed: {first_volume.name}")
                return
            
            # Mount the archive using rar2fs
            mount_info = self.rar2fs_handler.mount_archive(first_volume, target_info)
            
            # Handle archive files based on config
            if self.config['options']['delete_archives']:
                volumes = self.get_archive_volumes(first_volume)
                for vol in volumes:
                    if vol.exists():
                        vol.unlink()
                        self.logger.info(f"Deleted archive volume: {vol.name}")
            else:
                # Move to archive directory
                self._move_archive_to_archive_dir(first_volume)
            
            # Update stats
            self.stats['processed'] += len(mount_info.get('target_links', []))
            
            # Trigger Plex refresh
            self.plex_refresh(target_info['library_key'])
            
            self.logger.info(f"Successfully processed with rar2fs: {first_volume.name}")
            
        except Exception as e:
            self.logger.error(f"rar2fs processing failed for {first_volume.name}: {e}")
            # Move to failed directory on error
            self._move_archive_to_failed(first_volume)
            raise e
    
    def _process_archive_python_vfs(self, first_volume):
        """Process RAR archive using Python virtual file system"""
        if not self.rar2fs_handler:
            raise Exception("Python VFS handler not initialized")
        
        try:
            # Determine target directory and library key based on source
            target_info = self._get_target_info_for_file(first_volume)
            
            self.logger.info(f"Starting Python VFS mount: {first_volume.name}")
            
            # Skip archive integrity testing for Python VFS mode
            # Python VFS can handle serving files directly from archives
            # without needing to extract them first
            self.logger.info(f"Skipping integrity test for Python VFS mode: {first_volume.name}")
            
            # Mount the archive using Python VFS
            mount_info = self.rar2fs_handler.mount_archive(first_volume, target_info)
            
            # Handle archive files based on config
            if self.config['options']['delete_archives']:
                volumes = self.get_archive_volumes(first_volume)
                for vol in volumes:
                    if vol.exists():
                        vol.unlink()
                        self.logger.info(f"Deleted archive volume: {vol.name}")
            else:
                # For Python VFS mode, keep archives in place for HTTP server access
                self.logger.info(f"Archive files kept in place for Python VFS: {first_volume.name}")
            
            # Update stats
            self.stats['processed'] += len(mount_info.get('target_links', []))
            
            # Trigger Plex refresh
            self.plex_refresh(target_info['library_key'])
            
            self.logger.info(f"Successfully processed with Python VFS: {first_volume.name}")
            
        except Exception as e:
            self.logger.error(f"Python VFS processing failed for {first_volume.name}: {e}")
            # Move to failed directory on error
            self._move_archive_to_failed(first_volume)
            raise e
    
    def _process_archive_extraction(self, first_volume):
        """Extract RAR archive set (traditional method)"""
        try:
            stem = first_volume.stem.split('.part')[0] if '.part' in first_volume.name else first_volume.stem
            dest_dir = Path(self.config['paths']['work']) / stem
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            # Determine target directory and library key based on source
            target_info = self._get_target_info_for_file(first_volume)
            target_path = target_info['target']
            library_key = target_info['library_key']
            
            self.logger.info(f"Starting extraction: {first_volume.name}")
            
            # Test archive integrity first
            test_result = self.test_archive_integrity(first_volume)
            
            if test_result == "encrypted":
                # Move to failed directory
                failed_dir = Path(self.config['paths']['failed'])
                failed_dir.mkdir(parents=True, exist_ok=True)
                
                volumes = self.get_archive_volumes(first_volume)
                for vol in volumes:
                    if vol.exists():
                        shutil.move(vol, failed_dir / vol.name)
                
                self.logger.warning(f"Moved encrypted archive to failed directory: {first_volume.name}")
                return
            
            elif test_result != "ok":
                self.logger.error(f"Archive test failed: {first_volume.name}")
                return
            
            # Extract archive
            extract_cmd = [
                "unrar", "x", "-idq", "-y", 
                str(first_volume), 
                str(dest_dir)
            ]
            
            result = subprocess.run(
                extract_cmd,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutes timeout
            )
            
            if result.returncode != 0:
                self.logger.error(f"Extraction failed: {result.stderr}")
                return
            
            # Process extracted files
            media_extensions = {'.mkv', '.mp4', '.avi', '.mov', '.m4v', '.flv', '.wmv'}
            processed_files = []
            
            for file_path in dest_dir.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in media_extensions:
                    # Check for duplicates
                    if self.is_duplicate(file_path):
                        self.logger.info(f"Skipping duplicate file: {file_path.name}")
                        self.stats['duplicates'] += 1
                        continue
                    
                    # Sanitize filename
                    sanitized_name = self.sanitize_filename(file_path.name)
                    
                    # Re-encode if enabled
                    if self.config['options']['enable_reencoding'] and self.config['handbrake']['enabled']:
                        encoded_file = dest_dir / f"encoded_{sanitized_name}"
                        final_file = self.reencode_with_handbrake(file_path, encoded_file)
                        final_path = Path(final_file)
                    else:
                        final_path = file_path
                        if sanitized_name != file_path.name:
                            new_path = file_path.parent / sanitized_name
                            file_path.rename(new_path)
                            final_path = new_path
                    
                    # Move to target directory
                    target_file_path = Path(target_path) / final_path.name
                    
                    if target_file_path.exists():
                        self.logger.warning(f"Target file already exists: {target_file_path}")
                        continue
                    
                    # Ensure target directory exists
                    target_file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Log the move operation with full details
                    self.logger.info(f"Moving file: {final_path} -> {target_file_path}")
                    self.logger.info(f"File size: {final_path.stat().st_size} bytes")
                    
                    shutil.move(str(final_path), str(target_file_path))
                    processed_files.append(target_file_path)
                    
                    # Verify the file was moved successfully
                    if target_file_path.exists():
                        self.logger.info(f"Successfully moved to target: {target_file_path}")
                        self.logger.info(f"Final file size: {target_file_path.stat().st_size} bytes")
                    else:
                        self.logger.error(f"Failed to move file to target: {target_file_path}")
            
            # Cleanup
            shutil.rmtree(dest_dir, ignore_errors=True)
            
            # Handle archive files
            volumes = self.get_archive_volumes(first_volume)
            if self.config['options']['delete_archives']:
                for vol in volumes:
                    if vol.exists():
                        vol.unlink()
                        self.logger.info(f"Deleted archive volume: {vol.name}")
            else:
                # Move to archive directory
                archive_dir = Path(self.config['paths']['archive'])
                archive_dir.mkdir(parents=True, exist_ok=True)
                
                for vol in volumes:
                    if vol.exists():
                        shutil.move(vol, archive_dir / vol.name)
            
            if processed_files:
                self.stats['processed'] += len(processed_files)
                
                # Enhanced Plex integration
                self.logger.info(f"Processed {len(processed_files)} files, notifying Plex...")
                
                # Verify Plex can see the target directory
                if not hasattr(self, '_plex_verified'):
                    self._plex_verified = self.verify_plex_target_directory()
                
                # Trigger Plex refresh for the specific library
                self.plex_refresh(library_key)
                
                # Wait a bit for Plex to process
                time.sleep(3)
                
                self.logger.info(f"Successfully processed {len(processed_files)} files from {first_volume.name}")
                
                # Log final target directory contents for debugging
                target_dir = Path(self.config['paths']['target'])
                if target_dir.exists():
                    recent_files = sorted(target_dir.glob('*'), key=lambda x: x.stat().st_mtime, reverse=True)[:5]
                    self.logger.info(f"Recent files in target directory: {[f.name for f in recent_files]}")
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"Extraction timeout for {first_volume.name}")
            self.stats['errors'] += 1
        except Exception as e:
            self.logger.exception(f"Extraction error for {first_volume.name}: {e}")
            self.stats['errors'] += 1
    
    def _move_archive_to_failed(self, first_volume):
        """Move archive to failed directory"""
        try:
            failed_dir = Path(self.config['paths']['failed'])
            failed_dir.mkdir(parents=True, exist_ok=True)
            
            volumes = self.get_archive_volumes(first_volume)
            for vol in volumes:
                if vol.exists():
                    failed_path = failed_dir / vol.name
                    if not failed_path.exists():
                        shutil.move(vol, failed_path)
                        self.logger.info(f"Moved failed archive to: {failed_path}")
                    else:
                        self.logger.warning(f"Failed archive already exists: {failed_path}")
        except Exception as e:
            self.logger.exception(f"Error moving archive to failed directory: {e}")
    
    def _move_archive_to_archive_dir(self, first_volume):
        """Move archive to archive directory"""
        try:
            archive_dir = Path(self.config['paths']['archive'])
            archive_dir.mkdir(parents=True, exist_ok=True)
            
            volumes = self.get_archive_volumes(first_volume)
            for vol in volumes:
                if vol.exists():
                    archive_path = archive_dir / vol.name
                    if not archive_path.exists():
                        shutil.move(vol, archive_path)
                        self.logger.info(f"Moved archive to: {archive_path}")
                    else:
                        self.logger.warning(f"Archive already exists: {archive_path}")
        except Exception as e:
            self.logger.exception(f"Error moving archive to archive directory: {e}")
    
    def create_tray_icon(self):
        """Create system tray icon"""
        if not GUI_AVAILABLE or not self.config['options']['enable_gui']:
            return
        
        # Create a simple icon
        image = Image.new('RGB', (64, 64), color='blue')
        draw = ImageDraw.Draw(image)
        draw.ellipse((16, 16, 48, 48), fill='white')
        
        menu = pystray.Menu(
            pystray.MenuItem("Status", self.show_status),
            pystray.MenuItem("Statistics", self.show_stats),
            pystray.MenuItem("Open Logs", self.open_logs),
            pystray.MenuItem("Exit", self.stop_application)
        )
        
        self.tray_icon = pystray.Icon("PlexRarBridge", image, menu=menu)
        
        def run_tray():
            self.tray_icon.run()
        
        tray_thread = threading.Thread(target=run_tray, daemon=True)
        tray_thread.start()
    
    def show_status(self, icon=None, item=None):
        """Show current status"""
        uptime = datetime.now() - self.stats['start_time']
        status = f"""Plex RAR Bridge Status
        
Uptime: {uptime}
Processed: {self.stats['processed']} files
Duplicates: {self.stats['duplicates']} skipped
Errors: {self.stats['errors']}
Retries: {self.stats['retries']}
Currently processing: {len(self.processing_files)}
In retry queue: {len(self.retry_queue)}
"""
        print(status)  # Could be replaced with GUI dialog
    
    def show_stats(self, icon=None, item=None):
        """Show detailed statistics"""
        self.show_status()
    
    def open_logs(self, icon=None, item=None):
        """Open log directory"""
        os.startfile('logs')
    
    def stop_application(self, icon=None, item=None):
        """Stop the application"""
        self.stop()
        if self.tray_icon:
            self.tray_icon.stop()

class RarHandler(FileSystemEventHandler):
    def __init__(self, bridge, source_directory):
        self.bridge = bridge
        self.source_directory = source_directory
        
    def on_created(self, event):
        if event.is_directory:
            return
            
        file_path = Path(event.src_path)
        
        # Check if it's a RAR file
        if file_path.suffix.lower() not in self.bridge.config['options']['extensions']:
            return
        
        # Skip if already processing
        if str(file_path) in self.bridge.processing_files:
            return
        
        # Check if file is complete
        if not self.bridge.is_file_complete(file_path):
            # Only add first volumes to retry queue
            if self.is_first_volume(file_path):
                self.bridge.add_to_retry_queue(file_path)
            else:
                self.bridge.logger.debug(f"Non-first volume incomplete, skipping: {file_path.name}")
            return
        
        # Only process first volume of a set
        if not self.is_first_volume(file_path):
            return
        
        self.bridge.processing_files.add(str(file_path))
        self.bridge.logger.info(f"Detected new archive: {file_path.name}")
        
        # Add to processing queue instead of creating thread
        self.bridge.processing_queue.add_archive(file_path, source='new')
    
    def is_first_volume(self, file_path):
        """Check if this is the first volume of a RAR set"""
        name = file_path.name.lower()
        
        # Check for .part1.rar or .part01.rar
        if '.part' in name:
            return '.part1.rar' in name or '.part01.rar' in name
        
        # Check for .rar extension (first volume)
        return name.endswith('.rar')
    


class PlexRarBridgeApp:
    def __init__(self):
        self.bridge = PlexRarBridge()
        
    def start(self):
        """Start the RAR bridge application"""
        self.bridge.logger.info("Starting Plex RAR Bridge")
        
        # Create tray icon if enabled
        self.bridge.create_tray_icon()
        
        # Start the processing queue worker thread
        self.bridge.processing_queue.start()
        
        # Test Plex detection on startup
        self.bridge.logger.info("Testing Plex integration...")
        if self.bridge.verify_plex_target_directory():
            self.bridge.logger.info("Plex target directory verification successful")
        else:
            self.bridge.logger.warning("Plex target directory verification failed - files may not appear in Plex")
        
        # Create a detection test file
        self.bridge.create_plex_detection_test()
        
        # Scan for existing RAR files if enabled
        if self.bridge.config['options'].get('scan_existing_files', True):
            self.scan_existing_files()
        else:
            self.bridge.logger.info("Existing file scan disabled in config")
        
        # Give existing files time to start processing
        if self.bridge.processing_files or self.bridge.retry_queue:
            self.bridge.logger.info("Waiting for existing files to start processing...")
            time.sleep(5)
        
        # Setup file system watchers for each directory pair
        self.bridge.observers = []
        
        # Get recursive setting from setup config or fall back to config
        recursive = True
        if self.bridge.setup_config and self.bridge.setup_config.get('options'):
            recursive = self.bridge.setup_config['options'].get('recursive_monitoring', True)
        elif self.bridge.config.get('monitoring'):
            recursive = self.bridge.config['monitoring'].get('recursive', True)
        
        if self.bridge.directory_pairs:
            # Create observers for each directory pair
            for source_dir, pair_info in self.bridge.directory_pairs.items():
                if pair_info.get('enabled', True):
                    observer = Observer()
                    handler = RarHandler(self.bridge, source_dir)
                    
                    observer.schedule(handler, source_dir, recursive=recursive)
                    observer.start()
                    self.bridge.observers.append(observer)
                    
                    self.bridge.logger.info(f"Started monitoring: {source_dir} -> {pair_info['target']} (Library: {pair_info['library_key']}, Recursive: {recursive})")
        else:
            # Fallback to single directory from main config
            observer = Observer()
            handler = RarHandler(self.bridge, self.bridge.config['paths']['watch'])
            
            watch_path = self.bridge.config['paths']['watch']
            observer.schedule(handler, watch_path, recursive=recursive)
            observer.start()
            self.bridge.observers.append(observer)
            
            self.bridge.logger.info(f"Started monitoring directory: {watch_path} (recursive: {recursive})")
        
        self.bridge.logger.info(f"Total directories being monitored: {len(self.bridge.observers)}")
        self.bridge.logger.info("RAR Bridge is ready for new files!")
        self.bridge.logger.info("=" * 50)
        
        try:
            while True:
                time.sleep(60)
                # Clean up old processing entries
                self.cleanup_old_processing()
                # Process retry queue for incomplete files
                self.bridge.process_retry_queue()
                
                # Log queue status every 10 minutes
                if hasattr(self, '_last_status_log'):
                    if (datetime.now() - self._last_status_log).total_seconds() >= 600:
                        self._log_queue_status()
                        self._last_status_log = datetime.now()
                else:
                    self._last_status_log = datetime.now()
                    
        except KeyboardInterrupt:
            self.bridge.logger.info("Shutting down...")
            self.stop()
    
    def scan_existing_files(self):
        """Scan all watch directories for existing RAR files"""
        self.bridge.logger.info("Scanning for existing RAR files...")
        
        directories_to_scan = []
        
        if self.bridge.directory_pairs:
            # Scan all enabled directory pairs
            for source_dir, pair_info in self.bridge.directory_pairs.items():
                if pair_info.get('enabled', True):
                    directories_to_scan.append(Path(source_dir))
        else:
            # Fallback to main config watch path
            directories_to_scan.append(Path(self.bridge.config['paths']['watch']))
        
        total_found = 0
        for watch_path in directories_to_scan:
            self.bridge.logger.info(f"Scanning directory: {watch_path}")
            
            if not watch_path.exists():
                self.bridge.logger.warning(f"Watch directory does not exist: {watch_path}")
                continue
        
            # Recursive scan for RAR files
            rar_files = []
            for pattern in ['*.rar', '*.part01.rar', '*.part001.rar']:
                rar_files.extend(watch_path.rglob(pattern))
            
            # Process first volumes only
            first_volumes = []
            for rar_file in rar_files:
                if self.is_first_volume_check(rar_file):
                    first_volumes.append(rar_file)
            
            if first_volumes:
                self.bridge.logger.info(f"Found {len(first_volumes)} RAR archive sets in {watch_path}")
                total_found += len(first_volumes)
                
                # Process them with a small delay
                for rar_file in first_volumes:
                    # Check if already being processed
                    if str(rar_file) not in self.bridge.processing_files:
                        self.bridge.logger.info(f"Starting existing file: {rar_file.name}")
                        # Add to processing queue instead of retry queue
                        self.bridge.processing_queue.add_archive(rar_file, source='existing')
                        time.sleep(1)  # Small delay between files
            else:
                self.bridge.logger.info(f"No existing RAR files found in {watch_path}")
        
        if total_found > 0:
            self.bridge.logger.info(f"Total existing archives found across all directories: {total_found}")
        else:
            self.bridge.logger.info("No existing RAR files found in any monitored directory")
    
    def is_first_volume_check(self, file_path):
        """Check if file is a first volume (same logic as RarHandler)"""
        name = file_path.name.lower()
        
        # Check for .part1.rar or .part01.rar
        if '.part' in name:
            return '.part1.rar' in name or '.part01.rar' in name
        
        # Check for .rar extension (first volume)
        return name.endswith('.rar')
    
    def cleanup_old_processing(self):
        """Clean up old processing entries"""
        max_age = self.bridge.config['options']['max_file_age']
        cutoff_time = datetime.now() - timedelta(seconds=max_age)
        
        # This is a simple cleanup - in production, you'd want to track timestamps
        # for each processing file and remove stale entries
    
    def _log_queue_status(self):
        """Log current queue status for monitoring"""
        status = self.bridge.get_processing_status()
        self.bridge.logger.info(f"Queue Status - Queue: {status['queue_size']}, Processing: {status['processing']}, "
                               f"Current: {status['current_item'] or 'None'}, "
                               f"Retry Queue: {status['retry_queue_size']}")
        
        # Log detailed stats if there's activity
        if status['queue_size'] > 0 or status['processing'] or status['retry_queue_size'] > 0:
            queue_stats = status['queue_stats']
            self.bridge.logger.info(f"Queue Stats - Queued: {queue_stats['queued']}, "
                                   f"Processed: {queue_stats['processed']}, "
                                   f"Failed: {queue_stats['failed']}, "
                                   f"Retries: {queue_stats['retries']}")
        
    def stop(self):
        """Stop the application"""
        # Stop the processing queue worker thread
        self.bridge.processing_queue.stop()
        
        # Stop all observers
        for observer in self.bridge.observers:
            if observer and observer.is_alive():
                observer.stop()
                observer.join()
        
        self.bridge.logger.info("Stopped all file system observers")
        
        # Cleanup rar2fs mounts if enabled
        if self.bridge.rar2fs_handler:
            self.bridge.logger.info("Cleaning up rar2fs mounts...")
            self.bridge.rar2fs_handler.cleanup_all_mounts()
        
        # Stop tray icon if it exists
        if hasattr(self.bridge, 'tray_icon') and self.bridge.tray_icon:
            self.bridge.tray_icon.stop()

if __name__ == "__main__":
    app = PlexRarBridgeApp()
    app.start() 