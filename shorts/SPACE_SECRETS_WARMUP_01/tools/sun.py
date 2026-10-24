#!/usr/bin/env python3
# SPACE SECRETS WARM-UP 01: "What If the Sun Disappeared?" (15 s vertical TikTok)
# Visuals: procedural photoreal Sun (granulation, limb darkening, sunspots, prominences, corona), Earth rendered from
# Solar System Scope textures (CC BY 4.0, NASA-based) via earth.py, animated diagrams. Audio: Kokoro VO + synthesized score/SFX.
import json, math, re, subprocess, sys
from multiprocessing import Pool

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

import earth
from sfx import SR, lp, hp, bp, envx, place, osc, boom, crack, whoosh, tick, riser, reverb, arng

W, H, FPS, DUR = 1080, 1920, 30, 15.0
NF = int(DUR * FPS)
TIM = json.load(open("timing.json"))
WT = {(l["line"], k): (s, e) for l in TIM for k, (w, s, e) in enumerate(l["words"])}
def ws(l, k): return WT[(l, k)][0]

T_COL0 = ws(0, 6) - 0.05          # "now?" -> the collapse begins
T_GONE = T_COL0 + 0.28            # the Sun is gone: flash + impact
S2 = 3.0                          # the delay
T_DARK = ws(2, 2)                 # "darkness."  = last light reaches Earth (8 min 20 s after the vanish)
T_GRAV = ws(2, 8)                 # "gone." the orbit breaks
S4 = 11.0                         # the question / pullback
T_LOOP = 14.15                    # the Sun re-ignites for the loop

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

# ------------------------------------------------------------------ backgrounds
_ST = {}
def stars(zoom=1.0):
    if "base" not in _ST: _ST["base"] = earth.stars(int(W * 1.3), int(H * 1.3), seed=11, n=9000)
    b = _ST["base"]; bh, bw = b.shape[:2]
    cw, ch = W * 1.3 / zoom, H * 1.3 / zoom
    x0, y0 = (bw - cw) / 2, (bh - ch) / 2
    return np.asarray(Image.fromarray(b.astype(np.uint8)).resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch)), np.float32)

# ------------------------------------------------------------------ the Sun
def _noise(rng, shape, sigmas, weights):
    out = np.zeros(shape, np.float32)
    for s, w in zip(sigmas, weights):
        n = ndimage.gaussian_filter(rng.normal(0, 1, shape).astype(np.float32), s, mode="wrap")
        out += w * n / (n.std() + 1e-6)
    return out / sum(weights)

_SUN = {}
def sun_tex():
    if not _SUN:
        rng = np.random.default_rng(5)
        shp = (720, 1440)
        g1 = _noise(rng, shp, (1.1, 2.4, 9.0), (1.0, 0.7, 0.35))
        g2 = _noise(rng, shp, (1.1, 2.4, 9.0), (1.0, 0.7, 0.35))
        g1 = np.tanh(g1 * 1.6); g2 = np.tanh(g2 * 1.6)        # cell-like contrast
        spots = np.zeros(shp, np.float32)
        yy, xx = np.mgrid[0:shp[0], 0:shp[1]].astype(np.float32)
        for la, lo, r in ((18, -30, 14), (14, -22, 8), (-12, 40, 11), (-16, 52, 6), (22, 110, 10), (-20, 160, 9), (10, 200, 7)):
            v, u = (90 - la) / 180 * shp[0], (lo % 360) / 360 * shp[1]
            d = np.sqrt((xx - u) ** 2 + (yy - v) ** 2)
            spots = np.maximum(spots, np.clip(1 - d / (r * 1.8), 0, 1) ** 0.7 * 0.55 + (d < r * 0.7) * 0.4)
        spots = ndimage.gaussian_filter(spots, 1.5)
        fac = np.clip(_noise(rng, shp, (14.0,), (1.0,)), 0, None)       # faculae: bright patches visible near the limb
        _SUN.update(g1=g1, g2=g2, spots=spots, fac=fac)
        _SUN["ang"] = rng.normal(0, 1, 720)
    return _SUN

def ramp(x):
    xp = [0.0, 0.18, 0.4, 0.62, 0.8, 0.95, 1.15]
    r = np.interp(x, xp, [0, 120, 215, 255, 255, 255, 255])
    g = np.interp(x, xp, [0, 25, 80, 150, 205, 238, 252])
    b = np.interp(x, xp, [0, 0, 10, 40, 110, 190, 240])
    return np.stack([r, g, b], -1)

