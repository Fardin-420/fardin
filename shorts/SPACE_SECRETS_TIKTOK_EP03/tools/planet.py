"""HD 189733 b renderer: a deep-azure hot Jupiter with zonal bands, differential flow, Rayleigh-blue limb,
a soft terminator, a thermal night-side glow and an optional dayside heat map. Procedural texture (no imagery).
Coordinates: view x right, y up, z toward the viewer; lat0 = latitude at the disk centre, lon_c = longitude at centre."""
import math
import numpy as np
from scipy import ndimage

_T = {}
def _wrapnoise(rng, shp, sig):
    n = ndimage.gaussian_filter(rng.normal(0, 1, shp).astype(np.float32), sig, mode="wrap")
    return n / (n.std() + 1e-6)

def tex():
    if not _T:
        rng = np.random.default_rng(189733)
        h, w = 512, 1024
        lat = np.linspace(90, -90, h)[:, None] * np.ones((1, w))
        warp = _wrapnoise(rng, (h, w), (4, 40)) * 2.2 + _wrapnoise(rng, (h, w), (1.5, 12)) * 0.7
        la = lat + warp
        v = (0.52 + 0.2 * np.sin(np.radians(la) * 9.0 + 0.4) + 0.13 * np.sin(np.radians(la) * 21 + 1.3)
             + 0.07 * np.sin(np.radians(la) * 43 + 2.0))
        v += 0.07 * _wrapnoise(rng, (h, w), (0.7, 26)) + 0.04 * _wrapnoise(rng, (h, w), (2.5, 50))
        v += 0.02 * _wrapnoise(rng, (h, w), (0.8, 3))
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)          # a few large storm ovals
        for cy, cx, ry, rx, s in ((330, 300, 16, 40, 0.22), (180, 760, 10, 26, -0.18), (260, 520, 7, 18, 0.15)):
            d = ((yy - cy) / ry) ** 2 + ((xx - cx) / rx) ** 2
            ang = np.arctan2((yy - cy) / ry, (xx - cx) / rx)
            v += s * np.exp(-d) * (0.6 + 0.4 * np.sin(ang * 3 + d * 4))
        v = np.clip(v, 0, 1)
        xp = [0.0, 0.3, 0.5, 0.68, 0.84, 1.0]
        col = np.stack([np.interp(v, xp, [4, 8, 20, 45, 95, 160]),
                        np.interp(v, xp, [14, 36, 78, 128, 178, 220]),
                        np.interp(v, xp, [60, 120, 190, 235, 252, 255])], -1).astype(np.float32)
        _T["col"] = col
        _T["v"] = v.astype(np.float32)
    return _T

def blackbody(x):
    xp = [0.0, 0.25, 0.5, 0.75, 1.0]
    return np.stack([np.interp(x, xp, [20, 140, 235, 255, 255]), np.interp(x, xp, [0, 20, 80, 160, 225]),
                     np.interp(x, xp, [0, 5, 10, 50, 150])], -1)

def render(Wr, Hr, cx, cy, R, lon_c, lat0, light=(-0.6, 0.25, 0.76), t=0.0, base=None, star_col=(1.0, 0.9, 0.78),
           thermal=0.0, night_glow=0.12, flow=1.0, gain=1.0):
    T = tex(); col_t = T["col"]; th, tw = col_t.shape[:2]
    out = np.zeros((Hr, Wr, 3), np.float32) if base is None else base.astype(np.float32).copy()
    ext = R * 1.12
    x0, x1 = int(max(0, cx - ext)), int(min(Wr, cx + ext)); y0, y1 = int(max(0, cy - ext)), int(min(Hr, cy + ext))
    if x1 <= x0 or y1 <= y0: return out
    ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    nx = (xs - cx) / R; ny = (cy - ys) / R; r2 = nx * nx + ny * ny; r = np.sqrt(r2)
    L = np.array(light, np.float32); L /= np.linalg.norm(L)
    sc = np.array(star_col, np.float32)
    # thin outer atmosphere (lit side glows blue, forward scattering brightens the crescent)
    lit_out = np.clip((nx * L[0] + ny * L[1]) / np.maximum(r, 1e-3) * 0.9 + 0.35 + 0.6 * max(0.0, -L[2]), 0, 1.6)
    halo = np.exp(-np.clip(r - 1, 0, None) / 0.035) * (r >= 1) * lit_out
    sub = out[y0:y1, x0:x1]
    sub += (halo * 0.9)[..., None] * np.array([70, 140, 255], np.float32) * gain
    m = r2 < 1
    if m.any():
        nxm, nym = nx[m], ny[m]; nzm = np.sqrt(1 - r2[m])
        c0, s0 = math.cos(math.radians(lat0)), math.sin(math.radians(lat0))
        X = nxm; Y = nym * c0 + nzm * s0; Z = -nym * s0 + nzm * c0
        lat = np.degrees(np.arcsin(np.clip(Y, -1, 1))); lonv = np.degrees(np.arctan2(X, Z))
        lon = lonv + lon_c + flow * t * (5.0 * np.cos(np.radians(lat) * 2.2))          # zonal jets
        v = (90 - lat) / 180 * (th - 1); u = ((lon + 180) % 360) / 360 * tw
        col = np.stack([ndimage.map_coordinates(col_t[..., k], [v, u], order=1, mode="wrap") for k in range(3)], -1)
        ndl = nxm * L[0] + nym * L[1] + nzm * L[2]
        diff = np.clip(ndl, 0, 1) ** 0.85
        dayw = np.clip((ndl + 0.06) / 0.3, 0, 1)
        c = col * (0.02 + 1.05 * diff)[:, None] * sc
        rim = (1 - nzm) ** 2.4
        c += (rim * (0.15 + 1.0 * dayw))[:, None] * np.array([60, 125, 255], np.float32) * 0.9
        Hh = L + np.array([0, 0, 1.0], np.float32); Hh /= np.linalg.norm(Hh) + 1e-6
        c += (np.clip(nxm * Hh[0] + nym * Hh[1] + nzm * Hh[2], 0, 1) ** 40 * 0.35 * (ndl > 0))[:, None] * np.array([255, 245, 230], np.float32)
        # thermal emission: night-side ember glow, hot spot shifted east of the substellar point (Spitzer map)
        hot = np.clip(np.cos(np.radians(lonv - 30)) * np.cos(np.radians(lat)), 0, 1)
        c += ((1 - dayw) * night_glow * (0.4 + 0.6 * hot))[:, None] * np.array([190, 45, 15], np.float32)
        if thermal > 0:
            tm = np.clip(0.25 + 0.75 * (0.65 * hot + 0.35 * dayw) + 0.12 * (T["v"][v.astype(int), u.astype(int) % tw] - 0.5), 0, 1)
            c = c * (1 - 0.8 * thermal) + blackbody(tm * 0.82) * thermal * (0.55 + 0.45 * tm)[:, None]
        edge = np.clip((1 - np.sqrt(r2[m])) * R / 1.5, 0, 1)[:, None]
        sub[m] = sub[m] * (1 - edge) + c * gain * edge
    out[y0:y1, x0:x1] = sub
    return out
