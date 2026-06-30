from voiceclaw.config import Config
from voiceclaw import auth


def cfg(auth_mode="auto", key=""):
    return Config({"brain": {"auth": auth_mode, "anthropic_api_key": key,
                             "model": "m", "max_tokens": 10}})


def test_no_credentials(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    creds = auth.resolve(cfg())
    assert creds.mode == "none" and not creds.usable


def test_api_key_resolves(monkeypatch):
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    creds = auth.resolve(cfg(key="sk-abc"))
    assert creds.mode == "api_key" and creds.api_key == "sk-abc"


def test_subscription_token(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "oauth-xyz")
    creds = auth.resolve(cfg(auth_mode="auto"))
    assert creds.mode == "subscription" and creds.auth_token == "oauth-xyz"


def test_explicit_api_key_mode_ignores_token(monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "oauth-xyz")
    creds = auth.resolve(cfg(auth_mode="api_key", key="sk-abc"))
    assert creds.mode == "api_key"


def test_resolves_from_store(monkeypatch):
    # No env/config creds, but a token in the secure store.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    import voiceclaw.credentials_store as cs
    monkeypatch.setattr(cs, "load",
                        lambda k: "sk-ant-oat01-stored" if k == "oauth_token" else None)
    creds = auth.resolve(cfg())
    assert creds.mode == "subscription"
    assert creds.auth_token == "sk-ant-oat01-stored"
    assert creds.source == "store"
