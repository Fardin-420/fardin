#!/usr/bin/env python3
# SPACE SECRETS — "The Moon Is Rusting": procedural cinematic toolkit (macro regolith, heightfield terrain, Moon with
# hematite overlay, Earth, oxygen-ion particles). All imagery is original CGI; scientific visualizations are labelled.
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

import earth, moonr, star

W, H, FPS = 1080, 1920, 30
star.W, star.H = W, H
earth.TEX = "tex/"

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

# ------------------------------------------------------------------ grading (shared by every shot)
def tone(arr, exp=1.25):
    a = np.clip(arr, 0, None) / 255.0
    return np.clip(255 * (1 - np.exp(-a * exp)) / (1 - math.exp(-exp)), 0, 255)

def glow(arr, amt=0.4, thr=170, rad=36):
    small = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
    hi = np.clip(np.asarray(small, np.float32) - thr, 0, None) * 1.8
    bl = np.asarray(Image.fromarray(np.clip(hi, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(rad / 4)).resize((W, H), Image.BILINEAR), np.float32)
    return arr + bl * amt

def finish(arr, g=0.4, exp=1.25):
    return Image.fromarray(np.clip(tone(glow(arr, g), exp), 0, 255).astype(np.uint8))

def stars(seed=7, n=2600):
    def make():
        rng = np.random.default_rng(seed)
        a = np.zeros((H, W, 3), np.float32) + np.array([2, 2, 4], np.float32)
        ys = rng.integers(0, H, n); xs = rng.integers(0, W, n); b = rng.pareto(2.6, n) * 32 + 10
        np.add.at(a, (ys, xs), np.stack([b, b * 0.97, b * 1.05], -1))
        return np.clip(a, 0, 255)
    return cache(("stars", seed), make)

# ------------------------------------------------------------------ 1. macro regolith (extreme close-up, conceptual rust transformation)
GREY = [(142, 139, 134), (116, 113, 110), (166, 162, 155), (100, 98, 95), (190, 186, 178), (130, 125, 112), (88, 86, 84), (152, 146, 130)]
RUST = [(112, 42, 32), (128, 52, 38), (94, 38, 32), (142, 62, 42), (100, 66, 60), (120, 46, 36)]

def make_macro(seed=11, Wm=1620, Hm=2880, patch=(0.5, 0.5), pr=0.15):
    """Return base RGB, rusted RGB and per-pixel activation delay (0..1, NaN = never) at Wm x Hm."""
    rng = np.random.default_rng(seed)
    S = 2
    Wb, Hb = Wm * S, Hm * S
    base = Image.new("RGB", (Wb, Hb), (44, 43, 42)); rust = base.copy()
    shad = Image.new("L", (Wb, Hb), 0)
    act = Image.new("F", (Wb, Hb), -1.0)
    db, dr, ds, da = ImageDraw.Draw(base), ImageDraw.Draw(rust), ImageDraw.Draw(shad), ImageDraw.Draw(act)
    grains = []
    for _ in range(16000):                                                        # power-law grain sizes, big first
        r = 8 * (1 - rng.random()) ** -0.5
        if r > 140: continue
        grains.append((rng.uniform(0, Wb), rng.uniform(0, Hb), r * S))
    grains.sort(key=lambda g: -g[2])
    px, py = patch[0] * Wb, patch[1] * Hb
    for x, y, r in grains:
        n = int(rng.integers(6, 10))                                               # angular shard: random convex polygon
        th = np.sort(rng.uniform(0, 2 * np.pi, n))
        rad = r * rng.uniform(0.72, 1.0, n)
        sq = rng.uniform(0.6, 1.0); rot = rng.uniform(0, np.pi)
        cx_, cy_ = rad * np.cos(th), rad * np.sin(th) * sq
        pts = np.stack([cx_ * np.cos(rot) - cy_ * np.sin(rot), cx_ * np.sin(rot) + cy_ * np.cos(rot)], 1)
        poly = lambda k, dx=0.0, dy=0.0: [(x + dx + p[0] * k, y + dy + p[1] * k) for p in pts]
        ds.polygon(poly(1.05, r * 0.28, r * 0.34), fill=200)
        g = GREY[rng.integers(len(GREY))]; glass = rng.random() < 0.07
        if glass: g = (36, 36, 40)
        d = math.hypot((x - px) / Wb, (y - py) / Hb) / pr
        rusty = d < 1 and rng.random() < 0.7 * (1.0 - 0.7 * d) and r < 70
        rc = RUST[rng.integers(len(RUST))]
        apex = (x - r * 0.12 + rng.normal(0, r * 0.08), y - r * 0.14 + rng.normal(0, r * 0.08))
        for i in range(n):                                                       # facets lit from the upper left
            p, q = pts[i], pts[(i + 1) % n]
            mid = math.atan2((p[1] + q[1]) / 2, (p[0] + q[0]) / 2)
            f = 0.5 + 0.42 * math.cos(mid - math.radians(225)) + rng.normal(0, 0.05)
            tri = [apex, (x + p[0], y + p[1]), (x + q[0], y + q[1])]
            db.polygon(tri, fill=tuple(int(clamp(c * f, 0, 255)) for c in g))
            dr.polygon(tri, fill=tuple(int(clamp(c * f, 0, 255)) for c in (rc if rusty else g)))
        if glass or rng.random() < 0.15:
            sx, sy = x - r * 0.35, y - r * 0.38; sr = max(2, r * (0.12 if glass else 0.06))
            db.ellipse((sx - sr, sy - sr, sx + sr, sy + sr), fill=(235, 235, 240))
            dr.ellipse((sx - sr, sy - sr, sx + sr, sy + sr), fill=(235, 235, 240) if not rusty else (230, 170, 140))
        da.polygon(poly(1.0), fill=float(clamp(0.15 + 0.7 * d + rng.uniform(0, 0.15), 0, 1)) if rusty else -1.0)
    shad = shad.filter(ImageFilter.GaussianBlur(9 * S))
    sh = 1 - 0.55 * np.asarray(shad, np.float32)[..., None] / 255
    fine = (ndimage.gaussian_filter(rng.normal(0, 1, (Hb, Wb)).astype(np.float32), 1.2) * 10
            + ndimage.gaussian_filter(rng.normal(0, 1, (Hb, Wb)).astype(np.float32), 5) * 9)[..., None]
    B = np.asarray(base, np.float32) * sh + fine; R_ = np.asarray(rust, np.float32) * sh + fine
    out = []
    for a in (B, R_):
        out.append(np.asarray(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((Wm, Hm), Image.LANCZOS), np.float32))
    A = np.asarray(act.resize((Wm, Hm), Image.NEAREST), np.float32)
    return out[0], out[1], A

def macro_frame(M, k_rust, zoom=1.0, cx=0.5, cy=0.52, dof=True):
    """Crop the macro plate at 'zoom' (1 = full frame width covers 1080/1620 of the plate)."""
    B, R_, A = M
    on = np.where(A < 0, 0.0, np.clip((k_rust - A) / 0.18, 0, 1))[..., None]
    img = B * (1 - on) + R_ * on
    hm, wm = img.shape[:2]
    cw = W / zoom * wm / 1620; ch = cw * H / W
    x0, y0 = cx * wm - cw / 2, cy * hm - ch / 2
    pil = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).transform((W, H), Image.EXTENT, (x0, y0, x0 + cw, y0 + ch), Image.BILINEAR)
    a = np.asarray(pil, np.float32)
    if dof:                                                                       # shallow depth of field: soft top/bottom
        bl = np.asarray(pil.filter(ImageFilter.GaussianBlur(9)), np.float32)
        yy = np.abs(np.linspace(-1, 1, H))[:, None, None]
        m = np.clip((yy - 0.45) / 0.45, 0, 1)
        a = a * (1 - m) + bl * m
    return a

