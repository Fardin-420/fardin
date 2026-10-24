"""Shared graphics for SPACE SECRETS EP01 (YouTube, 1920x1080): fonts, skies, landscape, city, globe helpers, labels."""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

import earth, moonr

W, H = 1920, 1080
W2, H2 = 960, 540

def clamp(v, a, b): return max(a, min(b, v))
def seg(t, a, b): return clamp((t - a) / (b - a), 0.0, 1.0) if b > a else float(t >= a)
def ease(x): x = clamp(x, 0, 1); return x * x * (3 - 2 * x)
def ease_out(x): x = clamp(x, 0, 1); return 1 - (1 - x) ** 3
def ease_in(x): x = clamp(x, 0, 1); return x ** 3
def lerp(a, b, k): return a + (b - a) * k

FD = "/usr/share/fonts/opentype/inter/"
F_TITLE = FD + "InterDisplay-ExtraLight.otf"
F_LIGHT = FD + "InterDisplay-Light.otf"
F_REG = FD + "InterDisplay-Regular.otf"
F_MED = FD + "InterDisplay-Medium.otf"
F_SEMI = FD + "InterDisplay-SemiBold.otf"
F_BOLD = FD + "InterDisplay-Bold.otf"
F_BLACK = FD + "InterDisplay-Black.otf"
F_MONO = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf"
_F = {}
def font(p, s):
    k = (p, int(s))
    if k not in _F: _F[k] = ImageFont.truetype(p, max(1, int(s)))
    return _F[k]

WHITE, BLACK = (255, 255, 255), (0, 0, 0)
GOLD = (242, 200, 110); ICE = (170, 215, 255); SOFT = (205, 210, 220); RED = (235, 90, 70); TEAL = (110, 220, 210)

def spaced(d, xy, txt, f, fill, anchor="lm", track=0.12):
    """Letter-spaced text (documentary titles)."""
    x, y = xy
    widths = [f.getlength(c) for c in txt]
    tw = sum(widths) + track * f.size * (len(txt) - 1)
    if anchor[0] == "m": x -= tw / 2
    elif anchor[0] == "r": x -= tw
    for c, w in zip(txt, widths):
        d.text((x, y), c, font=f, fill=fill, anchor="l" + anchor[1])
        x += w + track * f.size
    return tw

# ------------------------------------------------------------------ cached backgrounds
_C = {}
def cache(key, fn):
    if key not in _C: _C[key] = fn()
    return _C[key]

def _stars(w, h, seed, n, gain=1.0):
    rng = np.random.default_rng(seed)
    a = np.zeros((h, w, 3), np.float32) + np.array([3, 5, 11], np.float32)
    ys = rng.integers(0, h, n); xs = rng.integers(0, w, n)
    b = (rng.pareto(2.4, n) * 55 + 22) * gain
    col = np.stack([b, b * rng.uniform(0.9, 1.0, n), b * rng.uniform(0.95, 1.15, n)], -1)
    np.add.at(a, (ys, xs), col)
    big = b > 90
    for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0)):
        np.add.at(a, (np.clip(ys[big] + dy, 0, h - 1), np.clip(xs[big] + dx, 0, w - 1)), col[big] * 0.3)
    return np.clip(a, 0, 255)

def starfield():
    return cache("stars", lambda: _stars(W, H, 21, 6500))

def stars_half():
    return cache("stars2", lambda: _stars(W2, H2, 22, 2200, 0.9))

