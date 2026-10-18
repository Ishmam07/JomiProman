@echo off
cd /d "%~dp0"
title JomiProman - Logs
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0logs-windows.ps1"
set "RC=%ERRORLEVEL%"
echo.
pause
exit /b %RC%
