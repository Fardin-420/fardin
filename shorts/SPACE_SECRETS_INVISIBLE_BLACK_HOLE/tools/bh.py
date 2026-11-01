#!/usr/bin/env python3
# SPACE SECRETS — "The Invisible Black Hole That Could Pass Through Space Unseen" — production renderer.
# Usage: python3 bh.py stills t... | hooks | preview t0 t1 out.mp4 | final | audio out.wav
import json, math, os, re, subprocess, sys
from multiprocessing import Pool
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

import bhfx as B
from bhfx import W, H, FPS, seg, ease, ease_out, ease_in, ease_io, lerp, clamp
import earth, star
from sfx import SR, lp, hp, bp, place, osc, boom, crack, whoosh, tick, riser, reverb, arng
star.W, star.H = W, H
earth.TEX = "tex/"

TIM = json.load(open("timing.json"))
def ls(i): return TIM[i]["start"]
def le(i): return TIM[i]["start"] + TIM[i]["dur"]
def ws(i, k): return TIM[i]["words"][k][1]
NARR_END = le(len(TIM) - 1)
DUR = round(NARR_END + 6.0, 1)
NF = int(DUR * FPS)
HOOK = os.environ.get("HOOK", "B")

F_CAP = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
F_UI = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
F_MONO = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf"
_F = {}
def font(p, s):
    k = (p, int(s))
    if k not in _F: _F[k] = ImageFont.truetype(p, max(1, int(s)))
    return _F[k]
WHITE, YELLOW, BLACK, CYAN, ORANGE = (255, 255, 255), (255, 212, 0), (0, 0, 0), (130, 210, 255), (255, 160, 80)
SUN_DIR = (-0.7, 0.35, 0.62)

def to_img(a): return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
def tag(d, txt, col=(130, 210, 255)):
    f = font(F_MONO, 22)
    d.rounded_rectangle((60, 196, 60 + f.getlength(txt) + 28, 236), 10, fill=(0, 0, 0, 160))
    d.ellipse((72, 210, 84, 222), fill=col)
    d.text((94, 216), txt, font=f, fill=(232, 232, 232), anchor="lm")
def label(d, x, y, title, body=None, a=255, col=WHITE, anchor="mm", size=34):
    if a <= 0: return
    d.text((x, y), title, font=font(F_UI, size), fill=col + (a,), anchor=anchor, stroke_width=5, stroke_fill=BLACK)
    if body: d.text((x, y + size + 6), body, font=font(F_MONO, 22), fill=(228, 228, 232, a), anchor=anchor, stroke_width=4, stroke_fill=BLACK)
def headline(d, txt, k, y=300, col=WHITE, size=70):
    if k <= 0: return
    a = int(255 * k); dy = 14 * (1 - ease_out(k))
    d.text((540, y + dy), txt, font=font(F_CAP, size), fill=col + (a,), anchor="mm", stroke_width=9, stroke_fill=BLACK + (a,))
def zoom_blur(img, amount, cx=540, cy=960, n=7):
    if amount < 0.004: return img
    acc = np.zeros((H, W, 3), np.float32)
    for i in range(n):
        s = 1 + amount * i / (n - 1)
        acc += np.asarray(img.resize((W, H), Image.BICUBIC, box=(cx - cx / s, cy - cy / s, cx + (W - cx) / s, cy + (H - cy) / s)), np.float32)
    return to_img(acc / n)

def sun_glare(arr, x, y, r=34, amt=1.0, col=(1.0, 0.98, 0.93)):
    yy, xx = np.ogrid[0:H, 0:W]
    d = np.sqrt((xx - x) ** 2 + (yy - y) ** 2)
    core = np.clip(1 - d / r, 0, 1) ** 0.5 * 600 + np.exp(-d / (r * 2.2)) * 160 + np.exp(-d / (r * 9)) * 40
    return arr + (core * amt)[..., None] * np.array(col, np.float32)

def bh_lens(cx, cy, tE, shadow=0.42):
    return (cx, cy, tE, tE * shadow)

# ====================================================================== SCENE 1 — hook (three variants) + "found one"
HOOK_END = ls(1) - 0.1

def hook_A(t):
    """Frame 0: lens already distorting a dense field; it glides and its arcs swing; impact pulse on frame 0."""
    pulse = 1 + 0.18 * math.exp(-t / 0.18)
    cx, cy = lerp(470, 590, ease_io(seg(t, 0, HOOK_END))), lerp(1010, 930, ease_io(seg(t, 0, HOOK_END)))
    tE = lerp(185, 205, seg(t, 0, HOOK_END)) * pulse
    arr = B.lens_view(B.plate("bulge"), [bh_lens(cx, cy, tE)], off=(30 * t, -12 * t))
    return B.finish(arr, 0.4)

def hook_B(t):
    """Lens enters from the right edge at speed: arcs sweep across the field."""
    u = ease_out(seg(t, 0, 1.4))
    cx = lerp(1010, 560, u); cy = lerp(880, 960, u)
    arr = B.lens_view(B.plate("bulge"), [bh_lens(cx, cy, 200 * (1 + 0.15 * math.exp(-t / 0.2)))], off=(18 * t, 0))
    return B.finish(arr, 0.4)

def hook_C(t):
    """Extreme close-up on one lensed bright arc, then fast pull-back reveals the shadow."""
    z = lerp(3.2, 1.0, ease_out(seg(t, 0.15, 1.3)))
    arr = B.lens_view(B.plate("bulge"), [bh_lens(540 + (380 - 540) / z * 0 , 960, 200 * z)], off=(0, 0), zoom=z)
    img = B.finish(arr, 0.4)
    return zoom_blur(img, 0.25 * seg(t, 0.15, 0.6) * (1 - seg(t, 0.6, 1.3)))

def sc_hook(t):
    img = {"A": hook_A, "B": hook_B, "C": hook_C}[HOOK](t)
    d = ImageDraw.Draw(img, "RGBA")
    k = max(0.85, 1.15 - 0.3 * seg(t, 0, 0.12))
    d.text((540, 300), "AN INVISIBLE", font=font(F_CAP, 112 * k), fill=WHITE, anchor="mm", stroke_width=11, stroke_fill=BLACK)
    d.text((540, 420), "BLACK HOLE?!", font=font(F_CAP, 112 * k), fill=YELLOW, anchor="mm", stroke_width=11, stroke_fill=BLACK)
    tag(d, "VISUALIZATION  ·  lensing exaggerated for visibility")
    return img

