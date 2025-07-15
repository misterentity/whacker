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
        self.logger = logger or logging.getLogger(__name__)
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Download URLs (these would need to be updated with actual URLs)
        self.downloads = {
            'winfsp': 'https://github.com/winfsp/winfsp/releases/download/v2.0/winfsp-2.0.msi',
            'rar2fs_binary': 'https://github.com/hasse69/rar2fs/releases/download/v1.29.7/rar2fs-windows.zip',
            'cygwin_minimal': 'https://cygwin.com/setup-x86_64.exe',
            'required_dlls': 'https://github.com/hasse69/rar2fs/releases/download/v1.29.7/rar2fs-deps.zip'
        }
        
        # Installation status
        self.status = {
            'winfsp_installed': False,
            'rar2fs_installed': False,
            'dependencies_installed': False,
            'configuration_complete': False
        }
    
    def check_existing_installation(self):
        """Check if rar2fs components are already installed"""
        self.logger.info("Checking for existing rar2fs installation...")
        
        # Check WinFSP
        try:
            # Check Windows services for WinFSP
            result = subprocess.run(['sc', 'query', 'WinFsp.Launcher'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                self.status['winfsp_installed'] = True
                self.logger.info("WinFSP service found")
        except Exception as e:
            self.logger.debug(f"WinFSP check failed: {e}")
        
        # Check for rar2fs executable
        rar2fs_exe = self.install_dir / 'bin' / 'rar2fs.exe'
        if rar2fs_exe.exists():
            self.status['rar2fs_installed'] = True
            self.logger.info("rar2fs executable found")
        
        return self.status
    
    def install_winfsp(self):
        """Install WinFSP if not already installed"""
        if self.status['winfsp_installed']:
            self.logger.info("WinFSP already installed, skipping...")
            return True
        
        self.logger.info("Installing WinFSP...")
        
        try:
            # Download WinFSP installer
            winfsp_installer = self.temp_dir / 'winfsp-installer.msi'
            self.logger.info("Downloading WinFSP installer...")
            urllib.request.urlretrieve(self.downloads['winfsp'], winfsp_installer)
            
            # Install WinFSP silently
            self.logger.info("Installing WinFSP (this may take a few minutes)...")
            result = subprocess.run([
                'msiexec', '/i', str(winfsp_installer), 
                '/quiet', '/norestart',
                'ADDLOCAL=ALL'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                self.status['winfsp_installed'] = True
                self.logger.info("WinFSP installed successfully")
                return True
            else:
                self.logger.error(f"WinFSP installation failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error installing WinFSP: {e}")
            return False
    
    def install_rar2fs_binary(self):
        """Install pre-compiled rar2fs binary"""
        if self.status['rar2fs_installed']:
            self.logger.info("rar2fs already installed, skipping...")
            return True
        
        self.logger.info("Installing rar2fs binary...")
        
        try:
            # Create installation directory
            self.install_dir.mkdir(parents=True, exist_ok=True)
            
            # Download rar2fs binary package
            rar2fs_zip = self.temp_dir / 'rar2fs.zip'
            self.logger.info("Downloading rar2fs binary...")
            urllib.request.urlretrieve(self.downloads['rar2fs_binary'], rar2fs_zip)
            
            # Extract rar2fs
            self.logger.info("Extracting rar2fs...")
            with zipfile.ZipFile(rar2fs_zip, 'r') as zip_ref:
                zip_ref.extractall(self.install_dir)
            
            # Download required DLLs
            deps_zip = self.temp_dir / 'deps.zip'
            self.logger.info("Downloading rar2fs dependencies...")
            urllib.request.urlretrieve(self.downloads['required_dlls'], deps_zip)
            
            # Extract dependencies
            with zipfile.ZipFile(deps_zip, 'r') as zip_ref:
                zip_ref.extractall(self.install_dir)
            
            # Verify installation
            rar2fs_exe = self.install_dir / 'bin' / 'rar2fs.exe'
            if rar2fs_exe.exists():
                self.status['rar2fs_installed'] = True
                self.logger.info("rar2fs binary installed successfully")
                return True
            else:
                self.logger.error("rar2fs binary not found after installation")
                return False
                
        except Exception as e:
            self.logger.error(f"Error installing rar2fs binary: {e}")
            return False
    
    def install_minimal_cygwin(self):
        """Install minimal Cygwin dependencies for rar2fs"""
        self.logger.info("Installing minimal Cygwin dependencies...")
        
        try:
            # Download Cygwin setup
            cygwin_setup = self.temp_dir / 'cygwin-setup.exe'
            self.logger.info("Downloading Cygwin setup...")
            urllib.request.urlretrieve(self.downloads['cygwin_minimal'], cygwin_setup)
            
            # Install only required packages
            cygwin_dir = self.install_dir / 'cygwin'
            cygwin_dir.mkdir(parents=True, exist_ok=True)
            
            # Silent installation with minimal packages
            result = subprocess.run([
                str(cygwin_setup),
                '--quiet-mode',
                '--no-shortcuts',
                '--no-startmenu',
                '--no-desktop',
                '--root', str(cygwin_dir),
                '--packages', 'cygwin,libfuse2,libgcc1,libstdc++6'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                self.status['dependencies_installed'] = True
                self.logger.info("Minimal Cygwin dependencies installed")
                return True
            else:
                self.logger.error(f"Cygwin installation failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error installing Cygwin dependencies: {e}")
            return False
    
    def configure_rar2fs(self):
        """Configure rar2fs for use with Plex RAR Bridge"""
        self.logger.info("Configuring rar2fs...")
        
        try:
            # Create configuration file
            config = {
                'rar2fs': {
                    'enabled': True,
                    'executable': str(self.install_dir / 'bin' / 'rar2fs.exe'),
                    'mount_base': str(self.install_dir / 'mounts'),
                    'mount_options': [
                        'uid=-1',
                        'gid=-1',
                        'allow_other'
                    ],
                    'cleanup_on_exit': True,
                    'winfsp_required': True
                }
            }
            
            # Save configuration
            config_file = self.install_dir / 'rar2fs_config.json'
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Create mount directories
            (self.install_dir / 'mounts').mkdir(parents=True, exist_ok=True)
            
            # Test rar2fs installation
            if self.test_rar2fs():
                self.status['configuration_complete'] = True
                self.logger.info("rar2fs configuration complete")
                return True
            else:
                self.logger.error("rar2fs configuration test failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Error configuring rar2fs: {e}")
            return False
    
    def test_rar2fs(self):
        """Test rar2fs installation"""
        self.logger.info("Testing rar2fs installation...")
        
        try:
            rar2fs_exe = self.install_dir / 'bin' / 'rar2fs.exe'
            
            # Test help command
            result = subprocess.run([str(rar2fs_exe), '--help'], 
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                self.logger.info("rar2fs test passed")
                return True
            else:
                self.logger.error(f"rar2fs test failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("rar2fs test timed out")
            return False
        except Exception as e:
            self.logger.error(f"Error testing rar2fs: {e}")
            return False
    
    def install(self):
        """Complete installation process"""
        self.logger.info("Starting rar2fs installation...")
        
        try:
            # Check existing installation
            self.check_existing_installation()
            
            # Install components
            if not self.install_winfsp():
                return False
            
            if not self.install_rar2fs_binary():
                return False
            
            if not self.install_minimal_cygwin():
                return False
            
            if not self.configure_rar2fs():
                return False
            
            self.logger.info("rar2fs installation completed successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"Installation failed: {e}")
            return False
        finally:
            # Cleanup temp directory
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def uninstall(self):
        """Uninstall rar2fs and dependencies"""
        self.logger.info("Uninstalling rar2fs...")
        
        try:
            # Remove installation directory
            if self.install_dir.exists():
                shutil.rmtree(self.install_dir)
                self.logger.info("rar2fs installation directory removed")
            
            # Note: We don't uninstall WinFSP as it might be used by other applications
            self.logger.info("rar2fs uninstalled successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error uninstalling rar2fs: {e}")
            return False
    
    def get_config_for_bridge(self):
        """Get configuration settings for Plex RAR Bridge"""
        config_file = self.install_dir / 'rar2fs_config.json'
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                return json.load(f)
        else:
            return None

def install_rar2fs_interactive():
    """Interactive installation function"""
    import logging
    
    # Setup logging
    logging.basicConfig(level=logging.INFO,
                       format='%(asctime)s %(levelname)s: %(message)s')
    logger = logging.getLogger(__name__)
    
    logger.info("Starting rar2fs installation for Plex RAR Bridge")
    
    # Create installer
    installer = Rar2fsInstaller(logger=logger)
    
    # Check if already installed
    status = installer.check_existing_installation()
    
    if all(status.values()):
        logger.info("rar2fs appears to be already installed")
        choice = input("Reinstall? (y/n): ").lower()
        if choice != 'y':
            return True
    
    # Install
    if installer.install():
        logger.info("Installation successful!")
        
        # Show configuration
        config = installer.get_config_for_bridge()
        if config:
            logger.info("Add this to your config.yaml:")
            logger.info(f"processing_mode: rar2fs")
            logger.info(f"rar2fs:")
            for key, value in config['rar2fs'].items():
                logger.info(f"  {key}: {value}")
        
        return True
    else:
        logger.error("Installation failed")
        return False

if __name__ == "__main__":
    install_rar2fs_interactive() 