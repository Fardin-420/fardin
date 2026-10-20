"""Render a project's timeline.

    python render.py <project> --stills 92,358,1425 [--scale 0.5]     # PNG stills + contact sheet
    python render.py <project> --preview                              # 540x960 60 fps preview MP4
    python render.py <project> --final                                # 1080x1920 60 fps master MP4

Frames are rendered by a pool of forked workers (each frame is a pure function
of its time) and streamed in order into ffmpeg (libx264, yuv420p, BT.709
broadcast range). Audio is muxed afterwards by mix_audio.py.
"""
from __future__ import annotations

import importlib.util
import json
import multiprocessing as mp
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from engine import Ctx  # noqa: E402

_TL = None


def load_timeline(project: Path, scale: float):
    ev = json.loads((project / "source/music_events.json").read_text())
    ctx = Ctx(project, ev, scale)
    spec = importlib.util.spec_from_file_location("edit", project / "source/edit.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.build(ctx)


def _work(i: int) -> bytes:
    return _TL.frame(i).tobytes()


def encode_cmd(out: Path, W: int, H: int, fps: int, final: bool) -> list[str]:
    q = ["-crf", "14", "-preset", "slow"] if final else ["-crf", "20", "-preset", "veryfast"]
    return ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
            "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
            "-c:v", "libx264", *q, "-profile:v", "high", "-level:v", "5.1", "-g", str(fps), "-bf", "2",
            "-x264-params", "aq-mode=3:aq-strength=0.9:deblock=-1,-1", "-tune", "film",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
            "-movflags", "+faststart", str(out)]


def render_video(project: Path, scale: float, out: Path, final: bool, frames: range | None = None, workers: int = 4):
    global _TL
    _TL = load_timeline(project, scale)
    ctx = _TL.ctx
    n = _TL.ctx.ev["frames"]
    idx = list(frames or range(n))
    p = subprocess.Popen(encode_cmd(out, ctx.W, ctx.H, ctx.fps, final), stdin=subprocess.PIPE)
    t0 = time.time()
    with mp.get_context("fork").Pool(workers) as pool:
        for k, buf in enumerate(pool.imap(_work, idx, chunksize=2)):
            p.stdin.write(buf)
            if k % 120 == 0:
                el = time.time() - t0
                print(f"  frame {idx[k]:5d}/{n}  {el:7.1f}s  ({(k + 1) / max(el, 1e-6):.2f} fps)", flush=True)
    p.stdin.close()
    p.wait()
    print(f"rendered {len(idx)} frames in {time.time() - t0:.1f}s -> {out}")


def mux(video: Path, audio: Path, out: Path):
    """Video stream copied untouched; master mix encoded once to AAC-LC 320k 48 kHz."""
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-ac", "2",
                    "-metadata", "title=NPC x CYBERWOLF - TWO SHADOWS. ONE ARMY.", "-movflags", "+faststart", str(out)], check=True)
    print(f"muxed -> {out}")


def stills(project: Path, scale: float, frames: list[int], out_dir: Path, label: str = ""):
    tl = load_timeline(project, scale)
    out_dir.mkdir(parents=True, exist_ok=True)
    ims = []
    t0 = time.time()
    for f in frames:
        a = tl.frame(f)
        im = Image.fromarray(a)
        im.save(out_dir / f"f{f:05d}.png")
        ims.append((f, im))
    print(f"{len(frames)} stills in {time.time() - t0:.1f}s ({(time.time() - t0) / len(frames):.2f}s/frame)")
    cols = min(6, len(ims))
    rows = (len(ims) + cols - 1) // cols
    tw = 270
    th = int(tw * 16 / 9)
    sheet = Image.new("RGB", (cols * tw, rows * (th + 22)), (12, 12, 12))
    from PIL import ImageDraw
    d = ImageDraw.Draw(sheet)
    for k, (f, im) in enumerate(ims):
        x, y = (k % cols) * tw, (k // cols) * (th + 22)
        sheet.paste(im.resize((tw, th), Image.LANCZOS), (x, y))
        d.text((x + 6, y + th + 4), f"f{f} {f / 60:.3f}s", fill=(200, 200, 200))
    sheet.save(out_dir / f"sheet{label}.jpg", quality=88)


if __name__ == "__main__":
    proj = Path(sys.argv[1]).resolve()
    scale = float(sys.argv[sys.argv.index("--scale") + 1]) if "--scale" in sys.argv else 0.5
    if "--stills" in sys.argv:
        fr = [int(x) for x in sys.argv[sys.argv.index("--stills") + 1].split(",")]
        label = sys.argv[sys.argv.index("--label") + 1] if "--label" in sys.argv else ""
        stills(proj, scale, fr, proj / "previews/stills", label)
    elif "--final" in sys.argv:
        render_video(proj, 1.0, proj / "final/.video_only.mp4", True, workers=int(os.environ.get("NPC_WORKERS", 4)))
        mux(proj / "final/.video_only.mp4", proj / "audio/mix.wav", proj / "final/NPC_X_CYBERWOLF_ONE_ARMY_FINAL.mp4")
    else:
        rng = None
        if "--range" in sys.argv:
            a, b = map(int, sys.argv[sys.argv.index("--range") + 1].split(":"))
            rng = range(a, b)
        render_video(proj, scale, proj / "previews/.video_only_preview.mp4", False, rng)
        if rng is None:
            mux(proj / "previews/.video_only_preview.mp4", proj / "audio/mix.wav", proj / "previews/NPC_X_CYBERWOLF_ONE_ARMY_PREVIEW.mp4")
