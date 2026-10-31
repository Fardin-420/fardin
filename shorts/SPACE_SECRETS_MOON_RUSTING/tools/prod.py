#!/usr/bin/env python3
# SPACE SECRETS — "The Moon Is Rusting" — production renderer (scenes, phrase captions, sound design).
# Usage: python3 prod.py preview t0 t1 out.mp4 | stills t... | full out.mp4 | audio out.wav
import json, math, os, re, subprocess, sys
from multiprocessing import Pool
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

import moonfx as M
from moonfx import W, H, FPS, seg, ease, ease_out, ease_in, ease_io, lerp, clamp, font, F_CAP, F_UI, F_MONO, WHITE, YELLOW, BLACK
from sfx import SR, lp, hp, bp, place, osc, boom, crack, whoosh, tick, riser, reverb, arng

TIM = json.load(open("timing.json"))
def ls(i): return TIM[i]["start"]
def le(i): return TIM[i]["start"] + TIM[i]["dur"]
def ws(i, k): return TIM[i]["words"][k][1]
NARR_END = le(len(TIM) - 1)
DUR = round(NARR_END + 2.4, 1)
NF = int(DUR * FPS)
SUN = (-0.72, 0.30, 0.62)
O_GREEN = (120, 255, 190)

def macro(): return M.cache("macro", M.make_macro)

def zoom_blur(img, amount, cx=540, cy=960, n=7):
    """Radial motion blur for whip moves (amount = fractional scale spread)."""
    if amount < 0.004: return img
    acc = np.zeros((H, W, 3), np.float32)
    for i in range(n):
        s = 1 + amount * i / (n - 1)
        w_, h_ = W * s, H * s
        box = (cx - cx / s, cy - cy / s, cx + (W - cx) / s, cy + (H - cy) / s)
        acc += np.asarray(img.transform((W, H), Image.EXTENT, box, Image.BILINEAR), np.float32)
    return Image.fromarray(np.clip(acc / n, 0, 255).astype(np.uint8))

def to_img(arr): return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

def label(d, x, y, title, body=None, a=255, col=WHITE, anchor="mm", size=34):
    d.text((x, y), title, font=font(F_UI, size), fill=col + (a,), anchor=anchor, stroke_width=5, stroke_fill=BLACK)
    if body: d.text((x, y + size + 6), body, font=font(F_MONO, 22), fill=(225, 225, 230, a), anchor=anchor, stroke_width=4, stroke_fill=BLACK)

def headline(d, txt, k, y=300, col=WHITE, size=74):
    if k <= 0: return
    a = int(255 * k); dy = 16 * (1 - ease_out(k))
    d.text((540, y + dy), txt, font=font(F_CAP, size), fill=col + (a,), anchor="mm", stroke_width=9, stroke_fill=BLACK + (a,))

# ====================================================================== SCENE 01 — hook (0 – 2.55 s)
EC, ER = (540, 2430), 1160
MC, MR = (540, 735), 285
HOOK_END = ls(2) - 0.08

def o_paths(ec, eR, mc, mR, k=7, spread=0.42):
    paths = []
    for a in np.linspace(-spread, spread, k):
        p0 = (ec[0] + eR * 1.012 * math.sin(a), ec[1] - eR * 1.012 * math.cos(a))
        p3 = (mc[0] + mR * 0.5 * math.sin(a * 2), mc[1] + mR * 0.9)
        paths.append((p0, (p0[0] + 240 * math.sin(a * 1.7) + 110, p0[1] - 240), (p3[0] + 180, p3[1] + 240), p3))
    return paths

def earth_moon(t, life=1.0, stream=1.0, mR=MR, mc=MC):
    arr = M.stars().copy()
    arr = M.earth_disc(arr, EC[0], EC[1], ER, lon=20 + 1.5 * t, lat0=5, sun=SUN)
    arr = M.limb_glow(arr, EC[0], EC[1], ER, SUN)
    arr = M.moon(arr, mc[0], mc[1], mR, light=SUN, lat0=8, hem=0.9, earthshine=0.6)
    if stream > 0:
        arr = M.particles(arr, o_paths(EC, ER, mc, mR), t, n=200, speed=0.42, size=3.0, amt=0.55 * stream, spread=9, life=life)
    return arr

def sc_hook(t):
    if t < 0.62:                                                                  # extreme macro: grains turn to hematite
        k = lerp(0.55, 1.25, seg(t, 0.0, 0.42))
        z = 2.3 * math.exp(-2.6 * ease_in(seg(t, 0.38, 0.62)))
        img = to_img(M.tone(M.macro_frame(macro(), k, zoom=z)))
        img = zoom_blur(img, 0.5 * seg(t, 0.38, 0.62))
        if t > 0.5:                                                                # whip into the full Moon over Earth
            R = 3600
            g = to_img(M.tone(M.moon(M.stars().copy(), 540, MC[1] + 600, R, light=SUN, lat0=8, hem=0.9)))
            img = Image.blend(img, zoom_blur(g, 0.6), seg(t, 0.5, 0.62))
    elif t < 1.05:
        u = ease_out(seg(t, 0.62, 1.05))
        R = lerp(3600, MR, u); cy = lerp(MC[1] + 600, MC[1], u)
        arr = earth_moon(t, life=0.05, stream=0.0, mR=R, mc=(540, cy)) if u > 0.35 else M.moon(M.stars().copy(), 540, cy, R, light=SUN, lat0=8, hem=0.9)
        img = zoom_blur(M.finish(arr, 0.45), 0.6 * (1 - u))
    else:
        img = M.finish(earth_moon(t, life=clamp((t - 1.05) / 0.8, 0.05, 1.0)), 0.45)
    d = ImageDraw.Draw(img, "RGBA")
    M.hook_title(d, max(0.85, 1.15 - 0.3 * seg(t, 0, 0.12)))
    if t >= 1.05: M.tag(d, "SCIENTIFIC VISUALIZATION  ·  oxygen ions shown glowing", O_GREEN)
    return img

# ====================================================================== SCENE 02 — airless surface (2.55 – 10.8 s)
def sun_glare(arr, x, y, r=34, amt=1.0):
    yy, xx = np.ogrid[0:H, 0:W]
    d = np.sqrt((xx - x) ** 2 + (yy - y) ** 2)
    core = np.clip(1 - d / r, 0, 1) ** 0.5 * 600 + np.exp(-d / (r * 2.2)) * 160 + np.exp(-d / (r * 9)) * 40
    streak = np.exp(-np.abs(yy - y) / 3.0) * np.exp(-np.abs(xx - x) / 420) * 120
    return arr + ((core + streak) * amt)[..., None] * np.array([1.0, 0.98, 0.93], np.float32)

def sc_surface(t, t0, t1):
    """Low-angle fly over cratered regolith, sun low behind-left, black sky."""
    u = (t - t0) / (t1 - t0)
    h = M.terrain()[0]
    e = ease_io(u)
    x, y = 760 + 40 * e, 300 + 420 * e                                           # brisk forward dolly with a slow yaw sweep
    ground = ndimage.map_coordinates(h, [[y], [x]], order=1, mode="wrap")[0]
    arr = M.terrain_shot(x, y, ground + lerp(11, 24, e), math.pi / 2 - 0.35 + 0.5 * e, horizon=lerp(0.28, 0.33, e), fov=64, sun_el=14.0)
    img = M.finish(arr, 0.3, exp=1.15)
    d = ImageDraw.Draw(img, "RGBA")
    M.tag(d, "CGI RECONSTRUCTION  ·  lunar regolith, low sun", (200, 200, 200))
    return img

def sc_horizon(t, t0, t1):
    """Camera rises: hard horizon, pitch-black sky in daylight, the Sun as a white point -> no air to scatter light."""
    u = ease(seg(t, t0, t1))
    h = M.terrain()[0]
    x, y = 1500 + 40 * u, 600
    ground = ndimage.map_coordinates(h, [[y], [x]], order=1, mode="wrap")[0]
    sky = M.sun_glare(M.stars(seed=9, n=900).copy(), 250, lerp(640, 600, u), 30, 1.0) if hasattr(M, "sun_glare") else sun_glare(M.stars(seed=9, n=900).copy(), 250, lerp(640, 600, u), 30)
    arr = M.terrain_shot(x, y, ground + lerp(14, 60, u), math.pi + 0.35, horizon=lerp(0.40, 0.36, u), fov=72, sun_el=14.0, sky=sky)
    img = M.finish(arr, 0.5, exp=1.15); d = ImageDraw.Draw(img, "RGBA")
    q = seg(t, ws(3, 4), ws(3, 4) + 0.4)
    if q > 0: label(d, 540, 520, "NO AIR TO SCATTER SUNLIGHT", "the sky stays black, even at noon", int(255 * q), (200, 220, 255))
    M.tag(d, "CGI RECONSTRUCTION  ·  airless sky", (200, 200, 200))
    return img

