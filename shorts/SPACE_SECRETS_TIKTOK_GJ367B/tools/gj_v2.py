#!/usr/bin/env python3
# SPACE SECRETS — "Three Years in One Day" (GJ 367 b), vertical 1080x1920, 30 fps. Retention System V3 + agent pipeline.
import json, math, os, re, subprocess, sys
from multiprocessing import Pool

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

import earth, star
from sfx import SR, lp, hp, bp, envx, place, osc, boom, crack, whoosh, tick, riser, reverb, arng

W, H, FPS = 1080, 1920, 30
star.W, star.H = W, H
TIM = json.load(open("timing.json"))
NARR_END = TIM[-1]["start"] + TIM[-1]["dur"]
DUR = round(NARR_END + 2.6, 1)
NF = int(DUR * FPS)
def ls(i): return TIM[i]["start"]
def le(i): return TIM[i]["start"] + TIM[i]["dur"]
def ws(i, k): return TIM[i]["words"][min(k, len(TIM[i]["words"]) - 1)][1]

P_H = 7.7                                     # orbital period, hours (Lam et al. 2021)
HOOK_T = 2.5                                  # the hook animates 24 Earth hours in 2.5 s -> 3 orbits
HOOK_END = 3.0                                # hook scene + hook caption hold until all 3 laps have landed
VARIANT = os.environ.get("HOOK", "A")

def clamp(v, a, b): return max(a, min(b, v))
def seg(t, a, b): return clamp((t - a) / (b - a), 0.0, 1.0) if b > a else float(t >= a)
def ease(x): x = clamp(x, 0, 1); return x * x * (3 - 2 * x)
def ease_out(x): x = clamp(x, 0, 1); return 1 - (1 - x) ** 3
def ease_back(x): x = clamp(x, 0, 1); c = 1.7; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2
def lerp(a, b, k): return a + (b - a) * k

F_CAP = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
F_UI = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
F_MONO = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf"
_F = {}
def font(p, s):
    k = (p, int(s))
    if k not in _F: _F[k] = ImageFont.truetype(p, max(1, int(s)))
    return _F[k]
WHITE, YELLOW, BLACK, CYAN, ORANGE, RED, GREEN = (255, 255, 255), (255, 212, 0), (0, 0, 0), (120, 210, 255), (255, 150, 70), (240, 80, 60), (110, 230, 150)
IRON = (190, 195, 205)
SAFE_CX = 510

_C = {}
def cache(k, fn):
    if k not in _C: _C[k] = fn()
    return _C[k]

def stars():
    def make():
        rng = np.random.default_rng(367)
        a = np.zeros((H, W, 3), np.float32) + np.array([4, 4, 9], np.float32)
        y = np.linspace(0, 1, H)[:, None, None]
        a += np.array([10, 3, 4], np.float32) * (1 - y) ** 2                     # faint warm cast from the red dwarf
        n = 3200; ys = rng.integers(0, H, n); xs = rng.integers(0, W, n); b = rng.pareto(2.4, n) * 45 + 18
        np.add.at(a, (ys, xs), np.stack([b, b * 0.96, b * 1.04], -1))
        return np.clip(a, 0, 255)
    return cache("stars", make)

def tone(arr):
    a = np.clip(arr, 0, None) / 255.0
    return np.clip(255 * (1 - np.exp(-a * 1.25)) / (1 - math.exp(-1.25)), 0, 255)

