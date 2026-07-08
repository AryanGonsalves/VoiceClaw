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


def test_env_key_not_persisted_in_data(monkeypatch, tmp_path):
    """Regression: an ANTHROPIC_API_KEY provided via the environment must NOT be
    copied into cfg.data (which the UI dumps to config.yaml), or the secret would
    be written to disk in plaintext. The property still surfaces it at read time."""
    import yaml
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-secret-env")
    c = Config.load("config.example.yaml")
    # Property surfaces the env key for auth...
    assert c.anthropic_key == "sk-ant-secret-env"
    # ...but the persisted data dict must not contain it.
    assert c.data["brain"]["anthropic_api_key"] == ""
    # A dump of cfg.data (as the UI does) must not leak the secret.
    dumped = yaml.safe_dump(c.data)
    assert "sk-ant-secret-env" not in dumped
