# VoiceClaw — Copyright (c) 2026 Aryan Gonsalves. All rights reserved. Proprietary; see LICENSE.
"""Drive Claude Code headless as the agent backend, using the user's subscription.

For PERSONAL use only. This runs `claude -p` (Claude Code, authenticated with your
subscription login) and connects it to VoiceClaw's MCP server (mcp_server.py) so
Claude reasons and calls our PC-control tools — including screenshot+click.

NOTE: Anthropic's docs steer agents toward API keys and disallow subscription login
for distributed products. This is appropriate only for your own personal machine; do
not ship a product that signs other users in with their subscription this way.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, Optional

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)

MCP_TOOLS = [
    "open_app", "close_app", "open_url", "run_shell", "list_files", "search_files",
    "read_file", "write_file", "type_text", "press_keys", "scroll", "system_info",
    "web_search", "fetch_url", "screenshot", "click", "double_click", "move_mouse",
    "drag",
]

SYSTEM_APPEND = (
    "You are VoiceClaw, controlling the user's PC by voice. Use the voiceclaw MCP "
    "tools to actually perform actions. For on-screen clicks (buttons, links, video "
    "thumbnails, menu items), call screenshot to SEE the screen, then click with the "
    "pixel coordinates you see; re-screenshot to verify and continue. Keep your final "
    "reply short and natural — it will be spoken aloud."
)


class ClaudeCodeBrain:
    def __init__(self, project_root: str = PROJECT_ROOT, max_turns: int = 14):
        self.project_root = project_root
        self.max_turns = max_turns

    def available(self) -> bool:
        return shutil.which("claude") is not None

    def handle(self, text: str,
               on_status: Optional[Callable[[str], None]] = None) -> str:
        if on_status:
            on_status("thinking (Claude Code)…")
        mcp_cfg = {"mcpServers": {"voiceclaw": {
            "command": sys.executable,
            "args": ["-m", "voiceclaw.mcp_server"],
            "env": {"PYTHONPATH": self.project_root},
        }}}
        allowed = ",".join(f"mcp__voiceclaw__{t}" for t in MCP_TOOLS)
        f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                        encoding="utf-8")
        json.dump(mcp_cfg, f)
        f.close()
        # Resolve the real path. On Windows, Claude Code is often a .cmd shim
        # (npm global) which CreateProcess can't launch by bare name — run it via
        # `cmd /c <fullpath>`.
        exe = (shutil.which("claude.cmd") or shutil.which("claude.exe")
               or shutil.which("claude") or "claude")
        args = ["-p", text, "--output-format", "json",
                "--mcp-config", f.name, "--allowedTools", allowed,
                "--permission-mode", "bypassPermissions",
                "--append-system-prompt", SYSTEM_APPEND,
                "--max-turns", str(self.max_turns)]
        # Headless Claude Code authenticates via CLAUDE_CODE_OAUTH_TOKEN
        # (what `claude setup-token` produces). Pass the stored subscription token.
        env = os.environ.copy()
        tok = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") or ""
        if not tok:
            try:
                from . import credentials_store as _store
                tok = _store.load("oauth_token") or ""
            except Exception:
                tok = ""
        if tok:
            env["CLAUDE_CODE_OAUTH_TOKEN"] = tok
        try:
            if os.name == "nt":
                # .cmd shims (npm) + spaced user paths -> go through the shell.
                cmd = subprocess.list2cmdline([exe] + args)
                proc = subprocess.run(cmd, shell=True, capture_output=True,
                                      text=True, cwd=self.project_root,
                                      timeout=240, env=env)
            else:
                cmd = [exe] + args
                proc = subprocess.run(cmd, capture_output=True, text=True,
                                      cwd=self.project_root, timeout=240, env=env)
            out = (proc.stdout or "").strip()
            if not out:
                from .issues import log_issue
                log_issue("claude_code", (proc.stderr or "no output")[:400])
                return ("Claude Code returned nothing. Make sure it's installed "
                        "and you're logged in (`claude` then /login).")
            try:
                data = json.loads(out)
                if isinstance(data, dict):
                    return (data.get("result") or data.get("text") or "Done.").strip()
                if isinstance(data, list) and data:
                    last = data[-1]
                    return (last.get("result") or last.get("text") or "Done.").strip()
            except Exception:
                return out[:500]
            return "Done."
        except FileNotFoundError:
            return "Claude Code ('claude') isn't installed or not on PATH."
        except subprocess.TimeoutExpired:
            return "That took too long; Claude Code timed out."
        except Exception as e:
            from .issues import log_issue
            log_issue("claude_code", e)
            return "Claude Code error; check the Logs tab."
        finally:
            try:
                os.unlink(f.name)
            except Exception:
                pass

    def reset(self) -> None:
        pass