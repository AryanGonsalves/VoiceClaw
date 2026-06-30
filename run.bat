@echo off
REM Launch the VoiceClaw companion app.
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python -m voiceclaw.ui
echo.
echo [VoiceClaw exited - any error is shown above]
pause