def _ang_noise(theta, t, freq, speed):
    A = sun_tex()["ang"]; n = len(A)
    p = (theta / (2 * np.pi) * freq + speed * t) % 1.0 * n
    i0 = np.floor(p).astype(int) % n; f = p - np.floor(p)
    a = A[i0] * (1 - f) + A[(i0 + 1) % n] * f
    return a

def draw_sun(base, cx, cy, R, ts, bright=1.0, corona=1.0):
    """Adds a Sun (linear light, 0..~1.2 scale) onto base (H,W,3 float 0..255). ts = sun time (texture drift)."""
    T = sun_tex()
    ext = R * 3.2
    x0, x1 = int(max(0, cx - ext)), int(min(W, cx + ext)); y0, y1 = int(max(0, cy - ext)), int(min(H, cy + ext))
    if x1 <= x0 or y1 <= y0 or R < 0.5: return base
    ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    nx = (xs - cx) / R; ny = (cy - ys) / R
    r = np.sqrt(nx * nx + ny * ny); theta = np.arctan2(ny, nx)
    lin = np.zeros(r.shape + (3,), np.float32)
    # corona + glow (outside and over the disk)
    streak = 1 + 0.55 * _ang_noise(theta, ts, 9, 0.004) + 0.35 * _ang_noise(theta, ts, 23, -0.006)
    rr = np.maximum(r, 1.0)
    cor = (0.35 * np.exp(-(rr - 1) / 0.035) + 0.16 * rr ** -5 * streak + 0.025 * rr ** -1.6) * corona
    lin += cor[..., None] * np.array([1.0, 0.62, 0.28], np.float32)
    # prominences / chromosphere flames along the rim
    fl = np.clip(_ang_noise(theta, ts, 40, 0.02) * 0.9 + _ang_noise(theta, ts, 97, -0.03) * 0.5 - 0.35, 0, None)
    flame = fl * np.exp(-np.clip(r - 1, 0, None) / (0.012 + 0.05 * fl)) * (r >= 0.995)
    lin += (flame * 0.9 * corona)[..., None] * np.array([1.0, 0.35, 0.12], np.float32)
    # photosphere
    m = r < 1
    if m.any():
        mu = np.sqrt(1 - np.clip(r[m], 0, 1) ** 2)
        tilt = math.radians(7)
        X, Y, Z = nx[m], ny[m] * math.cos(tilt) + mu * math.sin(tilt), -ny[m] * math.sin(tilt) + mu * math.cos(tilt)
        lat = np.degrees(np.arcsin(np.clip(Y, -1, 1))); lon = np.degrees(np.arctan2(X, Z))
        th, tw = T["g1"].shape
        v = (90 - lat) / 180 * (th - 1)
        u1 = ((lon + 25 + 2.2 * ts) % 360) / 360 * tw; u2 = ((lon + 25 + 2.2 * ts + 0.9 * ts) % 360) / 360 * tw
        sm = lambda img, u: ndimage.map_coordinates(img, [v, u], order=1, mode="wrap")
        w = 0.5 + 0.5 * math.sin(ts * 0.9)
        gran = sm(T["g1"], u1) * w + sm(T["g2"], u2) * (1 - w)
        u0 = ((lon + 25 + 2.2 * ts) % 360) / 360 * tw
        spot = sm(T["spots"], u0); fac = sm(T["fac"], u0)
        limb = 1 - 0.62 * (1 - mu) - 0.18 * (1 - mu) ** 2
        val = limb * (0.86 + 0.13 * gran) * (1 - 0.75 * spot) + 0.25 * fac * (1 - mu) ** 2
        col = ramp(val * 0.8 * bright ** 0.5) / 255.0
        edge = np.clip((1 - r[m]) * R / 1.5, 0, 1)[:, None]
        lin[m] = lin[m] * (1 - edge) + col * edge + lin[m] * 0.3 * edge
    base[y0:y1, x0:x1] += lin * 255 * min(bright, 1.6)
    return base

def bloom(arr, amt=0.6, radius=40):
    small = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
    hi = np.clip(np.asarray(small, np.float32) - 150, 0, None)
    bl = np.asarray(Image.fromarray(np.clip(hi * 1.6, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius / 4)).resize((W, H), Image.BILINEAR), np.float32)
    return arr + bl * amt

def tone(arr):
    a = arr / 255.0
    return np.clip(255 * (1 - np.exp(-a * 1.25)) / (1 - math.exp(-1.25)), 0, 255)

def to_img(arr): return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

