#!/usr/bin/env python3
# SPACE SECRETS — TikTok EP04: "The Moon That Sprays an Ocean Into Space" (Enceladus), vertical 1080x1920.
# Built under the Viral Retention System V3 (frame-0 visual event, hook caption only during the hook, story beats).
import json, math, re, subprocess, sys
from multiprocessing import Pool

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

import ence
from sfx import SR, lp, hp, bp, envx, place, osc, boom, crack, whoosh, tick, riser, reverb, arng

W, H, FPS = 1080, 1920, 30
RS = 2 / 3; WR, HR = int(W * RS), int(H * RS)
TIM = json.load(open("timing.json"))
NARR_END = TIM[-1]["start"] + TIM[-1]["dur"]
DUR = round(NARR_END + 3.0, 1)
NF = int(DUR * FPS)
def ls(i): return TIM[i]["start"]
def le(i): return TIM[i]["start"] + TIM[i]["dur"]
def ws(i, k): return TIM[i]["words"][min(k, len(TIM[i]["words"]) - 1)][1]

def clamp(v, a, b): return max(a, min(b, v))
def seg(t, a, b): return clamp((t - a) / (b - a), 0.0, 1.0) if b > a else float(t >= a)
def ease(x): x = clamp(x, 0, 1); return x * x * (3 - 2 * x)
def ease_out(x): x = clamp(x, 0, 1); return 1 - (1 - x) ** 3
def ease_in(x): x = clamp(x, 0, 1); return x ** 3
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
WHITE, YELLOW, BLACK, CYAN, ORANGE, RED, GREEN = (255, 255, 255), (255, 212, 0), (0, 0, 0), (120, 210, 255), (255, 150, 60), (235, 60, 50), (110, 230, 150)
ICE = (190, 235, 255)
SAFE_CX = 510                                   # TikTok safe area: x 60..960, y 220..1500

# ------------------------------------------------------------------ backgrounds / helpers
_C = {}
def cache(k, fn):
    if k not in _C: _C[k] = fn()
    return _C[k]

def stars_half():
    def make():
        rng = np.random.default_rng(41)
        a = np.zeros((HR, WR, 3), np.float32) + np.array([2, 4, 9], np.float32)
        n = 3800; ys = rng.integers(0, HR, n); xs = rng.integers(0, WR, n)
        b = rng.pareto(2.4, n) * 50 + 20
        np.add.at(a, (ys, xs), np.stack([b, b * 0.97, b * 1.05], -1))
        return np.clip(a, 0, 255)
    return cache("stars", make)

def up(arr):
    return np.asarray(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32)

def tone(arr):
    a = np.clip(arr, 0, None) / 255.0
    return np.clip(255 * (1 - np.exp(-a * 1.3)) / (1 - math.exp(-1.3)), 0, 255)

def glow(arr, amt=0.4, thr=160, rad=34):
    small = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
    hi = np.clip(np.asarray(small, np.float32) - thr, 0, None) * 1.8
    bl = np.asarray(Image.fromarray(np.clip(hi, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(rad / 4)).resize((W, H), Image.BILINEAR), np.float32)
    return arr + bl * amt

def finish(arr, g=0.4): return Image.fromarray(np.clip(tone(glow(arr, g)), 0, 255).astype(np.uint8))

def push(img, k, cx=W / 2, cy=H / 2):
    if k <= 1.0001: return img
    w, h = W / k, H / k
    x0 = clamp(cx - w / 2, 0, W - w); y0 = clamp(cy - h / 2, 0, H - h)
    return img.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + w, y0 + h))

def shake(t, t0, dur, amp):
    if not (t0 <= t < t0 + dur): return 0.0, 0.0
    k = 1 - (t - t0) / dur
    return amp * k * math.sin(t * 97), amp * k * math.cos(t * 83)

def tag(d, txt="SCIENTIFIC VISUALIZATION  ·  not real footage", col=CYAN):
    f = font(F_MONO, 23)
    d.rounded_rectangle((60, 196, 60 + f.getlength(txt) + 28, 238), 10, fill=(0, 0, 0, 150))
    d.ellipse((72, 211, 84, 223), fill=col)
    d.text((94, 217), txt, font=f, fill=(230, 230, 230), anchor="lm")

def pop(d, x, y, txt, size, age, color=WHITE, sw=10, a=255):
    if age < 0: return
    s = size * (1 + 0.35 * max(0, 1 - age / 0.14))
    d.text((x, y), txt, font=font(F_CAP, s), fill=color + (a,), anchor="mm", stroke_width=sw, stroke_fill=BLACK)

def sub(d, x, y, txt, color=(225, 225, 225), size=30, a=255, anchor="mm"):
    d.text((x, y), txt, font=font(F_MONO, size), fill=color + (a,), anchor=anchor, stroke_width=4, stroke_fill=BLACK)

def chip(d, x, y, title, body, k, color=CYAN, w=None):
    if k <= 0: return
    a = int(255 * k); dx = 40 * (1 - ease_out(k))
    f1, f2 = font(F_UI, 36), font(F_MONO, 25)
    w = w or max(f1.getlength(title), f2.getlength(body)) + 50
    d.rounded_rectangle((x + dx, y, x + dx + w, y + 106), 16, fill=(0, 0, 0, int(185 * k)), outline=color + (a,), width=3)
    d.text((x + dx + 25, y + 32), title, font=f1, fill=color + (a,), anchor="lm")
    d.text((x + dx + 25, y + 78), body, font=f2, fill=(235, 235, 235, a), anchor="lm")

# ------------------------------------------------------------------ captions (series identity, safe area)
EMPH = {"OCEAN", "SPACE!", "NASA", "SPRAY.", "ENCELADUS.", "TINY,", "SATURN.", "LIFELESS", "EXTRAORDINARY", "GLOBAL", "LIQUID", "WATER.",
        "SOUTH", "CRACKS", "ERUPT", "CASSINI", "PLUMES", "INCREDIBLE.", "SALTS.", "ORGANIC", "COMPOUNDS.", "ENERGY", "LIFE.",
        "PHOSPHORUS,", "ESSENTIAL", "E", "RING,", "NOT", "ALIENS", "INGREDIENTS", "SUNLIGHT.", "KILOMETERS", "SAMPLES", "MYSTERY",
        "ALIVE", "THERE?", "IMPORTANT"}
CAPS = []
for l in TIM:
    toks = []; prev = -1
    for w, s, e in l["words"]:
        s = max(s, prev + 0.08); prev = s
        toks.append((w.upper(), s, e))
    chunk = []
    for i, tk in enumerate(toks):
        chunk.append(tk)
        if re.search(r"[,.:?!]$", tk[0]) or len(chunk) == 3 or i == len(toks) - 1:
            CAPS.append(chunk); chunk = []
CAPS = [(ch[0][1], (CAPS[i + 1][0][1] if i + 1 < len(CAPS) and CAPS[i + 1][0][1] - ch[-1][2] < 0.6 else ch[-1][2] + 0.4), ch)
        for i, ch in enumerate(CAPS)]
HOOK_END = ls(1) - 0.05

