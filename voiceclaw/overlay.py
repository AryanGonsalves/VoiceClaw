# VoiceClaw — Copyright (c) 2026 Aryan Gonsalves. All rights reserved. Proprietary; see LICENSE.
"""Lightweight on-screen clarify overlay (tkinter, stdlib — no extra deps).

When a command is ambiguous, the assistant can pop a small always-on-top window
asking a quick follow-up, with clickable options and/or a text box. Used by the
`ask_user` tool so Claude can disambiguate instead of guessing, and by Tier-1 for
cases like a bare "open" with no app named.

Design notes:
- Uses tkinter so it works without PySide6 (CLI/tray contexts).
- Creates and tears down its own root each call; returns the chosen string or
  None (cancel/timeout/headless). Never raises.
- tkinter prefers the main thread; if called from a worker thread and it fails,
  we degrade to returning None so the caller can fall back to speech/defaults.
"""
from __future__ import annotations

from typing import List, Optional


def overlay_available() -> bool:
    try:
        import tkinter  # noqa: F401
        return True
    except Exception:
        return False


def ask(question: str, options: Optional[List[str]] = None,
        timeout: float = 30.0) -> Optional[str]:
    """Show the clarify overlay. Returns the chosen option, typed text, or None."""
    try:
        import tkinter as tk
    except Exception:
        return None

    result = {"value": None}
    try:
        root = tk.Tk()
        root.title("VoiceClaw")
        root.attributes("-topmost", True)
        try:
            root.eval("tk::PlaceWindow . center")
        except Exception:
            pass

        pad = {"padx": 12, "pady": 6}
        tk.Label(root, text=question, wraplength=360, justify="left",
                 font=("Segoe UI", 11)).pack(**pad)

        def choose(val):
            result["value"] = val
            root.destroy()

        if options:
            btn_row = tk.Frame(root); btn_row.pack(**pad)
            for opt in options[:6]:
                tk.Button(btn_row, text=opt, width=14,
                          command=lambda o=opt: choose(o)).pack(side="left", padx=4)

        entry = tk.Entry(root, width=40)
        entry.pack(**pad)
        entry.focus_set()
        entry.bind("<Return>", lambda e: choose(entry.get().strip() or None))

        row = tk.Frame(root); row.pack(**pad)
        tk.Button(row, text="OK", width=10,
                  command=lambda: choose(entry.get().strip() or None)).pack(side="left", padx=4)
        tk.Button(row, text="Cancel", width=10,
                  command=lambda: choose(None)).pack(side="left", padx=4)

        if timeout and timeout > 0:
            root.after(int(timeout * 1000), root.destroy)
        root.mainloop()
    except Exception:
        return None
    return result["value"]