def sc_found(t, t0, t1):
    """Pull back: the lens shrinks into a crowded star field."""
    u = ease_io(seg(t, t0, t1))
    z = lerp(1.0, 0.86, u)
    cx, cy = 590 + 0 * u, 930
    arr = B.lens_view(B.plate("bulge"), [bh_lens(lerp(cx, 560, u), lerp(cy, 900, u), lerp(205, 120, u) * z)], off=(30 * t0, -12 * t0), zoom=z)
    img = B.finish(arr, 0.4); d = ImageDraw.Draw(img, "RGBA")
    tag(d, "VISUALIZATION  ·  lensing exaggerated for visibility")
    return img

# ====================================================================== SCENE 2 — how black holes are usually found, then: alone
def accretion_disk(arr, cx, cy, R, tilt, t, k=1.0):
    yy, xx = np.ogrid[0:H, 0:W]
    dx = (xx - cx) / R; dy = (yy - cy) / (R * tilt)
    r = np.sqrt(dx * dx + dy * dy)
    ang = np.arctan2(dy, dx)
    ring = np.clip((r - 0.18) / 0.06, 0, 1) * np.clip((1.0 - r) / 0.25, 0, 1)
    temp = np.clip(1.15 - r, 0, 1)
    swirl = 0.75 + 0.25 * np.sin(ang * 3 + 9 * r - t * 3.5) * np.sin(ang * 5 - 5 * r + t * 2.1)
    dop = 1 + 0.45 * np.cos(ang - 0.3)                                            # one side brighter (Doppler beaming)
    I = ring * swirl * dop * (0.35 + 1.6 * temp ** 2) * 260 * k
    col = np.stack([np.full_like(temp, 1.0), 0.55 + 0.4 * temp, 0.25 + 0.65 * temp ** 1.5], -1)
    return arr + I[..., None] * col

def sc_binary(t, t0, t1):
    u = ease_io(seg(t, t0, t1))
    arr = B.lens_view(B.plate("field"), [], off=(-200 + 40 * u, 300))
    arr = arr * 0.6
    arr = star.draw_sun(arr, lerp(300, 280, u), 760, 230, t, bright=0.9, corona=0.9) * np.array([0.82, 0.9, 1.0], np.float32) + arr * 0.0
    P = []
    for k in range(7):
        a = k / 6
        P.append(((300 + 200, 760 + 60 * (a - 0.5)), (560, 820), (690, lerp(980, 1050, a)), (760 + 60 * math.cos(a * 6), 1060 + 18 * math.sin(a * 6))))
    arr = accretion_disk(arr, 760, 1060, 210, lerp(0.30, 0.38, u), t)
    arr = add_particles(arr, P, t, n=260, speed=0.5, col=(255, 200, 150), amt=0.6)
    img = B.finish(arr, 0.5); d = ImageDraw.Draw(img, "RGBA")
    q = seg(t, ws(2, 9) - 0.2, ws(2, 9) + 0.3)
    label(d, 540, 330, "HOW MOST ARE FOUND", "a companion star + glowing material", int(255 * q), ORANGE, size=40)
    tag(d, "ILLUSTRATION  ·  a typical black-hole binary, not OGLE-2011-BLG-0462", ORANGE)
    return img

def sc_alone(t, t0, t1):
    u = ease_io(seg(t, t0, t1))
    arr = B.lens_view(B.plate("field"), [bh_lens(lerp(400, 620, u), lerp(1060, 930, u), 190)], off=(-250 + 60 * u, 600 - 40 * u))
    img = B.finish(arr, 0.4); d = ImageDraw.Draw(img, "RGBA")
    q = seg(t, ws(3, 5) - 0.2, ws(3, 5) + 0.3)
    label(d, 540, 330, "NO COMPANION · NO GLOWING DISK", None, int(255 * q), CYAN, size=40)
    tag(d, "VISUALIZATION  ·  an isolated black hole, only its gravity shows")
    return img

# ====================================================================== SCENE 3 — the name, the galaxy, the mass
BH_POS = np.array([6.68, 0.05, -0.02], np.float32)                                # ~1.52 kpc from the Sun toward the bulge
SUN_POS = np.array([8.2, 0.0, 0.02], np.float32)

def sc_galaxy_fly(t, t0, t1):
    u = ease_io(seg(t, t0, t1))
    cam = np.array([lerp(17, 9.6, u), lerp(-11, -1.6, u), lerp(6.5, 0.9, u)], np.float32)
    tgt = BH_POS * u + np.array([0, 0, 0], np.float32) * (1 - u)
    arr = B.render_galaxy(cam, tgt, fov=lerp(58, 64, u), base=B.lens_view(B.plate("sparse"), [], zoom=1.0) * 0.25)
    img = B.finish(arr, 0.45); d = ImageDraw.Draw(img, "RGBA")
    q = seg(t, ws(4, 2) - 0.15, ws(4, 2) + 0.25)
    d.text((540, 330), "OGLE-2011-BLG-0462", font=font(F_CAP, 74), fill=(255, 212, 0, int(255 * q)), anchor="mm", stroke_width=9, stroke_fill=BLACK)
    if q > 0: label(d, 540, 420, "", "found toward the Milky Way's central bulge", int(255 * q), WHITE, size=10)
    tag(d, "CGI MODEL  ·  Milky Way, illustrative")
    return img

