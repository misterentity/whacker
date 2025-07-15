"""
python_rar_vfs.py - Pure Python RAR Virtual File System

This module provides a virtual file system for RAR archives using only Python libraries,
eliminating the need for external dependencies like rar2fs, Cygwin, or WinFSP.

Features:
- Pure Python implementation using rarfile library
- No external dependencies
- FUSE-like interface for seamless integration
- Automatic file serving for Plex
- Cross-platform compatibility
"""

import os
import sys
import threading
import logging
import shutil
import hashlib
import tempfile
import time
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import unquote
import rarfile
import mimetypes
from upnp_port_manager import UPnPIntegratedVFS

class RarVirtualFile:
    """Represents a virtual file inside a RAR archive"""
    
    def __init__(self, rar_path, file_info, vfs_handler):
        self.rar_path = Path(rar_path)
        self.file_info = file_info
        self.vfs_handler = vfs_handler
        self.name = file_info.filename
        self.size = file_info.file_size
        self.modified_time = file_info.date_time
        self.is_dir = file_info.is_dir()
        
        # Generate virtual file path
        self.virtual_path = self._generate_virtual_path()
        
    def _generate_virtual_path(self):
        """Generate a virtual file path for this RAR file"""
        # Create a unique path based on RAR archive and file
        rar_name = self.rar_path.stem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{rar_name}_{timestamp}_{self.name}"
    
    def read(self, start=0, length=None):
        """Read file content from RAR archive"""
        try:
            with rarfile.RarFile(self.rar_path) as rf:
                with rf.open(self.file_info) as f:
                    if start > 0:
                        f.seek(start)
                    
                    if length is not None:
                        return f.read(length)
                    else:
                        return f.read()
        except Exception as e:
            self.vfs_handler.logger.error(f"Error reading from RAR: {e}")
            raise e
    
    def extract_to_temp(self):
        """Extract file to temporary location for direct access"""
        try:
            temp_dir = self.vfs_handler.temp_dir / "extracted"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            temp_file = temp_dir / self.name
            
            # Extract file
            with rarfile.RarFile(self.rar_path) as rf:
                rf.extract(self.file_info, temp_dir)
            
            return temp_file
        except Exception as e:
            self.vfs_handler.logger.error(f"Error extracting to temp: {e}")
            raise e

