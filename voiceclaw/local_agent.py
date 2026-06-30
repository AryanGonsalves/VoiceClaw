# VoiceClaw — Copyright (c) 2026 Aryan Gonsalves. All rights reserved. Proprietary; see LICENSE.
"""Local 'Cowork-lite' agent: a tool-use loop powered by a local model (Ollama).

Mirrors brain.ClaudeBrain but runs entirely on-device via Ollama's /api/chat
tool-calling. It reasons about a request and calls the SAME Toolbox tools
(open_app, close_app, run_shell, files, web, keyboard, ...), so you get
Cowork-style action routing without hand-coded rules — offline and free.

Caveat: local models (3B-8B) are far less reliable than Claude at multi-step
tool use. Use a tool-capable model (llama3.1, qwen2.5, mistral-nemo, llama3.2).
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional

from .tools import TOOL_SCHEMAS, Toolbox

SYSTEM_PROMPT = (
    "You are VoiceClaw, a voice assistant on the user's PC. Use the provided "
    "tools to actually perform actions (open/close apps, run commands, files, web, "
    "keyboard). Think step by step, call tools as needed, and when done reply in "
    "one short spoken sentence. Do not invent tool names; only use the given tools."
)


def _to_ollama_tools() -> List[Dict]:
    return [
        {"type": "function", "function": {
            "name": t["name"],
            "description": t["description"],
            "parameters": t["input_schema"],
        }}
        for t in TOOL_SCHEMAS
    ]


class LocalBrain:
    def __init__(self, base_url: str, model: str, toolbox: Toolbox,
                 max_iterations: int = 6):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.toolbox = toolbox
        self.max_iterations = max_iterations
        self.history: List[Dict] = []

    def available(self) -> bool:
        try:
            import requests
            r = requests.get(f"{self.base_url}/api/tags", timeout=1.5)
            return r.status_code == 200
        except Exception:
            return False

    def handle(self, user_text: str,
               on_status: Optional[Callable[[str], None]] = None) -> str:
        import requests

        def status(m):
            if on_status:
                on_status(m)

        msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
        msgs += self.history
        msgs.append({"role": "user", "content": user_text})
        tools = _to_ollama_tools()

        for _ in range(self.max_iterations):
            try:
                r = requests.post(
                    f"{self.base_url}/api/chat",
                    json={"model": self.model, "messages": msgs, "tools": tools,
                          "stream": False, "options": {"temperature": 0.0}},
                    timeout=120,
                )
                data = r.json()
            except Exception as e:
                from .issues import log_issue
                log_issue("local_agent", e)
                return "Local agent error. Is Ollama running with a tool-capable model?"

            msg = data.get("message", {}) or {}
            calls = msg.get("tool_calls") or []
            msgs.append(msg)  # keep assistant turn (with any tool_calls) in history

            if not calls:
                self.history = msgs[1:]  # drop system; keep convo
                return (msg.get("content") or "Done.").strip()

            for tc in calls:
                fn = (tc.get("function") or {})
                name = fn.get("name", "")
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    try:
                        import json
                        args = json.loads(args)
                    except Exception:
                        args = {}
                status(f"running {name}…")
                result = self.toolbox.run(name, args or {})
                msgs.append({"role": "tool", "name": name, "content": str(result)})

        return "I couldn't finish that locally within my step limit."

    def reset(self) -> None:
        self.history.clear()