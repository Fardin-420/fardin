"""Procedural props library. Every prop is drawn at a ground point (x, y) with
scale s (1.0 = sized for a 300px character) and animated by time t.
Colours go through core.setc / lc so time-of-day lighting applies."""
import math
import cairo
from .core import setc, hexc, shade, hrand, noise1, fbm1, lerp, clamp, TAU, lc


def _ell(ctx, x, y, rx, ry):
    ctx.save(); ctx.translate(x, y); ctx.scale(max(rx, 0.01), max(ry, 0.01)); ctx.arc(0, 0, 1, 0, TAU); ctx.restore()


def _blob(ctx, x, y, r, seed, n=10, jag=0.25, sy=1.0):
    pts = []
    for i in range(n):
        a = i / n * TAU
        rr = r * (1 + (hrand(seed, i) - .5) * jag * 2)
        pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr * sy))
    ctx.move_to(*pts[0])
    for i in range(n):
        p0, p1 = pts[i], pts[(i + 1) % n]
        mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
        ctx.curve_to(p0[0], p0[1], p0[0], p0[1], mx, my)
    ctx.close_path()


# ------------------------------------------------------------------ fire
def flame(ctx, x, y, h, t, seed=0, alpha=1.0):
    """Layered animated flame with base at (x, y)."""
    cols = [("#ff5a1f", 1.0), ("#ff9d2e", 0.72), ("#ffe27a", 0.45)]
    for li, (c, k) in enumerate(cols):
        hh = h * k * (0.85 + 0.15 * noise1(t * 6 + li, seed + 7))
        w = h * 0.36 * k
        sway = noise1(t * 3.5 + li * .3, seed) * w * 0.5
        ctx.move_to(x - w, y)
        ctx.curve_to(x - w * 1.1, y - hh * .45, x - w * .2 + sway * .5, y - hh * .7, x + sway, y - hh)
        ctx.curve_to(x + w * .2 + sway * .5, y - hh * .7, x + w * 1.1, y - hh * .45, x + w, y)
        ctx.close_path()
        cc = hexc(c)
        ctx.set_source_rgba(cc[0], cc[1], cc[2], alpha)
        ctx.fill()
    # licks
    for i in range(3):
        ph = (t * 1.8 + hrand(seed, "lick", i)) % 1
        lx = x + (hrand(seed, "lx", i) - .5) * h * .5 + noise1(t * 4 + i, seed) * h * .1
        ly = y - h * (0.5 + ph * 0.7)
        r = h * 0.07 * (1 - ph)
        ctx.set_source_rgba(1, 0.7, 0.25, alpha * (1 - ph))
        _ell(ctx, lx, ly, r, r * 1.6)
        ctx.fill()


def campfire(ctx, x, y, s, t, seed=0, lit=True, size=1.0):
    S = 300 * s * size
    # stones
    for i in range(9):
        a = math.pi * (i / 8.0)
        sx = x + math.cos(a) * S * 0.2 * (1 if i % 2 else 0.98)
        sy = y + math.sin(a) * S * 0.03 - S * 0.005
        setc(ctx, lc(shade("#7b7469", -0.15 * (i % 3) / 2)))
        _ell(ctx, sx, sy, S * 0.045, S * 0.03)
        ctx.fill()
    # logs
    for i, a in enumerate((-0.35, 0.35, 0.0)):
        ctx.save(); ctx.translate(x, y - S * 0.03); ctx.rotate(a)
        ctx.rectangle(-S * 0.16, -S * 0.022, S * 0.32, S * 0.044)
        ctx.restore()
        setc(ctx, lc("#4a3020")); ctx.fill()
    # embers
    setc(ctx, (1, 0.35, 0.1, 0.9 if lit else 0.3))
    _ell(ctx, x, y - S * 0.03, S * 0.12, S * 0.025); ctx.fill()
    if lit:
        flame(ctx, x, y - S * 0.03, S * 0.42, t, seed)
        # sparks
        for i in range(10):
            ph = (t * 0.6 + hrand(seed, "spk", i)) % 1
            sx = x + (hrand(seed, "sx", i) - .5) * S * .25 + math.sin(t * 3 + i) * S * 0.04 * ph
            sy = y - S * 0.2 - ph * S * 0.9
            ctx.set_source_rgba(1, 0.75, 0.3, (1 - ph) * 0.9)
            ctx.arc(sx, sy, S * 0.006 * (1.5 - ph), 0, TAU); ctx.fill()


