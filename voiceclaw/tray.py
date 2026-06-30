# VoiceClaw — Copyright (c) 2026 Aryan Gonsalves. All rights reserved. Proprietary; see LICENSE.
"""System-tray app: runs VoiceClaw in the background, 24/7.

Lives in the system tray with a menu to sign in, pause/resume listening, and
quit. The voice loop runs in a daemon thread; the wake-word listener idles
cheaply until you speak. Confirmations and sign-in pop small desktop dialogs.

Run:  python -m voiceclaw.tray
Deps: pip install pystray pillow   (plus the voice deps in requirements.txt)
"""
from __future__ import annotations

import sys
import threading

from .config import Config
from .app import build, gui_confirm


def _make_icon_image(color=(70, 130, 220)):
    """Generate a simple circular mic icon so we don't ship a binary asset."""
    from PIL import Image, ImageDraw
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((6, 6, size - 6, size - 6), fill=color)
    d.rounded_rectangle((27, 18, 37, 40), radius=5, fill=(255, 255, 255, 255))
    d.arc((22, 30, 42, 48), start=0, end=180, fill=(255, 255, 255, 255), width=3)
    d.line((32, 48, 32, 54), fill=(255, 255, 255, 255), width=3)
    return img


class TrayApp:
    def __init__(self, config_path=None):
        self.cfg = Config.load(config_path)
        self.asst = build(self.cfg, confirm_cb=gui_confirm(None))
        print(f"[backend] {self.asst.auth_message or 'no agent'} "
              f"(mode={self.asst.auth_mode})")
        self._paused = threading.Event()
        self._stop = threading.Event()
        self._thread = None

    def _loop(self):
        import sys as _sys
        from pathlib import Path
        _sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from main import run_voice  # type: ignore

        def stop_flag():
            while self._paused.is_set() and not self._stop.is_set():
                self._stop.wait(0.2)
            return self._stop.is_set()

        try:
            run_voice(self.asst, stop_flag=stop_flag)
        except Exception as e:
            print(f"[tray] voice loop ended: {e}")

    def _sign_in(self, icon):
        """Paste an official token (subscription or API key), store it securely,
        and activate the Claude brain without restarting."""
        try:
            import tkinter as tk
            from tkinter import simpledialog
            from . import credentials_store as store
            root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
            token = simpledialog.askstring(
                "VoiceClaw — Sign in",
                "Paste your Claude token (sk-ant-…).\n"
                "Get one with `claude setup-token` (Pro/Max), "
                "or paste an Anthropic API key.",
                show="*")
            root.destroy()
            if not token or not token.strip().startswith("sk-ant-"):
                self.asst.speaker.say("No valid token entered.")
                return
            key = "api_key" if "-api" in token else "oauth_token"
            store.save(key, token.strip())
            mode, _ = self.asst.reload_auth()
            self.asst.speaker.say("Signed in." if mode != "none"
                                  else "Saved, but sign-in failed.")
            icon.update_menu()
        except Exception as e:
            self.asst.speaker.say(f"Sign-in error: {e}")

    def _forget_learned(self, icon):
        """Wipe the personalized learned-command cache."""
        try:
            n = self.asst.learned.count() if self.asst.learned else 0
            if self.asst.learned:
                self.asst.learned.clear()
            self.asst.speaker.say(
                f"Forgot {n} learned command{'' if n == 1 else 's'}.")
            icon.update_menu()
        except Exception as e:
            self.asst.speaker.say(f"Couldn't clear learned commands: {e}")

    def start(self):
        import pystray
        from pystray import MenuItem as Item

        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

        def toggle_pause(icon, item):
            if self._paused.is_set():
                self._paused.clear()
                self.asst.speaker.say("Listening resumed.")
            else:
                self._paused.set()
                self.asst.speaker.say("Paused. Wake me from the tray.")
            icon.update_menu()

        def is_paused(item):
            return self._paused.is_set()

        def brain_label(item):
            return ("Claude: on (" + self.asst.auth_mode + ")") if self.asst.brain \
                else "Claude: off (local only)"

        def learned_label(item):
            n = self.asst.learned.count() if self.asst.learned else 0
            return f"Forget learned commands ({n})"

        def is_dictating(item):
            return bool(getattr(self.asst, "dictation_mode", False))

        def toggle_dictation(icon, item):
            self.asst.dictation_mode = not getattr(self.asst, "dictation_mode", False)
            self.asst.speaker.say("Dictation on. I'll type what you say."
                                  if self.asst.dictation_mode else "Dictation off.")
            icon.update_menu()

        menu = pystray.Menu(
            Item(brain_label, None, enabled=False),
            Item("Sign in…", lambda icon, item: self._sign_in(icon)),
            Item("Pause listening", toggle_pause, checked=is_paused),
            Item("Dictation mode (type what I say)", toggle_dictation,
                 checked=is_dictating),
            Item(learned_label, lambda icon, item: self._forget_learned(icon)),
            Item("Quit", lambda icon, item: (self._stop.set(), icon.stop())),
        )
        icon = pystray.Icon("VoiceClaw", _make_icon_image(), "VoiceClaw", menu)
        self.asst.speaker.say("Voice Claude is running in the tray.")
        icon.run()


def main():
    try:
        import pystray  # noqa: F401
        from PIL import Image  # noqa: F401
    except Exception:
        print("Tray needs extra deps:  pip install pystray pillow")
        return 1
    TrayApp().start()
    return 0


if __name__ == "__main__":
    sys.exit(main())