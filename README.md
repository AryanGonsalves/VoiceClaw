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

## Download & install

Grab a prebuilt Windows app from the [**Releases**](https://github.com/AryanGonsalves/VoiceClaw/releases)
page — no Python setup required:

- **VoiceClaw-Setup-0.1.0.exe** — one-click installer: Start Menu + desktop
  shortcuts, optional auto-start at sign-in, and a clean uninstaller.
- **VoiceClaw-portable.zip** — unzip anywhere and run `VoiceClaw.exe`; no install,
  lowest SmartScreen friction.

> VoiceClaw isn't code-signed yet, so Windows may show **"Windows protected your
> PC."** That's expected for a brand-new indie app — click **More info → Run
> anyway**. Prefer to run from source instead? See [Setup](#setup) below.

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

## How it works — the tiered brain

Every request flows through four tiers, cheapest first. A request only falls through
to the next tier when the current one can't handle it confidently, so the common case
stays **instant and offline** and the cloud agent is reserved for genuinely hard tasks.

| Tier | Handles | Latency | Cost / privacy |
|---|---|---|---|
| **0 · Learned cache** | phrasings you've used before that resolved to fixed actions | instant | local, free |
| **1 · Local skills** | literal control commands ("open chrome", "next video", "volume up") | instant | local, free |
| **2 · Local model** | short factual / chit-chat questions (via Ollama, if running) | fast | local, free |
| **3 · Agent** | multi-step, web, files, reasoning, on-screen vision | seconds | your API key |

**Tier 1 — local skills.** A tight phrase→action grammar maps spoken control commands
straight to keystrokes, app launches, URL opens, and window/media controls — no model
in the loop. Crucially, if a phrase only *looks* like a command but the match is
low-confidence, Tier 1 **declines and escalates** rather than firing the wrong action.
Doing the wrong thing silently is worse than taking the slow path.

**Tier 3 — the agent.** Conversational, multi-step, web, file, and on-screen requests
escalate to a full tool-use loop. It **observes the screen before and after each
action** (keeping only the latest screenshot in context) so it acts on real state
instead of guessing, and it can **ask a follow-up question** through an on-screen
overlay (the `ask_user` tool) when a request is ambiguous.

### Learning — turning slow agent tasks into instant ones

This is the part that makes VoiceClaw get **faster the more you use it**.

When the agent (Tier 3) handles a request, it doesn't just act — it records the
**sequence of deterministic primitives** it used to satisfy you: open this URL, launch
that app, send these keystrokes, scroll here. If the whole task reduces to such
repeatable primitives, VoiceClaw **caches the result against a normalized form of what
you said** and promotes it to Tier 0. The next time you say it — or say it a little
differently — it replays **instantly, offline, and free**, with no model call at all.

A few design choices keep this useful rather than brittle:

- **It learns from complex tasks, not just one-liners.** Even a request the agent had
  to reason through multiple steps gets distilled down to its deterministic action
  sequence and cached — so the *outcome* of expensive reasoning becomes a one-shot fast
  path you never pay for again.
- **Normalization beats your exact words.** Filler, casing, and small phrasing
  differences are folded together, so "open my email", "open email", and "open up my
  email" all land on the same learned entry instead of each paying the slow path.
- **Position-dependent steps are never cached.** Anything that depended on *where*
  something sat on screen (a vision click at some pixel) is deliberately left out — it
  would break the instant a window moved, so those always re-run live through the agent.
- **It's personal and local.** The cache reflects *your* speech and *your* apps, lives
  on your machine, and never leaves it.

Clear it anytime via **Settings → "Forget all learned commands"**, the tray menu, or
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
voiceclaw-app/
├── main.py                 # CLI entry: mode select + run loops
├── app_entry.py            # windowed entry for the packaged .exe
├── install_autostart.py    # login auto-start (Win/macOS/Linux)
├── make_shortcuts.py       # desktop / Start-Menu shortcut helper
├── packaging/              # PyInstaller spec, Inno Setup script + BUILD.md
├── docs/                   # DESIGN, WAKEWORD, PLUGINS, TESTING, OPEN_CORE
├── samples/plugins/        # example community plugin
├── tests/                  # pytest suite (83 tests + routing_eval)
├── requirements.txt / requirements-dev.txt / pytest.ini / .gitignore
├── config.example.yaml
└── voiceclaw/
    ├── app.py              # assembly + tiered request handling
    ├── router.py           # tier dispatch (learned → local → model → agent)
    ├── learned_skills.py   # personalized learned-command cache (public shim)
    ├── local_skills.py     # Tier 1: rule-based local control (public shim)
    ├── local_llm.py        # Tier 2: local model (Ollama) bridge
    ├── local_agent.py      # on-device fallback agent loop
    ├── brain.py            # Anthropic (Claude) agent backend
    ├── openai_brain.py     # OpenAI / Groq / OpenRouter backend
    ├── claude_code_brain.py# Claude Code backend (personal use only)
    ├── tools.py            # agent tool implementations (apps, files, keys, vision)
    ├── mcp_server.py       # expose VoiceClaw tools over MCP
    ├── config.py           # config + env overrides
    ├── auth.py             # API-key / subscription credential providers
    ├── credentials_store.py# secure storage (OS keychain + file fallback)
    ├── login.py            # login / logout / status flow
    ├── hotkeys.py          # global push-to-talk / kill-switch (pynput)
    ├── issues.py           # failures log for the UI
    ├── overlay.py          # on-screen clarify dialog (ask_user)
    ├── overlay_ring.py     # listening-state visual ring
    ├── plugins.py          # community plugin loader
    ├── resources.py        # bundled assets / paths
    ├── audio.py            # mic capture + endpointing + chime
    ├── audio_ducker.py     # lowers other audio while listening
    ├── wakeword.py         # openWakeWord listener (multi/custom)
    ├── stt.py              # faster-whisper (lazy + unloadable)
    ├── tts.py              # pyttsx3 speech (+ print fallback)
    ├── tray.py             # background system-tray app
    ├── ui.py               # PySide6 companion desktop app
    └── core/               # PRIVATE moat — grammar + learned cache (shipped compiled)
```
