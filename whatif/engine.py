"""Vertical 'What if...' video engine: animated scenes + population counter overlay.

Usage: python3 engine.py <story_name> <out.mp4>
"""
import math
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 576, 1024, 30
PAD = 1.12  # background is rendered larger so the camera can push in
BW, BH = int(W * PAD), int(H * PAD)
FONT_DIR = "/usr/share/fonts/truetype/"
F_LABEL = ImageFont.truetype(FONT_DIR + "dejavu/DejaVuSans-Bold.ttf", 13)
F_NUM = ImageFont.truetype(FONT_DIR + "dejavu/DejaVuSans.ttf", 40)
F_CAP = ImageFont.truetype(FONT_DIR + "liberation/LiberationSerif-Italic.ttf", 25)
F_TITLE = ImageFont.truetype(FONT_DIR + "liberation/LiberationSerif-Regular.ttf", 33)
F_CTA = ImageFont.truetype(FONT_DIR + "dejavu/DejaVuSansMono-Bold.ttf", 13)


# ---------------------------------------------------------------- helpers
def vgrad(h, w, top, bottom):
    t = np.linspace(0, 1, h)[:, None, None]
    return np.broadcast_to(np.array(top) * (1 - t) + np.array(bottom) * t, (h, w, 3)).astype(np.float32)


def add_glow(arr, x, y, r, color, strength=1.0):
    h, w, _ = arr.shape
    x0, x1, y0, y1 = max(0, int(x - r)), min(w, int(x + r)), max(0, int(y - r)), min(h, int(y + r))
    if x0 >= x1 or y0 >= y1:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    d = np.sqrt((xx - x) ** 2 + (yy - y) ** 2) / r
    g = np.clip(1 - d, 0, 1) ** 2 * strength
    arr[y0:y1, x0:x1] += g[..., None] * np.array(color, np.float32)


def to_img(arr):
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def blank_thresh():
    return np.full((BH, BW), np.inf, np.float32)