def smoke(ctx, x, y, s, t, seed=0, alpha=0.18):
    S = 300 * s
    for i in range(7):
        ph = (t * 0.12 + i / 7) % 1
        px = x + math.sin(ph * 5 + i) * S * 0.08 + ph * S * 0.25
        py = y - S * 0.4 - ph * S * 1.4
        r = S * (0.06 + ph * 0.22)
        ctx.set_source_rgba(0.75, 0.75, 0.78, alpha * math.sin(ph * math.pi))
        ctx.arc(px, py, r, 0, TAU); ctx.fill()


def fire_light(ctx, x, y, s, t, strength=1.0, seed=0, color=(1.0, 0.55, 0.2)):
    """Additive warm light pool (call after world, before Fardin)."""
    S = 300 * s
    fl = 0.85 + 0.15 * noise1(t * 7, seed + 3) + 0.05 * math.sin(t * 23)
    R = S * 2.6 * fl
    ctx.save()
    ctx.set_operator(cairo.OPERATOR_ADD)
    pat = cairo.RadialGradient(x, y - S * 0.2, 0, x, y - S * 0.2, R)
    pat.add_color_stop_rgba(0, *color, 0.55 * strength)
    pat.add_color_stop_rgba(0.35, *color, 0.22 * strength)
    pat.add_color_stop_rgba(1, *color, 0)
    ctx.set_source(pat)
    ctx.arc(x, y - S * 0.2, R, 0, TAU)
    ctx.fill()
    ctx.restore()


# ------------------------------------------------------------------ vegetation / rocks
def acacia(ctx, x, y, s, t, seed=0, col="#5d6b2e"):
    S = 300 * s
    wind = noise1(t * 0.5, seed) * S * 0.01
    trunk = lc("#4a3526")
    setc(ctx, trunk)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for k, (dx, ang) in enumerate(((0, 0), (-0.15, -0.5), (0.18, 0.45))):
        ctx.set_line_width(S * (0.05 if k == 0 else 0.03))
        ctx.move_to(x, y)
        bx = x + S * dx * 0.3
        ctx.curve_to(x + S * 0.02, y - S * 0.3, bx + S * dx, y - S * 0.6, x + S * dx * 2.2 + wind, y - S * 0.9)
        ctx.stroke()
    cx, cy = x + wind, y - S * 0.95
    setc(ctx, lc(shade(col, -0.3)))
    _ell(ctx, cx, cy + S * 0.04, S * 0.62, S * 0.1); ctx.fill()
    setc(ctx, lc(col))
    for i in range(6):
        ox = (i - 2.5) * S * 0.2 + (hrand(seed, i) - .5) * S * 0.1
        _ell(ctx, cx + ox, cy - S * 0.03 - hrand(seed, "y", i) * S * 0.06, S * 0.2, S * 0.08); ctx.fill()
    setc(ctx, lc(shade(col, 0.12)))
    for i in range(4):
        ox = (i - 1.5) * S * 0.22
        _ell(ctx, cx + ox, cy - S * 0.07, S * 0.13, S * 0.04); ctx.fill()


def bush(ctx, x, y, s, t, seed=0, col="#6b7a35"):
    S = 300 * s
    w = noise1(t * .7, seed) * S * 0.01
    for i, k in enumerate((-0.12, 0.0, 0.1)):
        setc(ctx, lc(shade(col, -0.15 + i * 0.1)))
        _ell(ctx, x + k * S + w, y - S * 0.07 - i * S * 0.015, S * 0.13, S * 0.09); ctx.fill()


def grass(ctx, x, y, s, t, seed=0, col="#b99a4a", n=7, h=0.12):
    S = 300 * s
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for i in range(n):
        bx = x + (i - n / 2) * S * 0.018
        hh = S * h * (0.6 + 0.6 * hrand(seed, i))
        sway = math.sin(t * 1.8 + bx * 0.01 + seed) * S * 0.02 + noise1(t * .6 + i, seed) * S * 0.015
        ctx.move_to(bx, y)
        ctx.curve_to(bx, y - hh * .5, bx + sway * .5, y - hh * .8, bx + sway + (hrand(seed, "l", i) - .5) * S * .04, y - hh)
        ctx.set_line_width(S * 0.008)
        setc(ctx, lc(shade(col, (hrand(seed, "c", i) - .5) * 0.3)))
        ctx.stroke()


