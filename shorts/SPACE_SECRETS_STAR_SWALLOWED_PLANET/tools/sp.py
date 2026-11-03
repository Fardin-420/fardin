#!/usr/bin/env python3
# SPACE SECRETS — "A Star Swallowed a Planet — Then Webb Found a Twist" (ZTF SLRN-2020). Native 1080x1920 renderer.
# Usage: python3 sp.py stills t... | hookone | preview t0 t1 out.mp4 | final | audio out.wav
import json, math, os, re, subprocess, sys
from multiprocessing import Pool
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

import star, bhfx as B
from sfx import SR, lp, hp, bp, place, osc, boom, crack, whoosh, tick, riser, reverb, arng

W, H, FPS = 1080, 1920, 30
star.W, star.H = W, H
TIM = json.load(open("timing.json"))
def ls(i): return TIM[i]["start"]
def le(i): return TIM[i]["start"] + TIM[i]["dur"]
def ws(i, k): return TIM[i]["words"][k][1]
NARR_END = le(len(TIM) - 1)
DUR = round(NARR_END + 3.4, 1)
NF = int(DUR * FPS)
HOOK = os.environ.get("HOOK", "A")

def clamp(v, a, b): return max(a, min(b, v))
def seg(t, a, b): return clamp((t - a) / (b - a), 0.0, 1.0) if b > a else float(t >= a)
def ease(x): x = clamp(x, 0, 1); return x * x * (3 - 2 * x)
def ease_out(x): x = clamp(x, 0, 1); return 1 - (1 - x) ** 3
def ease_in(x): x = clamp(x, 0, 1); return x ** 3
def ease_io(x): x = clamp(x, 0, 1); return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2
def lerp(a, b, k): return a + (b - a) * k
_C = {}
def cache(k, fn):
    if k not in _C: _C[k] = fn()
    return _C[k]
finish = B.finish
def _glare(arr, x, y, r=34, amt=1.0, col=(1.0, 0.98, 0.93)):
    yy, xx = np.ogrid[0:H, 0:W]
    d = np.sqrt((xx - x) ** 2 + (yy - y) ** 2)
    core = np.clip(1 - d / r, 0, 1) ** 0.5 * 600 + np.exp(-d / (r * 2.2)) * 160 + np.exp(-d / (r * 9)) * 40
    return arr + (core * amt)[..., None] * np.array(col, np.float32)
B.sun_glare = _glare
def to_img(a): return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

# ------------------------------------------------------------------ high-resolution stellar surface (6144x3072 granulation, ~1:1 at R=1400)
def _hires_sun():
    if star._SUN.get("hires"): return star._SUN
    rng = np.random.default_rng(5)
    shp = (3072, 6144); k = 6144 / 1440
    def nz(sigs, wts):
        a = np.zeros(shp, np.float32)
        for s, w in zip(sigs, wts):
            n = ndimage.gaussian_filter(rng.normal(0, 1, shp).astype(np.float32), s, mode="wrap"); a += w * n / (n.std() + 1e-6)
        return a
    g1 = np.tanh(nz((1.1 * k * 0.6, 2.4 * k * 0.6, 9.0 * k), (1.0, 0.7, 0.35)) * 1.6)
    g2 = np.tanh(nz((1.1 * k * 0.6, 2.4 * k * 0.6, 9.0 * k), (1.0, 0.7, 0.35)) * 1.6)
    spots = np.zeros(shp, np.float32)
    for la, lo, r in ((18, -30, 14), (-12, 40, 11), (22, 110, 10), (-20, 160, 9)):
        v, u = (90 - la) / 180 * shp[0], (lo % 360) / 360 * shp[1]
        y0, y1, x0, x1 = int(v - r * k * 3), int(v + r * k * 3), int(u - r * k * 3), int(u + r * k * 3)
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        d = np.sqrt((xx - u) ** 2 + (yy - v) ** 2)
        blob = np.clip(1 - d / (r * k * 1.8), 0, 1) ** 0.7 * 0.55 + (d < r * k * 0.7) * 0.4
        sl = (slice(max(0, y0), min(shp[0], y1)), slice(max(0, x0), min(shp[1], x1)))
        spots[sl] = np.maximum(spots[sl], blob[sl[0].start - y0:sl[0].stop - y0, sl[1].start - x0:sl[1].stop - x0])
    spots = ndimage.gaussian_filter(spots, 4)
    fac = np.clip(nz((14.0 * k,), (1.0,)), 0, None)
    star._SUN.update(g1=g1.astype(np.float32), g2=g2.astype(np.float32), spots=spots.astype(np.float32), fac=fac.astype(np.float32), hires=True)
    star._SUN["ang"] = rng.normal(0, 1, 720)
    return star._SUN
star.sun_tex = _hires_sun
K_TINT = np.array([1.0, 0.70, 0.42], np.float32)                                    # orange K-type star
def kstar(arr, cx, cy, R, t, bright=1.0, corona=1.0):
    lay = star.draw_sun(np.zeros_like(arr), cx, cy, R, t, bright=bright, corona=corona)
    return arr + lay * K_TINT

