# VoiceClaw — manual run-through checklist (Windows)

Automated tests cover the logic (`pytest` → 58 tests). These steps cover the
things that need real hardware/OS and can't run in CI: mic, audio out, global
hotkeys, the GUI, and sign-in. Do them on the target PC after `pip install -r
requirements.txt`.

Tip: keep a terminal open to watch logs; failures also appear in the UI **Logs**
tab and in `~/.voiceclaw/issues.log`.

## 0. Setup
- [ ] `python -m venv .venv && .venv\Scripts\activate`
- [ ] `pip install -r requirements.txt`
- [ ] `copy config.example.yaml config.yaml`
- [ ] `pytest -q` → expect "58 passed"

## 1. Text mode (no audio needed) — proves the brain + tools
- [ ] `python main.py login` (or `login --api-key`) → `python main.py status` shows signed in
- [ ] `python main.py --mode text`
- [ ] Type "what's my CPU and battery?" → spoken/printed answer with real numbers
- [ ] Type "open notepad" → Notepad launches
- [ ] Type "create a file on my desktop called vc_test.txt with hello" → confirm prompt → file appears
- [ ] Type something ambiguous ("open it") → it should ask a follow-up (ask_user)

## 2. Microphone + STT
- [ ] `python main.py --mode ptt`
- [ ] Press Enter, say "what time is it" → correct transcription + answer
- [ ] If wrong device is used: set it in the UI Settings → Microphone, save, retry
- [ ] Heavy accent? bump `stt.model` to `small` or `medium` in config.yaml and retry

## 3. Wake word
- [ ] `python main.py --mode voice`
- [ ] Say the wake word (default "hey jarvis") → chime → speak a command
- [ ] Enable a second wake word in Settings, save, restart → either word wakes it
- [ ] Tune `wakeword.threshold` if it triggers too easily / not enough

## 4. Global hotkeys (any app focused)
- [ ] In `voice` or `hotkey` mode, focus another app (e.g. a browser)
- [ ] Press push-to-talk (`Ctrl+Alt+Space`) → chime → speak → it acts
- [ ] Press kill-switch (`Ctrl+Alt+Q`) → listening stops
- [ ] Change the bindings in Settings, save, restart, re-test

## 5. "Next video" on YouTube Shorts (local, instant)
- [ ] Open YouTube Shorts in a browser, focus it
- [ ] Say/hotkey "next video" → advances; "previous" → goes back
- [ ] "volume up", "mute", "scroll down", "play", "pause" → all work with no network

## 6. Companion app
- [ ] `python -m voiceclaw.ui`
- [ ] Account tab: sign in / status / sign out all reflect correctly
- [ ] Settings tab: change voice rate + a hotkey, Save → reopen → persisted in config.yaml
- [ ] Header "Start listening" → status turns green; speak a command; "Stop" → grey
- [ ] Trigger a failure (e.g. unplug network then ask a web question) → appears in Logs tab

## 7. Tray + autostart
- [ ] `python -m voiceclaw.tray` → tray icon appears; Pause/Resume works; Sign in works; Quit works
- [ ] `python install_autostart.py` → reboot/sign-out test it launches; `--remove` to undo

## 8. Low-consumption sanity
- [ ] Let it idle a few minutes after a command; confirm RAM drops (Whisper unloads
      after `runtime.idle_unload_seconds`) via Task Manager

## Known-good expectations / gotchas
- First STT use downloads a Whisper model (needs network once).
- GUI control assumes the intended window is focused and uses standard shortcuts.
- If a global hotkey does nothing, another app may have claimed it — pick another combo.
- Destructive shell/file actions always prompt for confirmation; that's intended.