def rock(ctx, x, y, s, t, seed=0, col="#8a7f6e", w=1.0, h=1.0):
    S = 300 * s
    W, H = S * 0.3 * w, S * 0.2 * h
    pts = [(x - W, y), (x - W * 0.85, y - H * 0.55), (x - W * 0.4, y - H * (0.95 + .1 * hrand(seed, 1))),
           (x + W * 0.2, y - H), (x + W * 0.75, y - H * 0.6), (x + W, y)]
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()
    setc(ctx, lc(col))
    ctx.fill()
    # light facet
    ctx.move_to(x - W * 0.85, y - H * 0.55); ctx.line_to(x - W * 0.4, y - H * (0.95 + .1 * hrand(seed, 1)))
    ctx.line_to(x + W * 0.2, y - H); ctx.line_to(x + W * 0.05, y - H * 0.6); ctx.line_to(x - W * 0.5, y - H * 0.45)
    ctx.close_path()
    setc(ctx, lc(shade(col, 0.15))); ctx.fill()
    ctx.move_to(x + W * 0.2, y - H); ctx.line_to(x + W * 0.75, y - H * 0.6); ctx.line_to(x + W, y); ctx.line_to(x + W * 0.3, y)
    ctx.line_to(x + W * 0.05, y - H * 0.6); ctx.close_path()
    setc(ctx, lc(shade(col, -0.2))); ctx.fill()


def boulder(ctx, x, y, s, t, seed=0, col="#7d7263"):
    rock(ctx, x, y, s, t, seed, col, w=1.6, h=2.4)


def cliff(ctx, x, y, s, t, seed=0, col="#8c6f55", w=1.0, cave=True):
    """Broad rocky outcrop with a cave mouth on its left side (Jebel Irhoud was a cave)."""
    S = 300 * s
    W = S * 3.2 * w
    H = S * 1.3
    prof = [(0, 0), (0.03, 0.5), (0.08, 0.85), (0.16, 1.0), (0.3, 0.93), (0.42, 0.98), (0.55, 0.86), (0.66, 0.72),
            (0.76, 0.52), (0.87, 0.28), (0.95, 0.1), (1, 0)]
    pts = [(x - W / 2 + u * W, y - H * h * (0.94 + 0.06 * hrand(seed, i))) for i, (u, h) in enumerate(prof)]
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()
    setc(ctx, lc(col)); ctx.fill()
    # sunlit top ledge
    ctx.move_to(*pts[1])
    for p in pts[2:8]:
        ctx.line_to(*p)
    for p in reversed(pts[2:8]):
        ctx.line_to(p[0], p[1] + S * 0.12)
    ctx.close_path()
    setc(ctx, lc(shade(col, 0.12))); ctx.fill()
    # cracks / strata
    for k in range(5):
        yy = y - H * (0.15 + k * 0.15)
        x0 = x - W * (0.42 - 0.04 * k)
        ctx.move_to(x0, yy)
        for i in range(1, 7):
            ctx.line_to(x0 + i * W * (0.12 - 0.012 * k), yy + (hrand(seed, k, i) - .5) * S * 0.06)
        ctx.set_line_width(S * 0.01)
        setc(ctx, lc(shade(col, -0.16))); ctx.stroke()
    # shadow side
    ctx.move_to(*pts[6])
    for p in pts[7:]:
        ctx.line_to(*p)
    ctx.line_to(pts[6][0] + S * 0.3, y)
    ctx.close_path()
    setc(ctx, lc(shade(col, -0.12), 0.8)); ctx.fill()
    if cave:
        cx = x - W * 0.28
        cw, ch = S * 0.55, S * 0.72
        ctx.move_to(cx - cw, y)
        ctx.curve_to(cx - cw * 1.05, y - ch * 1.25, cx + cw * 0.9, y - ch * 1.3, cx + cw, y)
        ctx.close_path()
        setc(ctx, lc("#3a2a1e")); ctx.fill()
        ctx.move_to(cx - cw * 0.72, y)
        ctx.curve_to(cx - cw * .75, y - ch * .85, cx + cw * .65, y - ch * .9, cx + cw * .72, y)
        ctx.close_path()
        setc(ctx, lc("#22170f")); ctx.fill()


def bones(ctx, x, y, s, t, seed=0):
    S = 300 * s
    for i in range(5):
        a = (hrand(seed, i) - .5) * 2.4
        bx = x + (i - 2) * S * 0.07
        L = S * (0.06 + 0.05 * hrand(seed, "l", i))
        ctx.save(); ctx.translate(bx, y - S * 0.01); ctx.rotate(a)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_width(S * 0.014)
        setc(ctx, lc("#e8e0c8")); ctx.move_to(-L, 0); ctx.line_to(L, 0); ctx.stroke()
        for e in (-L, L):
            ctx.arc(e, -S * .006, S * .01, 0, TAU); ctx.arc(e, S * .006, S * .01, 0, TAU); ctx.fill()
        ctx.restore()