def glow(arr, amt=0.45, thr=150, rad=34):
    small = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
    hi = np.clip(np.asarray(small, np.float32) - thr, 0, None) * 1.8
    bl = np.asarray(Image.fromarray(np.clip(hi, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(rad / 4)).resize((W, H), Image.BILINEAR), np.float32)
    return arr + bl * amt

def finish(arr, g=0.45): return Image.fromarray(np.clip(tone(glow(arr, g)), 0, 255).astype(np.uint8))

def red_dwarf(arr, cx, cy, R, t, flare=0.0):
    lay = star.draw_sun(np.zeros_like(arr), cx, cy, R, t, bright=0.95 + 0.12 * flare, corona=1.0 + 0.7 * flare)
    return arr + lay * np.array([1.0, 0.46, 0.24], np.float32)

def sun_disc(arr, cx, cy, R, t):
    return star.draw_sun(arr, cx, cy, R, t, bright=0.9, corona=0.8)

# ------------------------------------------------------------------ rocky planet (procedural, labelled reconstruction)
_R = {}
def rock_tex():
    if not _R:
        rng = np.random.default_rng(3670)
        def n(sig): a = ndimage.gaussian_filter(rng.normal(0, 1, (512, 1024)).astype(np.float32), sig, mode="wrap"); return a / (a.std() + 1e-6)
        h = n(30) * 0.6 + n(9) * 0.25 + n(3) * 0.08
        alb = 0.32 + 0.06 * n(20) + 0.03 * n(4)
        gy, gx = np.gradient(ndimage.gaussian_filter(h, 1))
        _R.update(alb=alb.astype(np.float32), gx=(gx * 3).astype(np.float32), gy=(gy * 3).astype(np.float32))
    return _R

def rock(arr, cx, cy, R, light=(-0.8, 0.2, 0.55), hot=1.0, lon=0.0, rim=1.0):
    """Dark airless rock lit by the red dwarf; the star-facing side glows with heat (tidally locked)."""
    T = rock_tex()
    x0, x1 = int(max(0, cx - R - 2)), int(min(W, cx + R + 2)); y0, y1 = int(max(0, cy - R - 2)), int(min(H, cy + R + 2))
    if x1 <= x0 or y1 <= y0 or R < 1: return arr
    ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    nx = (xs - cx) / R; ny = (cy - ys) / R; r2 = nx * nx + ny * ny; m = r2 < 1
    if not m.any(): return arr
    L = np.array(light, np.float32); L /= np.linalg.norm(L)
    nxm, nym = nx[m], ny[m]; nzm = np.sqrt(1 - r2[m])
    lat = np.degrees(np.arcsin(np.clip(nym, -1, 1))); lo = np.degrees(np.arctan2(nxm, nzm)) + lon
    v = (90 - lat) / 180 * 511; u = ((lo + 180) % 360) / 360 * 1023
    smp = lambda a: ndimage.map_coordinates(a, [v, u], order=1, mode="wrap")
    alb = smp(T["alb"]); gx = smp(T["gx"]); gy = smp(T["gy"])
    pnx, pny, pnz = nxm - gx, nym + gy, nzm
    nn = np.sqrt(pnx ** 2 + pny ** 2 + pnz ** 2)
    ndl = (pnx * L[0] + pny * L[1] + pnz * L[2]) / nn
    diff = np.clip(ndl, 0, 1)
    c = (alb * diff * 240)[:, None] * np.array([1.0, 0.62, 0.45], np.float32)          # red-dwarf light
    heat = np.clip((nxm * L[0] + nym * L[1] + nzm * L[2]), 0, 1) ** 2.2 * hot
    c += heat[:, None] * np.array([255, 105, 35], np.float32) * (0.55 + 0.45 * alb[:, None] / 0.32)
    c += ((1 - nzm) ** 3 * diff * rim)[:, None] * np.array([120, 60, 40], np.float32)
    edge = np.clip((1 - np.sqrt(r2[m])) * R / 1.2, 0, 1)[:, None]
    sub = arr[y0:y1, x0:x1]
    sub[m] = sub[m] * (1 - edge) + c * edge
    arr[y0:y1, x0:x1] = sub
    return arr

# ------------------------------------------------------------------ overlays
def tag(d, txt="SCIENTIFIC RECONSTRUCTION  ·  not a photograph", col=ORANGE):
    f = font(F_MONO, 22)
    d.rounded_rectangle((60, 196, 60 + f.getlength(txt) + 28, 236), 10, fill=(0, 0, 0, 150))
    d.ellipse((72, 210, 84, 222), fill=col)
    d.text((94, 216), txt, font=f, fill=(230, 230, 230), anchor="lm")

def pop(d, x, y, txt, size, age, color=WHITE, sw=10, a=255):
    if age < 0: return
    s = size * (1 + 0.3 * max(0, 1 - age / 0.14))
    d.text((x, y), txt, font=font(F_CAP, s), fill=color + (a,), anchor="mm", stroke_width=sw, stroke_fill=BLACK)

def sub(d, x, y, txt, color=(225, 225, 225), size=29, a=255, anchor="mm"):
    d.text((x, y), txt, font=font(F_MONO, size), fill=color + (a,), anchor=anchor, stroke_width=4, stroke_fill=BLACK)

def chip(d, x, y, title, body, k, color=ORANGE, w=None):
    if k <= 0: return
    a = int(255 * k); dx = 40 * (1 - ease_out(k))
    f1, f2 = font(F_UI, 36), font(F_MONO, 24)
    w = w or max(f1.getlength(title), f2.getlength(body)) + 50
    d.rounded_rectangle((x + dx, y, x + dx + w, y + 104), 16, fill=(0, 0, 0, int(190 * k)), outline=color + (a,), width=3)
    d.text((x + dx + 25, y + 32), title, font=f1, fill=color + (a,), anchor="lm")
    d.text((x + dx + 25, y + 76), body, font=f2, fill=(235, 235, 235, a), anchor="lm")

def clock(d, cx, cy, r, hours, label="EARTH TIME", col=CYAN, arcs=None):
    d.ellipse((cx - r - 8, cy - r - 8, cx + r + 8, cy + r + 8), fill=(0, 0, 0, 170))
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=col + (255,), width=6)
    if arcs:
        for i, (h0, h1, c) in enumerate(arcs):
            if h1 > h0: d.arc((cx - r + 14, cy - r + 14, cx + r - 14, cy + r - 14), -90 + h0 / 24 * 360, -90 + h1 / 24 * 360, fill=c, width=22)
    for k in range(24):
        a = k / 24 * 2 * math.pi; r0 = r * (0.82 if k % 6 == 0 else 0.9)
        d.line((cx + r0 * math.sin(a), cy - r0 * math.cos(a), cx + r * 0.97 * math.sin(a), cy - r * 0.97 * math.cos(a)), fill=(255, 255, 255, 200), width=4 if k % 6 == 0 else 2)
    a = hours / 24 * 2 * math.pi
    d.line((cx, cy, cx + r * 0.78 * math.sin(a), cy - r * 0.78 * math.cos(a)), fill=YELLOW, width=8)
    d.ellipse((cx - 10, cy - 10, cx + 10, cy + 10), fill=YELLOW)
    hh = int(hours) % 25; mm = int((hours % 1) * 60)
    d.text((cx, cy + r + 46), f"{hh:02d}:{mm:02d}", font=font(F_CAP, 58), fill=WHITE, anchor="mm", stroke_width=6, stroke_fill=BLACK)
    d.text((cx, cy + r + 100), label, font=font(F_MONO, 24), fill=col, anchor="mm")

# ------------------------------------------------------------------ captions (series identity, safe area)
EMPH = {"THREE", "YEARS", "DAY!", "BIRTHDAY", "7.7", "HOURS", "NEVER", "WHY?", "EARTH,", "GJ", "367", "B.", "31", "LIGHT-YEARS", "SMALLER",
        "RED", "DWARF,", "HUNDREDTH", "SHORT.", "TIDALLY", "LOCKED,", "2,700", "°F.", "MELT", "MYSTERY", "IRON.", "JUNE", "2026,", "50", "70",
        "PERCENT", "ONE-THIRD", "MERCURY.", "RECONSTRUCTION,", "STARLIGHT.", "ONE", "ORDINARY", "ENTIRE", "YEARS."}
CAPS = []
for l in TIM:
    toks = []; prev = -1
    for w, s, e in l["words"]:
        s = max(s, prev + 0.08); prev = s; toks.append((w.upper(), s, e))
    merged = []                                                                    # keep "GJ 367 b" and "7.7 HOURS" in one caption
    for w, s, e in toks:
        if merged and (merged[-1][0] in ("GJ", "GJ 367") or re.fullmatch(r"[\d.,]+", merged[-1][0].split()[-1]) or merged[-1][0].endswith(" TO")) and not re.search(r"[,.:?!]$", merged[-1][0]):
            pw, ps, pe = merged.pop(); w = pw + " " + w; s = ps
        merged.append((w, s, e))
    toks = [(w.replace("GJ 367 B", "GJ 367 b"), s, e) for w, s, e in merged]
    chunk = []
    for i, tk in enumerate(toks):
        chunk.append(tk)
        if re.search(r"[,.:?!]$", tk[0]) or len(chunk) == 3 or i == len(toks) - 1:
            CAPS.append(chunk); chunk = []
