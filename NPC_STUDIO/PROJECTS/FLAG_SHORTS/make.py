#!/usr/bin/env python3
"""Flag-battle Shorts generator.

    python make.py episodes.json                 render every episode → out/<slug>.mp4 + out/<slug>.txt
    python make.py episodes.json --only spain    only episodes whose slug contains "spain"
    python make.py episodes.json --seed 42       skip the seed search and render this seed
    python make.py episodes.json --seeds 500     search more seeds
    python make.py episodes.json --cover-only    only (re)make covers, reusing the seed from out/<slug>.report.json
"""
import argparse
import json
import multiprocessing as mp
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

import audio
import cover
import flags
import render
import sim

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
_CTX = {}


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:80]


def build_cfg(defaults, ep):
    cfg = dict(sim.DEFAULTS)
    cfg.update(defaults or {})
    cfg.update(ep)
    cfg["teams"] = [t.lower() for t in cfg["teams"]]
    if len(cfg["teams"]) < 2 or len(set(cfg["teams"])) != len(cfg["teams"]):
        raise SystemExit("an episode needs at least 2 distinct teams")
    cfg["names"] = cfg.get("names") or [flags.country_name(t) for t in cfg["teams"]]
    cfg.setdefault("hook", "PICK ONE. NO SWITCHING.")
    cfg.setdefault("title", " VS ".join(n.upper() for n in cfg["names"]))
    cfg["slug"] = cfg.get("slug") or slugify(cfg["title"])
    return cfg


# ------------------------------------------------------------------ seed search
def _score(seed):
    cfg = _CTX["cfg"]
    res = sim.simulate(cfg, seed)
    s, b = sim.drama(res, cfg)
    return seed, s, b, res.get("winner")


def search(cfg, workers):
    _CTX["cfg"] = cfg
    t0 = time.time()
    with mp.Pool(workers) as pool:
        rows = []
        for k, row in enumerate(pool.imap_unordered(_score, range(1, int(cfg["seeds"]) + 1), chunksize=4), 1):
            rows.append(row)
            if k % 20 == 0 or k == cfg["seeds"]:
                print(f"\r  seed search {k}/{int(cfg['seeds'])}", end="", flush=True)
    print(f"  ({time.time() - t0:.0f}s)")
    rows.sort(key=lambda r: (-r[1], r[0]))
    ok = sum(1 for r in rows if r[2].get("hard_ok"))
    wins = [sum(1 for r in rows if r[3] == k) for k in range(len(cfg["teams"]))]
    print(f"  {ok}/{len(rows)} seeds meet all drama rules · wins per team (fair physics): "
          + ", ".join(f"{n} {w}" for n, w in zip(cfg["names"], wins)))
    print("  top seeds:")
    for seed, s, b, w in rows[:5]:
        print(f"    seed {seed:>4}  score {s:6.1f}  {b['length_s']:5.2f}s  near-misses {b['near_misses']:>2}  duel {b['duel_s']:5.2f}s  "
              f"lead@80% {b['winner_lead_at_80pct']:+d}  winner {cfg['names'][w]} ({b['winner_balls_left']} left)")
    if not rows[0][2].get("hard_ok"):
        print("  WARNING: no seed met every drama rule; using the best available. Try --seeds 500.")
    return rows


# ------------------------------------------------------------------ rendering
def _segment(job):
    k, a, b, path, counter = job
    r = _CTX["renderer"]
    ff = subprocess.Popen(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{render.W}x{render.H}",
                           "-r", str(r.fps), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                           "-profile:v", "high", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-g", str(r.fps), path],
                          stdin=subprocess.PIPE)
    for f in range(a, b):
        ff.stdin.write(r.frame(f).tobytes())
        with counter.get_lock():
            counter.value += 1
    ff.stdin.close()
    if ff.wait() != 0:
        raise RuntimeError("ffmpeg failed")
    return path


