from voiceclaw import login


def test_token_validation():
    assert login._looks_like_token("sk-ant-oat01-abcdefgh")
    assert not login._looks_like_token("hello")
    assert not login._looks_like_token("")
    assert not login._looks_like_token("sk-ant-")  # too short


def test_token_regex_extracts_from_noise():
    out = "Here is your token:\n  sk-ant-oat01-AbC123._-xyz \nDone."
    m = login.TOKEN_RE.search(out)
    assert m and m.group(0).startswith("sk-ant-oat01-")
