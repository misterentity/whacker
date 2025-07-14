@echo off
REM Simple launcher for the Python service installer
REM This automatically downloads NSSM and handles everything

echo Starting Plex RAR Bridge Service Installer...
echo.

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This script must be run as Administrator
    echo Right-click and select "Run as administrator"
    pause
    exit /b 1
)

REM Run the Python installer
python install_service_improved.py

pause 