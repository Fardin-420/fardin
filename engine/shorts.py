"""Auto Shorts: vertical 1080x1920 re-renders (not crops) of the strongest moments,
with a 2-second hook, bold word-by-word captions and an end card."""
import json
import math
import os
import subprocess
from multiprocessing import Pool
import numpy as np
from . import audio as A
from . import graphics as G
from .build import punctuate
from .core import clamp, out_back
from . import renderer as R

W, H = 1080, 1920


def plan(tl, spec):
    sc = {s["id"]: s for s in tl["scenes"]}
    a, b = sc[spec["from"]], sc[spec["to"]]
    start = a["start"] + spec.get("trim_in", 0.0)
    end = b["start"] + b["dur"] - spec.get("trim_out", 0.0)
    hs = sc[spec["hook_scene"]]
    hook_T = hs["start"] + spec.get("hook_at", 0.5) * hs["dur"]
    return {"start": start, "end": end, "hook_T": hook_T, "hook": spec["hook"], "hook_len": 2.0, "end_len": 2.6}


def frame_time(p, tau):
    if tau < p["hook_len"]:
        return p["hook_T"] + tau * 0.6, "hook", tau
    tau2 = tau - p["hook_len"]
    L = p["end"] - p["start"]
    if tau2 < L:
        return p["start"] + tau2, "clip", tau2
    k = tau2 - L
    return p["end"] - 0.05 + k * 0.25, "end", k


def overlay_hook(ctx, lt, text):
    u = W / 1080
    ctx.set_source_rgba(0, 0, 0, 0.35)
    ctx.paint()
    k = max(0.02, out_back(clamp(lt / 0.25), 2.5))
    words = text.split()
    lines = [" ".join(words[i:i + 2]) for i in range(0, len(words), 2)]
    ctx.save()
    ctx.translate(W / 2, H * 0.3)
    ctx.scale(k, k)
    ctx.rotate(-0.05)
    fs = 150 * u
    for i, ln in enumerate(lines):
        G.font(ctx, fs, "black")
        tw = ctx.text_extents(ln).x_advance
        sc = min(1.0, W * 0.9 / tw)
        ctx.save(); ctx.scale(sc, sc)
        ctx.move_to(-tw / 2, i * fs * 1.05)
        ctx.text_path(ln)
        ctx.set_source_rgba(0, 0, 0, 1); ctx.set_line_width(fs * 0.16); ctx.set_line_join(1); ctx.stroke_preserve()
        ctx.set_source_rgba(1, 0.86, 0.15, 1) if i == len(lines) - 1 else ctx.set_source_rgba(1, 1, 1, 1)
        ctx.fill()
        ctx.restore()
    ctx.restore()


def overlay_end(ctx, k):
    u = W / 1080
    a = clamp(k / 0.4)
    ctx.set_source_rgba(0.01, 0.02, 0.05, 0.78 * a)
    ctx.paint()
    G.text(ctx, "Full story", W / 2, H * 0.42, 110 * u, (1, 1, 1), "black", align="center", alpha=a)
    G.text(ctx, "on the channel.", W / 2, H * 0.42 + 125 * u, 96 * u, (1, 0.86, 0.15), "black", align="center", alpha=a)
    G.draw_subscribe(ctx, W, H, {"text": "SUBSCRIBE", "sub": "TIME GHOST · Episode L001", "dur": 99}, k, k)


def _worker(job):
    tl_path, p, f0, f1, out = job
    tl = json.load(open(tl_path))
    words = punctuate(tl)
    fps = tl["fps"]
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-threads", "2", out]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(f0, f1):
        tau = f / fps
        T, part, lt = frame_time(p, tau)
        opts = {"vertical": True}
        if part == "clip":
            opts.update(captions="words", words=words)
        elif part == "hook":
            opts["no_ui"] = True
            opts["overlay"] = lambda ctx, w, h, TT, lt=lt: overlay_hook(ctx, lt, p["hook"])
        else:
            opts["no_ui"] = True
            opts["overlay"] = lambda ctx, w, h, TT, k=lt: overlay_end(ctx, k)
        s = R.render_frame(tl, T, W, H, opts)
        pr.stdin.write(bytes(s.get_data()))
    pr.stdin.close()
    pr.wait()
    return out


def audio_for(p, mix):
    def sl(t0, t1):
        return mix[int(t0 * A.SR):int(t1 * A.SR)].copy()
    hook = sl(p["hook_T"], p["hook_T"] + p["hook_len"])
    n = len(hook)
    hook *= np.minimum(1, np.arange(n) / (0.05 * A.SR)) * np.minimum(1, (n - np.arange(n)) / (0.15 * A.SR))
    hook = hook * 0.8
    hit = A.sfx_impact(5, 1.2) * 0.5
    hook[:len(hit)] += hit[:n]
    clip = sl(p["start"], p["end"])
    m = len(clip)
    clip *= np.minimum(1, np.arange(m) / (0.08 * A.SR))
    tail_len = int(p["end_len"] * A.SR)
    tail = sl(p["end"], p["end"] + p["end_len"])
    tail = np.pad(tail, (0, max(0, tail_len - len(tail))))[:tail_len]
    tail *= np.linspace(0.6, 0, tail_len)
    w = A.sfx_whoosh(0.8, 3) * 0.4
    out = np.concatenate([hook, clip, tail])
    A.place(out, w, p["hook_len"] - 0.4)
    st = A.sfx_stinger(2) * 0.35
    A.place(out, st, p["hook_len"] + (p["end"] - p["start"]))
    return np.clip(out, -1, 1)


def make_short(tl_path, spec, out, mix, procs=None):
    tl = json.load(open(tl_path))
    p = plan(tl, spec)
    total = p["hook_len"] + (p["end"] - p["start"]) + p["end_len"]
    fps = tl["fps"]
    N = int(round(total * fps))
    work = out + ".parts"
    os.makedirs(work, exist_ok=True)
    step = 5 * fps
    jobs = [(tl_path, p, f, min(N, f + step), os.path.join(work, f"p{i:03d}.mp4")) for i, f in enumerate(range(0, N, step))]
    with Pool(procs or os.cpu_count()) as pool:
        list(pool.imap_unordered(_worker, jobs))
    lst = os.path.join(work, "list.txt")
    open(lst, "w").write("".join(f"file '{os.path.abspath(j[4])}'\n" for j in jobs))
    wav = os.path.join(work, "a.wav")
    au = audio_for(p, mix)
    na = int(round(N / fps * A.SR))
    au = np.pad(au, (0, max(0, na - len(au))))[:na]  # exactly the video length
    A.write_wav(wav, au)
    A.loudnorm_wav(wav, I=-15.0, TP=-1.6)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out], check=True)
    for j in jobs:
        os.remove(j[4])
    os.remove(lst); os.remove(wav); os.rmdir(work)
    return out, total


def make_all(ep, tl_path, out_dir, num, procs=None):
    from . import qc
    specs = json.load(open(os.path.join(ep, "shorts.json")))
    mix = A.decode(os.path.join(ep, "build", "mix.wav"))
    for i, spec in enumerate(specs, 1):
        out = os.path.join(out_dir, f"timeghost_{num}_short{i}.mp4")
        print(f"[short {i}] {spec['hook']}", flush=True)
        _, total = make_short(tl_path, spec, out, mix, procs)
        qc.report(out, check_len=True, min_len=30, max_len=60, w=W, h=H)
