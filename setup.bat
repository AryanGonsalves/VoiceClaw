@echo off
REM One-time setup: creates a venv and installs dependencies.
cd /d "%~dp0"
python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
echo.
echo Setup complete. Run run.bat to start VoiceClaw, or: python main.py login
pause
