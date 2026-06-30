# VoiceClaw — Copyright (c) 2026 Aryan Gonsalves. All rights reserved. Proprietary; see LICENSE.
"""OpenAI-compatible agent backend (OpenAI, Groq, OpenRouter, local servers).

Runs the SAME tool-use loop as the Claude brain over the OpenAI Chat Completions
API, so a user can bring an OpenAI/Groq/OpenRouter key. Vision (screenshot->click)
works with vision-capable models (e.g. gpt-4o). The "agentic" behavior is our loop
+ tools — the model only needs function-calling (+ vision for clicking).

Grounding strategy ("contexting"):
  * Observe BEFORE acting: a screenshot of the current screen is attached to the
    first message, so the model reuses what's already open instead of duplicating.
  * Observe AFTER acting: navigation / click / search tools auto-attach a fresh
    screenshot, so the model verifies the real result before its next move.
  * Only the LATEST screenshot is kept in context (older ones are pruned to a text
    placeholder) — stale views are what cause acting on the wrong screen, and this
    keeps the request fast and cheap.
"""
from __future__ import annotations

import json
import time
from typing import Callable, Dict, List, Optional

from .tools import TOOL_SCHEMAS, Toolbox

SYSTEM_PROMPT = (
    "You are VoiceClaw, a voice-operated assistant on the user's computer. Use the "
    "provided tools to take real actions: open/close apps, run shell, files, web, and "
    "GUI control.\n"
    "GROUNDING RULES — follow these every time:\n"
    "1. LOOK FIRST. A screenshot of the current screen is given to you. Read it before "
    "acting. If the app, website, or browser tab you need is ALREADY open or visible, "
    "switch to it (click its tab/window, or use the taskbar) instead of opening a new "
    "instance. Never open a duplicate of something already open.\n"
    "2. VERIFY BEFORE YOU CLICK. After you open a URL, launch an app, type, or submit a "
    "search, a fresh screenshot is given to you automatically. Confirm the page actually "
    "loaded and the content matches the request before clicking anything. If it's still "
    "loading or blank, wait and screenshot again.\n"
    "3. MATCH THE REQUEST. When asked for 'the first result about X', READ the on-screen "
    "titles and click a result that genuinely matches X — not just the first thing you "
    "see (ads, unrelated suggestions, or a leftover video from a previous search).\n"
    "4. Click using the exact pixel coordinates visible in the most recent screenshot. "
    "If you're unsure what's under a spot, screenshot again rather than guessing.\n"
    "5. RESOLVE ROUTINE SCREENS YOURSELF. If you hit a profile picker, a cookie/consent "
    "banner, a 'Continue'/'Got it'/'No thanks' dialog, or a sign-in-later prompt, click "
    "the obvious default (e.g. the first profile, Accept/Continue) and keep going. Do NOT "
    "stop to ask the user about routine UI — only ask if you are genuinely stuck.\n"
    "6. To open a website, prefer the open_url tool (e.g. open_url to youtube.com or "
    "directly to its search URL) rather than launching the browser app, which may show a "
    "profile picker.\n"
    "7. DEVICE CONTROL from natural speech: for media playback, volume, scrolling, and "
    "tab/window actions, use press_keys with the documented keys -- 'nexttrack' for "
    "\"play the next song\", 'prevtrack' for \"go back a song\", 'volumedown' for "
    "\"turn it down\", 'playpause', 'ctrl+w' to close a tab. No need to find on-screen "
    "buttons for these.\n"
    "You are spoken aloud: keep final answers short and natural, no markdown. Take action "
    "with tools rather than describing what you would do."
)

# Tools whose effect changes the screen — auto-capture a fresh screenshot afterwards
# so the model always reasons about the real resulting state.
_AUTO_CAPTURE = {
    "open_url", "open_app", "click", "double_click", "press_keys",
    "type_text", "scroll", "move_mouse", "drag",
}
# Longer settle time for actions that trigger navigation / page loads.
_SLOW = {"open_url", "open_app", "press_keys"}


