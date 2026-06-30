@echo off
REM Launch the VoiceClaw voice agent (CLI).
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python main.py
pause
