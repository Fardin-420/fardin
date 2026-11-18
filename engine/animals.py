"""Stylised procedural animals (gazelle, hyena, lion) with gait cycles."""
import math
import cairo
from .core import setc, lc, shade, hrand, noise1, lerp, clamp, TAU, Track

SPECIES = {
    "gazelle": dict(body=(0.40, 0.15), leg=(0.15, 0.15), hind=(0.15, 0.16), neck=0.12, neck_ang=-55, head=0.065,
                    col="#c8925a", belly="#f1e4cc", stripe="#5a3a22", horns=True, cycle=0.9, run_cycle=2.0),
    "hyena": dict(body=(0.42, 0.19), leg=(0.14, 0.13), hind=(0.11, 0.11), neck=0.11, neck_ang=-30, head=0.085,
                  col="#a99064", belly="#c9b48a", spots="#4a3a28", ears=True, cycle=0.8, run_cycle=1.6),
    "lion": dict(body=(0.56, 0.2), leg=(0.16, 0.14), hind=(0.15, 0.14), neck=0.12, neck_ang=-35, head=0.1,
                 col="#c99a50", belly="#e0c48e", ears=True, cycle=1.0, run_cycle=2.2),
}


def _ell(ctx, x, y, rx, ry, rot=0):
    ctx.save(); ctx.translate(x, y); ctx.rotate(rot); ctx.scale(max(rx, .01), max(ry, .01)); ctx.arc(0, 0, 1, 0, TAU); ctx.restore()


def _leg(ctx, hip, a1, a2, l1, l2, f, w, col):
    r1, r2 = math.radians(a1), math.radians(a1 + a2)
    k = (hip[0] + math.sin(r1) * l1 * f, hip[1] + math.cos(r1) * l1)
    e = (k[0] + math.sin(r2) * l2 * f, k[1] + math.cos(r2) * l2)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_line_width(w); setc(ctx, col)
    ctx.move_to(*hip); ctx.line_to(*k); ctx.line_to(*e); ctx.stroke()
    return e


