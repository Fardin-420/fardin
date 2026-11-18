"""Era pack: Old Kingdom Egypt (c. 2560 BC) — workers, poses, tools, props, sets, sledges.

Everything registers itself into the shared engine registries (rig.POSES, props.PROPS,
character item/actor hooks, scene set hooks), so episodes just reference names.
"""
import math
import cairo
from .core import setc, lc, shade, hexc, hrand, noise1, lerp, clamp, TAU, cmix, Track, smoothstep
from . import rig as R
from .rig import P, _breath, HIP_H, HEAD_R
from . import props as PR
from .props import _ell, flame, fire_light

# =============================================================== poses
def p_pull_rope(t, ph, a):
    s, c = math.sin(ph), math.cos(ph)
    return P(torso=30 + 2 * s, head=-16, y=0.03 + 0.015 * abs(s),
             hl_f=20 * s + 14, hl_b=-20 * s + 14, kn_f=-(14 + 34 * max(0, c)), kn_b=-(14 + 34 * max(0, -c)),
             sa_f=-28 + 4 * s, ea_f=-30, sa_b=-40 - 4 * s, ea_b=-20)


def p_push_lever(t, ph, a):
    k = 0.5 + 0.5 * math.sin(t * 2.2 + (a or 0))
    return P(torso=38 + 14 * k, head=-22, y=0.06 + 0.05 * k, sa_f=70 + 20 * k, ea_f=10, sa_b=60 + 20 * k, ea_b=14,
             hl_f=30, kn_f=-30 - 20 * k, hl_b=-24, kn_b=-10)


def p_carve(t, ph, a):
    hit = (t * 1.8 + (a or 0)) % 1.0
    k = math.sin(clamp(hit / 0.6) * math.pi) if hit < 0.6 else 0
    return P(torso=8, head=-6, sa_f=88, ea_f=24, sa_b=60 + 50 * k, ea_b=70 - 40 * k, hl_f=10, hl_b=-10, kn_f=-6, kn_b=-6)


def p_carry_block_team(t, ph, a):
    d = R.p_walk(t, ph, a)
    d.update(sa_f=165, ea_f=-20, sa_b=-165, ea_b=20, torso=4, head=-4)
    return d


def p_pour_water(t, ph, a):
    k = 0.5 + 0.5 * math.sin(t * 1.4)
    return P(torso=36, head=-26, y=0.08, sa_f=72 + 10 * k, ea_f=22, sa_b=60, ea_b=56,
             hl_f=34, kn_f=-46, hl_b=-14, kn_b=-30)


def p_write_papyrus(t, ph, a):
    w = math.sin(t * 9 + (a or 0)) * 4
    b = _breath(t)
    return P(torso=18 + b, head=-24, y=HIP_H - 0.06, hl_f=135, kn_f=-120, hl_b=125, kn_b=-115,
             sa_f=60 + w, ea_f=40 - w, sa_b=40, ea_b=50)


def p_bake(t, ph, a):
    k = math.sin(t * 1.6 + (a or 0))
    return P(torso=34 + 6 * k, head=-20, y=0.18, hl_f=75, kn_f=-90, hl_b=50, kn_b=-95,
             sa_f=80 + 14 * k, ea_f=20, sa_b=66 + 10 * k, ea_b=30)


def p_cheer_team(t, ph, a):
    k = abs(math.sin(t * 5 + (a or 0)))
    return P(y=-0.03 * k, torso=-4, head=-12, sa_f=160 + 10 * k, ea_f=-10, sa_b=-140 + 30 * k, ea_b=40,
             hl_f=8, hl_b=-8, kn_f=-12 * k, kn_b=-12 * k)


def p_wipe_sweat(t, ph, a):
    k = math.sin(clamp((t % 2.6) / 1.2) * math.pi)
    return P(torso=4, head=-8 + 6 * k, sa_f=60 + 80 * k, ea_f=60 + 70 * k, sa_b=-6, ea_b=14, hl_f=6, hl_b=-6)


def p_stand_staff(t, ph, a):
    b = _breath(t)
    return P(torso=-2 + b, head=-6 + math.sin(t * 0.6 + (a or 0)) * 6, sa_f=22, ea_f=40, sa_b=-8, ea_b=20, hl_f=6, hl_b=-6)


def p_row(t, ph, a):
    k = math.sin(t * 2.4 + (a or 0))
    return P(torso=20 + 18 * k, head=-10, y=HIP_H - 0.06, hl_f=110, kn_f=-80, hl_b=100, kn_b=-80,
             sa_f=70 - 40 * k, ea_f=20, sa_b=60 - 40 * k, ea_b=20)


def p_dive(t, ph, a):
    u = clamp(t / 0.5)
    return P(x=-0.55 * math.sin(u * math.pi / 2), y=-0.12 * math.sin(u * math.pi) + 0.2 * smoothstep(0.5, 0.9, t),
             rot=-60 * u, torso=20, head=10, sa_f=-150, ea_f=10, sa_b=-170, ea_b=10, hl_f=-30, kn_f=-10, hl_b=-50, kn_b=-20)


R.POSES.update({"pull_rope": p_pull_rope, "push_lever": p_push_lever, "carve": p_carve,
                "carry_block_team": p_carry_block_team, "pour_water": p_pour_water, "write_papyrus": p_write_papyrus,
                "bake": p_bake, "cheer_team": p_cheer_team, "wipe_sweat": p_wipe_sweat, "stand_staff": p_stand_staff,
                "row": p_row, "dive": p_dive})
R.LOCOMOTION.update({"pull_rope": 0.6, "carry_block_team": 0.7})

# =============================================================== items
def _seg(ctx, a, b, w, col):
    ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_width(w); setc(ctx, col)
    ctx.move_to(*a); ctx.line_to(*b); ctx.stroke()


def draw_egypt_item(ctx, item, J, side, s, st):
    wr, el = J["wrist_" + side], J["elbow_" + side]
    dx, dy = wr[0] - el[0], wr[1] - el[1]
    ln = math.hypot(dx, dy) or 1
    dx, dy = dx / ln, dy / ln
    f = st["f"]
    if item == "staff" and side == "f":
        _seg(ctx, (wr[0] + f * 0.01 * s, wr[1] - 0.45 * s), (wr[0] - f * 0.01 * s, wr[1] + 0.42 * s), 0.02 * s, "#6b4a2a")
        _seg(ctx, (wr[0] + f * 0.01 * s, wr[1] - 0.45 * s), (wr[0] + f * 0.06 * s, wr[1] - 0.5 * s), 0.02 * s, "#6b4a2a")
    elif item == "papyrus" and side == "b":
        ctx.save(); ctx.translate(wr[0] + f * 0.06 * s, wr[1] + 0.01 * s)
        ctx.rectangle(-0.07 * s, -0.025 * s, 0.14 * s, 0.05 * s); setc(ctx, "#efe2b8"); ctx.fill()
        setc(ctx, "#8a6a3c")
        for i in range(3):
            ctx.rectangle(-0.06 * s, -0.018 * s + i * 0.014 * s, 0.1 * s, 0.004 * s); ctx.fill()
        ctx.restore()
    elif item == "pen" and side == "f":
        _seg(ctx, wr, (wr[0] + dx * 0.07 * s, wr[1] + dy * 0.07 * s), 0.008 * s, "#3a2a1a")
    elif item == "chisel" and side == "f":
        _seg(ctx, wr, (wr[0] + f * 0.08 * s, wr[1] - 0.01 * s), 0.016 * s, "#b5652e")
    elif item == "mallet" and side == "b":
        hx, hy = wr[0] + dx * 0.06 * s, wr[1] + dy * 0.06 * s
        _seg(ctx, wr, (hx, hy), 0.014 * s, "#6b4a2a")
        ctx.save(); ctx.translate(hx, hy); ctx.rotate(math.atan2(dy, dx))
        ctx.rectangle(-0.01 * s, -0.035 * s, 0.05 * s, 0.07 * s); setc(ctx, "#8a5a32"); ctx.fill(); ctx.restore()
    elif item == "jar" and side == "f":
        ctx.save(); ctx.translate(wr[0] + dx * 0.04 * s, wr[1] + dy * 0.04 * s)
        ctx.rotate(math.atan2(dy, dx) - math.pi / 2)
        _ell(ctx, 0, 0.03 * s, 0.045 * s, 0.06 * s); setc(ctx, "#a4532e"); ctx.fill()
        ctx.rectangle(-0.02 * s, -0.04 * s, 0.04 * s, 0.03 * s); ctx.fill()
        ctx.restore()
    elif item == "bread" and side == "f":
        ctx.move_to(wr[0] - 0.035 * s, wr[1]); ctx.line_to(wr[0], wr[1] - 0.08 * s); ctx.line_to(wr[0] + 0.035 * s, wr[1])
        ctx.close_path(); setc(ctx, "#c98b45"); ctx.fill()
    elif item == "rope" and side == "f":
        pass
    else:
        return False
    return True


