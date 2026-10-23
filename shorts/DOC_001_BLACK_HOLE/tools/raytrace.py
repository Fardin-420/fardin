"""Schwarzschild black-hole renderer (units G = M = c = 1, horizon r = 2, photon sphere r = 3, ISCO r = 6).

Each pixel's light ray is traced backwards from a static camera by integrating the photon orbit equation
    d^2u/dphi^2 = 3u^2 - u,   u = 1/r
in the plane containing the camera, the hole and the ray. Orbits depend only on the impact parameter b, so one
batched RK4 integration per camera distance gives r(phi) for every b; pixels then look up where their ray escapes
(lensed starfield), falls in (shadow) or first crosses the thin equatorial accretion disk.
Simplifications (stated on screen as "simulation"): non-rotating hole, static (hovering) camera, thin disk with
approximate Doppler beaming and gravitational redshift, no disk self-occlusion beyond the first crossing.
"""
import math
from functools import lru_cache

import numpy as np

R_IN, R_OUT = 6.0, 22.0


@lru_cache(maxsize=10)
def photon_table(D, theta_max, nb=6000, nphi=2600, phimax=3.2 * math.pi):
    D = float(D)
    th = np.linspace(1e-4, theta_max, nb)
    b = D * np.sin(th) / math.sqrt(1 - 2 / D)
    u = np.full(nb, 1 / D)
    sgn = np.where(th < math.pi / 2, 1.0, -1.0)                      # inward (toward the hole) or outward
    w = sgn * np.sqrt(np.maximum(0, 1 / b ** 2 - u ** 2 * (1 - 2 * u)))
    h = phimax / nphi
    r_tab = np.full((nb, nphi), np.nan, np.float32)
    alive = np.ones(nb, bool)
    status = np.zeros(nb, np.int8)            # 0 still going, 1 captured, 2 escaped
    phi_inf = np.full(nb, np.nan)
    f = lambda u_, w_: (w_, 3 * u_ * u_ - u_)
    for i in range(nphi):
        r_tab[alive, i] = 1 / u[alive]
        k1u, k1w = f(u, w)
        k2u, k2w = f(u + h / 2 * k1u, w + h / 2 * k1w)
        k3u, k3w = f(u + h / 2 * k2u, w + h / 2 * k2w)
        k4u, k4w = f(u + h * k3u, w + h * k3w)
        un = u + h / 6 * (k1u + 2 * k2u + 2 * k3u + k4u)
        wn = w + h / 6 * (k1w + 2 * k2w + 2 * k3w + k4w)
        cap = alive & (un >= 0.5)
        esc = alive & (un <= 0)
        status[cap] = 1
        status[esc] = 2
        frac = u[esc] / np.maximum(u[esc] - un[esc], 1e-12)
        phi_inf[esc] = (i + frac) * h
        alive &= ~(cap | esc)
        u, w = np.where(alive, un, u), np.where(alive, wn, w)
        if not alive.any():
            break
    status[alive] = 1   # still circling at phimax: treat as captured (vanishingly thin)
    return th, r_tab, status, phi_inf, h


