#!/usr/bin/env python3
# Tempo the narration lines, place them on the 20 s timeline, and estimate word times from energy dips.
import json, re, subprocess
import numpy as np, soundfile as sf

TEMPO = 1.0
STARTS = [0.12, 3.15, 7.05, 11.6]
SPOKEN = [
 "What if the Sun vanished... right now?",
 "For about eight minutes, Earth wouldn't even know.",
 "Then suddenly... darkness. And the Sun's gravity is gone.",
 "Could humanity survive?",
]

def syllables(w):
    w = re.sub(r"[^a-z]", "", w.lower())
    if w == "nasa": return 2
    if w == "dart": return 1
    n = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and n > 1 and not w.endswith("le"): n -= 1
    return max(1, n)

def tempo(i):
    out = f"T{i}.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", f"L{i}.wav", "-af", f"atempo={TEMPO}",
                    "-ar", "48000", "-ac", "1", out], check=True)
    return out

def align(path, text):
    s, sr = sf.read(path)
    hop = int(0.01 * sr)
    e = np.array([np.sqrt(np.mean(s[i:i + hop] ** 2)) for i in range(0, len(s) - hop, hop)])
    e = np.convolve(e, np.ones(3) / 3, "same")
    voiced = np.where(e > 0.02 * e.max())[0]
    a, b = voiced[0], voiced[-1]
    words = text.split()
    wts = np.array([syllables(w) + (0.6 if re.search(r"[,.]$", w) else 0) for w in words], float)
    bounds = a + (b - a) * np.concatenate([[0], np.cumsum(wts) / wts.sum()])
    # snap interior boundaries to the quietest 10 ms frame within +-90 ms
    for k in range(1, len(bounds) - 1):
        c = int(bounds[k]); lo, hi = max(a, c - 9), min(b, c + 9)
        bounds[k] = lo + int(np.argmin(e[lo:hi + 1]))
    bounds = np.maximum.accumulate(bounds)
    return [(w, bounds[k] * 0.01, bounds[k + 1] * 0.01) for k, w in enumerate(words)], len(s) / sr

out = []
for i, text in enumerate(SPOKEN):
    words, dur = align(tempo(i), text); t = STARTS[i]
    out.append({"line": i, "file": f"T{i}.wav", "start": t, "dur": round(dur, 3),
                "words": [(w, round(t + ws, 3), round(t + we, 3)) for w, ws, we in words]})
json.dump(out, open("timing.json", "w"), indent=1)
for l in out:
    print(f"L{l['line']} @{l['start']:.2f} dur {l['dur']:.2f}: " + "  ".join(f"{w}@{s:.2f}" for w, s, _ in l["words"]))
