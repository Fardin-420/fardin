#!/usr/bin/env python3
# Pale Blue Dot documentary Short (test 002, 20 s): original illustrations + local Kokoro narration + synthesized score/SFX.
import json, math, subprocess, sys
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy.signal import butter, sosfilt

W, H, FPS, DUR = 1080, 1920, 30, 20.0
NF = int(DUR * FPS)
SR = 48000
PREVIEW = len(sys.argv) > 1 and sys.argv[1] == "preview"
rng = np.random.default_rng(1990)
TIM = json.load(open("timing.json"))
WT = {(l["line"], k): (s, e) for l in TIM for k, (w, s, e) in enumerate(l["words"])}
def ws(line, k): return WT[(line, k)][0]
def we(line, k): return WT[(line, k)][1]

# ------------------------------------------------------------------ beats (from narration timing)
T_B = ws(1, 0)                 # solar-system diagram
T_TURN = ws(1, 5)              # "turned around"
T_DIST = ws(1, 8)              # "four billion miles"
T_SNAP = ws(1, 16)             # "look back" -> shutter
T_C = ws(2, 0)                 # back to the photo
T_PIXEL = ws(2, 7)             # "single pixel"
T_BEAM = ws(2, 12)             # "beam of sunlight"
T_D = ws(3, 0)                 # cameras off
T_OFF = ws(3, 5)               # "switched off"
T_E = ws(4, 0)                 # payoff
T_END = we(4, 8)

# ------------------------------------------------------------------ helpers
def clamp(v, a, b): return max(a, min(b, v))
def seg(t, a, b): return clamp((t - a) / (b - a), 0, 1)
def ease(x): x = clamp(x, 0, 1); return x * x * (3 - 2 * x)
def ease_out(x): x = clamp(x, 0, 1); return 1 - (1 - x) ** 3
def ease_back(x): x = clamp(x, 0, 1); c = 1.7; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2
def lerp(a, b, k): return a + (b - a) * k

F_CAP = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
F_UI = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
F_MONO = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf"
_fc = {}
def font(p, s):
    s = max(1, int(s))
    if (p, s) not in _fc: _fc[(p, s)] = ImageFont.truetype(p, s)
    return _fc[(p, s)]
WHITE, YELLOW, BLACK, RED, CYAN, PALE = (255, 255, 255), (255, 212, 0), (0, 0, 0), (235, 45, 45), (120, 210, 255), (170, 205, 255)