def _to_openai_tools(extra: List[Dict]) -> List[Dict]:
    return [
        {"type": "function", "function": {
            "name": t["name"], "description": t["description"],
            "parameters": t["input_schema"],
        }}
        for t in (TOOL_SCHEMAS + (extra or []))
    ]


def _image_block(b64: str) -> Dict:
    return {"type": "image_url", "image_url": {
        "url": "data:image/png;base64," + b64, "detail": "high"}}


def _prune_old_images(msgs: List[Dict]) -> None:
    """Keep only the most recent screenshot in context; replace earlier image
    messages with a short text placeholder so the model never acts on a stale view
    (and the request stays small/fast)."""
    img_idxs = [
        i for i, mm in enumerate(msgs)
        if isinstance(mm.get("content"), list)
        and any(isinstance(p, dict) and p.get("type") == "image_url"
                for p in mm["content"])
    ]
    for i in img_idxs[:-1]:  # all but the last
        msgs[i]["content"] = "[earlier screenshot omitted — see the latest one]"


class OpenAIBrain:
    def __init__(self, api_key: str, model: str, toolbox: Toolbox,
                 base_url: str = "", max_iterations: int = 20):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key, base_url=base_url or None,
                             max_retries=4)
        self.model = model
        self.toolbox = toolbox
        self.max_iterations = max_iterations
        self.history: List[Dict] = []

    def _grab(self) -> Optional[str]:
        """Take a screenshot via the toolbox and return its base64 (or None)."""
        try:
            self.toolbox.run("screenshot", {})
            return getattr(self.toolbox, "_last_screenshot_b64", None)
        except Exception:
            return None

    def handle(self, user_text: str,
               on_status: Optional[Callable[[str], None]] = None) -> str:
        def status(m):
            if on_status:
                on_status(m)

        self.last_trace = []  # model-issued (tool, args) calls, for learning
        msgs: List[Dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
        msgs += self.history

        # OBSERVE FIRST: attach the current screen to the opening message.
        start_b64 = self._grab()
        if start_b64:
            msgs.append({"role": "user", "content": [
                {"type": "text", "text": user_text
                 + "\n\n[Current screen — reuse anything already open; "
                   "do not open duplicates.]"},
                _image_block(start_b64),
            ]})
        else:
            msgs.append({"role": "user", "content": user_text})

        tools = _to_openai_tools(getattr(self.toolbox, "extra_schemas", []))

        for _ in range(self.max_iterations):
            _prune_old_images(msgs)
            resp = self.client.chat.completions.create(
                model=self.model, messages=msgs, tools=tools,
                tool_choice="auto", temperature=0,
            )
            m = resp.choices[0].message
            assistant = {"role": "assistant", "content": m.content or ""}
            if m.tool_calls:
                assistant["tool_calls"] = [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name,
                                  "arguments": tc.function.arguments}}
                    for tc in m.tool_calls
                ]
            msgs.append(assistant)

            if not m.tool_calls:
                self.history = msgs[1:]
                return (m.content or "Done.").strip()

            pending_capture = False
            for tc in m.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except Exception:
                    args = {}
                self.last_trace.append((name, args))
                status(f"running {name}…")
                result = self.toolbox.run(name, args)
                msgs.append({"role": "tool", "tool_call_id": tc.id,
                             "content": str(result)})

                if name == "screenshot" and getattr(
                        self.toolbox, "_last_screenshot_b64", None):
                    msgs.append({"role": "user", "content": [
                        _image_block(self.toolbox._last_screenshot_b64),
                        {"type": "text", "text":
                         "Latest screen. Verify it matches the request, then act."},
                    ]})
                elif name in _AUTO_CAPTURE:
                    pending_capture = name

            # After this turn's actions, observe the resulting screen once.
            if pending_capture:
                time.sleep(1.4 if pending_capture in _SLOW else 0.6)
                b64 = self._grab()
                if b64:
                    msgs.append({"role": "user", "content": [
                        _image_block(b64),
                        {"type": "text", "text":
                         "Resulting screen after your action. Verify it worked and "
                         "matches the request before your next step."},
                    ]})

        self.history = msgs[1:]
        return "I couldn't finish that within my step limit."

    def reset(self) -> None:
        self.history.clear()