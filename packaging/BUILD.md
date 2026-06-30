# Building VoiceClaw.exe (Windows)

PyInstaller must run **on Windows** (it doesn't cross-compile). On the target PC:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
pyinstaller packaging\VoiceClaw.spec
```

Output: `dist\VoiceClaw\VoiceClaw.exe` (an *onedir* build — the whole folder
is the app; ship the folder or wrap it with an installer like Inno Setup).

### Notes / gotchas
- **onedir, not onefile.** The ML/audio deps (faster-whisper/ctranslate2,
  openWakeWord models, sounddevice/PortAudio) are fragile under `--onefile`'s temp
  extraction. onedir is more reliable; switch to onefile only if you test it.
- **Whisper models** download on first use to a cache; the first run needs network
  unless you pre-bundle a model.
- **Microphone permission**: Windows may prompt on first mic use.
- **Autostart**: `python install_autostart.py` points at the tray; for the packaged
  app, point a Startup shortcut at `VoiceClaw.exe` instead.
- **Icon**: drop an `.ico` and set `icon=` in the spec.

### One-line dev run (no packaging)
```bat
python -m voiceclaw.ui      REM the desktop app
python main.py                REM the CLI agent
python -m voiceclaw.tray    REM tray only
```

## Wrapping it in an installer (Inno Setup)

After `pyinstaller packaging\VoiceClaw.spec` produces `dist\VoiceClaw\`:

1. Install Inno Setup: https://jrsoftware.org/isdl.php
2. Open `packaging\installer.iss` in the Inno Setup IDE and click **Compile**
   (or run `ISCC.exe packaging\installer.iss`).
3. Output: `Output\VoiceClaw-Setup-0.1.0.exe` — a normal Windows installer.

The installer:
- installs to `%LocalAppData%\Programs\VoiceClaw` (per-user, no admin needed),
- adds Start Menu + optional desktop shortcut,
- offers an **auto-start at sign-in** checkbox (Startup-folder shortcut),
- leaves user settings/credentials in `%USERPROFILE%\.voiceclaw` on uninstall.

Set `PrivilegesRequired=admin` and `DefaultDirName={autopf}` for an all-users
install. Add a code-signing step (signtool) before shipping to avoid SmartScreen
warnings.
