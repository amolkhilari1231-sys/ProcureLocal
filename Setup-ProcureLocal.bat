@echo off
setlocal enabledelayedexpansion
title ProcureLocal Enterprise - 1-Click Permanent Installer

echo ==============================================================================
echo                 ProcureLocal Enterprise Edition (v3.5)
echo               1-Click Permanent Installer ^& Remote Backup Setup
echo ==============================================================================
echo.

:: 1. Installation Path Selection
set "INSTALL_DIR=C:\ProcureLocal"
echo [1/5] Choose Permanent Installation Directory:
echo Default: %INSTALL_DIR%
set /p USER_DIR="Press ENTER for default or enter custom path: "
if not "!USER_DIR!"=="" set "INSTALL_DIR=!USER_DIR!"

echo Target Directory: %INSTALL_DIR%
echo.

:: 2. Remote Backup Location
echo [2/5] Remote Backup Share Destination (NAS / Windows Network Shared Drive):
echo e.g. \\192.168.1.100\ProcureBackup or D:\Backups
set /p REMOTE_BAK="Enter Remote Backup Path (or press ENTER to configure later): "
echo.

:: 3. Prepare Target Folder and Copy Files
echo [3/5] Installing application files to %INSTALL_DIR%...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

set "SRC=%~dp0"
if exist "%~dp0ProcureLocal\server.js" set "SRC=%~dp0ProcureLocal\"

echo Copying core files...
xcopy /E /I /Y /Q "%SRC%*" "%INSTALL_DIR%\" >nul 2>&1
if exist "%~dp0ProcureLocal.exe" copy /Y "%~dp0ProcureLocal.exe" "%INSTALL_DIR%\ProcureLocal.exe" >nul 2>&1

:: 4. Configure config.json
echo [4/5] Configuring network and backup settings...
set "CFG_FILE=%INSTALL_DIR%\config.json"
(
echo {
echo   "dataDir": "./DB",
if not "!REMOTE_BAK!"=="" (
  set "ESCAPED_BAK=!REMOTE_BAK:\=\\!"
  echo   "remoteBackupDir": "!ESCAPED_BAK!",
)
echo   "port": 3002
echo }
) > "%CFG_FILE%"

:: 5. Create Desktop Shortcut
echo [5/5] Creating Desktop and Start Menu Shortcuts...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws = New-Object -ComObject WScript.Shell; " ^
  "$s = $ws.CreateShortcut([IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'ProcureLocal ERP.lnk')); " ^
  "$s.TargetPath = [IO.Path]::Combine('%INSTALL_DIR%', 'ProcureLocal.exe'); " ^
  "$s.WorkingDirectory = '%INSTALL_DIR%'; " ^
  "$s.Description = 'ProcureLocal Enterprise Procurement Studio'; " ^
  "$s.IconLocation = [IO.Path]::Combine('%INSTALL_DIR%', 'ProcureLocal.exe') + ',0'; " ^
  "$s.Save(); " ^
  "$p = $ws.CreateShortcut([IO.Path]::Combine([Environment]::GetFolderPath('Programs'), 'ProcureLocal ERP.lnk')); " ^
  "$p.TargetPath = [IO.Path]::Combine('%INSTALL_DIR%', 'ProcureLocal.exe'); " ^
  "$p.WorkingDirectory = '%INSTALL_DIR%'; " ^
  "$p.Save();"

:: Lock source files for safety
echo Locking core engine files (Read-Only security)...
attrib +r "%INSTALL_DIR%\server.js" >nul 2>&1
attrib +r "%INSTALL_DIR%\public\index.html" >nul 2>&1
attrib +r "%INSTALL_DIR%\core\node.exe" >nul 2>&1

echo.
echo ==============================================================================
echo                     Installation Complete Successfully!
echo ==============================================================================
echo.
echo Installed to: %INSTALL_DIR%
echo Desktop Icon: Created ("ProcureLocal ERP")
if not "!REMOTE_BAK!"=="" (
  echo Remote Backup Vault: Active ^(!REMOTE_BAK!^)
) else (
  echo Remote Backup Vault: Local ^(Configure anytime in Settings^)
)
echo.
echo Launching ProcureLocal ERP now...
start "" "%INSTALL_DIR%\ProcureLocal.exe"
exit /b

