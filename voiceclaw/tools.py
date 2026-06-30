# VoiceClaw — Copyright (c) 2026 Aryan Gonsalves. All rights reserved. Proprietary; see LICENSE.
"""Cross-platform PC-control tools exposed to the Claude agent.

Each tool has (1) an Anthropic tool schema and (2) a Python implementation.
This is the same tool abstraction a Cowork-style agent uses, so the voice
front-end inherits real capabilities: apps, files, shell, web, GUI, system.

Safety: destructive shell commands and out-of-scope file paths are gated by a
confirmation callback supplied by the host application.
"""
from __future__ import annotations

import glob
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, List

OS = platform.system()  # "Windows" | "Darwin" | "Linux"


TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "name": "run_shell",
        "description": "Run a shell command on the user's computer and return "
                       "stdout/stderr. Use for tasks not covered by other tools. "
                       "Destructive commands require user confirmation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The command to run."},
                "timeout": {"type": "integer", "description": "Seconds (default 30)."},
            },
            "required": ["command"],
        },
    },
    {
        "name": "open_app",
        "description": "Launch an application by name (e.g. 'notepad', 'Safari', "
                       "'chrome', 'Calculator').",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "close_app",
        "description": "Close/quit a running application by name (e.g. 'notepad', "
                       "'chrome'), regardless of which window is focused.",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "list_files",
        "description": "List files and folders in a directory.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Defaults to home."}},
            "required": [],
        },
    },
    {
        "name": "search_files",
        "description": "Search for files by name or glob pattern under a root.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "e.g. '*.pdf'"},
                "root": {"type": "string", "description": "Defaults to home."},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "read_file",
        "description": "Read a text file's contents (first ~20k chars).",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Create or overwrite a text file. Requires confirmation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "type_text",
        "description": "Type text into the currently focused window (GUI automation).",
        "input_schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "press_keys",
        "description": (
            "Press a keyboard shortcut or media/system key. Combine with '+'. "
            "MEDIA: 'playpause', 'nexttrack' (next song), 'prevtrack' (previous song), "
            "'volumeup', 'volumedown', 'volumemute'. "
            "NAVIGATION: 'down'/'up' (next/previous YouTube Short or feed item), "
            "'pagedown', 'pageup', 'home' (top of page), 'end' (bottom), "
            "'f5' (reload), 'f' (fullscreen). "
            "TABS/WINDOWS: 'ctrl+w' (close tab), 'ctrl+t' (new tab), "
            "'ctrl+tab' (switch tab), 'ctrl+shift+w' (close all tabs in window), "
            "'alt+f4' (close window). "
            "Prefer this for media, volume, scrolling and tab/window control instead "
            "of hunting for on-screen buttons."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"keys": {"type": "string"}},
            "required": ["keys"],
        },
    },
    {
        "name": "scroll",
        "description": "Scroll the active window up or down by an amount.",
        "input_schema": {
            "type": "object",
            "properties": {
                "direction": {"type": "string", "enum": ["up", "down"]},
                "amount": {"type": "integer", "description": "Clicks (default 5)."},
            },
            "required": ["direction"],
        },
    },
    {
        "name": "screenshot",
        "description": "Take a screenshot to SEE the screen before clicking on-screen "
                       "elements. Returns an image; use the pixel coordinates you see "
                       "in it for click/double_click/move_mouse/drag.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "click",
        "description": "Left-click at (x, y) pixel coordinates from the most recent screenshot.",
        "input_schema": {"type": "object",
                         "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}},
                         "required": ["x", "y"]},
    },
    {
        "name": "double_click",
        "description": "Double-click at (x, y) from the most recent screenshot.",
        "input_schema": {"type": "object",
                         "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}},
                         "required": ["x", "y"]},
    },
    {
        "name": "move_mouse",
        "description": "Move the mouse to (x, y) from the most recent screenshot.",
        "input_schema": {"type": "object",
                         "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}},
                         "required": ["x", "y"]},
    },
    {
        "name": "drag",
        "description": "Drag from the current mouse position to (x, y) from the screenshot.",
        "input_schema": {"type": "object",
                         "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}},
                         "required": ["x", "y"]},
    },
    {
        "name": "system_info",
        "description": "Get system info: OS, CPU/RAM usage, battery, running app count.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "ask_user",
        "description": "Ask the user a brief clarifying question when a request is "
                       "ambiguous, and get their answer. Prefer this over guessing. "
                       "Optionally provide a few choices.",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "options": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["question"],
        },
    },
    {
        "name": "open_url",
        "description": "Open a URL (or a web search) in the default browser.",
        "input_schema": {"type": "object",
                          "properties": {"url": {"type": "string"}},
                          "required": ["url"]},
    },
    {
        "name": "web_search",
        "description": "Search the web and return top result snippets.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "fetch_url",
        "description": "Fetch the text content of a web page.",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
]


