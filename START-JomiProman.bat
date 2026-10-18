@echo off
cd /d "%~dp0"
title JomiProman - Start
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-windows.ps1"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" echo Could not start JomiProman. See the error above.
pause
exit /b %RC%
