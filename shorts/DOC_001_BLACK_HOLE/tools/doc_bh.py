#!/usr/bin/env python3
# "What Would Happen If You Fell Into a Black Hole?" — 70 s vertical documentary.
# Visuals: ray-traced Schwarzschild simulation (raytrace.py) + animated diagrams. Audio: Kokoro VO + synthesized score/SFX.
import json, math, re, subprocess, sys
from multiprocessing import Pool

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.signal import butter, sosfilt

import raytrace as rt

W, H, FPS, DUR = 1080, 1920, 30, 70.0
NF = int(DUR * FPS)
SR = 48000
SW, SH = 720, 1280                      # simulation render size (upscaled to 1080x1920)
TIM = json.load(open("timing.json"))
WT = {(l["line"], k): (s, e) for l in TIM for k, (w, s, e) in enumerate(l["words"])}
def ws(l, k): return WT[(l, k)][0]
def we(l, k): return WT[(l, k)][1]
def ls(l): return TIM[l]["start"]

# ------------------------------------------------------------------ scene boundaries (from narration)
S1, S2, S3, S4 = ls(1), ls(2), ls(3), ls(4)
T_FALL_DIAG = ws(4, 4)          # "First problem"
S5, S6, S7, S8, S9, S10 = ls(5), ls(6), ls(7), ls(8), ls(9), ls(10)
T_HORIZON = ws(8, 8)            # "event horizon"
T_BLACK = we(8, 14) - 0.1       # "...a thing." -> fully crossed
T_END = TIM[10]["start"] + TIM[10]["dur"]

# ------------------------------------------------------------------ helpers
def clamp(v, a, b): return max(a, min(b, v))
def seg(t, a, b): return clamp((t - a) / (b - a), 0.0, 1.0)
def ease(x): x = clamp(x, 0, 1); return x * x * (3 - 2 * x)
def ease_out(x): x = clamp(x, 0, 1); return 1 - (1 - x) ** 3
def ease_in(x): x = clamp(x, 0, 1); return x ** 3
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
WHITE, YELLOW, BLACK, RED, CYAN, ORANGE = (255, 255, 255), (255, 212, 0), (0, 0, 0), (235, 45, 45), (120, 210, 255), (255, 150, 40)

# ------------------------------------------------------------------ simulation layer
SKY = None
def sky():
    global SKY
    if SKY is None: SKY = np.load("sky.npy").astype(np.float32)
    return SKY

def qD(D): return round(D * 4) / 4 if D > 10 else round(D * 40) / 40   # quantized so lensing tables get reused

def tonemap(a, bloom=0.55):
    a = a / 255.0
    hh, ww = a.shape[:2]
    small = Image.fromarray(np.clip(a * 160, 0, 255).astype(np.uint8)).resize((ww // 4, hh // 4), Image.BILINEAR)
    b = np.asarray(small.filter(ImageFilter.GaussianBlur(6 * ww / SW)).resize((ww, hh), Image.BILINEAR), np.float32) / 160
    a = a + bloom * b
    a = a * (2.51 * a + 0.03) / (a * (2.43 * a + 0.59) + 0.14)
    return Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8))

def sim(D, incl, az, t, fov=62.0, roll=0.0, look=(0.0, 0.0), w=SW, h=SH, gain=1.0):
    a = rt.render(qD(D), incl, az, sky(), W=w, H=h, fov_y=fov, t=t, roll=roll, look=look, disk_gain=gain)
    return tonemap(a).resize((W, H), Image.BICUBIC)

