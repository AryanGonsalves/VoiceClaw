# VoiceClaw — Copyright (c) 2026 Aryan Gonsalves. All rights reserved. Proprietary; see LICENSE.
"""Animated rainbow 'listening' ring around the screen edge.

A frameless, top-most, click-through tkinter overlay. show()/hide() toggle it;
the tk event loop runs in a daemon thread. Best-effort and Windows-tuned for the
click-through bit; degrades to no-op if the GUI/ctypes calls fail.
"""
from __future__ import annotations

import threading


def ring_available() -> bool:
    try:
        import tkinter  # noqa: F401
        return True
    except Exception:
        return False


class RingOverlay:
    def __init__(self, thickness: int = 7, speed: float = 0.015):
        self.thickness = thickness
        self.speed = speed
        self._visible = False
        self._stop = False
        self._thread = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def show(self) -> None:
        self._visible = True

    def hide(self) -> None:
        self._visible = False

    def stop(self) -> None:
        self._stop = True

    def _run(self) -> None:
        try:
            import colorsys
            import tkinter as tk
        except Exception:
            return
        try:
            root = tk.Tk()
            root.overrideredirect(True)
            root.attributes("-topmost", True)
            sw = root.winfo_screenwidth()
            sh = root.winfo_screenheight()
            root.geometry(f"{sw}x{sh}+0+0")
            trans = "#010101"
            try:
                root.attributes("-transparentcolor", trans)
            except Exception:
                pass
            cv = tk.Canvas(root, width=sw, height=sh, highlightthickness=0, bg=trans)
            cv.pack()
            # Make it click-through on Windows (WS_EX_LAYERED | WS_EX_TRANSPARENT).
            try:
                import ctypes
                hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
                GWL_EXSTYLE = -20
                cur = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                ctypes.windll.user32.SetWindowLongW(
                    hwnd, GWL_EXSTYLE, cur | 0x80000 | 0x20)
            except Exception:
                pass
            root.withdraw()
            hue = [0.0]
            t = max(3, self.thickness)
            segs = 48

            def col(i):
                r, g, b = colorsys.hsv_to_rgb(((hue[0] + i / segs) % 1.0), 1.0, 1.0)
                return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))

            def tick():
                if self._stop:
                    try:
                        root.destroy()
                    except Exception:
                        pass
                    return
                if self._visible:
                    root.deiconify()
                    root.attributes("-topmost", True)
                    cv.delete("ring")
                    for i in range(segs):
                        c = col(i)
                        x0, x1 = sw * i / segs, sw * (i + 1) / segs
                        cv.create_rectangle(x0, 0, x1, t, fill=c, outline=c, tags="ring")
                        cv.create_rectangle(x0, sh - t, x1, sh, fill=c, outline=c, tags="ring")
                        y0, y1 = sh * i / segs, sh * (i + 1) / segs
                        cv.create_rectangle(0, y0, t, y1, fill=c, outline=c, tags="ring")
                        cv.create_rectangle(sw - t, y0, sw, y1, fill=c, outline=c, tags="ring")
                    hue[0] = (hue[0] + self.speed) % 1.0
                else:
                    cv.delete("ring")
                    root.withdraw()
                root.after(40, tick)

            root.after(40, tick)
            root.mainloop()
        except Exception:
            return