#!/usr/bin/env python3
# SPACE SECRETS EP02 — "What If Earth Stopped Spinning for 5 Seconds?" (70 s vertical documentary)
# Visuals: Earth rendered from Solar System Scope textures (CC BY 4.0, NASA-based) + animated diagrams.
# Audio: Kokoro VO + original synthesized score/SFX (same engine and identity as EP01).
import json, math, re, subprocess, sys
from multiprocessing import Pool

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.signal import butter, sosfilt

import earth

W, H, FPS, DUR = 1080, 1920, 30, 70.0
NF = int(DUR * FPS)
SR = 48000
RS = 2 / 3                                   # Earth layer render scale (720x1280, upscaled)
TIM = json.load(open("timing.json"))
WT = {(l["line"], k): (s, e) for l in TIM for k, (w, s, e) in enumerate(l["words"])}
def ws(l, k): return WT[(l, k)][0]
def we(l, k): return WT[(l, k)][1]
def ls(l): return TIM[l]["start"]

S1, S2, S3, S4, S5, S6, S7 = 0.0, ls(1), ls(2), ls(3), ls(4), ls(5), ls(6)
T_STOP = we(0, 4)                 # "stopped" -> the solid surface halts
T_RESTART = ws(5, 6)              # "lurches"
OMEGA = 14.0                      # visual spin, deg/s (sped up for visibility)
OMEGA_AIR = 26.0                  # visual eastward drift of air relative to the stopped ground
LON_STOP = -12.0                  # longitude at the disk centre when the surface freezes

# ------------------------------------------------------------------ helpers
def clamp(v, a, b): return max(a, min(b, v))
def seg(t, a, b): return clamp((t - a) / (b - a), 0.0, 1.0)
def ease(x): x = clamp(x, 0, 1); return x * x * (3 - 2 * x)
def ease_out(x): x = clamp(x, 0, 1); return 1 - (1 - x) ** 3
def ease_back(x): x = clamp(x, 0, 1); c = 1.7; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2
def lerp(a, b, k): return a + (b - a) * k

F_CAP = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
F_UI = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
F_MONO = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf"
_fc = {}
def font(p, s):
    s = max(1, int(s))
    if (p, s) not in _fc: _fc[(p, s)] = ImageFont.truetype(p, s)
    return _fc[(p, s)]
WHITE, YELLOW, BLACK, RED, CYAN, ORANGE, GREEN = (255, 255, 255), (255, 212, 0), (0, 0, 0), (235, 60, 50), (120, 210, 255), (255, 150, 60), (90, 220, 120)

_ST = None
def starbg():
    global _ST
    if _ST is None: _ST = earth.stars(int(W * RS), int(H * RS))
    return _ST

def globe(cx, cy, R, lat0, lon_c, lon_cloud, **kw):
    a = earth.render(int(W * RS), int(H * RS), cx * RS, cy * RS, R * RS, lat0, lon_c, lon_cloud, stars=starbg(), **kw)
    a = a / 255.0
    a = a * (2.51 * a + 0.03) / (a * (2.43 * a + 0.59) + 0.14) * 1.08       # filmic tone curve, same as EP01
    return Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)

def tag(d, kind):
    txt = {"vis": "VISUALIZATION  ·  rotation sped up for visibility",
           "hyp": "HYPOTHETICAL SIMULATION  ·  not real footage",
           "diag": "DIAGRAM  ·  not to scale"}[kind]
    col = CYAN if kind == "vis" else (YELLOW if kind == "diag" else ORANGE)
    f = font(F_MONO, 24)
    d.rounded_rectangle((36, 60, 36 + f.getlength(txt) + 28, 104), 10, fill=(0, 0, 0, 150))
    d.ellipse((48, 76, 60, 88), fill=col)
    d.text((70, 82), txt, font=f, fill=(230, 230, 230), anchor="lm")
    d.text((W - 40, 144), "SPACE SECRETS · EP 02", font=f, fill=(200, 200, 200), anchor="rm", stroke_width=3, stroke_fill=BLACK)
    d.text((W / 2, 1890), "Earth imagery: Solar System Scope (CC BY 4.0), based on NASA data", font=font(F_MONO, 20),
           fill=(170, 170, 170), anchor="mm")

def clock_chip(d, t_story, label="SURFACE STOPPED"):
    txt = f"{label}  t = {t_story:3.1f} s / 5 s"
    f = font(F_MONO, 30)
    d.rounded_rectangle((36, 118, 36 + f.getlength(txt) + 40, 170), 10, fill=(160, 30, 25, 220))
    d.text((56, 144), txt, font=f, fill=WHITE, anchor="lm")

def big(d, x, y, txt, size, age, color=WHITE, sub=None, subcol=CYAN):
    pop = 1 + 0.35 * max(0, 1 - age / 0.14)
    d.text((x, y), txt, font=font(F_CAP, size * pop), fill=color, anchor="mm", stroke_width=10, stroke_fill=BLACK)
    if sub: d.text((x, y + size * 0.72), sub, font=font(F_MONO, 32), fill=subcol, anchor="mm", stroke_width=4, stroke_fill=BLACK)

