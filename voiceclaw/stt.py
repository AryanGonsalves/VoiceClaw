# VoiceClaw — Copyright (c) 2026 Aryan Gonsalves. All rights reserved. Proprietary; see LICENSE.
"""Speech-to-text with two routes:

  • Local  : faster-whisper (free/offline). small.en default; GPU auto.
  • Cloud  : route audio to a BIG hosted Whisper via an OpenAI-compatible
             /audio/transcriptions endpoint. Recommended free option: Groq
             (whisper-large-v3). Works with OpenAI / others too.

Pick with config.stt.provider = "local" | "cloud". make_transcriber(cfg) returns
the right backend; both expose .transcribe(samples)->str plus the Unloadable
protocol so the rest of the app doesn't care which is active.
"""
from __future__ import annotations

import io
import os
import time
import wave
from typing import Optional

SAMPLE_RATE = 16000
MIN_SECONDS = 0.35

CONTEXT_PROMPT = (
    "Voice commands for a PC assistant. Likely phrases: open, launch, start, close, "
    "switch tab, new tab, refresh, scroll up, scroll down, next video, previous, "
    "play, pause, stop, volume up, volume down, mute, search for, find, type, "
    "screenshot, shut down, restart. App names: Chrome, Edge, Notepad, Calculator, "
    "File Explorer, Spotify, Discord, Steam, Valorant, YouTube, VS Code, Word, Excel."
)

_HALLUCINATIONS = {
    "", ".", "you", "bye.", "bye", "thank you.", "thank you", "thanks.",
    "thanks for watching!", "thank you for watching!", "please subscribe.",
    "okay.", "ok.", "uh.", "um.", "hmm.", "...",
}


def stt_available() -> bool:
    try:
        import faster_whisper  # noqa: F401
        return True
    except Exception:
        return False


def _to_wav_bytes(samples) -> bytes:
    """float32 mono [-1,1] @16k -> 16-bit PCM WAV bytes."""
    import numpy as np
    pcm = (np.clip(samples, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()
    buf = io.BytesIO()
    w = wave.open(buf, "wb")
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SAMPLE_RATE)
    w.writeframes(pcm)
    w.close()
    return buf.getvalue()


def _clean(text: str) -> str:
    text = (text or "").strip()
    return "" if text.lower() in _HALLUCINATIONS else text


# ---------------------------------------------------------------------------
# Local backend (faster-whisper)
# ---------------------------------------------------------------------------
class Transcriber:
    def __init__(self, model: str = "small.en", language: str = "en",
                 device: str = "auto", compute_type: str = "auto",
                 context_prompt: str = ""):
        self.model_name = model
        self.language = language
        self.device = device
        self.compute_type = compute_type
        self.context_prompt = context_prompt or CONTEXT_PROMPT
        self._model = None
        self.last_used = time.time()

    def is_loaded(self) -> bool:
        return self._model is not None

    def unload(self) -> None:
        self._model = None

    def _resolve(self):
        # IMPORTANT: a present NVIDIA GPU does NOT mean the CUDA runtime
        # (cuBLAS/cuDNN) is installed. Auto -> CPU (always works). Only use CUDA
        # when the user explicitly sets device: cuda (and has the CUDA libs).
        dev = (self.device or "cpu").lower()
        ct = self.compute_type if self.compute_type not in ("", "auto") else None
        if dev == "cuda":
            return "cuda", (ct or "float16")
        return "cpu", (ct or "int8")

    def _ensure(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            dev, ctype = self._resolve()
            try:
                self._model = WhisperModel(self.model_name, device=dev, compute_type=ctype)
            except Exception:
                self._model = WhisperModel(self.model_name, device="cpu", compute_type="int8")
        return self._model

    def transcribe(self, samples) -> str:
        if samples is None or len(samples) < int(MIN_SECONDS * SAMPLE_RATE):
            return ""
        self.last_used = time.time()
        model = self._ensure()
        lang = "en" if self.model_name.endswith(".en") else self.language
        segments, _ = model.transcribe(
            samples, language=lang, beam_size=5, temperature=0.0,
            condition_on_previous_text=False, no_speech_threshold=0.6,
            vad_filter=True, vad_parameters=dict(min_silence_duration_ms=300),
            initial_prompt=self.context_prompt,
        )
        parts = []
        for seg in segments:
            if getattr(seg, "no_speech_prob", 0.0) > 0.6:
                continue
            if getattr(seg, "avg_logprob", 0.0) < -1.0:
                continue
            parts.append(seg.text.strip())
        self.last_used = time.time()
        return _clean(" ".join(parts))


# ---------------------------------------------------------------------------
# Cloud backend (OpenAI-compatible /audio/transcriptions; Groq/OpenAI/etc.)
# ---------------------------------------------------------------------------
class CloudTranscriber:
    def __init__(self, base_url: str, model: str, api_key: str,
                 language: str = "en", context_prompt: str = ""):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.language = language
        self.context_prompt = context_prompt or CONTEXT_PROMPT
        self.last_used = time.time()

    # Unloadable protocol (nothing to load/unload for a cloud backend)
    def is_loaded(self) -> bool:
        return False

    def unload(self) -> None:
        pass

    def transcribe(self, samples) -> str:
        if samples is None or len(samples) < int(MIN_SECONDS * SAMPLE_RATE):
            return ""
        self.last_used = time.time()
        try:
            import requests
            wav = _to_wav_bytes(samples)
            r = requests.post(
                f"{self.base_url}/audio/transcriptions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                files={"file": ("audio.wav", wav, "audio/wav")},
                data={"model": self.model, "language": self.language,
                      "temperature": "0", "prompt": self.context_prompt},
                timeout=30,
            )
            if r.status_code != 200:
                from .issues import log_issue
                log_issue("stt.cloud", f"HTTP {r.status_code}: {r.text[:200]}")
                return ""
            return _clean(r.json().get("text", ""))
        except Exception as e:
            try:
                from .issues import log_issue
                log_issue("stt.cloud", e)
            except Exception:
                pass
            return ""


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def make_transcriber(cfg):
    s = cfg["stt"]
    provider = (s.get("provider") or "local").lower()
    if provider in ("cloud", "groq", "openai", "openai_compatible"):
        c = s.get("cloud", {}) or {}
        key = (os.environ.get(c.get("api_key_env", "GROQ_API_KEY"))
               or c.get("api_key") or "")
        if not key:
            try:
                from . import credentials_store as store
                key = store.load("stt_key") or ""
            except Exception:
                key = ""
        if key:
            return CloudTranscriber(
                base_url=c.get("base_url", "https://api.groq.com/openai/v1"),
                model=c.get("model", "whisper-large-v3"),
                api_key=key, language=s.get("language", "en"),
                context_prompt=s.get("context_prompt", ""),
            )
        # No key -> fall back to local so the app still works.
    return Transcriber(
        s.get("model", "small.en"), s.get("language", "en"),
        device=s.get("device", "auto"), compute_type=s.get("compute_type", "auto"),
        context_prompt=s.get("context_prompt", ""),
    )