# VoiceClaw — Copyright (c) 2026 Aryan Gonsalves. All rights reserved. Proprietary; see LICENSE.
"""Alexa-style audio ducking: lower OTHER apps' volume while listening, then
restore. Windows via pycaw (per-session volume); no-op elsewhere / if unavailable."""
from __future__ import annotations

import os


def ducking_available() -> bool:
    if os.name != "nt":
        return False
    try:
        import pycaw  # noqa: F401
        import comtypes  # noqa: F401
        return True
    except Exception:
        return False


class AudioDucker:
    def __init__(self, level: float = 0.15):
        self.level = level
        self._saved = []

    def duck(self) -> None:
        """Lower every other app's session volume to `level`, remembering originals."""
        self._saved = []
        try:
            from pycaw.pycaw import AudioUtilities
            mypid = os.getpid()
            for s in AudioUtilities.GetAllSessions():
                try:
                    if s.Process and s.Process.pid != mypid:
                        v = s.SimpleAudioVolume
                        self._saved.append((v, v.GetMasterVolume()))
                        v.SetMasterVolume(self.level, None)
                except Exception:
                    continue
        except Exception:
            pass

    def restore(self) -> None:
        for v, old in self._saved:
            try:
                v.SetMasterVolume(old, None)
            except Exception:
                pass
        self._saved = []