class Toolbox:
    def __init__(
        self,
        allowed_paths: List[Path],
        confirm_patterns: List[str],
        confirm_cb: Callable[[str], bool],
        speak_cb: Callable[[str], None] = None,
    ):
        self.allowed_paths = [Path(p) for p in allowed_paths] or [Path.home()]
        self.confirm_patterns = confirm_patterns
        self.confirm_cb = confirm_cb  # returns True if the user approves
        self.speak_cb = speak_cb     # optional: speak a question aloud
        self.extra_tools = {}        # name -> impl(args, toolbox)  (from plugins)
        self.extra_schemas = []      # Anthropic schemas for plugin tools

    # -- helpers ----------------------------------------------------------
    def _expand(self, p: str) -> Path:
        return Path(os.path.expanduser(p)).resolve()

    def _path_allowed(self, p: Path) -> bool:
        for root in self.allowed_paths:
            try:
                p.relative_to(root.resolve())
                return True
            except ValueError:
                continue
        return False

    def _needs_confirm(self, command: str) -> bool:
        low = command.lower()
        return any(pat.strip() and pat.lower() in low for pat in self.confirm_patterns)

    def register_tool(self, schema: Dict[str, Any], impl) -> None:
        """Register a plugin-provided tool (schema + impl(args, toolbox))."""
        self.extra_schemas.append(schema)
        self.extra_tools[schema["name"]] = impl

    # -- dispatch ---------------------------------------------------------
    def run(self, name: str, args: Dict[str, Any]) -> str:
        fn = getattr(self, f"_tool_{name}", None)
        if fn is None:
            impl = self.extra_tools.get(name)
            if impl is None:
                return f"ERROR: unknown tool '{name}'"
            try:
                return impl(args, self)
            except Exception as e:
                try:
                    from .issues import log_issue
                    log_issue(f"tool:{name}", e)
                except Exception:
                    pass
                return f"ERROR running {name}: {e}"
        try:
            return fn(args)
        except Exception as e:  # surface errors to the model, don't crash
            try:
                from .issues import log_issue
                log_issue(f"tool:{name}", e)
            except Exception:
                pass
            return f"ERROR running {name}: {e}"

    # -- tool implementations --------------------------------------------
    def _tool_run_shell(self, a: Dict[str, Any]) -> str:
        cmd = a["command"]
        if self._needs_confirm(cmd) and not self.confirm_cb(
            f"Run potentially destructive command: {cmd}"
        ):
            return "User declined the command."
        timeout = int(a.get("timeout", 30))
        proc = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        return (out[:8000] or "(no output)") + (
            f"\n[exit {proc.returncode}]" if proc.returncode else ""
        )

    def _tool_open_app(self, a: Dict[str, Any]) -> str:
        name = a["name"]
        if OS == "Windows":
            if os.path.exists(name):
                os.startfile(name)  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["cmd", "/c", "start", "", name], shell=False)
        elif OS == "Darwin":
            subprocess.Popen(["open", "-a", name])
        else:
            subprocess.Popen([name])
        return f"Launched {name}."

    # Friendly name -> actual process/exe (Windows). Extend as needed.
    _APP_ALIASES = {
        "google": "chrome", "google chrome": "chrome", "chrome": "chrome",
        "edge": "msedge", "microsoft edge": "msedge", "explorer": "explorer",
        "file explorer": "explorer", "vs code": "Code", "vscode": "Code",
        "code": "Code", "discord": "Discord", "spotify": "Spotify",
        "steam": "steam", "word": "WINWORD", "excel": "EXCEL",
        "notepad": "notepad", "calculator": "CalculatorApp",
    }

    def _tool_close_app(self, a: Dict[str, Any]) -> str:
        name = a["name"].strip()
        if OS == "Windows":
            base = self._APP_ALIASES.get(name.lower(), name)
            exe = base if base.lower().endswith(".exe") else base + ".exe"
            r = subprocess.run(["taskkill", "/IM", exe, "/F"],
                               capture_output=True, text=True)
            if r.returncode != 0:
                return f"Couldn't close {name}: {(r.stderr or r.stdout).strip()[:120]}"
            return f"Closed {name}."
        else:
            subprocess.run(["pkill", "-i", name], capture_output=True, text=True)
            return f"Closed {name}."

    def _tool_list_files(self, a: Dict[str, Any]) -> str:
        p = self._expand(a.get("path") or str(Path.home()))
        if not self._path_allowed(p):
            return f"Path not allowed: {p}"
        items = sorted(os.listdir(p))
        tagged = [f"{'[dir] ' if (p / i).is_dir() else '      '}{i}" for i in items]
        return "\n".join(tagged[:200]) or "(empty)"

    def _tool_search_files(self, a: Dict[str, Any]) -> str:
        root = self._expand(a.get("root") or str(Path.home()))
        if not self._path_allowed(root):
            return f"Path not allowed: {root}"
        hits = glob.glob(str(root / "**" / a["pattern"]), recursive=True)
        return "\n".join(hits[:100]) or "No matches."

    def _tool_read_file(self, a: Dict[str, Any]) -> str:
        p = self._expand(a["path"])
        if not self._path_allowed(p):
            return f"Path not allowed: {p}"
        return p.read_text(encoding="utf-8", errors="replace")[:20000]

    def _tool_write_file(self, a: Dict[str, Any]) -> str:
        p = self._expand(a["path"])
        if not self._path_allowed(p):
            return f"Path not allowed: {p}"
        if not self.confirm_cb(f"Write file: {p}"):
            return "User declined the write."
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(a["content"], encoding="utf-8")
        return f"Wrote {len(a['content'])} chars to {p}."

    def _tool_type_text(self, a: Dict[str, Any]) -> str:
        import pyautogui
        pyautogui.typewrite(a["text"], interval=0.01)
        return "Typed text."

    def _tool_press_keys(self, a: Dict[str, Any]) -> str:
        import pyautogui
        keys = [k.strip() for k in a["keys"].replace("+", " ").split()]
        pyautogui.hotkey(*keys)
        return f"Pressed {a['keys']}."

    def _tool_scroll(self, a: Dict[str, Any]) -> str:
        import pyautogui
        amount = int(a.get("amount", 5)) * 120  # one notch ~= 120 units
        pyautogui.scroll(amount if a["direction"] == "up" else -amount)
        return f"Scrolled {a['direction']}."

    def _tool_screenshot(self, a: Dict[str, Any]) -> str:
        import base64, io
        import pyautogui
        img = pyautogui.screenshot()
        sw, sh = img.size
        target_w = 1280
        if sw > target_w:
            ratio = target_w / sw
            img = img.resize((target_w, int(sh * ratio)))
        self._shot_scale = sw / img.size[0]   # actual screen px per image px
        buf = io.BytesIO(); img.save(buf, format="PNG")
        self._last_screenshot_b64 = base64.b64encode(buf.getvalue()).decode()
        self._shot_dims = img.size
        return f"SCREENSHOT {img.size[0]}x{img.size[1]}"

    def _click_xy(self, a):
        import pyautogui
        scale = getattr(self, "_shot_scale", 1.0)
        return int(a["x"] * scale), int(a["y"] * scale)

    def _tool_click(self, a: Dict[str, Any]) -> str:
        import pyautogui
        x, y = self._click_xy(a); pyautogui.click(x, y)
        return f"Clicked ({a['x']},{a['y']})."

    def _tool_double_click(self, a: Dict[str, Any]) -> str:
        import pyautogui
        x, y = self._click_xy(a); pyautogui.doubleClick(x, y)
        return f"Double-clicked ({a['x']},{a['y']})."

    def _tool_move_mouse(self, a: Dict[str, Any]) -> str:
        import pyautogui
        x, y = self._click_xy(a); pyautogui.moveTo(x, y)
        return f"Moved to ({a['x']},{a['y']})."

    def _tool_drag(self, a: Dict[str, Any]) -> str:
        import pyautogui
        x, y = self._click_xy(a); pyautogui.dragTo(x, y, duration=0.3)
        return f"Dragged to ({a['x']},{a['y']})."

    def _tool_system_info(self, a: Dict[str, Any]) -> str:
        info = [f"OS: {platform.platform()}"]
        try:
            import psutil
            info.append(f"CPU: {psutil.cpu_percent(interval=0.3)}%")
            vm = psutil.virtual_memory()
            info.append(f"RAM: {vm.percent}% of {vm.total // (1024**3)} GB")
            batt = psutil.sensors_battery()
            if batt:
                info.append(f"Battery: {batt.percent}%"
                            f"{' (charging)' if batt.power_plugged else ''}")
            info.append(f"Processes: {len(psutil.pids())}")
        except Exception:
            info.append("(install psutil for CPU/RAM/battery)")
        return "\n".join(info)

    def _tool_ask_user(self, a: Dict[str, Any]) -> str:
        from . import overlay
        q = a["question"]
        if self.speak_cb:
            try:
                self.speak_cb(q)
            except Exception:
                pass
        ans = overlay.ask(q, a.get("options"))
        return ans if ans else "(no answer)"

    def _tool_open_url(self, a: Dict[str, Any]) -> str:
        import webbrowser
        webbrowser.open(a["url"])
        return f"Opened {a['url']}"

    def _tool_web_search(self, a: Dict[str, Any]) -> str:
        import requests
        # DuckDuckGo Instant Answer API — no key required.
        r = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": a["query"], "format": "json", "no_html": 1},
            timeout=15,
        )
        d = r.json()
        out = []
        if d.get("AbstractText"):
            out.append(d["AbstractText"])
        for topic in d.get("RelatedTopics", [])[:5]:
            if isinstance(topic, dict) and topic.get("Text"):
                out.append("- " + topic["Text"])
        return "\n".join(out) or "No instant answer; try fetch_url on a result."

    def _tool_fetch_url(self, a: Dict[str, Any]) -> str:
        import re
        import requests
        r = requests.get(a["url"], timeout=20, headers={"User-Agent": "VoiceClaw"})
        text = r.text
        text = re.sub(r"<script.*?</script>", " ", text, flags=re.S | re.I)
        text = re.sub(r"<style.*?</style>", " ", text, flags=re.S | re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text[:8000]