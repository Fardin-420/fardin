import subprocess, sys
from multiprocessing import Pool
import prod as g
SRC, DST = sys.argv[1], sys.argv[2]
R = [(float(a), float(b)) for a, b in (x.split(":") for x in sys.argv[3:])]
redo = [i for i in range(g.NF) if any(a <= i / g.FPS < b for a, b in R)]
g.warm()
with Pool(4) as p: new = dict(zip(redo, p.map(g.frame, redo, chunksize=2)))
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", SRC, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{g.W}x{g.H}", "-r", str(g.FPS), "-i", "-",
                       "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", DST], stdin=subprocess.PIPE)
n = 0
while True:
    b = dec.stdout.read(g.W * g.H * 3)
    if len(b) < g.W * g.H * 3: break
    enc.stdin.write(new.get(n, b)); n += 1
enc.stdin.close(); enc.wait(); print("re-rendered", len(new), "of", n)
