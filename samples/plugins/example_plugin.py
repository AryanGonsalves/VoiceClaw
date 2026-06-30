"""Example VoiceClaw plugin.

Copy this file to ~/.voiceclaw/plugins/ to activate it. It adds a local voice
command ("good night") and a Claude tool ("flip_coin").
"""


def register(reg):
    # Tier-1 local skill: instant, offline. handler(match, toolbox) -> spoken reply.
    reg.add_skill(
        r"\b(good night|goodnight)\b",
        lambda m, tb: tb.run("press_keys", {"keys": "volumemute"}) and "Good night.",
    )

    # A Claude tool: schema + impl(args, toolbox) -> string result.
    reg.add_tool(
        {
            "name": "flip_coin",
            "description": "Flip a fair coin and return heads or tails.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        lambda args, toolbox: __import__("random").choice(["heads", "tails"]),
    )
