# PyInstaller spec — build on Windows:  pyinstaller packaging/VoiceClaw.spec
# Produces dist/VoiceClaw/VoiceClaw.exe (onedir; more reliable for the
# audio/ML deps than onefile). See packaging/BUILD.md.
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], []
for pkg in ("openwakeword", "faster_whisper", "ctranslate2", "pyttsx3",
            "sounddevice", "pynput", "keyring", "anthropic", "openai",
            "pvporcupine", "pycaw", "comtypes", "pystray", "mcp"):
    try:
        d, b, h = collect_all(pkg)
        datas += d; binaries += b; hiddenimports += h
    except Exception:
        pass

a = Analysis(
    ["..\\app_entry.py"],
    pathex=[".."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + ["main", "voiceclaw.core",
        "voiceclaw.core.local_skills", "voiceclaw.core.learned_skills",
        "comtypes", "pycaw"],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="VoiceClaw",
          console=False, icon=None)
coll = COLLECT(exe, a.binaries, a.datas, name="VoiceClaw")
