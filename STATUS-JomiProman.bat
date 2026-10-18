@echo off
cd /d "%~dp0"
title JomiProman - Status
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0status-windows.ps1"
set "RC=%ERRORLEVEL%"
echo.
pause
exit /b %RC%
