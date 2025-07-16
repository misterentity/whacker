#!/usr/bin/env python3
"""
Quick Fix: Install WinFSP with Developer Components (Cygfuse)
=============================================================

This script fixes the missing Cygfuse issue by reinstalling WinFSP 
with all components including the Developer option.
"""

import subprocess
import requests
import tempfile
import os
from pathlib import Path

def download_winfsp():
    """Download WinFSP installer"""
    print("Downloading WinFSP installer...")
    
    urls = [
        'https://github.com/winfsp/winfsp/releases/download/v2.0/winfsp-2.0.23075.msi',
        'https://winfsp.dev/rel/winfsp-2.0.23075.msi'
    ]
    
    temp_dir = Path(tempfile.mkdtemp())
    msi_path = temp_dir / "winfsp.msi"
    
    for url in urls:
        try:
            print(f"Trying: {url}")
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(msi_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            print(f"SUCCESS: Downloaded to {msi_path}")
            return msi_path
            
        except Exception as e:
            print(f"Failed: {e}")
            continue
            
    raise Exception("All download URLs failed")

def install_winfsp_with_developer_components(msi_path):
    """Install WinFSP with ALL components including Developer (Cygfuse)"""
    print("Installing WinFSP with Developer components...")
    print("This includes Cygfuse integration required for rar2fs")
    print("Note: UAC prompt will appear - please accept")
    
    # Use ADDLOCAL=ALL to install all features including Developer components
    powershell_cmd = [
        'powershell', '-Command',
        f'Start-Process msiexec -ArgumentList "/i", "{msi_path}", "/quiet", "/norestart", "ADDLOCAL=ALL" -Verb RunAs -Wait'
    ]
    
    result = subprocess.run(powershell_cmd, timeout=600)  # 10 minute timeout
    
    if result.returncode == 0:
        print("SUCCESS: WinFSP with Developer components installed!")
        return True
    else:
        print(f"ERROR: Installation failed with code {result.returncode}")
        return False

def verify_cygfuse_installation():
    """Verify that Cygfuse was properly installed"""
    print("Verifying Cygfuse installation...")
    
    possible_cygfuse_dirs = [
        Path("C:/Program Files (x86)/WinFsp/opt/cygfuse"),
        Path("C:/Program Files/WinFsp/opt/cygfuse"),
    ]
    
    for cygfuse_dir in possible_cygfuse_dirs:
        if cygfuse_dir.exists() and (cygfuse_dir / "install.sh").exists():
            print(f"SUCCESS: Found Cygfuse at {cygfuse_dir}")
            return True
            
    print("ERROR: Cygfuse still not found after installation")
    return False

def main():
    """Main execution"""
    print("================================================================================")
    print("                    WinFSP Cygfuse Fix - Developer Components")
    print("================================================================================")
    print()
    print("This will reinstall WinFSP with Developer components (includes Cygfuse)")
    print("Required for rar2fs compilation")
    print()
    
    try:
        # Download WinFSP
        msi_path = download_winfsp()
        
        # Install with all components
        if install_winfsp_with_developer_components(msi_path):
            # Verify installation
            if verify_cygfuse_installation():
                print()
                print("================================================================================")
                print("                              SUCCESS!")
                print("================================================================================")
                print("WinFSP with Cygfuse is now properly installed!")
                print()
                print("You can now run the advanced rar2fs installer again:")
                print('  "C:\\Program Files\\PlexRarBridge\\run_advanced_installer.bat"')
                print()
                print("The Cygfuse installation step should now succeed.")
                print("================================================================================")
            else:
                print("ERROR: Cygfuse verification failed")
                return False
        else:
            print("ERROR: WinFSP installation failed")
            return False
            
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    success = main()
    input("\nPress Enter to continue...")
    exit(0 if success else 1) 