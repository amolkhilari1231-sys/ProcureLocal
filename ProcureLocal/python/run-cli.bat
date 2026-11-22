@echo off
cd /d "%~dp0"
title ProcureLocal Python CLI & Analytics Console
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Python 3 is required. Please ensure Python is installed and added to PATH.
    pause
    exit /b 1
)
python procure_cli.py
pause
