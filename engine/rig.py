"""Stickman skeletal rig, pose library, expressions and drawing.

Angles are degrees. Limbs: measured from straight-down, positive = toward the
facing direction. Torso: measured from straight-up, positive = lean forward.
Pose key 'y' is a downward root offset in body-heights, 'x' a forward offset.
"""
import math
import cairo
from .core import clamp, lerp, hrand, noise1, setc, shade, TAU

# proportions (fractions of body height)
THIGH, SHIN = 0.235, 0.235
HIP_H = THIGH + SHIN
TORSO = 0.27
NECK = 0.035
HEAD_R = 0.098
UARM, FARM = 0.165, 0.155
FOOT = 0.065

NEUTRAL = dict(x=0.0, y=0.0, rot=0.0, torso=0.0, head=0.0,
               sa_f=8.0, ea_f=10.0, sa_b=-6.0, ea_b=12.0,
               hl_f=4.0, kn_f=-4.0, hl_b=-4.0, kn_b=-4.0, look=0.0)
KEYS = list(NEUTRAL.keys())


def P(**kw):
    d = dict(NEUTRAL)
    d.update(kw)
    return d


def blend(a, b, w):
    return {k: a.get(k, NEUTRAL[k]) + (b.get(k, NEUTRAL[k]) - a.get(k, NEUTRAL[k])) * w for k in KEYS}


# ---------------------------------------------------------------- pose library
# Each pose is fn(t, phase, arg) -> dict.  't' = seconds since action start,
# 'phase' = locomotion phase (radians) supplied by the actor.

def _breath(t, amt=1.0):
    return math.sin(t * TAU / 3.6) * amt


def p_idle(t, ph, a):
    b = _breath(t)
    sway = noise1(t * 0.4, 3) * 3
    return P(torso=2 + b * 1.2, head=-2 + b * 1.5 + noise1(t * .3, 9) * 4, y=0.004 * (1 + b),
             sa_f=8 + b * 2 + sway, ea_f=12 + b * 3, sa_b=-7 - b * 2 - sway, ea_b=14,
             hl_f=4 + sway * .3, hl_b=-4, kn_f=-3, kn_b=-3)


def p_walk(t, ph, a):
    s, c = math.sin(ph), math.cos(ph)
    amp = 26
    return P(torso=5, head=-3 + math.sin(ph * 2) * 2,
             y=0.022 * abs(s) - 0.006,
             hl_f=amp * s, hl_b=-amp * s,
             kn_f=-(6 + 42 * max(0, c)), kn_b=-(6 + 42 * max(0, -c)),
             sa_f=-24 * s + 4, ea_f=18 + 10 * max(0, -s), sa_b=24 * s - 2, ea_b=18 + 10 * max(0, s))


def p_run(t, ph, a):
    s, c = math.sin(ph), math.cos(ph)
    return P(torso=16, head=-10 + math.sin(ph * 2) * 3,
             y=0.045 * abs(s) - 0.02,
             hl_f=44 * s + 8, hl_b=-44 * s + 8,
             kn_f=-(14 + 85 * max(0, c)), kn_b=-(14 + 85 * max(0, -c)),
             sa_f=-48 * s + 10, ea_f=85, sa_b=48 * s + 10, ea_b=85)


def p_sneak(t, ph, a):
    s, c = math.sin(ph), math.cos(ph)
    return P(torso=26 + s * 2, head=-18, y=0.09 + 0.012 * abs(s),
             hl_f=30 * s + 22, hl_b=-30 * s + 22,
             kn_f=-(40 + 40 * max(0, c)), kn_b=-(40 + 40 * max(0, -c)),
             sa_f=60 + 6 * s, ea_f=70, sa_b=40 - 6 * s, ea_b=80)


def p_crouch_hide(t, ph, a):
    sh = math.sin(t * 31) * 1.2  # trembling
    b = _breath(t * 1.8, 1.0)
    return P(torso=34 + b * 2, head=-20 + sh, y=0.24 + b * 0.004,
             hl_f=95, kn_f=-110, hl_b=70, kn_b=-115,
             sa_f=118 + sh, ea_f=88, sa_b=100 - sh, ea_b=96)


