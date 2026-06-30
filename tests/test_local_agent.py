import json
from pathlib import Path
import voiceclaw.local_agent as la
from voiceclaw.tools import Toolbox


def test_tool_conversion_to_ollama():
    tools = la._to_ollama_tools()
    assert tools and all(t["type"] == "function" for t in tools)
    names = {t["function"]["name"] for t in tools}
    assert {"open_app", "close_app", "run_shell"} <= names
    # parameters carried over from input_schema
    assert all("parameters" in t["function"] for t in tools)


class FakeResp:
    def __init__(self, payload): self._p = payload
    def json(self): return self._p


def test_agent_runs_tool_then_answers(monkeypatch, tmp_path):
    calls = {"n": 0}

    def fake_post(url, json=None, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return FakeResp({"message": {"role": "assistant", "content": "",
                "tool_calls": [{"function": {"name": "open_app",
                                             "arguments": {"name": "notepad"}}}]}})
        return FakeResp({"message": {"role": "assistant", "content": "Opened it."}})

    import requests
    monkeypatch.setattr(requests, "post", fake_post)

    ran = []
    tb = Toolbox([tmp_path], [], confirm_cb=lambda p: True, speak_cb=lambda s: None)
    monkeypatch.setattr(tb, "run", lambda n, a: ran.append((n, a)) or "ok")

    brain = la.LocalBrain("http://x", "m", tb, max_iterations=4)
    out = brain.handle("open notepad")
    assert out == "Opened it."
    assert ran == [("open_app", {"name": "notepad"})]