class RarVirtualFileSystem:
    """Virtual file system for RAR archives using HTTP serving"""
    
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.temp_dir = Path(tempfile.mkdtemp(prefix="rar_vfs_"))
        self.active_archives = {}  # {archive_path: RarArchiveHandler}
        self.http_server = None
        self.http_thread = None
        self.server_port = self._find_available_port()
        self.shutdown_event = threading.Event()
        
        # Initialize UPnP integration
        self.upnp_vfs = UPnPIntegratedVFS(config, logger)
        
        # Create directories
        self.mount_base = Path(config.get('rar2fs', {}).get('mount_base', 'C:/PlexRarBridge/mounts'))
        self.mount_base.mkdir(parents=True, exist_ok=True)
        
        # Start HTTP server for file serving
        self._start_http_server()
        
    def _find_available_port(self, start_port=8765):
        """Find an available port for HTTP server"""
        import socket
        for port in range(start_port, start_port + 100):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('0.0.0.0', port))
                    return port
            except OSError:
                continue
        raise Exception("No available ports found")
    
    def _get_server_ip(self):
        """Get the server IP address for HTTP URLs"""
        import socket
        try:
            # Try to get the actual network IP address
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                # Connect to a remote address (doesn't actually send data)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                return ip
        except Exception:
            # Fallback to localhost if network detection fails
            return "127.0.0.1"
    
    def _start_http_server(self):
        """Start HTTP server for serving virtual files"""
        try:
            handler = self._create_request_handler()
            self.http_server = HTTPServer(('0.0.0.0', self.server_port), handler)
            self.http_thread = threading.Thread(target=self._run_server, daemon=True)
            self.http_thread.start()
            self.logger.info(f"RAR VFS HTTP server started on 0.0.0.0:{self.server_port}")
            
            # Setup UPnP port forwarding
            self.upnp_vfs.setup_port_forwarding(self.server_port)
            
        except Exception as e:
            self.logger.error(f"Failed to start HTTP server: {e}")
            raise e
    
    def _create_request_handler(self):
        """Create HTTP request handler class"""
        vfs = self
        
        class RarFileHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                # Suppress HTTP server logs
                pass
            
            def do_GET(self):
                try:
                    # Parse request path
                    file_path = unquote(self.path.lstrip('/'))
                    
                    # Find virtual file
                    virtual_file = vfs._find_virtual_file(file_path)
                    if not virtual_file:
                        self.send_error(404, "File not found")
                        return
                    
                    # Handle range requests (important for media streaming)
                    range_header = self.headers.get('Range')
                    if range_header:
                        self._handle_range_request(virtual_file, range_header)
                    else:
                        self._handle_full_request(virtual_file)
                        
                except Exception as e:
                    vfs.logger.error(f"HTTP handler error: {e}")
                    self.send_error(500, "Internal server error")
            
            def _handle_range_request(self, virtual_file, range_header):
                """Handle HTTP range requests for media streaming"""
                try:
                    # Parse range header
                    range_match = range_header.replace('bytes=', '').split('-')
                    start = int(range_match[0]) if range_match[0] else 0
                    end = int(range_match[1]) if range_match[1] else virtual_file.size - 1
                    
                    # Validate range
                    if start >= virtual_file.size or end >= virtual_file.size:
                        self.send_error(416, "Range not satisfiable")
                        return
                    
                    content_length = end - start + 1
                    
                    # Send headers
                    self.send_response(206)
                    self.send_header('Content-Type', mimetypes.guess_type(virtual_file.name)[0] or 'application/octet-stream')
                    self.send_header('Content-Length', str(content_length))
                    self.send_header('Content-Range', f'bytes {start}-{end}/{virtual_file.size}')
                    self.send_header('Accept-Ranges', 'bytes')
                    self.end_headers()
                    
                    # Send file content
                    data = virtual_file.read(start, content_length)
                    self.wfile.write(data)
                    
                except Exception as e:
                    vfs.logger.error(f"Range request error: {e}")
                    self.send_error(500, "Internal server error")
            
            def _handle_full_request(self, virtual_file):
                """Handle full file requests"""
                try:
                    # Send headers
                    self.send_response(200)
                    self.send_header('Content-Type', mimetypes.guess_type(virtual_file.name)[0] or 'application/octet-stream')
                    self.send_header('Content-Length', str(virtual_file.size))
                    self.send_header('Accept-Ranges', 'bytes')
                    self.end_headers()
                    
                    # Send file content
                    data = virtual_file.read()
                    self.wfile.write(data)
                    
                except Exception as e:
                    vfs.logger.error(f"Full request error: {e}")
                    self.send_error(500, "Internal server error")
        
        return RarFileHandler
    
    def _run_server(self):
        """Run HTTP server"""
        try:
            self.http_server.serve_forever()
        except Exception as e:
            self.logger.error(f"HTTP server error: {e}")
    
    def _find_virtual_file(self, file_path):
        """Find virtual file by path"""
        for archive_handler in self.active_archives.values():
            for virtual_file in archive_handler.virtual_files:
                if virtual_file.virtual_path == file_path:
                    return virtual_file
        return None
    
    def mount_archive(self, archive_path, target_info):
        """Mount a RAR archive as virtual file system"""
        archive_path = Path(archive_path)
        
        if not archive_path.exists():
            raise Exception(f"Archive not found: {archive_path}")
        
        try:
            # Create archive handler
            archive_handler = RarArchiveHandler(archive_path, target_info, self)
            
            # Mount the archive
            mount_info = archive_handler.mount()
            
            # Store handler
            self.active_archives[str(archive_path)] = archive_handler
            
            self.logger.info(f"Successfully mounted RAR archive: {archive_path.name}")
            return mount_info
            
        except Exception as e:
            self.logger.error(f"Failed to mount archive {archive_path}: {e}")
            raise e
    
    def unmount_archive(self, archive_path):
        """Unmount a RAR archive"""
        archive_path = str(archive_path)
        
        if archive_path not in self.active_archives:
            self.logger.warning(f"Archive not mounted: {archive_path}")
            return False
        
        try:
            archive_handler = self.active_archives[archive_path]
            archive_handler.unmount()
            del self.active_archives[archive_path]
            
            self.logger.info(f"Successfully unmounted archive: {archive_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to unmount archive {archive_path}: {e}")
            return False
    
    def cleanup_all_mounts(self):
        """Clean up all mounted archives"""
        self.logger.info("Cleaning up all RAR VFS mounts...")
        
        archives_to_cleanup = list(self.active_archives.keys())
        for archive_path in archives_to_cleanup:
            self.unmount_archive(archive_path)
        
        # Clean up UPnP port forwarding
        self.upnp_vfs.cleanup_port_forwarding()
        
        # Stop HTTP server
        if self.http_server:
            self.http_server.shutdown()
            self.http_server.server_close()
        
        if self.http_thread and self.http_thread.is_alive():
            self.http_thread.join(timeout=5)
        
        # Clean up temp directory
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        self.logger.info("RAR VFS cleanup completed")
    
    def get_upnp_status(self):
        """Get UPnP status information"""
        return self.upnp_vfs.get_upnp_status()
    
    def get_mount_status(self):
        """Get status of all mounts"""
        status = {
            'active_mounts': len(self.active_archives),
            'server_port': self.server_port,
            'mounts': []
        }
        
        for archive_path, handler in self.active_archives.items():
            mount_status = {
                'archive': archive_path,
                'mount_point': str(handler.mount_point),
                'mounted_at': handler.mounted_at.isoformat(),
                'virtual_files': len(handler.virtual_files),
                'target_links': len(handler.target_links)
            }
            status['mounts'].append(mount_status)
        
        return status

