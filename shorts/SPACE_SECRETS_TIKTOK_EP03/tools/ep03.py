#!/usr/bin/env python3
# SPACE SECRETS — TikTok EP03: "The Planet Where It Rains Glass" (HD 189733 b), ~86 s vertical documentary.
# Visuals: procedural exoplanet (planet.py), procedural K-dwarf star (star.py), Earth from Solar System Scope textures
# (CC BY 4.0, NASA-based) for scale, particle/volumetric simulations. Audio: Kokoro VO + original synthesized score/SFX.
import json, math, re, subprocess, sys
from multiprocessing import Pool

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

import earth, planet, star
from sfx import SR, lp, hp, bp, envx, place, osc, boom, crack, whoosh, tick, riser, reverb, arng

W, H, FPS = 1080, 1920, 30
TIM = json.load(open("timing.json"))
NARR_END = TIM[-1]["start"] + TIM[-1]["dur"]
DUR = round(NARR_END + 3.7, 1)
NF = int(DUR * FPS)
RS = 2 / 3                                      # planet / volumetric layers render at 720x1280, upscaled
WR, HR = int(W * RS), int(H * RS)
WT = {(l["line"], k): (s, e) for l in TIM for k, (w, s, e) in enumerate(l["words"])}
def ws(l, k): return WT[(l, k)][0]
def we(l, k): return WT[(l, k)][1]
def ls(l): return TIM[l]["start"]
def le(l): return TIM[l]["start"] + TIM[l]["dur"]

# scene boundaries, all keyed to the narration
S_A = le(0) + 0.25                 # smash cut: hook -> planet from darkness
S_B = ls(4) - 0.2                  # the blue world
S_C = ls(6) - 0.25                 # silicate haze
S_D = ls(8) - 0.25                 # superstorm
S_E = ls(10) - 0.15                # heat
S_F = ls(12) - 0.2                 # dive: no surface
S_G = ls(14) - 0.2                 # orbit + distance
S_G2 = ls(16) - 0.2                # observations
S_H = ls(17) - 0.25                # honesty: visualization
S_I = ls(18) - 0.25                # return + reveal
T_HIDE = ws(19, 6)                 # "hide"
T_FINAL = we(19, 9)                # "weather." -> final hit

def clamp(v, a, b): return max(a, min(b, v))
def seg(t, a, b): return clamp((t - a) / (b - a), 0.0, 1.0)
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
WHITE, YELLOW, BLACK, CYAN, ORANGE, RED = (255, 255, 255), (255, 212, 0), (0, 0, 0), (120, 210, 255), (255, 150, 60), (235, 60, 50)
ICE = (190, 235, 255)

# TikTok safe area: keep text inside x 60..960 (right-side buttons) and y 220..1500 (top tabs, bottom caption/UI).
SAFE_CX = 510

