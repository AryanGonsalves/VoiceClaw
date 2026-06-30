# VoiceClaw — Design, Architecture & Project Plan

A hands-free, always-listening voice agent for your PC. Say a wake word, talk
naturally, and it answers out loud *and acts on your machine* — opening apps,
navigating UIs, managing files, searching the web, running multi-step tasks.

> **One honest framing.** "Full Claude, lightweight, local" is two layers. The
> *intelligence* of full Claude is a large cloud model reached over the Anthropic
> API — it can't be shrunk onto a consumer PC. What **does** run lightweight 24/7
> is the **client**: a small background process that listens, transcribes, routes,
> acts, and speaks. VoiceClaw is that client plus a **three-tier hybrid brain**.

---

## 1. Goals

- **Always-on, low-consumption.** Idle CPU near zero; only the wake-word listener
  runs while idle. Heavy parts load on demand and unload when idle.
- **Cross-platform.** Windows, macOS, Linux from one codebase; OS-specific control
  behind a thin abstraction.
- **Hybrid intelligence (three tiers).** Local rules → local model → Claude API.
- **Agentic.** A real tool-use loop that can open apps, run shell, read/write
  files, search/fetch the web, automate the keyboard/mouse, and chain steps.
- **Private & safe by default.** On-device wake word + STT, confirmation gates for
  destructive actions, path scoping, full auditable transcript.

## 2. The three-tier brain  *(updated)*

Every request is handled by the cheapest tier that can do the job:

```
                       ┌───────────────────────────────────────────────┐
  "Hey Claude, …"  ──▶ │  Tier 1 · Local skills (rules)                 │  instant · offline · free
                       │    next video, scroll, volume, play/pause,     │
                       │    open app, tabs, refresh …                   │
                       └───────────────┬───────────────────────────────┘
                                       │ no match
                                       ▼
                       ┌───────────────────────────────────────────────┐
                       │  Tier 2 · Local LLM (Ollama)                   │  fast · offline · free
                       │    short factual / chit-chat answers           │
                       └───────────────┬───────────────────────────────┘
                                       │ escalate / low-confidence
                                       ▼
                       ┌───────────────────────────────────────────────┐
                       │  Tier 3 · Claude API agent (tool-use loop)     │  full power · cloud
                       │    reasoning, web, files, multi-step Cowork     │
                       └───────────────────────────────────────────────┘
```

**Why a local control tier exists.** You don't need an LLM to press the Down
arrow. Tier 1 is a small phrase→action grammar (`local_skills.py`) that maps
direct commands straight to tool calls — no network, no API cost, sub-50ms. This
is the "lightweight local control agent." Tiers 2–3 handle anything that needs
language understanding or reasoning.

## 3. The voice loop

1. **Idle listen** — tiny wake-word model scans mic audio (the only always-on cost).
2. **Wake** — on the wake word, play a chime, start capturing.
3. **Capture + endpoint** — record until silence (energy-based VAD).
4. **Transcribe** — local Whisper → text.
5. **Route** — Tier 1 → Tier 2 → Tier 3 as above.
6. **Act** — execute tools (Tier 3 loops until done).
7. **Speak** — TTS reads the reply; transcript logged.
8. Back to idle.

## 4. Worked example — "Claude, scroll to next video" (YouTube Shorts)

This is handled entirely **locally**, instantly:

1. Wake word → record → Whisper transcribes "scroll to next video".
2. `LocalSkills.handle()` matches the `next video` rule.
3. It calls the `press_keys` tool with `down` — the Shorts "next" shortcut.
4. The focused browser advances to the next short; VoiceClaw says "Next."

No cloud round-trip, no API cost. The same path covers "previous", "scroll
down/up", "volume up", "mute", "play/pause", "close tab", "refresh", and
"open <app>". A request like "find the funniest cooking short and save its link"
would instead fall through to Tier 3, where Claude uses web/file tools.

> Caveat: keystroke control assumes the right window is focused and that the app
> uses standard shortcuts. More robust, app-aware control (vision-based clicking,
> per-site adapters) is on the roadmap (§8).

## 5. Components

