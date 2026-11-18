"""Actors: Fardin (the time ghost) and era people, with action tracks.

An actor's track is a list of actions (already resolved to scene seconds):
  {"t": 2.0, "pose": "walk", "to": 400, "dur": 3.0, "ease": "linear",
   "face": 1, "expr": "shock", "pop": true, "hold": "spear", "blend": 0.25,
   "y_to": -80, "watch": 1.0, "alpha": 1.0}
Everything is evaluated as a pure function of time.
"""
import math
import cairo
from .core import Track, clamp, lerp, ease, hrand, noise1, setc, shade, hexc, TAU, out_back
from .rig import (POSES, LOCOMOTION, Skeleton, blend, draw_face, HEAD_R, NEUTRAL, _seg, _poly2,
                  HIP_H, TORSO)

GHOST = (0.55, 0.88, 1.0)
WATCH = (0.25, 0.95, 1.0)
HOODIE = "#ff2a2a"
HOODIE_D = "#c3121b"
INK = (0.05, 0.05, 0.07, 1)


def pop_scale(dt):
    """Squash & stretch after a reaction pop; returns (sx, sy)."""
    if dt < 0 or dt > 1.2:
        return 1.0, 1.0
    sy = 1 - 0.17 * math.exp(-5.5 * dt) * math.cos(dt * 19)
    sx = 1 / (sy ** 0.7)
    return sx, sy