def flakes(ctx, x, y, s, t, seed=0, n=8):
    S = 300 * s
    for i in range(n):
        fx = x + (hrand(seed, i) - .5) * S * 0.35
        fy = y - hrand(seed, "y", i) * S * 0.02
        r = S * (0.012 + 0.012 * hrand(seed, "r", i))
        a = hrand(seed, "a", i) * TAU
        ctx.move_to(fx + math.cos(a) * r, fy + math.sin(a) * r * .5)
        ctx.line_to(fx + math.cos(a + 2.2) * r, fy + math.sin(a + 2.2) * r * .5)
        ctx.line_to(fx + math.cos(a + 4.1) * r * .8, fy + math.sin(a + 4.1) * r * .5)
        ctx.close_path()
        setc(ctx, lc(shade("#9a9282", (hrand(seed, "c", i) - .5) * .4))); ctx.fill()


def grass_bed(ctx, x, y, s, t, seed=0, w=1.0):
    S = 300 * s
    W = S * 0.5 * w
    setc(ctx, lc("#5c5a52", 0.9))  # ash layer beneath
    _ell(ctx, x, y + S * 0.005, W * 1.05, S * 0.03); ctx.fill()
    setc(ctx, lc("#b09a55"))
    _ell(ctx, x, y - S * 0.012, W, S * 0.035); ctx.fill()
    ctx.set_line_width(S * 0.005)
    for i in range(26):
        gx = x + (hrand(seed, i) - .5) * W * 1.8
        a = (hrand(seed, "a", i) - .5) * 0.6
        L = S * 0.08
        ctx.move_to(gx - math.cos(a) * L, y - S * 0.015 + math.sin(a) * L * .2)
        ctx.line_to(gx + math.cos(a) * L, y - S * 0.025 - math.sin(a) * L * .2)
        setc(ctx, lc(shade("#c9b064", (hrand(seed, "c", i) - .5) * .4))); ctx.stroke()


def ochre(ctx, x, y, s, t, seed=0):
    S = 300 * s
    for i in range(3):
        setc(ctx, lc(shade("#a3402a", -0.1 * i)))
        _blob(ctx, x + i * S * 0.05, y - S * 0.02, S * 0.025, seed + i, 7, 0.3)
        ctx.fill()


def hide_rack(ctx, x, y, s, t, seed=0):
    S = 300 * s
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    setc(ctx, lc("#4f3a26")); ctx.set_line_width(S * 0.02)
    for dx in (-0.25, 0.25):
        ctx.move_to(x + dx * S, y); ctx.line_to(x + dx * S * .9, y - S * 0.55); ctx.stroke()
    ctx.move_to(x - S * .28, y - S * .5); ctx.line_to(x + S * .28, y - S * .5); ctx.stroke()
    w = math.sin(t * 1.3 + seed) * S * 0.01
    ctx.move_to(x - S * 0.2, y - S * 0.5)
    ctx.curve_to(x - S * .25 + w, y - S * .3, x - S * .15 + w, y - S * .15, x - S * .1 + w, y - S * .12)
    ctx.line_to(x + S * .12 + w, y - S * .14)
    ctx.curve_to(x + S * .2 + w, y - S * .2, x + S * .25, y - S * .35, x + S * .2, y - S * .5)
    ctx.close_path()
    setc(ctx, lc("#a57f55")); ctx.fill()


def termite_mound(ctx, x, y, s, t, seed=0):
    S = 300 * s
    ctx.move_to(x - S * 0.2, y)
    ctx.curve_to(x - S * 0.15, y - S * 0.4, x - S * 0.05, y - S * 0.75, x, y - S * 0.8)
    ctx.curve_to(x + S * 0.08, y - S * 0.6, x + S * 0.16, y - S * 0.3, x + S * 0.22, y)
    ctx.close_path()
    setc(ctx, lc("#a86f45")); ctx.fill()


def carcass(ctx, x, y, s, t, seed=0, butchered=0.0):
    """Gazelle carcass lying on its side; butchered 0..1 reveals red/bone."""
    S = 300 * s
    from .animals import draw_quadruped
    draw_quadruped(ctx, "gazelle", x, y, s * 0.9, 1, t, state="dead")
    if butchered > 0:
        ctx.set_source_rgba(*lc("#8e2a22")[:3], butchered)
        _ell(ctx, x - S * 0.02, y - S * 0.13, S * 0.13 * butchered + 1, S * 0.05); ctx.fill()
        ctx.set_source_rgba(*lc("#efe6cf")[:3], butchered)
        for i in range(4):
            _ell(ctx, x - S * 0.1 + i * S * 0.05, y - S * 0.15, S * 0.008, S * 0.035); ctx.fill()