# ------------------------------------------------------------------ overlays
def tag(d, txt="HYPOTHETICAL  ·  VISUALIZATION", col=ORANGE):
    f = font(F_MONO, 24)
    d.rounded_rectangle((36, 60, 36 + f.getlength(txt) + 28, 104), 10, fill=(0, 0, 0, 150))
    d.ellipse((48, 76, 60, 88), fill=col)
    d.text((70, 82), txt, font=f, fill=(230, 230, 230), anchor="lm")
    d.text((W - 40, 82), "SPACE SECRETS", font=f, fill=(200, 200, 200), anchor="rm", stroke_width=3, stroke_fill=BLACK)

def credit(d):
    d.text((W / 2, 1890), "Earth imagery: Solar System Scope (CC BY 4.0), based on NASA data", font=font(F_MONO, 20),
           fill=(170, 170, 170), anchor="mm", stroke_width=2, stroke_fill=BLACK)

def pop(d, x, y, txt, size, age, color=WHITE, sw=10):
    if age < 0: return
    s = size * (1 + 0.35 * max(0, 1 - age / 0.14))
    d.text((x, y), txt, font=font(F_CAP, s), fill=color, anchor="mm", stroke_width=sw, stroke_fill=BLACK)

def shake(t, t0, dur, amp):
    if not (t0 <= t < t0 + dur): return 0.0, 0.0
    k = 1 - (t - t0) / dur
    return amp * k * math.sin(t * 97), amp * k * math.cos(t * 83)

# ------------------------------------------------------------------ captions (series identity)
EMPH = {"SUN", "VANISHED...", "NOW?", "EIGHT", "MINUTES,", "WOULDN'T", "DARKNESS.", "GRAVITY", "GONE.", "SURVIVE?", "HUMANITY"}
CAPS = []
for l in TIM:
    toks = []; prev = -1
    for w, s, e in l["words"]:
        s = max(s, prev + 0.09); prev = s                      # energy-dip alignment can collapse two words onto one time
        toks.append((w.upper(), s, e))
    chunk = []
    for i, tk in enumerate(toks):
        chunk.append(tk)
        if re.search(r"[,.?!]$", tk[0]) or len(chunk) == 3 or i == len(toks) - 1:
            CAPS.append(chunk); chunk = []
CAPS = [(ch[0][1], (CAPS[i + 1][0][1] if i + 1 < len(CAPS) and CAPS[i + 1][0][1] - ch[-1][2] < 0.6 else ch[-1][2] + 0.45), ch)
        for i, ch in enumerate(CAPS)]

def draw_caption(img, t, y=1660):
    d = ImageDraw.Draw(img)
    for a, b, ch in CAPS:
        if not (a <= t < b): continue
        vis = [x for x in ch if x[1] <= t + 0.02]
        if not vis: return
        base, gap, maxw = 96, 24, 960
        line, tot = [], 0
        for w, s, e in vis:
            sz = base * (1 + 0.25 * max(0, 1 - (t - s) / 0.11))
            fw = font(F_CAP, sz).getlength(w)
            if fw > maxw: sz *= maxw / fw; fw = maxw
            line.append((w, sz, w in EMPH, fw)); tot += fw
        tot += gap * (len(line) - 1)
        if tot > maxw:                                        # two lines
            rows = [line[:-1], line[-1:]]
        else:
            rows = [line]
        lh = int(base * 1.1); y0 = y - (len(rows) - 1) * lh / 2
        for ri, row in enumerate(rows):
            tw = sum(x[3] for x in row) + gap * (len(row) - 1); x = W / 2 - tw / 2
            for w, sz, em, fw in row:
                d.text((x, y0 + ri * lh), w, font=font(F_CAP, sz), fill=YELLOW if em else WHITE, anchor="lm", stroke_width=10, stroke_fill=BLACK)
                x += fw + gap
        return

# ------------------------------------------------------------------ scenes
SUN_X, SUN_Y = 540, 860
def sun_R(t): return lerp(400, 450, ease(seg(t, 0, T_COL0)))   # slow push-in during the hook