# ====================================================================== SCENE 03 — Chandrayaan-1 + M3 (10.8 – 21.4 s)
def box(c, s):
    x, y, z = c; a, b, e = s[0] / 2, s[1] / 2, s[2] / 2
    v = np.array([[x - a, y - b, z - e], [x + a, y - b, z - e], [x + a, y + b, z - e], [x - a, y + b, z - e],
                  [x - a, y - b, z + e], [x + a, y - b, z + e], [x + a, y + b, z + e], [x - a, y + b, z + e]], np.float32)
    F = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (1, 2, 6, 5), (0, 3, 7, 4)]
    return [(v[list(f)]) for f in F]

def spacecraft(d, cx, cy, scale, yaw, pitch, light=SUN):
    """Chandrayaan-1-like orbiter (reconstruction): ~1.5 m gold-foil cube, one solar wing, a dish on a boom."""
    faces = []
    for q in box((0, 0, 0), (1.5, 1.5, 1.5)): faces.append((q, (205, 160, 70), "foil"))
    for q in box((1.95, 0, 0), (2.2, 0.04, 1.6)): faces.append((q, (32, 44, 92), "cells"))
    for q in box((0.95, 0, 0), (0.45, 0.06, 0.06)): faces.append((q, (170, 170, 175), None))
    for q in box((-0.75 - 0.35, 0.3, 0.2), (0.7, 0.05, 0.05)): faces.append((q, (170, 170, 175), None))
    for q in box((-1.45, 0.3, 0.2), (0.06, 0.7, 0.7)): faces.append((q, (225, 225, 228), "dish"))
    for q in box((0, -0.8, 0.35), (0.35, 0.12, 0.3)): faces.append((q, (60, 60, 64), None))      # M3-style instrument box (nadir)
    cy_, sy = math.cos(yaw), math.sin(yaw); cp, sp = math.cos(pitch), math.sin(pitch)
    Rm = np.array([[cy_, 0, sy], [0, 1, 0], [-sy, 0, cy_]], np.float32) @ np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]], np.float32)
    L = np.array(light, np.float32); L /= np.linalg.norm(L)
    out = []
    for q, col, kind in faces:
        p = q @ Rm.T
        nrm = np.cross(p[1] - p[0], p[2] - p[0]); nl = np.linalg.norm(nrm)
        if nl < 1e-6: continue
        nrm /= nl
        if nrm[2] < 0: nrm = -nrm
        sh = 0.25 + 0.95 * max(0.0, float(nrm @ L))
        out.append((float(p[:, 2].mean()), [(cx + v[0] * scale, cy - v[1] * scale) for v in p], tuple(int(clamp(c * sh, 0, 255)) for c in col), kind, sh))
    out.sort(key=lambda o: o[0])
    for z, pts, col, kind, sh in out:
        d.polygon(pts, fill=col)
        if kind == "cells":
            for k in range(1, 6):
                a = [lerp(pts[0][i], pts[1][i], k / 6) for i in range(2)]; b = [lerp(pts[3][i], pts[2][i], k / 6) for i in range(2)]
                d.line((a[0], a[1], b[0], b[1]), fill=(80, 100, 150), width=1)
        if kind == "foil":
            d.line(pts + [pts[0]], fill=(255, 220, 140), width=1)

def sc_orbiter(t, t0, t1):
    u = ease_io(seg(t, t0, t1))
    arr = M.stars().copy()
    arr = M.moon(arr, 540, 2480, 1700, light=SUN, lat0=25 + 10 * u, lon_c=-20 + 14 * u, hem=0.0)
    img = M.finish(arr, 0.35); d = ImageDraw.Draw(img, "RGBA")
    spacecraft(d, lerp(330, 720, u), lerp(640, 560, u), 175, 0.6 + 1.1 * u, 0.32, SUN)
    q = seg(t, ws(4, 6), ws(4, 6) + 0.4)
    if q > 0: label(d, 540, 960, "CHANDRAYAAN-1 (India, 2008–09)", "carrying NASA's Moon Mineralogy Mapper (M3)", int(255 * q), (255, 210, 140))
    M.tag(d, "RECONSTRUCTION  ·  not mission imagery", (255, 200, 120))
    return img

def m3_colour():
    """False-colour 'mineral map' version of the orbital terrain plate (illustrative)."""
    def make():
        col = M.shaded(25.0); h, alb = M.terrain()
        rng = np.random.default_rng(31)
        n1 = ndimage.gaussian_filter(rng.normal(0, 1, (M.N, M.N)).astype(np.float32), 40, mode="wrap"); n1 /= n1.std()
        n2 = ndimage.gaussian_filter(rng.normal(0, 1, (M.N, M.N)).astype(np.float32), 14, mode="wrap"); n2 /= n2.std()
        lum = col.mean(-1, keepdims=True)
        fc = np.stack([0.92 + 0.10 * n1, 0.95 + 0.05 * n2, 1.08 - 0.10 * n1], -1)
        fc = lum * fc * 1.05
        spots = np.clip((ndimage.gaussian_filter(rng.normal(0, 1, (M.N, M.N)).astype(np.float32), 3, mode="wrap") * 5 - 2.6), 0, 1)
        return np.clip(fc, 0, 255).astype(np.float32), spots.astype(np.float32)
    return M.cache("m3", make)

def sc_scan(t, t0, t1):
    """Looking straight down from orbit: the push-broom spectrometer swath sweeps the ground."""
    u = seg(t, t0, t1)
    col = M.shaded(25.0); fc, spots = m3_colour()
    cw = 900; ch = cw * H / W; cx0 = 1024; cy0 = 400 + 420 * u
    box_ = (cx0 - cw / 2, cy0 - ch / 2, cx0 + cw / 2, cy0 + ch / 2)
    plain = np.asarray(M.cache("plain25", lambda: to_img(M.tone(col))).transform((W, H), Image.EXTENT, box_, Image.BILINEAR), np.float32)
    false = np.asarray(M.cache("fc25", lambda: to_img(M.tone(fc))).transform((W, H), Image.EXTENT, box_, Image.BILINEAR), np.float32)
    sp = np.asarray(M.cache("sp25", lambda: Image.fromarray((spots * 255).astype(np.uint8))).transform((W, H), Image.EXTENT, box_, Image.BILINEAR), np.float32)[..., None] / 255
    line = lerp(1600, 300, u)                                                      # scan line moves up the frame (ground scrolls)
    yy = np.arange(H, dtype=np.float32)[:, None, None]
    scanned = np.clip((yy - line) / 30, 0, 1)
    hk = seg(t, ws(4, 12) - 0.2, ws(4, 12) + 0.4)
    mapped = false * (1 - sp * hk) + np.array([235, 70, 45], np.float32) * sp * hk
    arr = plain * (1 - scanned) + mapped * scanned
    arr += np.exp(-np.abs(yy - line) / 6) * np.array([170, 230, 255], np.float32) * 0.9
    img = to_img(arr); d = ImageDraw.Draw(img, "RGBA")
    if hk > 0: label(d, 540, 330, "HEMATITE-LIKE SIGNATURES", "spectral fingerprint consistent with hematite", int(255 * hk), (255, 140, 110))
    M.tag(d, "ILLUSTRATION  ·  false-colour mineral mapping", (120, 220, 210))
    return img

def sc_poles(t, t0, t1):
    """Orbit up over the north pole: where the signatures cluster (illustrative distribution, exaggerated colour)."""
    u = ease_io(seg(t, t0, t1 - 0.4))
    R = lerp(470, 640, u); lat0 = lerp(25, 72, u)
    arr = M.moon(M.stars().copy(), 540, 900, R, light=(-0.55, 0.55, 0.62), lat0=lat0, lon_c=lerp(-25, 0, u),
                 hem=lerp(0.5, 1.0, seg(t, ws(4, 17), ws(4, 18))), hem_col=(225, 75, 45), earthshine=0.5)
    img = M.finish(arr, 0.4); d = ImageDraw.Draw(img, "RGBA")
    q = seg(t, ws(4, 17) - 0.1, ws(4, 17) + 0.3)
    if q > 0:
        label(d, 540, 300, "HEMATITE — IRON OXIDE", "Fe₂O₃ · signatures at high latitudes", int(255 * q), (255, 150, 110), size=46)
    M.tag(d, "ILLUSTRATIVE MAP  ·  colour exaggerated · after Li et al. 2020", (255, 150, 110))
    return img

