#!/usr/bin/env python3
"""
Advanced rar2fs Installer for Windows
=====================================

This installer automates the entire rar2fs compilation process:
- Installs Cygwin with build tools
- Downloads and compiles UnRAR source library
- Installs WinFSP and Cygfuse
- Downloads and compiles rar2fs from source
- Sets up proper Windows integration

Author: Plex RAR Bridge Enhanced Edition
Version: 1.0.0
"""

import os
import sys
import subprocess
import tempfile
import logging
import requests
import time
import shutil
import zipfile
import tarfile
from pathlib import Path
from urllib.parse import urlparse

class AdvancedRarFSInstaller:
    def __init__(self):
        self.setup_logging()
        self.temp_dir = Path(tempfile.mkdtemp())
        self.cygwin_root = Path("C:/cygwin64")
        self.install_dir = Path("C:/Program Files/rar2fs")
        
        # Download URLs
        self.downloads = {
            'cygwin_setup': 'https://cygwin.com/setup-x86_64.exe',
            'winfsp': 'https://github.com/winfsp/winfsp/releases/download/v2.0/winfsp-2.0.23075.msi',
            'winfsp_fallback': 'https://winfsp.dev/rel/winfsp-2.0.23075.msi',
            'unrar_source': 'https://www.rarlab.com/rar/unrarsrc-6.0.3.tar.gz',
            'rar2fs_source': 'https://github.com/hasse69/rar2fs/archive/refs/heads/master.zip'
        }
        
        # Required Cygwin packages
        self.cygwin_packages = [
            'automake',
            'autoconf', 
            'binutils',
            'gcc-core',
            'gcc-g++',
            'make',
            'git',
            'wget',
            'tar',
            'gzip',
            'unzip',  # Required for extracting rar2fs source
            'gettext-devel',  # Required for autopoint (used by autoreconf)
            'pkg-config',
            'libtool',
            'patch',
            'diffutils',
            'cygwin-devel'
        ]
        
        self.logger.info("Advanced rar2fs Installer initialized")
        
    def setup_logging(self):
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('advanced_rar2fs_installer.log', encoding='utf-8')
            ]
        )
        self.logger = logging.getLogger(__name__)

    def check_admin_privileges(self):
        """Check if running with admin privileges"""
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

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

    def install_winfsp(self):
        """Install WinFSP filesystem driver"""
        try:
            # Check if already installed
            if self.check_winfsp_installed():
                self.logger.info("WinFSP is already installed")
                return True
                
            # Download WinFSP installer
            msi_path = self.temp_dir / "winfsp.msi"
            
            if not self.download_file(self.downloads['winfsp'], msi_path, "WinFSP installer"):
                self.logger.info("Primary WinFSP download failed, trying fallback URL...")
                if not self.download_file(self.downloads['winfsp_fallback'], msi_path, "WinFSP installer (fallback)"):
                    self.logger.error("ERROR: Both WinFSP download URLs failed")
                    return False

            # Install WinFSP silently (requires admin privileges)
            self.logger.info("Installing WinFSP (this may take a few minutes)...")
            self.logger.info("Note: This installation requires administrator privileges")
            
            # Run MSI with elevated privileges using PowerShell
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
            return result.returncode == 0 or Path("C:/Program Files (x86)/WinFsp").exists()
        except:
            return False

    def install_cygwin(self):
        """Install Cygwin with required build tools"""
        try:
            self.logger.info("Installing Cygwin with build tools...")
            
            # Download Cygwin setup
            setup_path = self.temp_dir / "setup-x86_64.exe"
            if not self.download_file(self.downloads['cygwin_setup'], setup_path, "Cygwin setup"):
                return False
            
            # Prepare package list
            packages = ','.join(self.cygwin_packages)
            
            # Install Cygwin silently with required packages
            self.logger.info("Installing Cygwin (this may take 10-15 minutes)...")
            cmd = [
                str(setup_path),
                '--quiet-mode',
                '--no-shortcuts',
                '--no-startmenu',
                '--no-desktop',
                '--root', str(self.cygwin_root),
                '--local-package-dir', str(self.temp_dir / 'cygwin_packages'),
                '--site', 'http://cygwin.mirror.constant.com',
                '--packages', packages
            ]
            
            result = subprocess.run(cmd, timeout=1800)  # 30 minute timeout
            
            if result.returncode == 0:
                self.logger.info("SUCCESS: Cygwin installed successfully!")
                return True
            else:
                self.logger.error(f"ERROR: Cygwin installation failed with code {result.returncode}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("ERROR: Cygwin installation timed out")
            return False
        except Exception as e:
            self.logger.error(f"ERROR: Cygwin installation failed: {e}")
            return False

    def check_cygwin_installed(self):
        """Check if Cygwin is already installed"""
        return self.cygwin_root.exists() and (self.cygwin_root / "bin" / "bash.exe").exists()

    def run_cygwin_command(self, command, working_dir=None):
        """Run a command in Cygwin environment"""
        try:
            bash_exe = self.cygwin_root / "bin" / "bash.exe"
            if not bash_exe.exists():
                self.logger.error("ERROR: Cygwin bash not found")
                return False
                
            # Set up Cygwin environment
            env = os.environ.copy()
            env['PATH'] = f"{self.cygwin_root}/bin;{env.get('PATH', '')}"
            env['CYGWIN'] = 'nodosfilewarning'
            
            if working_dir:
                # Convert Windows path to Cygwin path
                cygwin_path = self.windows_to_cygwin_path(working_dir)
                full_command = f"cd '{cygwin_path}' && {command}"
            else:
                full_command = command
            
            self.logger.info(f"Running Cygwin command: {command}")
            result = subprocess.run(
                [str(bash_exe), '-l', '-c', full_command],
                env=env,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.stdout:
                self.logger.info(f"Command output: {result.stdout}")
            if result.stderr:
                self.logger.warning(f"Command stderr: {result.stderr}")
                
            return result.returncode == 0
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"ERROR: Command timed out: {command}")
            return False
        except Exception as e:
            self.logger.error(f"ERROR: Failed to run Cygwin command '{command}': {e}")
            return False

    def windows_to_cygwin_path(self, windows_path):
        """Convert Windows path to Cygwin path format"""
        path = Path(windows_path).resolve()
        path_str = str(path).replace('\\', '/')
        
        # Convert C: to /cygdrive/c
        if path_str[1:3] == ':/':
            drive = path_str[0].lower()
            path_str = f"/cygdrive/{drive}{path_str[2:]}"
        
        return path_str

    def download_and_compile_unrar(self):
        """Download and compile UnRAR source library"""
        try:
            self.logger.info("Downloading and compiling UnRAR source library...")
            
            # Create build directory in Cygwin
            build_dir = self.temp_dir / "unrar_build"
            build_dir.mkdir(exist_ok=True)
            
            # Download UnRAR source
            unrar_tar = build_dir / "unrarsrc.tar.gz"
            if not self.download_file(self.downloads['unrar_source'], unrar_tar, "UnRAR source"):
                return False
            
            # Extract UnRAR source in Cygwin
            if not self.run_cygwin_command(f"cd '{self.windows_to_cygwin_path(build_dir)}' && tar -zxf unrarsrc.tar.gz"):
                self.logger.error("ERROR: Failed to extract UnRAR source")
                return False
            
            # Compile UnRAR library
            unrar_dir = build_dir / "unrar"
            if not self.run_cygwin_command("make lib", unrar_dir):
                self.logger.error("ERROR: Failed to compile UnRAR library")
                return False
            
            self.logger.info("SUCCESS: UnRAR library compiled successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"ERROR: UnRAR compilation failed: {e}")
            return False

    def install_cygfuse(self):
        """Install Cygfuse (WinFSP integration for Cygwin)"""
        try:
            self.logger.info("Installing Cygfuse...")
            
            # Check if WinFSP Cygfuse directory exists
            cygfuse_dir = Path("C:/Program Files (x86)/WinFsp/opt/cygfuse")
            if not cygfuse_dir.exists():
                self.logger.error("ERROR: WinFSP Cygfuse directory not found. Ensure WinFSP is installed.")
                return False
            
            # Run Cygfuse install script
            cygfuse_path = self.windows_to_cygwin_path(cygfuse_dir)
            if not self.run_cygwin_command(f"cd '{cygfuse_path}' && ./install.sh"):
                self.logger.error("ERROR: Failed to install Cygfuse")
                return False
            
            self.logger.info("SUCCESS: Cygfuse installed successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"ERROR: Cygfuse installation failed: {e}")
            return False

    def download_and_compile_rar2fs(self):
        """Download and compile rar2fs from source"""
        try:
            self.logger.info("Downloading and compiling rar2fs...")
            
            # Create build directory
            build_dir = self.temp_dir / "rar2fs_build"  
            build_dir.mkdir(exist_ok=True)
            
            # Download rar2fs source
            rar2fs_zip = build_dir / "rar2fs-master.zip"
            if not self.download_file(self.downloads['rar2fs_source'], rar2fs_zip, "rar2fs source"):
                return False
            
            # Extract rar2fs source in Cygwin
            build_cygwin_path = self.windows_to_cygwin_path(build_dir)
            if not self.run_cygwin_command(f"cd '{build_cygwin_path}' && unzip -q rar2fs-master.zip"):
                self.logger.error("ERROR: Failed to extract rar2fs source")
                return False
            
            # Prepare build environment
            rar2fs_source_dir = build_dir / "rar2fs-master"
            rar2fs_cygwin_path = self.windows_to_cygwin_path(rar2fs_source_dir)
            
            # Run autoreconf
            if not self.run_cygwin_command("autoreconf -fi", rar2fs_source_dir):
                self.logger.error("ERROR: Failed to run autoreconf")
                return False
            
            # Configure build
            unrar_lib_path = self.windows_to_cygwin_path(self.temp_dir / "unrar_build" / "unrar")
            configure_cmd = f"./configure --with-unrar='{unrar_lib_path}' --with-fuse=/usr/include/fuse"
            if not self.run_cygwin_command(configure_cmd, rar2fs_source_dir):
                self.logger.error("ERROR: Failed to configure rar2fs build")
                return False
            
            # Compile rar2fs
            if not self.run_cygwin_command("make", rar2fs_source_dir):
                self.logger.error("ERROR: Failed to compile rar2fs")
                return False
            
            # Install rar2fs
            if not self.run_cygwin_command("make install", rar2fs_source_dir):
                self.logger.error("ERROR: Failed to install rar2fs")
                return False
            
            self.logger.info("SUCCESS: rar2fs compiled and installed successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"ERROR: rar2fs compilation failed: {e}")
            return False

    def setup_windows_integration(self):
        """Set up Windows integration for rar2fs"""
        try:
            self.logger.info("Setting up Windows integration...")
            
            # Create installation directory
            self.install_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy rar2fs executable to Windows accessible location
            rar2fs_exe = self.cygwin_root / "usr" / "local" / "bin" / "rar2fs.exe"
            if rar2fs_exe.exists():
                target_exe = self.install_dir / "rar2fs.exe"
                shutil.copy2(rar2fs_exe, target_exe)
                self.logger.info(f"Copied rar2fs.exe to {target_exe}")
            
            # Copy required Cygwin DLLs
            dll_files = [
                "cygwin1.dll",
                "cygfuse-2.dll", 
                "cyggcc_s-seh-1.dll",
                "cygstdc++-6.dll"
            ]
            
            for dll in dll_files:
                dll_path = self.cygwin_root / "bin" / dll
                if dll_path.exists():
                    target_dll = self.install_dir / dll
                    shutil.copy2(dll_path, target_dll)
                    self.logger.info(f"Copied {dll} to installation directory")
            
            # Create wrapper script for easier Windows usage
            wrapper_content = f'''@echo off
REM rar2fs Windows Wrapper Script
REM Usage: rar2fs.bat <rar_directory> <mount_point> [options]

set RAR2FS_DIR={self.install_dir}
set PATH=%RAR2FS_DIR%;%PATH%

"%RAR2FS_DIR%\\rar2fs.exe" %*
'''
            
            wrapper_path = self.install_dir / "rar2fs.bat"
            with open(wrapper_path, 'w') as f:
                f.write(wrapper_content)
            
            self.logger.info("SUCCESS: Windows integration set up successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"ERROR: Windows integration setup failed: {e}")
            return False

    def run_installation(self):
        """Main installation process"""
        print("================================================================================")
        print("                    Advanced rar2fs Installer for Windows")
        print("================================================================================")
        print()
        
        # Check admin privileges
        if not self.check_admin_privileges():
            print("WARNING: Administrator privileges recommended for WinFSP installation")
            print("         You may be prompted for UAC elevation during installation.")
            print()

        try:
            # Step 1: Install WinFSP
            print("STEP 1/6: Installing WinFSP filesystem driver...")
            if not self.install_winfsp():
                print("ERROR: Failed to install WinFSP")
                return False
            print("SUCCESS: WinFSP installation completed!")
            print()

            # Step 2: Install Cygwin
            print("STEP 2/6: Installing Cygwin with build tools...")
            if self.check_cygwin_installed():
                print("SUCCESS: Cygwin is already installed!")
            else:
                if not self.install_cygwin():
                    print("ERROR: Failed to install Cygwin")
                    return False
                print("SUCCESS: Cygwin installation completed!")
            print()

            # Step 3: Download and compile UnRAR
            print("STEP 3/6: Downloading and compiling UnRAR library...")
            if not self.download_and_compile_unrar():
                print("ERROR: Failed to compile UnRAR library")
                return False
            print("SUCCESS: UnRAR library compilation completed!")
            print()

            # Step 4: Install Cygfuse
            print("STEP 4/6: Installing Cygfuse (WinFSP integration)...")
            if not self.install_cygfuse():
                print("ERROR: Failed to install Cygfuse")
                return False
            print("SUCCESS: Cygfuse installation completed!")
            print()

            # Step 5: Download and compile rar2fs
            print("STEP 5/6: Downloading and compiling rar2fs...")
            if not self.download_and_compile_rar2fs():
                print("ERROR: Failed to compile rar2fs")
                return False
            print("SUCCESS: rar2fs compilation completed!")
            print()

            # Step 6: Set up Windows integration
            print("STEP 6/6: Setting up Windows integration...")
            if not self.setup_windows_integration():
                print("ERROR: Failed to set up Windows integration")
                return False
            print("SUCCESS: Windows integration completed!")
            print()

            return True

        except Exception as e:
            self.logger.error(f"ERROR: Installation failed: {e}")
            return False

    def print_success_message(self):
        """Print installation success message with usage instructions"""
        print("================================================================================")
        print("                          INSTALLATION COMPLETED!")
        print("================================================================================")
        print()
        print("SUCCESS: rar2fs has been successfully compiled and installed!")
        print()
        print("INSTALLATION LOCATIONS:")
        print(f"  - rar2fs executable: {self.install_dir / 'rar2fs.exe'}")
        print(f"  - Windows wrapper:   {self.install_dir / 'rar2fs.bat'}")
        print(f"  - Cygwin installation: {self.cygwin_root}")
        print()
        print("USAGE:")
        print("  From Windows Command Prompt:")
        print(f'    "{self.install_dir / "rar2fs.bat"}" "X:\\path\\to\\rar\\files" "Y:" -ouid=-1,gid=-1')
        print()
        print("  From Cygwin Terminal:")
        print("    rar2fs /cygdrive/x/path/to/rar/files /cygdrive/y/mount/point -ouid=-1,gid=-1")
        print()
        print("NEXT STEPS:")
        print("  1. Test the installation by mounting a RAR archive")
        print("  2. Configure PlexRarBridge to use rar2fs mode")
        print("  3. Add the installation directory to your Windows PATH (optional)")
        print()
        print("For support and documentation:")
        print("  - rar2fs project: https://hasse69.github.io/rar2fs/")
        print("  - Installation log: advanced_rar2fs_installer.log")
        print()
        print("================================================================================")

def main():
    """Main entry point"""
    try:
        installer = AdvancedRarFSInstaller()
        
        success = installer.run_installation()
        if success:
            installer.print_success_message()
        else:
            print("\nERROR: Installation failed. Check the log file for details.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nWARNING: Installation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 