@echo off
setlocal
title ProcureLocal Java Enterprise SAP & Batch Bridge
echo ==============================================================================
echo       PROCURELOCAL ENTERPRISE - JAVA SAP RFC & BATCH ENGINE
echo ==============================================================================
echo.

set JAVA_CMD=java
where java >nul 2>nul
if %errorlevel% neq 0 (
    if exist "C:\Program Files\Java\jdk*\bin\java.exe" (
        for /d %%i in ("C:\Program Files\Java\jdk*") do set JAVA_CMD="%%i\bin\java.exe"
    ) else (
        echo [ERROR] Java Runtime (JRE / JDK) was not detected on this system.
        echo Please install Java 8 or higher to execute the SAP RFC connector.
        echo.
        pause
        exit /b 1
    )
)

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%..\java"

where javac >nul 2>nul
if %errorlevel% equ 0 (
    echo [*] Compiling Java Enterprise Bridge Sources...
    javac com\procurelocal\*.java
)

echo [*] Launching Enterprise SAP Bridge...
%JAVA_CMD% -cp . com.procurelocal.ProcureSapBridge %*
pause

