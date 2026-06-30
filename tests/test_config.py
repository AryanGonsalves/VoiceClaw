import os
from voiceclaw.config import Config


def test_defaults_load():
    c = Config()
    assert c["brain"]["model"]
    assert c.wake_models == ["hey_jarvis"]


def test_wake_models_backcompat():
    c = Config({"wakeword": {"model": "alexa"}})
    assert c.wake_models == ["alexa"]


def test_env_overrides_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    c = Config.load("config.example.yaml")
    assert c.anthropic_key == "sk-test"


def test_allowed_paths_defaults_home():
    c = Config()
    assert len(c.allowed_paths) >= 1