def sc_hook(t):
    dx, dy = shake(t, T_GONE, 0.6, 30)
    arr = stars(1.0)
    if t < T_GONE:
        k = seg(t, T_COL0, T_GONE)
        R = sun_R(t) * (1 - ease_in(k)) ** 1.4
        arr = draw_sun(arr, SUN_X + dx, SUN_Y + dy, max(R, 1), t, bright=1 + 2.2 * k ** 2, corona=1 + 2.0 * k)
    arr = bloom(arr, 0.45)
    img = to_img(tone(arr)); d = ImageDraw.Draw(img, "RGBA")
    if T_COL0 <= t < T_GONE:                                   # light collapsing inward
        k = seg(t, T_COL0, T_GONE)
        for i in range(70):
            a = i * 2 * math.pi / 70 + 0.3
            r0 = lerp(1100, 80, ease_in(k)) * (0.8 + 0.4 * ((i * 37) % 11) / 11); r1 = r0 * lerp(0.55, 0.1, k)
            d.line((SUN_X + r0 * math.cos(a), SUN_Y + r0 * math.sin(a), SUN_X + r1 * math.cos(a), SUN_Y + r1 * math.sin(a)),
                   fill=(255, 230, 170, int(200 * k)), width=6)
    if t >= T_GONE:
        age = t - T_GONE
        if age < 0.9:                                          # shock ring of the last light
            rr = 60 + 1400 * ease_out(age / 0.9)
            d.ellipse((SUN_X - rr, SUN_Y - rr, SUN_X + rr, SUN_Y + rr), outline=(255, 170, 90, int(200 * (1 - age / 0.9))), width=int(10 + 30 * (1 - age / 0.9)))
        if age < 0.3:
            img = Image.blend(img, Image.new("RGB", (W, H), (255, 246, 230)), 0.9 * (1 - age / 0.3)); d = ImageDraw.Draw(img, "RGBA")
    tag(d)
    k = ease_back(seg(t, 0.03, 0.25))
    if t < T_GONE and k > 0:
        d.text((W / 2, 250), "WHAT IF THE SUN", font=font(F_CAP, 84 * k), fill=WHITE, anchor="mm", stroke_width=9, stroke_fill=BLACK)
        d.text((W / 2, 350), "DISAPPEARED?", font=font(F_CAP, 110 * k), fill=YELLOW, anchor="mm", stroke_width=10, stroke_fill=BLACK)
    if t >= T_GONE:
        pop(d, W / 2 + dx, SUN_Y - 60 + dy, "THE SUN", 120, t - T_GONE)
        pop(d, W / 2 + dx, SUN_Y + 70 + dy, "DISAPPEARS", 128, t - T_GONE - 0.08, YELLOW)
    return img

E_X, E_Y, E_R = 540, 1130, 400
GHOST_Y, GHOST_R = 250, 70
SUNDIR = (0.05, 0.92, 0.38)                                    # light from the top of the frame, where the Sun was

def earth_layer(t, cx, cy, R, light, zoom=1.0, night_only=False):
    st = stars(zoom)
    lon = -20 - 3.0 * t
    lit = earth.render(W, H, cx, cy, R, 12, lon, lon - 1.5 * t, sun=SUNDIR, stars=st) if light > 0 else None
    if light >= 1: return lit
    dark = earth.render(W, H, cx, cy, R, 12, lon, lon - 1.5 * t, sun=(0.2, 0.1, -0.97), stars=st, night_gain=3.2, ambient=0.03)  # no sunlight: night everywhere
    dark = st + (dark - st) * 0.8
    return dark if lit is None else lit * light + dark * (1 - light)

def cprog(t): return 1 - (1 - seg(t, S2 + 0.25, T_DARK)) ** 3      # fast, then crawling through the last seconds
T_8MIN = S2 + 0.25 + (1 - 0.04 ** (1 / 3)) * (T_DARK - S2 - 0.25)    # count passes 8:00
def countdown(t):
    s = 500 * cprog(t)
    return f"{int(s // 60)}:{int(s % 60):02d}"

