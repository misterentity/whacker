#!/usr/bin/env python3
"""
Improved service installer for Plex RAR Bridge
Handles NSSM download and installation automatically
"""

import os
import sys
import subprocess
import urllib.request
import zipfile
import shutil
import ctypes
from pathlib import Path
import tempfile

class ServiceInstaller:
    def __init__(self):
        self.script_dir = Path(__file__).parent.absolute()
        self.service_name = "PlexRarBridge"
        self.python_script = self.script_dir / "plex_rar_bridge.py"
        self.nssm_dir = self.script_dir / "nssm"
        self.nssm_exe = self.nssm_dir / "nssm.exe"
        
    def is_admin(self):
        """Check if running as administrator"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    
    def download_nssm(self):
        """Download and extract NSSM"""
        print("NSSM not found. Downloading...")
        
        nssm_url = "https://nssm.cc/release/nssm-2.24.zip"
        temp_dir = Path(tempfile.gettempdir())
        zip_path = temp_dir / "nssm.zip"
        
        try:
            # Download NSSM
            print("  Downloading NSSM...")
            urllib.request.urlretrieve(nssm_url, zip_path)
            
            # Extract NSSM
            print("  Extracting NSSM...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Copy the appropriate version
            extracted_dir = temp_dir / "nssm-2.24"
            if sys.maxsize > 2**32:  # 64-bit
                nssm_source = extracted_dir / "win64" / "nssm.exe"
            else:  # 32-bit
                nssm_source = extracted_dir / "win32" / "nssm.exe"
            
            # Create nssm directory and copy executable
            self.nssm_dir.mkdir(exist_ok=True)
            shutil.copy2(nssm_source, self.nssm_exe)
            
            # Cleanup
            zip_path.unlink()
            shutil.rmtree(extracted_dir)
            
            print(f"  [OK] NSSM installed to: {self.nssm_exe}")
            return True
            
        except Exception as e:
            print(f"  [ERROR] Failed to download NSSM: {e}")
            return False
    
    def check_nssm(self):
        """Check if NSSM is available"""
        # Check if NSSM is in PATH
        try:
            result = subprocess.run(['nssm', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("  [OK] NSSM found in PATH")
                return "nssm"
        except FileNotFoundError:
            pass
        
        # Check if NSSM is in local directory
        if self.nssm_exe.exists():
            print(f"  [OK] NSSM found: {self.nssm_exe}")
            return str(self.nssm_exe)
        
        # Try to download NSSM
        if self.download_nssm():
            return str(self.nssm_exe)
        
        return None
    
    def run_nssm(self, args):
        """Run NSSM command"""
        nssm_cmd = self.check_nssm()
        if not nssm_cmd:
            return False
        
        try:
            result = subprocess.run([nssm_cmd] + args, 
                                  capture_output=True, text=True)
            return result.returncode == 0, result.stdout, result.stderr
        except Exception as e:
            print(f"  [ERROR] Failed to run NSSM: {e}")
            return False, "", str(e)
    
    def service_exists(self):
        """Check if service already exists"""
        try:
            result = subprocess.run(['sc', 'query', self.service_name], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    def install_service(self):
        """Install the service"""
        print(f"\nInstalling {self.service_name} service...")
        
        # Check if service already exists
        if self.service_exists():
            print("  [WARN] Service already exists")
            response = input("  Remove existing service and reinstall? (y/n): ")
            if response.lower() in ['y', 'yes']:
                self.remove_service()
            else:
                return False
        
        # Find Python executable
        python_exe = sys.executable
        print(f"  Using Python: {python_exe}")
        
        # Install service
        success, stdout, stderr = self.run_nssm(['install', self.service_name, 
                                                python_exe, str(self.python_script)])
        if not success:
            print(f"  [ERROR] Failed to install service: {stderr}")
            return False
        
        # Configure service
        configs = [
            ['set', self.service_name, 'AppDirectory', str(self.script_dir)],
            ['set', self.service_name, 'DisplayName', 'Plex RAR Bridge'],
            ['set', self.service_name, 'Description', 'Automatic RAR extraction service for Plex Media Server'],
            ['set', self.service_name, 'Start', 'SERVICE_AUTO_START'],
            ['set', self.service_name, 'AppStdout', str(self.script_dir / 'logs' / 'service_stdout.log')],
            ['set', self.service_name, 'AppStderr', str(self.script_dir / 'logs' / 'service_stderr.log')],
            ['set', self.service_name, 'AppRotateFiles', '1'],
            ['set', self.service_name, 'AppRotateOnline', '1'],
            ['set', self.service_name, 'AppRotateSeconds', '86400'],
            ['set', self.service_name, 'AppRotateBytes', '10485760']
        ]
        
        for config in configs:
            success, _, _ = self.run_nssm(config)
            if not success:
                print(f"  [WARN] Failed to set {config[2]}")
        
        print("  [OK] Service installed successfully!")
        return True
    
    def start_service(self):
        """Start the service"""
        print(f"\nStarting {self.service_name} service...")
        success, stdout, stderr = self.run_nssm(['start', self.service_name])
        if success:
            print("  [OK] Service started successfully!")
        else:
            print(f"  [ERROR] Failed to start service: {stderr}")
        return success
    
    def stop_service(self):
        """Stop the service"""
        print(f"\nStopping {self.service_name} service...")
        success, stdout, stderr = self.run_nssm(['stop', self.service_name])
        if success:
            print("  [OK] Service stopped successfully!")
        else:
            print(f"  [ERROR] Failed to stop service: {stderr}")
        return success
    
    def restart_service(self):
        """Restart the service"""
        print(f"\nRestarting {self.service_name} service...")
        success, stdout, stderr = self.run_nssm(['restart', self.service_name])
        if success:
            print("  [OK] Service restarted successfully!")
        else:
            print(f"  [ERROR] Failed to restart service: {stderr}")
        return success
    
    def remove_service(self):
        """Remove the service"""
        print(f"\nRemoving {self.service_name} service...")
        
        # Stop service first
        self.run_nssm(['stop', self.service_name])
        
        # Remove service
        success, stdout, stderr = self.run_nssm(['remove', self.service_name, 'confirm'])
        if success:
            print("  [OK] Service removed successfully!")
        else:
            print(f"  [ERROR] Failed to remove service: {stderr}")
        return success
    
    def status_service(self):
        """Show service status"""
        print(f"\n{self.service_name} Service Status:")
        try:
            result = subprocess.run(['sc', 'query', self.service_name], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(result.stdout)
            else:
                print("  Service not found")
        except Exception as e:
            print(f"  [ERROR] Failed to get status: {e}")
    
    def show_logs(self):
        """Show service logs"""
        logs_dir = self.script_dir / 'logs'
        if logs_dir.exists():
            print(f"\nOpening logs directory: {logs_dir}")
            os.startfile(str(logs_dir))
        else:
            print("\nLogs directory not found. Service may not have run yet.")
    
    def test_installation(self):
        """Test the installation"""
        print("\nRunning installation test...")
        test_script = self.script_dir / "test_installation.py"
        if test_script.exists():
            subprocess.run([sys.executable, str(test_script)])
        else:
            print("  [WARN] test_installation.py not found")
    
    def run(self):
        """Main menu"""
        print("=" * 50)
        print("Plex RAR Bridge Service Installer")
        print("=" * 50)
        
        # Check admin privileges
        if not self.is_admin():
            print("ERROR: This script must be run as Administrator")
            print("Right-click and select 'Run as administrator'")
            input("Press Enter to exit...")
            return
        
        # Check if main script exists
        if not self.python_script.exists():
            print(f"ERROR: {self.python_script} not found")
            input("Press Enter to exit...")
            return
        
        # Check NSSM
        print("Checking NSSM...")
        if not self.check_nssm():
            print("ERROR: Failed to get NSSM")
            input("Press Enter to exit...")
            return
        
        while True:
            print("\nAvailable commands:")
            print("[1] Install service")
            print("[2] Start service")
            print("[3] Stop service")
            print("[4] Restart service")
            print("[5] Remove service")
            print("[6] View service status")
            print("[7] View service logs")
            print("[8] Test installation")
            print("[9] Exit")
            
            choice = input("\nEnter your choice (1-9): ").strip()
            
            if choice == '1':
                self.install_service()
            elif choice == '2':
                self.start_service()
            elif choice == '3':
                self.stop_service()
            elif choice == '4':
                self.restart_service()
            elif choice == '5':
                self.remove_service()
            elif choice == '6':
                self.status_service()
            elif choice == '7':
                self.show_logs()
            elif choice == '8':
                self.test_installation()
            elif choice == '9':
                print("Goodbye!")
                break
            else:
                print("Invalid choice. Please enter 1-9.")
            
            input("\nPress Enter to continue...")

if __name__ == "__main__":
    installer = ServiceInstaller()
    installer.run() 