def arrow(d, x0, y0, x1, y1, color=YELLOW, w=12, head=34):
    d.line((x0, y0, x1, y1), fill=BLACK, width=w + 8); d.line((x0, y0, x1, y1), fill=color, width=w)
    a = math.atan2(y1 - y0, x1 - x0)
    pts = [(x1 + 8 * math.cos(a), y1 + 8 * math.sin(a)), (x1 - head * math.cos(a - 0.5), y1 - head * math.sin(a - 0.5)),
           (x1 - head * math.cos(a + 0.5), y1 - head * math.sin(a + 0.5))]
    d.polygon(pts, fill=color, outline=BLACK, width=4)

def callout(d, x, y, tx, ty, title, sub, k, color=WHITE, anchor="lb"):
    if k <= 0: return
    ex, ey = lerp(tx, x, ease_out(k)), lerp(ty, y, ease_out(k))
    d.line((tx, ty, ex, ey), fill=color, width=4)
    d.ellipse((tx - 10, ty - 10, tx + 10, ty + 10), outline=color, width=4)
    if k > 0.6:
        d.text((x, y), title, font=font(F_UI, 44), fill=color, anchor=anchor, stroke_width=5, stroke_fill=BLACK)
        if sub:
            sy = y + 58 if anchor.endswith("t") else y + 10
            d.text((x, sy), sub, font=font(F_MONO, 29), fill=(230, 230, 230), anchor=anchor[0] + "t", stroke_width=4, stroke_fill=BLACK)

def polyline_lat(d, lat, cx, cy, R, lat0, lon_c, color, width, span=89):
    lons = np.linspace(lon_c - span, lon_c + span, 120)
    x, y, vis = earth.project(np.full_like(lons, lat), lons, cx, cy, R, lat0, lon_c)
    pts = [(float(a), float(b)) for a, b, v in zip(x, y, vis) if v]
    if len(pts) > 1: d.line(pts, fill=color, width=width)

def shake(t, t0, dur, amp):
    if not (t0 <= t < t0 + dur): return (0, 0)
    k = 1 - (t - t0) / dur
    return (amp * k * math.sin(t * 97), amp * k * math.cos(t * 83))

# ------------------------------------------------------------------ wind / water particles
PR = np.random.default_rng(12)
AIR_LAT = PR.uniform(-66, 66, 900); AIR_LON = PR.uniform(-100, 80, 900); AIR_PH = PR.uniform(0, 1, 900)
SEA_LAT = PR.uniform(-22, 22, 700); SEA_LON = PR.uniform(-55, 15, 700)

def draw_wind(img, t, cx, cy, R, lat0, lon_c, strength=1.0):
    d = ImageDraw.Draw(img, "RGBA")
    lon_now = AIR_LON + OMEGA_AIR * (t - S3)
    lon_now = (lon_now - (lon_c - 95)) % 190 + (lon_c - 95)
    for la, lo, ph in zip(AIR_LAT, lon_now, AIR_PH):
        L = 7 + 5 * ph
        x0, y0, v0 = earth.project(la, lo - L, cx, cy, R, lat0, lon_c)
        x1, y1, v1 = earth.project(la, lo, cx, cy, R, lat0, lon_c)
        if not (v0 and v1): continue
        a = int(220 * strength * (0.25 + 0.75 * math.cos(math.radians(la))))
        d.line((float(x0), float(y0), float(x1), float(y1)), fill=(230, 245, 255, min(255, int(a * 1.25))), width=5)

def draw_sea(img, t, cx, cy, R, lat0, lon_c, k):
    if k <= 0: return
    land = earth.tex()["land"]; th, tw = land.shape
    d = ImageDraw.Draw(img, "RGBA")
    lon_now = SEA_LON + 7.0 * (t - S4)
    lon_now = (lon_now + 55) % 70 - 55
    for la, lo in zip(SEA_LAT, lon_now):
        u = int(((lo + 180) / 360 * tw)) % tw; v = int((90 - la) / 180 * th)
        if land[v, u] > 0.5: continue
        x0, y0, v0 = earth.project(la, lo - 2.2, cx, cy, R, lat0, lon_c)
        x1, y1, v1 = earth.project(la, lo, cx, cy, R, lat0, lon_c)
        if v0 and v1:
            d.line((float(x0), float(y0), float(x1), float(y1)), fill=(150, 235, 255, int(230 * k)), width=5)

# ------------------------------------------------------------------ captions (same identity as EP01)
EMPH = {"STOPPED", "SPINNING", "FIVE", "SECONDS", "NOTHING", "CONSEQUENCES", "CATASTROPHIC", "EQUATOR", "EAST", "1,670",
        "AIR", "OCEANS", "HALTS", "ATMOSPHERE", "FOUR", "STRONGEST", "GUST", "WEST-FACING", "EAST-FACING", "UNCERTAIN",
        "DEPTH", "INERTIA", "BEDROCK", "FASTEST", "POLES", "FRICTION", "SUDDENLY", "LURCHES", "ABRUPTLY", "JOLT",
        "HARMLESS", "STOP", "LONG", "PILE"}
DISPLAY = {1: {10: "1,670", 11: None, 12: None, 13: None, 14: None}, 2: {20: "1,670", 21: None, 22: None, 23: None, 24: None}}
CAPS = []
for l in TIM:
    toks = []
    for k, (w, s, e) in enumerate(l["words"]):
        ov = DISPLAY.get(l["line"], {})
        if k in ov:
            if ov[k] is None: continue
            w = ov[k]
        toks.append((w.upper(), s, e))
    chunk = []
    for i, tk in enumerate(toks):
        chunk.append(tk)
        if re.search(r"[,.:?!]$", tk[0]) or len(chunk) == 3 or i == len(toks) - 1:
            CAPS.append(chunk); chunk = []
