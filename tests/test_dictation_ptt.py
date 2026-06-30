"""Hold-to-dictate (push-to-talk) capture: record while held -> type into focus."""
import os, sys, types
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import main


class FakeMic:
    def chime(self, k): pass
    def record_while_held(self, held): return "AUDIO"
    def record_until_silence(self): return "AUDIO"


class FakeTrans:
    def __init__(self, t): self.t = t
    def transcribe(self, a): return self.t


class FakeTB:
    def __init__(self): self.calls = []
    def run(self, n, a): self.calls.append((n, a)); return True


class FakeDHK:
    def held(self): return False


def _asst(send=True):
    return types.SimpleNamespace(
        toolbox=FakeTB(),
        cfg={"runtime": {}, "hotkeys": {"dictation_ptt_send": send}})


def test_dictate_types_and_sends():
    a = _asst(send=True)
    main._capture_and_dictate(a, FakeMic(), FakeTrans("continue"), FakeDHK())
    assert a.toolbox.calls == [("type_text", {"text": "continue"}),
                               ("press_keys", {"keys": "enter"})]


def test_dictate_no_send_when_disabled():
    a = _asst(send=False)
    main._capture_and_dictate(a, FakeMic(), FakeTrans("hello world"), FakeDHK())
    assert a.toolbox.calls == [("type_text", {"text": "hello world"})]


def test_dictate_empty_is_noop():
    a = _asst()
    main._capture_and_dictate(a, FakeMic(), FakeTrans(""), FakeDHK())
    assert a.toolbox.calls == []


def test_dictation_hotkey_keyname():
    from voiceclaw.hotkeys import DictationHotkey
    d = DictationHotkey(key="<ctrl_r>")
    assert d.key_name == "ctrl_r"
    assert d.held() is False