CAPS = [(ch[0][1], (CAPS[i + 1][0][1] if i + 1 < len(CAPS) and CAPS[i + 1][0][1] - ch[-1][2] < 0.6 else ch[-1][2] + 0.4), ch) for i, ch in enumerate(CAPS)]

CAP_START = ls(1) - 0.02

def draw_caption(img, t, y=1390):
    if t < CAP_START: return
    if t < HOOK_END: y = 1462                                                      # below the hook's 24 h clock
    d = ImageDraw.Draw(img)
    for a, b, ch in CAPS:
        if not (a <= t < b): continue
        vis = [x for x in ch if x[1] <= t + 0.02]
        if not vis: return
        base, gap, maxw = 92, 22, 860
        items = []
        for w, s, e in vis:
            sz = base * (1 + 0.25 * max(0, 1 - (t - s) / 0.11)); fw = font(F_CAP, sz).getlength(w)
            if fw > maxw: sz *= maxw / fw; fw = maxw
            items.append((w, sz, any(p in EMPH for p in w.split()), fw))
        rows, cur, cw = [], [], 0
        for it in items:
            if cur and cw + gap + it[3] > maxw: rows.append(cur); cur, cw = [], 0
            cur.append(it); cw += (gap if len(cur) > 1 else 0) + it[3]
        rows.append(cur); rows = rows[-2:]
        lh = int(base * 1.1); y0 = y - (len(rows) - 1) * lh / 2
        for ri, row in enumerate(rows):
            tw = sum(x[3] for x in row) + gap * (len(row) - 1); x = SAFE_CX - tw / 2
            for w, sz, em, fw in row:
                d.text((x, y0 + ri * lh), w, font=font(F_CAP, sz), fill=YELLOW if em else WHITE, anchor="lm", stroke_width=10, stroke_fill=BLACK)
                x += fw + gap
        return

# ------------------------------------------------------------------ orbit view (true proportion: a ≈ 3.35 stellar radii)
def orbit_view(t, hours, cx=540, cy=620, Rs=105, tilt=0.30, planet_px=26, flare=0.0, trail=True, base=None, marker=False):
    a_ = Rs * 3.35; b_ = a_ * tilt
    ang = 2 * math.pi * hours / P_H + 0.4
    px, py = cx + a_ * math.cos(ang), cy + b_ * math.sin(ang)
    behind = math.sin(ang) < 0
    arr = stars().copy() if base is None else base
    L = (cx - px, -(cy - py), 0.0); n = math.hypot(L[0], L[1]) + 1e-6; light = (L[0] / n, L[1] / n, 0.35)
    if behind: arr = rock(arr, px, py, planet_px, light=light, hot=1.0)
    arr = red_dwarf(arr, cx, cy, Rs, t, flare)
    if not behind: arr = rock(arr, px, py, planet_px, light=light, hot=1.0)
    img = finish(arr, 0.55); d = ImageDraw.Draw(img, "RGBA")
    for i in range(0, 360, 5):
        d.arc((cx - a_, cy - b_, cx + a_, cy + b_), i, i + 2.5, fill=(255, 210, 180, 70), width=2)
    if trail:
        for j in range(1, 18):
            aj = ang - j * 0.06
            x, y = cx + a_ * math.cos(aj), cy + b_ * math.sin(aj)
            if math.sin(aj) < 0 and (x - cx) ** 2 + (y - cy) ** 2 < Rs * Rs: continue
            d.ellipse((x - planet_px * 0.45, y - planet_px * 0.45, x + planet_px * 0.45, y + planet_px * 0.45), fill=(255, 170, 120, int(150 * (1 - j / 18))))
    if marker:                                                                     # tidal lock: the same face always points at the star
        d.line((px, py, px + (cx - px) * 0.18, py + (cy - py) * 0.18), fill=YELLOW, width=5)
    return img, (px, py)

# ------------------------------------------------------------------ scenes
def hook_bg():
    def make():
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        dist = np.hypot(xx - 540, (yy - 620) * 0.8)
        g = 55 * np.exp(-dist / 430) + 21 * np.exp(-dist / 1500)
        return stars() + g[..., None] * np.array([1.0, 0.42, 0.26], np.float32)
    return cache("hookbg", make)

def sc_hook(t):
    hrs = 24 * t / HOOK_T if VARIANT != "B" else P_H * seg(t, 0, HOOK_T)
    flare = max(0.0, 1 - t / 0.25)
    img, (px, py) = orbit_view(t, hrs, flare=flare, base=hook_bg().copy())
    d = ImageDraw.Draw(img, "RGBA")
    if t < 0.4:                                                                   # frame-0 impact shockwave (no white flash)
        rr = 120 + 900 * ease_out(t / 0.4)
        d.ellipse((540 - rr, 620 - rr * 0.6, 540 + rr, 620 + rr * 0.6), outline=(255, 140, 80, int(200 * (1 - t / 0.4))), width=8)
    n_orb = int(hrs / P_H + 1e-6)
    hrs_c = min(hrs, 24.0)
    clock(d, 540, 1070, 150, hrs_c, "ONE EARTH DAY" if VARIANT != "B" else "EARTH TIME", CYAN,
          arcs=[(i * P_H, min(hrs_c, (i + 1) * P_H), (255, 150, 70, 220) if i % 2 == 0 else (255, 212, 0, 220)) for i in range(4)])
    for i in range(3 if VARIANT != "B" else 1):                                  # orbit counters, popping as each lap completes
        x = 360 + i * 180 if VARIANT != "B" else 540
        done = n_orb > i
        age = t - HOOK_T * (i + 1) * P_H / 24 if VARIANT != "B" else t - HOOK_T
        s = 1 + 0.4 * max(0, 1 - age / 0.15) if done and age >= 0 else 1
        r = 40 * s
        d.ellipse((x - r, 860 - r, x + r, 860 + r), fill=(255, 150, 70, 235) if done else (40, 30, 30, 200), outline=WHITE, width=3)
        d.text((x, 860), str(i + 1), font=font(F_CAP, 46 * s), fill=WHITE if done else (150, 150, 150), anchor="mm")
    cap = {"A": ("3 YEARS", "1 EARTH DAY"), "B": ("1 YEAR =", "7.7 HOURS"), "C": ("3 ORBITS", "24 HOURS")}[VARIANT]
    k = max(0.85, ease_back(seg(t, -0.05, 0.12)))
    d.text((SAFE_CX, 300), cap[0], font=font(F_CAP, 124 * k), fill=WHITE, anchor="mm", stroke_width=11, stroke_fill=BLACK)
    d.text((SAFE_CX, 420), cap[1], font=font(F_CAP, 104 * k), fill=YELLOW, anchor="mm", stroke_width=10, stroke_fill=BLACK)
    sub(d, 540, 772, "orbit to scale · planet enlarged", (220, 200, 190), 22)
    return img

