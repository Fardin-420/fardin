"""Procedural star (granulation, limb darkening, spots, prominences, corona), shared with WARM-UP 01."""
import math
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

W, H = 1080, 1920
def lerp(a, b, k): return a + (b - a) * k

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
    cor = cor * np.clip((3.15 - r) / 0.9, 0, 1) ** 2               # fade to zero inside the render box
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