# ====================================================================== generic mesh drawing (reconstructions)
def draw_mesh(d, faces, cx, cy, scale, yaw, pitch, light=SUN):
    cy_, sy = math.cos(yaw), math.sin(yaw); cp, sp = math.cos(pitch), math.sin(pitch)
    Rm = np.array([[cy_, 0, sy], [0, 1, 0], [-sy, 0, cy_]], np.float32) @ np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]], np.float32)
    L = np.array(light, np.float32); L /= np.linalg.norm(L)
    out = []
    for q, col, kind in faces:
        p = np.asarray(q, np.float32) @ Rm.T
        nrm = np.cross(p[1] - p[0], p[2] - p[0]); nl = np.linalg.norm(nrm)
        if nl < 1e-6: continue
        nrm /= nl
        if nrm[2] < 0: nrm = -nrm
        sh = 0.22 + 0.95 * max(0.0, float(nrm @ L))
        out.append((float(p[:, 2].mean()), [(cx + v[0] * scale, cy - v[1] * scale) for v in p], tuple(int(clamp(c * sh, 0, 255)) for c in col), kind))
    out.sort(key=lambda o: o[0])
    for z, pts, col, kind in out:
        d.polygon(pts, fill=col)
        if kind == "cells":
            for k in range(1, 5):
                a = [lerp(pts[0][i], pts[1][i], k / 5) for i in range(2)]; b = [lerp(pts[3][i], pts[2][i], k / 5) for i in range(2)]
                d.line((a[0], a[1], b[0], b[1]), fill=(70, 90, 140), width=1)
        if kind == "foil": d.line(pts + [pts[0]], fill=(255, 225, 150), width=1)

def lander_faces():
    """Chang'e-6-like lander + ascender (reconstruction, simplified)."""
    F = []
    for q in box((0, 0.9, 0), (2.4, 0.9, 2.4)): F.append((q, (200, 150, 60), "foil"))
    for q in box((0, 1.75, 0), (1.3, 0.8, 1.3)): F.append((q, (215, 205, 190), None))
    for q in box((1.4, 1.95, 0), (1.3, 0.04, 0.9)): F.append((q, (35, 45, 95), "cells"))
    for q in box((-1.4, 1.95, 0), (1.3, 0.04, 0.9)): F.append((q, (35, 45, 95), "cells"))
    for sx in (-1, 1):
        for sz in (-1, 1):
            for q in box((sx * 1.45, 0.35, sz * 1.45), (0.12, 0.9, 0.12)): F.append((q, (190, 190, 195), None))
            for q in box((sx * 1.6, -0.08, sz * 1.6), (0.5, 0.06, 0.5)): F.append((q, (170, 170, 175), None))
    for q in box((0.9, 1.0, 1.25), (0.15, 0.15, 1.2)): F.append((q, (120, 120, 125), None))   # sampling arm
    return F

# ====================================================================== SCENE 04 — near side vs far side (21.3 – 27.1 s)
def sc_nearfar(t, t0, t1):
    tc = ws(6, 3) - 0.2                                                          # cut to the comparison on "frequently"
    if t < tc:
        u = ease_io(seg(t, t0, tc))
        arr = M.stars().copy()
        arr = M.earth_disc(arr, 540, lerp(2500, 2150, u), 900, lon=20, lat0=5, sun=SUN)
        arr = M.limb_glow(arr, 540, lerp(2500, 2150, u), 900, SUN)
        arr = M.moon(arr, 540, 760, 360, light=(-0.5, 0.35, 0.79), lat0=30, lon_c=lerp(175, 0, u), hem=1.0, earthshine=0.5)
        img = M.finish(arr, 0.4); d = ImageDraw.Draw(img, "RGBA")
        q = seg(t, t0 + 0.5, t0 + 0.9)
        if u > 0.6: label(d, 540, 1080, "THE SIDE THAT ALWAYS FACES EARTH", None, int(255 * seg(u, 0.6, 0.8)), (170, 210, 255))
        M.tag(d, "ILLUSTRATIVE MAP  ·  colour exaggerated · after Li et al. 2020", (255, 150, 110))
        return img
    u = ease_out(seg(t, tc, tc + 0.6))
    arr = M.stars().copy()
    drift = t - tc                                                                # keep the comparison alive: slow spin + push
    for i, (lon, x) in enumerate(((0, 290), (180, 790))):
        arr = M.moon(arr, lerp(540, x, u), 760, lerp(360, 235, u) + 6 * drift, light=(-0.2, 0.3, 0.93), lat0=48 + 2 * drift, lon_c=lon + 7 * drift,
                     hem=lerp(1.0, 2.6, u), hem_col=(235, 80, 45), earthshine=0.0)
    img = M.finish(arr, 0.35); d = ImageDraw.Draw(img, "RGBA")
    if u > 0.9:
        label(d, 290, 1030, "NEAR SIDE", "faces Earth", 255, (170, 210, 255))
        label(d, 790, 1030, "FAR SIDE", "faces away", 255, (210, 210, 210))
    headline(d, "MORE DETECTED ON THE NEAR SIDE", seg(t, ws(6, 7) - 0.2, ws(6, 7) + 0.2), 380, YELLOW, 50)
    M.tag(d, "COMPARISON  ·  illustrative distribution, not data", (255, 150, 110))
    return img

# ====================================================================== SCENE 05 — oxygen escapes into the magnetotail (27.1 – 37.4 s)
def sc_towards_earth(t, t0, t1):
    """Fast orbital move from the Moon back toward Earth."""
    u = ease_io(seg(t, t0, t1))
    arr = M.stars().copy()
    eR = lerp(110, 520, u)
    arr = M.earth_disc(arr, 540, lerp(820, 860, u), eR, lon=0 + 10 * u, lat0=10, sun=SUN)
    arr = M.limb_glow(arr, 540, lerp(820, 860, u), eR, SUN)
    arr = M.moon(arr, lerp(760, 1500, ease_in(u)), lerp(1500, 2400, ease_in(u)), lerp(420, 900, u), light=SUN, lat0=10, lon_c=-30, hem=0.4)
    img = M.finish(arr, 0.4); d = ImageDraw.Draw(img, "RGBA")
    M.tag(d, "CGI  ·  Earth texture: Solar System Scope (CC BY 4.0)", (170, 210, 255))
    return img

E5, ER5 = (540, 600), 120
def field_lines(d, alpha):
    col = (130, 160, 255)
    for Lr in (1.7, 2.3, 3.0, 3.9, 5.0):
        for side in (-1, 1):                                                    # dayside (up, toward the Sun) / nightside (down)
            pts = []
            for lam in np.linspace(-1.35, 1.35, 90):
                r = Lr * ER5 * math.cos(lam) ** 2
                a = r * math.sin(lam); p = r * math.cos(lam)
                p = p * (1 - 0.32 * min(1, r / (5 * ER5))) if side < 0 else p * (1 + 1.6 * (r / (5 * ER5)) ** 2)
                pts.append((E5[0] + a * 1.0, E5[1] + side * p))
            d.line(pts, fill=col + (int(alpha * (150 - 18 * Lr)),), width=2)
    for k, off in enumerate((70, 110, 150, 195)):                               # open tail-lobe field lines
        for sgn in (-1, 1):
            x0 = E5[0] + sgn * ER5 * 0.55
            pts = [(x0 + sgn * off * math.sin(min(1, (y - E5[1]) / 500) * 1.4), y) for y in np.linspace(E5[1], H + 50, 60)]
            d.line(pts, fill=col + (int(alpha * (95 - 15 * k)),), width=2)
    d.arc((E5[0] - 420, E5[1] - 330, E5[0] + 420, E5[1] + 600), 195, 345, fill=(255, 200, 140, int(alpha * 90)), width=3)   # bow shock

def magneto_base(t, pan=0.0):
    arr = M.stars(seed=12, n=1800).copy()
    arr = sun_glare(arr, 540, -260 - pan, 160, 0.9)
    arr = M.earth_disc(arr, E5[0], E5[1] - pan, ER5, lon=10, lat0=0, sun=(0.0, 0.95, 0.3))
    arr = M.limb_glow(arr, E5[0], E5[1] - pan, ER5, (0.0, 0.95, 0.3))
    return arr

def ion_paths(pan, to_moon=None):
    P = []
    for sgn in (-1, 1):
        for k in range(4):
            x0, y0 = E5[0] + sgn * ER5 * 0.9, E5[1] - pan - 20 + k * 8
            end = (E5[0] + sgn * (40 + 25 * k), H + 120) if to_moon is None else to_moon
            P.append(((x0, y0), (x0 + sgn * (180 + 40 * k), y0 - 120), (E5[0] + sgn * (120 + 20 * k), E5[1] - pan + 520), end))
    return P

def wind_paths(pan):
    P = []
    for x in np.linspace(-500, 500, 11):
        sgn = 1 if x >= 0 else -1
        P.append(((540 + x, -40), (540 + x * 1.05, E5[1] - pan - 380), (540 + sgn * max(abs(x) * 1.1, 420), E5[1] - pan + 100), (540 + sgn * max(abs(x) * 1.2, 470), H + 60)))
    return P

