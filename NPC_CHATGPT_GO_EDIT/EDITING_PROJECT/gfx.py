"""NPC motion-graphics primitives: text sprites, glass panels, outlines, glitch, easing.

Frames are uint8 BGR numpy arrays. Sprites are float32 BGRA (straight alpha, 0..1).
"""
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONTS = Path(__file__).resolve().parents[2] / "NPC_STUDIO" / "BRAND" / "fonts"

# Brand palette (BGR)
INK = (8, 8, 8)            # #080808
IVORY = (240, 245, 245)    # #F5F5F0
RED = (56, 48, 255)        # #FF3038
GRAPHITE = (30, 28, 27)
STEEL = (153, 144, 141)


def hex_rgb(bgr):
    return (bgr[2], bgr[1], bgr[0])


@lru_cache(None)
def font(name, size):
    files = {"black": "InterDisplay-Black.otf", "xbold": "InterDisplay-ExtraBold.otf",
             "bold": "InterDisplay-Bold.otf", "medium": "InterDisplay-Medium.otf",
             "regular": "InterDisplay-Regular.otf", "light": "InterDisplay-Light.otf",
             "mono": "JetBrainsMono-Bold.ttf", "mono_med": "JetBrainsMono-Medium.ttf"}
    return ImageFont.truetype(str(FONTS / files[name]), size)


@lru_cache(4096)
def text_sprite(text, face, size, color=IVORY, tracking=0.0, pad=6):
    """Rendered text as a BGRA float sprite; tracking is extra spacing in em."""
    f = font(face, size)
    if tracking:
        widths = [f.getlength(ch) + tracking * size for ch in text]
        w = int(sum(widths)) + pad * 2
    else:
        w = int(f.getlength(text)) + pad * 2
    asc, desc = f.getmetrics()
    h = asc + desc + pad * 2
    im = Image.new("L", (max(w, 1), h), 0)
    d = ImageDraw.Draw(im)
    if tracking:
        x = pad
        for ch, cw in zip(text, widths):
            d.text((x, pad), ch, font=f, fill=255)
            x += cw
    else:
        d.text((pad, pad), text, font=f, fill=255)
    a = np.asarray(im, np.float32) / 255.0
    spr = np.zeros((h, w, 4), np.float32)
    spr[..., 0], spr[..., 1], spr[..., 2] = color[0], color[1], color[2]
    spr[..., 3] = a
    spr.setflags(write=False)
    return spr


def blend(dst, spr, x, y, alpha=1.0):
    """Alpha-composite sprite (BGRA float) onto dst (uint8 BGR) at integer top-left (x, y)."""
    if alpha <= 0.002:
        return
    x, y = int(round(x)), int(round(y))
    h, w = spr.shape[:2]
    H, W = dst.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if x1 <= x0 or y1 <= y0:
        return
    s = spr[y0 - y:y1 - y, x0 - x:x1 - x]
    a = s[..., 3:4] * alpha
    roi = dst[y0:y1, x0:x1].astype(np.float32)
    dst[y0:y1, x0:x1] = (roi * (1 - a) + s[..., :3] * a).astype(np.uint8)


def scale_sprite(spr, k):
    if abs(k - 1) < 0.01:
        return spr
    h, w = spr.shape[:2]
    return cv2.resize(spr, (max(1, int(w * k)), max(1, int(h * k))), interpolation=cv2.INTER_LINEAR)


@lru_cache(256)
def rr_mask(w, h, r):
    """Anti-aliased rounded-rectangle alpha mask (float32)."""
    ss = 3
    im = Image.new("L", (w * ss, h * ss), 0)
    ImageDraw.Draw(im).rounded_rectangle([0, 0, w * ss - 1, h * ss - 1], radius=r * ss, fill=255)
    m = np.asarray(im.resize((w, h), Image.LANCZOS), np.float32) / 255.0
    m.setflags(write=False)
    return m


def glass(dst, rect, alpha=0.72, radius=22, color=INK, blur=True):
    """Dark frosted panel: blurred, darkened backdrop inside a rounded rect."""
    x0, y0, x1, y1 = [int(round(v)) for v in rect]
    H, W = dst.shape[:2]
    cx0, cy0, cx1, cy1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
    if cx1 <= cx0 or cy1 <= cy0:
        return
    m = rr_mask(x1 - x0, y1 - y0, radius)[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0][..., None] * alpha
    roi = dst[cy0:cy1, cx0:cx1]
    base = cv2.blur(roi, (21, 21)) if blur and roi.shape[0] > 4 and roi.shape[1] > 4 else roi
    out = base.astype(np.float32) * (1 - 0.85) + np.array(color, np.float32) * 0.85
    dst[cy0:cy1, cx0:cx1] = (roi * (1 - m) + out * m).astype(np.uint8)


