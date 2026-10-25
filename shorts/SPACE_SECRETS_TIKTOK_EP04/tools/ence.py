"""Enceladus, Saturn and plume renderers for SPACE SECRETS EP04. All procedural (no third-party imagery).
Enceladus: very bright water-ice surface, cratered north, smooth young south with four parallel 'tiger stripe' fractures
(~130 km long, ~35 km apart) around the south pole. Saturn: oblate banded globe with A/B/C rings and the Cassini Division."""
import math
import numpy as np
from scipy import ndimage

_T = {}
H_, W_ = 1024, 2048
STRIPES = [-12.0, -4.0, 4.0, 12.0]          # stripe offsets in polar-plane degrees (~8 deg = ~35 km at R = 252 km)

def _pp(lat, lon):
    """South-polar plane coords (degrees of arc from the pole)."""
    p = 90 + lat
    return p * np.cos(np.radians(lon)), p * np.sin(np.radians(lon))

def stripe_field(lat, lon):
    px, py = _pp(lat, lon)
    best = np.full(np.shape(lat), 99.0)
    for c in STRIPES:
        dist = np.abs(py - c - 0.012 * px ** 2)
        dist = np.where(np.abs(px) < 16 - 0.15 * abs(c), dist, 99.0)
        best = np.minimum(best, dist)
    return best

def jet_sites(n=160, seed=3):
    rng = np.random.default_rng(seed); out = []
    while len(out) < n:
        c = STRIPES[rng.integers(0, 4)]; px = rng.uniform(-15 + 0.15 * abs(c), 15 - 0.15 * abs(c)); py = c + 0.012 * px ** 2
        p = math.hypot(px, py); lon = math.degrees(math.atan2(py, px)); out.append((p - 90, lon))
    return np.array(out)

def tex():
    if _T: return _T
    rng = np.random.default_rng(504)
    yy, xx = np.mgrid[0:H_, 0:W_].astype(np.float32)
    lat = 90 - yy / H_ * 180; lon = xx / W_ * 360 - 180
    clat = np.cos(np.radians(lat))
    def n(sig, amp=1.0):
        a = ndimage.gaussian_filter(rng.normal(0, 1, (H_, W_)).astype(np.float32), sig, mode="wrap"); return a / (a.std() + 1e-6) * amp
    height = n(24, 0.25) + n(7, 0.04)
    alb = 0.97 + 0.025 * n(14) + 0.01 * n(4)
    crater_w = np.clip((lat + 30) / 60, 0, 1)                    # old cratered terrain in the north, young plains in the south
    for _ in range(1100):
        r = 0.35 * (1 - rng.random()) ** -0.6
        if r > 5: continue
        la = math.degrees(math.asin(rng.uniform(-1, 1))); lo = rng.uniform(-180, 180)
        if rng.random() > np.clip((la + 30) / 60, 0.05, 1) or abs(la) > 75: continue
        v = (90 - la) / 180 * H_; rr = int(4 * r / 180 * H_) + 4
        y0, y1 = int(max(0, v - rr)), int(min(H_, v + rr)); sl = (slice(y0, y1), slice(None))
        d = np.sqrt(((lat[sl] - la) / r) ** 2 + (((lon[sl] - lo + 180) % 360 - 180) * clat[sl] / r) ** 2)
        height[sl] += (np.where(d < 1, -(1 - d ** 2), 0) + np.exp(-((d - 1) / 0.2) ** 2) * 0.3) * r * 0.05
    # ridged plains in the south (fine parallel grooves)
    south = np.clip((-lat - 40) / 25, 0, 1)
    px, py = _pp(lat, lon)
    height += south * 0.02 * np.sin(py * 1.6 + n(16, 1.2))
    sd = stripe_field(lat, lon)
    groove = np.exp(-(sd / 0.9) ** 2)
    rim = np.exp(-((sd - 1.6) / 0.7) ** 2)
    height += rim * 0.35 - groove * 0.6
    alb = alb * (1 - 0.35 * groove) + 0.06 * rim
    col = np.stack([alb * 0.93, alb * 0.97, alb * 1.0], -1)
    col = col * (1 - groove[..., None] * 0.5) + groove[..., None] * np.array([0.45, 0.62, 0.78]) * 0.5   # bluish fresh ice in stripes
    gy, gx = np.gradient(ndimage.gaussian_filter(height, 0.8))
    _T.update(col=np.clip(col, 0, 1.1).astype(np.float32), gx=(gx * 2.5).astype(np.float32), gy=(gy * 2.5).astype(np.float32))
    return _T

def view_basis(lat0, lon_c):
    return math.cos(math.radians(lat0)), math.sin(math.radians(lat0)), lon_c

