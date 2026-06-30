"""Headless test harness: feed an exact sentence into whatever agent backend is
configured (brain.backend), bypassing wake word / STT. Writes cc_test_result.txt."""
import time, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "cc_test_result.txt"
TEXT = "Open YouTube, search me a funny cat video and play the first video that shows up."

out = [f"=== cc_test @ {time.strftime('%H:%M:%S')} ===", f"input: {TEXT}"]
try:
    from voiceclaw.config import Config
    from voiceclaw.tools import Toolbox
    from voiceclaw.app import _select_brain
    cfg = Config.load("config.yaml")
    tb = Toolbox(cfg.allowed_paths, cfg["agent"]["confirm_patterns"],
                 confirm_cb=lambda p: True, speak_cb=None)
    brain, mode, msg = _select_brain(cfg, tb)
    out.append(f"backend: {cfg['brain'].get('backend')}  resolved-mode: {mode}")
    out.append(f"auth msg: {msg}")
    if brain is None:
        out.append("NO BRAIN (no credential resolved).")
    else:
        t0 = time.time()
        result = brain.handle(TEXT, on_status=lambda m: out.append(f"status: {m}"))
        out.append(f"elapsed: {time.time()-t0:.1f}s")
        out.append("RESULT:\n" + str(result))
except Exception:
    out.append("HARNESS EXCEPTION:\n" + traceback.format_exc())

OUT.write_text("\n".join(out), encoding="utf-8")
print("done -> cc_test_result.txt")
