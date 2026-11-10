#!/usr/bin/env python3
"""Quality gate for final/final.mp4 → qa/contact_sheet.png + qa/report.json.

Checks: container specs, loudness/true peak, contact sheet of 6 stills (0/5/10/18/26/29 s),
counter readable, no ball escapes before the finale, glow not blown out, title clear of
the circle, and audio sync (note triggered by a hit at frame N starts at N/60 s, measured
on the AAC track decoded back out of the MP4).
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import signal

HERE = Path(__file__).resolve().parent
FINAL = HERE / "final" / "final.mp4"
BUILD, QA = HERE / "build", HERE / "qa"
QA.mkdir(exist_ok=True)
W, H, FPS = 1080, 1920, 60
STILLS = [0, 5, 10, 18, 26, 29]
results, failures = {}, []


def check(name, ok, detail):
    results[name] = {"pass": bool(ok), "detail": detail}
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    if not ok:
        failures.append(name)


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True, check=True)


# ---------------------------------------------------------------- specs
probe = json.loads(sh("ffprobe", "-v", "error", "-show_streams", "-show_format", "-count_frames", "-of", "json", str(FINAL)).stdout)
v = next(s for s in probe["streams"] if s["codec_type"] == "video")
a = next(s for s in probe["streams"] if s["codec_type"] == "audio")
check("video_spec", v["codec_name"] == "h264" and v["width"] == W and v["height"] == H and v["r_frame_rate"] == "60/1"
      and int(v["nb_read_frames"]) == 1800 and v["pix_fmt"] == "yuv420p",
      f'{v["codec_name"]} {v["width"]}x{v["height"]} {v["r_frame_rate"]} {v["nb_read_frames"]} frames {v["pix_fmt"]}')
dur = float(probe["format"]["duration"])
check("audio_spec", a["codec_name"] == "aac" and a["sample_rate"] == "48000" and a["channels"] == 2 and abs(dur - 30) < 0.05,
      f'{a["codec_name"]} {a["sample_rate"]} Hz {a["channels"]} ch, container {dur:.3f}s')

# ---------------------------------------------------------------- loudness (ffmpeg's own EBU R128 meter)
log = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(FINAL), "-map", "0:a", "-af", "ebur128=peak=true",
                      "-f", "null", "-"], capture_output=True, text=True).stderr
summ = log[log.rfind("Summary:"):]
I = float(re.search(r"I:\s+(-?[\d.]+) LUFS", summ).group(1))
TP = float(re.search(r"True peak:\s+Peak:\s+(-?[\d.]+) dBFS", summ, re.S).group(1))
check("loudness", abs(I + 14) <= 0.5 and TP <= -0.5, f"{I:.1f} LUFS integrated, {TP:.1f} dBTP")

# ---------------------------------------------------------------- stills + contact sheet
frames = {}
for s in STILLS:
    n = s * FPS
    raw = sh_bytes = subprocess.run(["ffmpeg", "-v", "error", "-i", str(FINAL), "-vf", f"select=eq(n\\,{n})", "-vframes", "1",
                                     "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    frames[s] = np.frombuffer(raw, np.uint8).reshape(H, W, 3)
font_path = sh("fc-match", "-f", "%{file}", "Inter Display:black").stdout
font = ImageFont.truetype(font_path, 44)
tw, th = 360, 640
sheet = Image.new("RGB", (tw * 3 + 40, (th + 70) * 2 + 20), (20, 20, 24))
d = ImageDraw.Draw(sheet)
for k, s in enumerate(STILLS):
    im = Image.fromarray(frames[s]).resize((tw, th), Image.LANCZOS)
    x0, y0 = 10 + (k % 3) * (tw + 10), 10 + (k // 3) * (th + 70)
    sheet.paste(im, (x0, y0 + 60))
    d.text((x0 + 4, y0 + 6), f"{s}s · frame {s * FPS}", fill=(255, 255, 255), font=font)
sheet.save(QA / "contact_sheet.png")
results["contact_sheet"] = str(QA / "contact_sheet.png")

ev = json.loads((BUILD / "events.json").read_text())
lay = ev["layout"]
cx, cy, R = lay["circle"]["cx"], lay["circle"]["cy"], lay["circle"]["r"]
yy, xx = np.mgrid[0:H, 0:W]
inside = (xx - cx) ** 2 + (yy - cy) ** 2 < (R - 12) ** 2
outside_ring = ((xx - cx) ** 2 + (yy - cy) ** 2 > (R + 45) ** 2) & (yy > lay["titleBottom"] + 20) & (yy < lay["counterCenterY"] - 90)

# no escapes before the finale: physics audit + pixels outside the wall halo stay black
st = ev["stats"]
leak = max(float(np.mean(frames[s][outside_ring].max(axis=1) > 60)) for s in STILLS if s < 27)
check("no_escape_before_finale", st["escapedBeforeCrack"] == 0 and st["maxOverflowBeforeCrack"] < 0.5 and leak < 0.001,
      f'sim max overflow {st["maxOverflowBeforeCrack"]:.2e}px, escapes {st["escapedBeforeCrack"]}, '
      f'lit pixels outside wall {leak * 100:.3f}%')

# glow not blown out: share of clipped near-white pixels inside the circle
blow = {s: float(np.mean(frames[s][inside].min(axis=1) >= 245)) for s in STILLS if s < 27}
check("glow_not_blown_out", max(blow.values()) < 0.02, "clipped-white inside circle: " +
      ", ".join(f"{s}s {v * 100:.2f}%" for s, v in blow.items()))

# title clear of the circle (+ its ~30px glow) and actually in frame
gap = lay["circle"]["top"] - 30 - lay["titleBottom"]
check("title_clear_of_circle", gap >= 30 and lay["titleWidth"] < W - 120,
      f'title bottom y={lay["titleBottom"]:.0f}, circle glow top y={lay["circle"]["top"] - 30}, gap {gap:.0f}px, '
      f'title width {lay["titleWidth"]:.0f}px, font {lay["fontUsed"]}')

# counter readable: big type, high-contrast white glyphs present in the counter band
cy0 = lay["counterCenterY"]
band = slice(cy0 - 75, cy0 + 65)
white = {s: float(np.mean(frames[s][band].min(axis=2) > 200)) for s in STILLS if s < 28}
check("counter_readable", lay["counterFontPx"] >= 96 and min(white.values()) > 0.03,
      f'{lay["counterFontPx"]}px type; white glyph coverage ' + ", ".join(f"{s}s {v * 100:.1f}%" for s, v in white.items()))

# ---------------------------------------------------------------- audio sync
SR = 48000
dec = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", str(FINAL), "-map", "0:a", "-f", "f32le", "-ac", "1", "-ar",
                                    str(SR), "-"], capture_output=True, check=True).stdout, np.float32)
from scipy.io import wavfile  # noqa: E402
_, src = wavfile.read(BUILD / "audio.wav")
src = src.mean(axis=1)
notes = json.loads((BUILD / "notes.json").read_text())["notes"]
# (1) whole-track lag between generated master and AAC in the MP4
seg = slice(0, SR * 12)
cc = signal.correlate(dec[seg], src[seg], mode="full", method="fft")
lag = int(np.argmax(cc)) - (len(src[seg]) - 1)
# (2) onset of isolated notes measured in the decoded MP4 vs frame/60
errs = []
for nt in notes:
    t_exp = nt["frame"] / FPS
    if t_exp > 12 or len(errs) >= 12:
        break
    s0 = int(t_exp * SR)
    w = np.abs(dec[s0 - 2400: s0 + 2400])
    pre = np.abs(dec[s0 - 2400: s0 - 600]).max()
    thr = max(pre * 3, w.max() * 0.25)
    onset = np.argmax(w > thr) + s0 - 2400
    errs.append((onset / SR - t_exp) * 1000)
errs = np.array(errs)
check("audio_sync", abs(lag) <= 48 and np.max(np.abs(errs)) <= 5,
      f"master→mp4 lag {lag} samples ({lag / SR * 1000:.2f} ms); onset error of first {len(errs)} notes vs N/60: "
      f"mean {errs.mean():+.2f} ms, max |{np.max(np.abs(errs)):.2f}| ms")
fr = np.array([nt["frame"] for nt in notes])
rate = int(max(np.sum((fr >= f) & (fr < f + FPS)) for f in fr))
check("note_rate", rate <= 25, f"{len(notes)} notes, peak {rate} notes/s (hits merged)")

# growth curve (for the record)
cnt = ev["countAtFrame"]
results["count_by_second"] = {s: cnt[s * FPS] for s in range(0, 30, 2)}
results["first_frame_at_2048"] = next((i for i, c in enumerate(cnt) if c == 2048), None)
(QA / "report.json").write_text(json.dumps(results, indent=2))
print("count by second:", results["count_by_second"], "· 2048 reached at",
      f'{results["first_frame_at_2048"] / FPS:.2f}s')
print("QA:", "ALL PASS" if not failures else f"FAILED {failures}")
sys.exit(1 if failures else 0)
