from voiceclaw.hotkeys import HotkeyManager


def test_manager_constructs_with_defaults():
    m = HotkeyManager()
    assert m.ptt_combo and m.kill_combo


def test_safe_wrapper_swallows_errors(capsys):
    def boom():
        raise RuntimeError("x")
    wrapped = HotkeyManager._safe(boom)
    wrapped()  # must not raise
    assert "handler error" in capsys.readouterr().out


def test_callbacks_assigned():
    flag = {"ptt": False}
    m = HotkeyManager(on_ptt=lambda: flag.__setitem__("ptt", True))
    m.on_ptt()
    assert flag["ptt"]


def test_wakeword_choose_engine():
    from voiceclaw.wakeword import _choose_engine
    assert _choose_engine("porcupine", True, True) == "porcupine"
    assert _choose_engine("porcupine", True, False) == "openwakeword"   # fallback
    assert _choose_engine("porcupine", False, True) == "porcupine"
    assert _choose_engine("openwakeword", True, True) == "openwakeword"
    assert _choose_engine("openwakeword", False, True) == "porcupine"   # fallback
    assert _choose_engine("anything", False, False) is None
