#!/usr/bin/env python3
# SPACE SECRETS — Short #1 from the Moon documentary: "No Moon = No Tides?" (vertical 1080x1920).
# Script: /yt-script-scored hook (82 STRONG) + documentary lines 38–48. Built under Retention System V3.
import json, math, re, subprocess, sys
from multiprocessing import Pool

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

import earth, moonr, star
from sfx import SR, lp, hp, bp, envx, place, osc, boom, crack, whoosh, tick, riser, reverb, arng

W, H, FPS = 1080, 1920, 30
star.W, star.H = W, H
DOC = json.load(open("../moon/timing.json"))["lines"]

# ------------------------------------------------------------------ timeline: new hook + documentary lines 38-48
HOOK_WORDS = ["Lose", "the", "Moon,", "and", "you", "lose", "about", "2", "of", "every", "3", "feet", "of", "tide.", "But", "why", "not", "all", "of", "it?"]
def build_timing():
    h, sr = sf.read("vo/TH.wav")
    hop = int(0.01 * sr)
    e = np.array([np.sqrt(np.mean(h[i:i + hop] ** 2)) for i in range(0, len(h) - hop, hop)])
    v = np.where(e > 0.02 * e.max())[0]; a, b = v[0], v[-1]
    syl = lambda w: max(1, len(re.findall(r"[aeiouy]+", w.lower()))) + (0.6 if re.search(r"[,.?]$", w) else 0)
    wts = np.array([syl(w if w not in ("2", "3") else "three") for w in HOOK_WORDS], float)
    bnd = a + (b - a) * np.concatenate([[0], np.cumsum(wts) / wts.sum()])
    t0 = 0.05
    lines = [{"file": "vo/TH.wav", "start": t0, "dur": len(h) / sr,
              "words": [(w, round(t0 + bnd[i] * 0.01, 3), round(t0 + bnd[i + 1] * 0.01, 3)) for i, w in enumerate(HOOK_WORDS)]}]
    t = t0 + len(h) / sr + 0.35
    for i in range(38, 49):
        L = DOC[i]; off = t - L["start"]
        lines.append({"file": f"vo/T{i:03d}.wav", "start": round(t, 3), "dur": L["dur"],
                      "words": [(w, round(s + off, 3), round(e + off, 3)) for w, s, e in L["words"]], "doc": i})
        n = len(L["words"])
        t += L["dur"] + (0.45 if n <= 3 else 0.4)
    return lines
TIM = build_timing()
NARR_END = TIM[-1]["start"] + TIM[-1]["dur"]
DUR = round(NARR_END + 1.6, 1)
NF = int(DUR * FPS)
def ls(i): return TIM[i]["start"]                    # i: 0 = hook, 1.. = doc lines 38..48
def ws(i, k): return TIM[i]["words"][min(k, len(TIM[i]["words"]) - 1)][1]
T_VANISH = min(ws(0, 2), 0.45)                        # on "Moon": the visual event lands inside 0.5 s (gate)
HOOK_END = ls(1) - 0.05

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
WHITE, YELLOW, BLACK, CYAN, ORANGE, RED, GREEN = (255, 255, 255), (255, 212, 0), (0, 0, 0), (120, 210, 255), (255, 190, 90), (240, 80, 60), (110, 230, 150)
SAFE_CX = 510

_C = {}
def cache(k, fn):
    if k not in _C: _C[k] = fn()
    return _C[k]

def stars(w=W, h=H, n=3000, seed=8):
    def make():
        rng = np.random.default_rng(seed)
        a = np.zeros((h, w, 3), np.float32) + np.array([3, 6, 14], np.float32)
        ys = rng.integers(0, h, n); xs = rng.integers(0, w, n); b = rng.pareto(2.4, n) * 50 + 20
        np.add.at(a, (ys, xs), np.stack([b, b * 0.97, b * 1.06], -1))
        return np.clip(a, 0, 255)
    return cache(("st", w, h), make)