def sc_magneto(t, t0, t1):
    k_lines = seg(t, t0, t0 + 0.8)
    pan = 0.0
    arr = magneto_base(t, pan)
    arr = M.particles(arr, wind_paths(pan), t, n=260, speed=0.30, size=2.0, col=np.array([255, 225, 160], np.float32), amt=0.35, spread=6, seed=8)
    ki = seg(t, ws(8, 3) - 0.3, ws(8, 3) + 1.0)
    if ki > 0: arr = M.particles(arr, ion_paths(pan), t, n=420, speed=0.22, size=3.0, amt=0.75 * ki, spread=8, seed=5, life=clamp(ki * 1.2, 0.05, 1))
    img = M.finish(arr, 0.5); d = ImageDraw.Draw(img, "RGBA")
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); field_lines(ImageDraw.Draw(lay), k_lines)
    img.paste(lay.filter(ImageFilter.GaussianBlur(1.2)), (0, 0), lay.filter(ImageFilter.GaussianBlur(1.2)))
    d = ImageDraw.Draw(img, "RGBA")
    label(d, 540, 120, "SUN ↑", None, int(255 * k_lines), (255, 220, 160), size=28)
    q = seg(t, ws(8, 12) - 0.2, ws(8, 12) + 0.3)
    if q > 0: label(d, 540, 1170, "MAGNETOTAIL", "stretches away from the Sun", int(255 * q), (150, 175, 255), size=40)
    if ki > 0: label(d, 850, 520, "O⁺ IONS", "from the upper atmosphere", int(255 * seg(ki, 0.2, 0.6)), O_GREEN, size=30)
    M.tag(d, "SCIENTIFIC VISUALIZATION  ·  not to scale", O_GREEN)
    return img

# ====================================================================== SCENE 06 — the Moon passes through the tail (37.4 – 48.1 s)
def sc_escape(t, t0, t1):
    """Close on Earth's limb: O+ ions lift off the upper atmosphere (visualized)."""
    u = ease_io(seg(t, t0, t1))
    arr = M.stars().copy()
    cx, cy, R = 540, lerp(1950, 1880, u), 1300
    arr = M.earth_disc(arr, cx, cy, R, lon=10 + 4 * u, lat0=62, sun=(-0.75, 0.35, 0.56), night=1.6)
    arr = M.limb_glow(arr, cx, cy, R, (-0.75, 0.35, 0.56), 1.6)
    yy, xx = np.ogrid[0:H, 0:W]
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    aur = np.exp(-np.abs(r - R * 1.012) / 9) * np.clip(1 - np.abs(xx - cx) / 700, 0, 1) * 70
    arr = arr + aur[..., None] * np.array(O_GREEN, np.float32) / 255
    P = []
    for a in np.linspace(-0.45, 0.45, 9):
        p0 = (cx + R * 1.01 * math.sin(a), cy - R * 1.01 * math.cos(a))
        P.append((p0, (p0[0] + 60 * a, p0[1] - 300), (p0[0] + 300 * a + 80, p0[1] - 700), (p0[0] + 600 * a + 200, -60)))
    arr = M.particles(arr, P, t, n=340, speed=0.32, size=3.0, amt=0.75, spread=14, seed=17)
    img = M.finish(arr, 0.5); d = ImageDraw.Draw(img, "RGBA")
    q = seg(t, t0 + 0.3, t0 + 0.7)
    label(d, 540, 330, "O⁺ IONS ESCAPING", "from Earth's upper atmosphere · visualized", int(255 * q), O_GREEN, size=40)
    M.tag(d, "SCIENTIFIC VISUALIZATION  ·  ions are invisible to the eye", O_GREEN)
    return img

def sc_moon_tail(t, t0, t1):
    """Reverse angle: the Moon looms in the tail; Earth far behind; ions arrive on the Earth-facing side."""
    u = ease_io(seg(t, t0, t1))
    arr = M.stars(seed=14, n=2000).copy()
    ex, ey, eR = 560, 330, lerp(70, 62, u)
    arr = M.earth_disc(arr, ex, ey, eR, lon=10, lat0=5, sun=(0.0, 0.95, 0.3))
    arr = M.limb_glow(arr, ex, ey, eR, (0.0, 0.95, 0.3))
    mR = lerp(520, 640, u); mx, my = 520, lerp(1560, 1520, u)
    arr = M.moon(arr, mx, my, mR, light=(-0.2, 0.9, 0.38), lat0=-10, lon_c=0, hem=0.0)
    kk = seg(t, ws(9, 9) - 0.6, ws(9, 12))
    P = [((ex + s * 30, ey + eR), (ex + s * 160, ey + 420), (mx + s * mR * 0.7, my - mR - 300), (mx + s * mR * 0.55, my - mR * 0.84)) for s in np.linspace(-1, 1, 9)]
    arr = M.particles(arr, P, t, n=420, speed=0.38, size=3.2, amt=0.55 + 0.4 * kk, spread=10, seed=9)
    if kk > 0:
        rng = np.random.default_rng(int(t * 30))
        for _ in range(int(14 * kk)):
            a = rng.uniform(-0.9, 0.9); x = mx + mR * 0.98 * math.sin(a); y = my - mR * 0.98 * math.cos(a)
            arr = sun_glare(arr, x, y, 4, 0.12) if False else arr
    img = M.finish(arr, 0.5)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    for k, off in enumerate((120, 220, 320)):
        for sgn in (-1, 1):
            ld.line([(ex + sgn * lerp(eR, off * 2.4, (y - ey) / (H - ey)), y) for y in np.linspace(ey, H, 30)], fill=(130, 160, 255, 55 - 12 * k), width=2)
    img.paste(lay, (0, 0), lay); d = ImageDraw.Draw(img, "RGBA")
    label(d, ex + eR + 24, ey, "EARTH", None, 200, (170, 210, 255), "lm", 24)
    M.tag(d, "SCIENTIFIC VISUALIZATION  ·  hypothesis (Li et al. 2020) · not to scale", O_GREEN)
    return img

def sc_reaction(t, t0, t1):
    """Orbital scale -> microscopic: ions land on iron-bearing grains; some convert to hematite (conceptual)."""
    u = seg(t, t0, t1)
    kr = lerp(0.0, 1.15, ease(seg(t, ws(10, 7), ws(10, 12) + 0.4)))
    z = lerp(1.1, 1.75, ease_io(u))
    arr = M.macro_frame(macro(), kr, zoom=z, cx=0.5, cy=0.5)
    P = [((540 + 600 * s, -80), (540 + 400 * s, 500), (540 + 120 * s, 900), (540 + 200 * s * math.sin(s * 3), 1050 + 150 * s)) for s in np.linspace(-1, 1, 9)]
    arr = M.particles(arr, P, t, n=160, speed=0.5, size=4.0, amt=0.6, spread=40, seed=13)
    img = M.finish(arr, 0.35); d = ImageDraw.Draw(img, "RGBA")
    headline(d, "POSSIBLE FORMATION PROCESS", seg(t, t0 + 0.2, t0 + 0.6), 300, WHITE, 58)
    q = seg(t, ws(10, 7), ws(10, 7) + 0.4)
    if q > 0: label(d, 540, 400, "iron-bearing minerals + oxygen  →  hematite (Fe₂O₃)", None, int(255 * q), (255, 170, 140), size=30)
    M.tag(d, "CGI CONCEPT  ·  microscopic scale, not observed directly", O_GREEN)
    return img

# ====================================================================== SCENE 07 — Chang'e-6 samples (48.1 – 61.4 s)
def sc_farside_swing(t, t0, t1):
    u = ease_io(seg(t, t0, t1))
    arr = M.moon(M.stars().copy(), 540, 900, lerp(380, 470, u), light=(0.75, 0.2, 0.62), lat0=-20, lon_c=lerp(60, 175, u), hem=0.0)
    img = M.finish(arr, 0.4); d = ImageDraw.Draw(img, "RGBA")
    M.tag(d, "CGI  ·  real lunar albedo map (NASA-derived)", (200, 200, 200))
    return img

def sc_lander(t, t0, t1):
    u = ease_io(seg(t, t0, t1))
    h = M.terrain()[0]
    x, y = 1300 + 30 * u, 1500
    ground = ndimage.map_coordinates(h, [[y], [x]], order=1, mode="wrap")[0]
    arr = M.terrain_shot(x, y, ground + 7, math.pi / 2 + 0.2 - 0.25 * u, horizon=0.36, fov=58, sun_el=12.0)
    img = M.finish(arr, 0.3, exp=1.15); d = ImageDraw.Draw(img, "RGBA")
    draw_mesh(d, lander_faces(), 560, 1200, 120, 0.5 + 0.6 * u, 0.12, light=(-0.9, 0.25, 0.35))
    q = seg(t, ws(12, 14) - 0.2, ws(12, 14) + 0.2)
    if q > 0: label(d, 540, 470, "CHANG'E-6 (China) · far-side samples returned June 2024", None, int(255 * q), (255, 210, 140), size=28)
    M.tag(d, "RECONSTRUCTION  ·  not mission imagery", (255, 200, 120))
    return img

