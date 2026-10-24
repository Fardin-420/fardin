"""Shot library for SPACE SECRETS EP01 (YouTube). Every function: fn(t, s0, s1, **kw) -> PIL RGB image (1920x1080)."""
import json, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

import earth, moonr, star
from gfx import *
star.W, star.H = W, H                      # star.py defaults to the vertical frame

TIM = json.load(open("timing.json"))
LINES = TIM["lines"]
def ls(i): return LINES[i]["start"]
def le(i): return LINES[i]["start"] + LINES[i]["dur"]
def lw(i, k): return LINES[i]["words"][min(k, len(LINES[i]["words"]) - 1)][1]
def find(i, word, nth=0):
    c = 0
    for w, s, e in LINES[i]["words"]:
        if w.strip(".,?!:;").lower() == word.lower():
            if c == nth: return s
            c += 1
    raise KeyError((i, word))

T_GONE = find(0, "gone")
SUN_DIR = (-0.62, 0.25, 0.74)

# ================================================================== CHAPTER 1
def sh_city(t, s0, s1, moon=True, gone_at=None, clouds=False, plane=False, walkers=False, pz=(1.0, 1.06)):
    present = moon and (gone_at is None or t < gone_at)
    ml = 1.0 if present else 0.0
    if gone_at is not None and t >= gone_at: ml = 0.0
    sky = night_sky(ml, stars=1.0 if not present else 0.8)
    if present:
        sky = moon_full(sky, 1240, 330, 290, light=(-0.12, 0.05, 1.0), halo=0.55)
    if gone_at is not None and gone_at <= t < gone_at + 0.5:          # afterimage of the vanished disc
        k = 1 - (t - gone_at) / 0.5
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        rr = np.sqrt((xx - 1240) ** 2 + (yy - 330) ** 2)
        sky += (np.exp(-((rr - 290) / 26) ** 2) * 60 * k ** 2)[..., None] * np.array([0.8, 0.9, 1.0])
    if clouds:
        def cl():
            rng = np.random.default_rng(4)
            a = ndimage.gaussian_filter(rng.normal(0, 1, (270, 960)), (14, 40), mode="wrap")
            return np.clip((a / a.std() - 0.3) * 0.5, 0, 0.6)
        c = cache("clouds", cl)
        off = int((t - s0) * 12)
        cc = np.roll(c, -off, axis=1)
        cc = np.asarray(Image.fromarray((cc * 255).astype(np.uint8)).resize((W, H // 2 + 200), Image.BICUBIC), np.float32) / 255
        sky[:H // 2 + 200] = sky[:H // 2 + 200] * (1 - 0.7 * cc[..., None]) + cc[..., None] * np.array([40, 46, 62], np.float32)
    arr = city(sky, ml, shift=(t - s0) * 6)
    img = finish(arr, 0.35 if present else 0.2)
    d = ImageDraw.Draw(img, "RGBA")
    if plane:
        k = seg(t, s0, s1); x = lerp(-60, W + 60, k); y = 260 - 80 * k
        if int(t * 2.2) % 2 == 0: d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(255, 70, 60, 255))
        if int(t * 1.3 + 0.5) % 2 == 0: d.ellipse((x + 10 - 3, y - 3, x + 10 + 3, y + 3), fill=(255, 255, 255, 255))
        d.ellipse((x + 4, y - 2, x + 7, y + 1), fill=(120, 255, 140, 200))
    if walkers:
        for j in range(9):
            sp = 40 + 13 * j; x = ((t - s0) * sp + j * 233) % (W + 100) - 50; y = H - 18
            ph = math.sin((t - s0) * 6 + j)
            d.ellipse((x - 5, y - 46, x + 5, y - 36), fill=(0, 0, 0, 255))
            d.line((x, y - 36, x, y - 16), fill=(0, 0, 0), width=6)
            d.line((x, y - 16, x - 7 * ph, y), fill=(0, 0, 0), width=5); d.line((x, y - 16, x + 7 * ph, y), fill=(0, 0, 0), width=5)
    return push(img, lerp(pz[0], pz[1], ease(seg(t, s0, s1))), 1100, 420)

def sh_hud(t, s0, s1):
    sky = night_sky(0.0) * 0.8
    img = finish(sky, 0.1); d = ImageDraw.Draw(img, "RGBA")
    cx, cy = W / 2, H / 2 - 30
    for r in (120, 260):
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(140, 220, 200, 150), width=2)
    for a in range(0, 360, 90):
        x0, y0 = cx + 140 * math.cos(math.radians(a)), cy + 140 * math.sin(math.radians(a))
        x1, y1 = cx + 240 * math.cos(math.radians(a)), cy + 240 * math.sin(math.radians(a))
        d.line((x0, y0, x1, y1), fill=(140, 220, 200, 150), width=2)
    blink = (int(t * 2) % 2 == 0)
    f = font(F_MONO, 22)
    lines = ["TARGET ......... MOON", "PREDICTED POS .. RA 14h 32m  DEC -12° 05'", f"TRACKING ....... {(t - s0) * 13 + 2041:7.0f} s",
             "OPTICAL ........ NO SOURCE", "RADAR ECHO ..... NONE", "GRAVITATIONAL .. NOT DETECTED"]
    for i, l in enumerate(lines):
        if t - s0 > 0.25 * i:
            d.text((120, 640 + i * 34), l, font=f, fill=(140, 220, 200, 230) if i < 3 else (255, 120, 100, 240), anchor="lm")
    if blink: d.text((cx, cy + 300), "MOON NOT FOUND", font=font(F_SEMI, 34), fill=(255, 120, 100, 230), anchor="mm")
    tag(d, "scen", "telescope tracking view")
    return img

def _orbit_frame(t, ecx, ecy, eR, mang, mR, a, b, moon_alpha=1.0, outline=False, earth_lon=None, tilt=0.0):
    """Earth at (ecx,ecy) radius eR; Moon on an ellipse (a,b) at angle mang. Returns float array."""
    lon = -40 - 6 * t if earth_lon is None else earth_lon
    mx, my = ecx + a * math.cos(mang), ecy + b * math.sin(mang)
    behind = math.sin(mang) < 0
    base = stars_half().copy()
    sun = SUN_DIR
    if behind and moon_alpha > 0:
        m = moonr.render(W2, H2, mx / 2, my / 2, mR / 2, light=sun, base=np.zeros((H2, W2, 3), np.float32))
        base = base + m * moon_alpha
    arr = earth.render(W2, H2, ecx / 2, ecy / 2, eR / 2, 15, lon, lon - 3 * t, sun=sun, stars=base)
    if not behind and moon_alpha > 0:
        m = moonr.render(W2, H2, mx / 2, my / 2, mR / 2, light=sun, base=np.zeros((H2, W2, 3), np.float32))
        mk = (m.sum(-1, keepdims=True) > 0.5)
        arr = np.where(mk, arr * (1 - moon_alpha) + m * moon_alpha, arr)
    return up(arr), (mx, my)

def sh_orbit(t, s0, s1, vanish_at=None, mode="orbit", zoom=(1.0, 1.0), facts=False):
    k = ease(seg(t, s0, s1))
    z = lerp(zoom[0], zoom[1], k)
    ecx, ecy = 820, 560; eR = 210 * z; a, b = 640 * z, 170 * z
    mang = 0.35 + (t - s0) * 0.22
    ma = 1.0
    if vanish_at is not None and t >= vanish_at: ma = 0.0
    if mode == "gone": ma = 0.0
    arr, (mx, my) = _orbit_frame(t, ecx, ecy, eR, mang, 58 * z, a, b, ma)
    img = finish(arr, 0.3); d = ImageDraw.Draw(img, "RGBA")
    if mode != "plain":
        for i in range(0, 360, 4):
            d.arc((ecx - a, ecy - b, ecx + a, ecy + b), i, i + 2, fill=(200, 210, 230, 70 if ma > 0 else 110), width=2)
    if vanish_at is not None and vanish_at <= t < vanish_at + 0.7:
        q = (t - vanish_at) / 0.7; r = 58 * z * (1 + 1.5 * q)
        d.ellipse((mx - r, my - r, mx + r, my + r), outline=(220, 230, 255, int(200 * (1 - q))), width=3)
    if ma == 0 and mode in ("gone", "orbit"):
        dashed_circle(d, mx, my, 58 * z, 58 * z, (220, 225, 240, 150), 2, 10, 5)
        d.text((mx, my + 58 * z + 26), "the Moon's orbit · empty", font=font(F_LIGHT, 24), fill=(220, 225, 240, 200), anchor="mt")
    if facts:
        factcard(d, 1300, 760, "4.5 billion years", "the Moon has orbited Earth for most of its history", seg(t, s0 + 0.6, s0 + 1.2), GOLD, 560)
        for i, (w, txt) in enumerate((("tides", "TIDES"), ("nights", "NIGHT LIGHT"), ("evolution", "LIFE'S RHYTHMS"))):
            try: tw = find(5, w)
            except KeyError: continue
            headline(d, 1300, 300 + i * 90, txt, seg(t, tw, tw + 0.5), 46, ICE)
    tag(d, "sim" if mode != "gone" else "scen", "not to scale")
    return img

def sh_questions(t, s0, s1):
    k = ease(seg(t, s0, s1))
    lon = -60 - 8 * (t - s0)
    arr = globe(960, 560 + 30 * k, 360 * lerp(1.0, 1.12, k), lat0=20, lon=lon, sun=(-0.4, 0.3, 0.86), night_gain=2.4)
    img = finish(arr * 0.85, 0.25); d = ImageDraw.Draw(img, "RGBA")
    qs = [("oceans", "Would the oceans swallow our cities?"), ("rotation", "Would Earth lose control of its rotation?"),
          ("survive", "Could humanity survive?")]
    for i, (w, q) in enumerate(qs):
        tw = find(7, w) - 0.6
        headline(d, 120, 230 + i * 92, q, seg(t, tw, tw + 0.5) * (1 - 0.55 * seg(t, tw + 2.2, tw + 2.6)) if i < 2 else seg(t, tw, tw + 0.5), 46, WHITE)
    tag(d, "sim")
    return img

def sh_timescale(t, s0, s1):
    k = ease(seg(t, s0, s1))
    arr = globe(1460, 560, 300 * lerp(1.0, 1.15, k), lat0=15, lon=-100 - 5 * (t - s0), sun=(-0.6, 0.2, 0.77), night_gain=2.0)
    img = finish(arr * 0.8, 0.25); d = ImageDraw.Draw(img, "RGBA")
    x0, x1, y = 140, 1100, 620
    d.line((x0, y, x1, y), fill=(220, 225, 235, 200), width=3)
    marks = [("TONIGHT", 0.0, None), ("THOUSANDS OF YEARS", 0.33, ("thousands", 10)), ("MILLIONS", 0.66, ("millions", 10)), ("BILLIONS", 1.0, ("billions", 10))]
    for name, f_, cue in marks:
        x = lerp(x0, x1, f_)
        tw = s0 if cue is None else find(cue[1], cue[0]) - 0.1
        a = seg(t, tw, tw + 0.4)
        if a <= 0: continue
        d.ellipse((x - 9, y - 9, x + 9, y + 9), fill=GOLD + (int(255 * a),))
        d.text((x, y + 40), name, font=font(F_SEMI, 28), fill=(255, 255, 255, int(255 * a)), anchor="mt")
    headline(d, 140, 420, "The real consequences unfold slowly", seg(t, find(9, "consequences") - 0.3, find(9, "consequences") + 0.3), 50, GOLD)
    tag(d, "sim")
    return img

# ================================================================== CHAPTER 2
def sh_rule(t, s0, s1):
    k = seg(t, s0, s1)
    sky = night_sky(0.0) * 0.9
    fade = 1 - ease(seg(t, find(12, "vanish") - 0.2, find(12, "vanish") + 1.4))
    if fade > 0:
        sky = moon_full(sky, 520, 520, 230, light=(-0.4, 0.1, 0.9), halo=0.3 * fade, gain=fade)
    img = finish(sky, 0.3); d = ImageDraw.Draw(img, "RGBA")
    headline(d, 960, 230, "THE RULE OF THIS SCENARIO", seg(t, s0, s0 + 0.5), 30, GOLD)
    items = [("explode", "It doesn't explode into fragments", False), ("crash", "It doesn't crash into Earth", False),
             ("vanish", "Its mass and gravity simply vanish", True), ("releasing", "No destructive energy is released", False)]
    for i, (w, txt, ok) in enumerate(items):
        try: tw = find(12, w) - 0.3
        except KeyError: tw = s0 + 1 + i
        a = seg(t, tw, tw + 0.4)
        if a <= 0: continue
        y = 360 + i * 92; x = 960
        col = (120, 230, 170) if ok else (255, 140, 120)
        d.ellipse((x - 2, y - 18, x + 34, y + 18), outline=col + (int(255 * a),), width=3)
        if ok: d.line((x + 6, y, x + 14, y + 9, x + 27, y - 9), fill=col + (int(255 * a),), width=4)
        else:
            d.line((x + 7, y - 9, x + 25, y + 9), fill=col + (int(255 * a),), width=4); d.line((x + 25, y - 9, x + 7, y + 9), fill=col + (int(255 * a),), width=4)
        d.text((x + 56, y), txt, font=font(F_MED, 36), fill=(255, 255, 255, int(255 * a)), anchor="lm")
    tag(d, "scen")
    return img

def sh_versus(t, s0, s1):
    sky = night_sky(0.0) * 0.85
    q = seg(t, s0 + 0.3, s0 + 3.0)
    sky = moon_full(sky, 520, 540, 170, light=(-0.4, 0.1, 0.9), gain=1 - ease(q), halo=0.2 * (1 - q))
    img = finish(sky, 0.3); d = ImageDraw.Draw(img, "RGBA")
    # right: an explosion we are NOT simulating
    rng = np.random.default_rng(3)
    cx, cy = 1400, 540; e = ease_out(seg(t, s0 + 0.4, s0 + 3.5))
    for i in range(260):
        ang = rng.uniform(0, 2 * math.pi); sp = rng.uniform(0.2, 1.0); r = 170 * (0.6 + 2.0 * e * sp)
        x, y = cx + r * math.cos(ang), cy + r * math.sin(ang) * 0.9
        s = rng.uniform(3, 14) * (1 - 0.4 * e)
        g = int(rng.uniform(110, 200))
        d.polygon([(x + s * math.cos(ang + j * 2.1 + i), y + s * math.sin(ang + j * 2.1 + i)) for j in range(3)], fill=(g, g, g - 10, 230))
    d.line((1150, 300, 1650, 780), fill=(235, 90, 70, 200), width=10); d.line((1650, 300, 1150, 780), fill=(235, 90, 70, 200), width=10)
    d.text((520, 840), "VANISHES", font=font(F_SEMI, 36), fill=(130, 230, 170), anchor="mm")
    d.text((520, 885), "our scenario", font=font(F_LIGHT, 26), fill=SOFT, anchor="mm")
    d.text((1400, 840), "EXPLODES", font=font(F_SEMI, 36), fill=(255, 140, 120), anchor="mm")
    d.text((1400, 885), "a different disaster · not this film", font=font(F_LIGHT, 26), fill=SOFT, anchor="mm")
    d.line((960, 200, 960, 900), fill=(255, 255, 255, 60), width=2)
    tag(d, "illus")
    return img

def sh_noshock(t, s0, s1):
    k = ease(seg(t, s0, s1))
    arr = globe(960, 560, 330 * lerp(1.0, 1.06, k), lat0=18, lon=-20 - 5 * (t - s0), sun=(-0.6, 0.25, 0.76))
    img = finish(arr, 0.3); d = ImageDraw.Draw(img, "RGBA")
    a = seg(t, s0 + 0.4, s0 + 1.0)
    for r in (520, 600, 680):
        dashed_circle(d, 960, 560, r, r, (255, 140, 120, int(110 * a)), 3, 8, 4)
    headline(d, 960, 130, "NO SHOCK WAVE", a, 44, (255, 160, 140), "mm")
    tw = find(16, "atmosphere") - 0.3 if True else s0
    headline(d, 960, 960, "Atmosphere stays in place", seg(t, tw, tw + 0.5), 38, ICE, "mm")
    tag(d, "sim")
    return img

def sh_spin(t, s0, s1, axis=False, clock=False, Lvec=False, cx=960, R=360):
    k = ease(seg(t, s0, s1))
    lon = -20 - 14 * (t - s0)
    arr = globe(cx, 560, R * lerp(1.0, 1.05, k), lat0=12, lon=lon, sun=(-0.6, 0.25, 0.76))
    img = finish(arr, 0.3); d = ImageDraw.Draw(img, "RGBA")
    if axis or Lvec:
        d.line((cx, 560 - R - 120, cx, 560 + R + 60), fill=(255, 255, 255, 120), width=3)
        d.arc((cx - 160, 560 - R - 70, cx + 160, 560 - R + 10), 200, 340, fill=GOLD + (220,), width=5)
        arrow(d, cx + 150, 560 - R - 50, cx + 165, 560 - R - 35, GOLD, 5, 18)
    if Lvec:
        a = seg(t, s0 + 0.5, s0 + 1.1)
        arrow(d, cx, 560 - R - 10, cx, 560 - R - 10 - 170 * ease_out(a), (130, 230, 255, 255), 7, 26)
        label(d, cx + 30, 560 - R - 170, "L", "angular momentum", (130, 230, 255), int(255 * a), size=40)
    if clock:
        x, y, r = 1580, 540, 120
        d.ellipse((x - r, y - r, x + r, y + r), outline=(255, 255, 255, 200), width=4)
        for i in range(24):
            ang = i / 24 * 2 * math.pi
            d.line((x + (r - 12) * math.sin(ang), y - (r - 12) * math.cos(ang), x + r * math.sin(ang), y - r * math.cos(ang)), fill=(255, 255, 255, 180), width=2)
        ang = (t - s0) * 0.9
        d.line((x, y, x + (r - 25) * math.sin(ang), y - (r - 25) * math.cos(ang)), fill=GOLD, width=5)
        d.text((x, y + r + 40), "1 day = 24 h", font=font(F_SEMI, 34), fill=WHITE, anchor="mm")
        d.text((x, y + r + 80), "unchanged the next morning", font=font(F_LIGHT, 24), fill=SOFT, anchor="mm")
    tag(d, "sim", "rotation sped up")
    return img

def sh_landscape(t, s0, s1, ml=(1.0, 1.0), milky=(0.0, 0.0), moon=None, lux=False, dawn=0.0, pan=0.0, text=None):
    k = seg(t, s0, s1)
    if isinstance(ml, tuple) and len(ml) == 4: m_ = lerp(ml[0], ml[1], ease(seg(t, ml[2], ml[3])))
    else: m_ = lerp(ml[0], ml[1], ease(k))
    if isinstance(milky, tuple) and len(milky) == 4: mw = lerp(milky[0], milky[1], ease(seg(t, milky[2], milky[3])))
    else: mw = lerp(milky[0], milky[1], ease(k))
    sky = night_sky(m_, milky=mw * (1 - 0.8 * m_), warm=dawn)
    if moon is not None and m_ > 0.02:
        mx, my, mr = moon
        sky = moon_full(sky, mx, my, mr, light=(-0.1, 0.05, 1.0), halo=0.7 * m_, gain=m_)
    if dawn > 0:
        sky = star.draw_sun(sky, 1450, 640 - 120 * dawn, 38, t, bright=0.9, corona=0.8)
    arr = landscape(sky, m_ * 0.95, shift=pan * k, dawn=dawn)
    img = finish(arr, 0.35); d = ImageDraw.Draw(img, "RGBA")
    if lux:
        x, y = 1480, 170
        d.rounded_rectangle((x - 20, y - 30, x + 380, y + 150), 10, fill=(5, 8, 16, 160))
        d.text((x, y), "GROUND ILLUMINATION", font=font(F_MONO, 18), fill=(200, 210, 225), anchor="lm")
        lx = 10 ** lerp(-3, -0.7, m_)
        d.text((x, y + 55), f"{lx:.3f} lux", font=font(F_SEMI, 46), fill=GOLD, anchor="lm")
        d.text((x, y + 108), "full Moon ≈ 0.1–0.3 lux · starlight ≈ 0.001", font=font(F_LIGHT, 20), fill=SOFT, anchor="lm")
    if text:
        txt, cue_line, cue_word, col = text
        tw = find(cue_line, cue_word) - 0.3
        headline(d, 120, 200, txt, seg(t, tw, tw + 0.6), 52, col)
    tag(d, "illus" if dawn == 0 else "illus", "")
    return img

# ================================================================== CHAPTER 3: tides
def sh_coast(t, s0, s1, amp=1.0, amp_to=None, period=7.0, flats=False, title=None):
    k = seg(t, s0, s1)
    A = amp if amp_to is None else lerp(amp, amp_to, ease(k))
    img = Image.new("RGB", (W, H)); d = ImageDraw.Draw(img, "RGBA")
    for y in range(0, 700, 4):                                       # dusk sky
        q = y / 700
        d.rectangle((0, y, W, y + 4), fill=(int(lerp(12, 70, q ** 2)), int(lerp(20, 60, q ** 2)), int(lerp(45, 90, q))))
    sx = lambda x: 640 - 0.32 * (x - 300)                             # sloped beach: ground height at x
    level = 770 - A * 85 * math.sin(2 * math.pi * (t - s0) / period)
    # water body
    pts = [(0, H)]
    for x in range(0, W + 20, 20):
        y = level + 6 * math.sin(x * 0.02 + t * 2.4) + 3 * math.sin(x * 0.051 - t * 3.1)
        pts.append((x, y))
    pts.append((W, H))
    d.polygon(pts, fill=(22, 52, 86))
    for i in range(6):
        yy = level + 30 + i * 50
        d.line([(x, yy + 4 * math.sin(x * 0.01 + t + i)) for x in range(0, W, 30)], fill=(60, 110, 150, 60), width=2)
    # beach (sand) drawn over the water where ground is higher than water
    beach = [(W, H), (W, 700)] + [(x, min(H, max(300, 640 + 0.32 * (x - 1000)))) for x in range(W, 900, -20)] + [(900, H)]
    beach = [(x, max(300, 470 + 0.30 * (W - x) * -1 + 300)) for x in range(W, 799, -10)]
    gx = list(range(800, W + 10, 10))
    ground = [(x, 930 - 0.25 * (x - 800)) for x in gx]
    d.polygon([(800, H)] + ground + [(W, H)], fill=(132, 112, 82))
    d.line((0, 520, W, 520), fill=(120, 140, 170, 90), width=2)
    wet_y = level
    for x, y in ground:
        if abs(y - level) < 26: d.line((x, y, x, y + 10), fill=(90, 80, 64), width=10)
    if flats:
        d.text((1450, 470), "tidal flat", font=font(F_MED, 30), fill=WHITE, anchor="mm")
        d.text((1450, 505), "flooded and exposed twice a day", font=font(F_LIGHT, 22), fill=SOFT, anchor="mm")
    # gauge
    gx0 = 180
    d.line((gx0, 380, gx0, 860), fill=(255, 255, 255, 140), width=3)
    for j in range(9): d.line((gx0 - 10, 380 + j * 60, gx0 + 10, 380 + j * 60), fill=(255, 255, 255, 140), width=2)
    d.polygon([(gx0 + 14, level), (gx0 + 34, level - 10), (gx0 + 34, level + 10)], fill=GOLD)
    d.text((gx0 + 44, level), "sea level", font=font(F_MED, 24), fill=GOLD, anchor="lm")
    if title: headline(d, 120, 160, title[0], seg(t, s0 + 0.2, s0 + 0.8), 46, WHITE, sub=title[1])
    tag(d, "illus", "time-lapse, tides sped up")
    return img

def _envelope(R0, am, th_m, as_, th_s, n=360):
    th = np.linspace(0, 2 * np.pi, n)
    r = R0 * (1 + am * np.cos(2 * (th - th_m)) + as_ * np.cos(2 * (th - th_s)))
    return th, r

def sh_bulge(t, s0, s1, moon_off_at=None, show_sun=True, marker=True, graph=True, notes=None, lag=0.0, torque=False):
    k = seg(t, s0, s1)
    cx, cy, R = 700, 560, 210
    rot = (t - s0) * 0.5
    arr = up(earth.render(W2, H2, cx / 2, cy / 2, R / 2, 90, -rot * 57.3, -rot * 57.3, sun=(-1, 0, 0.35), stars=stars_half()))
    img = finish(arr, 0.25); d = ImageDraw.Draw(img, "RGBA")
    am = 0.18
    if moon_off_at is not None and t >= moon_off_at:                # lunar bulge relaxes with a damped slosh
        q = t - moon_off_at
        am = 0.18 * math.exp(-q / 2.2) * math.cos(q * 2.6)
    th_m = -math.radians(lag)
    th, r = _envelope(R * 1.12, am, th_m, 0.083 if show_sun else 0.0, math.pi)
    pts = [(cx + rr * math.cos(a), cy - rr * math.sin(a)) for a, rr in zip(th, r)]
    d.polygon(pts, fill=(60, 140, 255, 70), outline=(130, 200, 255, 220))
    moon_vis = moon_off_at is None or t < moon_off_at
    if moon_vis:
        mimg = moonr.render(260, 260, 130, 130, 60, light=(-1, 0, 0.3))
        mi = to_img(tone(mimg)); img.paste(mi, (1500 - 130, cy - 130), Image.fromarray((np.clip(mimg.sum(-1) * 3, 0, 255)).astype(np.uint8)))
        d = ImageDraw.Draw(img, "RGBA")
        d.text((1500, cy + 100), "MOON", font=font(F_SEMI, 28), fill=WHITE, anchor="mm")
        d.line((cx + R * 1.4, cy, 1500 - 70, cy), fill=(255, 255, 255, 60), width=2)
    else:
        dashed_circle(d, 1500, cy, 60, 60, (220, 225, 240, 140), 2, 10, 5)
        d.text((1500, cy + 100), "MOON GONE", font=font(F_SEMI, 28), fill=(255, 150, 130), anchor="mm")
    if show_sun:
        for j in range(5):
            y = cy - 160 + j * 80
            arrow(d, 60, y, 200, y, (255, 210, 120, 160), 3, 14)
        d.text((80, cy - 220), "SUNLIGHT  ·  SUN FAR TO THE LEFT", font=font(F_MONO, 18), fill=(255, 210, 140), anchor="lm")
    if marker:
        ma = math.pi / 2 + rot
        mx, my = cx + R * 0.98 * math.cos(ma), cy - R * 0.98 * math.sin(ma)
        d.ellipse((mx - 9, my - 9, mx + 9, my + 9), fill=GOLD, outline=BLACK, width=2)
        d.text((mx + 14, my), "your coast", font=font(F_MED, 22), fill=GOLD, anchor="lm")
    if torque:
        arrow(d, cx + R * 1.25 * math.cos(math.radians(lag)), cy - R * 1.25 * math.sin(math.radians(lag)), 1430, cy - 10, (255, 150, 120), 4, 16)
        d.arc((cx - R - 50, cy - R - 50, cx + R + 50, cy + R + 50), 200, 300, fill=(255, 150, 120), width=5)
        d.text((cx, cy + R + 95), "Earth's spin slows", font=font(F_SEMI, 30), fill=(255, 160, 140), anchor="mm")
        arrow(d, 1560, cy - 120, 1720, cy - 120, (130, 230, 255), 5, 20)
        d.text((1640, cy - 160), "Moon drifts outward", font=font(F_SEMI, 28), fill=(130, 230, 255), anchor="mm")
        d.text((cx + R * 1.6, cy - R * 0.9), "bulge carried ahead", font=font(F_LIGHT, 24), fill=SOFT, anchor="lm")
    if graph:                                                        # sea level at the marker vs time
        gx, gy, gw, gh = 1180, 820, 620, 150
        d.rectangle((gx, gy - gh / 2, gx + gw, gy + gh / 2), outline=(255, 255, 255, 50))
        d.text((gx, gy - gh / 2 - 22), "sea level at your coast", font=font(F_MONO, 18), fill=SOFT, anchor="lm")
        pts = []
        for i in range(120):
            tt = t - (119 - i) * 0.05
            rr_ = rot - (t - tt) * 0.5
            ama = 0.18
            if moon_off_at is not None and tt >= moon_off_at:
                q = tt - moon_off_at; ama = 0.18 * math.exp(-q / 2.2) * math.cos(q * 2.6)
            ang = math.pi / 2 + rr_
            h = ama * math.cos(2 * (ang - th_m)) + (0.083 if show_sun else 0) * math.cos(2 * (ang - math.pi))
            pts.append((gx + i / 119 * gw, gy - h / 0.3 * gh / 2))
        d.line(pts, fill=(130, 200, 255), width=3)
    if notes:
        for txt, cue, col in notes:
            tw = find(*cue) - 0.3
            headline(d, 1180, 200, txt, seg(t, tw, tw + 0.5) * (1 if True else 0), 40, col)
    tag(d, "diag", "tidal bulges hugely exaggerated")
    return img

def sh_basin(t, s0, s1):
    def make():
        rng = np.random.default_rng(8)
        a = ndimage.gaussian_filter(rng.normal(0, 1, (270, 480)), 18)
        a = (a - a.min()) / (a.max() - a.min())
        yy, xx = np.mgrid[0:270, 0:480]
        edge = np.minimum.reduce([xx, yy, 479 - xx, 269 - yy]) / 60
        return (a * 0.6 + np.clip(edge, 0, 1) * 0.6) > 0.55
    sea = cache("basin", make)
    yy, xx = np.mgrid[0:270, 0:480].astype(np.float32)
    ph = np.arctan2(yy - 120, xx - 170) + np.arctan2(yy - 160, xx - 330) * -1
    ph = ph - (t - s0) * 1.6
    amp = np.clip(np.sqrt((yy - 120) ** 2 + (xx - 170) ** 2) / 120, 0, 1) * np.clip(np.sqrt((yy - 160) ** 2 + (xx - 330) ** 2) / 120, 0, 1)
    v = np.cos(ph) * amp
    col = np.stack([40 + 50 * v, 90 + 70 * v, 160 + 70 * v], -1)
    land = np.array([70, 64, 50], np.float32)
    arr = np.where(sea[..., None], col, land)
    lines = (np.abs(np.sin(ph * 3)) < 0.06) & sea
    arr = np.where(lines[..., None], np.array([230, 240, 255], np.float32), arr)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)
    d = ImageDraw.Draw(img, "RGBA")
    for px, py in ((170, 120), (330, 160)):
        d.ellipse((px * 4 - 10, py * 4 - 10, px * 4 + 10, py * 4 + 10), outline=WHITE, width=3)
    d.text((170 * 4 + 20, 120 * 4 - 30), "amphidromic point", font=font(F_MED, 24), fill=WHITE, anchor="lm")
    headline(d, 80, 140, "Real tides are shaped by ocean basins", seg(t, s0, s0 + 0.6), 44, WHITE,
             sub="tide crests rotate around points of near-zero tide")
    tag(d, "schem")
    return img

def sh_bars(t, s0, s1, remove_at=None):
    img = finish(stars_half_up() * 0.7, 0.1); d = ImageDraw.Draw(img, "RGBA")
    headline(d, 160, 170, "TIDE-RAISING FORCE ON EARTH", seg(t, s0, s0 + 0.5), 34, TEAL)
    k = ease_out(seg(t, s0 + 0.2, s0 + 1.2))
    mk = 1.0 if remove_at is None or t < remove_at else 1 - ease(seg(t, remove_at, remove_at + 1.0))
    x0, w = 160, 1100
    d.rectangle((x0, 330, x0 + w * k * mk, 410), fill=(200, 210, 230))
    d.text((x0, 300), "MOON", font=font(F_SEMI, 28), fill=WHITE, anchor="lm")
    d.text((x0 + w * k * mk + 20, 370), "1.00" if mk > 0.05 else "gone", font=font(F_SEMI, 34), fill=WHITE, anchor="lm")
    d.rectangle((x0, 520, x0 + w * 0.46 * k, 600), fill=(255, 205, 110))
    d.text((x0, 490), "SUN", font=font(F_SEMI, 28), fill=(255, 205, 110), anchor="lm")
    d.text((x0 + w * 0.46 * k + 20, 560), "≈ 0.46", font=font(F_SEMI, 34), fill=(255, 205, 110), anchor="lm")
    # spring/neap trace
    gx, gy, gw = 160, 840, 1600
    pts1, pts2 = [], []
    for i in range(400):
        x = i / 399
        h1 = math.cos(2 * math.pi * x * 16) * (1.0 + 0.46 * math.cos(2 * math.pi * x * 2))
        h2 = math.cos(2 * math.pi * x * 16) * 0.46
        pts1.append((gx + x * gw, gy - h1 * 70)); pts2.append((gx + x * gw, gy - h2 * 70))
    a1 = seg(t, s0 + 1.0, s0 + 1.6) * (1 - 0.7 * (1 - mk))
    d.line(pts1, fill=(200, 210, 230, int(220 * a1)), width=2)
    if remove_at is not None and t >= remove_at:
        d.line(pts2, fill=(255, 205, 110, int(255 * seg(t, remove_at + 0.5, remove_at + 1.2))), width=3)
        d.text((gx + gw, gy - 120), "solar tides only: weaker, no spring–neap cycle", font=font(F_MED, 26), fill=(255, 205, 110), anchor="rm")
    d.text((gx, gy - 120), "today: Moon + Sun (springs and neaps)", font=font(F_MED, 26), fill=(200, 210, 230, int(255 * a1)), anchor="lm")
    tag(d, "diag", "relative tidal forces")
    return img

def stars_half_up():
    return cache("stars_up", lambda: up(stars_half()))

# ================================================================== CHAPTER 4: animals
def sh_phases(t, s0, s1):
    img = finish(stars_half_up() * 0.8, 0.1); d = ImageDraw.Draw(img, "RGBA")
    cx, cy, rr = 960, 560, 330
    n = 8
    for i in range(n):
        a = i / n * 2 * math.pi - math.pi / 2 + (t - s0) * 0.05
        x, y = cx + rr * math.cos(a), cy + rr * math.sin(a)
        ph = i / n * 2 * math.pi
        L = (math.sin(ph), 0, -math.cos(ph))
        m = moonr.render(140, 140, 70, 70, 52, light=(L[0] + 1e-3, 0.0, L[2]), earthshine=0.15)
        mi = to_img(tone(m)); img.paste(mi, (int(x - 70), int(y - 70)), Image.fromarray(np.clip(m.sum(-1) * 2 + 60 * (m.sum(-1) > 0), 0, 255).astype(np.uint8)))
    d = ImageDraw.Draw(img, "RGBA")
    d.text((cx, cy - 20), "29.5 days", font=font(F_SEMI, 56), fill=GOLD, anchor="mm")
    d.text((cx, cy + 34), "one lunar cycle", font=font(F_LIGHT, 28), fill=SOFT, anchor="mm")
    headline(d, 960, 100, "A BIOLOGICAL CALENDAR", seg(t, s0 + 0.3, s0 + 0.9), 30, TEAL, "mm")
    tag(d, "diag")
    return img

def sh_reef(t, s0, s1, spawn_at=None):
    def bg():
        y = np.linspace(0, 1, H)[:, None, None]
        top = np.array([20, 70, 110], np.float32); bot = np.array([2, 10, 24], np.float32)
        a = top + (bot - top) * y ** 0.7
        return np.repeat(a, W, axis=1)
    arr = cache("reefbg", bg).copy()
    yy, xx = np.mgrid[0:H:4, 0:W:4].astype(np.float32)
    shafts = np.clip(np.sin((xx * 0.012 + yy * 0.004) + t * 0.4) * np.sin(xx * 0.031 - t * 0.3), 0, 1) ** 3 * np.clip(1 - yy / 900, 0, 1)
    sh = np.asarray(Image.fromarray((shafts * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), np.float32) / 255
    arr += sh[..., None] * np.array([22, 34, 42], np.float32)
    img = finish(arr, 0.2); d = ImageDraw.Draw(img, "RGBA")
    # wobbly moon through the surface
    mx, my = 1400, 90
    d.ellipse((mx - 50, my - 26, mx + 50, my + 26), fill=(210, 230, 240, 120))
    rng = np.random.default_rng(2)
    for c in range(14):                                            # coral heads
        x = rng.uniform(0, W); base = H; h = rng.uniform(140, 360); w = rng.uniform(90, 220)
        col = tuple(int(v) for v in rng.choice([(60, 40, 70), (40, 60, 70), (70, 50, 40)]))
        for b in range(9):
            ang = -math.pi / 2 + rng.uniform(-0.9, 0.9)
            L = h * rng.uniform(0.5, 1.0)
            x1, y1 = x + L * math.cos(ang), base + L * math.sin(ang)
            d.line((x, base, x1, y1), fill=col + (255,), width=int(rng.uniform(10, 26)))
            d.ellipse((x1 - 14, y1 - 14, x1 + 14, y1 + 14), fill=col + (255,))
    if spawn_at is not None and t >= spawn_at:
        q = t - spawn_at
        rs = np.random.default_rng(9)
        for i in range(700):
            x0 = rs.uniform(0, W); v = rs.uniform(25, 70); ph = rs.uniform(0, 3)
            y = H - 200 - (q + ph) * v
            if y < -20: continue
            x = x0 + 18 * math.sin(q * 0.7 + i)
            s = rs.uniform(2, 5)
            d.ellipse((x - s, y - s, x + s, y + s), fill=(255, 170, 150, int(200 * min(1, q))))
    label(d, 120, 160, "CORAL SPAWNING", "timed partly by moonlight cues", WHITE, int(255 * seg(t, s0 + 0.3, s0 + 0.9)), size=40)
    tag(d, "illus")
    return img

def _cat(d, x, y, s, col):
    d.ellipse((x - 60 * s, y - 28 * s, x + 50 * s, y + 10 * s), fill=col)
    d.ellipse((x + 38 * s, y - 42 * s, x + 74 * s, y - 10 * s), fill=col)
    for lx in (-45, -25, 20, 38):
        d.rectangle((x + lx * s, y, x + (lx + 9) * s, y + 40 * s), fill=col)
    d.line((x - 58 * s, y - 15 * s, x - 90 * s, y + 10 * s), fill=col, width=int(6 * s))

def _zebra(d, x, y, s, col):
    d.ellipse((x - 50 * s, y - 30 * s, x + 45 * s, y + 8 * s), fill=col)
    d.polygon([(x + 30 * s, y - 20 * s), (x + 60 * s, y - 80 * s), (x + 80 * s, y - 70 * s), (x + 48 * s, y - 10 * s)], fill=col)
    for lx in (-40, -25, 22, 35):
        d.rectangle((x + lx * s, y, x + (lx + 7) * s, y + 55 * s), fill=col)

def sh_savanna(t, s0, s1, bright_to=0.0):
    k = seg(t, s0, s1)
    m_ = lerp(1.0, bright_to, ease(k))
    sky = night_sky(m_)
    if m_ > 0.05: sky = moon_full(sky, 1500, 210, 46, halo=0.6 * m_, gain=m_)
    img = finish(sky, 0.3); d = ImageDraw.Draw(img, "RGBA")
    g = int(lerp(8, 26, m_))
    d.rectangle((0, 820, W, H), fill=(g, g + 2, g + 6))
    for j in range(6):
        _zebra(d, 1050 + j * 120 + 20 * math.sin(t + j) + (t - s0) * 18, 800 + (j % 2) * 18, 0.9, (g + 4, g + 6, g + 10))
    _cat(d, 420 + (t - s0) * 25, 830, 1.1, (g + 2, g + 3, g + 6))
    d.text((420, 960), "predator", font=font(F_MED, 24), fill=(255, 180, 150, int(200 * m_ + 55)), anchor="mm")
    d.text((1300, 960), "prey", font=font(F_MED, 24), fill=(180, 220, 255, int(200 * m_ + 55)), anchor="mm")
    label(d, 120, 160, "BRIGHT NIGHT vs DARK NIGHT", "behaviour shifts with moonlight", WHITE, int(255 * seg(t, s0 + 0.3, s0 + 0.9)), size=36)
    tag(d, "illus")
    return img

def sh_turtles(t, s0, s1):
    sky = night_sky(0.6)
    img = finish(sky, 0.2); d = ImageDraw.Draw(img, "RGBA")
    d.rectangle((0, 520, W, 640), fill=(40, 60, 90))
    for i in range(10):
        y = 540 + i * 10
        d.line([(x, y + 3 * math.sin(x * 0.02 + t * 2 + i)) for x in range(0, W, 30)], fill=(150, 180, 210, 80), width=2)
    d.rectangle((0, 640, W, H), fill=(58, 52, 44))
    rng = np.random.default_rng(13)
    for i in range(26):
        x = rng.uniform(100, W - 100); y0 = rng.uniform(820, 1050); v = rng.uniform(20, 40)
        y = max(650, y0 - (t - s0) * v)
        ang = -math.pi / 2 + rng.uniform(-0.3, 0.3)
        d.ellipse((x - 9, y - 12, x + 9, y + 12), fill=(18, 16, 14))
        f = math.sin((t - s0) * 8 + i) * 6
        d.line((x - 8, y - 4, x - 18, y - 4 + f), fill=(18, 16, 14), width=4); d.line((x + 8, y - 4, x + 18, y - 4 - f), fill=(18, 16, 14), width=4)
    arrow(d, 960, 900, 960, 680, (255, 220, 150, 200), 4, 18)
    label(d, 120, 160, "SEA TURTLE HATCHLINGS", "head for the brighter, open horizon over the sea", WHITE, int(255 * seg(t, s0 + 0.2, s0 + 0.8)), size=40)
    tag(d, "illus")
    return img

def sh_cards(t, s0, s1, title, items, kind="diag", bg="stars"):
    base = stars_half_up() * 0.75 if bg == "stars" else globe(1500, 560, 380, lon=-30 - 4 * (t - s0)) * 0.55
    img = finish(base, 0.15); d = ImageDraw.Draw(img, "RGBA")
    headline(d, 160, 200, title, seg(t, s0, s0 + 0.5), 44, GOLD)
    for i, (txt, cue, col) in enumerate(items):
        tw = (find(*cue) - 0.25) if cue else s0 + 0.5 + i * 0.4
        factcard(d, 160, 300 + i * 135, txt[0], txt[1], seg(t, tw, tw + 0.45), col, 980)
    tag(d, kind)
    return img

def sh_popgraph(t, s0, s1):
    img = finish(stars_half_up() * 0.6, 0.1); d = ImageDraw.Draw(img, "RGBA")
    gx, gy, gw, gh = 200, 260, 1400, 560
    d.line((gx, gy + gh, gx + gw, gy + gh), fill=(255, 255, 255, 150), width=2); d.line((gx, gy, gx, gy + gh), fill=(255, 255, 255, 150), width=2)
    d.text((gx + gw, gy + gh + 30), "generations →", font=font(F_LIGHT, 26), fill=SOFT, anchor="rm")
    d.text((gx - 20, gy - 20), "population (illustrative)", font=font(F_LIGHT, 24), fill=SOFT, anchor="lm")
    k = seg(t, s0 + 0.3, s1 - 0.3)
    curves = [((130, 230, 170), 0.12, "adapts"), ((255, 205, 110), 0.0, "holds steady"), ((255, 130, 110), -0.35, "declines")]
    for col, slope, name in curves:
        pts = []
        for i in range(int(200 * k) + 1):
            x = i / 200
            y = 0.5 + (slope * max(0, x - 0.15) * 1.4 if x > 0.15 else 0) + 0.02 * math.sin(x * 40 + slope * 10)
            pts.append((gx + x * gw, gy + gh * (1 - y)))
        if len(pts) > 1:
            d.line(pts, fill=col, width=4)
            d.text((pts[-1][0] + 14, pts[-1][1]), name, font=font(F_MED, 26), fill=col, anchor="lm")
    d.line((gx + 0.15 * gw, gy, gx + 0.15 * gw, gy + gh), fill=(255, 255, 255, 80), width=2)
    d.text((gx + 0.15 * gw + 10, gy + 10), "Moon disappears", font=font(F_MONO, 18), fill=SOFT, anchor="lt")
    tag(d, "illus", "not a forecast")
    return img

def sh_foodweb(t, s0, s1):
    img = finish(stars_half_up() * 0.6, 0.1); d = ImageDraw.Draw(img, "RGBA")
    rng = np.random.default_rng(31)
    nodes = [(rng.uniform(300, 1620), rng.uniform(220, 880)) for _ in range(22)]
    edges = [(i, j) for i in range(22) for j in range(i + 1, 22) if math.dist(nodes[i], nodes[j]) < 330 and rng.random() < 0.6]
    src = 5; q = (t - s0) * 260
    for i, j in edges:
        d.line((*nodes[i], *nodes[j]), fill=(150, 190, 220, 90), width=2)
    for i, (x, y) in enumerate(nodes):
        dist = math.dist(nodes[i], nodes[src])
        hit = clamp(1 - abs(q - dist) / 120, 0, 1)
        r = 12 + 10 * hit
        d.ellipse((x - r, y - r, x + r, y + r), fill=(int(lerp(150, 255, hit)), int(lerp(200, 170, hit)), int(lerp(230, 110, hit)), 230))
    rr = q
    d.ellipse((nodes[src][0] - rr, nodes[src][1] - rr, nodes[src][0] + rr, nodes[src][1] + rr), outline=(255, 190, 120, int(140 * clamp(1 - q / 1400, 0, 1))), width=3)
    label(d, 120, 140, "FOOD WEB", "a change in one species ripples outward", WHITE, int(255 * seg(t, s0 + 0.3, s0 + 0.9)), size=40)
    tag(d, "illus")
    return img

# ================================================================== CHAPTER 5: rotation
def sh_sunorbit(t, s0, s1):
    arr = stars_half_up() * 0.7
    arr = star.draw_sun(arr.copy(), 960, 560, 80, t, bright=0.9, corona=1.0)
    img = finish(arr, 0.5); d = ImageDraw.Draw(img, "RGBA")
    dashed_circle(d, 960, 560, 620, 330, (220, 225, 240, 110), 2, 4, 2)
    a = (t - s0) * 0.25 + 0.3
    ex, ey = 960 + 620 * math.cos(a), 560 + 330 * math.sin(a)
    e = earth.render(120, 120, 60, 60, 34, 15, -40, -40, sun=(-(ex - 960) / 700, (ey - 560) / 700, 0.5), stars=None)
    ei = to_img(tone(e)); img.paste(ei, (int(ex - 60), int(ey - 60)), Image.fromarray(np.clip(e.sum(-1) * 3, 0, 255).astype(np.uint8)))
    d = ImageDraw.Draw(img, "RGBA")
    label(d, ex + 46, ey, "Earth", None, WHITE, 230, size=26)
    headline(d, 120, 140, "Earth keeps orbiting the Sun", seg(t, s0 + 0.2, s0 + 0.8), 44, WHITE)
    tag(d, "diag", "not to scale")
    return img

def sh_daychart(t, s0, s1, nomoon_from=None):
    img = finish(stars_half_up() * 0.55, 0.1); d = ImageDraw.Draw(img, "RGBA")
    gx, gy, gw, gh = 220, 250, 1300, 560
    d.line((gx, gy + gh, gx + gw, gy + gh), fill=(255, 255, 255, 150), width=2); d.line((gx, gy, gx, gy + gh), fill=(255, 255, 255, 150), width=2)
    X = lambda mya: gx + (1 - mya / 650) * gw
    Y = lambda h: gy + gh - (h - 20) / 5 * gh
    for h in (21, 22, 23, 24, 25):
        d.text((gx - 16, Y(h)), f"{h} h", font=font(F_LIGHT, 22), fill=SOFT, anchor="rm")
        d.line((gx, Y(h), gx + gw, Y(h)), fill=(255, 255, 255, 25), width=1)
    for mya in (600, 400, 200, 0):
        d.text((X(mya), gy + gh + 30), "today" if mya == 0 else f"{mya} Myr ago", font=font(F_LIGHT, 22), fill=SOFT, anchor="mm")
    pts = [(620, 21.9), (400, 22.0), (0, 24.0)]
    k = ease(seg(t, s0 + 0.3, s0 + 2.0))
    line = [(X(m), Y(h)) for m, h in pts]
    n = max(2, int(len(line) * 1))
    d.line([(lerp(line[0][0], p[0], 1), lerp(line[0][1], p[1], 1)) for p in line][:2 + int(k)], fill=GOLD, width=4)
    for (m, h), (x, y) in zip(pts, line):
        d.ellipse((x - 9, y - 9, x + 9, y + 9), fill=GOLD)
    d.text((X(620), Y(21.9) + 34), "~21.9 h  (tidal rhythmites, ~620 Myr)", font=font(F_MED, 22), fill=WHITE, anchor="lm")
    d.text((X(400), Y(22.0) - 34), "~22 h  (Devonian corals: ~400 days/yr)", font=font(F_MED, 22), fill=WHITE, anchor="lm")
    d.text((X(0) - 10, Y(24) - 30), "24 h", font=font(F_SEMI, 30), fill=GOLD, anchor="rm")
    headline(d, 220, 150, "Earth's day has been getting longer", seg(t, s0, s0 + 0.5), 42, WHITE, sub="approximate values from the geological record")
    if nomoon_from is not None and t >= nomoon_from:
        a = seg(t, nomoon_from, nomoon_from + 0.8)
        fx = [(X(0) + i * 12, Y(24) - i * 0.6) for i in range(20)]
        d.line([(X(0), Y(24)), (gx + gw + 230 * a, Y(24) - 18 * a)], fill=(130, 230, 255), width=4)
        d.line([(X(0), Y(24)), (gx + gw + 230 * a, Y(24) - 120 * a)], fill=(255, 205, 110, 200), width=3)
        d.text((gx + gw + 240, Y(24) - 18 - 30), "without the Moon: slower change", font=font(F_MED, 20), fill=(130, 230, 255, int(255 * a)), anchor="rm")
        d.text((gx + gw + 240, Y(24) - 150), "with the Moon", font=font(F_MED, 20), fill=(255, 205, 110, int(255 * a)), anchor="rm")
    tag(d, "diag", "future branch is qualitative")
    return img

# ================================================================== CHAPTER 6: axis
def tilted_globe(t, cx, cy, R, tilt_deg, lon, ice=0.0, zones=None):
    e = earth.render(int(R * 2.4), int(R * 2.4), R * 1.2, R * 1.2, R, 0, lon, lon - 2 * t, sun=(-0.6, 0.2, 0.77), stars=None)
    if ice != 0.0:
        hh = e.shape[0]; yy = (np.arange(hh)[:, None] - R * 1.2) / R
        lat = np.degrees(np.arcsin(np.clip(-yy, -1, 1)))
        cap = 70 - 25 * ice
        xx_ = (np.arange(hh)[None, :] - R * 1.2) / R
        m = (np.abs(lat) > cap) & (xx_ ** 2 + yy ** 2 < 0.985)
        e = np.where(m[..., None], e * 0.3 + np.array([225, 235, 245], np.float32) * 0.7, e)
    img = to_img(tone(e))
    mask = Image.fromarray(np.clip(e.sum(-1) * 4, 0, 255).astype(np.uint8))
    img = img.rotate(tilt_deg, resample=Image.BICUBIC); mask = mask.rotate(tilt_deg, resample=Image.BICUBIC)
    return img, mask

def sh_axis(t, s0, s1, tilt=23.4, wobble=None, ice=None, title=None, upright_note=False):
    k = seg(t, s0, s1)
    td = tilt
    if wobble is not None:                                    # hypothetical: tilt drifting over (labelled) geological time
        td = 23.4 + wobble * math.sin((t - s0) * 0.9) * (0.5 + 0.5 * math.sin((t - s0) * 0.37 + 1))
    ic = 0.0 if ice is None else ice * math.sin((t - s0) * 0.8)
    base = finish(stars_half_up() * 0.7, 0.1)
    R = 300
    g, m = tilted_globe(t, 960, 560, R, -td, -30 - 10 * (t - s0), ice=ic)
    base.paste(g, (int(960 - g.width / 2), int(560 - g.height / 2)), m)
    d = ImageDraw.Draw(base, "RGBA")
    d.line((480, 560, 1440, 560), fill=(255, 255, 255, 70), width=2)
    d.text((1450, 560), "orbital plane", font=font(F_LIGHT, 22), fill=SOFT, anchor="lm")
    a = math.radians(td)
    ax, ay = math.sin(a), -math.cos(a)
    d.line((960 - ax * (R + 120), 560 - ay * (R + 120), 960 + ax * (R + 120), 560 + ay * (R + 120)), fill=GOLD + (230,), width=4)
    d.line((960, 560 - R - 120, 960, 560 + R + 120), fill=(255, 255, 255, 60), width=2)
    d.arc((960 - 200, 560 - 200, 960 + 200, 560 + 200), -90, -90 + td, fill=GOLD, width=4)
    d.text((960 + 70 + td * 2, 560 - 230), f"{td:.1f}°", font=font(F_SEMI, 40), fill=GOLD, anchor="lm")
    if title: headline(d, 120, 160, title[0], seg(t, s0 + 0.2, s0 + 0.8), 44, title[1], sub=title[2] if len(title) > 2 else None)
    tag(d, "hyp" if wobble or ice else "diag", "timescale: many thousands to millions of years" if wobble or ice else "")
    return base

def sh_seasons(t, s0, s1):
    arr = stars_half_up() * 0.6
    arr = star.draw_sun(arr.copy(), 960, 540, 70, t, bright=0.9, corona=1.0)
    img = finish(arr, 0.5); d = ImageDraw.Draw(img, "RGBA")
    dashed_circle(d, 960, 540, 640, 300, (220, 225, 240, 100), 2, 4, 2)
    pos = {"summer": (0.0, "JUNE · SUMMER (north)"), "winter": (math.pi, "DECEMBER · WINTER (north)"),
           "spring": (math.pi / 2, "MARCH · SPRING (north)"), "autumn": (-math.pi / 2, "SEPTEMBER · AUTUMN (north)")}
    cur = None
    for i, w in zip(range(92, 96), ("summer", "winter", "spring", "autumn")):
        if t >= ls(i) - 0.2: cur = w
    for w, (ang, txt) in pos.items():
        ex, ey = 960 - 640 * math.cos(ang), 540 + 300 * math.sin(ang)
        on = (w == cur)
        e = earth.render(150, 150, 75, 75, 46 if on else 32, 0, -30 - 20 * t, -30, sun=((960 - ex) / 700, (ey - 540) / -700, 0.4), stars=None)
        ei = to_img(tone(e)); mk = Image.fromarray(np.clip(e.sum(-1) * 3, 0, 255).astype(np.uint8))
        ei = ei.rotate(-23.4, resample=Image.BICUBIC); mk = mk.rotate(-23.4, resample=Image.BICUBIC)
        img.paste(ei, (int(ex - 75), int(ey - 75)), mk)
        d = ImageDraw.Draw(img, "RGBA")
        a = math.radians(23.4)
        d.line((ex - math.sin(a) * 70, ey + math.cos(a) * 70, ex + math.sin(a) * 70, ey - math.cos(a) * 70), fill=GOLD + (200 if on else 90,), width=3)
        d.text((ex, ey + 92), txt, font=font(F_SEMI if on else F_LIGHT, 26 if on else 20), fill=(255, 255, 255, 255 if on else 120), anchor="mm")
    headline(d, 960, 90, "The tilt makes the seasons", seg(t, s0, s0 + 0.6), 40, WHITE, "mm")
    tag(d, "diag", "not to scale")
    return img

def _obl_chart(d, t, s0, show_nomoon, gx=200, gy=240, gw=1500, gh=560):
    d.line((gx, gy + gh, gx + gw, gy + gh), fill=(255, 255, 255, 150), width=2); d.line((gx, gy, gx, gy + gh), fill=(255, 255, 255, 150), width=2)
    Y = lambda deg: gy + gh - deg / 90 * gh
    for deg in (0, 23.4, 45, 90):
        d.text((gx - 14, Y(deg)), f"{deg:g}°", font=font(F_LIGHT, 22), fill=SOFT, anchor="rm")
        d.line((gx, Y(deg), gx + gw, Y(deg)), fill=(255, 255, 255, 25), width=1)
    k = seg(t, s0 + 0.3, s0 + 2.5)
    pts = [(gx + x * gw, Y(23.3 + 1.2 * math.sin(x * 2 * math.pi * 6))) for x in np.linspace(0, k, 200)]
    if len(pts) > 1: d.line(pts, fill=GOLD, width=3)
    d.text((gx + gw, Y(24.5) - 26), "with the Moon: ~22.1°–24.5° (≈41,000-year cycle)", font=font(F_MED, 22), fill=GOLD, anchor="rm")
    if show_nomoon is not None and t >= show_nomoon:
        q = seg(t, show_nomoon, show_nomoon + 2.0)
        rng = np.random.default_rng(4); y = 23.4; pts2 = []
        for x in np.linspace(0, q, 220):
            y = clamp(y + rng.normal(0, 4.5), 2, 80); pts2.append((gx + x * gw, Y(y)))
        if len(pts2) > 1: d.line(pts2, fill=(255, 130, 110), width=3)
        d.text((gx + 20, gy + 20), "without the Moon, SOME models: large chaotic swings (Laskar et al. 1993: 0°–85°)",
               font=font(F_MED, 22), fill=(255, 150, 130), anchor="lt")
        d.text((gx + 20, gy + 54), "other models: much more limited variation (e.g. Lissauer et al. 2012)", font=font(F_MED, 22), fill=(130, 230, 255), anchor="lt")
    d.text((gx + gw, gy + gh + 30), "time → (many millions of years)", font=font(F_LIGHT, 22), fill=SOFT, anchor="rm")

def sh_obliquity(t, s0, s1, nomoon_at=None):
    img = finish(stars_half_up() * 0.5, 0.1); d = ImageDraw.Draw(img, "RGBA")
    headline(d, 200, 150, "EARTH'S AXIAL TILT OVER TIME", seg(t, s0, s0 + 0.5), 36, TEAL)
    _obl_chart(d, t, s0, nomoon_at)
    tag(d, "hyp" if nomoon_at else "diag", "red curve is illustrative, not a prediction")
    return img

INSOL = None
def insolation_table():
    global INSOL
    if INSOL is None:
        lat = np.radians(np.linspace(-89.5, 89.5, 180)); lam = np.linspace(0, 2 * np.pi, 120, endpoint=False)
        tab = []
        for eps in range(0, 91):
            dec = np.arcsin(np.sin(np.radians(eps)) * np.sin(lam))[None, :]
            ph = lat[:, None]
            c = np.clip(-np.tan(ph) * np.tan(dec), -1, 1); h0 = np.arccos(c)
            Q = 1361 / np.pi * (h0 * np.sin(ph) * np.sin(dec) + np.cos(ph) * np.cos(dec) * np.sin(h0))
            tab.append(Q.mean(1))
        INSOL = np.array(tab)
    return INSOL

def sh_insol(t, s0, s1):
    img = finish(stars_half_up() * 0.5, 0.1); d = ImageDraw.Draw(img, "RGBA")
    eps = 23.4 + 36.6 * (0.5 - 0.5 * math.cos((t - s0) * 0.7))
    tab = insolation_table()
    gx, gy, gw, gh = 760, 230, 1000, 600
    d.line((gx, gy + gh, gx + gw, gy + gh), fill=(255, 255, 255, 150), width=2); d.line((gx, gy, gx, gy + gh), fill=(255, 255, 255, 150), width=2)
    for lat in (-90, -45, 0, 45, 90):
        d.text((gx + (lat + 90) / 180 * gw, gy + gh + 28), f"{lat}°", font=font(F_LIGHT, 22), fill=SOFT, anchor="mm")
    d.text((gx + gw / 2, gy + gh + 64), "latitude", font=font(F_LIGHT, 22), fill=SOFT, anchor="mm")
    d.text((gx - 14, gy - 20), "yearly-average sunlight (W/m²)", font=font(F_LIGHT, 22), fill=SOFT, anchor="lm")
    def curve(e_, col, w_):
        q = tab[int(round(e_))]
        pts = [(gx + i / 179 * gw, gy + gh - q[i] / 450 * gh) for i in range(180)]
        d.line(pts, fill=col, width=w_)
    curve(23.4, GOLD + (220,), 3)
    curve(eps, (255, 130, 110), 4)
    d.text((gx + gw, gy + 10), "today (23.4°)", font=font(F_MED, 22), fill=GOLD, anchor="rt")
    d.text((gx + gw, gy + 42), f"hypothetical tilt {eps:.0f}°", font=font(F_MED, 22), fill=(255, 150, 130), anchor="rt")
    g, m = tilted_globe(t, 380, 540, 230, -eps, -30 - 10 * (t - s0))
    img.paste(g, (int(380 - g.width / 2), int(540 - g.height / 2)), m)
    d = ImageDraw.Draw(img, "RGBA")
    d.text((380, 860), f"axis tilt {eps:.0f}°", font=font(F_SEMI, 32), fill=(255, 150, 130), anchor="mm")
    headline(d, 120, 120, "Where the sunlight lands", seg(t, s0, s0 + 0.6), 40, WHITE, sub="computed from orbital geometry")
    tag(d, "hyp", "physics-based sunlight calculation")
    return img

def sh_system(t, s0, s1, upright=False):
    img = finish(stars_half_up() * 0.6, 0.1); d = ImageDraw.Draw(img, "RGBA")
    arr = np.asarray(img, np.float32)
    arr = star.draw_sun(arr.copy(), 260, 540, 90, t, bright=0.9, corona=0.9)
    img = finish(arr, 0.4); d = ImageDraw.Draw(img, "RGBA")
    e = earth.render(220, 220, 110, 110, 70, 10, -40 - 8 * t, -40, sun=(-1, 0, 0.3), stars=None)
    img.paste(to_img(tone(e)), (960 - 110, 540 - 110), Image.fromarray(np.clip(e.sum(-1) * 3, 0, 255).astype(np.uint8)))
    m = moonr.render(80, 80, 40, 40, 20, light=(-1, 0, 0.3))
    ma = (t - s0) * 0.6
    mx, my = 960 + 200 * math.cos(ma), 540 + 70 * math.sin(ma)
    img.paste(to_img(tone(m)), (int(mx - 40), int(my - 40)), Image.fromarray(np.clip(m.sum(-1) * 3, 0, 255).astype(np.uint8)))
    d = ImageDraw.Draw(img, "RGBA")
    d.ellipse((1640 - 44, 540 - 44, 1640 + 44, 540 + 44), fill=(200, 160, 120))
    for yy in range(-30, 40, 14): d.line((1640 - 40, 540 + yy, 1640 + 40, 540 + yy), fill=(170, 120, 90), width=5)
    d.text((1640, 620), "Jupiter", font=font(F_MED, 24), fill=SOFT, anchor="mm")
    for a_, b_ in (((350, 540), (870, 540)), ((1590, 540), (1050, 540)), ((mx, my - 30), (960, 450))):
        arrow(d, *a_, *b_, (130, 230, 255, 160), 3, 14)
    headline(d, 960, 150, "A complicated gravitational system", seg(t, s0, s0 + 0.6), 40, WHITE, "mm",
             sub="Sun, Moon and planets all tug on Earth's spin axis")
    tag(d, "real", "not to scale")
    return img

# ================================================================== CHAPTER 7: eclipses
def sh_lunar_eclipse(t, s0, s1):
    k = seg(t, s0, s1)
    arr = stars_half_up() * 0.8
    shadow = ease(seg(t, s0 + 0.3, s0 + 2.5))
    tint = (lerp(1.0, 0.95, shadow), lerp(0.98, 0.35, shadow), lerp(0.94, 0.2, shadow))
    arr = moonr.render(W, H, 960, 540, 300, light=(-0.05, 0, 1), base=arr, gain=lerp(1.0, 0.28, shadow), tint=tint, halo=0.15)
    img = finish(arr, 0.3); d = ImageDraw.Draw(img, "RGBA")
    headline(d, 120, 160, "TOTAL LUNAR ECLIPSE", seg(t, s0, s0 + 0.5), 40, (255, 160, 130), sub="Earth's shadow turns the Moon copper-red")
    tag(d, "sim")
    return img

def sh_solar_eclipse(t, s0, s1, sizes=False, total_at=None):
    k = seg(t, s0, s1)
    cx, cy, R = 960, 540, 200
    tt = (t - s0)
    if total_at is None: total_at = s0 + 2.0
    off = clamp((total_at - t) * 140, -10000, 10000) if t < total_at else max(-40, -(t - total_at) * 6)
    totality = abs(off) < 30
    corona = 1.0 + (3.2 if totality else 0.0) * clamp(1 - abs(off) / 30, 0, 1)
    arr = stars_half_up() * (0.5 if totality else 0.2)
    arr = star.draw_sun(arr.copy(), cx, cy, R, t, bright=1.0, corona=corona * (1.6 if totality else 1.0))
    arr = bloom(arr, 0.5)
    img = to_img(tone(arr)); d = ImageDraw.Draw(img, "RGBA")
    d.ellipse((cx - R * 1.01 + off, cy - R * 1.01, cx + R * 1.01 + off, cy + R * 1.01), fill=(2, 2, 4))
    if totality:
        dr = clamp(1 - abs(off + 22) / 12, 0, 1)                         # diamond ring as the Moon begins to leave
        if dr > 0:
            x = cx + R + off - 4
            d.ellipse((x - 16, cy - 16, x + 16, cy + 16), fill=(255, 250, 240, int(255 * dr)))
    if sizes:
        a = seg(t, s0 + 0.4, s0 + 1.0)
        factcard(d, 100, 700, "Sun ≈ 400× wider", "1.39 million km across", a, GOLD, 520)
        factcard(d, 1300, 700, "…and ≈ 400× farther", "150 million km vs 384,400 km", seg(t, s0 + 1.4, s0 + 2.0), ICE, 520)
    headline(d, 120, 140, "TOTAL SOLAR ECLIPSE", seg(t, s0, s0 + 0.5), 40, WHITE, sub="the corona appears only in totality")
    tag(d, "sim")
    return img

def sh_transit(t, s0, s1):
    arr = stars_half_up() * 0.2
    arr = star.draw_sun(arr.copy(), 960, 540, 330, t, bright=0.85, corona=0.6)
    img = finish(arr, 0.4); d = ImageDraw.Draw(img, "RGBA")
    k = seg(t, s0, s1)
    x = lerp(700, 1220, k); y = 470 + 40 * k
    d.ellipse((x - 11, y - 11, x + 11, y + 11), fill=(5, 5, 8))
    d.text((x, y - 30), "Venus", font=font(F_MED, 24), fill=WHITE, anchor="mb")
    headline(d, 120, 140, "Planetary transits would remain", seg(t, s0, s0 + 0.5), 40, WHITE, sub="a tiny dot, not an eclipse")
    tag(d, "sim")
    return img

def lunar_ground():
    def make():
        rng = np.random.default_rng(3)
        x = np.arange(W)
        prof = 760 + 40 * ndimage.gaussian_filter1d(rng.normal(0, 1, W), 140) * 8 + 10 * ndimage.gaussian_filter1d(rng.normal(0, 1, W), 15) * 4
        yy = np.arange(H)[:, None]
        n = ndimage.gaussian_filter(rng.normal(0, 1, (H // 2, W // 2)), 2)
        n = np.asarray(Image.fromarray(((n / n.std() * 0.2 + 0.5).clip(0, 1) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32) / 255
        depth = np.clip((yy - prof[None, :]) / 320, 0, 1)
        g = (110 + 90 * n) * (0.55 + 0.45 * depth)
        mask = yy >= prof[None, :]
        return np.where(mask[..., None], np.repeat(g[..., None], 3, -1) * np.array([1.0, 0.98, 0.95]), -1.0)
    return cache("lground", make)

def sh_lunar_surface(t, s0, s1, earth_rise=(0.0, 0.0), footprint=False, text=None):
    k = seg(t, s0, s1)
    arr = stars_half_up() * 0.5
    ey = lerp(900, 420, ease(lerp(earth_rise[0], earth_rise[1], k)))
    arr = globe(1250, ey, 150, lat0=20, lon=-60 - 2 * (t - s0), sun=(-0.9, 0.1, 0.4), base=stars_half() * 0.5)
    g = lunar_ground()
    arr = np.where(g >= 0, g, arr)
    img = finish(arr, 0.3); d = ImageDraw.Draw(img, "RGBA")
    if footprint:
        for j in range(5):
            x = 520 + j * 90; y = 960 - j * 20
            d.rounded_rectangle((x - 18, y - 34, x + 18, y + 34), 16, fill=(70, 68, 64))
            for r_ in range(4): d.line((x - 14, y - 26 + r_ * 16, x + 14, y - 26 + r_ * 16), fill=(55, 53, 50), width=4)
    if text:
        headline(d, 120, 150, text[0], seg(t, s0 + 0.2, s0 + 0.8), 44, WHITE, sub=text[1])
    tag(d, "illus")
    return img

# ================================================================== CHAPTER 8: weather / oceans
def sh_weather(t, s0, s1, big_no=None):
    k = ease(seg(t, s0, s1))
    lon = -40 - 3 * (t - s0)
    arr = globe(960, 560, 400 * lerp(1.0, 1.06, k), lat0=20, lon=lon, lon_cloud=lon - 9 * (t - s0), sun=(-0.5, 0.3, 0.8))
    img = finish(arr, 0.3); d = ImageDraw.Draw(img, "RGBA")
    if big_no is not None and t >= big_no:
        headline(d, 220, 200, "NO.", seg(t, big_no, big_no + 0.3), 120, GOLD, "mm")
    tag(d, "sim")
    return img

def sh_mixing(t, s0, s1):
    img = Image.new("RGB", (W, H)); d = ImageDraw.Draw(img, "RGBA")
    for y in range(0, H, 4):
        q = y / H
        d.rectangle((0, y, W, y + 4), fill=(int(lerp(30, 3, q)), int(lerp(90, 10, q)), int(lerp(150, 30, q))))
    d.rectangle((0, 0, W, 120), fill=(10, 18, 34))
    rng = np.random.default_rng(6)
    floor = [(x, 1000 - 120 * math.exp(-((x - 1200) / 160) ** 2) - 40 * math.sin(x * 0.01)) for x in range(0, W + 20, 20)]
    d.polygon([(0, H)] + floor + [(W, H)], fill=(40, 34, 30))
    for i in range(9):
        y0 = 300 + i * 70
        amp = 18 + 22 * math.exp(-((i - 6) / 2) ** 2)
        pts = [(x, y0 + amp * math.sin(x * 0.006 - (t - s0) * 1.4 + i * 0.6) * (0.5 + 0.5 * math.exp(-((x - 1200) / 400) ** 2))) for x in range(0, W + 20, 20)]
        d.line(pts, fill=(140, 200, 255, 90), width=2)
    for j in range(16):
        x = 1050 + rng.uniform(-260, 260); y = 760 + rng.uniform(-150, 120); ph = (t - s0) * 1.5 + j
        r = 20 + 8 * math.sin(ph)
        d.arc((x - r, y - r, x + r, y + r), int(ph * 60) % 360, int(ph * 60) % 360 + 260, fill=(255, 205, 140, 160), width=3)
    d.text((1200, 860), "tidal flow over ridges breaks into turbulence", font=font(F_MED, 24), fill=(255, 215, 160), anchor="mm")
    factcard(d, 100, 160, "≈ 3.7 TW", "total tidal energy dissipated in Earth's oceans", seg(t, s0 + 0.5, s0 + 1.0), GOLD, 640)
    factcard(d, 100, 300, "≈ 1 TW", "of it in the deep ocean, helping mix it (Egbert & Ray, 2000)", seg(t, s0 + 2.0, s0 + 2.5), ICE, 760)
    tag(d, "schem", "internal tides and deep mixing")
    return img

def sh_currents(t, s0, s1):
    def mp():
        a = np.asarray(Image.open("tex/earth_day_4096.jpg").convert("RGB").resize((W, H), Image.BILINEAR), np.float32)
        return a * 0.45
    img = to_img(cache("map", mp)); d = ImageDraw.Draw(img, "RGBA")
    def lonlat(lo, la): return ((lo + 180) / 360 * W, (90 - la) / 180 * H)
    warm = [(-80, 25), (-60, 38), (-35, 50), (-15, 60), (5, 68)]
    cold = [(-20, 62), (-35, 45), (-40, 10), (-30, -30), (0, -55), (60, -55), (110, -50), (150, -55), (-160, -58), (-100, -58), (-60, -58)]
    for path, col in ((warm, (255, 120, 90)), (cold, (110, 180, 255))):
        pts = [lonlat(*p) for p in path]
        d.line(pts, fill=col + (200,), width=6)
        ph = (t - s0) * 0.25
        for j in range(len(pts) - 1):
            q = (ph + j * 0.37) % 1
            x = lerp(pts[j][0], pts[j + 1][0], q); y = lerp(pts[j][1], pts[j + 1][1], q)
            d.ellipse((x - 7, y - 7, x + 7, y + 7), fill=WHITE)
    label(d, 120, 120, "GLOBAL OCEAN CIRCULATION", "warm surface flow  ·  cold deep return (schematic)", WHITE, int(255 * seg(t, s0, s0 + 0.6)), size=36)
    d.text((W - 40, H - 40), "Base map: Solar System Scope (CC BY 4.0), NASA-based", font=font(F_MONO, 16), fill=(200, 200, 200), anchor="rm")
    tag(d, "schem")
    return img

# ================================================================== CHAPTER 9-10
def sh_night_earth(t, s0, s1, checklist=None, title=None):
    k = ease(seg(t, s0, s1))
    lon = 60 - 4 * (t - s0)
    arr = globe(1240, 600, 430 * lerp(1.0, 1.06, k), lat0=25, lon=lon, sun=(0.75, 0.2, -0.6), night_gain=3.0, ambient=0.02)
    img = finish(arr, 0.35); d = ImageDraw.Draw(img, "RGBA")
    if title: headline(d, 120, 170, title[0], seg(t, title[1], title[1] + 0.5), 52, title[2] if len(title) > 2 else WHITE)
    if checklist:
        for i, (txt, cue) in enumerate(checklist):
            tw = find(*cue) - 0.2
            a = seg(t, tw, tw + 0.4)
            if a <= 0: continue
            y = 300 + i * 84
            d.ellipse((120, y - 16, 152, y + 16), outline=(130, 230, 170, int(255 * a)), width=3)
            d.line((128, y, 135, y + 8, 146, y - 8), fill=(130, 230, 170, int(255 * a)), width=4)
            d.text((175, y), txt, font=font(F_MED, 36), fill=(255, 255, 255, int(255 * a)), anchor="lm")
    tag(d, "sim")
    return img

def sh_recede(t, s0, s1, ruler=False, dino=False):
    img = finish(stars_half_up() * 0.6, 0.1); d = ImageDraw.Draw(img, "RGBA")
    e = earth.render(300, 300, 150, 150, 110, 15, -40 - 6 * t, -40, sun=(-0.6, 0.2, 0.77), stars=None)
    img.paste(to_img(tone(e)), (300 - 150, 540 - 150), Image.fromarray(np.clip(e.sum(-1) * 3, 0, 255).astype(np.uint8)))
    k = ease(seg(t, s0, s1))
    mx = lerp(1300, 1560, k)
    m = moonr.render(140, 140, 70, 70, 34, light=(-0.6, 0.1, 0.8))
    img.paste(to_img(tone(m)), (int(mx - 70), 540 - 70), Image.fromarray(np.clip(m.sum(-1) * 3, 0, 255).astype(np.uint8)))
    d = ImageDraw.Draw(img, "RGBA")
    dashed_circle(d, 1300, 540, 34, 34, (220, 225, 240, 120), 2, 10, 5)
    arrow(d, 1340, 640, mx + 40, 640, GOLD, 4, 16)
    d.text((300, 720), "Earth", font=font(F_MED, 26), fill=SOFT, anchor="mm")
    d.text((mx, 620), "Moon", font=font(F_MED, 26), fill=SOFT, anchor="mm")
    d.line((420, 540, mx - 40, 540), fill=(255, 255, 255, 50), width=2)
    d.text((860, 510), "≈ 384,400 km (average)", font=font(F_LIGHT, 26), fill=SOFT, anchor="mm")
    factcard(d, 120, 140, "+3.8 cm per year", "measured by laser ranging to Apollo-era reflectors", seg(t, find(162, "3.8") - 0.4, find(162, "3.8") + 0.1) if s0 <= ls(162) + 0.1 else 1.0, GOLD, 760)
    if ruler:
        a = seg(t, s0 + 0.2, s0 + 0.8)
        x0, y0 = 760, 760
        d.rectangle((x0, y0, x0 + 380 * a, y0 + 50), fill=(240, 220, 160, 230))
        for j in range(39):
            if j / 38 > a: break
            d.line((x0 + j * 10, y0, x0 + j * 10, y0 + (22 if j % 10 == 0 else 12)), fill=(40, 30, 20), width=2)
        d.text((x0 + 190, y0 + 90), "3.8 cm · about how fast fingernails grow in a year", font=font(F_MED, 26), fill=WHITE, anchor="mm")
    if dino:
        factcard(d, 1100, 740, "66 million years ago", "≈ 2,500 km closer at today's rate (the real rate has varied)", seg(t, s0 + 0.3, s0 + 0.9), (255, 190, 140), 700)
    tag(d, "real", "not to scale")
    return img

def sh_moon_tonight(t, s0, s1):
    k = seg(t, s0, s1)
    sky = night_sky(1.0)
    my = lerp(560, 300, ease(k))
    sky = moon_full(sky, 1240, my, 120, light=(-0.15, 0.05, 1.0), halo=0.7)
    arr = landscape(sky, 0.9, shift=0.3 * k)
    img = finish(arr, 0.4)
    tag(ImageDraw.Draw(img, "RGBA"), "illus", "the Moon, as it really is tonight")
    return img
