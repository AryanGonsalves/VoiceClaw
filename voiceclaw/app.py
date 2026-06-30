# VoiceClaw — Copyright (c) 2026 Aryan Gonsalves. All rights reserved. Proprietary; see LICENSE.
"""Core assembly + request handling, shared by the CLI (main.py) and the tray."""
from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from . import auth
from . import tts as tts_mod
from .config import Config
from .local_llm import LocalLLM
from .local_skills import LocalSkills
from .learned_skills import LearnedSkills
from .local_agent import LocalBrain
from .router import Router
from .resources import ResourceManager
from .tools import Toolbox
from .brain import ClaudeBrain


@dataclass
class Assistant:
    cfg: Config
    speaker: object
    router: Router
    skills: LocalSkills
    toolbox: Toolbox
    brain: object
    resources: ResourceManager
    local_agent: Optional[LocalBrain] = None
    learned: Optional[LearnedSkills] = None
    dictation_mode: bool = False
    auth_mode: str = "none"
    auth_message: str = ""

    def reload_auth(self):
        """Re-resolve the agent backend (after a sign-in change) at runtime."""
        self.brain, self.auth_mode, self.auth_message = _select_brain(
            self.cfg, self.toolbox)
        return self.auth_mode, self.auth_message

    def _pick_agent(self):
        if self.brain is not None:
            return self.brain, self.auth_mode if self.auth_mode != "none" else "agent"
        if self.local_agent is not None and self.local_agent.available():
            return self.local_agent, "local-agent"
        return None, "none"

    def respond(self, text: str) -> str:
        text = (text or "").strip()
        if not text:
            return ""
        _log(self.cfg, "user", text)
        print(f"> {text}")

        # --- Voice dictation / relay: type spoken words into the FOCUSED window
        # (a dev chat like Cowork/Codex/Claude Code, an editor, etc.) instead of
        # interpreting them as PC commands. Checked before any command routing.
        dctl = _dictation_action(text, self.dictation_mode)
        if dctl is not None:
            kind, payload = dctl
            if kind == "start":
                self.dictation_mode = True
                msg = ("Dictation on — I'll type what you say into the active window. "
                       "Say 'stop dictation' to finish.")
                _log(self.cfg, "dictation", "ON")
                self.speaker.say(msg)
                return msg
            if kind == "stop":
                self.dictation_mode = False
                _log(self.cfg, "dictation", "OFF")
                self.speaker.say("Dictation off.")
                return "dictation off"
            verbatim, send = payload
            self.toolbox.run("type_text", {"text": verbatim})
            if send:
                self.toolbox.run("press_keys", {"keys": "enter"})
            print(f"  [dictation] typed{' + sent' if send else ''}: {verbatim}")
            _log(self.cfg, "dictation", verbatim)
            return verbatim  # typed silently; no spoken echo

        # Personalized fast-path: replay a previously-learned resolution instantly.
        if self.learned is not None:
            hit = self.learned.lookup(text)
            if hit is not None:
                actions, reply = hit
                try:
                    for name, args in actions:
                        self.toolbox.run(name, args)
                    reply = reply or "Done."
                    _log(self.cfg, "learned", reply)
                    self.speaker.say(reply)
                    return reply
                except Exception as e:
                    from .issues import log_issue
                    log_issue("learned.replay", e)  # fall through to normal handling

        agent, label = self._pick_agent()
        # When a reasoning agent is available, natural/multi-step phrasing should go
        # straight to it instead of being hijacked by a greedy Tier-1 rule.
        complex_req = agent is not None and _is_complex(text)

        if not complex_req:
            skill_reply = self.skills.handle(text, self.toolbox)
            if skill_reply is not None:
                _log(self.cfg, "skill", skill_reply)
                self.speaker.say(skill_reply)
                return skill_reply
            local_answer = self.router.try_local(text)
            if local_answer:
                _log(self.cfg, "local", local_answer)
                self.speaker.say(local_answer)
                return local_answer

        if agent is None:
            msg = self.auth_message or ("That needs the agent. Add an API key in the "
                                        "Account tab, or run Ollama for the local agent.")
            self.speaker.say(msg)
            return msg

        try:
            answer = agent.handle(text, on_status=lambda m: print(f"  …{m}"))
            if self.learned is not None:
                trace = list(getattr(agent, "last_trace", None) or [])
                if self.learned.record(text, trace, answer):
                    print("  [learned] cached this phrasing for instant reuse")
        except Exception as e:
            from .issues import log_issue
            log_issue(label, e)
            es = str(e).lower()
            if "429" in es or "rate_limit" in es or "rate limit" in es:
                answer = ("That model is rate-limited right now. "
                          "Give it a little while and try again.")
            elif "401" in es or "403" in es or "authentication" in es:
                answer = "Sign-in failed or expired. Please sign in again in the Account tab."
            else:
                answer = "Sorry, I ran into an error handling that. It's in the log."
        _log(self.cfg, label, answer)
        self.speaker.say(answer)
        return answer


