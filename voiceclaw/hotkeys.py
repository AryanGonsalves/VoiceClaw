# VoiceClaw — Copyright (c) 2026 Aryan Gonsalves. All rights reserved. Proprietary; see LICENSE.
"""Global (system-wide) hotkeys via pynput.

Works regardless of which window is focused, so the user can push-to-talk or kill
the assistant from anywhere. Optional: if pynput isn't installed, the app simply
runs without global hotkeys (wake word / Enter still work).

Default bindings (configurable):
  push_to_talk : <ctrl>+<alt>+space   -> capture one utterance now
  kill_switch  : <ctrl>+<alt>+q       -> stop listening / quit the loop
"""
from __future__ import annotations

from typing import Callable, Optional


def hotkeys_available() -> bool:
    try:
        import pynput  # noqa: F401
        return True
    except Exception:
        return False


class HotkeyManager:
    def __init__(self, push_to_talk: str = "<ctrl>+<alt>+space",
                 kill_switch: str = "<ctrl>+<alt>+q",
                 on_ptt: Optional[Callable[[], None]] = None,
                 on_kill: Optional[Callable[[], None]] = None):
        self.ptt_combo = push_to_talk
        self.kill_combo = kill_switch
        self.on_ptt = on_ptt or (lambda: None)
        self.on_kill = on_kill or (lambda: None)
        self._listener = None

    def start(self) -> bool:
        """Begin listening for global hotkeys in a background thread.
        Returns True if started, False if pynput is unavailable/failed."""
        try:
            from pynput import keyboard
        except Exception:
            return False
        mapping = {}
        if self.ptt_combo:
            mapping[self.ptt_combo] = self._safe(self.on_ptt)
        if self.kill_combo:
            mapping[self.kill_combo] = self._safe(self.on_kill)
        if not mapping:
            return False
        try:
            self._listener = keyboard.GlobalHotKeys(mapping)
            self._listener.start()
            return True
        except Exception:
            self._listener = None
            return False

    @staticmethod
    def _safe(fn: Callable[[], None]) -> Callable[[], None]:
        def wrapped():
            try:
                fn()
            except Exception as e:
                print(f"[hotkeys] handler error: {e}")
        return wrapped

    def stop(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None


class DictationHotkey:
    """Hold a single key (default Right Ctrl) to dictate. on_press fires on key-down;
    held() reports the live key state so the recorder can capture while it's held."""

    def __init__(self, key: str = "<ctrl_r>",
                 on_press: Optional[Callable[[], None]] = None):
        self.key_name = (key or "").strip().strip("<>").lower()
        self.on_press = on_press or (lambda: None)
        self._held = False
        self._listener = None

    def held(self) -> bool:
        return self._held

    def _resolve(self, keyboard):
        K = keyboard.Key
        special = {
            "ctrl_r": getattr(K, "ctrl_r", None), "ctrl_l": getattr(K, "ctrl_l", None),
            "alt_r": getattr(K, "alt_r", None), "alt_gr": getattr(K, "alt_gr", None),
            "shift_r": getattr(K, "shift_r", None), "shift_l": getattr(K, "shift_l", None),
            "scroll_lock": getattr(K, "scroll_lock", None),
            "pause": getattr(K, "pause", None), "menu": getattr(K, "menu", None),
        }
        for i in range(1, 13):
            special[f"f{i}"] = getattr(K, f"f{i}", None)
        return special.get(self.key_name)

    def start(self) -> bool:
        try:
            from pynput import keyboard
        except Exception:
            return False
        target = self._resolve(keyboard)
        if target is None:
            return False

        def on_press(k):
            if k == target and not self._held:
                self._held = True
                try:
                    self.on_press()
                except Exception:
                    pass

        def on_release(k):
            if k == target:
                self._held = False

        try:
            self._listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            self._listener.start()
            return True
        except Exception:
            self._listener = None
            return False

    def stop(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None