def sc_delay(t):                                              # 3.0 -> T_GRAV - 0.9 : the light still in transit, then darkness
    R = lerp(E_R, E_R + 30, seg(t, S2, S4))
    light = 1 - ease(seg(t, T_DARK, T_DARK + 0.45))
    if T_DARK <= t < T_DARK + 0.45: light *= 0.75 + 0.25 * math.sin(t * 90)      # last-light flicker
    dx, dy = shake(t, T_DARK, 0.5, 12)
    arr = earth_layer(t, E_X + dx, E_Y + dy, R, light)
    img = to_img(tone(bloom(arr, 0.35))); d = ImageDraw.Draw(img, "RGBA")
    # beam of sunlight still travelling: from the vanished Sun down to Earth; its tail (the last light) descends
    tail = lerp(GHOST_Y + GHOST_R, E_Y - R, cprog(t))
    if t < T_DARK + 0.05:
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
        bot = E_Y - R * 0.55
        for j in range(26):
            q = j / 26; y_a = lerp(tail, bot, q); y_b = lerp(tail, bot, q + 1 / 26)
            fa = lambda y: lerp(GHOST_R * 1.2, R * 0.95, (y - GHOST_Y) / (E_Y - GHOST_Y))
            od.polygon([(E_X - fa(y_a), y_a), (E_X + fa(y_a), y_a), (E_X + fa(y_b), y_b), (E_X - fa(y_b), y_b)],
                       fill=(255, 200, 110, int(16 + 26 * q)))
        rng = np.random.default_rng(int(t * 30))
        for _ in range(26):                                   # photons streaming down
            y = rng.uniform(tail, bot); x = E_X + rng.uniform(-1, 1) * lerp(GHOST_R, R, (y - GHOST_Y) / (E_Y - GHOST_Y))
            od.line((x, y, x, y + 60), fill=(255, 235, 180, 170), width=3)
        od.line((E_X - 360, tail, E_X + 360, tail), fill=(255, 212, 0, 230), width=4)
        od.text((E_X + 370, tail), "LAST SUNLIGHT", font=font(F_MONO, 24), fill=YELLOW, anchor="rm", stroke_width=3, stroke_fill=BLACK)
        ov = ov.filter(ImageFilter.GaussianBlur(1.2)); img.paste(ov, (0, 0), ov); d = ImageDraw.Draw(img, "RGBA")
    ga = int(255 * (1 - seg(t, T_DARK + 0.2, T_DARK + 0.9)))
    if ga > 0:                                                 # where the Sun was
        for i in range(0, 360, 12):
            a0 = math.radians(i)
            d.arc((E_X - GHOST_R, GHOST_Y - GHOST_R, E_X + GHOST_R, GHOST_Y + GHOST_R), i, i + 7, fill=(255, 200, 120, ga), width=4)
        d.text((E_X, GHOST_Y - GHOST_R - 22), "THE SUN WAS HERE", font=font(F_MONO, 26), fill=(255, 210, 150, ga), anchor="mb", stroke_width=3, stroke_fill=BLACK)
    tag(d)
    if t < T_DARK + 0.3:
        a = int(255 * (1 - seg(t, T_DARK + 0.1, T_DARK + 0.3)))
        d.text((W / 2, 420), "LIGHT + GRAVITY TRAVEL TIME", font=font(F_MONO, 30), fill=(230, 230, 230, a), anchor="mm", stroke_width=4, stroke_fill=BLACK)
        k = ease_back(seg(t, S2, S2 + 0.25))
        d.text((W / 2, 520), countdown(t), font=font(F_CAP, 150 * k), fill=(255, 255, 255, a) if t < T_DARK else (255, 212, 0, a), anchor="mm", stroke_width=12, stroke_fill=BLACK)
    t8 = T_8MIN                                       # "8 MINUTES LATER..." card as the count passes 8 minutes
    if t8 <= t < T_DARK + 0.5:
        a = int(255 * (1 - seg(t, T_DARK + 0.1, T_DARK + 0.5)))
        s = 1 + 0.3 * max(0, 1 - (t - t8) / 0.14)
        d.rounded_rectangle((W / 2 - 440 * s, 650 - 58 * s, W / 2 + 440 * s, 650 + 58 * s), 18, fill=(0, 0, 0, int(a * 0.75)))
        d.text((W / 2, 650), "8 MINUTES LATER...", font=font(F_CAP, 84 * s), fill=(255, 212, 0, a), anchor="mm", stroke_width=8, stroke_fill=BLACK)
    if t >= T_DARK + 0.3:
        pop(d, W / 2, 470, "DARKNESS", 140, t - T_DARK - 0.3)
        d.text((W / 2, 570), "no incoming sunlight anywhere", font=font(F_MONO, 30), fill=(200, 200, 200), anchor="mm", stroke_width=4, stroke_fill=BLACK)
    credit(d)
    return img

ORB_X, ORB_Y, ORB_R = 540, 560, 250
def orbit_pos(t):
    w = 0.55; a0 = -0.6
    tg = T_GRAV
    if t < tg:
        a = a0 + w * (t - (T_GRAV - 1.0))
        return ORB_X + ORB_R * math.cos(a), ORB_Y - ORB_R * math.sin(a), a
    ag = a0 + w * 1.0
    px, py = ORB_X + ORB_R * math.cos(ag), ORB_Y - ORB_R * math.sin(ag)
    tx, ty = -math.sin(ag), -math.cos(ag)                    # tangent (counter-clockwise on screen)
    s = ORB_R * w * (t - tg) * 1.5
    return px + tx * s, py + ty * s, ag

