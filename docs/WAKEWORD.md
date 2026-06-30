# Getting a real "Hey Claude" wake word

openWakeWord (the default) has no built-in "claude" model. Two ways to wake on
the literal phrase "Hey Claude":

## Option A — Picovoice Porcupine (easiest, recommended)
1. Make a free account at https://console.picovoice.ai/
2. Create a **custom wake word** "Hey Claude" for **Windows**, download the `.ppn`.
3. Copy your **Access Key** from the console.
4. Put the file somewhere (e.g. `D:\VoiceClaw\models\Hey-Claude_windows.ppn`).
5. In `config.yaml`:
   ```yaml
   wakeword:
     engine: "porcupine"
     porcupine:
       access_key: "YOUR_ACCESS_KEY"
       keyword_path: "models/Hey-Claude_windows.ppn"
       sensitivity: 0.5
   ```
6. `pip install pvporcupine` (already in requirements.txt), then run normally.

Pros: works in minutes, robust. Cons: needs a (free) key; Picovoice's terms apply.

## Option B — train an openWakeWord model (fully free/offline)
openWakeWord can train a model from synthetic speech (no recordings needed):
1. Use the official openWakeWord training notebook/automatic pipeline
   (https://github.com/dscripka/openWakeWord) with the phrase "hey claude".
   This needs a GPU (Google Colab works) and produces a `.onnx`/`.tflite`.
2. Put the file in `models/` and set:
   ```yaml
   wakeword:
     engine: "openwakeword"
     custom_model_path: "models/hey_claude.onnx"
   ```
Pros: 100% free/offline, no key. Cons: training step; accuracy depends on data.

## Tuning
- Too many false triggers → raise `sensitivity` (Porcupine) / `threshold` (oWW)
  is *lower* = more sensitive for oWW, so raise it; for Porcupine higher = more
  sensitive, so lower it.
- Strong accent → record-based custom training (Porcupine custom or oWW with your
  samples) helps most.
