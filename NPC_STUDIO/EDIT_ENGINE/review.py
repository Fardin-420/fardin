"""Film-strip review of a rendered MP4: consecutive frames + the audio onset under each frame.

    python review.py <video.mp4> <out.jpg> <t0:t1> [<t0:t1> ...] [--every 1] [--w 150]

Each row is one time window. Under every frame a bar shows that frame's onset
rise (how hard the audio hits during the frame) and its frame number, so visual
impacts can be checked against the audio frame by frame.
"""
from __future__ import annotations

import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from analyze_music import Curves  # noqa: E402

SR = 48000


def decode_audio(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def frames(path, t0, t1, w):
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate",
                            "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip().split(",")
    W, H = int(probe[0]), int(probe[1])
    num, den = map(int, probe[2].split("/"))
    fps = num / den
    h = int(w * H / W)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.4f}", "-i", path, "-t", f"{t1 - t0:.4f}",
                          "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    arr = np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)
    return arr, fps


def main(argv):
    video, out = argv[1], argv[2]
    every = int(argv[argv.index("--every") + 1]) if "--every" in argv else 1
    w = int(argv[argv.index("--w") + 1]) if "--w" in argv else 150
    wins = [tuple(map(float, a.split(":"))) for a in argv[3:] if ":" in a and not a.startswith("--")]
    c = Curves(decode_audio(video))
    rows = []
    for t0, t1 in wins:
        arr, fps = frames(video, t0, t1, w)
        f0 = int(round(t0 * fps))
        tiles = []
        for k in range(0, len(arr), every):
            f = f0 + k
            a, b = int(f / fps * 1000), int((f + 1) / fps * 1000)
            rise = float(c.R[a:b].max()) if b <= c.n else 0.0
            tile = Image.new("RGB", (w, arr.shape[1] + 26), (10, 10, 10))
            tile.paste(Image.fromarray(arr[k]), (0, 0))
            d = ImageDraw.Draw(tile)
            bw = int(min(1.0, rise / 50) * (w - 4))
            col = (255, 60, 60) if rise > 35 else (255, 190, 60) if rise > 20 else (90, 160, 255)
            d.rectangle([2, arr.shape[1] + 3, 2 + bw, arr.shape[1] + 9], fill=col)
            d.text((3, arr.shape[1] + 11), f"f{f} {rise:.0f}dB", fill=(220, 220, 220))
            tiles.append(tile)
        row = Image.new("RGB", (len(tiles) * w, tiles[0].height), (0, 0, 0))
        for i, t in enumerate(tiles):
            row.paste(t, (i * w, 0))
        rows.append(row)
    W = max(r.width for r in rows)
    sheet = Image.new("RGB", (W, sum(r.height + 4 for r in rows)), (30, 30, 30))
    y = 0
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height + 4
    sheet.save(out, quality=86)


if __name__ == "__main__":
    main(sys.argv)