CAPS = [(ch[0][1], (CAPS[i + 1][0][1] if i + 1 < len(CAPS) and CAPS[i + 1][0][1] - ch[-1][2] < 0.6 else ch[-1][2] + 0.4), ch)
        for i, ch in enumerate(CAPS)]

def draw_caption(img, t, y=1470):
    d = ImageDraw.Draw(img)
    for a, b, ch in CAPS:
        if not (a <= t < b): continue
        vis = [x for x in ch if x[1] <= t + 0.02]
        if not vis: return
        base, gap, maxw = 100, 24, 940
        lines, cur, cw = [], [], 0
        for w, s, e in vis:
            sz = base * (1 + 0.25 * max(0, 1 - (t - s) / 0.11))
            fw = font(F_CAP, sz).getlength(w)
            if fw > maxw: sz *= maxw / fw; fw = font(F_CAP, sz).getlength(w)
            core = re.sub(r"[^A-Z0-9,'\-]", "", w).strip(",")
            if cur and cw + gap + fw > maxw: lines.append(cur); cur, cw = [], 0
            cur.append((w, sz, core in EMPH or core.rstrip(",") in EMPH, fw)); cw += (gap if len(cur) > 1 else 0) + fw
        lines.append(cur); lines = lines[-2:]
        lh = int(base * 1.1); y0 = y - (len(lines) - 1) * lh / 2
        for li, line in enumerate(lines):
            tot = sum(x[3] for x in line) + gap * (len(line) - 1); x = W / 2 - tot / 2
            for w, sz, em, fw in line:
                d.text((x, y0 + li * lh), w, font=font(F_CAP, sz), fill=YELLOW if em else WHITE, anchor="lm",
                       stroke_width=10, stroke_fill=BLACK)
                x += fw + gap
        return

# ------------------------------------------------------------------ scenes
def lon_spin(t, t_ref, lon_ref): return lon_ref - OMEGA * (t - t_ref)

def sc1(t):                                         # rotation, then the solid planet freezes
    R = lerp(470, 540, ease(seg(t, 0, S2))); cx, cy, lat0 = 540, 930, 10
    lon_c = lon_spin(min(t, T_STOP), T_STOP, LON_STOP)
    lon_cl = lon_spin(t, T_STOP, LON_STOP)          # clouds (air) keep going after the stop
    dx, dy = shake(t, T_STOP, 0.45, 26)
    img = globe(cx + dx, cy + dy, R, lat0, lon_c, lon_cl)
    if T_STOP <= t < T_STOP + 0.08: img = Image.blend(img, Image.new("RGB", (W, H), WHITE), 0.75)
    d = ImageDraw.Draw(img, "RGBA"); tag(d, "vis" if t < T_STOP else "hyp")
    k = ease_back(seg(t, 0.05, 0.35))
    d.text((W / 2, 220), "WHAT IF EARTH STOPPED SPINNING", font=font(F_CAP, 50 * k), fill=WHITE, anchor="mm", stroke_width=8, stroke_fill=BLACK)
    d.text((W / 2, 300), "FOR 5 SECONDS?", font=font(F_CAP, 92 * k), fill=YELLOW, anchor="mm", stroke_width=9, stroke_fill=BLACK)
    if t >= T_STOP:
        clock_chip(d, 0.0)
        kk = ease_out(seg(t, T_STOP + 0.5, T_STOP + 0.9))
        if kk > 0 and t < S2 - 0.3:
            d.text((W / 2, 1290), "SURFACE: STOPPED", font=font(F_UI, 44), fill=(255, 120, 90), anchor="mm", stroke_width=5, stroke_fill=BLACK)
            d.text((W / 2, 1345), "AIR + OCEANS: still moving", font=font(F_UI, 40), fill=CYAN, anchor="mm", stroke_width=5, stroke_fill=BLACK)
    return img

