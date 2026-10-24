"""Earth renderer for SPACE SECRETS EP02: per-pixel sphere projection with separate surface and cloud rotation.

Textures: Solar System Scope (CC BY 4.0, based on NASA imagery), via the three.js examples folder.
  day   = earth_day_4096.jpg, night = earth_night_4096.jpg,
  aux   = earth_bump_roughness_clouds_4096.jpg  (R elevation, G land mask, B clouds)
Coordinates: view space x right, y up, z toward the viewer. lat0 = latitude at the disk centre.
lon_c = geographic longitude at the disk centre; it DEcreases as the planet spins east (features move right).
"""
import math
import numpy as np
from PIL import Image

TEX = "tex/"
_T = {}


def tex():
    if not _T:
        _T["day"] = np.asarray(Image.open(TEX + "earth_day_4096.jpg").convert("RGB"), np.float32)
        _T["night"] = np.asarray(Image.open(TEX + "earth_night_4096.jpg").convert("RGB"), np.float32)
        aux = np.asarray(Image.open(TEX + "earth_bump_roughness_clouds_4096.jpg").convert("RGB"), np.float32)
        _T["land"] = (aux[..., 1] > 128).astype(np.float32)
        _T["cloud"] = aux[..., 2] / 255.0
        from scipy import ndimage
        land = ndimage.binary_opening(_T["land"] > 0.5, structure=np.ones((9, 9)))   # drop small islands (streak artifacts)
        h = land.shape[0]
        lat = np.linspace(90, -90, h)[:, None]
        band = (np.abs(lat) < 62).astype(np.float32) * np.cos(np.radians(lat))
        surge = np.zeros(land.shape, np.float32); recede = np.zeros(land.shape, np.float32)
        K = 20                                                       # ~1.8 degrees of longitude
        for k in range(1, K + 1):
            w = 1 - (k - 1) / K
            surge = np.maximum(surge, np.roll(land, -k, axis=1) * w)    # land just to the east: west-facing coast
            recede = np.maximum(recede, np.roll(land, k, axis=1) * w)   # land just to the west: east-facing coast
        sea = ~land
        _T["surge"] = ndimage.gaussian_filter(surge * sea * band, 2.0)
        _T["recede"] = ndimage.gaussian_filter(recede * sea * band, 2.0)
    return _T


def _sample(img, u, v):
    """Bilinear lookup; u wraps in longitude, v clamps at the poles."""
    h, w = img.shape[:2]
    u = np.mod(u, w); v = np.clip(v, 0, h - 1.001)
    u0 = np.floor(u).astype(np.int32); v0 = np.floor(v).astype(np.int32)
    fu = (u - u0)[..., None] if img.ndim == 3 else (u - u0); fv = (v - v0)[..., None] if img.ndim == 3 else (v - v0)
    u1 = (u0 + 1) % w; v1 = np.minimum(v0 + 1, h - 1)
    a, b, c, d = img[v0, u0], img[v0, u1], img[v1, u0], img[v1, u1]
    return (a * (1 - fu) + b * fu) * (1 - fv) + (c * (1 - fu) + d * fu) * fv