# ------------------------------------------------------------------ gas giant: 4096x2048 banded texture, lit, with tidal stretch + heating
def jtex():
    def make():
        rng = np.random.default_rng(2020)
        h, w = 2048, 4096
        def nz(sy, sx):
            a = ndimage.gaussian_filter(rng.normal(0, 1, (h // 2, w // 2)).astype(np.float32), (sy / 2, sx / 2), mode="wrap")
            a = np.asarray(Image.fromarray(a).resize((w, h), Image.BICUBIC), np.float32); return a / (a.std() + 1e-6)
        lat = np.linspace(90, -90, h)[:, None] * np.ones((1, w), np.float32)
        la = lat + nz(14, 150) * 2.6 + nz(5, 40) * 0.9 + nz(1.6, 10) * 0.3
        v = 0.5 + 0.22 * np.sin(np.radians(la) * 10 + 0.4) + 0.12 * np.sin(np.radians(la) * 23 + 1.2) + 0.06 * np.sin(np.radians(la) * 47)
        v += 0.07 * nz(3, 110) + 0.04 * nz(9, 220) + 0.025 * nz(1.2, 5)
        v = np.clip(v, 0, 1)
        xp = [0.0, 0.25, 0.45, 0.6, 0.78, 1.0]
        col = np.stack([np.interp(v, xp, [70, 120, 170, 205, 230, 245]), np.interp(v, xp, [40, 78, 125, 170, 210, 235]),
                        np.interp(v, xp, [25, 50, 85, 130, 180, 215])], -1).astype(np.float32)
        return col
    return cache("jtex", make)

def giant(arr, cx, cy, R, light, lon=0.0, lat0=12.0, t=0.0, stretch=1.0, sdir=(0.0, 1.0), heat=0.0, gain=1.0):
    """Banded gas giant. stretch>1 elongates it along sdir (unit screen vector toward the star); heat makes the star-facing side glow."""
    T = jtex(); th, tw = T.shape[:2]
    ext = R * stretch * 1.1
    x0, x1 = int(max(0, cx - ext)), int(min(W, cx + ext)); y0, y1 = int(max(0, cy - ext)), int(min(H, cy + ext))
    if x1 <= x0 or y1 <= y0 or R < 1: return arr
    ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    dx, dy = xs - cx, ys - cy
    ux, uy = sdir; px_ = dx * ux + dy * uy; qx_ = -dx * uy + dy * ux
    px_ = px_ / stretch; qx_ = qx_ * (stretch ** 0.35)
    dx, dy = px_ * ux - qx_ * uy, px_ * uy + qx_ * ux
    nx = dx / R; ny = -dy / R; r2 = nx * nx + ny * ny; m = r2 < 1
    if not m.any(): return arr
    L = np.array(light, np.float32); L /= np.linalg.norm(L)
    nxm, nym = nx[m], ny[m]; nzm = np.sqrt(1 - r2[m])
    c0, s0 = math.cos(math.radians(lat0)), math.sin(math.radians(lat0))
    X = nxm; Y = nym * c0 + nzm * s0; Z = -nym * s0 + nzm * c0
    lat = np.degrees(np.arcsin(np.clip(Y, -1, 1))); lonv = np.degrees(np.arctan2(X, Z)) + lon + t * 4 * np.cos(np.radians(lat) * 2)
    v = (90 - lat) / 180 * (th - 1); u = ((lonv + 180) % 360) / 360 * tw
    col = np.stack([ndimage.map_coordinates(T[..., k], [v, u], order=1, mode="wrap") for k in range(3)], -1)
    ndl = nxm * L[0] + nym * L[1] + nzm * L[2]
    diff = np.clip(ndl, 0, 1) ** 0.9
    c = col * (0.03 + 1.05 * diff)[:, None] * np.array([1.0, 0.82, 0.62], np.float32) * gain
    c += ((1 - nzm) ** 2.5 * (0.2 + diff))[:, None] * np.array([255, 170, 100], np.float32) * 0.35
    if heat > 0:
        hot = np.clip(ndl, 0, 1) ** 3 * heat
        c += hot[:, None] * np.array([255, 150, 70], np.float32) * 1.4
    edge = np.clip((1 - np.sqrt(r2[m])) * R / 1.3, 0, 1)[:, None]
    sub = arr[y0:y1, x0:x1]
    sub[m] = sub[m] * (1 - edge) + c * edge
    arr[y0:y1, x0:x1] = sub
    return arr

def stream(arr, pts_fn, t, n=300, seed=1, col=(255, 170, 90), amt=1.0, size=2.4, spread=10):
    """Particles flowing along a parametric path pts_fn(u)->(x,y); used for stripped gas and debris."""
    rng = np.random.default_rng(seed)
    lay = Image.new("L", (W, H), 0); d = ImageDraw.Draw(lay)
    ph = rng.random(n); off = rng.normal(0, 1, (n, 2)); br = rng.uniform(0.35, 1.0, n); sp = rng.uniform(0.7, 1.3, n)
    for i in range(n):
        u = (ph[i] + t * 0.45 * sp[i]) % 1.0
        x, y = pts_fn(u); x += off[i, 0] * spread * u; y += off[i, 1] * spread * u
        f = min(1, u / 0.05, (1 - u) / 0.25) * br[i]
        d.ellipse((x - size, y - size, x + size, y + size), fill=int(255 * f))
    g = np.asarray(lay.filter(ImageFilter.GaussianBlur(1.4)), np.float32)[..., None] / 255
    return arr + g * np.array(col, np.float32) * amt * 1.5

def stars_bg(seed="field", off=(0, 0), gain=0.6):
    return B.lens_view(B.plate(seed), [], off=off) * gain

# ------------------------------------------------------------------ JWST reconstruction (gold hexagonal mirror + five-layer sunshield)
def jwst(d, cx, cy, s, yaw, pitch, alpha=255):
    cyw, syw = math.cos(yaw), math.sin(yaw); cp, sp_ = math.cos(pitch), math.sin(pitch)
    def P(x, y, z):
        x, z = x * cyw + z * syw, -x * syw + z * cyw
        y, z = y * cp - z * sp_, y * sp_ + z * cp
        return cx + x * s, cy - y * s, z
    polys = []
    shield = [(-3.6, -2.4, -1.2), (3.6, -2.4, -1.2), (3.0, -2.6, 2.2), (-3.0, -2.6, 2.2)]                  # sunshield layers
    for k in range(5):
        q = [P(x, y - k * 0.09, z) for x, y, z in shield]
        polys.append((sum(p[2] for p in q) / 4 - 0.01 * k, [(p[0], p[1]) for p in q], (150 + 12 * k, 140 + 10 * k, 175 + 10 * k)))
    hexr = 0.62
    for qx, qy in [(0, 0), (1, 0), (-1, 0), (0.5, 0.866), (-0.5, 0.866), (0.5, -0.866), (-0.5, -0.866), (1.5, 0.866), (-1.5, 0.866),
                   (1.5, -0.866), (-1.5, -0.866), (2, 0), (-2, 0), (1, 1.732), (-1, 1.732), (0, 1.732), (1, -1.732), (-1, -1.732)]:
        if qx == 0 and qy == 0: continue
        hx, hy = qx * hexr * 1.75, qy * hexr * 1.75 + 1.4
        q = [P(hx + hexr * math.cos(a), hy + hexr * math.sin(a), 0.25 - 0.04 * (hx * hx + (hy - 1.4) ** 2)) for a in np.linspace(0, 2 * np.pi, 7)[:-1] + np.pi / 6]
        shade = 0.75 + 0.25 * math.cos(hx * 0.7 + yaw * 2)
        polys.append((sum(p[2] for p in q) / 6 + 0.5, [(p[0], p[1]) for p in q], (int(230 * shade), int(175 * shade), int(60 * shade))))
    polys.sort(key=lambda p: p[0])
    for z, pts, col in polys:
        d.polygon(pts, fill=col + (alpha,)); d.line(pts + [pts[0]], fill=(40, 30, 20, alpha), width=1)
    tip = P(0, 1.4, 3.2)
    for a in (0, 2.1, 4.2):
        b = P(2.0 * math.cos(a), 1.4 + 2.0 * math.sin(a), 0.4)
        d.line((b[0], b[1], tip[0], tip[1]), fill=(200, 200, 205, alpha), width=3)
    d.ellipse((tip[0] - 7, tip[1] - 7, tip[0] + 7, tip[1] + 7), fill=(225, 180, 70, alpha))

# ------------------------------------------------------------------ text
F_CAP = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
F_UI = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
F_MONO = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf"
_F = {}
def font(p, s):
    k = (p, int(s))
    if k not in _F: _F[k] = ImageFont.truetype(p, max(1, int(s)))
    return _F[k]
WHITE, YELLOW, BLACK, ORANGE, CYAN = (255, 255, 255), (255, 212, 0), (0, 0, 0), (255, 160, 80), (130, 210, 255)
def tag(d, txt, col=(255, 170, 100)):
    f = font(F_MONO, 22)
    d.rounded_rectangle((60, 196, 60 + f.getlength(txt) + 28, 236), 10, fill=(0, 0, 0, 160))
    d.ellipse((72, 210, 84, 222), fill=col); d.text((94, 216), txt, font=f, fill=(235, 235, 235), anchor="lm")
def label(d, x, y, title, body=None, a=255, col=WHITE, size=36, anchor="mm"):
    if a <= 0: return
    d.text((x, y), title, font=font(F_UI, size), fill=col + (a,), anchor=anchor, stroke_width=5, stroke_fill=BLACK)
    if body: d.text((x, y + size + 6), body, font=font(F_MONO, 22), fill=(230, 230, 232, a), anchor=anchor, stroke_width=4, stroke_fill=BLACK)
def headline(d, txt, k, y=320, col=WHITE, size=66):
    if k <= 0: return
    a = int(255 * k); dy = 14 * (1 - ease_out(k))
    d.text((540, y + dy), txt, font=font(F_CAP, size), fill=col + (a,), anchor="mm", stroke_width=9, stroke_fill=BLACK + (a,))

# ====================================================================== SCENES
HOOK_END = 2.5
SR_C, SR_R = (430, 2480), 1400                                                       # the star's limb fills the lower frame

def plunge_view(t, u, variant="A"):
    """Gas giant plunging into the outer atmosphere of a huge orange star (reconstruction)."""
    arr = stars_bg("field", off=(-200, -500), gain=0.55)
    arr = kstar(arr, SR_C[0], SR_C[1], SR_R, t * 2, bright=1.15, corona=1.25)
    if variant == "B":
        gx, gy, gr = lerp(980, 700, u), lerp(260, 1000, u), lerp(170, 190, u)
    elif variant == "C":
        gx, gy, gr = lerp(640, 690, u), lerp(1040, 1070, u), lerp(430, 250, ease_out(u))
    else:
        gx, gy, gr = lerp(735, 680, u), lerp(950, 1110, u), 240
    vx, vy = SR_C[0] - gx, SR_C[1] - gy; dist = math.hypot(vx, vy); sd = (vx / dist, vy / dist)
    depth = clamp((SR_R + gr * 1.2 - dist) / (gr * 1.6), 0, 1)
    light = (vx / dist, -vy / dist, 0.25)
    arr = giant(arr, gx, gy, gr, light, lon=30 * u, t=t, stretch=1 + 0.35 * depth, sdir=sd, heat=0.4 + 1.2 * depth)
    shock = depth * 1.0                                                              # compressed, heated gas where it ploughs in
    if shock > 0:
        yy, xx = np.ogrid[0:H, 0:W]
        bx, by = gx + sd[0] * gr * 0.95, gy + sd[1] * gr * 0.95
        g = np.exp(-((xx - bx) ** 2 + (yy - by) ** 2) / (2 * (gr * 0.55) ** 2)) * 380 * shock
        arr = arr + g[..., None] * np.array([1.0, 0.65, 0.35], np.float32)
    def path(s):                                                                     # stripped gas trailing behind
        return gx - sd[0] * gr * (0.6 + 2.6 * s) + 80 * math.sin(s * 5 + t), gy - sd[1] * gr * (0.6 + 2.6 * s) - 120 * s * s
    arr = stream(arr, path, t, n=650, seed=4, amt=0.6 + 1.0 * depth, spread=70, size=3.0)
    return arr

def hook_frame(t):
    u = seg(t, 0, 2.4)
    arr = plunge_view(t, u, HOOK)
    img = finish(arr, 0.55); d = ImageDraw.Draw(img, "RGBA")
    k = max(0.85, 1.15 - 0.3 * seg(t, 0, 0.12))
    d.text((540, 300), "A STAR ATE", font=font(F_CAP, 120 * k), fill=WHITE, anchor="mm", stroke_width=12, stroke_fill=BLACK)
    d.text((540, 425), "A PLANET?!", font=font(F_CAP, 128 * k), fill=YELLOW, anchor="mm", stroke_width=12, stroke_fill=BLACK)
    tag(d, "SCIENTIFIC RECONSTRUCTION  ·  not NASA footage")
    return img

def sc_webb(t, t0, t1):
    u = ease_io(seg(t, t0, t1))
    arr = stars_bg("sparse", off=(100, 200), gain=0.9)
    arr = B.sun_glare(arr, -200, 2100, 500, 0.25) if hasattr(B, "sun_glare") else arr
    img = finish(arr, 0.4); d = ImageDraw.Draw(img, "RGBA")
    jwst(d, lerp(560, 520, u), lerp(980, 930, u), lerp(78, 92, u), lerp(-0.5, 0.25, u), lerp(0.35, 0.2, u))
    q = seg(t, ws(1, 6) - 0.2, ws(1, 6) + 0.3)
    label(d, 540, 400, "JAMES WEBB SPACE TELESCOPE", "2025 · infrared spectroscopy", int(255 * q), (255, 212, 0), 40)
    tag(d, "CGI RECONSTRUCTION  ·  not NASA imagery")
    return img

TARGET = np.array([5.38, 2.37, 0.0], np.float32)                                     # ~3.7 kpc (12,000 ly) from the Sun toward Aquila (l≈40°)
SUNP = np.array([8.2, 0.0, 0.02], np.float32)
def sc_where(t, t0, t1):
    u = ease_io(seg(t, t0, t1))
    mid = (SUNP + TARGET) / 2
    h = lerp(7.0, 13.0, u)
    cam = mid + np.array([1.0, -0.3 * h, h], np.float32)
    arr = B.render_galaxy(cam, mid * (1 - 0.3 * u), fov=55, up=(1, 0, 0), dust_k=0.6, gain=lerp(4.0, 2.6, u))
    img = finish(arr, 0.4); d = ImageDraw.Draw(img, "RGBA")
    r_, u_, f_ = B.look_at(cam, mid * (1 - 0.3 * u), (1, 0, 0)); fpx = (W / 2) / math.tan(math.radians(55 / 2))
    def proj(Q):
        dd = Q - cam; z = dd @ f_
        return W / 2 + (dd @ r_) / z * fpx, H / 2 - (dd @ u_) / z * fpx
    sx, sy = proj(SUNP); tx, ty = proj(TARGET)
    d.line((sx, sy, tx, ty), fill=(255, 212, 0, 220), width=3)
    d.ellipse((sx - 9, sy - 9, sx + 9, sy + 9), fill=(255, 230, 140)); label(d, sx + 18, sy, "SUN", None, 255, (255, 230, 140), 26, "lm")
    pul = 1 + 0.4 * math.sin(t * 6)
    d.ellipse((tx - 12 * pul, ty - 12 * pul, tx + 12 * pul, ty + 12 * pul), outline=(255, 150, 70), width=4); label(d, tx + 22, ty, "ZTF SLRN-2020", None, 255, ORANGE, 26, "lm")
    headline(d, "~12,000 LIGHT-YEARS AWAY", seg(t, t0 + 0.2, t0 + 0.6), 330, YELLOW, 58)
    tag(d, "CGI MODEL  ·  Milky Way, positions approximate", (130, 210, 255))
    return img

def sc_flare(t, t0, t1):
    """A point of light in a crowded field flares, then fades; simplified optical vs infrared curves draw below."""
    u = seg(t, t0, t1)
    arr = B.lens_view(B.plate("bulge"), [], off=(60, -140), zoom=1.6) * 0.8
    k = seg(t, t0 + 0.3, t0 + 1.0) * (1 - seg(t, t0 + 2.6, t0 + 4.2) * 0.85)
    arr = B.sun_glare(arr, 540, 760, 10 + 30 * k, 0.6 + 2.2 * k, (1.0, 0.8, 0.6)) if hasattr(B, "sun_glare") else arr
    img = finish(arr, 0.5); d = ImageDraw.Draw(img, "RGBA")
    gx0, gx1, gy0, gy1 = 110, 970, 1080, 1300
    d.rectangle((gx0 - 14, gy0 - 60, gx1 + 14, gy1 + 30), fill=(0, 0, 0, 175))
    d.text((gx0, gy0 - 34), "BRIGHTNESS  (simplified)", font=font(F_MONO, 24), fill=(255, 212, 0), anchor="lm")
    xs = np.linspace(0, 1, 220)[: max(2, int(220 * seg(t, t0 + 0.3, t1 - 0.4)))]
    opt = np.exp(-((xs - 0.12) / 0.035) ** 2) + 0.05
    ir = 0.45 * np.clip((xs - 0.08) / 0.1, 0, 1) * np.exp(-np.clip(xs - 0.2, 0, None) / 0.45) + 0.05
    for curve, col in ((opt, (255, 212, 0)), (ir, (255, 120, 80))):
        pts = [(gx0 + x * (gx1 - gx0), gy1 - c * (gy1 - gy0 - 10)) for x, c in zip(xs, curve)]
        if len(pts) > 1: d.line(pts, fill=col, width=5)
    d.text((gx0 + 150, gy0 + 10), "visible: ~10 days", font=font(F_MONO, 22), fill=(255, 212, 0), anchor="lm")
    d.text((gx0 + 470, gy0 + 120), "infrared: months", font=font(F_MONO, 22), fill=(255, 140, 100), anchor="lm")
    tag(d, "SIMULATED STAR FIELD + SIMPLIFIED CURVES", (130, 210, 255))
    return img

def sc_name(t, t0, t1):
    u = ease_io(seg(t, t0, t1))
    arr = B.lens_view(B.plate("bulge"), [], off=(60, -140), zoom=lerp(1.6, 2.4, u)) * 0.7
    arr = B.sun_glare(arr, 540, lerp(760, 820, u), 12, 0.7, (1.0, 0.75, 0.55))
    img = finish(arr, 0.5); d = ImageDraw.Draw(img, "RGBA")
    q = seg(t, ws(4, 2) - 0.15, ws(4, 2) + 0.25)
    d.text((540, 360), "ZTF SLRN-2020", font=font(F_CAP, 92), fill=(255, 212, 0, int(255 * q)), anchor="mm", stroke_width=10, stroke_fill=BLACK)
    label(d, 540, 460, "", "Zwicky Transient Facility · Aquila", int(255 * q), WHITE, 10)
    tag(d, "SIMULATED STAR FIELD", (130, 210, 255))
    return img

def sc_evidence(t, t0, t1):
    """The 2023 reading: a gas giant, roughly Jupiter-size, close to its star."""
    u = ease_io(seg(t, t0, t1))
    arr = stars_bg("sparse", off=(-100, 300), gain=0.7)
    arr = kstar(arr, -260, lerp(700, 640, u), 520, t, bright=1.0, corona=1.0)
    gr = lerp(330, 380, u)
    arr = giant(arr, lerp(640, 600, u), 1080, gr, (-0.92, 0.2, 0.32), lon=-40 + 25 * u, t=t)
    img = finish(arr, 0.45); d = ImageDraw.Draw(img, "RGBA")
    q = seg(t, ws(5, 6) - 0.2, ws(5, 6) + 0.3)
    headline(d, "2023: FIRST DIRECT EVIDENCE", q, 330, YELLOW, 58)
    q2 = seg(t, ws(5, 15) - 0.2, ws(5, 15) + 0.3)
    label(d, 540, 420, "", "a star swallowing a planet · likely a gas giant (inferred)", int(255 * q2), WHITE, 10)
    tag(d, "SCIENTIFIC RECONSTRUCTION  ·  planet size inferred, not imaged")
    return img

def sc_redgiant(t, t0, t1):
    """The 2023 hypothesis: the aging star swells into a red giant and overtakes the planet's orbit."""
    u = ease_io(seg(t, t0, t1))
    arr = stars_bg("sparse", off=(200, 0), gain=0.6)
    R = lerp(150, 520, u)
    arr = B.sun_glare(arr, 540, 960, 4, 0.0)
    lay = star.draw_sun(np.zeros_like(arr), 540, 960, R, t, bright=1.0, corona=0.9)
    arr = arr + lay * np.array([1.0, 0.45 + 0.25 * (1 - u), 0.25 + 0.2 * (1 - u)], np.float32)
    orb = 430
    ang = t * 1.4
    gx, gy = 540 + orb * math.cos(ang), 960 + orb * 0.32 * math.sin(ang)
    if math.hypot(gx - 540, (gy - 960) / 0.32 * 1) > R * 0.98 or math.sin(ang) > 0:
        arr = giant(arr, gx, gy, 46, ((540 - gx) / orb, (gy - 960) / orb, 0.3), t=t)
    img = finish(arr, 0.45); d = ImageDraw.Draw(img, "RGBA")
    d.arc((540 - orb, 960 - orb * 0.32, 540 + orb, 960 + orb * 0.32), 0, 360, fill=(255, 255, 255, 80), width=2)
    headline(d, "2023 IDEA: A SWELLING RED GIANT", seg(t, t0 + 0.2, t0 + 0.6), 330, ORANGE, 52)
    tag(d, "ILLUSTRATION  ·  the original hypothesis, not to scale")
    return img

def sc_webb2(t, t0, t1):
    u = ease_io(seg(t, t0, t1))
    arr = stars_bg("field", off=(-300, 500), gain=0.7)
    img = finish(arr, 0.4); d = ImageDraw.Draw(img, "RGBA")
    jwst(d, lerp(380, 520, u), lerp(1150, 1000, u), lerp(120, 150, u), lerp(2.6, 3.1, u), lerp(-0.25, -0.1, u))
    tag(d, "CGI RECONSTRUCTION  ·  not NASA imagery")
    return img

def sc_twist(t, t0, t1):
    """TWIST: the 'red giant' deflates back into a modest orange star."""
    u = ease_io(seg(t, t0 + 0.5, t1))
    arr = stars_bg("sparse", off=(200, 0), gain=0.6)
    R = lerp(520, 210, u)
    lay = star.draw_sun(np.zeros_like(arr), 540, 960, R, t, bright=1.0, corona=0.9)
    arr = arr + lay * np.array([1.0, lerp(0.45, 0.70, u), lerp(0.25, 0.42, u)], np.float32)
    img = finish(arr, 0.5); d = ImageDraw.Draw(img, "RGBA")
    headline(d, "THE TWIST", seg(t, ws(8, 3) - 0.2, ws(8, 3) + 0.2), 300, YELLOW, 96)
    label(d, 540, 420, "TOO FAINT TO BE A RED GIANT", None, int(255 * seg(t, ls(9) + 0.2, ls(9) + 0.6)), WHITE, 40)
    tag(d, "ILLUSTRATION  ·  based on JWST results (2025)")
    return img

def sc_compare(t, t0, t1):
    u = ease_io(seg(t, t0, t1))
    arr = stars_bg("sparse", off=(-200, -200), gain=0.5)
    lay = star.draw_sun(np.zeros_like(arr), 300, 1000, 230, t, bright=1.0, corona=0.8); arr = arr + lay
    lay = star.draw_sun(np.zeros_like(arr), 790, 1000, 230 * 0.72, t + 3, bright=0.95, corona=0.8); arr = arr + lay * K_TINT
    img = finish(arr, 0.45); d = ImageDraw.Draw(img, "RGBA")
    label(d, 300, 1290, "OUR SUN", "for comparison", 255, (255, 230, 160), 34)
    label(d, 790, 1290, "THIS STAR", "~0.7 solar masses · cooler, orange", 255, ORANGE, 34)
    headline(d, "STILL IN THE PRIME OF ITS LIFE", seg(t, ws(10, 7) - 0.2, ws(10, 7) + 0.2), 330, YELLOW, 52)
    tag(d, "ILLUSTRATION  ·  sizes approximate (main-sequence K-type)")
    return img

def sc_decay(t, t0, t1):
    """Orbital decay: the planet spirals inward lap after lap (illustrative, timescale compressed)."""
    u = seg(t, t0, t1)
    arr = stars_bg("sparse", off=(0, -300), gain=0.5)
    arr = kstar(arr, 540, 980, 150, t, bright=1.0, corona=1.0)
    img = finish(arr, 0.45); d = ImageDraw.Draw(img, "RGBA")
    tilt = lerp(0.45, 0.62, ease_io(u))
    a0, a1 = 470, 175
    turns = 4.0
    pts = []
    for k in range(400):
        s = k / 399 * u
        a = lerp(a0, a1, s ** 1.3); ang = s * turns * 2 * math.pi
        pts.append((540 + a * math.cos(ang), 980 + a * tilt * math.sin(ang)))
    if len(pts) > 1:
        for i in range(1, len(pts)):
            al = int(40 + 200 * i / len(pts))
            d.line((pts[i - 1][0], pts[i - 1][1], pts[i][0], pts[i][1]), fill=(255, 200, 140, al), width=3)
    arr2 = np.asarray(img, np.float32).copy()
    gx, gy = pts[-1]
    a = lerp(a0, a1, u ** 1.3); ang = u * turns * 2 * math.pi
    if math.sin(ang) < 0 or a > 160:
        arr2 = giant(arr2, gx, gy, 34, ((540 - gx) / a, (gy - 980) / a, 0.3), t=t)
    img = to_img(arr2); d = ImageDraw.Draw(img, "RGBA")
    headline(d, "THE PLANET FELL IN", seg(t, ws(11, 11) - 0.2, ws(11, 11) + 0.2), 330, YELLOW, 70)
    q = seg(t, ls(12), ls(12) + 0.3)
    label(d, 540, 430, "", "orbital decay · each lap a little closer (timescale compressed)", int(255 * q), WHITE, 10)
    tag(d, "ILLUSTRATION  ·  likely mechanism per JWST study")
    return img

def sc_plunge(t, t0, t1):
    """The payoff: grazing the outer atmosphere, then plunging in (reconstruction)."""
    u = ease_in(seg(t, t0, t1)) * 0.9 + 0.1 * seg(t, t0, t1)
    arr = plunge_view(t, u * 1.15, "A")
    img = finish(arr, 0.6); d = ImageDraw.Draw(img, "RGBA")
    tag(d, "SCIENTIFIC RECONSTRUCTION  ·  not NASA footage")
    return img

def sc_ejecta(t, t0, t1):
    """Gas blasted from the star's outer layers expands and cools into dust."""
    u = seg(t, t0, t1)
    arr = stars_bg("field", off=(250, 300), gain=0.5)
    arr = kstar(arr, 540, 960, 180, t, bright=1.0 + 0.5 * (1 - u), corona=1.3)
    rng = np.random.default_rng(9); n = 1400
    ang = rng.uniform(0, 2 * np.pi, n); v = rng.uniform(0.3, 1.0, n); lat = rng.normal(0, 0.35, n)
    r = 200 + 620 * v * ease_out(u)
    cool = np.clip(r / 800, 0, 1)
    lay = np.zeros((H, W, 3), np.float32)
    x = (540 + r * np.cos(ang)).astype(int); y = (960 + r * np.sin(ang) * 0.6 + r * lat * 0.4).astype(int)
    ok = (x >= 0) & (x < W) & (y >= 0) & (y < H)
    col = np.stack([np.full(n, 255.0), 230 - 160 * cool, 180 - 160 * cool], -1) * (1 - 0.5 * cool)[:, None]
    np.add.at(lay, (y[ok], x[ok]), col[ok] * 1.4)
    lay = ndimage.gaussian_filter(lay, (2.5, 2.5, 0)) * 6 + ndimage.gaussian_filter(lay, (14, 14, 0)) * 18
    arr = arr + lay
    img = finish(arr, 0.5); d = ImageDraw.Draw(img, "RGBA")
    label(d, 540, 330, "GAS → DUST", "ejected gas expands, cools and condenses", int(255 * seg(t, ws(14, 8), ws(14, 8) + 0.4)), ORANGE, 52)
    tag(d, "SCIENTIFIC RECONSTRUCTION  ·  based on JWST interpretation")
    return img

def sc_aftermath(t, t0, t1):
    """What Webb found: hot molecular gas (CO) close to the star, colder dust farther out. Camera orbits."""
    u = ease_io(seg(t, t0, t1))
    arr = stars_bg("field", off=(-150, -400), gain=0.45)
    tilt = lerp(0.28, 0.42, u); rot = t * 0.15
    yy, xx = np.ogrid[0:H, 0:W]
    dx = (xx - 540) / 1.0; dy = (yy - 960) / tilt
    rr = np.sqrt(dx * dx + dy * dy); th = np.arctan2(dy, dx) + rot
    tex = 0.75 + 0.25 * np.sin(th * 7 + rr / 40) * np.sin(th * 3 - rr / 70)
    dust = np.exp(-((rr - 520) / 170) ** 2) * tex * 70
    gas = np.exp(-((rr - 210) / 55) ** 2) * (0.8 + 0.2 * np.sin(th * 11 - t * 2)) * 150
    front = (yy > 960).astype(np.float32)
    arr = arr + dust[..., None] * np.array([0.85, 0.42, 0.24], np.float32)
    arr = kstar(arr, 540, 960, 110, t, bright=0.9, corona=0.9)
    arr = arr + (gas * (0.55 + 0.45 * front))[..., None] * np.array([1.0, 0.75, 0.4], np.float32)
    arr = arr + (dust * front * 0.6)[..., None] * np.array([0.6, 0.3, 0.18], np.float32)
    img = finish(arr, 0.5); d = ImageDraw.Draw(img, "RGBA")
    q1 = seg(t, ws(15, 6) - 0.2, ws(15, 6) + 0.3); q2 = seg(t, ws(15, 9) - 0.2, ws(15, 9) + 0.3); q3 = seg(t, ls(16) - 0.1, ls(16) + 0.3)
    headline(d, "WHAT WEBB FOUND", seg(t, t0 + 0.2, t0 + 0.6), 300, YELLOW, 70)
    label(d, 540, 1115, "HOT MOLECULAR GAS", "incl. carbon monoxide (CO)", int(255 * max(q1, q2)), (255, 200, 120), 32)
    label(d, 540, 1235, "COLDER DUST", "farther out", int(255 * q3), (220, 140, 110), 30)
    tag(d, "SCIENTIFIC RECONSTRUCTION  ·  inferred from JWST spectra")
    return img

def sc_point(t, t0, t1):
    """Pull back until the whole system is a single point of light; then its light splits into a spectrum."""
    u = ease_io(seg(t, t0, t0 + 3.5))
    arr = B.lens_view(B.plate("bulge"), [], off=(60, -140), zoom=lerp(3.0, 1.6, u)) * 0.75
    s = lerp(1.0, 0.0, u)
    if s > 0.02:
        yy, xx = np.ogrid[0:H, 0:W]
        rr = np.sqrt((xx - 540) ** 2 + ((yy - 900) / 0.4) ** 2)
        ring = np.exp(-((rr - 520 * s) / (170 * s + 1)) ** 2) * 70 * s
        arr = arr + ring[..., None] * np.array([0.85, 0.42, 0.24], np.float32)
    arr = B.sun_glare(arr, 540, 900, lerp(60, 8, u), lerp(1.2, 0.8, u), (1.0, 0.78, 0.55))
    img = finish(arr, 0.5); d = ImageDraw.Draw(img, "RGBA")
    k = seg(t, ws(17, 14) - 0.3, ws(17, 14) + 0.5)
    if k > 0:                                                                       # illustrative infrared spectrum
        x0, x1, y0, y1 = 110, 970, 1080, 1300
        d.rectangle((x0 - 14, y0 - 60, x1 + 14, y1 + 40), fill=(0, 0, 0, int(190 * k)))
        bar = np.zeros((30, x1 - x0, 3), np.uint8)
        for i in range(x1 - x0):
            hue = i / (x1 - x0); bar[:, i] = (int(255 * min(1, 2 - 2 * hue)), int(255 * (1 - abs(hue - 0.5) * 2)), int(255 * min(1, 2 * hue)))
        img.paste(Image.fromarray(bar[:, ::-1]), (x0, y0 - 40)); d = ImageDraw.Draw(img, "RGBA")
        xs = np.linspace(0, 1, 300)[: int(300 * k)]
        spec = 0.35 + 0.25 * xs + 0.35 * np.exp(-((xs - 0.62) / 0.025) ** 2) + 0.15 * np.exp(-((xs - 0.85) / 0.08) ** 2)
        pts = [(x0 + x * (x1 - x0), y1 - s_ * (y1 - y0)) for x, s_ in zip(xs, spec)]
        if len(pts) > 1: d.line(pts, fill=(255, 212, 0), width=4)
        d.text((x0 + 0.62 * (x1 - x0), y0 + 6), "CO", font=font(F_UI, 28), fill=(255, 212, 0), anchor="mm", stroke_width=4, stroke_fill=BLACK)
        d.text((x0, y1 + 24), "infrared spectrum  (illustrative)", font=font(F_MONO, 20), fill=(220, 220, 225), anchor="lm")
    headline(d, "TO WEBB: ONE POINT OF LIGHT", seg(t, ws(17, 6) - 0.2, ws(17, 6) + 0.2), 330, WHITE, 54)
    tag(d, "SIMULATED FIELD  ·  graphic illustrative, not the published spectrum", (130, 210, 255))
    return img

def sc_safe(t, t0, t1):
    u = ease_io(seg(t, t0, t1))
    mid = (SUNP + TARGET) / 2
    cam = mid + np.array([1.0, -4.0, 14.0], np.float32)
    arr = B.render_galaxy(cam, mid * 0.7, fov=lerp(55, 60, u), up=(1, 0, 0), dust_k=0.6, gain=2.6)
    img = finish(arr, 0.4); d = ImageDraw.Draw(img, "RGBA")
    r_, u_, f_ = B.look_at(cam, mid * 0.7, (1, 0, 0)); fpx = (W / 2) / math.tan(math.radians(lerp(55, 60, u) / 2))
    def proj(Q):
        dd = Q - cam; z = dd @ f_
        return W / 2 + (dd @ r_) / z * fpx, H / 2 - (dd @ u_) / z * fpx
    sx, sy = proj(SUNP); tx, ty = proj(TARGET)
    d.line((sx, sy, tx, ty), fill=(255, 212, 0, 200), width=3)
    d.ellipse((sx - 8, sy - 8, sx + 8, sy + 8), fill=(255, 230, 140)); label(d, sx + 18, sy, "US", None, 255, (255, 230, 140), 26, "lm")
    d.ellipse((tx - 10, ty - 10, tx + 10, ty + 10), outline=(255, 150, 70), width=4)
    headline(d, "NO THREAT TO EARTH", seg(t, ws(18, 8) - 0.2, ws(18, 8) + 0.2), 330, WHITE, 64)
    tag(d, "CGI MODEL  ·  ~12,000 light-years apart", (130, 210, 255))
    return img

def sc_final(t, t0):
    """The aftermath glowing quietly; the planet's final path traced as a fading arc of light."""
    u = ease_io(seg(t, t0, DUR))
    arr = stars_bg("field", off=(-150, -400), gain=0.45)
    yy, xx = np.ogrid[0:H, 0:W]
    tilt = 0.35
    rr = np.sqrt((xx - 540) ** 2 + ((yy - 980) / tilt) ** 2)
    dust = np.exp(-((rr - 560) / 190) ** 2) * 60
    arr = arr + dust[..., None] * np.array([0.85, 0.42, 0.24], np.float32)
    arr = kstar(arr, 540, 980, lerp(120, 140, u), t, bright=0.95, corona=1.0)
    img = finish(arr, 0.5); d = ImageDraw.Draw(img, "RGBA")
    pts = []
    for k in range(300):
        s = k / 299; a = lerp(470, 120, s ** 1.3); ang = s * 4 * 2 * math.pi
        pts.append((540 + a * math.cos(ang), 980 + a * tilt * math.sin(ang)))
    for i in range(1, len(pts)):
        al = int((40 + 160 * i / len(pts)) * (0.5 + 0.5 * math.sin(t * 2)) * 0.8)
        d.line((pts[i - 1][0], pts[i - 1][1], pts[i][0], pts[i][1]), fill=(255, 190, 120, al), width=2)
    k = seg(t, NARR_END + 0.2, NARR_END + 0.9)
    if k > 0:
        s = max(0.9, ease_out(k))
        d.text((540, 300), "WRITTEN", font=font(F_CAP, 120 * s), fill=(255, 255, 255, int(255 * k)), anchor="mm", stroke_width=11, stroke_fill=BLACK)
        d.text((540, 425), "IN LIGHT", font=font(F_CAP, 120 * s), fill=(255, 212, 0, int(255 * k)), anchor="mm", stroke_width=11, stroke_fill=BLACK)
    tag(d, "SCIENTIFIC RECONSTRUCTION  ·  ZTF SLRN-2020 aftermath")
    return img

def build():
    c = [HOOK_END, ls(2) - 0.1, ls(3) - 0.1, ls(4) - 0.1, ls(5) - 0.1, ls(6) - 0.1, ls(7) - 0.1, ls(8) - 0.1, ls(10) - 0.1,
         ls(11) - 0.1, ls(13) - 0.1, ls(14) - 0.1, ls(15) - 0.1, ls(17) - 0.1, ls(18) - 0.1, ls(19) - 0.1]
    fns = [sc_webb, sc_where, sc_flare, sc_name, sc_evidence, sc_redgiant, sc_webb2, sc_twist, sc_compare, sc_decay, sc_plunge,
           sc_ejecta, sc_aftermath, sc_point, sc_safe]
    out = [(0.0, HOOK_END, hook_frame)]
    for i, fn in enumerate(fns):
        out.append((c[i], c[i + 1], (lambda f, a, b: (lambda t: f(t, a, b)))(fn, c[i], c[i + 1])))
    out.append((c[-1], DUR + 1, lambda t: sc_final(t, c[-1])))
    return out
SCENES = build()

# ====================================================================== captions
PHRASE_TEXT = [
 "A STAR ATE ITS OWN PLANET.",
 "YOU'D NEVER GUESS WHY: | IN 2025, NASA'S WEBB FOUND | THE STAR WASN'T DYING. | SO HOW DID IT HAPPEN?",
 "12,000 LIGHT-YEARS AWAY, | IN THE CONSTELLATION AQUILA, | A STAR SUDDENLY FLARED UP | IN 2020.",
 "FOR ABOUT TEN DAYS, | IT BLAZED FAR BRIGHTER THAN NORMAL. | THEN IT FADED, | BUT KEPT GLOWING IN INFRARED FOR MONTHS.",
 "ASTRONOMERS NAMED IT ZTF SLRN-2020.",
 "IN 2023, A TEAM ANNOUNCED | THE FIRST DIRECT EVIDENCE | OF A STAR SWALLOWING A PLANET, | MOST LIKELY A GAS GIANT, | ROUGHLY THE SIZE OF JUPITER.",
 "THEIR EXPLANATION: AN AGING STAR, | SWELLING INTO A RED GIANT, | HAD ENGULFED THE PLANET IN ITS PATH.",
 "THEN THE JAMES WEBB SPACE TELESCOPE | TOOK A CLOSER LOOK.",
 "AND WEBB FOUND A TWIST.",
 "THE STAR WAS TOO FAINT | TO BE A RED GIANT.",
 "IT'S MOST LIKELY A STAR | STILL IN THE PRIME OF ITS LIFE, | SLIGHTLY SMALLER AND COOLER THAN OUR SUN.",
 "SO THE STAR DIDN'T GROW | TO REACH THE PLANET. | THE PLANET FELL INTO THE STAR.",
 "ITS ORBIT PROBABLY SHRANK | OVER A VERY LONG TIME, | EACH LAP A LITTLE CLOSER THAN THE LAST.",
 "UNTIL IT GRAZED | THE STAR'S OUTER ATMOSPHERE, | AND PLUNGED IN.",
 "THE STAR BLASTED GAS AWAY | FROM ITS OUTER LAYERS. | AS THAT GAS EXPANDED AND COOLED, | IT FORMED DUST.",
 "AND WEBB FOUND WHAT WAS LEFT: | HOT MOLECULAR GAS, | INCLUDING CARBON MONOXIDE, | STILL GLOWING CLOSE TO THE STAR,",
 "SURROUNDED BY COLDER DUST, FARTHER OUT.",
 "THESE PICTURES ARE RECONSTRUCTIONS. | TO WEBB, THE WHOLE SYSTEM | IS A SINGLE POINT OF LIGHT. | EVERY DETAIL CAME FROM SPLITTING | THAT LIGHT INTO A SPECTRUM.",
 "THIS HAPPENED FAR FROM US, | AND IT POSES NO THREAT TO EARTH.",
 "BUT SOMEWHERE OUT THERE, | A PLANET'S FINAL MOMENTS | ARE STILL WRITTEN IN LIGHT, | AND WEBB IS LEARNING TO READ THEM.",
]
KEY = {"ATE", "PLANET.", "WEBB", "WASN'T", "DYING.", "12,000", "2020.", "TEN", "INFRARED", "ZTF", "SLRN-2020.", "2023,", "FIRST", "JUPITER.",
       "RED", "GIANT,", "GIANT.", "TWIST.", "FAINT", "PRIME", "FELL", "SHRANK", "PLUNGED", "DUST.", "CARBON", "MONOXIDE,", "COLDER",
       "RECONSTRUCTIONS.", "SINGLE", "SPECTRUM.", "NO", "THREAT", "LIGHT,", "2025,"}
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
    if t < ls(1) - 0.05 or t >= NARR_END + 0.2: return
    for a, b, ph in PHRASES:
        if not (a <= t < b): continue
        d = ImageDraw.Draw(img); f = font(F_CAP, 68); gap = 16; maxw = 880
        items = [(w, f.getlength(w), bool(re.search(r"\d", w)) or w in KEY) for w, s, e in ph]
        rows, cur, cw = [], [], 0
        for it in items:
            if cur and cw + gap + it[1] > maxw: rows.append(cur); cur, cw = [], 0
            cur.append(it); cw += (gap if len(cur) > 1 else 0) + it[1]
        rows.append(cur)
        k = ease_out(seg(t, a, a + 0.12)); al = int(255 * k); dy = 12 * (1 - k)
        lh = 80; y0 = 1420 - (len(rows) - 1) * lh / 2 + dy
        lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
        for ri, row in enumerate(rows):
            tw = sum(x[1] for x in row) + gap * (len(row) - 1); x = 520 - tw / 2                 # slightly left of centre: clear of right-side controls
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

def warm():
    _hires_sun(); jtex(); B.plate("field"); B.plate("sparse"); B.plate("bulge"); B.galaxy(); B.grid()
FINAL_X264 = ["-c:v", "libx264", "-preset", "slow", "-crf", "15", "-maxrate", "18M", "-bufsize", "36M", "-profile:v", "high", "-level", "4.2",
              "-pix_fmt", "yuv420p", "-g", "60", "-x264-params", "aq-mode=3:aq-strength=0.9:deblock=-1,-1", "-r", "30", "-fps_mode", "cfr"]
def encode(frames, out):
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"] + FINAL_X264 + [out], stdin=subprocess.PIPE)
    warm()
    with Pool(4) as pool:
        for i, b in enumerate(pool.imap(frame, frames, chunksize=2)):
            p.stdin.write(b)
            if i % 300 == 0: print("frame", frames[0] + i, flush=True)
    p.stdin.close(); p.wait()

# ====================================================================== sound
def rumble(d=3.0, f=40):
    n = int(d * SR); tt = np.arange(n) / SR
    return (lp(arng.normal(0, 1, n), 160) * 1.2 + np.sin(2 * np.pi * f * tt) * 0.5) * np.minimum(1, tt / 0.6) * np.minimum(1, (d - tt) / 0.8)
def render_audio(out):
    n = int(DUR * SR); tt = np.arange(n) / SR
    chords = [(0, [41.2, 61.74, 98.0, 123.47]), (ls(5), [43.65, 65.41, 103.83, 130.81]), (ls(8), [46.25, 69.3, 110.0, 138.59]),
              (ls(12), [38.89, 58.27, 92.5, 116.54]), (ls(15), [43.65, 65.41, 110.0, 130.81]), (ls(19), [41.2, 61.74, 103.83, 155.56, 207.65])]
    pad = np.zeros(n)
    for ci, (t0, notes) in enumerate(chords):
        t1 = chords[ci + 1][0] if ci + 1 < len(chords) else DUR
        i0, i1 = int(t0 * SR), min(n, int(t1 * SR) + int(1.0 * SR)); m = i1 - i0; sg = np.zeros(m)
        for f in notes:
            for det in (-0.1, 0.0, 0.09): sg += osc(f * 2 ** (det / 12), m)
        e = np.minimum(1, np.arange(m) / (1.0 * SR)) * np.minimum(1, (m - np.arange(m)) / (1.0 * SR))
        pad[i0:i1] += sg * e / 12
    pulse = np.zeros(n); t = ls(12); bpm = 70                                       # tension builds through the orbital decay
    while t < ls(14):
        place(pulse, boom(0.45, 64, 40, 0.11), t, 0.3 + 0.4 * (t - ls(12)) / (ls(14) - ls(12))); bpm += 3; t += 60 / bpm
    swell = np.interp(tt, [0, 2.0, 2.6, ls(8), ls(12), ls(14), ls(15), NARR_END, DUR - 0.5, DUR], [0.9, 0.9, 0.55, 0.85, 0.85, 1.15, 0.8, 0.9, 0.5, 0.0])
    mus = (lp(pad, 1000) * 0.7 + lp(pad, 360) * 0.6 + osc(30.9, n, "sin") * 0.16 + pulse) * swell
    fx = np.zeros(n)
    place(fx, reverb(boom(2.8, 110, 22, 0.9), 3.4, 0.45), 0.0, 1.7)                                # one frame-0 impact
    place(fx, rumble(2.4, 38), 0.0, 0.6)
    for a, b, fn in SCENES[1:]: place(fx, whoosh(0.6), a - 0.2, 0.13)
    place(fx, riser(1.2, 90) * 0.5, ws(8, 3) - 1.2, 0.35)                                            # "twist"
    place(fx, rumble(4.0, 32), ls(13) - 0.4, 0.9)                                                    # the plunge
    place(fx, reverb(boom(2.2, 90, 26, 0.6), 3.0, 0.4), ws(13, 7), 0.8)
    place(fx, lp(arng.normal(0, 1, int(5 * SR)), 500) * np.exp(-np.arange(int(5 * SR)) / SR / 2.5) * 0.6, ls(14), 0.5)   # outflowing gas
    m = int(4.5 * SR); tm = np.arange(m) / SR
    place(fx, sum(np.sin(2 * np.pi * f * tm) * np.exp(-tm / dec) * a for f, dec, a in ((392.0, 2.6, 0.5), (523.25, 2.0, 0.3), (784.0, 1.3, 0.16))), NARR_END + 0.25, 0.5)
    vo = np.zeros(n)
    for l in TIM:
        s, _ = sf.read(l["file"]); place(vo, s, l["start"])
    vo = lp(hp(vo, 80), 13500); vo = vo / (np.abs(vo).max() + 1e-9) * 0.9
    env = lp(np.abs(vo), 7); env /= env.max() + 1e-9
    duck = 1 - 0.68 * np.clip(env * 3, 0, 1)
    mix = vo + mus * 0.12 * duck + fx * 0.3 * (0.4 + 0.6 * duck)
    sf.write(out, np.stack([np.tanh(mix * 1.05) * 0.95] * 2, 1).astype(np.float32), SR, subtype="FLOAT")

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "stills":
        warm(); os.makedirs("st", exist_ok=True)
        for x in sys.argv[2:]:
            t = float(x); Image.frombytes("RGB", (W, H), frame(int(round(t * FPS)))).save(f"st/s_{int(t * 100):05d}.png")
    elif cmd == "hookone":
        warm()
        p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                              "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", f"hook{HOOK}.mp4"], stdin=subprocess.PIPE)
        for i in range(60): p.stdin.write(frame(i))
        p.stdin.close(); p.wait()
    elif cmd == "audio": render_audio(sys.argv[2])
    elif cmd == "preview":
        t0, t1, out = float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
        encode(list(range(int(t0 * FPS), int(t1 * FPS))), "_v.mp4"); render_audio("_a.wav")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", "_v.mp4", "-ss", str(t0), "-t", str(t1 - t0), "-i", "_a.wav", "-map", "0:v", "-map", "1:a",
                        "-af", "loudnorm=I=-14:TP=-1.5", "-c:v", "copy", "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-shortest", out], check=True)
    elif cmd == "final": encode(list(range(NF)), "video_final_v.mp4")
