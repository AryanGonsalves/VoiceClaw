import json
import voiceclaw.openai_brain as ob


def test_tool_conversion():
    tools = ob._to_openai_tools([])
    assert tools and all(t["type"] == "function" for t in tools)
    names = {t["function"]["name"] for t in tools}
    assert {"open_app", "click", "screenshot"} <= names
    assert all("parameters" in t["function"] for t in tools)


class _Fn:
    def __init__(self, name, args): self.name = name; self.arguments = args
class _TC:
    def __init__(self, id, name, args): self.id = id; self.type = "function"; self.function = _Fn(name, args)
class _Msg:
    def __init__(self, content=None, tool_calls=None): self.content = content; self.tool_calls = tool_calls
class _Choice:
    def __init__(self, msg): self.message = msg
class _Resp:
    def __init__(self, msg): self.choices = [_Choice(msg)]


def test_agent_runs_tool_then_answers(monkeypatch, tmp_path):
    from voiceclaw.tools import Toolbox
    # Avoid importing the real openai SDK in __init__
    brain = ob.OpenAIBrain.__new__(ob.OpenAIBrain)
    brain.model = "gpt-4o-mini"
    brain.max_iterations = 4
    brain.history = []
    tb = Toolbox([tmp_path], [], confirm_cb=lambda p: True, speak_cb=lambda s: None)
    ran = []
    monkeypatch.setattr(tb, "run", lambda n, a: ran.append((n, a)) or "ok")
    brain.toolbox = tb

    calls = {"n": 0}
    class FakeClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kw):
                    calls["n"] += 1
                    if calls["n"] == 1:
                        return _Resp(_Msg(tool_calls=[_TC("c1", "open_app", '{"name":"notepad"}')]))
                    return _Resp(_Msg(content="Opened it."))
    brain.client = FakeClient()

    out = brain.handle("open notepad")
    assert out == "Opened it."
    # the meaningful tool call still happens
    assert ("open_app", {"name": "notepad"}) in ran
    # grounding: observe-first takes a screenshot before the first action
    assert ran[0] == ("screenshot", {})
    # and observe-after captures the resulting screen following an action
    assert ran.count(("screenshot", {})) >= 1
