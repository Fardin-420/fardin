# NPC_VOICE_V1 synthesis pipeline

The pipeline code lives in `NPC_STUDIO/VOICE_ENGINE/`, so every project shares one engine:

- `npc_voice.py` — shared helpers: reference cleanup, analysis, model loading, `Voice.say()` with best-of-N speaker-similarity gating
- `register_voice.py` — registers or extends the reference and writes `../voice_config.json`
- `voice_test.py` — short test, one line per emotion, scored against the reference
- `build_narration.py` — renders a project's script line by line and writes measured timings

Environment: `VOICE_ENGINE/.venv` (Python 3.11, torch 2.6 CPU, chatterbox-tts 0.1.7).
Rebuild it with:
`uv venv --python 3.11 .venv && uv pip install --python .venv/bin/python chatterbox-tts librosa soundfile pyloudnorm`