def sc2(t):                                         # normal rotation, equator speed
    k = ease(seg(t, S2, S2 + 3.0))
    R = lerp(540, 1150, k); cy = lerp(930, 1330, k); lat0 = lerp(10, 22, k); cx = 540
    lon_c = lon_spin(t, S2, LON_STOP + 40)
    img = globe(cx, cy, R, lat0, lon_c, lon_c)
    d = ImageDraw.Draw(img, "RGBA"); tag(d, "vis")
    d.rounded_rectangle((36, 118, 400, 170), 10, fill=(20, 90, 50, 220)); d.text((56, 144), "NORMAL ROTATION", font=font(F_MONO, 30), fill=WHITE, anchor="lm")
    ke = seg(t, ws(1, 2), ws(1, 2) + 0.4)
    if ke > 0:
        polyline_lat(d, 0, cx, cy, R, lat0, lon_c, (255, 212, 0, int(255 * ke)), 6)
        for la in (45, 60):
            polyline_lat(d, la, cx, cy, R, lat0, lon_c, (255, 255, 255, int(110 * ke)), 3)
    # markers fixed at the centre meridian: the ground under them moves east (right)
    ex, ey, _ = earth.project(0, lon_c, cx, cy, R, lat0, lon_c)
    if t >= ws(1, 7):
        ka = ease_out(seg(t, ws(1, 7), ws(1, 7) + 0.35))
        arrow(d, ex - 40, ey - 40, ex - 40 + 300 * ka, ey - 40, YELLOW, 14, 40)
        d.text((ex - 40, ey - 80), "EAST", font=font(F_MONO, 30), fill=YELLOW, anchor="lb", stroke_width=4, stroke_fill=BLACK)
    if t >= ws(1, 10):
        big(d, W / 2, 360, "1,670 km/h", 120, t - ws(1, 10), YELLOW, "at the equator  ·  1,037 mph  ·  464 m/s")
    if t >= ws(1, 18):
        kk = ease_out(seg(t, ws(1, 18), ws(1, 18) + 0.35))
        for la, txt in ((45, "45°N ≈ 1,180 km/h"), (60, "60°N ≈ 835 km/h")):
            x, y, vis = earth.project(la, lon_c + 18, cx, cy, R, lat0, lon_c)
            if vis: d.text((float(x), float(y) - 10), txt, font=font(F_UI, 36), fill=(255, 255, 255, int(255 * kk)), anchor="lb", stroke_width=4, stroke_fill=BLACK)
        d.text((W / 2, 520), "poles ≈ 0 km/h", font=font(F_MONO, 30), fill=(230, 230, 230, int(255 * kk)), anchor="mm", stroke_width=4, stroke_fill=BLACK)
    if t >= ws(1, 24):
        d.text((W / 2, 1290), "air + oceans move with the ground", font=font(F_UI, 40), fill=CYAN, anchor="mm", stroke_width=5, stroke_fill=BLACK)
    return img

def sc3(t):                                         # the atmosphere keeps going
    k = ease(seg(t, S3, S4))
    R = lerp(680, 820, k); cx, cy, lat0 = 540, 930, 8
    lon_c = LON_STOP
    lon_cl = LON_STOP - OMEGA_AIR * (t - S3)
    dx, dy = shake(t, S3, 12.0, 4)
    img = globe(cx + dx, cy + dy, R, lat0, lon_c, lon_cl)
    draw_wind(img, t, cx + dx, cy + dy, R, lat0, lon_c, 0.4 + 0.6 * ease(seg(t, S3, S3 + 1.5)))
    d = ImageDraw.Draw(img, "RGBA"); tag(d, "hyp"); clock_chip(d, lerp(0.3, 1.8, k))
    if t >= ws(2, 8):
        callout(d, 80, 470, 290, 640, "ATMOSPHERE", "keeps its eastward motion", seg(t, ws(2, 8), ws(2, 8) + 0.3), CYAN)
    if t >= ws(2, 20):
        big(d, W / 2, 300, "WIND: 1,670 km/h", 96, t - ws(2, 20), WHITE, "at the equator, relative to the stopped ground")
    if t >= ws(2, 28):
        kb = ease_out(seg(t, ws(2, 28), ws(2, 28) + 0.6))
        x0, y0, bw = 70, 1140, 940
        d.rounded_rectangle((x0 - 20, y0 - 60, x0 + bw + 20, y0 + 190), 16, fill=(0, 0, 0, 170))
        d.text((x0, y0 - 30), "STRONGEST GUST EVER MEASURED · 408 km/h", font=font(F_MONO, 26), fill=(230, 230, 230), anchor="lm")
        d.rectangle((x0, y0, x0 + bw * 408 / 1670 * kb, y0 + 40), fill=(200, 200, 200))
        d.text((x0, y0 + 80), "THIS SCENARIO, AT THE EQUATOR · 1,670 km/h", font=font(F_MONO, 26), fill=YELLOW, anchor="lm")
        d.rectangle((x0, y0 + 110, x0 + bw * kb, y0 + 150), fill=YELLOW)
    if t >= ws(2, 33) + 0.6:
        d.text((W / 2, 1365), "in 5 s, equatorial air would slide ~2.3 km over the ground", font=font(F_MONO, 26), fill=CYAN, anchor="mm", stroke_width=3, stroke_fill=BLACK)
    return img

def sc4(t):                                         # the oceans keep moving
    k = ease(seg(t, S4, S4 + 1.6))
    R = lerp(820, 1250, k); cx = 540; cy = lerp(930, 900, k); lat0 = lerp(8, 0, k); lon_c = lerp(LON_STOP, -22, k)
    lon_cl = LON_STOP - OMEGA_AIR * (t - S3)
    ksg = ease(seg(t, ws(3, 9) - 0.2, ws(3, 9) + 0.8)) * (0.85 + 0.15 * math.sin(t * 5))
    krc = ease(seg(t, ws(3, 15) - 0.2, ws(3, 15) + 0.8)) * (0.85 + 0.15 * math.sin(t * 5 + 1))
    img = globe(cx, cy, R, lat0, lon_c, lon_cl, surge=ksg, recede=krc, cloud_amt=0.55)
    draw_sea(img, t, cx, cy, R, lat0, lon_c, ease(seg(t, S4 + 0.8, S4 + 1.6)))
    d = ImageDraw.Draw(img, "RGBA"); tag(d, "hyp"); clock_chip(d, lerp(1.8, 3.3, seg(t, S4, S5)))
    d.text((W / 2, 1890 - 34), "coastal effects illustrative · not to scale", font=font(F_MONO, 22), fill=(200, 200, 200), anchor="mm", stroke_width=3, stroke_fill=BLACK)
    if ksg > 0.05:
        x, y, _ = earth.project(9, -15, cx, cy, R, lat0, lon_c)
        callout(d, 560, 470, float(x) - 20, float(y), "WEST-FACING COAST", "water piles up", seg(t, ws(3, 9), ws(3, 9) + 0.3), CYAN)
    if krc > 0.05:
        x, y, _ = earth.project(-6, -35.2, cx, cy, R, lat0, lon_c)
        callout(d, 60, 1240, float(x) + 10, float(y), "EAST-FACING COAST", "water pulls away", seg(t, ws(3, 15), ws(3, 15) + 0.3), ORANGE, "lt")
    if t >= ws(3, 17):
        big(d, W / 2, 300, "HOW HIGH?  UNCERTAIN", 80, t - ws(3, 17), YELLOW, "depends on ocean depth, coastline shape, latitude", WHITE)
    return img