def sc_birthday(t, t0, t1):
    k = seg(t, t0, t1)
    hrs = 24 * t0 / HOOK_T + (t - t0) * 2.2
    z = ease(k)                                                                    # slow push-in toward the system
    pr = lerp(44, 54, z)
    img, (px, py) = orbit_view(t, hrs, cx=540, cy=lerp(760, 740, z), Rs=lerp(140, 170, z), planet_px=pr)
    d = ImageDraw.Draw(img, "RGBA"); tag(d)
    sub(d, SAFE_CX, 360, "1 ORBIT = 1 YEAR = 7.7 h", (255, 200, 160), 40)
    if t >= ws(1, 11):                                                             # the "never survive" beat: dayside heat ring
        k = ease_out(seg(t, ws(1, 11), ws(1, 11) + 0.4))
        d.ellipse((px - pr - 30 * k, py - pr - 30 * k, px + pr + 30 * k, py + pr + 30 * k), outline=(255, 90, 40, int(220 * k)), width=5)
        sub(d, clamp(px, 230, 850), py + pr + 70, "~1,500 °C dayside", (255, 170, 130), 28, int(255 * k))
    return img

def sc_earthday(t, t0, t1):
    k = seg(t, t0, t1)
    arr = earth.render(W, H, 540, 560, 260, 20, -60 - 40 * k, -60 - 40 * k, sun=(-0.6, 0.3, 0.75), stars=stars())
    img = finish(arr, 0.3); d = ImageDraw.Draw(img, "RGBA")
    hrs = 24 * ease(seg(t, t0 + 0.2, t1 - 0.3))
    arcs = [(i * P_H, min(hrs, (i + 1) * P_H), c) for i, c in enumerate(((255, 150, 70, 230), (255, 212, 0, 230), (255, 110, 60, 230), (255, 212, 0, 230)))]
    clock(d, 540, 960, 140, hrs, "1 DAY ON EARTH", CYAN, arcs=arcs)
    for i in range(3):
        if hrs >= (i + 1) * P_H:
            pop(d, 200 + i * 340, 1240, f"YEAR {i + 1}", 46, t - (t0 + 0.2 + (t1 - t0 - 0.5) * (i + 1) * P_H / 24), ORANGE, 6)
    tag(d, "ILLUSTRATION  ·  Earth: Solar System Scope (CC BY 4.0)", CYAN)
    return img

def sc_reveal(t, t0, t1):
    k = seg(t, t0, t1)
    arr = stars().copy()
    arr = red_dwarf(arr, 1180, 300, 520, t)                                       # the star looms off-frame right
    R = lerp(330, 380, ease(k))
    arr = rock(arr, 470, 900, R, light=(0.75, 0.45, 0.48), hot=1.0, lon=20 * k)
    img = finish(arr, 0.5); d = ImageDraw.Draw(img, "RGBA"); tag(d)
    if t >= ls(4) - 0.05:
        pop(d, SAFE_CX, 360, "GJ 367 b", 140, t - ls(4) + 0.05, YELLOW, 11)
    if t >= ws(4, 3):
        chip(d, 70, 1150, "REAL EXOPLANET", "~31 light-years away · constellation Vela", seg(t, ws(4, 3), ws(4, 3) + 0.35), ORANGE)
    return img

def sc_size(t, t0, t1):
    k = seg(t, t0, t1)
    arr = earth.render(W, H, 330, 860, 240, 15, -40 - 8 * k, -40, sun=(-0.5, 0.3, 0.8), stars=stars())
    arr = rock(arr, 820, 860 + 240 - 168, 168, light=(-0.6, 0.3, 0.75), hot=0.7)
    img = finish(arr, 0.35); d = ImageDraw.Draw(img, "RGBA"); tag(d)
    sub(d, 330, 1150, "EARTH", (190, 220, 255), 32); sub(d, 820, 1150, "GJ 367 b", (255, 190, 150), 32)
    sub(d, 820, 1195, "~0.7× Earth's width", (240, 210, 190), 26)
    pop(d, SAFE_CX, 340, "SMALLER THAN EARTH", 86, t - ws(5, 3), WHITE, 8) if t >= ws(5, 3) else None
    return img

def sc_stars(t, t0, t1):
    arr = stars().copy()
    arr = sun_disc(arr, 560, 1330, 470, t)
    arr = red_dwarf(arr, 300, 560, 215, t)
    img = finish(arr, 0.4); d = ImageDraw.Draw(img, "RGBA")
    sub(d, 640, 520, "GJ 367: RED DWARF", (255, 170, 140), 30, anchor="lm"); sub(d, 640, 562, "~0.46× the Sun's width", (240, 210, 200), 23, anchor="lm")
    sub(d, 560, 820, "OUR SUN (for scale)", (255, 230, 170), 30)
    if t >= ws(6, 4): pop(d, SAFE_CX, 330, "A RED DWARF", 110, t - ws(6, 4), ORANGE)
    tag(d, "ILLUSTRATION  ·  star sizes to scale", ORANGE)
    return img

def backdrop(t, hot=0.5):
    """Lit planet limb under the diagram so a diagram scene never opens on a near-black frame."""
    arr = stars().copy()
    arr = red_dwarf(arr, 1120, 1500, 260, t)
    return rock(arr, 470, 2380, 900, light=(0.55, 0.75, 0.35), hot=hot)