def sc_mass(t, t0, t1):
    arr = B.lens_view(B.plate("sparse"), [], off=(200, 100)) * 0.7
    k = ease_io(seg(t, ws(5, 4) - 0.2, ws(5, 5) + 0.6))                         # suns line up on "seven", then collapse
    col = ease_in(seg(t, ws(5, 9), ws(5, 9) + 0.9))
    for i in range(7):
        a = -math.pi / 2 + (i - 3) * 0.32
        x0, y0 = 540 + 330 * math.cos(a), 1180 + 330 * math.sin(a)
        x, y = lerp(x0, 540, col), lerp(y0, 900, col)
        if k > 0 and col < 0.98:
            arr = star.draw_sun(arr, x, y, 46 * k * (1 - col * 0.8), t, bright=0.9, corona=0.6)
    lenses = [bh_lens(540, 900, 150 * col)] if col > 0.05 else []
    if lenses:
        base = arr.copy()
        lensed = B.lens_view(B.plate("sparse"), lenses, off=(200, 100)) * 0.7
        m = np.clip(col * 1.3, 0, 1)
        arr = base * (1 - m) + lensed * m
    img = B.finish(arr, 0.45); d = ImageDraw.Draw(img, "RGBA")
    headline(d, "~7 SOLAR MASSES", seg(t, ws(5, 4) - 0.1, ws(5, 4) + 0.3), 330, YELLOW, 86)
    q = seg(t, ws(5, 12), ws(5, 12) + 0.3)
    label(d, 540, 1150, "NO LIGHT DETECTED", "event horizon ≈ 42 km across (for 7 M☉)", int(255 * q), CYAN, size=40)
    tag(d, "GRAPHIC  ·  mass 7.15 ± 0.83 M☉ (Sahu et al. 2025)")
    return img

# ====================================================================== SCENE 4 — observatory, Hubble, the target star
def mountain(arr, t):
    rng = np.random.default_rng(9)
    xs = np.arange(W)
    ridge = 1480 + 60 * np.sin(xs / 210 + 0.6) + 35 * np.sin(xs / 77 + 2.0) + ndimage.gaussian_filter1d(rng.normal(0, 18, W), 6)
    yy = np.arange(H)[:, None]
    m = (yy > ridge[None, :]).astype(np.float32)
    arr = arr * (1 - m[..., None]) + np.array([4, 4, 6], np.float32) * m[..., None]
    return arr, ridge

def sc_observatory(t, t0, t1):
    u = ease_io(seg(t, t0, t1))
    sky = B.render_galaxy(SUN_POS, np.array([0, 0, 0], np.float32), fov=lerp(78, 70, u), roll=lerp(0.85, 0.78, u),
                          base=B.lens_view(B.plate("sparse"), [], off=(0, -300)) * 0.35, gain=1.3)
    arr, ridge = mountain(sky, t)
    img = B.finish(arr, 0.5); d = ImageDraw.Draw(img, "RGBA")
    cx, base_y = 640, int(ridge[640]) + 6                                        # dome with an open slit
    d.rectangle((cx - 130, base_y - 90, cx + 130, base_y + 40), fill=(14, 14, 18))
    d.pieslice((cx - 130, base_y - 220, cx + 130, base_y + 40), 180, 360, fill=(22, 22, 28))
    d.polygon([(cx - 22, base_y - 218), (cx + 22, base_y - 218), (cx + 18, base_y - 92), (cx - 18, base_y - 92)], fill=(3, 3, 5))
    d.arc((cx - 130, base_y - 220, cx + 130, base_y + 40), 200, 260, fill=(70, 80, 110), width=3)
    label(d, 540, 1700, "", "ground-based survey telescopes monitor the bulge", 220, WHITE, size=10)
    tag(d, "CGI  ·  observatory under the Milky Way (illustration)", (200, 200, 220))
    return img

def cyl_faces(r, L, n=18, col=(200, 202, 208)):
    F = []
    for i in range(n):
        a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
        F.append(([(r * math.cos(a0), r * math.sin(a0), -L / 2), (r * math.cos(a1), r * math.sin(a1), -L / 2),
                   (r * math.cos(a1), r * math.sin(a1), L / 2), (r * math.cos(a0), r * math.sin(a0), L / 2)], col, "foil" if i % 2 else None))
    return F

def box(c, s):
    x, y, z = c; a, b, e = s[0] / 2, s[1] / 2, s[2] / 2
    v = np.array([[x - a, y - b, z - e], [x + a, y - b, z - e], [x + a, y + b, z - e], [x - a, y + b, z - e],
                  [x - a, y - b, z + e], [x + a, y - b, z + e], [x + a, y + b, z + e], [x - a, y + b, z + e]], np.float32)
    Fc = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (1, 2, 6, 5), (0, 3, 7, 4)]
    return [v[list(f)] for f in Fc]

def hubble_faces():
    F = cyl_faces(2.1, 13.2, 20, (205, 208, 214))
    F += [([(2.1 * math.cos(a), 2.1 * math.sin(a), 6.6) for a in np.linspace(0, 2 * math.pi, 20, endpoint=False)], (18, 18, 22), None)]
    F += cyl_faces(2.15, 1.4, 20, (150, 150, 155))
    for sgn in (-1, 1):
        for q in box((sgn * 4.2, 0, -1.0), (5.4, 0.08, 2.4)): F.append((q, (40, 52, 110), "cells"))
        for q in box((sgn * 2.4, 0, -1.0), (1.2, 0.12, 0.12)): F.append((q, (170, 170, 175), None))
    return F

def draw_mesh(d, faces, cx, cy, scale, yaw, pitch, light=SUN_DIR):
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
        sh = 0.2 + 0.95 * max(0.0, float(nrm @ L))
        out.append((float(p[:, 2].mean()), [(cx + v[0] * scale, cy - v[1] * scale) for v in p], tuple(int(clamp(c * sh, 0, 255)) for c in col), kind))
    out.sort(key=lambda o: o[0])
    for z, pts, col, kind in out:
        d.polygon(pts, fill=col)
        if kind == "cells":
            for k in range(1, 6):
                a = [lerp(pts[0][i], pts[1][i], k / 6) for i in range(2)]; b = [lerp(pts[3][i], pts[2][i], k / 6) for i in range(2)]
                d.line((a[0], a[1], b[0], b[1]), fill=(80, 100, 150), width=1)
        if kind == "foil": d.line(pts + [pts[0]], fill=(235, 238, 245), width=1)

