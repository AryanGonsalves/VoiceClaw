# VoiceClaw — Copyright (c) 2026 Aryan Gonsalves. All rights reserved. Proprietary; see LICENSE.
"""Secure local storage for VoiceClaw credentials.

Prefers the OS keychain (via the optional `keyring` package: macOS Keychain,
Windows Credential Manager, Linux Secret Service). If keyring is unavailable,
falls back to a JSON file at ~/.voiceclaw/credentials.json with 0600 perms.

Stored keys:
  oauth_token  -> Claude Pro/Max subscription OAuth token (sk-ant-oat...)
  api_key      -> Anthropic API key (sk-ant-api...)

We only ever store tokens the user obtained through official means. Nothing here
touches browser cookies or web sessions.
"""
from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Optional

SERVICE = "voiceclaw"
_FILE = Path(os.path.expanduser("~/.voiceclaw/credentials.json"))
_VALID_KEYS = ("oauth_token", "api_key", "openai_key")


def _keyring():
    try:
        import keyring  # type: ignore
        # Some environments have keyring installed but no usable backend.
        from keyring.errors import NoKeyringError  # noqa: F401
        return keyring
    except Exception:
        return None


# -- file fallback --------------------------------------------------------
def _read_file() -> dict:
    if not _FILE.exists():
        return {}
    try:
        return json.loads(_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_file(data: dict) -> None:
    _FILE.parent.mkdir(parents=True, exist_ok=True)
    _FILE.write_text(json.dumps(data), encoding="utf-8")
    try:
        os.chmod(_FILE, stat.S_IRUSR | stat.S_IWUSR)  # 0600
    except Exception:
        pass


# -- public API -----------------------------------------------------------
def save(key: str, value: str) -> str:
    """Store a credential. Returns the backend used ('keyring' | 'file')."""
    if key not in _VALID_KEYS:
        raise ValueError(f"unknown credential key: {key}")
    kr = _keyring()
    if kr is not None:
        try:
            kr.set_password(SERVICE, key, value)
            return "keyring"
        except Exception:
            pass
    data = _read_file()
    data[key] = value
    _write_file(data)
    return "file"


def load(key: str) -> Optional[str]:
    if key not in _VALID_KEYS:
        return None
    kr = _keyring()
    if kr is not None:
        try:
            val = kr.get_password(SERVICE, key)
            if val:
                return val
        except Exception:
            pass
    return _read_file().get(key)


def clear(key: Optional[str] = None) -> None:
    """Remove one key, or all credentials if key is None."""
    keys = [key] if key else list(_VALID_KEYS)
    kr = _keyring()
    if kr is not None:
        for k in keys:
            try:
                kr.delete_password(SERVICE, k)
            except Exception:
                pass
    data = _read_file()
    for k in keys:
        data.pop(k, None)
    if data:
        _write_file(data)
    elif _FILE.exists():
        try:
            _FILE.unlink()
        except Exception:
            pass


def backend_name() -> str:
    return "OS keychain" if _keyring() is not None else f"file ({_FILE})"