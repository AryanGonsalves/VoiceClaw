# VoiceClaw — Copyright (c) 2026 Aryan Gonsalves. All rights reserved. Proprietary; see LICENSE.
"""Configuration loading with sensible defaults and env-var overrides."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

DEFAULTS: Dict[str, Any] = {
    "brain": {
        "backend": "auto",       # auto | anthropic | openai | claude_code
        "auth": "auto",                 # auto | api_key | subscription
        "anthropic_api_key": "",
        "model": "claude-sonnet-4-6",
        "max_tokens": 2048,
        "openai": {"api_key_env": "OPENAI_API_KEY", "api_key": "",
                   "base_url": "", "model": "gpt-4o-mini"},
    },
    "local_llm": {
        "enabled": True,
        "base_url": "http://localhost:11434",
        "model": "llama3.2:3b",
        "fast_path_max_words": 8,
        "agent": True,          # local Cowork-lite tool-use agent (Ollama)
        "agent_model": "",      # tool-capable model; blank = use 'model' above
    },
    "wakeword": {
        "enabled": True,
        # One or more built-in models; users can enable several and say any.
        # Built-ins: hey_jarvis | alexa | hey_mycroft. For the literal word
        # "claude"/"hey claude", train a model and point custom_model_path at it.
        "engine": "openwakeword",   # openwakeword | porcupine
        "models": ["hey_jarvis"],
        "custom_model_path": "",
        "threshold": 0.5,
        "porcupine": {
            "access_key": "",
            "keyword_path": "",      # path to a "Hey Claude" .ppn for a real wake word
            "builtin_keyword": "",   # e.g. "jarvis" if no custom file
            "sensitivity": 0.5,
        },
    },
    "stt": {"enabled": True, "provider": "local", "model": "small.en",
            "language": "en", "device": "cpu", "compute_type": "auto",
            "context_prompt": "",
            "cloud": {"base_url": "https://api.groq.com/openai/v1",
                      "model": "whisper-large-v3",
                      "api_key_env": "GROQ_API_KEY", "api_key": ""}},
    "audio": {"input_device": None, "duck": True, "duck_level": 0.15},
    "tts": {"enabled": True, "rate": 185, "voice": ""},
    "hotkeys": {
        "enabled": True,
        "push_to_talk": "<ctrl>+<alt>+space",
        "kill_switch": "<ctrl>+<alt>+q",
        "dictation_ptt": "<ctrl_r>",      # hold to dictate into the focused window
        "dictation_ptt_send": True,       # press Enter after typing (send the message)
    },
    "agent": {
        "max_tool_iterations": 8,
        "confirm_patterns": ["rm ", "del ", "format", "shutdown", "rmdir",
                             "mkfs", "dd ", "> /dev"],
        "allowed_paths": [],
    },
    "ui": {"ring": True, "ring_thickness": 7},
    "runtime": {
        "idle_unload_seconds": 300,
        "log_transcript": True,
        "transcript_path": "~/.voiceclaw/transcript.log",
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


@dataclass
class Config:
    data: Dict[str, Any] = field(default_factory=lambda: dict(DEFAULTS))

    @classmethod
    def load(cls, path: str | None = None) -> "Config":
        data = dict(DEFAULTS)
        candidates = [path] if path else ["config.yaml", "config.example.yaml"]
        for c in candidates:
            if c and Path(c).exists() and yaml is not None:
                with open(c, "r", encoding="utf-8") as f:
                    loaded = yaml.safe_load(f) or {}
                data = _deep_merge(data, loaded)
                break
        cfg = cls(data)
        cfg._apply_env()
        return cfg

    def _apply_env(self) -> None:
        # NOTE: We deliberately do NOT copy ANTHROPIC_API_KEY into
        # self.data["brain"]["anthropic_api_key"] here. self.data is dumped back
        # to config.yaml by the UI (see ui.py save handlers), so baking a real
        # env-provided key into it would persist the secret to disk in plaintext.
        # The env var is resolved at read time by the `anthropic_key` property
        # (and by auth._api_key, which checks the env var first).
        if os.environ.get("VOICECLAUDE_MODEL"):
            self.data["brain"]["model"] = os.environ["VOICECLAUDE_MODEL"]
        if os.environ.get("VOICECLAUDE_AUTH"):
            self.data["brain"]["auth"] = os.environ["VOICECLAUDE_AUTH"]

    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    @property
    def anthropic_key(self) -> str:
        # Prefer the env var (resolved at access time so it is never persisted
        # into self.data / dumped to config.yaml), else the config-file value.
        return os.environ.get("ANTHROPIC_API_KEY") \
            or self.data["brain"].get("anthropic_api_key", "")

    @property
    def wake_models(self) -> List[str]:
        ww = self.data["wakeword"]
        if ww.get("models"):
            return list(ww["models"])
        return [ww.get("model", "hey_jarvis")]  # back-compat with single "model"

    @property
    def allowed_paths(self) -> List[Path]:
        roots = self.data["agent"].get("allowed_paths") or []
        if not roots:
            return [Path.home()]
        return [Path(os.path.expanduser(r)).resolve() for r in roots]
