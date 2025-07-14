@echo off
echo Starting Plex RAR Bridge Setup Panel...
python gui_monitor.py setup
if errorlevel 1 (
    echo.
    echo Failed to start GUI. Make sure Python is installed and in PATH.
    pause
) 