def draw_caption(img, t, y=1390):
    if t < HOOK_END: return                       # rule: only the hook caption during the hook
    d = ImageDraw.Draw(img)
    for a, b, ch in CAPS:
        if not (a <= t < b): continue
        vis = [x for x in ch if x[1] <= t + 0.02]
        if not vis: return
        base, gap, maxw = 92, 22, 860
        items = []
        for w, s, e in vis:
            sz = base * (1 + 0.25 * max(0, 1 - (t - s) / 0.11))
            fw = font(F_CAP, sz).getlength(w)
            if fw > maxw: sz *= maxw / fw; fw = maxw
            items.append((w, sz, w.strip(",.!?") in {x.strip(",.!?") for x in EMPH} or w in EMPH, fw))
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

# ------------------------------------------------------------------ Cassini (CGI silhouette model)
def cassini(scale, rot=0.0, lit=1.0):
    s = scale; im = Image.new("RGBA", (int(s * 16), int(s * 16)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    cx, cy = s * 8, s * 8
    d.line((cx + s * 0.6, cy + s * 0.2, cx + s * 7.2, cy - s * 1.8), fill=(90, 90, 95, 255), width=max(2, int(s * 0.12)))   # magnetometer boom
    d.rectangle((cx + s * 7.0, cy - s * 2.0, cx + s * 7.5, cy - s * 1.6), fill=(150, 150, 150, 255))
    d.rounded_rectangle((cx - s * 0.8, cy - s * 0.6, cx + s * 0.8, cy + s * 2.2), s * 0.15, fill=(int(180 * lit), int(140 * lit), int(50 * lit), 255))  # gold foil bus
    for k in range(5): d.line((cx - s * 0.8, cy - s * 0.3 + k * s * 0.5, cx + s * 0.8, cy - s * 0.3 + k * s * 0.5), fill=(110, 85, 30, 255), width=max(1, int(s * 0.06)))
    d.rectangle((cx - s * 1.0, cy + s * 2.2, cx + s * 1.0, cy + s * 3.0), fill=(60, 60, 64, 255))                          # lower module
    for ex in (-0.45, 0.45): d.polygon([(cx + s * (ex - 0.25), cy + s * 3.0), (cx + s * (ex + 0.25), cy + s * 3.0), (cx + s * (ex + 0.4), cy + s * 3.8), (cx + s * (ex - 0.4), cy + s * 3.8)], fill=(40, 40, 44, 255))
    for ang in (-2.4, 2.4, 3.14):                                                                                          # RTGs
        x0, y0 = cx + s * 0.9 * math.sin(ang), cy + s * 2.4
        d.line((x0, y0, x0 + s * 1.4 * math.sin(ang), y0 + s * 0.6), fill=(70, 70, 70, 255), width=max(2, int(s * 0.32)))
    d.ellipse((cx - s * 2.2, cy - s * 1.5, cx + s * 2.2, cy - s * 0.2), fill=(int(235 * lit), int(235 * lit), int(230 * lit), 255))  # high-gain antenna
    d.ellipse((cx - s * 1.9, cy - s * 1.25, cx + s * 1.9, cy - s * 0.45), fill=(int(205 * lit), int(205 * lit), int(205 * lit), 255))
    d.line((cx, cy - s * 0.85, cx, cy - s * 1.9), fill=(200, 200, 200, 255), width=max(1, int(s * 0.08)))
    return im.rotate(rot, resample=Image.BICUBIC, expand=False)

def paste_c(img, sprite, x, y):
    img.paste(sprite, (int(x - sprite.width / 2), int(y - sprite.height / 2)), sprite)

# ------------------------------------------------------------------ flying ice grains toward the camera (hook rush)
NG = 900
GRN_ = np.random.default_rng(5)
G_X = GRN_.uniform(-3, 3, NG); G_Y = GRN_.uniform(-5.5, 5.5, NG); G_Z0 = GRN_.uniform(0.2, 10, NG); G_B = GRN_.uniform(0.4, 1.0, NG)
def grains(img, t, speed, vpx=540, vpy=900, foc=420, tint=(220, 240, 255), amount=1.0):
    if amount <= 0: return img
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    zs = (G_Z0 - speed * t) % 10 + 0.2
    for x, y, z, b in zip(G_X, G_Y, zs, G_B):
        px, py = vpx + foc * x / z, vpy + foc * y / z
        if not (-50 < px < W + 50 and -50 < py < H + 50): continue
        z2 = z + speed * 0.04
        qx, qy = vpx + foc * x / z2, vpy + foc * y / z2
        a = int(clamp(255 * b * (1.25 - z / 9) * amount, 0, 255))
        wd = max(1, int(6 / z))
        d.line((qx, qy, px, py), fill=tint + (a,), width=wd)
    lb = lay.filter(ImageFilter.GaussianBlur(1.6)); img.paste(lb, (0, 0), lb); img.paste(lay, (0, 0), lay)
    return img

# ------------------------------------------------------------------ scene building blocks
SUN_BACK = (0.35, 0.25, -0.9)                    # sunlight from behind: plumes glow (forward scattering)
def limb_plume(t, R, cy_off, lon_c=0.0, lat0=-22, light=SUN_BACK, strength=1.0, saturn=True, sat_xy=(250, 360), sat_R=150, flip=True, height=1.5):
    """Enceladus limb with the south polar plume rising UP (render pole-down, then flip vertically)."""
    base = stars_half().copy()
    if saturn:
        sx, sy = sat_xy
        base = ence.render_saturn(WR, HR, sx * RS, (H - sy) * RS if flip else sy * RS, sat_R * RS, tilt=-16 if flip else 16, light=(0.6, 0.2, 0.75), base=base, gain=0.9)
    cy = (H - cy_off) * RS if flip else cy_off * RS
    a = ence.render_enceladus(WR, HR, 540 * RS, cy, R * RS, light=light, lat0=lat0, lon_c=lon_c, base=base, halo=0.25)
    a = ence.plumes(a, t, 540 * RS, cy, R * RS, lat0, lon_c, strength=strength, light_back=1.6, height=height)
    img = up(a)
    if flip: img = img[::-1]
    return img

def sc_hook(t):                                   # 0 -> HOOK_END: rushing through the erupting plume
    k = seg(t, 0, HOOK_END)
    arr = limb_plume(t + 1.5, 1300, 2600 + 160 * ease(k), lat0=4, light=(0.0, -0.35, -0.9), strength=2.4, height=0.95,
                     sat_xy=(800, 330), sat_R=150)
    dx, dy = shake(t, 0.0, 0.5, 18)
    img = finish(arr, 0.55)
    img = grains(img, t, 7.5, vpx=540, vpy=1000, amount=0.8)
    img = push(img, lerp(1.0, 1.18, ease_in(k)), 540 + dx, 1000 + dy)
    d = ImageDraw.Draw(img, "RGBA")
    kk = max(0.85, ease_back(seg(t, -0.05, 0.12)))
    d.text((SAFE_CX, 470), "AN OCEAN", font=font(F_CAP, 150 * kk), fill=WHITE, anchor="mm", stroke_width=12, stroke_fill=BLACK)
    s2 = 1 + 0.3 * max(0, 1 - (t - ws(0, 7)) / 0.14) if t >= ws(0, 7) else 1
    d.text((SAFE_CX, 640), "IN SPACE?!", font=font(F_CAP, 128 * kk * s2), fill=YELLOW, anchor="mm", stroke_width=12, stroke_fill=BLACK)
    tag(d)
    return img

def sc_flyby(t, t0, t1, path=((980, 620), (-120, 1000)), scale=34, label=True, chipcue=None):
    k = seg(t, t0, t1)
    arr = limb_plume(t + 2.0, 1300, 2700 + 120 * k, lat0=4, lon_c=10, light=(0.0, -0.35, -0.9), strength=2.2, height=0.95, sat_xy=(820, 330), sat_R=130)
    img = finish(arr, 0.5)
    img = grains(img, t, 3.0, vpx=540, vpy=900, amount=0.55)
    x = lerp(path[0][0], path[1][0], ease(k)); y = lerp(path[0][1], path[1][1], ease(k))
    sp = cassini(scale, rot=-18 + 10 * k, lit=0.9)
    paste_c(img, sp, x, y)
    d = ImageDraw.Draw(img, "RGBA")
    tag(d, "CGI RECONSTRUCTION  ·  not real footage", ORANGE)
    if label:
        sub(d, x, y + scale * 5.2, "CASSINI", (255, 220, 160), 28)
    if chipcue is not None:
        chip(d, 70, 1110, chipcue[0], chipcue[1], seg(t, chipcue[2], chipcue[2] + 0.35), ORANGE)
    return img

def sc_meet(t, t0, t1):
    k = seg(t, t0, t1)
    base = stars_half().copy()
    base = ence.render_saturn(WR, HR, 620 * RS, 470 * RS, 330 * RS, tilt=14, light=(-0.4, 0.25, 0.85), base=base, gain=0.95)
    R = lerp(340, 400, ease(k))
    a = ence.render_enceladus(WR, HR, 520 * RS, 1000 * RS, R * RS, light=(-0.45, 0.3, 0.84), lat0=-10, lon_c=20 - 6 * t, base=base, halo=0.2)
    a = ence.plumes(a, t, 520 * RS, 1000 * RS, R * RS, -10, 20 - 6 * t, strength=0.45, height=1.1)
    img = finish(up(a), 0.4)
    if t - t0 < 0.12:                                 # fast whip in
        img = img.filter(ImageFilter.GaussianBlur(14 * (1 - (t - t0) / 0.12)))
    d = ImageDraw.Draw(img, "RGBA"); tag(d)
    if t >= ws(2, 1):
        pop(d, SAFE_CX, 330, "ENCELADUS", 128, t - ws(2, 1), WHITE)
        sub(d, SAFE_CX, 420, "moon of Saturn", (210, 230, 255), 30)
    if t >= ws(3, 1):
        chip(d, 70, 1150, "504 km WIDE", "about as wide as Arizona", seg(t, ws(3, 1), ws(3, 1) + 0.35), ICE)
    return img

def sc_lifeless(t, t0, t1):
    k = seg(t, t0, t1)
    a = ence.render_enceladus(WR, HR, 540 * RS, 900 * RS, lerp(520, 600, ease(k)) * RS, light=(-0.35, 0.35, 0.87), lat0=25, lon_c=60 - 4 * t, base=stars_half())
    arr = up(a); g = arr.mean(-1, keepdims=True); arr = arr * 0.6 + g * 0.4
    img = finish(arr, 0.3); d = ImageDraw.Draw(img, "RGBA"); tag(d)
    if t >= ws(4, 7): pop(d, SAFE_CX, 330, "LIFELESS?", 130, t - ws(4, 7), (200, 215, 230))
    return img

def sc_cutaway(t, t0, t1):
    k = seg(t, t0, t1)
    cx, cy, R = 540, 940, 470
    a = ence.render_enceladus(WR, HR, cx * RS, cy * RS, R * RS, light=(-0.5, 0.3, 0.8), lat0=5, lon_c=90 - 5 * t, base=stars_half())
    img = finish(up(a), 0.3)
    op = ease_out(seg(t, ws(5, 2) - 0.2, ws(5, 2) + 0.9))
    if op > 0:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        a0, a1 = -60 * op, 0
        box = lambda r: (cx - r, cy - r, cx + r, cy + r)
        d.pieslice(box(R), a0, a1, fill=(205, 230, 245, 255))                 # ice shell
        d.pieslice(box(R * 0.91), a0, a1, fill=(25, 70, 140, 255))            # global ocean
        d.pieslice(box(R * 0.76), a0, a1, fill=(105, 80, 60, 255))            # rocky core
        rng = np.random.default_rng(3)
        for i in range(160):
            ang = math.radians(rng.uniform(a0, a1)); r = R * 0.76 * math.sqrt(rng.random())
            d.ellipse((cx + r * math.cos(ang) - 3, cy + r * math.sin(ang) - 3, cx + r * math.cos(ang) + 3, cy + r * math.sin(ang) + 3), fill=(80, 60, 45, 255))
        for i in range(10):                                                    # warm water-rock interface glints
            ang = math.radians(lerp(a0, a1, (i + 0.5) / 10)); r = R * 0.765
            g = 0.5 + 0.5 * math.sin(t * 3 + i)
            d.ellipse((cx + r * math.cos(ang) - 6, cy + r * math.sin(ang) - 6, cx + r * math.cos(ang) + 6, cy + r * math.sin(ang) + 6), fill=(255, 150, 70, int(160 * g)))
        img.paste(lay, (0, 0), lay)
        d = ImageDraw.Draw(img, "RGBA")
        if op > 0.8:
            ang = math.radians(a0 * 0.5)
            for r_, name, col, y in ((R * 0.955, "ICE SHELL", ICE, 1150), (R * 0.835, "OCEAN", (120, 190, 255), 1205), (R * 0.4, "ROCKY CORE", (230, 180, 140), 1260)):
                px, py = cx + r_ * math.cos(ang), cy + r_ * math.sin(ang)
                d.line((px, py, 700, y - 20), fill=col + (220,), width=3)
                d.text((710, y - 20), name, font=font(F_UI, 34), fill=col, anchor="lm", stroke_width=4, stroke_fill=BLACK)
    d = ImageDraw.Draw(img, "RGBA"); tag(d)
    if t >= ws(5, 2): pop(d, SAFE_CX, 330, "BENEATH THE ICE", 84, t - ws(5, 2), YELLOW)
    return img

def ice_column():
    def make():
        rng = np.random.default_rng(12)
        h, w = 2400, 360
        n = ndimage.gaussian_filter(rng.normal(0, 1, (h, w)), (3, 18))
        strata = np.sin(np.linspace(0, 90, h))[:, None] * 0.6 + n * 3.5
        v = np.clip(0.75 + 0.08 * strata, 0, 1)
        col = np.stack([v * 150, v * 205, v * 245], -1)
        depth = np.linspace(0, 1, h)[:, None, None]
        col = col * (1 - 0.65 * depth)
        cracks = np.zeros((h, w))
        for _ in range(40):
            x = rng.integers(0, w); y0 = rng.integers(0, h - 200); L = rng.integers(60, 260)
            xs = (x + np.cumsum(rng.normal(0, 1, L))).astype(int) % w
            cracks[y0:y0 + L, :][np.arange(L), xs] = 1
        cracks = ndimage.gaussian_filter(cracks, 0.8)
        col = col * (1 - 0.5 * cracks[..., None])
        return col.astype(np.float32)
    return cache("icecol", make)

def sc_descent(t, t0, t1):
    k = seg(t, t0, t1)
    col = ice_column()
    depth = ease(k)                                                # 0 -> 1: surface -> ocean
    ch = col.shape[0] - 1280
    y0 = int(lerp(0, ch, min(1, depth * 1.15)))
    view = col[y0:y0 + 1280]
    arr = np.asarray(Image.fromarray(np.clip(view, 0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32)
    water = ease(seg(k, 0.72, 0.95))                               # break through into the ocean
    yy = np.linspace(0, 1, H)[:, None, None]
    ocean = np.array([4, 18, 46], np.float32) + np.array([10, 30, 60], np.float32) * (1 - yy)
    bd = (yy > (1 - water * 1.1))                                  # ocean rises from below
    arr = np.where(bd, ocean + 0 * arr, arr) if water > 0 else arr
    img = finish(arr, 0.2); d = ImageDraw.Draw(img, "RGBA")
    if water > 0:
        rng = np.random.default_rng(int(t * 5))
        for i in range(120):
            x = rng.uniform(0, W); y = rng.uniform(H * (1 - water), H)
            d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(170, 210, 255, 90))
    gx, g0, g1 = 90, 520, 1300                                      # depth gauge
    d.line((gx, g0, gx, g1), fill=(255, 255, 255, 170), width=4)
    my = lerp(g0, g1, depth)
    d.polygon([(gx + 14, my), (gx + 38, my - 13), (gx + 38, my + 13)], fill=YELLOW)
    d.text((gx + 48, my), f"{depth * 22:.0f} km", font=font(F_MONO, 28), fill=YELLOW, anchor="lm", stroke_width=3, stroke_fill=BLACK)
    d.text((gx - 10, g0 - 34), "ICE SHELL", font=font(F_MONO, 24), fill=(230, 240, 255), anchor="lm", stroke_width=3, stroke_fill=BLACK)
    tag(d)
    if t >= ws(6, 7):
        pop(d, SAFE_CX + 30, 360, "A GLOBAL OCEAN", 104, t - ws(6, 7), (120, 200, 255))
        sub(d, SAFE_CX + 30, 450, "of liquid water, under ~20–25 km of ice", (220, 235, 255), 27)
    return img

def sc_stripes(t, t0, t1, erupt_from=None, view="pole"):
    k = seg(t, t0, t1)
    if view == "pole":
        R = lerp(520, 600, ease(k)); lat0 = -78; cy = 960
        light = (-0.5, 0.4, 0.75)
    else:                                                          # oblique
        R = 640; lat0 = -52; cy = 1080; light = (0.5, 0.45, 0.72)
    a = ence.render_enceladus(WR, HR, 540 * RS, cy * RS, R * RS, light=light, lat0=lat0, lon_c=15 + 3 * (t - t0), base=stars_half(), halo=0.2)
    if erupt_from is not None and t >= erupt_from:
        a = ence.plumes(a, t, 540 * RS, cy * RS, R * RS, lat0, 15 + 3 * (t - t0), strength=ease(seg(t, erupt_from, erupt_from + 1.0)) * 0.9, height=1.0)
    img = finish(up(a), 0.4); d = ImageDraw.Draw(img, "RGBA"); tag(d)
    if view == "pole" and t >= ws(7, 6):
        kk = seg(t, ws(7, 6), ws(7, 6) + 0.4)
        pop(d, SAFE_CX, 330, "TIGER STRIPES", 110, t - ws(7, 6), YELLOW)
        sub(d, SAFE_CX, 420, "4 huge fractures · each ~130 km long", (230, 235, 245), 27, int(255 * kk))
    return img

def sc_backlit(t, t0, t1, R=430, cy=760, sat=False, txt=None, strength=1.6, lat0=-12):
    k = seg(t, t0, t1)
    base = stars_half().copy()
    if sat: base = ence.render_saturn(WR, HR, 300 * RS, 1500 * RS, 260 * RS, tilt=10, light=(0.7, 0.2, 0.7), base=base, gain=0.8)
    a = ence.render_enceladus(WR, HR, 540 * RS, cy * RS, R * lerp(1.0, 1.08, ease(k)) * RS, light=(0.92, 0.25, -0.3), lat0=lat0, lon_c=0, base=base)
    a = ence.plumes(a, t, 540 * RS, cy * RS, R * lerp(1.0, 1.08, ease(k)) * RS, lat0, 0, strength=strength, light_back=1.7, height=1.7)
    img = finish(up(a), 0.5); d = ImageDraw.Draw(img, "RGBA"); tag(d)
    if txt:
        pop(d, SAFE_CX, 330, txt[0], txt[1], t - txt[2], txt[3])
    return img

ITEMS = [("WATER", "H₂O vapour and ice", 11, 0, CYAN), ("SALTS", "sodium salts in the ice grains", 12, 0, (240, 240, 240)),
         ("ORGANIC COMPOUNDS", "carbon-based molecules", 13, 0, (255, 190, 120))]
def molecule(d, x, y, kind, a):
    if kind == 0:
        for dx, r, c in ((0, 26, (255, 90, 80)), (-34, 16, (240, 240, 240)), (34, 16, (240, 240, 240))):
            d.ellipse((x + dx - r, y + (12 if dx else 0) - r, x + dx + r, y + (12 if dx else 0) + r), fill=c + (a,))
    elif kind == 1:
        for i in range(3):
            for j in range(3):
                c = (180, 120, 255) if (i + j) % 2 else (120, 220, 120)
                d.ellipse((x - 36 + i * 36 - 12, y - 36 + j * 36 - 12, x - 36 + i * 36 + 12, y - 36 + j * 36 + 12), fill=c + (a,))
    else:
        pts = [(x + 34 * math.cos(math.radians(60 * i + 30)), y + 34 * math.sin(math.radians(60 * i + 30))) for i in range(6)]
        d.line(pts + [pts[0]], fill=(255, 190, 120, a), width=6)
        for p in pts: d.ellipse((p[0] - 8, p[1] - 8, p[0] + 8, p[1] + 8), fill=(70, 70, 70, a))

def sc_found(t, t0, t1):
    k = seg(t, t0, t1)
    arr = limb_plume(t + 4, 1300, 2050, strength=0.9, saturn=False)
    img = finish(arr * 0.55, 0.3)
    img = grains(img, t, 1.4, vpx=540, vpy=1000, amount=0.5)
    d = ImageDraw.Draw(img, "RGBA"); tag(d, "WHAT CASSINI MEASURED  ·  real results", YELLOW)
    if t >= ws(10, 2) - 0.2:
        pop(d, SAFE_CX, 330, "WHAT CASSINI FOUND", 84, t - ws(10, 2) + 0.2, YELLOW, 9)
    for i, (name, desc, li, wk, col) in enumerate(ITEMS):
        tw = ws(li, wk) - 0.05
        a = seg(t, tw, tw + 0.25)
        if a <= 0: continue
        y = 520 + i * 230; x = 90; dy = 30 * (1 - ease_out(a))
        aa = int(255 * a)
        d.rounded_rectangle((x, y + dy, 940, y + 190 + dy), 22, fill=(0, 0, 0, int(170 * a)), outline=col + (aa,), width=3)
        molecule(d, x + 95, y + 95 + dy, i, aa)
        s = 1 + 0.25 * max(0, 1 - (t - tw) / 0.14)
        d.text((x + 190, y + 75 + dy), name, font=font(F_CAP, (64 if i < 2 else 52) * s), fill=col + (aa,), anchor="lm", stroke_width=6, stroke_fill=BLACK)
        d.text((x + 192, y + 140 + dy), desc, font=font(F_MONO, 26), fill=(230, 230, 230, aa), anchor="lm")
    return img

def seafloor():
    def make():
        rng = np.random.default_rng(21)
        prof = 1500 + 90 * ndimage.gaussian_filter1d(rng.normal(0, 1, W), 60) * 6 + 20 * ndimage.gaussian_filter1d(rng.normal(0, 1, W), 8) * 4
        return prof
    return cache("floor", make)

def sc_vents(t, t0, t1):
    k = seg(t, t0, t1)
    yy = np.linspace(0, 1, H)[:, None, None] * np.ones((1, W, 1))
    arr = np.array([8, 30, 70], np.float32) * (1.2 - yy * 0.6) + np.array([3, 6, 12], np.float32)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(img, "RGBA")
    prof = seafloor()
    for x in range(0, W, 4):
        d.rectangle((x, prof[x], x + 4, H), fill=(52, 44, 38))
    vents = [(300, 1480, 120), (620, 1440, 180), (840, 1500, 100)]
    glow_l = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(glow_l)
    for vx, vy, h in vents:
        d.polygon([(vx - 40, vy + 60), (vx - 14, vy - h), (vx + 14, vy - h), (vx + 40, vy + 60)], fill=(70, 58, 50))
        for j in range(8):                                                     # shimmering warm water rising
            ph = (t * 0.4 + j / 8) % 1
            yv = vy - h - ph * 520; r = 30 + 90 * ph
            gd.ellipse((vx - r, yv - r * 0.7, vx + r, yv + r * 0.7), fill=(255, 140, 60, int(95 * (1 - ph))))
        gd.ellipse((vx - 40, vy - h - 40, vx + 40, vy - h + 20), fill=(255, 150, 70, 120))
    gb = glow_l.filter(ImageFilter.GaussianBlur(26)); img.paste(gb, (0, 0), gb)
    d = ImageDraw.Draw(img, "RGBA")
    rng = np.random.default_rng(4)
    for i in range(90):                                                         # hydrogen bubbles
        vx, vy, h = vents[i % 3]
        ph = (t * rng.uniform(0.15, 0.3) + rng.random()) % 1
        x = vx + rng.normal(0, 30) + 20 * math.sin(t * 2 + i); y = vy - h - ph * 1100
        r = rng.uniform(3, 8)
        d.ellipse((x - r, y - r, x + r, y + r), outline=(200, 230, 255, int(200 * (1 - ph))), width=2)
    tag(d, "SCIENTIFIC VISUALIZATION  ·  possible seafloor vents")
    if t >= ws(14, 3):
        chip(d, 70, 300, "H₂ IN THE PLUME", "hints at hot water–rock reactions", seg(t, ws(14, 3), ws(14, 3) + 0.35), GREEN, 870)
    if t >= ws(14, 8):
        chip(d, 70, 430, "= CHEMICAL ENERGY", "the kind some Earth microbes use", seg(t, ws(14, 8), ws(14, 8) + 0.35), YELLOW, 870)
    return img

def sc_phos(t, t0, t1):
    k = seg(t, t0, t1)
    ering_at = ws(15, 18) - 0.3
    if t < ering_at:
        arr = limb_plume(t + 6, 1300, 2050, strength=0.7, saturn=False)
        img = finish(arr * 0.45, 0.2)
        img = grains(img, t, 1.0, amount=0.4)
        d = ImageDraw.Draw(img, "RGBA")
        a = seg(t, ws(15, 3) - 0.2, ws(15, 3) + 0.2)
        if a > 0:
            s = 1 + 0.25 * max(0, 1 - (t - ws(15, 3) + 0.2) / 0.14)
            x0, y0, sz = SAFE_CX - 170 * s, 470, 340 * s
            d.rounded_rectangle((x0, y0, x0 + sz, y0 + sz), 26, fill=(30, 20, 10, int(220 * a)), outline=(255, 190, 90, int(255 * a)), width=6)
            d.text((x0 + 30 * s, y0 + 30 * s), "15", font=font(F_UI, 46 * s), fill=(255, 210, 150, int(255 * a)), anchor="lt")
            d.text((x0 + sz / 2, y0 + sz * 0.55), "P", font=font(F_CAP, 190 * s), fill=(255, 190, 90, int(255 * a)), anchor="mm")
            d.text((x0 + sz / 2, y0 + sz * 0.88), "PHOSPHORUS", font=font(F_UI, 34 * s), fill=(255, 225, 180, int(255 * a)), anchor="mm")
        if t >= ws(15, 7):
            sub(d, SAFE_CX, 900, "essential to life as we know it", (255, 225, 190), 30, int(255 * seg(t, ws(15, 7), ws(15, 7) + 0.3)))
        if t >= ws(15, 13):
            sub(d, SAFE_CX, 960, "found as phosphates in ice grains (2023)", (220, 230, 245), 26, int(255 * seg(t, ws(15, 13), ws(15, 13) + 0.3)))
        tag(d, "CASSINI DATA, ANALYSED 2023  ·  illustration", YELLOW)
        return img
    # Saturn with the faint, wide E ring fed by Enceladus
    q = seg(t, ering_at, t1)
    base = stars_half().copy()
    base = ence.render_saturn(WR, HR, 540 * RS, 900 * RS, 140 * RS, tilt=12, light=(-0.5, 0.25, 0.83), base=base, gain=0.95)
    img = finish(up(base), 0.3)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for r in np.linspace(330, 470, 30):
        a = int(60 * math.exp(-((r - 410) / 60) ** 2) * ease(seg(t, ering_at, ering_at + 0.8)))
        d.ellipse((540 - r, 900 - r * 0.21, 540 + r, 900 + r * 0.21), outline=(170, 200, 255, a), width=8)
    lb = lay.filter(ImageFilter.GaussianBlur(8)); img.paste(lb, (0, 0), lb)
    d = ImageDraw.Draw(img, "RGBA")
    ang = (t - ering_at) * 1.2 + 2.2
    ex, ey = 540 + 410 * math.cos(ang), 900 + 410 * 0.21 * math.sin(ang)
    for j in range(16):                                                         # trail of plume material feeding the ring
        a2 = ang - j * 0.05
        x, y = 540 + 410 * math.cos(a2), 900 + 410 * 0.21 * math.sin(a2)
        d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(200, 225, 255, int(200 * (1 - j / 16))))
    d.ellipse((ex - 10, ey - 10, ex + 10, ey + 10), fill=(250, 250, 255))
    sub(d, ex, ey - 34, "Enceladus", (240, 245, 255), 24)
    pop(d, SAFE_CX, 360, "SATURN'S E RING", 96, t - ering_at, (170, 210, 255))
    sub(d, SAFE_CX, 450, "made of ice from Enceladus's plumes", (220, 230, 245), 27)
    tag(d, "SCIENTIFIC VISUALIZATION  ·  not to scale")
    return img

def sc_saturn_tiny(t, t0, t1):
    k = seg(t, t0, t1)
    base = stars_half().copy()
    base = ence.render_saturn(WR, HR, 600 * RS, 820 * RS, lerp(420, 450, ease(k)) * RS, tilt=20, light=(-0.6, 0.3, 0.75), base=base, gain=1.0)
    a = ence.render_enceladus(WR, HR, 200 * RS, 1150 * RS, 26 * RS, light=(-0.6, 0.3, 0.75), lat0=-10, base=base)
    a = ence.plumes(a, t, 200 * RS, 1150 * RS, 26 * RS, -10, 0, strength=0.5, height=1.4)
    img = finish(up(a), 0.35); d = ImageDraw.Draw(img, "RGBA"); tag(d, "SCIENTIFIC VISUALIZATION  ·  sizes to scale, distance not")
    d.ellipse((200 - 46, 1150 - 46, 200 + 46, 1150 + 46), outline=(255, 255, 255, 160), width=3)
    sub(d, 200, 1225, "Enceladus", (230, 240, 255), 24)
    if t >= ws(17, 2):
        ag = t - ws(17, 2)
        pop(d, SAFE_CX, 330, "NOT ALIENS", 140, ag, WHITE, 12)
        sub(d, SAFE_CX, 430, "no life has been found there", (255, 200, 190), 30)
    return img

def under_ice(t, depth=0.0, snow=1.0, vent_glow=0.0):
    """Dark ocean beneath the ice shell. depth 0 = just below the ice ceiling, 1 = deep."""
    yy = np.linspace(0, 1, H)[:, None, None] * np.ones((1, W, 1))
    ceil = clamp(1 - depth * 1.4, 0, 1)
    xx = np.linspace(-1, 1, W)[None, :, None]
    arr = (np.array([4, 14, 32], np.float32) + np.array([20, 60, 100], np.float32) * np.clip(1 - yy * 2.0, 0, 1) * ceil
           + np.array([10, 30, 55], np.float32) * np.exp(-(xx ** 2 / 0.5 + (yy - 0.55) ** 2 / 0.12)))
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(img, "RGBA")
    if ceil > 0:                                                                 # undulating ice ceiling
        pts = [(x, 160 * ceil + 40 * math.sin(x * 0.006 + 1) + 22 * math.sin(x * 0.019 + t * 0.2) - 200 * (1 - ceil)) for x in range(0, W + 20, 20)]
        d.polygon([(0, 0)] + pts + [(W, 0)], fill=(int(60 * ceil), int(90 * ceil), int(120 * ceil)))
        d.line(pts, fill=(int(120 * ceil), int(170 * ceil), int(210 * ceil), 200), width=3)
    if vent_glow > 0:
        gl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(gl)
        gd.ellipse((540 - 460, H - 220, 540 + 460, H + 300), fill=(255, 120, 50, int(120 * vent_glow)))
        gb = gl.filter(ImageFilter.GaussianBlur(70)); img.paste(gb, (0, 0), gb); d = ImageDraw.Draw(img, "RGBA")
    rng = np.random.default_rng(17)
    for i in range(int(260 * snow)):                                             # drifting particles (no creatures)
        x0 = rng.uniform(0, W); y0 = rng.uniform(0, H); sp = rng.uniform(8, 30)
        x = (x0 + 6 * math.sin(t * 0.5 + i)) % W; y = (y0 - t * sp) % H
        r = rng.uniform(1.2, 3.6); a = int(rng.uniform(70, 190))
        d.ellipse((x - r, y - r, x + r, y + r), fill=(170, 200, 230, a))
    return img

def sc_ingredients(t, t0, t1):
    k = seg(t, t0, t1)
    img = under_ice(t, depth=0.2 + 0.2 * k, snow=0.8, vent_glow=0.3)
    d = ImageDraw.Draw(img, "RGBA")
    tag(d, "SCIENTIFIC VISUALIZATION  ·  beneath the ice")
    tw = ws(18, 2)
    if t >= tw:
        pop(d, SAFE_CX, 360, "THE INGREDIENTS", 104, t - tw, YELLOW)
        pop(d, SAFE_CX, 470, "FOR LIFE", 104, t - tw - 0.1, YELLOW)
    items = [("Liquid water", True), ("Salts", True), ("Organic molecules", True), ("Chemical energy", True), ("Phosphorus", True), ("Life itself: not found", False)]
    for i, (txt, ok) in enumerate(items):
        ti = tw + 0.4 + i * 0.55
        a = seg(t, ti, ti + 0.25)
        if a <= 0: continue
        y = 640 + i * 100; aa = int(255 * a)
        col = GREEN if ok else (255, 170, 150)
        d.ellipse((110, y - 26, 162, y + 26), outline=col + (aa,), width=4)
        if ok: d.line((122, y, 133, y + 12, 152, y - 12), fill=col + (aa,), width=6)
        else: d.text((136, y), "?", font=font(F_CAP, 40), fill=col + (aa,), anchor="mm")
        d.text((190, y), txt, font=font(F_UI, 46), fill=(255, 255, 255, aa) if ok else col + (aa,), anchor="lm", stroke_width=5, stroke_fill=BLACK)
    return img

def sc_dark(t, t0, t1, txts=(), depth=(0.0, 0.5), vent=(0.0, 0.0), loop=False):
    k = seg(t, t0, t1)
    img = under_ice(t, depth=lerp(depth[0], depth[1], ease(k)), snow=1.0, vent_glow=lerp(vent[0], vent[1], k))
    d = ImageDraw.Draw(img, "RGBA")
    tag(d, "SCIENTIFIC VISUALIZATION  ·  no creatures shown, none are known")
    for txt, size, col, cue, y in txts:
        if t >= cue: pop(d, SAFE_CX, y, txt, size, t - cue, col)
    if loop:                                                                     # light from above: back toward the opening plume
        q = ease_in(seg(t, DUR - 0.8, DUR))
        if q > 0:
            img = Image.blend(img, finish(limb_plume(1.5, 1300, 2600, lat0=4, light=(0.0, -0.35, -0.9), strength=2.4, height=0.95,
                                                     sat_xy=(800, 330), sat_R=150), 0.55), q)
    return img

def sc_samples(t, t0, t1):
    return sc_backlit(t, t0, t1, R=520, cy=900, sat=True, txt=("OCEAN SAMPLES", 96, ws(21, 5), ICE), strength=1.7, lat0=-8)

# ------------------------------------------------------------------ timeline
def scenes():
    return [
        (0.0, HOOK_END, lambda t: sc_hook(t)),
        (HOOK_END, ls(2) - 0.1, lambda t: sc_flyby(t, HOOK_END, ls(2) - 0.1, chipcue=("REAL MISSION", "Cassini dove through the plume · 2008–2015", ws(1, 2)))),
        (ls(2) - 0.1, ls(4) - 0.1, lambda t: sc_meet(t, ls(2) - 0.1, ls(4) - 0.1)),
        (ls(4) - 0.1, ls(5) - 0.1, lambda t: sc_lifeless(t, ls(4) - 0.1, ls(5) - 0.1)),
        (ls(5) - 0.1, ls(6) - 0.1, lambda t: sc_cutaway(t, ls(5) - 0.1, ls(6) - 0.1)),
        (ls(6) - 0.1, ls(7) - 0.1, lambda t: sc_descent(t, ls(6) - 0.1, ls(7) - 0.1)),
        (ls(7) - 0.1, ls(8) - 0.1, lambda t: sc_stripes(t, ls(7) - 0.1, ls(8) - 0.1)),
        (ls(8) - 0.1, ws(8, 3) - 0.1, lambda t: sc_stripes(t, ls(8) - 0.1, ws(8, 3) - 0.1, erupt_from=ls(8), view="oblique")),
        (ws(8, 3) - 0.1, ls(9) - 0.1, lambda t: sc_backlit(t, ws(8, 3) - 0.1, ls(9) - 0.1, txt=("ERUPTING INTO SPACE", 84, ws(8, 8), ICE))),
        (ls(9) - 0.1, ls(10) - 0.1, lambda t: sc_flyby(t, ls(9) - 0.1, ls(10) - 0.1, path=((-150, 700), (1250, 1150)), scale=44, chipcue=("SAMPLED IN FLIGHT", "mass spectrometer + dust analyser", ws(9, 7)))),
        (ls(10) - 0.1, ls(14) - 0.1, lambda t: sc_found(t, ls(10) - 0.1, ls(14) - 0.1)),
        (ls(14) - 0.1, ls(15) - 0.1, lambda t: sc_vents(t, ls(14) - 0.1, ls(15) - 0.1)),
        (ls(15) - 0.1, ls(16) - 0.1, lambda t: sc_phos(t, ls(15) - 0.1, ls(16) - 0.1)),
        (ls(16) - 0.1, ls(18) - 0.1, lambda t: sc_saturn_tiny(t, ls(16) - 0.1, ls(18) - 0.1)),
        (ls(18) - 0.1, ls(19) - 0.1, lambda t: sc_ingredients(t, ls(18) - 0.1, ls(19) - 0.1)),
        (ls(19) - 0.1, ls(21) - 0.1, lambda t: sc_dark(t, ls(19) - 0.1, ls(21) - 0.1, txts=(("NO SUNLIGHT", 104, (150, 200, 255), ws(19, 6), 380),
                                                                                         ("KM OF ICE ABOVE", 76, ICE, ws(20, 4), 500)), depth=(0.0, 0.35))),
        (ls(21) - 0.1, ls(22) - 0.1, lambda t: sc_samples(t, ls(21) - 0.1, ls(22) - 0.1)),
        (ls(22) - 0.1, DUR + 1, lambda t: sc_dark(t, ls(22) - 0.1, DUR, txts=(("IS THERE LIFE", 110, WHITE, ws(23, 0), 380),
                                                                             ("BELOW?", 150, YELLOW, ws(23, 3), 520)), depth=(0.4, 1.0), vent=(0.0, 0.6), loop=True)),
    ]
SCENES = scenes()

yy_, xx_ = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1 - 0.32 * (((xx_ - W / 2) / (W / 2)) ** 2 + ((yy_ - H / 2) / (H / 2)) ** 2) ** 1.6).clip(0.5, 1)[..., None]
del yy_, xx_
GRN = np.random.default_rng(3)
GRAIN = [GRN.normal(0, 3.2, (H // 2, W // 2, 1)).astype(np.float32).repeat(2, 0).repeat(2, 1) for _ in range(4)]

def frame(fi):
    t = fi / FPS
    for a, b, fn in SCENES:
        if a <= t < b:
            img = fn(t); break
    for a, b, fn in SCENES[1:]:                           # 2-frame light flash on cuts (motivated: camera whip)
        if 0 <= t - a < 0.067:
            img = Image.blend(img.convert("RGB"), Image.new("RGB", (W, H), (225, 238, 255)), 0.22 * (1 - (t - a) / 0.067))
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
def hiss(dur, seed=1, lo=1500, hi=9000):
    rng = np.random.default_rng(seed); n = int(dur * SR); tt = np.arange(n) / SR
    x = bp(rng.normal(0, 1, n), lo, hi) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.6 * tt))
    return x * np.minimum(1, tt / 0.3) * np.minimum(1, (dur - tt) / 0.4)

def rumble(dur, seed=3):
    rng = np.random.default_rng(seed); n = int(dur * SR); tt = np.arange(n) / SR
    return (lp(rng.normal(0, 1, n), 110) * 3 + osc(36, n, "sin") * 0.4) * np.minimum(1, tt / 0.6) * np.minimum(1, (dur - tt) / 0.6)

def creak(dur=1.4, seed=5):
    rng = np.random.default_rng(seed); n = int(dur * SR); tt = np.arange(n) / SR
    f = 90 + 40 * np.sin(2 * np.pi * 0.7 * tt) + rng.normal(0, 3, n).cumsum() * 0.002
    return lp(osc(f, n), 900) * (np.sin(np.pi * tt / dur) ** 2) * (0.6 + 0.4 * (rng.random(n) > 0.995))

def ping(f=1800, dur=0.9):
    n = int(dur * SR); tt = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * tt) + 0.4 * np.sin(2 * np.pi * f * 1.5 * tt)) * np.exp(-tt / 0.25)