def p_crouch(t, ph, a):
    b = _breath(t)
    return P(torso=30 + b, head=-14, y=0.18,
             hl_f=75, kn_f=-90, hl_b=50, kn_b=-95,
             sa_f=46 + b * 2, ea_f=40, sa_b=30, ea_b=50)


def p_point(t, ph, a):
    b = _breath(t)
    jab = math.sin(clamp(t / 0.25) * math.pi) * 6
    return P(torso=6 + jab * .3, head=-6, y=0.004,
             sa_f=96 + jab + b, ea_f=4, sa_b=-10, ea_b=20,
             hl_f=10, hl_b=-8, kn_f=-4, kn_b=-6)


def p_jump_scared(t, ph, a):
    u = clamp(t / 0.42)
    hop = math.sin(u * math.pi) * 0.17
    land = math.exp(-max(0, t - .42) * 8) * 0.05 if t > .42 else 0
    sh = math.sin(t * 40) * 2 * math.exp(-t * 1.5)
    return P(x=-0.18 * min(1, t / .42), y=-hop + land, torso=-14 + sh, head=12,
             sa_f=158 + sh * 2, ea_f=-26, sa_b=-150 - sh * 2, ea_b=26,
             hl_f=22, kn_f=-30 * (1 - u) - 10, hl_b=-26, kn_b=-20)


def p_cover_mouth(t, ph, a):
    heave = max(0, math.sin(t * 7.0)) * 4 * (0.6 + 0.4 * math.sin(t * 1.3))
    return P(torso=-4 + heave, head=8 + heave * 1.2, y=0.01,
             sa_f=88, ea_f=132, sa_b=-12, ea_b=60,
             hl_f=-2, hl_b=8, kn_f=-6, kn_b=-4)


def p_hands_on_head(t, ph, a):
    sh = math.sin(t * 2.4) * 2
    return P(torso=-8, head=-12 + sh, y=0.0,
             sa_f=140, ea_f=100, sa_b=-140, ea_b=-100,
             hl_f=12, hl_b=-12, kn_f=-3, kn_b=-3)


def p_laugh(t, ph, a):
    k = math.sin(t * 15)
    return P(torso=6 + k * 6, head=-22 + k * 7, y=0.012 + k * 0.006,
             sa_f=24, ea_f=96, sa_b=-4, ea_b=100,
             hl_f=8, hl_b=-8, kn_f=-8, kn_b=-8)


def p_sit(t, ph, a):
    b = _breath(t)
    return P(torso=10 + b, head=-6 + noise1(t * .3, 4) * 5, y=HIP_H - 0.06,
             hl_f=135, kn_f=-120, hl_b=125, kn_b=-115,
             sa_f=58 + b * 2, ea_f=34, sa_b=46, ea_b=30)


def p_sleep(t, ph, a):
    b = _breath(t * 0.7, 1.0)
    return P(rot=-86, y=HIP_H - 0.045, torso=4 + b * 2, head=10,
             hl_f=12, kn_f=-24, hl_b=4, kn_b=-14,
             sa_f=24, ea_f=-30, sa_b=10, ea_b=-20)


def p_climb(t, ph, a):
    s = math.sin(t * 4.2)
    return P(torso=14, head=-28, y=0.02,
             sa_f=160 + 14 * s, ea_f=-10 - 15 * s, sa_b=150 - 14 * s, ea_b=-14 + 15 * s,
             hl_f=60 + 30 * max(0, s), kn_f=-90 - 30 * max(0, s), hl_b=10 + 30 * max(0, -s), kn_b=-20 - 50 * max(0, -s))


def p_look_around(t, ph, a):
    b = _breath(t)
    look = math.sin(t * 1.6)
    return P(torso=1 + b, head=-6 + math.sin(t * 0.8) * 8, look=look,
             sa_f=10, ea_f=14, sa_b=-8, ea_b=14, hl_f=5, hl_b=-5, kn_f=-3, kn_b=-3)


def p_wave(t, ph, a):
    w = math.sin(t * 11)
    return P(torso=-2, head=-6, sa_f=150 + 10 * w, ea_f=30 + 22 * w, sa_b=-8, ea_b=14)


