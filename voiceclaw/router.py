# VoiceClaw — Copyright (c) 2026 Aryan Gonsalves. All rights reserved. Proprietary; see LICENSE.
"""Hybrid router: decide whether a request goes to the local model or Claude.

Conservative by design — when in doubt, escalate to Claude, because a wrong
cheap answer is worse than a slightly slower good one.
"""
from __future__ import annotations

import re

# Words that almost always imply tools / actions / multi-step work -> Claude.
ACTION_HINTS = re.compile(
    r"\b(open|launch|run|close|type|click|press|search|find|file|files|folder|"
    r"download|install|email|send|write|create|delete|move|rename|browse|"
    r"website|web|google|look up|schedule|remind|play|screenshot|volume|"
    r"shutdown|restart|code|fix|build|summari|translate|calculate|read)\b",
    re.I,
)


class Router:
    def __init__(self, local_llm, fast_path_max_words: int = 8,
                 local_enabled: bool = True):
        self.local = local_llm
        self.fast_path_max_words = fast_path_max_words
        self.local_enabled = local_enabled

    def try_local(self, text: str):
        """Return a local answer string if appropriate, else None (escalate)."""
        if not self.local_enabled or self.local is None:
            return None
        words = text.split()
        # Long or action-y requests always go to Claude.
        if len(words) > self.fast_path_max_words:
            return None
        if ACTION_HINTS.search(text):
            return None
        if not self.local.available():
            return None
        return self.local.ask(text)