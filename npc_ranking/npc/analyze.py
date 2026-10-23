"""Video analysis: scene cuts, motion energy, cross-file sync offsets, timestamped contact sheets."""
import json
import subprocess
import sys

import numpy as np


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "format=duration:stream=codec_type,width,height,r_frame_rate",
                          "-of", "json", path], capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    v = next(s for s in d["streams"] if s["codec_type"] == "video")
    num, den = map(int, v["r_frame_rate"].split("/"))
    return {"duration": float(d["format"]["duration"]), "width": v["width"], "height": v["height"],
            "fps": num / den, "has_audio": any(s["codec_type"] == "audio" for s in d["streams"])}


def gray_frames(path, fps=10, size=(64, 36), start=0.0, dur=None):
    args = ["ffmpeg", "-v", "error", "-ss", str(start)] + (["-t", str(dur)] if dur else []) + [
        "-i", path, "-vf", f"fps={fps},scale={size[0]}:{size[1]},format=gray", "-f", "rawvideo", "-"]
    raw = subprocess.run(args, capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, size[1], size[0]).astype(np.float32)


def scene_cuts(path, fps=10, thresh=28.0):
    f = gray_frames(path, fps)
    diff = np.abs(np.diff(f, axis=0)).mean(axis=(1, 2))
    return [round((i + 1) / fps, 2) for i in np.where(diff > thresh)[0]], diff


def motion_energy(path, fps=10):
    f = gray_frames(path, fps)
    e = np.abs(np.diff(f, axis=0)).mean(axis=(1, 2))
    return np.concatenate([[0], e])


def sync_offset(ref, other, fps=10, search=5.0):
    """Seconds to add to a time in `other` to get the same picture in `ref`."""
    a, b = gray_frames(ref, fps), gray_frames(other, fps)
    a = (a - a.mean(axis=(1, 2), keepdims=True)) / (a.std(axis=(1, 2), keepdims=True) + 1e-6)
    b = (b - b.mean(axis=(1, 2), keepdims=True)) / (b.std(axis=(1, 2), keepdims=True) + 1e-6)
    best = (None, -1e9)
    for lag in range(-int(search * fps), int(search * fps) + 1):
        i0, j0 = max(0, lag), max(0, -lag)
        n = min(len(a) - i0, len(b) - j0)
        if n < fps * 5:
            continue
        score = float((a[i0:i0 + n] * b[j0:j0 + n]).mean())
        if score > best[1]:
            best = (lag / fps, score)
    return best


def contact_sheet(path, out, start, dur, fps=2, cols=6, width=200):
    rows = int(np.ceil(dur * fps / cols))
    vf = (f"fps={fps},scale={width}:-1,drawtext=fontfile=/usr/share/fonts/truetype/jetbrains-mono/"
          f"JetBrainsMono-Bold.ttf:text='%{{pts\\:hms}}':x=4:y=4:fontsize=14:fontcolor=yellow:box=1:"
          f"boxcolor=black,tile={cols}x{rows}")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(start), "-t", str(dur), "-i", path,
                    "-vf", vf, "-frames:v", "1", out], check=True)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        info = probe(p)
        cuts, _ = scene_cuts(p)
        print(p, info, "cuts:", cuts)
