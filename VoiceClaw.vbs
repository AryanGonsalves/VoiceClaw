' VoiceClaw launcher — starts the GUI with NO console window.
Set sh  = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
base = fso.GetParentFolderName(WScript.ScriptFullName)
pyw  = base & "\.venv\Scripts\pythonw.exe"
sh.CurrentDirectory = base
sh.Run """" & pyw & """ -m voiceclaw.ui", 0, False
