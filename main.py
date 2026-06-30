# VoiceClaw — Copyright (c) 2026 Aryan Gonsalves. All rights reserved. Proprietary; see LICENSE.
#!/usr/bin/env python3
"""VoiceClaw CLI entry point.

Run modes (auto-selected by what's installed, overridable with --mode):
  voice   wake word -> record -> STT -> route -> act -> speak (global hotkeys too)
  hotkey  no wake word; global push-to-talk hotkey captures on demand
  ptt     terminal push-to-talk: press Enter to record one utterance
  text    type requests instead of speaking (no audio libs needed)

Account subcommands:
  python main.py login [--api-key] | status | logout
  python main.py forget-learned   # wipe the personalized learned cache

Background tray app:  python -m voiceclaw.tray
Companion desktop UI: python -m voiceclaw.ui
"""
from __future__ import annotations

import argparse
import sys
import threading

from voiceclaw.config import Config
from voiceclaw import audio, wakeword as ww, stt as stt_mod, hotkeys as hk
from voiceclaw.app import build, Assistant


def _make_transcriber(asst: Assistant):
    t = stt_mod.make_transcriber(asst.cfg)
    asst.resources.register(t)

    # Pre-load (and download on first run) the speech model in the background,
    # so the first spoken command isn't a long pause.
    def _warm():
        try:
            if hasattr(t, "_ensure"):
                print("[stt] preparing speech model (first run downloads it once)...")
                t._ensure()
                print("[stt] speech model ready.")
            else:
                print("[stt] using cloud speech-to-text.")
        except Exception as e:
            from voiceclaw.issues import log_issue
            log_issue("stt.warmup", e)
    threading.Thread(target=_warm, daemon=True).start()
    return t


def _make_feedback(asst: Assistant):
    """Build the listening ring + audio ducker from config (both optional)."""
    ring = ducker = None
    ui = asst.cfg.get("ui", {}) or {}
    if ui.get("ring", True):
        try:
            from voiceclaw import overlay_ring
            if overlay_ring.ring_available():
                ring = overlay_ring.RingOverlay(thickness=ui.get("ring_thickness", 7))
                ring.start()
        except Exception:
            ring = None
    acfg = asst.cfg.get("audio", {}) or {}
    if acfg.get("duck", True):
        try:
            from voiceclaw import audio_ducker
            if audio_ducker.ducking_available():
                ducker = audio_ducker.AudioDucker(level=acfg.get("duck_level", 0.15))
        except Exception:
            ducker = None
    return ring, ducker


def _capture_and_respond(asst: Assistant, mic, transcriber, ring=None, ducker=None):
    if ducker is not None:
        ducker.duck()      # Alexa-style: quiet other apps while listening
    if ring is not None:
        ring.show()        # rainbow listening ring
    try:
        mic.chime("wake")
        text = transcriber.transcribe(mic.record_until_silence())
        if not text:
            asst.speaker.say("I didn't catch that.")
            return
        asst.respond(text)
    finally:
        if ring is not None:
            ring.hide()
        if ducker is not None:
            ducker.restore()


def _make_hotkeys(asst: Assistant, ptt_event: threading.Event, stop_event: threading.Event):
    """Start global hotkeys if enabled+available. Returns a HotkeyManager or None."""
    hcfg = asst.cfg.get("hotkeys", {}) or {}
    if not hcfg.get("enabled", True) or not hk.hotkeys_available():
        return None
    mgr = hk.HotkeyManager(
        push_to_talk=hcfg.get("push_to_talk", "<ctrl>+<alt>+space"),
        kill_switch=hcfg.get("kill_switch", "<ctrl>+<alt>+q"),
        on_ptt=ptt_event.set,
        on_kill=stop_event.set,
    )
    if mgr.start():
        print(f"[hotkeys] push-to-talk={hcfg.get('push_to_talk', '<ctrl>+<alt>+space')}"
              f"  kill={hcfg.get('kill_switch', '<ctrl>+<alt>+q')}")
        return mgr
    return None


