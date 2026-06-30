; Inno Setup script for VoiceClaw.
; Build the app first:  pyinstaller packaging\VoiceClaw.spec
; Then compile this in Inno Setup (ISCC.exe installer.iss) to get Setup.exe.
; Inno Setup: https://jrsoftware.org/isdl.php

#define MyAppName "VoiceClaw"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "VoiceClaw"
#define MyAppExeName "VoiceClaw.exe"

[Setup]
AppId={{A7E2F1C0-5B3D-4E8A-9F12-0C1A2B3C4D5E}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputBaseFilename=VoiceClaw-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Per-user install needs no admin; use lowest. Switch to admin for all-users.
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"
Name: "startup"; Description: "Start VoiceClaw automatically when I sign in"; GroupDescription: "Startup:"

[Files]
; Ships the entire PyInstaller onedir output folder.
Source: "..\dist\VoiceClaw\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
; Autostart shortcut (per-user Startup folder)
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch VoiceClaw"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Leave user config/credentials in %USERPROFILE%\.voiceclaw by default.
; To also remove them, uncomment:
; Type: filesandordirs; Name: "{%USERPROFILE}\.voiceclaw"
