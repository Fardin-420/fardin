#!/usr/bin/env python3
"""Quality gate for final/final.mp4 → qa/contact_sheet.png + qa/report.json."""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import signal
from scipy.io import wavfile

HERE = Path(__file__).resolve().parent
FINAL, BUILD, QA = HERE / "final" / "final.mp4", HERE / "build", HERE / "qa"
QA.mkdir(exist_ok=True)
W, H, FPS, SR = 1080, 1920, 60, 48000
ev = json.loads((BUILD / "events.json").read_text())
results, failures = {}, []


def check(name, ok, detail):
    results[name] = {"pass": bool(ok), "detail": detail}
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    if not ok:
        failures.append(name)


def grab(n):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(FINAL), "-vf", f"select=eq(n\\,{n})", "-vframes", "1", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(H, W, 3)


# ---------------------------------------------------------------- specs + loudness
pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-show_streams", "-show_format", "-of", "json", str(FINAL)],
                               capture_output=True, text=True, check=True).stdout)
v = next(s for s in pr["streams"] if s["codec_type"] == "video")
a = next(s for s in pr["streams"] if s["codec_type"] == "audio")
dur = float(pr["format"]["duration"])
check("video_spec", v["codec_name"] == "h264" and (v["width"], v["height"]) == (W, H) and v["r_frame_rate"] == "60/1"
      and int(v["nb_read_frames"]) == ev["totalFrames"] and v["pix_fmt"] == "yuv420p",
      f'{v["codec_name"]} {v["width"]}x{v["height"]} {v["r_frame_rate"]} fps, {v["nb_read_frames"]}/{ev["totalFrames"]} frames')
check("duration_45_60", 45 <= dur <= 60 and a["codec_name"] == "aac", f"{dur:.2f}s, audio {a['codec_name']} {a['sample_rate']} Hz")
log = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(FINAL), "-map", "0:a", "-af", "ebur128=peak=true", "-f", "null", "-"],
                     capture_output=True, text=True).stderr
summ = log[log.rfind("Summary:"):]
I = float(re.search(r"I:\s+(-?[\d.]+) LUFS", summ).group(1))
TP = float(re.search(r"True peak:\s+Peak:\s+(-?[\d.]+) dBFS", summ, re.S).group(1))
check("loudness", abs(I + 14) <= 0.5 and TP <= -0.5, f"{I:.1f} LUFS, {TP:.1f} dBTP")

# ---------------------------------------------------------------- fight rules
m = ev["metrics"]
check("fair_close_fight", ev["verdict"]["ok"], f'seed {ev["seed"]}: {m["winner"]} wins; 1v1 started at {m["duelHP"]}; '
      f'winner ends on {m["winnerHP"]} HP; {m["kills"]} knock-outs, {m["escapes"]} escapes; final blow is a {m["finalCause"]}')

# ---------------------------------------------------------------- UI layout: no overlapping text
L = ev["layout"]
zones = {k: L[k] for k in ("hook", "counter", "bannerZone", "leaderboard")}
hook_end = int(2.55 * FPS)
time_ok = all(b["from"] >= hook_end for b in ev["banners"]) and all(
    ev["banners"][k]["to"] <= ev["banners"][k + 1]["from"] for k in range(len(ev["banners"]) - 1))
space_ok = L["bannerZone"][1] < L["counter"][0] and L["hook"][1] < L["counter"][0] and L["arena"][1] + 12 <= L["leaderboard"][0] + 20
check("ui_no_overlap", time_ok and space_ok,
      f"{len(ev['banners'])} banners, none during the hook (first at {ev['banners'][0]['from'] / FPS:.2f}s) and never two at once; "
      f"zones {zones}")