def sc_distance(t, t0, t1):
    k = seg(t, t0, t1)
    img = finish(backdrop(t), 0.4); d = ImageDraw.Draw(img, "RGBA")
    x0, x1, y = 80, 1000, 760
    d.line((x0, y, x1, y), fill=(190, 220, 255, 230), width=6)
    d.ellipse((x0 - 22, y - 22, x0 + 22, y + 22), fill=(255, 220, 120))
    d.ellipse((x1 - 16, y - 16, x1 + 16, y + 16), fill=(90, 160, 255), outline=WHITE, width=2)
    sub(d, x0 + 10, y - 60, "SUN", (255, 225, 160), 26, anchor="lm"); sub(d, x1, y - 60, "EARTH", (170, 210, 255), 26, anchor="rm")
    sub(d, (x0 + x1) / 2, y + 50, "1 AU ≈ 150 million km", (220, 230, 245), 26)
    q = ease(seg(t, ws(7, 7), ws(7, 7) + 0.8))
    xs = x0 + (x1 - x0) * 0.0071
    if q > 0:
        d.line((x0, y + 140, x0 + max(6, (x1 - x0) * 0.0071), y + 140), fill=(255, 150, 70, int(255 * q)), width=14)
        d.line((x0 + 6, y + 120, x0 + 6, y + 330), fill=(255, 150, 70, int(200 * q)), width=2)
        sub(d, x0 + 30, y + 190, "GJ 367 b's orbit: ~0.007 AU", (255, 190, 140), 30, int(255 * q), "lm")
        sub(d, x0 + 30, y + 235, "less than 1/100 of Earth's distance", (240, 220, 200), 26, int(255 * q), "lm")
    z = ease_out(seg(t, ws(7, 7) + 0.6, ws(7, 7) + 1.2))
    if z > 0:
        bx0, by0, bx1, by1 = 120, 1030, 960, 1250; zc = (540, 1140)
        d.rounded_rectangle((bx0, by0, bx1, by1), 16, fill=(0, 0, 0, int(200 * z)), outline=(255, 150, 70, int(255 * z)), width=3)
        d.line((x0 + 6, y + 330, bx0 + 30, by0), fill=(255, 150, 70, int(160 * z)), width=2)
        ro, rs = 340 * z, 340 * z * 0.0021 / 0.0071                                 # star radius ~0.0021 AU vs orbit 0.0071 AU
        d.arc((zc[0] - ro, zc[1] - ro * 0.3, zc[0] + ro, zc[1] + ro * 0.3), 0, 360, fill=(255, 210, 180, int(200 * z)), width=3)
        d.ellipse((zc[0] - rs, zc[1] - rs, zc[0] + rs, zc[1] + rs), fill=(235, 95, 50, int(255 * z)))
        d.arc((zc[0] - ro, zc[1] - ro * 0.3, zc[0] + ro, zc[1] + ro * 0.3), 0, 180, fill=(255, 220, 190, int(230 * z)), width=3)
        d.ellipse((zc[0] + ro - 9, zc[1] - 9, zc[0] + ro + 9, zc[1] + 9), fill=(200, 140, 110, int(255 * z)))
        sub(d, bx1 - 20, by1 - 24, "orbit ≈ 3.4 star-widths from centre", (240, 220, 200), 22, int(255 * z), "rm")
        sub(d, bx0 + 20, by0 + 26, "ZOOM: GJ 367 system", (255, 190, 140), 24, int(255 * z), "lm")
    if t >= ls(8): pop(d, SAFE_CX, 360, "SO CLOSE, SO FAST", 84, t - ls(8), YELLOW, 8)
    tag(d, "DIAGRAM  ·  distances to scale", (110, 220, 210))
    return img

def sc_locked(t, t0, t1):
    hrs = (t - t0) * 1.3
    img, (px, py) = orbit_view(t, hrs, cx=540, cy=780, Rs=135, planet_px=58, marker=True, trail=False)
    d = ImageDraw.Draw(img, "RGBA"); tag(d)
    if t >= ws(9, 2): pop(d, SAFE_CX, 340, "TIDALLY LOCKED", 108, t - ws(9, 2), ORANGE)
    sub(d, SAFE_CX, 440, "probably: one face always toward its star", (240, 220, 210), 26)
    return img

def sc_heat(t, t0, t1):
    k = seg(t, t0, t1)
    arr = stars().copy()
    arr = red_dwarf(arr, -120, 560, 420, t)
    arr = rock(arr, 640, 930, lerp(420, 470, ease(k)), light=(-0.92, 0.18, 0.35), hot=1.6)
    img = finish(arr, 0.7); d = ImageDraw.Draw(img, "RGBA"); tag(d)
    if t >= ws(10, 4):
        kk = ease_out(seg(t, ws(10, 4), ws(10, 6) + 0.2))
        x, y0, y1 = 110, 1230, 560
        d.rounded_rectangle((x - 24, y1 - 20, x + 24, y0 + 10), 24, fill=(0, 0, 0, 170), outline=(255, 255, 255, 200), width=3)
        d.ellipse((x - 44, y0 - 20, x + 44, y0 + 68), fill=(235, 70, 30), outline=WHITE, width=3)
        top = lerp(y0, y1 + 10, kk)
        d.rounded_rectangle((x - 13, top, x + 13, y0 + 20), 13, fill=(255, int(lerp(170, 70, kk)), 30))
        d.text((x + 46, top), f"~{int(round(2700 * kk, -1)):,}°F", font=font(F_CAP, 60), fill=WHITE, anchor="lm", stroke_width=6, stroke_fill=BLACK)
        if kk >= 1: sub(d, x + 48, top + 56, "≈ 1,500 °C · estimated dayside", (255, 220, 190), 24, anchor="lm")
    if t >= ws(10, 8): pop(d, SAFE_CX, 330, "HOT ENOUGH TO MELT ROCK", 66, t - ws(10, 8), YELLOW, 8)
    return img