def crystals_plate():
    """Micrometre-scale view: a troilite (FeS) grain with Fe2O3 crystals overgrowing parts of its rim (CGI, after Liu et al. 2025)."""
    def make():
        rng = np.random.default_rng(66)
        Wb, Hb = 2160, 3840
        mb = macro()[0]
        bg = to_img(mb * 0.55).resize((Wb, Hb), Image.BICUBIC).filter(ImageFilter.GaussianBlur(10))
        img = bg.copy(); d = ImageDraw.Draw(img)
        cx, cy, R = Wb / 2, Hb / 2, 720
        n = 17; th = np.sort(rng.uniform(0, 2 * np.pi, n)); rad = R * rng.uniform(0.78, 1.0, n)
        pts = [(cx + rr * math.cos(a) * 1.08, cy + rr * math.sin(a) * 0.82) for rr, a in zip(rad, th)]
        sh = Image.new("L", (Wb, Hb), 0); ImageDraw.Draw(sh).polygon([(x + 60, y + 80) for x, y in pts], fill=170)
        img = Image.composite(Image.new("RGB", (Wb, Hb), (8, 8, 8)), img, sh.filter(ImageFilter.GaussianBlur(40))); d = ImageDraw.Draw(img)
        mask = Image.new("L", (Wb, Hb), 0); ImageDraw.Draw(mask).polygon(pts, fill=255)
        m = np.asarray(mask, np.float32) / 255
        dist = ndimage.distance_transform_edt(m > 0.5).astype(np.float32)
        hgt = np.sqrt(dist) * 6 + ndimage.gaussian_filter(rng.normal(0, 1, (Hb, Wb)).astype(np.float32), 6) * 10 \
              + ndimage.gaussian_filter(rng.normal(0, 1, (Hb, Wb)).astype(np.float32), (2, 22)) * 4
        gy, gx = np.gradient(hgt)
        nz = 1 / np.sqrt(gx ** 2 + gy ** 2 + 1)
        Lx, Ly, Lz = -0.55, -0.55, 0.63
        ndl = np.clip((-gx * Lx - gy * Ly + Lz) * nz, 0, 1)
        spec = np.clip((-gx * -0.3 - gy * -0.3 + 0.9) * nz, 0, 1) ** 40
        metal = np.array([182, 150, 96], np.float32)
        shade = (0.18 + 0.95 * ndl)[..., None] * metal + spec[..., None] * np.array([255, 235, 190], np.float32) * 0.8
        a = np.asarray(img, np.float32)
        a = a * (1 - m[..., None]) + shade * m[..., None]
        img = to_img(a); d = ImageDraw.Draw(img)
        hexes = []
        for cl in range(7):                                                      # clusters along parts of the rim and on the face
            a0 = rng.uniform(0, 2 * np.pi); spread = rng.uniform(0.25, 0.6)
            for _ in range(int(rng.uniform(40, 90))):
                ang = a0 + rng.normal(0, spread); rr = R * rng.uniform(0.62, 1.0)
                hexes.append((cx + rr * math.cos(ang) * 1.08, cy + rr * math.sin(ang) * 0.82, rng.uniform(8, 30), rng.uniform(0, 1), rng.random()))
        for x, y, sz, ph, kind in sorted(hexes, key=lambda v: v[1]):
            if kind < 0.7:                                                       # hematite plates: dark steel-grey with red-brown tint
                col = [(92, 48, 44), (112, 52, 42), (70, 58, 58)][int(ph * 3) % 3]
                p6 = [(x + sz * math.cos(k * math.pi / 3 + ph), y + sz * 0.55 * math.sin(k * math.pi / 3 + ph)) for k in range(6)]
                d.polygon([(px, py + sz * 0.35) for px, py in p6], fill=tuple(int(c * 0.5) for c in col))
                d.polygon(p6, fill=col); d.line(p6 + [p6[0]], fill=(185, 130, 115), width=1)
            else:                                                                # maghemite: small blocky grains
                s2 = sz * 0.5
                d.polygon([(x - s2, y), (x, y - s2 * 0.6), (x + s2, y), (x, y + s2 * 0.6)], fill=(96, 70, 54))
        a = np.asarray(img, np.float32)
        a += ndimage.gaussian_filter(rng.normal(0, 1, (Hb, Wb)).astype(np.float32), 1.2)[..., None] * 6
        return np.asarray(to_img(a).resize((1620, 2880), Image.LANCZOS), np.float32)
    return M.cache("crystals", make)

def sc_crystals(t, t0, t1):
    u = ease_io(seg(t, t0, t1))
    P = crystals_plate()
    z = lerp(1.0, 1.6, u); cw = W / z * 1620 / 1620 * 1.5; ch = cw * H / W
    cx, cy = lerp(810, 1080, u), lerp(1440, 1200, u)
    img = to_img(P).transform((W, H), Image.EXTENT, (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2), Image.BILINEAR)
    img = to_img(M.tone(np.asarray(img, np.float32) * 1.15)); d = ImageDraw.Draw(img, "RGBA")
    headline(d, "2025: IRON OXIDES IN RETURNED SAMPLES", seg(t, ws(12, 1) - 0.2, ws(12, 1) + 0.25), 300, YELLOW, 44)
    q = seg(t, ws(12, 5), ws(12, 5) + 0.4)
    if q > 0:
        label(d, 540, 410, "IRON-OXIDE CRYSTALS", "hematite + maghemite on a troilite grain · micrometre scale", int(255 * q), (255, 150, 120), size=44)
    d.line((120, 1300, 320, 1300), fill=(255, 255, 255, 220), width=5); d.text((220, 1270), "~μm scale", font=font(F_MONO, 22), fill=WHITE, anchor="mm")
    M.tag(d, "CGI RECONSTRUCTION  ·  not the actual microscope image", (255, 150, 120))
    return img

def sc_farside_site(t, t0, t1):
    u = ease_out(seg(t, t0, t1))
    lat_s, lon_s = -41.6, -154.0                                                 # Chang'e-6 site, Apollo basin within South Pole–Aitken
    arr = M.moon(M.stars().copy(), 540, 880, lerp(420, 560, u), light=(0.3, 0.25, 0.92), lat0=-30, lon_c=-160, hem=0.0)
    img = M.finish(arr, 0.35); d = ImageDraw.Draw(img, "RGBA")
    R = lerp(420, 560, u); c0, s0 = math.cos(math.radians(-30)), math.sin(math.radians(-30))
    la, lo = math.radians(lat_s), math.radians(lon_s - (-160))
    X, Y, Z = math.cos(la) * math.sin(lo), math.sin(la), math.cos(la) * math.cos(lo)
    ny = Y * c0 - Z * s0
    px, py = 540 + X * R, 880 - ny * R
    k = seg(t, t0 + 0.2, t0 + 0.6)
    d.ellipse((px - 22, py - 22, px + 22, py + 22), outline=(255, 212, 0, int(255 * k)), width=4)
    d.ellipse((px - 5, py - 5, px + 5, py + 5), fill=(255, 212, 0, int(255 * k)))
    label(d, 540, 300, "FAR SIDE", "Chang'e-6 site · South Pole–Aitken basin", int(255 * k), (255, 212, 0), size=44)
    M.tag(d, "CGI  ·  real lunar albedo map · site position approximate", (200, 200, 200))
    return img

