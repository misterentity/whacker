#!/usr/bin/env python3
"""
Quick Fix: Install missing gettext-devel package in Cygwin
=========================================================

The rar2fs installer failed because Cygwin is missing the 'gettext-devel' package
which contains 'autopoint' needed for autoreconf.
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

def install_gettext_package(setup_path):
    """Install gettext-devel package in existing Cygwin installation"""
    print("Installing gettext-devel package in Cygwin...")
    print("This may take a few minutes...")
    
    # Install gettext-devel package to existing Cygwin installation
    cmd = [
        str(setup_path),
        '--quiet-mode',
        '--no-desktop',
        '--no-shortcuts', 
        '--no-startmenu',
        '--root', 'C:\\cygwin64',
        '--site', 'http://cygwin.mirror.constant.com',
        '--packages', 'gettext-devel'
    ]
    
    result = subprocess.run(cmd, timeout=300)  # 5 minute timeout
    
    if result.returncode == 0:
        print("SUCCESS: gettext-devel package installed!")
        return True
    else:
        print(f"ERROR: Failed to install gettext-devel package (code {result.returncode})")
        return False

def verify_autopoint_installation():
    """Verify that autopoint is now available in Cygwin"""
    print("Verifying autopoint installation...")
    
    try:
        # Test autopoint command in Cygwin
        result = subprocess.run([
            'C:\\cygwin64\\bin\\bash.exe', '-l', '-c', 'which autopoint'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and 'autopoint' in result.stdout:
            print(f"SUCCESS: autopoint found at {result.stdout.strip()}")
            return True
        else:
            print("ERROR: autopoint still not found")
            return False
            
    except Exception as e:
        print(f"ERROR: Verification failed: {e}")
        return False

def main():
    """Main execution"""
    print("================================================================================")
    print("                    Cygwin gettext-devel Package Installer")
    print("================================================================================")
    print()
    print("Installing missing 'gettext-devel' package needed for rar2fs compilation...")
    print("This package contains 'autopoint' required by autoreconf")
    print()
    
    try:
        # Download Cygwin setup
        setup_path = download_cygwin_setup()
        
        # Install gettext-devel package
        if install_gettext_package(setup_path):
            # Verify installation
            if verify_autopoint_installation():
                print()
                print("================================================================================")
                print("                              SUCCESS!")
                print("================================================================================")
                print("The 'gettext-devel' package has been installed in Cygwin!")
                print("autopoint is now available for autoreconf")
                print()
                print("You can now run the advanced rar2fs installer again:")
                print('  echo Y | python advanced_rar2fs_installer.py')
                print()
                print("It should continue from Step 5 and complete successfully.")
                print("================================================================================")
                return True
            else:
                print("ERROR: autopoint verification failed")
                return False
        else:
            print("ERROR: gettext-devel installation failed")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    success = main()
    input("\nPress Enter to continue...")
    exit(0 if success else 1) 