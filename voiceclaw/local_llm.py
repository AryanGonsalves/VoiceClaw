# VoiceClaw — Copyright (c) 2026 Aryan Gonsalves. All rights reserved. Proprietary; see LICENSE.
"""Local LLM via Ollama (HTTP). Fast path for simple/offline requests."""
from __future__ import annotations

from typing import Optional


class LocalLLM:
    def __init__(self, base_url: str = "http://localhost:11434",
                 model: str = "llama3.2:3b"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def available(self) -> bool:
        try:
            import requests
            r = requests.get(f"{self.base_url}/api/tags", timeout=1.5)
            return r.status_code == 200
        except Exception:
            return False

    def ask(self, prompt: str, system: str = "", timeout: int = 30) -> Optional[str]:
        """Return a short answer, or None if the model can't/shouldn't answer."""
        try:
            import requests
            r = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "system": system or (
                        "You are a concise local voice assistant. Answer in one "
                        "or two short sentences. If the request needs tools, web "
                        "access, files, or multi-step work, reply exactly: ESCALATE"
                    ),
                    "stream": False,
                    "options": {"num_predict": 120, "temperature": 0.3},
                },
                timeout=timeout,
            )
            text = (r.json().get("response") or "").strip()
            if not text or "ESCALATE" in text.upper():
                return None
            return text
        except Exception:
            return None