def sc_gravity(t):                                            # T_GRAV - 1.0 -> S4 : the orbit lets go
    R = lerp(E_R, E_R + 30, seg(t, S2, S4))
    drift = 60 * ease(seg(t, T_GRAV, S4 + 1))
    arr = earth_layer(t, E_X + drift, E_Y + 40 * ease(seg(t, T_GRAV, S4 + 1)), R, 0.0)
    img = to_img(tone(bloom(arr, 0.3))); d = ImageDraw.Draw(img, "RGBA"); tag(d)
    k = ease_out(seg(t, T_GRAV - 1.0, T_GRAV - 0.6))
    fade = 1 - ease(seg(t, T_GRAV, T_GRAV + 0.5))
    # orbit diagram
    d.rounded_rectangle((70, 230, W - 70, 880), 26, fill=(0, 0, 0, int(150 * k)))
    if fade > 0:
        for i in range(0, 360, 6):
            d.arc((ORB_X - ORB_R, ORB_Y - ORB_R, ORB_X + ORB_R, ORB_Y + ORB_R), i, i + 3, fill=(255, 255, 255, int(150 * k * fade)), width=3)
        d.ellipse((ORB_X - 16, ORB_Y - 16, ORB_X + 16, ORB_Y + 16), outline=(255, 200, 120, int(255 * k * fade)), width=3)
        d.text((ORB_X, ORB_Y + 30), "no Sun", font=font(F_MONO, 24), fill=(255, 210, 150, int(255 * k * fade)), anchor="mt")
    ex, ey, ag = orbit_pos(t)
    if t >= T_GRAV:
        px, py, _ = orbit_pos(T_GRAV)
        d.line((px, py, ex, ey), fill=(255, 212, 0, 255), width=6)
        tx, ty = -math.sin(ag), -math.cos(ag)
        for j in range(8):                                     # dashed path ahead
            a = 40 + j * 46
            d.line((ex + tx * a, ey + ty * a, ex + tx * (a + 22), ey + ty * (a + 22)), fill=(255, 212, 0, 160), width=4)
    d.ellipse((ex - 20, ey - 20, ex + 20, ey + 20), fill=(90, 160, 255, int(255 * k)), outline=WHITE, width=3)
    d.text((ex + 30, ey + 4), "Earth", font=font(F_MONO, 26), fill=(255, 255, 255, int(255 * k)), anchor="lm", stroke_width=3, stroke_fill=BLACK)
    if t >= T_GRAV:
        pop(d, W / 2, 310, "GRAVITY: GONE", 92, t - T_GRAV, YELLOW, 9)
        d.text((W / 2, 830), "Earth coasts off in a straight line · ~30 km/s", font=font(F_MONO, 28), fill=WHITE, anchor="mm", stroke_width=4, stroke_fill=BLACK)
    else:
        d.text((W / 2, 310), "ORBIT", font=font(F_CAP, 70), fill=(255, 255, 255, int(255 * k)), anchor="mm", stroke_width=8, stroke_fill=BLACK)
    credit(d)
    return img

def sc_question(t):                                           # S4 -> 15 : pullback, the question, the loop
    k = ease(seg(t, S4, T_LOOP + 0.3))
    R = lerp(E_R + 30, 70, k ** 0.8)
    ex = lerp(E_X + 60, 540, k); ey = lerp(E_Y + 40, 1040, k)
    zoom = lerp(1.25, 1.0, k)
    st = stars(zoom)
    lon = -20 - 3.0 * t
    arr = earth.render(W, H, ex, ey, R, 12, lon, lon - 1.5 * t, sun=(0.2, 0.1, -0.97), stars=st, night_gain=3.2, ambient=0.03)
    arr = st + (arr - st) * 0.8
    if t >= T_LOOP:                                            # the Sun re-ignites: seamless loop into frame 0
        q = seg(t, T_LOOP, DUR)
        arr = st + (arr - st) * (1 - ease(q))
        arr = draw_sun(arr, SUN_X, SUN_Y, max(1, sun_R(0) * ease_in(q) ** 0.9), t - DUR, bright=lerp(2.5, 1.0, q), corona=lerp(2.5, 1.0, q))
    arr = bloom(arr, lerp(0.35, 0.45, seg(t, T_LOOP, DUR)))
    img = to_img(tone(arr)); d = ImageDraw.Draw(img, "RGBA")
    tag(d)
    if t < T_LOOP + 0.35:
        a = int(255 * (1 - seg(t, T_LOOP, T_LOOP + 0.35)))
        k2 = ease_back(seg(t, ws(3, 0), ws(3, 0) + 0.25))
        if k2 > 0:
            d.text((W / 2, 380), "WOULD WE", font=font(F_CAP, 130 * k2), fill=(255, 255, 255, a), anchor="mm", stroke_width=11, stroke_fill=BLACK)
            s = 1 + 0.3 * max(0, 1 - (t - ws(3, 2)) / 0.14) if t >= ws(3, 2) else 1
            d.text((W / 2, 520), "SURVIVE?", font=font(F_CAP, 150 * k2 * s), fill=(255, 212, 0, a), anchor="mm", stroke_width=12, stroke_fill=BLACK)
        if t >= 12.9:
            d.text((W / 2, 640), "hypothetical · the Sun can't actually vanish", font=font(F_MONO, 28), fill=(210, 210, 210, a), anchor="mm", stroke_width=4, stroke_fill=BLACK)
        credit(d)
    if t >= DUR - 0.12:
        img = Image.blend(img, Image.new("RGB", (W, H), (255, 246, 230)), 0.0)
    return img

