"""Re-render selected scene ranges and swap them into an existing master, frame-exact (no full re-render)."""
import math, subprocess, sys
from multiprocessing import Pool
import numpy as np
import doc_bh as D

src, dst = sys.argv[1], sys.argv[2]
ranges = [(D.T_FALL_DIAG, D.S5), (D.S5, D.S6), (D.S7, D.S8), (D.S8, D.S9)]
frames = sorted({fi for a, b in ranges for fi in range(math.floor(a * D.FPS), math.ceil(b * D.FPS))})
print("re-rendering", len(frames), "frames", flush=True)
with Pool(4) as pool:
    new = dict(zip(frames, pool.map(D.frame, frames, chunksize=4)))
fsz = D.W * D.H * 3
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{D.W}x{D.H}", "-r", "30",
                        "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", dst], stdin=subprocess.PIPE)
i = 0
while True:
    buf = dec.stdout.read(fsz)
    if len(buf) < fsz: break
    enc.stdin.write(new.get(i, buf)); i += 1
enc.stdin.close(); enc.wait(); dec.wait()
print("frames written", i, "replaced", len(new))