def sc5(t):                                         # inertia: latitude, altitude, how suddenly
    cx, cy, R, lat0 = 540, 900, 520, 8
    lon_cl = LON_STOP - OMEGA_AIR * (t - S3)
    img = globe(cx, cy, R, lat0, LON_STOP, lon_cl)
    img = Image.blend(img, Image.new("RGB", (W, H), (0, 0, 0)), 0.35 * ease(seg(t, S5, S5 + 0.5)))
    d = ImageDraw.Draw(img, "RGBA"); tag(d, "diag"); clock_chip(d, lerp(3.3, 4.8, seg(t, S5, S6)))
    if t >= ws(4, 1):
        big(d, W / 2, 290, "INERTIA", 120, t - ws(4, 1), YELLOW, "things keep moving unless a force stops them", WHITE)
    if t >= ws(4, 10) and t < ws(4, 22) + 0.3:
        for i, (la, txt) in enumerate(((0, "1,670"), (30, "1,450"), (-30, "1,450"), (60, "835"), (-60, "835"), (80, "290"))):
            kk = ease_out(seg(t, ws(4, 10) + 0.12 * i, ws(4, 10) + 0.12 * i + 0.35))
            x, y, vis = earth.project(la, LON_STOP - 25, cx, cy, R, lat0, LON_STOP)
            if not vis or kk <= 0: continue
            L = 300 * math.cos(math.radians(la)) * kk
            arrow(d, float(x), float(y), float(x) + max(8, L), float(y), YELLOW if la == 0 else WHITE, 9, 26)
            d.text((float(x) + max(8, L) + 30, float(y)), f"{txt} km/h", font=font(F_MONO, 28), fill=WHITE, anchor="lm", stroke_width=4, stroke_fill=BLACK)
    if t >= ws(4, 22) and t < ws(4, 30) + 0.2:      # altitude: friction slows the lowest air first
        kk = ease_out(seg(t, ws(4, 22), ws(4, 22) + 0.4))
        x0, y0 = 120, 1000
        d.rounded_rectangle((x0 - 30, y0 - 330, x0 + 870, y0 + 70), 18, fill=(0, 0, 0, 200))
        d.text((x0, y0 - 300), "ALTITUDE", font=font(F_UI, 40), fill=WHITE, anchor="lt")
        d.line((x0, y0, x0 + 820, y0), fill=(150, 110, 70), width=10)
        d.text((x0 + 820, y0 + 14), "ground (stopped)", font=font(F_MONO, 24), fill=(200, 170, 130), anchor="rt")
        for j in range(5):
            yy = y0 - 40 - j * 52
            L = (120 + 150 * j) * kk
            arrow(d, x0 + 20, yy, x0 + 20 + L, yy, CYAN, 7, 20)
        d.text((x0 + 830, y0 - 250), "faster aloft", font=font(F_MONO, 26), fill=CYAN, anchor="rm")
        d.text((x0 + 830, y0 - 40), "slowed by friction", font=font(F_MONO, 26), fill=CYAN, anchor="rm")
    if t >= ws(4, 30):                               # how suddenly: same speed change, very different accelerations
        kk = ease_out(seg(t, ws(4, 30), ws(4, 30) + 0.4))
        x0, y0 = 70, 980
        d.rounded_rectangle((x0 - 20, y0 - 90, x0 + 960, y0 + 250), 18, fill=(0, 0, 0, 210))
        d.text((x0, y0 - 60), "HOW SUDDENLY? (equator, 464 m/s)", font=font(F_UI, 40), fill=WHITE, anchor="lt")
        d.text((x0, y0 + 20), "stop in 1 second", font=font(F_MONO, 30), fill=(255, 140, 120), anchor="lt")
        d.text((x0 + 940, y0 + 20), "~47 g", font=font(F_CAP, 54), fill=RED, anchor="rt")
        d.text((x0, y0 + 100), "stop over 1 hour", font=font(F_MONO, 30), fill=(160, 240, 170), anchor="lt")
        d.text((x0 + 940, y0 + 100), "~0.013 g", font=font(F_CAP, 54), fill=GREEN, anchor="rt")
        d.text((x0, y0 + 190), "real Earth: days lengthen ~2 ms per century", font=font(F_MONO, 26), fill=(200, 200, 200), anchor="lt")
    return img

