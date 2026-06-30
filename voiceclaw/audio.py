# VoiceClaw — Copyright (c) 2026 Aryan Gonsalves. All rights reserved. Proprietary; see LICENSE.
"""Microphone capture with robust endpointing.

All audio stays on-device. The recorder keeps every frame from the moment it
opens (so a command spoken immediately after the wake chime is never lost) and
uses a light energy heuristic only to decide WHEN to stop. Whisper's own VAD then
trims silence. If audio libs are unavailable, callers fall back to text input.
"""
from __future__ import annotations

import time

SAMPLE_RATE = 16000
FRAME_MS = 80
FRAME_SAMPLES = SAMPLE_RATE * FRAME_MS // 1000


def _safe_call(fn):
    try:
        return bool(fn())
    except Exception:
        return False


def list_input_devices():
    """Return [(index, name)] of input-capable audio devices, or [] if unavailable."""
    try:
        import sounddevice as sd
        devs = sd.query_devices()
        return [(i, d["name"]) for i, d in enumerate(devs)
                if d.get("max_input_channels", 0) > 0]
    except Exception:
        return []


def audio_available() -> bool:
    try:
        import sounddevice  # noqa: F401
        import numpy  # noqa: F401
        return True
    except Exception:
        return False


class Microphone:
    def __init__(self, sample_rate: int = SAMPLE_RATE, device=None):
        import sounddevice as sd
        import numpy as np
        self.sd = sd
        self.np = np
        self.sample_rate = sample_rate
        self.device = device

    def record_until_silence(self, max_seconds: float = 8.0,
                             silence_seconds: float = 1.2,
                             start_timeout: float = 7.0):
        """Record from the mic and return float32 mono samples. Captures ALL
        audio from the start; stops after trailing silence once speech is seen,
        or at max_seconds. Returns whatever was captured (Whisper trims silence)."""
        np = self.np
        frames = []
        started = False
        silence_run = 0.0
        calib = []
        thresh = 0.015            # sane default until calibrated
        t0 = time.time()

        with self.sd.InputStream(
            samplerate=self.sample_rate, channels=1, dtype="float32",
            blocksize=FRAME_SAMPLES, device=self.device,
        ) as stream:
            while True:
                block, _ = stream.read(FRAME_SAMPLES)
                mono = block[:, 0]
                frames.append(mono.copy())          # always keep the audio
                energy = float(np.sqrt(np.mean(mono ** 2)) + 1e-9)

                # Calibrate ambient level from the first ~0.24s ONLY.
                if len(calib) < 3:
                    calib.append(energy)
                    if len(calib) == 3:
                        thresh = max(float(np.mean(calib)) * 2.5, 0.015)
                else:
                    if energy > thresh:
                        started = True
                        silence_run = 0.0
                    elif started:
                        silence_run += FRAME_MS / 1000.0

                elapsed = time.time() - t0
                if started and silence_run >= silence_seconds:
                    break
                if elapsed >= max_seconds:
                    break
                if not started and elapsed >= start_timeout:
                    break

        if not frames:
            return np.zeros(0, dtype="float32")
        return np.concatenate(frames).astype("float32")

    def record_while_held(self, is_held, max_seconds: float = 30.0,
                          min_seconds: float = 0.3):
        """Hold-to-talk: record from the mic for as long as is_held() returns True
        (with a short minimum so a quick tap still captures), capped at max_seconds.
        Returns float32 mono samples."""
        np = self.np
        frames = []
        t0 = time.time()
        with self.sd.InputStream(
            samplerate=self.sample_rate, channels=1, dtype="float32",
            blocksize=FRAME_SAMPLES, device=self.device,
        ) as stream:
            while True:
                block, _ = stream.read(FRAME_SAMPLES)
                frames.append(block[:, 0].copy())
                elapsed = time.time() - t0
                if elapsed >= max_seconds:
                    break
                if elapsed >= min_seconds and not _safe_call(is_held):
                    break
        if not frames:
            return np.zeros(0, dtype="float32")
        return np.concatenate(frames).astype("float32")

    def chime(self, kind: str = "wake") -> None:
        """Play a short tone so the user knows we're listening.
        Prefer winsound on Windows (very reliable); fall back to sounddevice."""
        freq = 880 if kind == "wake" else 440
        try:
            import winsound
            winsound.Beep(freq, 130)
            return
        except Exception:
            pass
        try:
            np = self.np
            dur = 0.13
            t = np.linspace(0, dur, int(self.sample_rate * dur), False)
            tone = (0.2 * np.sin(2 * np.pi * freq * t)).astype("float32")
            self.sd.play(tone, self.sample_rate)
            self.sd.wait()
        except Exception:
            pass