def interior(d, cx, cy, R, core_frac, rng_lo=None, rng_hi=None, t=0.0):
    """Cutaway: rocky mantle + iron core; core RADIUS chosen so the core MASS fraction matches (densities ~4.5 / ~11 g/cc)."""
    def core_r(fm):
        rho_m, rho_c = 4.5, 11.0
        x = (fm / rho_c) / (fm / rho_c + (1 - fm) / rho_m)                          # core volume fraction
        return R * x ** (1 / 3)
    d.ellipse((cx - R, cy - R, cx + R, cy + R), fill=(120, 70, 45), outline=(255, 160, 110), width=4)
    d.pieslice((cx - R, cy - R, cx + R, cy + R), -90, 90, fill=(90, 60, 45))
    if rng_lo is not None:
        r_hi, r_lo = core_r(rng_hi), core_r(rng_lo)
        d.ellipse((cx - r_hi, cy - r_hi, cx + r_hi, cy + r_hi), fill=(150, 155, 165, 120), outline=(220, 225, 235), width=3)
        d.ellipse((cx - r_lo, cy - r_lo, cx + r_lo, cy + r_lo), fill=(150, 155, 170), outline=WHITE, width=3)
        d.text((cx, cy - 20), "IRON", font=font(F_CAP, 60), fill=(40, 44, 56), anchor="mm")
        d.text((cx, cy + 34), "50–70%", font=font(F_MONO, 30), fill=(40, 44, 56), anchor="mm")
        d.text((cx, cy - r_hi + 26), "range", font=font(F_MONO, 22), fill=(235, 235, 245), anchor="mm")
        d.text((cx, cy - R + 40), "ROCK", font=font(F_MONO, 26), fill=(255, 200, 160), anchor="mm")
        return r_lo, r_hi
    rc = core_r(core_frac)
    for j in range(12):                                                             # shaded metallic core
        rr = rc * (1 - j / 14); c = int(110 + 9 * j)
        d.ellipse((cx - rr + j * 2, cy - rr - j * 2, cx + rr + j * 2, cy + rr - j * 2), fill=(c, c + 4, c + 16))
    d.ellipse((cx - rc, cy - rc, cx + rc, cy + rc), outline=WHITE, width=3)
    d.text((cx, cy), "IRON", font=font(F_CAP, 64), fill=(40, 44, 56), anchor="mm")
    d.line((cx + R * 0.97, cy - R * 0.25, cx + R + 40, cy - R * 0.55), fill=(255, 190, 150), width=3)
    d.text((cx + R + 44, cy - R * 0.55), "ROCK", font=font(F_MONO, 26), fill=(255, 190, 150), anchor="rb")
    return rc, rc

def sc_old_model(t, t0, t1):
    img = finish(backdrop(t, 0.8), 0.4); d = ImageDraw.Draw(img, "RGBA")
    pop(d, SAFE_CX, 330, "WHAT IS IT MADE OF?", 84, t - t0, WHITE, 8)
    if t >= ls(12) - 0.1:
        g = ease_out(seg(t, ls(12) - 0.1, ls(12) + 0.6))
        interior(d, 540, 820, 300 * g + 1, 0.9)
        if g > 0.9:
            sub(d, 540, 1170, "EARLIER ESTIMATE: up to ~90% iron", (230, 230, 240), 30)
            sub(d, 540, 1215, "(Goffo et al. 2023)", (200, 200, 210), 24)
        if t >= ws(12, 9): pop(d, SAFE_CX, 450, "ALMOST PURE IRON?", 70, t - ws(12, 9), IRON, 8)
    tag(d, "INTERIOR MODEL  ·  illustration, not observed", IRON)
    return img

def sc_update(t, t0, t1):
    img = finish(stars() * 0.8, 0.1); d = ImageDraw.Draw(img, "RGBA")
    flash = max(0.0, 1 - (t - ws(13, 2)) / 0.25) if t >= ws(13, 2) else 0
    chip(d, 70, 300, "NEW RESEARCH · JUNE 22, 2026", "peer-reviewed · revised mass and radius", seg(t, ws(13, 2), ws(13, 2) + 0.35), YELLOW, 900)
    m = ease(seg(t, ls(14) - 0.2, ws(14, 6)))
    if m < 1:
        interior(d, 540, 860, 300, lerp(0.9, 0.6, m))
    else:
        r_lo, r_hi = interior(d, 540, 860, 300, 0.6, 0.5, 0.7)
        sub(d, 540, 1200, "IRON CORE: ~50–70% of the mass", (235, 235, 245), 30)
        sub(d, 540, 1245, "(interior models · not observed directly)", (200, 200, 210), 24)
    if t >= ws(14, 6): pop(d, SAFE_CX, 470, "50–70% IRON", 110, t - ws(14, 6), YELLOW)
    if flash > 0:
        img = Image.blend(img, Image.new("RGB", (W, H), (255, 245, 220)), 0.25 * flash)
        d = ImageDraw.Draw(img, "RGBA")
    tag(d, "INTERIOR MODEL  ·  illustration, not observed", IRON)
    return img

def sc_compare(t, t0, t1):
    img = finish(stars() * 0.8, 0.1); d = ImageDraw.Draw(img, "RGBA")
    pop(d, SAFE_CX, 330, "IRON, BY MASS", 96, t - t0, IRON)
    rows = [("EARTH", 0.32, 0.32, CYAN, ls(15)), ("MERCURY", 0.70, 0.70, (200, 200, 200), ws(16, 13)), ("GJ 367 b", 0.50, 0.70, ORANGE, ls(15) + 0.6)]
    for i, (name, lo, hi, col, cue) in enumerate(rows):
        y = 560 + i * 200; k = ease_out(seg(t, cue, cue + 0.6))
        if k <= 0: continue
        x0, w = 110, 820
        d.text((x0, y - 46), name, font=font(F_UI, 40), fill=col, anchor="lm")
        d.rounded_rectangle((x0, y, x0 + w, y + 70), 12, fill=(30, 30, 40, 200))
        d.rounded_rectangle((x0, y, x0 + w * lo * k, y + 70), 12, fill=col + (230,))
        if hi > lo:
            d.rectangle((x0 + w * lo * k, y, x0 + w * hi * k, y + 70), fill=col + (110,))
        txt = f"~{int(lo * 100)}%" if hi == lo else f"~{int(lo * 100)}–{int(hi * 100)}%"
        d.text((x0 + w * hi * k + 16 if hi < 0.8 else x0 + w - 10, y + 35), txt, font=font(F_CAP, 44), fill=WHITE, anchor="lm" if hi < 0.8 else "rm", stroke_width=5, stroke_fill=BLACK)
    if t >= ws(16, 12): sub(d, SAFE_CX, 1190, "a scorched, oversized cousin of Mercury", (255, 210, 180), 28)
    tag(d, "DIAGRAM  ·  approximate published values", (110, 220, 210))
    return img

