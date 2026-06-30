from voiceclaw.router import Router


class StubLLM:
    def __init__(self, up=True, answer="hi"):
        self.up, self.answer = up, answer
    def available(self):
        return self.up
    def ask(self, text):
        return self.answer


def test_long_requests_escalate():
    r = Router(StubLLM(), fast_path_max_words=8)
    assert r.try_local("this is a very long request " * 5) is None


def test_action_words_escalate():
    r = Router(StubLLM(), fast_path_max_words=8)
    assert r.try_local("open the browser") is None


def test_short_simple_uses_local():
    r = Router(StubLLM(answer="42"), fast_path_max_words=8)
    assert r.try_local("hello there") == "42"


def test_disabled_local_escalates():
    r = Router(StubLLM(), local_enabled=False)
    assert r.try_local("hi") is None


def test_offline_local_escalates():
    r = Router(StubLLM(up=False))
    assert r.try_local("hi") is None
