# Changelog

All notable changes to VoiceClaw are documented here.
Format follows Keep a Changelog; this project uses semantic versioning.

## [0.1.0] — 2026-06-30

First public release.

### Added
- **Packaging & release**: one-click Windows **installer** (Inno Setup, per-user, no admin) and a **portable zip**, both shipped as GitHub Release assets. PyInstaller onedir bundle; the proprietary Tier-1 grammar + learned cache ship **compiled**, not as source.
- **Open-core split**: the public repo is the shell; the command grammar and learned-cache "core" live in a private module and ship only as compiled binaries. Public shims fall back to agent-only mode if the core is absent.
- **Window & system voice commands**: minimize / maximize / snap left|right / show desktop / switch window / lock screen / take a screenshot (instant key combos).
- **Expanded website routing**: ~30 more web destinations (news, dev, shopping, reference, mail) open as URLs; widened routing stress test to 1005 cases (all ideal).
- **Routing stress test** (337 generated commands across all PC-activity categories) as a regression guard; added launch-verb synonyms (launch / fire up / boot up / open up) and close synonyms (kill / shut down) to the instant path.
- **Open folders & drives by voice**: "open the D drive", "open downloads folder" open in
  Explorer; unknown folder names go to the agent instead of a "file not found" popup.
- **Hold-to-dictate hotkey** (default Right Ctrl): hold, speak, release → your words
  are typed (and sent) into the focused window. Configurable (`hotkeys.dictation_ptt`).
- **Companion app overhaul** (production-style, dark theme): new **Dashboard** (live
  status, recent-activity feed, command tester), **Learned** tab (search/delete/forget
  learned commands), an in-app **Developer console** toggle (replaces the external cmd
  window), backend selector, and a header Dictation toggle.
- **Voice dictation / relay**: type spoken words verbatim into the focused window
  (dev chats like Cowork/Codex/Claude Code, editors). "type X", "tell Claude X"/
  "send X" (presses Enter), and a continuous "start/stop dictation" mode; toggles in
  the tray menu and app header.
- **Learned-command cache** (`learned_skills.py`): when the agent resolves a new
  phrasing with deterministic actions (open URL/app, close app, keypress, scroll),
  that phrasing is cached and replayed instantly next time. Vision clicks are never
  cached. Clear via Settings → "Forget all learned commands", the tray menu, or
  `python main.py forget-learned`. Toggle with `learning.enabled` in config.
- **Agent grounding/"contexting"**: the agent observes the screen before and after
  each action and keeps only the latest screenshot in context, so it acts on real
  state (reuses open tabs, reads results, resolves profile/cookie dialogs) instead
  of blindly clicking.
- **Device control from natural speech**: `press_keys` documents the full media/
  volume/navigation/tab vocabulary; the agent maps free phrasing to the right key.
- **Routing evaluation harness** (`routing_eval.py`, `tests/test_routing.py`): 55
  realistic utterances checked against the real router (no mic/LLM) — AGENT vs Tier-1
  plus exact tool/args. Agent backend selector dropdown in the GUI Account tab.

### Changed
- Tier-1 is now high-precision and **biases to fallback**: anchored rules, a
  confidence gate (`ESCALATE`) that declines low-confidence captures, and `_is_complex`
  escalation for vision (`click`/`tap`/`drag`) and conversational phrasing.
- `agent.max_tool_iterations` 8 → 20 (vision loops need more steps).

### Fixed
- "file explorer" open/close (was wrongly escalated); bare "calendar"/"outlook"/"maps" now open the desktop app, not a Google URL.
- "open youtube/gmail/maps…" open as **websites**; real apps still launch.
- "next track"/"next song" no longer hijacked by the "next" feed-nav rule.
- "close all (chrome) tabs" actually closes them.
- Auto-start shortcut creation broke on usernames containing an apostrophe.
- OpenAI backend silently inactive when the `openai` package wasn't installed.

## [0.0.1] — 2026-06-23
First internal prototype.

### Added
- Three-tier hybrid brain: local control skills → local model (Ollama) → Claude agent.
- Always-listening voice loop: wake word → STT (faster-whisper) → act → TTS.
- Wake word: openWakeWord (multi/custom) **and** Picovoice Porcupine engine for a
  real "Hey Claude" wake word; engine selector + config.
- Cross-platform PC-control tools (shell, apps, files, keyboard, scroll, web, system).
- `ask_user` tool + on-screen clarify **overlay**; bare "open" prompts for the target.
- Global push-to-talk and kill-switch **hotkeys** (pynput); `hotkey` run mode.
- Hybrid auth: Anthropic API key **or** Claude Pro/Max subscription via the official
  OAuth token; `login`/`logout`/`status`; secure keychain storage.
- Companion **desktop app** (PySide6): Account, Settings, Logs; Start/Stop.
- System-tray app + login auto-start; idle model unloading; issues log.
- **Plugin system** for community skills/tools (`~/.voiceclaw/plugins/`).
- Packaging: PyInstaller spec + Inno Setup installer; `setup.bat`/`run.bat`.
- 61 automated tests + CI (Python 3.10–3.12) + manual test checklist.

### Known limitations
- "Hey Claude" needs a Porcupine `.ppn` or a trained openWakeWord model (see docs).
- GUI control assumes the target window is focused / standard shortcuts.
- No per-user accent learning yet.
