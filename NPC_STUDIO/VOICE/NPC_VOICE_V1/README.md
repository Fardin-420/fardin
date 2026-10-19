# NPC_VOICE_V1

NPC's permanent narration voice. Every NPC video narrates with this profile.
The pipeline never swaps in a generic or stock voice.

## Contents

| Path | What | In git? |
|---|---|---|
| `original_reference/` | Raw recordings exactly as provided | **No** (private) |
| `clean_reference/` | Gently cleaned 24 kHz mono reference (`npc_reference_clean.wav`) | **No** (private) |
| `voice_config.json` | Analysis, readiness, engine and per-emotion synthesis settings | Yes |
| `synthesis_pipeline/` | Pointer to the engine code in `../../VOICE_ENGINE` | Yes |
| `voice_tests/` | Generated test lines + `voice_test_report.json` | **No** (private) |

The repository is public, so `.gitignore` excludes every file containing your voice.
The recordings stay inside this workspace and are never uploaded to any external service.

## Current status

**Not ready for cloning.** The first recording (`npc_ref_001.m4a`) has only
**1.9 s of speech**. Analysis: male voice, median F0 ≈ 135 Hz (range ≈ 119–149 Hz),
very clean (estimated SNR ≈ 38 dB). Chatterbox needs **at least 8 s, ideally 20–30 s**
of continuous speech to reproduce the timbre and accent reliably.

## Register or extend the reference

Record 20–30 s of natural English speech (reading the voiceover script is ideal)
in a quiet room, then:

```bash
cd NPC_STUDIO/VOICE_ENGINE
.venv/bin/python register_voice.py /path/to/new_recording.m4a   # appended to existing takes
.venv/bin/python voice_test.py                                   # 7 emotions, speaker-similarity scored
```

`register_voice.py` keeps every take, cleans each one (70 Hz high-pass, light spectral
denoise at `nr=10` so the vocal texture survives, edge trim, −20 LUFS), joins them, re-analyzes,
and sets `ready_for_cloning`.

## How consistency is enforced

* One reference file and one fixed seed for every line.
* Emotions only change Chatterbox's `exaggeration`, `cfg_weight` and `temperature`. The speaker conditioning always comes from the same reference.
* Each line is generated as 3 takes. The take with the highest speaker-embedding similarity to the reference wins.
* A line that falls below `min_speaker_similarity` (0.80) fails the build instead of shipping.

## Engine

Chatterbox TTS 0.1.7 (ResembleAI, MIT), running locally on CPU. The weights download from
`huggingface.co/ResembleAI/chatterbox`. If that host is blocked, place `ve.safetensors`,
`t3_cfg.safetensors`, `s3gen.safetensors`, `tokenizer.json` and `conds.pt` in
`NPC_STUDIO/VOICE_ENGINE/models/chatterbox/` and the engine loads them from there.
