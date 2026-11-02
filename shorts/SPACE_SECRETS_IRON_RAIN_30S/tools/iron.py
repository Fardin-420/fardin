#!/usr/bin/env python3
# SPACE SECRETS — "A Planet Where It Rains Iron?!" (WASP-76 b) — 30 s native 1080x1920 renderer.
# Usage: python3 iron.py stills t... | preview t0 t1 out.mp4 | final | audio out.wav
import json, math, os, re, subprocess, sys
from multiprocessing import Pool
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

import star
from sfx import SR, lp, hp, bp, place, osc, boom, crack, whoosh, tick, riser, reverb, arng

W, H, FPS = 1080, 1920, 30
star.W, star.H = W, H
TIM = json.load(open("timing.json"))
def ls(i): return TIM[i]["start"]
def le(i): return TIM[i]["start"] + TIM[i]["dur"]
def ws(i, k): return TIM[i]["words"][k][1]
NARR_END = le(len(TIM) - 1)
DUR = 30.0
NF = int(DUR * FPS)

def clamp(v, a, b): return max(a, min(b, v))
def seg(t, a, b): return clamp((t - a) / (b - a), 0.0, 1.0) if b > a else float(t >= a)
def ease(x): x = clamp(x, 0, 1); return x * x * (3 - 2 * x)
def ease_out(x): x = clamp(x, 0, 1); return 1 - (1 - x) ** 3
def ease_io(x): x = clamp(x, 0, 1); return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2
def lerp(a, b, k): return a + (b - a) * k

_C = {}
def cache(k, fn):
    if k not in _C: _C[k] = fn()
    return _C[k]

def tone(a, exp=1.2):
    a = np.clip(a, 0, None) / 255.0
    return np.clip(255 * (1 - np.exp(-a * exp)) / (1 - math.exp(-exp)), 0, 255)
