#!/usr/bin/env python3
# Tempo the narration lines, place them on the 20 s timeline, and estimate word times from energy dips.
import json, re, subprocess
import numpy as np, soundfile as sf

TEMPO = 1.0
from lines import flat, parse, CHAPTERS

def syllables(w):
    w = re.sub(r"[^a-z]", "", w.lower())
    if w == "nasa": return 2
    if w == "dart": return 1
    n = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and n > 1 and not w.endswith("le"): n -= 1
    return max(1, n)

def tempo(i):
    out = f"vo/T{i:03d}.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", f"vo/L{i:03d}.wav", "-af", f"atempo={TEMPO}",
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

FL = flat()
out, t = [], 0.3
chap_start = {}
for i, (ci, pi, text) in enumerate(FL):
    if pi == 0: chap_start[ci] = t
    spoken, disp = parse(text)
    words, dur = align(tempo(i), spoken)
    out.append({"line": i, "chapter": ci, "para": pi, "text": text, "file": f"vo/T{i:03d}.wav", "start": round(t, 3), "dur": round(dur, 3),
                "words": [(w, round(t + words[a][1], 3), round(t + words[b][2], 3)) for w, a, b in disp]})
    last = i + 1 == len(FL) or FL[i + 1][0] != ci
    n = len(spoken.split())
    if i == 0: gap = 1.6                                   # the hook: impact, then silence
    elif last: gap = 3.0                                   # chapter break (title card)
    elif n <= 3: gap = 0.6
    elif text.endswith("?"): gap = 0.65
    else: gap = 0.42
    t += dur + gap
json.dump({"lines": out, "chapters": [{"title": c[0], "start": round(chap_start[i], 3)} for i, c in enumerate(CHAPTERS)]}, open("timing.json", "w"), indent=0)
print("narration ends", round(out[-1]["start"] + out[-1]["dur"], 2))
for c, (title, _) in enumerate(CHAPTERS): print(c, round(chap_start[c], 1), title)
