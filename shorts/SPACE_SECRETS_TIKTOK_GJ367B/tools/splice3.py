import subprocess, sys
from multiprocessing import Pool
import gj3 as g
SRC, DST, OFF = sys.argv[1], sys.argv[2], float(sys.argv[3])
R = [(36.1, 41.65), (69.14, 74.34)]
f0 = int(OFF * g.FPS)
redo = [i for i in range(f0, g.NF) if any(a <= i / g.FPS < b for a, b in R)]
with Pool(4) as p: new = dict(zip(redo, p.map(g.frame, redo, chunksize=4)))
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", SRC, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{g.W}x{g.H}", "-r", str(g.FPS), "-i", "-",
                       "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", DST], stdin=subprocess.PIPE)
n = f0
while True:
    b = dec.stdout.read(g.W * g.H * 3)
    if len(b) < g.W * g.H * 3: break
    enc.stdin.write(new.get(n, b)); n += 1
enc.stdin.close(); enc.wait(); print("re-rendered", len(new), "frames; total", n - f0)
