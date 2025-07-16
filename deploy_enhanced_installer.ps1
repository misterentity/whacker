# Deploy Enhanced Advanced rar2fs Installer
Write-Host "Deploying enhanced advanced rar2fs installer..."
Copy-Item "advanced_rar2fs_installer.py" "C:\Program Files\PlexRarBridge\" -Force
Write-Host "Enhanced installer deployed successfully!"
Write-Host "The installer now includes automatic WinFSP Cygfuse handling."
pause 