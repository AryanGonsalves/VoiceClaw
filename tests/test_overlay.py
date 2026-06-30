from voiceclaw import overlay


def test_headless_ask_returns_none():
    # No display in CI/sandbox -> must return None, never raise.
    assert overlay.ask("Which file?", ["a.txt", "b.txt"]) is None


def test_overlay_available_is_bool():
    assert isinstance(overlay.overlay_available(), bool)