# ====================================================================== SCENE 08 — impacts (61.4 – 68.1 s)
def sc_impact(t, t0, t1):
    ti = ws(14, 5)                                                               # strike lands on "violent"
    h = M.terrain()[0]
    x, y = 300, 1700
    ground = ndimage.map_coordinates(h, [[y], [x]], order=1, mode="wrap")[0]
    u = seg(t, t0, t1)
    arr = M.terrain_shot(x, y, ground + 22 + 4 * u, math.pi / 2 - 0.05, horizon=0.34, fov=56, sun_el=14.0)
    ix, iy = 560, 1230
    if t < ti:
        k = seg(t, ti - 0.35, ti)
        if k > 0:
            sx, sy = lerp(ix + 520, ix, k), lerp(-100, iy, k)
            yy, xx = np.ogrid[0:H, 0:W]
            dist = np.abs((xx - sx) * 0.9 - (yy - sy) * 0.42) / 1.0
            m = (np.hypot(xx - sx, yy - sy) < 300) & (xx >= sx - 3)
            arr = arr + (np.exp(-dist / 3) * m * 600)[..., None] * np.array([1, 0.9, 0.7], np.float32)
    else:
        a = t - ti
        fl = math.exp(-a / 0.12)
        arr = sun_glare(arr, ix, iy, 40 + 120 * min(1, a / 0.2), 1.6 * fl + 0.0)
        yy, xx = np.ogrid[0:H, 0:W]
        hot = np.exp(-((xx - ix) ** 2 / 9000 + (yy - iy) ** 2 / 1800)) * math.exp(-a / 1.8) * 300
        arr = arr + hot[..., None] * np.array([1.0, 0.45, 0.12], np.float32)
        rng = np.random.default_rng(4); n = 500
        ang = rng.uniform(-math.pi * 0.95, -math.pi * 0.05, n); v = rng.uniform(250, 900, n)
        px = ix + np.cos(ang) * v * a; py = iy + np.sin(ang) * v * a * 0.6 + 300 * a * a
        lay = Image.new("L", (W, H), 0); dl = ImageDraw.Draw(lay)
        for X, Y, i in zip(px, py, range(n)):
            if 0 <= X < W and 0 <= Y < iy + 30:
                b = int(255 * math.exp(-a / (0.6 + 0.8 * (i % 3))))
                dl.ellipse((X - 2, Y - 2, X + 2, Y + 2), fill=b)
        arr = arr + np.asarray(lay.filter(ImageFilter.GaussianBlur(1.2)), np.float32)[..., None] * np.array([1.0, 0.75, 0.5], np.float32) * 1.4
    img = M.finish(arr, 0.5, exp=1.15); d = ImageDraw.Draw(img, "RGBA")
    headline(d, "IMPACTS MAY ALSO PLAY A ROLE", seg(t, ws(14, 6), ws(14, 6) + 0.3), 340, YELLOW, 58)
    M.tag(d, "CGI  ·  illustrative impact, not to scale", (255, 180, 120))
    return img

def sc_hot_grains(t, t0, t1, labels=True):
    """Inside the heated zone: grains glow and cool; iron oxides form locally (proposed, ~700–1000 °C)."""
    u = seg(t, t0, t1)
    heat = math.exp(-u * 2.2)
    arr = M.macro_frame(macro(), lerp(0, 1.15, ease(seg(t, t0 + 0.6, t1))), zoom=lerp(1.5, 2.0, u), cx=0.5, cy=0.5)
    lum = arr.mean(-1, keepdims=True)
    arr = arr * (1 - 0.6 * heat) + lum * np.array([2.4, 1.0, 0.35], np.float32) * heat * 1.4
    img = M.finish(arr, 0.6); d = ImageDraw.Draw(img, "RGBA")
    if not labels: return img
    label(d, 540, 330, "~700–1,000 °C, MOMENTARILY", "proposed: impact-released oxygen forms Fe₂O₃ locally", int(255 * seg(t, t0 + 0.2, t0 + 0.5)), (255, 170, 110), size=40)
    M.tag(d, "CGI CONCEPT  ·  after Liu et al. 2025", (255, 150, 120))
    return img

# ====================================================================== SCENE 09 — more than one process (68.1 – 78.3 s)
def sc_split(t, t0, t1):
    u = seg(t, t0, t1)
    left = np.asarray(sc_polar_rain(t, 0.0), np.float32)
    right = np.asarray(sc_hot_grains(t0 + 1.6 + (t - t0) * 0.2, t0, t0 + 6, False), np.float32)
    k = ease_out(seg(t, ws(15, 10) - 0.15, ws(15, 10) + 0.35))
    xm = int(lerp(W, 540, k))
    out = left.copy(); out[:, xm:] = right[:, xm:]
    img = to_img(out); d = ImageDraw.Draw(img, "RGBA")
    d.line((xm, 0, xm, H), fill=(255, 255, 255, 200), width=4)
    label(d, 270, 520, "EARTH'S OXYGEN?", "polar terrain", 255, O_GREEN, size=36)
    if k > 0.8: label(d, 810, 520, "IMPACTS?", "heated soil", 255, (255, 170, 110), size=36)
    return img

def sc_polar_rain(t, extra=0.0):
    h = M.terrain()[0]
    x, y = 900, 600
    ground = ndimage.map_coordinates(h, [[y], [x]], order=1, mode="wrap")[0]
    sky = M.stars().copy()
    arr = M.terrain_shot(x, y, ground + 30, math.pi / 2 + 0.6, horizon=0.42, fov=60, sun_el=9.0, sky=sky)
    P = [((540 + 500 * s, -60), (540 + 420 * s, 400), (540 + 300 * s, 800), (540 + 340 * s, 1500)) for s in np.linspace(-1, 1, 9)]
    arr = M.particles(arr, P, t, n=260, speed=0.4, size=3.0, amt=0.7, spread=20, seed=21)
    img = M.finish(arr, 0.4, exp=1.15)
    return img

def sc_panorama(t, t0, t1):
    """The paths merge: a wide polar panorama under a black sky, Earth low over the horizon (telephoto)."""
    u = ease_io(seg(t, t0, t1))
    sky = M.stars().copy()
    eR = W / 2 * math.tan(math.radians(0.95)) / math.tan(math.radians(9 / 2))
    sky = M.earth_disc(sky, lerp(470, 600, u), 560, eR, lon=20, lat0=5, sun=SUN)
    sky = M.limb_glow(sky, lerp(470, 600, u), 560, eR, SUN)
    h = M.terrain()[0]
    x, y = 200 + 60 * u, 400
    ground = ndimage.map_coordinates(h, [[y], [x]], order=1, mode="wrap")[0]
    arr = M.terrain_shot(x, y, ground + 45, 0.15 + 0.02 * u, horizon=0.42, fov=9, sun_el=10.0, sky=sky)
    img = M.finish(arr, 0.4, exp=1.15); d = ImageDraw.Draw(img, "RGBA")
    headline(d, "MORE THAN ONE POSSIBLE PROCESS", seg(t, t0 + 0.2, t0 + 0.6), 300, YELLOW, 56)
    M.tag(d, "CGI  ·  telephoto view, Earth shown at its true apparent size for this lens", (170, 210, 255))
    return img

# ====================================================================== SCENE 10 — finale (78.3 – end)
def sc_grain(t, t0, t1):
    u = ease_io(seg(t, t0, t1))
    arr = M.macro_frame(macro(), 1.2, zoom=lerp(2.6, 1.0, u), cx=0.5, cy=0.5)
    img = zoom_blur(M.finish(arr, 0.35), 0.15 * seg(u, 0.5, 1.0))
    return img

def sc_rise(t, t0, t1):
    """Pull back up off the surface: Earth hangs in the black sky (telephoto, true apparent size for the lens)."""
    u = ease_io(seg(t, t0, t1))
    fov = lerp(60, 14, u)
    eR = W / 2 * math.tan(math.radians(0.95)) / math.tan(math.radians(fov / 2))
    sky = M.stars().copy()
    sky = M.earth_disc(sky, 540, lerp(700, 560, u), max(8, eR), lon=20, lat0=5, sun=SUN)
    sky = M.limb_glow(sky, 540, lerp(700, 560, u), max(8, eR), SUN)
    h = M.terrain()[0]
    x, y = 1000, 1000
    ground = ndimage.map_coordinates(h, [[y], [x]], order=1, mode="wrap")[0]
    arr = M.terrain_shot(x - 300 * u, y, ground + lerp(10, 90, u), -math.pi / 2 - 0.1, horizon=lerp(0.45, 0.44, u), fov=fov, sun_el=12.0, sky=sky)
    img = M.finish(arr, 0.4, exp=1.15); d = ImageDraw.Draw(img, "RGBA")
    M.tag(d, "CGI  ·  Earth at its true apparent size for this lens", (170, 210, 255))
    return img