class Actor:
    kind = "base"

    def __init__(self, spec, seed=0):
        self.spec = spec
        self.id = spec.get("id", "actor")
        self.size = spec.get("size", 300)
        self.seed = seed
        self.layer = spec.get("layer", 0)
        acts = sorted(spec.get("track", [{"t": 0, "pose": "idle"}]), key=lambda a: a["t"])
        if acts[0]["t"] > 0:
            acts.insert(0, dict(acts[0], t=0))
        self.acts = acts
        x = spec.get("x", 0.0)
        y = spec.get("y", 0.0)
        f = spec.get("facing", 1)
        a = spec.get("alpha", 1.0)
        xk, yk, ak = [(0, x)], [(0, y)], [(0, a)]
        expr, hold, watch = spec.get("expr", "neutral"), spec.get("hold"), spec.get("watch", 0.25)
        wk = [(0, watch)]
        for act in acts:
            t = act["t"]
            d = act.get("dur", 1.0)
            if "to" in act:
                xk.append((t, x))
                if "face" not in act and act["to"] != x:
                    act["face"] = 1 if act["to"] > x else -1
                x = act["to"]
                xk.append((t + d, x, act.get("ease", "inOutSine")))
            if "y_to" in act:
                yk.append((t, y))
                y = act["y_to"]
                yk.append((t + d, y, act.get("ease", "inOutSine")))
            if "alpha" in act:
                ak.append((t, a))
                a = act["alpha"]
                ak.append((t + act.get("fade", 0.4), a, "inOutSine"))
            if "watch" in act:
                wk.append((t, watch))
                watch = act["watch"]
                wk.append((t + act.get("wdur", 0.5), watch, "inOutSine"))
            if "face" in act:
                f = act["face"]
            act["_face"] = f
            if "expr" in act:
                expr = act["expr"]
            act["_expr"] = expr
            if "hold" in act:
                hold = act["hold"]
            act["_hold"] = hold
        self.xt, self.yt, self.at, self.wt = Track(xk), Track(yk), Track(ak), Track(wk)
        self.says = spec.get("say", [])
        self.talks = [(s["t"], s["t"] + s.get("dur", 1.2)) for s in self.says]
        self.pops = [a["t"] for a in acts if a.get("pop")]

    # ------------------------------------------------------------ state
    def _act_index(self, t):
        i = 0
        for j, a in enumerate(self.acts):
            if a["t"] <= t:
                i = j
        return i

    def _phase(self, act, t):
        name = act.get("pose", "idle")
        if name in LOCOMOTION:
            x0 = self.xt(act["t"])
            dist = abs(self.xt(t) - x0) + abs(self.yt(t) - self.yt(act["t"])) * 0.5
            if dist > 1:
                return dist / (LOCOMOTION[name] * self.size) * TAU + self.seed
            rate = {"run": 2.6, "walk": 1.6}.get(name, 1.3) * act.get("inplace", 0)
            return (t - act["t"]) * TAU * rate + self.seed
        return 0.0

    def pose_at(self, t):
        i = self._act_index(t)
        act = self.acts[i]
        fn = POSES.get(act.get("pose", "idle"), POSES["idle"])
        lt = t - act["t"] + self.seed * 0.37
        cur = fn(lt, self._phase(act, t), act.get("arg"))
        if i > 0:
            bl = act.get("blend", 0.14 if act.get("pop") else 0.3)
            u = (t - act["t"]) / bl
            if u < 1:
                pa = self.acts[i - 1]
                pfn = POSES.get(pa.get("pose", "idle"), POSES["idle"])
                prev = pfn(t - pa["t"] + self.seed * 0.37, self._phase(pa, t), pa.get("arg"))
                w = out_back(clamp(u), 1.9 if act.get("pop") else 1.2)
                cur = blend(prev, cur, w)
        return cur, act

    def state(self, t):
        pose, act = self.pose_at(t)
        sx, sy = 1.0, 1.0
        for p in self.pops:
            if 0 <= t - p < 1.2:
                sx, sy = pop_scale(t - p)
        x = self.xt(t)
        y = self.yt(t) + (self.ground_fn(x) if getattr(self, "ground_fn", None) else 0.0)
        return dict(t=t, pose=pose, act=act, x=x, y=y, f=act["_face"],
                    expr=act["_expr"], hold=act["_hold"], sx=sx, sy=sy, alpha=self.at(t), watch=self.wt(t))

    def blink(self, t):
        period = 3.4 + hrand(self.id, "bp") * 1.6
        k = math.floor((t + hrand(self.id, "bo") * period) / period)
        tb = k * period + hrand(self.id, k) * 1.2 - hrand(self.id, "bo") * period
        d = t - tb
        return 1.0 if 0 <= d < 0.13 else 0.0

    def mouth(self, t):
        for a, b in self.talks:
            if a <= t <= b:
                return 0.25 + 0.75 * abs(math.sin((t - a) * 17 + noise1(t * 6, 5) * 2))
        return 0.0

    def screen_head(self, t):
        st = self.state(t)  # includes ramp slope
        J = Skeleton.solve(st["pose"], st["x"], st["y"], self.size, st["f"], st["sx"], st["sy"])
        return J["head"]

    # ------------------------------------------------------------ drawing
    def draw(self, ctx, t, light=None):
        st = self.state(t)
        if st["alpha"] <= 0.01:
            return
        J = Skeleton.solve(st["pose"], st["x"], st["y"], self.size, st["f"], st["sx"], st["sy"])
        self._shadow(ctx, st, J)
        self.render(ctx, t, st, J)
        for s in self.says:
            if s["t"] - 0.05 <= t <= s["t"] + s.get("dur", 1.2) + 0.5:
                draw_bubble(ctx, J["head"], self.size, st["f"], s["text"], t - s["t"], s.get("dur", 1.2))

    def _shadow(self, ctx, st, J, a=0.22):
        g = st["y"]
        lift = max(0, g - min(J["ankle_f"][1], J["ankle_b"][1]))
        w = self.size * 0.16 * (1 - min(0.5, lift / self.size))
        ctx.save()
        ctx.translate(J["hip"][0], g + 2)
        ctx.scale(w, w * 0.16)
        ctx.arc(0, 0, 1, 0, TAU)
        ctx.restore()
        ctx.set_source_rgba(0, 0, 0, a * st["alpha"])
        ctx.fill()

    def render(self, ctx, t, st, J):
        pass