def _capture_and_dictate(asst, mic, transcriber, dhk, ring=None, ducker=None):
    """Hold-to-dictate: record while the key is held, then TYPE the words verbatim
    into the focused window (a dev chat/editor) instead of running a command."""
    if ducker is not None:
        ducker.duck()
    if ring is not None:
        ring.show()
    try:
        mic.chime("wake")
        audio_data = (mic.record_while_held(dhk.held)
                      if dhk is not None else mic.record_until_silence())
        text = transcriber.transcribe(audio_data)
        if not text:
            return
        asst.toolbox.run("type_text", {"text": text})
        if (asst.cfg.get("hotkeys", {}) or {}).get("dictation_ptt_send", True):
            asst.toolbox.run("press_keys", {"keys": "enter"})
        print(f"  [dictation] typed: {text}")
        from voiceclaw.app import _log
        _log(asst.cfg, "dictation", text)
    finally:
        if ring is not None:
            ring.hide()
        if ducker is not None:
            ducker.restore()


def _make_dictation_hotkey(asst: Assistant, dictate_event: threading.Event):
    """Start the hold-to-dictate key listener (default Right Ctrl). Returns it or None."""
    hcfg = asst.cfg.get("hotkeys", {}) or {}
    keyname = hcfg.get("dictation_ptt", "<ctrl_r>")
    if not keyname or not hcfg.get("enabled", True) or not hk.hotkeys_available():
        return None
    d = hk.DictationHotkey(key=keyname, on_press=dictate_event.set)
    if d.start():
        print(f"[hotkeys] hold-to-dictate={keyname} (type into focused window)")
        return d
    return None