# =============================================================== Egyptian worker
EG_SKINS = ["#8d5a3b", "#a0673f", "#7a4a30", "#b07448", "#6b4026", "#94603e", "#c08455"]
EG_HAIR = ["cap", "cap", "cap", "wig", "bald", "headcloth"]
KILT = "#f3eee0"


class EgyptPerson:
    """Mixin-style renderer swapped onto an EraPerson instance (keeps all animation logic)."""

    @staticmethod
    def setup(self, spec, seed):
        r = lambda k: hrand(self.id, k, seed)
        self.skin = spec.get("skin", EG_SKINS[int(r("skin") * len(EG_SKINS))])
        self.role = spec.get("role", "worker")
        self.hair = spec.get("hair", "wig" if self.role in ("overseer", "scribe") else EG_HAIR[int(r("hair") * len(EG_HAIR))])
        self.kilt_len = {"overseer": 0.2, "scribe": 0.17, "healer": 0.19}.get(self.role, 0.13)
        self.collar = spec.get("collar", self.role in ("overseer", "scribe", "healer"))
        self.cloth = spec.get("cloth", ["#e9dcc0", "#d9c9a6", "#f0e6cf"][int(r("cloth") * 3)])

    @staticmethod
    def render(self, ctx, t, st, J):
        from .character import _poly2, draw_item
        from .rig import draw_face
        s, f = self.size, st["f"]
        A = st["alpha"]
        if A < 0.999:
            ctx.push_group()
        limb = shade(self.skin, -0.45)
        limb_b = shade(self.skin, -0.62)
        _poly2(ctx, [J["shoulder"], J["elbow_b"], J["wrist_b"]], 0.04 * s, limb_b)
        if st["hold"]:
            draw_item(ctx, st["hold"], J, "b", s, st, back=True)
        _poly2(ctx, [J["hip"], J["knee_b"], J["ankle_b"], J["toe_b"]], 0.044 * s, limb_b)
        _poly2(ctx, [J["hip"], J["neck"]], 0.06 * s, limb)
        _poly2(ctx, [J["hip"], J["knee_f"], J["ankle_f"], J["toe_f"]], 0.044 * s, limb)
        # kilt (shendyt): white wrap with belt + front flap
        hip, neck = J["hip"], J["neck"]
        ax, ay = neck[0] - hip[0], neck[1] - hip[1]
        L = math.hypot(ax, ay) or 1
        ux, uy = ax / L, ay / L
        nx, ny = -uy, ux
        top = (hip[0] + ux * 0.045 * s, hip[1] + uy * 0.045 * s)
        bot = (hip[0] - ux * self.kilt_len * s, hip[1] - uy * self.kilt_len * s)
        sway = math.sin(t * 3 + self.seed) * 0.006 * s
        w0, w1 = 0.05 * s, 0.085 * s
        ctx.move_to(top[0] + nx * w0, top[1] + ny * w0)
        ctx.line_to(bot[0] + nx * w1 + sway, bot[1] + ny * w1)
        ctx.line_to(bot[0] - nx * w1 + sway, bot[1] - ny * w1)
        ctx.line_to(top[0] - nx * w0, top[1] - ny * w0)
        ctx.close_path()
        setc(ctx, KILT); ctx.fill_preserve()
        ctx.set_line_width(0.008 * s); setc(ctx, "#b8ad94"); ctx.stroke()
        # pleats + front flap
        ctx.set_line_width(0.004 * s); setc(ctx, "#cfc5ad")
        for k in (-0.5, 0.0, 0.5):
            ctx.move_to(lerp(top[0], top[0] + nx * w0 * k, 1), top[1] + ny * w0 * k)
            ctx.line_to(bot[0] + nx * w1 * k + sway, bot[1] + ny * w1 * k)
        ctx.stroke()
        _seg(ctx, (top[0] + nx * w0, top[1] + ny * w0), (top[0] - nx * w0, top[1] - ny * w0), 0.016 * s, "#c9b98f")
        if self.role == "overseer":
            _seg(ctx, (neck[0] + nx * 0.04 * s, neck[1] + ny * 0.04 * s), (top[0] - nx * 0.04 * s, top[1] - ny * 0.04 * s), 0.02 * s, "#e8dfc6")
        hc = J["head"]
        r = HEAD_R * s
        # hair back part
        dark = (0.06, 0.05, 0.05, 1)
        if self.hair == "wig":
            setc(ctx, dark)
            ctx.move_to(hc[0] - f * r * 0.1, hc[1] - r * 1.05)
            ctx.curve_to(hc[0] - f * r * 1.35, hc[1] - r * 0.8, hc[0] - f * r * 1.25, hc[1] + r * 0.9, hc[0] - f * r * 0.5, hc[1] + r * 1.15)
            ctx.line_to(hc[0] + f * r * 0.1, hc[1] + r * 0.5); ctx.close_path(); ctx.fill()
        elif self.hair == "headcloth":
            setc(ctx, self.cloth)
            ctx.move_to(hc[0] - f * r * 0.2, hc[1] - r * 0.9)
            ctx.curve_to(hc[0] - f * r * 1.3, hc[1] - r * 0.6, hc[0] - f * r * 1.2, hc[1] + r * 0.7, hc[0] - f * r * 0.8, hc[1] + r * 1.0)
            ctx.line_to(hc[0] - f * r * 0.2, hc[1] + r * 0.2); ctx.close_path(); ctx.fill()
        ctx.arc(hc[0], hc[1], r, 0, TAU)
        setc(ctx, self.skin); ctx.fill_preserve()
        ctx.set_line_width(0.013 * s); setc(ctx, shade(self.skin, -0.5)); ctx.stroke()
        if self.hair in ("cap", "wig"):
            setc(ctx, dark)
            ctx.arc(hc[0] - f * 0.05 * r, hc[1] - 0.05 * r, r * 1.04, math.pi * 1.04 if f > 0 else math.pi * 1.0,
                    math.pi * 1.96 if f > 0 else math.pi * 2.0)
            ctx.fill()
            if self.hair == "wig":
                ctx.rectangle(hc[0] - f * r * 0.15 - r * 0.15, hc[1] - r * 0.1, r * 0.3, r * 0.5); ctx.fill()
        elif self.hair == "headcloth":
            setc(ctx, self.cloth)
            ctx.arc(hc[0] - f * 0.05 * r, hc[1] - 0.05 * r, r * 1.06, math.pi * 1.0, math.pi * 2.0); ctx.fill()
            _seg(ctx, (hc[0] - r, hc[1] - 0.12 * r), (hc[0] + r, hc[1] - 0.12 * r), 0.06 * r, shade(self.cloth, -0.2))
        if self.collar:  # broad collar (wesekh)
            ctx.arc(neck[0], neck[1] + 0.01 * s, 0.05 * s, 0, math.pi)
            ctx.set_line_width(0.02 * s); setc(ctx, "#2c7a8a"); ctx.stroke()
            ctx.arc(neck[0], neck[1] + 0.01 * s, 0.035 * s, 0, math.pi)
            ctx.set_line_width(0.01 * s); setc(ctx, "#d9a441"); ctx.stroke()
        ink = (0.07, 0.04, 0.03, 1)
        hr = J.get("rot", 0) + st["pose"]["head"] * 0.3
        draw_face(ctx, hc, r, f, st["expr"], self.blink(t), self.mouth(t), st["pose"].get("look", 0), ink, rot=hr)
        _poly2(ctx, [J["shoulder"], J["elbow_f"], J["wrist_f"]], 0.04 * s, limb)
        ctx.arc(J["wrist_f"][0], J["wrist_f"][1], 0.022 * s, 0, TAU); setc(ctx, limb); ctx.fill()
        if st["hold"]:
            draw_item(ctx, st["hold"], J, "f", s, st)
        if A < 0.999:
            ctx.pop_group_to_source()
            ctx.paint_with_alpha(A)