def sc_hubble(t, t0, t1):
    u = ease_io(seg(t, t0, t1))
    arr = B.lens_view(B.plate("sparse"), [], off=(0, 0)) * 0.6
    arr = earth.render(W, H, 540, 2350, 1050, 10, -30 + 5 * u, -38, sun=SUN_DIR, stars=arr)
    img = B.finish(arr, 0.4); d = ImageDraw.Draw(img, "RGBA")
    draw_mesh(d, hubble_faces(), lerp(470, 600, u), lerp(720, 680, u), 30, 0.9 + 0.5 * u, 0.25 + 0.1 * u)
    label(d, 540, 1000, "HUBBLE SPACE TELESCOPE", "precise positions of faint stars", int(255 * seg(t, t0 + 0.3, t0 + 0.7)), CYAN, size=40)
    tag(d, "CGI RECONSTRUCTION  ·  not NASA imagery", (200, 200, 220))
    return img

TARGET = (110.0, -60.0)                                                          # target source star offset in the bulge plate (output px)
def sc_target(t, t0, t1):
    u = ease_io(seg(t, t0, t1))
    z = lerp(1.0, 2.0, u)
    arr = B.lens_view(B.plate("bulge"), [], off=(TARGET[0] * u, TARGET[1] * u), zoom=z)
    img = B.finish(arr, 0.35); d = ImageDraw.Draw(img, "RGBA")
    k = seg(t, t0 + 0.25, t0 + 0.75)
    r = lerp(140, 46, ease_out(k))
    if k > 0:
        d.ellipse((540 - r, 960 - r, 540 + r, 960 + r), outline=(255, 212, 0, int(255 * k)), width=4)
        for a in range(4):
            ang = a * math.pi / 2
            d.line((540 + (r + 8) * math.cos(ang), 960 + (r + 8) * math.sin(ang), 540 + (r + 40) * math.cos(ang), 960 + (r + 40) * math.sin(ang)), fill=(255, 212, 0, int(255 * k)), width=4)
        label(d, 540, 960 + r + 70, "THE BACKGROUND STAR", "~20,000+ light-years away, in the bulge", int(255 * k), YELLOW, size=34)
    tag(d, "SIMULATED FIELD  ·  crowded bulge star field", (200, 200, 220))
    return img

# ====================================================================== SCENE 5–7 — microlensing geometry, light curve, astrometric shift, Hubble epochs
def sc_geometry(t, t0, t1):
    """Not to scale: observer — lens — source alignment; the lens crosses the line of sight; rays bend."""
    u = seg(t, t0, t1)
    arr = B.lens_view(B.plate("sparse"), [], off=(-300, 400)) * 0.45
    ex, ey, sx, sy = 160, 1500, 920, 520
    lx = lerp(ex, sx, 0.45); ly = lerp(ey, sy, 0.45)
    perp = np.array([0.79, 0.61]); offset = lerp(-260, 260, ease_io(u))
    bx, by = lx + perp[0] * offset, ly + perp[1] * offset
    arr = B.lens_view(B.plate("sparse"), [bh_lens(bx, by, 60, 0.42)], off=(-300, 400)) * 0.45
    arr = sun_glare(arr, sx, sy, 10, 0.7, (1.0, 0.9, 0.75))
    img = B.finish(arr, 0.4); d = ImageDraw.Draw(img, "RGBA")
    d.ellipse((ex - 16, ey - 16, ex + 16, ey + 16), fill=(70, 140, 255), outline=WHITE, width=2)
    label(d, ex + 10, ey + 50, "EARTH", None, 230, CYAN, "lm", 26)
    label(d, sx, sy - 50, "BACKGROUND STAR", None, 230, YELLOW, "mm", 26)
    label(d, bx + 70, by, "BLACK HOLE", "moving ~50 km/s", 230, WHITE, "lm", 26)
    near = math.exp(-(offset / 120) ** 2)
    for s_ in (-1, 1):                                                          # two bent light paths around the lens
        mx, my = bx + s_ * perp[0] * (40 + 60 * (1 - near)), by + s_ * perp[1] * (40 + 60 * (1 - near))
        pts = [(sx + (mx - sx) * k, sy + (my - sy) * k) for k in np.linspace(0, 1, 20)] + [(mx + (ex - mx) * k, my + (ey - my) * k) for k in np.linspace(0, 1, 20)]
        d.line(pts, fill=(255, 220, 140, int(90 + 140 * near)), width=3)
    tag(d, "DIAGRAM  ·  not to scale (distances ~5,000 and ~20,000+ light-years)", (200, 200, 220))
    return img

def lens_track(t, t0, t1):
    """Lens path across the target star for the lensing shots: u(t) from -1.4 to +1.4 in thetaE units."""
    return lerp(-1.6, 1.6, seg(t, t0, t1))

def sc_lensing(t, t0, t1, small=False):
    x = lens_track(t, t0, t1); u0 = 0.12
    tE = 140
    cx, cy = 540 + x * tE, 960 - u0 * tE
    arr = B.lens_view(B.plate("bulge"), [(cx, cy, tE, 0)], off=TARGET, zoom=2.0)
    img = B.finish(arr, 0.5)
    if small: return img
    d = ImageDraw.Draw(img, "RGBA")
    tag(d, "VISUALIZATION  ·  real effect is millions of times smaller, unresolved", (200, 200, 220))
    return img