def p_shrug(t, ph, a):
    u = clamp(t / .3)
    return P(torso=-2, head=8 * u, y=-0.01 * u, sa_f=40, ea_f=110, sa_b=-40, ea_b=-110)


def p_lean_in(t, ph, a):
    b = _breath(t)
    return P(torso=22 + b, head=-16, y=0.03, sa_f=40, ea_f=60, sa_b=10, ea_b=40, hl_f=12, hl_b=-16, kn_f=-14, kn_b=-6)


def p_amazed(t, ph, a):
    b = _breath(t * 1.4)
    return P(torso=-6 + b, head=-18, sa_f=70 + b * 3, ea_f=40, sa_b=-62, ea_b=-30, hl_f=8, hl_b=-8)


def p_cheer(t, ph, a):
    k = abs(math.sin(t * 6))
    return P(y=-0.05 * k, torso=-6, head=-14, sa_f=165, ea_f=-10, sa_b=-165, ea_b=10, hl_f=10, hl_b=-10, kn_f=-20 * k, kn_b=-20 * k)


def p_check_watch(t, ph, a):
    b = _breath(t)
    return P(torso=10, head=24, sa_f=58 + b, ea_f=96, sa_b=-4, ea_b=14)


def p_tap_watch(t, ph, a):
    tap = max(0, math.sin(t * 9)) * 6
    return P(torso=10, head=22, sa_f=56, ea_f=98, sa_b=40 + tap, ea_b=104 + tap)


def p_sit_chair(t, ph, a):
    b = _breath(t)
    return P(torso=4 + b, head=-4, y=0.2, hl_f=92, kn_f=-92, hl_b=86, kn_b=-86, sa_f=60, ea_f=40, sa_b=50, ea_b=40)


def p_tiptoe(t, ph, a):
    s, c = math.sin(ph), math.cos(ph)
    return P(torso=8, head=-10, y=-0.01, hl_f=22 * s, hl_b=-22 * s,
             kn_f=-(10 + 50 * max(0, c)), kn_b=-(10 + 50 * max(0, -c)),
             sa_f=70, ea_f=80, sa_b=50, ea_b=90)


# era-people task poses ----------------------------------------------------
def p_knap(t, ph, a):
    hit = (t * 1.6 + (a or 0)) % 1.0
    k = math.sin(clamp(hit / 0.55) * math.pi) if hit < .55 else 0
    return P(torso=24, head=-26, y=HIP_H - 0.06,
             hl_f=135, kn_f=-120, hl_b=125, kn_b=-115,
             sa_f=74 + 46 * k, ea_f=40 - 30 * k, sa_b=62, ea_b=40)


def p_cook(t, ph, a):
    s = math.sin(t * 2.0 + (a or 0))
    return P(torso=30, head=-18, y=0.18, hl_f=75, kn_f=-90, hl_b=50, kn_b=-95,
             sa_f=76 + 10 * s, ea_f=20, sa_b=40, ea_b=60)


def p_carry(t, ph, a):
    d = p_walk(t, ph, a)
    d.update(sa_f=150, ea_f=40, sa_b=-150, ea_b=-40, torso=2)
    return d


def p_talk(t, ph, a):
    g = math.sin(t * 3.1 + (a or 0)) * 0.5 + 0.5
    return P(torso=3, head=-4 + math.sin(t * 2.2) * 4, sa_f=30 + 40 * g, ea_f=50 + 30 * g, sa_b=-6, ea_b=14)


def p_throw(t, ph, a):
    u = clamp(t / 0.5)
    w = u * u
    return P(torso=10 - 30 * (1 - w) + 20 * w, head=-12,
             sa_f=lerp(-150, 110, w), ea_f=lerp(-30, 0, w), sa_b=60, ea_b=20,
             hl_f=30, kn_f=-10, hl_b=-24, kn_b=-10)


def p_aim(t, ph, a):
    b = _breath(t)
    return P(torso=10 + b, head=-6, y=0.05, sa_f=-140 + b * 2, ea_f=-40, sa_b=70, ea_b=20,
             hl_f=32, kn_f=-30, hl_b=-26, kn_b=-14)


