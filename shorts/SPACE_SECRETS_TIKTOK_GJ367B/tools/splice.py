import subprocess, sys
from multiprocessing import Pool
import gj
W, H, FPS, NF = gj.W, gj.H, gj.FPS, gj.NF
SRC, DST = sys.argv[1], sys.argv[2]
R = [(0.0, 3.0), (gj.DUR - 0.6, gj.DUR + 1)]
redo = [i for i in range(NF) if any(a <= i / FPS < b for a, b in R)]
with Pool(4) as p: new = dict(zip(redo, p.map(gj.frame, redo, chunksize=4)))
print("re-rendered", len(new), flush=True)
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", SRC, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", DST], stdin=subprocess.PIPE)
n = 0
while True:
    b = dec.stdout.read(W * H * 3)
    if len(b) < W * H * 3: break
    enc.stdin.write(new.get(n, b)); n += 1
enc.stdin.close(); enc.wait(); print("frames", n, "of", NF)
