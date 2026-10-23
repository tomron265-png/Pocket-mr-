@echo off
cd /d "%~dp0"
echo PocketMR Windows Companion setup
where py >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3.11 or 3.12 from https://www.python.org/downloads/windows/
  echo During setup, check the box that says Add Python to PATH.
  pause
  exit /b 1
)
py -m venv .venv
if errorlevel 1 goto fail
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 goto fail
if not exist token.txt py -c "import secrets;from pathlib import Path;Path('token.txt').write_text(secrets.token_urlsafe(32),encoding='utf-8')"
echo.
echo Setup complete. Run start_companion.bat next.
pause
exit /b 0
:fail
echo Setup failed. Check the error above and try again.
pause
exit /b 1
