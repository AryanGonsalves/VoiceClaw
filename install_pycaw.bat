@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
pip install pycaw
echo.
echo [OK] pycaw installed (audio ducking enabled).
pause
