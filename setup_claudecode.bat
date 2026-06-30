@echo off
REM Install the Claude Code route dependency (MCP) into the venv.
cd /d "%~dp0"
call .venv\Scripts\activate.bat
pip install mcp
echo.
echo [OK] MCP installed. Make sure Claude Code works: run "claude" in a terminal.
pause