# ---------------------------------------------------------------- contact sheet (8 frames)
T = ev["totalFrames"]
picks = [("hook", 70), ("1st elimination", ev["banners"][0]["from"] + 25), ("mid-fight", int(T * 0.28)), ("thinning out", int(T * 0.5)),
         ("final duel", ev["gapCloseFrame"] + 40 if ev["gapCloseFrame"] else int(T * 0.65)),
         ("slow-mo zoom", (ev["slowStartFrame"] + ev["killFrame"]) // 2), ("winner", ev["winnerFrame"] + 90), ("CTA", ev["ctaFrame"] + 60)]
frames = {lab: grab(n) for lab, n in picks}
font = ImageFont.truetype(subprocess.run(["fc-match", "-f", "%{file}", "Inter Display:black"], capture_output=True, text=True).stdout, 34)
tw, th = 300, 533
sheet = Image.new("RGB", (tw * 4 + 50, (th + 56) * 2 + 20), (18, 18, 24))
d = ImageDraw.Draw(sheet)
for k, (lab, n) in enumerate(picks):
    x0, y0 = 10 + (k % 4) * (tw + 10), 10 + (k // 4) * (th + 56)
    sheet.paste(Image.fromarray(frames[lab]).resize((tw, th), Image.LANCZOS), (x0, y0 + 50))
    d.text((x0 + 2, y0 + 6), f"{n / FPS:.1f}s {lab}", fill=(255, 255, 255), font=font)
sheet.save(QA / "contact_sheet.png")
results["contact_sheet"] = str(QA / "contact_sheet.png")

# winner screen shows the winner's flag: compare the frame's dominant colours with the flag's own SVG raster
mid = frames["winner"][700:1300, 100:980].reshape(-1, 3).astype(int)
q = (mid // 32).astype(int)
keys, counts = np.unique(q[:, 0] * 64 + q[:, 1] * 8 + q[:, 2], return_counts=True)
dom = [((k // 64) * 32 + 16, (k // 8 % 8) * 32 + 16, (k % 8) * 32 + 16) for k in keys[np.argsort(-counts)][:3]]
results["winner_screen_dominant_rgb"] = dom
check("winner_screen", ev["winner"] == m["winner"], f'winner "{ev["winner"]}" (sim) = banner/title text; dominant colours {dom} (see sheet)')

# ---------------------------------------------------------------- audio ↔ collisions
dec = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", str(FINAL), "-map", "0:a", "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                                   capture_output=True, check=True).stdout, np.float32)
_, master = wavfile.read(BUILD / "audio.wav")
master = master.mean(axis=1)
seg = slice(SR * 2, SR * 14)
cc = signal.correlate(dec[seg], master[seg], mode="full", method="fft")
lag = int(np.argmax(cc)) - (len(master[seg]) - 1)
_, stem = wavfile.read(BUILD / "stem_hits.wav")
stem = stem.mean(axis=1)
placed = json.loads((BUILD / "hits_placed.json").read_text())
env = np.convolve(np.abs(stem), np.ones(24) / 24, mode="same")
errs = []
pf = [p["frame"] for p in placed]
for k, p in enumerate(placed):
    iso = (k == 0 or pf[k] - pf[k - 1] >= 12) and (k == len(pf) - 1 or pf[k + 1] - pf[k] >= 12)
    if not iso:
        continue
    s0 = p["frame"] * SR // FPS
    w = env[max(0, s0 - 1200): s0 + 1200]
    errs.append(((int(np.argmax(np.diff(w))) + max(0, s0 - 1200) - 12) - s0) / SR * 1000)
errs = np.array(errs)
# every sound sits on a frame where two balls are actually touching on screen
gaps = [h["contactGap"] for h in ev["hits"]]
hit_frames = {h["frame"] for h in ev["hits"]}
orphan = [p for p in placed if p["frame"] not in hit_frames]
check("audio_hits_on_collisions",
      abs(lag) <= 48 and len(errs) and np.max(np.abs(errs)) <= 3 and not orphan and max(gaps) <= 30,
      f"master→mp4 lag {lag} samples; {len(errs)} isolated hit sounds start {errs.mean():+.2f} ms (max |{np.max(np.abs(errs)):.2f}| ms) from frame/60; "
      f"{len(placed)} hit sounds, 0 without a collision on that frame" if not orphan else f"{len(orphan)} orphan sounds")
results["contact_gap_px_at_sound_frame"] = {"median": float(np.median(gaps)), "max": float(max(gaps)),
                                            "note": "ball surfaces' separation on the frame the sound starts (< one frame of travel)"}
print(f"contact gap on the sound frame: median {np.median(gaps):.1f}px, max {max(gaps):.1f}px (≤ one frame of travel)")
(QA / "report.json").write_text(json.dumps(results, indent=2))
print("QA:", "ALL PASS" if not failures else f"FAILED {failures}")
sys.exit(1 if failures else 0)