def render_enceladus(Wr, Hr, cx, cy, R, light=(-0.5, 0.3, 0.8), lon_c=0.0, lat0=0.0, base=None, gain=1.0, halo=0.0):
    T = tex()
    out = np.zeros((Hr, Wr, 3), np.float32) if base is None else base.astype(np.float32).copy()
    ext = R * (1.25 if halo else 1.02) + 2
    x0, x1 = int(max(0, cx - ext)), int(min(Wr, cx + ext)); y0, y1 = int(max(0, cy - ext)), int(min(Hr, cy + ext))
    if x1 <= x0 or y1 <= y0 or R < 0.5: return out
    ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    nx = (xs - cx) / R; ny = (cy - ys) / R; r2 = nx * nx + ny * ny
    sub = out[y0:y1, x0:x1]
    if halo:
        r = np.sqrt(r2); sub += (halo * np.exp(-np.clip(r - 1, 0, None) / 0.05) * (r >= 1))[..., None] * np.array([150, 180, 220], np.float32)
    m = r2 < 1
    if m.any():
        L = np.array(light, np.float32); L /= np.linalg.norm(L)
        nxm, nym = nx[m], ny[m]; nzm = np.sqrt(1 - r2[m])
        c0, s0 = math.cos(math.radians(lat0)), math.sin(math.radians(lat0))
        X = nxm; Y = nym * c0 + nzm * s0; Z = -nym * s0 + nzm * c0
        lat = np.degrees(np.arcsin(np.clip(Y, -1, 1))); lon = np.degrees(np.arctan2(X, Z)) + lon_c
        v = (90 - lat) / 180 * (H_ - 1); u = ((lon + 180) % 360) / 360 * W_
        smp = lambda a: ndimage.map_coordinates(a, [v, u], order=1, mode="wrap")
        col = np.stack([smp(T["col"][..., k]) for k in range(3)], -1)
        gx = smp(T["gx"]); gy = smp(T["gy"])
        pnx = nxm - gx; pny = nym + gy; pnz = nzm
        nn = np.sqrt(pnx ** 2 + pny ** 2 + pnz ** 2)
        mu0 = np.clip((pnx * L[0] + pny * L[1] + pnz * L[2]) / nn, 0, None)
        term = np.clip((nxm * L[0] + nym * L[1] + nzm * L[2] + 0.03) / 0.08, 0, 1)
        val = (0.05 + 0.95 * mu0 ** 0.7) * term
        c = col * val[:, None] * 262 * gain + col * 6 * (1 - term[:, None])
        rim = (1 - nzm) ** 3 * term
        c += rim[:, None] * np.array([40, 60, 90], np.float32)
        edge = np.clip((1 - np.sqrt(r2[m])) * R / 1.2, 0, 1)[:, None]
        sub[m] = sub[m] * (1 - edge) + c * edge
    out[y0:y1, x0:x1] = sub
    return out

def project(lat, lon, cx, cy, R, lat0, lon_c):
    lat = np.radians(lat); lv = np.radians(np.asarray(lon) - lon_c)
    X = np.cos(lat) * np.sin(lv); Y = np.sin(lat) * np.ones_like(lv); Z = np.cos(lat) * np.cos(lv)
    c0, s0 = math.cos(math.radians(lat0)), math.sin(math.radians(lat0))
    nx = X; ny = Y * c0 - Z * s0; nz = Y * s0 + Z * c0
    return cx + nx * R, cy - ny * R, nx, ny, nz

# ------------------------------------------------------------------ plumes (particles splatted additively)
def _plume_layer(Hh, Ww, t, cx, cy, R, lat0, lon_c, st, n_per, spread, height, seed, rate):
    rng = np.random.default_rng(seed)
    gx, gy, nx, ny, nz = project(st[:, 0], st[:, 1], cx, cy, R, lat0, lon_c)
    ns = len(st)
    ph = rng.random((ns, n_per)); sp = rng.uniform(0.5, 1.25, (ns, n_per))
    ang = rng.normal(0, spread, (ns, n_per))
    age = (ph + t * rate * sp) % 1.0
    dist = age * height * R * sp
    base_ang = np.arctan2(-ny, nx)[:, None]
    a = base_ang + ang
    foreshort = np.sqrt(np.clip(1 - nz ** 2, 0.08, 1))[:, None]
    px = gx[:, None] + np.cos(a) * dist * foreshort
    py = gy[:, None] + np.sin(a) * dist * foreshort
    behind = (nz[:, None] < 0) & (((px - cx) ** 2 + (py - cy) ** 2) < R * R)
    w = (1 - age) ** 2 * (nz[:, None] > -0.3) * (~behind)
    ok = (px >= 0) & (px < Ww) & (py >= 0) & (py < Hh) & (w > 0.01)
    acc = np.zeros((Hh, Ww), np.float32)
    np.add.at(acc, (py[ok].astype(int), px[ok].astype(int)), w[ok])
    return acc

