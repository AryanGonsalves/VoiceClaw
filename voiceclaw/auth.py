# VoiceClaw — Copyright (c) 2026 Aryan Gonsalves. All rights reserved. Proprietary; see LICENSE.
"""Credential providers for the Claude brain.

Two supported ways to authenticate, selected by `brain.auth` in config
("auto" | "api_key" | "subscription"):

1. api_key  — a pay-as-you-go Anthropic API key (env ANTHROPIC_API_KEY, config,
              or stored via `voiceclaw login --api-key`). Sent as x-api-key.

2. subscription — a Claude Pro/Max subscription used the *officially supported*
              way: an OAuth token minted by Anthropic's tooling
              (`claude setup-token`), provided via the CLAUDE_CODE_OAUTH_TOKEN env
              var OR stored via `voiceclaw login`. Sent as a Bearer token.

Credential lookup order (per type): env var -> config -> secure store.

IMPORTANT — terms of service:
  The subscription path works ONLY through Anthropic's official OAuth token. We
  never read, reuse, or reverse-engineer claude.ai web-session cookies — that
  violates Anthropic's Terms and is not supported here.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, Tuple

from . import credentials_store as store


@dataclass
class Credentials:
    mode: str                      # "api_key" | "subscription" | "none"
    api_key: Optional[str] = None
    auth_token: Optional[str] = None
    source: str = ""              # where it came from (env/config/store)

    @property
    def usable(self) -> bool:
        return bool(self.api_key or self.auth_token)


def _api_key(cfg) -> Tuple[Optional[str], str]:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ["ANTHROPIC_API_KEY"], "env"
    if cfg.anthropic_key:
        return cfg.anthropic_key, "config"
    stored = store.load("api_key")
    if stored:
        return stored, "store"
    return None, ""


def _sub_token(cfg) -> Tuple[Optional[str], str]:
    for var in ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_AUTH_TOKEN"):
        if os.environ.get(var):
            return os.environ[var], "env"
    stored = store.load("oauth_token")
    if stored:
        return stored, "store"
    return None, ""


def resolve(cfg) -> Credentials:
    """Resolve credentials from env + config + secure store per brain.auth."""
    mode = (cfg["brain"].get("auth") or "auto").lower()
    api_key, api_src = _api_key(cfg)
    tok, tok_src = _sub_token(cfg)

    if mode == "api_key":
        return Credentials("api_key", api_key=api_key, source=api_src) if api_key \
            else Credentials("none")
    if mode == "subscription":
        return Credentials("subscription", auth_token=tok, source=tok_src) if tok \
            else Credentials("none")
    # auto: prefer an explicit API key, else a subscription token.
    if api_key:
        return Credentials("api_key", api_key=api_key, source=api_src)
    if tok:
        return Credentials("subscription", auth_token=tok, source=tok_src)
    return Credentials("none")


def make_client(cfg) -> Tuple[Optional[object], str, str]:
    """Return (anthropic_client_or_None, mode, human_message)."""
    creds = resolve(cfg)
    if not creds.usable:
        return (None, "none",
                "Not signed in. Run `python -m voiceclaw.login` (Claude "
                "Pro/Max) or set ANTHROPIC_API_KEY for an API key.")
    try:
        from anthropic import Anthropic
    except Exception:
        return (None, creds.mode, "The 'anthropic' package is not installed.")

    if creds.mode == "api_key":
        return (Anthropic(api_key=creds.api_key, max_retries=4), "api_key",
                f"Authenticated with Anthropic API key (from {creds.source}).")
    return (Anthropic(auth_token=creds.auth_token, max_retries=4), "subscription",
            f"Authenticated with Claude subscription (from {creds.source}).")