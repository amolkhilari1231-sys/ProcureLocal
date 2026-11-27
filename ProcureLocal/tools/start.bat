@echo off
cd /d "%~dp0.."
where node >nul 2>nul || (echo Node.js 22.13 or newer is required. Install the LTS version from https://nodejs.org & pause & exit /b 1)
if not exist config.json (
  echo First-time setup.
  set /p DIR=Enter the full path of the folder to store ALL data ^(e.g. D:\Procurement or \\server\share\Procurement^): 
  set /p SHARE=Allow other PCs on your network to open the app? ^(y/n^): 
  setlocal enabledelayedexpansion
  set HOST=127.0.0.1
  if /i "!SHARE!"=="y" set HOST=0.0.0.0
  set "J=!DIR:\=\\!"
  echo {"dataDir":"!J!","port":3002,"host":"!HOST!"}> config.json
  endlocal
)
node -e "const fs=require('fs'); let p=3002; try{p=JSON.parse(fs.readFileSync('config.json')).port||3002}catch{}; require('child_process').exec('start http://localhost:'+p);"
node server.js
pause