_COMPLEX_MARKERS = ("can you", "could you", "would you", "please", " and ",
                    " then ", "find me", "look for", "search and", "after that")

# On-screen actions that require vision (screenshot->click). Tier-1 regex can't do
# these, so any command containing one is sent straight to the agent.
_VISION_MARKERS = ("click", "tap on", "double click", "double-click", "drag ",
                   "select the", "press the")

# Conversational / free-form phrasing the LLM should interpret (not the rigid Tier-1
# grammar). These signal "general speech", so we hand off to the agent.
_CONVERSATIONAL_MARKERS = ("this one", "that one", "for me", "go back to", "put on",
                           "i want", "i'd like", "let's ", "can we", "how about",
                           "next one", "last one", "instead", "as well")


_DICT_START = {"start dictation", "dictation mode", "begin dictation",
               "start dictating", "enter dictation", "dictation on"}
_DICT_STOP = {"stop dictation", "end dictation", "exit dictation",
              "stop dictating", "dictation off", "leave dictation"}
# verbatim-typing prefixes that work even when dictation mode is OFF.
_DICT_TYPE = re.compile(r"^(?:type|dictate|insert|write down)[,:]?\s+(.+)$", re.I)
_DICT_SEND = re.compile(
    r"^(?:send|tell claude|tell cloud|message claude|say to claude|relay)[,:]?\s+(.+)$",
    re.I)


def _dictation_action(text: str, mode: bool):
    """Decide how an utterance maps to dictation. Returns one of:
    ("start",None) | ("stop",None) | ("type",(verbatim, send_enter)) | None.
    Preserves original casing (verbatim) for typing."""
    t = (text or "").strip()
    low = t.lower().rstrip(".!?")
    if low in _DICT_START:
        return ("start", None)
    if low in _DICT_STOP:
        return ("stop", None)
    m = _DICT_SEND.match(t)
    if m:
        return ("type", (m.group(1).strip(), True))
    m = _DICT_TYPE.match(t)
    if m:
        return ("type", (m.group(1).strip(), False))
    if mode:  # continuous dictation: everything is typed and sent
        return ("type", (t, True))
    return None


def _is_complex(text: str) -> bool:
    """Natural-language / multi-step requests a reasoning agent should handle."""
    t = " " + text.lower().strip() + " "
    if len(t.split()) > 7:
        return True
    if any(m in t for m in _VISION_MARKERS):
        return True
    if any(m in t for m in _CONVERSATIONAL_MARKERS):
        return True
    return any(m in t for m in _COMPLEX_MARKERS)


def _log(cfg: Config, role: str, text: str) -> None:
    if not cfg["runtime"].get("log_transcript"):
        return
    p = Path(os.path.expanduser(cfg["runtime"]["transcript_path"]))
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{role}\t{text}\n")


def cli_confirm(speaker) -> Callable[[str], bool]:
    def confirm(prompt: str) -> bool:
        speaker.say(prompt + ". Say yes to confirm, or press y.")
        try:
            return input(f"[confirm] {prompt}  [y/N]: ").strip().lower() in ("y", "yes")
        except EOFError:
            return False
    return confirm


def gui_confirm(_speaker=None) -> Callable[[str], bool]:
    def confirm(prompt: str) -> bool:
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
            ans = messagebox.askyesno("VoiceClaw — confirm", prompt)
            root.destroy()
            return bool(ans)
        except Exception:
            return False
    return confirm