def tone(arr):
    a = np.clip(arr, 0, None) / 255.0
    return np.clip(255 * (1 - np.exp(-a * 1.25)) / (1 - math.exp(-1.25)), 0, 255)

def glow(arr, amt=0.35, thr=165, rad=30):
    small = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
    hi = np.clip(np.asarray(small, np.float32) - thr, 0, None) * 1.8
    bl = np.asarray(Image.fromarray(np.clip(hi, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(rad / 4)).resize((W, H), Image.BILINEAR), np.float32)
    return arr + bl * amt

def finish(arr, g=0.35): return Image.fromarray(np.clip(tone(glow(arr, g)), 0, 255).astype(np.uint8))

def tag(d, txt, col=CYAN):
    f = font(F_MONO, 23)
    d.rounded_rectangle((60, 196, 60 + f.getlength(txt) + 28, 238), 10, fill=(0, 0, 0, 150))
    d.ellipse((72, 211, 84, 223), fill=col)
    d.text((94, 217), txt, font=f, fill=(230, 230, 230), anchor="lm")

def pop(d, x, y, txt, size, age, color=WHITE, sw=10, a=255):
    if age < 0: return
    s = size * (1 + 0.35 * max(0, 1 - age / 0.14))
    d.text((x, y), txt, font=font(F_CAP, s), fill=color + (a,), anchor="mm", stroke_width=sw, stroke_fill=BLACK)

def sub(d, x, y, txt, color=(225, 225, 225), size=30, a=255):
    d.text((x, y), txt, font=font(F_MONO, size), fill=color + (a,), anchor="mm", stroke_width=4, stroke_fill=BLACK)

def shake(t, t0, dur, amp):
    if not (t0 <= t < t0 + dur): return 0.0, 0.0
    k = 1 - (t - t0) / dur
    return amp * k * math.sin(t * 97), amp * k * math.cos(t * 83)

# ------------------------------------------------------------------ captions (series identity, safe area)
EMPH = {"MOON,", "LOSE", "2", "3", "FEET", "TIDE.", "WHY", "ALL", "FLATTEN", "MOMENTUM.", "COMPLEX", "SHAPES.", "DISAPPEAR.", "NOT",
        "VANISH", "COMPLETELY.", "WHY?", "SUN", "TIDES.", "WEAKER", "SIGNIFICANT.", "SOLAR"}
CAPS = []
for l in TIM:
    toks = []; prev = -1
    for w, s, e in l["words"]:
        s = max(s, prev + 0.08); prev = s; toks.append((w.upper(), s, e))
    chunk = []
    for i, tk in enumerate(toks):
        chunk.append(tk)
        if re.search(r"[,.:?!]$", tk[0]) or len(chunk) == 3 or i == len(toks) - 1:
            CAPS.append(chunk); chunk = []
CAPS = [(ch[0][1], (CAPS[i + 1][0][1] if i + 1 < len(CAPS) and CAPS[i + 1][0][1] - ch[-1][2] < 0.6 else ch[-1][2] + 0.4), ch) for i, ch in enumerate(CAPS)]

def draw_caption(img, t, y=1390):
    if t < HOOK_END: return
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
            items.append((w, sz, w in EMPH, fw))
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

# ------------------------------------------------------------------ scenes
MX, MY, MR = 700, 420, 150
def sky(moon_lit):
    def grad():
        y = np.linspace(0, 1, 1060)[:, None, None]
        return np.array([5, 9, 22], np.float32) + np.array([20, 34, 64], np.float32) * y ** 1.5
    g = cache("grad", grad)
    a = stars().copy()
    a[:1060] = a[:1060] * (1 - 0.6 * moon_lit) + g * (0.7 + 0.6 * moon_lit)
    return a

def beach(t, moon=1.0, amp=1.0, ring=None, gauge=None, tl_label=True, push=0.0):
    """Night beach: Moon over the sea, tide rising and falling (time-lapse), a tide ruler on the left."""
    arr = sky(moon)
    if moon > 0:
        arr = moonr.render(W, H, MX, MY, MR, light=(-0.1, 0.05, 1.0), base=arr, halo=0.6 * moon, gain=moon)
    img = finish(arr, 0.4); d = ImageDraw.Draw(img, "RGBA")
    if ring is not None:
        q = ring
        r = MR * (1 + 1.6 * q); d.ellipse((MX - r, MY - r, MX + r, MY + r), outline=(220, 230, 255, int(220 * (1 - q))), width=int(10 * (1 - q)) + 2)
    hz = 1060
    tide = amp * math.sin(2 * math.pi * t / 4.2)                               # -1..1 (time-lapse)
    ys = 1330 + 110 * tide                                                     # shoreline: high tide = closer to camera
    for y in range(hz, H, 6):                                                  # sea, far -> near
        q = (y - hz) / (H - hz)
        d.rectangle((0, y, W, y + 6), fill=(int(14 + 20 * q), int(34 + 40 * q), int(60 + 50 * q)))
    if moon > 0:                                                               # moonlight glitter path
        for j in range(40):
            y = hz + 8 + j * 7; w_ = 30 + j * 4 + 20 * math.sin(t * 3 + j)
            d.line((MX - w_ / 2, y, MX + w_ / 2, y), fill=(220, 230, 255, int(110 * moon * (1 - j / 40))), width=3)
    shore = [(x, ys + 18 * math.sin(x * 0.011 + t * 1.3) + 10 * math.sin(x * 0.03 - t)) for x in range(-20, W + 40, 20)]
    for k in range(6):                                                         # sand: wet band, then dry
        q = k / 5
        col = (int(lerp(70, 150, q)), int(lerp(62, 128, q)), int(lerp(50, 96, q)))
        d.polygon([(x, y + k * 32) for x, y in shore] + [(W + 40, H), (-20, H)], fill=col)
    d.line(shore, fill=(230, 240, 250, 230), width=6)                          # foam line
    d.line([(x, y + 14) for x, y in shore], fill=(200, 220, 235, 90), width=3)
    level = 1200 - 100 * tide                                                  # water height on the tide post (screen y)
    gx = 150
    d.rectangle((gx - 9, 1020, gx + 9, 1420), fill=(60, 50, 40))               # tide post
    top_ft, ft = 1050, 100
    for k in range(4):
        y = top_ft + k * ft
        d.line((gx - 24, y, gx + 24, y), fill=(255, 255, 255, 230), width=4)
        d.text((gx + 38, y), f"{3 - k} ft", font=font(F_MONO, 26), fill=WHITE, anchor="lm", stroke_width=3, stroke_fill=BLACK)
    level = top_ft + ft * (1.5 - 1.5 * tide)
    d.rectangle((gx - 40, level, gx + 40, level + 6), fill=(140, 200, 255, 230))
    d.ellipse((gx - 13, level - 10, gx + 13, level + 16), fill=YELLOW, outline=BLACK, width=3)
    if gauge is not None:                                                      # tidal range lost (top two feet turn red)
        g = ease(gauge)
        for k in range(2):
            y0 = top_ft + k * ft
            d.rectangle((gx - 18, y0 + 6, gx + 18, y0 + ft - 6), fill=(240, 80, 60, int(200 * g)))
        if g > 0.5:
            d.text((gx + 80, top_ft + ft * 0.5), "LOST", font=font(F_CAP, 54), fill=RED + (int(255 * g),), anchor="lm", stroke_width=6, stroke_fill=BLACK)
            d.text((gx + 80, top_ft + 2.5 * ft), "kept (Sun)", font=font(F_UI, 34), fill=ORANGE + (int(255 * g),), anchor="lm", stroke_width=4, stroke_fill=BLACK)
    if tl_label: tag(d, "ILLUSTRATION  ·  time-lapse, ~2/3 of tidal range is lunar", ORANGE)
    return img

def bulge(t, t0, moon_off=None, sun=True, notes=(), plain=False):
    cx, cy, R = 540, 1000, 250
    rot = (t - t0) * 0.5
    arr = earth.render(W, H, cx, cy, R, 90, -rot * 57.3, -rot * 57.3, sun=(-1, 0, 0.35), stars=stars())
    img = finish(arr, 0.25); d = ImageDraw.Draw(img, "RGBA")
    am = 0.2
    if moon_off is not None and t >= moon_off:
        q = t - moon_off; am = 0.2 * math.exp(-q / 2.4) * math.cos(q * 2.6)
    th = np.linspace(0, 2 * np.pi, 360)
    rr = R * 1.13 * (1 + am * np.cos(2 * (th - math.pi / 2)) + (0.092 if sun else 0) * np.cos(2 * (th - math.pi)))
    d.polygon([(cx + r * math.cos(a), cy - r * math.sin(a)) for a, r in zip(th, rr)], fill=(60, 140, 255, 70), outline=(140, 205, 255, 230))
    if moon_off is None or t < moon_off:
        m = moonr.render(220, 220, 110, 110, 62, light=(0, -1, 0.35))
        img.paste(Image.fromarray(np.clip(tone(m), 0, 255).astype(np.uint8)), (cx - 110, 400 - 110), Image.fromarray(np.clip(m.sum(-1) * 3, 0, 255).astype(np.uint8)))
        d = ImageDraw.Draw(img, "RGBA"); sub(d, cx, 520, "MOON", WHITE, 28)
        d.line((cx, 545, cx, cy - R * 1.4), fill=(255, 255, 255, 70), width=2)
    else:
        for i in range(0, 360, 12): d.arc((cx - 62, 400 - 62, cx + 62, 400 + 62), i, i + 6, fill=(220, 225, 240, 150), width=3)
        sub(d, cx, 520, "MOON GONE", (255, 170, 150), 28)
    if sun:
        for j in range(5):
            y = cy - 160 + j * 80
            d.line((30, y, 160, y), fill=(255, 210, 120, 170), width=4)
            d.polygon([(160, y), (144, y - 9), (144, y + 9)], fill=(255, 210, 120, 170))
        d.text((40, cy - 220), "SUNLIGHT", font=font(F_MONO, 22), fill=(255, 210, 140), anchor="lm")
    ma = math.pi / 2 + rot; mx, my = cx + R * 0.98 * math.cos(ma), cy - R * 0.98 * math.sin(ma)
    d.ellipse((mx - 10, my - 10, mx + 10, my + 10), fill=YELLOW, outline=BLACK, width=2)
    for txt, cue, col, y in notes:
        if t >= cue: pop(d, SAFE_CX, y, txt, 76, t - cue, col, 8)
    if not plain: tag(d, "DIAGRAM  ·  tidal bulges hugely exaggerated", (110, 220, 210))
    return img

def bulge_zoom(t, t0):
    img = bulge(t, t0 - 20, moon_off=t0 - 30.0, plain=True)
    k = 1.0 + 0.35 * ease(seg(t, t0, t0 + 4))
    w, h = W / k, H / k
    y0 = clamp(1000 - h * 0.55, 0, H - h)
    img = img.resize((W, H), Image.BICUBIC, box=(540 - w / 2, y0, 540 + w / 2, y0 + h))
    d = ImageDraw.Draw(img, "RGBA")
    if t >= ws(7, 1): pop(d, SAFE_CX, 330, "BUT NOT ALL TIDES", 76, t - ws(7, 1), YELLOW, 8)
    if t >= ls(8): pop(d, SAFE_CX, 440, "WHY?", 110, t - ls(8), WHITE)
    tag(d, "DIAGRAM  ·  tidal bulges hugely exaggerated", (110, 220, 210))
    return img

def basin(t, t0):
    def make():
        rng = np.random.default_rng(8)
        a = ndimage.gaussian_filter(rng.normal(0, 1, (480, 270)), 18)
        a = (a - a.min()) / (a.max() - a.min())
        yy, xx = np.mgrid[0:480, 0:270]
        edge = np.minimum.reduce([xx, yy, 269 - xx, 479 - yy]) / 50
        return (a * 0.6 + np.clip(edge, 0, 1) * 0.6) > 0.55
    sea = cache("basin", make)
    yy, xx = np.mgrid[0:480, 0:270].astype(np.float32)
    ph = np.arctan2(yy - 170, xx - 120) - np.arctan2(yy - 320, xx - 160) - (t - t0) * 1.6
    amp = np.clip(np.hypot(yy - 170, xx - 120) / 100, 0, 1) * np.clip(np.hypot(yy - 320, xx - 160) / 100, 0, 1)
    v = np.cos(ph) * amp
    col = np.stack([40 + 50 * v, 90 + 70 * v, 160 + 70 * v], -1)
    arr = np.where(sea[..., None], col, np.array([70, 64, 50], np.float32))
    arr = np.where(((np.abs(np.sin(ph * 3)) < 0.05) & sea)[..., None], np.array([230, 240, 255], np.float32), arr)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC); d = ImageDraw.Draw(img, "RGBA")
    for px, py in ((120, 170), (160, 320)):
        d.ellipse((px * 4 - 12, py * 4 - 12, px * 4 + 12, py * 4 + 12), outline=WHITE, width=4)
    pop(d, SAFE_CX, 330, "OCEAN BASINS", 96, t - t0, WHITE)
    sub(d, SAFE_CX, 420, "tide crests swing around 'no-tide' points", (230, 235, 245), 26)
    tag(d, "SCHEMATIC  ·  not a real map", (110, 220, 210))
    return img