def p_butcher(t, ph, a):
    k = math.sin(t * 5 + (a or 0))
    return P(torso=48, head=-30, y=0.12, hl_f=40, kn_f=-60, hl_b=-10, kn_b=-50,
             sa_f=70 + 26 * k, ea_f=26, sa_b=58, ea_b=40)


def p_smash(t, ph, a):
    hit = (t * 1.2 + (a or 0)) % 1.0
    up = clamp(hit / .7)
    k = math.sin(up * math.pi * 0.5) if hit < .7 else (1 - clamp((hit - .7) / .08))
    return P(torso=34, head=-26, y=0.18, hl_f=75, kn_f=-90, hl_b=50, kn_b=-95,
             sa_f=60 + 100 * k, ea_f=20 + 30 * k, sa_b=70, ea_b=30)


def p_eat(t, ph, a):
    k = max(0, math.sin(t * 2.6 + (a or 0)))
    return P(torso=10, head=-8 + 6 * k, y=HIP_H - 0.06, hl_f=135, kn_f=-120, hl_b=125, kn_b=-115,
             sa_f=40 + 30 * k, ea_f=90 + 40 * k, sa_b=46, ea_b=30)


def p_watch(t, ph, a):
    b = _breath(t)
    return P(torso=4 + b, head=-6 + noise1(t * .5 + (a or 0), 2) * 8, sa_f=20, ea_f=60, sa_b=-4, ea_b=20, hl_f=6, hl_b=-6)


def p_lookout(t, ph, a):
    b = _breath(t)
    return P(torso=6 + b, head=-10 + math.sin(t * .7) * 6, sa_f=140, ea_f=150, sa_b=-10, ea_b=40, hl_f=10, hl_b=-8)


def p_build(t, ph, a):
    k = math.sin(t * 1.4 + (a or 0))
    return P(torso=40 + 25 * max(0, k), head=-20, y=0.05 + .05 * max(0, k), sa_f=70 + 30 * k, ea_f=30, sa_b=60 + 30 * k, ea_b=30, hl_f=20, kn_f=-30, hl_b=-10, kn_b=-20)


def p_spar(t, ph, a):
    k = math.sin(t * 4 + (a or 0))
    return P(torso=14 + 8 * k, head=-10, y=0.06, sa_f=80 + 40 * k, ea_f=40, sa_b=60, ea_b=60, hl_f=30, kn_f=-30, hl_b=-30, kn_b=-20)


def p_trade(t, ph, a):
    k = clamp(math.sin(t * 1.2 + (a or 0)) * 1.5 + .5)
    return P(torso=10, head=-10, sa_f=40 + 50 * k, ea_f=30 - 20 * k, sa_b=-6, ea_b=14)


def p_dig(t, ph, a):
    k = math.sin(t * 3 + (a or 0))
    return P(torso=55, head=-30, y=0.1, sa_f=50 + 25 * k, ea_f=30, sa_b=46 + 25 * k, ea_b=30, hl_f=30, kn_f=-50, hl_b=-14, kn_b=-30)


def p_tumble(t, ph, a):
    return P(rot=(t * 150) % 360, torso=-10, head=-10, sa_f=130 + 20 * math.sin(t * 5), ea_f=-20,
             sa_b=-130 - 20 * math.sin(t * 5), ea_b=20, hl_f=40, kn_f=-30, hl_b=-35, kn_b=-20)


def p_no(t, ph, a):
    return P(torso=-2, head=-4 + math.sin(t * 2) * 2, look=math.sin(t * 9), sa_f=30, ea_f=110, sa_b=-30, ea_b=-110)


def p_stretch(t, ph, a):
    k = 0.5 + 0.5 * math.sin(t * 1.2)
    return P(torso=-6 * k, head=-20 * k, y=-0.01 * k, sa_f=150 + 20 * k, ea_f=10, sa_b=-150 - 20 * k, ea_b=-10)


def p_lie_awake(t, ph, a):
    d = p_sleep(t, ph, a)
    d["head"] = 2 + math.sin(t * 0.6) * 4
    return d


