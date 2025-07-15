@echo off
REM Advanced rar2fs Installer - Batch Wrapper
REM Runs the Python installer with elevated privileges

echo ================================================================================
echo                    Advanced rar2fs Installer for Windows
echo ================================================================================
echo.
echo This installer will automatically:
echo   1. Install WinFSP filesystem driver
echo   2. Install Cygwin with build tools
echo   3. Download and compile UnRAR library
echo   4. Install Cygfuse integration
echo   5. Download and compile rar2fs from source
echo   6. Set up Windows integration
echo.
echo REQUIREMENTS:
echo   - Administrator privileges (will prompt for UAC)
echo   - Internet connection for downloads
echo   - 2-4 GB free disk space
echo   - 30-60 minutes installation time
echo.

set /p CONTINUE="Continue with installation? (Y/N): "
if /i not "%CONTINUE%"=="Y" (
    echo Installation cancelled.
    pause
    exit /b 1
)

echo.
echo Starting advanced rar2fs installation...
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7+ and try again
    pause
    exit /b 1
)

REM Run the advanced installer
python "%~dp0advanced_rar2fs_installer.py"

if errorlevel 1 (
    echo.
    echo ERROR: Installation failed. Check the log file for details.
    echo Log file: advanced_rar2fs_installer.log
) else (
    echo.
    echo SUCCESS: Installation completed successfully!
)

echo.
pause 