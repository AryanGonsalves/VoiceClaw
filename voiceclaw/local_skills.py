# VoiceClaw — Copyright (c) 2026 Aryan Gonsalves. All rights reserved. Proprietary; see LICENSE.
"""Open-core shim. Loads the proprietary Tier-1 grammar from voiceclaw/core if
present (private). In the public build (no core) it falls back to a minimal
matcher that sends every command to the agent — so the app still runs."""
from __future__ import annotations

try:
    from .core.local_skills import LocalSkills, _SITES, ESCALATE  # type: ignore  # noqa
except Exception:  # public build: proprietary core not bundled
    ESCALATE = object()
    _SITES: dict = {}

    class LocalSkills:  # minimal fallback (no built-in grammar)
        def __init__(self, enabled: bool = True):
            self.enabled = enabled
            self.rules = []

        def add_rule(self, pattern, handler) -> None:
            self.rules.append((pattern, handler))

        def handle(self, text, toolbox):
            return None  # nothing matched locally -> escalate to the agent