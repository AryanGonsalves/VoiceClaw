@echo off
setlocal
cd /d "%~dp0\.."
call ".venv\Scripts\activate.bat"
echo === Compiling VoiceClaw core to binary (.pyd) ===
python -m pip install --quiet cython
python packaging\build_core_setup.py build_ext --inplace
if errorlevel 1 (
  echo.
  echo [!] Compile failed - you likely need the Microsoft C++ Build Tools:
  echo     https://visualstudio.microsoft.com/visual-cpp-build-tools/
  echo     No compiler? Use the PyArmor fallback in docs\OPEN_CORE.md
  pause & exit /b 1
)
echo.
echo [OK] core compiled to voiceclaw\core\*.pyd
echo For a SHIPPING build, delete the readable source so ONLY the binary ships:
echo     del voiceclaw\core\local_skills.py voiceclaw\core\learned_skills.py
echo Then build the installer (see packaging\BUILD.md).
pause
