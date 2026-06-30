@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python cc_test.py