def bars(t, t0, remove_at):
    img = finish(stars() * 0.8, 0.1); d = ImageDraw.Draw(img, "RGBA")
    pop(d, SAFE_CX, 330, "TIDE-RAISING PULL", 80, t - t0, (110, 220, 210), 8)
    k = ease_out(seg(t, t0 + 0.2, t0 + 1.0))
    mk = 1.0 if t < remove_at else 1 - ease(seg(t, remove_at, remove_at + 0.8))
    x0, w = 110, 760
    d.text((x0, 520), "MOON", font=font(F_UI, 44), fill=WHITE, anchor="lm")
    d.rounded_rectangle((x0, 560, x0 + max(8, w * k * mk), 660), 14, fill=(205, 215, 235))
    d.text((x0 + w * k * mk + 20 if mk > 0.05 else x0 + 30, 610), "1.00" if mk > 0.05 else "GONE", font=font(F_CAP, 50), fill=WHITE if mk > 0.05 else RED, anchor="lm", stroke_width=5, stroke_fill=BLACK)
    d.text((x0, 760), "SUN", font=font(F_UI, 44), fill=ORANGE, anchor="lm")
    d.rounded_rectangle((x0, 800, x0 + w * 0.46 * k, 900), 14, fill=(255, 200, 100))
    d.text((x0 + w * 0.46 * k + 20, 850), "≈ 0.46", font=font(F_CAP, 50), fill=ORANGE, anchor="lm", stroke_width=5, stroke_fill=BLACK)
    gy = 1130; pts1, pts2 = [], []
    for i in range(300):
        x = i / 299
        pts1.append((80 + x * 860, gy - 80 * math.cos(2 * math.pi * x * 10) * (1 + 0.46 * math.cos(2 * math.pi * x * 1.5)) / 1.46))
        pts2.append((80 + x * 860, gy - 80 * math.cos(2 * math.pi * x * 10) * 0.46 / 1.46))
    d.line(pts1, fill=(205, 215, 235, int(200 * mk) + 40), width=3)
    if t >= remove_at: d.line(pts2, fill=(255, 200, 100, int(255 * seg(t, remove_at + 0.3, remove_at + 1.0))), width=5)
    sub(d, SAFE_CX, gy + 120, "sea level: today vs. Sun only", (220, 225, 235), 26)
    tag(d, "DIAGRAM  ·  relative tidal forces", (110, 220, 210))
    return img

