import voiceclaw.issues as issues


def _isolate(monkeypatch, tmp_path):
    monkeypatch.setattr(issues, "LOG_PATH", tmp_path / "issues.log")


def test_log_and_read(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    issues.log_issue("brain", "boom happened", level="ERROR")
    rows = issues.read_issues()
    assert len(rows) == 1
    assert rows[0]["source"] == "brain"
    assert rows[0]["level"] == "ERROR"
    assert "boom" in rows[0]["message"]


def test_tabs_newlines_sanitized(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    issues.log_issue("tool:x", "line1\nline2\tcol", level="WARN")
    rows = issues.read_issues()
    assert len(rows) == 1  # stayed one record
    assert "\n" not in rows[0]["message"] and "\t" not in rows[0]["message"]


def test_clear(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    issues.log_issue("s", "m")
    issues.clear_issues()
    assert issues.read_issues() == []