def draw_quadruped(ctx, species, x, y, s, f, t, state="stand", phase=0.0, eyes_glow=0.0, seed=0):
    sp = SPECIES[species]
    S = 300 * s
    bl, bh = sp["body"][0] * S, sp["body"][1] * S
    l1, l2 = sp["leg"][0] * S, sp["leg"][1] * S
    h1, h2 = sp["hind"][0] * S, sp["hind"][1] * S
    col, belly = sp["col"], sp["belly"]
    dark = shade(col, -0.35)
    if state == "dead":
        ctx.save()
        ctx.translate(x, y - bh * 0.5)
        for i, dx in enumerate((-0.38, -0.28, 0.22, 0.32)):
            _leg(ctx, (dx * bl * f, bh * 0.2), 78 + i * 3, 6, l1, l2 * 0.9, f, S * 0.022, dark)
        _ell(ctx, 0, 0, bl * 0.55, bh * 0.5)
        setc(ctx, col); ctx.fill()
        _ell(ctx, 0, bh * 0.18, bl * 0.42, bh * 0.25)
        setc(ctx, belly); ctx.fill()
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_width(bh * 0.4); setc(ctx, col)
        ctx.move_to(bl * 0.4 * f, -bh * 0.1); ctx.line_to(bl * 0.7 * f, bh * 0.25); ctx.stroke()
        _ell(ctx, bl * 0.8 * f, bh * 0.32, sp["head"] * S * 1.2, sp["head"] * S * 0.6, 0.2 * f)
        setc(ctx, col); ctx.fill()
        if sp.get("horns"):
            ctx.set_line_width(S * 0.011); setc(ctx, "#2e2117")
            ctx.move_to(bl * 0.72 * f, bh * 0.15); ctx.curve_to(bl * 0.6 * f, -bh * 0.3, bl * 0.45 * f, -bh * 0.2, bl * 0.4 * f, -bh * 0.5); ctx.stroke()
        ctx.restore()
        return
    run = state == "run"
    leg_len = l1 + l2
    gait = phase
    bob = (abs(math.sin(gait)) * (0.06 if run else 0.015)) * S * 0.3
    hip_y = y - leg_len * (0.92 if not run else 0.85) - bob
    if state == "prowl":
        hip_y += leg_len * 0.12
    cx = x
    tilt = -0.12 if species == "hyena" else 0.0
    shoulder = (cx + bl * 0.36 * f, hip_y - (bl * 0.36 * math.sin(-tilt)))
    hipp = (cx - bl * 0.36 * f, hip_y + (bl * 0.36 * math.sin(-tilt)) * 0.3)
    # legs (far pair first, darker)
    amp = 38 if run else 22
    if state in ("stand", "graze", "alert", "prowl_still"):
        amp = 0
    offs = [(0.0, 0.5), (0.25, 0.75)] if not run else [(0.0, 0.12), (0.55, 0.65)]
    def legs(pair, col_, w):
        fo, ho = offs[0][pair], offs[1][pair]
        pf = gait + fo * TAU
        ph = gait + ho * TAU
        a = amp * math.sin(pf)
        kb = 25 * max(0, math.cos(pf)) if amp else 4
        _leg(ctx, shoulder, a, -kb - 4, l1, l2, f, w, col_)
        a2 = amp * math.sin(ph)
        kb2 = 30 * max(0, -math.cos(ph)) if amp else 6
        _leg(ctx, hipp, a2 + 10, kb2 + 4, h1, h2, f, w * 1.1, col_)
    legs(1, shade(col, -0.45), S * 0.022)
    legs(0, shade(col, -0.2), S * 0.026)
    # tail
    ctx.set_line_width(S * 0.012); setc(ctx, dark)
    tw = math.sin(t * 4 + seed) * 0.4
    ctx.move_to(hipp[0] - f * bl * 0.12, hipp[1] - bh * 0.2)
    ctx.line_to(hipp[0] - f * bl * (0.22 + 0.04 * tw), hipp[1] + bh * (0.2 + tw * .3))
    ctx.stroke()
    # body
    bx, by = (shoulder[0] + hipp[0]) / 2, (shoulder[1] + hipp[1]) / 2 - bh * 0.15
    ang = math.atan2(shoulder[1] - hipp[1], shoulder[0] - hipp[0]) if f > 0 else math.atan2(hipp[1] - shoulder[1], hipp[0] - shoulder[0])
    _ell(ctx, bx, by, bl * 0.55, bh * 0.55, ang)
    setc(ctx, col); ctx.fill()
    _ell(ctx, bx, by + bh * 0.22, bl * 0.45, bh * 0.28, ang)
    setc(ctx, belly); ctx.fill()
    if sp.get("stripe"):
        ctx.set_line_width(S * 0.012); setc(ctx, sp["stripe"])
        ctx.move_to(bx - bl * 0.38 * f, by + bh * 0.06); ctx.line_to(bx + bl * 0.4 * f, by + bh * 0.06); ctx.stroke()
    if sp.get("spots"):
        setc(ctx, sp["spots"])
        for i in range(9):
            _ell(ctx, bx + (hrand(species, i) - .5) * bl * 0.8, by + (hrand(species, "y", i) - .6) * bh * 0.6, S * 0.012, S * 0.01)
            ctx.fill()
        # bristly mane ridge
        ctx.set_line_width(S * 0.016); setc(ctx, "#3d2f20")
        ctx.move_to(bx - bl * 0.05 * f, by - bh * 0.5); ctx.line_to(bx + f * bl * 0.3, by - bh * 0.62); ctx.stroke()
    # neck + head
    na = sp["neck_ang"]
    if state == "graze":
        na = 50 + math.sin(t * 2 + seed) * 6
    elif state == "prowl":
        na = 5
    elif state == "alert":
        na = sp["neck_ang"] - 15
    na += noise1(t * 0.7, seed + 3) * 5
    r = math.radians(na)
    nb = (shoulder[0] + f * bl * 0.06, shoulder[1] - bh * 0.35)
    nh = (nb[0] + math.cos(r) * sp["neck"] * S * f, nb[1] + math.sin(r) * sp["neck"] * S)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_width(bh * (0.55 if species != "gazelle" else 0.38)); setc(ctx, col)
    ctx.move_to(*nb); ctx.line_to(*nh); ctx.stroke()
    hr = sp["head"] * S
    hd_ang = (0.5 if state == "graze" else 0.15) * f
    _ell(ctx, nh[0] + f * hr * 0.5, nh[1] + hr * 0.15, hr * 1.05, hr * 0.62, hd_ang)
    setc(ctx, col); ctx.fill()
    _ell(ctx, nh[0] + f * hr * 1.35, nh[1] + hr * 0.35, hr * 0.38, hr * 0.32, hd_ang)
    setc(ctx, shade(col, -0.5)); ctx.fill()
    if sp.get("horns"):
        ctx.set_line_width(S * 0.011); setc(ctx, "#2e2117")
        for k in (0, 1):
            ox = f * hr * (0.1 + 0.15 * k)
            ctx.move_to(nh[0] + ox, nh[1] - hr * 0.3)
            ctx.curve_to(nh[0] + ox - f * hr * 0.4, nh[1] - hr * 1.6, nh[0] + ox - f * hr * 1.2, nh[1] - hr * 1.6, nh[0] + ox - f * hr * 0.9, nh[1] - hr * 2.4)
            ctx.stroke()
        setc(ctx, col)
        _ell(ctx, nh[0] - f * hr * 0.2, nh[1] - hr * 0.5, hr * 0.15, hr * 0.4, -0.5 * f); ctx.fill()
    if sp.get("ears"):
        setc(ctx, shade(col, -0.2))
        for k in (0, 1):
            ctx.arc(nh[0] - f * hr * (0.1 + 0.25 * k), nh[1] - hr * 0.5, hr * 0.32, 0, TAU); ctx.fill()
    # eye
    ex, ey = nh[0] + f * hr * 0.75, nh[1] - hr * 0.05
    if eyes_glow > 0:
        for rr, a in ((hr * 0.9, 0.15), (hr * 0.45, 0.35)):
            ctx.set_source_rgba(1, 0.92, 0.45, a * eyes_glow)
            ctx.arc(ex, ey, rr, 0, TAU); ctx.fill()
        ctx.set_source_rgba(1, 1, 0.7, eyes_glow)
        ctx.arc(ex, ey, hr * 0.16, 0, TAU); ctx.fill()
    else:
        setc(ctx, "#140d08"); ctx.arc(ex, ey, hr * 0.12, 0, TAU); ctx.fill()


