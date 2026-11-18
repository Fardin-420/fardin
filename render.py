#!/usr/bin/env python3
"""Time Ghost renderer — one command from script to finished episode.

  python render.py episodes/L001                 # build + full render + srt + QC
  python render.py episodes/L001 --stills        # one preview still per scene (build/stills/)
  python render.py episodes/L001 --test 30       # first 30 s only (output/..._test.mp4)
  python render.py episodes/L001 --captions      # burn subtitles into the full render
  python render.py episodes/L001 --shorts        # 3 vertical Shorts from shorts.json
  python render.py episodes/L001 --thumbs        # thumbnails from thumbs.json
  python render.py episodes/L001 --all           # everything
"""
import argparse
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from engine import build as B  # noqa: E402
from engine import renderer as R  # noqa: E402
from engine import qc  # noqa: E402


def stale(ep):
    tl = os.path.join(ep, "build", "timeline.json")
    if not os.path.exists(tl):
        return True
    src = [os.path.join(ep, "script.json"), os.path.join(ep, "narration.mp3"), os.path.join(ep, "music.mp3")]
    src += [os.path.join(ROOT, "engine", f) for f in ("build.py", "audio.py")]
    t = os.path.getmtime(tl)
    return any(os.path.exists(s) and os.path.getmtime(s) > t for s in src)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    ap.add_argument("--stills", action="store_true")
    ap.add_argument("--test", type=float, default=0)
    ap.add_argument("--captions", action="store_true")
    ap.add_argument("--shorts", action="store_true")
    ap.add_argument("--thumbs", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--no-video", action="store_true")
    ap.add_argument("--procs", type=int, default=None)
    ap.add_argument("--rebuild", action="store_true")
    a = ap.parse_args()
    ep = a.episode.rstrip("/")
    num = os.path.basename(ep)
    out_dir = os.path.join(ROOT, "output")
    os.makedirs(out_dir, exist_ok=True)
    bdir = os.path.join(ep, "build")
    if a.rebuild or stale(ep):
        print("[build] narration, timing, audio mix…", flush=True)
        t0 = time.time()
        B.build(ep)
        print(f"[build] done in {time.time() - t0:.0f}s", flush=True)
    tl_path = os.path.join(bdir, "timeline.json")
    tl = json.load(open(tl_path))
    print(f"[timeline] {len(tl['scenes'])} scenes, {tl['duration']:.1f}s ({tl['duration'] / 60:.2f} min)")
    words = B.punctuate(tl)
    srt = os.path.join(out_dir, f"timeghost_{num}.srt")
    B.write_srt(words, srt)
    mix = os.path.join(bdir, "mix.wav")

    if a.stills:
        sd = os.path.join(bdir, "stills")
        os.makedirs(sd, exist_ok=True)
        for s in tl["scenes"]:
            for frac in (0.25, 0.7):
                T = s["start"] + s["dur"] * frac
                R.still(tl, T, os.path.join(sd, f"{s['id']}_{int(frac * 100)}.png"), 960, 540)
        print(f"[stills] written to {sd}")
    if a.test:
        out = os.path.join(out_dir, f"timeghost_{num}_test.mp4")
        R.render_video(tl_path, out, mix, t1=a.test, procs=a.procs, chunk_s=5)
        print("[test]", out)
        qc.report(out, expect_dur=min(a.test, tl["duration"]), check_len=False)
    full = os.path.join(out_dir, f"timeghost_{num}.mp4")
    if (a.all or not (a.stills or a.test or a.shorts or a.thumbs)) and not a.no_video:
        print("[render] full episode…", flush=True)
        t0 = time.time()
        R.render_video(tl_path, full, mix, procs=a.procs, captions=a.captions)
        print(f"[render] {full} in {time.time() - t0:.0f}s")
        qc.report(full, expect_dur=tl["duration"])
    if a.shorts or a.all:
        from engine import shorts
        shorts.make_all(ep, tl_path, out_dir, num, procs=a.procs)
    if a.thumbs or a.all:
        from engine import thumbs
        thumbs.make_all(ep, out_dir, num)


if __name__ == "__main__":
    main()
