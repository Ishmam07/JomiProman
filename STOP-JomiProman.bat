@echo off
cd /d "%~dp0"
title JomiProman - Stop
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop-windows.ps1"
set "RC=%ERRORLEVEL%"
echo.
pause
exit /b %RC%