def sc_measure(t, t0, t1):
    img = finish(stars() * 0.75, 0.1); d = ImageDraw.Draw(img, "RGBA")
    pop(d, SAFE_CX, 330, "WHAT WE ACTUALLY MEASURE", 64, t - t0, YELLOW, 7)
    k = seg(t, t0 + 0.3, t1 - 0.3)
    gx0, gx1 = 100, 980
    d.text((gx0, 470), "STARLIGHT DIMMING (transit · TESS)", font=font(F_MONO, 25), fill=(255, 200, 160), anchor="lm")
    pts = []
    for i in range(int(300 * k) + 1):
        x = i / 300; ph = (x * 3.0) % 1
        dip = 1 if 0.45 < ph < 0.55 else 0
        pts.append((gx0 + x * (gx1 - gx0), 560 + 60 * dip))
    if len(pts) > 1: d.line(pts, fill=(255, 170, 120), width=5)
    d.text((gx0, 760), "STAR'S WOBBLE (radial velocity · HARPS)", font=font(F_MONO, 25), fill=CYAN, anchor="lm")
    pts = [(gx0 + x * (gx1 - gx0), 880 - 70 * math.sin(2 * math.pi * x * 3)) for x in np.linspace(0, k, int(300 * k) + 2)]
    if len(pts) > 1: d.line(pts, fill=CYAN, width=5)
    sub(d, SAFE_CX, 1060, "→ size + mass → density → interior models", (235, 235, 245), 28)
    if t >= ws(18, 4): pop(d, SAFE_CX, 1180, "RECONSTRUCTION", 84, t - ws(18, 4), ORANGE, 8)
    tag(d, "DIAGRAM  ·  illustrative signals", (110, 220, 210))
    return img

def sc_finale(t, t0):
    hrs = 24 * ease(seg(t, t0 + 0.4, le(20) - 0.2))
    img, (px, py) = orbit_view(t, hrs, cx=540, cy=600, Rs=100, planet_px=26)
    d = ImageDraw.Draw(img, "RGBA")
    x0, x1, y = 90, 990, 1060                                                     # an ordinary Earth day
    segs = [(0, 7, "SLEEP", (70, 90, 160)), (7, 15, "SCHOOL / WORK", (60, 140, 120)), (15, 22, "EVENING", (150, 110, 60)), (22, 24, "SLEEP", (70, 90, 160))]
    for h0, h1, name, col in segs:
        xa, xb = x0 + (x1 - x0) * h0 / 24, x0 + (x1 - x0) * h1 / 24
        d.rectangle((xa, y, xb, y + 60), fill=col + (230,))
        if h1 - h0 > 3: d.text(((xa + xb) / 2, y + 30), name, font=font(F_UI, 24), fill=WHITE, anchor="mm")
    xh = x0 + (x1 - x0) * hrs / 24
    d.line((xh, y - 20, xh, y + 80), fill=YELLOW, width=6)
    for i in range(3):
        xo = x0 + (x1 - x0) * (i + 1) * P_H / 24
        d.line((xo, y - 40, xo, y - 4), fill=ORANGE, width=4)
        if hrs >= (i + 1) * P_H: pop(d, xo, y - 70, f"YEAR {i + 1}", 34, t - (t0 + 0.4), ORANGE, 5)
    sub(d, SAFE_CX, y + 110, "ONE EARTH DAY", CYAN, 28)
    if t >= ws(20, 6): pop(d, SAFE_CX, 330, "3 ENTIRE YEARS", 110, t - ws(20, 6), YELLOW)
    q = ease(seg(t, DUR - 0.6, DUR))
    if q > 0: img = Image.blend(img, sc_hook(0.0), q)                           # loop back to frame 0
    tag(d, "SCIENTIFIC RECONSTRUCTION  ·  orbit to scale, planet enlarged")
    return img

def scenes():
    L = lambda i: ls(i) - 0.1
    return [
        (0.0, HOOK_END, sc_hook),
        (HOOK_END, L(2), lambda t: sc_birthday(t, HOOK_END, L(2))),
        (L(2), L(3), lambda t: sc_earthday(t, L(2), L(3))),
        (L(3), L(5), lambda t: sc_reveal(t, L(3), L(5))),
        (L(5), L(6), lambda t: sc_size(t, L(5), L(6))),
        (L(6), L(7), lambda t: sc_stars(t, L(6), L(7))),
        (L(7), L(9), lambda t: sc_distance(t, L(7), L(9))),
        (L(9), L(10), lambda t: sc_locked(t, L(9), L(10))),
        (L(10), L(11), lambda t: sc_heat(t, L(10), L(11))),
        (L(11), L(13), lambda t: sc_old_model(t, L(11), L(13))),
        (L(13), L(15), lambda t: sc_update(t, L(13), L(15))),
        (L(15), L(17), lambda t: sc_compare(t, L(15), L(17))),
        (L(17), L(19), lambda t: sc_measure(t, L(17), L(19))),
        (L(19), DUR + 1, lambda t: sc_finale(t, L(19))),
    ]
SCENES = scenes()