def make_sky(w=4096, h=2048, seed=4):
    rng = np.random.default_rng(seed)
    lat = np.linspace(math.pi / 2, -math.pi / 2, h)[:, None]
    lon = np.linspace(-math.pi, math.pi, w)[None, :]
    # galactic band (tilted) with dusty structure
    band_lat = np.arcsin(np.clip(np.sin(lat) * math.cos(0.5) - np.cos(lat) * np.sin(lon) * math.sin(0.5), -1, 1))
    from PIL import Image
    def noise(octs, s):
        r = np.random.default_rng(s); out = np.zeros((h, w))
        for o in range(octs):
            g = r.normal(0, 1, (8 * 2 ** o, 16 * 2 ** o)).astype(np.float32)
            out += np.asarray(Image.fromarray(g).resize((w, h), Image.BICUBIC)) * 0.55 ** o
        return out
    n1 = noise(6, seed + 1)
    band = np.exp(-(band_lat / 0.22) ** 2) * (0.55 + 0.45 * np.tanh(n1))
    sky = np.zeros((h, w, 3), np.float32)
    sky += band[..., None] * np.array([38, 34, 46], np.float32)
    sky += (np.exp(-(band_lat / 0.08) ** 2) * np.clip(n1, 0, None))[..., None] * np.array([30, 22, 18], np.float32)
    n2 = noise(5, seed + 2)
    sky += (np.clip(n2 - 1.0, 0, None) * 18)[..., None] * np.array([0.6, 0.3, 0.9], np.float32)   # faint nebulae
    # stars: more along the band, small soft discs so lensing smears them smoothly
    n = 26000
    ys = rng.integers(0, h, n); xs = rng.integers(0, w, n)
    keep = rng.random(n) < 0.35 + 0.65 * band[ys, xs]
    ys, xs = ys[keep], xs[keep]
    mag = rng.pareto(2.2, len(xs)) * 60 + 40
    tint = np.stack([np.ones(len(xs)), 0.85 + 0.15 * rng.random(len(xs)), 0.7 + 0.3 * rng.random(len(xs))], 1)
    swap = rng.random(len(xs)) < 0.4
    tint[swap] = tint[swap][:, ::-1]
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            wgt = 1.0 if dx == dy == 0 else 0.35
            np.add.at(sky, ((ys + dy) % h, (xs + dx) % w), (mag[:, None] * tint * wgt).astype(np.float32))
    return np.clip(sky, 0, 255)


def blackbody(tn):
    """tn ~ 0..1.4 normalized temperature -> RGB 0..1 (red-orange-white-blue-ish ramp)."""
    stops = np.array([0.0, 0.25, 0.5, 0.75, 1.0, 1.4])
    cols = np.array([[0.25, 0.02, 0.0], [0.85, 0.22, 0.03], [1.0, 0.55, 0.15], [1.0, 0.82, 0.55], [1.0, 0.97, 0.9], [0.8, 0.9, 1.0]])
    return np.stack([np.interp(tn, stops, cols[:, c]) for c in range(3)], -1)


