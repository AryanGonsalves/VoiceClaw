# VoiceClaw — Copyright (c) 2026 Aryan Gonsalves. All rights reserved. Proprietary; see LICENSE.
#!/usr/bin/env python3
"""Register (or remove) VoiceClaw to start automatically at login.

Cross-platform:
  - Windows: a Start-up **shortcut (.lnk)** so it appears cleanly in
             Task Manager > Startup apps (where users can enable/disable it).
  - macOS:   a LaunchAgent plist in ~/Library/LaunchAgents
  - Linux:   a .desktop entry in ~/.config/autostart

Usage:
  python install_autostart.py            # install
  python install_autostart.py --remove   # uninstall

Note: Task Manager can toggle this on/off once it's registered, but Windows does
not let you *add* a new startup item from Task Manager — that's what this does.
"""
from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path

APP = "VoiceClaw"
OS = platform.system()
PROJECT_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable
LAUNCH_ARGS = ["-m", "voiceclaw.tray"]  # background tray entry


def _win_startup_dir() -> Path:
    return Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs/Startup"


def _win_lnk() -> Path:
    return _win_startup_dir() / f"{APP}.lnk"


def _macos_path() -> Path:
    return Path.home() / "Library/LaunchAgents" / "com.voiceclaw.agent.plist"


def _linux_path() -> Path:
    return Path.home() / ".config/autostart" / f"{APP}.desktop"


def _ps_quote(s) -> str:
    """Escape a string for a PowerShell single-quoted literal.
    Single quotes are doubled, so paths with apostrophes (e.g. a Windows
    username like "Aryan's Laptop") don't break the command."""
    return str(s).replace("'", "''")


def _make_win_shortcut() -> Path:
    """Create a .lnk in the Startup folder via PowerShell (no extra deps).
    Uses pythonw.exe so no console window appears."""
    lnk = _win_lnk()
    lnk.parent.mkdir(parents=True, exist_ok=True)
    pyw = PYTHON.replace("python.exe", "pythonw.exe")
    args = " ".join(LAUNCH_ARGS)
    ps = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{lnk}');"
        "$s.TargetPath='{pyw}';"
        "$s.Arguments='{args}';"
        "$s.WorkingDirectory='{wd}';"
        "$s.WindowStyle=7;"
        "$s.Description='VoiceClaw voice assistant';"
        "$s.Save()"
    ).format(lnk=_ps_quote(lnk), pyw=_ps_quote(pyw),
             args=_ps_quote(args), wd=_ps_quote(PROJECT_DIR))
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                   check=True)
    return lnk


def install():
    if OS == "Windows":
        # Clean up any legacy .bat from older versions.
        legacy = _win_startup_dir() / f"{APP}.bat"
        if legacy.exists():
            legacy.unlink()
        p = _make_win_shortcut()
    elif OS == "Darwin":
        p = _macos_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        args = "".join(f"\n    <string>{a}</string>" for a in [PYTHON, *LAUNCH_ARGS])
        p.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
            '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            '<plist version="1.0"><dict>\n'
            '  <key>Label</key><string>com.voiceclaw.agent</string>\n'
            f'  <key>ProgramArguments</key><array>{args}\n  </array>\n'
            f'  <key>WorkingDirectory</key><string>{PROJECT_DIR}</string>\n'
            '  <key>RunAtLoad</key><true/>\n'
            '</dict></plist>\n', encoding="utf-8")
        os.system(f'launchctl load "{p}" 2>/dev/null')
    else:
        p = _linux_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            "[Desktop Entry]\nType=Application\n"
            f"Name={APP}\n"
            f'Exec={PYTHON} {" ".join(LAUNCH_ARGS)}\n'
            f"Path={PROJECT_DIR}\n"
            "X-GNOME-Autostart-enabled=true\nTerminal=false\n", encoding="utf-8")
    print(f"Installed auto-start: {p}")
    if OS == "Windows":
        print("You can enable/disable it anytime in Task Manager > Startup apps.")


def remove():
    if OS == "Windows":
        removed = False
        for f in (_win_lnk(), _win_startup_dir() / f"{APP}.bat"):
            if f.exists():
                f.unlink(); removed = True
        print("Removed auto-start." if removed else "Nothing to remove.")
        return
    p = _macos_path() if OS == "Darwin" else _linux_path()
    if OS == "Darwin":
        os.system(f'launchctl unload "{p}" 2>/dev/null')
    if p.exists():
        p.unlink(); print(f"Removed auto-start: {p}")
    else:
        print("Nothing to remove.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--remove", action="store_true")
    args = ap.parse_args()
    remove() if args.remove else install()