TS_CUT = None
def sc_truescale(t, t0):
    """Wide shot of the Earth–Moon system: sizes to scale (Moon = 0.27 Earth), distance compressed. O+ tail streams away from the Sun past the Moon."""
    u = ease_out(seg(t, t0, DUR))
    s = lerp(1.18, 1.0, u)
    ex, ey = 660 + 30 * (1 - u), 1230
    eR = 150 * s; mR = eR * 0.273
    mx, my = ex + (300 - ex) * s, ey + (560 - ey) * s
    arr = M.stars(seed=21, n=3600).copy()
    arr = sun_glare(arr, -350, -420, 260, 0.6)
    yy, xx = np.ogrid[0:H, 0:W]
    dx, dy = xx - ex, yy - ey
    along = (dx * 0.55 + dy * 0.83); perp = np.abs(-dx * 0.83 + dy * 0.55)
    tail = np.exp(-perp / (40 + along.clip(0) * 0.25)) * np.clip(along / 120, 0, 1) * np.exp(-along.clip(0) / 1600) * 55
    arr = arr + tail[..., None] * np.array(O_GREEN, np.float32) / 255
    arr = M.earth_disc(arr, ex, ey, eR, lon=20 + 2 * (t - t0), lat0=5, sun=SUN)
    arr = M.limb_glow(arr, ex, ey, eR, SUN)
    arr = M.moon(arr, mx, my, mR, light=SUN, lat0=8, hem=0.9, earthshine=0.6)
    P = [((ex + eR * math.cos(a), ey - eR * math.sin(a)), (ex - 120, ey - 420), (mx + 160, my + 260), (mx + mR * 0.3, my + mR * 0.9)) for a in np.linspace(1.3, 2.4, 5)]
    arr = M.particles(arr, P, t, n=120, speed=0.3, size=2.4, amt=0.45, spread=8)
    img = M.finish(arr, 0.5); d = ImageDraw.Draw(img, "RGBA")
    rx, ry = math.hypot(mx - ex, my - ey), math.hypot(mx - ex, my - ey) * 0.34
    d.ellipse((ex - rx, ey - ry, ex + rx, ey + ry), outline=(200, 200, 225, 40), width=2)
    k = seg(t, NARR_END + 0.1, NARR_END + 0.6)
    if k > 0:
        sc = max(0.85, ease_out(k))
        d.text((540, 300), "THE MOON STILL", font=font(F_CAP, 104 * sc), fill=(255, 255, 255, int(255 * k)), anchor="mm", stroke_width=10, stroke_fill=BLACK)
        d.text((540, 412), "HAS SECRETS", font=font(F_CAP, 104 * sc), fill=(255, 212, 0, int(255 * k)), anchor="mm", stroke_width=10, stroke_fill=BLACK)
    M.tag(d, "CGI  ·  sizes to scale, distance compressed · glow = O⁺ visualization", O_GREEN)
    return img

def sc_final(t, t0):
    """Out into space: the Moon above Earth again, the faint O⁺ stream between them — the opening image, now understood."""
    tc = ls(20) - 0.15
    if t >= tc:
        img = sc_truescale(t, tc)
        if t < tc + 0.5:
            prev = sc_final_close(t, t0, tc)
            k = ease(seg(t, tc, tc + 0.5))
            img = Image.blend(zoom_blur(prev, 0.25 * k), img, k)
        return img
    return sc_final_close(t, t0, tc)

def sc_final_close(t, t0, tc):
    u = ease_io(seg(t, t0, tc))
    eR = lerp(1400, 1160, u); mR = lerp(330, 285, u)
    arr = M.stars().copy()
    arr = M.earth_disc(arr, 540, lerp(2700, EC[1], u), eR, lon=20 + 2 * (t - t0), lat0=5, sun=SUN)
    arr = M.limb_glow(arr, 540, lerp(2700, EC[1], u), eR, SUN)
    mc = (540, lerp(900, MC[1], u))
    arr = M.moon(arr, mc[0], mc[1], mR, light=SUN, lat0=8, hem=0.9, earthshine=0.6)
    arr = M.particles(arr, o_paths((540, lerp(2700, EC[1], u)), eR, mc, mR), t, n=200, speed=0.42, size=3.0, amt=0.55, spread=9)
    img = M.finish(arr, 0.45); d = ImageDraw.Draw(img, "RGBA")
    M.tag(d, "SCIENTIFIC VISUALIZATION  ·  oxygen ions shown glowing", O_GREEN)
    return img

# ====================================================================== timeline
def scenes():
    c = [HOOK_END, ws(3, 13) - 0.1, ls(4) - 0.1, ws(4, 8) - 0.15, ws(4, 13) - 0.1, ls(5) - 0.1, ls(7) - 0.1, ls(8) - 0.1, ws(8, 7) - 0.1, ls(9) - 0.1,
         ls(10) - 0.1, ls(11) - 0.1, ls(12) - 0.1, ws(12, 11) - 0.1, ls(13) - 0.1, ls(14) - 0.1, ws(14, 9) - 0.1, ls(15) - 0.1,
         ls(16) - 0.1, ls(17) - 0.1, ls(18) - 0.1, ws(19, 6) - 0.1]
    fns = [sc_surface, sc_horizon, sc_orbiter, sc_scan, sc_poles, sc_nearfar, sc_towards_earth, sc_escape, sc_magneto, sc_moon_tail, sc_reaction,
           sc_farside_swing, sc_crystals, sc_lander, sc_farside_site, sc_impact, sc_hot_grains, sc_split, sc_panorama, sc_grain, sc_rise]
    out = [(0.0, HOOK_END, sc_hook)]
    for i, fn in enumerate(fns):
        a, b = c[i], c[i + 1]
        out.append((a, b, (lambda f, a, b: (lambda t: f(t, a, b)))(fn, a, b)))
    out.append((c[-1], DUR + 1, lambda t: sc_final(t, c[-1])))
    return out
SCENES = scenes()

# ====================================================================== phrase captions
PHRASE_TEXT = [
 "THE MOON IS RUSTING.",
 "AND EARTH MAY BE WHY.",
 "THAT SOUNDS IMPOSSIBLE.",
 "THE MOON HAS ALMOST NO ATMOSPHERE, | HARDLY ANY ACCESSIBLE WATER, | AND A SURFACE CONSTANTLY EXPOSED TO SPACE.",
 "BUT SCIENTISTS ANALYZING DATA | FROM INDIA'S CHANDRAYAAN-1 SPACECRAFT | FOUND SPECTRAL EVIDENCE OF HEMATITE, | A MINERAL ASSOCIATED WITH RUST, | NEAR THE MOON'S POLES.",
 "AND THE STRANGE PART?",
 "THOSE SIGNATURES APPEARED MORE FREQUENTLY | ON THE SIDE OF THE MOON FACING EARTH.",
 "ONE EXPLANATION POINTS | DIRECTLY BACK AT OUR PLANET.",
 "OXYGEN PARTICLES CAN ESCAPE | EARTH'S UPPER ATMOSPHERE, | AND TRAVEL INTO THE LONG MAGNETIC TAIL | STRETCHING AWAY FROM THE SUN.",
 "AS THE MOON PASSES THROUGH THAT REGION, | SOME OF EARTH'S OXYGEN | MAY REACH ITS SURFACE.",
 "UNDER THE RIGHT CONDITIONS, | THAT OXYGEN COULD HELP TRANSFORM | IRON-BEARING MINERALS INTO HEMATITE.",
 "BUT THE MYSTERY DOESN'T END THERE.",
 "IN 2025, RESEARCHERS REPORTED | MICROSCOPIC IRON-OXIDE CRYSTALS | IN ACTUAL LUNAR SOIL | RETURNED BY CHINA'S CHANG'E-6 MISSION.",
 "THOSE SAMPLES CAME | FROM THE FAR SIDE OF THE MOON.",
 "AND THE RESEARCHERS SUGGESTED | THAT VIOLENT IMPACTS | COULD CREATE LOCAL CONDITIONS | FOR IRON OXIDES TO FORM.",
 "SO EARTH'S OXYGEN | MIGHT EXPLAIN PART OF THE STORY, | WHILE IMPACTS AND OTHER PROCESSES | COULD EXPLAIN MORE.",
 "SCIENTISTS ARE STILL WORKING OUT | EXACTLY HOW LUNAR RUST FORMS.",
 "THINK ABOUT THAT.",
 "THE MOON ISN'T JUST | A SILENT ROCK IN OUR SKY.",
 "ITS SURFACE MAY PRESERVE TRACES | OF EARTH'S ESCAPING ATMOSPHERE, | AND CLUES FROM ANCIENT COSMIC COLLISIONS.",
 "EVEN OUR NEAREST NEIGHBOR | IS HIDING A CHEMICAL MYSTERY.",
]
KEY = {"RUSTING.", "HEMATITE,", "HEMATITE.", "RUST,", "POLES.", "EARTH.", "EARTH", "OXYGEN", "MAGNETIC", "TAIL", "IRON-OXIDE", "CHANG'E-6",
       "CHANDRAYAAN-1", "FAR", "IMPACTS", "IRON", "OXIDES", "RUST", "MYSTERY.", "2025,", "ATMOSPHERE,", "NO", "COLLISIONS.", "SIDE"}
def build_phrases():
    res = []
    for li, l in enumerate(TIM):
        words = [(w.upper(), s, e) for w, s, e in l["words"]]
        parts = [p.split() for p in PHRASE_TEXT[li].split("|")]
        assert " ".join(" ".join(p) for p in parts) == " ".join(w for w, _, _ in words), (li, PHRASE_TEXT[li], [w for w, _, _ in words])
        i = 0
        for p in parts:
            res.append(words[i:i + len(p)]); i += len(p)
    out = []
    for i, ph in enumerate(res):
        a = ph[0][1]; nxt = res[i + 1][0][1] if i + 1 < len(res) else 1e9
        b = nxt if nxt - ph[-1][2] < 0.7 else ph[-1][2] + 0.35
        out.append((a, b, ph))
    return out