| Layer | Default tech | Footprint |
|---|---|---|
| Wake word | openWakeWord | tens of MB, ~1–3% of one core idle |
| Speech-to-text | faster-whisper (`base`) | ~150 MB, loaded on demand |
| Text-to-speech | pyttsx3 (→ Piper later) | minimal |
| Tier 1 control | `local_skills.py` (regex grammar) | negligible |
| Tier 2 local LLM | Ollama (`llama3.2:3b`) | loads on demand; idle = 0 |
| Tier 3 brain | Anthropic API (Claude) | network only |
| PC control | `pyautogui`, `subprocess`, `psutil` | minimal |
| Tray / autostart | pystray + Pillow | minimal |

## 6. Function catalog

**Claude tools** (`tools.py`): `run_shell`, `open_app`, `list_files`,
`search_files`, `read_file`, `write_file`, `type_text`, `press_keys`, `scroll`,
`system_info`, `web_search`, `fetch_url`.

**Local skills** (`local_skills.py`, no LLM needed):

| Say | Action |
|---|---|
| "next / skip (video)" | Down arrow |
| "previous / go back" | Up arrow |
| "scroll down / up" | mouse scroll |
| "page down / up", "top", "bottom" | PageDown/PageUp/Home/End |
| "play / pause / stop" | media play-pause |
| "next / previous track" | media track keys |
| "volume up / down", "mute" | media volume keys |
| "close tab", "new tab", "switch tab" | Ctrl+W / Ctrl+T / Ctrl+Tab |
| "refresh / reload", "fullscreen" | F5 / f |
| "open <app>" | launch application |

## 7. Safety & privacy

- On-device wake word + STT; only transcribed text of *escalated* requests leaves
  the machine.
- Confirmation gates for destructive shell commands and file writes (terminal
  prompt in CLI, desktop dialog in tray).
- File tools scoped to `agent.allowed_paths` (home dir by default).
- Auditable transcript at `~/.voiceclaw/transcript.log`.
- Pause/quit from the tray; (planned) global kill-switch hotkey.

## 8. Roadmap / future ideas

**Near term (v1)**
- ✅ System-tray background app + login auto-start *(done)*
- ✅ Local control-skill tier *(done)*
- Custom **"Hey Claude"** wake word (train an openWakeWord model) *(deferred by request)*
- Global push-to-talk / kill-switch hotkey
- Idle unload of Whisper/Ollama after `runtime.idle_unload_seconds`
- Piper TTS option for a more natural voice
- Per-utterance "barge-in" (interrupt TTS by speaking)

**Mid term (v2)**
- Vision-based GUI control (screenshot → locate element → click) for robustness
  beyond fixed keyboard shortcuts
- Per-app / per-site adapters (YouTube, Spotify, Slack, VS Code) with richer verbs
- Persistent long-term memory + user preferences
- Streaming STT + streaming TTS to cut latency
- On-screen overlay showing what it heard / is doing

**Long term (v3)**
- Skill/plugin marketplace so the community can add verbs and app adapters
- Multiple wake words / multi-user voice profiles
- Multi-device handoff (start on PC, continue on phone)
- Optional fully-local mode (local STT+LLM+TTS) for offline-only users

## 9. Known issues / bugs to watch

- **Tier-1 over-matching.** Broad rules can misfire — e.g. "stop the download"
  contains "stop" and may trigger media play-pause. Needs tighter intent scoping
  or a confidence/clarify step.
- **"open <app>" naming.** "open the calculator" passes "the calculator" to the
  launcher; needs stop-word stripping and an app-name alias table.
- **Focus assumption.** Keystroke/scroll commands act on whatever window is
  focused; no check that the intended app is in front.
- **Endpointing.** Energy-based VAD can cut off slow talkers or trail on noise;
  a proper VAD model would help.
- **`_press` masks tool errors.** Local skill confirmations report success even if
  the underlying keypress failed (e.g. pyautogui missing).
- **Wake-word false triggers.** Tunable via `threshold`; custom model will help.
- **Cost.** Tier-3 usage scales with use; the lower tiers exist partly to contain it.

## 10. Making it a community project (GitHub)

This is structured to grow into an open project:

- **Modular layout** — each capability is its own file, so contributors can own
  `wakeword`, `stt`, `tools`, `local_skills`, etc. independently.
- **Good first issues** — add a local skill, add an app adapter, add a TTS/STT
  backend, improve VAD, write tests.
- **Suggested repo scaffolding to add:** `LICENSE` (MIT?), `CONTRIBUTING.md`,
  `CODE_OF_CONDUCT.md`, GitHub Actions CI running `py_compile` + tests, issue/PR
  templates, a `tests/` suite, and a plugin interface so skills are drop-in.