def glow(arr, amt=0.45, thr=160, rad=36):
    small = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
    hi = np.clip(np.asarray(small, np.float32) - thr, 0, None) * 1.8
    bl = np.asarray(Image.fromarray(np.clip(hi, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(rad / 4)).resize((W, H), Image.BILINEAR), np.float32)
    return arr + bl * amt
def finish(arr, g=0.45, exp=1.2): return Image.fromarray(np.clip(tone(glow(arr, g), exp), 0, 255).astype(np.uint8))
def to_img(a): return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

def blackbody(x):                                                               # 0 = deep red ... 1 = yellow-white
    xp = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    return np.stack([np.interp(x, xp, [18, 120, 225, 255, 255, 255]), np.interp(x, xp, [2, 18, 70, 140, 205, 245]),
                     np.interp(x, xp, [1, 4, 12, 40, 110, 200])], -1).astype(np.float32)

def stars():
    def make():
        rng = np.random.default_rng(76)
        a = np.zeros((H, W, 3), np.float32) + np.array([2, 2, 4], np.float32)
        n = 3800; ys = rng.uniform(0, H - 1, n); xs = rng.uniform(0, W - 1, n); b = rng.pareto(2.4, n) * 40 + 12
        iy, ix = ys.astype(int), xs.astype(int); fy, fx = ys - iy, xs - ix
        for dy, dx, w in ((0, 0, (1 - fy) * (1 - fx)), (0, 1, (1 - fy) * fx), (1, 0, fy * (1 - fx)), (1, 1, fy * fx)):
            np.add.at(a, (np.clip(iy + dy, 0, H - 1), np.clip(ix + dx, 0, W - 1)), (b * w)[:, None] * np.array([1, 0.97, 1.03]))
        return ndimage.gaussian_filter(a, (0.5, 0.5, 0))
    return cache("stars", make)

# ------------------------------------------------------------------ volumetric atmosphere plates (native, scrolled — never enlarged)
def noise_plate(seed, sig, h=2600, w=1500):
    rng = np.random.default_rng(seed)
    a = ndimage.gaussian_filter(rng.normal(0, 1, (h, w)).astype(np.float32), sig, mode="wrap")
    return a / (a.std() + 1e-6)
def atmo():
    def make():
        big = noise_plate(1, 60) * 0.6 + noise_plate(2, 22) * 0.3 + noise_plate(3, 7) * 0.12
        mid = noise_plate(4, 34) * 0.6 + noise_plate(5, 12) * 0.3 + noise_plate(6, 3) * 0.1
        return big.astype(np.float32), mid.astype(np.float32)
    return cache("atmo", make)

def atmosphere(t, heat=1.0, speed=1.0, swirl=1.0, gain=0.5):
    """Emissive turbulent haze: two layers drifting at different speeds (parallax)."""
    big, mid = atmo()
    y1 = int((t * 70 * speed) % 600); x1 = int((t * 22 * speed) % 300)
    y2 = int((t * 180 * speed) % 600); x2 = int((t * 50 * speed + 100) % 300)
    a = big[y1:y1 + H, x1:x1 + W]; b = mid[y2:y2 + H, x2:x2 + W]
    f = np.clip(0.30 + 0.26 * a + 0.18 * b * swirl, 0, 1) ** 1.6
    yy = np.linspace(0, 1, H)[:, None]
    f = f * (0.75 + 0.35 * (1 - yy))
    col = blackbody(np.clip(f * (0.55 + 0.45 * heat), 0, 1)) * (0.35 + 0.65 * heat) * gain
    return col

# ------------------------------------------------------------------ molten iron droplets
def droplets(arr, t, n=90, seed=7, heat=1.0, fall=1.0, zmin=0.6, zmax=4.0, big=None, focus=1.4):
    """Glowing liquid-iron droplets in 3D: perspective size, depth of field, motion elongation, specular highlight."""
    rng = np.random.default_rng(seed)
    X = rng.uniform(-1.2, 1.2, n); Y0 = rng.uniform(-2.0, 2.0, n); Z = rng.uniform(zmin, zmax, n)
    rad = rng.uniform(0.018, 0.05, n); vel = rng.uniform(0.25, 0.5, n) * fall; ph = rng.uniform(0, 6.28, n)
    if big is not None:
        X = np.append(X, big[0]); Y0 = np.append(Y0, big[1]); Z = np.append(Z, big[2]); rad = np.append(rad, big[3])
        vel = np.append(vel, big[4]); ph = np.append(ph, 0.0)
    f = 900.0
    layers = {}
    order = np.argsort(-Z)
    for i in order:
        y = ((Y0[i] + vel[i] * t + 2.0) % 4.0) - 2.0
        sx = W / 2 + X[i] / Z[i] * f + 18 * math.sin(t * 1.3 + ph[i]); sy = H / 2 + y / Z[i] * f
        r = rad[i] / Z[i] * f
        if r < 1.2 or sx < -3 * r or sx > W + 3 * r or sy < -4 * r or sy > H + 4 * r: continue
        blur = abs(Z[i] - focus) / focus * 9
        key = min(4, int(blur / 2.2))
        lay = layers.setdefault(key, np.zeros((H, W, 3), np.float32))
        el = 1 + 0.35 * min(1.0, vel[i] * 1.8)                                    # slight teardrop stretch along the fall
        bx0, bx1 = int(max(0, sx - r * 3.0)), int(min(W, sx + r * 3.0)); by0, by1 = int(max(0, sy - r * el * 3.0)), int(min(H, sy + r * el * 3.0))
        if bx1 <= bx0 or by1 <= by0: continue
        ys, xs = np.mgrid[by0:by1, bx0:bx1].astype(np.float32)
        nx = (xs - sx) / r; ny = (ys - sy) / (r * el); d2 = nx * nx + ny * ny
        m = d2 < 1
        if not m.any(): continue
        nz = np.sqrt(np.clip(1 - d2, 0, 1))
        core = blackbody(np.clip(0.30 + 0.38 * nz * heat, 0, 1)) * (0.55 + 0.45 * heat)
        rim = (1 - nz) ** 2.5
        spec = np.clip(-nx * 0.45 - ny * 0.55 + nz * 0.7, 0, 1) ** 36 * 1.1
        c = core * (0.55 + 0.6 * nz)[..., None] + rim[..., None] * np.array([255, 120, 40], np.float32) * 0.5 * heat + spec[..., None] * 255
        edge = np.clip((1 - np.sqrt(d2)) * r / 1.2, 0, 1)[..., None]
        sub = lay[by0:by1, bx0:bx1]
        lay[by0:by1, bx0:bx1] = np.maximum(sub, c * edge * m[..., None])
        halo = np.exp(-np.clip(np.sqrt(d2) - 1, 0, None) * 4.5) * (1 - m)
        lay[by0:by1, bx0:bx1] += halo[..., None] * np.array([255, 110, 30], np.float32) * 0.25 * heat
    for key, lay in sorted(layers.items(), reverse=True):
        if key > 0: lay = ndimage.gaussian_filter(lay, (key * 2.2, key * 2.2, 0))
        arr = arr * (1 - np.clip(lay.max(-1, keepdims=True) / 255 * 0.9, 0, 0.9)) + lay
    return arr

# ------------------------------------------------------------------ WASP-76 b: ultra-hot gas giant, 4096x2048 procedural texture
def planet_tex():
    def make():
        rng = np.random.default_rng(76)
        h, w = 2048, 4096
        def nz(sy, sx):
            a = ndimage.gaussian_filter(rng.normal(0, 1, (h // 2, w // 2)).astype(np.float32), (sy / 2, sx / 2), mode="wrap")
            a = np.asarray(Image.fromarray(a).resize((w, h), Image.BICUBIC), np.float32); return a / (a.std() + 1e-6)
        lat = np.linspace(90, -90, h)[:, None] * np.ones((1, w), np.float32)
        warp = nz(16, 160) * 2.4 + nz(6, 48) * 0.8 + nz(2, 12) * 0.25
        la = lat + warp
        v = 0.5 + 0.18 * np.sin(np.radians(la) * 8 + 0.3) + 0.1 * np.sin(np.radians(la) * 19 + 1.1) + 0.05 * np.sin(np.radians(la) * 41)
        v += 0.08 * nz(3, 100) + 0.05 * nz(10, 200) + 0.03 * nz(1.5, 6)
        return np.clip(v, 0, 1).astype(np.float32)
    return cache("ptex", make)

def planet(arr, cx, cy, R, lon_c, lat0, light, t=0.0, night=0.18, flow=1.0, hot=1.0):
    T = planet_tex(); th, tw = T.shape
    ext = R * 1.06
    x0, x1 = int(max(0, cx - ext)), int(min(W, cx + ext)); y0, y1 = int(max(0, cy - ext)), int(min(H, cy + ext))
    if x1 <= x0 or y1 <= y0: return arr
    ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    nx = (xs - cx) / R; ny = (cy - ys) / R; r2 = nx * nx + ny * ny; r = np.sqrt(r2)
    L = np.array(light, np.float32); L /= np.linalg.norm(L)
    sub = arr[y0:y1, x0:x1]
    lit_out = np.clip((nx * L[0] + ny * L[1]) / np.maximum(r, 1e-3) * 0.9 + 0.4, 0, 1.4)
    sub += (np.exp(-np.clip(r - 1, 0, None) / 0.025) * (r >= 1) * lit_out)[..., None] * np.array([255, 140, 60], np.float32) * 0.8
    m = r2 < 1
    if m.any():
        nxm, nym = nx[m], ny[m]; nzm = np.sqrt(1 - r2[m])
        c0, s0 = math.cos(math.radians(lat0)), math.sin(math.radians(lat0))
        X = nxm; Y = nym * c0 + nzm * s0; Z = -nym * s0 + nzm * c0
        lat = np.degrees(np.arcsin(np.clip(Y, -1, 1))); lonv = np.degrees(np.arctan2(X, Z))
        lon = lonv + lon_c + flow * t * (6.0 * np.cos(np.radians(lat) * 2))
        v = (90 - lat) / 180 * (th - 1); u = ((lon + 180) % 360) / 360 * tw
        tv = ndimage.map_coordinates(T, [v, u], order=1, mode="wrap")
        ndl = nxm * L[0] + nym * L[1] + nzm * L[2]
        day = np.clip((ndl + 0.08) / 0.35, 0, 1)
        temp = np.clip(0.26 + 0.44 * np.clip(ndl, 0, 1) ** 0.7 * hot + 0.22 * (tv - 0.5), 0, 1)
        c = blackbody(temp) * (0.2 + 0.62 * day)[:, None] * (0.7 + 0.6 * tv)[:, None]
        c += ((1 - day) * night * (0.4 + 0.8 * tv))[:, None] * np.array([150, 30, 10], np.float32)
        c += ((1 - nzm) ** 3 * (0.3 + day))[:, None] * np.array([255, 150, 70], np.float32) * 0.5
        edge = np.clip((1 - np.sqrt(r2[m])) * R / 1.5, 0, 1)[:, None]
        sub[m] = sub[m] * (1 - edge) + c * edge
    arr[y0:y1, x0:x1] = sub
    return arr

def wind_streaks(arr, t, cx, cy, R, lat0, light, n=520, seed=3, amt=1.0, col=(255, 210, 150), spark=0.0):
    """Iron-vapour streaks flowing over the sphere from the substellar point toward the night side (visualized)."""
    rng = np.random.default_rng(seed)
    lay = Image.new("L", (W, H), 0); d = ImageDraw.Draw(lay)
    sp = Image.new("L", (W, H), 0); ds = ImageDraw.Draw(sp)
    L = np.array(light, np.float32); L /= np.linalg.norm(L)
    up = np.array([0, 1, 0], np.float32); e1 = np.cross(up, L); e1 /= np.linalg.norm(e1) + 1e-6; e2 = np.cross(L, e1)
    th0 = rng.uniform(0, 2 * np.pi, n); ph0 = rng.uniform(0, 1, n); sp_ = rng.uniform(0.6, 1.2, n)
    c0, s0 = math.cos(math.radians(lat0)), math.sin(math.radians(lat0))
    for i in range(n):
        u = (ph0[i] + t * 0.12 * sp_[i]) % 1.0
        pts = []
        for k in range(6):
            a = (u - k * 0.012) * math.pi * 0.95                                    # angle from the substellar point
            th = th0[i] + 0.55 * a * (1 if i % 2 else -1)                            # Coriolis-like curl
            p = L * math.cos(a) + (e1 * math.cos(th) + e2 * math.sin(th)) * math.sin(a)
            p = p * 1.012
            if p[2] < 0.05: break
            pts.append((cx + p[0] * R, cy - p[1] * R))
        if len(pts) > 1:
            fade = min(1, u / 0.08, (1 - u) / 0.15)
            d.line(pts, fill=int(120 * fade * (1 - 0.5 * u)), width=2)
            if spark > 0 and u > 0.55:                                             # condensation on the cool side (conceptual)
                x, y = pts[0]; s = 2.2
                ds.ellipse((x - s, y - s, x + s, y + s), fill=int(255 * spark * fade))
    g = np.asarray(lay.filter(ImageFilter.GaussianBlur(1.8)), np.float32)[..., None] / 255
    arr = arr + g * np.array(col, np.float32) * amt
    if spark > 0:
        s = np.asarray(sp.filter(ImageFilter.GaussianBlur(0.8)), np.float32)[..., None] / 255
        arr = arr + s * np.array([255, 150, 70], np.float32) * 1.4
    return arr

# ------------------------------------------------------------------ text
F_CAP = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
F_UI = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
F_MONO = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf"
_F = {}
def font(p, s):
    k = (p, int(s))
    if k not in _F: _F[k] = ImageFont.truetype(p, max(1, int(s)))
    return _F[k]
WHITE, YELLOW, BLACK, ORANGE = (255, 255, 255), (255, 212, 0), (0, 0, 0), (255, 150, 70)
def tag(d, txt, col=(255, 160, 90)):
    f = font(F_MONO, 22)
    d.rounded_rectangle((60, 196, 60 + f.getlength(txt) + 28, 236), 10, fill=(0, 0, 0, 160))
    d.ellipse((72, 210, 84, 222), fill=col); d.text((94, 216), txt, font=f, fill=(235, 235, 235), anchor="lm")
def label(d, x, y, title, body=None, a=255, col=WHITE, size=36):
    if a <= 0: return
    d.text((x, y), title, font=font(F_UI, size), fill=col + (a,), anchor="mm", stroke_width=5, stroke_fill=BLACK)
    if body: d.text((x, y + size + 6), body, font=font(F_MONO, 22), fill=(230, 230, 232, a), anchor="mm", stroke_width=4, stroke_fill=BLACK)

# ====================================================================== shots
SUNL = (-0.88, 0.22, 0.42)

def sc_hook(t):
    """Extreme macro: glowing liquid iron droplets forming and falling through turbulent incandescent haze."""
    arr = atmosphere(t, heat=0.85, speed=1.6, swirl=1.4, gain=0.6)
    arr = droplets(arr, t * 1.25, n=110, seed=7, heat=1.0, fall=1.2, zmin=0.5, zmax=3.5, focus=1.1,
                   big=(0.05, -0.15, 0.62, 0.05, 0.22))
    img = finish(arr, 0.55); d = ImageDraw.Draw(img, "RGBA")
    k = max(0.85, 1.15 - 0.3 * seg(t, 0, 0.12))
    d.text((540, 300), "IT RAINS", font=font(F_CAP, 132 * k), fill=WHITE, anchor="mm", stroke_width=12, stroke_fill=BLACK)
    d.text((540, 432), "IRON?!", font=font(F_CAP, 150 * k), fill=YELLOW, anchor="mm", stroke_width=12, stroke_fill=BLACK)
    tag(d, "SCIENTIFIC RECONSTRUCTION  ·  not actual footage")
    return img

def sc_reveal(t, t0, t1):
    """Orbital tracking: the inflated gas giant skims its F-type star (orbit 1.8 days)."""
    u = ease_io(seg(t, t0, t1))
    arr = stars().copy()
    arr = star.draw_sun(arr, lerp(-160, -120, u), lerp(560, 640, u), 640, t, bright=1.05, corona=1.1) * np.array([1.0, 1.0, 1.04], np.float32) + 0
    px, py, R = lerp(760, 700, u), lerp(1200, 1080, u), lerp(250, 320, u)
    arr = planet(arr, px, py, R, lon_c=20 * u, lat0=12, light=(-0.95, 0.25, lerp(0.15, 0.3, u)), t=t)
    img = finish(arr, 0.5); d = ImageDraw.Draw(img, "RGBA")
    q = seg(t, ws(1, 1) - 0.1, ws(1, 1) + 0.3)
    label(d, 540, 330, "WASP-76 b", "ultra-hot gas giant · ~640 light-years · one orbit = 1.8 days", int(255 * q), YELLOW, 64)
    tag(d, "CGI RECONSTRUCTION  ·  not a photograph")
    return img

def sc_dayside(t, t0, t1):
    """Close over the permanent dayside: incandescent bands, iron vapour streaming outward."""
    u = ease_io(seg(t, t0, t1))
    arr = stars().copy()
    R = 1000; cx, cy = lerp(700, 640, u), lerp(1500, 1440, u)
    L = (-0.25, 0.35, 0.9)
    arr = planet(arr, cx, cy, R, lon_c=-10 + 12 * u, lat0=20, light=L, t=t * 3, hot=1.15)
    arr = wind_streaks(arr, t, cx, cy, R, 20, L, n=520, amt=0.55, col=(255, 190, 120))
    img = finish(arr, 0.55); d = ImageDraw.Draw(img, "RGBA")
    q = seg(t, ws(2, 4) - 0.15, ws(2, 4) + 0.3)
    label(d, 540, 330, "DAYSIDE: OVER 2,400 °C", "≈ 4,350 °F · hot enough to vaporize iron", int(255 * q), ORANGE, 52)
    tag(d, "CGI RECONSTRUCTION  ·  vapour flow visualized")
    return img

def sc_terminator(t, t0, t1):
    """The camera follows the vapour across the terminator into the cooler night side; droplets begin to form."""
    u = ease_io(seg(t, t0, t1))
    arr = stars().copy()
    R = 1000; cx, cy = 540, 1520
    L = (lerp(-0.2, -0.95, u), 0.3, lerp(0.9, 0.05, u))                           # we swing round toward the night side
    arr = planet(arr, cx, cy, R, lon_c=lerp(-10, 75, u), lat0=24, light=L, t=t * 3, night=0.22)
    arr = wind_streaks(arr, t, cx, cy, R, 24, L, n=480, amt=0.8, spark=seg(t, ws(4, 7) - 1.2, ws(4, 7) + 0.2))
    img = finish(arr, 0.55); d = ImageDraw.Draw(img, "RGBA")
    q = seg(t, ws(3, 7) - 0.2, ws(3, 7) + 0.3)
    label(d, 540, 330, "TOWARD THE COOLER NIGHT SIDE", "iron vapour carried by powerful winds (visualized)", int(255 * q), (255, 200, 150), 44)
    tag(d, "CGI RECONSTRUCTION  ·  vapour flow visualized")
    return img

def sc_night_rain(t, t0, t1):
    """Night side, inside the atmosphere: droplets condense and fall, cooling from orange to deep red."""
    u = seg(t, t0, t1)
    arr = atmosphere(t, heat=0.2, speed=0.6, swirl=0.8, gain=0.35)
    arr = droplets(arr, t, n=140, seed=19, heat=lerp(0.75, 0.55, u), fall=0.9, zmin=0.8, zmax=5.0, focus=1.8)
    img = finish(arr, 0.5); d = ImageDraw.Draw(img, "RGBA")
    k = seg(t, ws(5, 2) - 0.1, ws(5, 2) + 0.3)                                    # a forecast panel on "weather forecast"
    if k > 0:
        a = int(235 * k); x0, y0 = 120, 300
        d.rounded_rectangle((x0, y0, x0 + 840, y0 + 250), 26, fill=(10, 10, 16, int(200 * k)), outline=(255, 212, 0, a), width=3)
        d.text((x0 + 40, y0 + 52), "FORECAST · WASP-76 b · NIGHT SIDE", font=font(F_MONO, 24), fill=(255, 212, 0, a), anchor="lm")
        d.text((x0 + 40, y0 + 125), "MOLTEN IRON RAIN", font=font(F_CAP, 70), fill=(255, 255, 255, a), anchor="lm", stroke_width=6, stroke_fill=BLACK)
        d.text((x0 + 40, y0 + 200), "~1,400 °C after dark  ·  winds: extreme", font=font(F_MONO, 24), fill=(235, 235, 235, a), anchor="lm")
    tag(d, "SCIENTIFIC RECONSTRUCTION  ·  not actual footage")
    return img

def sc_single(t, t0, t1):
    """One droplet in extreme close-up, falling past the lens."""
    u = seg(t, t0, t1)
    arr = atmosphere(t, heat=0.25, speed=0.5, swirl=0.6, gain=0.3)
    arr = droplets(arr, t, n=50, seed=31, heat=0.6, fall=0.6, zmin=1.5, zmax=6.0, focus=0.5,
                   big=(0.0, lerp(-0.12, 0.04, u), 0.55, 0.1, 0.0))
    img = finish(arr, 0.5); d = ImageDraw.Draw(img, "RGBA")
    tag(d, "SCIENTIFIC RECONSTRUCTION  ·  based on ESPRESSO observations")
    return img

def sc_final(t, t0):
    """Pull back: the whole giant, half incandescent, half dark."""
    u = ease_out(seg(t, t0, DUR - 0.5))
    arr = stars().copy()
    R = lerp(900, 360, u); cx, cy = 540, lerp(1200, 960, u)
    arr = planet(arr, cx, cy, R, lon_c=35, lat0=15, light=(-1.0, 0.08, 0.02), t=t * 3, night=0.24)
    arr = wind_streaks(arr, t, cx, cy, R, 15, (-1.0, 0.08, 0.02), n=260, amt=0.5, spark=0.5)
    img = finish(arr, 0.5); d = ImageDraw.Draw(img, "RGBA")
    k = seg(t, ws(7, 2) - 0.1, ws(7, 2) + 0.4)
    if k > 0:
        s = max(0.9, ease_out(k))
        d.text((540, 300), "A REAL", font=font(F_CAP, 130 * s), fill=(255, 255, 255, int(255 * k)), anchor="mm", stroke_width=12, stroke_fill=BLACK)
        d.text((540, 440), "PLANET.", font=font(F_CAP, 130 * s), fill=(255, 212, 0, int(255 * k)), anchor="mm", stroke_width=12, stroke_fill=BLACK)
    label(d, 540, 1620, "", "iron detected with ESO's ESPRESSO · Ehrenreich et al. 2020", 220, WHITE, 10)
    tag(d, "CGI RECONSTRUCTION  ·  half day, half night (tidally locked)")
    return img

HOOK_END = ls(1) - 0.1
def build():
    c = [HOOK_END, ls(2) - 0.1, ls(3) - 0.1, ws(4, 7) - 0.15, ls(6) - 0.1, ls(7) - 0.15]
    fns = [sc_reveal, sc_dayside, sc_terminator, sc_night_rain, sc_single]
    out = [(0.0, HOOK_END, sc_hook)]
    for i, fn in enumerate(fns):
        out.append((c[i], c[i + 1], (lambda f, a, b: (lambda t: f(t, a, b)))(fn, c[i], c[i + 1])))
    out.append((c[-1], DUR + 1, lambda t: sc_final(t, c[-1])))
    return out
SCENES = build()

# ====================================================================== captions
PHRASE_TEXT = [
 "ON THIS PLANET, IT RAINS IRON.",
 "MEET WASP-76 B, | A WORLD SO HOT THAT METAL | CAN EVAPORATE INTO THE SKY.",
 "ITS DAYSIDE REACHES OVER 4,000 °F.",
 "POWERFUL WINDS CARRY IRON VAPOR | TOWARD THE COOLER NIGHTSIDE.",
 "AND THERE, SCIENTISTS BELIEVE | THE IRON CONDENSES | INTO LIQUID DROPLETS.",
 "IMAGINE A WEATHER FORECAST THAT SAYS: | MOLTEN METAL RAIN.",
 "AND THE CRAZIEST PART? | THIS ISN'T SCIENCE FICTION.",
 "IT'S A REAL PLANET.",
]
KEY = {"IRON.", "IRON", "WASP-76", "B,", "EVAPORATE", "4,000", "°F.", "WINDS", "NIGHTSIDE.", "CONDENSES", "LIQUID", "DROPLETS.", "MOLTEN", "METAL", "RAIN.", "REAL"}
def phrases():
    res = []
    for li, l in enumerate(TIM):
        words = [(w.upper(), s, e) for w, s, e in l["words"]]
        parts = [p.split() for p in PHRASE_TEXT[li].split("|")]
        assert " ".join(" ".join(p) for p in parts) == " ".join(w for w, _, _ in words), (li, [w for w, _, _ in words])
        i = 0
        for p in parts: res.append(words[i:i + len(p)]); i += len(p)
    out = []
    for i, ph in enumerate(res):
        a = ph[0][1]; nxt = res[i + 1][0][1] if i + 1 < len(res) else 1e9
        out.append((a, nxt if nxt - ph[-1][2] < 0.7 else ph[-1][2] + 0.35, ph))
    return out
PHRASES = phrases()

def draw_caption(img, t):
    if t < ls(1) - 0.05 or t >= ws(7, 2) - 0.1: return                           # hook title carries line 0; final title carries the last
    for a, b, ph in PHRASES:
        if not (a <= t < b): continue
        d = ImageDraw.Draw(img); f = font(F_CAP, 72); gap = 18; maxw = 900
        items = [(("b," if w == "B," else w), f.getlength("b," if w == "B," else w), bool(re.search(r"\d", w)) or w in KEY) for w, s, e in ph]
        rows, cur, cw = [], [], 0
        for it in items:
            if cur and cw + gap + it[1] > maxw: rows.append(cur); cur, cw = [], 0
            cur.append(it); cw += (gap if len(cur) > 1 else 0) + it[1]
        rows.append(cur)
        k = ease_out(seg(t, a, a + 0.12)); al = int(255 * k); dy = 12 * (1 - k)
        lh = 84; y0 = 1420 - (len(rows) - 1) * lh / 2 + dy
        lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
        for ri, row in enumerate(rows):
            tw = sum(x[1] for x in row) + gap * (len(row) - 1); x = 540 - tw / 2
            for w, fw, em in row:
                ld.text((x, y0 + ri * lh), w, font=f, fill=(YELLOW if em else WHITE) + (255,), anchor="lm", stroke_width=9, stroke_fill=BLACK)
                x += fw + gap
        if al < 255: lay.putalpha(Image.eval(lay.getchannel("A"), lambda v: v * al // 255))
        img.paste(lay, (0, 0), lay)
        return

# ====================================================================== frame + encode
GR = np.random.default_rng(3)
GRAIN = [GR.normal(0, 2.2, (H, W, 1)).astype(np.float32) for _ in range(4)]
yy_, xx_ = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1 - 0.25 * (((xx_ - W / 2) / (W / 2)) ** 2 + ((yy_ - H / 2) / (H / 2)) ** 2) ** 1.6).clip(0.55, 1)[..., None]
del yy_, xx_

def frame(fi):
    t = fi / FPS
    img = None
    for a, b, fn in SCENES:
        if a <= t < b: img = fn(t); break
    for i, (a, b, fn) in enumerate(SCENES[1:]):
        if 0 <= t - a < 0.2: img = Image.blend(SCENES[i][2](t).convert("RGB"), img.convert("RGB"), ease(seg(t, a, a + 0.2)))
    arr = np.asarray(img.convert("RGB"), np.float32) * VIG + GRAIN[fi % 4]
    img = to_img(arr); draw_caption(img, t)
    return img.tobytes()

def warm(): stars(); atmo(); planet_tex()
FINAL_X264 = ["-c:v", "libx264", "-preset", "slow", "-crf", "15", "-maxrate", "18M", "-bufsize", "36M", "-profile:v", "high", "-level", "4.2",
              "-pix_fmt", "yuv420p", "-g", "60", "-x264-params", "aq-mode=3:aq-strength=0.9:deblock=-1,-1", "-r", "30", "-fps_mode", "cfr"]
def encode(frames, out):
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"] + FINAL_X264 + [out], stdin=subprocess.PIPE)
    warm()
    with Pool(4) as pool:
        for b in pool.imap(frame, frames, chunksize=2): p.stdin.write(b)
    p.stdin.close(); p.wait()

# ====================================================================== sound
def sizzle(d=1.2):
    n = int(d * SR); tt = np.arange(n) / SR
    return bp(arng.normal(0, 1, n), 2500, 9000) * np.exp(-tt / (d * 0.5)) * 0.5
def drip(f=900):
    n = int(0.25 * SR); tt = np.arange(n) / SR
    return np.sin(2 * np.pi * f * (1 + 0.6 * np.exp(-tt / 0.02)) * tt) * np.exp(-tt / 0.06)
def render_audio(out):
    n = int(DUR * SR); tt = np.arange(n) / SR
    chords = [(0, [41.2, 61.74, 98.0, 123.47]), (ls(2), [43.65, 65.41, 103.83, 130.81]), (ls(4), [38.89, 58.27, 92.5, 116.54]),
              (ls(6), [41.2, 61.74, 98.0, 155.56, 185.0])]
    pad = np.zeros(n)
    for ci, (t0, notes) in enumerate(chords):
        t1 = chords[ci + 1][0] if ci + 1 < len(chords) else DUR
        i0, i1 = int(t0 * SR), min(n, int(t1 * SR) + int(0.8 * SR)); m = i1 - i0; sg = np.zeros(m)
        for f in notes:
            for det in (-0.1, 0.0, 0.09): sg += osc(f * 2 ** (det / 12), m)
        e = np.minimum(1, np.arange(m) / (0.8 * SR)) * np.minimum(1, (m - np.arange(m)) / (0.8 * SR))
        pad[i0:i1] += sg * e / 12
    pulse = np.zeros(n); t = ls(1)
    while t < ls(6):
        place(pulse, boom(0.4, 66, 40, 0.1), t, 0.3); t += 60 / 92
    swell = np.interp(tt, [0, 1.6, 2.2, ls(4), ls(6), NARR_END, DUR - 0.4, DUR], [0.9, 0.9, 0.6, 0.85, 1.0, 1.1, 0.5, 0.0])
    mus = (lp(pad, 1100) * 0.7 + lp(pad, 380) * 0.6 + osc(30.9, n, "sin") * 0.18 + pulse) * swell
    fx = np.zeros(n)
    place(fx, reverb(boom(2.6, 120, 24, 0.9), 3.2, 0.45), 0.0, 1.7)                                 # frame-0 impact
    place(fx, crack(0.5), 0.0, 0.45)
    place(fx, sizzle(1.6), 0.0, 0.5)
    for a, b, fn in SCENES[1:]: place(fx, whoosh(0.6), a - 0.2, 0.16)
    m = int(3.5 * SR); place(fx, lp(arng.normal(0, 1, m), 300) * np.minimum(1, np.arange(m) / SR / 0.6) * 1.2, ls(3), 0.35)   # wind
    rng = np.random.default_rng(4)
    for k in range(14): place(fx, drip(rng.uniform(600, 1300)), ls(4) + 2.2 + k * 0.42 + rng.uniform(0, 0.2), 0.12)
    place(fx, reverb(boom(2.0, 100, 28, 0.6), 3.0, 0.4), ws(7, 2), 0.9)                             # "real planet" payoff
    vo = np.zeros(n)
    for l in TIM:
        s, _ = sf.read(l["file"]); place(vo, s, l["start"])
    vo = lp(hp(vo, 80), 13500); vo = vo / (np.abs(vo).max() + 1e-9) * 0.9
    env = lp(np.abs(vo), 7); env /= env.max() + 1e-9
    duck = 1 - 0.66 * np.clip(env * 3, 0, 1)
    mix = vo + mus * 0.12 * duck + fx * 0.3 * (0.4 + 0.6 * duck)
    sf.write(out, np.stack([np.tanh(mix * 1.05) * 0.95] * 2, 1).astype(np.float32), SR, subtype="FLOAT")

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "stills":
        warm(); os.makedirs("st", exist_ok=True)
        for x in sys.argv[2:]:
            t = float(x); Image.frombytes("RGB", (W, H), frame(int(round(t * FPS)))).save(f"st/s_{int(t * 100):05d}.png")
    elif cmd == "audio": render_audio(sys.argv[2])
    elif cmd == "preview":
        t0, t1, out = float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
        encode(list(range(int(t0 * FPS), int(t1 * FPS))), "_v.mp4"); render_audio("_a.wav")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", "_v.mp4", "-ss", str(t0), "-t", str(t1 - t0), "-i", "_a.wav", "-map", "0:v", "-map", "1:a",
                        "-af", "loudnorm=I=-14:TP=-1.5", "-c:v", "copy", "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-shortest", out], check=True)
    elif cmd == "final": encode(list(range(NF)), "video_final_v.mp4")