SCENES = [(0, S2, sc_hook), (S2, T_GRAV - 1.0, sc_delay), (T_GRAV - 1.0, S4, sc_gravity), (S4, DUR + 1, sc_question)]

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1 - 0.35 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) ** 1.6).clip(0.45, 1)[..., None]
GR = np.random.default_rng(3)
GRAIN = [GR.normal(0, 3.5, (H // 2, W // 2, 1)).astype(np.float32).repeat(2, 0).repeat(2, 1) for _ in range(4)]

def frame(fi):
    t = fi / FPS
    for a, b, fn in SCENES:
        if a <= t < b:
            img = fn(t); break
    arr = np.asarray(img.convert("RGB"), np.float32) * VIG + GRAIN[fi % 4]
    img = Image.fromarray(arr.clip(0, 255).astype(np.uint8))
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
        for i, b in enumerate(pool.imap(frame, range(NF), chunksize=2)):
            p.stdin.write(b)
            if i % 75 == 0: print("frame", i, "/", NF, flush=True)
    p.stdin.close(); p.wait()

# ------------------------------------------------------------------ audio
def drone(n, f=41.2):
    tt = np.arange(n) / SR
    return osc(f, n, "sin") * 0.5 + lp(osc(f * 2 * (1 + 0.002 * np.sin(2 * np.pi * 0.3 * tt)), n), 300) * 0.25

def plasma(dur):
    """Sun roar: rumbling low noise with slow swells."""
    n = int(dur * SR); tt = np.arange(n) / SR; x = arng.normal(0, 1, n)
    g = 0.7 + 0.3 * np.sin(2 * np.pi * 0.7 * tt) * np.sin(2 * np.pi * 1.9 * tt + 1)
    return (lp(x, 220) * 2.2 + bp(x, 300, 1200) * 0.35) * g

def pad(n, chords):
    out = np.zeros(n)
    for ci, (t0, notes) in enumerate(chords):
        t1 = chords[ci + 1][0] if ci + 1 < len(chords) else DUR
        i0, i1 = int(t0 * SR), min(n, int(t1 * SR) + int(0.5 * SR)); m = i1 - i0
        sg = np.zeros(m)
        for f in notes:
            for det in (-0.12, 0.0, 0.11): sg += osc(f * 2 ** (det / 12), m)
        e = np.minimum(1, np.arange(m) / (0.5 * SR)) * np.minimum(1, (m - np.arange(m)) / (0.5 * SR))
        out[i0:i1] += sg * e / 12
    return lp(out, 1100) * 0.7 + lp(out, 380) * 0.6

def render_audio(out):
    n = int(DUR * SR); tt = np.arange(n) / SR
    mus = pad(n, [(0, [82.41, 123.47, 196.0]), (S2, [77.78, 116.54, 185.0, 155.56]), (T_DARK, [65.41, 98.0, 155.56]),
                  (S4, [73.42, 110.0, 174.61, 146.83]), (T_LOOP, [82.41, 123.47, 196.0])])
    mus += drone(n)
    lvl = np.interp(tt, [0, T_GONE - 0.02, T_GONE + 0.02, T_GONE + 0.9, S2, T_DARK - 0.05, T_DARK + 0.05, T_DARK + 0.9, S4, DUR],
                    [0.8, 0.9, 0.0, 0.0, 0.75, 1.0, 0.0, 0.7, 0.85, 1.0])
    mus *= lvl
    hb = np.zeros(n); t = S2 + 0.1                             # heartbeat pulse under the countdown, speeding up
    while t < T_DARK - 0.2:
        place(hb, boom(0.4, 70, 40, 0.1), t, 0.6); place(hb, boom(0.35, 60, 38, 0.09), t + 0.2, 0.35)
        t += lerp(0.85, 0.5, seg(t, S2, T_DARK))
    t = T_DARK + 1.0
    while t < S4 + 2.4:
        place(hb, boom(0.4, 60, 36, 0.12), t, 0.4); place(hb, boom(0.35, 55, 34, 0.1), t + 0.22, 0.25); t += 0.95
    mus += hb
    fx = np.zeros(n)
    place(fx, plasma(T_GONE + 0.05) * np.minimum(1, np.arange(int((T_GONE + 0.05) * SR)) / (0.08 * SR)), 0.0, 0.55)
    place(fx, whoosh(0.5), 0.0, 0.35)
    r = riser(0.6, 120); place(fx, r[::-1][::-1] * np.linspace(0.3, 1, len(r)), T_GONE - 0.6, 0.7)   # suction into the collapse
    place(fx, reverb(boom(3.2, 120, 22, 1.1), 3.5, 0.45), T_GONE, 1.3)                          # the vanish
    place(fx, crack(0.8), T_GONE, 0.8)
    place(fx, reverb(osc(55 * np.exp(-np.arange(int(1.6 * SR)) / SR / 0.5) + 26, int(1.6 * SR), "sin") * envx(int(1.6 * SR), 0.6), 2.0, 0.3), T_GONE + 0.05, 0.9)
    ring = osc(3150, int(1.4 * SR), "sin") * envx(int(1.4 * SR), 0.6) * np.minimum(1, np.arange(int(1.4 * SR)) / (0.1 * SR))
    place(fx, ring, T_GONE + 0.15, 0.05)                                                         # stunned ear-ring
    place(fx, whoosh(0.6), S2 - 0.25, 0.4)
    k = 0; t = S2 + 0.25
    while t < T_DARK - 0.1:                                                                      # countdown clicks, accelerating
        place(fx, tick(1500 if k % 4 == 0 else 1150), t, 0.3); k += 1
        t += 0.12 if t < T_8MIN else 0.32
    place(fx, reverb(boom(1.6, 90, 34, 0.45)), T_8MIN, 0.7)                             # "8 MINUTES LATER..."
    place(fx, riser(T_DARK - S2 - 1.0, 70), S2 + 1.0, 0.35)
    place(fx, reverb(boom(3.0, 110, 22, 1.0), 3.5, 0.5), T_DARK, 1.2); place(fx, crack(0.5), T_DARK, 0.5)   # darkness
    place(fx, reverb(boom(2.0, 80, 26, 0.7), 3.0, 0.4), T_GRAV, 0.9); place(fx, whoosh(0.9), T_GRAV - 0.1, 0.5)  # orbit lets go
    place(fx, whoosh(1.3), S4 - 0.2, 0.45)                                                       # pullback
    place(fx, reverb(boom(1.6, 90, 34, 0.5), 3.0, 0.45), ws(3, 2), 0.75)                         # "survive?"
    place(fx, riser(DUR - T_LOOP + 0.1, 90), T_LOOP - 0.1, 0.6)                                  # into the loop
    vo = np.zeros(n)
    for l in TIM:
        s, _ = sf.read(l["file"]); place(vo, s, l["start"])
    vo = lp(hp(vo, 85), 13000); vo = vo / (np.abs(vo).max() + 1e-9) * 0.9
    env = lp(np.abs(vo), 7); env /= env.max() + 1e-9
    duck = 1 - 0.6 * np.clip(env * 3, 0, 1)
    mix = vo + mus * 0.13 * duck + fx * 0.36 * (0.5 + 0.5 * duck)
    mix = np.tanh(mix * 1.05) * 0.95
    sf.write(out, np.stack([mix, mix], 1).astype(np.float32), SR, subtype="FLOAT")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        render_video(None, [float(x) for x in sys.argv[2:]] or [0.0, 0.4, 1.2, 1.75, 1.95, 2.4, 3.3, 4.5, 6.0, 7.2, 7.95,
                                                               8.4, 9.0, 9.9, 10.8, 11.7, 12.6, 13.6, 14.4, 14.9])
    elif len(sys.argv) > 1 and sys.argv[1] == "audio":
        render_audio("mix.wav"); print("audio done")
    else:
        render_audio("mix.wav"); print("audio done", flush=True)
        render_video("video.mp4"); print("video done", flush=True)
