# Open-core: full app, hidden core

Goal: users install the **full, working app**, but the proprietary "moat" — the
Tier-1 command grammar and the learned-command cache — **cannot be read** as source.

## What's where

| Part | Where it lives | Ships to users? | Readable? |
|------|----------------|-----------------|-----------|
| Shell (UI, voice I/O, tools, agent backends, installer) | **public repo** | yes | yes (open) |
| Core moat (`voiceclaw/core/`: grammar + learned cache) | **private** (git-ignored from public repo) | yes, as compiled `.pyd` | **no** |
| Grammar corpus & tests (`routing_*.py`, grammar test files) | **private** | no | no |

The public repo's `.gitignore` excludes `voiceclaw/core/` and the grammar
corpus/tests, so cloning the public repo never reveals the moat. If the core is
absent, the shims in `voiceclaw/local_skills.py` / `learned_skills.py` fall back
to an agent-only mode — the app still runs, just without the instant offline
grammar/learning. (Keep the core's source in a SEPARATE PRIVATE repo or backup.)

## What v0.1.0 actually shipped
The first release ships the core as **compiled Python bytecode (`.pyc`) inside the
PyInstaller archive** — the installer contains no `.py` source for the core, only the
public shims are readable. That is a solid deterrent (no readable source), though weaker
than a Cython `.pyd`. The `.pyd` path below needs the Microsoft C++ Build Tools, which
weren't available on the build machine (install blocked by UAC); PyArmor is the
no-compiler alternative.

## Release flow (build machine, where the core source IS present)

1. **Compile the core to binary:**
   ```
   packaging\build_core.bat
   ```
   (Cython → `voiceclaw/core/local_skills.pyd` + `learned_skills.pyd`.
   Requires `pip install cython` and the Microsoft C++ Build Tools.)
2. **Drop the readable source so only the binary ships:**
   ```
   del voiceclaw\core\local_skills.py voiceclaw\core\learned_skills.py
   ```
   (Keep your originals in the private repo — this only affects the build dir.)
3. **Build the app/installer** (PyInstaller + Inno Setup): see `packaging/BUILD.md`.
   PyInstaller bundles the `.pyd`; the shipped `.exe` runs the full app, and the
   core is a compiled binary — no Python source to read.

## No C compiler? PyArmor fallback
```
pip install pyarmor
pyarmor gen -O voiceclaw\core_obf voiceclaw\core\local_skills.py voiceclaw\core\learned_skills.py
```
Then point the package at the obfuscated output. Obfuscation is easier to set up
but weaker than compilation.

## Honest limits
Anything that runs on a user's machine — `.pyc`, PyArmor, or a Cython `.pyd` —
can be reverse-engineered with enough effort; compilation/obfuscation is a strong
**deterrent**, not an unbreakable lock. The only *true* hiding is running the core
on **your server** (the app calls it over the network; the logic never ships). The
license is your legal backstop; this is the technical one.