def sc6(t):                                         # the surface lurches back into motion
    cx, cy, lat0 = 540, 930, 10
    R = lerp(620, 520, ease(seg(t, S6, S7)))
    lon_c = LON_STOP if t < T_RESTART else lon_spin(t, T_RESTART, LON_STOP)
    lon_cl = LON_STOP - OMEGA_AIR * (t - S3) if t < T_RESTART else (LON_STOP - OMEGA_AIR * (T_RESTART - S3)) - OMEGA * (t - T_RESTART)
    dx, dy = shake(t, T_RESTART, 0.6, 30)
    img = globe(cx + dx, cy + dy, R, lat0, lon_c, lon_cl)
    if T_RESTART <= t < T_RESTART + 0.08: img = Image.blend(img, Image.new("RGB", (W, H), WHITE), 0.75)
    d = ImageDraw.Draw(img, "RGBA"); tag(d, "hyp")
    if t < T_RESTART: clock_chip(d, lerp(4.8, 5.0, seg(t, S6, T_RESTART)))
    else:
        d.rounded_rectangle((36, 118, 560, 170), 10, fill=(200, 120, 0, 230))
        d.text((56, 144), "RESTART  t = 5.0 s", font=font(F_MONO, 30), fill=WHITE, anchor="lm")
        big(d, W / 2, 300, "ANOTHER JOLT", 104, t - T_RESTART, (255, 140, 90), "the ground snaps back to full speed")
    if t >= ws(5, 18):
        kk = ease_out(seg(t, ws(5, 18), ws(5, 18) + 0.4))
        y0 = 1270
        arrow(d, 260, y0, 260 + 380 * kk, y0, YELLOW, 12, 34)
        d.text((240, y0), "ground", font=font(F_MONO, 30), fill=YELLOW, anchor="rm", stroke_width=4, stroke_fill=BLACK)
        arrow(d, 260, y0 + 70, 260 + 230 * kk, y0 + 70, CYAN, 12, 34)
        d.text((240, y0 + 70), "air, sea", font=font(F_MONO, 30), fill=CYAN, anchor="rm", stroke_width=4, stroke_fill=BLACK)
        d.text((700, y0 + 35), "out of step", font=font(F_UI, 44), fill=WHITE, anchor="lm", stroke_width=5, stroke_fill=BLACK)
    return img

LOOP_LON0 = lon_spin(0.0, T_STOP, LON_STOP)          # opening frame's centre longitude
def sc7(t):                                         # payoff; ends on the opening framing for a clean loop
    k = ease(seg(t, S7, DUR))
    R = lerp(520, 470, k); cx, cy, lat0 = 540, 930, 10
    lon_c = LOOP_LON0 + OMEGA * (DUR - t)            # arrives exactly at the opening longitude at t = DUR
    img = globe(cx, cy, R, lat0, lon_c, lon_c)
    d = ImageDraw.Draw(img, "RGBA"); tag(d, "vis")
    if t >= ws(6, 9):
        age = t - ws(6, 9)
        d.text((W / 2, 230), "HOW YOU STOP", font=font(F_CAP, 104 * (1 + 0.3 * max(0, 1 - age / 0.14))), fill=YELLOW, anchor="mm", stroke_width=10, stroke_fill=BLACK)
        if t >= ws(6, 12):
            d.text((W / 2, 340), "MATTERS MORE THAN HOW LONG", font=font(F_CAP, 60), fill=WHITE, anchor="mm", stroke_width=8, stroke_fill=BLACK)
    elif t >= ws(6, 0):
        d.text((W / 2, 260), "5 SECONDS", font=font(F_CAP, 110), fill=WHITE, anchor="mm", stroke_width=10, stroke_fill=BLACK)
    return img