def sc_curve(t, t0, t1):
    """Top: lensing view. Bottom: brightness (light curve) and the star's apparent position shift, both drawing live."""
    top = sc_lensing(t, t0, t1, small=True)
    arr = np.asarray(top, np.float32).copy()
    arr[1180:] *= 0.18
    img = to_img(arr); d = ImageDraw.Draw(img, "RGBA")
    x = lens_track(t, t0, t1); u0 = 0.12
    gx0, gx1, gy0, gy1 = 110, 970, 1240, 1520
    d.rectangle((gx0 - 10, gy0 - 50, gx1 + 10, gy1 + 30), fill=(0, 0, 0, 170))
    d.text((gx0, gy0 - 28), "BRIGHTNESS  (simplified)", font=font(F_MONO, 24), fill=(255, 212, 0), anchor="lm")
    xs = np.linspace(-1.6, x, max(2, int(200 * (x + 1.6) / 3.2)))
    A = B.mag(np.sqrt(u0 ** 2 + xs ** 2)); A = np.log10(A) / np.log10(B.mag(u0))
    pts = [(gx0 + (xx + 1.6) / 3.2 * (gx1 - gx0), gy1 - a * (gy1 - gy0 - 20)) for xx, a in zip(xs, A)]
    if len(pts) > 1: d.line(pts, fill=(255, 212, 0), width=5)
    cx_, cy_ = 820, 1010
    d.ellipse((cx_ - 120, cy_ - 120, cx_ + 120, cy_ + 120), fill=(0, 0, 0, 170), outline=(130, 210, 255, 200), width=2)
    d.text((cx_, cy_ - 140), "POSITION SHIFT (exaggerated)", font=font(F_MONO, 20), fill=CYAN, anchor="mm", stroke_width=3, stroke_fill=BLACK)
    path = []
    for xx in np.linspace(-1.6, x, 60):
        uu = math.hypot(xx, u0); s_ = B.centroid_shift(uu)
        path.append((cx_ - xx / uu * s_ * 160, cy_ + u0 / uu * s_ * 160))
    if len(path) > 1: d.line(path, fill=CYAN, width=3)
    d.ellipse((path[-1][0] - 7, path[-1][1] - 7, path[-1][0] + 7, path[-1][1] + 7), fill=CYAN)
    tag(d, "SIMPLIFIED  ·  shape only; real shift ~ milliarcseconds", (200, 200, 220))
    return img

def cutout(i, n=11):
    """Simulated Hubble-like cutout of the source star with a fixed neighbour; the source's offset is exaggerated."""
    S = 220
    img = np.zeros((S, S), np.float32) + 6
    rng = np.random.default_rng(100 + i)
    img += rng.normal(0, 2.0, (S, S))
    x = np.linspace(-1.6, 1.6, n)[i]; uu = math.hypot(x, 0.12); s_ = B.centroid_shift(uu)
    yy, xx = np.mgrid[0:S, 0:S]
    for (px, py, f) in ((S / 2 - x / uu * s_ * 40, S / 2 + 0.12 / uu * s_ * 40, 1.0), (S * 0.22, S * 0.75, 0.55)):
        r2 = (xx - px) ** 2 + (yy - py) ** 2
        img += f * (210 * np.exp(-r2 / 18) + 40 * np.exp(-r2 / 160))
        img += f * 30 * (np.exp(-((xx - px) ** 2) / 2) * np.exp(-np.abs(yy - py) / 22) + np.exp(-((yy - py) ** 2) / 2) * np.exp(-np.abs(xx - px) / 22))
    return np.clip(img, 0, 255)

def sc_epochs(t, t0, t1):
    arr = np.zeros((H, W, 3), np.float32) + np.array([5, 6, 10], np.float32)
    img = to_img(arr); d = ImageDraw.Draw(img, "RGBA")
    headline(d, "HUBBLE: 11 EPOCHS · ~11 YEARS", seg(t, t0, t0 + 0.3), 300, WHITE, 56)
    for i in range(11):
        k = seg(t, t0 + 0.2 + i * 0.18, t0 + 0.4 + i * 0.18)
        if k <= 0: continue
        c = cutout(i); r, cl = divmod(i, 3)
        x0, y0 = 120 + cl * 290, 430 + r * 250
        tile = Image.fromarray(c.astype(np.uint8)).convert("RGB")
        img.paste(tile, (x0, y0))
        d.rectangle((x0, y0, x0 + 220, y0 + 220), outline=(130, 210, 255, int(220 * k)), width=2)
        d.line((x0 + 110, y0 + 4, x0 + 110, y0 + 30), fill=(255, 212, 0), width=2); d.line((x0 + 4, y0 + 110, x0 + 30, y0 + 110), fill=(255, 212, 0), width=2)
        d.text((x0 + 8, y0 + 204), f"epoch {i + 1}", font=font(F_MONO, 18), fill=(220, 220, 230), anchor="lm")
    tag(d, "SIMULATED CUTOUTS  ·  shift exaggerated ~10,000×, not Hubble data", (200, 200, 220))
    return img

def sc_result(t, t0, t1):
    u = ease_io(seg(t, t0, t1))
    arr = B.lens_view(B.plate("field"), [bh_lens(lerp(500, 580, u), lerp(980, 920, u), lerp(230, 260, u))], off=(-120 + 60 * u, 420 - 30 * u))
    img = B.finish(arr, 0.45); d = ImageDraw.Draw(img, "RGBA")
    q = seg(t, ws(11, 13) - 0.2, ws(11, 13) + 0.3)
    headline(d, "STELLAR-MASS BLACK HOLE", q, 320, YELLOW, 64)
    label(d, 540, 1350, "7.15 ± 0.83 SOLAR MASSES", "Sahu et al. 2025 · light curve + Hubble positions", int(255 * q), WHITE, size=40)
    tag(d, "VISUALIZATION  ·  lensing exaggerated, no disk (none observed)")
    return img

# ====================================================================== SCENE 8 — the distance
def sc_distance(t, t0, t1):
    u = ease_io(seg(t, t0, t1))
    mid = (SUN_POS + BH_POS) / 2
    h = lerp(5.0, 15.0, u)
    cam = mid + np.array([0.0, -0.3 * h, h], np.float32)
    arr = B.render_galaxy(cam, mid * (1 - 0.35 * u), fov=55, up=(1, 0, 0), dust_k=0.6, gain=lerp(6.0, 3.0, u))
    img = B.finish(arr, 0.4); d = ImageDraw.Draw(img, "RGBA")
    r_, u_, f_ = B.look_at(cam, mid, (1, 0, 0)); fpx = (W / 2) / math.tan(math.radians(55 / 2))
    def proj(Q):
        dd = Q - cam; z = dd @ f_
        return W / 2 + (dd @ r_) / z * fpx, H / 2 - (dd @ u_) / z * fpx
    tgt_ = mid * (1 - 0.35 * u); r_, u_, f_ = B.look_at(cam, tgt_, (1, 0, 0))
    sx, sy = proj(SUN_POS); bx, by = proj(BH_POS)
    d.line((sx, sy, bx, by), fill=(255, 212, 0, 220), width=3)
    d.ellipse((sx - 9, sy - 9, sx + 9, sy + 9), fill=(255, 230, 140)); label(d, sx + 20, sy, "SUN", None, 255, (255, 230, 140), "lm", 28)
    d.ellipse((bx - 11, by - 11, bx + 11, by + 11), outline=(130, 210, 255), width=3); label(d, bx + 20, by, "BLACK HOLE", None, 255, CYAN, "lm", 28)
    headline(d, "ABOUT 5,000 LIGHT-YEARS AWAY", seg(t, ws(12, 2) - 0.2, ws(12, 2) + 0.2), 330, YELLOW, 56)
    q = seg(t, ws(13, 2), ws(13, 2) + 0.3)
    label(d, 540, 440, "NO EVIDENCE IT IS APPROACHING US", None, int(255 * q), WHITE, size=36)
    tag(d, "CGI MODEL  ·  Milky Way, positions approximate")
    return img