def shimmer(dur, seed=4):
    rng = np.random.default_rng(seed); n = int(dur * SR); tt = np.arange(n) / SR; out = np.zeros(n)
    for f in (1318.5, 1567.98, 1975.5, 2637.0):
        out += np.sin(2 * np.pi * f * tt + rng.uniform(0, 6)) * (0.5 + 0.5 * np.sin(2 * np.pi * rng.uniform(0.1, 0.4) * tt))
    return out / 4 * np.minimum(1, tt / 0.8) * np.minimum(1, (dur - tt) / 0.8)

def score(n):
    tt = np.arange(n) / SR
    chords = [(0, [55.0, 82.41, 130.81, 164.81]), (ls(2), [65.41, 98.0, 164.81, 196.0]), (ls(5), [58.27, 87.31, 146.83, 174.61]),
              (ls(9), [55.0, 82.41, 138.59, 164.81]), (ls(14), [61.74, 92.5, 146.83, 185.0]), (ls(16), [51.91, 77.78, 123.47, 155.56]),
              (ls(18), [65.41, 98.0, 164.81, 196.0]), (ls(19), [49.0, 73.42, 116.54, 146.83]), (ls(22), [46.25, 69.3, 110.0, 138.59])]
    pad = np.zeros(n)
    for ci, (t0, notes) in enumerate(chords):
        t1 = chords[ci + 1][0] if ci + 1 < len(chords) else DUR
        i0, i1 = int(t0 * SR), min(n, int(t1 * SR) + int(0.8 * SR)); m = i1 - i0
        sg = np.zeros(m)
        for f in notes:
            for det in (-0.12, 0.0, 0.11): sg += osc(f * 2 ** (det / 12), m)
        e = np.minimum(1, np.arange(m) / (0.8 * SR)) * np.minimum(1, (m - np.arange(m)) / (0.8 * SR))
        pad[i0:i1] += sg * e / 12
    pad = lp(pad, 1000) * 0.7 + lp(pad, 360) * 0.6
    sub_ = osc(41.2, n, "sin") * 0.22
    pulse = np.zeros(n); t = ls(9)
    while t < ls(16):
        place(pulse, boom(0.45, 72, 42, 0.11), t, 0.4); place(pulse, boom(0.35, 60, 40, 0.09), t + 0.23, 0.22); t += 60 / 84
    lvl = np.interp(tt, [0, 0.1, HOOK_END, ls(5), ls(16), ws(17, 2) - 0.05, ws(17, 2) + 0.05, ls(18), ls(19), DUR - 1.2, DUR],
                    [0.75, 0.8, 0.8, 0.85, 0.9, 1.0, 0.15, 0.6, 0.75, 0.9, 0.6])
    return (pad + sub_ + pulse) * lvl

