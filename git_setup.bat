@echo off
cd /d "%~dp0"
echo === VoiceClaw: local git setup ===

REM clear any half-made repo
if exist ".git" rmdir /s /q ".git"

REM D: is a non-standard-ownership volume; tell git it's safe
git config --global --add safe.directory "*"
git config --global --add safe.directory "%CD%"

git init
git add -A
git commit -m "Initial commit: VoiceClaw (proprietary) - hybrid voice agent" -m "Tiered router (learned cache + Tier-1 grammar + agent), dictation/relay, companion GUI, hold-to-dictate, 1041-case routing stress test, 143 unit tests."

echo.
git log --oneline -1 2>nul && echo [OK] committed.
echo.
echo === LEAK CHECK: the moat must NOT be tracked (these should print nothing) ===
git ls-files voiceclaw/core routing_eval.py routing_stress.py tests/test_local_skills.py tests/test_routing.py tests/test_shortcuts.py
echo === (if the lines above are empty, the core is safely excluded) ===
echo.
echo NEXT - push to your PUBLIC shell repo:
echo   1) On github.com create a NEW repo, add NO README/license (we have them).
echo   2) Run (replace YOURNAME):
echo        git branch -M main
echo        git remote add origin https://github.com/YOURNAME/voiceclaw.git
echo        git push -u origin main
echo.
pause