# ===================================================================== Fardin
class Fardin(Actor):
    kind = "fardin"

    def __init__(self, spec, seed=0):
        super().__init__(spec, seed)
        self.ghost = spec.get("ghost", True)

    def _shadow(self, ctx, st, J, a=0.22):
        super()._shadow(ctx, st, J, 0.12 if self.ghost else 0.22)

    def skeleton_paths(self, J):
        return [
            [J["hip"], J["neck"]],
            [J["shoulder"], J["elbow_f"], J["wrist_f"]],
            [J["shoulder"], J["elbow_b"], J["wrist_b"]],
            [J["hip"], J["knee_f"], J["ankle_f"], J["toe_f"]],
            [J["hip"], J["knee_b"], J["ankle_b"], J["toe_b"]],
        ]

    def render(self, ctx, t, st, J):
        s = self.size
        A = st["alpha"]
        if self.ghost:
            pulse = 0.82 + 0.18 * math.sin(t * 2.7)
            r = HEAD_R * s
            for w, a in ((0.20, 0.05), (0.13, 0.09), (0.085, 0.16), (0.055, 0.30)):
                ctx.set_source_rgba(*GHOST, a * pulse * A)
                ctx.set_line_width(w * s)
                ctx.set_line_cap(cairo.LINE_CAP_ROUND)
                ctx.set_line_join(cairo.LINE_JOIN_ROUND)
                for path in self.skeleton_paths(J):
                    ctx.move_to(*path[0])
                    for p in path[1:]:
                        ctx.line_to(*p)
                    ctx.stroke()
                # hoodie body + head
                ctx.set_line_width(w * s + 0.12 * s)
                ctx.move_to(*J["hip"]); ctx.line_to(*J["neck"]); ctx.stroke()
                ctx.arc(J["head"][0], J["head"][1], r + w * s * 0.5, 0, TAU)
                ctx.fill()
            # drifting ghost sparks
            for i in range(6):
                ph = (t * 0.35 + hrand(self.id, "sp", i)) % 1.0
                ang = hrand(self.id, "sa", i) * TAU
                rad = s * (0.18 + 0.2 * hrand(self.id, "sr", i))
                px = J["hip"][0] + math.cos(ang) * rad
                py = J["hip"][1] - s * 0.15 - ph * s * 0.5 + math.sin(ang) * rad * .5
                ctx.set_source_rgba(*GHOST, 0.55 * math.sin(ph * math.pi) * A)
                ctx.arc(px, py, s * 0.008 * (1 + hrand(self.id, "sz", i)), 0, TAU)
                ctx.fill()
        body_alpha = (0.9 if self.ghost else 1.0) * A
        x0, y0 = J["hip"][0] - s, J["hip"][1] - s * 1.0
        ctx.save()
        ctx.rectangle(x0, y0, s * 2, s * 1.9)
        ctx.clip()
        ctx.push_group()
        self._body(ctx, t, st, J)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(body_alpha)
        ctx.restore()
        # watch glow on top (unaffected by ghost alpha)
        wr, el = J["wrist_f"], J["elbow_f"]
        wp = (lerp(el[0], wr[0], 0.8), lerp(el[1], wr[1], 0.8))
        g = st["watch"]
        rad = s * (0.04 + 0.11 * min(g, 2.0))
        pat = cairo.RadialGradient(wp[0], wp[1], 0, wp[0], wp[1], rad)
        pat.add_color_stop_rgba(0, *WATCH, min(0.85, 0.5 * (0.5 + g)) * A)
        pat.add_color_stop_rgba(1, *WATCH, 0)
        ctx.set_source(pat)
        ctx.arc(wp[0], wp[1], rad, 0, TAU)
        ctx.fill()

    def _limb_leg(self, ctx, J, side, s, dark=False):
        col = (0.12, 0.12, 0.16, 1) if not dark else (0.03, 0.03, 0.05, 1)
        _poly2(ctx, [J["hip"], J["knee_" + side], J["ankle_" + side]], 0.05 * s, col)
        # sneaker
        an, toe = J["ankle_" + side], J["toe_" + side]
        dx, dy = toe[0] - an[0], toe[1] - an[1]
        ln = math.hypot(dx, dy) or 1
        heel = (an[0] - dx / ln * 0.022 * s, an[1] - dy / ln * 0.022 * s)
        tip = (toe[0] + dx / ln * 0.012 * s, toe[1] + dy / ln * 0.012 * s)
        _seg(ctx, heel, tip, 0.06 * s, INK)
        _seg(ctx, heel, tip, 0.042 * s, (0.97, 0.97, 0.97, 1) if not dark else (0.85, 0.85, 0.88, 1))
        _seg(ctx, (heel[0], heel[1] + 0.016 * s), (tip[0], tip[1] + 0.016 * s), 0.012 * s, (0.6, 0.6, 0.65, 1))

    def _limb_arm(self, ctx, J, side, s, dark=False, watch=False):
        sh, el, wr = J["shoulder"], J["elbow_" + side], J["wrist_" + side]
        red = hexc(HOODIE_D) if dark else hexc(HOODIE)
        cuff = (lerp(el[0], wr[0], 0.86), lerp(el[1], wr[1], 0.86))
        _poly2(ctx, [sh, el, cuff], 0.088 * s, INK)
        _poly2(ctx, [sh, el, cuff], 0.07 * s, red)
        _seg(ctx, cuff, wr, 0.04 * s, INK)
        ctx.arc(wr[0], wr[1], 0.03 * s, 0, TAU)
        setc(ctx, INK)
        ctx.fill()
        if watch:
            wp = (lerp(el[0], wr[0], 0.8), lerp(el[1], wr[1], 0.8))
            ctx.arc(wp[0], wp[1], 0.026 * s, 0, TAU)
            setc(ctx, INK); ctx.fill()
            ctx.arc(wp[0], wp[1], 0.018 * s, 0, TAU)
            ctx.set_source_rgba(*WATCH, 1); ctx.fill()

    def _body(self, ctx, t, st, J):
        s, f = self.size, st["f"]
        hold = st["hold"]
        self._limb_arm(ctx, J, "b", s, dark=True)
        if hold:
            draw_item(ctx, hold, J, "b", s, st, back=True)
        self._limb_leg(ctx, J, "b", s, dark=True)
        # hoodie torso
        hip, neck = J["hip"], J["neck"]
        ax, ay = neck[0] - hip[0], neck[1] - hip[1]
        ln = math.hypot(ax, ay) or 1
        ux, uy = ax / ln, ay / ln
        nx, ny = -uy, ux
        vel = (self.xt(t) - self.xt(t - 0.12)) / 0.12
        sway = clamp(-vel / 900, -1, 1) * 0.05 * s + math.sin(t * 3.3) * 0.006 * s
        hem = (hip[0] - ux * 0.06 * s, hip[1] - uy * 0.06 * s)
        sw = 0.07 * s
        bw = 0.083 * s
        pts = [(neck[0] + nx * sw, neck[1] + ny * sw),
               (hem[0] + nx * bw + sway, hem[1] + ny * bw),
               (hem[0] - nx * bw + sway, hem[1] - ny * bw),
               (neck[0] - nx * sw, neck[1] - ny * sw)]
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.move_to(*pts[0])
        ctx.curve_to(pts[0][0] + nx * 0.02 * s, pts[0][1] + ny * .02 * s, pts[1][0], pts[1][1] - 0.04 * s, *pts[1])
        ctx.line_to(*pts[2])
        ctx.curve_to(pts[2][0], pts[2][1] - 0.04 * s, pts[3][0] - nx * .02 * s, pts[3][1] - ny * .02 * s, *pts[3])
        ctx.close_path()
        setc(ctx, HOODIE)
        ctx.fill_preserve()
        ctx.set_line_width(0.016 * s)
        setc(ctx, INK)
        ctx.stroke()
        # kangaroo pocket (front side) + hem band
        pc = (lerp(hem[0], neck[0], 0.22) + sway * .5, lerp(hem[1], neck[1], 0.22))
        fx = f
        ctx.save()
        ctx.translate(*pc)
        ctx.rotate(math.atan2(uy, ux) + math.pi / 2)
        ctx.rectangle(-0.05 * s, -0.025 * s, 0.1 * s, 0.05 * s)
        ctx.restore()
        setc(ctx, HOODIE_D)
        ctx.fill()
        _seg(ctx, (hem[0] + nx * bw * .95 + sway, hem[1] + ny * bw * .95), (hem[0] - nx * bw * .95 + sway, hem[1] - ny * bw * .95), 0.022 * s, HOODIE_D, cairo.LINE_CAP_BUTT)
        self._limb_leg(ctx, J, "f", s)
        # hood behind head
        hc = J["head"]
        r = HEAD_R * s
        ctx.arc(hc[0] - f * 0.035 * s, hc[1] + 0.012 * s, r * 1.13, 0, TAU)
        setc(ctx, HOODIE_D)
        ctx.fill_preserve()
        ctx.set_line_width(0.014 * s)
        setc(ctx, INK)
        ctx.stroke()
        # drawstrings
        for k in (-1, 1):
            p0 = (neck[0] + f * 0.02 * s + k * 0.012 * s, neck[1] + 0.005 * s)
            _seg(ctx, p0, (p0[0] + f * 0.004 * s, p0[1] + 0.07 * s), 0.008 * s, (1, 1, 1, 1))
        # head
        ctx.arc(hc[0], hc[1], r, 0, TAU)
        ctx.set_source_rgba(1, 1, 1, 1)
        ctx.fill_preserve()
        ctx.set_line_width(0.017 * s)
        setc(ctx, INK)
        ctx.stroke()
        draw_face(ctx, hc, r, f, st["expr"], self.blink(t), self.mouth(t), st["pose"].get("look", 0), INK,
                  rot=J.get("rot", 0) + st["pose"]["head"] * 0.3)
        self._limb_arm(ctx, J, "f", s, watch=True)
        if hold:
            draw_item(ctx, hold, J, "f", s, st)