# ====================================================================== SCENE 9 — hypothetical close pass (simulation)
def sc_hyp_card(t, t0, t1):
    u = ease_io(seg(t, t0, t1))
    arr = B.lens_view(B.plate("sparse"), [bh_lens(lerp(1250, 760, u), 1050, 110)], off=(0, -500))
    img = B.finish(arr, 0.4); d = ImageDraw.Draw(img, "RGBA")
    k = seg(t, t0, t0 + 0.3)
    headline(d, "HYPOTHETICAL", k, 820, ORANGE, 110); headline(d, "CLOSE PASS", k, 950, ORANGE, 110)
    label(d, 540, 1070, "", "a different, simulated black hole · not a known object", int(255 * k), WHITE, size=10)
    return img

def sc_nbody(t, t0, t1):
    names, tr, yrs = B.nbody_close_pass()
    n = len(tr)
    u = seg(t, t0, t1)
    i = int(lerp(n * 0.30, n * 0.80, u))
    S = 13.0                                                                     # px per AU
    cx, cy = 540, 960
    sunp = tr[i, 0]
    def P(p): return cx + (p[0] - sunp[0]) * S, cy - (p[1] - sunp[1]) * S          # Sun-centred frame
    bh = tr[i, -1]
    bxp, byp = P(bh)
    arr = B.lens_view(B.plate("sparse"), [bh_lens(bxp, byp, 70)], off=(0, -700))
    arr = sun_glare(arr, *P(sunp), 10, 0.9)
    img = B.finish(arr, 0.4); d = ImageDraw.Draw(img, "RGBA")
    for a in (1.0, 5.2, 9.58, 19.2, 30.07):                                      # original orbits (faint)
        d.ellipse((cx - a * S, cy - a * S, cx + a * S, cy + a * S), outline=(120, 140, 180, 70), width=1)
    cols = [(90, 160, 255), (230, 190, 140), (230, 210, 160), (150, 220, 230), (110, 140, 255)]
    j0 = int(n * 0.30)
    for k in range(1, 6):
        pts = [(cx + (tr[j, k][0] - tr[j, 0][0]) * S, cy - (tr[j, k][1] - tr[j, 0][1]) * S) for j in range(j0, i + 1, 2)]
        if len(pts) > 1: d.line(pts, fill=cols[k - 1] + (230,), width=3)
        x, y = P(tr[i, k]); d.ellipse((x - 6, y - 6, x + 6, y + 6), fill=cols[k - 1])
    bpts = [(cx + (tr[j, -1][0] - tr[j, 0][0]) * S, cy - (tr[j, -1][1] - tr[j, 0][1]) * S) for j in range(j0, i + 1, 3)]
    if len(bpts) > 1: d.line(bpts, fill=(255, 255, 255, 90), width=2)
    label(d, 540, 300, "HYPOTHETICAL CLOSE PASS", None, 255, ORANGE, size=44)
    label(d, 540, 1600, "", "simulation: 7 M☉ black hole, closest ~35 AU from the Sun, 30 km/s", 230, WHITE, size=10)
    q = seg(t, ws(15, 5) - 0.2, ws(15, 5) + 0.3)
    label(d, 540, 380, "ORBITS DISTURBED, NOT SWALLOWED", None, int(255 * q), WHITE, size=32)
    tag(d, "N-BODY SIMULATION  ·  hypothetical, illustrative", ORANGE)
    return img

# ====================================================================== SCENE 10 — the invisible universe
def sc_final(t, t0):
    u = seg(t, t0, DUR)
    z = lerp(1.0, 0.86, ease_io(seg(t, ls(17), DUR - 1.0)))                      # slow pull-back on "in plain sight"
    arr = B.lens_view(B.plate("field"), [bh_lens(lerp(-80, 1160, u), lerp(1150, 820, u), 95 * z, 0.0)], off=(250 - 60 * u, -520), zoom=z)
    img = B.finish(arr, 0.4); d = ImageDraw.Draw(img, "RGBA")
    k = seg(t, NARR_END + 0.2, NARR_END + 1.0)
    if k > 0:
        s = max(0.9, ease_out(k))
        d.text((540, 880), "THE INVISIBLE", font=font(F_CAP, 108 * s), fill=(255, 255, 255, int(255 * k)), anchor="mm", stroke_width=10, stroke_fill=BLACK)
        d.text((540, 1000), "UNIVERSE", font=font(F_CAP, 108 * s), fill=(255, 212, 0, int(255 * k)), anchor="mm", stroke_width=10, stroke_fill=BLACK)
    tag(d, "VISUALIZATION  ·  a lens drifting across distant stars")
    return img

# ====================================================================== particles helper
def add_particles(arr, paths, t, n=200, speed=0.4, col=(255, 255, 255), amt=1.0, spread=8.0, seed=3, size=2.6):
    rng = np.random.default_rng(seed)
    lay = Image.new("L", (W, H), 0); d = ImageDraw.Draw(lay)
    ph = rng.random(n); pi = rng.integers(0, len(paths), n); off = rng.normal(0, 1, (n, 2)); br = rng.uniform(0.4, 1.0, n)
    for i in range(n):
        u = (ph[i] + t * speed) % 1.0
        P = np.array(paths[pi[i]], np.float32)
        b = (1 - u) ** 3 * P[0] + 3 * (1 - u) ** 2 * u * P[1] + 3 * (1 - u) * u ** 2 * P[2] + u ** 3 * P[3] + off[i] * spread * math.sin(math.pi * u)
        f = min(1, u / 0.08, (1 - u) / 0.12) * br[i]
        d.ellipse((b[0] - size, b[1] - size, b[0] + size, b[1] + size), fill=int(255 * f))
    g = np.asarray(lay.filter(ImageFilter.GaussianBlur(1.6)), np.float32) / 255
    return arr + g[..., None] * np.array(col, np.float32) * amt * 1.6

