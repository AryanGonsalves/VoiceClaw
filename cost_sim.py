"""VoiceClaw cost simulation: gpt-4o-mini vs gpt-5.4-mini.

Models the REAL token drivers of this app:
  - system prompt + ~20 tool schemas are resent on every model call in the loop
  - one screenshot is kept in context per call (we prune older ones)
  - the agent loop takes several calls for vision/multi-step tasks
  - the learned-cache + Tier-1 make most *repeated* commands free (no model call)

All numbers are clearly-labeled ESTIMATES; tweak the ASSUMPTIONS block to taste.
"""

# ---- PRICES ($ per 1M tokens), verified Jun 2026 -------------------------
PRICE = {
    "gpt-4o-mini":  {"in": 0.15, "out": 0.60},
    "gpt-5.4-mini": {"in": 0.75, "out": 4.50},
}

# ---- ASSUMPTIONS ---------------------------------------------------------
SYS_PROMPT_TOK   = 550     # grounding system prompt
TOOL_SCHEMA_TOK  = 1900    # ~20 tool JSON schemas, resent each call
IMG_TOK          = 1200    # one 1280px high-detail screenshot (~6 tiles, 4o tile math)
OUT_PER_CALL     = 45      # avg output tokens per model call (a tool call or short reply)

# command "shapes": how many model calls + how many screenshots each
SHAPES = {
    "simple_agent": {"calls": 2, "shots": 2},   # e.g. "pull up my morning news"
    "vision_multi": {"calls": 5, "shots": 5},   # e.g. "find a cat video and play it"
}

# ---- usage profile (ideal: user reuses phrasings, cache absorbs repeats) --
CMDS_PER_DAY     = 40
CACHE_FREE_FRAC  = 0.75    # Tier-1 + learned-cache hits -> $0 (no model call)
# of the remaining (agent) commands, the split:
AGENT_MIX        = {"simple_agent": 0.6, "vision_multi": 0.4}
DAYS             = 30


def call_input_tokens(call_idx, has_shot):
    """Input tokens for one model call: fixed overhead + growing history + 1 image."""
    base = SYS_PROMPT_TOK + TOOL_SCHEMA_TOK
    history = call_idx * 300          # prior assistant/tool messages accumulate
    img = IMG_TOK if has_shot else 0
    return base + history + img


def command_tokens(shape):
    calls, shots = SHAPES[shape]["calls"], SHAPES[shape]["shots"]
    tin = sum(call_input_tokens(i, has_shot=(i < shots)) for i in range(calls))
    tout = calls * OUT_PER_CALL
    return tin, tout


def cost(model, tin, tout):
    p = PRICE[model]
    return tin / 1e6 * p["in"] + tout / 1e6 * p["out"]


print("=== Per-command token + cost estimate ===\n")
print(f"{'command type':16} {'in tok':>8} {'out tok':>8} "
      f"{'4o-mini $':>11} {'5.4-mini $':>12}")
for shape in SHAPES:
    tin, tout = command_tokens(shape)
    c4 = cost("gpt-4o-mini", tin, tout)
    c5 = cost("gpt-5.4-mini", tin, tout)
    print(f"{shape:16} {tin:8d} {tout:8d} {c4:11.5f} {c5:12.5f}  ({c5/c4:.1f}x)")

# ---- daily / monthly under the usage profile -----------------------------
agent_cmds = CMDS_PER_DAY * (1 - CACHE_FREE_FRAC)
free_cmds  = CMDS_PER_DAY * CACHE_FREE_FRAC

daily = {"gpt-4o-mini": 0.0, "gpt-5.4-mini": 0.0}
for shape, frac in AGENT_MIX.items():
    n = agent_cmds * frac
    tin, tout = command_tokens(shape)
    for model in PRICE:
        daily[model] += n * cost(model, tin, tout)

print("\n=== Usage profile ===")
print(f"  {CMDS_PER_DAY} commands/day | {CACHE_FREE_FRAC*100:.0f}% free "
      f"(Tier-1 + learned cache) | {agent_cmds:.0f} hit the agent "
      f"({free_cmds:.0f} free)")
print(f"  agent mix: {AGENT_MIX}")

print("\n=== Cost ===")
print(f"{'model':14} {'per day':>10} {'per month':>12} {'per year':>10}")
for model in PRICE:
    d = daily[model]
    print(f"{model:14} {d:10.4f} {d*DAYS:12.2f} {d*365:10.2f}")

ratio = daily["gpt-5.4-mini"] / daily["gpt-4o-mini"]
print(f"\n5.4-mini costs ~{ratio:.1f}x more per month "
      f"(${daily['gpt-5.4-mini']*DAYS:.2f} vs ${daily['gpt-4o-mini']*DAYS:.2f}).")

# ---- sensitivity: heavier screenshots (mini image-billing multiple) ------
print("\n=== Sensitivity: if screenshots cost more tokens (heavier vision) ===")
for img in (1200, 4000, 8000):
    globals()['IMG_TOK'] = img
    dd = {m: 0.0 for m in PRICE}
    for shape, frac in AGENT_MIX.items():
        n = agent_cmds * frac
        tin, tout = command_tokens(shape)
        for m in PRICE:
            dd[m] += n * cost(m, tin, tout)
    print(f"  img={img:5d} tok/shot -> 4o-mini ${dd['gpt-4o-mini']*DAYS:6.2f}/mo | "
          f"5.4-mini ${dd['gpt-5.4-mini']*DAYS:6.2f}/mo")