# ------------------------------------------------------------------ modern room
def room(ctx, x, y, s, t, seed=0):
    S = 300 * s
    # window with night city
    wx, wy, ww, wh = x - S * 1.9, y - S * 1.55, S * 0.9, S * 0.75
    setc(ctx, "#1b2a4a"); ctx.rectangle(wx, wy, ww, wh); ctx.fill()
    for i in range(9):
        bx = wx + i * ww / 9
        bh = wh * (0.3 + 0.5 * hrand(seed, "b", i))
        setc(ctx, "#0f1830"); ctx.rectangle(bx, wy + wh - bh, ww / 9 - 4, bh); ctx.fill()
        for j in range(int(bh / 22)):
            if hrand(seed, i, j) > 0.55:
                ctx.set_source_rgba(1, 0.85, 0.45, 0.85); ctx.rectangle(bx + 6, wy + wh - bh + 8 + j * 22, 6, 8); ctx.fill()
    setc(ctx, "#f2efe8"); ctx.set_line_width(S * 0.03); ctx.rectangle(wx, wy, ww, wh); ctx.stroke()
    ctx.move_to(wx + ww / 2, wy); ctx.line_to(wx + ww / 2, wy + wh); ctx.stroke()
    # poster: timeline
    px, py = x + S * 0.9, y - S * 1.5
    setc(ctx, "#20324f"); ctx.rectangle(px, py, S * 0.55, S * 0.7); ctx.fill()
    setc(ctx, "#f4c95d"); ctx.arc(px + S * .27, py + S * .3, S * 0.13, 0, TAU); ctx.fill()
    setc(ctx, "#f2efe8"); ctx.rectangle(px + S * .07, py + S * .52, S * .41, S * .04); ctx.fill()
    # desk + laptop + lamp
    dx = x - S * 0.65
    setc(ctx, "#8a5a3b"); ctx.rectangle(dx - S * 0.55, y - S * 0.42, S * 1.1, S * 0.05); ctx.fill()
    for lx in (dx - S * .5, dx + S * .48):
        ctx.rectangle(lx, y - S * 0.38, S * 0.04, S * 0.38); ctx.fill()
    setc(ctx, "#2b2f38"); ctx.rectangle(dx - S * 0.2, y - S * 0.62, S * 0.34, S * 0.2); ctx.fill()
    ctx.set_source_rgba(0.45, 0.8, 1.0, 0.9 + 0.1 * math.sin(t * 3)); ctx.rectangle(dx - S * .18, y - S * .6, S * .3, S * .16); ctx.fill()
    setc(ctx, "#2b2f38"); ctx.rectangle(dx - S * 0.25, y - S * 0.44, S * 0.44, S * 0.025); ctx.fill()
    setc(ctx, "#444444"); ctx.set_line_width(S * 0.015)
    ctx.move_to(dx + S * .38, y - S * .42); ctx.line_to(dx + S * .38, y - S * .7); ctx.line_to(dx + S * .3, y - S * .78); ctx.stroke()
    pat = cairo.RadialGradient(dx + S * .28, y - S * .74, 0, dx + S * .28, y - S * .74, S * .6)
    pat.add_color_stop_rgba(0, 1, .85, .5, .35); pat.add_color_stop_rgba(1, 1, .85, .5, 0)
    ctx.set_source(pat); ctx.arc(dx + S * .28, y - S * .74, S * .6, 0, TAU); ctx.fill()
    # bed
    bx = x + S * 1.6
    setc(ctx, "#3f5a8a"); ctx.rectangle(bx - S * .6, y - S * .3, S * 1.3, S * .18); ctx.fill()
    setc(ctx, "#e9e4da"); ctx.rectangle(bx + S * .4, y - S * .38, S * .26, S * .1); ctx.fill()
    setc(ctx, "#5b3d2a"); ctx.rectangle(bx - S * .62, y - S * .12, S * 1.34, S * .12); ctx.fill()
    # rug
    setc(ctx, "#b0413e"); _ell(ctx, x + S * 0.2, y + S * 0.02, S * 0.7, S * 0.06); ctx.fill()


PROPS = {
    "campfire": campfire, "smoke": smoke, "acacia": acacia, "bush": bush, "grass": grass,
    "rock": rock, "boulder": boulder, "cliff": cliff, "bones": bones, "flakes": flakes,
    "grass_bed": grass_bed, "ochre": ochre, "hide_rack": hide_rack, "termite_mound": termite_mound,
    "carcass": carcass, "room": room,
}
