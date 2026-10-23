#!/usr/bin/env python3
# Tempo the narration lines, place them on the 20 s timeline, and estimate word times from energy dips.
import json, re, subprocess
import numpy as np, soundfile as sf

TEMPO = 1.0
GAPS = [0.6, 0.3, 0.4, 0.6, 0.3, 0.4, 0.7, 0.5, 0.4, 0.4]  # designed pauses (title hit, scene turns)
SPOKEN = [
 "Fall into a black hole... and to everyone watching, you'd never quite make it in.",
 "This is a simulation, built from Einstein's equations. That ring is superheated gas, swirling around it.",
 "Its gravity bends light so much, you can see the far side of the disk, warped up and over the top.",
 "In twenty nineteen, telescopes captured the first real image of one: a glowing ring, fifty five million light years away.",
 "Now, let's fall in. First problem: tidal forces. Gravity pulls your feet harder than your head.",
 "Near a small black hole, that would stretch you apart, long before the edge. Scientists call it spaghettification.",
 "But near a supermassive one, like the giant at the center of our galaxy, you'd cross in one piece.",
 "Now it gets strange. To a friend far away, your clock ticks slower... and slower. Your light fades redder and dimmer, until you seem to freeze at the edge.",
 "But for you, time feels normal. You'd cross the event horizon without feeling a thing.",
 "Because it isn't a surface. It's the point of no return, where escaping would mean moving faster than light.",
 "Past it, every path leads inward. And at the center? No one knows. It's where our physics breaks down.",
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

out, t = [], 0.0
for i, text in enumerate(SPOKEN):
    words, dur = align(tempo(i), text)
    out.append({"line": i, "file": f"T{i}.wav", "start": round(t, 3), "dur": round(dur, 3),
                "words": [(w, round(t + ws, 3), round(t + we, 3)) for w, ws, we in words]})
    t += dur + (GAPS[i] if i < len(GAPS) else 0)
json.dump(out, open("timing.json", "w"), indent=1)
for l in out:
    print(f"L{l['line']} @{l['start']:.2f} dur {l['dur']:.2f}: " + "  ".join(f"{w}@{s:.2f}" for w, s, _ in l["words"]))
print("narration ends", round(out[-1]["start"] + out[-1]["dur"], 2))
