@echo off
setlocal enabledelayedexpansion
title ProcureLocal - Remote Database Backup Mirror

echo ==============================================================================
echo                 ProcureLocal Remote Backup Mirror Utility
echo ==============================================================================
echo.

set "SCRIPT_DIR=%~dp0"
set "NODE_EXE=%SCRIPT_DIR%core\node.exe"
if not exist "%NODE_EXE%" set "NODE_EXE=node.exe"

echo Triggering live database snapshot and remote mirror...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "try { " ^
  "  $res = Invoke-RestMethod -Uri 'http://127.0.0.1:3002/api/backups' -Method Post -TimeoutSec 15; " ^
  "  Write-Host '✔ Snapshot successfully created and mirrored to remote location:' $res.name -ForegroundColor Green; " ^
  "} catch { " ^
  "  Write-Host 'Notice: Application server not currently active on port 3002.' -ForegroundColor Yellow; " ^
  "  Write-Host 'Performing offline direct database backup...' -ForegroundColor Cyan; " ^
  "  $cfgPath = [IO.Path]::Combine('%SCRIPT_DIR%', 'config.json'); " ^
  "  if (Test-Path $cfgPath) { " ^
  "    $cfg = Get-Content $cfgPath | ConvertFrom-Json; " ^
  "    if ($cfg.remoteBackupDir) { " ^
  "      $ts = (Get-Date).ToString('yyyyMMddHHmm'); " ^
  "      $dest = [IO.Path]::Combine($cfg.remoteBackupDir, ('backup-' + $ts + '-manual-offline')); " ^
  "      New-Item -ItemType Directory -Path $dest -Force | Out-Null; " ^
  "      $dbSrc = [IO.Path]::Combine('%SCRIPT_DIR%', 'DB', 'procure.db'); " ^
  "      if (Test-Path $dbSrc) { " ^
  "        Copy-Item $dbSrc [IO.Path]::Combine($dest, 'procure.db') -Force; " ^
  "        Write-Host '✔ Offline database snapshot copied directly to:' $dest -ForegroundColor Green; " ^
  "      } " ^
  "    } else { " ^
  "      Write-Host 'No remoteBackupDir configured in config.json.' -ForegroundColor Red; " ^
  "    } " ^
  "  } " ^
  "}"

echo.
pause