class Animal:
    def __init__(self, spec, seed=0):
        self.spec = spec
        self.species = spec.get("species", "gazelle")
        self.size = spec.get("size", 1.0)
        self.seed = seed
        self.layer = spec.get("layer", 0)
        acts = sorted(spec.get("track", [{"t": 0, "state": spec.get("state", "stand")}]), key=lambda a: a["t"])
        x, f, glow = spec.get("x", 0), spec.get("facing", 1), spec.get("glow", 0.0)
        xk, gk = [(0, x)], [(0, glow)]
        for a in acts:
            if "to" in a:
                xk.append((a["t"], x))
                if "face" not in a and a["to"] != x:
                    a["face"] = 1 if a["to"] > x else -1
                x = a["to"]
                xk.append((a["t"] + a.get("dur", 1), x, a.get("ease", "linear")))
            if "face" in a:
                f = a["face"]
            if "glow" in a:
                gk.append((a["t"], glow)); glow = a["glow"]; gk.append((a["t"] + .4, glow))
            a["_f"] = f
        self.acts, self.xt, self.gt = acts, Track(xk), Track(gk)
        self.y = spec.get("y", 0)

    def draw(self, ctx, t):
        act = self.acts[0]
        for a in self.acts:
            if a["t"] <= t:
                act = a
        x = self.xt(t)
        st = act.get("state", "stand")
        sp = SPECIES[self.species]
        cyc = (sp["run_cycle"] if st == "run" else sp["cycle"]) * 300 * self.size
        dist = abs(x - self.xt(act["t"]))
        ph = dist / cyc * TAU + self.seed if st in ("walk", "run", "prowl") else 0
        if st in ("walk", "run", "prowl") and dist < 1:
            ph = t * TAU * (2.4 if st == "run" else 1.1)
        # shadow
        S = 300 * self.size
        ctx.save(); ctx.translate(x, self.y + 2); ctx.scale(S * 0.25, S * 0.035); ctx.arc(0, 0, 1, 0, TAU); ctx.restore()
        ctx.set_source_rgba(0, 0, 0, 0.2); ctx.fill()
        draw_quadruped(ctx, self.species, x, self.y, self.size, act["_f"], t, st, ph, self.gt(t), self.seed)