def zoom_blur(img, amount):
    """Radial motion blur for the fall-in rush."""
    if amount <= 0: return img
    acc = np.zeros((H, W, 3), np.float32)
    n = 6
    for i in range(n):
        z = 1 + amount * i / n
        cw, ch = W / z, H / z
        acc += np.asarray(img.resize((W, H), Image.BILINEAR, box=((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2)), np.float32)
    return Image.fromarray((acc / n).astype(np.uint8))

# ------------------------------------------------------------------ graphics helpers
def tag(d, kind):
    txt = {"sim": "SIMULATION  ·  computed for this video from Einstein's equations",
           "blur": "SIMULATION blurred to telescope resolution  ·  not the EHT image",
           "diag": "DIAGRAM  ·  not to scale",
           "view": "SIMULATION  ·  simplified view from a hovering camera"}[kind]
    col = (120, 210, 255) if kind != "diag" else (255, 212, 0)
    d.rounded_rectangle((36, 60, 36 + font(F_MONO, 24).getlength(txt) + 28, 104), 10, fill=(0, 0, 0, 150))
    d.ellipse((48, 76, 60, 88), fill=col)
    d.text((70, 82), txt, font=font(F_MONO, 24), fill=(230, 230, 230), anchor="lm")

def callout(d, x, y, tx, ty, title, sub, k, color=WHITE, anchor="lb"):
    if k <= 0: return
    ex, ey = lerp(tx, x, ease_out(k)), lerp(ty, y, ease_out(k))
    d.line((tx, ty, ex, ey), fill=color, width=4)
    d.ellipse((tx - 10, ty - 10, tx + 10, ty + 10), outline=color, width=4)
    if k > 0.6:
        d.text((x, y), title, font=font(F_UI, 46), fill=color, anchor=anchor, stroke_width=5, stroke_fill=BLACK)
        if sub:
            sy = y + 62 if anchor.endswith("t") else y + 10
            d.text((x, sy), sub, font=font(F_MONO, 30), fill=(225, 225, 225), anchor=anchor[0] + "t", stroke_width=4, stroke_fill=BLACK)

def big_text(d, x, y, txt, size, age, color=WHITE, sub=None):
    pop = 1 + 0.35 * max(0, 1 - age / 0.14)
    d.text((x, y), txt, font=font(F_CAP, size * pop), fill=color, anchor="mm", stroke_width=10, stroke_fill=BLACK)
    if sub: d.text((x, y + size * 0.75), sub, font=font(F_MONO, 36), fill=CYAN, anchor="mm", stroke_width=4, stroke_fill=BLACK)

def arrow(d, x0, y0, x1, y1, color=YELLOW, w=14, head=40):
    d.line((x0, y0, x1, y1), fill=BLACK, width=w + 10); d.line((x0, y0, x1, y1), fill=color, width=w)
    a = math.atan2(y1 - y0, x1 - x0)
    pts = [(x1 + 10 * math.cos(a), y1 + 10 * math.sin(a)), (x1 - head * math.cos(a - 0.5), y1 - head * math.sin(a - 0.5)),
           (x1 - head * math.cos(a + 0.5), y1 - head * math.sin(a + 0.5))]
    d.polygon(pts, fill=color, outline=BLACK, width=5)

def astronaut(size, stretch=1.0, tint=(1, 1, 1), alpha=1.0):
    """Feet-down astronaut sprite; stretch > 1 elongates vertically and thins (tidal stretching)."""
    s = int(size); im = Image.new("RGBA", (s * 2, s * 4), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    cx = s
    suit = tuple(int(c * t) for c, t in zip((236, 236, 240), tint)) + (int(255 * alpha),)
    dark = tuple(int(c * t) for c, t in zip((70, 80, 95), tint)) + (int(255 * alpha),)
    visor = tuple(int(c * t) for c, t in zip((255, 190, 60), tint)) + (int(255 * alpha),)
    d.rounded_rectangle((cx - s * 0.45, s * 1.05, cx + s * 0.45, s * 2.3), s * 0.2, fill=suit)          # torso
    d.rounded_rectangle((cx - s * 0.36, s * 2.2, cx - s * 0.06, s * 3.4), s * 0.12, fill=suit)          # legs
    d.rounded_rectangle((cx + s * 0.06, s * 2.2, cx + s * 0.36, s * 3.4), s * 0.12, fill=suit)
    d.rounded_rectangle((cx - s * 0.78, s * 1.15, cx - s * 0.5, s * 2.1), s * 0.12, fill=suit)          # arms
    d.rounded_rectangle((cx + s * 0.5, s * 1.15, cx + s * 0.78, s * 2.1), s * 0.12, fill=suit)
    d.ellipse((cx - s * 0.48, s * 0.2, cx + s * 0.48, s * 1.16), fill=suit)                           # helmet
    d.ellipse((cx - s * 0.32, s * 0.4, cx + s * 0.32, s * 0.9), fill=visor)
    d.rounded_rectangle((cx - s * 0.22, s * 1.35, cx + s * 0.22, s * 1.7), s * 0.06, fill=dark)       # chest pack
    if stretch != 1.0:
        im = im.resize((max(2, int(im.width / math.sqrt(stretch))), int(im.height * stretch)), Image.BICUBIC)
    return im

def clock(d, cx, cy, r, ang, label, color=WHITE):
    d.ellipse((cx - r - 6, cy - r - 6, cx + r + 6, cy + r + 6), fill=(0, 0, 0, 170))
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=color, width=6)
    for k in range(12):
        a = k * math.pi / 6; r0 = r * (0.8 if k % 3 == 0 else 0.88)
        d.line((cx + r0 * math.sin(a), cy - r0 * math.cos(a), cx + r * 0.95 * math.sin(a), cy - r * 0.95 * math.cos(a)), fill=color, width=5)
    d.line((cx, cy, cx + r * 0.82 * math.sin(ang), cy - r * 0.82 * math.cos(ang)), fill=YELLOW, width=7)
    d.ellipse((cx - 9, cy - 9, cx + 9, cy + 9), fill=YELLOW)
    d.text((cx, cy + r + 34), label, font=font(F_MONO, 30), fill=color, anchor="mm", stroke_width=4, stroke_fill=BLACK)

def starfield(t, drift=0.0, zoom=1.0):
    """Static deep-sky backdrop for diagram scenes, with slow motion so no frame is ever static."""
    global _BG
    try: _BG
    except NameError:
        a = rt.render(400.0, 60, 0, sky(), W=SW, H=SH, fov_y=70, disk=False)
        _BG = tonemap(a, 0.3).resize((int(W * 1.25), int(H * 1.25)), Image.BICUBIC)
    z = 1.25 / zoom
    cw, ch = W * 1.25 / z * 0.8, H * 1.25 / z * 0.8
    ox = (W * 1.25 - cw) / 2 + 60 * math.sin(drift); oy = (H * 1.25 - ch) / 2
    return _BG.resize((W, H), Image.BILINEAR, box=(ox, oy, ox + cw, oy + ch))

# ------------------------------------------------------------------ captions (word-by-word, max 2 lines)
EMPH = {"BLACK", "HOLE", "NEVER", "SIMULATION", "EINSTEIN'S", "SUPERHEATED", "BENDS", "LIGHT", "FAR", "2019", "REAL",
        "55", "MILLION", "LIGHT-YEARS", "FALL", "TIDAL", "FORCES", "FEET", "HEAD", "STRETCH", "SPAGHETTIFICATION",
        "SUPERMASSIVE", "PIECE", "STRANGE", "SLOWER", "REDDER", "DIMMER", "FREEZE", "NORMAL", "EVENT", "HORIZON",
        "THING", "SURFACE", "NO", "RETURN", "FASTER", "INWARD", "CENTER", "KNOWS", "BREAKS"}
DISPLAY = {3: {1: "2019,", 2: None, 14: "55", 15: None, 16: "MILLION", 17: "LIGHT-YEARS", 18: None}}
CAPS = []
for l in TIM:
    toks = []
    for k, (w, s, e) in enumerate(l["words"]):
        ov = DISPLAY.get(l["line"], {})
        if k in ov:
            if ov[k] is None: continue
            w = ov[k]
        toks.append((w.upper(), s, e))
    line_end = l["start"] + l["dur"]
    chunk = []
    for i, tk in enumerate(toks):
        chunk.append(tk)
        if re.search(r"[,.:?!]$", tk[0]) or len(chunk) == 3 or i == len(toks) - 1:
            CAPS.append([chunk, line_end]); chunk = []
for i, (ch, le) in enumerate(CAPS):
    nxt = CAPS[i + 1][0][0][1] if i + 1 < len(CAPS) else 1e9
    end = nxt if nxt - ch[-1][2] < 0.6 else min(ch[-1][2] + 0.4, nxt)
    CAPS[i] = (ch[0][1], end, ch)

def draw_caption(img, t, y=1470):
    d = ImageDraw.Draw(img)
    for a, b, ch in CAPS:
        if not (a <= t < b): continue
        vis = [x for x in ch if x[1] <= t + 0.02]
        if not vis: return
        base, gap, maxw = 100, 24, 940
        lines, cur, cw = [], [], 0
        for w, s, e in vis:
            sz = base * (1 + 0.25 * max(0, 1 - (t - s) / 0.11))
            fw = font(F_CAP, sz).getlength(w)
            if fw > maxw: sz *= maxw / fw; fw = font(F_CAP, sz).getlength(w)
            core = re.sub(r"[^A-Z0-9'\-]", "", w)
            if cur and cw + gap + fw > maxw: lines.append(cur); cur, cw = [], 0
            cur.append((w, sz, core in EMPH, fw)); cw += (gap if len(cur) > 1 else 0) + fw
        lines.append(cur); lines = lines[-2:]
        lh = int(base * 1.1); y0 = y - (len(lines) - 1) * lh / 2
        for li, line in enumerate(lines):
            tot = sum(x[3] for x in line) + gap * (len(line) - 1); x = W / 2 - tot / 2
            for w, sz, em, fw in line:
                d.text((x, y0 + li * lh), w, font=font(F_CAP, sz), fill=YELLOW if em else WHITE, anchor="lm",
                       stroke_width=10, stroke_fill=BLACK)
                x += fw + gap
        return

# ------------------------------------------------------------------ scenes
def title(d, t, t0=0.0):
    k = ease_back(seg(t, t0 + 0.05, t0 + 0.35))
    if k <= 0: return
    d.text((W / 2, 230), "WHAT WOULD HAPPEN IF", font=font(F_CAP, 66 * k), fill=WHITE, anchor="mm", stroke_width=8, stroke_fill=BLACK)
    d.text((W / 2, 320), "YOU FELL INTO A BLACK HOLE?", font=font(F_CAP, 66 * k), fill=YELLOW, anchor="mm", stroke_width=8, stroke_fill=BLACK)

HOOK_D, HOOK_I, HOOK_A = 70.0, 84.0, 10.0
def sc_hook(t):
    k = ease_out(seg(t, 0, S1))
    img = sim(lerp(HOOK_D, 34, k), HOOK_I, lerp(HOOK_A, 25, k), t, roll=lerp(5, 0, k))
    d = ImageDraw.Draw(img, "RGBA"); tag(d, "sim"); title(d, t)
    if t < 0.12: img = Image.blend(img, Image.new("RGB", (W, H), WHITE), 0.8 * (1 - t / 0.12))
    return img

def sc_orbit(t):
    k = ease(seg(t, S1, S2))
    img = sim(lerp(34, 30, k), lerp(84, 80, k), lerp(25, 70, k), t)
    d = ImageDraw.Draw(img, "RGBA"); tag(d, "sim")
    callout(d, 90, 520, 300, 760, "BLACK HOLE SHADOW", "light that never escapes", seg(t, ws(1, 3), ws(1, 3) + 0.3))
    callout(d, 600, 1160, 860, 1000, "ACCRETION DISK", "superheated gas", seg(t, ws(1, 11), ws(1, 11) + 0.3), ORANGE)
    return img

def sc_lensing(t):
    k = ease(seg(t, S2, S3))
    img = sim(lerp(30, 21, k), 80, lerp(70, 85, k), t)
    d = ImageDraw.Draw(img, "RGBA"); tag(d, "sim")
    callout(d, 520, 330, 560, 610, "FAR SIDE OF THE DISK", "bent up and over the top", seg(t, ws(2, 10), ws(2, 10) + 0.3), YELLOW)
    # inset: side view of a light ray from the far side of the disk curving over the hole to the camera
    ki = seg(t, ws(2, 3), ws(2, 3) + 0.3)
    if ki > 0:
        x0, y0, w_, h_ = 600, 1120, 420, 240
        d.rounded_rectangle((x0, y0, x0 + w_, y0 + h_), 18, fill=(0, 0, 0, 190), outline=(255, 255, 255, 120), width=3)
        cx, cy = x0 + 170, y0 + 140
        d.line((cx - 120, cy, cx + 60, cy), fill=ORANGE, width=6)
        d.ellipse((cx - 26, cy - 26, cx + 26, cy + 26), fill=BLACK, outline=(255, 255, 255), width=2)
        ex, ey = x0 + w_ - 40, cy - 30
        d.text((ex, ey + 30), "you", font=font(F_MONO, 24), fill=WHITE, anchor="mt")
        d.ellipse((ex - 8, ey - 8, ex + 8, ey + 8), fill=WHITE)
        pr = ease(seg(t, ws(2, 3) + 0.2, ws(2, 12)))
        pts = []
        for j in range(41):
            q = j / 40
            if q > pr: break
            px = lerp(cx - 100, ex, q); py = cy - 4 - 110 * math.sin(math.pi * min(1, q * 1.15)) * (1 - 0.3 * q) + 30 * q * 0
            pts.append((px, py if q < 0.87 else lerp(py, ey, (q - 0.87) / 0.13)))
        if len(pts) > 1: d.line(pts, fill=YELLOW, width=5)
        d.text((x0 + 18, y0 + 16), "SIDE VIEW", font=font(F_MONO, 24), fill=(200, 200, 200))
    return img

def sc_eht(t):
    k = ease(seg(t, S3, S4))
    raw = rt.render(40.0, 17.0, lerp(0, 40, k), sky(), W=360, H=640, fov_y=34, t=t)
    a = np.asarray(tonemap(raw, 0.2).convert("L"), np.float32)
    blur = np.asarray(Image.fromarray(a.astype(np.uint8)).filter(ImageFilter.GaussianBlur(lerp(3, 12, ease(seg(t, S3, S3 + 2.5))))), np.float32) / 255
    blur = np.clip(blur * 1.6, 0, 1)
    rgb = np.stack([np.clip(blur * 2.2, 0, 1), np.clip(blur * 1.6 - 0.35, 0, 1), np.clip(blur * 2.4 - 1.5, 0, 1)], -1)   # "afmhot"
    img = Image.fromarray((rgb * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)
    z = lerp(1.0, 1.18, k)
    img = img.resize((W, H), Image.BICUBIC, box=((W - W / z) / 2, (H - H / z) / 2, (W + W / z) / 2, (H + H / z) / 2))
    d = ImageDraw.Draw(img, "RGBA"); tag(d, "blur")
    d.text((W / 2, 1720), "Real image: Event Horizon Telescope, M87*, April 2019 (not shown)", font=font(F_MONO, 26),
           fill=(220, 220, 220), anchor="mm", stroke_width=3, stroke_fill=BLACK)
    if t >= ws(3, 14):
        big_text(d, W / 2, 330, "55 MILLION LIGHT-YEARS", 76, t - ws(3, 14), WHITE, "away, in galaxy M87")
    elif t >= ws(3, 1):
        big_text(d, W / 2, 330, "APRIL 2019", 96, t - ws(3, 1), YELLOW, "first image of a black hole")
    return img

def sc_fall_rush(t):
    k = ease_in(seg(t, S4, T_FALL_DIAG))
    img = sim(lerp(21, 7.0, k), 80, 85, t, fov=lerp(62, 80, k))
    img = zoom_blur(img, 0.25 * k)
    if t > T_FALL_DIAG - 0.12: img = Image.blend(img, Image.new("RGB", (W, H), WHITE), seg(t, T_FALL_DIAG - 0.12, T_FALL_DIAG))
    d = ImageDraw.Draw(img, "RGBA"); tag(d, "sim")
    return img

def sc_tidal(t):
    img = starfield(t, drift=t * 0.05)
    d = ImageDraw.Draw(img, "RGBA"); tag(d, "diag")
    hx, hy = W / 2, 1640
    for rr, al in ((420, 25), (330, 60), (300, 255)):
        d.ellipse((hx - rr, hy - rr, hx + rr, hy + rr), fill=(0, 0, 0, al) if al == 255 else (255, 150, 60, al))
    d.text((hx, hy - 250), "BLACK HOLE", font=font(F_MONO, 30), fill=(230, 230, 230), anchor="mm")
    bob = 12 * math.sin(t * 2.2)
    stretch = 1 + 0.18 * ease(seg(t, ws(4, 11), ws(4, 15) + 0.4))
    sp = astronaut(120, stretch); x0, y0 = int(hx - sp.width / 2), int(700 + bob)
    img.paste(sp, (x0, y0), sp); d = ImageDraw.Draw(img, "RGBA")
    feet_y, head_y = y0 + sp.height * 0.85, y0 + sp.height * 0.1
    ka = ease_out(seg(t, ws(4, 11), ws(4, 11) + 0.35)); kb = ease_out(seg(t, ws(4, 15), ws(4, 15) + 0.35))
    if ka > 0:
        arrow(d, hx + 260, feet_y - 40, hx + 260, feet_y - 40 + 260 * ka, YELLOW)
        d.text((hx + 240, feet_y - 90), "FEET: stronger pull", font=font(F_UI, 40), fill=YELLOW, anchor="mm", stroke_width=5, stroke_fill=BLACK)
    if kb > 0:
        arrow(d, hx - 260, head_y, hx - 260, head_y + 110 * kb, CYAN, 10, 30)
        d.text((hx - 260, head_y - 40), "HEAD: weaker", font=font(F_UI, 40), fill=CYAN, anchor="mm", stroke_width=5, stroke_fill=BLACK)
    if t >= ws(4, 6):
        big_text(d, W / 2, 300, "TIDAL FORCES", 104, t - ws(4, 6), WHITE, "the difference in gravity's pull")
    return img

def sc_small(t):
    k = ease(seg(t, S5, S6))
    img = starfield(t, drift=t * 0.05, zoom=lerp(1.0, 1.08, k))
    d = ImageDraw.Draw(img, "RGBA"); tag(d, "diag")
    hx, hy = W / 2, 1180
    r = 46
    for rr, al in ((120, 30), (80, 60)):
        d.ellipse((hx - rr, hy - rr, hx + rr, hy + rr), fill=(255, 150, 60, al))
    d.ellipse((hx - r, hy - r, hx + r, hy + r), fill=BLACK, outline=(255, 190, 120), width=3)
    callout(d, 600, 1250, hx + r * 0.7, hy + r * 0.7, "EVENT HORIZON", "~60 km across (10 Suns)", seg(t, S5 + 0.4, S5 + 0.7), WHITE, "lt")
    # astronaut falls toward the hole and is stretched far outside the horizon
    fall = ease(seg(t, S5 + 0.2, ws(5, 13)))
    st = 1 + 7.0 * ease_in(seg(t, ws(5, 6), ws(5, 13)))
    sp = astronaut(70, st)
    top = lerp(430, 520, fall); yb = top + sp.height
    if yb > hy - r - 110:                                # keep the noodle outside the horizon, like the physics says
        sp = sp.resize((sp.width, int(hy - r - 110 - top)), Image.BICUBIC)
    img.paste(sp, (int(hx - sp.width / 2), int(top)), sp); d = ImageDraw.Draw(img, "RGBA")
    if t >= ws(5, 10):
        callout(d, 90, 560, hx - 30, top + sp.height * 0.5, "STRETCHED HERE", "long before the edge", seg(t, ws(5, 10), ws(5, 10) + 0.3), YELLOW)
    if t >= ws(5, 17):
        big_text(d, W / 2, 300, "SPAGHETTIFICATION", 88, t - ws(5, 17), YELLOW, "real term, used by astronomers")
    else:
        d.text((W / 2, 300), "SMALL BLACK HOLE", font=font(F_CAP, 80), fill=WHITE, anchor="mm", stroke_width=8, stroke_fill=BLACK)
    return img

def sc_super(t):
    k = ease(seg(t, S6, S7))
    img = starfield(t, drift=t * 0.05, zoom=1.1)
    d = ImageDraw.Draw(img, "RGBA"); tag(d, "diag")
    R = lerp(900, 1500, k); hx, hy = W / 2, 1250 + R
    for rr, al in ((R + 160, 25), (R + 70, 55)):
        d.ellipse((hx - rr, hy - rr, hx + rr, hy + rr), fill=(255, 150, 60, al))
    d.ellipse((hx - R, hy - R, hx + R, hy + R), fill=BLACK, outline=(255, 190, 120), width=4)
    d.text((W / 2, 300), "SUPERMASSIVE", font=font(F_CAP, 96 * (1 + 0.3 * max(0, 1 - (t - S6) / 0.14))), fill=YELLOW, anchor="mm", stroke_width=10, stroke_fill=BLACK)
    d.text((W / 2, 380), "Sagittarius A*  ·  ~4 million Suns  ·  horizon ~24 million km", font=font(F_MONO, 28), fill=CYAN, anchor="mm", stroke_width=4, stroke_fill=BLACK)
    fall = ease(seg(t, S6 + 0.3, S7 - 0.2))
    sp = astronaut(90, 1.0)
    y = lerp(600, 1240, fall)
    img.paste(sp, (int(hx - sp.width / 2), int(y)), sp); d = ImageDraw.Draw(img, "RGBA")
    if t >= ws(6, 16):
        callout(d, 120, 640, hx - 60, y + 140, "IN ONE PIECE", "tidal stretch is tiny here", seg(t, ws(6, 16), ws(6, 16) + 0.3), YELLOW)
    return img

DIL_D = 20.0
def sc_dilation(t):
    k = seg(t, S7, S8)
    img = sim(DIL_D, 82, lerp(85, 95, k), t, fov=58)
    d = ImageDraw.Draw(img, "RGBA"); tag(d, "sim")
    # friend's view: you approach the shadow's edge ever more slowly, redden, dim, and seem to freeze
    q = 1 - math.exp(-3.2 * seg(t, S7 + 0.3, ws(7, 27) + 0.5))
    red = seg(t, ws(7, 15), ws(7, 27))
    alpha = 1 - 0.9 * ease(seg(t, ws(7, 21), ws(7, 28) + 0.6))
    sp = astronaut(lerp(80, 46, q), 1.0, tint=(1.0, lerp(1, 0.35, red), lerp(1, 0.2, red)), alpha=alpha)
    x = lerp(860, 640, q); y = lerp(700, 830, q)
    img.paste(sp, (int(x - sp.width / 2), int(y - sp.height / 2)), sp); d = ImageDraw.Draw(img, "RGBA")
    rate = math.exp(-2.6 * seg(t, ws(7, 10), ws(7, 27)))     # your clock, as seen from far away, slows toward a stop
    ang = 2 * math.pi * (t - S7) * 0.5 * rate
    clock(d, 250, 1130, 115, ang, "YOUR CLOCK", CYAN)
    d.text((250, 1320), "as seen from far away", font=font(F_MONO, 28), fill=CYAN, anchor="mm", stroke_width=4, stroke_fill=BLACK)
    if t >= ws(7, 0):
        big_text(d, W / 2, 300, "TIME DILATION", 100, t - ws(7, 0), WHITE, "gravity slows time")
    return img

def sc_crossing(t):
    k = seg(t, S8, T_BLACK)
    D = lerp(9.0, 2.12, ease_in(k) * 0.65 + k * 0.35)
    img = sim(D, 82, 95, t, fov=lerp(70, 128, ease(k)))
    blk = seg(t, T_BLACK - 0.6, T_BLACK)
    if blk > 0: img = Image.blend(img, Image.new("RGB", (W, H), (0, 0, 0)), ease(blk))
    d = ImageDraw.Draw(img, "RGBA"); tag(d, "view")
    ang = 2 * math.pi * (t - S8) * 0.5      # normal ticking: proper time feels normal
    clock(d, 250, 1130, 115, ang, "YOUR CLOCK", YELLOW)
    d.text((250, 1320), "as you feel it", font=font(F_MONO, 28), fill=YELLOW, anchor="mm", stroke_width=4, stroke_fill=BLACK)
    if T_HORIZON <= t < T_BLACK + 0.2:
        kk = ease_out(seg(t, T_HORIZON, T_HORIZON + 0.4))
        yy = lerp(H + 40, H * 0.62, kk)
        d.line((0, yy, W, yy), fill=(255, 212, 0, 220), width=5)
        d.text((W / 2, yy - 30), "EVENT HORIZON", font=font(F_UI, 48), fill=YELLOW, anchor="mb", stroke_width=5, stroke_fill=BLACK)
    return img

def sc_cones(t):
    img = Image.new("RGB", (W, H), (4, 5, 10)); d = ImageDraw.Draw(img, "RGBA"); tag(d, "diag")
    d.text((W / 2, 300), "POINT OF NO RETURN", font=font(F_CAP, 84 * (1 + 0.3 * max(0, 1 - (t - ws(9, 7)) / 0.14)) if t >= ws(9, 7) else 84),
           fill=YELLOW if t >= ws(9, 7) else WHITE, anchor="mm", stroke_width=10, stroke_fill=BLACK)
    hx = 120; ay = 900
    d.ellipse((hx - 200, ay - 200, hx + 200, ay + 200), fill=(0, 0, 0), outline=(255, 170, 80), width=4)  # hole at the left
    hz = 420                                                                                              # horizon line
    d.line((hz, 470, hz, 1330), fill=YELLOW, width=5)
    d.text((hz, 1355), "EVENT HORIZON", font=font(F_UI, 40), fill=YELLOW, anchor="mt", stroke_width=5, stroke_fill=BLACK)
    d.text((hz + 20, 500), "not a surface", font=font(F_MONO, 30), fill=WHITE, anchor="lt", stroke_width=4, stroke_fill=BLACK)
    # light cones: where light (and anything) can go next. They tip toward the hole; past the horizon every path points in.
    xs = [940, 815, 690, 570, 450, 330]
    half = math.radians(30)
    for i, x in enumerate(xs):
        kk = ease_out(seg(t, S9 + 0.25 + i * 0.35, S9 + 0.6 + i * 0.35))
        if kk <= 0: continue
        dist = (x - hz) / (940 - hz)                      # 1 far away, 0 at the horizon, < 0 inside
        if dist >= 0:                                      # tilt toward the hole; outer edge vertical at the horizon
            tilt = half * (1 - dist) ** 0.6
        else:
            tilt = half + math.radians(40) * min(1, -dist / 0.4)
        dirA = -math.pi / 2 - tilt                         # screen angle; up = future, left = toward the hole
        L = 185 * kk; cx, cy = x, ay
        poly = [(cx, cy), (cx + L * math.cos(dirA + half), cy + L * math.sin(dirA + half)),
                (cx + L * math.cos(dirA - half), cy + L * math.sin(dirA - half))]
        inside = dist < 0
        d.polygon(poly, fill=(255, 212, 0, 90) if not inside else (255, 80, 60, 110), outline=YELLOW if not inside else RED, width=4)
        d.ellipse((cx - 8, cy - 8, cx + 8, cy + 8), fill=WHITE)
    if t >= ws(9, 16):
        d.text((690, 1150), "escape would need", font=font(F_MONO, 32), fill=CYAN, anchor="mm", stroke_width=4, stroke_fill=BLACK)
        d.text((690, 1195), "more than light speed", font=font(F_MONO, 32), fill=CYAN, anchor="mm", stroke_width=4, stroke_fill=BLACK)
    arrow(d, 1010, 1260, 1010, 1100, (200, 200, 200), 6, 22)
    d.text((990, 1290), "future", font=font(F_MONO, 28), fill=(200, 200, 200), anchor="rt")
    d.text((620, 700), "light cones tip inward", font=font(F_MONO, 30), fill=(210, 210, 210), anchor="lm", stroke_width=3, stroke_fill=BLACK)
    return img

def sc_center(t):
    img = Image.new("RGB", (W, H), (2, 2, 5)); d = ImageDraw.Draw(img, "RGBA"); tag(d, "diag")
    cx, cy = W / 2, 880
    k = seg(t, S10, T_END)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(glow)
    for rr, al in ((520, 40), (340, 55), (190, 70)):        # faint central glow, slowly breathing
        rr *= 1 + 0.05 * math.sin(t * 1.7)
        gd.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=(255, 120, 50, al))
    img.paste(glow.filter(ImageFilter.GaussianBlur(60)), (0, 0), glow.filter(ImageFilter.GaussianBlur(60)))
    d = ImageDraw.Draw(img, "RGBA"); tag(d, "diag")
    for i in range(64):                                     # every path leads inward
        a = i * math.pi / 32 + 0.25 * t
        ph = (t * 0.9 + i * 0.137) % 1
        r0 = lerp(1000, 60, ph); r1 = r0 - 220
        al = int(255 * math.sin(math.pi * ph))
        d.line((cx + r0 * math.cos(a), cy + r0 * math.sin(a), cx + max(30, r1) * math.cos(a), cy + max(30, r1) * math.sin(a)),
               fill=(255, 215, 150, al), width=7)
    if t >= ws(10, 9):
        age = t - ws(10, 9)
        pul = 1 + 0.08 * math.sin(age * 8)
        d.text((cx, cy), "?", font=font(F_CAP, 300 * pul * (1 + 0.4 * max(0, 1 - age / 0.15))), fill=YELLOW, anchor="mm", stroke_width=12, stroke_fill=BLACK)
    if t >= ws(10, 15):                                     # "our physics breaks down": the field equation glitches apart
        g = seg(t, ws(10, 17), T_END + 0.4)
        eq = Image.new("RGBA", (W, 160), (0, 0, 0, 0)); ImageDraw.Draw(eq).text((W / 2, 80), "Gμν + Λgμν = 8πG/c⁴ Tμν",
                                                                                   font=font(F_UI, 64), fill=WHITE, anchor="mm")
        a = np.asarray(eq).copy()
        rng = np.random.default_rng(int(t * 30))
        for _ in range(int(14 * g)):
            y0 = rng.integers(0, 150); hh = rng.integers(4, 20)
            a[y0:y0 + hh] = np.roll(a[y0:y0 + hh], rng.integers(-int(160 * g) - 1, int(160 * g) + 1), axis=1)
        a[..., 3] = (a[..., 3] * (1 - 0.85 * g)).astype(np.uint8)
        img.paste(Image.fromarray(a), (0, 1220), Image.fromarray(a))
    return img

def sc_outro(t):
    k = seg(t, T_END, DUR)
    img = sim(lerp(34, HOOK_D, ease(k)), HOOK_I, HOOK_A, t, roll=lerp(0, 5, ease(k)))
    fade = 1 - ease(seg(t, T_END, T_END + 1.2))
    if fade > 0: img = Image.blend(img, Image.new("RGB", (W, H), (0, 0, 0)), fade)
    d = ImageDraw.Draw(img, "RGBA"); tag(d, "sim")
    if t > DUR - 1.6: title(d, t, DUR - 1.6)
    return img

SCENES = [(0, S1, sc_hook), (S1, S2, sc_orbit), (S2, S3, sc_lensing), (S3, S4, sc_eht), (S4, T_FALL_DIAG, sc_fall_rush),
          (T_FALL_DIAG, S5, sc_tidal), (S5, S6, sc_small), (S6, S7, sc_super), (S7, S8, sc_dilation),
          (S8, S9, sc_crossing), (S9, S10, sc_cones), (S10, T_END, sc_center), (T_END, DUR + 1, sc_outro)]

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1 - 0.4 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) ** 1.6).clip(0.4, 1)[..., None]
GR = np.random.default_rng(3)
GRAIN = [GR.normal(0, 4, (H // 2, W // 2, 1)).astype(np.float32).repeat(2, 0).repeat(2, 1) for _ in range(4)]

def frame(fi):
    t = fi / FPS
    for a, b, fn in SCENES:
        if a <= t < b:
            img = fn(t); break
    # whip flash between scenes: 2 frames of light leak at every scene boundary (except into darkness)
    for a, b, fn in SCENES[1:]:
        if 0 <= t - a < 0.067 and fn not in (sc_outro, sc_cones, sc_center):
            img = Image.blend(img, Image.new("RGB", (W, H), (255, 240, 220)), 0.35 * (1 - (t - a) / 0.067))
    arr = np.asarray(img.convert("RGB"), np.float32) * VIG + GRAIN[fi % 4]
    img = Image.fromarray(arr.clip(0, 255).astype(np.uint8))
    draw_caption(img, t)
    return img.tobytes()

def render_video(out, preview=None):
    if preview:
        for t in preview:
            Image.frombytes("RGB", (W, H), frame(int(t * FPS))).resize((270, 480)).save(f"pv/p_{int(t * 100):05d}.jpg", quality=82)
        return
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for i, b in enumerate(pool.imap(frame, range(NF), chunksize=3)):
            p.stdin.write(b)
            if i % 150 == 0: print("frame", i, "/", NF, flush=True)
    p.stdin.close(); p.wait()

# ------------------------------------------------------------------ audio: original score + SFX
arng = np.random.default_rng(42)
def bp(x, lo, hi): return sosfilt(butter(2, [lo, hi], btype="band", fs=SR, output="sos"), x)
def lp(x, hi, o=2): return sosfilt(butter(o, hi, btype="low", fs=SR, output="sos"), x)
def hp(x, lo): return sosfilt(butter(2, lo, btype="high", fs=SR, output="sos"), x)
def envx(n, tau): return np.exp(-np.arange(n) / (tau * SR))
def place(buf, sig, t0, g=1.0):
    i = int(t0 * SR)
    if i < 0: sig, i = sig[-i:], 0
    j = min(len(buf), i + len(sig))
    if j > i: buf[i:j] += sig[:j - i] * g
def osc(freq, n, kind="saw"):
    ph = np.cumsum(np.broadcast_to(freq, (n,)) / SR) % 1.0
    return 2 * ph - 1 if kind == "saw" else np.sin(2 * np.pi * ph)
def boom(dur=2.0, f0=90, f1=28, tau=0.6):
    n = int(dur * SR); tt = np.arange(n) / SR
    s = osc(f1 + (f0 - f1) * np.exp(-tt / 0.09), n, "sin") * envx(n, tau)
    return np.tanh((s + lp(arng.normal(0, 1, n), 2500) * envx(n, 0.02) * 0.5) * 1.6)
def whoosh(dur=0.6, rev=False):
    n = int(dur * SR); x = arng.normal(0, 1, n); out = np.zeros(n)
    for s in range(12):
        a, b = s * n // 12, (s + 1) * n // 12; fc = 250 + 3000 * s / 12
        out[a:b] = bp(x, fc * 0.6, fc * 1.5)[a:b]
    out *= np.hanning(n)
    return out[::-1] if rev else out
def tick(f=2400): n = int(0.04 * SR); return osc(f, n, "sin") * envx(n, 0.006)
def riser(dur, f0=90):
    n = int(dur * SR); tt = np.arange(n) / SR
    return (osc(f0 * 2 ** (2.5 * tt / dur), n, "sin") * 0.4 + bp(arng.normal(0, 1, n), 800, 7000) * 0.3 * tt / dur) * (tt / dur) ** 2
def shepard(dur, base=55.0, up=False):
    """Endless falling (or rising) tone: octave-spaced partials gliding under a fixed bell envelope."""
    n = int(dur * SR); tt = np.arange(n) / SR; out = np.zeros(n)
    rate = 0.25 * (1 if up else -1)
    for k in range(7):
        pos = (k + rate * tt) % 7
        f = base * 2 ** pos
        amp = np.exp(-((pos - 3.5) / 1.6) ** 2)
        out += np.sin(2 * np.pi * np.cumsum(f) / SR) * amp
    return out / 3 * np.minimum(1, tt / 0.5) * np.minimum(1, (dur - tt) / 0.5)
def groan(dur=2.0):
    n = int(dur * SR); tt = np.arange(n) / SR
    f = 160 * np.exp(-tt / 1.2) + 40
    s = osc(f * (1 + 0.02 * np.sin(2 * np.pi * 7 * tt)), n) * 0.5
    return lp(s, 900) * np.minimum(1, tt / 0.2) * np.minimum(1, (dur - tt) / 0.3)
def glitch(dur=0.6):
    n = int(dur * SR); tt = np.arange(n) / SR
    s = np.sign(osc(180 + 1200 * (np.floor(tt * 30) % 5), n, "sin")) * 0.3 * (np.floor(tt * 45) % 2)
    return s * np.hanning(n)
def reverb(x, dur=3.0, mix=0.4):
    n = int(dur * SR); ir = lp(arng.normal(0, 1, n), 5000) * envx(n, dur / 5); ir /= np.abs(ir).sum() / 8
    wet = np.convolve(x, ir); out = np.zeros(len(wet)); out[:len(x)] += x * (1 - mix); out += wet * mix
    return out

def score(n):
    tt = np.arange(n) / SR
    # dark string-like pad: detuned saws through a slowly breathing low-pass, D minor (D2 A2 F3 + D3), modulates at the fall
    chords = [(0, [73.42, 110.0, 174.61, 146.83]), (S4, [65.41, 98.0, 155.56, 130.81]),      # Dm -> Cm (descend into the fall)
              (S7, [58.27, 87.31, 138.59, 116.54]), (S9, [55.0, 82.41, 130.81, 110.0]),     # Bbm -> Am (deeper)
              (T_END, [73.42, 110.0, 174.61, 146.83])]                                       # back to the opening (loop)
    pad = np.zeros(n)
    for ci, (t0, notes) in enumerate(chords):
        t1 = chords[ci + 1][0] if ci + 1 < len(chords) else DUR
        i0, i1 = int(t0 * SR), min(n, int(t1 * SR) + int(0.8 * SR))
        m = i1 - i0
        seg_ = np.zeros(m)
        for f in notes:
            for det in (-0.12, 0.0, 0.11):
                seg_ += osc(f * 2 ** (det / 12), m)
        e = np.minimum(1, np.arange(m) / (0.8 * SR)) * np.minimum(1, (m - np.arange(m)) / (0.8 * SR))
        pad[i0:i1] += seg_ * e / 12
    pad = lp(pad, 1200) * 0.7 + lp(pad, 400) * 0.6
    sub = osc(36.7, n, "sin") * 0.35
    # slow heartbeat-like timpani pulse that tightens toward the horizon
    pulse = np.zeros(n)
    t = 0.0
    while t < DUR:
        bpm = 60 if t < S4 else (72 if t < S7 else (84 if t < S8 else 52))
        if not (T_BLACK - 0.4 < t < S9 + 0.5):
            place(pulse, boom(0.5, 70, 42, 0.12), t, 0.5)
            place(pulse, boom(0.4, 60, 40, 0.1), t + 0.22, 0.32)
        t += 60 / bpm
    lvl = np.interp(tt, [0, 3.5, S1, S4, S7, S8, T_BLACK - 0.4, T_BLACK, S9 + 0.6, S10, T_END, DUR],
                    [0.9, 0.9, 0.75, 0.85, 0.8, 0.9, 1.0, 0.0, 0.7, 0.85, 1.0, 0.9])
    return (pad + sub + pulse) * lvl

def render_audio(out):
    n = int(DUR * SR)
    mus = score(n)
    fx = np.zeros(n)
    place(fx, reverb(boom(2.4, 95, 26, 0.8), 3.0, 0.4), 0.0, 1.0)              # hook impact
    place(fx, whoosh(1.2, rev=True), S1 - 1.2, 0.35)
    for t0 in (ws(1, 3), ws(1, 11)): place(fx, tick(1300), t0, 0.4)           # callout pings
    place(fx, whoosh(0.7), S2 - 0.3, 0.35); place(fx, tick(1500), ws(2, 10), 0.45)
    place(fx, riser(1.4), S3 - 1.4, 0.4); place(fx, reverb(boom(1.8, 80, 30, 0.5)), ws(3, 1), 0.8)
    place(fx, boom(1.2, 70, 38, 0.3), ws(3, 14), 0.55)
    place(fx, shepard(T_FALL_DIAG - S4 + 0.3, 110, up=False), S4, 0.5)          # "let's fall in": endless falling tone
    place(fx, whoosh(T_FALL_DIAG - S4), S4, 0.6); place(fx, reverb(boom(2.0, 90, 30, 0.6)), T_FALL_DIAG, 0.9)
    place(fx, tick(1200), ws(4, 11), 0.5); place(fx, tick(900), ws(4, 15), 0.5)
    place(fx, groan(ws(5, 13) - ws(5, 6) + 0.6), ws(5, 6), 0.55)              # stretching
    place(fx, reverb(boom(1.6, 85, 30, 0.45)), ws(5, 17), 0.85)               # "spaghettification"
    place(fx, whoosh(0.7), S6 - 0.3, 0.35); place(fx, boom(1.4, 60, 30, 0.4), S6, 0.6)
    # time dilation: ticks of "your clock" as seen from far away, spreading out and dying
    t = S7 + 0.3; gap = 0.5
    while t < ws(7, 28):
        place(fx, tick(2600), t, 0.45); gap *= 1.18; t += gap
    place(fx, shepard(T_BLACK - S8, 220, up=False) * 0.8, S8, 0.45)            # second fall, into the horizon
    for k in range(int((T_BLACK - S8) / 0.5)): place(fx, tick(2000), S8 + k * 0.5, 0.35)   # normal ticking for you
    place(fx, riser(T_BLACK - T_HORIZON), T_HORIZON, 0.45)
    place(fx, reverb(boom(3.0, 70, 24, 1.0), 4.0, 0.5), T_BLACK, 1.0)          # crossing: hit, then near-silence
    place(fx, whoosh(0.6), S9, 0.3)
    for i in range(6): place(fx, tick(1100 + 120 * i), S9 + 0.25 + i * 0.35, 0.35)   # cones appearing
    place(fx, boom(1.2, 75, 35, 0.35), ws(9, 7), 0.6)
    place(fx, reverb(boom(2.0, 70, 26, 0.6), 3.0, 0.45), ws(10, 9), 0.8)        # "?"
    place(fx, glitch(1.0), ws(10, 17), 0.5)
    place(fx, reverb(boom(3.0, 60, 22, 1.1), 4.0, 0.5), ws(10, 17), 0.9)        # "breaks down"
    place(fx, whoosh(1.6), DUR - 1.6, 0.35)
    vo = np.zeros(n)
    for l in TIM:
        s, _ = sf.read(l["file"]); place(vo, s, l["start"])
    vo = lp(hp(vo, 85), 13000); vo = vo / (np.abs(vo).max() + 1e-9) * 0.9
    env = lp(np.abs(vo), 7); env /= env.max() + 1e-9
    duck = 1 - 0.55 * np.clip(env * 3, 0, 1)
    mix = vo + mus * 0.11 * duck + fx * (0.55 + 0.45 * duck)
    mix = np.tanh(mix * 1.05) * 0.95
    sf.write(out, np.stack([mix, mix], 1).astype(np.float32), SR, subtype="FLOAT")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        import os; os.makedirs("pv", exist_ok=True)
        ts = [float(x) for x in sys.argv[2:]] if len(sys.argv) > 2 else None
        render_video(None, ts or [0.1, 2.0, 6.0, 8.6, 12.5, 14.8, 17.0, 21.5, 24.3, 27.0, 30.5, 34.6, 38.0, 43.0, 47.5, 51.5, 53.6, 57.0, 59.7, 63.6, 65.4, 69.8])
    else:
        render_audio("mix.wav"); print("audio done", flush=True)
        render_video("video.mp4"); print("video done", flush=True)
