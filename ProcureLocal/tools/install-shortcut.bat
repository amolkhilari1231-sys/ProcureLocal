@echo off
cd /d "%~dp0"
echo ========================================================
echo   ProcureLocal - Installing Desktop Application Shortcut
echo ========================================================
echo.

set VBS_SCRIPT="%TEMP%\create_procurelocal_shortcut.vbs"
(
echo Set sh = CreateObject^("WScript.Shell"^)
echo target = "%~dp0ProcureLocal.vbs"
echo desk = sh.SpecialFolders^("Desktop"^)
echo Set lnk = sh.CreateShortcut^(desk ^& "\ProcureLocal.lnk"^)
echo lnk.TargetPath = "wscript.exe"
echo lnk.Arguments = """" ^& target ^& """"
echo lnk.WorkingDirectory = "%~dp0"
echo lnk.IconLocation = "shell32.dll,13"
echo lnk.Description = "ProcureLocal Enterprise Procurement Studio"
echo lnk.Save
echo startFolder = sh.SpecialFolders^("Startup"^)
echo Set fs = CreateObject^("Scripting.FileSystemObject"^)
echo If fs.FileExists^(startFolder ^& "\ProcureLocal-Server.lnk"^) Then fs.DeleteFile startFolder ^& "\ProcureLocal-Server.lnk", True
) > %VBS_SCRIPT%

cscript //nologo %VBS_SCRIPT%
del %VBS_SCRIPT% 2>nul

echo.
echo ========================================================
echo   Done! 'ProcureLocal' shortcut is created on your Desktop.
echo.
echo   Automation Active:
echo   1. Jab aap Desktop shortcut open karenge - Backend apne aap start hoga.
echo   2. Jab aap App window (X) band karenge - Backend apne aap band ho jayega.
echo ========================================================
echo.
pause
