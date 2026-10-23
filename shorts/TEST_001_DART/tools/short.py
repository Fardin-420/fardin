#!/usr/bin/env python3
# DART documentary Short (test, 20 s): original procedural graphics + local Kokoro narration + synthesized score/SFX.
import json, math, subprocess, sys
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy.signal import butter, sosfilt

W, H, FPS, DUR = 1080, 1920, 30, 20.0
NF = int(DUR * FPS)
SR = 48000
PREVIEW = len(sys.argv) > 1 and sys.argv[1] == "preview"
rng = np.random.default_rng(22)
TIM = json.load(open("timing.json"))
WT = {}  # (line, word index) -> start time
for l in TIM:
    for k, (w, s, e) in enumerate(l["words"]):
        WT[(l["line"], k)] = (s, e)
def ws(line, k): return WT[(line, k)][0]
def we(line, k): return WT[(line, k)][1]

# ------------------------------------------------------------------ key beats (from narration timing)
T_FLASH = we(0, 6) - 0.05            # "asteroid." -> impact frame
T_ONPURPOSE = ws(0, 7)
T_REWIND = (2.35, 2.84)
T_B = 2.84                           # mission diagram
T_LABEL_DIM = ws(1, 8)
T_SPEED = ws(1, 10)
T_C = ws(2, 0)                       # camera feed
IMG_TIMES = [T_C, T_C + 1.0, T_C + 2.0, T_C + 3.0]
T_LOST = we(2, 12)                   # "stopped."
T_D = ws(3, 0)                       # orbit result
T_32 = ws(3, 9)                      # "thirty"
T_E = ws(4, 0)
T_LOOP = 19.80

# ------------------------------------------------------------------ procedural asteroid
def fbm(n, seed, octaves=6):
    r = np.random.default_rng(seed); out = np.zeros((n, n)); amp = 1.0
    for o in range(octaves):
        g = 4 * 2 ** o
        base = r.normal(0, 1, (g, g))
        out += amp * np.asarray(Image.fromarray(base.astype(np.float32)).resize((n, n), Image.BICUBIC))
        amp *= 0.5
    return out / 2.0

