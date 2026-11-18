"""Parallel chunked renderer: cairo frames -> ffmpeg (H.264) chunks -> concat + mux."""
import json
import math
import os
import subprocess
import sys
import time
from multiprocessing import Pool
import cairo
import numpy as np
from .scene import Scene, BASE_W, BASE_H
from .core import clamp, lerp, smoothstep, in_out_cubic
from . import graphics as G

_CACHE = {}
_CHUNKS = {}


def _scene(tl, i):
    key = (id(tl), i)
    if key not in _CACHE:
        _CACHE[key] = Scene(tl["scenes"][i])
    return _CACHE[key]


def scene_at(tl, T):
    sc = tl["scenes"]
    lo, hi = 0, len(sc) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if sc[mid]["start"] <= T:
            lo = mid
        else:
            hi = mid - 1
    return lo


# ------------------------------------------------------------------ post: ripple
_GRID = {}


def ripple(arr, t, amt, W, H, cx=None, cy=None):
    key = (W, H)
    if key not in _GRID:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        _GRID[key] = (yy, xx)
    yy, xx = _GRID[key]
    cx = W / 2 if cx is None else cx
    cy = H / 2 if cy is None else cy
    dx, dy = xx - cx, yy - cy
    r = np.sqrt(dx * dx + dy * dy) + 1e-3
    wave = np.sin(r / (28 * W / BASE_W) - t * 14) * amt * 22 * W / BASE_W * np.exp(-r / (W * 0.6))
    sx = np.clip((xx + dx / r * wave).astype(np.int32), 0, W - 1)
    sy = np.clip((yy + dy / r * wave).astype(np.int32), 0, H - 1)
    arr[:] = arr[sy, sx]


# ------------------------------------------------------------------ captions (shorts)
def draw_word_captions(ctx, W, H, words, T, y_frac=0.79):
    """Bold word-by-word captions: shows a 3-word window, current word highlighted."""
    cur = None
    for i, w in enumerate(words):
        if w["t"] <= T < w["t"] + max(w["d"], 0.12) + 0.25:
            cur = i
    if cur is None:
        return
    # group into chunks of up to 3 words, breaking at sentence ends
    key = id(words)
    if _CHUNKS.get("key") != key:
        starts, n = [], 0
        for i, w in enumerate(words):
            if n == 0 or n == 3 or words[i - 1]["w"][-1:] in ".?!:" or w["t"] - words[i - 1]["t"] > 1.0:
                starts.append(i); n = 0
            n += 1
        _CHUNKS.update(key=key, starts=starts)
    starts = _CHUNKS["starts"]
    start = max(s0 for s0 in starts if s0 <= cur)
    nxt = [s0 for s0 in starts if s0 > start]
    chunk = words[start:(nxt[0] if nxt else start + 3)]
    if T > chunk[-1]["t"] + chunk[-1]["d"] + 0.4:
        return
    u = W / 1080
    fs = 92 * u
    G.font(ctx, fs, "black")
    toks = [w["w"].upper().strip(",.;:") for w in chunk]
    widths = [ctx.text_extents(tk).x_advance + fs * 0.28 for tk in toks]
    total = sum(widths)
    scale = min(1.0, (W * 0.92) / total)
    x = (W - total * scale) / 2
    y = H * y_frac
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(scale, scale)
    xx = 0
    for j, (tk, wd) in enumerate(zip(toks, widths)):
        active = start + j == cur
        pop = 1.0
        if active:
            k = clamp((T - chunk[j]["t"]) / 0.12)
            pop = 1 + 0.12 * math.sin(k * math.pi)
        ctx.save()
        ctx.translate(xx + wd / 2, 0)
        ctx.scale(pop, pop)
        ctx.translate(-(wd / 2), 0)
        ctx.move_to(0, 0)
        ctx.text_path(tk)
        ctx.set_line_width(fs * 0.16)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.set_source_rgba(0, 0, 0, 1)
        ctx.stroke_preserve()
        if active:
            ctx.set_source_rgba(1, 0.86, 0.15, 1)
        else:
            ctx.set_source_rgba(1, 1, 1, 1)
        ctx.fill()
        ctx.restore()
        xx += wd
    ctx.restore()


