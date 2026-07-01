# Cutting a release

The Windows app is built **locally**: GitHub's Linux runners can't produce a Windows
`.exe`, and the full test suite needs the private core. CI only compile-checks the shell.

## Steps (on the Windows build machine, with the private core present)
1. Bump `CHANGELOG.md` and the version in `voiceclaw/__init__.py`.
2. Build the app bundle: `packaging\build_app.bat` -> `dist\VoiceClaw\VoiceClaw.exe` (+ `_internal`).
3. Build the installer: `packaging\build_installer.bat` -> `packaging\Output\VoiceClaw-Setup-<ver>.exe`.
   Needs Inno Setup: `winget install JRSoftware.InnoSetup --scope user` (user scope, no admin).
4. Build the portable zip: `packaging\zip_dist.bat` -> `dist\VoiceClaw-portable.zip`.
5. Tag and push: `git tag v<ver> && git push origin v<ver>`.
6. On GitHub -> Releases -> Draft new release -> pick the tag -> **drag both assets in**
   (installer + portable zip) -> Publish. Both exceed GitHub's 100 MB file limit, so they
   must be **release assets** (allowed up to 2 GB), not committed files.

## Notes
- The installer/zip are **not** code-signed, so SmartScreen shows "unknown publisher";
  users click **More info -> Run anyway** (the portable zip trips it far less). Signing
  (signtool + a cert, or Azure Trusted Signing) removes this — deferred, no budget.
- `.github/workflows/release.yml` (PyInstaller-on-tag) is kept for reference, but a Linux
  runner can't build the Windows binary; the local `.bat` flow above is the real path.
