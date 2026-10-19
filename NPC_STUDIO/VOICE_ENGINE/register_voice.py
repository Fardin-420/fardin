"""Register (or extend) the NPC_VOICE_V1 reference.

    .venv/bin/python register_voice.py path/to/recording.m4a [more.m4a ...]

Copies each recording into original_reference/, joins and cleans them into
clean_reference/npc_reference_clean.wav, analyzes the voice and writes
voice_config.json. Nothing is uploaded anywhere.
"""
from __future__ import annotations

import shutil
import sys
from datetime import date
from pathlib import Path

from npc_voice import (CONFIG_PATH, MIN_SPEECH_SECONDS, PROFILE_DIR, RECOMMENDED_SPEECH_SECONDS,
                       STUDIO, analyze, clean_reference, run, save_config)

EMOTIONS = {
    # exaggeration: emotional intensity; cfg_weight: lower = slower, more deliberate pacing
    "CALM":       {"exaggeration": 0.35, "cfg_weight": 0.50, "temperature": 0.70},
    "MYSTERIOUS": {"exaggeration": 0.40, "cfg_weight": 0.35, "temperature": 0.70},
    "CONFIDENT":  {"exaggeration": 0.50, "cfg_weight": 0.50, "temperature": 0.75},
    "CINEMATIC":  {"exaggeration": 0.60, "cfg_weight": 0.35, "temperature": 0.75},
    "DRAMATIC":   {"exaggeration": 0.70, "cfg_weight": 0.30, "temperature": 0.75},
    "AGGRESSIVE": {"exaggeration": 0.80, "cfg_weight": 0.35, "temperature": 0.80},
    "ENERGETIC":  {"exaggeration": 0.70, "cfg_weight": 0.50, "temperature": 0.80},
}


def main(paths: list[str]) -> None:
    orig_dir = PROFILE_DIR / "original_reference"
    clean_dir = PROFILE_DIR / "clean_reference"
    stored = sorted(p for p in orig_dir.iterdir() if p.name != ".gitkeep")
    for p in map(Path, paths):
        dst = orig_dir / f"npc_ref_{len(stored) + 1:03d}{p.suffix.lower()}"
        shutil.copy2(p, dst)
        stored.append(dst)
    if not stored:
        raise SystemExit("No reference recordings. Pass at least one file.")

    # Clean each take, then join with short gaps into one reference.
    cleaned = []
    for p in stored:
        out = clean_dir / f"{p.stem}_clean.wav"
        clean_reference(p, out)
        cleaned.append(out)
    joined = clean_dir / "npc_reference_clean.wav"
    if len(cleaned) == 1:
        shutil.copy2(cleaned[0], joined)
    else:
        inputs, filt = [], ""
        for i, c in enumerate(cleaned):
            inputs += ["-i", str(c)]
            filt += f"[{i}:a]apad=pad_dur=0.35[a{i}];"
        filt += "".join(f"[a{i}]" for i in range(len(cleaned))) + f"concat=n={len(cleaned)}:v=0:a=1"
        run(["ffmpeg", "-hide_banner", "-y", *inputs, "-filter_complex", filt, "-ar", "24000", str(joined)])

    stats = analyze(joined)
    issues = []
    if stats["speech_s"] < MIN_SPEECH_SECONDS:
        issues.append(f"only {stats['speech_s']}s of speech; need at least {MIN_SPEECH_SECONDS}s "
                      f"(ideally {RECOMMENDED_SPEECH_SECONDS}s+) of continuous English speech")
    if stats["est_snr_db"] < 20:
        issues.append(f"noisy reference (est. SNR {stats['est_snr_db']} dB)")

    cfg = {
        "profile": "NPC_VOICE_V1",
        "owner": "NPC",
        "updated": date.today().isoformat(),
        "privacy": "Local only. Reference audio is git-ignored and never sent to external services.",
        "engine": {"name": "Chatterbox TTS", "package": "chatterbox-tts==0.1.7",
                   "weights": "ResembleAI/chatterbox", "device": "cpu"},
        "original_references": [str(p.relative_to(STUDIO)) for p in stored],
        "clean_reference": str(joined.relative_to(STUDIO)),
        "analysis": stats,
        "language": "en (target narration language)",
        "ready_for_cloning": not issues,
        "issues": issues,
        "synthesis": {
            "seed": 4207,
            "takes": 3,
            "min_speaker_similarity": 0.80,
            "sample_rate": 24000,
            "emotions": EMOTIONS,
        },
    }
    save_config(cfg)
    print(f"wrote {CONFIG_PATH}")
    print(stats)
    print("READY" if not issues else "NOT READY: " + "; ".join(issues))


if __name__ == "__main__":
    main(sys.argv[1:])
