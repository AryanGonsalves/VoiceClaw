# VoiceClaw

A lightweight, always-listening **voice agent for your PC**. Say a wake word,
talk naturally, and it answers out loud *and acts on your computer* — opening
apps, navigating UIs (e.g. "next video" on YouTube Shorts), managing files,
searching the web, and running multi-step tasks.

**Three-tier hybrid brain:** instant on-device control commands, a small local
model (Ollama) for quick questions, and the full Claude agent for anything
complex. The client is featherweight and built to run 24/7 — only the wake-word
listener runs while idle, and heavy models unload themselves when not in use.

> Full architecture, roadmap, and function catalog: `docs/DESIGN.md`.
> Dense machine-readable project state (for seeding an AI dev chat): `CONTEXT.md`.

## What it can do

- **Instant local control** (no cloud): "next video", "scroll down", "volume up",
  "mute", "play/pause", "close tab", "refresh", "open chrome".
- **Quick answers** via a local model when available.
- **Full agent tasks** via Claude: "find every PDF in Documents", "search the web
  for tomorrow's weather and tell me if I need an umbrella", "create notes.txt on
  my Desktop with my shopping list".

## Modes & graceful degradation

Runs at whatever level your machine supports; missing libraries drop you a tier
instead of crashing.

| Mode | Needs | What you get |
|---|---|---|
| `voice` | openWakeWord + faster-whisper + sounddevice | Full hands-free loop |
| `ptt` | faster-whisper + sounddevice | Push-to-talk (Enter, speak) |
| `hotkey` | + pynput | Global push-to-talk hotkey (no wake word) |
| `text` | nothing extra | Type requests, hear/print replies |

## Setup

```bash
cd voice-claude
python -m venv .venv
# Windows:  .venv\Scripts\activate   | mac/Linux: source .venv/bin/activate

pip install anthropic pyyaml requests   # minimum (text mode + Claude)
pip install -r requirements.txt         # full voice + control + tray
cp config.example.yaml config.yaml      # then edit
```

## Choosing how the smart agent is powered

VoiceClaw has two layers:

- **Free local tier (no account):** wake word, open/close apps, web & YouTube search,
  media keys, on-device speech recognition. Works offline, for everyone.
- **Smart agent (bring your own API key):** reasoning, vision, and multi-step
  "click on Shorts" computer use. Pick any provider:

| Provider | `brain.backend` | Key | Notes |
|---|---|---|---|
| Anthropic | `anthropic` / `auto` | `ANTHROPIC_API_KEY` | Claude models |
| OpenAI / Groq / OpenRouter | `openai` / `auto` | `OPENAI_API_KEY` | set `brain.openai.base_url` for Groq/OpenRouter; use a vision model (e.g. `gpt-4o`) for clicking |
| Claude Code (personal only) | `claude_code` | your `claude` login | uses your Claude subscription — **personal use only**, see note below |

`auto` uses whatever key is present (Anthropic → OpenAI → Claude Code).

**Easiest way to add a key:** launch the app (`python -m voiceclaw.ui`) → **Account**
tab → the matching "Sign in" button. Keys are stored in your OS keychain. (You can also
set the env var or edit `config.yaml`.)

> ### Distribution & the Claude subscription — important
> Anthropic does **not** permit third‑party products to offer claude.ai / subscription
> login — and this includes routing through **Claude Code or the Agent SDK** — even if
> each user signs into their *own* account, unless you have prior approval from
> Anthropic. So if you publish VoiceClaw (e.g. on GitHub), ship it as
> **bring‑your‑own API key** (Anthropic, or OpenAI/Groq/OpenRouter). The `claude_code`
> backend is for **your own personal use on your own machine only** — don't make it the
> sign‑in path in a distributed build.

## Wake word (toggle / "either")

Set one or more built-in wake words in `config.yaml` — enable several to let users
say **any** of them:

```yaml
wakeword:
  models: ["hey_jarvis", "alexa"]   # say either one
  custom_model_path: ""             # path to a trained model (see below)
```

Built-ins: `hey_jarvis`, `alexa`, `hey_mycroft`. For a **real "Hey Claude"** wake word, set `wakeword.engine: porcupine` and supply a Picovoice `.ppn` (free console) — or train an openWakeWord model. Full steps: `docs/WAKEWORD.md`.

## Run

```bash
python main.py                 # auto-picks voice / ptt / text
python main.py --mode text     # force a mode
setup.bat / run.bat            # Windows: one-time setup, then launch the app
python -m voiceclaw.ui       # companion desktop app (pip install PySide6)
python main.py --mode hotkey   # global push-to-talk, no wake word
python -m voiceclaw.tray     # background system-tray app (pip install pystray pillow)
python install_autostart.py    # launch automatically at login (--remove to undo)
#   (registers a Startup shortcut; toggle it anytime in Task Manager > Startup apps)
```

## Plugins & extras

VoiceClaw is extensible: drop a `.py` file in `~/.voiceclaw/plugins/` to add new voice commands and Claude tools — see `docs/PLUGINS.md` and `samples/plugins/example_plugin.py`. Manual test plan: `docs/TESTING.md`. Build a Windows installer: `packaging/BUILD.md` (+ `packaging/installer.iss`).

## Companion app & global hotkeys

An optional **desktop app** (PySide6) makes setup and monitoring friendly — it is *not* required for the agent to work (like the NVIDIA app). Launch it with `python -m voiceclaw.ui`. Dark, production-style; tabs:

