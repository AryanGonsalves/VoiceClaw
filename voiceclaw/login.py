# VoiceClaw — Copyright (c) 2026 Aryan Gonsalves. All rights reserved. Proprietary; see LICENSE.
"""`voiceclaw login` — friendly subscription/API sign-in.

Goal: let a Claude Pro/Max subscriber sign in without wrestling with env vars.
We use ONLY Anthropic's official token mechanism:

  - Subscription: runs `claude setup-token` (Claude Code) which performs the
    official OAuth browser flow and yields an OAuth token; we capture or accept
    it and store it securely (OS keychain via credentials_store).
  - API key: paste an Anthropic API key to store instead.

No browser cookies, no web-session scraping — that would violate Anthropic's ToS.

CLI:
  python -m voiceclaw.login            # interactive subscription login
  python -m voiceclaw.login --api-key  # paste an API key instead
  python -m voiceclaw.login --token T  # store a token you already have
  python -m voiceclaw.login --status
  python -m voiceclaw.login --logout
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from typing import Optional

from . import credentials_store as store

TOKEN_RE = re.compile(r"sk-ant-[A-Za-z0-9._\-]{8,}")


def _looks_like_token(s: str) -> bool:
    return bool(s) and s.strip().startswith("sk-ant-") and len(s.strip()) >= 16


def _run_setup_token() -> Optional[str]:
    """Try the official `claude setup-token`. Returns a token if we can capture
    one from its output, else None (caller falls back to manual paste)."""
    if shutil.which("claude") is None:
        return None
    print("Launching the official `claude setup-token` flow "
          "(a browser window may open)…\n")
    try:
        # Inherit stdin/stderr so the OAuth flow stays interactive; capture stdout
        # so we can scrape the printed token.
        proc = subprocess.run(["claude", "setup-token"], stdout=subprocess.PIPE,
                              stderr=None, text=True, timeout=600)
    except Exception as e:
        print(f"(couldn't run `claude setup-token`: {e})")
        return None
    out = proc.stdout or ""
    print(out)
    m = TOKEN_RE.search(out)
    return m.group(0) if m else None


def login(interactive: bool = True) -> int:
    print("VoiceClaw — Claude subscription login\n"
          "This uses Anthropic's official token flow (Claude Pro/Max).\n")
    token = _run_setup_token()

    if not token and interactive:
        print("\nIf a token was shown above, paste it here. Otherwise:\n"
              "  1) Install Claude Code:  https://docs.claude.com/claude-code\n"
              "  2) Run:  claude setup-token\n"
              "  3) Paste the token it gives you below.\n")
        try:
            token = input("Paste subscription token (sk-ant-…): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return 1

    if not _looks_like_token(token or ""):
        print("That doesn't look like a valid token (expected to start with "
              "'sk-ant-'). Nothing saved.")
        return 1

    backend = store.save("oauth_token", token.strip())
    print(f"\n✓ Signed in. Token stored in {backend}. "
          f"VoiceClaw will use your subscription automatically.")
    return 0


def login_api_key(key: Optional[str] = None) -> int:
    if not key:
        try:
            key = input("Paste your Anthropic API key (sk-ant-…): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return 1
    if not _looks_like_token(key or ""):
        print("That doesn't look like a valid key. Nothing saved.")
        return 1
    backend = store.save("api_key", key.strip())
    print(f"✓ API key stored in {backend}.")
    return 0


def logout() -> int:
    store.clear()
    print("✓ Signed out. All stored VoiceClaw credentials removed.")
    return 0


def status() -> int:
    oauth = store.load("oauth_token")
    api = store.load("api_key")
    print(f"Credential store: {store.backend_name()}")
    print(f"  subscription token: {'present' if oauth else 'none'}")
    print(f"  api key:            {'present' if api else 'none'}")
    if not (oauth or api):
        print("Not signed in. Run:  python -m voiceclaw.login")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="voiceclaw.login",
                                 description="Sign in to Claude for VoiceClaw.")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--api-key", action="store_true", help="store an API key instead")
    g.add_argument("--token", help="store a token you already have")
    g.add_argument("--logout", action="store_true", help="remove stored credentials")
    g.add_argument("--status", action="store_true", help="show sign-in status")
    args = ap.parse_args(argv)

    if args.logout:
        return logout()
    if args.status:
        return status()
    if args.token:
        if not _looks_like_token(args.token):
            print("Invalid token."); return 1
        backend = store.save("oauth_token", args.token.strip())
        print(f"✓ Token stored in {backend}."); return 0
    if args.api_key:
        return login_api_key()
    return login()


if __name__ == "__main__":
    sys.exit(main())