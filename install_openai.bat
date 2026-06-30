@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
pip install openai
echo.
echo [OK] openai installed.
pause