- **Naming/branding** — pick a project name (VoiceClaw is a working title;
  Anthropic trademark considerations apply if "Claude" is in the public name).
- **Security posture** — because it can run shell commands, document the threat
  model and keep confirmation gates on by default; never ship with an embedded
  API key.

---

*Status: v0 prototype implementing tiers 1–3, voice loop, tray + autostart, and a
cross-platform tool set. See the top-level `README.md` for setup and run steps.*

---

## Addendum — v0.1.0 updates

**Authentication (two paths).** A pluggable credential layer (`auth.py`) supports
either an **Anthropic API key** (x-api-key) or a **Claude Pro/Max subscription**
via Anthropic's *official* OAuth token (`claude setup-token` →
`CLAUDE_CODE_OAUTH_TOKEN`, sent as a Bearer token). `brain.auth` selects
`auto`/`api_key`/`subscription`. The subscription path uses only the official
token — never claude.ai web-session cookies, which would violate Anthropic's ToS.

**Idle model unloading (the "lightweight 24/7" mechanism).** `resources.py`
defines an `Unloadable` protocol (`last_used`/`is_loaded`/`unload`) and a
`ResourceManager` watchdog thread. Whisper (`stt.Transcriber`) is now lazy-loaded
on first use and unloaded after `runtime.idle_unload_seconds`, so resident RAM
falls back toward the wake-word footprint between interactions. (Ollama runs as a
separate process and unloads its own models, so nothing to unload in-process.)

**Wake-word toggle.** `wakeword.models` is now a list — enable several built-ins
and the user can say any of them. `wakeword.custom_model_path` loads a trained
model. *Note:* there is no built-in "claude" model; waking on the literal word
"Claude"/"Hey Claude" requires a trained model (openWakeWord training or Picovoice
Porcupine custom keyword). Tracked as a deferred roadmap item.

**Tests + CI.** A `tests/` pytest suite (40 tests) covers local skills (incl. the
over-matching guards), routing, config, tools (path scoping + confirm gates),
auth resolution, and idle-unloading. GitHub Actions (`.github/workflows/ci.yml`)
byte-compiles and runs the suite on Python 3.10–3.12.

**Dev note — cross-filesystem write glitch.** During development, writing code via
the Windows file tool occasionally injected NUL bytes / truncated files. Mitigation:
write code files through the sandbox shell (heredoc) directly to the mounted path,
and always `py_compile` + `pytest` after edits. Recorded in `CONTEXT.md`.

**Roadmap status:** tray+autostart ✅, local control tier ✅, idle-unload ✅,
API-key + subscription auth ✅, wake-word toggle ✅. Still open: custom "Hey Claude"
wake word (deferred), global PTT/kill hotkey, Piper TTS, vision-based GUI control.

---

## Addendum — login UX (v0.1.0+)

A built-in sign-in removes the env-var friction for subscribers:

- `voiceclaw/credentials_store.py` — stores credentials in the OS keychain
  (via optional `keyring`), falling back to `~/.voiceclaw/credentials.json`
  at `0600`. Keys: `oauth_token` (subscription), `api_key`.
- `voiceclaw/login.py` — `login` runs Anthropic's official `claude setup-token`
  OAuth flow (captures or accepts the printed token), `login --api-key` stores a
  key, plus `status`/`logout`. CLI: `python main.py login|status|logout`.
- `auth.py` now resolves credentials **env → config → keychain**, so a stored
  login is picked up automatically.
- `Assistant.reload_auth()` rebuilds the brain at runtime, so the tray
  **"Sign in…"** dialog activates Claude without a restart.

Still ToS-bound: subscription auth uses only the official OAuth token; claude.ai
web-session cookies are never used (would get users banned and sink a public
project — explicitly out of scope).

---

## Addendum — global hotkeys + companion app (v0.1.0+)

**Global hotkeys** (`hotkeys.py`, via `pynput`). System-wide, focus-independent:
push-to-talk (`<ctrl>+<alt>+space`) captures one command on demand; kill-switch
(`<ctrl>+<alt>+q`) stops the loop. `WakeWordListener.wait_for_wake(interrupt=…)`
is now interruptible, so in `voice` mode PTT acts like a manual wake and the
kill-switch breaks out promptly. New `hotkey` run mode = no wake word, PTT-only.

