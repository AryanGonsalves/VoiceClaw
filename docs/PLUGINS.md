# Writing VoiceClaw plugins

Plugins let the community add new voice commands and tools without touching core
code. A plugin is a single `.py` file in `~/.voiceclaw/plugins/` that defines a
`register(reg)` function. Plugins load at startup.

> Plugins run with the same privileges as the app. Only install ones you trust.

## API

```python
def register(reg):
    # 1) A local skill (Tier 1): instant, offline. Regex + handler(match, toolbox).
    reg.add_skill(r"\bgood night\b",
                  lambda m, tb: tb.run("press_keys", {"keys": "volumemute"}) and "Good night.")

    # 2) A Claude tool: Anthropic schema + impl(args, toolbox) -> str.
    reg.add_tool(
        {"name": "flip_coin",
         "description": "Flip a fair coin.",
         "input_schema": {"type": "object", "properties": {}, "required": []}},
        lambda args, toolbox: __import__("random").choice(["heads", "tails"]))
```

- **add_skill(pattern, handler)** — `handler(match, toolbox)` returns the spoken
  reply string. Use `toolbox.run("press_keys"|"open_app"|...)` to act.
- **add_tool(schema, impl)** — `impl(args, toolbox)` returns a string the model
  reads. The tool becomes available to Claude automatically.

## Install
1. Copy `samples/plugins/example_plugin.py` to `~/.voiceclaw/plugins/`.
2. Restart VoiceClaw. You should see `[plugins] loaded: example_plugin`.
3. Say "good night" (mutes), or ask Claude something that needs `flip_coin`.

Errors in a plugin are logged to `~/.voiceclaw/issues.log` and never crash the app.
