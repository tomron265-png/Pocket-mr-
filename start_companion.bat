@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Please run setup_windows.bat first.
  pause
  exit /b 1
)
echo Keep this window open while using PocketMR.
echo If Windows Firewall asks, allow private network access only.
echo.
.venv\Scripts\python.exe companion.py
pause
