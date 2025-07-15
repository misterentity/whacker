"""
rar2fs_handler.py - Handler for rar2fs virtual file system operations

This module provides functionality to:
- Mount RAR archives as virtual file systems using rar2fs
- Manage mount points and cleanup
- Create symbolic links for Plex library integration
- Handle Windows-specific WinFSP requirements
"""

import os
import sys
import subprocess
import time
import shutil
import logging
from pathlib import Path
from datetime import datetime
import threading
import signal
import psutil

class Rar2fsHandler:
    """Handler for rar2fs virtual file system operations"""
    
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.rar2fs_config = config.get('rar2fs', {})
        self.active_mounts = {}  # {archive_path: mount_info}
        self.mount_lock = threading.Lock()
        
        # Validate rar2fs availability
        self._validate_rar2fs()
        
        # Setup mount base directory
        self.mount_base = Path(self.rar2fs_config.get('mount_base', 'C:/PlexRarBridge/mounts'))
        self.mount_base.mkdir(parents=True, exist_ok=True)
        
        # Setup cleanup on exit
        if self.rar2fs_config.get('cleanup_on_exit', True):
            signal.signal(signal.SIGINT, self._cleanup_on_exit)
            signal.signal(signal.SIGTERM, self._cleanup_on_exit)
    
    def _validate_rar2fs(self):
        """Validate that rar2fs is available and working"""
        executable = self.rar2fs_config.get('executable', 'rar2fs.exe')
        
        try:
            result = subprocess.run([executable, '--help'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                raise Exception(f"rar2fs returned non-zero exit code: {result.returncode}")
            self.logger.info(f"rar2fs validated successfully: {executable}")
        except FileNotFoundError:
            raise Exception(f"rar2fs executable not found: {executable}")
        except subprocess.TimeoutExpired:
            raise Exception("rar2fs validation timed out")
        except Exception as e:
            raise Exception(f"rar2fs validation failed: {e}")
    
    def _check_winfsp_requirements(self):
        """Check if WinFSP is properly installed (Windows only)"""
        if not self.rar2fs_config.get('winfsp_required', True):
            return True
            
        try:
            # Check if WinFSP service is running
            for service in psutil.win_service_iter():
                if service.name().lower() == 'winfsp.launcher':
                    if service.status() == 'running':
                        self.logger.info("WinFSP service is running")
                        return True
                    else:
                        self.logger.warning(f"WinFSP service status: {service.status()}")
            
            self.logger.warning("WinFSP service not found or not running")
            return False
        except Exception as e:
            self.logger.warning(f"Could not check WinFSP status: {e}")
            return False
    
    def mount_archive(self, archive_path, target_info):
        """Mount a RAR archive using rar2fs"""
        archive_path = Path(archive_path)
        
        if not archive_path.exists():
            raise Exception(f"Archive not found: {archive_path}")
        
        # Check WinFSP requirements
        if not self._check_winfsp_requirements():
            raise Exception("WinFSP is required but not available")
        
        with self.mount_lock:
            # Check if already mounted
            if str(archive_path) in self.active_mounts:
                mount_info = self.active_mounts[str(archive_path)]
                if self._is_mount_active(mount_info):
                    self.logger.info(f"Archive already mounted: {archive_path.name}")
                    return mount_info
                else:
                    # Clean up stale mount
                    self._cleanup_mount(str(archive_path))
            
            # Create unique mount point
            mount_point = self._create_mount_point(archive_path)
            
            try:
                # Mount the archive
                mount_info = self._execute_mount(archive_path, mount_point)
                
                # Create symbolic links in target directory
                self._create_target_links(mount_info, target_info)
                
                # Store mount info
                self.active_mounts[str(archive_path)] = mount_info
                
                self.logger.info(f"Successfully mounted: {archive_path.name} -> {mount_point}")
                return mount_info
                
            except Exception as e:
                # Cleanup on failure
                self._cleanup_mount_point(mount_point)
                raise e
    
    def _create_mount_point(self, archive_path):
        """Create a unique mount point for the archive"""
        archive_name = archive_path.stem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        mount_dir = f"{archive_name}_{timestamp}"
        
        mount_point = self.mount_base / mount_dir
        mount_point.mkdir(parents=True, exist_ok=True)
        
        return mount_point
    
    def _execute_mount(self, archive_path, mount_point):
        """Execute the rar2fs mount command"""
        executable = self.rar2fs_config.get('executable', 'rar2fs.exe')
        mount_options = self.rar2fs_config.get('mount_options', [])
        
        # Build command
        cmd = [executable, str(archive_path), str(mount_point)]
        
        # Add mount options
        for option in mount_options:
            cmd.extend(['-o', option])
        
        # Add foreground option for better control
        cmd.append('-f')
        
        self.logger.info(f"Executing mount command: {' '.join(cmd)}")
        
        try:
            # Start the mount process
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE, text=True)
            
            # Wait a moment for mount to establish
            time.sleep(2)
            
            # Check if mount is successful
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                raise Exception(f"Mount failed: {stderr}")
            
            # Verify mount by checking if directory is accessible
            if not self._verify_mount(mount_point):
                process.terminate()
                raise Exception("Mount verification failed")
            
            mount_info = {
                'archive_path': str(archive_path),
                'mount_point': str(mount_point),
                'process': process,
                'mounted_at': datetime.now(),
                'target_links': []
            }
            
            return mount_info
            
        except Exception as e:
            self.logger.error(f"Failed to mount {archive_path}: {e}")
            raise e
    
    def _verify_mount(self, mount_point):
        """Verify that the mount is working"""
        try:
            # Try to list directory contents
            contents = list(mount_point.iterdir())
            self.logger.info(f"Mount verified, found {len(contents)} items")
            return True
        except Exception as e:
            self.logger.error(f"Mount verification failed: {e}")
            return False
    
    def _create_target_links(self, mount_info, target_info):
        """Create symbolic links in the target directory"""
        mount_point = Path(mount_info['mount_point'])
        target_dir = Path(target_info['target'])
        
        try:
            # Create target directory if it doesn't exist
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Create links for each file in the mounted archive
            for item in mount_point.iterdir():
                if item.is_file():
                    # Create link in target directory
                    link_path = target_dir / item.name
                    
                    # Remove existing link if it exists
                    if link_path.exists() or link_path.is_symlink():
                        link_path.unlink()
                    
                    # Create symbolic link
                    link_path.symlink_to(item)
                    mount_info['target_links'].append(str(link_path))
                    
                    self.logger.info(f"Created link: {link_path} -> {item}")
                    
        except Exception as e:
            self.logger.error(f"Failed to create target links: {e}")
            raise e
    
    def _is_mount_active(self, mount_info):
        """Check if a mount is still active"""
        try:
            process = mount_info.get('process')
            if process and process.poll() is None:
                return True
            return False
        except Exception:
            return False
    
    def unmount_archive(self, archive_path):
        """Unmount a RAR archive"""
        archive_path = str(archive_path)
        
        with self.mount_lock:
            if archive_path not in self.active_mounts:
                self.logger.warning(f"Archive not mounted: {archive_path}")
                return False
            
            mount_info = self.active_mounts[archive_path]
            return self._cleanup_mount(archive_path)
    
    def _cleanup_mount(self, archive_path):
        """Clean up a specific mount"""
        if archive_path not in self.active_mounts:
            return False
        
        mount_info = self.active_mounts[archive_path]
        
        try:
            # Remove target links
            for link_path in mount_info.get('target_links', []):
                try:
                    link_path = Path(link_path)
                    if link_path.exists() or link_path.is_symlink():
                        link_path.unlink()
                        self.logger.info(f"Removed link: {link_path}")
                except Exception as e:
                    self.logger.warning(f"Failed to remove link {link_path}: {e}")
            
            # Terminate the rar2fs process
            process = mount_info.get('process')
            if process and process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
                self.logger.info(f"Terminated rar2fs process for {archive_path}")
            
            # Clean up mount point
            mount_point = Path(mount_info['mount_point'])
            self._cleanup_mount_point(mount_point)
            
            # Remove from active mounts
            del self.active_mounts[archive_path]
            
            self.logger.info(f"Successfully cleaned up mount: {archive_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup mount {archive_path}: {e}")
            return False
    
    def _cleanup_mount_point(self, mount_point):
        """Clean up a mount point directory"""
        try:
            mount_point = Path(mount_point)
            if mount_point.exists():
                # Try to remove the directory
                shutil.rmtree(mount_point, ignore_errors=True)
                self.logger.info(f"Removed mount point: {mount_point}")
        except Exception as e:
            self.logger.warning(f"Failed to remove mount point {mount_point}: {e}")
    
    def cleanup_all_mounts(self):
        """Clean up all active mounts"""
        self.logger.info("Cleaning up all rar2fs mounts...")
        
        with self.mount_lock:
            archives_to_cleanup = list(self.active_mounts.keys())
            
            for archive_path in archives_to_cleanup:
                self._cleanup_mount(archive_path)
        
        self.logger.info("All rar2fs mounts cleaned up")
    
    def _cleanup_on_exit(self, signum, frame):
        """Signal handler for cleanup on exit"""
        self.logger.info(f"Received signal {signum}, cleaning up rar2fs mounts...")
        self.cleanup_all_mounts()
        sys.exit(0)
    
    def get_mount_status(self):
        """Get status of all mounts"""
        status = {
            'active_mounts': len(self.active_mounts),
            'mounts': []
        }
        
        for archive_path, mount_info in self.active_mounts.items():
            mount_status = {
                'archive': archive_path,
                'mount_point': mount_info['mount_point'],
                'mounted_at': mount_info['mounted_at'].isoformat(),
                'active': self._is_mount_active(mount_info),
                'target_links': len(mount_info.get('target_links', []))
            }
            status['mounts'].append(mount_status)
        
        return status 