def make_rock(n, seed, ax=1.0, ay=0.82, boulders=260, light=(-0.65, -0.45, 0.62)):
    r = np.random.default_rng(seed)
    y, x = np.mgrid[-1:1:n * 1j, -1:1:n * 1j]
    ang = np.arctan2(y, x)
    edge = 0.86 + 0.05 * np.sin(3 * ang + seed) + 0.03 * np.sin(7 * ang + 2 * seed)
    rr = np.sqrt((x / ax) ** 2 + (y / ay) ** 2) / edge
    inside = rr < 1
    h = np.sqrt(np.clip(1 - rr ** 2, 0, 1)) * 0.9
    h += fbm(n, seed, 7) * 0.05
    lump = fbm(n, seed + 5, 6)
    for _ in range(boulders):                      # rubble-pile boulders: flat, irregular, varied
        cx, cy = r.uniform(-0.9, 0.9, 2); rad = r.uniform(0.01, 0.06) ** 1.2 * 1.8
        sq = r.uniform(0.6, 1.4); th = r.uniform(0, np.pi)
        u = (x - cx) * np.cos(th) + (y - cy) * np.sin(th); v = -(x - cx) * np.sin(th) + (y - cy) * np.cos(th)
        d = ((u / sq) ** 2 + (v * sq) ** 2) / rad ** 2 * (1 + 0.35 * lump)
        h += np.where(d < 1, np.clip(1 - d, 0, 1) ** 0.6 * rad * 0.45, 0)
    gy, gx = np.gradient(h, 2.0 / n)
    nrm = np.stack([-gx, -gy, np.ones_like(h)], -1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    L = np.array(light); L /= np.linalg.norm(L)
    shade = np.clip(nrm @ L, 0, 1) ** 1.1
    albedo = 0.75 + 0.18 * fbm(n, seed + 9, 5)
    g = np.clip(shade * albedo * 255 * 1.15 + 4, 0, 255)
    alpha = np.clip((1 - rr) * n * 0.08, 0, 1) * inside
    rgba = np.dstack([g, g, g, alpha * 255]).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")

print("building rocks", flush=True)
DIMO = make_rock(1600 if not PREVIEW else 800, 3, boulders=180)
DIDY = make_rock(900 if not PREVIEW else 500, 11, ax=1.0, ay=0.93, boulders=90)

# starfield
STARS = Image.new("RGB", (W, H), (2, 3, 8))
_d = ImageDraw.Draw(STARS)
for _ in range(900):
    x, y = rng.uniform(0, W), rng.uniform(0, H); b = int(rng.uniform(40, 255) ** 1.0); s = rng.choice([1, 1, 1, 2])
    _d.ellipse((x, y, x + s, y + s), fill=(b, b, min(255, b + 20)))
STARS = STARS.filter(ImageFilter.GaussianBlur(0.6))

# ------------------------------------------------------------------ helpers
def clamp(v, a, b): return max(a, min(b, v))
def seg(t, a, b): return clamp((t - a) / (b - a), 0, 1)
def ease(x): x = clamp(x, 0, 1); return x * x * (3 - 2 * x)
def ease_out(x): x = clamp(x, 0, 1); return 1 - (1 - x) ** 3
def lerp(a, b, k): return a + (b - a) * k

F_CAP = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
F_UI = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
F_MONO = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf"
_fc = {}
def font(p, s):
    if (p, s) not in _fc: _fc[(p, s)] = ImageFont.truetype(p, s)
    return _fc[(p, s)]
WHITE, YELLOW, BLACK, RED, CYAN = (255, 255, 255), (255, 212, 0), (0, 0, 0), (235, 45, 45), (120, 210, 255)

def paste_rock(canvas, rock, cx, cy, width, rot=0):
    hgt = int(width * rock.height / rock.width)
    if width < 2: return
    im = rock.resize((int(width), max(1, hgt)), Image.BILINEAR)
    if rot: im = im.rotate(rot, Image.BILINEAR, expand=True)
    canvas.paste(im, (int(cx - im.width / 2), int(cy - im.height / 2)), im)

def rock_crop_view(rock, scale, cx_off=0.0, cy_off=0.0):
    """Asteroid filling the frame: scale = rock width / frame width; crops before resizing (fast at big scales)."""
    img = Image.new("RGB", (W, H), (0, 0, 0))
    rw = W * scale; rh = rw * rock.height / rock.width
    left = W / 2 - rw / 2 + cx_off * W; top = H / 2 - rh / 2 + cy_off * H
    # visible window in rock coords
    sx = rock.width / rw
    x0, y0 = max(0, -left * sx), max(0, -top * sx)
    x1, y1 = min(rock.width, (W - left) * sx), min(rock.height, (H - top) * sx)
    if x1 <= x0 or y1 <= y0: return img
    crop = rock.crop((int(x0), int(y0), int(math.ceil(x1)), int(math.ceil(y1))))
    tw, th = int((x1 - x0) / sx), int((y1 - y0) / sx)
    crop = crop.resize((max(1, tw), max(1, th)), Image.BILINEAR)
    img.paste(crop, (int(left + x0 / sx), int(top + y0 / sx)), crop)
    return img

def draw_dart(d, x, y, s, ang):
    """DART: box bus + two long roll-out solar arrays, drawn as a simple icon."""
    ca, sa = math.cos(ang), math.sin(ang)
    def P(px, py): return (x + (px * ca - py * sa) * s, y + (px * sa + py * ca) * s)
    body = [P(-0.5, -0.5), P(0.5, -0.5), P(0.5, 0.5), P(-0.5, 0.5)]
    for sgn in (-1, 1):
        arr = [P(-0.35, sgn * 0.6), P(0.35, sgn * 0.6), P(0.35, sgn * 3.2), P(-0.35, sgn * 3.2)]
        d.polygon(arr, fill=(60, 90, 170), outline=(170, 200, 255))
    d.polygon(body, fill=(215, 205, 170), outline=WHITE)
    d.ellipse((P(0.5, 0)[0] - s * 0.18, P(0.5, 0)[1] - s * 0.18, P(0.5, 0)[0] + s * 0.18, P(0.5, 0)[1] + s * 0.18), fill=(40, 40, 40))

def label(d, x, y, text, sub=None, anchor_x=None, anchor_y=None, k=1.0, color=WHITE):
    if k <= 0: return
    f = font(F_UI, 40); fs = font(F_MONO, 30)
    if anchor_x is not None:
        ex, ey = lerp(anchor_x, x, ease_out(k)), lerp(anchor_y, y, ease_out(k))
        d.line((anchor_x, anchor_y, ex, ey), fill=color, width=4)
        d.ellipse((anchor_x - 9, anchor_y - 9, anchor_x + 9, anchor_y + 9), outline=color, width=4)
    if k > 0.5:
        d.text((x, y), text, font=f, fill=color, anchor="lb", stroke_width=4, stroke_fill=BLACK)
        if sub: d.text((x, y + 8), sub, font=fs, fill=(220, 220, 220), anchor="lt", stroke_width=3, stroke_fill=BLACK)

def chip(d, x, y, text, bg=RED, size=34):
    f = font(F_MONO, size); tw = f.getlength(text)
    d.rounded_rectangle((x, y, x + tw + 36, y + size + 26), 10, fill=bg)
    d.text((x + 18, y + (size + 26) / 2), text, font=f, fill=WHITE, anchor="lm")

def big_stamp(d, cx, cy, text, age, color=YELLOW, size=150):
    pop = 1 + 0.5 * max(0, 1 - age / 0.12)
    f = font(F_CAP, int(size * pop))
    d.text((cx, cy), text, font=f, fill=color, anchor="mm", stroke_width=12, stroke_fill=BLACK)

# ------------------------------------------------------------------ captions (word-by-word, max 2 lines)
CHUNKS = [  # (line, first word idx, last word idx, display text tokens with emphasis)
    (0, 0, 1, [("NASA", 0), ("CRASHED", 1)]),
    (0, 2, 3, [("A", 0), ("SPACECRAFT", 0)]),
    (0, 4, 6, [("INTO", 0), ("AN", 0), ("ASTEROID.", 1)]),
    (0, 7, 8, [("ON", 1), ("PURPOSE.", 1)], ),
    (1, 0, 3, [("IN", 0), ("2022,", 0)]),
    (1, 4, 7, [("DART", 1), ("FLEW", 0), ("STRAIGHT", 0), ("AT", 0)]),
    (1, 8, 8, [("DIMORPHOS,", 1)]),
    (1, 9, 14, [("AT", 0), ("14,000", 1), ("MPH.", 1)]),
    (2, 0, 2, [("ITS", 0), ("CAMERA", 0), ("SENT", 0)]),
    (2, 3, 7, [("BACK", 0), ("ONE", 1), ("IMAGE", 1), ("EVERY", 0), ("SECOND...", 0)]),
    (2, 8, 10, [("UNTIL", 0), ("THE", 0), ("SIGNAL", 0)]),
    (2, 11, 12, [("JUST", 0), ("STOPPED.", 1)]),
    (3, 0, 1, [("WEEKS", 0), ("LATER,", 0)]),
    (3, 2, 4, [("TELESCOPES", 0), ("CONFIRMED", 0), ("IT.", 0)]),
    (3, 5, 7, [("THE", 0), ("ASTEROID'S", 0), ("ORBIT", 1)]),
    (3, 8, 12, [("WAS", 0), ("32", 1), ("MINUTES", 1), ("SHORTER.", 1)]),
    (4, 0, 3, [("THE", 0), ("FIRST", 1), ("TIME", 0), ("HUMANS", 0)]),
    (4, 4, 5, [("DELIBERATELY", 1), ("CHANGED", 1)]),
    (4, 6, 10, [("HOW", 0), ("A", 0), ("CELESTIAL", 1), ("BODY", 1), ("MOVES.", 1)]),
]
# map each display token to the start time of the spoken word(s) it covers
CAPS = []
for ci, (ln, a, b, toks) in enumerate(CHUNKS):
    n_sp = b - a + 1
    times = [ws(ln, a + min(n_sp - 1, round(j * n_sp / len(toks)))) for j in range(len(toks))]
    if ln == 1 and a == 9: times = [ws(1, 9), ws(1, 10), ws(1, 12)]
    if ln == 1 and a == 0: times = [ws(1, 0), ws(1, 1)]
    if ln == 3 and a == 8: times = [ws(3, 8), ws(3, 9), ws(3, 11), ws(3, 12)]
    start = times[0]
    if ci + 1 < len(CHUNKS):
        nl, na = CHUNKS[ci + 1][0], CHUNKS[ci + 1][1]
        end = ws(nl, na) if nl == ln else min(we(ln, b) + 0.35, ws(nl, na))
    else:
        end = we(ln, b) + 0.4
    CAPS.append((start, end, list(zip([t for t, _ in toks], times, [e for _, e in toks]))))

def cap_y(t):
    return 1460

def draw_caption(img, t):
    d = ImageDraw.Draw(img)
    for (a, b, toks) in CAPS:
        if not (a <= t < b): continue
        vis = [(w, s, e) for (w, s, e) in toks if s <= t + 0.02]
        if not vis: return
        base = 104
        items = []
        for w, s, e in vis:
            age = t - s; pop = 1 + 0.25 * max(0, 1 - age / 0.11)
            items.append((w, int(base * pop), e))
        gap, maxw = 24, 920
        lines, cur, cw = [], [], 0
        for w, sz, e in items:
            fw = font(F_CAP, sz).getlength(w)
            if cur and cw + gap + fw > maxw: lines.append(cur); cur, cw = [], 0
            cur.append((w, sz, e, fw)); cw += (gap if len(cur) > 1 else 0) + fw
        lines.append(cur)
        lines = lines[-2:]
        lh = int(base * 1.1); y0 = cap_y(t) - (len(lines) - 1) * lh / 2
        for li, line in enumerate(lines):
            tot = sum(x[3] for x in line) + gap * (len(line) - 1); x = W / 2 - tot / 2
            for w, sz, e, fw in line:
                d.text((x, y0 + li * lh), w, font=font(F_CAP, sz), fill=YELLOW if e else WHITE, anchor="lm",
                       stroke_width=10, stroke_fill=BLACK)
                x += fw + gap
        return

# ------------------------------------------------------------------ grading / texture
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1 - 0.5 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) ** 1.5).clip(0.3, 1)[..., None]
GRAIN = [rng.normal(0, 6, (H // 2, W // 2, 1)).astype(np.float32).repeat(2, 0).repeat(2, 1) for _ in range(4)]
def grade(img, fi, warm=True, noise=1.0, shake=(0, 0)):
    a = np.asarray(img, np.float32)
    if warm:  # teal shadows / warm highlights, documentary grade
        lum = a.mean(2, keepdims=True) / 255
        a = a * (1 + 0.06 * (lum - 0.5) * np.array([1, 0.2, -1], np.float32)) + (1 - lum) * np.array([-2, 3, 8], np.float32)
    a = a * VIG + GRAIN[fi % 4] * noise
    out = Image.fromarray(a.clip(0, 255).astype(np.uint8))
    if shake != (0, 0):
        out = out.transform(out.size, Image.AFFINE, (1, 0, shake[0], 0, 1, shake[1]), Image.BILINEAR)
    return out

def static_frame(fi, level=1.0):
    n = rng.integers(0, 255, (H // 4, W // 4, 1), dtype=np.uint8).repeat(3, 2)
    im = Image.fromarray(n).resize((W, H), Image.NEAREST)
    return Image.eval(im, lambda v: int(v * 0.35 * level))

# ------------------------------------------------------------------ scenes
def scene_approach(t, fi, k):
    """Close approach, illustrated camera view. k: 0..1 progress of the rush."""
    scale = lerp(0.95, 3.4, ease(k) ** 1.6)
    img = rock_crop_view(DIMO, scale, 0.02, 0.03)
    return img

DIDY_POS = (430, 860); DIMO_ORBIT = (430, 860, 360, 120)  # cx, cy, rx, ry
def dimorphos_pos(phase):
    cx, cy, rx, ry = DIMO_ORBIT
    return cx + rx * math.cos(phase), cy + ry * math.sin(phase)

def scene_mission(t, fi):
    k = seg(t, T_B, T_C)
    z = lerp(1.0, 1.07, ease(k))
    img = STARS.copy(); d = ImageDraw.Draw(img, "RGBA")
    cx, cy, rx, ry = DIMO_ORBIT
    d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), outline=(120, 170, 220, 110), width=3)
    paste_rock(img, DIDY, *DIDY_POS, 300)
    ph = 0.35 + 0.05 * k
    dx, dy = dimorphos_pos(ph)
    paste_rock(img, DIMO, dx, dy, 70)
    # DART inbound from lower right
    p = ease(seg(t, T_B + 0.2, T_C - 0.1))
    sx, sy = W + 120, H - 300
    tx, ty = lerp(sx, dx + 60, p * 0.9), lerp(sy, dy + 90, p * 0.9)
    ang = math.atan2(dy - sy, dx - sx)
    for j in range(1, 26):  # dotted trajectory to the target
        q = j / 25
        px, py = lerp(sx, dx, q), lerp(sy, dy, q)
        if q > p * 0.9: d.ellipse((px - 4, py - 4, px + 4, py + 4), fill=(255, 212, 0, 170))
    for j in range(12):     # motion streak behind the spacecraft
        q = j / 12
        d.line((tx - 26 * j * math.cos(ang) * 1.6, ty - 26 * j * math.sin(ang) * 1.6,
                tx - 26 * (j + 1) * math.cos(ang) * 1.6, ty - 26 * (j + 1) * math.sin(ang) * 1.6),
               fill=(160, 210, 255, int(150 * (1 - q))), width=6)
    draw_dart(d, tx, ty, 13, ang)
    label(d, 170, 600, "DIDYMOS", "780 m wide", DIDY_POS[0] - 60, DIDY_POS[1] - 120, seg(t, T_B + 0.6, T_B + 0.95))
    label(d, 640, 1080, "DIMORPHOS", "160 m wide - the target", dx + 10, dy + 30, seg(t, T_LABEL_DIM, T_LABEL_DIM + 0.3), YELLOW)
    if t >= T_SPEED:
        age = t - T_SPEED
        f = font(F_CAP, int(118 * (1 + 0.4 * max(0, 1 - age / 0.12))))
        d.text((W / 2, 300), "14,000 MPH", font=f, fill=WHITE, anchor="mm", stroke_width=10, stroke_fill=BLACK)
        d.text((W / 2, 395), "6.1 km/s", font=font(F_MONO, 44), fill=CYAN, anchor="mm", stroke_width=4, stroke_fill=BLACK)
    chip(d, 40, 160, "SEPT 26, 2022", bg=(30, 30, 30))
    if z != 1.0:  # motivated push toward the target
        zw, zh = W / z, H / z; fx, fy = lerp(W / 2, dx, 0.5), lerp(H / 2, dy, 0.35)
        x0, y0 = clamp(fx - zw / 2, 0, W - zw), clamp(fy - zh / 2, 0, H - zh)
        img = img.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + zw, y0 + zh))
    return img

FEED_SCALES = [0.28, 0.55, 1.15, 2.6]
def scene_feed(t, fi):
    idx = sum(1 for it in IMG_TIMES if t >= it) - 1
    idx = clamp(idx, 0, 3)
    img = rock_crop_view(DIMO, FEED_SCALES[idx], 0.01, 0.0)
    img = Image.eval(img.convert("L"), lambda v: int(min(255, v * 1.05))).convert("RGB")
    d = ImageDraw.Draw(img)
    if idx == 3:  # the last image only partly arrived before the signal cut
        cut = int(H * 0.58)
        jag = [(x, cut + int(25 * math.sin(x * 0.05) + rng.integers(-8, 8))) for x in range(0, W + 40, 40)]
        d.polygon([(0, H)] + jag + [(W, H)], fill=(0, 0, 0))
    since = t - IMG_TIMES[idx]
    if since < 0.08: img = Image.eval(img, lambda v: min(255, v + 70))  # frame-arrival pop
    d.text((40, 160), f"IMAGE {idx + 1:02d}", font=font(F_MONO, 40), fill=WHITE, stroke_width=3, stroke_fill=BLACK)
    d.text((40, 215), "1 IMAGE / SECOND", font=font(F_MONO, 30), fill=CYAN, stroke_width=3, stroke_fill=BLACK)
    return img

def scene_lost(t, fi):
    img = static_frame(fi, 0.6 if t < T_LOST + 0.25 else 0.25)
    d = ImageDraw.Draw(img)
    d.text((W / 2, 780), "SIGNAL LOST", font=font(F_CAP, 120), fill=RED, anchor="mm", stroke_width=10, stroke_fill=BLACK)
    return img

def scene_orbit(t, fi, pull=0.0):
    img = STARS.copy(); d = ImageDraw.Draw(img, "RGBA")
    cx, cy = 540, 900
    r_old, r_new = 360, 330
    for a0 in range(0, 360, 6):  # dashed pre-impact orbit
        d.arc((cx - r_old, cy - r_old, cx + r_old, cy + r_old), a0, a0 + 3, fill=(170, 170, 170, 200), width=4)
    k_new = seg(t, T_D + 0.3, T_D + 1.0)
    if k_new > 0:
        d.arc((cx - r_new, cy - r_new, cx + r_new, cy + r_new), -90, -90 + 360 * ease(k_new), fill=YELLOW, width=7)
    paste_rock(img, DIDY, cx, cy, 250)
    ph = -0.9 + 0.35 * seg(t, T_D, 19.4)
    px, py = cx + r_new * math.cos(ph), cy + r_new * math.sin(ph)
    tail_dir = ph + math.pi * 0.62
    for j in range(40):  # ejecta tail seen after impact
        q = j / 40
        tx, ty = px + math.cos(tail_dir) * 420 * q, py + math.sin(tail_dir) * 420 * q
        rr = 10 + 70 * q
        d.ellipse((tx - rr, ty - rr, tx + rr, ty + rr), fill=(200, 200, 210, int(26 * (1 - q))))
    paste_rock(img, DIMO, px, py, 66)
    if pull == 0:  # labels clear out for the closing pull-back so the caption owns the frame
        label(d, 60, 560, "OLD ORBIT", "11 h 55 min", cx - r_old * 0.71, cy - r_old * 0.71, seg(t, T_D + 0.1, T_D + 0.4), (210, 210, 210))
        label(d, 60, 1330, "NEW ORBIT", "11 h 23 min", cx - r_new * 0.5, cy + r_new * 0.87, seg(t, T_32 - 0.1, T_32 + 0.2), YELLOW)
    # period counter
    mins = int(round(lerp(55, 23, ease(seg(t, T_32 - 0.25, T_32 + 0.6)))))
    d.text((W / 2, 250), f"11 h {mins:02d} min", font=font(F_MONO, 86), fill=WHITE, anchor="mm", stroke_width=6, stroke_fill=BLACK)
    d.text((W / 2, 330), "TIME FOR ONE ORBIT", font=font(F_MONO, 30), fill=CYAN, anchor="mm", stroke_width=3, stroke_fill=BLACK)
    if t >= T_32 + 0.6 and t < T_E:
        big_stamp(d, W / 2, 440, "-32 MIN", t - (T_32 + 0.6), size=120)
    d.text((W / 2, 1780), "diagram not to scale  |  source: NASA, Oct 11 2022", font=font(F_MONO, 24),
           fill=(190, 190, 190), anchor="mm")
    if pull > 0:  # slow motivated pull-back for the closing line
        z = 1 + 0.22 * (1 - pull)
        zw, zh = W / z, H / z
        img = img.resize((W, H), Image.BICUBIC, box=((W - zw) / 2, (H - zh) / 2 - 60 * (1 - pull), (W + zw) / 2, (H + zh) / 2 - 60 * (1 - pull)))
        d = ImageDraw.Draw(img)
        kk = seg(t, T_E + 0.2, T_E + 0.6)
        if kk > 0:
            y = 1660
            d.rectangle((60, y - 4, 60 + 960 * ease_out(kk), y), fill=YELLOW)
            d.text((60, y + 20), "FIRST PLANETARY DEFENSE TEST", font=font(F_UI, 46), fill=WHITE, stroke_width=4, stroke_fill=BLACK)
    return img

def frame(t, fi):
    shake = (0, 0); warm = True; noise = 1.0
    if t < T_FLASH:
        k = seg(t, 0, T_FLASH)
        img = scene_approach(t, fi, k)
        amp = 2 + 14 * k ** 2
        shake = (rng.uniform(-amp, amp), rng.uniform(-amp, amp))
        d = ImageDraw.Draw(img)
        d.text((40, 160), f"RANGE {lerp(18.0, 0.2, k):05.1f} km", font=font(F_MONO, 38), fill=WHITE, stroke_width=3, stroke_fill=BLACK)
    elif t < T_FLASH + 0.1:
        img = Image.new("RGB", (W, H), (255, 255, 255))           # impact frame
    elif t < T_REWIND[0]:
        img = scene_lost(t, fi)
    elif t < T_B:                                                  # rewind to the story's start
        k = seg(t, *T_REWIND)
        img = scene_approach(t, fi, 1 - k)
        img = Image.blend(img, static_frame(fi, 1.0), 0.35)
        d = ImageDraw.Draw(img)
        chip(d, 40, 160, "REWIND", bg=(30, 30, 30))
        shake = (0, rng.uniform(-20, 20))
    elif t < T_C:
        img = scene_mission(t, fi)
    elif t < T_LOST:
        img = scene_feed(t, fi); warm = False
    elif t < T_D:
        img = scene_lost(t, fi); warm = False; noise = 0.5
    elif t < T_E:
        img = scene_orbit(t, fi)
    elif t < T_LOOP:
        img = scene_orbit(t, fi, pull=ease(seg(t, T_E, T_LOOP)))
    else:
        img = scene_approach(t, fi, 0.0)                           # loops into the opening shot
    img = grade(img, fi, warm, noise, shake)
    d = ImageDraw.Draw(img)
    d.text((40, 70), "ILLUSTRATION - NOT MISSION FOOTAGE", font=font(F_MONO, 26), fill=(215, 215, 215),
           stroke_width=3, stroke_fill=BLACK)
    draw_caption(img, t)
    return img

def render_video(out):
    if PREVIEW:
        for t in [0.4, 1.4, 1.95, 2.6, 3.6, 5.0, 6.4, 7.6, 9.6, 10.6, 11.3, 12.6, 15.5, 16.2, 18.6, 19.7]:
            frame(t, int(t * FPS)).resize((270, 480)).save(f"pv_{int(t*100):04d}.jpg", quality=82)
        return
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                          "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for fi in range(NF):
        p.stdin.write(frame(fi / FPS, fi).tobytes())
        if fi % 60 == 0: print("frame", fi, flush=True)
    p.stdin.close(); p.wait()

# ------------------------------------------------------------------ audio
def bp(x, lo, hi): return sosfilt(butter(2, [lo, hi], btype="band", fs=SR, output="sos"), x)
def lp(x, hi): return sosfilt(butter(2, hi, btype="low", fs=SR, output="sos"), x)
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
def static_n(dur):
    n = int(dur * SR); return bp(rng.normal(0, 1, n), 1200, 9000) * 0.5
def riser(dur):
    n = int(dur * SR); tt = np.arange(n) / SR; fr = 120 * 2 ** (2.3 * tt / dur)
    return (np.sin(2 * np.pi * np.cumsum(fr) / SR) * 0.4 + bp(rng.normal(0, 1, n), 900, 6000) * 0.3 * tt / dur) * (tt / dur) ** 2
def rewind_s(dur):
    n = int(dur * SR); tt = np.arange(n) / SR; fr = 2600 - 2200 * tt / dur
    return (np.sin(2 * np.pi * np.cumsum(fr) / SR) * 0.25 + bp(rng.normal(0, 1, n), 1500, 8000) * 0.3) * np.hanning(n)

def render_audio(out):
    n = int(DUR * SR); tt = np.arange(n) / SR
    # score: slow minor pad (A minor add9) with a pulse that tightens toward the reveal
    pad = sum(a * np.sin(2 * np.pi * f * tt + 0.4 * np.sin(2 * np.pi * 0.13 * tt * (i + 1)))
              for i, (f, a) in enumerate([(55, 0.5), (110, 0.3), (130.8, 0.18), (164.8, 0.16), (246.9, 0.08)]))
    pad = lp(pad, 1800)
    pulse_rate = np.interp(tt, [0, T_C, T_LOST, T_D, 19.3, 20], [1.6, 2.0, 3.2, 1.6, 1.6, 1.6])
    pulse = (0.6 + 0.4 * np.sin(2 * np.pi * np.cumsum(pulse_rate) / SR) ** 8)
    lvl = np.interp(tt, [0, 1.6, T_FLASH, T_FLASH + 0.05, T_B, T_C, T_LOST, T_LOST + 0.05, T_D - 0.05, T_D + 0.4, T_E, 19.4, 20],
                    [0.16, 0.2, 0.22, 0.0, 0.14, 0.17, 0.22, 0.0, 0.0, 0.16, 0.2, 0.2, 0.16])
    bed = pad * pulse * lvl
    fx = np.zeros(n)
    place(fx, whoosh(T_FLASH), 0.0, 0.35)
    place(fx, riser(T_FLASH - 0.2), 0.2, 0.35)
    place(fx, boom(2.2, 95, 28, 0.7), T_FLASH, 1.0)                    # impact frame
    place(fx, static_n(T_REWIND[0] - T_FLASH - 0.1), T_FLASH + 0.1, 0.35)
    place(fx, rewind_s(T_REWIND[1] - T_REWIND[0]), T_REWIND[0], 0.6)
    place(fx, whoosh(0.6), T_B + 0.1, 0.4)                              # DART streak
    place(fx, blip(1000), T_B + 0.6, 0.6); place(fx, blip(1300), T_LABEL_DIM, 0.6)
    place(fx, boom(0.9, 70, 40, 0.2), T_SPEED, 0.6)
    for it in IMG_TIMES: place(fx, blip(1800, 0.07), it, 0.7)          # image arrivals
    place(fx, riser(T_LOST - IMG_TIMES[2]), IMG_TIMES[2], 0.4)
    place(fx, static_n(T_D - T_LOST), T_LOST, 0.22)                    # controlled near-silence before the reveal
    place(fx, boom(1.6, 70, 32, 0.45), T_D, 0.55)
    place(fx, blip(900), T_D + 0.1, 0.5)
    place(fx, riser(0.9), T_32 - 0.3, 0.4)
    place(fx, boom(1.8, 85, 30, 0.55), T_32 + 0.6, 0.9)                 # -32 MIN stamp
    place(fx, whoosh(0.5), T_E, 0.3)
    place(fx, whoosh(0.45), T_LOOP - 0.3, 0.35)
    vo = np.zeros(n)
    for l in TIM:
        s, sr = sf.read(l["file"])
        place(vo, s, l["start"])
    vo = lp(sosfilt(butter(2, 90, btype="high", fs=SR, output="sos"), vo), 12000)
    vo = vo / (np.abs(vo).max() + 1e-9) * 0.85
    env = lp(np.abs(vo), 7); env /= env.max() + 1e-9
    duck = 1 - 0.6 * np.clip(env * 3, 0, 1)
    mix = vo + bed * duck + fx * (0.5 + 0.5 * duck)
    mix = np.tanh(mix * 1.05) * 0.95
    sf.write(out, np.stack([mix, mix], 1).astype(np.float32), SR, subtype="FLOAT")

if __name__ == "__main__":
    if PREVIEW: render_video(None)
    else:
        render_audio("mix.wav"); print("audio done", flush=True)
        render_video("video.mp4"); print("video done", flush=True)
