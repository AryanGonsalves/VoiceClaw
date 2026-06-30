"""Voice dictation / relay: type spoken words into the focused window."""
from voiceclaw.app import _dictation_action, Assistant
from voiceclaw.local_skills import LocalSkills
from voiceclaw.learned_skills import LearnedSkills


def test_dictation_action_prefixes():
    assert _dictation_action("tell Claude continue", False) == ("type", ("continue", True))
    assert _dictation_action("Tell Claude, let's work on the GUI now", False) == \
        ("type", ("let's work on the GUI now", True))
    assert _dictation_action("type def foo(): pass", False) == \
        ("type", ("def foo(): pass", False))
    assert _dictation_action("start dictation", False) == ("start", None)
    assert _dictation_action("stop dictation", False) == ("stop", None)
    # normal command, mode off -> not dictation
    assert _dictation_action("open youtube", False) is None
    # continuous mode -> everything typed + sent
    assert _dictation_action("do all the suggested tasks", True) == \
        ("type", ("do all the suggested tasks", True))


class Cfg(dict):
    def __init__(self): super().__init__(); self["runtime"] = {}
class Speaker:
    def __init__(self): self.said = []
    def say(self, m): self.said.append(m)
class Toolbox:
    def __init__(self): self.calls = []
    def run(self, n, a): self.calls.append((n, a)); return True


def _asst(tb):
    return Assistant(Cfg(), Speaker(), None, LocalSkills(True), tb, None,
                     resources=None, learned=LearnedSkills())


def test_relay_types_and_sends():
    tb = Toolbox(); a = _asst(tb)
    a.respond("Tell Claude, continue")
    assert tb.calls == [("type_text", {"text": "continue"}),
                        ("press_keys", {"keys": "enter"})]


def test_type_prefix_no_enter():
    tb = Toolbox(); a = _asst(tb)
    a.respond("type hello world")
    assert tb.calls == [("type_text", {"text": "hello world"})]


def test_continuous_mode_toggle():
    tb = Toolbox(); a = _asst(tb)
    a.respond("start dictation")
    assert a.dictation_mode is True
    tb.calls.clear()
    a.respond("do all the suggested tasks")           # typed + sent verbatim
    assert tb.calls == [("type_text", {"text": "do all the suggested tasks"}),
                        ("press_keys", {"keys": "enter"})]
    a.respond("stop dictation")
    assert a.dictation_mode is False