def render(W, H, cx, cy, R, lat0, lon_c, lon_cloud, sun=(-0.55, 0.28, 0.79), surge=0.0, recede=0.0, cloud_amt=1.0,
           stars=None, t=0.0, night_gain=1.4, ambient=0.0):
    T = tex()
    th, tw = T["land"].shape
    out = np.zeros((H, W, 3), np.float32) if stars is None else stars.astype(np.float32).copy()
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    nx = (xs - cx) / R; ny = (cy - ys) / R
    r2 = nx * nx + ny * ny
    # outer atmosphere halo
    rr = np.sqrt(r2)
    halo = np.clip(1 - np.abs(rr - 1) / 0.06, 0, 1)            # both sides of the limb: no dark seam when blending
    out += (halo ** 2)[..., None] * np.array([70, 130, 255], np.float32) * 0.9
    m = r2 < 1
    if not m.any():
        return out
    nxm, nym = nx[m], ny[m]; nzm = np.sqrt(1 - r2[m])
    c0, s0 = math.cos(math.radians(lat0)), math.sin(math.radians(lat0))
    X = nxm; Y = nym * c0 + nzm * s0; Z = -nym * s0 + nzm * c0
    lat = np.degrees(np.arcsin(np.clip(Y, -1, 1)))
    lonv = np.degrees(np.arctan2(X, Z))
    v = (90 - lat) / 180 * th
    us = (lonv + lon_c + 180) / 360 * tw
    uc = (lonv + lon_cloud + 180) / 360 * tw
    day = _sample(T["day"], us, v)
    night = _sample(T["night"], us, v)
    land = _sample(T["land"], us, v)
    cloud = np.clip(_sample(T["cloud"], uc, v) * 1.25 - 0.08, 0, 1) * cloud_amt
    L = np.array(sun, np.float32); L /= np.linalg.norm(L)
    ndl = nxm * L[0] + nym * L[1] + nzm * L[2]
    diff = np.clip(ndl, 0, 1)
    dayw = np.clip((ndl + 0.08) / 0.3, 0, 1)
    Hh = L + np.array([0, 0, 1.0]); Hh /= np.linalg.norm(Hh)
    spec = np.clip(nxm * Hh[0] + nym * Hh[1] + nzm * Hh[2], 0, 1) ** 70 * (1 - land) * (1 - cloud) * 0.9 * (ndl > 0)
    col = day * (0.05 + 1.05 * diff)[:, None] + night * ((1 - dayw) ** 2 * night_gain)[:, None] + day * ambient * np.array([0.55, 0.7, 1.0], np.float32) * (1 - cloud[:, None])
    col += spec[:, None] * np.array([255, 240, 215], np.float32)
    if surge > 0 or recede > 0:
        sg = _sample(T["surge"], us, v) * surge; rc = _sample(T["recede"], us, v) * recede
        col = col * (1 - 0.6 * sg[:, None]) + sg[:, None] * np.array([120, 230, 255], np.float32) * (0.6 + 0.4 * dayw[:, None])
        col = col * (1 - 0.5 * rc[:, None]) + rc[:, None] * np.array([255, 140, 60], np.float32) * 0.55
    ccol = np.array([250, 252, 255], np.float32) * (0.06 + 1.0 * diff)[:, None]
    col = col * (1 - cloud[:, None] * 0.92) + ccol * cloud[:, None] * 0.92
    rim = (1 - nzm) ** 2.6
    col += (rim * (0.35 + 0.9 * diff))[:, None] * np.array([90, 150, 255], np.float32)
    edge = np.clip((1 - np.sqrt(r2[m])) * R / 1.5, 0, 1)[:, None]          # anti-aliased limb
    out[m] = out[m] * (1 - edge) + col * edge
    return out


def project(lat, lon, cx, cy, R, lat0, lon_c):
    """Geographic (deg) -> screen (x, y, visible)."""
    lat = np.radians(lat); lv = np.radians(np.asarray(lon) - lon_c)
    X = np.cos(lat) * np.sin(lv); Y = np.sin(lat) * np.ones_like(lv); Z = np.cos(lat) * np.cos(lv)
    c0, s0 = math.cos(math.radians(lat0)), math.sin(math.radians(lat0))
    nx = X; ny = Y * c0 - Z * s0; nz = Y * s0 + Z * c0
    return cx + nx * R, cy - ny * R, nz > 0.02


def stars(W, H, seed=7, n=5200):
    """Deep-space backdrop: dense starfield plus a faint diagonal Milky Way haze, so space reads as depth, not void."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = ((xx / W - 0.15) * 0.8 - (yy / H - 0.1) * 0.45)             # distance from a tilted band
    g = rng.normal(0, 1, (H // 16 + 1, W // 16 + 1)).astype(np.float32)
    from PIL import Image as _I
    lump = np.asarray(_I.fromarray(g).resize((W, H), _I.BICUBIC), np.float32)
    band = np.exp(-(d / 0.16) ** 2) * (0.6 + 0.4 * np.tanh(lump))
    a = np.zeros((H, W, 3), np.float32)
    a += band[..., None] * np.array([34, 30, 46], np.float32)
    a += np.array([5, 7, 14], np.float32) * (0.6 + 0.4 * (yy / H))[..., None]   # cool ambient sky
    ys = rng.integers(0, H, n); xs = rng.integers(0, W, n)
    keep = rng.random(n) < 0.45 + 0.55 * band[ys, xs]
    ys, xs = ys[keep], xs[keep]
    b = rng.pareto(2.3, len(xs)) * 60 + 35
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            w = 1.0 if dx == dy == 0 else 0.3
            np.add.at(a, (np.clip(ys + dy, 0, H - 1), np.clip(xs + dx, 0, W - 1)), (b * w)[:, None] * np.array([1, 1, 1.08]))
    return np.clip(a, 0, 255)