def render_audio(out):
    n = int(DUR * SR)
    mus = score(n); fx = np.zeros(n)
    place(fx, reverb(boom(2.6, 120, 24, 0.9), 3.0, 0.4), 0.0, 1.4)                              # frame-0 impact
    place(fx, hiss(HOOK_END + 0.3, 2, 2000, 10000) * 1.2, 0.0, 0.9)                            # rushing ice particles
    place(fx, whoosh(1.2), 0.0, 0.6); place(fx, riser(HOOK_END, 120) * 0.5, 0.0, 0.3)
    place(fx, whoosh(0.9), HOOK_END - 0.2, 0.55)                                               # into the flyby
    place(fx, hiss(ls(2) - HOOK_END, 3) * 0.7, HOOK_END, 0.6)
    m = int((ls(2) - HOOK_END) * SR); tt = np.arange(m) / SR
    place(fx, osc(70 * (1.2 - 0.4 * tt / tt[-1]), m, "sin") * np.sin(np.pi * tt / tt[-1]) * 0.6, HOOK_END, 0.5)  # doppler hum
    place(fx, reverb(boom(1.8, 80, 30, 0.6), 3.0, 0.45), ws(2, 1), 0.85)                        # "Enceladus"
    place(fx, tick(1300), ws(3, 1), 0.35)
    place(fx, reverb(boom(1.4, 70, 30, 0.5)), ws(4, 7), 0.5)
    place(fx, creak(1.6, 6), ws(5, 2), 0.5); place(fx, reverb(boom(1.6, 75, 28, 0.6)), ws(5, 2), 0.6)  # cutaway opens
    place(fx, rumble(ls(7) - ls(6)) * 0.4, ls(6), 0.7); place(fx, creak(1.4, 8), ls(6) + 1.0, 0.45)  # descent through ice
    place(fx, reverb(boom(1.8, 85, 28, 0.6), 3.0, 0.5), ws(6, 7), 0.75)                          # "global ocean"
    place(fx, reverb(crack(0.8) * 0.6 + 0), 3.0, 0.4) if False else None
    place(fx, reverb(boom(1.4, 90, 34, 0.45)), ws(7, 6), 0.6)                                   # cracks
    place(fx, hiss(ls(9) - ls(8) + 0.3, 9) * 1.1, ls(8), 0.9); place(fx, reverb(boom(2.0, 100, 26, 0.7), 3.0, 0.45), ws(8, 8), 0.8)  # eruption
    place(fx, whoosh(1.0), ls(9) - 0.2, 0.55); place(fx, hiss(ls(10) - ls(9), 11) * 0.6, ls(9), 0.6)
    for li in (11, 12, 13): place(fx, ping(1500 + 250 * (li - 11)), ws(li, 0), 0.4); place(fx, reverb(boom(1.0, 90, 40, 0.3)), ws(li, 0), 0.45)
    place(fx, rumble(ls(15) - ls(14) + 0.5, 12), ls(14) - 0.1, 0.9)                             # vents
    m = int((ls(15) - ls(14)) * SR); rng = np.random.default_rng(3); bub = np.zeros(m)
    for i in range(60):
        i0 = rng.integers(0, m - 4000); f = rng.uniform(300, 900); L = 3000
        bub[i0:i0 + L] += np.sin(2 * np.pi * np.cumsum(np.linspace(f, f * 1.6, L)) / SR) * np.exp(-np.arange(L) / 800)
    place(fx, bub * 0.25, ls(14), 1.0)
    place(fx, ping(2200, 1.2), ws(15, 3) - 0.2, 0.45); place(fx, reverb(boom(1.6, 85, 30, 0.5)), ws(15, 3) - 0.2, 0.6)
    place(fx, whoosh(0.8), ws(15, 18) - 0.4, 0.4); place(fx, shimmer(3.0, 7), ws(15, 18) - 0.3, 0.25)
    place(fx, reverb(boom(2.8, 110, 22, 1.0), 3.5, 0.5), ws(17, 2), 1.3)                         # "NOT"
    place(fx, shimmer(ls(19) - ls(18), 9), ls(18), 0.3)
    for i in range(6): place(fx, tick(1100 + 90 * i), ws(18, 2) + 0.4 + 0.55 * i, 0.3)
    place(fx, rumble(DUR - ls(19), 14) * 0.5, ls(19), 0.7)
    for tc in (ls(19) + 0.6, ls(20) + 0.5, ls(22) + 1.5): place(fx, creak(1.8, int(tc)), tc, 0.4)
    place(fx, hiss(ls(22) - ls(21), 15) * 0.7, ls(21), 0.7)
    place(fx, reverb(boom(2.4, 70, 22, 0.9), 3.5, 0.5), ws(23, 0), 0.8)
    place(fx, riser(0.9, 140), DUR - 0.9, 0.5)                                                   # back toward the plume (loop)
    vo = np.zeros(n)
    for l in TIM:
        s, _ = sf.read(l["file"]); place(vo, s, l["start"])
    vo = lp(hp(vo, 85), 13000); vo = vo / (np.abs(vo).max() + 1e-9) * 0.9
    env = lp(np.abs(vo), 7); env /= env.max() + 1e-9
    duck = 1 - 0.62 * np.clip(env * 3, 0, 1)
    mix = vo + mus * 0.11 * duck + fx * 0.30 * (0.45 + 0.55 * duck)
    mix = np.tanh(mix * 1.05) * 0.95
    sf.write(out, np.stack([mix, mix], 1).astype(np.float32), SR, subtype="FLOAT")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        render_video(None, [float(x) for x in sys.argv[2:]])
    elif len(sys.argv) > 1 and sys.argv[1] == "audio":
        render_audio("mix.wav"); print("audio done", DUR)
    else:
        render_audio("mix.wav"); print("audio done", flush=True)
        render_video("video.mp4"); print("video done", flush=True)