# ------------------------------------------------------------------ 2. heightfield terrain (cratered regolith, hard sun, no air)
N = 2048
def terrain():
    def make():
        rng = np.random.default_rng(1969)
        def noise(sig, amp):
            a = ndimage.gaussian_filter(rng.normal(0, 1, (N, N)).astype(np.float32), sig, mode="wrap"); return a / (a.std() + 1e-6) * amp
        h = noise(220, 26) + noise(70, 9) + noise(18, 1.6) + noise(4, 0.35)
        alb = 0.15 + 0.012 * noise(60, 1) + 0.008 * noise(6, 1)
        yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
        def crater(cx, cy, r, depth, fresh):
            nonlocal h, alb
            b = int(r * 3.2) + 3
            y0, y1, x0, x1 = int(cy - b), int(cy + b), int(cx - b), int(cx + b)
            ys = np.arange(y0, y1) % N; xs = np.arange(x0, x1) % N
            Y, X = np.meshgrid(np.arange(y0, y1), np.arange(x0, x1), indexing="ij")
            d = np.hypot(X - cx, Y - cy) / r
            bowl = np.where(d < 1, (d ** 2 - 1) * depth, 0) + np.exp(-((d - 1) / 0.22) ** 2) * depth * 0.32 + np.where(d > 1, np.exp(-(d - 1) / 0.7) * depth * 0.08, 0)
            h[np.ix_(ys, xs)] += bowl
            if fresh: alb[np.ix_(ys, xs)] += fresh * np.exp(-np.clip(d - 0.8, 0, None) / 1.1) * (d > 0.6) * 0.06
        for _ in range(900):
            r = 4 * (1 - rng.random()) ** -0.62
            if r > 190: continue
            crater(rng.uniform(0, N), rng.uniform(0, N), r, r * rng.uniform(0.18, 0.3), rng.random() < 0.15)
        bould = np.zeros((N, N), np.float32)                                      # scattered boulders
        for _ in range(9000):
            x, y = rng.integers(0, N, 2); bould[y, x] = rng.uniform(0.6, 2.2)
        h += ndimage.gaussian_filter(bould, 1.1) * 6
        alb += ndimage.gaussian_filter(bould, 1.1) * 0.25
        return h.astype(np.float32), np.clip(alb, 0.06, 0.4).astype(np.float32)
    return cache("terrain", make)

