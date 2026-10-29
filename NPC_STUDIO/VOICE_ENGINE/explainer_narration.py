"""Narration for flat 2D explainer projects (Kokoro TTS, any language Kokoro speaks).

    python VOICE_ENGINE/explainer_narration.py PROJECTS/PERSIAN_TWO_DIALECTS_EN

Each script line is spoken from its `say` text (falls back to `text`), trimmed,
resampled to 48 kHz and measured. Captions need word times, which Kokoro does
not give, so they are aligned from the audio itself: the pauses inside a line
are found by energy, matched to the punctuation breaks of the on-screen text,
and the words of each phrase are spread over its voiced span by length.

Writes audio/narration/narration.wav and narration_manifest.json (line and word
times). build_explainer_timeline.py turns that into the timeline.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

MODEL_DIR = Path(__file__).resolve().parent / "models" / "kokoro"
OUT_SR = 48000
HOP = 0.01  # analysis hop for the energy envelope, seconds


def trim(wav: np.ndarray, sr: int, db: float = -42, pad: float = 0.04) -> np.ndarray:
    win = int(sr * 0.01)
    frames = len(wav) // win
    rms = np.sqrt(np.mean(wav[: frames * win].reshape(frames, win) ** 2, axis=1) + 1e-12)
    loud = np.where(20 * np.log10(rms / (rms.max() + 1e-12)) > db)[0]
    if not len(loud):
        return wav
    a = max(0, loud[0] * win - int(pad * sr))
    b = min(len(wav), (loud[-1] + 1) * win + int(pad * sr))
    return wav[a:b]


def internal_gaps(wav: np.ndarray, sr: int, min_gap: float = 0.09, db: float = -34) -> list[tuple[float, float]]:
    """Silent stretches inside a trimmed line, as (start, end) seconds."""
    win = int(sr * HOP)
    frames = len(wav) // win
    rms = np.sqrt(np.mean(wav[: frames * win].reshape(frames, win) ** 2, axis=1) + 1e-12)
    quiet = 20 * np.log10(rms / (rms.max() + 1e-12)) < db
    gaps, i = [], 0
    while i < frames:
        if quiet[i]:
            j = i
            while j < frames and quiet[j]:
                j += 1
            if i > 0 and j < frames and (j - i) * HOP >= min_gap:
                gaps.append((i * HOP, j * HOP))
            i = j
        else:
            i += 1
    return gaps


def phrases(words: list[str]) -> list[list[int]]:
    """Word indices grouped at punctuation breaks."""
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(i)
        if w[-1] in ",.?!:;" or w.endswith("..."):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def align_words(words: list[str], dur: float, gaps: list[tuple[float, float]]) -> list[tuple[float, float]]:
    groups = phrases(words)
    # Where each punctuation break should fall if speech were uniform by text length;
    # snap it to the nearest unused pause (the spoken text may pause more often).
    weight = [sum(len(words[i]) + 2 for i in g) for g in groups]
    expect = np.cumsum(weight)[:-1] / sum(weight) * dur
    bounds, used = [], set()
    for e in expect:
        cands = [(abs((a + b) / 2 - e), k) for k, (a, b) in enumerate(gaps) if k not in used and (a + b) / 2 > (bounds[-1][1] if bounds else 0)]
        best = min(cands, default=None)
        if best and best[0] < 0.22 * dur:
            used.add(best[1])
            bounds.append(gaps[best[1]])
        else:
            bounds.append((e, e))
    edges = [(0.0, None)] + [(b, a) for a, b in bounds]
    spans = [(edges[k][0], bounds[k][0] if k < len(bounds) else dur) for k in range(len(groups))]
    times = [None] * len(words)
    for (a, b), g in zip(spans, groups):
        w = np.array([len(words[i].strip(",.?!:;")) + 2 for i in g], float)
        e = a + (b - a) * np.concatenate([[0], np.cumsum(w) / w.sum()])
        for n, i in enumerate(g):
            times[i] = (round(float(e[n]), 3), round(float(e[n + 1]), 3))
    return times


def main(project: Path) -> None:
    from kokoro_onnx import Kokoro

    script = json.loads((project / "source" / "script.json").read_text())
    vcfg = script["voice"]
    k = Kokoro(str(MODEL_DIR / "kokoro-v1.0.onnx"), str(MODEL_DIR / "voices-v1.0.bin"))
    style = sum(k.get_voice_style(v) * w for v, w in vcfg["blend"].items())
    out_dir = project / "audio" / "narration"
    out_dir.mkdir(parents=True, exist_ok=True)

    t = script["lead_in"]
    pieces, lines = [np.zeros(int(t * OUT_SR), np.float32)], []
    for line in script["lines"]:
        wav, sr = k.create(line.get("say", line["text"]), voice=style, speed=vcfg.get("speed", 1.0), lang=vcfg.get("lang", "en-us"))
        wav = resample_poly(trim(wav, sr), OUT_SR, sr).astype(np.float32)
        dur = len(wav) / OUT_SR
        words = line["text"].split()
        wt = align_words(words, dur, internal_gaps(wav, OUT_SR))
        lines.append({"id": line["id"], "start": round(t, 3), "end": round(t + dur, 3),
                      "words": [{"w": w, "start": round(t + a, 3), "end": round(t + b, 3)} for w, (a, b) in zip(words, wt)]})
        print(f"{line['id']} {dur:5.2f}s  {line['text']}")
        pieces += [wav, np.zeros(int(line["pause_after"] * OUT_SR), np.float32)]
        t += dur + line["pause_after"]

    full = np.concatenate(pieces)
    full *= 0.89 / max(np.abs(full).max(), 1e-9)
    sf.write(out_dir / "narration.wav", full, OUT_SR)
    manifest = {"source": "KOKORO:" + "+".join(f"{v}@{w}" for v, w in vcfg["blend"].items()),
                "sample_rate": OUT_SR, "duration": round(len(full) / OUT_SR, 3), "lines": lines}
    (out_dir / "narration_manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"narration {manifest['duration']:.2f}s -> {out_dir / 'narration.wav'}")


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