SCENES = [(S1, S2, sc1), (S2, S3, sc2), (S3, S4, sc3), (S4, S5, sc4), (S5, S6, sc5), (S6, S7, sc6), (S7, DUR + 1, sc7)]

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1 - 0.35 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) ** 1.6).clip(0.45, 1)[..., None]
GR = np.random.default_rng(3)
GRAIN = [GR.normal(0, 3.5, (H // 2, W // 2, 1)).astype(np.float32).repeat(2, 0).repeat(2, 1) for _ in range(4)]

def frame(fi):
    t = fi / FPS
    for a, b, fn in SCENES:
        if a <= t < b:
            img = fn(t); break
    for a, b, fn in SCENES[1:]:                      # 2-frame light leak at each cut
        if 0 <= t - a < 0.067:
            img = Image.blend(img, Image.new("RGB", (W, H), (255, 245, 230)), 0.3 * (1 - (t - a) / 0.067))
    arr = np.asarray(img.convert("RGB"), np.float32) * VIG + GRAIN[fi % 4]
    img = Image.fromarray(arr.clip(0, 255).astype(np.uint8))
    draw_caption(img, t)
    return img.tobytes()

def render_video(out, preview=None):
    if preview:
        import os; os.makedirs("pv", exist_ok=True)
        for t in preview:
            Image.frombytes("RGB", (W, H), frame(int(round(t * FPS)))).resize((270, 480)).save(f"pv/p_{int(t * 100):05d}.jpg", quality=82)
        return
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for i, b in enumerate(pool.imap(frame, range(NF), chunksize=3)):
            p.stdin.write(b)
            if i % 150 == 0: print("frame", i, "/", NF, flush=True)
    p.stdin.close(); p.wait()

# ------------------------------------------------------------------ audio
arng = np.random.default_rng(42)
def bp(x, lo, hi): return sosfilt(butter(2, [lo, hi], btype="band", fs=SR, output="sos"), x)
def lp(x, hi, o=2): return sosfilt(butter(o, hi, btype="low", fs=SR, output="sos"), x)
def hp(x, lo): return sosfilt(butter(2, lo, btype="high", fs=SR, output="sos"), x)
def envx(n, tau): return np.exp(-np.arange(n) / (tau * SR))
def place(buf, sig, t0, g=1.0):
    i = int(t0 * SR)
    if i < 0: sig, i = sig[-i:], 0
    j = min(len(buf), i + len(sig))
    if j > i: buf[i:j] += sig[:j - i] * g
def osc(freq, n, kind="saw"):
    ph = np.cumsum(np.broadcast_to(freq, (n,)) / SR) % 1.0
    return 2 * ph - 1 if kind == "saw" else np.sin(2 * np.pi * ph)
def boom(dur=2.0, f0=90, f1=28, tau=0.6):
    n = int(dur * SR); tt = np.arange(n) / SR
    s = osc(f1 + (f0 - f1) * np.exp(-tt / 0.09), n, "sin") * envx(n, tau)
    return np.tanh((s + lp(arng.normal(0, 1, n), 2500) * envx(n, 0.02) * 0.5) * 1.6)
def crack(dur=0.6):
    n = int(dur * SR); return hp(arng.normal(0, 1, n), 1200) * envx(n, 0.05) * 0.9
def whoosh(dur=0.6):
    n = int(dur * SR); x = arng.normal(0, 1, n); out = np.zeros(n)
    for s in range(12):
        a, b = s * n // 12, (s + 1) * n // 12; fc = 250 + 3000 * s / 12
        out[a:b] = bp(x, fc * 0.6, fc * 1.5)[a:b]
    return out * np.hanning(n)
def tick(f=1500): n = int(0.05 * SR); return osc(f, n, "sin") * envx(n, 0.008)
def riser(dur, f0=90):
    n = int(dur * SR); tt = np.arange(n) / SR
    return (osc(f0 * 2 ** (2.5 * tt / dur), n, "sin") * 0.4 + bp(arng.normal(0, 1, n), 800, 7000) * 0.3 * tt / dur) * (tt / dur) ** 2
def groan(dur=1.6):
    n = int(dur * SR); tt = np.arange(n) / SR
    f = 120 * np.exp(-tt / 0.8) + 32
    return lp(osc(f * (1 + 0.03 * np.sin(2 * np.pi * 9 * tt)), n), 700) * np.minimum(1, tt / 0.05) * np.minimum(1, (dur - tt) / 0.3)
def wind(dur, gust=0.35):
    """Howling wind: band-passed noise with slow gusts and a moving whistle."""
    n = int(dur * SR); tt = np.arange(n) / SR
    x = arng.normal(0, 1, n)
    body = lp(x, 900) * 0.9 + bp(x, 900, 3500) * 0.35
    g = 0.6 + gust * np.sin(2 * np.pi * 0.31 * tt) + 0.25 * np.sin(2 * np.pi * 0.83 * tt + 1)
    whistle = osc(700 + 250 * np.sin(2 * np.pi * 0.2 * tt), n, "sin") * 0.04 * (g > 0.9)
    return (body * g + whistle) * np.minimum(1, tt / 0.6) * np.minimum(1, (dur - tt) / 0.6)
def surf(dur):
    n = int(dur * SR); tt = np.arange(n) / SR
    x = lp(arng.normal(0, 1, n), 400) * 1.6
    sw = 0.5 + 0.5 * np.sin(2 * np.pi * 0.25 * tt) ** 2
    return x * sw * np.minimum(1, tt / 0.8) * np.minimum(1, (dur - tt) / 0.8)
def reverb(x, dur=3.0, mix=0.4):
    n = int(dur * SR); ir = lp(arng.normal(0, 1, n), 5000) * envx(n, dur / 5); ir /= np.abs(ir).sum() / 8
    wet = np.convolve(x, ir); out = np.zeros(len(wet)); out[:len(x)] += x * (1 - mix); out += wet * mix
    return out

def score(n):
    tt = np.arange(n) / SR
    chords = [(0, [82.41, 123.47, 196.0, 164.81]), (S3, [73.42, 110.0, 174.61, 146.83]),     # Em -> Dm
              (S5, [65.41, 98.0, 155.56, 130.81]), (S6, [61.74, 92.5, 146.83, 123.47]),     # Cm -> Bm-ish (tension)
              (S7, [82.41, 123.47, 196.0, 164.81])]                                          # back to Em (loop)
    pad = np.zeros(n)
    for ci, (t0, notes) in enumerate(chords):
        t1 = chords[ci + 1][0] if ci + 1 < len(chords) else DUR
        i0, i1 = int(t0 * SR), min(n, int(t1 * SR) + int(0.8 * SR)); m = i1 - i0
        sg = np.zeros(m)
        for f in notes:
            for det in (-0.12, 0.0, 0.11): sg += osc(f * 2 ** (det / 12), m)
        e = np.minimum(1, np.arange(m) / (0.8 * SR)) * np.minimum(1, (m - np.arange(m)) / (0.8 * SR))
        pad[i0:i1] += sg * e / 12
    pad = lp(pad, 1200) * 0.7 + lp(pad, 400) * 0.6
    sub = osc(41.2, n, "sin") * 0.3
    pulse = np.zeros(n); t = 0.0
    while t < DUR:
        bpm = 66 if t < S3 else (84 if t < S5 else (70 if t < S6 else 60))
        if not (T_STOP - 0.05 < t < ws(0, 6) + 0.2 or we(5, 25) < t < S7):
            place(pulse, boom(0.5, 70, 42, 0.12), t, 0.5); place(pulse, boom(0.4, 60, 40, 0.1), t + 0.22, 0.3)
        t += 60 / bpm
    lvl = np.interp(tt, [0, T_STOP - 0.02, T_STOP + 0.02, ws(0, 6) + 0.1, ws(0, 6) + 0.8, S3, S5, S6, we(5, 25), we(5, 25) + 0.3, S7 - 0.2, S7 + 1.0, DUR],
                    [0.85, 0.9, 0.0, 0.0, 0.8, 0.9, 0.75, 0.85, 0.9, 0.15, 0.15, 1.0, 0.85])
    return (pad + sub + pulse) * lvl

def render_audio(out):
    n = int(DUR * SR)
    mus = score(n); fx = np.zeros(n)
    place(fx, whoosh(1.0), 0.0, 0.3)
    place(fx, reverb(boom(2.6, 100, 24, 0.8), 3.0, 0.4), T_STOP, 1.0); place(fx, crack(), T_STOP, 0.7)   # the stop
    place(fx, wind(3.0, 0.15) * 0.25, T_STOP + 0.6, 0.4)                       # faint: air still moving
    place(fx, whoosh(0.7), S2 - 0.3, 0.35); place(fx, tick(1300), ws(1, 7), 0.4)
    place(fx, reverb(boom(1.4, 80, 34, 0.35)), ws(1, 10), 0.65); place(fx, tick(1100), ws(1, 18), 0.4)
    place(fx, riser(1.2), S3 - 1.2, 0.4)
    place(fx, wind(S4 - S3 + 0.6), S3, 1.0)                                    # the atmosphere keeps going
    place(fx, wind(S6 - S4, 0.2) * 0.35, S4, 0.8)                               # wind continues, lower
    place(fx, reverb(boom(1.6, 85, 32, 0.45)), ws(2, 20), 0.75); place(fx, tick(1600), ws(2, 28), 0.45)
    place(fx, whoosh(0.9), S4 - 0.2, 0.4)
    place(fx, surf(S5 - S4), S4, 0.9)                                           # ocean surge bed
    place(fx, reverb(boom(1.4, 60, 28, 0.6)), ws(3, 9), 0.7); place(fx, reverb(boom(1.2, 55, 28, 0.5)), ws(3, 15), 0.55)
    place(fx, reverb(boom(1.6, 80, 32, 0.45)), ws(3, 17), 0.6)
    place(fx, reverb(boom(1.6, 90, 34, 0.4)), ws(4, 1), 0.8)                     # "Inertia"
    for i in range(6): place(fx, tick(1000 + 110 * i), ws(4, 10) + 0.12 * i, 0.35)
    place(fx, tick(900), ws(4, 22), 0.4); place(fx, tick(1400), ws(4, 30), 0.45)
    place(fx, riser(T_RESTART - S6), S6, 0.45)
    place(fx, reverb(boom(2.8, 110, 22, 0.9), 3.5, 0.45), T_RESTART, 1.0); place(fx, groan(), T_RESTART, 0.6); place(fx, crack(), T_RESTART, 0.6)
    place(fx, reverb(boom(2.4, 70, 24, 0.9), 3.0, 0.5), we(5, 25) + 0.2, 0.55)    # held moment before the payoff
    place(fx, reverb(boom(2.2, 85, 28, 0.7), 3.0, 0.45), ws(6, 9), 0.8)
    place(fx, whoosh(1.4), DUR - 1.4, 0.3)
    vo = np.zeros(n)
    for l in TIM:
        s, _ = sf.read(l["file"]); place(vo, s, l["start"])
    vo = lp(hp(vo, 85), 13000); vo = vo / (np.abs(vo).max() + 1e-9) * 0.9
    env = lp(np.abs(vo), 7); env /= env.max() + 1e-9
    duck = 1 - 0.6 * np.clip(env * 3, 0, 1)
    mix = vo + mus * 0.11 * duck + fx * 0.32 * (0.45 + 0.55 * duck)
    mix = np.tanh(mix * 1.05) * 0.95
    sf.write(out, np.stack([mix, mix], 1).astype(np.float32), SR, subtype="FLOAT")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        ts = [float(x) for x in sys.argv[2:]] or [0.2, 1.2, 2.0, 4.5, 8.5, 11.0, 14.5, 18.5, 23.5, 28.2, 31.0, 34.0, 38.0,
                                                    42.0, 46.0, 49.5, 52.0, 55.0, 57.0, 61.0, 63.5, 67.5, 69.95]
        render_video(None, ts)
    else:
        render_audio("mix.wav"); print("audio done", flush=True)
        render_video("video.mp4"); print("video done", flush=True)