# ------------------------------------------------------------------ the illustrated "photo" (big canvas, zoomable)
PW, PH = 2160, 3840                     # 2x the frame, so push-ins stay sharp
DOT = (1418, 2210)                      # where Earth sits, inside the brightest ray
def make_photo():
    a = np.zeros((PH, PW, 3), np.float32)
    yy, xx = np.mgrid[0:PH, 0:PW].astype(np.float32)
    # scattered-sunlight rays: soft, slightly tilted bands (the camera optics scattered sunlight; Earth sits in one)
    rays = [(560, 150, (120, 92, 70), 0.5), (1000, 90, (95, 85, 95), 0.35), (1430, 120, (150, 118, 92), 0.7),
            (1800, 70, (80, 82, 110), 0.3)]
    for cx, wid, col, amp in rays:
        x0 = cx + (yy - PH / 2) * -0.10
        g = np.exp(-((xx - x0) / wid) ** 2) * amp
        g *= 0.75 + 0.25 * np.sin(yy / 230 + cx)
        a += g[..., None] * np.array(col, np.float32)
    a += rng.normal(0, 5, (PH // 4, PW // 4, 1)).repeat(4, 0).repeat(4, 1)          # sensor grain
    img = Image.fromarray(a.clip(0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    for r, al in ((14, 40), (9, 90), (5, 255)):                                      # Earth: a faint pale-blue point
        d.ellipse((DOT[0] - r, DOT[1] - r, DOT[0] + r, DOT[1] + r), fill=tuple(int(c * al / 255) + 0 for c in PALE))
    return img.filter(ImageFilter.GaussianBlur(1.2))
print("building photo", flush=True)
PHOTO = make_photo()

def photo_view(z, fx=DOT[0], fy=DOT[1]):
    vw, vh = PW / z, PH / z
    x0 = clamp(fx - vw / 2, 0, PW - vw); y0 = clamp(fy - vh / 2, 0, PH - vh)
    img = PHOTO.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + vw, y0 + vh))
    to = lambda px, py: ((px - x0) * W / vw, (py - y0) * H / vh)
    return img, to

# starfield for the diagram
STARS = Image.new("RGB", (W, H), (2, 3, 8)); _d = ImageDraw.Draw(STARS)
for _ in range(1000):
    x, y = rng.uniform(0, W), rng.uniform(0, H); b = int(rng.uniform(40, 230)); s = rng.choice([1, 1, 1, 2])
    _d.ellipse((x, y, x + s, y + s), fill=(b, b, min(255, b + 20)))
STARS = STARS.filter(ImageFilter.GaussianBlur(0.6))

def draw_voyager(d, x, y, s, ang):
    """Voyager: high-gain dish, bus, magnetometer boom, RTG boom, as a simple icon."""
    ca, sa = math.cos(ang), math.sin(ang)
    def P(px, py): return (x + (px * ca - py * sa) * s, y + (px * sa + py * ca) * s)
    d.line((P(0, 0), P(-4.2, 2.4)), fill=(200, 200, 200), width=max(2, int(s * 0.12)))   # RTG boom
    d.ellipse((P(-4.4, 2.5)[0] - s * 0.35, P(-4.4, 2.5)[1] - s * 0.35, P(-4.4, 2.5)[0] + s * 0.35, P(-4.4, 2.5)[1] + s * 0.35), fill=(120, 110, 100))
    d.line((P(0, 0), P(5.5, -3.0)), fill=(170, 170, 170), width=max(1, int(s * 0.06)))   # magnetometer boom
    d.polygon([P(-0.7, -0.6), P(0.7, -0.6), P(0.7, 0.6), P(-0.7, 0.6)], fill=(190, 160, 90), outline=WHITE)
    dish = [P(1.0 + 0.45 * math.cos(q), 2.0 * math.sin(q)) for q in np.linspace(0, 2 * math.pi, 28)]
    d.polygon(dish, fill=(235, 235, 235), outline=(140, 140, 140))
    d.line((P(1.3, 0), P(2.4, 0)), fill=(220, 220, 220), width=max(1, int(s * 0.08)))     # feed

def chip(d, x, y, text, bg=(25, 25, 25), size=34):
    f = font(F_MONO, size); tw = f.getlength(text)
    d.rounded_rectangle((x, y, x + tw + 36, y + size + 26), 10, fill=bg)
    d.text((x + 18, y + (size + 26) / 2), text, font=f, fill=WHITE, anchor="mm" if False else "lm")

def label(d, x, y, text, sub=None, ax=None, ay=None, k=1.0, color=WHITE):
    if k <= 0: return
    if ax is not None:
        ex, ey = lerp(ax, x, ease_out(k)), lerp(ay, y, ease_out(k))
        d.line((ax, ay, ex, ey), fill=color, width=4)
        d.ellipse((ax - 9, ay - 9, ax + 9, ay + 9), outline=color, width=4)
    if k > 0.5:
        d.text((x, y), text, font=font(F_UI, 42), fill=color, anchor="lb", stroke_width=4, stroke_fill=BLACK)
        if sub: d.text((x, y + 8), sub, font=font(F_MONO, 30), fill=(220, 220, 220), anchor="lt", stroke_width=3, stroke_fill=BLACK)

def ring(d, x, y, r, t, color=YELLOW):
    r *= 1 + 0.06 * math.sin(t * 9)
    for wdt, col in ((12, BLACK), (6, color)):
        d.ellipse((x - r, y - r, x + r, y + r), outline=col, width=wdt)

# ------------------------------------------------------------------ captions
CHUNKS = [  # (line, [(token, spoken word index, emphasis)])
    (0, [("THIS", 0, 0), ("TINY", 1, 0), ("DOT", 2, 1)]),
    (0, [("MIGHT", 3, 0), ("BE", 4, 0), ("THE", 5, 0)]),
    (0, [("MOST", 6, 0), ("HUMBLING", 7, 1)]),
    (0, [("PHOTO", 8, 1), ("EVER", 9, 0), ("TAKEN.", 10, 0)]),
    (1, [("IN", 0, 0), ("1990,", 1, 0)]),
    (1, [("VOYAGER", 3, 1), ("1", 4, 1)]),
    (1, [("TURNED", 5, 0), ("AROUND,", 6, 1)]),
    (1, [("NEARLY", 7, 0), ("4", 8, 1), ("BILLION", 9, 1), ("MILES", 10, 1)]),
    (1, [("FROM", 11, 0), ("HOME,", 12, 0)]),
    (1, [("FOR", 13, 0), ("ONE", 14, 0), ("LAST", 15, 0)]),
    (1, [("LOOK", 16, 1), ("BACK.", 17, 1)]),
    (2, [("EARTH", 0, 1), ("SHOWED", 1, 0), ("UP", 2, 0)]),
    (2, [("AS", 3, 0), ("LESS", 4, 0), ("THAN", 5, 0)]),
    (2, [("A", 6, 0), ("SINGLE", 7, 1), ("PIXEL...", 8, 1)]),
    (2, [("FLOATING", 9, 0), ("IN", 10, 0), ("A", 11, 0)]),
    (2, [("BEAM", 12, 1), ("OF", 13, 0), ("SUNLIGHT.", 14, 1)]),
    (3, [("SOON", 0, 0), ("AFTER,", 1, 0)]),
    (3, [("ITS", 2, 0), ("CAMERAS", 3, 1), ("WERE", 4, 0)]),
    (3, [("SWITCHED", 5, 1), ("OFF", 6, 1)]),
    (3, [("FOR", 7, 0), ("GOOD.", 8, 1)]),
    (4, [("EVERY", 0, 1), ("PERSON", 1, 0)]),
    (4, [("YOU'VE", 2, 0), ("EVER", 3, 0), ("KNOWN", 4, 0)]),
    (4, [("LIVED", 5, 0), ("ON", 6, 0)]),
    (4, [("THAT", 7, 0), ("SPECK.", 8, 1)]),
]
CAPS = []
for i, (ln, toks) in enumerate(CHUNKS):
    items = [(t, ws(ln, k), e) for t, k, e in toks]
    last = toks[-1][1]
    if i + 1 < len(CHUNKS):
        nl, nt = CHUNKS[i + 1]
        nxt = ws(nl, nt[0][1])
        end = nxt if nl == ln else min(we(ln, last) + 0.35, nxt)
    else:
        end = we(ln, last) + 0.5
    CAPS.append((items[0][1], end, items))

def draw_caption(img, t, y=1460):
    d = ImageDraw.Draw(img)
    for a, b, items in CAPS:
        if not (a <= t < b): continue
        vis = [x for x in items if x[1] <= t + 0.02]
        if not vis: return
        base, gap, maxw = 104, 24, 920
        lines, cur, cw = [], [], 0
        for w, s, e in vis:
            sz = int(base * (1 + 0.25 * max(0, 1 - (t - s) / 0.11)))
            fw = font(F_CAP, sz).getlength(w)
            if cur and cw + gap + fw > maxw: lines.append(cur); cur, cw = [], 0
            cur.append((w, sz, e, fw)); cw += (gap if len(cur) > 1 else 0) + fw
        lines.append(cur); lines = lines[-2:]
        lh = int(base * 1.1); y0 = y - (len(lines) - 1) * lh / 2
        for li, line in enumerate(lines):
            tot = sum(x[3] for x in line) + gap * (len(line) - 1); x = W / 2 - tot / 2
            for w, sz, e, fw in line:
                d.text((x, y0 + li * lh), w, font=font(F_CAP, sz), fill=YELLOW if e else WHITE, anchor="lm",
                       stroke_width=10, stroke_fill=BLACK)
                x += fw + gap
        return

# ------------------------------------------------------------------ grade / texture
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1 - 0.5 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) ** 1.5).clip(0.3, 1)[..., None]
GRAIN = [rng.normal(0, 5, (H // 2, W // 2, 1)).astype(np.float32).repeat(2, 0).repeat(2, 1) for _ in range(4)]
def grade(img, fi, shake=(0, 0)):
    a = np.asarray(img, np.float32)
    lum = a.mean(2, keepdims=True) / 255
    a = a + (1 - lum) * np.array([-2, 2, 7], np.float32)
    a = a * VIG + GRAIN[fi % 4]
    out = Image.fromarray(a.clip(0, 255).astype(np.uint8))
    if shake != (0, 0):
        out = out.transform(out.size, Image.AFFINE, (1, 0, shake[0], 0, 1, shake[1]), Image.BILINEAR)
    return out

# ------------------------------------------------------------------ scenes
HOOK_Z = 3.2
def scene_photo_hook(t):
    z = lerp(HOOK_Z, 3.9, ease(seg(t, 0, T_B)))
    img, to = photo_view(z)
    d = ImageDraw.Draw(img); x, y = to(*DOT)
    if t > ws(0, 2) - 0.05: ring(d, x, y, 46 * z / 3, t)
    return img

def scene_system(t):
    img = STARS.copy(); d = ImageDraw.Draw(img, "RGBA")
    sun = (300, 640)
    for r, al in ((240, 18), (150, 40), (80, 90), (36, 255)):     # sun glare
        d.ellipse((sun[0] - r, sun[1] - r, sun[0] + r, sun[1] + r), fill=(255, 235, 170, al))
    for k, (rx, ry) in enumerate(((70, 26), (110, 40), (150, 55), (230, 84), (330, 120), (430, 156))):  # inner orbits, tilted view
        d.ellipse((sun[0] - rx, sun[1] - ry, sun[0] + rx, sun[1] + ry), outline=(120, 160, 210, 90), width=2)
    ex, ey = sun[0] + 150 * math.cos(0.9), sun[1] + 55 * math.sin(0.9)      # Earth on its orbit
    d.ellipse((ex - 6, ey - 6, ex + 6, ey + 6), fill=PALE)
    label(d, 120, 430, "EARTH", None, ex, ey, seg(t, T_B + 0.5, T_B + 0.8), CYAN)
    vx, vy = 800, 1010
    turn = ease(seg(t, T_TURN, T_TURN + 0.7))
    draw_voyager(d, vx, vy, 42, lerp(0.6, math.atan2(sun[1] - vy, sun[0] - vx), turn))
    label(d, 470, 1215, "VOYAGER 1", "looking back toward the Sun", vx - 30, vy + 70, seg(t, T_B + 0.9, T_B + 1.2), YELLOW)
    if turn > 0:  # line of sight from the camera back home
        k = ease(seg(t, T_TURN + 0.4, T_DIST))
        for j in range(1, 40):
            q = j / 40
            if q > k: break
            px, py = lerp(vx, ex, q), lerp(vy, ey, q)
            d.ellipse((px - 3, py - 3, px + 3, py + 3), fill=(255, 212, 0, 150))
    if t >= T_DIST:
        age = t - T_DIST
        d.text((W / 2, 240), "3.7 BILLION MILES", font=font(F_CAP, 96 * (1 + 0.4 * max(0, 1 - age / 0.12))), fill=WHITE,
               anchor="mm", stroke_width=10, stroke_fill=BLACK)
        d.text((W / 2, 330), "6 billion km from Earth", font=font(F_MONO, 40), fill=CYAN, anchor="mm", stroke_width=4, stroke_fill=BLACK)
    chip(d, 40, 140, "FEB 14, 1990")
    d.text((W / 2, 1800), "diagram not to scale", font=font(F_MONO, 24), fill=(180, 180, 180), anchor="mm")
    return img

def scene_photo_pixel(t):
    k = ease(seg(t, T_C, T_PIXEL))
    z = lerp(1.0, 9.0, k ** 1.3)
    img, to = photo_view(z)
    d = ImageDraw.Draw(img, "RGBA"); x, y = to(*DOT)
    if t >= T_PIXEL - 0.1:   # pixel grid: one camera pixel vs the size of Earth (0.12 pixel)
        kk = ease_out(seg(t, T_PIXEL - 0.1, T_PIXEL + 0.25))
        cell = 300
        gx0, gy0 = x - cell / 2, y - cell / 2
        for i in range(-2, 4):
            al = int(160 * kk)
            d.line((gx0 + i * cell, 0, gx0 + i * cell, H), fill=(255, 255, 255, al), width=2)
            d.line((0, gy0 + i * cell, W, gy0 + i * cell), fill=(255, 255, 255, al), width=2)
        d.rectangle((gx0, gy0, gx0 + cell, gy0 + cell), outline=(255, 212, 0, int(255 * kk)), width=6)
        er = cell * math.sqrt(0.12 / math.pi)  # disc with 12% of the pixel's area
        d.ellipse((x - er, y - er, x + er, y + er), fill=(*PALE, int(255 * kk)))
        if t >= T_PIXEL + 0.2:
            d.text((W / 2, y - cell / 2 - 70), "EARTH = 0.12 PIXEL", font=font(F_CAP, 84), fill=YELLOW, anchor="mm",
                   stroke_width=10, stroke_fill=BLACK)
            d.text((gx0 + cell + 20, gy0 + cell - 10), "1 pixel", font=font(F_MONO, 34), fill=WHITE, anchor="lb",
                   stroke_width=4, stroke_fill=BLACK)
    if t >= T_BEAM - 0.3:   # pull back out to show the beam it floats in
        pass
    return img

def scene_photo_beam(t):
    k = ease(seg(t, T_BEAM - 0.4, T_BEAM + 0.6))
    z = lerp(9.0, 1.6, k)
    img, to = photo_view(z)
    d = ImageDraw.Draw(img); x, y = to(*DOT)
    ring(d, x, y, 40, t)
    if t >= T_BEAM + 0.2:
        label(d, 90, 520, "SCATTERED SUNLIGHT", "light bouncing inside the camera", x - 90, y - 420, seg(t, T_BEAM + 0.2, T_BEAM + 0.5), (240, 200, 150))
    return img

def scene_off(t):
    """Close on the spacecraft camera; an iris shuts at 'switched off'."""
    img = STARS.copy(); d = ImageDraw.Draw(img, "RGBA")
    draw_voyager(d, 560, 900, 78, math.pi * 0.95)
    chip(d, 40, 140, "VOYAGER 1 CAMERAS")
    k = ease(seg(t, T_OFF, T_OFF + 0.45))
    if k > 0:
        r = lerp(1300, 0, k)
        mask = Image.new("L", (W, H), 255); ImageDraw.Draw(mask).ellipse((W / 2 - r, H / 2 - r, W / 2 + r, H / 2 + r), fill=0)
        img.paste(Image.new("RGB", (W, H), (0, 0, 0)), (0, 0), mask)
        d = ImageDraw.Draw(img)
        if t >= T_OFF + 0.45:
            d.text((W / 2, 880), "CAMERA OFF", font=font(F_CAP, 120), fill=RED, anchor="mm", stroke_width=10, stroke_fill=BLACK)
            d.text((W / 2, 990), "the last images it ever took", font=font(F_MONO, 38), fill=(220, 220, 220), anchor="mm")
    return img

def scene_payoff(t):
    k = ease(seg(t, T_E, DUR))
    z = lerp(1.6, HOOK_Z, k)    # ends on the exact framing of the first frame -> clean loop
    img, to = photo_view(z)
    d = ImageDraw.Draw(img); x, y = to(*DOT)
    ring(d, x, y, 46 * z / 3, t)
    kk = seg(t, T_END - 0.2, T_END + 0.3)
    if kk > 0:
        yb = 1700
        d.rectangle((60, yb - 4, 60 + 960 * ease_out(kk), yb), fill=YELLOW)
        d.text((60, yb + 18), "VOYAGER 1  ·  \"PALE BLUE DOT\"  ·  1990", font=font(F_UI, 40), fill=WHITE,
               stroke_width=4, stroke_fill=BLACK)
    return img

def frame(t, fi):
    shake = (0, 0)
    if t < T_B:
        img = scene_photo_hook(t)
    elif t < T_C:
        img = scene_system(t)
        if T_SNAP <= t < T_SNAP + 0.12: img = Image.blend(img, Image.new("RGB", (W, H), WHITE), 0.85)  # shutter flash
    elif t < T_BEAM - 0.4:
        img = scene_photo_pixel(t)
        if T_C <= t < T_C + 0.1: img = Image.blend(img, Image.new("RGB", (W, H), WHITE), 0.6)
    elif t < T_D:
        img = scene_photo_beam(t)
    elif t < T_E:
        img = scene_off(t)
        if T_OFF <= t < T_OFF + 0.35: shake = (rng.uniform(-6, 6), rng.uniform(-6, 6))
    else:
        img = scene_payoff(t)
    img = grade(img, fi, shake)
    d = ImageDraw.Draw(img)
    d.text((40, 70), "ILLUSTRATION - NOT THE ORIGINAL NASA IMAGE", font=font(F_MONO, 26), fill=(215, 215, 215),
           stroke_width=3, stroke_fill=BLACK)
    draw_caption(img, t)
    return img

def render_video(out):
    if PREVIEW:
        for t in [0.3, 1.2, 2.6, 3.6, 5.6, 6.9, 8.4, 9.5, 10.9, 11.6, 12.6, 13.6, 14.7, 15.6, 16.8, 18.4, 19.95]:
            frame(t, int(t * FPS)).resize((270, 480)).save(f"pv_{int(t * 100):04d}.jpg", quality=82)
        return
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                          "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for fi in range(NF):
        p.stdin.write(frame(fi / FPS, fi).tobytes())
        if fi % 60 == 0: print("frame", fi, flush=True)
    p.stdin.close(); p.wait()

# ------------------------------------------------------------------ audio
def bp(x, lo, hi): return sosfilt(butter(2, [lo, hi], btype="band", fs=SR, output="sos"), x)
def lp(x, hi): return sosfilt(butter(2, hi, btype="low", fs=SR, output="sos"), x)
def hp(x, lo): return sosfilt(butter(2, lo, btype="high", fs=SR, output="sos"), x)
def place(buf, sig, t0, g=1.0):
    i = int(t0 * SR); j = min(len(buf), i + len(sig))
    if j > i: buf[i:j] += sig[:j - i] * g
def envx(n, tau): return np.exp(-np.arange(n) / (tau * SR))
def boom(dur=1.8, f0=80, f1=30, tau=0.5):
    n = int(dur * SR); tt = np.arange(n) / SR
    fr = f1 + (f0 - f1) * np.exp(-tt / 0.1)
    s = np.sin(2 * np.pi * np.cumsum(fr) / SR) * envx(n, tau)
    return np.tanh((s + lp(rng.normal(0, 1, n), 2500) * envx(n, 0.015) * 0.5) * 1.6)
def whoosh(dur=0.5):
    n = int(dur * SR); x = rng.normal(0, 1, n); out = np.zeros(n)
    for s in range(10):
        a, b = s * n // 10, (s + 1) * n // 10; fc = 300 + 2600 * s / 10
        out[a:b] = bp(x, fc * 0.6, fc * 1.5)[a:b]
    return out * np.hanning(n)
def blip(f=1400, dur=0.09):
    n = int(dur * SR); tt = np.arange(n) / SR
    return np.sin(2 * np.pi * f * tt) * envx(n, 0.03) * 0.6
def shutter():
    n = int(0.12 * SR); c = hp(rng.normal(0, 1, n), 2000) * envx(n, 0.01)
    c[int(0.06 * SR):] += hp(rng.normal(0, 1, n - int(0.06 * SR)), 2500) * envx(n - int(0.06 * SR), 0.008) * 0.8
    return c
def power_down(dur=0.9):
    n = int(dur * SR); tt = np.arange(n) / SR; fr = 900 * np.exp(-tt / 0.25) + 40
    return np.sin(2 * np.pi * np.cumsum(fr) / SR) * (1 - tt / dur) * 0.5
def riser(dur):
    n = int(dur * SR); tt = np.arange(n) / SR; fr = 120 * 2 ** (2.3 * tt / dur)
    return (np.sin(2 * np.pi * np.cumsum(fr) / SR) * 0.4 + bp(rng.normal(0, 1, n), 900, 6000) * 0.3 * tt / dur) * (tt / dur) ** 2
def reverb(x, dur=2.5, mix=0.4):
    n = int(dur * SR); ir = lp(rng.normal(0, 1, n), 4000) * envx(n, dur / 5); ir /= np.abs(ir).sum() / 8
    wet = np.convolve(x, ir); out = np.zeros(len(wet)); out[:len(x)] += x * (1 - mix); out += wet * mix
    return out

def render_audio(out):
    n = int(DUR * SR); tt = np.arange(n) / SR
    # score: slow, wide pad (D major add9) -> awe, with a soft high shimmer
    notes = [(73.4, 0.45), (146.8, 0.28), (220.0, 0.18), (277.2, 0.12), (329.6, 0.1), (659.3, 0.03)]
    pad = sum(a * np.sin(2 * np.pi * f * tt + 0.5 * np.sin(2 * np.pi * 0.09 * (i + 1) * tt)) for i, (f, a) in enumerate(notes))
    pad = lp(pad, 2500) * (0.85 + 0.15 * np.sin(2 * np.pi * 0.25 * tt))
    lvl = np.interp(tt, [0, 2.5, T_B, T_C, T_OFF, T_OFF + 0.4, T_E - 0.05, T_E + 1.2, 19.0, 20],
                    [0.18, 0.2, 0.16, 0.2, 0.22, 0.0, 0.0, 0.24, 0.24, 0.18])
    bed = pad * lvl
    fx = np.zeros(n)
    place(fx, reverb(boom(2.0, 70, 30, 0.6)), 0.0, 0.7)
    place(fx, blip(1200), ws(0, 2), 0.5)                            # ring on the dot
    place(fx, whoosh(0.6), T_B - 0.25, 0.4)
    place(fx, blip(1000), T_B + 0.5, 0.45); place(fx, blip(1300), T_B + 0.9, 0.45)
    place(fx, whoosh(0.7), T_TURN, 0.35)                             # spacecraft turns
    place(fx, boom(1.0, 70, 40, 0.25), T_DIST, 0.55)
    place(fx, riser(T_SNAP - T_DIST), T_DIST, 0.35)
    place(fx, shutter(), T_SNAP, 0.9)
    place(fx, whoosh(0.5), T_C - 0.2, 0.35)
    place(fx, riser(T_PIXEL - T_C), T_C, 0.4)
    place(fx, reverb(boom(1.6, 85, 30, 0.45)), T_PIXEL, 0.8)          # 0.12 pixel reveal
    place(fx, blip(1500), T_BEAM + 0.2, 0.4)
    place(fx, power_down(), T_OFF, 0.7); place(fx, boom(1.2, 60, 30, 0.35), T_OFF + 0.4, 0.5)
    place(fx, reverb(boom(2.2, 75, 28, 0.7), 3.0, 0.45), T_E, 0.6)     # payoff swell
    vo = np.zeros(n)
    for l in TIM:
        s, sr = sf.read(l["file"]); place(vo, s, l["start"])
    vo = lp(hp(vo, 90), 12000); vo = vo / (np.abs(vo).max() + 1e-9) * 0.85
    env = lp(np.abs(vo), 7); env /= env.max() + 1e-9
    duck = 1 - 0.6 * np.clip(env * 3, 0, 1)
    mix = np.tanh((vo + bed * duck + fx * (0.5 + 0.5 * duck)) * 1.05) * 0.95
    sf.write(out, np.stack([mix, mix], 1).astype(np.float32), SR, subtype="FLOAT")

if __name__ == "__main__":
    if PREVIEW: render_video(None)
    else:
        render_audio("mix.wav"); print("audio done", flush=True)
        render_video("video.mp4"); print("video done", flush=True)
