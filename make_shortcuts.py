# VoiceClaw — Copyright (c) 2026 Aryan Gonsalves. All rights reserved. Proprietary; see LICENSE.
"""Create a no-console Desktop shortcut for the VoiceClaw companion app."""
import os, subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parent
PYW = BASE / ".venv" / "Scripts" / "pythonw.exe"


def _q(s):  # escape for a PowerShell single-quoted literal (handles apostrophes)
    return str(s).replace("'", "''")


def main():
    desktop = Path(os.path.expanduser("~/Desktop"))
    lnk = desktop / "VoiceClaw.lnk"
    ps = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{lnk}');"
        "$s.TargetPath='{pyw}';"
        "$s.Arguments='-m voiceclaw.ui';"
        "$s.WorkingDirectory='{wd}';"
        "$s.WindowStyle=1;"
        "$s.Description='VoiceClaw';"
        "$s.Save()"
    ).format(lnk=_q(lnk), pyw=_q(PYW), wd=_q(BASE))
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                   check=True)
    print(f"Created shortcut: {lnk}")


if __name__ == "__main__":
    main()