# ---------------------------------------------------------------- scenes
# Each builder returns (A, B, T, dyn): base layer, alternate layer, per-pixel
# threshold map (pixel shows B once progress >= T) and a per-frame draw hook.
def sc_city(rng, p):
    A = vgrad(BH, BW, (18, 8, 40), (60, 20, 70))
    for _ in range(140):  # stars
        A[rng.integers(0, BH // 3), rng.integers(0, BW)] += 120
    B = A.copy()
    T = blank_thresh()
    lit = (255, 214, 140)
    # Two canyon walls of skyscrapers (looking down an avenue) + distant skyline
    for side in (0, 1):
        x = 0
        while x < BW * 0.42:
            bw = rng.integers(40, 90)
            top = rng.integers(0, int(BH * 0.25))
            bx = x if side == 0 else BW - x - bw
            col = np.array(rng.integers(20, 45, 3), np.float32)
            A[top:, bx:bx + bw] = col
            B[top:, bx:bx + bw] = col
            for wy in range(top + 8, int(BH * 0.75), 14):
                for wx in range(bx + 5, bx + bw - 6, 11):
                    if rng.random() < 0.65:
                        th = rng.random()
                        c = np.array(lit) * rng.uniform(0.6, 1.0)
                        A[wy:wy + 7, wx:wx + 6] = c
                        B[wy:wy + 7, wx:wx + 6] = col * 0.8
                        T[wy:wy + 7, wx:wx + 6] = th
            if p.get("billboards", True) and rng.random() < 0.6:
                by = rng.integers(top + 40, int(BH * 0.55))
                bc = [(255, 40, 120), (40, 200, 255), (255, 200, 40), (140, 80, 255)][rng.integers(0, 4)]
                bh = rng.integers(50, 120)
                A[by:by + bh, bx + 4:bx + bw - 4] = np.array(bc) * 0.8
                add_glow(A, bx + bw / 2, by + bh / 2, 90, np.array(bc) * 0.35)
                B[by:by + bh, bx + 4:bx + bw - 4] = col * 0.7
                T[by:by + bh, bx + 4:bx + bw - 4] = rng.random()
            x += bw + rng.integers(0, 8)
    # crowd / street floor
    fy = int(BH * 0.62)
    floor = vgrad(BH - fy, BW, (40, 20, 40), (25, 15, 25))
    A[fy:] = floor
    B[fy:] = floor
    if p.get("crowd", 0):
        n = int(p["crowd"])
        for _ in range(n):
            y = fy + int((rng.random() ** 1.6) * (BH - fy))
            s = 2 + int((y - fy) / (BH - fy) * 9)
            x = rng.integers(0, BW)
            c = np.array(rng.integers(30, 220, 3), np.float32)
            th = rng.random()
            A[y:y + s * 2, x:x + s] = c * 0.6
            A[y - s:y, x:x + s] = (200, 150, 120)
            T[y - s:y + s * 2, x:x + s] = th
        add_glow(A, BW / 2, fy + 40, 260, (120, 30, 60), 0.6)
    add_glow(A, BW / 2, BH * 0.3, 300, (80, 40, 120), 0.4)
    add_glow(B, BW / 2, BH * 0.3, 300, (30, 20, 60), 0.4)

    def dyn(img, d, t, prog):
        if p.get("confetti"):
            r = np.random.default_rng(int(t * 7))
            for i in range(60):
                x = (i * 97 + t * 30) % W
                y = (i * 53 + t * 80 * (1 + i % 3)) % H
                d.rectangle([x, y, x + 3, y + 2], fill=tuple(int(v) for v in r.integers(120, 255, 3)))
    return A, B, T, dyn


def sc_corridor(rng, p):
    tint = np.array(p.get("tint", (230, 235, 240)), np.float32)
    img = Image.new("RGB", (BW, BH))
    d = ImageDraw.Draw(img)
    cx, cy = BW / 2, BH * 0.42
    vw, vh = 70, 90  # far wall
    far = [cx - vw, cy - vh, cx + vw, cy + vh]
    c = lambda k: tuple(int(v * k) for v in tint)
    d.polygon([(0, 0), (BW, 0), (far[2], far[1]), (far[0], far[1])], fill=c(0.55))  # ceiling
    d.polygon([(0, BH), (BW, BH), (far[2], far[3]), (far[0], far[3])], fill=c(0.62))  # floor
    d.polygon([(0, 0), (far[0], far[1]), (far[0], far[3]), (0, BH)], fill=c(0.45))
    d.polygon([(BW, 0), (far[2], far[1]), (far[2], far[3]), (BW, BH)], fill=c(0.40))
    d.rectangle(far, fill=c(0.7))
    d.rectangle([cx - 18, cy + 20, cx + 18, cy + vh], fill=c(0.35))
    for k in np.linspace(0.08, 0.95, 9):  # ceiling lights + doors receding
        s = 1 - k
        ly = cy - vh - (cy - vh) * s * 0.92
        lw = 30 + 230 * s
        d.rectangle([cx - lw / 2, ly - 6 * s - 2, cx + lw / 2, ly + 6 * s + 2], fill=(255, 255, 245))
        for side in (-1, 1):
            dx = cx + side * (vw + (BW / 2 - vw) * s * 0.95)
            dh = vh + (BH * 0.58 - vh) * s
            d.rectangle([min(dx, dx - side * 40 * s), cy - dh * 0.6, max(dx, dx - side * 40 * s), cy + dh], outline=c(0.25), width=max(1, int(3 * s)))
    for _ in range(14):  # papers on floor
        x, y = rng.uniform(0, BW), rng.uniform(BH * 0.65, BH)
        d.rectangle([x, y, x + 30, y + 14], fill=(235, 235, 230))
    d.line([(BW * 0.12, BH), (far[0] + 10, far[3])], fill=(40, 70, 140), width=6)
    d.line([(BW * 0.88, BH), (far[2] - 10, far[3])], fill=(40, 70, 140), width=6)
    A = np.asarray(img.filter(ImageFilter.GaussianBlur(1.2)), np.float32).copy()
    add_glow(A, cx, cy, 220, tint * 0.25)
    B = A * 0.25
    T = np.full((BH, BW), 0.5, np.float32)

    def dyn(img, d, t, prog):
        pass
    return A, B, T, dyn


def sc_vigil(rng, p):
    A = vgrad(BH, BW, (10, 10, 25), (25, 18, 22))
    hy = int(BH * 0.33)
    if p.get("tower"):
        tx = BW / 2
        for i in range(30):
            y = hy - i * 9
            w = 4 + (30 - i) * 2.2
            A[max(0, y - 9):y, int(tx - w / 2):int(tx + w / 2)] = (255, 220, 170)
        add_glow(A, tx, hy - 140, 240, (255, 200, 140), 0.6)
    for x in range(0, BW, 60):  # building row on horizon
        h = rng.integers(60, 140)
        A[hy - h:hy, x:x + 56] = (40, 35, 55)
        for wy in range(hy - h + 10, hy - 6, 16):
            for wx in range(x + 6, x + 50, 12):
                if rng.random() < 0.3:
                    A[wy:wy + 6, wx:wx + 5] = (255, 200, 130)
    A[hy:] = vgrad(BH - hy, BW, (35, 30, 35), (55, 45, 45))
    glowA = np.zeros_like(A)
    glowB = np.zeros_like(A)
    for i in range(int(p.get("candles", 900))):
        y = hy + (rng.random() ** 1.8) * (BH - hy)
        s = 0.3 + (y - hy) / (BH - hy) * 2.5
        x = rng.uniform(0, BW)
        A[int(y):int(y + 3 * s + 1), int(x):int(x + s + 1)] = (230, 220, 200)
        tgt = glowA if i % 2 else glowB
        add_glow(tgt, x, y - 2, 6 + 9 * s, (255, 170, 70), 0.9)
    A += (glowA + glowB) * 0.5
    T = blank_thresh()
    gA, gB = glowA * 0.5, glowB * 0.5
    base = A - gA - gB

    state = {"base": base}

    def dyn(img, d, t, prog):
        pass
    # flicker is applied through the 'arr' hook below
    def arr_hook(arr, t):
        k1 = 0.85 + 0.15 * math.sin(t * 11.0)
        k2 = 0.85 + 0.15 * math.sin(t * 13.7 + 1)
        return state["base"] + gA * k1 + gB * k2
    dyn.arr_hook = arr_hook
    return A, A, T, dyn


def sc_ticker(rng, p):
    A = vgrad(BH, BW, (40, 0, 5), (15, 0, 2))
    for x in range(0, BW, 40):
        A[:, x] += 25
    for y in range(0, BH, 40):
        A[y, :] += 25
    T = blank_thresh()
    big = p.get("big", "-46.8%")
    head = p.get("head", "GLOBAL INDEX")
    ftk = ImageFont.truetype(FONT_DIR + "dejavu/DejaVuSansMono-Bold.ttf", 22)
    fbig = ImageFont.truetype(FONT_DIR + "dejavu/DejaVuSans-Bold.ttf", 86)
    rows = [f"{s} {v:+.1f}%" for s, v in zip(["NRSY", "DJIX", "FTSX", "NKEI", "DAXX", "HSIX", "CRUD", "GOLD"], rng.uniform(-38, -4, 8))]
    ticker = "   ▼ ".join(rows)

    def dyn(img, d, t, prog):
        off = -(t * 70) % 1200
        for k in (0, 1):
            d.text((off + k * 1200 - 600, 70), ticker, font=ftk, fill=(255, 70, 70))
        d.text((40, 150), head, font=ftk, fill=(255, 120, 120))
        d.text((40, 185), ("▲" if big.startswith("+") else "▼") + big, font=fbig, fill=(255, 50, 50))
        pts = []
        r = np.random.default_rng(3)
        y = 330
        for i in range(int(60 * min(1, 0.2 + prog))):
            y += r.normal(2.4, 6)
            pts.append((40 + i * 8.3, y))
        if len(pts) > 1:
            d.line(pts, fill=(255, 40, 40), width=4)
        if int(t * 2) % 2 == 0:
            d.rectangle([W - 120, 150, W - 40, 175], fill=(200, 0, 0))
            d.text((W - 112, 152), "HALT", font=ftk, fill=(255, 255, 255))
    return A, A, T, dyn


def sc_street(rng, p):
    img = Image.new("RGB", (BW, BH))
    d = ImageDraw.Draw(img)
    cx, cy = BW / 2, BH * 0.40
    sky = to_img(vgrad(BH, BW, (8, 10, 25), (25, 20, 35)))
    img.paste(sky)
    d.polygon([(0, BH), (BW, BH), (cx + 20, cy), (cx - 20, cy)], fill=(30, 30, 38))  # road
    d.polygon([(0, BH * 0.7), (0, BH), (BW * 0.18, BH), (cx - 24, cy)], fill=(50, 45, 50))
    d.polygon([(BW, BH * 0.7), (BW, BH), (BW * 0.82, BH), (cx + 24, cy)], fill=(50, 45, 50))
    for side in (-1, 1):  # building facades
        pts = [(cx + side * 26, cy - 60), (cx + side * 26, cy), (BW / 2 + side * BW / 2, BH * 0.72), (BW / 2 + side * BW / 2, 0)]
        d.polygon(pts, fill=(55, 30, 30) if side < 0 else (45, 28, 35))
        for k in np.linspace(0.1, 0.95, 8):
            x = cx + side * (26 + (BW / 2 - 26) * k)
            yb = cy + (BH * 0.72 - cy) * k
            wdt = 40 * k
            d.rectangle([min(x, x - side * wdt), yb - 120 * k, max(x, x - side * wdt), yb - 10 * k], fill=(255, 150, 70) if rng.random() < p.get("lit", 0.6) else (35, 25, 25))
    for _ in range(40):
        x, y = rng.uniform(0, BW), rng.uniform(BH * 0.6, BH)
        d.ellipse([x, y, x + rng.uniform(5, 20), y + rng.uniform(3, 8)], fill=(80, 75, 70))
    if p.get("sign"):
        fs = ImageFont.truetype(FONT_DIR + "dejavu/DejaVuSans-Bold.ttf", 30)
        d.rectangle([BW - 90, 140, BW - 40, 470], fill=(200, 20, 30))
        for i, ch in enumerate(p["sign"]):
            d.text((BW - 76, 150 + i * 38), ch, font=fs, fill=(255, 230, 230))
    A = np.asarray(img, np.float32).copy()
    for k in np.linspace(0.15, 1, 5):  # street lamps
        for side in (-1, 1):
            x = cx + side * (30 + (BW * 0.42) * k)
            y = cy + (BH * 0.25) * k - 260 * k
            add_glow(A, x, y, 40 + 120 * k, (255, 170, 80), 0.7)
    T = blank_thresh()

    def dyn(img, d, t, prog):
        if p.get("fire"):
            pass
        n = p.get("ash", 30)
        for i in range(n):
            x = (i * 131 + math.sin(t + i) * 20) % W
            y = (i * 71 + t * 25 * (1 + i % 4)) % H
            d.ellipse([x, y, x + 2, y + 2], fill=(200, 190, 180))

    if p.get("fire"):
        def arr_hook(arr, t):
            a = arr.copy()
            add_glow(a, BW * 0.3, BH * 0.62, 180 + 20 * math.sin(t * 9), (255, 110, 30), 0.8 + 0.2 * math.sin(t * 13))
            return a
        dyn.arr_hook = arr_hook
    return A, A, T, dyn


def sc_sky(rng, p):
    A = vgrad(BH, BW, p.get("top", (40, 60, 110)), p.get("bottom", (240, 140, 90)))
    for _ in range(9):
        cx, cy = rng.uniform(0, BW), rng.uniform(BH * 0.2, BH * 0.8)
        for _ in range(6):
            add_glow(A, cx + rng.uniform(-80, 80), cy + rng.uniform(-20, 20), rng.uniform(50, 110), (255, 230, 230), 0.12)
    T = blank_thresh()

    def dyn(img, d, t, prog):
        if not p.get("plane"):
            return
        x = W * 0.2 + prog * W * 0.45
        y = H * 0.18 + (prog ** 1.6) * H * 0.55
        for k in range(30):  # smoke trail
            tx = x - k * 9
            ty = y - k * 9 * (0.4 + prog)
            r = 4 + k * 0.9
            g = 60 + k * 3
            d.ellipse([tx - r, ty - r, tx + r, ty + r], fill=(g, g, g))
        ang = 0.3 + prog * 0.6
        ca, sa = math.cos(ang), math.sin(ang)
        body = [(-40, -5), (40, -5), (50, 0), (40, 5), (-40, 5)]
        wing = [(-5, 0), (10, 0), (-10, 40), (-20, 40)]
        tr = lambda pts: [(x + px * ca - py * sa, y + px * sa + py * ca) for px, py in pts]
        d.polygon(tr(body), fill=(30, 30, 40))
        d.polygon(tr(wing), fill=(25, 25, 35))
        d.ellipse([x - 8, y - 8, x + 8, y + 8], fill=(255, 140, 40))
    return A, A, T, dyn


def sc_lab(rng, p):
    A = vgrad(BH, BW, (0, 30, 35), (0, 12, 18))
    cx = BW / 2
    A[int(BH * 0.5):] = vgrad(BH - int(BH * 0.5), BW, (0, 25, 28), (0, 45, 45))
    for k in np.linspace(0.12, 1, 6):  # two rows of glowing tubes, far to near
        for side in (-1, 1):
            x = cx + side * (55 + 250 * k)
            y = BH * 0.5 + 330 * k
            w, h = 12 + 70 * k, 40 + 300 * k
            add_glow(A, x, y - h / 2, w * 1.5, (0, 200, 170), 0.35)
            A[int(y - h):int(y), int(x - w / 2):int(x + w / 2)] = np.array((60, 235, 200)) * (0.45 + 0.4 * k)
            A[int(y - h):int(y), int(x - w / 6):int(x - w / 10)] = (210, 255, 245)
            A[int(y - h - 8 * k - 2):int(y - h), int(x - w / 2 - 4):int(x + w / 2 + 4)] = (60, 70, 75)
            A[int(y):int(y + 8 * k + 2), int(x - w / 2 - 4):int(x + w / 2 + 4)] = (60, 70, 75)
    for y in range(0, int(BH * 0.2), 60):
        A[y:y + 6, :] = (150, 255, 230)
    T = blank_thresh()
    fs = ImageFont.truetype(FONT_DIR + "dejavu/DejaVuSansMono-Bold.ttf", 26)

    def dyn(img, d, t, prog):
        d.rectangle([W * 0.55, H * 0.22, W * 0.88, H * 0.29], fill=(10, 30, 35), outline=(80, 255, 220), width=2)
        d.text((W * 0.58, H * 0.235), p.get("screen", "{:,}").format(int(12000 + t * 37)), font=fs, fill=(150, 255, 230))
        for i in range(25):
            x = (i * 89) % W
            y = H - ((t * 40 + i * 41) % H)
            d.ellipse([x, y, x + 3, y + 3], fill=(120, 255, 220))
    return A, A, T, dyn


def sc_field(rng, p):
    A = vgrad(BH, BW, p.get("top", (90, 150, 220)), p.get("bottom", (250, 210, 160)))
    add_glow(A, BW * 0.7, BH * 0.22, 160, (255, 230, 150), 0.9)
    hy = int(BH * 0.42)
    yy = np.arange(BH)[:, None]
    xx = np.arange(BW)[None, :]
    hill = hy + 25 * np.sin(xx / 90.0)
    mask = yy > hill
    g = np.array(p.get("grass", (80, 140, 60)), np.float32)
    A = np.where(mask[..., None], g * (0.6 + 0.5 * yy[..., None] / BH), A).astype(np.float32)
    B = A.copy()
    dead = np.array((120, 95, 60), np.float32)
    B = np.where(mask[..., None], dead * (0.6 + 0.5 * yy[..., None] / BH), B).astype(np.float32)
    T = np.where(mask, rng.random((BH, BW)).astype(np.float32) * 0.2 + 0.4, np.inf).astype(np.float32)
    cols = [(255, 90, 120), (255, 220, 60), (250, 250, 255), (180, 90, 255), (255, 140, 40)]
    for _ in range(int(p.get("flowers", 1500))):
        y = int(hy + 20 + (rng.random() ** 1.5) * (BH - hy - 20))
        s = 1 + int((y - hy) / (BH - hy) * 7)
        x = rng.integers(0, BW - s)
        th = rng.random()
        A[y:y + s, x:x + s] = cols[rng.integers(0, 5)]
        A[y + s:y + 3 * s, x + s // 2:x + s // 2 + 1] = (40, 100, 40)
        B[y:y + s, x:x + s] = (90, 70, 45)
        T[y:y + 3 * s, x:x + s] = th
    bees = p.get("bees", (0, 0))

    def dyn(img, d, t, prog):
        n = int(bees[0] + (bees[1] - bees[0]) * prog)
        for i in range(n):
            x = W * 0.5 + math.sin(t * (1.3 + i % 5 * 0.3) + i) * W * 0.4
            y = H * 0.6 + math.sin(t * (2.1 + i % 3 * 0.4) + i * 2) * H * 0.2
            d.ellipse([x - 4, y - 3, x + 4, y + 3], fill=(250, 200, 30))
            d.line([x - 2, y - 3, x - 2, y + 3], fill=(30, 20, 10), width=2)
            d.ellipse([x - 3, y - 8, x + 3, y - 3], fill=(230, 240, 255))
    return A, B, T, dyn


def sc_screens(rng, p):
    A = vgrad(BH, BW, (10, 10, 20), (20, 20, 30))
    B = A.copy()
    T = blank_thresh()
    cols = [(60, 140, 255), (255, 80, 120), (80, 230, 160), (255, 200, 60), (190, 100, 255)]
    for gy in range(40, BH - 100, 120):
        for gx in range(20, BW - 100, 130):
            w, h = 110, 95
            c = np.array(cols[rng.integers(0, 5)], np.float32)
            A[gy:gy + h, gx:gx + w] = c * 0.5
            A[gy + 10:gy + 30, gx + 10:gx + w - 10] = c
            A[gy + 40:gy + 48, gx + 10:gx + w - 30] = (230, 230, 240)
            A[gy + 56:gy + 62, gx + 10:gx + w - 50] = (200, 200, 210)
            add_glow(A, gx + w / 2, gy + h / 2, 100, c * 0.25)
            B[gy:gy + h, gx:gx + w] = (8, 8, 10)
            B[gy - 3:gy + h + 3, gx - 3:gx] = (40, 40, 45)
            T[gy - 30:gy + h + 30, gx - 30:gx + w + 30] = rng.random()

    def dyn(img, d, t, prog):
        if p.get("nosignal") and prog > 0.5:
            f = ImageFont.truetype(FONT_DIR + "dejavu/DejaVuSansMono-Bold.ttf", 22)
            if int(t * 3) % 2:
                d.text((W / 2 - 80, H * 0.25), "NO CONNECTION", font=f, fill=(255, 80, 80))
    return A, B, T, dyn


def sc_fire(rng, p):
    A = vgrad(BH, BW, (5, 6, 15), (20, 12, 10))
    for _ in range(200):
        A[rng.integers(0, BH // 2), rng.integers(0, BW)] += 90
    for i in range(14):  # bare trees
        x = rng.uniform(0, BW)
        A[int(BH * 0.25):int(BH * 0.55), int(x):int(x + 4)] = (15, 12, 15)
    A[int(BH * 0.55):] = vgrad(BH - int(BH * 0.55), BW, (25, 18, 15), (10, 8, 8))
    T = blank_thresh()
    people = p.get("people", 6)

    def arr_hook(arr, t):
        a = arr.copy()
        k = 0.85 + 0.15 * math.sin(t * 12) * math.sin(t * 5.3)
        add_glow(a, BW / 2, BH * 0.66, 260 * k, (255, 120, 30), 0.9)
        add_glow(a, BW / 2, BH * 0.66, 60, (255, 220, 120), 1.0)
        return a

    def dyn(img, d, t, prog):
        cx, cy = W / 2, H * 0.66
        for i in range(people):
            ang = math.pi * (0.15 + 0.7 * i / max(1, people - 1))
            x = cx + math.cos(ang) * 140
            y = cy - math.sin(ang) * 25 + 40
            d.ellipse([x - 13, y - 75, x + 13, y - 49], fill=(15, 10, 10))
            d.rounded_rectangle([x - 22, y - 50, x + 22, y + 20], radius=12, fill=(18, 12, 12))
        for i in range(30):  # sparks
            sx = cx + math.sin(i * 3.1 + t * 2) * 30
            sy = cy - ((t * 80 + i * 23) % 260)
            d.ellipse([sx, sy, sx + 2, sy + 2], fill=(255, 200, 100))
    dyn.arr_hook = arr_hook
    return A, A, T, dyn


def sc_dark(rng, p):
    A = vgrad(BH, BW, (5, 8, 18), (15, 20, 40))
    for _ in range(300):
        A[rng.integers(0, BH), rng.integers(0, BW)] += rng.integers(60, 200)
    T = blank_thresh()

    def dyn(img, d, t, prog):
        if p.get("cursor") and int(t * 2) % 2 == 0:
            d.rectangle([W / 2 - 6, H * 0.32, W / 2 + 6, H * 0.32 + 30], fill=(230, 255, 230))
        if p.get("snow"):
            for i in range(80):
                x = (i * 67 + math.sin(t + i) * 15) % W
                y = (i * 43 + t * 30) % H
                d.ellipse([x, y, x + 2, y + 2], fill=(220, 225, 240))
    if p.get("light"):
        def arr_hook(arr, t):
            a = arr.copy()
            add_glow(a, BW / 2, BH * 0.72, 120 + 10 * math.sin(t * 6), (255, 200, 120), 0.9)
            return a
        dyn.arr_hook = arr_hook
    return A, A, T, dyn


SCENES = dict(city=sc_city, corridor=sc_corridor, vigil=sc_vigil, ticker=sc_ticker, street=sc_street,
              sky=sc_sky, lab=sc_lab, field=sc_field, screens=sc_screens, fire=sc_fire, dark=sc_dark)


# ---------------------------------------------------------------- overlay
def shadow_text(d, xy, text, font, fill=(255, 255, 255), anchor="la", spacing=6, align="left"):
    x, y = xy
    for ox, oy in ((2, 2), (1, 1), (0, 2)):
        d.multiline_text((x + ox, y + oy), text, font=font, fill=(0, 0, 0), anchor=anchor, spacing=spacing, align=align)
    d.multiline_text((x, y), text, font=font, fill=fill, anchor=anchor, spacing=spacing, align=align)


def spaced(s, n=1):
    return (" " * n).join(s) if n else s


def draw_overlay(img, sc, t, dur):
    d = ImageDraw.Draw(img)
    if sc.get("title"):
        a = ease(t / 0.8)
        col = tuple(int(255 * a) for _ in range(3))
        shadow_text(d, (W / 2, H * 0.43), sc["title"], F_TITLE, fill=col, anchor="mm", align="center")
        return
    if "counter" in sc:
        c0, c1 = sc["counter"]
        v = c0 + (c1 - c0) * ease(t / max(0.1, dur * sc.get("count_speed", 0.8)))
        x0, y0 = 34, H * 0.465
        shadow_text(d, (x0, y0), spaced(sc.get("label", "WORLD POPULATION").upper(), 0), F_LABEL)
        shadow_text(d, (x0 - 2, y0 + 16), sc.get("fmt", "{:,}").format(int(round(v))), F_NUM)
        if sc.get("sub"):
            shadow_text(d, (x0, y0 + 66), sc["sub"].upper(), F_LABEL)
    if sc.get("caption"):
        a = ease((t - 0.4) / 0.6)
        if a > 0:
            col = tuple(int(255 * a) for _ in range(3))
            shadow_text(d, (W / 2, H * 0.635), sc["caption"], F_CAP, fill=col, anchor="ma", align="center")


def end_card(sc, t):
    img = Image.new("RGB", (W, H), (12, 12, 14))
    d = ImageDraw.Draw(img)
    d.text((W / 2, H * 0.42), sc["title"], font=ImageFont.truetype(FONT_DIR + "liberation/LiberationSerif-Regular.ttf", 26), fill=(235, 235, 235), anchor="mm")
    a = ease((t - 0.8) / 1.0)
    g = int(200 * a)
    d.multiline_text((W / 2, H * 0.47), sc["lines"], font=F_CTA, fill=(g, g, g), anchor="ma", align="center", spacing=8)
    b = ease((t - 2.2) / 1.0)
    g = int(255 * b)
    # share arrow
    ax, ay = W / 2, H * 0.575
    d.line([(ax - 12, ay + 8), (ax - 12, ay), (ax + 8, ay - 8)], fill=(g, g, g), width=3)
    d.polygon([(ax + 2, ay - 16), (ax + 14, ay - 8), (ax + 2, ay)], fill=(g, g, g))
    d.multiline_text((W / 2, H * 0.62), sc["cta"], font=F_CTA, fill=(g, g, g), anchor="ma", align="center", spacing=8)
    if b > 0.5:
        bb = d.multiline_textbbox((W / 2, H * 0.62), sc["cta"], font=F_CTA, anchor="ma", align="center", spacing=8)
        d.line([(bb[0], bb[3] + 4), (bb[2], bb[3] + 4)], fill=(g, g, g), width=1)
    return img


# ---------------------------------------------------------------- audio
def make_audio(story, path):
    sr = 44100
    total = sum(s["dur"] for s in story)
    n = int(total * sr)
    t = np.arange(n) / sr
    rng = np.random.default_rng(1)
    drone = 0.16 * np.sin(2 * np.pi * 55 * t) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.07 * t))
    drone += 0.10 * np.sin(2 * np.pi * 82.4 * t + np.sin(2 * np.pi * 0.2 * t))
    drone += 0.05 * np.sin(2 * np.pi * 110.3 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.05 * t))
    noise = rng.normal(0, 1, n)
    k = np.ones(400) / 400
    wind = np.convolve(noise, k, mode="same") * 0.6 * (0.6 + 0.4 * np.sin(2 * np.pi * 0.11 * t))
    out = drone + wind
    # soft piano-ish notes (A minor) every ~2.5s
    notes = [220.0, 261.6, 329.6, 293.7, 246.9, 196.0]
    for i, st in enumerate(np.arange(1.0, total - 3, 2.6)):
        f = notes[i % len(notes)]
        s0 = int(st * sr)
        L = int(3 * sr)
        tt = np.arange(min(L, n - s0)) / sr
        env = np.exp(-tt * 1.6)
        out[s0:s0 + len(tt)] += 0.10 * env * (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt))
    # low boom at each cut
    pos = 0.0
    for s in story:
        s0 = int(pos * sr)
        L = int(1.5 * sr)
        tt = np.arange(min(L, n - s0)) / sr
        out[s0:s0 + len(tt)] += 0.5 * np.exp(-tt * 3.5) * np.sin(2 * np.pi * (45 - 10 * tt) * tt)
        pos += s["dur"]
    fade = np.minimum(1, np.minimum(t / 1.5, (total - t) / 2.5))
    out = out * np.clip(fade, 0, 1)
    out = out / np.max(np.abs(out)) * 0.8
    pcm = (out * 32767).astype(np.int16)
    st = np.stack([pcm, pcm], 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(st.tobytes())


# ---------------------------------------------------------------- render
def render(story, out):
    wav = out.replace(".mp4", ".wav")
    make_audio(story, wav)
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    cache = {}
    for idx, sc in enumerate(story):
        dur = sc["dur"]
        nf = int(dur * FPS)
        if sc["type"] != "end":
            key = (sc["type"], repr(sorted(sc.get("p", {}).items())))
            if key not in cache:
                cache[key] = SCENES[sc["type"]](np.random.default_rng(hash(key) % 2**32), sc.get("p", {}))
            A, B, T, dyn = cache[key]
        pr0, pr1 = sc.get("prog", (0, 0))
        zoom0, zoom1 = sc.get("zoom", (1.0, 1.08))
        for f in range(nf):
            t = f / FPS
            u = t / dur
            if sc["type"] == "end":
                img = end_card(sc, t)
            else:
                prog = pr0 + (pr1 - pr0) * ease(u / 0.85)
                base = dyn.arr_hook(A, t) if hasattr(dyn, "arr_hook") else A
                arr = np.where((T <= prog)[..., None], B, base) if pr1 > 0 else base
                z = zoom0 + (zoom1 - zoom0) * u
                cw, ch = BW / z, BH / z
                l = (BW - cw) / 2 + sc.get("pan", 0) * u * 30
                tp = (BH - ch) / 2
                img = to_img(arr).resize((W, H), Image.BILINEAR, box=(l, tp, l + cw, tp + ch))
                d = ImageDraw.Draw(img)
                dyn(img, d, t, prog)
                draw_overlay(img, sc, t, dur)
            # dip to black at cuts
            fade = min(1.0, t / 0.25, (dur - t) / 0.2)
            if fade < 1:
                img = Image.eval(img, lambda v, k=max(0.0, fade): int(v * k))
            ff.stdin.write(img.tobytes())
        print(f"  scene {idx + 1}/{len(story)} done", flush=True)
    ff.stdin.close()
    ff.wait()


if __name__ == "__main__":
    from stories import STORIES
    render(STORIES[sys.argv[1]], sys.argv[2])
