# VoiceClaw — Copyright (c) 2026 Aryan Gonsalves. All rights reserved. Proprietary; see LICENSE.
"""Plugin interface for community-contributed skills and tools.

A plugin is a single .py file in ~/.voiceclaw/plugins/ that defines:

    def register(reg):
        reg.add_skill(r"\\bgood night\\b", lambda m, tb: tb.run("press_keys",
                      {"keys": "volumemute"}) and "Good night.")
        reg.add_tool(SCHEMA_DICT, lambda args, toolbox: "result string")

- add_skill(pattern, handler): a Tier-1 rule (regex + handler(match, toolbox)).
- add_tool(schema, impl): a new Claude tool (Anthropic schema + impl(args, toolbox)).

Plugins load at startup and extend the running assistant. They run with the same
privileges as the app, so only install plugins you trust. See docs/PLUGINS.md.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Any, Callable, Dict, List

PLUGINS_DIR = Path(os.path.expanduser("~/.voiceclaw/plugins"))


class Registry:
    def __init__(self, skills, toolbox):
        self.skills = skills
        self.toolbox = toolbox

    def add_skill(self, pattern: str, handler: Callable) -> None:
        self.skills.add_rule(pattern, handler)

    def add_tool(self, schema: Dict[str, Any], impl: Callable) -> None:
        self.toolbox.register_tool(schema, impl)


def load_plugins(skills, toolbox) -> List[str]:
    """Import every plugin and let it register skills/tools. Returns loaded names."""
    loaded: List[str] = []
    if not PLUGINS_DIR.exists():
        return loaded
    reg = Registry(skills, toolbox)
    for f in sorted(PLUGINS_DIR.glob("*.py")):
        if f.name.startswith("_"):
            continue
        try:
            spec = importlib.util.spec_from_file_location(f"vc_plugin_{f.stem}", f)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            if hasattr(mod, "register"):
                mod.register(reg)
                loaded.append(f.stem)
        except Exception as e:
            try:
                from .issues import log_issue
                log_issue(f"plugin:{f.name}", e)
            except Exception:
                pass
    return loaded