# =============================================================== props
def block(ctx, x, y, s, t, seed=0, kind="rough", w=1.0, h=1.0):
    S = 300 * s
    bw, bh, d = S * 0.42 * w, S * 0.3 * h, S * 0.08
    base = "#f4efe3" if kind == "polished" else "#d9c497"
    ctx.rectangle(x - bw / 2, y - bh, bw, bh); setc(ctx, lc(base)); ctx.fill()
    ctx.move_to(x - bw / 2, y - bh); ctx.line_to(x - bw / 2 + d, y - bh - d * 0.6); ctx.line_to(x + bw / 2 + d, y - bh - d * 0.6)
    ctx.line_to(x + bw / 2, y - bh); ctx.close_path(); setc(ctx, lc(shade(base, 0.12))); ctx.fill()
    ctx.move_to(x + bw / 2, y - bh); ctx.line_to(x + bw / 2 + d, y - bh - d * 0.6); ctx.line_to(x + bw / 2 + d, y - d * 0.6)
    ctx.line_to(x + bw / 2, y); ctx.close_path(); setc(ctx, lc(shade(base, -0.18))); ctx.fill()
    if kind == "polished":
        g = (t * 0.25 + hrand(seed, "g")) % 1
        ctx.save(); ctx.rectangle(x - bw / 2, y - bh, bw, bh); ctx.clip()
        ctx.move_to(x - bw / 2 + g * bw * 1.6 - bw * 0.3, y - bh); ctx.line_to(x - bw / 2 + g * bw * 1.6, y - bh)
        ctx.line_to(x - bw / 2 + g * bw * 1.6 - bw * 0.4, y); ctx.line_to(x - bw / 2 + g * bw * 1.6 - bw * 0.7, y); ctx.close_path()
        ctx.set_source_rgba(1, 1, 1, 0.45); ctx.fill(); ctx.restore()
    else:
        ctx.set_line_width(S * 0.005); setc(ctx, lc("#a8936a"))
        for i in range(7):
            px = x - bw / 2 + hrand(seed, "cx", i) * bw
            py = y - bh + hrand(seed, "cy", i) * bh
            ctx.move_to(px, py); ctx.line_to(px + S * 0.025, py + S * 0.012); ctx.stroke()
    ctx.rectangle(x - bw / 2, y - bh, bw, bh); ctx.set_line_width(S * 0.006); setc(ctx, lc(shade(base, -0.35))); ctx.stroke()


