import time
from voiceclaw.resources import ResourceManager


class FakeModel:
    def __init__(self):
        self.loaded = True
        self.last_used = time.time() - 1000  # long idle
    def is_loaded(self):
        return self.loaded
    def unload(self):
        self.loaded = False


def test_idle_model_gets_unloaded():
    rm = ResourceManager(idle_seconds=1, poll_seconds=0.1)
    m = FakeModel()
    rm.register(m)
    rm.start()
    time.sleep(0.4)
    rm.stop()
    assert m.loaded is False


def test_disabled_when_idle_seconds_zero():
    rm = ResourceManager(idle_seconds=0)
    rm.start()
    assert rm._thread is None