def p_land(t, ph, a):
    k = math.exp(-t * 5)
    return P(y=0.16 * k, torso=24 * k, head=-10 * k, sa_f=60 * k + 8, ea_f=40 * k + 10, sa_b=-50 * k - 6, ea_b=30 * k,
             hl_f=60 * k + 4, kn_f=-110 * k - 4, hl_b=30 * k - 4, kn_b=-100 * k - 4)


POSES = {
    "idle": p_idle, "walk": p_walk, "run": p_run, "sneak": p_sneak, "crouch_hide": p_crouch_hide,
    "crouch": p_crouch, "point": p_point, "jump_scared": p_jump_scared, "cover_mouth": p_cover_mouth,
    "hands_on_head": p_hands_on_head, "laugh": p_laugh, "sit": p_sit, "sleep": p_sleep,
    "climb": p_climb, "look_around": p_look_around, "wave": p_wave, "shrug": p_shrug,
    "lean_in": p_lean_in, "amazed": p_amazed, "cheer": p_cheer, "check_watch": p_check_watch,
    "tap_watch": p_tap_watch, "sit_chair": p_sit_chair, "tiptoe": p_tiptoe,
    "knap": p_knap, "cook": p_cook, "carry": p_carry, "talk": p_talk, "throw": p_throw, "aim": p_aim,
    "butcher": p_butcher, "smash": p_smash, "eat": p_eat, "watch": p_watch, "lookout": p_lookout,
    "tumble": p_tumble, "no": p_no, "stretch": p_stretch, "lie_awake": p_lie_awake, "land": p_land,
    "build": p_build, "spar": p_spar, "trade": p_trade, "dig": p_dig,
}
LOCOMOTION = {"walk": 0.9, "run": 1.7, "sneak": 0.75, "carry": 0.8, "tiptoe": 0.55}  # body-heights per cycle

# ---------------------------------------------------------------- expressions
# brow: (inner_raise, outer_raise) in head radii; eyes: dot|wide|closed|happy|squint|tiny
# mouth: smile|frown|o|flat|grin|wavy|teeth|smirk ; open 0..1
EXPR = {
    "neutral": dict(brow=(0.0, 0.0), eyes="dot", mouth="flat", open=0.0),
    "happy": dict(brow=(0.05, 0.05), eyes="dot", mouth="smile", open=0.15),
    "laugh": dict(brow=(0.08, 0.04), eyes="happy", mouth="grin", open=0.85),
    "shock": dict(brow=(0.22, 0.16), eyes="wide", mouth="o", open=1.0),
    "scared": dict(brow=(0.2, -0.04), eyes="wide", mouth="teeth", open=0.5),
    "disgust": dict(brow=(-0.1, 0.06), eyes="squint", mouth="wavy", open=0.3),
    "amazed": dict(brow=(0.18, 0.14), eyes="wide", mouth="o", open=0.55),
    "curious": dict(brow=(0.12, -0.02), eyes="dot", mouth="smirk", open=0.0),
    "worried": dict(brow=(0.16, -0.08), eyes="dot", mouth="frown", open=0.1),
    "focused": dict(brow=(-0.08, 0.0), eyes="dot", mouth="flat", open=0.0),
    "sleepy": dict(brow=(-0.02, -0.02), eyes="closed", mouth="flat", open=0.0),
    "sad": dict(brow=(0.14, -0.1), eyes="dot", mouth="frown", open=0.0),
    "grin": dict(brow=(0.06, 0.1), eyes="dot", mouth="grin", open=0.4),
    "determined": dict(brow=(-0.12, 0.02), eyes="dot", mouth="smirk", open=0.0),
}


# ---------------------------------------------------------------- drawing helpers
def _seg(ctx, a, b, w, col, cap=cairo.LINE_CAP_ROUND):
    ctx.set_line_cap(cap)
    ctx.set_line_width(w)
    setc(ctx, col)
    ctx.move_to(*a)
    ctx.line_to(*b)
    ctx.stroke()


def _poly2(ctx, pts, w, col):
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_line_width(w)
    setc(ctx, col)
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.stroke()


def _dir_down(a, f):
    r = math.radians(a)
    return (math.sin(r) * f, math.cos(r))