def block_stack(ctx, x, y, s, t, seed=0, n=6, kind="rough"):
    S = 300 * s
    k = 0
    for row in range(3):
        for i in range(max(1, n // 2 - row)):
            if k >= n:
                return
            block(ctx, x + (i - (n // 2 - row - 1) / 2) * S * 0.44, y - row * S * 0.3, s, t, seed + k, kind)
            k += 1


def sledge_draw(ctx, x, y, s, f, block_kind="rough", t=0, seed=0):
    S = 300 * s
    L = S * 0.75
    ctx.save(); ctx.translate(x, y)
    ctx.scale(f, 1)
    # runners
    ctx.set_line_width(S * 0.035); ctx.set_line_cap(cairo.LINE_CAP_ROUND); setc(ctx, lc("#7a5230"))
    ctx.move_to(-L / 2, -S * 0.02); ctx.line_to(L / 2 - S * 0.06, -S * 0.02)
    ctx.curve_to(L / 2, -S * 0.02, L / 2 + S * 0.05, -S * 0.06, L / 2 + S * 0.05, -S * 0.12); ctx.stroke()
    ctx.set_line_width(S * 0.02); setc(ctx, lc("#5e3e22"))
    for i in range(5):
        xx = -L / 2 + S * 0.04 + i * (L - S * 0.1) / 4
        ctx.move_to(xx, -S * 0.02); ctx.line_to(xx, -S * 0.07); ctx.stroke()
    ctx.rectangle(-L / 2, -S * 0.08, L - S * 0.02, S * 0.025); setc(ctx, lc("#8a6038")); ctx.fill()
    ctx.restore()
    block(ctx, x, y - S * 0.08, s * 1.35, t, seed, block_kind, w=1.0, h=1.05)
    # lashing ropes over block
    ctx.set_line_width(S * 0.01); setc(ctx, lc("#c2a36a"))
    for k in (-0.18, 0.18):
        ctx.move_to(x + k * S, y - S * 0.08); ctx.line_to(x + k * S + S * 0.03, y - S * 0.52); ctx.stroke()


def pyramid(ctx, x, y, s, t, seed=0, stage=1.0, casing=0.0, ramp=False, workers=True, gleam=0.0):
    S = 300 * s
    W = S * 4.0
    Hh = W * 0.636
    st = clamp(stage, 0.02, 1.0)
    h = Hh * st
    tw = W / 2 * (1 - st)
    lit, shd = "#dcc290", "#b89a68"
    if ramp and st < 1:
        rx0 = x - W / 2 - W * 0.45
        ctx.move_to(rx0, y); ctx.line_to(x - tw * 0.6, y - h); ctx.line_to(x - tw * 0.6 + S * 0.25, y - h)
        ctx.line_to(x - W / 2 + S * 0.4, y); ctx.close_path()
        setc(ctx, lc("#a57a50")); ctx.fill()
        ctx.set_line_width(S * 0.01); setc(ctx, lc("#8a6340"))
        for i in range(1, 12):
            u = i / 12
            ctx.move_to(lerp(rx0, x - tw * 0.6, u), y - h * u)
            ctx.line_to(lerp(x - W / 2 + S * 0.4, x - tw * 0.6 + S * 0.25, u), y - h * u); ctx.stroke()
    # faces
    ctx.move_to(x - W / 2, y); ctx.line_to(x - tw, y - h); ctx.line_to(x, y - h); ctx.line_to(x, y); ctx.close_path()
    setc(ctx, lc(lit)); ctx.fill()
    ctx.move_to(x, y); ctx.line_to(x, y - h); ctx.line_to(x + tw, y - h); ctx.line_to(x + W / 2, y); ctx.close_path()
    setc(ctx, lc(shd)); ctx.fill()
    # stone courses
    nc = int(40 * st) + 1
    ctx.set_line_width(max(1.0, S * 0.004))
    for i in range(1, nc):
        yy = y - h * i / nc
        half = W / 2 * (1 - st * i / nc)
        setc(ctx, lc(shade(lit, -0.12), 0.8))
        ctx.move_to(x - half, yy); ctx.line_to(x, yy); ctx.stroke()
        setc(ctx, lc(shade(shd, -0.12), 0.8))
        ctx.move_to(x, yy); ctx.line_to(x + half, yy); ctx.stroke()
    # white Tura casing from the bottom up
    if casing > 0:
        ch = h * clamp(casing)
        ctw = W / 2 * (1 - st * clamp(casing))
        ctx.move_to(x - W / 2, y); ctx.line_to(x - ctw, y - ch); ctx.line_to(x, y - ch); ctx.line_to(x, y); ctx.close_path()
        setc(ctx, lc("#f6f2e8")); ctx.fill()
        ctx.move_to(x, y); ctx.line_to(x, y - ch); ctx.line_to(x + ctw, y - ch); ctx.line_to(x + W / 2, y); ctx.close_path()
        setc(ctx, lc("#d8d0bf")); ctx.fill()
        if gleam > 0:
            g = (t * 0.12) % 1.4 - 0.2
            ctx.save()
            ctx.move_to(x - W / 2, y); ctx.line_to(x - ctw, y - ch); ctx.line_to(x, y - ch); ctx.line_to(x, y); ctx.close_path(); ctx.clip()
            gx = x - W / 2 + g * W * 0.6
            grad = cairo.LinearGradient(gx - S * 0.6, 0, gx + S * 0.6, 0)
            grad.add_color_stop_rgba(0, 1, 1, 1, 0); grad.add_color_stop_rgba(0.5, 1, 1, 0.95, 0.75 * gleam); grad.add_color_stop_rgba(1, 1, 1, 1, 0)
            ctx.set_source(grad); ctx.paint()
            ctx.restore()
    # tiny workers moving on the ramp / faces
    if workers and st < 1:
        for i in range(24):
            ph = (t * 0.03 + hrand(seed, "w", i)) % 1
            if ramp:
                px = lerp(x - W / 2 - W * 0.4, x - tw * 0.6, ph) + hrand(seed, "wx", i) * S * 0.2
                py = y - h * ph
            else:
                py = y - h * (0.1 + 0.85 * hrand(seed, "wy", i))
                half = W / 2 * (1 - st * (y - py) / max(1, h))
                px = x - half + (hrand(seed, "wx", i) * 2 * half)
            ctx.rectangle(px, py - S * 0.022, S * 0.008, S * 0.022); setc(ctx, lc("#3a2618")); ctx.fill()
            ctx.rectangle(px - S * 0.002, py - S * 0.01, S * 0.012, S * 0.006); setc(ctx, lc("#f3eee0")); ctx.fill()


def palm(ctx, x, y, s, t, seed=0):
    S = 300 * s
    sway = math.sin(t * 0.8 + seed) * S * 0.02
    hgt = S * (1.0 + 0.3 * hrand(seed, "h"))
    lean = (hrand(seed, "l") - 0.5) * S * 0.3
    tx, ty = x + lean + sway, y - hgt
    ctx.set_line_width(S * 0.05); ctx.set_line_cap(cairo.LINE_CAP_ROUND); setc(ctx, lc("#6e5235"))
    ctx.move_to(x, y); ctx.curve_to(x, y - hgt * 0.5, tx - lean * 0.2, ty + hgt * 0.3, tx, ty); ctx.stroke()
    setc(ctx, lc("#5b4430")); ctx.set_line_width(S * 0.008)
    for i in range(8):
        u = i / 8
        px = lerp(x, tx, u); py = lerp(y, ty, u)
        ctx.move_to(px - S * 0.025, py); ctx.line_to(px + S * 0.025, py - S * 0.01); ctx.stroke()
    for i in range(8):
        a = -math.pi / 2 + (i - 3.5) * 0.42 + math.sin(t * 1.1 + i) * 0.04
        L = S * (0.45 + 0.1 * hrand(seed, "f", i))
        ex, ey = tx + math.cos(a) * L, ty + math.sin(a) * L * 0.6 + L * 0.35
        ctx.move_to(tx, ty)
        ctx.curve_to(tx + math.cos(a) * L * 0.5, ty + math.sin(a) * L * 0.6 - S * 0.05, ex, ey - S * 0.04, ex, ey)
        ctx.set_line_width(S * 0.045); setc(ctx, lc("#4f7a2f" if i % 2 else "#5f8a35")); ctx.stroke()
    setc(ctx, lc("#8a4a1a"))
    for i in range(4):
        ctx.arc(tx + (i - 1.5) * S * 0.02, ty + S * 0.04, S * 0.014, 0, TAU); ctx.fill()


def reeds(ctx, x, y, s, t, seed=0, n=14):
    S = 300 * s
    for i in range(n):
        bx = x + (i - n / 2) * S * 0.025
        hh = S * (0.25 + 0.2 * hrand(seed, i))
        sw = math.sin(t * 1.5 + i * 0.7) * S * 0.015
        ctx.move_to(bx, y); ctx.curve_to(bx, y - hh * 0.6, bx + sw, y - hh * 0.8, bx + sw * 1.5, y - hh)
        ctx.set_line_width(S * 0.008); setc(ctx, lc("#6d8a3a" if i % 3 else "#839a45")); ctx.stroke()
        _ell(ctx, bx + sw * 1.5, y - hh, S * 0.008, S * 0.025); setc(ctx, lc("#8a6a3a")); ctx.fill()


def reed_boat(ctx, x, y, s, t, seed=0, flip=False, rower=True):
    S = 300 * s
    by = y + math.sin(t * 1.6 + seed) * S * 0.01
    L = S * 0.9
    ctx.move_to(x - L / 2, by - S * 0.12)
    ctx.curve_to(x - L * 0.3, by + S * 0.04, x + L * 0.3, by + S * 0.04, x + L / 2, by - S * 0.12)
    ctx.curve_to(x + L * 0.35, by - S * 0.02, x - L * 0.35, by - S * 0.02, x - L / 2, by - S * 0.12)
    ctx.close_path(); setc(ctx, lc("#b9a052")); ctx.fill()
    ctx.set_line_width(S * 0.008); setc(ctx, lc("#7f6a2e"))
    for i in range(7):
        xx = x - L * 0.38 + i * L * 0.127
        ctx.move_to(xx, by - S * 0.08); ctx.line_to(xx + S * 0.01, by - S * 0.0); ctx.stroke()
    if rower:
        ctx.set_line_width(S * 0.012); setc(ctx, lc("#6b4a2a"))
        a = math.sin(t * 2.2 + seed) * 0.4
        ctx.move_to(x, by - S * 0.25); ctx.line_to(x + math.sin(a) * S * 0.3, by + S * 0.05); ctx.stroke()


def barge(ctx, x, y, s, t, seed=0, cargo=2, sail=True):
    S = 300 * s
    by = y + math.sin(t * 1.2 + seed) * S * 0.008
    L = S * 2.2
    ctx.move_to(x - L / 2, by - S * 0.22)
    ctx.curve_to(x - L * 0.35, by + S * 0.03, x + L * 0.35, by + S * 0.03, x + L / 2, by - S * 0.24)
    ctx.line_to(x + L * 0.42, by - S * 0.12); ctx.line_to(x - L * 0.42, by - S * 0.12); ctx.close_path()
    setc(ctx, lc("#8a5a32")); ctx.fill()
    ctx.set_line_width(S * 0.008); setc(ctx, lc("#5e3a1e"))
    for i in range(3):
        ctx.move_to(x - L * 0.42, by - S * 0.1 + i * S * 0.035); ctx.line_to(x + L * 0.42, by - S * 0.1 + i * S * 0.035); ctx.stroke()
    for i in range(cargo):
        block(ctx, x - L * 0.22 + i * S * 0.5, by - S * 0.12, s * 0.95, t, seed + i, "polished" if seed % 2 else "rough")
    if sail:
        mx = x + L * 0.18
        ctx.set_line_width(S * 0.02); setc(ctx, lc("#6b4a2a"))
        ctx.move_to(mx, by - S * 0.12); ctx.line_to(mx, by - S * 1.2); ctx.stroke()
        bil = math.sin(t * 0.9 + seed) * S * 0.04
        ctx.move_to(mx - S * 0.35, by - S * 1.15); ctx.line_to(mx + S * 0.35, by - S * 1.15)
        ctx.curve_to(mx + S * 0.38 + bil, by - S * 0.8, mx + S * 0.38 + bil, by - S * 0.6, mx + S * 0.35, by - S * 0.45)
        ctx.line_to(mx - S * 0.35, by - S * 0.45)
        ctx.curve_to(mx - S * 0.32 + bil, by - S * 0.6, mx - S * 0.32 + bil, by - S * 0.8, mx - S * 0.35, by - S * 1.15)
        ctx.close_path(); setc(ctx, lc("#efe7d2")); ctx.fill()
    # steering oar
    ctx.set_line_width(S * 0.02); setc(ctx, lc("#6b4a2a"))
    ctx.move_to(x - L * 0.45, by - S * 0.35); ctx.line_to(x - L * 0.55, by + S * 0.05); ctx.stroke()


def mudbrick_house(ctx, x, y, s, t, seed=0, w=1.0):
    S = 300 * s
    W, Hh = S * 0.9 * w, S * 0.62
    ctx.rectangle(x - W / 2, y - Hh, W, Hh); setc(ctx, lc("#b98a5e")); ctx.fill()
    ctx.rectangle(x - W / 2, y - Hh, W, S * 0.05); setc(ctx, lc("#a07450")); ctx.fill()
    ctx.set_line_width(max(1, S * 0.003)); setc(ctx, lc("#a27a52"))
    for r in range(1, 9):
        yy = y - Hh + r * Hh / 9
        ctx.move_to(x - W / 2, yy); ctx.line_to(x + W / 2, yy); ctx.stroke()
    for i in range(5):
        ctx.move_to(x - W / 2 + (i + 0.5) * W / 5, y - Hh - S * 0.02); ctx.line_to(x - W / 2 + (i + 0.5) * W / 5 + S * 0.04, y - Hh - S * 0.05)
    ctx.set_line_width(S * 0.015); setc(ctx, lc("#6e4e30")); ctx.stroke()
    ctx.rectangle(x - S * 0.09, y - S * 0.36, S * 0.18, S * 0.36); setc(ctx, lc("#3b2416")); ctx.fill()
    ctx.rectangle(x + W * 0.25, y - Hh * 0.75, S * 0.1, S * 0.07); ctx.fill()


def oven(ctx, x, y, s, t, seed=0):
    S = 300 * s
    ctx.move_to(x - S * 0.3, y); ctx.curve_to(x - S * 0.3, y - S * 0.45, x + S * 0.3, y - S * 0.45, x + S * 0.3, y)
    ctx.close_path(); setc(ctx, lc("#9b5a3a")); ctx.fill()
    ctx.move_to(x - S * 0.12, y); ctx.curve_to(x - S * 0.12, y - S * 0.18, x + S * 0.12, y - S * 0.18, x + S * 0.12, y)
    ctx.close_path(); setc(ctx, (1, 0.5, 0.15, 0.9)); ctx.fill()
    flame(ctx, x, y, S * 0.12, t, seed)
    PR.smoke(ctx, x + S * 0.05, y - S * 0.25, s * 0.5, t, seed, 0.12)


def bread_moulds(ctx, x, y, s, t, seed=0, n=7):
    S = 300 * s
    for i in range(n):
        row = i // 4
        bx = x + (i % 4 - 1.5) * S * 0.1 + row * S * 0.05
        by = y - row * S * 0.12
        ctx.move_to(bx - S * 0.045, by - S * 0.12); ctx.line_to(bx + S * 0.045, by - S * 0.12); ctx.line_to(bx + S * 0.012, by)
        ctx.line_to(bx - S * 0.012, by); ctx.close_path(); setc(ctx, lc("#a0522d" if i % 2 else "#8e4a28")); ctx.fill()
        ctx.move_to(bx - S * 0.04, by - S * 0.12); ctx.curve_to(bx - S * 0.03, by - S * 0.17, bx + S * 0.03, by - S * 0.17, bx + S * 0.04, by - S * 0.12)
        setc(ctx, lc("#d8a35a")); ctx.fill()


def beer_jars(ctx, x, y, s, t, seed=0, n=5):
    S = 300 * s
    for i in range(n):
        bx = x + (i - n / 2) * S * 0.13
        ctx.move_to(bx, y)
        ctx.curve_to(bx - S * 0.08, y - S * 0.08, bx - S * 0.07, y - S * 0.3, bx - S * 0.03, y - S * 0.34)
        ctx.line_to(bx + S * 0.03, y - S * 0.34)
        ctx.curve_to(bx + S * 0.07, y - S * 0.3, bx + S * 0.08, y - S * 0.08, bx, y)
        setc(ctx, lc("#b2683f" if i % 2 else "#a35c38")); ctx.fill()
        _ell(ctx, bx, y - S * 0.35, S * 0.04, S * 0.02); setc(ctx, lc("#6b4a2e")); ctx.fill()


def torch_post(ctx, x, y, s, t, seed=0):
    S = 300 * s
    ctx.set_line_width(S * 0.025); setc(ctx, lc("#5a3a20"))
    ctx.move_to(x, y); ctx.line_to(x, y - S * 0.75); ctx.stroke()
    _ell(ctx, x, y - S * 0.76, S * 0.04, S * 0.02); setc(ctx, lc("#3a2414")); ctx.fill()
    flame(ctx, x, y - S * 0.77, S * 0.22, t, seed)


def water_jar(ctx, x, y, s, t, seed=0):
    S = 300 * s
    _ell(ctx, x, y - S * 0.1, S * 0.08, S * 0.1); setc(ctx, lc("#a4532e")); ctx.fill()
    ctx.rectangle(x - S * 0.035, y - S * 0.23, S * 0.07, S * 0.05); ctx.fill()


def tent(ctx, x, y, s, t, seed=0):
    S = 300 * s
    ctx.move_to(x - S * 0.7, y); ctx.line_to(x, y - S * 0.7); ctx.line_to(x + S * 0.7, y); ctx.close_path()
    setc(ctx, lc("#e4d6b4")); ctx.fill()
    ctx.move_to(x, y - S * 0.7); ctx.line_to(x + S * 0.7, y); ctx.line_to(x + S * 0.2, y); ctx.close_path()
    setc(ctx, lc("#c9b791")); ctx.fill()
    ctx.move_to(x - S * 0.12, y); ctx.line_to(x, y - S * 0.35); ctx.line_to(x + S * 0.12, y); ctx.close_path()
    setc(ctx, lc("#3b2a1c")); ctx.fill()


def lever_beam(ctx, x, y, s, t, seed=0, ang=-0.35):
    S = 300 * s
    ctx.save(); ctx.translate(x, y - S * 0.1); ctx.rotate(ang + math.sin(t * 2.2) * 0.06)
    ctx.rectangle(-S * 0.6, -S * 0.025, S * 1.2, S * 0.05); setc(ctx, lc("#7a5230")); ctx.fill(); ctx.restore()
    block(ctx, x - S * 0.35, y, s * 0.6, t, seed)


def scribe_mat(ctx, x, y, s, t, seed=0):
    S = 300 * s
    _ell(ctx, x, y + S * 0.01, S * 0.35, S * 0.04); setc(ctx, lc("#b59a5e")); ctx.fill()
    ctx.rectangle(x + S * 0.12, y - S * 0.12, S * 0.22, S * 0.12); setc(ctx, lc("#7a5230")); ctx.fill()
    for i in range(3):
        _ell(ctx, x + S * 0.17 + i * S * 0.05, y - S * 0.14, S * 0.02, S * 0.012); setc(ctx, lc("#efe2b8")); ctx.fill()


def dust_cloud(ctx, x, y, s, t, seed=0, amount=1.0):
    S = 300 * s
    for i in range(8):
        ph = (t * 0.25 + hrand(seed, "dc", i)) % 1
        r = S * (0.08 + 0.18 * ph)
        ctx.set_source_rgba(0.86, 0.76, 0.58, 0.35 * amount * math.sin(ph * math.pi))
        ctx.arc(x + (hrand(seed, "dx", i) - 0.5) * S * 0.6 + ph * S * 0.2, y - r * 0.6 - ph * S * 0.1, r, 0, TAU); ctx.fill()


def volcano(ctx, x, y, s, t, seed=0):
    S = 300 * s
    ctx.move_to(x - S * 2.2, y); ctx.line_to(x - S * 0.35, y - S * 1.3); ctx.line_to(x + S * 0.35, y - S * 1.32); ctx.line_to(x + S * 2.4, y)
    ctx.close_path(); setc(ctx, lc("#5a4a4a")); ctx.fill()
    ctx.move_to(x - S * 0.35, y - S * 1.3); ctx.line_to(x + S * 0.35, y - S * 1.32); ctx.line_to(x + S * 0.2, y - S * 1.2); ctx.line_to(x - S * 0.2, y - S * 1.2)
    ctx.close_path(); setc(ctx, (1, 0.45, 0.15, 0.8)); ctx.fill()
    for i in range(14):
        ph = (t * 0.06 + i / 14) % 1
        r = S * (0.15 + 0.6 * ph)
        ctx.set_source_rgba(0.35, 0.33, 0.33, 0.55 * math.sin(ph * math.pi))
        ctx.arc(x + math.sin(ph * 4 + i) * S * 0.2 + ph * S * 0.9, y - S * 1.35 - ph * S * 2.2, r, 0, TAU); ctx.fill()


PR.PROPS.update({"volcano": volcano, "block": block, "block_stack": block_stack, "pyramid": pyramid, "palm": palm, "reeds": reeds,
                 "reed_boat": reed_boat, "barge": barge, "mudbrick_house": mudbrick_house, "oven": oven,
                 "bread_moulds": bread_moulds, "beer_jars": beer_jars, "torch_post": torch_post, "water_jar": water_jar,
                 "tent": tent, "lever_beam": lever_beam, "scribe_mat": scribe_mat, "dust_cloud": dust_cloud})
LIGHT_PROPS = {"torch_post": (0.8, -230), "oven": (0.6, -30)}  # light scale, y offset

# =============================================================== sledge (moving block + rope team + water)
class Sledge:
    def __init__(self, spec):
        self.spec = spec
        keys = [(0, spec.get("x", 0.0))]
        x = spec.get("x", 0.0)
        for k in sorted(spec.get("track", []), key=lambda a: a["t"]):
            keys.append((k["t"], x))
            x = k["to"]
            keys.append((k["t"] + k.get("dur", 1.0), x, k.get("ease", "linear")))
        self.xt = Track(keys)
        self.f = spec.get("facing", 1)
        self.s = spec.get("s", 1.0)

    def draw(self, ctx, t, scene):
        sp = self.spec
        x = self.xt(t)
        y = sp.get("y", 0) + scene.ground_y(x)
        S = 300 * self.s
        front = (x + self.f * S * 0.42, y - S * 0.06)
        # wet sand in front of the sledge once water has been poured
        wet_from = sp.get("wet_from")
        if wet_from is not None and t >= wet_from:
            k = clamp((t - wet_from) / 1.0)
            _ell(ctx, front[0] + self.f * S * 0.25, y + 3, S * 0.45 * k, S * 0.05 * k)
            ctx.set_source_rgba(0.45, 0.33, 0.2, 0.55); ctx.fill()
        sledge_draw(ctx, x, y, self.s, self.f, sp.get("block", "rough"), t, sp.get("seed", 3))
        # ropes to the pullers' hands
        from .rig import Skeleton
        for pid in sp.get("pullers", []):
            a = scene.actors.get(pid)
            if not a:
                continue
            st = a.state(t)
            J = Skeleton.solve(st["pose"], st["x"], st["y"], a.size, st["f"], st["sx"], st["sy"])
            hand = J["wrist_f"]
            ctx.set_line_width(S * 0.012); ctx.set_line_cap(cairo.LINE_CAP_ROUND); setc(ctx, lc("#c2a36a"))
            mx = (front[0] + hand[0]) / 2
            sag = abs(hand[0] - front[0]) * 0.03
            ctx.move_to(*front); ctx.curve_to(mx, front[1] + sag, mx, hand[1] + sag, hand[0], hand[1]); ctx.stroke()
        # water stream from the pourer's jar
        pid = sp.get("pourer")
        if pid and pid in scene.actors:
            a = scene.actors[pid]
            st = a.state(t)
            if st["act"].get("pose") == "pour_water":
                J = Skeleton.solve(st["pose"], st["x"], st["y"], a.size, st["f"], st["sx"], st["sy"])
                jx, jy = J["wrist_f"][0] + st["f"] * 0.06 * a.size, J["wrist_f"][1] + 0.05 * a.size
                gx, gy = front[0] + self.f * S * 0.25, y
                ctx.set_line_width(S * 0.018); ctx.set_source_rgba(0.6, 0.85, 1.0, 0.85)
                ctx.move_to(jx, jy); ctx.curve_to(jx + (gx - jx) * 0.3, jy + 10, gx, (jy + gy) / 2, gx, gy); ctx.stroke()
                for i in range(6):
                    ph = (t * 2.5 + i / 6) % 1
                    ctx.set_source_rgba(0.7, 0.9, 1.0, 0.8 * (1 - ph))
                    ctx.arc(gx + (i - 3) * S * 0.03 * ph * 2, gy - S * 0.06 * math.sin(ph * math.pi), S * 0.008, 0, TAU); ctx.fill()


# =============================================================== sets
SETS = {
    "nile": dict(ground=("#b89a6a", "#8f7650"), far="#d8c6a0", water=(-150, -20), palms=True),
    "harbor": dict(ground=("#c8b083", "#a08a62"), far="#dccaa2", water=(-140, -40), quay=True, pyramid_mid=True),
    "quarry": dict(ground=("#ddd3bd", "#b9ac90"), far="#e4d6b5", quarry=True),
    "giza": dict(ground=("#d9bd86", "#b8975f"), far="#e2cfa3", pyramid_mid=True, valley=True),
    "ramp": dict(ground=("#d2b47c", "#ad8d58"), far="#e2cfa3", ramp=True),
    "village": dict(ground=("#c5a576", "#a3845a"), far="#e0cca2", village=True, pyramid_far=True),
    "pyramid_top": dict(ground=("#cfb27a", "#a88a58"), far="#e6d2a6", top=True),
    "desert_night": dict(ground=("#a88f68", "#7f6a4c"), far="#b79f78", dunes=True),
    "tent": dict(ground=("#c8ab7c", "#a38758"), far="#e0cca2", tent=True, pyramid_far=True),
}


def ridge(ctx, x0, x1, base, height, seed, freq, col, rough=0.3):
    from .core import fbm1
    ctx.move_to(x0, base + 900)
    n = int((x1 - x0) / 30) + 1
    for i in range(n + 1):
        x = x0 + i * (x1 - x0) / n
        h = height * (0.55 + 0.45 * fbm1(x * freq, seed, 3))
        ctx.line_to(x, base - h)
    ctx.line_to(x1, base + 900); ctx.close_path(); setc(ctx, col); ctx.fill()


def draw_set(ctx, W, H, name, tod, t, cam, seed, opts):
    from .scene import layer, world_to_screen, TOD
    st = SETS[name]
    pal = TOD[tod]
    hz = cmix(pal["haze"], pal["sky"][2], 0.4)
    stage = opts.get("pyramid", 1.0)
    casing = opts.get("casing", 0.0)
    gleam = opts.get("gleam", 0.0)
    # --- far layer: desert hills (+ distant pyramid)
    ctx.save(); layer(ctx, cam, 0.12, W, H)
    cx = cam[0] * 0.12
    drop = 260 if st.get("top") else 0
    ridge(ctx, cx - 2400, cx + 2400, drop, 120 if not st.get("top") else 40, 4 + seed, 0.0016, lc(cmix(st["far"], hz, 0.55)))
    if st.get("pyramid_far") or (name in ("nile",) and opts.get("pyramid_far", True)):
        px = opts.get("pyramid_far_x", 700)
        pyramid(ctx, px, drop + 5, 0.35, t, 1, stage, casing, False, False, gleam * 0.6)
    if st.get("valley") or st.get("top"):
        # green Nile valley strip with the river glinting
        ctx.rectangle(cx - 2400, drop - 6, 4800, 14); setc(ctx, lc(cmix("#6f8a3c", hz, 0.4))); ctx.fill()
        ctx.rectangle(cx - 2400, drop - 1, 4800, 3); setc(ctx, lc(cmix("#7fb3c9", hz, 0.3))); ctx.fill()
    ctx.restore()
    # --- ground plane
    hy = world_to_screen((0, drop), cam, W, H, 0.12)[1]
    g = cairo.LinearGradient(0, hy, 0, H)
    g.add_color_stop_rgba(0, *lc(cmix(st["ground"][0], hz, 0.45)))
    g.add_color_stop_rgba(0.5, *lc(st["ground"][0]))
    g.add_color_stop_rgba(1, *lc(st["ground"][1]))
    ctx.set_source(g); ctx.rectangle(0, hy - 2, W, H - hy + 2); ctx.fill()
    # --- mid layer
    ctx.save(); layer(ctx, cam, 0.45, W, H)
    mx = cam[0] * 0.45
    if st.get("pyramid_mid"):
        pyramid(ctx, opts.get("pyramid_x", 300), opts.get("pyramid_y", 10), opts.get("pyramid_s", 0.8), t, 2, stage, casing,
                opts.get("ramp", stage < 0.95), True, gleam)
    if st.get("dunes"):
        for k in range(3):
            ridge(ctx, mx - 2600, mx + 2600, 30 + k * 25, 90 - k * 20, 20 + k, 0.0025, lc(shade(st["ground"][0], -0.15 + k * 0.08)))
    if st.get("palms") or name in ("harbor", "village"):
        for i in range(-9, 10):
            px = math.floor(mx / 260) * 260 + i * 260 + hrand("pm", i, seed) * 120
            ii = math.floor(px / 260)
            if hrand("palm", ii, seed) > 0.45:
                palm(ctx, px, -40 if name != "village" else -60, 0.42 + 0.12 * hrand("ps", ii), t, ii)
    ctx.restore()
    ctx.save(); layer(ctx, cam, 0.7, W, H)
    m7 = cam[0] * 0.7
    if st.get("quarry"):
        # Tura limestone cliff with cut terraces
        x0, x1 = m7 - 2600, m7 + 2600
        ctx.move_to(x0, 60)
        for i in range(53):
            xx = x0 + i * 100
            ctx.line_to(xx, -520 - 40 * noise1(xx * 0.004, 7) - (60 if (int(xx // 100) % 5 == 0) else 0))
        ctx.line_to(x1, 60); ctx.close_path(); setc(ctx, lc("#eee6d4")); ctx.fill()
        for k in range(4):
            yy = -120 - k * 110
            for j in range(-14, 15):
                bx = math.floor(m7 / 220) * 220 + j * 220 + (k % 2) * 110
                if hrand("q", j, k) > 0.35:
                    ctx.rectangle(bx, yy, 210, 100)
                    setc(ctx, lc(shade("#e8dec8", -0.08 if (j + k) % 2 else 0.04))); ctx.fill()
                    ctx.rectangle(bx, yy + 96, 210, 6); setc(ctx, lc("#c8bba0")); ctx.fill()
            ctx.rectangle(x0, yy + 100, x1 - x0, 10); setc(ctx, lc("#d4c8ae")); ctx.fill()
        ctx.set_line_width(3); setc(ctx, lc("#c3b597"))
        for j in range(-30, 30):
            bx = math.floor(m7 / 90) * 90 + j * 90
            ctx.move_to(bx, -500); ctx.line_to(bx + 12 * noise1(j, 3), -130); ctx.stroke()
    if st.get("village"):
        for i in range(-7, 8):
            hx = math.floor(m7 / 330) * 330 + i * 330
            ii = math.floor(hx / 330)
            mudbrick_house(ctx, hx, 20, 0.85 + 0.25 * hrand("hs", ii), t, ii, 0.8 + 0.5 * hrand("hw", ii))
    if st.get("ramp"):
        pyramid(ctx, opts.get("pyramid_x", 900), 120, opts.get("pyramid_s", 1.6), t, 5, stage, casing, False, False, gleam)
    if st.get("tent"):
        for i in range(-5, 6):
            tx_ = math.floor(m7 / 500) * 500 + i * 500
            tent(ctx, tx_, 30, 0.7, t, i)
    if st.get("dunes"):
        for i in range(-5, 6):
            tx_ = math.floor(m7 / 420) * 420 + i * 420
            if hrand("tn", i) > 0.4:
                tent(ctx, tx_, 40, 0.6, t, i)
    ctx.restore()
    # --- water (world layer)
    if "water" in st:
        ctx.save(); layer(ctx, cam, 1.0, W, H)
        w0, w1 = st["water"]
        x0, x1 = cam[0] - 4000, cam[0] + 4000
        gw = cairo.LinearGradient(0, w0, 0, w1)
        gw.add_color_stop_rgba(0, *lc(cmix("#4f8fae", hz, 0.3)))
        gw.add_color_stop_rgba(1, *lc("#2f6a88"))
        ctx.set_source(gw); ctx.rectangle(x0, w0, x1 - x0, w1 - w0); ctx.fill()
        for i in range(70):
            ph = (t * (0.08 + 0.05 * hrand("sh", i)) + hrand("sx", i)) % 1
            sx = cam[0] - 1500 + ((hrand("wx", i) * 3000 + t * 25) % 3000)
            sy = w0 + 8 + hrand("wy", i) * (w1 - w0 - 16)
            ctx.set_source_rgba(1, 1, 1, 0.35 * math.sin(ph * math.pi))
            ctx.rectangle(sx, sy, 20 + 40 * hrand("wl", i), 2); ctx.fill()
        # bank edge
        ctx.rectangle(x0, w1 - 4, x1 - x0, 10); setc(ctx, lc("#7d6744")); ctx.fill()
        if st.get("quay"):
            for j in range(-20, 21):
                bx = math.floor(cam[0] / 120) * 120 + j * 120
                ctx.rectangle(bx, w1 - 30, 116, 30); setc(ctx, lc("#d9c79c" if j % 2 else "#cdb98b")); ctx.fill()
        for i in range(-10, 11):
            rx = math.floor(cam[0] / 300) * 300 + i * 300 + hrand("rd", i) * 160
            if hrand("rdk", math.floor(rx / 300)) > 0.5 and not st.get("quay"):
                reeds(ctx, rx, w1 + 2, 0.6, t, i)
        ctx.restore()
    # --- ramp surface (world layer)
    if st.get("ramp") and opts.get("slope"):
        sl = opts["slope"]
        ctx.save(); layer(ctx, cam, 1.0, W, H)
        x0, x1, k = sl["x0"], sl["x1"], sl["k"]
        top = k * (x1 - x0)
        # raised causeway: only the wedge between the slope and the ground (sky/pyramid stay visible above)
        ctx.move_to(x0 - 300, 30); ctx.line_to(x0, 0); ctx.line_to(x1, top); ctx.line_to(x1 + 260, top)
        ctx.line_to(x1 + 260 - top * 0.25, 30); ctx.close_path()
        setc(ctx, lc("#a57a50")); ctx.fill()
        ctx.move_to(x0, 0); ctx.line_to(x1, top); ctx.set_line_width(14); setc(ctx, lc("#c39467")); ctx.stroke()
        ctx.set_line_width(6); setc(ctx, lc("#7f5a36"))
        for i in range(0, 30):
            xx = x0 - 300 + i * 90
            yy = k * (clamp(xx, x0, x1) - x0) if xx >= x0 else 0
            ctx.move_to(xx, yy + 4); ctx.line_to(xx + 40, yy + 4 + (k * 40 if x0 <= xx < x1 else 0)); ctx.stroke()
        ctx.restore()
    if st.get("top"):
        ctx.save(); layer(ctx, cam, 1.0, W, H)
        # the top courses of the pyramid we stand on
        ctx.move_to(-900, 0); ctx.line_to(900, 0); ctx.line_to(2600, 1400); ctx.line_to(-2600, 1400); ctx.close_path()
        setc(ctx, lc("#f2ece0" if casing > 0.5 else "#d6bd8c")); ctx.fill()
        ctx.move_to(0, 0); ctx.line_to(900, 0); ctx.line_to(2600, 1400); ctx.line_to(0, 1400); ctx.close_path()
        setc(ctx, lc("#d9d0bf" if casing > 0.5 else "#b99c6a")); ctx.fill()
        ctx.set_line_width(3); setc(ctx, lc("#b9ad97" if casing > 0.5 else "#a88a5a"))
        for i in range(1, 14):
            yy = i * 55
            ctx.move_to(-900 - yy * 1.21, yy); ctx.line_to(900 + yy * 1.21, yy); ctx.stroke()
            for j in range(-12, 13):
                xx = j * 150 + (i % 2) * 75
                ctx.move_to(xx * (1 + yy / 740), yy - 55); ctx.line_to(xx * (1 + yy / 740), yy); ctx.stroke()
        ctx.move_to(0, 0); ctx.line_to(0, 1400); ctx.set_line_width(6); setc(ctx, lc("#a99f8c")); ctx.stroke()
        ctx.restore()


def sun_glare(ctx, W, H, t, x=0.78, y=0.2, amt=1.0):
    sx, sy = W * x, H * y
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for i, (k, r, a) in enumerate(((0.0, 0.35, 0.16), (1.15, 0.03, 0.18), (1.3, 0.05, 0.08))):
        px, py = lerp(sx, W - sx, k), lerp(sy, H - sy, k)
        R = W * r
        g = cairo.RadialGradient(px, py, 0, px, py, R)
        g.add_color_stop_rgba(0, 1, 0.9, 0.6, a * amt * (0.85 + 0.15 * math.sin(t * 2))); g.add_color_stop_rgba(1, 1, 0.9, 0.6, 0)
        ctx.set_source(g); ctx.arc(px, py, R, 0, TAU); ctx.fill()
    ctx.restore()


def heat_shimmer(ctx, W, H, t, amt=1.0):
    """Cheap heat haze: wavering translucent bands near the horizon."""
    for i in range(10):
        y = H * (0.5 + 0.02 * i) + math.sin(t * 3 + i) * 3
        ctx.set_source_rgba(1, 0.95, 0.85, 0.035 * amt)
        ctx.rectangle(0, y, W, 6 + 4 * math.sin(t * 2.3 + i * 1.7)); ctx.fill()


def sand_particles(ctx, W, H, t, amt=1.0):
    for i in range(90):
        ph = (t * (0.12 + 0.1 * hrand("sp", i)) + hrand("spx", i)) % 1
        x = ph * W * 1.3 - W * 0.15
        y = H * (0.35 + 0.65 * hrand("spy", i)) + math.sin(t * 2 + i) * 12
        ctx.set_source_rgba(0.95, 0.85, 0.62, 0.35 * amt * math.sin(ph * math.pi))
        ctx.arc(x, y, 1.2 + 2 * hrand("sps", i), 0, TAU); ctx.fill()
