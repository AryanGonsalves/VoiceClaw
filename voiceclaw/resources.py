# VoiceClaw — Copyright (c) 2026 Aryan Gonsalves. All rights reserved. Proprietary; see LICENSE.
"""Resource manager: lazy-load heavy models and unload them when idle.

This is the mechanism behind "lightweight 24/7". Heavy components (Whisper, and
any in-process model) implement the Unloadable protocol: a `last_used` timestamp,
an `is_loaded()` check, and an `unload()` method. A background watchdog unloads
anything idle longer than `idle_seconds`, so resident RAM drops back to near the
wake-word listener's footprint between interactions.
"""
from __future__ import annotations

import threading
import time
from typing import List, Protocol, runtime_checkable


@runtime_checkable
class Unloadable(Protocol):
    last_used: float
    def is_loaded(self) -> bool: ...
    def unload(self) -> None: ...


class ResourceManager:
    def __init__(self, idle_seconds: int = 300, poll_seconds: float = 15.0):
        self.idle_seconds = idle_seconds
        self.poll_seconds = poll_seconds
        self._items: List[Unloadable] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def register(self, item: Unloadable) -> Unloadable:
        self._items.append(item)
        return item

    def start(self) -> None:
        if self.idle_seconds <= 0 or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        while not self._stop.wait(self.poll_seconds):
            now = time.time()
            for it in self._items:
                try:
                    if it.is_loaded() and (now - it.last_used) > self.idle_seconds:
                        it.unload()
                        print(f"[resources] unloaded idle {type(it).__name__}")
                except Exception as e:
                    print(f"[resources] unload error: {e}")