def shaded(sun_el=9.0, gain=1.0):
    """Top-down shaded colour (sun from the -x side at sun_el degrees), with cast shadows."""
    def make():
        h, alb = terrain()
        gy, gx = np.gradient(h)
        L = np.array([math.cos(math.radians(sun_el)), 0.0, math.sin(math.radians(sun_el))])
        nz = 1 / np.sqrt(gx ** 2 + gy ** 2 + 1)
        ndl = np.clip((-gx * L[0] + 0 * gy + L[2]) * nz, 0, None)
        t = math.tan(math.radians(sun_el)); xs = np.arange(N, dtype=np.float32)[None, :]
        hh = np.concatenate([h, h], 1); xx = np.arange(2 * N, dtype=np.float32)[None, :]
        m = np.maximum.accumulate(hh + xx * t, axis=1)[:, N:]
        lit = (m <= h + (xs + N) * t + 0.01).astype(np.float32)
        lit = ndimage.gaussian_filter(lit, 0.6)
        K = 70 / (0.15 * math.sin(math.radians(sun_el)))
        v = alb * (ndl * lit + 0.006) * K * gain
        col = v[..., None] * np.array([1.0, 0.985, 0.955], np.float32)
        return col.astype(np.float32)
    return cache(("shaded", sun_el, gain), make)

def mip(sun_el):
    return cache(("mip", sun_el), lambda: np.stack([ndimage.gaussian_filter(shaded(sun_el)[..., c], 2.5, mode="wrap") for c in range(3)], -1))

def detail():
    def make():
        rng = np.random.default_rng(5)
        a = ndimage.gaussian_filter(rng.normal(0, 1, (512, 512)).astype(np.float32), 0.8, mode="wrap")
        return a / a.std()
    return cache("detail", make)