PHRASES = build_phrases()
CAP_Y = {}                                                                        # per-scene caption height overrides

def draw_caption(img, t):
    if t < ls(1) - 0.02: return                                                   # the hook title carries line 0
    y = 1180 if t < HOOK_END else 1420
    for a, b, ph in PHRASES:
        if not (a <= t < b) or a < ls(1) - 0.05: continue
        d = ImageDraw.Draw(img); f = font(F_CAP, 72); gap = 18; maxw = 900
        items = [(w, f.getlength(w), bool(re.search(r"\d", w)) or w in KEY) for w, s, e in ph]
        rows, cur, cw = [], [], 0
        for it in items:
            if cur and cw + gap + it[1] > maxw: rows.append(cur); cur, cw = [], 0
            cur.append(it); cw += (gap if len(cur) > 1 else 0) + it[1]
        rows.append(cur)
        k = ease_out(seg(t, a, a + 0.12)); al = int(255 * k); dy = 12 * (1 - k)
        lh = 84; y0 = y - (len(rows) - 1) * lh / 2 + dy
        lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
        for ri, row in enumerate(rows):
            tw = sum(x[1] for x in row) + gap * (len(row) - 1); x = 540 - tw / 2
            for w, fw, em in row:
                ld.text((x, y0 + ri * lh), w, font=f, fill=(YELLOW if em else WHITE) + (255,), anchor="lm", stroke_width=9, stroke_fill=BLACK)
                x += fw + gap
        if al < 255: lay.putalpha(Image.eval(lay.getchannel("A"), lambda v: v * al // 255))
        img.paste(lay, (0, 0), lay)
        return

# ====================================================================== frame assembly
GR = np.random.default_rng(3)
GRAIN = [GR.normal(0, 2.6, (H // 2, W // 2, 1)).astype(np.float32).repeat(2, 0).repeat(2, 1) for _ in range(4)]
yy_, xx_ = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1 - 0.28 * (((xx_ - W / 2) / (W / 2)) ** 2 + ((yy_ - H / 2) / (H / 2)) ** 2) ** 1.6).clip(0.55, 1)[..., None]
del yy_, xx_

def frame(fi):
    t = fi / FPS
    img = None
    for a, b, fn in SCENES:
        if a <= t < b: img = fn(t); break
    for i, (a, b, fn) in enumerate(SCENES[1:]):                                   # 6-frame dissolve on each cut
        if 0 <= t - a < 0.2 and i + 1 < len(SCENES):
            prev = SCENES[i][2](t)
            img = Image.blend(prev.convert("RGB"), img.convert("RGB"), ease(seg(t, a, a + 0.2)))
    arr = np.asarray(img.convert("RGB"), np.float32) * VIG + GRAIN[fi % 4]
    img = to_img(arr)
    draw_caption(img, t)
    return img.tobytes()

def warm():
    macro(); M.terrain(); M.shaded(8.0); M.shaded(14.0); M.shaded(25.0); M.hem_mask(); M.moonr.tex(); m3_colour()

def encode(frames, out, crf=17):
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    warm()
    with Pool(4) as pool:
        for i, b in enumerate(pool.imap(frame, frames, chunksize=2)):
            p.stdin.write(b)
            if i % 150 == 0: print("frame", frames[0] + i, flush=True)
    p.stdin.close(); p.wait()

# ====================================================================== sound
def rev_whoosh(d=0.6):
    return whoosh(d)[::-1].copy()

def shimmer(d=2.0, f0=2400):
    n = int(d * SR); tt = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f0 * k * tt + k) * np.exp(-tt / (0.4 + 0.2 * k)) for k in (1, 1.5, 2.01, 2.97))
    return bp(arng.normal(0, 1, n), 3000, 9000) * 0.25 * np.exp(-tt / 0.8) + s * 0.08

def render_audio(out):
    n = int(DUR * SR); tt = np.arange(n) / SR
    chords = [(0, [49.0, 73.42, 116.54, 146.83]), (ls(4), [55.0, 82.41, 130.81, 164.81]), (ls(8), [43.65, 65.41, 103.83, 130.81]),
              (ls(12), [46.25, 69.3, 110.0, 138.59]), (ls(15), [49.0, 73.42, 116.54, 146.83]), (ls(17), [41.2, 61.74, 98.0, 123.47, 185.0]),
              (ls(19), [43.65, 65.41, 110.0, 130.81, 196.0])]
    pad = np.zeros(n)
    for ci, (t0, notes) in enumerate(chords):
        t1 = chords[ci + 1][0] if ci + 1 < len(chords) else DUR
        i0, i1 = int(t0 * SR), min(n, int(t1 * SR) + int(1.0 * SR)); m = i1 - i0; sg = np.zeros(m)
        for f in notes:
            for det in (-0.1, 0.0, 0.09): sg += osc(f * 2 ** (det / 12), m)
        e = np.minimum(1, np.arange(m) / (1.0 * SR)) * np.minimum(1, (m - np.arange(m)) / (1.0 * SR))
        pad[i0:i1] += sg * e / 12
    pulse = np.zeros(n); t = ls(8)
    while t < ls(11):
        place(pulse, boom(0.4, 70, 42, 0.1), t, 0.28); t += 60 / 84
    t = ls(17)
    while t < DUR - 2:
        place(pulse, boom(0.5, 66, 40, 0.12), t, 0.35); t += 60 / 76
    swell = np.interp(tt, [0, 2.4, 3.0, ls(8), ls(11), ls(12), ls(17), ls(19), NARR_END, DUR], [0.9, 0.9, 0.55, 0.75, 0.85, 0.7, 0.85, 1.15, 1.2, 0.6])
    mus = (lp(pad, 1100) * 0.7 + lp(pad, 380) * 0.6 + osc(36.7, n, "sin") * 0.18 + pulse) * swell
    fx = np.zeros(n)
    place(fx, reverb(boom(2.6, 120, 26, 0.85), 3.2, 0.42), 0.0, 1.6)                                    # frame-0 impact
    place(fx, crack(0.5), 0.0, 0.5)
    place(fx, rev_whoosh(0.55), 0.10, 0.7)                                                              # into the pullback at 0.62 s
    place(fx, whoosh(0.9), 0.55, 0.45)
    place(fx, shimmer(2.2, 2600), 1.05, 0.35)                                                           # ion stream appears
    place(fx, shimmer(1.2, 3400), 0.15, 0.25)                                                           # grains change
    for a, b, fn in SCENES[1:]:
        if a < DUR - 1: place(fx, whoosh(0.6), a - 0.2, 0.18)
    m = int(2.5 * SR); place(fx, lp(arng.normal(0, 1, m), 120) * np.minimum(1, np.arange(m) / SR / 0.8) * np.exp(-np.arange(m) / SR / 2.5), HOOK_END, 0.4)
    place(fx, tick(1800), ws(4, 12), 0.25); place(fx, shimmer(1.4, 2000), ws(4, 12) + 0.05, 0.3)    # 'hematite' (soft, under speech)
    vo = np.zeros(n)
    for l in TIM:
        s, _ = sf.read(l["file"]); place(vo, s, l["start"])
    vo = lp(hp(vo, 80), 13500); vo = vo / (np.abs(vo).max() + 1e-9) * 0.9
    env = lp(np.abs(vo), 7); env /= env.max() + 1e-9
    duck = 1 - 0.65 * np.clip(env * 3, 0, 1)
    mix = vo + mus * 0.12 * duck + fx * 0.3 * (0.4 + 0.6 * duck)
    sf.write(out, np.stack([np.tanh(mix * 1.05) * 0.95] * 2, 1).astype(np.float32), SR, subtype="FLOAT")

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "stills":
        warm(); os.makedirs("st", exist_ok=True)
        for x in sys.argv[2:]:
            t = float(x); Image.frombytes("RGB", (W, H), frame(int(round(t * FPS)))).resize((270, 480)).save(f"st/s_{int(t * 100):05d}.jpg", quality=86)
    elif cmd == "audio": render_audio(sys.argv[2])
    elif cmd == "preview":
        t0, t1, out = float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
        encode(list(range(int(t0 * FPS), int(t1 * FPS))), "_v.mp4")
        render_audio("_a.wav")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", "_v.mp4", "-ss", str(t0), "-t", str(t1 - t0), "-i", "_a.wav", "-map", "0:v", "-map", "1:a",
                        "-af", "loudnorm=I=-14:TP=-1.5", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", out], check=True)
    elif cmd == "full":
        encode(list(range(NF)), "video_full.mp4", 16)
