#!/usr/bin/env python3
"""
Quick Fix: Install missing unzip package in Cygwin
==================================================

The rar2fs installer failed because Cygwin is missing the 'unzip' package.
This script will install it and allow the installation to continue.
"""

import subprocess
import tempfile
import requests
from pathlib import Path

def download_cygwin_setup():
    """Download Cygwin setup executable"""
    print("Downloading Cygwin setup...")
    
    temp_dir = Path(tempfile.mkdtemp())
    setup_path = temp_dir / "setup-x86_64.exe"
    
    url = 'https://cygwin.com/setup-x86_64.exe'
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    with open(setup_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            
    print(f"Downloaded to: {setup_path}")
    return setup_path

def install_unzip_package(setup_path):
    """Install unzip package in existing Cygwin installation"""
    print("Installing unzip package in Cygwin...")
    print("This may take a few minutes...")
    
    # Install unzip package to existing Cygwin installation
    cmd = [
        str(setup_path),
        '--quiet-mode',
        '--no-desktop',
        '--no-shortcuts', 
        '--no-startmenu',
        '--root', 'C:\\cygwin64',
        '--site', 'http://cygwin.mirror.constant.com',
        '--packages', 'unzip'
    ]
    
    result = subprocess.run(cmd, timeout=300)  # 5 minute timeout
    
    if result.returncode == 0:
        print("SUCCESS: unzip package installed!")
        return True
    else:
        print(f"ERROR: Failed to install unzip package (code {result.returncode})")
        return False

def verify_unzip_installation():
    """Verify that unzip is now available in Cygwin"""
    print("Verifying unzip installation...")
    
    try:
        # Test unzip command in Cygwin
        result = subprocess.run([
            'C:\\cygwin64\\bin\\bash.exe', '-l', '-c', 'which unzip'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and 'unzip' in result.stdout:
            print(f"SUCCESS: unzip found at {result.stdout.strip()}")
            return True
        else:
            print("ERROR: unzip still not found")
            return False
            
    except Exception as e:
        print(f"ERROR: Verification failed: {e}")
        return False

def main():
    """Main execution"""
    print("================================================================================")
    print("                    Cygwin unzip Package Installer")
    print("================================================================================")
    print()
    print("Installing missing 'unzip' package needed for rar2fs compilation...")
    print()
    
    try:
        # Download Cygwin setup
        setup_path = download_cygwin_setup()
        
        # Install unzip package
        if install_unzip_package(setup_path):
            # Verify installation
            if verify_unzip_installation():
                print()
                print("================================================================================")
                print("                              SUCCESS!")
                print("================================================================================")
                print("The 'unzip' package has been installed in Cygwin!")
                print()
                print("You can now run the advanced rar2fs installer again:")
                print('  "C:\\Program Files\\PlexRarBridge\\run_advanced_installer.bat"')
                print()
                print("It should continue from Step 5 and complete successfully.")
                print("================================================================================")
                return True
            else:
                print("ERROR: unzip verification failed")
                return False
        else:
            print("ERROR: unzip installation failed")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    success = main()
    input("\nPress Enter to continue...")
    exit(0 if success else 1) 