def render_terrain(cx, cy, ch, yaw, horizon=0.30, fov=62, sun_el=9.0, Wr=720, Hr=1280, zmax=2200, S=900):
    """Low-angle terrain camera (voxel-space, front-to-back cover). Returns RGB float (Hr,Wr,3) and sky mask."""
    h, _ = terrain(); col = shaded(sun_el); colm = mip(sun_el); det = detail()
    f = (Wr / 2) / math.tan(math.radians(fov / 2))
    zs = np.geomspace(3.0, zmax, S).astype(np.float32)
    cols = (np.arange(Wr, dtype=np.float32) - Wr / 2) / f
    dx, dy = math.cos(yaw), math.sin(yaw); rx, ry = -dy, dx
    X = cx + zs[:, None] * (dx + cols[None, :] * rx); Y = cy + zs[:, None] * (dy + cols[None, :] * ry)
    coords = [Y.ravel() % N, X.ravel() % N]
    hs = ndimage.map_coordinates(h, coords, order=1, mode="wrap").reshape(S, Wr)
    hz = horizon * Hr
    yp = hz + (ch - hs) / zs[:, None] * f
    run = np.minimum.accumulate(yp, axis=0)
    c_near = np.stack([ndimage.map_coordinates(col[..., c], coords, order=1, mode="wrap").reshape(S, Wr) for c in range(3)], -1)
    c_far = np.stack([ndimage.map_coordinates(colm[..., c], coords, order=1, mode="wrap").reshape(S, Wr) for c in range(3)], -1)
    wfar = np.clip((zs - 60) / 300, 0, 1)[:, None, None]
    cc = c_near * (1 - wfar) + c_far * wfar
    dt = ndimage.map_coordinates(det, [(Y.ravel() * 3.5) % 512, (X.ravel() * 3.5) % 512], order=1, mode="wrap").reshape(S, Wr)
    cc = cc * (1 + 0.15 * dt * np.clip(1 - zs / 160, 0, 1)[:, None])[..., None]
    cc = np.concatenate([cc, np.zeros((1, Wr, 3), np.float32)], 0)
    ys = -np.arange(Hr, dtype=np.float32)
    idx = np.empty((Hr, Wr), np.int32)
    for c in range(Wr):
        idx[:, c] = np.searchsorted(-run[:, c], ys, side="left")
    img = cc[idx, np.arange(Wr)[None, :]]
    return img, (idx >= S)