**Microphone selection.** `audio.list_input_devices()` + `audio.Microphone(device=)`
and `config.audio.input_device`, surfaced in the UI's Settings tab.

**Companion desktop app** (`ui.py`, PySide6) — optional, NVIDIA-app-style:
Account (sign-in via the official token flow), Settings (wake words, mic, voice,
hotkeys, idle-unload, folders → saved to `config.yaml`), and Logs (from
`issues.py`). A header Start/Stop runs the agent in a worker thread; tool
confirmations are marshalled to the GUI thread via a `ConfirmBridge` (Qt signal).
The agent works headless too — the UI is convenience, not a dependency.

**Issues log** (`issues.py`). Failures from the brain and tools are appended to
`~/.voiceclaw/issues.log` (capped, TSV) and shown in the Logs tab.

**Packaging.** `app_entry.py` is the windowed entry (UI → tray → CLI fallback);
`packaging/VoiceClaw.spec` + `packaging/BUILD.md` build a single Windows app
with PyInstaller (onedir; must run on Windows).

**Roadmap status:** global PTT/kill-switch ✅, companion UI ✅, mic selection ✅,
issues log ✅. Still open: custom "Hey Claude" wake word (deferred), Piper TTS,
vision-based GUI control, installer (Inno Setup) wrapping the onedir build.

---

## Addendum — overlay, plugins, packaging & QA (v0.1.0+)

**Disambiguation overlay** (`overlay.py`, tkinter — no extra deps). A small
top-most clarify dialog. Exposed to Claude as the **`ask_user`** tool, so when a
request is ambiguous the agent asks one follow-up (with optional choices) instead
of guessing. Headless-safe (returns None, never raises). The toolbox speaks the
question via `speak_cb`.

**Plugin system** (`plugins.py`). Drop a `.py` into `~/.voiceclaw/plugins/`
exposing `register(reg)`; `reg.add_skill(pattern, handler)` adds a Tier-1 rule and
`reg.add_tool(schema, impl)` adds a Claude tool. Tools register via
`Toolbox.register_tool` (`extra_tools`/`extra_schemas`, merged into the brain's
tool list); skills via `LocalSkills.add_rule`. Failures are logged, never fatal.
See `docs/PLUGINS.md` and `samples/plugins/example_plugin.py`.

**Microphone selection.** `config.audio.input_device` + UI picker, threaded into
`Microphone(device=)` and the wake-word stream.

**QA / packaging.** `docs/TESTING.md` is the on-device manual checklist (mic,
audio, hotkeys, GUI, sign-in). `packaging/installer.iss` (Inno Setup) wraps the
PyInstaller onedir build into a per-user Windows installer with optional autostart.

**GitHub readiness.** MIT `LICENSE`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`,
issue/PR templates under `.github/`, CI in `.github/workflows/ci.yml`.

**Testing status:** 61 automated tests (logic + 5 end-to-end integration routing
tests with mocks). Hardware/GUI paths covered by `docs/TESTING.md`.

**Dev note (recurring):** rewriting larger files directly on the Windows mount
occasionally truncates them. Mitigation now standardized: write to a sandbox temp
file, `py_compile`, then copy onto the mount and re-verify. Recorded in CONTEXT.md.

---

## Addendum — "Hey Claude", Tier-1 clarify, release (v0.1.0)

**Wake-word engines.** `wakeword.py` now supports two interchangeable engines
behind `make_listener(cfg)`: openWakeWord (default, free/offline) and **Picovoice
Porcupine** for a real **"Hey Claude"** keyword (`.ppn` from the free console +
access key). `_choose_engine()` selects and gracefully falls back. See
`docs/WAKEWORD.md`.

**Tier-1 clarify.** A bare "open"/"launch"/"start" with no target now triggers the
overlay ("Open what?") and launches the answer — ambiguity handled locally,
without escalating to Claude.

**Release.** `CHANGELOG.md`, `.github/workflows/release.yml` (builds the Windows
exe on a `v*` tag and attaches a zip to a GitHub Release), and `docs/RELEASE.md`.
`setup.bat`/`run.bat`/`run_cli.bat` give non-tech users a double-click path.

**Testing status:** 64 automated tests. Engine selection, plugins, overlay, and
end-to-end routing all covered; hardware/GUI via `docs/TESTING.md`.