# ===================================================================== Era person
SKINS = ["#6b4430", "#7a4e35", "#5a3826", "#8a5a3c", "#4d3022", "#6f4a33"]
HIDES = ["#8b6a45", "#9c7a50", "#7a5a3a", "#a5845a", "#6e5235", "#94704a"]
LIMB = (0.16, 0.10, 0.07, 1)


class EraPerson(Actor):
    kind = "era"

    def __init__(self, spec, seed=0):
        super().__init__(spec, seed)
        r = lambda k: hrand(self.id, k, seed)
        self.skin = spec.get("skin", SKINS[int(r("skin") * len(SKINS))])
        self.hide = spec.get("hide", HIDES[int(r("hide") * len(HIDES))])
        self.hair = spec.get("hair", ["curls", "short", "long", "curls", "bun"][int(r("hair") * 5)])
        self.beard = spec.get("beard", r("beard") > 0.6)
        self.wrap = spec.get("wrap", ["skirt", "skirt", "cape", "sash"][int(r("wrap") * 4)])
        self.paint = spec.get("paint", r("paint") > 0.75)

    def render(self, ctx, t, st, J):
        s, f = self.size, st["f"]
        A = st["alpha"]
        if A < 0.999:
            ctx.push_group()
        light = 0.82
        limb_b = shade(LIMB, -0.3)
        _poly2(ctx, [J["shoulder"], J["elbow_b"], J["wrist_b"]], 0.042 * s, limb_b)
        if st["hold"]:
            draw_item(ctx, st["hold"], J, "b", s, st, back=True)
        _poly2(ctx, [J["hip"], J["knee_b"], J["ankle_b"], J["toe_b"]], 0.045 * s, limb_b)
        _poly2(ctx, [J["hip"], J["neck"]], 0.05 * s, LIMB)
        _poly2(ctx, [J["hip"], J["knee_f"], J["ankle_f"], J["toe_f"]], 0.045 * s, LIMB)
        self._wrap(ctx, t, st, J)
        hc = J["head"]
        r = HEAD_R * s
        self._hair(ctx, hc, r, f, back=True)
        ctx.arc(hc[0], hc[1], r, 0, TAU)
        setc(ctx, self.skin)
        ctx.fill_preserve()
        ctx.set_line_width(0.014 * s)
        setc(ctx, shade(self.skin, -0.5))
        ctx.stroke()
        self._hair(ctx, hc, r, f, back=False)
        # heavier brow ridge (archaic feature)
        ink = (0.07, 0.04, 0.03, 1)
        hr = J.get("rot", 0) + st["pose"]["head"] * 0.3
        draw_face(ctx, hc, r, f, st["expr"], self.blink(t), self.mouth(t), st["pose"].get("look", 0), ink, rot=hr)
        ctx.save()
        ctx.translate(*hc)
        ctx.rotate(math.radians(hr) * f)
        _seg(ctx, (f * 0.02 * r, -0.33 * r), (f * 0.72 * r, -0.36 * r), 0.07 * r, shade(self.skin, -0.35))
        if self.beard:
            ctx.arc(f * 0.25 * r, 0.25 * r, r * 0.62, math.radians(20), math.radians(160))
            ctx.set_line_width(0.14 * r)
            ctx.set_source_rgba(0.1, 0.07, 0.05, 1)
            ctx.stroke()
        if self.paint:
            _seg(ctx, (f * 0.45 * r, 0.05 * r), (f * 0.75 * r, 0.05 * r), 0.06 * r, (0.72, 0.22, 0.12, 1))
        ctx.restore()
        _poly2(ctx, [J["shoulder"], J["elbow_f"], J["wrist_f"]], 0.042 * s, LIMB)
        ctx.arc(J["wrist_f"][0], J["wrist_f"][1], 0.024 * s, 0, TAU)
        setc(ctx, LIMB)
        ctx.fill()
        if st["hold"]:
            draw_item(ctx, st["hold"], J, "f", s, st)
        if A < 0.999:
            ctx.pop_group_to_source()
            ctx.paint_with_alpha(A)

    def _wrap(self, ctx, t, st, J):
        s = self.size
        hip, neck = J["hip"], J["neck"]
        ax, ay = neck[0] - hip[0], neck[1] - hip[1]
        ln = math.hypot(ax, ay) or 1
        ux, uy = ax / ln, ay / ln
        nx, ny = -uy, ux
        top = (hip[0] + ux * 0.07 * s, hip[1] + uy * 0.07 * s)
        bot = (hip[0] - ux * 0.11 * s, hip[1] - uy * 0.11 * s)
        sway = math.sin(t * 3 + self.seed) * 0.008 * s
        w0, w1 = 0.05 * s, 0.075 * s
        ctx.move_to(top[0] + nx * w0, top[1] + ny * w0)
        ctx.line_to(bot[0] + nx * w1 + sway, bot[1] + ny * w1)
        # ragged hem
        for i in range(1, 5):
            k = i / 5
            px = lerp(bot[0] + nx * w1, bot[0] - nx * w1, k) + sway
            py = lerp(bot[1] + ny * w1, bot[1] - ny * w1, k) + (0.018 * s if i % 2 else 0)
            ctx.line_to(px, py)
        ctx.line_to(bot[0] - nx * w1 + sway, bot[1] - ny * w1)
        ctx.line_to(top[0] - nx * w0, top[1] - ny * w0)
        ctx.close_path()
        setc(ctx, self.hide)
        ctx.fill_preserve()
        ctx.set_line_width(0.01 * s)
        setc(ctx, shade(self.hide, -0.45))
        ctx.stroke()
        if self.wrap in ("cape", "sash"):
            sh = J["shoulder"]
            if self.wrap == "cape":
                p1 = (sh[0] - st["f"] * 0.05 * s, sh[1] - 0.01 * s)
                p2 = (lerp(sh[0], hip[0], 0.75) - st["f"] * 0.07 * s, lerp(sh[1], hip[1], 0.75))
                p3 = (lerp(sh[0], hip[0], 0.6) + st["f"] * 0.03 * s, lerp(sh[1], hip[1], 0.6))
                ctx.move_to(*p1); ctx.line_to(*p2); ctx.line_to(*p3); ctx.close_path()
            else:
                p1 = (sh[0] + nx * 0.03 * s, sh[1] + ny * .03 * s)
                p2 = (top[0] - nx * 0.04 * s, top[1] - ny * 0.04 * s)
                ctx.set_line_width(0.035 * s)
                ctx.move_to(*p1); ctx.line_to(*p2)
                setc(ctx, shade(self.hide, -0.15))
                ctx.stroke()
                return
            setc(ctx, shade(self.hide, -0.12))
            ctx.fill_preserve()
            setc(ctx, shade(self.hide, -0.45))
            ctx.stroke()

    def _hair(self, ctx, hc, r, f, back):
        dark = (0.09, 0.06, 0.05, 1)
        setc(ctx, dark)
        if self.hair == "curls":
            if back:
                return
            for i in range(9):
                a = math.radians(-160 + i * 17) if f > 0 else math.radians(-20 - i * 17)
                ctx.arc(hc[0] + math.cos(a) * r * 0.86 - f * r * 0.06, hc[1] + math.sin(a) * r * 0.86, r * 0.27, 0, TAU)
                ctx.fill()
        elif self.hair == "short":
            if back:
                return
            ctx.arc(hc[0] - f * 0.05 * r, hc[1] - 0.05 * r, r * 1.05, math.pi * 1.02, math.pi * 1.98)
            ctx.fill()
        elif self.hair == "long":
            if back:
                ctx.move_to(hc[0] - f * r * 0.2, hc[1] - r * 1.02)
                ctx.curve_to(hc[0] - f * r * 1.4, hc[1] - r * .6, hc[0] - f * r * 1.3, hc[1] + r * 1.0, hc[0] - f * r * 0.7, hc[1] + r * 1.5)
                ctx.line_to(hc[0] - f * r * 0.1, hc[1] + r * 0.4)
                ctx.close_path()
                ctx.fill()
            else:
                ctx.arc(hc[0] - f * 0.08 * r, hc[1] - 0.06 * r, r * 1.04, math.pi * 1.05, math.pi * 1.95)
                ctx.fill()
        elif self.hair == "bun":
            if back:
                ctx.arc(hc[0] - f * r * 0.85, hc[1] - r * 0.55, r * 0.42, 0, TAU)
                ctx.fill()
            else:
                ctx.arc(hc[0] - f * 0.05 * r, hc[1] - 0.05 * r, r * 1.04, math.pi * 1.05, math.pi * 1.95)
                ctx.fill()


