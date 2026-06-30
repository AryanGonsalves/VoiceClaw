# VoiceClaw — Copyright (c) 2026 Aryan Gonsalves. All rights reserved. Proprietary; see LICENSE.
"""Wake-word detection with two interchangeable engines.

  • openWakeWord (default, free, offline) — built-in models (hey_jarvis, alexa,
    hey_mycroft) or a custom-trained model file. No built-in "claude".
  • Picovoice Porcupine — supports a real custom "Hey Claude" wake word: create a
    "Hey Claude" keyword in the free Picovoice Console, download the .ppn, and
    point config.wakeword.porcupine.keyword_path at it. Needs an access key.

Pick via config.wakeword.engine = "openwakeword" | "porcupine". Both expose
wait_for_wake(interrupt) returning WAKE or INTERRUPT, so the rest of the app
doesn't care which engine is active.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Optional

WAKE = "wake"
INTERRUPT = "interrupt"


# -- availability guards --------------------------------------------------
def openwakeword_available() -> bool:
    try:
        import openwakeword  # noqa: F401
        import sounddevice  # noqa: F401
        import numpy  # noqa: F401
        return True
    except Exception:
        return False


def porcupine_available() -> bool:
    try:
        import pvporcupine  # noqa: F401
        import sounddevice  # noqa: F401
        import numpy  # noqa: F401
        return True
    except Exception:
        return False


def wakeword_available() -> bool:
    """True if ANY wake-word engine can run."""
    return openwakeword_available() or porcupine_available()


def _choose_engine(requested: str, oww_ok: bool, porc_ok: bool) -> Optional[str]:
    """Pure selection logic (unit-testable). Returns the engine to use, or None."""
    requested = (requested or "openwakeword").lower()
    if requested == "porcupine":
        if porc_ok:
            return "porcupine"
        if oww_ok:
            return "openwakeword"   # graceful fallback
        return None
    # default / openwakeword
    if oww_ok:
        return "openwakeword"
    if porc_ok:
        return "porcupine"
    return None


# -- openWakeWord engine --------------------------------------------------
class WakeWordListener:
    def __init__(self, models: Optional[List[str]] = None, threshold: float = 0.5,
                 custom_model_path: str = "", device=None):
        from openwakeword.model import Model
        import sounddevice as sd
        self.sd = sd
        self.threshold = threshold
        load: List[str] = []
        if custom_model_path and Path(custom_model_path).exists():
            load.append(custom_model_path)
        load.extend(models or ["hey_jarvis"])
        # openWakeWord defaults to the tflite runtime, which has no Windows
        # build; force the onnx runtime (we ship onnxruntime). Older versions
        # don't accept the kwarg, so fall back. Also pre-download onnx models.
        try:
            import openwakeword
            try:
                openwakeword.utils.download_models()
            except Exception:
                pass
        except Exception:
            pass

        def _mk(**kw):
            try:
                return Model(inference_framework="onnx", **kw)
            except TypeError:
                return Model(**kw)

        try:
            self.model = _mk(wakeword_models=load)
        except Exception:
            self.model = _mk()
        self.sample_rate = 16000
        self.frame = 1280
        self.device = device

    def wait_for_wake(self, interrupt: Optional[Callable[[], bool]] = None) -> str:
        with self.sd.InputStream(samplerate=self.sample_rate, channels=1,
                                 dtype="int16", blocksize=self.frame,
                                 device=self.device) as stream:
            while True:
                if interrupt is not None and interrupt():
                    return INTERRUPT
                block, _ = stream.read(self.frame)
                scores = self.model.predict(block[:, 0])
                if any(s >= self.threshold for s in scores.values()):
                    try:
                        self.model.reset()
                    except Exception:
                        pass
                    return WAKE


# -- Porcupine engine -----------------------------------------------------
class PorcupineListener:
    def __init__(self, access_key: str, keyword_path: str = "",
                 builtin_keyword: str = "", sensitivity: float = 0.5, device=None):
        import pvporcupine
        import sounddevice as sd
        self.sd = sd
        kwargs = {"access_key": access_key, "sensitivities": [sensitivity]}
        if keyword_path and Path(keyword_path).exists():
            kwargs["keyword_paths"] = [keyword_path]      # custom "Hey Claude"
        else:
            kwargs["keywords"] = [builtin_keyword or "jarvis"]
        self.porcupine = pvporcupine.create(**kwargs)
        self.sample_rate = self.porcupine.sample_rate     # 16000
        self.frame = self.porcupine.frame_length          # 512
        self.device = device

    def wait_for_wake(self, interrupt: Optional[Callable[[], bool]] = None) -> str:
        with self.sd.InputStream(samplerate=self.sample_rate, channels=1,
                                 dtype="int16", blocksize=self.frame,
                                 device=self.device) as stream:
            while True:
                if interrupt is not None and interrupt():
                    return INTERRUPT
                block, _ = stream.read(self.frame)
                if self.porcupine.process(block[:, 0]) >= 0:
                    return WAKE


# -- factory --------------------------------------------------------------
def make_listener(cfg):
    """Build the configured wake-word listener, or None if no engine is available."""
    ww = cfg["wakeword"]
    engine = _choose_engine(ww.get("engine", "openwakeword"),
                            openwakeword_available(), porcupine_available())
    device = cfg.get("audio", {}).get("input_device")
    if engine == "porcupine":
        pc = ww.get("porcupine", {}) or {}
        return PorcupineListener(
            access_key=pc.get("access_key", ""),
            keyword_path=pc.get("keyword_path", ""),
            builtin_keyword=pc.get("builtin_keyword", ""),
            sensitivity=float(pc.get("sensitivity", 0.5)),
            device=device,
        )
    if engine == "openwakeword":
        return WakeWordListener(
            models=cfg.wake_models,
            threshold=ww.get("threshold", 0.5),
            custom_model_path=ww.get("custom_model_path", ""),
            device=device,
        )
    return None