# ====================================================================== timeline
def build_scenes():
    c = [HOOK_END, ls(2) - 0.1, ls(3) - 0.1, ls(4) - 0.1, ls(5) - 0.1, ls(6) - 0.1, ls(7) - 0.1, ws(7, 5) - 0.2, ls(8) - 0.1,
         ws(8, 10) - 0.1, ls(9) - 0.1, ls(10) - 0.1, ls(11) - 0.1, ls(12) - 0.1, le(13) + 0.25, ls(14) - 0.1, ls(16) - 0.1]
    fns = [sc_found, sc_binary, sc_alone, sc_galaxy_fly, sc_mass, sc_observatory, sc_hubble, sc_target, sc_geometry,
           sc_lensing, sc_curve, sc_epochs, sc_result, sc_distance, sc_hyp_card, sc_nbody]
    out = [(0.0, HOOK_END, sc_hook)]
    for i, fn in enumerate(fns):
        a, b = c[i], c[i + 1]
        if fn is sc_lensing: out.append((a, b, (lambda a, b: (lambda t: sc_lensing(t, a, b + 5.2)))(a, b)))
        elif fn is sc_curve: out.append((a, b, (lambda a, b, a0: (lambda t: sc_curve(t, a0, b + 0.0)))(a, b, c[i - 1])))
        else: out.append((a, b, (lambda f, a, b: (lambda t: f(t, a, b)))(fn, a, b)))
    out.append((c[-1], DUR + 1, lambda t: sc_final(t, c[-1])))
    return out
SCENES = build_scenes()

# ====================================================================== captions (phrase-based)
PHRASE_TEXT = [
 "AN INVISIBLE BLACK HOLE | IS MOVING THROUGH OUR GALAXY.",
 "AND SCIENTISTS HAVE ACTUALLY FOUND ONE.",
 "MOST BLACK HOLES ARE DISCOVERED | THROUGH THEIR EFFECTS ON NEARBY STARS, | OR GLOWING MATERIAL.",
 "BUT THIS ONE WAS COMPLETELY ALONE.",
 "IT'S CALLED OGLE-2011-BLG-0462.",
 "ITS MASS IS ABOUT SEVEN TIMES OUR SUN'S, | YET IT GIVES OFF NO LIGHT | WE CAN DIRECTLY DETECT.",
 "SO HOW DID ASTRONOMERS | FIND SOMETHING INVISIBLE?",
 "THEY WATCHED A DISTANT STAR | BEHAVE IN A VERY STRANGE WAY.",
 "AS THE BLACK HOLE CROSSED | IN FRONT OF THE BACKGROUND STAR, | ITS GRAVITY BENT AND MAGNIFIED | THE STAR'S LIGHT.",
 "THE STAR APPEARED TO BRIGHTEN, | AND ITS APPARENT POSITION | SHIFTED BY A TINY AMOUNT.",
 "HUBBLE TRACKED THAT MOVEMENT OVER YEARS.",
 "SCIENTISTS COMBINED THOSE MEASUREMENTS | TO DETERMINE THAT THE HIDDEN OBJECT | WAS A STELLAR-MASS BLACK HOLE.",
 "IT'S ROUGHLY 5,000 LIGHT-YEARS AWAY.",
 "THERE IS NO EVIDENCE | THAT THIS OBJECT IS APPROACHING | OUR SOLAR SYSTEM.",
 "BUT IMAGINE A DIFFERENT BLACK HOLE | PASSING CLOSE TO OUR PLANETARY NEIGHBORHOOD.",
 "ITS GRAVITY COULD DISTURB PLANETARY ORBITS, | DEPENDING ON ITS MASS AND DISTANCE.",
 "THE FRIGHTENING PART | ISN'T THAT ONE IS COMING.",
 "IT'S THAT THE UNIVERSE CAN HIDE | SOMETHING THIS MASSIVE | IN PLAIN SIGHT.",
]
KEY = {"INVISIBLE", "FOUND", "ALONE.", "OGLE-2011-BLG-0462.", "SEVEN", "NO", "INVISIBLE?", "BENT", "MAGNIFIED", "BRIGHTEN,", "SHIFTED",
       "HUBBLE", "STELLAR-MASS", "BLACK", "HOLE.", "NO", "DIFFERENT", "DISTURB", "ORBITS,", "PLAIN", "SIGHT.", "GRAVITY"}
def build_phrases():
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
PHRASES = build_phrases()

def draw_caption(img, t):
    if t < ls(1) - 0.05: return                                                  # the hook title carries line 0
    y = 1420
    for a, b, ph in PHRASES:
        if not (a <= t < b): continue
        d = ImageDraw.Draw(img); f = font(F_CAP, 70); gap = 17; maxw = 900
        items = [(w, f.getlength(w), bool(re.search(r"\d", w)) or w in KEY) for w, s, e in ph]
        rows, cur, cw = [], [], 0
        for it in items:
            if cur and cw + gap + it[1] > maxw: rows.append(cur); cur, cw = [], 0
            cur.append(it); cw += (gap if len(cur) > 1 else 0) + it[1]
        rows.append(cur)
        k = ease_out(seg(t, a, a + 0.12)); al = int(255 * k); dy = 12 * (1 - k)
        lh = 82; y0 = y - (len(rows) - 1) * lh / 2 + dy
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
GRAIN = [GR.normal(0, 2.2, (H, W, 1)).astype(np.float32) for _ in range(4)]       # per-pixel grain at native res (anti-banding)
yy_, xx_ = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1 - 0.25 * (((xx_ - W / 2) / (W / 2)) ** 2 + ((yy_ - H / 2) / (H / 2)) ** 2) ** 1.6).clip(0.55, 1)[..., None]
del yy_, xx_