# ===================================================================== items
def draw_item(ctx, item, J, side, s, st, back=False):
    from .egypt import draw_egypt_item
    if draw_egypt_item(ctx, item, J, side, s, st):
        return
    wr, el = J["wrist_" + side], J["elbow_" + side]
    fa = J["farm_ang_" + side]
    f = st["f"]
    dx, dy = wr[0] - el[0], wr[1] - el[1]
    ln = math.hypot(dx, dy) or 1
    dx, dy = dx / ln, dy / ln
    if item == "spear" and side == "f":
        raised = st["act"].get("pose") in ("aim", "throw")
        if raised:
            vx, vy = dx, dy
            if st["act"].get("pose") == "aim":
                vx, vy = f * 0.98, -0.2
        else:
            ang = math.radians(8) * f
            vx, vy = math.sin(ang), -math.cos(ang)
        L = s * 0.95
        a = (wr[0] - vx * L * 0.35, wr[1] - vy * L * 0.35)
        b = (wr[0] + vx * L * 0.65, wr[1] + vy * L * 0.65)
        _seg(ctx, a, b, 0.022 * s, (0.42, 0.28, 0.14, 1))
        nx, ny = -vy, vx
        tip = (b[0] + vx * 0.09 * s, b[1] + vy * 0.09 * s)
        ctx.move_to(*tip)
        ctx.line_to(b[0] + nx * 0.03 * s, b[1] + ny * 0.03 * s)
        ctx.line_to(b[0] - vx * .02 * s, b[1] - vy * .02 * s)
        ctx.line_to(b[0] - nx * 0.03 * s, b[1] - ny * 0.03 * s)
        ctx.close_path()
        ctx.set_source_rgba(0.55, 0.55, 0.52, 1)
        ctx.fill_preserve()
        ctx.set_line_width(0.006 * s)
        ctx.set_source_rgba(0.2, 0.2, 0.2, 1)
        ctx.stroke()
        _seg(ctx, (b[0] - vx * .02 * s, b[1] - vy * .02 * s), (b[0] - vx * .06 * s, b[1] - vy * .06 * s), 0.03 * s, (0.3, 0.2, 0.1, 1))
    elif item in ("stone", "hammerstone") and side == "f":
        ctx.save(); ctx.translate(wr[0] + dx * 0.02 * s, wr[1] + dy * 0.02 * s)
        ctx.scale(0.045 * s, 0.034 * s); ctx.arc(0, 0, 1, 0, TAU); ctx.restore()
        ctx.set_source_rgba(0.5, 0.48, 0.44, 1); ctx.fill()
    elif item in ("flake", "core") and side in ("b", "f"):
        if (item == "core") != (side == "b"):
            return
        c = (wr[0] + dx * 0.02 * s, wr[1] + dy * .02 * s)
        ctx.move_to(c[0] - 0.035 * s, c[1]); ctx.line_to(c[0], c[1] - 0.04 * s); ctx.line_to(c[0] + 0.04 * s, c[1] + 0.01 * s); ctx.line_to(c[0], c[1] + 0.03 * s)
        ctx.close_path(); ctx.set_source_rgba(0.62, 0.58, 0.5, 1); ctx.fill_preserve()
        ctx.set_line_width(0.005 * s); ctx.set_source_rgba(0.25, 0.22, 0.2, 1); ctx.stroke()
    elif item == "bone" and side == "f":
        a = (wr[0] - dy * 0.06 * s, wr[1] + dx * 0.06 * s)
        b = (wr[0] + dy * 0.06 * s, wr[1] - dx * 0.06 * s)
        _seg(ctx, a, b, 0.02 * s, (0.93, 0.9, 0.8, 1))
        for p in (a, b):
            ctx.arc(p[0], p[1], 0.017 * s, 0, TAU); ctx.set_source_rgba(0.93, 0.9, 0.8, 1); ctx.fill()
    elif item == "meat" and side == "f":
        ctx.save(); ctx.translate(wr[0], wr[1] + 0.01 * s); ctx.scale(0.05 * s, 0.035 * s); ctx.arc(0, 0, 1, 0, TAU); ctx.restore()
        ctx.set_source_rgba(0.6, 0.18, 0.14, 1); ctx.fill()
    elif item == "torch" and side == "f":
        top = (wr[0] + 0.01 * s * f, wr[1] - 0.25 * s)
        _seg(ctx, (wr[0], wr[1] + 0.05 * s), top, 0.022 * s, (0.4, 0.26, 0.12, 1))
        from .props import flame
        flame(ctx, top[0], top[1], 0.12 * s, st.get("t", 0) if isinstance(st, dict) else 0)
    elif item == "grass" and (side == "f" or side == "b"):
        for i in range(7):
            a = math.radians(-60 + i * 20)
            ctx.move_to(wr[0], wr[1]); ctx.line_to(wr[0] + math.sin(a) * 0.12 * s, wr[1] - math.cos(a) * 0.12 * s)
        ctx.set_line_width(0.008 * s); ctx.set_source_rgba(0.75, 0.68, 0.32, 1); ctx.stroke()


