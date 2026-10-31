"""Procedural Moon for SPACE SECRETS EP01 (YouTube). Original albedo + relief built from the real near-side layout:
maria placed at their selenographic positions, named craters (Tycho, Copernicus, Kepler, Aristarchus, Plato) with ray
systems, plus a power-law crater population. No third-party imagery. Orthographic sphere render with lunar-style
(Lommel-Seeliger blended with Lambert) shading so a full Moon looks evenly bright and the terminator shows relief."""
import math
import numpy as np
from scipy import ndimage

_T = {}
H_, W_ = 1024, 2048

def _ll(lat, lon):
    return (90 - lat) / 180 * H_, ((lon + 180) % 360) / 360 * W_

def tex():
    if _T: return _T
    rng = np.random.default_rng(1969)
    yy, xx = np.mgrid[0:H_, 0:W_].astype(np.float32)
    lat = 90 - yy / H_ * 180; lon = xx / W_ * 360 - 180
    clat = np.cos(np.radians(lat))
    def blob(la, lo, ry, rx, rot=0.0):
        dy = (lat - la); dx = ((lon - lo + 180) % 360 - 180) * clat
        c, s = math.cos(rot), math.sin(rot)
        u, v = dx * c - dy * s, dx * s + dy * c
        return (u / rx) ** 2 + (v / ry) ** 2
    def n(sig, amp=1.0):
        a = ndimage.gaussian_filter(rng.normal(0, 1, (H_, W_)).astype(np.float32), sig, mode="wrap"); return a / (a.std() + 1e-6) * amp
    warp = n(26, 1.0) * 0.55 + n(9, 1.0) * 0.22 + n(3, 1.0) * 0.06
    mare = np.zeros((H_, W_), np.float32)
    MARIA = [(33, -16, 15, 19, 0.2), (18, -57, 26, 17, 0.3), (0, -50, 16, 12, 0), (28, 17, 8.5, 9.5, 0), (8.5, 31, 9.5, 12, 0.4),
             (17, 59, 5.5, 7, 0), (-7.8, 51, 9, 6, -0.2), (-15, 35, 5, 5, 0), (-21, -17, 9, 10, 0), (-24, -39, 5, 5, 0),
             (56, 1, 4.5, 30, 0), (13, 4, 4, 5, 0), (-10, -23, 5, 6, 0), (2, 1, 3, 4, 0), (-3, -27, 6, 8, 0.2), (24, 40, 4, 6, 0)]
    for la, lo, ry, rx, rot in MARIA:
        d = blob(la, lo, ry, rx, rot)
        mare = np.maximum(mare, np.clip((1.5 - d - warp) / 0.9, 0, 1))
    mare = np.clip(mare, 0, 1) ** 0.8
    mare = ndimage.gaussian_filter(mare, 2.5)
    height = n(30, 0.5) + n(6, 0.06) - mare * 0.6
    alb = 0.62 + 0.06 * n(10) + 0.03 * n(2.5)
    alb = alb * (1 - 0.42 * mare) + 0.025 * n(6) * mare
    rays = np.zeros((H_, W_), np.float32)
    def crater(la, lo, r, depth=1.0, ray=0.0, bright=0.0, dark_floor=0.0):
        nonlocal height, alb, rays
        d = np.sqrt(blob(la, lo, r, r))
        win = d < 3.2
        if not win.any(): return
        bowl = np.where(d < 1, -(1 - d ** 2) * depth, 0) + np.exp(-((d - 1) / 0.18) ** 2) * 0.35 * depth
        height = height + bowl * r * 0.05
        alb = alb + np.exp(-((d - 1) / 0.25) ** 2) * 0.05 + bright * np.clip(1.3 - d, 0, 1) - dark_floor * (d < 0.9)
        if ray > 0:
            ang = np.arctan2(lat - la, (lon - lo) * clat)
            spokes = np.clip(np.sin(ang * 23 + 1) * np.sin(ang * 37 + 2) * 1.6, 0, 1) ** 2
            rays = np.maximum(rays, ray * spokes * np.exp(-np.clip(d - 1, 0, None) / 4.5) * (d > 0.8))
    for la, lo, r, dep, ray, br, df in ((-43.3, -11.2, 2.8, 1.2, 0.6, 0.2, 0), (9.6, -20.1, 3.1, 1.1, 0.18, 0.1, 0),
                                       (8.1, -38, 1.0, 1.0, 0.3, 0.12, 0), (23.7, -47.4, 1.3, 1.0, 0.25, 0.3, 0),
                                       (51.6, -9.4, 3.4, 0.5, 0, 0, 0.12), (-9.3, -1.9, 4.5, 0.8, 0, 0, 0.02),
                                       (-20, -9, 2.6, 0.8, 0, 0, 0), (-36, 15, 2.5, 0.9, 0, 0.03, 0), (-40, -60, 3.5, 0.9, 0, 0, 0.03)):
        crater(la, lo, r, dep, ray, br, df)
    # power-law crater population (more on the highlands)
    for _ in range(1400):
        r = 0.25 * (1 - rng.random()) ** -0.65
        if r > 3.5: continue
        la = math.degrees(math.asin(rng.uniform(-1, 1))); lo = rng.uniform(-180, 180)
        if abs(la) > 72: continue
        v, u = _ll(la, lo)
        if mare[int(min(v, H_ - 1)), int(u) % W_] > 0.5 and rng.random() < 0.7: continue
        rr = int(4 * r / 180 * H_) + 4
        y0, y1 = int(max(0, v - rr)), int(min(H_, v + rr)); sl = (slice(y0, y1), slice(None))
        d = np.sqrt(((lat[sl] - la) / r) ** 2 + (((lon[sl] - lo + 180) % 360 - 180) * clat[sl] / r) ** 2)
        height[sl] += (np.where(d < 1, -(1 - d ** 2), 0) + np.exp(-((d - 1) / 0.2) ** 2) * 0.3) * r * 0.045
        alb[sl] += np.exp(-((d - 1) / 0.3) ** 2) * 0.03 * (r < 1.2) + 0.05 * np.clip(1 - d, 0, 1) * (r < 0.5)
    alb = np.clip(alb + rays * 0.22, 0.08, 1.0)
    alb = ndimage.gaussian_filter(alb, 0.6)
    gy, gx = np.gradient(ndimage.gaussian_filter(height, 0.8))
    _T.update(alb=alb.astype(np.float32), gx=(gx * 5).astype(np.float32), gy=(gy * 5).astype(np.float32))
    return _T

