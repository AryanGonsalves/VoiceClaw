# VoiceClaw — Copyright (c) 2026 Aryan Gonsalves. All rights reserved. Proprietary; see LICENSE.
"""Lightweight issues/failures log for the companion UI's Logs tab.

Records errors and notable events to ~/.voiceclaw/issues.log as TSV lines:
  ISO_TIME <tab> LEVEL <tab> SOURCE <tab> MESSAGE

Kept deliberately simple and dependency-free so any part of the app can call
log_issue() without wiring a logger through every object.
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import List

LOG_PATH = Path(os.path.expanduser("~/.voiceclaw/issues.log"))
_MAX_LINES = 2000  # cap file growth


def log_issue(source: str, message: str, level: str = "ERROR") -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        line = (f"{time.strftime('%Y-%m-%dT%H:%M:%S')}\t{level}\t{source}\t"
                f"{str(message).replace(chr(9), ' ').replace(chr(10), ' ')}\n")
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line)
        _trim()
    except Exception:
        pass  # logging must never crash the app


def _trim() -> None:
    try:
        if not LOG_PATH.exists():
            return
        lines = LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
        if len(lines) > _MAX_LINES:
            LOG_PATH.write_text("\n".join(lines[-_MAX_LINES:]) + "\n",
                                encoding="utf-8")
    except Exception:
        pass


def read_issues(limit: int = 200) -> List[dict]:
    """Return the most recent issues, newest last, as dicts."""
    if not LOG_PATH.exists():
        return []
    out = []
    try:
        lines = LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
        for ln in lines[-limit:]:
            parts = ln.split("\t", 3)
            if len(parts) == 4:
                out.append({"time": parts[0], "level": parts[1],
                            "source": parts[2], "message": parts[3]})
    except Exception:
        pass
    return out


def clear_issues() -> None:
    try:
        if LOG_PATH.exists():
            LOG_PATH.unlink()
    except Exception:
        pass