def _dir_up(a, f):
    r = math.radians(a)
    return (math.sin(r) * f, -math.cos(r))


class Skeleton:
    """Forward kinematics -> joint positions in world space."""

    @staticmethod
    def solve(pose, X, G, s, f, sx=1.0, sy=1.0):
        hip = (X + pose["x"] * s * f, G - (HIP_H - pose["y"]) * s)
        J = {"hip": hip}
        ux, uy = _dir_up(pose["torso"], f)
        neck = (hip[0] + ux * TORSO * s, hip[1] + uy * TORSO * s)
        J["neck"] = neck
        hx, hy = _dir_up(pose["torso"] + pose["head"] * 0.6, f)
        J["head"] = (neck[0] + hx * (NECK + HEAD_R) * s, neck[1] + hy * (NECK + HEAD_R) * s)
        sh = (neck[0] - ux * 0.025 * s, neck[1] - uy * 0.025 * s)
        J["shoulder"] = sh
        for side in ("f", "b"):
            sa, ea = pose["sa_" + side], pose["ea_" + side]
            d1 = _dir_down(sa, f)
            el = (sh[0] + d1[0] * UARM * s, sh[1] + d1[1] * UARM * s)
            d2 = _dir_down(sa + ea, f)
            wr = (el[0] + d2[0] * FARM * s, el[1] + d2[1] * FARM * s)
            J["elbow_" + side], J["wrist_" + side] = el, wr
            J["farm_ang_" + side] = sa + ea
            hl, kn = pose["hl_" + side], pose["kn_" + side]
            d3 = _dir_down(hl, f)
            k = (hip[0] + d3[0] * THIGH * s, hip[1] + d3[1] * THIGH * s)
            d4 = _dir_down(hl + kn, f)
            an = (k[0] + d4[0] * SHIN * s, k[1] + d4[1] * SHIN * s)
            fa = math.radians((hl + kn) * 0.55)
            toe = (an[0] + math.cos(fa) * f * FOOT * s, an[1] - math.sin(fa) * FOOT * s * 0.6)
            J["knee_" + side], J["ankle_" + side], J["toe_" + side] = k, an, toe
        # whole-body rotation around hip
        if abs(pose["rot"]) > 0.01:
            r = math.radians(pose["rot"]) * f
            cr, sr = math.cos(r), math.sin(r)
            for k_, p in list(J.items()):
                if isinstance(p, tuple):
                    dx, dy = p[0] - hip[0], p[1] - hip[1]
                    J[k_] = (hip[0] + dx * cr - dy * sr, hip[1] + dx * sr + dy * cr)
            for side in ("f", "b"):
                J["farm_ang_" + side] += pose["rot"]
        # squash & stretch about the feet base
        if sx != 1.0 or sy != 1.0:
            for k_, p in list(J.items()):
                if isinstance(p, tuple):
                    J[k_] = (X + (p[0] - X) * sx, G + (p[1] - G) * sy)
        J["rot"] = pose["rot"]
        return J


