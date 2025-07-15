"""
rar2fs_installer.py - Automated rar2fs installation for Plex RAR Bridge

This module automatically downloads, installs, and configures rar2fs and its dependencies
so users don't need to manually install Cygwin, WinFSP, or compile from source.
"""

import os
import sys
import subprocess
import urllib.request
import zipfile
import tempfile
import shutil
import winreg
import logging
from pathlib import Path
import json

class Rar2fsInstaller:
    """Automated installer for rar2fs and dependencies"""
    
    def __init__(self, install_dir="C:/PlexRarBridge/rar2fs", logger=None):
        self.install_dir = Path(install_dir)
        self.logger = logger or self._setup_logger()
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Verified download URLs 
        self.downloads = {
            # Use WinFSP official website download (always current)
            'winfsp': 'https://github.com/winfsp/winfsp/releases/latest/download/winfsp.msi',
            # Try multiple rar2fs sources
            'rar2fs_binary_primary': 'https://github.com/hasse69/rar2fs/releases/latest/download/rar2fs-win64.zip',
            'rar2fs_binary_fallback': 'https://github.com/hasse69/rar2fs/releases/download/v1.29.6/rar2fs-win64.zip',
            # Cygwin setup (official)
            'cygwin_setup': 'https://cygwin.com/setup-x86_64.exe'
        }
        
        # Installation status
        self.status = {
            'winfsp_installed': False,
            'rar2fs_installed': False,
            'dependencies_installed': False,
            'configuration_complete': False
        }
    
    def _setup_logger(self):
        """Setup a basic logger if none provided"""
        logger = logging.getLogger('rar2fs_installer')
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def check_existing_installation(self):
        """Check if rar2fs components are already installed"""
        self.logger.info("Checking for existing rar2fs installation...")
        
        # Check WinFSP
        try:
            # Check Windows services for WinFSP
            result = subprocess.run(['sc', 'query', 'WinFsp'], 
                                 capture_output=True, text=True)
            self.status['winfsp_installed'] = result.returncode == 0
            if self.status['winfsp_installed']:
                self.logger.info("✅ WinFSP service found")
            else:
                self.logger.info("❌ WinFSP service not found")
        except:
            self.status['winfsp_installed'] = False
            self.logger.info("❌ Error checking WinFSP service")
        
        # Check rar2fs executable
        potential_paths = [
            self.install_dir / "bin" / "rar2fs.exe",
            Path("C:/Program Files/rar2fs/rar2fs.exe"),
            Path("C:/rar2fs/rar2fs.exe")
        ]
        
        for path in potential_paths:
            if path.exists():
                self.status['rar2fs_installed'] = True
                self.logger.info(f"✅ rar2fs found at {path}")
                break
        else:
            self.status['rar2fs_installed'] = False
            self.logger.info("❌ rar2fs executable not found")
        
        # Mark dependencies as installed if rar2fs works
        if self.status['rar2fs_installed']:
            try:
                # Test if rar2fs can run (basic dependency check)
                result = subprocess.run([str(potential_paths[0]), '--help'], 
                                     capture_output=True, text=True, timeout=10)
                self.status['dependencies_installed'] = result.returncode == 0
            except:
                self.status['dependencies_installed'] = False
        
        # Check basic configuration
        self.status['configuration_complete'] = (
            self.status['winfsp_installed'] and 
            self.status['rar2fs_installed'] and 
            self.status['dependencies_installed']
        )
        
        return self.status
    
    def download_file(self, url, dest_path, description="file"):
        """Download a file with progress feedback"""
        try:
            self.logger.info(f"Downloading {description} from {url}")
            
            def progress_hook(block_num, block_size, total_size):
                if total_size > 0:
                    percent = min(100, (block_num * block_size * 100) // total_size)
                    if percent % 10 == 0:  # Log every 10%
                        self.logger.info(f"Download progress: {percent}%")
            
            urllib.request.urlretrieve(url, dest_path, progress_hook)
            self.logger.info(f"✅ Downloaded {description} successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to download {description}: {e}")
            return False
    
    def install_winfsp(self):
        """Install WinFSP"""
        if self.status['winfsp_installed']:
            self.logger.info("WinFSP already installed, skipping")
            return True
            
        self.logger.info("Installing WinFSP...")
        
        try:
            # Download WinFSP installer
            msi_path = self.temp_dir / "winfsp.msi"
            
            if not self.download_file(self.downloads['winfsp'], msi_path, "WinFSP installer"):
                return False
            
            # Install WinFSP silently
            self.logger.info("Installing WinFSP (this may take a few minutes)...")
            result = subprocess.run([
                'msiexec', '/i', str(msi_path), '/quiet', '/norestart'
            ], timeout=300)  # 5 minute timeout
            
            if result.returncode == 0:
                self.logger.info("✅ WinFSP installed successfully")
                self.status['winfsp_installed'] = True
                return True
            else:
                self.logger.error(f"❌ WinFSP installation failed with code {result.returncode}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("❌ WinFSP installation timed out")
            return False
        except Exception as e:
            self.logger.error(f"❌ Error installing WinFSP: {e}")
            return False
    
    def install_rar2fs(self):
        """Install rar2fs binary"""
        if self.status['rar2fs_installed']:
            self.logger.info("rar2fs already installed, skipping")
            return True
            
        self.logger.info("Installing rar2fs...")
        
        try:
            # Create installation directory
            self.install_dir.mkdir(parents=True, exist_ok=True)
            bin_dir = self.install_dir / "bin"
            bin_dir.mkdir(exist_ok=True)
            
            # Try primary download URL first, then fallback
            zip_path = self.temp_dir / "rar2fs.zip"
            downloaded = False
            
            for url_key in ['rar2fs_binary_primary', 'rar2fs_binary_fallback']:
                if url_key in self.downloads:
                    if self.download_file(self.downloads[url_key], zip_path, f"rar2fs binary ({url_key})"):
                        downloaded = True
                        break
            
            if not downloaded:
                self.logger.error("❌ Failed to download rar2fs from any source")
                return False
            
            # Extract rar2fs
            self.logger.info("Extracting rar2fs...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.temp_dir / "rar2fs_extract")
            
            # Find and copy rar2fs.exe
            extracted_dir = self.temp_dir / "rar2fs_extract"
            rar2fs_exe = None
            
            # Look for rar2fs.exe in extracted files
            for root, dirs, files in os.walk(extracted_dir):
                for file in files:
                    if file.lower() == 'rar2fs.exe':
                        rar2fs_exe = Path(root) / file
                        break
                if rar2fs_exe:
                    break
            
            if not rar2fs_exe or not rar2fs_exe.exists():
                self.logger.error("❌ rar2fs.exe not found in downloaded archive")
                return False
            
            # Copy to installation directory
            dest_exe = bin_dir / "rar2fs.exe"
            shutil.copy2(rar2fs_exe, dest_exe)
            
            # Verify installation
            if dest_exe.exists():
                self.logger.info(f"✅ rar2fs installed to {dest_exe}")
                self.status['rar2fs_installed'] = True
                self.status['dependencies_installed'] = True  # Assume deps are included
                return True
            else:
                self.logger.error("❌ Failed to copy rar2fs.exe")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error installing rar2fs: {e}")
            return False
    
    def install(self):
        """Main installation method"""
        try:
            self.logger.info("=== Starting rar2fs Installation ===")
            
            # Check existing installation first
            self.check_existing_installation()
            
            if all(self.status.values()):
                self.logger.info("✅ rar2fs is already fully installed and configured!")
                return True
            
            # Install WinFSP
            if not self.install_winfsp():
                self.logger.error("❌ WinFSP installation failed")
                return False
            
            # Install rar2fs
            if not self.install_rar2fs():
                self.logger.error("❌ rar2fs installation failed")
                return False
            
            # Final verification
            self.check_existing_installation()
            
            if all(self.status.values()):
                self.logger.info("🎉 rar2fs installation completed successfully!")
                self.logger.info(f"rar2fs installed to: {self.install_dir / 'bin' / 'rar2fs.exe'}")
                return True
            else:
                self.logger.error("❌ Installation verification failed")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Installation failed: {e}")
            return False
        finally:
            # Cleanup temp directory
            try:
                shutil.rmtree(self.temp_dir)
            except:
                pass

if __name__ == "__main__":
    # Test the installer
    installer = Rar2fsInstaller()
    success = installer.install()
    sys.exit(0 if success else 1) 