yy_, xx_ = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1 - 0.3 * (((xx_ - W / 2) / (W / 2)) ** 2 + ((yy_ - H / 2) / (H / 2)) ** 2) ** 1.6).clip(0.5, 1)[..., None]
del yy_, xx_
GRN = np.random.default_rng(3)
GRAIN = [GRN.normal(0, 3.0, (H // 2, W // 2, 1)).astype(np.float32).repeat(2, 0).repeat(2, 1) for _ in range(4)]

def frame(fi):
    t = fi / FPS
    for a, b, fn in SCENES:
        if a <= t < b: img = fn(t); break
    for a, b, fn in SCENES[1:]:                       # soft 2-frame cut light (no random flashing)
        if 0 <= t - a < 0.067: img = Image.blend(img.convert("RGB"), Image.new("RGB", (W, H), (255, 235, 220)), 0.15 * (1 - (t - a) / 0.067))
    arr = np.asarray(img.convert("RGB"), np.float32) * VIG + GRAIN[fi % 4]
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    draw_caption(img, t)
    return img.tobytes()

def render_video(out, preview=None, pdir="pv"):
    if preview:
        os.makedirs(pdir, exist_ok=True)
        for t in preview:
            Image.frombytes("RGB", (W, H), frame(int(round(t * FPS)))).resize((270, 480)).save(f"{pdir}/p_{int(t * 100):05d}.jpg", quality=85)
        return
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for i, b in enumerate(pool.imap(frame, range(NF), chunksize=3)):
            p.stdin.write(b)
            if i % 150 == 0: print("frame", i, "/", NF, flush=True)
    p.stdin.close(); p.wait()

# ------------------------------------------------------------------ audio
def pulse_hit(f=180):
    n = int(0.35 * SR); tt = np.arange(n) / SR
    return (np.sin(2 * np.pi * (f * (1 + 0.8 * np.exp(-tt / 0.03))) * tt) * np.exp(-tt / 0.09) + bp(arng.normal(0, 1, n), 2000, 7000) * np.exp(-tt / 0.02) * 0.3)

def render_audio(out):
    n = int(DUR * SR); tt = np.arange(n) / SR
    chords = [(0, [55.0, 82.41, 130.81, 164.81]), (ls(3), [58.27, 87.31, 138.59, 174.61]), (ls(9), [51.91, 77.78, 123.47, 155.56]),
              (ls(11), [49.0, 73.42, 116.54, 146.83]), (ls(13), [65.41, 98.0, 164.81, 196.0]), (ls(17), [55.0, 82.41, 130.81, 164.81]),
              (ls(19), [65.41, 98.0, 164.81, 196.0])]
    pad = np.zeros(n)
    for ci, (t0, notes) in enumerate(chords):
        t1 = chords[ci + 1][0] if ci + 1 < len(chords) else DUR
        i0, i1 = int(t0 * SR), min(n, int(t1 * SR) + int(0.8 * SR)); m = i1 - i0; sg = np.zeros(m)
        for f in notes:
            for det in (-0.12, 0.0, 0.11): sg += osc(f * 2 ** (det / 12), m)
        e = np.minimum(1, np.arange(m) / (0.8 * SR)) * np.minimum(1, (m - np.arange(m)) / (0.8 * SR))
        pad[i0:i1] += sg * e / 12
    pulse = np.zeros(n); t = ls(3)
    while t < ls(11):
        place(pulse, boom(0.45, 72, 42, 0.11), t, 0.35); place(pulse, boom(0.35, 60, 40, 0.09), t + 0.23, 0.2); t += 60 / 88
    mus = (lp(pad, 1000) * 0.7 + lp(pad, 360) * 0.6 + osc(41.2, n, "sin") * 0.2 + pulse) * np.interp(
        tt, [0, ls(11) - 0.1, ls(11) + 0.4, ws(13, 2) - 0.05, ws(13, 2) + 0.05, ls(15), DUR - 1, DUR], [0.8, 0.85, 0.5, 0.5, 1.0, 0.85, 1.0, 0.7])
    fx = np.zeros(n)
    place(fx, reverb(boom(2.4, 120, 26, 0.8), 3.0, 0.4), 0.0, 1.5)                                      # frame-0 impact
    for i in range(3): place(fx, pulse_hit(200 + 60 * i), HOOK_T * (i + 1) * P_H / 24, 0.9)             # three orbital pulses
    place(fx, whoosh(0.8), 0.0, 0.4)
    for a, b, fn in SCENES[1:]: place(fx, whoosh(0.5), a - 0.15, 0.22)
    place(fx, reverb(boom(1.6, 90, 34, 0.45)), ws(1, 11), 0.6)                                          # "never survive"
    for i in range(3): place(fx, tick(1300 + 200 * i), ls(2) + 0.1 + (ls(3) - ls(2) - 0.5) * (i + 1) * P_H / 24, 0.35)
    place(fx, reverb(boom(2.0, 80, 28, 0.7), 3.0, 0.45), ws(3, 1), 0.8)                                  # "GJ 367 b"
    place(fx, reverb(boom(1.4, 70, 30, 0.5)), ws(10, 4), 0.6)
    m = int((ls(11) - ls(10)) * SR); place(fx, lp(arng.normal(0, 1, m), 180) * 1.5 * np.minimum(1, np.arange(m) / SR / 0.6), ls(10), 0.6)  # heat rumble
    place(fx, riser(1.4, 70) * 0.5, ws(13, 2) - 1.4, 0.4)
    place(fx, reverb(boom(2.6, 110, 24, 0.9), 3.5, 0.5), ws(13, 2), 1.1)                                # 2026 research reveal
    m = int(1.2 * SR); place(fx, sum(np.sin(2 * np.pi * f * np.arange(m) / SR) for f in (1318.5, 1975.5)) / 2 * np.exp(-np.arange(m) / SR / 0.5), ws(13, 2) + 0.05, 0.08)
    place(fx, reverb(boom(1.4, 90, 34, 0.4)), ws(14, 6), 0.6)
    for i in range(3): place(fx, pulse_hit(220 + 50 * i), ls(19) - 0.1 + 0.4 + (le(20) - 0.2 - ls(19) - 0.3) * (i + 1) * P_H / 24, 0.6)
    place(fx, riser(0.6, 140), DUR - 0.6, 0.4)
    vo = np.zeros(n)
    for l in TIM:
        s, _ = sf.read(l["file"]); place(vo, s, l["start"])
    vo = lp(hp(vo, 85), 13000); vo = vo / (np.abs(vo).max() + 1e-9) * 0.9
    env = lp(np.abs(vo), 7); env /= env.max() + 1e-9
    duck = 1 - 0.62 * np.clip(env * 3, 0, 1)
    mix = vo + mus * 0.11 * duck + fx * 0.30 * (0.45 + 0.55 * duck)
    sf.write(out, np.stack([np.tanh(mix * 1.05) * 0.95] * 2, 1).astype(np.float32), SR, subtype="FLOAT")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "preview": render_video(None, [float(x) for x in sys.argv[2:]], os.environ.get("PVDIR", "pv"))
    elif cmd == "hooktest":
        out = os.environ.get("HOOK", "A")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                        "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", f"hook_{out}.mp4"],
                       input=b"".join(frame(i) for i in range(90)), check=True)
    else:
        render_audio("mix.wav"); print("audio done", flush=True)
        render_video("video.mp4"); print("video done", flush=True)