def milky_way():
    """Full-res night sky with a bright Milky Way band and dust lanes, for the moonless sky."""
    def make():
        rng = np.random.default_rng(77)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        # band from lower-left to upper-right
        u = (xx / W - 0.5) * 0.9 + (yy / H - 0.5) * 0.45
        v = (yy / H - 0.5) * 0.9 - (xx / W - 0.5) * 0.42
        def nz(sig, shape=(H // 2, W // 2)):
            a = ndimage.gaussian_filter(rng.normal(0, 1, shape), sig)
            a = np.asarray(Image.fromarray(((a / a.std() * 0.25 + 0.5).clip(0, 1) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32) / 255
            return a
        n1, n2, n3 = nz(28), nz(9), nz(3.5)
        band = np.exp(-((v + 0.05 * np.sin(u * 6)) / 0.11) ** 2)
        core = np.exp(-((u + 0.12) / 0.22) ** 2) * 0.8 + 0.4
        glow = band * core * np.clip(0.6 + 1.2 * (n1 - 0.5) + 0.7 * (n2 - 0.5) + 0.3 * (n3 - 0.5), 0, None) * 0.75
        dust = np.clip((n2 - 0.5) * 2.2 + (n1 - 0.5) * 1.5, 0, 1) ** 1.5 * np.exp(-((v + 0.01) / 0.05) ** 2)
        glow = np.clip(glow * (1 - 0.85 * dust), 0, None)
        sky = np.zeros((H, W, 3), np.float32)
        sky += glow[..., None] * np.array([150, 140, 150], np.float32)
        sky += (glow ** 2)[..., None] * np.array([90, 70, 40], np.float32)
        sky += np.array([4, 7, 16], np.float32)
        n = 22000
        ys = rng.integers(0, H, n); xs = rng.integers(0, W, n)
        keep = rng.random(n) < 0.25 + 0.75 * np.clip(band[ys, xs] * 1.5, 0, 1)
        ys, xs = ys[keep], xs[keep]
        b = rng.pareto(2.6, len(xs)) * 45 + 25
        col = np.stack([b, b * rng.uniform(0.92, 1.0, len(b)), b * rng.uniform(0.95, 1.12, len(b))], -1)
        np.add.at(sky, (ys, xs), col)
        for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            np.add.at(sky, (np.clip(ys + dy, 0, H - 1), np.clip(xs + dx, 0, W - 1)), col * 0.25 * (b[:, None] > 70))
        return np.clip(sky, 0, 255)
    return cache("milky", make)

def night_sky(moonlit=1.0, stars=1.0, milky=0.0, warm=0.0):
    """Gradient night sky. moonlit raises the blue sky glow and washes out faint stars."""
    def grad():
        y = np.linspace(0, 1, H)[:, None, None]
        top = np.array([4, 8, 20], np.float32); hor = np.array([18, 30, 58], np.float32)
        return top + (hor - top) * y ** 1.6
    g = cache("skygrad", grad)
    sky = g * (0.55 + 0.6 * moonlit) + np.array([6, 11, 22], np.float32) * moonlit
    if warm > 0:
        y = np.linspace(0, 1, H)[:, None, None]
        sky = sky + warm * np.array([110, 60, 30], np.float32) * y ** 3
    st = starfield() * stars * (1 - 0.75 * moonlit)
    sky = sky + st
    if milky > 0: sky = sky + milky_way() * milky
    return sky

# ------------------------------------------------------------------ landscape (rural night): layered ridges + trees
def _ridge(rng, n, base, amp, rough):
    x = np.arange(n, dtype=np.float32)
    y = np.zeros(n, np.float32)
    for k, a in ((180, 1.0), (70, 0.45), (25, 0.18), (8, 0.06 * rough)):
        ph = rng.uniform(0, 100)
        g = ndimage.gaussian_filter1d(rng.normal(0, 1, n), k)
        y += a * g / (np.abs(g).max() + 1e-6)
    return base - amp * (y - y.min()) / (y.max() - y.min() + 1e-6)

def landscape_layers():
    def make():
        rng = np.random.default_rng(5)
        n = int(W * 1.25)
        r1 = _ridge(rng, n, 760, 260, 1.0)    # far mountains
        r2 = _ridge(rng, n, 850, 190, 1.4)    # mid hills
        r3 = _ridge(rng, n, 960, 120, 2.0)    # near ground
        trees = np.zeros(n, np.float32)
        x = 0
        while x < n:
            w = rng.integers(16, 40); h = rng.uniform(40, 120) * (rng.random() < 0.8)
            xs = np.arange(max(0, x), min(n, x + w))
            trees[xs] = np.maximum(trees[xs], h * (1 - np.abs((xs - x - w / 2) / (w / 2)) ** 1.3).clip(0))
            x += int(rng.integers(8, 30))
        return r1, r2, r3, trees
    return cache("land", make)

def landscape(sky, moonlight=1.0, shift=0.0, dawn=0.0, lake=True):
    """Composite ridges over a sky array (H,W,3 float). moonlight: 0 (moonless) .. 1 (full Moon)."""
    r1, r2, r3, trees = landscape_layers()
    out = sky.copy()
    skyrow = np.median(sky[:, ::16], axis=1)
    yy = np.arange(H)[:, None]
    lit = np.array([120, 132, 155], np.float32) * moonlight + np.array([210, 140, 90], np.float32) * dawn
    for k, (r, par, col, amb) in enumerate(((r1, 0.25, (0.30, 0.34, 0.42), 9), (r2, 0.5, (0.22, 0.25, 0.30), 6),
                                            (r3 + 0 * trees, 0.85, (0.14, 0.16, 0.19), 4))):
        off = int(shift * par * 200)
        prof = np.roll(r, -off)[:W]
        if k == 2: prof = prof - np.roll(trees, -off)[:W] * 0.9
        slope = ndimage.gaussian_filter1d(np.gradient(prof), 30)
        shade = np.clip(0.62 - slope * 0.5, 0.4, 0.85)              # Moon from the left: west-facing slopes brighter
        mask = yy >= prof[None, :]
        depth = np.clip((yy - ndimage.gaussian_filter1d(prof, 30)[None, :]) / 300, 0, 1)
        c = (amb + lit[None, None, :] * np.array(col, np.float32) * shade[None, :, None] * (1 - 0.6 * depth[..., None]))
        haze = skyrow[np.clip(prof.astype(int), 0, H - 1)][None] * (0.55 - 0.18 * k)
        c = c + haze * (1 - depth[..., None])
        out = np.where(mask[..., None], c, out)
    return out

# ------------------------------------------------------------------ city skyline
def city_layer():
    def make():
        rng = np.random.default_rng(11)
        Wc = int(W * 1.15); Hc = 520
        sil = np.zeros((Hc, Wc), np.float32); win = np.zeros((Hc, Wc, 3), np.float32); rim = np.zeros((Hc, Wc), np.float32)
        for layer, (hmin, hmax, wmin, wmax, dens) in enumerate(((140, 330, 60, 150, 0.25), (80, 260, 50, 120, 0.45), (40, 170, 40, 110, 0.6))):
            x = -50
            while x < Wc:
                w = int(rng.integers(wmin, wmax)); h = int(rng.uniform(hmin, hmax) * (1.6 if rng.random() < 0.08 else 1))
                h = min(h, Hc - 10); x0, x1 = max(0, x), min(Wc, x + w); y0 = Hc - h
                sil[y0:, x0:x1] = layer + 1
                rim[y0:y0 + 3, x0:x1] = 1
                if rng.random() < 0.3 and w > 60:                       # antenna / setback
                    ax = x0 + w // 2; sil[max(0, y0 - 40):y0, ax:ax + 3] = layer + 1
                for wy in range(y0 + 12, Hc - 8, 14):
                    for wx in range(x0 + 8, x1 - 8, 12):
                        if rng.random() < dens * 0.55:
                            c = np.array([255, 205, 140]) if rng.random() < 0.8 else np.array([190, 220, 255])
                            win[wy:wy + 6, wx:wx + 5] = c * rng.uniform(0.35, 0.9)
                x += w + int(rng.integers(-10, 20))
        return sil, win, rim
    return cache("city", make)

def city(sky, moonlight=1.0, shift=0.0, scale=1.0):
    sil, win, rim = city_layer()
    Hc, Wc = sil.shape
    off = int((Wc - W) / 2 + shift)
    s = sil[:, off:off + W]; wn = win[:, off:off + W]; rm = rim[:, off:off + W]
    out = sky.copy()
    y0 = H - Hc
    base = np.where(s[..., None] == 1, np.array([14, 17, 26], np.float32),
                    np.where(s[..., None] == 2, np.array([9, 11, 17], np.float32), np.array([5, 6, 10], np.float32)))
    body = base + wn + rm[..., None] * np.array([90, 100, 120], np.float32) * moonlight
    region = out[y0:]
    out[y0:] = np.where(s[..., None] > 0, body, region + np.array([30, 22, 14], np.float32) * np.linspace(0, 1, Hc)[:, None, None] ** 4)
    return out

# ------------------------------------------------------------------ globe helpers (half-res render, upscaled)
def up(arr):
    return np.asarray(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32)

def globe(cx, cy, R, lat0=12, lon=-30.0, lon_cloud=None, sun=(-0.55, 0.28, 0.79), base=None, night_gain=1.4, ambient=0.0, half=True):
    if half:
        b = stars_half() if base is None else base
        a = earth.render(W2, H2, cx / 2, cy / 2, R / 2, lat0, lon, lon if lon_cloud is None else lon_cloud, sun=sun, stars=b,
                         night_gain=night_gain, ambient=ambient)
        return up(a)
    b = starfield() if base is None else base
    return earth.render(W, H, cx, cy, R, lat0, lon, lon if lon_cloud is None else lon_cloud, sun=sun, stars=b, night_gain=night_gain, ambient=ambient)

def moon_full(arr, cx, cy, R, light=(0, 0, 1), halo=0.0, gain=1.0, tint=(1.0, 0.98, 0.94), earthshine=0.0):
    return moonr.render(W, H, cx, cy, R, light=light, base=arr, halo=halo, gain=gain, tint=tint, earthshine=earthshine)

# ------------------------------------------------------------------ grading + labels
def tone(arr):
    a = np.clip(arr, 0, None) / 255.0
    return np.clip(255 * (1 - np.exp(-a * 1.2)) / (1 - math.exp(-1.2)), 0, 255)

def bloom(arr, amt=0.35, thr=170, rad=30):
    small = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
    hi = np.clip(np.asarray(small, np.float32) - thr, 0, None) * 1.8
    bl = np.asarray(Image.fromarray(np.clip(hi, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(rad / 4)).resize((W, H), Image.BILINEAR), np.float32)
    return arr + bl * amt

def to_img(arr): return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

def finish(arr, b=0.3):
    return to_img(tone(bloom(arr, b)))

KINDS = {"sim": ("SIMULATION", ICE), "hyp": ("HYPOTHETICAL SIMULATION", GOLD), "diag": ("DIAGRAM", TEAL),
         "illus": ("ILLUSTRATION", SOFT), "scen": ("HYPOTHETICAL SCENARIO", GOLD), "real": ("TODAY'S REAL SYSTEM", TEAL),
         "schem": ("SCHEMATIC · NOT TO SCALE", TEAL)}
def tag(d, kind, extra=""):
    txt, col = KINDS[kind]
    if extra: txt += "  ·  " + extra
    f = font(F_MONO, 17)
    d.ellipse((60, 54, 70, 64), fill=col)
    d.text((80, 59), txt, font=f, fill=(215, 220, 230, 220), anchor="lm")

def label(d, x, y, title, body=None, color=WHITE, a=255, anchor="lm", size=30):
    d.text((x, y), title, font=font(F_SEMI, size), fill=color + (a,), anchor=anchor)
    if body:
        d.text((x, y + size * 1.15), body, font=font(F_LIGHT, size * 0.72), fill=(215, 220, 230, a), anchor=anchor)

def factcard(d, x, y, big, small, k, color=GOLD, w=None):
    if k <= 0: return
    a = int(255 * ease(k)); dy = 14 * (1 - ease_out(k))
    fb, fs = font(F_SEMI, 46), font(F_LIGHT, 24)
    w = w or max(fb.getlength(big), fs.getlength(small)) + 56
    d.rounded_rectangle((x, y + dy, x + w, y + 112 + dy), 10, fill=(6, 10, 20, int(170 * ease(k))))
    d.line((x, y + dy, x, y + 112 + dy), fill=color + (a,), width=4)
    d.text((x + 28, y + 42 + dy), big, font=fb, fill=color + (a,), anchor="lm")
    d.text((x + 28, y + 86 + dy), small, font=fs, fill=(220, 225, 235, a), anchor="lm")

def headline(d, x, y, txt, k, size=64, color=WHITE, anchor="lm", sub=None):
    if k <= 0: return
    a = int(255 * ease(k)); dy = 10 * (1 - ease_out(k))
    d.text((x, y + dy), txt, font=font(F_SEMI, size), fill=color + (a,), anchor=anchor)
    if sub: d.text((x, y + dy + size * 0.95), sub, font=font(F_LIGHT, size * 0.42), fill=(215, 220, 230, a), anchor=anchor)

def arrow(d, x0, y0, x1, y1, color, w=5, head=18):
    d.line((x0, y0, x1, y1), fill=color, width=w)
    a = math.atan2(y1 - y0, x1 - x0)
    d.polygon([(x1, y1), (x1 - head * math.cos(a - 0.45), y1 - head * math.sin(a - 0.45)), (x1 - head * math.cos(a + 0.45), y1 - head * math.sin(a + 0.45))], fill=color)

def dashed_circle(d, cx, cy, rx, ry, color, w=2, step=6, on=3):
    for i in range(0, 360, step):
        d.arc((cx - rx, cy - ry, cx + rx, cy + ry), i, i + on, fill=color, width=w)

def push(img, k, cx=W / 2, cy=H / 2):
    """Camera push: scale image about (cx,cy) by k >= 1."""
    if k <= 1.0001: return img
    w, h = W / k, H / k
    x0 = clamp(cx - w / 2, 0, W - w); y0 = clamp(cy - h / 2, 0, H - h)
    return img.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + w, y0 + h))
