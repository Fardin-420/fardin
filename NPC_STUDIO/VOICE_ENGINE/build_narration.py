"""Generate a project's narration and measure real line timings.

    .venv/bin/python build_narration.py ../PROJECTS/NPC_NO_EDITOR_JUST_CODE           # NPC_VOICE_V1
    .venv/bin/python build_narration.py ../PROJECTS/NPC_NO_EDITOR_JUST_CODE --guest   # NPC_GUEST_VOICE

Writes audio/narration/narration.wav (48 kHz) and
audio/narration/narration_manifest.json, which build_timeline.py uses instead
of the estimated durations in script.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

from npc_voice import Voice, apply_pronunciation, env_device, trim

OUT_SR = 48000


def main(project: Path, guest: bool = False) -> None:
    script = json.loads((project / "source" / "script.json").read_text())
    out_dir = project / "audio" / "narration"
    out_dir.mkdir(parents=True, exist_ok=True)
    if guest:
        from guest_voice import GuestVoice
        v, floor, source = GuestVoice(), None, "NPC_GUEST_VOICE"
    else:
        v = Voice(env_device())
        floor, source = v.cfg["synthesis"]["min_speaker_similarity"], "NPC_VOICE_V1"

    t = script["lead_in"]
    pieces, lines = [np.zeros(int(t * OUT_SR), np.float32)], []
    for line in script["lines"]:
        text = apply_pronunciation(line["text"], script.get("pronunciation", {}))
        wav, sim = v.say(text, line["emotion"])
        wav = trim(wav, v.sr)
        wav = librosa.resample(wav, orig_sr=v.sr, target_sr=OUT_SR)
        wav *= 10 ** (line.get("gain_db", 0) / 20)
        sf.write(out_dir / f"{line['id']}.wav", wav, OUT_SR)
        dur = len(wav) / OUT_SR
        # The guest voice is a single fixed style, so there is no reference to score against.
        ok = sim is None or sim >= floor
        lines.append({"id": line["id"], "start": round(t, 3), "end": round(t + dur, 3),
                      "speaker_similarity": None if sim is None else round(sim, 3), "ok": ok})
        print(f"{line['id']} {dur:5.2f}s {'' if sim is None else f'sim={sim:.3f} '}{text}")
        pieces += [wav.astype(np.float32), np.zeros(int(line["pause_after"] * OUT_SR), np.float32)]
        t += dur + line["pause_after"]

    full = np.concatenate(pieces)
    peak = np.abs(full).max()
    if peak > 0:
        full *= 0.89 / peak  # -1 dBFS peak; final loudness is set in the mix
    sf.write(out_dir / "narration.wav", full, OUT_SR)
    manifest = {"source": source, "sample_rate": OUT_SR,
                "duration": round(len(full) / OUT_SR, 3), "lines": lines,
                "all_lines_same_speaker": all(l["ok"] for l in lines)}
    (out_dir / "narration_manifest.json").write_text(json.dumps(manifest, indent=2))
    if not manifest["all_lines_same_speaker"]:
        bad = [l["id"] for l in lines if not l["ok"]]
        raise SystemExit(f"Speaker drift on {bad}: regenerate with more takes or a longer reference.")


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve(), guest="--guest" in sys.argv)
