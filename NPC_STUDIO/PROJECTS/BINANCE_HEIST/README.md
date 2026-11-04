# THE 20-MINUTE HEIST — production folder

A factual documentary about the October 29, 2026 Binance security incident, built with NPC STUDIO's code-only pipeline. Spec: `/BINANCE_HEIST_MASTER_PROMPT.md`. Facts: `research/fact-ledger.md`. QA: `out/QA_REPORT.md`.

## Rebuild (or swap the narrator)
```bash
cd NPC_STUDIO/PROJECTS/BINANCE_HEIST
.venv/bin/python scripts/build_vo.py --voice am_puck     # or am_michael / am_fenrir — voice is swappable
.venv/bin/python scripts/build_timeline.py              # master clock → RENDER_ENGINE/src/heist/data/timeline.json + audio/vo_track.wav
.venv/bin/python scripts/build_captions.py              # caption pages + out/captions_en.srt
.venv/bin/python scripts/sound.py                       # score + SFX + ducking + −14 LUFS master
cd ../../RENDER_ENGINE
node pipeline/render_heist.mjs video ../PROJECTS/BINANCE_HEIST/out/chunks/c1.mp4 0 12999
node pipeline/render_heist.mjs video ../PROJECTS/BINANCE_HEIST/out/chunks/c2.mp4 13000   # to the end
node pipeline/render_heist.mjs thumbs ../PROJECTS/BINANCE_HEIST/out
cd ../PROJECTS/BINANCE_HEIST
.venv/bin/python scripts/finalize.py && .venv/bin/python scripts/qa.py
```
Setup: `uv venv --python 3.11 .venv && uv pip install --python .venv/bin/python kokoro-onnx num2words numpy scipy soundfile pyloudnorm pillow`. Kokoro model files go in `NPC_STUDIO/VOICE_ENGINE/models/kokoro/` (git-ignored; from the kokoro-onnx `model-files-v1.0` release). Chunks render in any split; `finalize.py` concatenates `out/chunks/c*.mp4` in numeric order.

## Drop-in upgrades
- **AI shots**: place `assets/ai/AI-01.mp4 … AI-13.mp4` and wire them into the matching plate slots, then set YouTube "altered or synthetic content" to **Yes**.
- **Licensed music**: `assets/music/act1_coldopen.wav … act7_outro.wav` replace the generated beds automatically (`sound.py`).
- **Captions off**: render with `inputProps {burnCaptions:false}` and upload the SRT only.