def draw_srt_caption(ctx, W, H, lines, T):
    """Long-form burned-in subtitle: bold white words with dark outline,
    the word being spoken highlighted, on a soft translucent band."""
    for l in lines:
        if not (l["t0"] - 0.05 <= T <= l["t1"]):
            continue
        u = W / BASE_W
        fs = 52 * u
        ws = l.get("words") or [{"w": l["text"], "t": l["t0"], "d": l["t1"] - l["t0"]}]
        G.font(ctx, fs, "xbold")
        sp = fs * 0.27
        widths = [ctx.text_extents(w["w"]).x_advance for w in ws]
        total = sum(widths) + sp * (len(ws) - 1)
        x = (W - total) / 2
        y = H * 0.9
        a = min(1.0, (T - l["t0"] + 0.05) / 0.12, (l["t1"] - T) / 0.12 + 0.2)
        a = max(0.0, min(1.0, a))
        g = cairo.LinearGradient(0, y - fs * 1.6, 0, H)
        g.add_color_stop_rgba(0, 0, 0, 0, 0)
        g.add_color_stop_rgba(0.45, 0, 0, 0, 0.45 * a)
        g.add_color_stop_rgba(1, 0, 0, 0, 0.55 * a)
        ctx.set_source(g)
        ctx.rectangle(0, y - fs * 1.6, W, H - (y - fs * 1.6))
        ctx.fill()
        for w, wd in zip(ws, widths):
            active = w["t"] <= T < w["t"] + max(w["d"], 0.1) + 0.08
            spoken = T >= w["t"]
            ctx.move_to(x, y)
            ctx.text_path(w["w"])
            ctx.set_line_join(cairo.LINE_JOIN_ROUND)
            ctx.set_line_width(fs * 0.14)
            ctx.set_source_rgba(0, 0, 0, 0.9 * a)
            ctx.stroke_preserve()
            if active:
                ctx.set_source_rgba(1, 0.85, 0.2, a)
            elif spoken:
                ctx.set_source_rgba(1, 1, 1, a)
            else:
                ctx.set_source_rgba(1, 1, 1, 0.7 * a)
            ctx.fill()
            x += wd + sp
        return


# ------------------------------------------------------------------ frame
def render_frame(tl, T, W, H, opts=None):
    opts = opts or {}
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    i = scene_at(tl, T)
    sc = _scene(tl, i)
    lt = T - sc.spec["start"]
    if opts.get("vertical"):
        # reframe: shift camera so Fardin (or a focus point) stays centred
        focus = sc.spec.get("short_focus")
        if focus is None:
            xs = [sc.fardin_screen(lt - k * 0.12)[0] for k in range(6)]
            fx = sum(xs) / len(xs)
        else:
            fx = focus
        cam = sc.cam_at(lt)
        sc._xshift = (fx - BASE_W / 2) / max(0.3, cam[2])
        sc._xshift = max(-600, min(600, sc._xshift * 0.6))
        orig = sc.cam_at
        def shifted(t, _o=orig, _s=sc):
            x, y, z = _o(t)
            return (x + _s._xshift, y, z)
        sc.cam_at = shifted
        try:
            sc.render(ctx, W, H, lt, ui=not opts.get("no_ui"))
        finally:
            sc.cam_at = orig
    else:
        sc.render(ctx, W, H, lt, ui=not opts.get("no_ui"))
    # ripple post effect
    for fx in sc.spec.get("fx", []):
        if fx["type"] == "ripple" and fx["t"] <= lt <= fx["t"] + fx.get("dur", 1.0):
            k = (lt - fx["t"]) / fx.get("dur", 1.0)
            amt = math.sin(k * math.pi) * fx.get("amt", 1.0)
            surf.flush()
            arr = np.ndarray((H, W, 4), np.uint8, surf.get_data())
            ripple(arr, lt, amt, W, H)
            surf.mark_dirty()
    # scene boundary dip (chapter changes get a soft dip to black)
    nxt = tl["scenes"][i + 1] if i + 1 < len(tl["scenes"]) else None
    if sc.spec.get("dip_out") or (nxt and nxt.get("chapter") != sc.spec.get("chapter") and not sc.spec.get("no_dip")):
        d = sc.spec.get("dip", 0.22)
        k = clamp((lt - (sc.dur - d)) / d)
        if k > 0:
            ctx.set_source_rgba(0, 0, 0, in_out_cubic(k)); ctx.paint()
    prev = tl["scenes"][i - 1] if i > 0 else None
    if sc.spec.get("dip_in") or (prev and prev.get("chapter") != sc.spec.get("chapter") and not sc.spec.get("no_dip")):
        d = sc.spec.get("dip", 0.22)
        k = 1 - clamp(lt / d)
        if k > 0:
            ctx.set_source_rgba(0, 0, 0, in_out_cubic(k)); ctx.paint()
    if opts.get("captions") == "srt":
        draw_srt_caption(ctx, W, H, opts["lines"], T)
    elif opts.get("captions") == "words":
        draw_word_captions(ctx, W, H, opts["words"], T)
    if opts.get("overlay"):
        opts["overlay"](ctx, W, H, T)
    surf.flush()
    return surf


