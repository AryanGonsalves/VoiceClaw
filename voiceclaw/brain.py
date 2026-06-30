# VoiceClaw — Copyright (c) 2026 Aryan Gonsalves. All rights reserved. Proprietary; see LICENSE.
"""Claude API agent: a tool-use loop that can act on the PC, including vision-based
computer use (screenshot -> see -> click)."""
from __future__ import annotations

from typing import Callable, Dict, List, Optional

from .tools import TOOL_SCHEMAS, Toolbox

SYSTEM_PROMPT = (
    "You are VoiceClaw, a voice-operated assistant on the user's computer. You can "
    "control the PC through tools: open/close apps, run shell commands, read/write "
    "files, automate the keyboard, scroll, search/fetch the web, and CONTROL THE GUI "
    "BY SIGHT.\n\n"
    "Computer use: to click on-screen elements (buttons, links, video thumbnails, "
    "menu items like 'Shorts'), first call screenshot to SEE the screen, then call "
    "click/double_click/move_mouse/drag using the pixel coordinates you see in that "
    "screenshot. After acting, take another screenshot to verify, and continue until "
    "the goal is done. Chain steps as needed (e.g. open app -> screenshot -> click).\n\n"
    "Rules:\n"
    "- You are spoken aloud. Keep FINAL answers short and natural. No markdown.\n"
    "- Prefer direct tools (open_app, close_app, open_url) when they suffice; use "
    "  screenshot+click for things only visible on screen.\n"
    "- For destructive/irreversible actions the tool layer asks the user to confirm.\n"
    "- If genuinely ambiguous, call ask_user for one brief follow-up.\n"
    "- After acting, confirm the result in one or two sentences."
)


class ClaudeBrain:
    def __init__(self, client, model: str, max_tokens: int,
                 toolbox: Toolbox, max_iterations: int = 8):
        self.client = client
        self.model = model
        self.max_tokens = max_tokens
        self.toolbox = toolbox
        self.max_iterations = max_iterations
        self.history: List[Dict] = []

    def handle(self, user_text: str,
               on_status: Optional[Callable[[str], None]] = None) -> str:
        def status(msg: str):
            if on_status:
                on_status(msg)

        self.history.append({"role": "user", "content": user_text})

        for _ in range(self.max_iterations):
            tools = TOOL_SCHEMAS + getattr(self.toolbox, "extra_schemas", [])
            resp = self.client.messages.create(
                model=self.model, max_tokens=self.max_tokens,
                system=SYSTEM_PROMPT, tools=tools, messages=self.history,
            )
            tool_uses = [b for b in resp.content if b.type == "tool_use"]
            text_blocks = [b.text for b in resp.content if b.type == "text"]
            self.history.append({"role": "assistant", "content": resp.content})

            if not tool_uses:
                return " ".join(text_blocks).strip() or "Done."

            tool_results = []
            for tu in tool_uses:
                status(f"running {tu.name}…")
                result = self.toolbox.run(tu.name, tu.input or {})
                # screenshot -> return the image to Claude's vision
                if tu.name == "screenshot" and getattr(self.toolbox,
                                                        "_last_screenshot_b64", None):
                    content = [
                        {"type": "image", "source": {"type": "base64",
                         "media_type": "image/png",
                         "data": self.toolbox._last_screenshot_b64}},
                        {"type": "text", "text": str(result) +
                         " (click using these image pixel coordinates)"},
                    ]
                else:
                    content = str(result)
                tool_results.append({"type": "tool_result",
                                     "tool_use_id": tu.id, "content": content})
            self.history.append({"role": "user", "content": tool_results})

        return "I wasn't able to finish that within my step limit."

    def reset(self) -> None:
        self.history.clear()