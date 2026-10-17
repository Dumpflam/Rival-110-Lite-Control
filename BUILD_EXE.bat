@echo off
setlocal
cd /d "%~dp0"
title Rival 110 Lite Control - Windows EXE Builder
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_windows.ps1"
if errorlevel 1 (
  echo.
  echo A build step failed. Please provide the error shown above.
  pause
  exit /b 1
)
echo.
echo The complete executable is here: "%~dp0Rival110LiteControl.exe"
pause
