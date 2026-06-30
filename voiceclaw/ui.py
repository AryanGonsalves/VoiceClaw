# VoiceClaw — Copyright (c) 2026 Aryan Gonsalves. All rights reserved. Proprietary; see LICENSE.
"""VoiceClaw companion desktop app (PySide6) — production-style control panel.

Optional NVIDIA-app-style window. You don't need it open for the voice agent to
run, but it makes setup and monitoring friendly. Tabs:

  • Dashboard — live status: backend, listening state, last command, recent activity,
                quick toggles, and a command tester.
  • Account   — sign in (subscription / API key / OpenAI), backend selector.
  • Settings  — wake words, mic, voice, hotkeys, folders, learning toggle.
  • Learned   — manage the personalized learned-command cache (search/delete/clear).
  • Logs      — recent issues/failures (issues.log).

A toggleable in-app Developer console shows live output (replaces needing the
external cmd window). Run:  python -m voiceclaw.ui      Deps: pip install PySide6
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

from .config import Config


def ui_available() -> bool:
    try:
        import PySide6  # noqa: F401
        return True
    except Exception:
        return False


CONFIG_FILE = "config.yaml"

APP_QSS = """
* { font-family: 'Segoe UI', 'Inter', sans-serif; }
QMainWindow, QWidget { background: #15171c; color: #e7e9ee; font-size: 13px; }
QTabWidget::pane { border: 1px solid #262a33; border-radius: 10px; top: -1px; }
QTabBar::tab { background: transparent; color: #98a0ad; padding: 9px 18px;
               border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: #ffffff; border-bottom: 2px solid #6c8cff; }
QTabBar::tab:hover { color: #cfd4dd; }
QGroupBox { border: 1px solid #262a33; border-radius: 10px; margin-top: 16px;
            padding: 12px 12px 10px 12px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px;
                   color: #8b93a1; }
QPushButton { background: #242833; color: #e7e9ee; border: 1px solid #333845;
              border-radius: 7px; padding: 7px 14px; }
QPushButton:hover { background: #2c313d; }
QPushButton:pressed { background: #353b49; }
QPushButton:checked { background: #2f5bd0; border-color: #3f6be0; color: #fff; }
QPushButton:disabled { color: #5b616d; }
QLineEdit, QComboBox, QSpinBox { background: #1b1e25; color: #e7e9ee;
    border: 1px solid #2a2f3a; border-radius: 7px; padding: 6px; min-height: 22px;
    selection-background-color: #2f5bd0; }
QPlainTextEdit, QTableWidget { background: #1b1e25; color: #e7e9ee;
    border: 1px solid #2a2f3a; border-radius: 7px; padding: 6px;
    selection-background-color: #2f5bd0; }
QFormLayout { spacing: 10px; }
QComboBox::drop-down { border: none; }
QHeaderView::section { background: #1b1e25; color: #8b93a1; border: none;
                       padding: 7px; }
QTableWidget { gridline-color: #262a33; }
QTableWidget::item:selected { background: #2f5bd0; color: #fff; }
QCheckBox { spacing: 8px; }
QLabel#hint { color: #7e8694; }
QLabel#h1 { font-size: 20px; font-weight: 700; }
QLabel#pill { padding: 3px 10px; border-radius: 10px; font-weight: 600; }
"""


def _build_classes():
    from PySide6.QtCore import Qt, QObject, Signal, Slot, QTimer
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QLineEdit, QCheckBox, QComboBox, QSpinBox,
        QPlainTextEdit, QTableWidget, QTableWidgetItem, QFileDialog, QInputDialog,
        QMessageBox, QGroupBox, QFormLayout, QHeaderView, QListWidget,
        QScrollArea,
    )

    from . import auth, credentials_store as store, issues, login as login_mod
    from . import audio as audio_mod
    from .learned_skills import LearnedSkills

    class _NoWheel:
        """Mixin: only react to the mouse wheel when focused (clicked into). When
        just hovered, let the wheel bubble up so the page scrolls instead of the
        control's value changing unintentionally."""
        def wheelEvent(self, e):
            if self.hasFocus():
                super().wheelEvent(e)
            else:
                e.ignore()

    class NoWheelComboBox(_NoWheel, QComboBox):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self.setFocusPolicy(Qt.StrongFocus)

    class NoWheelSpinBox(_NoWheel, QSpinBox):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self.setFocusPolicy(Qt.StrongFocus)

    class LogStream(QObject):
        line = Signal(str)

        def __init__(self, original):
            super().__init__()
            self._orig = original
            self._buf = ""

        def write(self, s):
            try:
                if self._orig:
                    self._orig.write(s)
            except Exception:
                pass
            self._buf += s
            while "\n" in self._buf:
                ln, self._buf = self._buf.split("\n", 1)
                if ln.strip():
                    self.line.emit(ln)

        def flush(self):
            try:
                if self._orig:
                    self._orig.flush()
            except Exception:
                pass

    class ConfirmBridge(QObject):
        request = Signal(str)

        def __init__(self):
            super().__init__()
            self._result = False
            self._event = threading.Event()
            self.request.connect(self._show)

        @Slot(str)
        def _show(self, prompt):
            self._result = QMessageBox.question(
                None, "VoiceClaw — confirm", prompt,
                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes
            self._event.set()

        def confirm(self, prompt: str) -> bool:
            self._event.clear()
            self.request.emit(prompt)
            self._event.wait()
            return self._result

    class MainWindow(QMainWindow):
        BUILTIN_WAKEWORDS = ["hey_jarvis", "alexa", "hey_mycroft"]

        def __init__(self):
            super().__init__()
            self.setWindowTitle("VoiceClaw")
            self.resize(860, 720)
            self.setMinimumSize(720, 560)
            self.cfg = Config.load(CONFIG_FILE)
            self.assistant = None
            self.agent_thread = None
            self.stop_event = threading.Event()
            self.confirm_bridge = ConfirmBridge()
            self._activity = []

            self._logstream = LogStream(sys.stdout)
            self._logstream.line.connect(self._on_log_line)
            sys.stdout = self._logstream

            central = QWidget(); self.setCentralWidget(central)
            root = QVBoxLayout(central)
            root.addLayout(self._header())

            self.tabs = QTabWidget()
            self.tabs.addTab(self._scroll(self._dashboard_tab()), "Dashboard")
            self.tabs.addTab(self._scroll(self._account_tab()), "Account")
            self.tabs.addTab(self._scroll(self._settings_tab()), "Settings")
            self.tabs.addTab(self._scroll(self._learned_tab()), "Learned")
            self.tabs.addTab(self._scroll(self._logs_tab()), "Logs")
            root.addWidget(self.tabs)

            self.console = QPlainTextEdit(); self.console.setReadOnly(True)
            self.console.setMaximumBlockCount(500)
            self.console.setFont(QFont("Consolas", 9))
            self.console.setFixedHeight(150)
            self.console.setVisible(False)
            root.addWidget(self.console)

            self._refresh_account()
            self._refresh_logs()
            self._refresh_learned()
            show_console = bool(self.cfg.data.get("ui", {}).get("show_console", False))
            self.console_chk.setChecked(show_console)
            self.console.setVisible(show_console)

            self._status_timer = QTimer(self)
            self._status_timer.timeout.connect(self._refresh_running_state)
            self._status_timer.start(1000)

        def _header(self):
            row = QHBoxLayout()
            title = QLabel("VoiceClaw"); title.setObjectName("h1")
            row.addWidget(title)
            self.status_pill = QLabel("● stopped"); self.status_pill.setObjectName("pill")
            self.status_pill.setStyleSheet("background:#2a2f3a; color:#98a0ad;")
            row.addWidget(self.status_pill)
            row.addStretch()
            self.console_chk = QCheckBox("Developer console")
            self.console_chk.toggled.connect(self._toggle_console)
            row.addWidget(self.console_chk)
            row.addWidget(QLabel("Mode:"))
            self.mode_combo = NoWheelComboBox(); self.mode_combo.addItems(["voice", "hotkey", "ptt"])
            row.addWidget(self.mode_combo)
            self.dictation_btn = QPushButton("Dictation: off"); self.dictation_btn.setCheckable(True)
            self.dictation_btn.setToolTip("Type what you say into the focused window "
                                          "(dev chats, editors) instead of running commands.")
            self.dictation_btn.clicked.connect(self._toggle_dictation)
            row.addWidget(self.dictation_btn)
            self.start_btn = QPushButton("Start listening")
            self.start_btn.clicked.connect(self._toggle_agent)
            row.addWidget(self.start_btn)
            return row

        def _scroll(self, inner):
            """Wrap a tab's content so it SCROLLS (instead of compressing) when the
            window is made small. Pinning the inner widget's minimum height to its
            preferred height is what forces a scrollbar rather than squeezing rows."""
            inner.setMinimumWidth(540)
            # Pin the content's minimum height to its REAL laid-out height once the
            # event loop has computed it, so the scroll area scrolls (never squeezes).
            def _pin(w=inner):
                w.setMinimumHeight(w.sizeHint().height())
            QTimer.singleShot(0, _pin)
            sa = QScrollArea()
            sa.setWidgetResizable(True)
            sa.setFrameShape(QScrollArea.NoFrame)
            sa.setWidget(inner)
            return sa

        def _toggle_console(self, on):
            self.console.setVisible(on)
            try:
                import yaml
                self.cfg.data.setdefault("ui", {})["show_console"] = bool(on)
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    yaml.safe_dump(self.cfg.data, f, sort_keys=False)
            except Exception:
                pass

        def _on_log_line(self, line):
            self.console.appendPlainText(line)
            self._activity.append(line)
            self._activity = self._activity[-200:]
            if hasattr(self, "activity_list"):
                interesting = (line.startswith("> ") or "[learned]" in line
                               or "[dictation]" in line or "running" in line
                               or line.startswith("  …"))
                if interesting:
                    self.activity_list.addItem(line.strip())
                    self.activity_list.scrollToBottom()
                    if self.activity_list.count() > 50:
                        self.activity_list.takeItem(0)
            if line.startswith("> ") and hasattr(self, "last_cmd_lbl"):
                self.last_cmd_lbl.setText("Last heard:  " + line[2:].strip())

        def _toggle_dictation(self):
            on = self.dictation_btn.isChecked()
            if self.assistant is None:
                self.dictation_btn.setChecked(False)
                QMessageBox.information(self, "VoiceClaw",
                                        "Start listening first, then toggle dictation.")
                return
            self.assistant.dictation_mode = on
            self.dictation_btn.setText("Dictation: ON" if on else "Dictation: off")

        def _dashboard_tab(self):
            w = QWidget(); lay = QVBoxLayout(w)
            status_box = QGroupBox("Status"); sg = QFormLayout(status_box)
            sg.setVerticalSpacing(8)
            self.dash_state = QLabel("stopped")
            self.dash_backend = QLabel("…")
            self.last_cmd_lbl = QLabel("Last heard:  —")
            self.dash_learned = QLabel("…")
            sg.addRow("Listening:", self.dash_state)
            sg.addRow("Agent backend:", self.dash_backend)
            sg.addRow("Learned commands:", self.dash_learned)
            sg.addRow(self.last_cmd_lbl)
            lay.addWidget(status_box)

            act_box = QGroupBox("Recent activity"); ag = QVBoxLayout(act_box)
            self.activity_list = QListWidget()
            ag.addWidget(self.activity_list)
            lay.addWidget(act_box, 1)

            test_box = QGroupBox("Command tester  (no mic — see where a phrase would route)")
            tg = QHBoxLayout(test_box)
            self.test_edit = QLineEdit()
            self.test_edit.setPlaceholderText("e.g. open youtube  /  click on shorts  /  tell Claude continue")
            self.test_edit.returnPressed.connect(self._run_test)
            test_btn = QPushButton("Test route"); test_btn.clicked.connect(self._run_test)
            tg.addWidget(self.test_edit, 1); tg.addWidget(test_btn)
            lay.addWidget(test_box)
            self.test_result = QLabel(""); self.test_result.setWordWrap(True)
            self.test_result.setObjectName("hint")
            lay.addWidget(self.test_result)
            return w

        def _run_test(self):
            text = self.test_edit.text().strip()
            if not text:
                return
            route, detail = self._classify_route(text)
            self.test_result.setText(f"→ {route}\n{detail}")

        def _classify_route(self, text):
            from .app import _is_complex, _dictation_action
            from .local_skills import LocalSkills
            dct = _dictation_action(text, False)
            if dct is not None:
                kind, payload = dct
                if kind == "start":
                    return ("DICTATION (turns on continuous dictation)", "")
                if kind == "stop":
                    return ("DICTATION (turns it off)", "")
                verbatim, send = payload
                return ("DICTATION / relay (typed verbatim)",
                        f"types {verbatim!r}" + (" + Enter" if send else ""))
            asst = getattr(self, "assistant", None)
            ls = asst.learned if asst and asst.learned else LearnedSkills()
            peek = ls.peek(text)
            if peek:
                actions, _ = peek
                return ("LEARNED cache (instant replay)",
                        "; ".join(f"{n} {a}" for n, a in actions))
            if _is_complex(text):
                return ("AGENT (vision / reasoning)", "sent to the model")
            rec = []
            class DryTB:
                def run(self, n, a): rec.append((n, a)); return True
            skills = asst.skills if asst else LocalSkills(enabled=True)
            try:
                skills.handle(text, DryTB())
            except Exception:
                pass
            if rec:
                return ("TIER-1 (instant local)",
                        "; ".join(f"{n} {a}" for n, a in rec))
            return ("AGENT (no local match)", "sent to the model")

        def _account_tab(self):
            w = QWidget(); lay = QVBoxLayout(w)
            self.account_status = QLabel("…"); self.account_status.setWordWrap(True)
            lay.addWidget(self.account_status)

            brow = QHBoxLayout()
            brow.addWidget(QLabel("Agent backend:"))
            self.backend_combo = NoWheelComboBox()
            self.backend_combo.addItems(["auto", "anthropic", "openai", "claude_code"])
            curb = self.cfg["brain"].get("backend", "auto")
            bi = self.backend_combo.findText(curb)
            if bi >= 0:
                self.backend_combo.setCurrentIndex(bi)
            self.backend_combo.currentTextChanged.connect(self._set_backend)
            brow.addWidget(self.backend_combo)
            brow.addWidget(QLabel("(claude_code = your subscription, personal use)"))
            brow.addStretch()
            lay.addLayout(brow)

            box = QGroupBox("Sign in"); bl = QVBoxLayout(box)
            sub = QPushButton("Sign in with Claude subscription (Pro/Max)")
            sub.clicked.connect(self._sign_in_subscription)
            key = QPushButton("Sign in with Anthropic API key")
            key.clicked.connect(self._sign_in_api_key)
            oai = QPushButton("Sign in with OpenAI / Groq / OpenRouter key")
            oai.clicked.connect(self._sign_in_openai)
            out = QPushButton("Sign out")
            out.clicked.connect(self._sign_out)
            for b in (sub, key, oai, out):
                bl.addWidget(b)
            lay.addWidget(box)

            hint = QLabel(
                "Subscription sign-in uses Anthropic's official token "
                "(`claude setup-token`). VoiceClaw never uses claude.ai cookies. "
                "Without sign-in, local voice control still works.")
            hint.setWordWrap(True); hint.setObjectName("hint")
            lay.addWidget(hint)
            lay.addStretch()
            return w

        def _set_backend(self, value):
            try:
                import yaml
                self.cfg.data["brain"]["backend"] = value
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    yaml.safe_dump(self.cfg.data, f, sort_keys=False)
                if self.assistant is not None:
                    self.assistant.reload_auth()
                self._refresh_account()
            except Exception as e:
                QMessageBox.warning(self, "VoiceClaw", f"Couldn't set backend: {e}")

        def _refresh_account(self):
            import os as _os, shutil as _sh
            creds = auth.resolve(self.cfg)
            ocfg = self.cfg["brain"].get("openai", {}) or {}
            openai_present = bool(
                _os.environ.get(ocfg.get("api_key_env", "OPENAI_API_KEY"))
                or ocfg.get("api_key") or store.load("openai_key"))
            cc = _sh.which("claude") is not None
            backend = self.cfg["brain"].get("backend", "auto")
            parts = [
                f"Anthropic: {creds.mode if creds.usable else 'no'}",
                f"OpenAI/Groq: {'yes' if openai_present else 'no'}",
                f"Claude Code (personal): {'available' if cc else 'no'}",
            ]
            self.account_status.setText(
                f"Backend: {backend}   |   store: {store.backend_name()}\n"
                + "   •   ".join(parts) +
                "\nNo credential? The free local tier still works offline.")

        def _sign_in_subscription(self):
            token, ok = QInputDialog.getText(
                self, "Sign in — subscription",
                "Run `claude setup-token` in a terminal, then paste the token:",
                QLineEdit.Password)
            if not ok:
                return
            if not login_mod._looks_like_token(token):
                QMessageBox.warning(self, "VoiceClaw", "That doesn't look like a token.")
                return
            store.save("oauth_token", token.strip())
            self._apply_auth_change()

        def _sign_in_api_key(self):
            key, ok = QInputDialog.getText(
                self, "Sign in — API key", "Paste your Anthropic API key:",
                QLineEdit.Password)
            if not ok:
                return
            if not login_mod._looks_like_token(key):
                QMessageBox.warning(self, "VoiceClaw", "That doesn't look like a key.")
                return
            store.save("api_key", key.strip())
            self._apply_auth_change()

        def _sign_in_openai(self):
            key, ok = QInputDialog.getText(
                self, "Sign in — OpenAI / Groq / OpenRouter key",
                "Paste your API key (OpenAI sk-..., Groq gsk_..., OpenRouter sk-or-...):",
                QLineEdit.Password)
            if not ok:
                return
            key = (key or "").strip()
            if not key:
                QMessageBox.warning(self, "VoiceClaw", "No key entered.")
                return
            store.save("openai_key", key)
            self._apply_auth_change()

        def _sign_out(self):
            store.clear()
            self._apply_auth_change()

        def _apply_auth_change(self):
            self._refresh_account()
            if self.assistant is not None:
                self.assistant.reload_auth()
            QMessageBox.information(self, "VoiceClaw", "Credentials updated.")

        def _settings_tab(self):
            w = QWidget(); lay = QVBoxLayout(w)

            ww_box = QGroupBox("Wake words (enable one or more)")
            wwl = QVBoxLayout(ww_box)
            self.ww_checks = {}
            active = set(self.cfg.wake_models)
            for name in self.BUILTIN_WAKEWORDS:
                cb = QCheckBox(name); cb.setChecked(name in active)
                self.ww_checks[name] = cb; wwl.addWidget(cb)
            crow = QHBoxLayout()
            self.custom_ww = QLineEdit(self.cfg["wakeword"].get("custom_model_path", ""))
            self.custom_ww.setPlaceholderText("custom model path (for 'hey claude')")
            browse = QPushButton("Browse")
            browse.clicked.connect(lambda: self._pick_file(self.custom_ww))
            crow.addWidget(QLabel("Custom:")); crow.addWidget(self.custom_ww); crow.addWidget(browse)
            wwl.addLayout(crow)
            lay.addWidget(ww_box)

            form_box = QGroupBox("Audio, voice, hotkeys"); form = QFormLayout(form_box)
            form.setVerticalSpacing(10); form.setLabelAlignment(Qt.AlignLeft)
            form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
            self.mic_combo = NoWheelComboBox()
            self.mic_combo.addItem("System default", None)
            for idx, name in audio_mod.list_input_devices():
                self.mic_combo.addItem(f"{idx}: {name}", idx)
            cur_dev = self.cfg.get("audio", {}).get("input_device")
            i = self.mic_combo.findData(cur_dev)
            if i >= 0:
                self.mic_combo.setCurrentIndex(i)
            form.addRow("Microphone:", self.mic_combo)
            self.stt_combo = NoWheelComboBox()
            self.stt_combo.addItems(["tiny.en", "base.en", "small.en", "medium.en"])
            cur_model = self.cfg["stt"].get("model", "small.en")
            j = self.stt_combo.findText(cur_model)
            if j >= 0:
                self.stt_combo.setCurrentIndex(j)
            form.addRow("Speech model:", self.stt_combo)

            self.rate_spin = NoWheelSpinBox(); self.rate_spin.setRange(80, 400)
            self.rate_spin.setValue(int(self.cfg["tts"].get("rate", 185)))
            form.addRow("Voice rate (wpm):", self.rate_spin)

            self.ptt_edit = QLineEdit(self.cfg["hotkeys"].get("push_to_talk", ""))
            form.addRow("Push-to-talk hotkey:", self.ptt_edit)
            self.kill_edit = QLineEdit(self.cfg["hotkeys"].get("kill_switch", ""))
            form.addRow("Kill-switch hotkey:", self.kill_edit)
            self.dictation_key_edit = QLineEdit(self.cfg["hotkeys"].get("dictation_ptt", "<ctrl_r>"))
            form.addRow("Hold-to-dictate key:", self.dictation_key_edit)

            self.idle_spin = NoWheelSpinBox(); self.idle_spin.setRange(0, 36000)
            self.idle_spin.setValue(int(self.cfg["runtime"].get("idle_unload_seconds", 300)))
            form.addRow("Idle model unload (s):", self.idle_spin)

            self.local_chk = QCheckBox("Use local model (Ollama) for quick questions")
            self.local_chk.setChecked(bool(self.cfg["local_llm"].get("enabled", True)))
            form.addRow(self.local_chk)
            self.learn_chk = QCheckBox("Learn repeated commands from the agent for instant reuse")
            self.learn_chk.setChecked(bool(self.cfg.data.get("learning", {}).get("enabled", True)))
            form.addRow(self.learn_chk)
            lay.addWidget(form_box)

            paths_box = QGroupBox("Allowed folders (one per line; empty = home only)")
            pl = QVBoxLayout(paths_box)
            self.paths_edit = QPlainTextEdit(
                "\n".join(self.cfg["agent"].get("allowed_paths", []) or []))
            self.paths_edit.setFixedHeight(64)
            pl.addWidget(self.paths_edit)
            lay.addWidget(paths_box)

            save = QPushButton("Save settings")
            save.clicked.connect(self._save_settings)
            lay.addWidget(save)
            lay.addStretch()
            return w

        def _pick_file(self, line_edit):
            path, _ = QFileDialog.getOpenFileName(self, "Choose model file")
            if path:
                line_edit.setText(path)

        def _save_settings(self):
            d = self.cfg.data
            d["wakeword"]["models"] = [n for n, cb in self.ww_checks.items()
                                       if cb.isChecked()] or ["hey_jarvis"]
            d["wakeword"]["custom_model_path"] = self.custom_ww.text().strip()
            d.setdefault("audio", {})["input_device"] = self.mic_combo.currentData()
            d["tts"]["rate"] = self.rate_spin.value()
            d["stt"]["model"] = self.stt_combo.currentText()
            d["hotkeys"]["push_to_talk"] = self.ptt_edit.text().strip()
            d["hotkeys"]["kill_switch"] = self.kill_edit.text().strip()
            d["hotkeys"]["dictation_ptt"] = self.dictation_key_edit.text().strip()
            d["runtime"]["idle_unload_seconds"] = self.idle_spin.value()
            d["local_llm"]["enabled"] = self.local_chk.isChecked()
            d.setdefault("learning", {})["enabled"] = self.learn_chk.isChecked()
            d["agent"]["allowed_paths"] = [p.strip() for p in
                                           self.paths_edit.toPlainText().splitlines()
                                           if p.strip()]
            try:
                import yaml
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    yaml.safe_dump(d, f, sort_keys=False)
                QMessageBox.information(
                    self, "VoiceClaw",
                    "Saved to config.yaml. Restart listening to apply.")
            except Exception as e:
                QMessageBox.warning(self, "VoiceClaw", f"Could not save: {e}")

        def _learned_tab(self):
            w = QWidget(); lay = QVBoxLayout(w)
            top = QHBoxLayout()
            self.learned_search = QLineEdit()
            self.learned_search.setPlaceholderText("Search learned commands…")
            self.learned_search.textChanged.connect(self._refresh_learned)
            top.addWidget(self.learned_search)
            lay.addLayout(top)

            self.learned_table = QTableWidget(0, 4)
            self.learned_table.setHorizontalHeaderLabels(
                ["Phrase", "Action(s)", "Hits", "Last used"])
            self.learned_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            self.learned_table.setSelectionBehavior(QTableWidget.SelectRows)
            lay.addWidget(self.learned_table)

            row = QHBoxLayout()
            self.learned_count2 = QLabel("")
            delsel = QPushButton("Delete selected"); delsel.clicked.connect(self._delete_selected_learned)
            clr = QPushButton("Forget all"); clr.clicked.connect(self._forget_learned)
            row.addWidget(self.learned_count2); row.addStretch()
            row.addWidget(delsel); row.addWidget(clr)
            lay.addLayout(row)
            return w

        def _learned_store(self):
            asst = getattr(self, "assistant", None)
            return asst.learned if asst and asst.learned else LearnedSkills()

        def _refresh_learned(self):
            ls = self._learned_store()
            q = self.learned_search.text().strip().lower() if hasattr(self, "learned_search") else ""
            rows = []
            for key, e in ls.items():
                raw = e.get("raw", key)
                actions = "; ".join(f"{n} {a}" for n, a in e.get("actions", []))
                if q and q not in raw.lower() and q not in actions.lower():
                    continue
                rows.append((raw, actions, str(e.get("hits", 0)), e.get("ts", "")))
            self.learned_table.setRowCount(len(rows))
            for r, vals in enumerate(rows):
                for c, v in enumerate(vals):
                    item = QTableWidgetItem(v)
                    if c == 0:
                        item.setData(Qt.UserRole, vals[0])
                    self.learned_table.setItem(r, c, item)
            self.learned_count2.setText(f"{ls.count()} learned command(s)")
            if hasattr(self, "dash_learned"):
                self.dash_learned.setText(f"{ls.count()} stored")

        def _delete_selected_learned(self):
            ls = self._learned_store()
            rows = sorted({i.row() for i in self.learned_table.selectedItems()}, reverse=True)
            for r in rows:
                it = self.learned_table.item(r, 0)
                if it:
                    ls.delete(it.text())
            self._refresh_learned()

        def _forget_learned(self):
            try:
                self._learned_store().clear()
                self._refresh_learned()
                QMessageBox.information(self, "VoiceClaw", "Forgot all learned commands.")
            except Exception as e:
                QMessageBox.warning(self, "VoiceClaw", f"Could not clear: {e}")

        def _logs_tab(self):
            w = QWidget(); lay = QVBoxLayout(w)
            self.logs_table = QTableWidget(0, 4)
            self.logs_table.setHorizontalHeaderLabels(["Time", "Level", "Source", "Message"])
            self.logs_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
            lay.addWidget(self.logs_table)
            row = QHBoxLayout()
            refresh = QPushButton("Refresh"); refresh.clicked.connect(self._refresh_logs)
            clear = QPushButton("Clear log"); clear.clicked.connect(self._clear_logs)
            row.addWidget(refresh); row.addWidget(clear); row.addStretch()
            lay.addLayout(row)
            return w

        def _refresh_logs(self):
            rows = issues.read_issues(300)
            self.logs_table.setRowCount(len(rows))
            for r, it in enumerate(reversed(rows)):
                for c, k in enumerate(("time", "level", "source", "message")):
                    self.logs_table.setItem(r, c, QTableWidgetItem(it[k]))

        def _clear_logs(self):
            issues.clear_issues(); self._refresh_logs()

        def _toggle_agent(self):
            if self.agent_thread and self.agent_thread.is_alive():
                self.stop_event.set()
                self.start_btn.setText("Stopping…")
                return
            from .app import build
            self.cfg = Config.load(CONFIG_FILE)
            self.assistant = build(self.cfg, confirm_cb=self.confirm_bridge.confirm)
            print(f"[backend] {self.assistant.auth_message or 'no agent'} "
                  f"(mode={self.assistant.auth_mode})")
            self.stop_event.clear()
            mode = self.mode_combo.currentText()

            def worker():
                import main as cli
                fn = {"voice": cli.run_voice, "hotkey": cli.run_hotkey,
                      "ptt": cli.run_ptt}.get(mode, cli.run_voice)
                try:
                    fn(self.assistant, stop_flag=lambda: self.stop_event.is_set())
                except TypeError:
                    fn(self.assistant)
                except Exception as e:
                    issues.log_issue("ui.agent", e)

            self.agent_thread = threading.Thread(target=worker, daemon=True)
            self.agent_thread.start()
            self.start_btn.setText("Stop listening")
            self._refresh_learned()

        def _refresh_running_state(self):
            alive = bool(self.agent_thread and self.agent_thread.is_alive())
            self.status_pill.setText("● listening" if alive else "● stopped")
            self.status_pill.setStyleSheet(
                "background:#16361f; color:#54d18a;" if alive
                else "background:#2a2f3a; color:#98a0ad;")
            self.dash_state.setText("listening" if alive else "stopped")
            self.dash_backend.setText(
                (self.assistant.auth_message if self.assistant else None) or "not started")
            if not alive and self.start_btn.text() != "Start listening":
                self.start_btn.setText("Start listening")
            dm = bool(self.assistant and getattr(self.assistant, "dictation_mode", False))
            if dm != self.dictation_btn.isChecked():
                self.dictation_btn.setChecked(dm)
                self.dictation_btn.setText("Dictation: ON" if dm else "Dictation: off")

    return QApplication, MainWindow


def main():
    if not ui_available():
        print("The desktop UI needs PySide6:  pip install PySide6")
        return 1
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    QApplication, MainWindow = _build_classes()
    app = QApplication(sys.argv)
    app.setApplicationName("VoiceClaw")
    app.setStyleSheet(APP_QSS)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())