def _select_brain(cfg: Config, toolbox: Toolbox):
    """Choose the agent backend per cfg.brain.backend. Returns (brain, mode, message).

    backend: auto | anthropic | openai | claude_code
      auto = Anthropic API key -> OpenAI-compatible key -> Claude Code (subscription)
    """
    # Anthropic API key
    client, mode, message = auth.make_client(cfg)
    api_brain = None
    if client is not None:
        api_brain = ClaudeBrain(
            client=client, model=cfg["brain"]["model"],
            max_tokens=cfg["brain"]["max_tokens"], toolbox=toolbox,
            max_iterations=cfg["agent"]["max_tool_iterations"])

    # OpenAI-compatible (OpenAI / Groq / OpenRouter / local)
    ocfg = cfg["brain"].get("openai", {}) or {}
    openai_brain = None
    try:
        okey = (os.environ.get(ocfg.get("api_key_env", "OPENAI_API_KEY"))
                or ocfg.get("api_key") or "")
        if not okey:
            try:
                from . import credentials_store as _store
                okey = _store.load("openai_key") or ""
            except Exception:
                okey = ""
        if okey:
            from .openai_brain import OpenAIBrain
            openai_brain = OpenAIBrain(
                okey, ocfg.get("model", "gpt-4o-mini"), toolbox,
                base_url=ocfg.get("base_url", ""),
                max_iterations=cfg["agent"]["max_tool_iterations"])
    except Exception as _oe:
        openai_brain = None
        try:
            from .issues import log_issue
            log_issue("openai.init", _oe)
        except Exception:
            pass

    # Claude Code (personal subscription)
    cc = None
    try:
        from .claude_code_brain import ClaudeCodeBrain
        _cc = ClaudeCodeBrain()
        cc = _cc if _cc.available() else None
    except Exception:
        cc = None

    backend = (cfg["brain"].get("backend") or "auto").lower()
    if backend in ("anthropic", "api"):
        brain = api_brain
    elif backend == "openai":
        brain = openai_brain
    elif backend == "claude_code":
        brain = cc
    else:
        brain = api_brain or openai_brain or cc

    if brain is None:
        return None, "none", message
    if brain is cc:
        return brain, "claude_code", "Using Claude Code (your Claude subscription)."
    if brain is openai_brain:
        return brain, "openai", \
            f"Using OpenAI-compatible model ({ocfg.get('model', 'gpt-4o-mini')})."
    return brain, mode, message


def build(cfg: Config, confirm_cb: Optional[Callable[[str], bool]] = None) -> Assistant:
    if cfg["tts"]["enabled"] and tts_mod.tts_available():
        try:
            speaker = tts_mod.Speaker(cfg["tts"]["rate"], cfg["tts"]["voice"])
        except Exception:
            speaker = tts_mod.PrintSpeaker()
    else:
        speaker = tts_mod.PrintSpeaker()

    confirm = confirm_cb or cli_confirm(speaker)

    toolbox = Toolbox(
        allowed_paths=cfg.allowed_paths,
        confirm_patterns=cfg["agent"]["confirm_patterns"],
        confirm_cb=confirm, speak_cb=getattr(speaker, "say", None))
    skills = LocalSkills(enabled=True)
    try:
        from .plugins import load_plugins
        loaded = load_plugins(skills, toolbox)
        if loaded:
            print(f"[plugins] loaded: {', '.join(loaded)}")
    except Exception:
        pass

    local = LocalLLM(cfg["local_llm"]["base_url"], cfg["local_llm"]["model"])
    router = Router(local, fast_path_max_words=cfg["local_llm"]["fast_path_max_words"],
                    local_enabled=cfg["local_llm"]["enabled"])

    local_agent = None
    if cfg["local_llm"].get("enabled", True) and cfg["local_llm"].get("agent", True):
        local_agent = LocalBrain(
            base_url=cfg["local_llm"]["base_url"],
            model=cfg["local_llm"].get("agent_model") or cfg["local_llm"]["model"],
            toolbox=toolbox, max_iterations=cfg["agent"]["max_tool_iterations"])

    resources = ResourceManager(idle_seconds=cfg["runtime"]["idle_unload_seconds"])
    resources.start()

    brain, mode, message = _select_brain(cfg, toolbox)

    learn_cfg = getattr(cfg, "data", {}).get("learning", {}) if hasattr(cfg, "data") else {}
    learned = LearnedSkills(enabled=learn_cfg.get("enabled", True))

    return Assistant(cfg, speaker, router, skills, toolbox, brain,
                     resources=resources, local_agent=local_agent, learned=learned,
                     auth_mode=mode, auth_message=message)