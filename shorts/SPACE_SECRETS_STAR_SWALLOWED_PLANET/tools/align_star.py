#!/usr/bin/env python3
# Tempo the narration lines, place them on the 20 s timeline, and estimate word times from energy dips.
import json, re, subprocess
import numpy as np, soundfile as sf

TEMPO = 1.0
from lines import LINES, parse

def syllables(w):
    w = re.sub(r"[^a-z]", "", w.lower())
    if w == "nasa": return 2
    if w == "dart": return 1
    n = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and n > 1 and not w.endswith("le"): n -= 1
    return max(1, n)

def tempo(i):
    out = f"vo/T{i:02d}.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", f"vo/L{i:02d}.wav", "-af", f"atempo={TEMPO}",
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

out, t = [], 0.0
for i, (text, gap, sp) in enumerate(LINES):
    spoken, disp = parse(text)
    words, dur = align(tempo(i), spoken)
    out.append({"line": i, "file": f"vo/T{i:02d}.wav", "start": round(t, 3), "dur": round(dur, 3),
                "words": [(w, round(t + words[a][1], 3), round(t + words[b][2], 3)) for w, a, b in disp]})
    t += dur + gap
json.dump(out, open("timing.json", "w"), indent=0)
for l in out: print(f"L{l['line']} @{l['start']:.2f}: " + " ".join(f"{w}@{s:.2f}" for w, s, _ in l["words"]))
print("narration ends", round(out[-1]["start"] + out[-1]["dur"], 2))