def terrain_shot(cx, cy, ch, yaw, horizon=0.3, fov=62, sun_el=9.0, sky=None):
    img, skym = render_terrain(cx, cy, ch, yaw, horizon, fov, sun_el)
    up = np.asarray(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((W, H), Image.LANCZOS), np.float32)
    m = np.asarray(Image.fromarray((skym * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), np.float32)[..., None] / 255
    bg = stars() if sky is None else sky
    return up * (1 - m) + bg * m

# ------------------------------------------------------------------ 3. Moon globe
def _real_moon_tex():
    """Real lunar albedo (three.js moon_1024.jpg, NASA-derived) upsampled, plus pole-safe fine relief."""
    if moonr._T.get("real"): return moonr._T
    H_, W_ = moonr.H_, moonr.W_
    img = Image.open("tex/moon_1024.jpg").convert("L").resize((W_, H_), Image.BICUBIC)
    a = np.asarray(img, np.float32) / 255.0
    alb = 0.16 + a * 0.62
    rng = np.random.default_rng(4)
    lat = 90 - (np.arange(H_) + 0.5) / H_ * 180
    clat = np.clip(np.cos(np.radians(lat)), 0.05, 1)[:, None]
    # isotropic fine relief: noise blurred more in longitude near the poles so it does not pinch
    n = rng.normal(0, 1, (H_, W_)).astype(np.float32)
    rel = np.zeros_like(n)
    for i in range(H_):
        rel[i] = ndimage.gaussian_filter1d(n[i], 1.2 / clat[i, 0], mode="wrap")
    rel = ndimage.gaussian_filter1d(rel, 1.2, axis=0)
    hgt = ndimage.gaussian_filter(a, 1.0) * 1.0 + rel * 0.05
    gy, gx = np.gradient(hgt)
    moonr._T.update(alb=alb.astype(np.float32), gx=(gx * 6 * clat).astype(np.float32), gy=(gy * 6).astype(np.float32), real=True)
    return moonr._T
moonr.tex = _real_moon_tex
# hematite overlay (spectral signature map)
def hem_mask():
    def make():
        H_, W_ = moonr.H_, moonr.W_
        rng = np.random.default_rng(2020)
        lat = 90 - (np.arange(H_) + 0.5) / H_ * 180
        lon = (np.arange(W_) + 0.5) / W_ * 360 - 180
        LA, LO = np.meshgrid(lat, lon, indexing="ij")
        hi = np.clip((np.abs(LA) - 52) / 18, 0, 1)                                # high latitudes
        near = np.where(np.abs(((LO + 180) % 360) - 180) < 90, 1.0, 0.3)           # more on the nearside (lon 0 faces Earth)
        n = ndimage.gaussian_filter(rng.normal(0, 1, (H_, W_)).astype(np.float32), 2.2, mode="wrap")
        spots = np.clip((n / n.std() - 1.2) / 0.9, 0, 1)                           # patchy, small exposures
        return (hi * near * spots).astype(np.float32)
    return cache("hem", make)

def moon(base, cx, cy, R, light=(0.0, 0.0, 1.0), lon_c=0.0, lat0=0.0, gain=1.0, hem=0.0, hem_col=(215, 70, 40), earthshine=0.0):
    out = moonr.render(W, H, cx, cy, R, light=light, lon_c=lon_c, lat0=lat0, base=base, gain=gain, earthshine=earthshine)
    if hem <= 0: return out
    ext = R + 2
    x0, x1 = int(max(0, cx - ext)), int(min(W, cx + ext)); y0, y1 = int(max(0, cy - ext)), int(min(H, cy + ext))
    if x1 <= x0 or y1 <= y0: return out
    ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    nx = (xs - cx) / R; ny = (cy - ys) / R; r2 = nx * nx + ny * ny; m = r2 < 1
    nxm, nym = nx[m], ny[m]; nzm = np.sqrt(1 - r2[m])
    c0, s0 = math.cos(math.radians(lat0)), math.sin(math.radians(lat0))
    X = nxm; Y = nym * c0 + nzm * s0; Z = -nym * s0 + nzm * c0
    lat = np.degrees(np.arcsin(np.clip(Y, -1, 1))); lon = np.degrees(np.arctan2(X, Z)) + lon_c
    v = (90 - lat) / 180 * (moonr.H_ - 1); u = ((lon + 180) % 360) / 360 * moonr.W_
    hv = np.clip(ndimage.map_coordinates(hem_mask(), [v, u], order=1, mode="wrap") * hem, 0, 1)
    sub = out[y0:y1, x0:x1]
    lum = sub[m].mean(-1, keepdims=True)
    tgt = np.array(hem_col, np.float32) * (0.35 + 0.65 * np.clip(lum / 160, 0, 1.3))
    sub[m] = sub[m] * (1 - hv[:, None]) + tgt * hv[:, None]
    out[y0:y1, x0:x1] = sub
    return out

# ------------------------------------------------------------------ 4. Earth
def earth_disc(base, cx, cy, R, lon=-40.0, lat0=15.0, sun=(-0.6, 0.35, 0.72), night=1.4):
    return earth.render(W, H, cx, cy, R, lat0, lon, lon - 8, sun=sun, stars=base, night_gain=night)

def limb_glow(arr, cx, cy, R, sun=(-0.6, 0.35, 0.72), amt=1.0):
    """Thin blue atmosphere ring, brighter on the sunlit side (Earth only)."""
    x0, x1 = int(max(0, cx - R * 1.08)), int(min(W, cx + R * 1.08)); y0, y1 = int(max(0, cy - R * 1.08)), int(min(H, cy + R * 1.08))
    if x1 <= x0 or y1 <= y0: return arr
    ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    nx, ny = (xs - cx) / R, (cy - ys) / R; r = np.sqrt(nx * nx + ny * ny)
    sl = np.clip((nx * sun[0] + ny * sun[1]) / (r + 1e-6) * 0.9 + 0.35, 0, 1)
    ring = np.exp(-np.abs(r - 1.0) / 0.012) * (r > 0.985) * sl * amt
    arr[y0:y1, x0:x1] += ring[..., None] * np.array([90, 150, 255], np.float32)
    return arr

# ------------------------------------------------------------------ 5. particles (oxygen ions: a visualization of an invisible process)
O_COL = np.array([120, 255, 190], np.float32)

def particles(arr, paths, t, n=260, speed=0.35, size=2.2, col=O_COL, amt=1.0, seed=3, spread=14.0, life=None):
    """paths: list of (P0,P1,P2,P3) cubic Bezier control points. Additive glowing dots flowing along them."""
    rng = np.random.default_rng(seed)
    lay = Image.new("L", (W // 2, H // 2), 0); d = ImageDraw.Draw(lay)
    core = Image.new("L", (W // 2, H // 2), 0); dc = ImageDraw.Draw(core)
    ph = rng.random(n); pi = rng.integers(0, len(paths), n); off = rng.normal(0, 1, (n, 2)); br = rng.uniform(0.4, 1.0, n)
    for i in range(n):
        u = (ph[i] + t * speed) % 1.0
        if life is not None and u > life: continue
        P = np.array(paths[pi[i]], np.float32)
        b = (1 - u) ** 3 * P[0] + 3 * (1 - u) ** 2 * u * P[1] + 3 * (1 - u) * u ** 2 * P[2] + u ** 3 * P[3]
        b = b + off[i] * spread * math.sin(math.pi * u)
        fade = min(1, u / 0.08, (1 - u) / 0.12) * br[i]
        x, y = b[0] / 2, b[1] / 2; r = size / 2
        d.ellipse((x - r * 2.2, y - r * 2.2, x + r * 2.2, y + r * 2.2), fill=int(110 * fade))
        dc.ellipse((x - r * 0.7, y - r * 0.7, x + r * 0.7, y + r * 0.7), fill=int(255 * fade))
    g = np.asarray(lay.filter(ImageFilter.GaussianBlur(3)).resize((W, H), Image.BILINEAR), np.float32) / 255
    c = np.asarray(core.filter(ImageFilter.GaussianBlur(0.6)).resize((W, H), Image.BILINEAR), np.float32) / 255
    return arr + (g * 1.6 + c * 1.2)[..., None] * col * amt

# ------------------------------------------------------------------ text
F_CAP = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
F_UI = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
F_MONO = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf"
_F = {}
def font(p, s):
    k = (p, int(s))
    if k not in _F: _F[k] = ImageFont.truetype(p, max(1, int(s)))
    return _F[k]
WHITE, YELLOW, BLACK = (255, 255, 255), (255, 212, 0), (0, 0, 0)
RUSTC = (240, 110, 60)

def tag(d, txt, col=(120, 220, 210)):
    f = font(F_MONO, 22)
    d.rounded_rectangle((60, 196, 60 + f.getlength(txt) + 28, 236), 10, fill=(0, 0, 0, 150))
    d.ellipse((72, 210, 84, 222), fill=col)
    d.text((94, 216), txt, font=f, fill=(232, 232, 232), anchor="lm")

def hook_title(d, k=1.0, y=300):
    """THE MOON IS RUSTING?! — two lines, white + rust-yellow, black stroke."""
    s = max(0.85, k)
    d.text((540, y), "THE MOON", font=font(F_CAP, 118 * s), fill=WHITE, anchor="mm", stroke_width=11, stroke_fill=BLACK)
    d.text((540, y + 122 * s), "IS RUSTING?!", font=font(F_CAP, 118 * s), fill=YELLOW, anchor="mm", stroke_width=11, stroke_fill=BLACK)