# ------------------------------------------------------------------ shared backgrounds
_BG = {}
def space_bg():
    if "space" not in _BG:
        rng = np.random.default_rng(31)
        st = earth.stars(WR, HR, seed=31, n=4200)
        neb = ndimage.gaussian_filter(rng.normal(0, 1, (HR // 4, WR // 4)), 9)
        neb = np.asarray(Image.fromarray(((neb / neb.std() * 0.5 + 0.5).clip(0, 1) * 255).astype(np.uint8)).resize((WR, HR), Image.BICUBIC), np.float32) / 255
        _BG["space"] = np.clip(st * 0.85 + (neb ** 2)[..., None] * np.array([10, 22, 55], np.float32), 0, 255)
    return _BG["space"]

def up(arr):                                     # 720x1280 float -> 1080x1920 float
    return np.asarray(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32)

def tone(arr):
    a = np.clip(arr, 0, None) / 255.0
    return np.clip(255 * (1 - np.exp(-a * 1.35)) / (1 - math.exp(-1.35)), 0, 255)

def glow(arr, amt=0.5, thr=150, rad=36):
    small = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
    hi = np.clip(np.asarray(small, np.float32) - thr, 0, None) * 1.8
    bl = np.asarray(Image.fromarray(np.clip(hi, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(rad / 4)).resize((W, H), Image.BILINEAR), np.float32)
    return arr + bl * amt

def to_img(arr): return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

def noise_tex(seed, shp, sig, aniso=(1, 1)):
    rng = np.random.default_rng(seed)
    n = ndimage.gaussian_filter(rng.normal(0, 1, shp).astype(np.float32), (sig * aniso[0], sig * aniso[1]), mode="wrap")
    return (n - n.min()) / (n.max() - n.min() + 1e-6)

def scroll_sample(tex, xs, ys):
    return ndimage.map_coordinates(tex, [ys % tex.shape[0], xs % tex.shape[1]], order=1, mode="wrap")

# ------------------------------------------------------------------ overlays
def tag(d, txt="SCIENTIFIC VISUALIZATION  ·  not real footage", col=CYAN):
    f = font(F_MONO, 24)
    d.rounded_rectangle((60, 196, 60 + f.getlength(txt) + 28, 240), 10, fill=(0, 0, 0, 150))
    d.ellipse((72, 212, 84, 224), fill=col)
    d.text((94, 218), txt, font=f, fill=(230, 230, 230), anchor="lm")

def credit(d, txt):
    d.text((SAFE_CX, 1528), txt, font=font(F_MONO, 20), fill=(175, 175, 175), anchor="mm", stroke_width=2, stroke_fill=BLACK)

def pop(d, x, y, txt, size, age, color=WHITE, sw=10, a=255):
    if age < 0: return
    s = size * (1 + 0.35 * max(0, 1 - age / 0.14))
    d.text((x, y), txt, font=font(F_CAP, s), fill=color + (a,), anchor="mm", stroke_width=sw, stroke_fill=BLACK)

def sub(d, x, y, txt, color=(225, 225, 225), size=30, a=255):
    d.text((x, y), txt, font=font(F_MONO, size), fill=color + (a,), anchor="mm", stroke_width=4, stroke_fill=BLACK)

def chip(d, x, y, title, body, k, color=CYAN):
    if k <= 0: return
    a = int(255 * k); dx = 40 * (1 - ease_out(k))
    f1, f2 = font(F_UI, 38), font(F_MONO, 27)
    w = max(f1.getlength(title), f2.getlength(body)) + 50
    d.rounded_rectangle((x + dx, y, x + dx + w, y + 112), 16, fill=(0, 0, 0, int(185 * k)), outline=color + (a,), width=3)
    d.text((x + dx + 25, y + 34), title, font=f1, fill=color + (a,), anchor="lm")
    d.text((x + dx + 25, y + 82), body, font=f2, fill=(235, 235, 235, a), anchor="lm")

def callout(d, x, y, tx, ty, title, body, k, color=WHITE, anchor="lb"):
    if k <= 0: return
    ex, ey = lerp(tx, x, ease_out(k)), lerp(ty, y, ease_out(k))
    d.line((tx, ty, ex, ey), fill=color, width=4)
    d.ellipse((tx - 10, ty - 10, tx + 10, ty + 10), outline=color, width=4)
    if k > 0.6:
        d.text((x, y), title, font=font(F_UI, 44), fill=color, anchor=anchor, stroke_width=5, stroke_fill=BLACK)
        if body:
            sy = y + 58 if anchor.endswith("t") else y + 10
            d.text((x, sy), body, font=font(F_MONO, 28), fill=(230, 230, 230), anchor=anchor[0] + "t", stroke_width=4, stroke_fill=BLACK)

def shake(t, t0, dur, amp):
    if not (t0 <= t < t0 + dur): return 0.0, 0.0
    k = 1 - (t - t0) / dur
    return amp * k * math.sin(t * 97), amp * k * math.cos(t * 83)

# ------------------------------------------------------------------ captions (series identity; TikTok safe area)
EMPH = {"GLASS", "GLASS.", "TEAR", "APART.", "EXISTS.", "HD", "189733", "B.", "BLUE", "OCEANS.", "SCORCHING", "SILICATE",
        "DROPLETS", "SIDEWAYS", "5,400", "MPH.", "FASTER", "HEAT?", "2,000°F.", "NO", "SOLID", "VIOLENT", "STRANGER.",
        "NIGHTMARE", "63", "LIGHT-YEARS", "HUBBLE", "EXTREME", "HAVEN'T", "POSSIBILITY", "PRETTIEST", "DEADLIEST", "WEATHER."}
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

def draw_caption(img, t, y=1390):
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

# ------------------------------------------------------------------ HOOK: glass shards rushing at the camera
NS = 320
SR_ = np.random.default_rng(7)
SH_X = SR_.uniform(-4.5, 4.5, NS); SH_Y = SR_.uniform(-8, 8, NS); SH_Z0 = SR_.uniform(0.3, 14, NS)
SH_S = SR_.uniform(0.07, 0.24, NS); SH_ROT = SR_.uniform(0, 2 * np.pi, NS); SH_SPIN = SR_.uniform(-6, 6, NS)
SH_SHAPE = [SR_.uniform(0.45, 1.0, 5) for _ in range(NS)]
SH_SPEED = 9.0
VPX, VPY, FOC = 560, 760, 520
CRACKS = [(0.30, 640, 720, 1.0, 11), (1.32, 330, 1140, 0.7, 23)]      # (time, x, y, size, seed) — "tear you apart"

def shard_layer(t):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    zs = (SH_Z0 - SH_SPEED * t) % 14 + 0.25
    order = np.argsort(-zs)
    for i in order:
        z = zs[i]; x, y = SH_X[i] + 0.5 * math.sin(t * 0.7 + i), SH_Y[i]
        px, py = VPX + FOC * x / z, VPY + FOC * y / z
        if not (-300 < px < W + 300 and -300 < py < H + 300): continue
        z2 = z + SH_SPEED * 0.05
        qx, qy = VPX + FOC * x / z2, VPY + FOC * y / z2
        s = FOC * SH_S[i] / z
        a = int(clamp(255 * (1.3 - z / 11), 30, 255))
        d.line((qx, qy, px, py), fill=(170, 220, 255, a // 3), width=max(1, int(s * 0.15)))
        rot = SH_ROT[i] + SH_SPIN[i] * t; shp = SH_SHAPE[i]
        pts = [(px + s * shp[k] * math.cos(rot + k * 1.257) * (1.9 if k % 2 == 0 else 0.8),
                py + s * shp[k] * math.sin(rot + k * 1.257) * (1.9 if k % 2 == 0 else 0.8)) for k in range(5)]
        d.polygon(pts, fill=(160, 215, 250, a // 2), outline=(240, 252, 255, a), width=max(1, int(s * 0.04)))
        if s > 18:
            d.line((pts[0], pts[2]), fill=(255, 255, 255, a // 2), width=max(1, int(s * 0.05)))
            d.ellipse((px - s * 0.12, py - s * 0.12, px + s * 0.12, py + s * 0.12), fill=(255, 255, 255, a))
    return img

def crack_layer(t):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    for t0, cx, cy, size, seed in CRACKS:
        if t < t0: continue
        k = ease_out(seg(t, t0, t0 + 0.12)); rng = np.random.default_rng(seed)
        a = int(255 * (1 - 0.5 * seg(t, t0 + 0.4, S_A)))
        for j in range(13):
            ang = j * 2 * math.pi / 13 + rng.uniform(-0.2, 0.2)
            L = size * rng.uniform(300, 900) * k; px, py = cx, cy; seg_n = 7
            for q in range(seg_n):
                ang += rng.uniform(-0.35, 0.35)
                nx_, ny_ = px + L / seg_n * math.cos(ang), py + L / seg_n * math.sin(ang)
                d.line((px, py, nx_, ny_), fill=(255, 255, 255, a), width=max(1, int(4 - q * 0.45)))
                if rng.random() < 0.35:
                    b = ang + rng.choice([-1, 1]) * rng.uniform(0.5, 1.1)
                    d.line((nx_, ny_, nx_ + 70 * size * math.cos(b), ny_ + 70 * size * math.sin(b)), fill=(255, 255, 255, a // 2), width=2)
                px, py = nx_, ny_
        for rr in (70, 150, 260):
            r = rr * size * k
            pts = [(cx + r * (1 + 0.15 * rng.uniform(-1, 1)) * math.cos(q * 0.45), cy + r * (1 + 0.15 * rng.uniform(-1, 1)) * math.sin(q * 0.45)) for q in range(15)]
            d.line(pts + [pts[0]], fill=(255, 255, 255, a // 2), width=2)
        d.ellipse((cx - 22 * size, cy - 22 * size, cx + 22 * size, cy + 22 * size), fill=(255, 255, 255, a))
    return img

HOOK_BG = None
def sc_hook(t):
    global HOOK_BG
    if HOOK_BG is None:
        n1 = noise_tex(3, (480, 270), 7); n2 = noise_tex(4, (480, 270), 2.5, (1, 3))
        HOOK_BG = (n1, n2)
    n1, n2 = HOOK_BG
    yy, xx = np.mgrid[0:480, 0:270].astype(np.float32)
    rad = np.sqrt((xx - VPX / 4) ** 2 + (yy - VPY / 4) ** 2)
    a = scroll_sample(n1, xx * 0.9 + t * 4, yy * 0.9 - t * 10) * 0.7 + scroll_sample(n2, xx + 30 * t, yy - 60 * t) * 0.3
    tunnel = np.clip(1 - rad / 330, 0, 1)
    v = (a * 0.8 + 0.25) * (0.35 + 0.9 * tunnel)
    bg = np.stack([v * 30, v * 75, v * 150], -1)
    bg = np.asarray(Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32)
    dx, dy = 0.0, 0.0
    for t0, *_ in CRACKS:
        sx, sy = shake(t, t0, 0.45, 26 if t0 < 1 else 18); dx += sx; dy += sy
    img = to_img(tone(glow(bg, 0.3)))
    sh = shard_layer(t)
    sh_bl = sh.filter(ImageFilter.GaussianBlur(5))
    img.paste(sh_bl, (int(dx), int(dy)), sh_bl); img.paste(sh, (int(dx), int(dy)), sh)
    cr = crack_layer(t); cb = cr.filter(ImageFilter.GaussianBlur(6))
    img.paste(cb, (0, 0), cb); img.paste(cr, (0, 0), cr)
    for t0, *_ in CRACKS:
        if t0 <= t < t0 + 0.12: img = Image.blend(img, Image.new("RGB", (W, H), (230, 245, 255)), 0.55 * (1 - (t - t0) / 0.12))
    d = ImageDraw.Draw(img, "RGBA")
    k = max(0.8, ease_back(seg(t, -0.06, 0.14)))
    d.text((SAFE_CX + dx, 430 + dy), "IT RAINS", font=font(F_CAP, 150 * k), fill=WHITE, anchor="mm", stroke_width=12, stroke_fill=BLACK)
    s = 1 + 0.3 * max(0, 1 - (t - CRACKS[0][0]) / 0.14) if t >= CRACKS[0][0] else 1
    d.text((SAFE_CX + dx, 600 + dy), "GLASS?!", font=font(F_CAP, 190 * k * s), fill=YELLOW, anchor="mm", stroke_width=14, stroke_fill=BLACK)
    tag(d)
    return img

# ------------------------------------------------------------------ planet helpers
LIGHT = (-0.62, 0.22, 0.75)
def planet_arr(t, cx, cy, R, lon_c=0.0, lat0=8.0, light=LIGHT, thermal=0.0, night_glow=0.12, base=None, gain=1.0):
    b = space_bg() if base is None else base
    a = planet.render(WR, HR, cx * RS, cy * RS, R * RS, lon_c - 1.2 * t, lat0, light=light, t=t, base=b,
                      thermal=thermal, night_glow=night_glow, gain=gain)
    return up(a)

def sc_reveal(t):                                     # S_A -> S_B : planet emerges from darkness, "Meet HD 189733 b"
    k = seg(t, S_A, S_B)
    # light swings from behind the planet (thin crescent) to three-quarter lit
    ang = lerp(2.75, 0.95, ease(seg(t, S_A, S_A + 5.5)))
    light = (-math.sin(ang) * 0.95, 0.22, math.cos(ang))
    R = lerp(330, 470, ease(k)); cy = lerp(900, 860, k)
    arr = planet_arr(t, 540, cy, R, light=light, gain=ease(seg(t, S_A, S_A + 0.6)) * 0.95 + 0.05)
    arr = star.draw_sun(arr, lerp(-120, -60, k), lerp(380, 340, k), 70, t, bright=0.9, corona=1.4) if t > S_A + 0.3 else arr
    img = to_img(tone(glow(arr, 0.45))); d = ImageDraw.Draw(img, "RGBA"); tag(d)
    if t < S_A + 0.08: img = Image.blend(img, Image.new("RGB", (W, H), WHITE), 0.6 * (1 - (t - S_A) / 0.08)); d = ImageDraw.Draw(img, "RGBA")
    if ws(2, 4) <= t < ws(3, 1):
        pop(d, SAFE_CX, 400, "IT'S REAL.", 120, t - ws(2, 4), WHITE)
    if t >= ws(3, 1):
        ag = t - ws(3, 1)
        d.rectangle((0, 0, W, H), fill=(0, 0, 0, 0))
        pop(d, SAFE_CX, 330, "HD 189733 b", 124, ag, YELLOW, 11)
        if ag > 0.3:
            sub(d, SAFE_CX, 420, "hot Jupiter  ·  confirmed exoplanet (2005)", (220, 230, 245), 30)
    credit(d, "Planet and star: scientifically informed visualization, not an image")
    return img

def sc_blue(t):                                       # S_B -> S_C : the beautiful blue world, then "not oceans"
    k = seg(t, S_B, S_C)
    R = lerp(470, 640, ease(k)); cx = lerp(540, 600, ease(k)); cy = lerp(860, 900, ease(k))
    arr = planet_arr(t, cx, cy, R, lon_c=20)
    ke = ease_out(seg(t, ws(4, 11), ws(4, 11) + 0.4))
    if ke > 0:                                        # Earth to scale (HD 189733 b ~ 1.13 Jupiter radii ~ 12.7 Earth radii)
        er = R / 12.7 * 1.0
        ex, ey = 230, 560
        e = earth.render(W, H, ex, ey, er, 10, -40, -40, sun=LIGHT)
        mask = (np.abs(e).sum(-1, keepdims=True) > 0)
        arr = np.where(mask, arr * (1 - ke) + e * ke, arr)
    img = to_img(tone(glow(arr, 0.35))); d = ImageDraw.Draw(img, "RGBA"); tag(d)
    if ke > 0:
        d.ellipse((230 - 60, 560 - 60, 230 + 60, 560 + 60), outline=(255, 255, 255, int(200 * ke)), width=3)
        d.text((230, 640), "EARTH, to scale", font=font(F_MONO, 26), fill=(255, 255, 255, int(255 * ke)), anchor="mt", stroke_width=3, stroke_fill=BLACK)
    if ws(4, 7) <= t < S_C:
        a = int(255 * (1 - seg(t, ws(5, 0), ws(5, 0) + 0.3)))
        if a > 0: pop(d, SAFE_CX, 330, "A BLUE WORLD", 112, t - ws(4, 7), (150, 210, 255), 10, a)
    if t >= ws(5, 7):
        ag = t - ws(5, 7)
        pop(d, SAFE_CX, 330, "NOT OCEANS", 128, ag, YELLOW, 11)
        if ag > 0.15:                                   # strike-through wave icon
            d.line((SAFE_CX - 330, 400, SAFE_CX + 330, 260), fill=(235, 60, 50, 230), width=12)
    credit(d, "Earth imagery: Solar System Scope (CC BY 4.0), NASA-based  ·  planet: visualization")
    return img

# ------------------------------------------------------------------ silicate haze close-up
NP = 1400
HZ = np.random.default_rng(12)
HP_X = HZ.uniform(-80, W + 80, NP); HP_Y = HZ.uniform(-80, H + 80, NP); HP_D = HZ.uniform(0.3, 1.0, NP)
NUC = np.stack([HZ.uniform(120, 960, 34), HZ.uniform(420, 1300, 34)], 1)
NUC_R = HZ.uniform(14, 46, 34)
HAZE_T = None

def haze_bg(t, push):
    global HAZE_T
    if HAZE_T is None:
        HAZE_T = [noise_tex(20 + i, (640, 360), s) for i, s in enumerate((24, 10, 4))]
    yy, xx = np.mgrid[0:HR // 2, 0:WR // 2].astype(np.float32)
    acc = np.zeros(xx.shape + (3,), np.float32)
    cols = [(10, 40, 120), (30, 95, 200), (90, 170, 255)]
    for i, (tx, c) in enumerate(zip(HAZE_T, cols)):
        sp = (i + 1) * 4.0
        z = 1 + push * (0.3 + 0.35 * i)
        v = scroll_sample(tx, (xx - 180) / z * 0.6 + sp * t, (yy - 320) / z * 0.6 - 2 * t)
        acc += (np.clip(v * 1.6 - 0.45, 0, 1) ** 1.5)[..., None] * np.array(c, np.float32) * (0.9 - 0.15 * i)
    grad = np.linspace(0.65, 1.2, yy.shape[0])[:, None, None]
    acc = acc * grad + np.array([4, 12, 35], np.float32)
    return np.asarray(Image.fromarray(np.clip(acc, 0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32)

def droplet(d, x, y, r, a=255):
    d.ellipse((x - r, y - r, x + r, y + r), fill=(120, 180, 240, int(a * 0.35)), outline=(220, 245, 255, a), width=max(2, int(r * 0.12)))
    d.ellipse((x - r * 0.75, y - r * 0.75, x + r * 0.55, y + r * 0.55), outline=(255, 255, 255, int(a * 0.25)), width=max(1, int(r * 0.08)))
    d.ellipse((x - r * 0.55, y - r * 0.6, x - r * 0.15, y - r * 0.25), fill=(255, 255, 255, int(a * 0.9)))
    d.arc((x - r * 0.8, y - r * 0.8, x + r * 0.8, y + r * 0.8), 20, 110, fill=(255, 255, 255, int(a * 0.5)), width=max(1, int(r * 0.07)))

def sc_haze(t):                                       # S_C -> S_D
    k = seg(t, S_C, S_D); push = ease(k)
    arr = haze_bg(t, push)
    form = ease(seg(t, ws(7, 6) - 0.2, ws(7, 6) + 1.4))        # "droplets" -> condensation
    img = to_img(tone(glow(arr, 0.25)))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    z = 1 + 0.35 * push
    px = (HP_X - 540) * z * (0.8 + 0.4 * HP_D) + 540 + (25 * t * HP_D) % 80
    py = (HP_Y - 900) * z * (0.8 + 0.4 * HP_D) + 900 + 8 * np.sin(t * 0.8 + HP_X * 0.01)
    if form > 0:                                        # particles get pulled into the nearest nucleus
        dd = (px[:, None] - NUC[None, :, 0]) ** 2 + (py[:, None] - NUC[None, :, 1]) ** 2
        j = np.argmin(dd, 1); near = np.sqrt(dd[np.arange(NP), j]) < 230
        px = np.where(near, lerp(px, NUC[j, 0], form * 0.95), px); py = np.where(near, lerp(py, NUC[j, 1], form * 0.95), py)
    for x, y, dep in zip(px, py, HP_D):
        r = 1.2 + 3.2 * dep
        d.ellipse((x - r, y - r, x + r, y + r), fill=(200, 235, 255, int(90 + 150 * dep)))
    if form > 0:
        for (nx_, ny_), r in zip(NUC, NUC_R):
            droplet(d, nx_, ny_, r * ease_out(form) * z, int(255 * form))
    lb = lay.filter(ImageFilter.GaussianBlur(3)); img.paste(lb, (0, 0), lb); img.paste(lay, (0, 0), lay)
    d = ImageDraw.Draw(img, "RGBA"); tag(d)
    if t >= ws(6, 4):
        pop(d, SAFE_CX, 320, "SCORCHING HAZE", 96, t - ws(6, 4), ORANGE, 9)
    if t >= ws(6, 9):
        callout(d, 110, 1240, 470, 1090, "SILICATE PARTICLES", "tiny grains of rock-forming minerals", seg(t, ws(6, 9), ws(6, 9) + 0.3), ICE, "lt")
    if t >= ws(7, 8):
        ag = t - ws(7, 8)
        d.rectangle((0, 250, W, 420), fill=(0, 0, 0, 0))
        pop(d, SAFE_CX, 440, "DROPLETS OF GLASS?", 88, ag, YELLOW, 9)
        sub(d, SAFE_CX, 515, "a possibility scientists propose · not observed", (210, 230, 255), 26)
    return img

# ------------------------------------------------------------------ superstorm (sideways glass rain)
STORM_T = None
NG = 520
GR_ = np.random.default_rng(44)
G_Y = GR_.uniform(-40, H + 40, NG); G_X0 = GR_.uniform(0, 1, NG); G_D = GR_.uniform(0.25, 1.0, NG)

def storm_bg(t, speed=1.0, tint=(1.0, 1.0, 1.0), horizon=None):
    global STORM_T
    if STORM_T is None:
        STORM_T = [noise_tex(60 + i, (360, 1440), s, (1, 9)) for i, s in enumerate((5, 2.5, 1.2))]
    yy, xx = np.mgrid[0:HR // 2, 0:WR // 2].astype(np.float32)
    acc = np.zeros(xx.shape + (3,), np.float32)
    cols = [(14, 50, 130), (40, 110, 210), (150, 205, 255)]
    for i, (tx, c) in enumerate(zip(STORM_T, cols)):
        v = scroll_sample(tx, xx * (1.2 - 0.25 * i) - speed * t * (150 + 260 * i), yy * (1.0 - 0.2 * i) + 40 * i)
        acc += (np.clip(v * 1.7 - 0.55, 0, 1) ** 1.3)[..., None] * np.array(c, np.float32) * (1.1 - 0.2 * i)
    if horizon is not None:                              # cloud deck below, darker sky above
        hy = horizon * yy.shape[0]
        sky = np.clip((hy - yy) / hy, 0, 1)[..., None]
        acc = acc * (1 - 0.7 * sky) + sky * np.array([3, 10, 30], np.float32)
    acc = acc * np.array(tint, np.float32) + np.array([3, 10, 28], np.float32)
    acc = ndimage.uniform_filter1d(acc, 9, axis=1)       # horizontal motion blur
    return np.asarray(Image.fromarray(np.clip(acc, 0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32)

def glass_rain(img, t, speed=1.0, ymin=-40, slant=0.12):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for y, x0, dep in zip(G_Y, G_X0, G_D):
        if y < ymin: continue
        v = speed * (1400 + 2600 * dep)
        x = (x0 * (W + 900) + v * t) % (W + 900) - 450
        L = 60 + 380 * dep * speed
        yy = y + slant * (x % 400)
        d.line((x - L, yy - slant * L, x, yy), fill=(190, 230, 255, int(70 + 150 * dep)), width=max(1, int(1 + 4 * dep)))
        if dep > 0.6: d.ellipse((x - 5 * dep, yy - 5 * dep, x + 5 * dep, yy + 5 * dep), fill=(255, 255, 255, int(220 * dep)))
    lb = lay.filter(ImageFilter.GaussianBlur(2)); img.paste(lb, (0, 0), lb); img.paste(lay, (0, 0), lay)
    return img

def sc_storm(t):                                      # S_D -> S_E
    sp = lerp(0.6, 1.6, ease(seg(t, S_D, ws(8, 9))))
    dx, dy = shake(t, ws(8, 11), 1.6, 9)
    arr = storm_bg(t, sp)
    img = to_img(tone(glow(arr, 0.3)))
    img = glass_rain(img, t, sp * 0.8)
    if dx: img = img.transform(img.size, Image.AFFINE, (1, 0, dx, 0, 1, dy))
    d = ImageDraw.Draw(img, "RGBA"); tag(d)
    if t >= ws(8, 5) and t < ws(8, 11):
        pop(d, SAFE_CX, 330, "SIDEWAYS", 130, t - ws(8, 5), WHITE)
    if t >= ws(8, 9):
        kk = ease_out(seg(t, ws(8, 9), ws(8, 11) + 0.15))
        mph = 5400 * kk
        d.rounded_rectangle((90, 250, 930, 520), 24, fill=(0, 0, 0, 165))
        d.text((SAFE_CX, 300), "WIND SPEED", font=font(F_MONO, 30), fill=(220, 230, 255), anchor="mm")
        s = 1 + 0.25 * max(0, 1 - (t - ws(8, 11) - 0.15) / 0.14) if t >= ws(8, 11) + 0.15 else 1
        d.text((SAFE_CX, 400), f"{int(round(mph, -1)):,} MPH", font=font(F_CAP, 128 * s), fill=YELLOW, anchor="mm", stroke_width=10, stroke_fill=BLACK)
        if kk >= 1:
            sub(d, SAFE_CX, 485, "≈ 8,700 km/h  ·  about 7× the speed of sound", (230, 240, 255), 27)
    if t >= ws(9, 0):
        kb = ease_out(seg(t, ws(9, 0), ws(9, 0) + 0.6))
        x0, y0, bw = 110, 1010, 800
        d.rounded_rectangle((x0 - 30, y0 - 70, x0 + bw + 30, y0 + 200), 18, fill=(0, 0, 0, 190))
        d.text((x0, y0 - 38), "EARTH'S FASTEST MEASURED WINDS  ≈ 300 mph", font=font(F_MONO, 25), fill=(230, 230, 230), anchor="lm")
        d.rectangle((x0, y0, x0 + bw * 300 / 5400 * kb + 6, y0 + 40), fill=(220, 220, 220))
        d.text((x0, y0 + 88), "HD 189733 b  ≈ 5,400 mph", font=font(F_MONO, 25), fill=YELLOW, anchor="lm")
        d.rectangle((x0, y0 + 112, x0 + bw * kb, y0 + 152), fill=YELLOW)
    return img

# ------------------------------------------------------------------ heat
def sc_heat(t):                                       # S_E -> S_F
    k = seg(t, S_E, S_F)
    th = ease(seg(t, ws(10, 2) - 0.2, ws(11, 4)))
    R = lerp(560, 700, ease(k)); cx, cy = lerp(640, 700, k), 980
    arr = planet_arr(t, cx, cy, R, lon_c=35, light=(-0.5, 0.15, 0.85), thermal=th, night_glow=0.12 + 0.3 * th)
    if th > 0.2:                                       # heat shimmer
        yy = np.arange(H)[:, None]
        off = (6 * th * np.sin(yy * 0.05 + t * 9)).astype(int)
        arr = np.take_along_axis(arr, (np.arange(W)[None, :] + off) % W, axis=1)[..., None].squeeze(-1) if False else np.stack([np.take_along_axis(arr[..., c], (np.arange(W)[None, :] + off) % W, axis=1) for c in range(3)], -1)
    img = to_img(tone(glow(arr, 0.45 + 0.3 * th, 140))); d = ImageDraw.Draw(img, "RGBA"); tag(d)
    if t >= ws(10, 2):
        pop(d, SAFE_CX, 330, "THE HEAT", 130, t - ws(10, 2), ORANGE)
    if t >= ws(11, 3):                                  # thermometer
        kk = ease_out(seg(t, ws(11, 3), ws(11, 9) + 0.2))
        x, y0, y1 = 120, 1250, 520
        d.rounded_rectangle((x - 26, y1 - 20, x + 26, y0 + 10), 26, fill=(0, 0, 0, 170), outline=(255, 255, 255, 200), width=3)
        d.ellipse((x - 46, y0 - 20, x + 46, y0 + 72), fill=(235, 70, 30), outline=WHITE, width=3)
        top = lerp(y0, y1 + 10, kk)
        d.rounded_rectangle((x - 14, top, x + 14, y0 + 20), 14, fill=(255, int(lerp(170, 70, kk)), 30))
        d.text((x + 50, top), f"{int(2000 * kk):,}°F", font=font(F_CAP, 64), fill=WHITE, anchor="lm", stroke_width=7, stroke_fill=BLACK)
        if kk >= 1:
            sub(d, x + 52, top + 62, "≈ 1,100 °C  ·  dayside", (255, 220, 190), 28)
            d.text((x + 52, top + 66), "", font=font(F_MONO, 10))
    credit(d, "Temperature colours: visualization based on Spitzer-era heat maps")
    return img

# ------------------------------------------------------------------ dive: no solid surface
DIVE_T = None
def sc_dive(t):                                       # S_F -> S_G
    global DIVE_T
    if DIVE_T is None:
        DIVE_T = [noise_tex(80 + i, (384, 384), s) for i, s in enumerate((14, 7, 3.5))]
    k = seg(t, S_F, S_G)
    yy, xx = np.mgrid[0:HR // 2, 0:WR // 2].astype(np.float32)
    cx, cy = WR / 4, HR / 4 * 0.9
    acc = np.zeros(xx.shape + (3,), np.float32); trans = np.ones(xx.shape, np.float32)
    depth = (t - S_F) * 1.1
    nl = 9
    for i in range(nl):                                # near -> far, front-to-back compositing
        zl = (i - (depth % 1.0)) + 0.6
        if zl <= 0.05: continue
        tx = DIVE_T[i % 3]
        v = scroll_sample(tx, (xx - cx) * zl * 0.9 + 97 * (i + math.floor(depth)), (yy - cy) * zl * 0.9 + 53 * (i + math.floor(depth)))
        dens = np.clip(v * 1.5 - 0.55, 0, 1) ** 1.4 * min(1.0, zl / 0.9) * (1 - zl / (nl + 0.6))
        deep = clamp(k * 1.1, 0, 1)
        col = np.array([lerp(60, 110, deep), lerp(120, 45, deep), lerp(220, 35, deep)], np.float32) * (1.15 - 0.08 * i)
        acc += (trans * dens)[..., None] * col
        trans *= 1 - dens * 0.85
    acc += trans[..., None] * np.array([lerp(8, 40, k), lerp(25, 6, k), lerp(60, 10, k)], np.float32)
    fl = 0.0
    for tf in (S_F + 2.3, ws(13, 6), ws(13, 7) + 0.25):          # lightning inside the cloud deck: "violent"
        if tf <= t < tf + 0.18: fl = max(fl, 1 - (t - tf) / 0.18)
    acc += fl * 120 * np.exp(-((xx - cx * 1.3) ** 2 + (yy - cy * 0.7) ** 2) / 9000)[..., None] * np.array([0.8, 0.9, 1.0])
    acc = ndimage.gaussian_filter(acc, (2.5, 2.5, 0))
    arr = np.asarray(Image.fromarray(np.clip(acc, 0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32)
    arr = arr * (1 + 0.2 * ease(seg(t, S_F, S_F + 1)))
    img = to_img(tone(glow(arr, 0.3))); d = ImageDraw.Draw(img, "RGBA"); tag(d)
    gx, g0, g1 = 90, 520, 1230                          # depth gauge
    d.line((gx, g0, gx, g1), fill=(255, 255, 255, 160), width=4)
    for j in range(8): d.line((gx - 12, lerp(g0, g1, j / 7), gx + 12, lerp(g0, g1, j / 7)), fill=(255, 255, 255, 120), width=3)
    my = lerp(g0, g1, ease(k))
    d.polygon([(gx + 16, my), (gx + 40, my - 14), (gx + 40, my + 14)], fill=YELLOW)
    d.text((gx + 50, my), "you", font=font(F_MONO, 26), fill=YELLOW, anchor="lm", stroke_width=3, stroke_fill=BLACK)
    d.text((gx - 10, g0 - 30), "DEPTH", font=font(F_MONO, 24), fill=(230, 230, 230), anchor="lm")
    d.text((gx - 10, g1 + 40), "pressure + heat rise", font=font(F_MONO, 24), fill=(255, 180, 140), anchor="lm", stroke_width=3, stroke_fill=BLACK)
    if t >= ws(12, 3):
        pop(d, SAFE_CX + 40, 330, "GAS GIANT", 120, t - ws(12, 3), (150, 210, 255))
    if t >= ws(12, 7):
        pop(d, SAFE_CX + 40, 470, "NO SOLID SURFACE", 82, t - ws(12, 7), YELLOW, 9)
    if t >= ws(13, 6):
        pop(d, SAFE_CX + 40, 600, "VIOLENT", 96, t - ws(13, 6), RED, 9)
    return img

# ------------------------------------------------------------------ orbit, distance, observations
def sc_orbit(t):                                      # S_G -> S_G2
    k = seg(t, S_G, S_G2)
    t_ly = ws(15, 6) - 0.3                               # "63 light-years": pull back to the distance view
    base = space_bg().copy()
    sx, sy = 430 * RS, 760 * RS
    q = ease(seg(t, t_ly, t_ly + 1.2))
    if q < 1:
        arr = base.copy()
        ang = (t - S_G) * 2.1 + 0.6
        ox, oy = 330 * math.cos(ang), 110 * math.sin(ang)
        px, py = (430 + ox) * RS, (760 + oy) * RS
        behind = math.sin(ang) < 0
        lx, ly = -ox / 330, oy / 110 * 0.4
        if behind: arr = planet.render(WR, HR, px, py, 34 * RS, 0, 5, light=(lx, ly, -0.3), t=t, base=arr)
        arr = up(arr)
        arr = star.draw_sun(arr, 430, 760, 120, t, bright=0.8, corona=1.3)
        if not behind:
            arr2 = planet.render(WR, HR, px, py, 34 * RS, 0, 5, light=(lx, -ly, 0.25), t=t, base=np.zeros((HR, WR, 3), np.float32))
            arr2 = up(arr2); m = arr2.sum(-1, keepdims=True) > 1
            arr = np.where(m, arr2, arr)
        arr = arr * (1 - q) + up(base) * q
        img = to_img(tone(glow(arr, 0.5)))
    else:
        img = to_img(tone(up(base)))
    d = ImageDraw.Draw(img, "RGBA"); tag(d)
    a = int(255 * (1 - q))
    if a > 0:
        for j in range(0, 360, 8):
            d.arc((430 - 330, 760 - 110, 430 + 330, 760 + 110), j, j + 4, fill=(255, 255, 255, int(a * 0.45)), width=2)
        if t >= ws(14, 3) - 0.1:
            pop(d, SAFE_CX, 330, "STRANGER...", 120, t - ws(14, 3) + 0.1, WHITE, 10, a)
        chip(d, 90, 990, "ORBIT: 2.2 DAYS", "~13× closer to its star than Mercury", seg(t, S_G + 0.5, S_G + 0.9) * (a / 255), ORANGE)
        if t >= ws(15, 1):
            pop(d, SAFE_CX, 470, "NIGHTMARE WORLD", 84, t - ws(15, 1), YELLOW, 9, a)
    if q > 0:                                            # distance line: us -> HD 189733
        aa = int(255 * q); y0, y1 = 1250, 430
        d.line((SAFE_CX, y0, SAFE_CX, y1), fill=(255, 212, 0, aa), width=4)
        for j in range(8): d.line((SAFE_CX - 14, lerp(y0, y1, j / 7), SAFE_CX + 14, lerp(y0, y1, j / 7)), fill=(255, 212, 0, aa), width=3)
        d.ellipse((SAFE_CX - 14, y0 - 14, SAFE_CX + 14, y0 + 14), fill=(255, 220, 120, aa))
        d.text((SAFE_CX + 30, y0), "the Sun (us)", font=font(F_MONO, 28), fill=(255, 255, 255, aa), anchor="lm", stroke_width=3, stroke_fill=BLACK)
        d.ellipse((SAFE_CX - 18, y1 - 18, SAFE_CX + 18, y1 + 18), fill=(90, 160, 255, aa), outline=WHITE, width=3)
        d.text((SAFE_CX + 34, y1), "HD 189733", font=font(F_MONO, 28), fill=(255, 255, 255, aa), anchor="lm", stroke_width=3, stroke_fill=BLACK)
        ly = 63 * ease_out(seg(t, t_ly, t_ly + 1.0))
        d.text((SAFE_CX - 40, (y0 + y1) / 2), f"{ly:.0f}", font=font(F_CAP, 150), fill=(255, 212, 0, aa), anchor="rm", stroke_width=11, stroke_fill=BLACK)
        d.text((SAFE_CX - 40, (y0 + y1) / 2 + 100), "LIGHT-YEARS", font=font(F_CAP, 46), fill=(255, 255, 255, aa), anchor="rm", stroke_width=6, stroke_fill=BLACK)
        sub(d, SAFE_CX, 1330, "in the constellation Vulpecula · \"only\" in cosmic terms", (210, 220, 240), 24, aa)
    return img

def sc_obs(t):                                        # S_G2 -> S_H : what was actually measured
    k = seg(t, S_G2, S_H)
    arr = planet_arr(t, 560, 1080, lerp(380, 430, ease(k)), lon_c=50)
    img = to_img(tone(glow(arr, 0.35))); d = ImageDraw.Draw(img, "RGBA")
    tag(d, "WHAT WAS ACTUALLY MEASURED", YELLOW)
    pop(d, SAFE_CX, 320, "REAL OBSERVATIONS", 84, t - S_G2, WHITE, 9)
    chip(d, 70, 400, "HUBBLE · 2013", "measured its deep-blue colour", seg(t, ws(16, 3), ws(16, 3) + 0.35), CYAN)
    chip(d, 70, 535, "SPITZER · 2007", "first temperature map of an exoplanet", seg(t, ws(16, 13), ws(16, 13) + 0.35), ORANGE)
    chip(d, 70, 670, "GROUND TELESCOPE · 2015", "winds of ~5,400 mph measured", seg(t, ws(16, 18), ws(16, 18) + 0.35), YELLOW)
    credit(d, "Planet: visualization  ·  results from NASA / ESA / published studies (see sources)")
    return img

def sc_honest(t):                                     # S_H -> S_I : glass rain as a labelled visualization
    arr = storm_bg(t, 0.9, tint=(0.95, 1.0, 1.1), horizon=0.42)
    img = to_img(tone(glow(arr, 0.3)))
    img = glass_rain(img, t, 0.7, ymin=300, slant=0.18)
    d = ImageDraw.Draw(img, "RGBA")
    tag(d, "VISUALIZATION  ·  NOT RECORDED FOOTAGE", YELLOW)
    if t >= ws(17, 1):
        pop(d, SAFE_CX, 340, "NEVER SEEN", 128, t - ws(17, 1), WHITE)
        sub(d, SAFE_CX, 430, "no one has observed glass rain there", (230, 230, 230), 28)
    if t >= ws(17, 10):
        kk = seg(t, ws(17, 10), ws(17, 10) + 0.3)
        chip(d, 90, 520, "A SCIENTIFIC POSSIBILITY", "based on conditions in its atmosphere", kk, YELLOW)
    return img

def sc_final(t):                                      # S_I -> DUR : pretty planet, then the storm beneath
    k = seg(t, S_I, T_HIDE)
    R = lerp(430, 520, ease(k)); cx, cy = 540, 900
    arr = planet_arr(t, cx, cy, R, lon_c=70, light=(-0.55, 0.3, 0.78), gain=1.05)
    rv = ease_out(seg(t, T_HIDE, T_HIDE + 1.0))
    if rv > 0:                                           # reveal the storm beneath the clouds inside the disk
        st = storm_bg(t, 1.3, tint=(1.1, 0.9, 0.9))
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        rr = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        lens = np.clip((R * 0.98 * rv - np.sqrt((xx - cx + R * 0.15) ** 2 + (yy - cy) ** 2)) / 8, 0, 1) * (rr < R * 0.985)
        arr = arr * (1 - lens[..., None] * 0.9) + st * lens[..., None] * 0.9
    dark = ease(seg(t, T_FINAL + 0.1, DUR - 0.2))
    arr = arr * (1 - 0.55 * dark)
    img = to_img(tone(glow(arr, 0.4)))
    if rv > 0:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); img2 = glass_rain(lay, t, 1.1, ymin=0)
        mk = Image.new("L", (W, H), 0); ImageDraw.Draw(mk).ellipse((cx - R * rv * 0.95 - R * 0.15, cy - R * rv * 0.95, cx + R * rv * 0.95 - R * 0.15, cy + R * rv * 0.95), fill=255)
        lay2 = Image.composite(img2, Image.new("RGBA", (W, H), (0, 0, 0, 0)), mk); img.paste(lay2, (0, 0), lay2)
    if T_FINAL <= t < T_FINAL + 0.1: img = Image.blend(img, Image.new("RGB", (W, H), WHITE), 0.5 * (1 - (t - T_FINAL) / 0.1))
    d = ImageDraw.Draw(img, "RGBA"); tag(d)
    if ws(18, 6) <= t < T_HIDE:
        pop(d, SAFE_CX, 330, "BEAUTIFUL...", 120, t - ws(18, 6), (150, 210, 255))
    if t >= T_HIDE:
        pop(d, SAFE_CX, 300, "PRETTIEST WORLDS", 80, t - T_HIDE, WHITE, 9)
        pop(d, SAFE_CX, 400, "DEADLIEST WEATHER", 82, t - T_FINAL, YELLOW, 9)
    if t >= T_FINAL + 0.8:
        a = int(255 * seg(t, T_FINAL + 0.8, T_FINAL + 1.4))
        d.text((SAFE_CX, 1560), "SPACE SECRETS · EP 03", font=font(F_MONO, 30), fill=(220, 220, 220, a), anchor="mm", stroke_width=3, stroke_fill=BLACK)
    return img

SCENES = [(0, S_A, sc_hook), (S_A, S_B, sc_reveal), (S_B, S_C, sc_blue), (S_C, S_D, sc_haze), (S_D, S_E, sc_storm),
          (S_E, S_F, sc_heat), (S_F, S_G, sc_dive), (S_G, S_G2, sc_orbit), (S_G2, S_H, sc_obs), (S_H, S_I, sc_honest),
          (S_I, DUR + 1, sc_final)]

yy_, xx_ = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1 - 0.35 * (((xx_ - W / 2) / (W / 2)) ** 2 + ((yy_ - H / 2) / (H / 2)) ** 2) ** 1.6).clip(0.45, 1)[..., None]
GRN = np.random.default_rng(3)
GRAIN = [GRN.normal(0, 3.5, (H // 2, W // 2, 1)).astype(np.float32).repeat(2, 0).repeat(2, 1) for _ in range(4)]
del yy_, xx_

def frame(fi):
    t = fi / FPS
    for a, b, fn in SCENES:
        if a <= t < b:
            img = fn(t); break
    for a, b, fn in SCENES[2:]:                       # quick light-leak flash at each cut (the hook cut has its own)
        if 0 <= t - a < 0.067:
            img = Image.blend(img.convert("RGB"), Image.new("RGB", (W, H), (230, 240, 255)), 0.25 * (1 - (t - a) / 0.067))
    arr = np.asarray(img.convert("RGB"), np.float32) * VIG + GRAIN[fi % 4]
    img = Image.fromarray(arr.clip(0, 255).astype(np.uint8))
    draw_caption(img, t)
    return img.tobytes()

def render_video(out, preview=None, tag_="pv"):
    if preview:
        import os; os.makedirs(tag_, exist_ok=True)
        for t in preview:
            Image.frombytes("RGB", (W, H), frame(int(round(t * FPS)))).resize((270, 480)).save(f"{tag_}/p_{int(t * 100):05d}.jpg", quality=85)
        return
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for i, b in enumerate(pool.imap(frame, range(NF), chunksize=3)):
            p.stdin.write(b)
            if i % 150 == 0: print("frame", i, "/", NF, flush=True)
    p.stdin.close(); p.wait()

# ------------------------------------------------------------------ audio
def glass_shatter(dur=1.2, seed=0):
    """Layered glass break: bright noise burst + many short ringing partials (shards) + tinkle tail."""
    rng = np.random.default_rng(seed); n = int(dur * SR); tt = np.arange(n) / SR
    out = hp(rng.normal(0, 1, n), 2500) * envx(n, 0.03) * 1.2
    for _ in range(46):
        f = rng.uniform(2200, 9500); t0 = rng.exponential(0.12); i0 = int(t0 * SR)
        if i0 >= n: continue
        m = n - i0; e = envx(m, rng.uniform(0.01, 0.08))
        out[i0:] += np.sin(2 * np.pi * f * np.arange(m) / SR) * e * rng.uniform(0.1, 0.4)
    return out * np.minimum(1, tt / 0.001)

def tinkle(dur, density=30, seed=1):
    rng = np.random.default_rng(seed); n = int(dur * SR); out = np.zeros(n)
    for _ in range(int(density * dur)):
        i0 = rng.integers(0, n - 2400); f = rng.uniform(3000, 9000); m = 2400
        out[i0:i0 + m] += np.sin(2 * np.pi * f * np.arange(m) / SR) * envx(m, rng.uniform(0.005, 0.02)) * rng.uniform(0.05, 0.25)
    return out

def windx(dur, bright=0.35, seed=2):
    rng = np.random.default_rng(seed); n = int(dur * SR); tt = np.arange(n) / SR; x = rng.normal(0, 1, n)
    g = 0.65 + 0.25 * np.sin(2 * np.pi * 0.37 * tt) + 0.15 * np.sin(2 * np.pi * 1.3 * tt + 1)
    body = lp(x, 700) * 1.2 + bp(x, 700, 4000) * bright
    return body * g * np.minimum(1, tt / 0.4) * np.minimum(1, (dur - tt) / 0.4)

def rumble(dur, f=38, seed=3):
    rng = np.random.default_rng(seed); n = int(dur * SR); tt = np.arange(n) / SR
    return (lp(rng.normal(0, 1, n), 120) * 3 + osc(f, n, "sin") * 0.5) * np.minimum(1, tt / 0.5) * np.minimum(1, (dur - tt) / 0.5)

def shimmer(dur, seed=4):
    """Crystalline pad: high sine partials with slow random amplitude."""
    rng = np.random.default_rng(seed); n = int(dur * SR); tt = np.arange(n) / SR; out = np.zeros(n)
    for f in (1318.5, 1567.98, 1975.5, 2637.0, 3135.96):
        out += np.sin(2 * np.pi * f * tt + rng.uniform(0, 6)) * (0.5 + 0.5 * np.sin(2 * np.pi * rng.uniform(0.1, 0.4) * tt + rng.uniform(0, 6)))
    return out / 5 * np.minimum(1, tt / 0.8) * np.minimum(1, (dur - tt) / 0.8)

def descend(dur, f0=220, f1=55):
    n = int(dur * SR); tt = np.arange(n) / SR
    f = f0 * (f1 / f0) ** (tt / dur)
    return lp(osc(f, n), 900) * 0.5 * np.minimum(1, tt / 0.3) * np.minimum(1, (dur - tt) / 0.5)

def score(n):
    tt = np.arange(n) / SR
    chords = [(0, [55.0, 82.41, 130.81, 164.81]), (S_B, [65.41, 98.0, 164.81, 196.0]),         # Am(add) -> C (wonder)
              (S_C, [58.27, 87.31, 138.59, 174.61]), (S_D, [55.0, 82.41, 130.81, 155.56]),     # tension
              (S_E, [51.91, 77.78, 123.47, 155.56]), (S_F, [49.0, 73.42, 116.54, 146.83]),
              (S_G, [55.0, 82.41, 130.81, 164.81]), (S_G2, [65.41, 98.0, 164.81, 196.0]),
              (S_H, [58.27, 87.31, 138.59, 174.61]), (S_I, [65.41, 98.0, 164.81, 196.0]), (T_HIDE, [51.91, 77.78, 123.47, 146.83])]
    pad = np.zeros(n)
    for ci, (t0, notes) in enumerate(chords):
        t1 = chords[ci + 1][0] if ci + 1 < len(chords) else DUR
        i0, i1 = int(t0 * SR), min(n, int(t1 * SR) + int(0.8 * SR)); m = i1 - i0
        sg = np.zeros(m)
        for f in notes:
            for det in (-0.12, 0.0, 0.11): sg += osc(f * 2 ** (det / 12), m)
        e = np.minimum(1, np.arange(m) / (0.8 * SR)) * np.minimum(1, (m - np.arange(m)) / (0.8 * SR))
        pad[i0:i1] += sg * e / 12
    pad = lp(pad, 1100) * 0.7 + lp(pad, 380) * 0.6
    sub = osc(41.2, n, "sin") * 0.25
    pulse = np.zeros(n); t = S_G
    while t < S_H:                                      # pulsing ambient score under orbit/distance
        place(pulse, boom(0.5, 70, 42, 0.12), t, 0.45); place(pulse, boom(0.4, 60, 40, 0.1), t + 0.24, 0.25); t += 60 / 72
    t = S_D
    while t < S_E:
        place(pulse, boom(0.4, 80, 45, 0.1), t, 0.4); t += 60 / 132
    lvl = np.interp(tt, [0, 0.05, S_A - 0.05, S_A + 0.1, S_A + 2, S_D, S_E, S_F, S_G, S_H, S_I, T_FINAL - 0.05, T_FINAL + 0.05, DUR],
                    [0.5, 0.6, 0.6, 0.3, 0.8, 0.9, 0.85, 0.8, 0.85, 0.8, 0.9, 1.0, 0.0, 0.0])
    return (pad + sub + pulse) * lvl

def render_audio(out):
    n = int(DUR * SR)
    mus = score(n); fx = np.zeros(n)
    # hook: glass rushing + cracks + sub impacts
    place(fx, tinkle(S_A, 70, 9) * np.linspace(1.0, 0.6, int(S_A * SR)), 0.0, 0.8)
    place(fx, whoosh(0.7), 0.0, 0.5)
    for t0, *_ in CRACKS:
        place(fx, glass_shatter(1.4, int(t0 * 10)), t0, 1.1 if t0 < 1 else 0.85)
        place(fx, reverb(boom(2.0, 110, 26, 0.6), 2.5, 0.35), t0, 1.2 if t0 < 1 else 0.8)
    place(fx, crack(0.5), S_A - 0.05, 0.5); place(fx, reverb(boom(2.5, 95, 24, 0.9), 3.0, 0.45), S_A, 1.0)      # smash cut
    place(fx, riser(S_B - S_A - 0.5, 55) * 0.8, S_A + 0.3, 0.55)                                               # deep rising drone
    place(fx, reverb(boom(1.8, 80, 30, 0.6), 3.0, 0.45), ws(2, 4), 0.7)                                        # "it's real"
    place(fx, reverb(boom(2.2, 70, 26, 0.8), 3.0, 0.5), ws(3, 1), 0.85)                                        # "HD 189733 b"
    place(fx, shimmer(S_C - S_B + 0.5) * 0.6, S_B, 0.35)                                                       # ethereal swell
    place(fx, tick(1200), ws(4, 11), 0.35); place(fx, reverb(boom(1.4, 80, 32, 0.4)), ws(5, 7), 0.65)
    place(fx, shimmer(S_D - S_C, 8), S_C, 0.45); place(fx, tinkle(S_D - S_C, 14, 5), S_C, 0.5)                 # crystalline
    place(fx, windx(S_D - S_C, 0.2, 7) * 0.5, S_C, 0.6)
    place(fx, tinkle(1.6, 90, 6), ws(7, 6), 0.7); place(fx, reverb(boom(1.6, 90, 34, 0.45)), ws(7, 8), 0.7)    # droplets form
    place(fx, whoosh(1.0), S_D - 0.3, 0.6); place(fx, windx(S_E - S_D + 0.3, 0.6, 11), S_D, 1.4)                # superstorm
    place(fx, tinkle(S_E - S_D, 40, 12), S_D, 0.55)
    place(fx, riser(ws(8, 11) - ws(8, 9) + 0.2, 110), ws(8, 9), 0.5)
    place(fx, reverb(boom(2.0, 100, 30, 0.6), 3.0, 0.45), ws(8, 11) + 0.15, 1.0)
    for i in range(3): place(fx, whoosh(0.45), ws(9, 0) + 0.25 * i, 0.35)
    place(fx, rumble(S_F - S_E + 0.4), S_E, 1.3); place(fx, reverb(boom(1.6, 70, 28, 0.6)), ws(10, 2), 0.75)     # heat
    place(fx, riser(ws(11, 9) - ws(11, 3), 60), ws(11, 3), 0.4); place(fx, reverb(boom(2.0, 85, 28, 0.7)), ws(11, 9) + 0.2, 0.9)
    place(fx, descend(S_G - S_F), S_F, 0.9); place(fx, windx(S_G - S_F, 0.3, 13) * 0.7, S_F, 0.9)               # dive
    for tf in (S_F + 2.3, ws(13, 6), ws(13, 7) + 0.25): place(fx, reverb(crack(1.2) + boom(1.2, 60, 26, 0.5) * 0.6, 2.5, 0.5), tf, 0.7)
    place(fx, reverb(boom(1.6, 90, 34, 0.5)), ws(12, 7), 0.7)
    place(fx, whoosh(0.8), S_G - 0.2, 0.4); place(fx, reverb(boom(1.6, 80, 30, 0.5)), ws(15, 1), 0.6)
    place(fx, whoosh(1.2), ws(15, 6) - 0.4, 0.5)
    for i in range(14): place(fx, tick(900 + 40 * i), ws(15, 6) - 0.3 + 0.07 * i, 0.25)
    for w_ in (3, 13, 18): place(fx, tick(1500), ws(16, w_), 0.4)
    place(fx, windx(S_I - S_H, 0.4, 15) * 0.7, S_H, 0.9); place(fx, tinkle(S_I - S_H, 25, 16), S_H, 0.45)
    place(fx, reverb(boom(1.4, 70, 30, 0.5)), ws(17, 1), 0.6)
    place(fx, shimmer(T_HIDE - S_I + 0.5, 21), S_I, 0.45)                                                       # pretty...
    place(fx, windx(T_FINAL - T_HIDE, 0.6, 17), T_HIDE, 1.2); place(fx, glass_shatter(1.0, 77), T_HIDE, 0.5)   # storm beneath
    place(fx, reverb(boom(3.5, 110, 22, 1.2), 4.0, 0.5), T_FINAL, 1.5); place(fx, glass_shatter(1.6, 78), T_FINAL, 0.7)  # final hit
    ring = osc(2960, int(2.5 * SR), "sin") * envx(int(2.5 * SR), 1.0) * np.minimum(1, np.arange(int(2.5 * SR)) / (0.2 * SR))
    place(fx, ring, T_FINAL + 0.3, 0.035)                                                                       # eerie silence
    vo = np.zeros(n)
    for l in TIM:
        s, _ = sf.read(l["file"]); place(vo, s, l["start"])
    vo = lp(hp(vo, 85), 13000); vo = vo / (np.abs(vo).max() + 1e-9) * 0.9
    env = lp(np.abs(vo), 7); env /= env.max() + 1e-9
    duck = 1 - 0.62 * np.clip(env * 3, 0, 1)
    mix = vo + mus * 0.12 * duck + fx * 0.30 * (0.45 + 0.55 * duck)
    mix = np.tanh(mix * 1.05) * 0.95
    sf.write(out, np.stack([mix, mix], 1).astype(np.float32), SR, subtype="FLOAT")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        ts = [float(x) for x in sys.argv[2:]] or [0.0, 0.2, 0.4, 1.4, 2.0, 3.2, 6.5, 9.5, 13.0, 15.5, 18.0, 21.8, 26.5, 29.5,
                                                    32.6, 35.5, 40.0, 43.2, 47.0, 51.9, 54.8, 58.4, 62.0, 66.8, 69.0, 72.0, 77.0,
                                                    81.0, 82.6, 85.5]
        render_video(None, ts)
    elif len(sys.argv) > 1 and sys.argv[1] == "audio":
        render_audio("mix.wav"); print("audio done")
    else:
        render_audio("mix.wav"); print("audio done", flush=True)
        render_video("video.mp4"); print("video done", flush=True)