# ------------------------------------------------------------------ chunk worker
def _worker(job):
    tl_path, f0, f1, W, H, out, opts_name = job
    tl = json.load(open(tl_path))
    fps = tl["fps"]
    opts = _OPTS.get(opts_name, {})
    if opts.get("captions") == "srt" and "lines" not in opts:
        from .build import caption_lines, punctuate
        opts = dict(opts, lines=caption_lines(punctuate(tl)))
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(fps),
           "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-threads", "2", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(f0, f1):
        s = render_frame(tl, f / fps, W, H, opts)
        p.stdin.write(bytes(s.get_data()))
    p.stdin.close()
    p.wait()
    return out


_OPTS = {"default": {}, "srt": {"captions": "srt"}}


def render_video(tl_path, out_path, mix_wav, W=1920, H=1080, procs=None, t0=0.0, t1=None, chunk_s=12.0, captions=False):
    tl = json.load(open(tl_path))
    fps = tl["fps"]
    t1 = tl["duration"] if t1 is None else min(t1, tl["duration"])
    F0, F1 = int(round(t0 * fps)), int(round(t1 * fps))
    work = os.path.join(os.path.dirname(out_path) or ".", ".chunks_" + os.path.basename(out_path))
    os.makedirs(work, exist_ok=True)
    step = int(chunk_s * fps)
    jobs = []
    for k, f in enumerate(range(F0, F1, step)):
        jobs.append((tl_path, f, min(F1, f + step), W, H, os.path.join(work, f"c{k:04d}.mp4"), "srt" if captions else "default"))
    procs = procs or os.cpu_count()
    t_start = time.time()
    done = 0
    with Pool(procs) as pool:
        for _ in pool.imap_unordered(_worker, jobs):
            done += 1
            el = time.time() - t_start
            print(f"  chunk {done}/{len(jobs)}  {el:.0f}s elapsed, ~{el / done * (len(jobs) - done):.0f}s left", flush=True)
    lst = os.path.join(work, "list.txt")
    with open(lst, "w") as f:
        for j in jobs:
            f.write(f"file '{os.path.abspath(j[5])}'\n")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", mix_wav,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-shortest", "-movflags", "+faststart", out_path], check=True)
    for j in jobs:
        os.remove(j[5])
    os.remove(lst)
    os.rmdir(work)
    return out_path


def still(tl, T, path, W=1920, H=1080, opts=None):
    s = render_frame(tl, T, W, H, opts)
    s.write_to_png(path)
