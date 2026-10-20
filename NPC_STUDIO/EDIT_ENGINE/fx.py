"""Image operations for the edit engine (NumPy + OpenCV, float32 RGB in [0, 1]).

Everything here is a pure function of its inputs; randomness is always seeded
by the caller, so any frame can be rendered alone, out of order, in any process.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

import cv2
import numpy as np

# ----------------------------------------------------------------------------- easing

def clamp01(x):
    return min(1.0, max(0.0, x))


def smooth(x):
    x = clamp01(x)
    return x * x * (3 - 2 * x)


def ease_out_expo(x):
    x = clamp01(x)
    return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)


def ease_in_expo(x):
    x = clamp01(x)
    return 0.0 if x <= 0 else 2 ** (10 * x - 10)


def ease_in_out_cubic(x):
    x = clamp01(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_out_cubic(x):
    x = clamp01(x)
    return 1 - (1 - x) ** 3


def ease_in_cubic(x):
    x = clamp01(x)
    return x ** 3


def ease_out_back(x, s=1.70158):
    x = clamp01(x)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def impulse(t, t0, attack=0.0, decay=0.08):
    """0 before t0, rises over `attack` s, then decays exponentially with time constant `decay`."""
    if t < t0:
        return 0.0
    if attack > 0 and t < t0 + attack:
        return (t - t0) / attack
    return math.exp(-(t - t0 - attack) / decay)


def window(t, a, b, fade_in=0.0, fade_out=0.0):
    if t < a or t > b:
        return 0.0
    v = 1.0
    if fade_in > 0:
        v = min(v, (t - a) / fade_in)
    if fade_out > 0:
        v = min(v, (b - t) / fade_out)
    return clamp01(v)


def lerp(a, b, x):
    return a + (b - a) * x


# ----------------------------------------------------------------------------- layers

class Layer:
    """An RGBA image (premultiplied) with a mip chain, sampled through a camera."""

    def __init__(self, rgb: np.ndarray, alpha: np.ndarray | None = None, overlay: bool = False):
        # photos reflect at the border (frames are clamped inside anyway); overlays (logo,
        # masks) are transparent outside their own bounds
        self.border = cv2.BORDER_CONSTANT if overlay else cv2.BORDER_REFLECT
        rgb = rgb.astype(np.float32)
        a = np.ones(rgb.shape[:2], np.float32) if alpha is None else alpha.astype(np.float32)
        rgba = np.dstack([rgb * a[..., None], a])
        self.h, self.w = rgba.shape[:2]
        self.mips = [(1.0, rgba)]
        s, cur = 1.0, rgba
        while min(cur.shape[:2]) > 300:
            s *= 0.5 ** 0.5
            cur = cv2.resize(rgba, (int(round(self.w * s)), int(round(self.h * s))), interpolation=cv2.INTER_AREA)
            self.mips.append((s, cur))

    def sample(self, M: np.ndarray, out_wh: tuple[int, int], scale: float, sharp: bool = True) -> np.ndarray:
        """M: 2x3 affine mapping output px -> level-0 source px. scale: output px per source px."""
        lvl_s, img = self.mips[0]
        for s, im in self.mips:
            if s >= scale * 0.999:
                lvl_s, img = s, im
        Ml = M * lvl_s
        Ml[:, 2] += 0.5 * (lvl_s - 1)  # INTER_AREA pixel-center convention of the mip level
        interp = cv2.INTER_CUBIC if sharp else cv2.INTER_LINEAR
        out = cv2.warpAffine(img, Ml, out_wh, flags=interp | cv2.WARP_INVERSE_MAP, borderMode=self.border, borderValue=0)
        if sharp:
            np.clip(out, 0, None, out=out)
        return out


@dataclass
class Cam:
    """Camera on an image: (cx, cy) source-normalized point at screen center; zoom 1 = cover fit."""
    cx: float = 0.5
    cy: float = 0.5
    zoom: float = 1.0
    rot: float = 0.0      # degrees
    ox: float = 0.0       # screen px offset (shake), applied before the cover clamp
    oy: float = 0.0

    def mix(self, o: "Cam", x: float) -> "Cam":
        return Cam(lerp(self.cx, o.cx, x), lerp(self.cy, o.cy, x), math.exp(lerp(math.log(self.zoom), math.log(o.zoom), x)),
                   lerp(self.rot, o.rot, x), lerp(self.ox, o.ox, x), lerp(self.oy, o.oy, x))


def cam_matrix(cam: Cam, src_wh, out_wh, clamp: bool = True, frame_wh=None, bounds=None):
    """Returns (M out->src, scale). With clamp, the visible window never leaves the source
    (or the normalized `bounds` rectangle x0, y0, x1, y1 inside it)."""
    w, h = src_wh
    W, H = out_wh
    FW, FH = frame_wh or out_wh  # cover fit is defined against the full frame, even for panels
    s = max(FW / w, FH / h) * cam.zoom * (W / FW)
    r = math.radians(cam.rot)
    c, si = math.cos(r), math.sin(r)
    # screen offset expressed as a source-space shift of the center
    cx = cam.cx * w - (c * cam.ox + si * cam.oy) / s
    cy = cam.cy * h - (-si * cam.ox + c * cam.oy) / s
    if clamp:
        bx0, by0, bx1, by1 = bounds or (0, 0, 1, 1)
        bx0, bx1, by0, by1 = bx0 * w, bx1 * w, by0 * h, by1 * h
        ex = (W / 2 * abs(c) + H / 2 * abs(si)) / s
        ey = (W / 2 * abs(si) + H / 2 * abs(c)) / s
        if 2 * ex > bx1 - bx0 or 2 * ey > by1 - by0:  # zoom up just enough to cover
            k = max(2 * ex / (bx1 - bx0), 2 * ey / (by1 - by0)) * 1.001
            s *= k
            ex, ey = ex / k, ey / k
        cx = min(max(cx, bx0 + ex), bx1 - ex)
        cy = min(max(cy, by0 + ey), by1 - ey)
    # out (u,v) -> src: src = C + R(-rot) * ((u,v) - center) / s
    M = np.array([[c / s, si / s, 0.0], [-si / s, c / s, 0.0]], np.float64)
    M[0, 2] = cx - (M[0, 0] * W / 2 + M[0, 1] * H / 2)
    M[1, 2] = cy - (M[1, 0] * W / 2 + M[1, 1] * H / 2)
    return M, s


def corners_disp(M1: np.ndarray, M2: np.ndarray, out_wh, s: float) -> float:
    """Largest screen-space displacement of a source point between two camera matrices."""
    W, H = out_wh
    pts = np.array([[0, 0, 1], [W, 0, 1], [0, H, 1], [W, H, 1], [W / 2, H / 2, 1]], np.float64)
    a, b = pts @ M1.T, pts @ M2.T
    return float(np.abs(a - b).max() * s)


def over(dst_rgb: np.ndarray, src_rgba: np.ndarray, opacity: float = 1.0) -> np.ndarray:
    """Premultiplied RGBA over RGB."""
    if opacity <= 0:
        return dst_rgb
    a = src_rgba[..., 3:4] * opacity
    return dst_rgb * (1 - a) + src_rgba[..., :3] * opacity


def over_rgba(dst: np.ndarray, src: np.ndarray) -> np.ndarray:
    a = src[..., 3:4]
    return dst * (1 - a) + src


# ----------------------------------------------------------------------------- blur & light

def blur(img: np.ndarray, sigma: float, down: int = 1) -> np.ndarray:
    if sigma <= 0.3:
        return img
    if down > 1:
        h, w = img.shape[:2]
        small = cv2.resize(img, (w // down, h // down), interpolation=cv2.INTER_AREA)
        small = cv2.GaussianBlur(small, (0, 0), sigma / down)
        return cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)
    return cv2.GaussianBlur(img, (0, 0), sigma)


def directional_blur(img: np.ndarray, dx: float, dy: float) -> np.ndarray:
    """Box blur along a screen vector (length in px). Separable fast path for axis-aligned motion."""
    L = math.hypot(dx, dy)
    if L < 1.5:
        return img
    if abs(dy) < 0.15 * L:
        return cv2.blur(img, (int(L) | 1, 1))
    if abs(dx) < 0.15 * L:
        return cv2.blur(img, (1, int(L) | 1))
    n = max(3, int(L / 3))
    acc = np.zeros_like(img)
    h, w = img.shape[:2]
    for i in range(n):
        f = i / (n - 1) - 0.5
        M = np.float32([[1, 0, dx * f], [0, 1, dy * f]])
        acc += cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REFLECT)
    return acc / n


def zoom_blur(img: np.ndarray, amount: float, center=None, n: int = 10, down: int = 2) -> np.ndarray:
    """Radial blur: average of copies scaled about `center` from 1 to 1+amount."""
    if amount < 0.004:
        return img
    h, w = img.shape[:2]
    cx, cy = center or (w / 2, h / 2)
    sm = cv2.resize(img, (w // down, h // down), interpolation=cv2.INTER_AREA) if down > 1 else img
    sh, sw = sm.shape[:2]
    acc = np.zeros_like(sm)
    for i in range(n):
        k = 1 + amount * i / (n - 1)
        M = np.float32([[k, 0, (1 - k) * cx / down], [0, k, (1 - k) * cy / down]])
        acc += cv2.warpAffine(sm, M, (sw, sh), borderMode=cv2.BORDER_REFLECT)
    acc /= n
    return cv2.resize(acc, (w, h), interpolation=cv2.INTER_LINEAR) if down > 1 else acc


def bloom(img: np.ndarray, threshold: float = 0.72, strength: float = 0.35, sigma: float = 28, tint=(1, 1, 1)) -> np.ndarray:
    lum = img.mean(2, keepdims=True)
    hi = img * np.clip((lum - threshold) / (1 - threshold + 1e-6), 0, 1)
    b = blur(hi, sigma, down=4) + 0.6 * blur(hi, sigma * 3, down=8)
    return img + b * strength * np.float32(tint)


def god_rays(light: np.ndarray, center, length: float = 0.35, n: int = 12, down: int = 4, decay: float = 0.93) -> np.ndarray:
    """Volumetric light scattering: radial smear of a light-source image toward `center`."""
    h, w = light.shape[:2]
    sm = cv2.resize(light, (w // down, h // down), interpolation=cv2.INTER_AREA)
    sh, sw = sm.shape[:2]
    cx, cy = center[0] / down, center[1] / down
    acc = sm.copy()
    wgt, tot = 1.0, 1.0
    for i in range(1, n):
        k = 1 - length * i / n
        M = np.float32([[1 / k, 0, (1 - 1 / k) * cx], [0, 1 / k, (1 - 1 / k) * cy]])
        wgt *= decay
        acc += cv2.warpAffine(sm, M, (sw, sh), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_CONSTANT) * wgt
        tot += wgt
    return cv2.resize(acc / tot, (w, h), interpolation=cv2.INTER_LINEAR)


def rim_light(alpha: np.ndarray, direction=(1.0, -0.4), width: float = 6.0) -> np.ndarray:
    """Edge highlight on the side of the matte facing `direction` (screen space)."""
    dx, dy = direction
    n = math.hypot(dx, dy)
    dx, dy = dx / n * width, dy / n * width
    h, w = alpha.shape
    shifted = cv2.warpAffine(alpha, np.float32([[1, 0, -dx], [0, 1, -dy]]), (w, h), borderMode=cv2.BORDER_REPLICATE)
    rim = np.clip(alpha - shifted, 0, 1)
    return cv2.GaussianBlur(rim, (0, 0), width * 0.45)


def light_band(shape, t: float, angle_deg: float, width: float, pos: float) -> np.ndarray:
    """A soft diagonal band of light at normalized position `pos` (0..1 across the frame)."""
    h, w = shape
    a = math.radians(angle_deg)
    xs = np.arange(w, dtype=np.float32)[None, :] / w
    ys = np.arange(h, dtype=np.float32)[:, None] / h * (h / w)
    d = xs * math.cos(a) + ys * math.sin(a)
    span = math.cos(a) + (h / w) * abs(math.sin(a))
    center = -0.2 + pos * (span + 0.4)
    return np.exp(-((d - center) / width) ** 2).astype(np.float32)


def vignette_mask(w: int, h: int, strength: float = 0.55, softness: float = 0.9) -> np.ndarray:
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    nx, ny = (xs / w - 0.5) * 2, (ys / h - 0.5) * 2 * (h / w) * 0.62
    r = np.sqrt(nx ** 2 + ny ** 2)
    return (1 - strength * smoothstep_arr(0.35, 0.35 + softness, r))[..., None].astype(np.float32)


def smoothstep_arr(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


# ----------------------------------------------------------------------------- distortion

class Distort:
    """Precomputed coordinate grids for remap-based lens effects at one resolution."""

    def __init__(self, w: int, h: int):
        self.w, self.h = w, h
        ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
        self.xs, self.ys = xs, ys
        self.cx, self.cy = w / 2, h / 2
        self.dx, self.dy = xs - self.cx, ys - self.cy
        self.r = np.sqrt(self.dx ** 2 + self.dy ** 2) / (0.5 * math.hypot(w, h))

    def barrel(self, img, k: float):
        if abs(k) < 1e-4:
            return img
        f = 1 + k * self.r ** 2
        f /= 1 + k * 0.6  # keep the frame filled (scale back so edges stay inside)
        return cv2.remap(img, self.cx + self.dx * f, self.cy + self.dy * f, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    def shockwave(self, img, radius: float, amp: float, width: float = 0.06, center=None):
        if amp < 0.05:
            return img
        if center is None:
            dx, dy, r = self.dx, self.dy, self.r
            cx, cy = self.cx, self.cy
        else:
            cx, cy = center
            dx, dy = self.xs - cx, self.ys - cy
            r = np.sqrt(dx ** 2 + dy ** 2) / (0.5 * math.hypot(self.w, self.h))
        g = np.exp(-((r - radius) / width) ** 2) * amp
        inv = 1 / (r * 0.5 * math.hypot(self.w, self.h) + 1e-3)
        return cv2.remap(img, (cx + dx - dx * inv * g).astype(np.float32), (cy + dy - dy * inv * g).astype(np.float32),
                         cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    def chroma(self, img, amount: float):
        """Radial chromatic aberration: R scaled out, B scaled in, by `amount` (fraction at the corners)."""
        if amount < 1e-4:
            return img
        out = img.copy()
        for ch, k in ((0, 1 + amount), (2, 1 - amount)):
            M = np.float32([[1 / k, 0, self.cx * (1 - 1 / k)], [0, 1 / k, self.cy * (1 - 1 / k)]])
            out[..., ch] = cv2.warpAffine(img[..., ch], M, (self.w, self.h), borderMode=cv2.BORDER_REFLECT)
        return out


def channel_shift(img, dx: float, dy: float = 0.0):
    if abs(dx) + abs(dy) < 0.5:
        return img
    h, w = img.shape[:2]
    out = img.copy()
    out[..., 0] = cv2.warpAffine(img[..., 0], np.float32([[1, 0, dx], [0, 1, dy]]), (w, h), borderMode=cv2.BORDER_REFLECT)
    out[..., 2] = cv2.warpAffine(img[..., 2], np.float32([[1, 0, -dx], [0, 1, -dy]]), (w, h), borderMode=cv2.BORDER_REFLECT)
    return out


# ----------------------------------------------------------------------------- glitch

def glitch_strips(img, seed: int, amount: float, bands: int = 7, max_shift: float = 0.12, rgb: float = 0.0):
    """Horizontal tearing: random bands shifted sideways (wrapping, so no empty areas)."""
    if amount <= 0.01:
        return img
    rng = np.random.default_rng(seed)
    h, w = img.shape[:2]
    out = img.copy()
    for _ in range(bands):
        y0 = int(rng.uniform(0, h))
        bh = int(rng.uniform(0.008, 0.07) * h)
        sh = int(rng.normal(0, max_shift) * w * amount)
        y1 = min(h, y0 + bh)
        out[y0:y1] = np.roll(img[y0:y1], sh, axis=1)
        if rgb > 0:
            out[y0:y1, :, 0] = np.roll(img[y0:y1, :, 0], sh + int(rgb * w * 0.01), axis=1)
    return out


def scanline_interrupt(img, seed: int, amount: float, y_band=None):
    if amount <= 0.01:
        return img
    rng = np.random.default_rng(seed)
    h, w = img.shape[:2]
    out = img.copy()
    y0, y1 = y_band or (int(rng.uniform(0, h * 0.8)), 0)
    y1 = y1 or min(h, y0 + int(h * rng.uniform(0.05, 0.18)))
    out[y0:y1:2] *= 1 - 0.65 * amount
    out[y0:y1] = np.roll(out[y0:y1], int(rng.normal(0, 0.03) * w * amount), axis=1)
    return out


def block_displace(img, seed: int, amount: float, blocks: int = 10):
    if amount <= 0.01:
        return img
    rng = np.random.default_rng(seed)
    h, w = img.shape[:2]
    out = img.copy()
    for _ in range(blocks):
        bw, bh = int(rng.uniform(0.08, 0.35) * w), int(rng.uniform(0.01, 0.05) * h)
        x, y = int(rng.uniform(0, w - bw)), int(rng.uniform(0, h - bh))
        sx = int(np.clip(x + rng.normal(0, 0.08) * w * amount, 0, w - bw))
        sy = int(np.clip(y + rng.normal(0, 0.01) * h * amount, 0, h - bh))
        out[y:y + bh, x:x + bw] = img[sy:sy + bh, sx:sx + bw]
    return out


# ----------------------------------------------------------------------------- particles

def splat(layer: np.ndarray, xs, ys, radii, intens, color, down: int = 2):
    """Additive soft dots. Drawn on a reduced canvas, then blurred: cheap, smooth."""
    h, w = layer.shape[:2]
    sm = np.zeros((h // down, w // down), np.float32)
    for x, y, r, a in zip(xs, ys, radii, intens):
        if a <= 0.003 or not (-50 < x < w + 50 and -50 < y < h + 50):
            continue
        cv2.circle(sm, (int(x / down), int(y / down)), max(1, int(r / down)), float(a), -1, cv2.LINE_AA)
    sm = cv2.GaussianBlur(sm, (0, 0), 1.2)
    big = cv2.resize(sm, (w, h), interpolation=cv2.INTER_LINEAR)
    return layer + big[..., None] * np.float32(color)


def streak(layer: np.ndarray, p0, p1, width: float, intensity: float, color, glow: float = 10):
    h, w = layer.shape[:2]
    m = np.zeros((h // 2, w // 2), np.float32)
    cv2.line(m, (int(p0[0] / 2), int(p0[1] / 2)), (int(p1[0] / 2), int(p1[1] / 2)), 1.0, max(1, int(width / 2)), cv2.LINE_AA)
    core = cv2.GaussianBlur(m, (0, 0), 0.8)
    halo = cv2.GaussianBlur(m, (0, 0), glow / 2)
    v = cv2.resize(core + 0.6 * halo, (w, h), interpolation=cv2.INTER_LINEAR)
    return layer + v[..., None] * intensity * np.float32(color)


# ----------------------------------------------------------------------------- finishing

def grain_bank(w: int, h: int, n: int = 6, seed: int = 7) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        g = rng.normal(0, 1, (h // 2, w // 2)).astype(np.float32)
        g = cv2.GaussianBlur(g, (0, 0), 0.7)
        out.append(cv2.resize(g, (w, h), interpolation=cv2.INTER_LINEAR)[..., None])
    return out


def filmic(img: np.ndarray, shoulder: float = 0.78) -> np.ndarray:
    """Soft highlight shoulder: linear below `shoulder`, smooth roll-off to 1 above (no hard clipping)."""
    x = np.maximum(img, 0)
    hi = x > shoulder
    if hi.any():
        k = 1 - shoulder
        x = np.where(hi, shoulder + k * (1 - np.exp(-(x - shoulder) / k)), x)
    return x


def to_u8(img: np.ndarray, dither: np.ndarray | None = None) -> np.ndarray:
    x = img * 255.0
    if dither is not None:
        x += dither[..., 0:1] * 0.6
    return np.clip(x + 0.5, 0, 255).astype(np.uint8)


def grade(rgb: np.ndarray, lift=(0, 0, 0), gain=(1, 1, 1), gamma=1.0, sat=1.0, contrast=0.0, pivot=0.45) -> np.ndarray:
    """Simple lift/gamma/gain + saturation + S-contrast around `pivot`."""
    x = np.clip(rgb, 0, None)
    lum = x @ np.float32([0.2126, 0.7152, 0.0722])
    x = lum[..., None] + (x - lum[..., None]) * sat
    x = np.clip(x, 0, None) ** (1 / gamma)
    if contrast:
        x = pivot + (x - pivot) * (1 + contrast) - contrast * (x - pivot) ** 3 * 1.2
    x = np.float32(lift) + x * (np.float32(gain) - np.float32(lift))
    return np.clip(x, 0, None).astype(np.float32)


def replace_cam(c: Cam, **kw) -> Cam:
    return replace(c, **kw)
