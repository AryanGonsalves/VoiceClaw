@echo off
setlocal
cd /d "%~dp0\.."
call ".venv\Scripts\activate.bat"
echo === [1/4] build deps (pyinstaller, cython) ===
python -m pip install --quiet pyinstaller cython
echo === [2/4] compile core to binary .pyd ===
python packaging\build_core_setup.py build_ext --inplace
if errorlevel 1 (
  echo [!] Core compile failed - install the Microsoft C++ Build Tools, or use the
  echo     PyArmor fallback in docs\OPEN_CORE.md. Aborting (won't ship readable core^).
  pause & exit /b 1
)
echo === [3/4] bundle app (core .py hidden so only the .pyd ships) ===
if exist voiceclaw\core\local_skills.py   move /y voiceclaw\core\local_skills.py   voiceclaw\core\local_skills.py.bak   >nul
if exist voiceclaw\core\learned_skills.py move /y voiceclaw\core\learned_skills.py voiceclaw\core\learned_skills.py.bak >nul
pyinstaller --noconfirm packaging\VoiceClaw.spec
set PYIERR=%errorlevel%
if exist voiceclaw\core\local_skills.py.bak   move /y voiceclaw\core\local_skills.py.bak   voiceclaw\core\local_skills.py   >nul
if exist voiceclaw\core\learned_skills.py.bak move /y voiceclaw\core\learned_skills.py.bak voiceclaw\core\learned_skills.py >nul
if not "%PYIERR%"=="0" ( echo [!] PyInstaller failed - see output above. & pause & exit /b 1 )
echo === [4/4] installer (optional; needs Inno Setup ISCC) ===
where iscc >nul 2>&1 && ( iscc packaging\installer.iss ) || echo [i] Inno Setup not found. App folder is dist\VoiceClaw\ ; install Inno to produce Setup.exe.
echo.
echo DONE.  App: dist\VoiceClaw\VoiceClaw.exe
pause