# ===================================================================== speech bubble
def draw_bubble(ctx, head, s, f, text, lt, dur):
    if lt < 0:
        return
    k = out_back(clamp(lt / 0.25), 2.2) if lt < dur else 1 - clamp((lt - dur) / 0.3)
    if k <= 0.01:
        return
    fs = max(26, s * 0.12)
    ctx.select_font_face("Inter Display", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(fs)
    ext = ctx.text_extents(text)
    w, h = ext.width + fs * 1.3, fs * 1.7
    cx = head[0] + f * (s * 0.05 + w * 0.5 + s * 0.1)
    cy = head[1] - s * 0.33
    ctx.save()
    ctx.translate(head[0] + f * s * 0.12, head[1] - s * 0.15)
    ctx.scale(k, k)
    ctx.translate(-(head[0] + f * s * 0.12), -(head[1] - s * 0.15))
    rr = h * 0.45
    x0, y0 = cx - w / 2, cy - h / 2
    ctx.new_sub_path()
    ctx.arc(x0 + w - rr, y0 + rr, rr, -math.pi / 2, 0)
    ctx.arc(x0 + w - rr, y0 + h - rr, rr, 0, math.pi / 2)
    ctx.arc(x0 + rr, y0 + h - rr, rr, math.pi / 2, math.pi)
    ctx.arc(x0 + rr, y0 + rr, rr, math.pi, 1.5 * math.pi)
    ctx.close_path()
    ctx.set_source_rgba(1, 1, 1, 0.96)
    ctx.fill_preserve()
    ctx.set_line_width(4)
    setc(ctx, INK)
    ctx.stroke()
    # tail
    tx = cx - f * w * 0.3
    ctx.move_to(tx - 12, y0 + h - 2)
    ctx.line_to(head[0] + f * s * 0.12, head[1] - s * 0.12)
    ctx.line_to(tx + 12, y0 + h - 2)
    ctx.close_path()
    ctx.set_source_rgba(1, 1, 1, 0.96)
    ctx.fill_preserve()
    setc(ctx, INK)
    ctx.stroke()
    ctx.move_to(cx - ext.width / 2 - ext.x_bearing, cy + fs * 0.35)
    setc(ctx, INK)
    ctx.show_text(text)
    ctx.restore()


class EgyptWorker(EraPerson):
    """Old Kingdom Egyptian (worker / overseer / scribe / baker / healer)."""
    kind = "egypt"

    def __init__(self, spec, seed=0):
        super().__init__(spec, seed)
        from .egypt import EgyptPerson
        EgyptPerson.setup(self, spec, seed)

    def render(self, ctx, t, st, J):
        from .egypt import EgyptPerson
        EgyptPerson.render(self, ctx, t, st, J)


def make_actor(spec, seed=0):
    k = spec.get("kind", "era")
    if k == "fardin":
        return Fardin(spec, seed)
    if k == "egypt":
        return EgyptWorker(spec, seed)
    return EraPerson(spec, seed)