def trace(t, t0):
    img = finish(stars() * 0.7, 0.1); d = ImageDraw.Draw(img, "RGBA")
    pop(d, SAFE_CX, 330, "LUNAR TIDE FADES", 88, t - t0, (255, 170, 150), 9)
    sub(d, SAFE_CX, 425, "sea level at one coast (illustrative)", (220, 225, 235), 26)
    gx0, gx1, gy = 70, 1010, 860
    d.line((gx0, gy, gx1, gy), fill=(255, 255, 255, 60), width=2)
    vx = gx0 + 0.3 * (gx1 - gx0)
    d.line((vx, 560, vx, 1160), fill=(255, 255, 255, 90), width=2)
    d.text((vx + 12, 580), "Moon vanishes", font=font(F_MONO, 24), fill=(230, 230, 230), anchor="lm")
    k = lerp(0.3, 1.0, seg(t, t0, t0 + 2.6))                                   # starts already drawn: never an empty frame
    pts = []
    for i in range(int(400 * k) + 1):
        x = i / 400
        lun = 1.0 if x < 0.3 else math.exp(-(x - 0.3) / 0.18)
        h = lun * math.cos(2 * math.pi * x * 9) + 0.46 * math.cos(2 * math.pi * x * 9.4)
        pts.append((gx0 + x * (gx1 - gx0), gy - h * 150))
    if len(pts) > 1: d.line(pts, fill=(140, 205, 255), width=5)
    tag(d, "DIAGRAM  ·  illustrative tide curve", (110, 220, 210))
    return img

