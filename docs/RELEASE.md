# Cutting a release

1. Update `CHANGELOG.md` and the version in `voiceclaw/__init__.py`.
2. Commit, then tag:
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```
3. The **release workflow** (`.github/workflows/release.yml`) runs on the tag:
   it builds the Windows app with PyInstaller, zips `dist/VoiceClaw`, and
   attaches it to a GitHub Release.
4. (Optional) Build the installer locally with Inno Setup (`packaging/installer.iss`)
   and upload `VoiceClaw-Setup-*.exe` to the same release.

## Manual fallback (no CI)
On a Windows machine:
```bat
setup.bat
.venv\Scripts\activate
pip install pyinstaller
pyinstaller packaging\VoiceClaw.spec
powershell Compress-Archive dist\VoiceClaw VoiceClaw-0.1.0-win64.zip
```
Then create the GitHub Release in the web UI and upload the zip (and installer).

> Note: PyInstaller bundling of faster-whisper/openWakeWord can need tweaks; test
> the produced exe before publishing. Sign the binary (signtool) to avoid
> SmartScreen warnings.
