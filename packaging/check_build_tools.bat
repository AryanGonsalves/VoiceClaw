@echo off
cd /d "%~dp0\.."
call ".venv\Scripts\activate.bat" 2>nul
echo === build tool check ===
python --version 2>&1
echo -- pyinstaller: & python -c "import PyInstaller;print(PyInstaller.__version__)" 2>&1
echo -- cython:      & python -c "import Cython;print(Cython.__version__)" 2>&1
echo -- MSVC cl.exe: & where cl 2>&1
echo -- Inno iscc:   & where iscc 2>&1
echo === done ===
pause
