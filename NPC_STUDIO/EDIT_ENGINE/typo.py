"""Kinetic typography: per-glyph sprites, laid out with kerning and animated tracking.

A Text is built once per process (glyphs rendered with FreeType at a high base
size), then drawn every frame through a `GlyphState` function that sets each
glyph's offset, scale, opacity, blur and horizontal slicing. Fill is a vertical
white -> silver gradient; shadow and glow are derived from the text alpha.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT_DIR = Path(__file__).resolve().parent.parent / "BRAND/fonts"
FONTS = {
    "anton": FONT_DIR / "Anton-Regular.ttf",
    "barlow_xb": FONT_DIR / "BarlowCondensed-ExtraBold.ttf",
    "barlow_sb": FONT_DIR / "BarlowCondensed-SemiBold.ttf",
    "barlow_md": FONT_DIR / "BarlowCondensed-Medium.ttf",
    "mono": FONT_DIR / "JetBrainsMono-Medium.ttf",
}

WHITE = np.float32([1.0, 1.0, 1.0])
SILVER = np.float32([0.80, 0.83, 0.87])
EMERALD = np.float32([0.22, 0.95, 0.58])   # muted neon green accent
ICE = np.float32([0.78, 0.88, 1.0])


@dataclass
class GlyphState:
    dx: float = 0.0        # px offset (at final size)
    dy: float = 0.0
    scale: float = 1.0
    alpha: float = 1.0
    blur: float = 0.0      # px
    slice_shift: float = 0.0   # horizontal tearing amplitude (px)
    slice_seed: int = 0


class Text:
    def __init__(self, s: str, font: str, size_px: float, tracking: float = 0.0, fill=(WHITE, SILVER),
                 accent=None, base_scale: float = 1.0):
        """size_px: cap height target in output px; tracking in em."""
        self.s, self.size, self.tracking = s, size_px, tracking
        self.fill, self.accent = fill, accent
        render_px = int(size_px * 1.45 * max(1.0, base_scale))  # font px for given cap height (Anton/Barlow caps ~0.69-0.72 em)
        self.ft = ImageFont.truetype(str(FONTS[font]), render_px)
        cap = self.ft.getbbox("H")
        self.k = size_px / (cap[3] - cap[1])  # glyph px -> output px at scale 1
        self.cap_top = cap[1]
        self.glyphs = []
        for i, ch in enumerate(s):
            if ch == " ":
                self.glyphs.append(None)
                continue
            l, t, r, b = self.ft.getbbox(ch)
            pad = 4
            im = Image.new("L", (r - l + 2 * pad, b - t + 2 * pad), 0)
            ImageDraw.Draw(im).text((pad - l, pad - t), ch, font=self.ft, fill=255)
            a = np.asarray(im, np.float32) / 255
            self.glyphs.append({"a": a, "ox": l - pad, "oy": t - pad})
        # advances with kerning: x of glyph i = length of s[:i]
        self.adv = [self.ft.getlength(s[:i]) for i in range(len(s) + 1)]
        self.em = self.ft.size

    def width(self, tracking=None) -> float:
        tr = self.tracking if tracking is None else tracking
        n = len(self.s)
        return (self.adv[-1] + tr * self.em * (n - 1)) * self.k

    def layout(self, tracking=None):
        tr = self.tracking if tracking is None else tracking
        return [(self.adv[i] + tr * self.em * i) * self.k for i in range(len(self.s))]

    def draw(self, canvas: np.ndarray, cx: float, cy: float, state=None, tracking=None, scale: float = 1.0,
             opacity: float = 1.0, shadow: float = 0.55, glow: float = 0.16, accent_glow: float = 0.0,
             mask_fn=None, rot: float = 0.0, shine: float | None = None):
        """Draw onto a premultiplied RGBA canvas; (cx, cy) = center of the cap-height box.

        state(i, n) -> GlyphState per glyph. mask_fn(xs_layer) optional reveal mask on the text layer."""
        if opacity <= 0.002:
            return canvas
        H, W = canvas.shape[:2]
        n = len(self.s)
        xs = self.layout(tracking)
        tw = self.width(tracking)
        x0 = cx - tw * scale / 2
        cap_top_y = cy - self.size * scale / 2
        # text alpha layer for this draw (full frame is wasteful: use a bbox)
        pad = int(80 + self.size * scale * 0.6)
        bx0, by0 = int(max(0, x0 - pad)), int(max(0, cap_top_y - pad))
        bx1, by1 = int(min(W, x0 + tw * scale + pad)), int(min(H, cap_top_y + self.size * scale + pad))
        if bx1 <= bx0 or by1 <= by0:
            return canvas
        layer = np.zeros((by1 - by0, bx1 - bx0), np.float32)
        for i, g in enumerate(self.glyphs):
            if g is None:
                continue
            st = state(i, n) if state else GlyphState()
            if st.alpha <= 0.003:
                continue
            k = self.k * scale * st.scale
            a = g["a"]
            gh, gw = a.shape
            tw_, th_ = max(1, int(round(gw * k))), max(1, int(round(gh * k)))
            sa = cv2.resize(a, (tw_, th_), interpolation=cv2.INTER_AREA if k < 1 else cv2.INTER_CUBIC)
            if st.blur > 0.4:
                sa = cv2.GaussianBlur(np.pad(sa, int(st.blur * 2.5) + 1), (0, 0), st.blur)
                off = int(st.blur * 2.5) + 1
            else:
                off = 0
            if st.slice_shift:
                rng = np.random.default_rng(st.slice_seed)
                rows = sa.shape[0]
                cut = np.sort(rng.integers(0, rows, 5))
                prev = 0
                out = np.zeros_like(sa)
                for c in list(cut) + [rows]:
                    sh = int(rng.normal(0, 1) * st.slice_shift)
                    out[prev:c] = np.roll(sa[prev:c], sh, axis=1)
                    prev = c
                sa = out
            # glyph position: pen x + bbox offset, scaled about the glyph's own center
            gx = x0 + xs[i] * scale + g["ox"] * self.k * scale
            gy = cap_top_y + (g["oy"] - self.cap_top) * self.k * scale
            gcx, gcy = gx + gw * self.k * scale / 2, gy + gh * self.k * scale / 2
            px = int(round(gcx - tw_ / 2 + st.dx - off - bx0))
            py = int(round(gcy - th_ / 2 + st.dy - off - by0))
            _blit_max(layer, sa * st.alpha, px, py)
        if mask_fn is not None:
            layer *= mask_fn(np.arange(bx0, bx1, dtype=np.float32)[None, :], np.arange(by0, by1, dtype=np.float32)[:, None])
        if rot:
            M = cv2.getRotationMatrix2D((cx - bx0, cy - by0), rot, 1.0)
            layer = cv2.warpAffine(layer, M, layer.shape[::-1], flags=cv2.INTER_LINEAR)
        layer *= opacity
        if layer.max() <= 0.002:
            return canvas
        # gradient fill
        ys = (np.arange(by0, by1, dtype=np.float32) - cap_top_y) / max(1.0, self.size * scale)
        g = np.clip(ys, 0, 1)[:, None, None]
        top, bot = self.fill
        col = top * (1 - g) + bot * g
        if shine is not None:  # diagonal light band crossing the word, slightly cool
            xs_ = (np.arange(bx0, bx1, dtype=np.float32)[None, :] - x0) / max(1.0, tw * scale)
            ys_ = (np.arange(by0, by1, dtype=np.float32)[:, None] - cap_top_y) / max(1.0, tw * scale)
            band = np.exp(-((xs_ + 0.35 * ys_ - (-0.2 + 1.4 * shine)) / 0.07) ** 2)
            col = col * (1 - 0.5 * band[..., None]) + band[..., None] * np.float32([0.75, 1.0, 0.88]) * 1.0
        reg = canvas[by0:by1, bx0:bx1]
        # shadow (below), glow and accent glow (additive-ish, as premultiplied light with low alpha)
        if shadow > 0:
            sh = cv2.GaussianBlur(np.roll(layer, int(6 + self.size * scale * 0.04), axis=0), (0, 0), 6 + self.size * scale * 0.06) * shadow
            reg[..., :3] *= (1 - sh[..., None])
            reg[..., 3] = reg[..., 3] + sh * (1 - reg[..., 3])
        if glow > 0 or accent_glow > 0:
            gl = cv2.GaussianBlur(layer, (0, 0), 8 + self.size * scale * 0.12)
            if glow > 0:
                reg[..., :3] += gl[..., None] * glow * WHITE
            if accent_glow > 0:
                gl2 = cv2.GaussianBlur(layer, (0, 0), 16 + self.size * scale * 0.25)
                reg[..., :3] += gl2[..., None] * accent_glow * (self.accent if self.accent is not None else EMERALD)
        a = layer[..., None]
        reg[..., :3] = reg[..., :3] * (1 - a) + col * a
        reg[..., 3:4] = reg[..., 3:4] * (1 - a) + a
        canvas[by0:by1, bx0:bx1] = reg
        return canvas


def _blit_max(dst: np.ndarray, src: np.ndarray, x: int, y: int):
    H, W = dst.shape
    h, w = src.shape
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    np.maximum(dst[y0:y1, x0:x1], src[y0 - y:y1 - y, x0 - x:x1 - x], out=dst[y0:y1, x0:x1])


# ----------------------------------------------------------------------------- animation states

def st_slam(p: float, i: int, n: int, overshoot=0.06) -> GlyphState:
    """Kinetic scale impact: whole word drops from large/blurred to crisp with a tiny overshoot."""
    from fx import ease_out_expo
    e = ease_out_expo(p)
    sc = 1 + 0.55 * (1 - e) - overshoot * math.sin(min(1, p * 1.6) * math.pi) * (p > 0.35)
    return GlyphState(scale=sc, alpha=1.0, blur=max(0, 7 * (1 - e) - 0.5))  # full presence on the hit frame


def st_assemble(p: float, i: int, n: int, spread=0.55, rise=60) -> GlyphState:
    """Letter-by-letter assembly: staggered glyphs rise into place from blur."""
    from fx import ease_out_cubic, clamp01
    d = spread * i / max(1, n - 1)
    q = clamp01((p - d) / (1 - spread))
    e = ease_out_cubic(q)
    return GlyphState(dy=rise * (1 - e), alpha=q ** 0.7, blur=6 * (1 - e), scale=1 + 0.08 * (1 - e))


def st_fragment(p: float, i: int, n: int, seed: int, amp=90) -> GlyphState:
    """Digital exit: glyph strips tear sideways and fade."""
    from fx import clamp01
    q = clamp01(p)
    return GlyphState(alpha=1 - q ** 1.4, slice_shift=amp * q ** 0.6, slice_seed=seed * 131 + i * 7 + int(p * 20),
                      dx=((i * 37 % 11) - 5) * 3 * q)


def st_exit_dir(p: float, i: int, n: int, dx=-420, stagger=0.25) -> GlyphState:
    from fx import ease_in_expo, clamp01
    q = clamp01((p - stagger * (n - 1 - i) / max(1, n - 1)) / (1 - stagger))
    e = ease_in_expo(q)
    return GlyphState(dx=dx * e, alpha=1 - e ** 2, blur=8 * e)
