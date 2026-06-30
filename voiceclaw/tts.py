# VoiceClaw — Copyright (c) 2026 Aryan Gonsalves. All rights reserved. Proprietary; see LICENSE.
"""Offline text-to-speech via pyttsx3. Lightweight, zero network."""
from __future__ import annotations


def tts_available() -> bool:
    try:
        import pyttsx3  # noqa: F401
        return True
    except Exception:
        return False


class Speaker:
    def __init__(self, rate: int = 185, voice: str = ""):
        import pyttsx3
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", rate)
        if voice:
            for v in self.engine.getProperty("voices"):
                if voice.lower() in (v.name or "").lower():
                    self.engine.setProperty("voice", v.id)
                    break

    def say(self, text: str) -> None:
        if not text:
            return
        import re
        # Speak sentence-by-sentence so long replies start immediately (streaming).
        for chunk in re.split(r"(?<=[.!?])\s+", text.strip()):
            chunk = chunk.strip()
            if chunk:
                self.engine.say(chunk)
                self.engine.runAndWait()


class PrintSpeaker:
    """Fallback 'speaker' that prints when TTS is unavailable."""

    def say(self, text: str) -> None:
        if text:
            print(f"\n[VoiceClaw] {text}\n")