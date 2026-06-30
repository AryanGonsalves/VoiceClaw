# VoiceClaw — Copyright (c) 2026 Aryan Gonsalves. All rights reserved. Proprietary; see LICENSE.
"""MCP server exposing VoiceClaw's PC-control tools to Claude Code.

Claude Code (authenticated with the user's subscription) connects to this server
and calls these tools to actually control the PC — including vision (screenshot)
and clicking. Run standalone for testing:  python -m voiceclaw.mcp_server

Personal-use note: destructive shell/file actions still go through a confirmation
dialog (overlay). Clicking/opening do not require confirmation.
"""
import base64

from mcp.server.fastmcp import FastMCP, Image

from .config import Config
from .tools import Toolbox


def _build_toolbox() -> Toolbox:
    cfg = Config.load("config.yaml")

    def confirm(prompt: str) -> bool:
        # GUI confirm for destructive actions (safe default if no display).
        try:
            from . import overlay
            ans = overlay.ask("Allow this action?\n" + prompt, ["Yes", "No"])
            return bool(ans) and ans.strip().lower().startswith("y")
        except Exception:
            return False

    return Toolbox(allowed_paths=cfg.allowed_paths,
                   confirm_patterns=cfg["agent"]["confirm_patterns"],
                   confirm_cb=confirm, speak_cb=None)


def build_server():
    mcp = FastMCP("voiceclaw")
    tb = _build_toolbox()

    @mcp.tool()
    def open_app(name: str) -> str:
        """Launch an application by name (e.g. 'notepad', 'chrome')."""
        return tb.run("open_app", {"name": name})

    @mcp.tool()
    def close_app(name: str) -> str:
        """Close/quit a running application by name."""
        return tb.run("close_app", {"name": name})

    @mcp.tool()
    def open_url(url: str) -> str:
        """Open a URL (or web search) in the default browser."""
        return tb.run("open_url", {"url": url})

    @mcp.tool()
    def run_shell(command: str, timeout: int = 30) -> str:
        """Run a shell command (destructive ones require user confirmation)."""
        return tb.run("run_shell", {"command": command, "timeout": timeout})

    @mcp.tool()
    def list_files(path: str = "") -> str:
        """List files/folders in a directory (defaults to home)."""
        return tb.run("list_files", {"path": path} if path else {})

    @mcp.tool()
    def search_files(pattern: str, root: str = "") -> str:
        """Find files by glob pattern under a root."""
        a = {"pattern": pattern}
        if root:
            a["root"] = root
        return tb.run("search_files", a)

    @mcp.tool()
    def read_file(path: str) -> str:
        """Read a text file's contents."""
        return tb.run("read_file", {"path": path})

    @mcp.tool()
    def write_file(path: str, content: str) -> str:
        """Create/overwrite a text file (requires confirmation)."""
        return tb.run("write_file", {"path": path, "content": content})

    @mcp.tool()
    def type_text(text: str) -> str:
        """Type text into the focused window."""
        return tb.run("type_text", {"text": text})

    @mcp.tool()
    def press_keys(keys: str) -> str:
        """Press a keyboard shortcut, e.g. 'ctrl+s', 'alt+f4', 'down'."""
        return tb.run("press_keys", {"keys": keys})

    @mcp.tool()
    def scroll(direction: str, amount: int = 5) -> str:
        """Scroll the active window 'up' or 'down'."""
        return tb.run("scroll", {"direction": direction, "amount": amount})

    @mcp.tool()
    def system_info() -> str:
        """Get OS, CPU/RAM, battery, process count."""
        return tb.run("system_info", {})

    @mcp.tool()
    def web_search(query: str) -> str:
        """Search the web and return snippets."""
        return tb.run("web_search", {"query": query})

    @mcp.tool()
    def fetch_url(url: str) -> str:
        """Fetch the text content of a web page."""
        return tb.run("fetch_url", {"url": url})

    @mcp.tool()
    def screenshot() -> Image:
        """Take a screenshot to SEE the screen; click using its pixel coordinates."""
        tb.run("screenshot", {})
        data = base64.b64decode(getattr(tb, "_last_screenshot_b64", "") or "")
        return Image(data=data, format="png")

    @mcp.tool()
    def click(x: int, y: int) -> str:
        """Left-click at (x, y) pixel coordinates from the latest screenshot."""
        return tb.run("click", {"x": x, "y": y})

    @mcp.tool()
    def double_click(x: int, y: int) -> str:
        """Double-click at (x, y) from the latest screenshot."""
        return tb.run("double_click", {"x": x, "y": y})

    @mcp.tool()
    def move_mouse(x: int, y: int) -> str:
        """Move the mouse to (x, y) from the latest screenshot."""
        return tb.run("move_mouse", {"x": x, "y": y})

    @mcp.tool()
    def drag(x: int, y: int) -> str:
        """Drag from the current position to (x, y) from the latest screenshot."""
        return tb.run("drag", {"x": x, "y": y})

    return mcp


def main():
    build_server().run()


if __name__ == "__main__":
    main()