def plumes(arr, t, cx, cy, R, lat0, lon_c, strength=1.0, height=1.2, n_per=70, sites=None, light_back=1.0, seed=7, spread=None):
    """Jets from the tiger-stripe sites: thin collimated jets plus a broad, diffuse fan of vapour and ice grains."""
    if strength <= 0: return arr
    st = jet_sites() if sites is None else sites
    Hh, Ww = arr.shape[:2]
    jets = _plume_layer(Hh, Ww, t, cx, cy, R, lat0, lon_c, st, n_per, 0.035, height, seed, 0.3)
    fan = _plume_layer(Hh, Ww, t, cx, cy, R, lat0, lon_c, st[::2], n_per * 2, 0.32, height * 1.5, seed + 1, 0.22)
    k = max(1.0, R / 300)
    soft = (ndimage.gaussian_filter(jets, 1.5 * k) * 110 + ndimage.gaussian_filter(jets, 6 * k) * 160
            + ndimage.gaussian_filter(fan, 10 * k) * 520 + ndimage.gaussian_filter(fan, 3 * k) * 40)
    return arr + (soft * strength * light_back)[..., None] * np.array([0.8, 0.9, 1.0], np.float32)

# ------------------------------------------------------------------ Saturn
_S = {}
def saturn_tex():
    if not _S:
        rng = np.random.default_rng(9)
        lat = np.linspace(90, -90, 512)[:, None]
        g = ndimage.gaussian_filter1d(rng.normal(0, 1, 512), 3)
        v = 0.75 + 0.1 * np.sin(np.radians(lat) * 14) + 0.06 * g[:, None] + 0.05 * np.sin(np.radians(lat) * 37)
        v = v * np.ones((1, 1024)) + 0.015 * ndimage.gaussian_filter(rng.normal(0, 1, (512, 1024)), (1, 18), mode="wrap") * 8
        col = np.stack([v * 1.0, v * 0.88, v * 0.66], -1)
        pole = np.clip((np.abs(lat) - 60) / 25, 0, 1)[..., None]
        col = col * (1 - 0.35 * pole) + pole * np.array([0.45, 0.55, 0.6]) * 0.35
        _S["col"] = col.astype(np.float32)
    return _S["col"]

RING = [(1.24, 1.53, 0.12), (1.53, 1.95, 0.85), (1.95, 2.03, 0.08), (2.03, 2.21, 0.6), (2.21, 2.22, 0.1), (2.22, 2.27, 0.55)]
def ring_opacity(r):
    o = np.zeros_like(r)
    for a, b, op in RING: o = np.where((r >= a) & (r < b), op, o)
    return o * (0.85 + 0.15 * np.sin(r * 180))

def render_saturn(Wr, Hr, cx, cy, R, tilt=18.0, light=(-0.6, 0.25, 0.75), base=None, gain=1.0):
    col_t = saturn_tex()
    out = np.zeros((Hr, Wr, 3), np.float32) if base is None else base.astype(np.float32).copy()
    ys, xs = np.mgrid[0:Hr, 0:Wr].astype(np.float32)
    obl = 0.9
    nx = (xs - cx) / R; ny = (cy - ys) / (R * obl); r2 = nx * nx + ny * ny
    st = math.sin(math.radians(tilt))
    # ring plane: (u, v) with v compressed by sin(tilt)
    u = (xs - cx) / R; v = (ys - cy) / (R * st + 1e-6)
    rr = np.sqrt(u * u + v * v)
    ring_a = ring_opacity(rr)
    ring_col = np.array([225, 205, 170], np.float32) * gain
    far = v < 0
    out = out * (1 - ring_a[..., None] * far[..., None]) + (ring_a * far)[..., None] * ring_col * 0.85
    m = r2 < 1
    L = np.array(light, np.float32); L /= np.linalg.norm(L)
    if m.any():
        nxm, nym = nx[m], ny[m]; nzm = np.sqrt(1 - r2[m])
        c0, s0 = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))
        Y = nym * c0 + nzm * s0
        lat = np.degrees(np.arcsin(np.clip(Y, -1, 1))); lon = np.degrees(np.arctan2(nxm, nzm))
        vv = (90 - lat) / 180 * 511; uu = ((lon + 180) % 360) / 360 * 1023
        col = np.stack([ndimage.map_coordinates(col_t[..., k], [vv, uu], order=1, mode="wrap") for k in range(3)], -1)
        diff = np.clip(nxm * L[0] + nym * L[1] + nzm * L[2], 0, 1)
        c = col * (0.04 + 1.0 * diff ** 0.8)[:, None] * 235 * gain
        # ring shadow band on the globe (thin dark band just below the rings' projection)
        sh = np.exp(-((ys[m] - cy - R * 0.08) / (R * 0.025)) ** 2) * 0.45
        c *= (1 - sh)[:, None]
        edge = np.clip((1 - np.sqrt(r2[m])) * R / 1.2, 0, 1)[:, None]
        out[m] = out[m] * (1 - edge) + c * edge
    near = ~far
    out = out * (1 - ring_a[..., None] * near[..., None]) + (ring_a * near)[..., None] * ring_col
    return out
