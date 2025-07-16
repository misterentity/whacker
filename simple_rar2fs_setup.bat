@echo off
REM Simple rar2fs Windows Integration Setup

echo ================================================================================
echo                    Complete rar2fs Installation
echo ================================================================================
echo.
echo Setting up Windows integration for rar2fs...
echo rar2fs is already compiled and working in Cygwin!
echo.

REM Create installation directory
echo Creating installation directory...
mkdir "C:\Program Files\rar2fs" 2>nul
if exist "C:\Program Files\rar2fs" (
    echo SUCCESS: Installation directory created!
) else (
    echo ERROR: Failed to create installation directory
    goto :error
)

REM Create Windows wrapper
echo Creating Windows wrapper...
(
echo @echo off
echo REM rar2fs Windows Wrapper
echo REM Runs rar2fs through Cygwin with proper PATH setup
echo.
echo setlocal
echo.
echo REM Add Cygwin to PATH
echo set PATH=C:\cygwin64\bin;%%PATH%%
echo.
echo REM Set Cygwin environment
echo set CYGWIN=nodosfilewarning
echo.
echo REM Run rar2fs with all passed arguments
echo C:\cygwin64\bin\bash.exe -l -c "rar2fs %%*"
echo.
echo endlocal
) > "C:\Program Files\rar2fs\rar2fs.bat"

if exist "C:\Program Files\rar2fs\rar2fs.bat" (
    echo SUCCESS: Windows wrapper created!
) else (
    echo ERROR: Failed to create Windows wrapper
    goto :error
)

REM Test the installation
echo Testing rar2fs installation...
"C:\Program Files\rar2fs\rar2fs.bat" --version
if %errorlevel% equ 0 (
    echo SUCCESS: rar2fs is working!
) else (
    echo ERROR: rar2fs test failed
    goto :error
)

echo.
echo ================================================================================
echo                          INSTALLATION COMPLETE!
echo ================================================================================
echo 🎉 rar2fs has been successfully installed and configured!
echo.
echo QUICK TEST:
echo   "C:\Program Files\rar2fs\rar2fs.bat" --version
echo.
echo MOUNT A RAR ARCHIVE:
echo   "C:\Program Files\rar2fs\rar2fs.bat" "C:\path\to\rar\files" "Z:" -ouid=-1,gid=-1
echo.
echo USAGE EXAMPLES:
echo   Mount to drive Z: "C:\Program Files\rar2fs\rar2fs.bat" "C:\My RAR Files" "Z:" -ouid=-1,gid=-1
echo   Mount with debug: "C:\Program Files\rar2fs\rar2fs.bat" "C:\Archives" "Y:" -ouid=-1,gid=-1 -d
echo.
echo UNMOUNTING:
echo   Press Ctrl+C in the rar2fs window, or use: net use Z: /delete
echo.
echo ================================================================================
pause
exit /b 0

:error
echo.
echo ERROR: Installation completion failed
pause
exit /b 1 