def run_text(asst: Assistant):
    print("VoiceClaw (text mode). Type a request, or 'quit'.")
    while True:
        try:
            text = input("\nyou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if text.lower() in ("quit", "exit"):
            break
        asst.respond(text)


def run_ptt(asst: Assistant):
    if not (audio.audio_available() and stt_mod.stt_available()):
        print("Audio/STT not available; falling back to text mode.")
        return run_text(asst)
    mic = audio.Microphone(device=asst.cfg.get('audio', {}).get('input_device'))
    transcriber = _make_transcriber(asst)
    ring, ducker = _make_feedback(asst)
    print("VoiceClaw (push-to-talk). Press Enter to speak, Ctrl+C to quit.")
    while True:
        try:
            input("\n[Enter to talk] ")
        except (EOFError, KeyboardInterrupt):
            break
        _capture_and_respond(asst, mic, transcriber, ring, ducker)


def run_hotkey(asst: Assistant, stop_flag=None):
    """No wake word — wait for the global push-to-talk hotkey, then capture."""
    if not (audio.audio_available() and stt_mod.stt_available()):
        print("Audio/STT not available; falling back to text mode.")
        return run_text(asst)
    if not hk.hotkeys_available():
        print("pynput not installed; falling back to terminal push-to-talk.")
        return run_ptt(asst)
    mic = audio.Microphone(device=asst.cfg.get('audio', {}).get('input_device'))
    transcriber = _make_transcriber(asst)
    ring, ducker = _make_feedback(asst)
    ptt_event = threading.Event()
    stop_event = threading.Event()
    dictate_event = threading.Event()
    mgr = _make_hotkeys(asst, ptt_event, stop_event)
    dhk = _make_dictation_hotkey(asst, dictate_event)
    if mgr is None and dhk is None:
        return run_ptt(asst)
    print("VoiceClaw (hotkey mode). Press push-to-talk to command, "
          "hold the dictation key to type.")
    try:
        while not stop_event.is_set() and not (stop_flag and stop_flag()):
            try:
                if dictate_event.is_set():
                    dictate_event.clear()
                    _capture_and_dictate(asst, mic, transcriber, dhk, ring, ducker)
                elif ptt_event.wait(timeout=0.2):
                    ptt_event.clear()
                    _capture_and_respond(asst, mic, transcriber, ring, ducker)
            except Exception as e:
                from voiceclaw.issues import log_issue
                log_issue("run_hotkey", e)
    finally:
        if mgr is not None:
            mgr.stop()
        if dhk is not None:
            dhk.stop()


def run_voice(asst: Assistant, stop_flag=None):
    if not (ww.wakeword_available() and stt_mod.stt_available()):
        print("Wake word / STT not available; falling back to push-to-talk.")
        return run_ptt(asst)
    mic = audio.Microphone(device=asst.cfg.get('audio', {}).get('input_device'))
    transcriber = _make_transcriber(asst)
    ring, ducker = _make_feedback(asst)
    listener = ww.make_listener(asst.cfg)
    if listener is None:
        print("No wake-word engine available; falling back to push-to-talk.")
        return run_ptt(asst)
    ptt_event = threading.Event()
    stop_event = threading.Event()
    dictate_event = threading.Event()
    mgr = _make_hotkeys(asst, ptt_event, stop_event)
    dhk = _make_dictation_hotkey(asst, dictate_event)
    print(f"VoiceClaw listening for {asst.cfg.wake_models}. Ctrl+C to quit.")

    def should_stop():
        return stop_event.is_set() or (stop_flag is not None and stop_flag())

    try:
        while not should_stop():
            try:
                reason = listener.wait_for_wake(
                    interrupt=lambda: should_stop() or ptt_event.is_set()
                    or dictate_event.is_set())
                if should_stop():
                    break
                if dictate_event.is_set():
                    dictate_event.clear()
                    _capture_and_dictate(asst, mic, transcriber, dhk, ring, ducker)
                else:
                    ptt_event.clear()  # woke by word or PTT -> capture a command
                    _capture_and_respond(asst, mic, transcriber, ring, ducker)
            except KeyboardInterrupt:
                break
            except Exception as e:
                from voiceclaw.issues import log_issue
                log_issue("run_voice", e)
                import time as _t
                _t.sleep(0.5)   # keep listening instead of dying
    finally:
        if mgr is not None:
            mgr.stop()
        if dhk is not None:
            dhk.stop()


def choose_mode() -> str:
    if ww.wakeword_available() and stt_mod.stt_available():
        return "voice"
    if audio.audio_available() and stt_mod.stt_available():
        return "ptt"
    return "text"


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("login", "logout", "status"):
        from voiceclaw import login as login_mod
        cmd, rest = sys.argv[1], sys.argv[2:]
        if cmd == "logout":
            return login_mod.logout()
        if cmd == "status":
            return login_mod.status()
        return login_mod.main(rest)

    if len(sys.argv) > 1 and sys.argv[1] in ("forget-learned", "clear-learned"):
        from voiceclaw.learned_skills import LearnedSkills
        ls = LearnedSkills()
        n = ls.count(); ls.clear()
        print(f"Forgot {n} learned command(s).")
        return 0

    ap = argparse.ArgumentParser(description="VoiceClaw — hybrid voice agent")
    ap.add_argument("--config", default=None)
    ap.add_argument("--mode", choices=["voice", "hotkey", "ptt", "text"], default=None)
    args = ap.parse_args()

    cfg = Config.load(args.config)
    asst = build(cfg)

    print(f"[auth] {asst.auth_message}")
    if asst.brain is None:
        print("[warn] Local control + offline answers only. "
              "Run `python main.py login` to enable full Claude.")

    mode = args.mode or choose_mode()
    {"voice": run_voice, "hotkey": run_hotkey,
     "ptt": run_ptt, "text": run_text}[mode](asst)
    asst.resources.stop()
    print("\nGoodbye.")


if __name__ == "__main__":
    sys.exit(main())