def render(D, incl, az, sky, W=720, H=1280, fov_y=62.0, t=0.0, roll=0.0, disk=True, disk_gain=1.0, look=(0.0, 0.0)):
    """Camera hovering at distance D (in M), inclination incl (deg from disk normal), azimuth az (deg).
    look: (yaw, pitch) offsets in degrees so the camera can glance away from the hole."""
    i_, a_ = math.radians(incl), math.radians(az)
    C = D * np.array([math.sin(i_) * math.cos(a_), math.sin(i_) * math.sin(a_), math.cos(i_)])
    f = -C / D
    upw = np.array([0.0, 0.0, 1.0])
    rgt = np.cross(f, upw); rgt /= np.linalg.norm(rgt)
    up = np.cross(rgt, f)
    if roll:
        cr, sr = math.cos(math.radians(roll)), math.sin(math.radians(roll))
        rgt, up = cr * rgt + sr * up, -sr * rgt + cr * up
    if look != (0.0, 0.0):
        yw, pt = math.radians(look[0]), math.radians(look[1])
        f = math.cos(yw) * f + math.sin(yw) * rgt; rgt = np.cross(f, up); rgt /= np.linalg.norm(rgt)
        f = math.cos(pt) * f + math.sin(pt) * up; up = np.cross(rgt, f)
    ty = math.tan(math.radians(fov_y) / 2); tx = ty * W / H
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    px = (2 * (xs + 0.5) / W - 1) * tx
    py = (1 - 2 * (ys + 0.5) / H) * ty
    d = f[None, None, :] + px[..., None] * rgt[None, None, :] + py[..., None] * up[None, None, :]
    d /= np.linalg.norm(d, axis=-1, keepdims=True)
    fh = -C / D                                   # direction to the hole (rays bend around it)
    cos_t = np.clip(d @ fh, -1, 1)
    theta = np.arccos(cos_t)
    e1 = C / D
    perp = d - cos_t[..., None] * fh
    pn = np.linalg.norm(perp, axis=-1, keepdims=True)
    e2 = perp / np.maximum(pn, 1e-9)
    th_max = float(min(math.pi - 1e-3, theta.max() + 1e-3))
    th_tab, r_tab, status, phi_inf, h = photon_table(round(D, 3), round(th_max, 3))
    bi = np.clip(np.rint((theta - th_tab[0]) / (th_tab[-1] - th_tab[0]) * (len(th_tab) - 1)).astype(np.int32), 0, len(th_tab) - 1)
    front = theta < th_tab[-1] + 1e-6
    st = np.where(front, status[bi], 2)
    out = np.zeros((H, W, 3), np.float32)
    # escaped rays -> lensed sky (rays behind the camera's tracing range use the undeflected direction)
    pinf = np.where(front, phi_inf[bi], math.pi - theta)
    esc = st == 2
    pinf = np.nan_to_num(pinf)
    sdir = np.cos(pinf)[..., None] * e1 + np.sin(pinf)[..., None] * e2
    lat = np.arcsin(np.clip(sdir[..., 2], -1, 1)); lon = np.arctan2(sdir[..., 1], sdir[..., 0])
    sh, sw = sky.shape[:2]
    sy = np.clip(((math.pi / 2 - lat) / math.pi * (sh - 1)).astype(np.int32), 0, sh - 1)
    sx = ((lon + math.pi) / (2 * math.pi) * (sw - 1)).astype(np.int32) % sw
    out[esc] = sky[sy[esc], sx[esc]]
    if disk:
        nrm = np.array([0.0, 0.0, 1.0])
        a = float(e1 @ nrm); c = e2 @ nrm
        phi0 = np.mod(np.arctan2(-a, c), math.pi)
        hit = np.zeros((H, W), bool); hr = np.zeros((H, W), np.float32); hphi = np.zeros((H, W), np.float32)
        nphi = r_tab.shape[1]
        for k in range(3):
            ph = phi0 + k * math.pi
            fi = ph / h
            pi_ = np.clip(fi.astype(np.int32), 0, nphi - 2)
            fr = np.clip(fi - pi_, 0, 1).astype(np.float32)
            r0, r1 = r_tab[bi, pi_], r_tab[bi, pi_ + 1]
            rr = np.where(np.isfinite(r1), r0 * (1 - fr) + r1 * fr, r0)   # interpolate along the orbit
            ok = front & ~hit & np.isfinite(rr) & (rr >= R_IN) & (rr <= R_OUT) & ((ph / h) < nphi - 1)
            hit |= ok; hr[ok] = rr[ok]; hphi[ok] = ph[ok]
        if hit.any():
            r = hr[hit]; ph = hphi[hit]
            p = r[:, None] * (np.cos(ph)[:, None] * e1 + np.sin(ph)[:, None] * e2[hit])
            vdir = np.cross(np.broadcast_to(nrm, p.shape), p); vdir /= np.linalg.norm(vdir, axis=1, keepdims=True)
            beta = 1 / np.sqrt(r)                            # Keplerian orbital speed (fraction of c)
            kdir = C[None, :] - p; kdir /= np.linalg.norm(kdir, axis=1, keepdims=True)
            gamma = 1 / np.sqrt(1 - beta ** 2)
            g = 1 / (gamma * (1 - beta * np.sum(vdir * kdir, 1)))  # relativistic Doppler factor
            g *= np.sqrt(np.clip(1 - 3 / r, 0.05, 1))        # gravitational + transverse redshift
            prof = (r / R_IN) ** -2.0 * np.clip(1 - np.sqrt(R_IN / r), 0, 1) ** 0.45 * 9.0
            prof *= np.clip((R_OUT - r) / (R_OUT * 0.35), 0, 1) ** 1.5      # soft outer edge
            psi = np.arctan2(p[:, 1], p[:, 0])
            omega = r ** -1.5
            swirl = 0.72 + 0.28 * np.sin(9 * np.log(r) + 3 * (psi - omega * t * 40)) * np.sin(5 * (psi - omega * t * 40) + 2 * np.log(r))
            inten = prof * swirl * g ** 3.2 * disk_gain
            col = blackbody(np.clip(0.95 * (r / R_IN) ** -0.75 * g, 0, 1.4))
            alpha = np.clip(prof / 0.6, 0, 1)[:, None]                       # thin, translucent outskirts
            out[hit] = out[hit] * (1 - 0.8 * alpha) + np.clip(col * inten[:, None], 0, 6) * 255
    out[st == 1] = 0
    return out
