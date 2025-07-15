#!/usr/bin/env python3
"""
rar2fs Installer for Windows
===========================

This installer sets up the WinFSP filesystem driver required for rar2fs
and provides instructions for manually compiling rar2fs from source.

NOTE: rar2fs does not provide pre-compiled Windows binaries and must
be compiled from source using Cygwin.
"""

import os
import sys
import subprocess
import tempfile
import logging
import requests
from pathlib import Path

class RarFSInstaller:
    def __init__(self):
        self.setup_logging()
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # WinFSP download URL (latest stable version)
        self.winfsp_url = 'https://github.com/winfsp/winfsp/releases/download/v2.0/winfsp-2.0.23075.msi'
        self.winfsp_fallback_url = 'https://winfsp.dev/rel/winfsp-2.0.23075.msi'
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('rar2fs_installer.log', encoding='utf-8')
            ]
        )
        self.logger = logging.getLogger(__name__)

    def download_file(self, url, dest_path, description):
        """Download a file with progress indication"""
        try:
            self.logger.info(f"Downloading {description}...")
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            print(f"\rProgress: {progress:.1f}%", end='', flush=True)
            
            print()  # New line after progress
            self.logger.info(f"SUCCESS: {description} downloaded successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"ERROR: Failed to download {description}: {e}")
            return False

    def check_admin_privileges(self):
        """Check if running with administrator privileges"""
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    def install_winfsp(self):
        """Download and install WinFSP"""
        try:
            # Download WinFSP installer
            msi_path = self.temp_dir / "winfsp.msi"
            
            # Try primary URL first, then fallback
            if not self.download_file(self.winfsp_url, msi_path, "WinFSP installer"):
                self.logger.info("Primary WinFSP download failed, trying fallback URL...")
                if not self.download_file(self.winfsp_fallback_url, msi_path, "WinFSP installer (fallback)"):
                    self.logger.error("ERROR: Both WinFSP download URLs failed")
                    return False

            # Install WinFSP silently (requires admin privileges)
            self.logger.info("Installing WinFSP (this may take a few minutes)...")
            self.logger.info("Note: This installation requires administrator privileges")
            
            # Try to run MSI with elevated privileges using PowerShell
            powershell_cmd = [
                'powershell', '-Command',
                f'Start-Process msiexec -ArgumentList "/i", "{msi_path}", "/quiet", "/norestart" -Verb RunAs -Wait'
            ]
            
            result = subprocess.run(powershell_cmd, timeout=300)  # 5 minute timeout
            
            if result.returncode == 0:
                self.logger.info("SUCCESS: WinFSP installed successfully!")
                return True
            else:
                self.logger.error(f"ERROR: WinFSP installation failed with code {result.returncode}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("ERROR: WinFSP installation timed out")
            return False
        except Exception as e:
            self.logger.error(f"ERROR: WinFSP installation failed: {e}")
            return False

    def check_winfsp_installed(self):
        """Check if WinFSP is already installed"""
        try:
            result = subprocess.run(['sc', 'query', 'WinFsp'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False

    def print_manual_compilation_instructions(self):
        """Print detailed instructions for manually compiling rar2fs"""
        instructions = """
================================================================================
                     rar2fs Manual Compilation Instructions                    
================================================================================

IMPORTANT: rar2fs does not provide pre-compiled Windows binaries!
           You must compile it from source using Cygwin.

STEP-BY-STEP COMPILATION GUIDE:

STEP 1: Install Cygwin (64-bit recommended):
   - Download setup-x86_64.exe from https://cygwin.com/
   - Install these packages during setup:
     * automake (wrapper + latest version)
     * autoconf (wrapper + latest version)  
     * binutils
     * gcc-core
     * gcc-g++
     * make
     * git
     * wget

STEP 2: Download rar2fs source:
   Open Cygwin Terminal and run:
   
   git clone https://github.com/hasse69/rar2fs.git
   cd rar2fs/
   autoreconf -fi

STEP 3: Download and build UnRAR source library:
   
   wget https://www.rarlab.com/rar/unrarsrc-6.0.3.tar.gz
   tar -zxf unrarsrc-6.0.3.tar.gz
   cd unrar
   make lib
   cd ..

STEP 4: Install Cygfuse (WinFSP integration):
   
   cd /cygdrive/c/Program\ Files\ \(x86\)/WinFsp/opt/cygfuse
   ./install.sh

STEP 5: Configure and build rar2fs:
   
   cd ~/rar2fs
   ./configure --with-fuse=/usr/include/fuse
   make
   make install

STEP 6: Add Cygwin to Windows PATH (optional):
   - Add C:\\cygwin64\\bin to your Windows System PATH
   - This allows running rar2fs from Windows Command Prompt

DETAILED DOCUMENTATION:
   - Windows HOWTO: https://github.com/hasse69/rar2fs/wiki/Windows-HOWTO
   - Project Homepage: https://hasse69.github.io/rar2fs/

USAGE AFTER COMPILATION:
   From Cygwin Terminal:
   rar2fs /cygdrive/x/path/to/rar/files/ /cygdrive/y/mount/point/ -ouid=-1,gid=-1

   Or from Windows (if PATH configured):
   rar2fs.exe X:\\path\\to\\rar\\files Y: -ouid=-1,gid=-1

TIP: Consider using PlexRarBridge's Python VFS mode instead, which works
     out-of-the-box without compilation requirements!

================================================================================
"""
        print(instructions)

    def run_installation(self):
        """Main installation process"""
        print("=====================================================================")
        print("                    rar2fs Setup for Windows                     ")
        print("=====================================================================")
        print()
        
        # Check admin privileges
        if not self.check_admin_privileges():
            print("WARNING: Administrator privileges required for WinFSP installation")
            print("         You may be prompted for UAC elevation during installation.")
            print()

        # Check if WinFSP is already installed
        if self.check_winfsp_installed():
            print("SUCCESS: WinFSP is already installed!")
            print()
        else:
            print("INSTALLING: WinFSP filesystem driver...")
            if not self.install_winfsp():
                print("ERROR: Failed to install WinFSP. rar2fs requires WinFSP to function.")
                return False
            print("SUCCESS: WinFSP installation completed!")
            print()

        # Always show compilation instructions since binaries don't exist
        print("NEXT STEPS - Manual Compilation Required:")
        self.print_manual_compilation_instructions()
        
        # Cleanup
        try:
            import shutil
            shutil.rmtree(self.temp_dir)
        except:
            pass
            
        return True

def main():
    installer = RarFSInstaller()
    
    try:
        success = installer.run_installation()
        if success:
            print("\nSUCCESS: Setup completed! Please follow the manual compilation instructions above.")
            print("         For easier setup, consider using PlexRarBridge's Python VFS mode instead.")
        else:
            print("\nERROR: Setup failed. Check the log file for details.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nWARNING: Installation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 