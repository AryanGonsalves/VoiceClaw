from pathlib import Path
from voiceclaw.tools import Toolbox


def make_box(tmp_path, approve=False):
    return Toolbox(allowed_paths=[tmp_path],
                   confirm_patterns=["rm ", "shutdown"],
                   confirm_cb=lambda prompt: approve)


def test_path_scoping_blocks_outside(tmp_path):
    tb = make_box(tmp_path)
    out = tb.run("read_file", {"path": "/etc/hostname"})
    assert "not allowed" in out.lower()


def test_write_requires_confirmation(tmp_path):
    tb = make_box(tmp_path, approve=False)
    out = tb.run("write_file", {"path": str(tmp_path / "a.txt"), "content": "hi"})
    assert "declined" in out.lower()
    assert not (tmp_path / "a.txt").exists()


def test_write_when_approved(tmp_path):
    tb = make_box(tmp_path, approve=True)
    out = tb.run("write_file", {"path": str(tmp_path / "a.txt"), "content": "hi"})
    assert (tmp_path / "a.txt").read_text() == "hi"


def test_destructive_shell_needs_confirmation(tmp_path):
    tb = make_box(tmp_path, approve=False)
    out = tb.run("run_shell", {"command": "rm -rf /tmp/x"})
    assert "declined" in out.lower()


def test_unknown_tool(tmp_path):
    assert "unknown tool" in make_box(tmp_path).run("nope", {}).lower()


def test_list_files(tmp_path):
    (tmp_path / "f.txt").write_text("x")
    out = make_box(tmp_path).run("list_files", {"path": str(tmp_path)})
    assert "f.txt" in out


def test_ask_user_tool_present():
    from voiceclaw.tools import TOOL_SCHEMAS
    assert any(s["name"] == "ask_user" for s in TOOL_SCHEMAS)


def test_ask_user_graceful_without_display(tmp_path):
    spoken = []
    tb = Toolbox(allowed_paths=[tmp_path], confirm_patterns=[],
                 confirm_cb=lambda p: False, speak_cb=spoken.append)
    out = tb.run("ask_user", {"question": "Which one?", "options": ["x", "y"]})
    assert out == "(no answer)"      # headless overlay returns None
    assert spoken == ["Which one?"]  # question was spoken