# ---------------------------------------------------------------- face
def draw_face(ctx, c, r, f, expr, blink, mouth_open, look=0.0, ink=(0, 0, 0, 1), rot=0.0, simple=False):
    e = EXPR.get(expr, EXPR["neutral"])
    ctx.save()
    ctx.translate(*c)
    if rot:
        ctx.rotate(math.radians(rot) * f)
    fx = f * 0.26 * r + look * 0.12 * r * f
    ex_sep = 0.27 * r
    ey = -0.08 * r
    eye_r = 0.085 * r
    setc(ctx, ink)
    eyes = e["eyes"]
    for i, side in enumerate((-1, 1)):
        x = fx + side * ex_sep
        y = ey
        # brows
        inner, outer = e["brow"]
        bx0, bx1 = x - side * 0.15 * r * -1, x + side * 0.15 * r
        # inner end is toward centre (fx)
        ix = x - side * 0.14 * r
        ox = x + side * 0.14 * r
        by = y - 0.24 * r
        ctx.set_line_width(0.055 * r)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.move_to(ix, by - inner * r)
        ctx.line_to(ox, by - outer * r)
        ctx.stroke()
        closed = blink > 0.5 or eyes == "closed"
        if closed:
            ctx.set_line_width(0.05 * r)
            ctx.move_to(x - eye_r * 1.3, y)
            ctx.line_to(x + eye_r * 1.3, y)
            ctx.stroke()
        elif eyes == "wide":
            ctx.set_line_width(0.04 * r)
            ctx.arc(x, y, eye_r * 2.0, 0, TAU)
            ctx.stroke()
            ctx.arc(x + look * eye_r * .7 * f, y, eye_r * 0.9, 0, TAU)
            ctx.fill()
        elif eyes == "happy":
            ctx.set_line_width(0.05 * r)
            ctx.arc(x, y + eye_r * .6, eye_r * 1.3, math.pi * 1.1, math.pi * 1.9)
            ctx.stroke()
        elif eyes == "squint":
            ctx.set_line_width(0.05 * r)
            ctx.move_to(x - eye_r * 1.4, y - side * eye_r * 0.5 * 0)
            ctx.line_to(x + eye_r * 1.4, y + eye_r * 0.4)
            ctx.stroke()
        else:
            rr = eye_r * (0.75 if eyes == "tiny" else 1.0)
            ctx.arc(x + look * eye_r * .5 * f, y, rr, 0, TAU)
            ctx.fill()
    # mouth
    m = e["mouth"]
    op = clamp(max(e["open"], mouth_open))
    mx, my = fx, 0.36 * r
    mw = 0.26 * r
    ctx.set_line_width(0.05 * r)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    if m in ("o",) or (op > 0.35 and m in ("flat", "smirk", "frown", "smile")):
        h = 0.08 * r + op * 0.16 * r
        ctx.save()
        ctx.translate(mx, my)
        ctx.scale(0.11 * r + 0.05 * r * op, h)
        ctx.arc(0, 0, 1, 0, TAU)
        ctx.restore()
        ctx.fill()
    elif m == "smile":
        ctx.arc(mx, my - 0.14 * r, mw * 0.9, math.pi * 0.2, math.pi * 0.8)
        ctx.stroke()
    elif m == "frown":
        ctx.arc(mx, my + 0.16 * r, mw * 0.75, math.pi * 1.22, math.pi * 1.78)
        ctx.stroke()
    elif m == "grin":
        h = 0.06 * r + op * 0.16 * r
        ctx.move_to(mx - mw, my - 0.04 * r)
        ctx.curve_to(mx - mw * .6, my + h * 1.6, mx + mw * .6, my + h * 1.6, mx + mw, my - 0.04 * r)
        ctx.close_path()
        ctx.fill()
    elif m == "wavy":
        ctx.move_to(mx - mw, my)
        for i in range(1, 7):
            ctx.line_to(mx - mw + i * mw / 3, my + (0.05 * r if i % 2 else -0.05 * r))
        ctx.stroke()
    elif m == "teeth":
        h = 0.08 * r + op * 0.08 * r
        ctx.rectangle(mx - mw * .9, my - h / 2, mw * 1.8, h)
        ctx.stroke_preserve()
        ctx.fill()
        ctx.set_source_rgba(1, 1, 1, 1)
        ctx.rectangle(mx - mw * .75, my - h / 2 + 0.02 * r, mw * 1.5, h - 0.04 * r)
        ctx.fill()
        setc(ctx, ink)
        ctx.set_line_width(0.025 * r)
        for i in range(1, 4):
            xx = mx - mw * .75 + i * mw * 1.5 / 4
            ctx.move_to(xx, my - h / 2)
            ctx.line_to(xx, my + h / 2)
        ctx.move_to(mx - mw * .75, my)
        ctx.line_to(mx + mw * .75, my)
        ctx.stroke()
    elif m == "smirk":
        ctx.move_to(mx - mw * .8, my)
        ctx.curve_to(mx - mw * .2, my + 0.06 * r, mx + mw * .4, my + 0.03 * r, mx + mw * .9, my - 0.07 * r)
        ctx.stroke()
    else:  # flat
        ctx.move_to(mx - mw * .7, my)
        ctx.line_to(mx + mw * .7, my)
        ctx.stroke()
    ctx.restore()
