#!/usr/bin/env python3
"""
Complete rar2fs Installation - Windows Integration
==================================================

This script completes the rar2fs installation by setting up Windows integration
that failed due to permission issues in the automated installer.
"""

import os
import subprocess
from pathlib import Path

def create_installation_directory():
    """Create rar2fs installation directory with admin privileges"""
    print("Creating rar2fs installation directory...")
    
    try:
        # Use PowerShell with admin privileges to create directory
        powershell_cmd = [
            'powershell', '-Command',
            'Start-Process powershell -ArgumentList "-Command", "New-Item -ItemType Directory -Path \\"C:\\Program Files\\rar2fs\\" -Force; Write-Host Done" -Verb RunAs -Wait'
        ]
        
        result = subprocess.run(powershell_cmd, timeout=60)
        
        if result.returncode == 0:
            print("SUCCESS: Installation directory created!")
            return True
        else:
            print(f"ERROR: Failed to create directory (code {result.returncode})")
            return False
            
    except Exception as e:
        print(f"ERROR: Directory creation failed: {e}")
        return False

def create_windows_wrapper():
    """Create a Windows batch wrapper for rar2fs"""
    print("Creating Windows wrapper for rar2fs...")
    
    try:
        # Create wrapper content
        wrapper_content = """@echo off
REM rar2fs Windows Wrapper
REM Runs rar2fs through Cygwin with proper PATH setup

setlocal

REM Add Cygwin to PATH
set PATH=C:\\cygwin64\\bin;%PATH%

REM Set Cygwin environment
set CYGWIN=nodosfilewarning

REM Run rar2fs with all passed arguments
C:\\cygwin64\\bin\\bash.exe -l -c "rar2fs %*"

endlocal
"""

        # Write to local directory first (no admin required)
        local_wrapper = Path("rar2fs.bat")
        with open(local_wrapper, 'w') as f:
            f.write(wrapper_content)
        
        print(f"Created wrapper: {local_wrapper.absolute()}")
        
        # Copy to Program Files with admin privileges
        powershell_cmd = [
            'powershell', '-Command',
            f'Start-Process powershell -ArgumentList "-Command", "Copy-Item \\"{local_wrapper.absolute()}\\" \\"C:\\Program Files\\rar2fs\\" -Force; Write-Host Done" -Verb RunAs -Wait'
        ]
        
        result = subprocess.run(powershell_cmd, timeout=60)
        
        if result.returncode == 0:
            print("SUCCESS: Windows wrapper installed!")
            return True
        else:
            print(f"ERROR: Failed to install wrapper (code {result.returncode})")
            return False
            
    except Exception as e:
        print(f"ERROR: Wrapper creation failed: {e}")
        return False

def create_usage_guide():
    """Create a usage guide for rar2fs"""
    print("Creating usage guide...")
    
    try:
        guide_content = """# rar2fs Installation Complete!

## Installation Locations
- rar2fs executable: C:\\cygwin64\\usr\\local\\bin\\rar2fs (Cygwin)
- Windows wrapper: C:\\Program Files\\rar2fs\\rar2fs.bat
- Cygwin installation: C:\\cygwin64

## Usage Examples

### From Windows Command Prompt:
```cmd
"C:\\Program Files\\rar2fs\\rar2fs.bat" "X:\\path\\to\\rar\\files" "Y:" -ouid=-1,gid=-1
```

### From Cygwin Terminal:
```bash
rar2fs /cygdrive/x/path/to/rar/files /cygdrive/y/mount/point -ouid=-1,gid=-1
```

### Basic Mount Command:
```cmd
"C:\\Program Files\\rar2fs\\rar2fs.bat" "C:\\My Archives" "Z:" -ouid=-1,gid=-1
```

## Important Options
- `-ouid=-1,gid=-1`: Use current user permissions (recommended)
- `-f`: Run in foreground (for debugging)
- `-d`: Enable debug output

## Testing the Installation
1. Create a test directory with some RAR files
2. Run: `"C:\\Program Files\\rar2fs\\rar2fs.bat" "C:\\path\\to\\rar\\files" "Z:" -ouid=-1,gid=-1`
3. Check if drive Z: appears in Windows Explorer

## Unmounting
- Press Ctrl+C in the command window
- Or use: `net use Z: /delete`

## Troubleshooting
- Make sure RAR files are valid and accessible
- Run with `-d` flag for debug output
- Check Windows Event Viewer for WinFSP errors

For more information: https://github.com/hasse69/rar2fs
"""

        guide_path = Path("rar2fs_usage_guide.txt")
        with open(guide_path, 'w') as f:
            f.write(guide_content)
        
        print(f"Created usage guide: {guide_path.absolute()}")
        return True
        
    except Exception as e:
        print(f"ERROR: Guide creation failed: {e}")
        return False

def test_installation():
    """Test the rar2fs installation"""
    print("Testing rar2fs installation...")
    
    try:
        # Test the Windows wrapper
        result = subprocess.run([
            'C:\\Program Files\\rar2fs\\rar2fs.bat', '--version'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and 'rar2fs' in result.stdout:
            print("SUCCESS: Windows wrapper is working!")
            print(f"Output: {result.stdout.strip()}")
            return True
        else:
            print("ERROR: Windows wrapper test failed")
            return False
            
    except Exception as e:
        print(f"ERROR: Installation test failed: {e}")
        return False

def main():
    """Main execution"""
    print("================================================================================")
    print("                    Complete rar2fs Installation")
    print("================================================================================")
    print()
    print("Setting up Windows integration for rar2fs...")
    print("rar2fs is already compiled and working in Cygwin!")
    print()
    
    success = True
    
    # Step 1: Create installation directory
    if not create_installation_directory():
        success = False
    
    # Step 2: Create Windows wrapper
    if success and not create_windows_wrapper():
        success = False
    
    # Step 3: Create usage guide
    if success and not create_usage_guide():
        success = False
    
    # Step 4: Test installation
    if success and not test_installation():
        success = False
    
    print()
    if success:
        print("================================================================================")
        print("                          INSTALLATION COMPLETE!")
        print("================================================================================")
        print("🎉 rar2fs has been successfully installed and configured!")
        print()
        print("QUICK TEST:")
        print('  "C:\\Program Files\\rar2fs\\rar2fs.bat" --version')
        print()
        print("MOUNT A RAR ARCHIVE:")
        print('  "C:\\Program Files\\rar2fs\\rar2fs.bat" "C:\\path\\to\\rar\\files" "Z:" -ouid=-1,gid=-1')
        print()
        print("See rar2fs_usage_guide.txt for detailed usage instructions!")
        print("================================================================================")
    else:
        print("ERROR: Installation completion failed")
        print("Check the messages above for details")
    
    return success

if __name__ == "__main__":
    success = main()
    input("\nPress Enter to continue...")
    exit(0 if success else 1) 