def render(Wr, Hr, cx, cy, R, light=(0.0, 0.0, 1.0), lon_c=0.0, lat0=0.0, base=None, gain=1.0, tint=(1.0, 0.98, 0.94),
           earthshine=0.0, halo=0.0):
    T = tex()
    out = np.zeros((Hr, Wr, 3), np.float32) if base is None else base.astype(np.float32).copy()
    ext = R * (1.6 if halo > 0 else 1.02) + 2
    x0, x1 = int(max(0, cx - ext)), int(min(Wr, cx + ext)); y0, y1 = int(max(0, cy - ext)), int(min(Hr, cy + ext))
    if x1 <= x0 or y1 <= y0 or R < 0.5: return out
    ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    nx = (xs - cx) / R; ny = (cy - ys) / R; r2 = nx * nx + ny * ny
    sub = out[y0:y1, x0:x1]
    if halo > 0:
        r = np.sqrt(r2)
        sub += (halo * np.exp(-np.clip(r - 1, 0, None) / 0.18) * (r >= 1))[..., None] * np.array([210, 215, 225], np.float32)
    m = r2 < 1
    if m.any():
        L = np.array(light, np.float32); L /= np.linalg.norm(L)
        nxm, nym = nx[m], ny[m]; nzm = np.sqrt(1 - r2[m])
        c0, s0 = math.cos(math.radians(lat0)), math.sin(math.radians(lat0))
        X = nxm; Y = nym * c0 + nzm * s0; Z = -nym * s0 + nzm * c0
        lat = np.degrees(np.arcsin(np.clip(Y, -1, 1))); lon = np.degrees(np.arctan2(X, Z)) + lon_c
        v = (90 - lat) / 180 * (H_ - 1); u = ((lon + 180) % 360) / 360 * W_
        smp = lambda a: ndimage.map_coordinates(a, [v, u], order=1, mode="wrap")
        alb = smp(T["alb"]); gx = smp(T["gx"]); gy = smp(T["gy"])
        # perturb the normal with the relief (in view space: east ~ +x, north ~ +y)
        pnx = nxm - gx * 0.9; pny = nym + gy * 0.9; pnz = nzm
        nn = np.sqrt(pnx ** 2 + pny ** 2 + pnz ** 2); pnx, pny, pnz = pnx / nn, pny / nn, pnz / nn
        mu0 = np.clip(pnx * L[0] + pny * L[1] + pnz * L[2], 0, None); mu = np.clip(nzm, 1e-3, None)
        ls = np.minimum(2 * mu0 / (mu0 + mu + 1e-4), 1.15)
        shade = 0.75 * ls + 0.25 * mu0
        term = np.clip((nxm * L[0] + nym * L[1] + nzm * L[2] + 0.02) / 0.06, 0, 1)
        val = alb * shade * term * 330 * gain + alb * earthshine * 60 * (1 - term)
        col = val[:, None] * np.array(tint, np.float32)
        edge = np.clip((1 - np.sqrt(r2[m])) * R / 1.2, 0, 1)[:, None]
        sub[m] = sub[m] * (1 - edge) + col * edge
    out[y0:y1, x0:x1] = sub
    return out
