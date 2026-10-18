@echo off
cd /d "%~dp0"
title JomiProman - One-click setup
echo This setup may install Docker Desktop through winget and may require administrator approval or a Windows restart.
echo Existing database volumes will be kept.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup-windows.ps1"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" echo Setup did not finish successfully. Read the error above or see WINDOWS-QUICKSTART.md.
pause
exit /b %RC%
