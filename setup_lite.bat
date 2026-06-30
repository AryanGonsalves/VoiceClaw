@echo off
REM Lite setup: UI + text mode only (PySide6, anthropic, pyyaml, requests).
cd /d "%~dp0"
set PY=
where python >nul 2>&1 && set PY=python
if not defined PY ( where py >nul 2>&1 && set PY=py )
if not defined PY (
  echo.
  echo [X] Python not found on PATH. Install Python 3.10+ from python.org and re-run.
  pause
  exit /b 1
)
echo Using %PY% ...
%PY% -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install PySide6 anthropic pyyaml requests
echo.
echo [OK] Lite setup complete. Launch with run.bat  (or: python main.py --mode text)
pause