def sun_tides(t, t0):
    arr = stars().copy()
    arr = star.draw_sun(arr, 540, 420, 150, t, bright=0.9, corona=1.1)
    arr = earth.render(W, H, 540, 1040, 210, 90, -t * 20, -t * 20, sun=(0, 1, 0.4), stars=arr)
    img = finish(arr, 0.5); d = ImageDraw.Draw(img, "RGBA")
    th = np.linspace(0, 2 * np.pi, 360); q = ease(seg(t, t0, t0 + 1.0))
    rr = 210 * 1.13 * (1 + 0.09 * q * np.cos(2 * (th - math.pi / 2)))
    d.polygon([(540 + r * math.cos(a), 1040 - r * math.sin(a)) for a, r in zip(th, rr)], fill=(255, 190, 90, 60), outline=(255, 210, 140, 220))
    pop(d, SAFE_CX, 200 + 120, "THE SUN MAKES TIDES TOO", 66, t - t0, ORANGE, 8)
    tag(d, "DIAGRAM  ·  solar tidal bulge exaggerated", (110, 220, 210))
    return img

# ------------------------------------------------------------------ scene list
def sc_hook(t):
    gone = t >= T_VANISH
    ring = (t - T_VANISH) / 0.6 if T_VANISH <= t < T_VANISH + 0.6 else None
    amp = lerp(1.0, 0.33, ease(seg(t, T_VANISH + 0.3, ws(0, 13))))
    img = beach(t + 1.05, moon=0.0 if gone else 1.0, amp=amp, ring=ring, gauge=seg(t, ws(0, 7), ws(0, 11) + 0.2))
    dx, dy = shake(t, T_VANISH, 0.4, 16)
    if dx: img = img.transform(img.size, Image.AFFINE, (1, 0, dx, 0, 1, dy))
    d = ImageDraw.Draw(img, "RGBA")
    k = max(0.85, ease_back(seg(t, -0.05, 0.12)))
    d.text((SAFE_CX, 740), "NO MOON =", font=font(F_CAP, 118 * k), fill=WHITE, anchor="mm", stroke_width=11, stroke_fill=BLACK)
    d.text((SAFE_CX, 875), "NO TIDES?", font=font(F_CAP, 128 * k), fill=YELLOW, anchor="mm", stroke_width=12, stroke_fill=BLACK)
    if T_VANISH <= t < T_VANISH + 0.08:
        img = Image.blend(img, Image.new("RGB", (W, H), (235, 240, 255)), 0.45 * (1 - (t - T_VANISH) / 0.08))
    return img

