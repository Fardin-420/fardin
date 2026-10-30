import subprocess, sys
from multiprocessing import Pool
import gj3 as g
a = float(sys.argv[1]); out = sys.argv[2]
f0, f1 = int(a * g.FPS), g.NF
p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{g.W}x{g.H}", "-r", str(g.FPS), "-i", "-",
                      "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
with Pool(4) as pool:
    for i, b in enumerate(pool.imap(g.frame, range(f0, f1), chunksize=3)):
        p.stdin.write(b)
        if i % 300 == 0: print("frame", f0 + i, "/", f1, flush=True)
p.stdin.close(); p.wait()
