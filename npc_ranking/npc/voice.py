"""Narration: Kokoro TTS per segment line, silence trim, and word timing estimated from energy dips."""
import json
import os
import re

import numpy as np
import soundfile as sf

SR = 48000


def _syllables(w):
    w = re.sub(r"[^a-z]", "", w.lower())
    n = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and n > 1 and not w.endswith("le"):
        n -= 1
    return max(1, n)


def _resample(x, sr_in, sr_out=SR):
    n = int(len(x) * sr_out / sr_in)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x)


def _trim(s, sr):
    env = np.convolve(np.abs(s), np.ones(240) / 240, "same")
    idx = np.where(env > 0.01)[0]
    return s[max(0, idx[0] - int(0.01 * sr)):min(len(s), idx[-1] + int(0.05 * sr))]


def word_times(s, text, sr=SR):
    """Split the voiced span by syllable weight, snap each boundary to the quietest 10 ms frame nearby."""
    hop = int(0.01 * sr)
    e = np.array([np.sqrt(np.mean(s[i:i + hop] ** 2)) for i in range(0, len(s) - hop, hop)])
    e = np.convolve(e, np.ones(3) / 3, "same")
    voiced = np.where(e > 0.02 * e.max())[0]
    a, b = voiced[0], voiced[-1]
    words = text.split()
    wts = np.array([_syllables(w) + (0.7 if re.search(r"[,.:!?]$", w) else 0) for w in words], float)
    bounds = a + (b - a) * np.concatenate([[0], np.cumsum(wts) / wts.sum()])
    for k in range(1, len(bounds) - 1):
        c = int(bounds[k]); lo, hi = max(a, c - 9), min(b, c + 9)
        bounds[k] = lo + int(np.argmin(e[lo:hi + 1]))
    bounds = np.maximum.accumulate(bounds)
    return [(w, round(bounds[k] * 0.01, 3), round(bounds[k + 1] * 0.01, 3)) for k, w in enumerate(words)]


def generate(cfg, segments, outdir):
    """segments: [{'id', 'vo', 'start', 'dur'}]. Writes vo_<id>.wav + voice.json; returns the timing list."""
    from kokoro_onnx import Kokoro
    v = cfg["voice"]
    k = Kokoro(v["model"], v["voices"])
    os.makedirs(outdir, exist_ok=True)
    out = []
    for seg in segments:
        if not seg.get("vo"):
            continue
        s, sr = k.create(seg["vo"], voice=v["voice_id"], speed=v["speed"], lang="en-us")
        s = _resample(_trim(np.asarray(s, np.float64), sr), sr)
        path = os.path.join(outdir, f"vo_{seg['id']}.wav")
        sf.write(path, s, SR)
        start = seg["start"] + (v["lead_in"] if seg.get("rank") else 0.08)
        dur = len(s) / SR
        words = [(w, round(start + a, 3), round(start + b, 3)) for w, a, b in word_times(s, seg["vo"])]
        fits = start + dur <= seg["start"] + seg["dur"] - 0.05
        out.append({"id": seg["id"], "file": path, "start": round(start, 3), "dur": round(dur, 3),
                    "fits": fits, "words": words})
    json.dump(out, open(os.path.join(outdir, "voice.json"), "w"), indent=1)
    return out