def scenes():
    L = lambda i: ls(i) - 0.1
    return [
        (0, HOOK_END, sc_hook),
        (HOOK_END, L(2), lambda t: bulge(t, HOOK_END, moon_off=ls(1) + 1.0, notes=(("STILL MOVING", ws(1, 9), YELLOW, 330),))),
        (L(2), L(3), lambda t: beach(t * 1.6, moon=0.0, amp=0.9, tl_label=False)),
        (L(3), L(5), lambda t: basin(t, L(3))),
        (L(5), L(6), lambda t: beach(t * 1.8 + 3, moon=0.0, amp=0.75, tl_label=True)),
        (L(6), L(7), lambda t: trace(t, L(6))),
        (L(7), L(9), lambda t: bulge_zoom(t, L(7))),
        (L(9), L(10), lambda t: sun_tides(t, L(9))),
        (L(10), L(11), lambda t: bars(t, L(10), ls(11) - 0.6)),
        (L(11), DUR + 1, lambda t: sc_end(t)),
    ]

def sc_end(t):
    t0 = ls(11) - 0.1
    img = beach(t, moon=0.0, amp=0.33, gauge=1.0)
    d = ImageDraw.Draw(img, "RGBA")
    pop(d, SAFE_CX, 330, "SOLAR TIDES STAY", 92, t - ws(11, 5), ORANGE)
    sub(d, SAFE_CX, 420, "about a third of today's tidal range", (240, 225, 200), 28)
    q = ease(seg(t, DUR - 0.7, DUR))                                         # loop: the Moon returns -> frame 0
    if q > 0: img = Image.blend(img, sc_hook(0.0), q)
    return img

