@echo off
cd /d "%~dp0"
call ".venv\Scripts\activate.bat"
echo Launching VoiceClaw tray (close this window or use tray menu to quit)...
python -m voiceclaw.tray
echo.
echo [tray exited - code %ERRORLEVEL%]
pause