def render_video(cfg, res, out_mp4, workers):
    tmp = OUT / f".{cfg['slug']}"
    tmp.mkdir(parents=True, exist_ok=True)
    _CTX["renderer"] = render.Renderer(cfg, res)          # built before fork → shared by all workers
    total = res["total_frames"]
    per = -(-total // workers)
    counter = mp.Value("i", 0)
    jobs = [(k, k * per, min(total, (k + 1) * per), str(tmp / f"seg{k}.mp4"), counter) for k in range(workers) if k * per < total]
    t0 = time.time()
    procs = []
    ctx = mp.get_context("fork")
    q = ctx.Queue()

    def run(job):
        try:
            q.put(("ok", _segment(job)))
        except Exception as e:        # noqa: BLE001
            q.put(("err", repr(e)))
    for j in jobs:
        p = ctx.Process(target=run, args=(j,))
        p.start()
        procs.append(p)
    done = 0
    while done < len(jobs):
        try:
            kind, val = q.get(timeout=1.0)
            if kind == "err":
                for p in procs:
                    p.terminate()
                raise SystemExit(f"render worker failed: {val}")
            done += 1
        except Exception as e:        # noqa: BLE001  (queue.Empty)
            if isinstance(e, SystemExit):
                raise
        c = counter.value
        el = time.time() - t0
        print(f"\r  render {c}/{total} frames  {100 * c / total:5.1f}%  {c / max(el, 1e-6):5.1f} fps  ETA {max(0, (total - c) / max(c / max(el, 1e-6), 1e-6)):4.0f}s ", end="", flush=True)
    for p in procs:
        p.join()
    print()
    wav = tmp / "audio.wav"
    info = audio.build(res, cfg, wav)
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{j[3]}'\n" for j in jobs))
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(wav),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-t", f"{total / cfg['fps']:.6f}", "-movflags", "+faststart", str(out_mp4)], check=True)
    for f in tmp.iterdir():
        f.unlink()
    tmp.rmdir()
    return info


# ------------------------------------------------------------------ verification
def verify(cfg, res, mp4):
    pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-show_streams", "-show_format", "-of", "json", str(mp4)],
                                   capture_output=True, text=True, check=True).stdout)
    v = next(s for s in pr["streams"] if s["codec_type"] == "video")
    a = next((s for s in pr["streams"] if s["codec_type"] == "audio"), None)
    dur = float(pr["format"]["duration"])
    lo, hi = cfg["target_seconds"]
    checks = {
        "1080x1920": (v["width"], v["height"]) == (1080, 1920),
        "60 fps": v["r_frame_rate"] == f"{cfg['fps']}/1",
        "h264 yuv420p": v["codec_name"] == "h264" and v["pix_fmt"] == "yuv420p",
        "frame count": int(v["nb_read_frames"]) == res["total_frames"],
        f"duration {lo}-{hi}s": lo <= dur <= hi,
        "aac audio stream": bool(a) and a["codec_name"] == "aac",
    }
    vol = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(mp4), "-map", "0:a", "-af", "volumedetect", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    m = re.search(r"max_volume: (-?[\d.]+) dB", vol)
    peak = float(m.group(1)) if m else 0.0
    checks["audio does not clip"] = peak <= -0.3
    line = (f"{v['codec_name']} {v['width']}x{v['height']} {v['r_frame_rate']} fps {v['pix_fmt']}, {v['nb_read_frames']} frames, {dur:.2f}s, "
            f"audio {a['codec_name'] if a else 'MISSING'} peak {peak:.1f} dB")
    print("  ffprobe:", line)
    bad = [k for k, ok in checks.items() if not ok]
    # check sheet: 0s, 1s, midpoint, last second (decoded back out of the MP4)
    times = [("0s", 0.0), ("1s", 1.0), ("midpoint", dur / 2), ("last second", dur - 0.5)]
    sheet = Image.new("RGB", (4 * 540 + 50, 960 + 70), (16, 16, 20))
    d = ImageDraw.Draw(sheet)
    for k, (lab, t) in enumerate(times):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp4), "-vf", f"select=eq(n\\,{int(round(t * cfg['fps']))})", "-vframes", "1",
                              "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
        im = Image.frombytes("RGB", (1080, 1920), raw)
        if im.resize((54, 96)).convert("L").getextrema()[1] < 40:
            bad.append(f"empty frame at {lab}")
        x = 10 + k * 550
        sheet.paste(im.resize((540, 960), Image.LANCZOS), (x, 60))
        d.text((x + 4, 12), f"{lab} ({t:.1f}s)", fill=(255, 255, 255), font=render.font(34))
        for y in (render.SAFE_TOP, render.SAFE_BOTTOM):          # platform-UI safe lines
            d.line([x, 60 + y // 2, x + 540, 60 + y // 2], fill=(255, 0, 255), width=1)
    sheet.save(OUT / f"{cfg['slug']}.check.png")
    if bad:
        raise SystemExit(f"VERIFY FAILED for {mp4.name}: {bad}")
    print("  verify: OK →", f"out/{cfg['slug']}.check.png")
    return dict(summary=line, checks=checks)


# ------------------------------------------------------------------ metadata
def write_meta(cfg):
    names = cfg["names"]
    em = " ".join(flags.emoji(t) for t in cfg["teams"])
    vs = " vs ".join(names)
    tags = ["#shorts", "#flags", "#simulation", "#satisfying", "#" + re.sub(r"[^a-z]", "", names[0].lower())]
    txt = (f"TITLE\n{cfg['title']}\n\n"
           f"DESCRIPTION\n{vs}: {cfg['balls_per_team']} balls each, one spinning ring, one way out. "
           f"Last flag inside wins. Real physics, nothing rigged. Who did you pick?\n\n"
           f"HASHTAGS\n{' '.join(tags)}\n\n"
           f"PINNED COMMENT\nPick one BEFORE it ends {em} no switching. Did your pick survive? "
           f"Drop 3 countries for the next battle 👇\n")
    (OUT / f"{cfg['slug']}.txt").write_text(txt, encoding="utf-8")


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episodes")
    ap.add_argument("--only", help="render only episodes whose slug contains this text")
    ap.add_argument("--seed", type=int, help="render this seed instead of searching")
    ap.add_argument("--seeds", type=int, help="number of seeds to search (default 200)")
    ap.add_argument("--cover-only", action="store_true", help="only make out/<slug>.cover.jpg + .thumb.jpg")
    ap.add_argument("--workers", type=int, default=max(1, min(8, (os.cpu_count() or 2))))
    args = ap.parse_args()
    data = json.loads(Path(args.episodes).read_text(encoding="utf-8"))
    eps = data["episodes"] if isinstance(data, dict) else data
    defaults = data.get("defaults", {}) if isinstance(data, dict) else {}
    flags.ensure_package()
    OUT.mkdir(exist_ok=True)
    made = []
    for ep in eps:
        cfg = build_cfg(defaults, ep)
        if args.seeds:
            cfg["seeds"] = args.seeds
        if args.only and args.only.lower() not in cfg["slug"]:
            continue
        print(f"\n== {cfg['title']}  [{', '.join(cfg['names'])} · {cfg['balls_per_team']} balls each · {cfg['gap_count']} gap(s)]")
        rep_path = OUT / f"{cfg['slug']}.report.json"
        if args.cover_only:
            seed = args.seed if args.seed is not None else (json.loads(rep_path.read_text())["seed"] if rep_path.exists() else None)
            if seed is None:
                seed = search(cfg, args.workers)[0][0]
            res = sim.simulate(cfg, seed, record=True)
            paths = cover.make_cover(cfg, res, render.Renderer(cfg, res), OUT)
            print("  cover:", ", ".join(str(p.relative_to(HERE)) for p in paths))
            continue
        if args.seed is not None:
            seed, rows = args.seed, None
        else:
            rows = search(cfg, args.workers)
            seed = rows[0][0]
        res = sim.simulate(cfg, seed, record=True)
        if not res.get("ok"):
            raise SystemExit(f"seed {seed} produced no winner")
        score, b = sim.drama(res, cfg)
        print(f"  rendering seed {seed}: {cfg['names'][res['winner']]} wins after {res['t_end']:.2f}s → {res['seconds']:.2f}s video")
        mp4 = OUT / f"{cfg['slug']}.mp4"
        ainfo = render_video(cfg, res, mp4, args.workers)
        v = verify(cfg, res, mp4)
        write_meta(cfg)
        paths = cover.make_cover(cfg, res, _CTX["renderer"], OUT)
        print("  cover:", ", ".join(str(p.relative_to(HERE)) for p in paths))
        report = dict(slug=cfg["slug"], seed=seed, winner=cfg["names"][res["winner"]], score=round(score, 1), drama=b, audio=ainfo, video=v["summary"],
                      seeds_searched=len(rows) if rows else 0, seeds_meeting_all_rules=sum(1 for r in rows if r[2].get("hard_ok")) if rows else None,
                      runner_up_seeds=[dict(seed=r[0], score=round(r[1], 1), winner=cfg["names"][r[3]]) for r in rows[1:4]] if rows else [])
        (OUT / f"{cfg['slug']}.report.json").write_text(json.dumps(report, indent=2, default=str))
        made.append((mp4, seed, cfg["names"][res["winner"]], score))
    print()
    for mp4, seed, w, s in made:
        print(f"DONE {mp4.relative_to(HERE)}  seed {seed}  winner {w}  drama score {s:.1f}")
    if not made:
        print("no episodes matched")


if __name__ == "__main__":
    sys.exit(main())
