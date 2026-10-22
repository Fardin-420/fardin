"""Per-frame visual activity of the source: mean abs difference to the previous frame
(downscaled, grayscale) plus hard-cut detection. Output contains no image content.

    python activity_scan.py SOURCE.mp4 OUT.json
"""
import json
import subprocess
import sys

import numpy as np

src, out = sys.argv[1], sys.argv[2]
W, H = 98, 214
p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-vf", f"scale={W}:{H},format=gray", "-f", "rawvideo", "-"],
                     stdout=subprocess.PIPE)
prev, diffs = None, []
while True:
    b = p.stdout.read(W * H)
    if len(b) < W * H:
        break
    g = np.frombuffer(b, np.uint8).astype(np.float32)[8:]  # skip nothing meaningful; keep shape simple
    diffs.append(0.0 if prev is None else float(np.abs(g - prev).mean()))
    prev = g
d = np.array(diffs)
cuts = [i for i in range(1, len(d)) if d[i] > 18 and d[i] > 4 * np.median(d[max(0, i - 15):i + 15])]
json.dump({"fps": 30, "frames": len(d), "diff": [round(x, 2) for x in d], "cuts": cuts}, open(out, "w"))
print("frames", len(d), "cuts", cuts)