SCENES = scenes()
yy_, xx_ = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1 - 0.32 * (((xx_ - W / 2) / (W / 2)) ** 2 + ((yy_ - H / 2) / (H / 2)) ** 2) ** 1.6).clip(0.5, 1)[..., None]
del yy_, xx_
GRN = np.random.default_rng(3)
GRAIN = [GRN.normal(0, 3.2, (H // 2, W // 2, 1)).astype(np.float32).repeat(2, 0).repeat(2, 1) for _ in range(4)]

def frame(fi):
    t = fi / FPS
    for a, b, fn in SCENES:
        if a <= t < b: img = fn(t); break
    for a, b, fn in SCENES[1:]:
        if 0 <= t - a < 0.067: img = Image.blend(img.convert("RGB"), Image.new("RGB", (W, H), (225, 238, 255)), 0.2 * (1 - (t - a) / 0.067))
    arr = np.asarray(img.convert("RGB"), np.float32) * VIG + GRAIN[fi % 4]
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    draw_caption(img, t)
    return img.tobytes()

def render_video(out, preview=None):
    if preview:
        import os; os.makedirs("pv", exist_ok=True)
        for t in preview:
            Image.frombytes("RGB", (W, H), frame(int(round(t * FPS)))).resize((270, 480)).save(f"pv/p_{int(t * 100):05d}.jpg", quality=85)
        return
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for i, b in enumerate(pool.imap(frame, range(NF), chunksize=3)):
            p.stdin.write(b)
            if i % 150 == 0: print("frame", i, "/", NF, flush=True)
    p.stdin.close(); p.wait()

# ------------------------------------------------------------------ audio
def surf(dur, seed=4):
    rng = np.random.default_rng(seed); n = int(dur * SR); tt = np.arange(n) / SR
    x = lp(rng.normal(0, 1, n), 600) * 1.4 + bp(rng.normal(0, 1, n), 1500, 6000) * 0.15
    return x * (0.45 + 0.55 * np.sin(2 * np.pi * tt / 4.2) ** 2) * np.minimum(1, tt / 0.5) * np.minimum(1, (dur - tt) / 0.5)

def render_audio(out):
    n = int(DUR * SR); tt = np.arange(n) / SR
    pad = np.zeros(n)
    for t0, t1, notes in ((0, ls(7), [55.0, 82.41, 130.81, 164.81]), (ls(7), DUR, [65.41, 98.0, 164.81, 196.0])):
        i0, i1 = int(t0 * SR), min(n, int(t1 * SR) + int(0.8 * SR)); m = i1 - i0; sg = np.zeros(m)
        for f in notes:
            for det in (-0.12, 0.0, 0.11): sg += osc(f * 2 ** (det / 12), m)
        e = np.minimum(1, np.arange(m) / (0.8 * SR)) * np.minimum(1, (m - np.arange(m)) / (0.8 * SR))
        pad[i0:i1] += sg * e / 12
    mus = (lp(pad, 1000) * 0.7 + lp(pad, 360) * 0.6 + osc(41.2, n, "sin") * 0.2) * np.interp(tt, [0, T_VANISH, T_VANISH + 0.05, T_VANISH + 1.2, DUR - 1, DUR], [0.6, 0.6, 0.1, 0.7, 0.9, 0.6])
    fx = np.zeros(n)
    place(fx, surf(DUR), 0.0, 0.7)
    place(fx, reverb(boom(1.6, 90, 34, 0.5), 2.5, 0.4), 0.0, 0.8)                         # frame-0 impact
    place(fx, reverb(boom(2.8, 110, 22, 1.0), 3.5, 0.5), T_VANISH, 1.3); place(fx, crack(0.4) * 0.4, T_VANISH, 0.4)   # the Moon vanishes
    place(fx, riser(1.2, 90) * 0.5, ws(0, 7) - 0.5, 0.35); place(fx, reverb(boom(1.2, 80, 36, 0.35)), ws(0, 11), 0.6)
    for a, b, fn in SCENES[1:]: place(fx, whoosh(0.5), a - 0.15, 0.3)
    place(fx, reverb(boom(1.4, 85, 32, 0.45)), ls(8), 0.6)                                 # "Why?"
    place(fx, reverb(boom(1.6, 70, 28, 0.6)), ls(11) - 0.6, 0.7)                           # Moon bar collapses
    place(fx, riser(0.8, 140), DUR - 0.8, 0.4)
    vo = np.zeros(n)
    for l in TIM:
        s, _ = sf.read(l["file"]); place(vo, s, l["start"])
    vo = lp(hp(vo, 85), 13000); vo = vo / (np.abs(vo).max() + 1e-9) * 0.9
    env = lp(np.abs(vo), 7); env /= env.max() + 1e-9
    duck = 1 - 0.62 * np.clip(env * 3, 0, 1)
    mix = vo + mus * 0.11 * duck + fx * 0.30 * (0.45 + 0.55 * duck)
    sf.write(out, np.stack([np.tanh(mix * 1.05) * 0.95] * 2, 1).astype(np.float32), SR, subtype="FLOAT")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        render_video(None, [float(x) for x in sys.argv[2:]])
    elif len(sys.argv) > 1 and sys.argv[1] == "info":
        print("DUR", DUR, "vanish", T_VANISH, "hook_end", HOOK_END); [print(round(l["start"], 2), " ".join(w for w, _, _ in l["words"])) for l in TIM]
    else:
        render_audio("mix.wav"); print("audio done", flush=True)
        render_video("video.mp4"); print("video done", flush=True)
