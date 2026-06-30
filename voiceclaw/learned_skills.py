# VoiceClaw — Copyright (c) 2026 Aryan Gonsalves. All rights reserved. Proprietary; see LICENSE.
"""Open-core shim for the learned-command cache. Loads the proprietary core if
present; otherwise a no-op cache (public build learns nothing locally)."""
from __future__ import annotations

try:
    from .core.learned_skills import (  # type: ignore  # noqa
        LearnedSkills, normalize, LEARNABLE_TOOLS)
except Exception:  # public build
    import re

    LEARNABLE_TOOLS = {"open_url", "open_app", "close_app", "press_keys", "scroll"}

    def normalize(text: str) -> str:
        t = (text or "").lower().strip()
        t = re.sub(r"[^a-z0-9 ]+", " ", t)
        return re.sub(r"\s+", " ", t).strip()

    class LearnedSkills:  # no-op fallback
        def __init__(self, path=None, enabled: bool = True, fuzzy: float = 0.92):
            self.enabled = enabled; self.data = {}
        @staticmethod
        def is_learnable(actions): return False
        def record(self, *a, **k): return False
        def lookup(self, *a, **k): return None
        def peek(self, *a, **k): return None
        def items(self): return []
        def delete(self, *a, **k): return False
        def clear(self): self.data = {}
        def count(self): return 0