- **Dashboard** — live status (backend, listening state, last command), a recent-activity feed, and a **command tester** that shows where any phrase would route (learned / Tier-1 / agent / dictation) without using the mic.
- **Account** — sign in (subscription / API key / OpenAI), backend selector, status.
- **Settings** — wake word(s), microphone, voice rate, hotkeys, idle-unload, allowed folders, learning toggle. Saves to `config.yaml`.
- **Learned** — manage the personalized learned-command cache: search, delete individual entries, or forget all.
- **Logs** — recent issues/failures.

The header has **Start/Stop listening**, a **Dictation** toggle, and a **Developer console** checkbox — an in-app live-output pane (hidden by default for a clean production look, on-demand for devs) that replaces needing the external cmd window.

**Global hotkeys** (work in any app, via `pynput`): push-to-talk captures a command (`<ctrl>+<alt>+space`), a kill-switch stops listening (`<ctrl>+<alt>+q`), and **hold-to-dictate** (default **Right Ctrl**) types what you say into the focused window. Change them in Settings or `config.yaml`.

To package a single Windows `.exe`, see `packaging/BUILD.md`.

## How requests are routed

1. **Learned cache** — if you've said this before and the agent resolved it with
   deterministic actions, it replays **instantly** (personalized, offline, free).
2. **Local skills** — clear, literal control commands run instantly via a tight
   phrase→action grammar. If a match looks low-confidence it *declines* and falls
   back to the agent **rather than running the wrong thing**.
3. **Local model** — short factual/chit-chat questions go to Ollama if running.
4. **Agent** — conversational, multi-step, web, files, and on-screen (vision)
   requests escalate to the full tool-use loop. It **observes the screen before and
   after each action** (keeping only the latest screenshot in context) so it acts on
   real state instead of guessing, and can **ask a follow-up** via an on-screen
   overlay (the `ask_user` tool) instead of guessing.

### Learning from the agent
When the agent resolves a new phrasing with deterministic actions (open a URL/app,
close an app, a keypress, a scroll), that phrasing is **learned** and becomes instant
next time — so the fast path grows to fit *your* speech patterns. Vision clicks are
never cached (they depend on screen position). Clear the cache anytime via
**Settings → "Forget all learned commands"**, the tray menu, or
`python main.py forget-learned`.

### Dictation / relay (talk to your dev agent)
VoiceClaw can also **type what you say into the focused window** — handy for
driving a coding assistant (Cowork, Codex, Claude Code) or any editor by voice:

- **"type \<text\>"** — types the text where your cursor is (no Enter).
- **"tell Claude \<text\>"** / **"send \<text\>"** — types it **and presses Enter**
  (e.g. *"tell Claude, continue"*, *"send do all the suggested tasks"*).
- **"start dictation"** … **"stop dictation"** — continuous mode: everything you say
  is typed + sent until you stop. Toggle it from the tray ("Dictation mode") or the
  app header too.
- **Hold-to-dictate hotkey** (default **Right Ctrl**): hold it, speak, release — your
  words are typed into the focused window (and sent). The fastest way to drive a dev
  agent hands-free.

In dictation mode your words are relayed verbatim, not interpreted as PC commands.

## Low-consumption design

Only the wake-word listener runs while idle. Whisper is **lazy-loaded** on first
use and **unloaded** after `runtime.idle_unload_seconds` of inactivity, so resident
RAM falls back toward the wake-word footprint between interactions.

## Safety

On-device wake word + STT (only escalated text leaves the machine); confirmation
gates for destructive shell/file actions; file tools scoped to `agent.allowed_paths`;
full transcript at `~/.voiceclaw/transcript.log`; pause/quit from the tray.

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q        # 83 tests incl. a 55-command routing eval; CI on Python 3.10–3.12
```

## Licensing & distribution

Proprietary (see `LICENSE`). The product is **open-core**: this repo is the public shell; the proprietary grammar + learned-cache (`voiceclaw/core/`) are kept private and shipped only as compiled binaries. See `docs/OPEN_CORE.md`.

## Project layout

```
voice-claude/
├── main.py                 # CLI entry: mode select + run loops
├── install_autostart.py    # login auto-start (Win/macOS/Linux)
├── app_entry.py            # windowed entry for the packaged .exe
├── packaging/              # PyInstaller spec + BUILD.md
├── requirements.txt / requirements-dev.txt / pytest.ini / .gitignore
├── config.example.yaml
├── CONTEXT.md              # dense project state for AI dev chats
├── docs/DESIGN.md          # architecture, roadmap, bugs, function catalog
├── .github/workflows/ci.yml
├── tests/                  # pytest suite (83 tests + routing_eval)
└── voiceclaw/
    ├── app.py              # assembly + tiered request handling (shared core)
    ├── learned_skills.py   # personalized learned-command cache (agent->fast path)
    ├── config.py           # config + env overrides
    ├── auth.py             # API-key / subscription credential providers
    ├── credentials_store.py# secure storage (OS keychain + file fallback)
    ├── login.py            # `login`/`logout`/`status` flow
    ├── hotkeys.py          # global push-to-talk / kill-switch (pynput)
    ├── issues.py           # failures log for the UI
    ├── overlay.py          # on-screen clarify dialog (ask_user)
    ├── plugins.py          # community plugin loader
    └── ui.py               # PySide6 companion desktop app
    ├── audio.py            # mic capture + endpointing + chime
    ├── wakeword.py         # openWakeWord listener (multi/custom)
    ├── stt.py              # faster-whisper (lazy + unloadable)
    ├── tts.py              # pyttsx3 speech (+ print fallback)
    ├── local_skills.py     # Tier 1: rule-based local control (no LLM)
    ├── local_llm.py     