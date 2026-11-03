#!/usr/bin/env python3
# SPACE SECRETS — "The Invisible Black Hole": native-resolution CGI toolkit.
# Starfield source plate at 2x output resolution, point-mass gravitational lensing by inverse ray mapping,
# a 3D particle Milky Way, microlensing light-curve/centroid math, and a small N-body integrator.
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

W, H, FPS = 1080, 1920, 30
SC = 2                                                                            # source plate pixels per output pixel
GAIN = 2.1                                                                        # exposure of the star plates
PW, PH = 2800, 4600                                                               # source plate size (covers 1400x2300 output px)

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

def tone(arr, exp=1.2):
    a = np.clip(arr, 0, None) / 255.0
    return np.clip(255 * (1 - np.exp(-a * exp)) / (1 - math.exp(-exp)), 0, 255)

def glow(arr, amt=0.35, thr=170, rad=30):
    small = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
    hi = np.clip(np.asarray(small, np.float32) - thr, 0, None) * 1.8
    bl = np.asarray(Image.fromarray(np.clip(hi, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(rad / 4)).resize((W, H), Image.BILINEAR), np.float32)
    return arr + bl * amt

def finish(arr, g=0.35, exp=1.2):
    return Image.fromarray(np.clip(tone(glow(arr, g), exp), 0, 255).astype(np.uint8))

# ------------------------------------------------------------------ star colours (blackbody-ish)
def star_rgb(T):
    T = np.asarray(T, np.float32) / 100.0
    r = np.where(T <= 66, 255, 329.7 * (np.maximum(T - 60, 1e-3)) ** -0.133)
    g = np.where(T <= 66, 99.47 * np.log(np.maximum(T, 1)) - 161.1, 288.1 * (np.maximum(T - 60, 1e-3)) ** -0.0755)
    b = np.where(T >= 66, 255, np.where(T <= 19, 0, 138.5 * np.log(np.maximum(T - 10, 1e-3)) - 305.0))
    return np.clip(np.stack([r, g, b], -1), 0, 255) / 255.0

# ------------------------------------------------------------------ source plates (photoreal dense starfields)
def make_plate(seed=1, n=170000, glow_amp=26.0, dust_amp=0.75, warm=1.0, bright_n=60):
    """Galactic-bulge-like crowded field at 2x output resolution: resolved stars + unresolved glow + dust lanes."""
    rng = np.random.default_rng(seed)
    def nz(sig, shape=(PH // 4, PW // 4)):
        a = ndimage.gaussian_filter(rng.normal(0, 1, shape).astype(np.float32), sig, mode="wrap"); return a / (a.std() + 1e-6)
    lo = nz(60) * 0.6 + nz(18) * 0.3 + nz(5) * 0.12
    dust = np.clip((nz(40) * 0.7 + nz(10) * 0.35 + nz(3) * 0.12 - 0.35) / 1.2, 0, 1) * dust_amp
    lo_full = np.asarray(Image.fromarray(lo).resize((PW, PH), Image.BICUBIC), np.float32)
    dust_full = np.asarray(Image.fromarray(dust.astype(np.float32)).resize((PW, PH), Image.BICUBIC), np.float32)
    yy = np.linspace(-1, 1, PH)[:, None]
    band = np.exp(-(yy * 0.9) ** 2) * (0.65 + 0.35 * np.clip(lo_full, -1, 2))
    base = band[..., None] * np.array([0.95, 0.86, 0.74], np.float32) * glow_amp * warm + np.array([1, 1, 2], np.float32)
    img = np.zeros((PH, PW, 3), np.float32)
    ys = rng.uniform(0, PH, n); xs = rng.uniform(0, PW, n)
    dens = np.exp(-(((ys / PH) * 2 - 1) * 0.9) ** 2)
    keep = rng.random(n) < (0.35 + 0.65 * dens); ys, xs = ys[keep], xs[keep]
    m = len(ys)
    flux = (rng.pareto(1.25, m) + 0.25) * 40
    T = np.clip(rng.normal(4800, 900, m), 3000, 11000)
    hot = rng.random(m) < 0.06; T[hot] = rng.uniform(9000, 22000, hot.sum())
    col = star_rgb(T) * flux[:, None]
    iy, ix = ys.astype(int), xs.astype(int)
    fy, fx = ys - iy, xs - ix                                                     # bilinear deposit = sub-pixel accurate stars
    for dy, dx, w in ((0, 0, (1 - fy) * (1 - fx)), (0, 1, (1 - fy) * fx), (1, 0, fy * (1 - fx)), (1, 1, fy * fx)):
        Y = np.clip(iy + dy, 0, PH - 1); X = np.clip(ix + dx, 0, PW - 1)
        np.add.at(img, (Y, X), col * w[:, None])
    img = ndimage.gaussian_filter(img, (0.85, 0.85, 0))                          # telescope PSF core (~0.4 output px)
    big = flux > np.quantile(flux, 0.997)
    halo = np.zeros_like(img)
    np.add.at(halo, (np.clip(iy[big], 0, PH - 1), np.clip(ix[big], 0, PW - 1)), col[big])
    img += ndimage.gaussian_filter(halo, (3, 3, 0)) * 0.7 + ndimage.gaussian_filter(halo, (14, 14, 0)) * 0.5
    order = np.argsort(-flux)[:bright_n]                                          # a few bright foreground stars with soft spikes
    for k in order:
        x, y, c = xs[k], ys[k], col[k] / (flux[k] + 1e-6)
        L = 40 + 140 * min(1, flux[k] / flux[order[0]])
        for ang in (0.0, math.pi / 2):
            t = np.linspace(-L, L, int(4 * L))
            px = np.clip((x + t * math.cos(ang)).astype(int), 0, PW - 1); py = np.clip((y + t * math.sin(ang)).astype(int), 0, PH - 1)
            img[py, px] += c * 60 * np.exp(-np.abs(t) / (L * 0.35))[:, None]
    img = ndimage.gaussian_filter(img, (0.6, 0.6, 0)) * 0 + img
    img = img * (1 - 0.85 * dust_full[..., None]) + base * (1 - 0.9 * dust_full[..., None])
    return img.astype(np.float32)

def plate(kind="bulge"):
    if kind == "bulge": return cache("p_bulge", lambda: make_plate(1, 520000, 16, 0.7, 1.0, 80))
    if kind == "sparse": return cache("p_sparse", lambda: make_plate(7, 45000, 6, 0.45, 0.6, 30))
    if kind == "field": return cache("p_field", lambda: make_plate(3, 220000, 9, 0.6, 0.85, 50))

_G = {}
def grid():
    if not _G:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        _G.update(xx=xx, yy=yy)
    return _G["xx"], _G["yy"]

def lens_view(src, lenses=(), off=(0.0, 0.0), zoom=1.0):
    """Render the source plate seen through point-mass lenses.
    lenses: list of (cx, cy, thetaE, shadow_r) in output px. off: plate offset in output px. zoom: output px per plate/SC px."""
    xx, yy = grid()
    bx, by = xx.copy(), yy.copy()
    dark = np.zeros((H, W), np.float32)
    for (cx, cy, tE, sh) in lenses:
        dx, dy = xx - cx, yy - cy
        r2 = dx * dx + dy * dy + 1e-3
        k = tE * tE / r2
        bx -= dx * k; by -= dy * k
        if sh > 0:
            r = np.sqrt(r2)
            dark = np.maximum(dark, np.clip((sh * 1.04 - r) / (sh * 0.08), 0, 1))
    mx, my = PW / SC / 2 - (W / 2) / zoom, PH / SC / 2 - (H / 2) / zoom           # keep the view inside the plate (no black edges)
    off = (clamp(off[0], -mx, mx) if mx > 0 else 0.0, clamp(off[1], -my, my) if my > 0 else 0.0)
    sx = PW / 2 + ((bx - W / 2) / zoom + off[0]) * SC
    sy = PH / 2 + ((by - H / 2) / zoom + off[1]) * SC
    out = np.stack([ndimage.map_coordinates(src[..., c], [sy, sx], order=1, mode="constant", cval=0.0) for c in range(3)], -1)
    return out * (1 - dark[..., None]) * GAIN

# ------------------------------------------------------------------ microlensing (point source, point lens)
def mag(u): return (u * u + 2) / (u * np.sqrt(u * u + 4))
def centroid_shift(u): return u / (u * u + 2)                                     # in units of thetaE, along the lens-source direction

# ------------------------------------------------------------------ 3D particle Milky Way (kpc), Sun at (8.2, 0, 0.02)
def galaxy(seed=42, n=420000):
    def make():
        rng = np.random.default_rng(seed)
        nd = int(n * 0.78); nb = n - nd
        R = rng.exponential(3.0, nd * 2); R = R[(R > 0.6) & (R < 15)][:nd]
        th = rng.uniform(0, 2 * np.pi, len(R))
        arm = (np.cos(2 * (th - np.log(R) / math.tan(math.radians(12))) ) + 1) / 2   # two logarithmic spiral arms
        keep = rng.random(len(R)) < 0.3 + 0.7 * arm ** 1.6
        R, th, arm = R[keep], th[keep], arm[keep]
        z = rng.normal(0, 0.12 + 0.02 * R, len(R))
        X, Y = R * np.cos(th), R * np.sin(th)
        T = np.where(arm > 0.8, rng.uniform(7000, 16000, len(R)), rng.normal(5200, 900, len(R)))
        b = rng.normal(0, 1, (nb, 3)) * np.array([1.4, 0.55, 0.42])
        Xb, Yb, Zb = b[:, 0] * math.cos(0.45) - b[:, 1] * math.sin(0.45), b[:, 0] * math.sin(0.45) + b[:, 1] * math.cos(0.45), b[:, 2]
        Tb = rng.normal(4300, 500, nb)
        bulge_w = 0.22
        P = np.concatenate([np.stack([X, Y, z], 1), np.stack([Xb, Yb, Zb], 1)]).astype(np.float32)
        Tt = np.concatenate([T, Tb])
        C = star_rgb(np.clip(Tt, 2800, 20000)).astype(np.float32) * rng.uniform(0.4, 1.0, len(Tt))[:, None].astype(np.float32)
        C[len(T):] *= bulge_w
        C[:len(T)] *= (0.6 + 0.9 * arm[:, None] ** 2).astype(np.float32)
        nd2 = 160000                                                               # dust lanes: on the inner edge of the arms
        Rd = rng.exponential(3.6, nd2 * 2); Rd = Rd[(Rd > 1.2) & (Rd < 12)][:nd2]
        thd = rng.uniform(0, 2 * np.pi, len(Rd))
        armd = (np.cos(2 * (thd - np.log(Rd) / math.tan(math.radians(12)) + 0.35)) + 1) / 2
        kd = rng.random(len(Rd)) < armd ** 4
        Rd, thd = Rd[kd], thd[kd]
        D = np.stack([Rd * np.cos(thd), Rd * np.sin(thd), rng.normal(0, 0.06, len(Rd))], 1).astype(np.float32)
        return P, C, D
    return cache("galaxy", make)

def look_at(cam, tgt, up=(0, 0, 1)):
    f = np.asarray(tgt, np.float32) - np.asarray(cam, np.float32); f /= np.linalg.norm(f)
    r = np.cross(f, up); r /= (np.linalg.norm(r) + 1e-9); u = np.cross(r, f)
    return r, u, f

def render_galaxy(cam, tgt, fov=60, up=(0, 0, 1), gain=1.0, base=None, dust_k=1.0, roll=0.0):
    P, C, D = galaxy()
    r, u, f = look_at(cam, tgt, up)
    if roll:
        cr, sr = math.cos(roll), math.sin(roll); r, u = r * cr + u * sr, -r * sr + u * cr
    fpx = (W / 2) / math.tan(math.radians(fov / 2))
    def proj(Q):
        d = Q - np.asarray(cam, np.float32)
        zc = d @ f; ok = zc > 0.02
        x = W / 2 + (d @ r) / np.maximum(zc, 1e-3) * fpx; y = H / 2 - (d @ u) / np.maximum(zc, 1e-3) * fpx
        ok &= (x >= 0) & (x < W - 1) & (y >= 0) & (y < H - 1)
        return x[ok], y[ok], zc[ok], ok
    img = np.zeros((H, W, 3), np.float32) if base is None else base.copy()
    x, y, zc, ok = proj(P)
    w = (gain * 9.0 / np.maximum(zc, 0.25) ** 1.15).astype(np.float32)
    acc = np.zeros((H, W, 3), np.float32)
    ix, iy = x.astype(int), y.astype(int); fx, fy = x - ix, y - iy
    cw = C[ok] * w[:, None]
    for dy, dx, ww in ((0, 0, (1 - fy) * (1 - fx)), (0, 1, (1 - fy) * fx), (1, 0, fy * (1 - fx)), (1, 1, fy * fx)):
        np.add.at(acc, (iy + dy, ix + dx), cw * ww[:, None])
    soft = ndimage.gaussian_filter(acc, (6, 6, 0))                                # unresolved glow of the same stars
    img += ndimage.gaussian_filter(acc, (0.6, 0.6, 0)) * 110 + soft * 150
    xd, yd, zd, okd = proj(D)
    dacc = np.zeros((H, W), np.float32)
    np.add.at(dacc, (yd.astype(int), xd.astype(int)), (1.0 / np.maximum(zd, 0.3)).astype(np.float32))
    dm = ndimage.gaussian_filter(dacc, 4) * 6 * dust_k
    img *= np.exp(-dm)[..., None]
    return img

# ------------------------------------------------------------------ N-body (AU, yr, Msun): Sun + planets + passing black hole
def nbody_close_pass(M_bh=7.0, b_au=35.0, v_kms=30.0, years=40.0, dt=0.002):
    def make():
        G = 4 * math.pi ** 2
        names = ["Earth", "Jupiter", "Saturn", "Uranus", "Neptune"]
        a = [1.0, 5.2, 9.58, 19.2, 30.07]; m = [3e-6, 9.5e-4, 2.86e-4, 4.4e-5, 5.15e-5]
        rng = np.random.default_rng(5)
        pos = [np.zeros(2)]; vel = [np.zeros(2)]; mass = [1.0]
        for ai, mi in zip(a, m):
            ph = rng.uniform(0, 2 * np.pi)
            pos.append(np.array([ai * math.cos(ph), ai * math.sin(ph)])); v = math.sqrt(G / ai)
            vel.append(np.array([-v * math.sin(ph), v * math.cos(ph)])); mass.append(mi)
        v = v_kms / 4.74                                                           # km/s -> AU/yr
        pos.append(np.array([-v * years / 2, b_au])); vel.append(np.array([v, 0.0])); mass.append(M_bh)
        pos, vel, mass = np.array(pos), np.array(vel), np.array(mass)
        steps = int(years / dt); rec = max(1, int(1 / (dt * 30)))
        out = []
        def acc(p):
            d = p[None, :, :] - p[:, None, :]; r3 = (np.sum(d * d, -1) + 1e-6) ** 1.5
            np.fill_diagonal(r3, np.inf)
            return G * np.sum(d * (mass[None, :, None] / r3[..., None]), 1)
        a0 = acc(pos)
        for s in range(steps):                                                     # velocity Verlet
            pos = pos + vel * dt + 0.5 * a0 * dt * dt
            a1 = acc(pos); vel = vel + 0.5 * (a0 + a1) * dt; a0 = a1
            if s % rec == 0: out.append(pos.copy())
        return names, np.array(out), years
    return cache(("nbody", M_bh, b_au, v_kms, years), make)