def rr_outline(dst, rect, color, thick=4, radius=18, alpha=1.0, glow=0):
    """Rounded-rect outline with optional soft glow."""
    x0, y0, x1, y1 = [int(round(v)) for v in rect]
    pad = thick + glow * 2 + 4
    H, W = dst.shape[:2]
    bx0, by0, bx1, by1 = max(x0 - pad, 0), max(y0 - pad, 0), min(x1 + pad, W), min(y1 + pad, H)
    if bx1 <= bx0 or by1 <= by0:
        return
    w, h = bx1 - bx0, by1 - by0
    im = Image.new("L", (w * 2, h * 2), 0)
    ImageDraw.Draw(im).rounded_rectangle([(x0 - bx0) * 2, (y0 - by0) * 2, (x1 - bx0) * 2, (y1 - by0) * 2],
                                         radius=radius * 2, outline=255, width=thick * 2)
    m = np.asarray(im.resize((w, h), Image.LANCZOS), np.float32) / 255.0
    if glow:
        g = cv2.GaussianBlur(m, (0, 0), glow) * 1.6
        m = np.clip(np.maximum(m, g), 0, 1)
    m = m[..., None] * alpha
    roi = dst[by0:by1, bx0:bx1].astype(np.float32)
    dst[by0:by1, bx0:bx1] = (roi * (1 - m) + np.array(color, np.float32) * m).astype(np.uint8)


def dim_outside(dst, rect, amount, radius=18):
    """Spotlight: darken everything except a rounded rect."""
    if amount <= 0.01:
        return
    H, W = dst.shape[:2]
    keep = np.zeros((H, W), np.float32)
    x0, y0, x1, y1 = [int(round(v)) for v in rect]
    cx0, cy0, cx1, cy1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
    if cx1 > cx0 and cy1 > cy0:
        keep[cy0:cy1, cx0:cx1] = rr_mask(x1 - x0, y1 - y0, radius)[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0]
    k = 1 - amount * (1 - keep)
    dst[:] = (dst.astype(np.float32) * k[..., None]).astype(np.uint8)


def pill(text, face="mono", size=26, fg=IVORY, bg=RED, padx=16, pady=8, tracking=0.08):
    t = text_sprite(text, face, size, fg, tracking, pad=0)
    h, w = t.shape[0] + pady * 2, t.shape[1] + padx * 2
    spr = np.zeros((h, w, 4), np.float32)
    spr[..., :3] = bg
    spr[..., 3] = rr_mask(w, h, h // 2)
    a = t[..., 3:4]
    spr[pady:pady + t.shape[0], padx:padx + t.shape[1], :3] = (
        spr[pady:pady + t.shape[0], padx:padx + t.shape[1], :3] * (1 - a) + t[..., :3] * a)
    return spr


def glitch(spr, amount, seed):
    """Horizontal slice displacement + chromatic split. amount 0..1."""
    if amount <= 0.01:
        return spr
    r = np.random.default_rng(seed)
    out = spr.copy()
    h, w = spr.shape[:2]
    for _ in range(int(3 + 6 * amount)):
        y = r.integers(0, max(h - 2, 1))
        hh = int(r.integers(2, max(3, h // 5)))
        dx = int(r.normal(0, 22 * amount))
        out[y:y + hh] = np.roll(out[y:y + hh], dx, axis=1)
    d = int(8 * amount) + 1
    res = out.copy()
    res[..., 2] = np.roll(out[..., 2], d, axis=1)  # red channel drift
    res[..., 0] = np.roll(out[..., 0], -d, axis=1)
    res[..., 3] = np.maximum(out[..., 3], np.roll(out[..., 3], d, axis=1) * 0.6)
    return res


def ease_out_back(x, s=1.70158):
    x = min(max(x, 0.0), 1.0) - 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = min(max(x, 0.0), 1.0)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def env(t, t0, t1, fin=0.25, fout=0.2):
    """0..1 envelope with fade in/out."""
    if t < t0 or t > t1:
        return 0.0
    return min(1.0, (t - t0) / fin if fin else 1.0, (t1 - t) / fout if fout else 1.0)


@lru_cache(8)
def brand_background(W, H, seed=7):
    """Deep black field: radial falloff, fine grid, faint red bloom, film grain."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = W * 0.5, H * 0.42
    d = np.sqrt(((xx - cx) / W) ** 2 + ((yy - cy) / H) ** 2)
    base = 8 + 14 * np.exp(-d * 3.2)
    img = np.stack([base, base, base * 1.02], axis=2)
    grid = ((xx % 60 < 1.2) | (yy % 60 < 1.2)).astype(np.float32) * 5 * np.exp(-d * 2.2)
    img += grid[..., None]
    bloom = np.exp(-(((xx - W * 0.85) / (W * 0.5)) ** 2 + ((yy - H * 0.1) / (H * 0.35)) ** 2)) * 22
    img[..., 2] += bloom
    img[..., 1] += bloom * 0.18
    img[..., 0] += bloom * 0.2
    img += np.random.default_rng(seed).normal(0, 1.6, img.shape).astype(np.float32)
    out = np.clip(img, 0, 255).astype(np.uint8)
    out.setflags(write=False)
    return out


def lock_icon(size=34, color=IVORY):
    s = size
    im = Image.new("L", (s, s), 0)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([s * 0.16, s * 0.44, s * 0.84, s * 0.96], radius=s * 0.1, fill=255)
    d.arc([s * 0.28, s * 0.08, s * 0.72, s * 0.62], 180, 360, fill=255, width=max(2, s // 9))
    d.line([s * 0.28 + 1, s * 0.35, s * 0.28 + 1, s * 0.47], fill=255, width=max(2, s // 9))
    d.line([s * 0.72 - 1, s * 0.35, s * 0.72 - 1, s * 0.47], fill=255, width=max(2, s // 9))
    a = np.asarray(im, np.float32) / 255
    spr = np.zeros((s, s, 4), np.float32)
    spr[..., :3] = color
    spr[..., 3] = a
    return spr