def frame(fi):
    t = fi / FPS
    img = None
    for a, b, fn in SCENES:
        if a <= t < b: img = fn(t); break
    for i, (a, b, fn) in enumerate(SCENES[1:]):
        if 0 <= t - a < 0.2:
            img = Image.blend(SCENES[i][2](t).convert("RGB"), img.convert("RGB"), ease(seg(t, a, a + 0.2)))
    arr = np.asarray(img.convert("RGB"), np.float32) * VIG + GRAIN[fi % 4]
    img = to_img(arr)
    draw_caption(img, t)
    return img.tobytes()

def warm():
    B.plate("bulge"); B.plate("sparse"); B.plate("field"); B.galaxy(); B.nbody_close_pass(); B.grid()

FINAL_X264 = ["-c:v", "libx264", "-preset", "slow", "-crf", "14", "-maxrate", "18M", "-bufsize", "36M", "-profile:v", "high", "-level", "4.2",
              "-pix_fmt", "yuv420p", "-g", "60", "-x264-params", "aq-mode=3:aq-strength=0.9:deblock=-1,-1", "-r", "30", "-fps_mode", "cfr"]

def encode(frames, out, final=False):
    vargs = FINAL_X264 if final else ["-c:v", "libx264", "-preset", "medium", "-crf", "15", "-pix_fmt", "yuv420p"]
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"] + vargs + [out], stdin=subprocess.PIPE)
    warm()
    with Pool(4) as pool:
        for i, b in enumerate(pool.imap(frame, frames, chunksize=2)):
            p.stdin.write(b)
            if i % 300 == 0: print("frame", frames[0] + i, flush=True)
    p.stdin.close(); p.wait()

# ====================================================================== sound
def lens_whoom(d=1.6, f0=38, f1=26):
    n = int(d * SR); tt = np.arange(n) / SR
    f = f0 + (f1 - f0) * tt / d
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(1, tt / 0.15) * np.exp(-tt / (d * 0.55))
    return s + lp(arng.normal(0, 1, n), 140) * 0.6 * np.exp(-tt / (d * 0.4))

def chime(d=4.0):
    n = int(d * SR); tt = np.arange(n) / SR
    return sum(np.sin(2 * np.pi * f * tt) * np.exp(-tt / dec) * a for f, dec, a in ((392.0, 2.4, 0.5), (587.3, 1.8, 0.3), (784.0, 1.2, 0.18)))

def render_audio(out):
    n = int(DUR * SR); tt = np.arange(n) / SR
    chords = [(0, [43.65, 65.41, 103.83, 130.81]), (ls(4), [41.2, 61.74, 98.0, 123.47]), (ls(8), [46.25, 69.3, 110.0, 138.59]),
              (ls(11), [43.65, 65.41, 110.0, 130.81]), (ls(14), [38.89, 58.27, 92.5, 116.54]), (ls(16), [43.65, 65.41, 103.83, 155.56, 196.0])]
    pad = np.zeros(n)
    for ci, (t0, notes) in enumerate(chords):
        t1 = chords[ci + 1][0] if ci + 1 < len(chords) else DUR
        i0, i1 = int(t0 * SR), min(n, int(t1 * SR) + int(1.0 * SR)); m = i1 - i0; sg = np.zeros(m)
        for f in notes:
            for det in (-0.1, 0.0, 0.09): sg += osc(f * 2 ** (det / 12), m)
        e = np.minimum(1, np.arange(m) / (1.0 * SR)) * np.minimum(1, (m - np.arange(m)) / (1.0 * SR))
        pad[i0:i1] += sg * e / 12
    pulse = np.zeros(n); t = ls(8)
    while t < ls(12):
        place(pulse, boom(0.45, 64, 40, 0.11), t, 0.28); t += 60 / 80
    swell = np.interp(tt, [0, 2.5, 3.2, ls(8), ls(11), ls(14), ls(16), NARR_END, DUR - 0.5, DUR], [0.9, 0.9, 0.55, 0.75, 0.9, 0.85, 0.7, 0.55, 0.3, 0.0])
    mus = (lp(pad, 1000) * 0.7 + lp(pad, 360) * 0.6 + osc(32.7, n, "sin") * 0.16 + pulse) * swell
    fx = np.zeros(n)
    place(fx, reverb(boom(2.8, 110, 22, 0.9), 3.4, 0.45), 0.0, 1.7)                                   # opening impact (one)
    place(fx, lens_whoom(2.2, 44, 24), 0.0, 0.9)
    for a, b, fn in SCENES[1:]:
        if a < DUR - 1: place(fx, whoosh(0.6), a - 0.2, 0.14)
    for tt0 in (ls(3) + 0.1, ls(8) + 1.0, ls(11) + 0.2, ls(14) + 0.3):                                 # subtle gravitational distortion swells
        place(fx, lens_whoom(1.8, 40, 28), tt0, 0.45)
    place(fx, tick(1500), ws(5, 4), 0.12)
    place(fx, chime(4.5), NARR_END + 0.25, 0.5)                                                     # quiet, memorable ending
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
    elif cmd == "hooks":
        for v in "ABC":
            os.environ["HOOK"] = v; HOOK = v; globals()["HOOK"] = v
            warm()
            p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                                  "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", f"hook{v}.mp4"], stdin=subprocess.PIPE)
            for i in range(90): p.stdin.write(frame(i))
            p.stdin.close(); p.wait()
    elif cmd == "hookone":
        warm()
        p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                              "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", f"hook{HOOK}.mp4"], stdin=subprocess.PIPE)
        for i in range(90): p.stdin.write(frame(i))
        p.stdin.close(); p.wait()
    elif cmd == "audio": render_audio(sys.argv[2])
    elif cmd == "preview":
        t0, t1, out = float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
        encode(list(range(int(t0 * FPS), int(t1 * FPS))), "_v.mp4", final=True)
        render_audio("_a.wav")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", "_v.mp4", "-ss", str(t0), "-t", str(t1 - t0), "-i", "_a.wav", "-map", "0:v", "-map", "1:a",
                        "-af", "loudnorm=I=-14:TP=-1.5", "-c:v", "copy", "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-shortest", out], check=True)
    elif cmd == "final":
        encode(list(range(NF)), "video_final_v.mp4", final=True)
