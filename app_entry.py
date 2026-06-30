# VoiceClaw — Copyright (c) 2026 Aryan Gonsalves. All rights reserved. Proprietary; see LICENSE.
#!/usr/bin/env python3
"""Single windowed entry point for the packaged app (VoiceClaw.exe).

Opens the companion desktop UI; from there the user can sign in, change settings,
and Start/Stop listening. Falls back to the tray, then the CLI, if the UI deps
are missing — so the .exe always does *something* useful.
"""
import sys


def main():
    try:
        from voiceclaw.ui import main as ui_main, ui_available
        if ui_available():
            return ui_main()
    except Exception:
        pass
    try:
        from voiceclaw.tray import main as tray_main
        return tray_main()
    except Exception:
        pass
    import main as cli
    return cli.main()


if __name__ == "__main__":
    sys.exit(main())