class RarArchiveHandler:
    """Handler for a single RAR archive"""
    
    def __init__(self, archive_path, target_info, vfs):
        self.archive_path = Path(archive_path)
        self.target_info = target_info
        self.vfs = vfs
        self.virtual_files = []
        self.target_links = []
        self.mounted_at = datetime.now()
        
        # Create mount point
        self.mount_point = self._create_mount_point()
        
    def _create_mount_point(self):
        """Create mount point directory"""
        archive_name = self.archive_path.stem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        mount_dir = f"{archive_name}_{timestamp}"
        
        mount_point = self.vfs.mount_base / mount_dir
        mount_point.mkdir(parents=True, exist_ok=True)
        
        return mount_point
    
    def mount(self):
        """Mount the RAR archive"""
        try:
            # Open RAR file and get file list
            with rarfile.RarFile(self.archive_path) as rf:
                file_list = rf.infolist()
                
                # Filter for media files
                media_extensions = {'.mkv', '.mp4', '.avi', '.mov', '.m4v', '.flv', '.wmv', '.m2ts', '.ts'}
                
                for file_info in file_list:
                    if not file_info.is_dir():
                        file_ext = Path(file_info.filename).suffix.lower()
                        if file_ext in media_extensions:
                            # Create virtual file
                            virtual_file = RarVirtualFile(self.archive_path, file_info, self.vfs)
                            self.virtual_files.append(virtual_file)
                            
                            # Create HTTP URL for the file using actual network IP
                            server_ip = self.vfs._get_server_ip()
                            http_url = f"http://{server_ip}:{self.vfs.server_port}/{virtual_file.virtual_path}"
                            
                            # Create link file that points to HTTP URL
                            self._create_link_file(virtual_file, http_url)
            
            # Create mount info
            mount_info = {
                'archive_path': str(self.archive_path),
                'mount_point': str(self.mount_point),
                'mounted_at': self.mounted_at,
                'target_links': self.target_links,
                'virtual_files': len(self.virtual_files),
                'server_port': self.vfs.server_port
            }
            
            return mount_info
            
        except Exception as e:
            self.vfs.logger.error(f"Failed to mount {self.archive_path}: {e}")
            raise e
    
    def _create_link_file(self, virtual_file, http_url):
        """Create a link file that Plex can access"""
        target_dir = Path(self.target_info['target'])
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a .strm file that points to the HTTP URL
        # .strm files are supported by Plex and other media servers
        strm_file = target_dir / f"{Path(virtual_file.name).stem}.strm"
        
        try:
            # Write HTTP URL to .strm file
            with open(strm_file, 'w') as f:
                f.write(http_url)
            
            self.target_links.append(str(strm_file))
            self.vfs.logger.info(f"Created STRM file: {strm_file}")
            
        except Exception as e:
            self.vfs.logger.error(f"Failed to create STRM file: {e}")
            raise e
    
    def unmount(self):
        """Unmount the archive"""
        try:
            # Remove target links
            for link_path in self.target_links:
                try:
                    link_file = Path(link_path)
                    if link_file.exists():
                        link_file.unlink()
                        self.vfs.logger.info(f"Removed link file: {link_file}")
                except Exception as e:
                    self.vfs.logger.warning(f"Failed to remove link {link_path}: {e}")
            
            # Remove mount point
            if self.mount_point.exists():
                shutil.rmtree(self.mount_point, ignore_errors=True)
            
            self.vfs.logger.info(f"Unmounted archive: {self.archive_path}")
            
        except Exception as e:
            self.vfs.logger.error(f"Failed to unmount {self.archive_path}: {e}")
            raise e

# Integration with main bridge
class PythonRarVfsHandler:
    """Handler that integrates Python RAR VFS with Plex RAR Bridge"""
    
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.vfs = RarVirtualFileSystem(config, logger)
        
        # Set up signal handlers for cleanup
        import signal
        signal.signal(signal.SIGINT, self._cleanup_on_exit)
        signal.signal(signal.SIGTERM, self._cleanup_on_exit)
    
    def mount_archive(self, archive_path, target_info):
        """Mount archive using Python VFS"""
        return self.vfs.mount_archive(archive_path, target_info)
    
    def unmount_archive(self, archive_path):
        """Unmount archive"""
        return self.vfs.unmount_archive(archive_path)
    
    def cleanup_all_mounts(self):
        """Clean up all mounts"""
        self.vfs.cleanup_all_mounts()
    
    def get_mount_status(self):
        """Get mount status"""
        return self.vfs.get_mount_status()
    
    def _cleanup_on_exit(self, signum, frame):
        """Signal handler for cleanup on exit"""
        self.logger.info(f"Received signal {signum}, cleaning up Python RAR VFS...")
        self.cleanup_all_mounts()
        sys.exit(0) 