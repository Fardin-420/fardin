"""Scene system: parallax sets, time-of-day lighting, weather, camera, compositing."""
import math
import cairo
from .core import (Track, clamp, lerp, ease, hrand, noise1, fbm1, setc, hexc, shade, cmix, TAU,
                   set_light, light_off, light_restore, lc, LIGHT, smoothstep)
from . import props as P
from .animals import Animal
from .character import make_actor, Fardin
from . import graphics as G

BASE_W, BASE_H = 1920, 1080
GROUND_CAM_Y = -210.0

TOD = {
    "dawn": dict(sky=("#27315e", "#c9787a", "#f6b98a"), sun=(0.72, 0.62, "#ffe0a8", 70), tint=(1.0, 0.8, 0.72), amt=0.3, dark=0.06, stars=0.25, haze="#d9937a"),
    "morning": dict(sky=("#4a86c8", "#a9cfe6", "#f3e1c0"), sun=(0.8, 0.3, "#fff2c8", 60), tint=(1.0, 0.95, 0.88), amt=0.12, dark=0.0, stars=0, haze="#d9d6c8"),
    "day": dict(sky=("#3d8bd0", "#93c8ea", "#e4f1f0"), sun=(0.25, 0.12, "#fffbe6", 55), tint=(1, 1, 1), amt=0.0, dark=0.0, stars=0, haze="#cfe0e2"),
    "golden": dict(sky=("#4e4380", "#e7845a", "#ffcf8c"), sun=(0.3, 0.58, "#ffd27a", 85), tint=(1.0, 0.78, 0.58), amt=0.32, dark=0.04, stars=0, haze="#efa26e"),
    "dusk": dict(sky=("#141734", "#5b3a66", "#cf6f55"), sun=(0.15, 0.78, "#ff9a5a", 80), tint=(0.68, 0.6, 0.86), amt=0.5, dark=0.28, stars=0.5, haze="#6d4a68"),
    "night": dict(sky=("#02040c", "#081029", "#16224a"), moon=(0.78, 0.18), tint=(0.42, 0.52, 0.9), amt=0.72, dark=0.5, stars=1.0, haze="#16203f"),
    "cave": dict(sky=("#0a0705", "#120c08", "#1c130d"), tint=(0.75, 0.62, 0.55), amt=0.35, dark=0.2, stars=0, haze="#1e150f"),
}

SETS = {
    "savanna": dict(ground=("#c8a35a", "#a98443"), far="#7d8fa3", mid="#9c9550", mid2="#8a8a48", trees=True, cliff=None),
    "camp": dict(ground=("#b9925e", "#94704a"), far="#86919e", mid="#9a8a55", mid2="#8f7d50", trees=True, cliff=True),
    "cave": dict(ground=("#7a5c42", "#5a4330"), interior=True),
    "room": dict(ground=("#8c6a4f", "#6d5240"), room=True),
    "void": dict(void=True),
}


class Camera:
    def __init__(self, keys, shakes=None, pushes=None):
        self.keys = sorted(keys or [{"t": 0}], key=lambda k: k["t"])
        self.shakes = shakes or []
        self.pushes = pushes or []

    def _resolve(self, k, t, actors):
        x = k.get("x", 0.0)
        y = k.get("y", GROUND_CAM_Y)
        if "track" in k and k["track"] in actors:
            a = actors[k["track"]]
            xs = [a.xt(t - i * 0.08) if hasattr(a, "xt") else 0 for i in range(6)]
            x = sum(xs) / len(xs) + k.get("dx", 0.0)
            if "dy" in k:
                y = a.yt(t) + k["dy"] if hasattr(a, "yt") else y
        return x, y, k.get("zoom", 1.0)

    def at(self, t, actors):
        ks = self.keys
        i = 0
        for j, k in enumerate(ks):
            if k["t"] <= t:
                i = j
        x, y, z = self._resolve(ks[i], t, actors)
        if i + 1 < len(ks):
            k1 = ks[i + 1]
            hold = ks[i].get("hold", 0.0)
            t0 = ks[i]["t"] + hold
            if t > t0:
                u = (t - t0) / max(1e-3, k1["t"] - t0)
                w = ease(k1.get("ease", "inOutSine"), u)
                x1, y1, z1 = self._resolve(k1, t, actors)
                x, y, z = lerp(x, x1, w), lerp(y, y1, w), lerp(z, z1, w)
        # reaction push-ins
        for p in self.pushes:
            dt = t - p["t"]
            if -0.05 < dt < p.get("dur", 1.6):
                k = smoothstep(-0.05, 0.12, dt) * (1 - smoothstep(p.get("dur", 1.6) - 0.6, p.get("dur", 1.6), dt))
                amt = p.get("amt", 0.14)
                z *= 1 + amt * k
                if p.get("x") is not None:
                    x = lerp(x, p["x"], 0.35 * k)
                    y = lerp(y, p["y"], 0.35 * k)
        sx = sy = 0.0
        for s in self.shakes:
            if s["t0"] <= t <= s["t1"]:
                fade = min(1, (t - s["t0"]) / 0.2, (s["t1"] - t) / 0.3)
                a = s.get("amp", 10) * fade
                sx += noise1(t * 14, 11) * a
                sy += noise1(t * 14, 23) * a
        return x + sx, y + sy, z


def layer(ctx, cam, p, W, H):
    cx, cy, z = cam
    k = W / BASE_W if W / H >= BASE_W / BASE_H else H / BASE_H * 0.72
    zz = 1 + (z - 1) * p
    ctx.translate(W / 2, H / 2)
    ctx.scale(zz * k, zz * k)
    ctx.translate(-cx * p, -cy * p)


def world_to_screen(pt, cam, W, H, p=1.0):
    cx, cy, z = cam
    k = W / BASE_W if W / H >= BASE_W / BASE_H else H / BASE_H * 0.72
    zz = 1 + (z - 1) * p
    return (W / 2 + (pt[0] - cx * p) * zz * k, H / 2 + (pt[1] - cy * p) * zz * k)


# ------------------------------------------------------------------ backgrounds
def draw_sky(ctx, W, H, tod, t, cam):
    pal = TOD[tod]
    c0, c1, c2 = pal["sky"]
    g = cairo.LinearGradient(0, 0, 0, H * 0.62)
    g.add_color_stop_rgba(0, *hexc(c0))
    g.add_color_stop_rgba(0.6, *hexc(c1))
    g.add_color_stop_rgba(1, *hexc(c2))
    ctx.set_source(g)
    ctx.paint()
    if pal.get("stars", 0) > 0:
        for i in range(140):
            sx = (hrand("st", i) * W * 1.2 - cam[0] * 0.01) % W
            sy = hrand("sty", i) ** 1.4 * H * 0.55
            tw = 0.6 + 0.4 * math.sin(t * (1 + 2 * hrand("tw", i)) + i)
            ctx.set_source_rgba(1, 1, 0.95, pal["stars"] * tw * (0.35 + 0.65 * hrand("sb", i)))
            ctx.arc(sx, sy, 1 + 1.6 * hrand("sr", i) * W / BASE_W, 0, TAU)
            ctx.fill()
    if "sun" in pal:
        ux, uy, sc, r = pal["sun"]
        sx, sy = ux * W - cam[0] * 0.02, uy * H
        r *= W / BASE_W
        for rr, a in ((r * 4, 0.12), (r * 2, 0.22)):
            gg = cairo.RadialGradient(sx, sy, 0, sx, sy, rr)
            gg.add_color_stop_rgba(0, *hexc(sc)[:3], a)
            gg.add_color_stop_rgba(1, *hexc(sc)[:3], 0)
            ctx.set_source(gg); ctx.arc(sx, sy, rr, 0, TAU); ctx.fill()
        setc(ctx, sc); ctx.arc(sx, sy, r, 0, TAU); ctx.fill()
    if "moon" in pal:
        ux, uy = pal["moon"]
        mx, my, r = ux * W - cam[0] * 0.02, uy * H, 46 * W / BASE_W
        gg = cairo.RadialGradient(mx, my, 0, mx, my, r * 5)
        gg.add_color_stop_rgba(0, 0.8, 0.85, 1, 0.22); gg.add_color_stop_rgba(1, 0.8, 0.85, 1, 0)
        ctx.set_source(gg); ctx.arc(mx, my, r * 5, 0, TAU); ctx.fill()
        ctx.set_source_rgba(0.93, 0.94, 0.88, 1); ctx.arc(mx, my, r, 0, TAU); ctx.fill()
        ctx.set_source_rgba(0.8, 0.82, 0.78, 1)
        for i in range(4):
            ctx.arc(mx + (hrand("cr", i) - .5) * r, my + (hrand("cry", i) - .5) * r, r * 0.15 * (1 + hrand("crr", i)), 0, TAU); ctx.fill()
    # clouds
    if tod not in ("night", "cave"):
        for i in range(5):
            cx = ((hrand("cl", i) * 2600 + t * (8 + 6 * hrand("cs", i)) - cam[0] * 0.05) % 2800 - 400) * W / BASE_W
            cy = (60 + hrand("cy", i) * 260) * H / BASE_H
            col = cmix(pal["sky"][2], "#ffffff", 0.5)
            ctx.set_source_rgba(col[0], col[1], col[2], 0.5)
            for k in range(4):
                ctx.save(); ctx.translate(cx + k * 55 * W / BASE_W, cy - (k % 2) * 16); ctx.scale(80 * W / BASE_W, 26 * W / BASE_W)
                ctx.arc(0, 0, 1, 0, TAU); ctx.restore(); ctx.fill()


def ridge(ctx, x0, x1, base, height, seed, freq, col, rough=0.5):
    ctx.move_to(x0, base + 600)
    n = int((x1 - x0) / 24) + 1
    for i in range(n + 1):
        x = x0 + i * (x1 - x0) / n
        h = height * (0.55 + 0.45 * fbm1(x * freq, seed, 4) + rough * 0.15 * noise1(x * freq * 6, seed + 9))
        ctx.line_to(x, base - h)
    ctx.line_to(x1, base + 600)
    ctx.close_path()
    setc(ctx, col)
    ctx.fill()


def draw_set(ctx, W, H, setname, tod, t, cam, seed=0, opts=None):
    opts = opts or {}
    st = SETS[setname]
    pal = TOD[tod]
    if st.get("void"):
        G.time_tunnel(ctx, W, H, t, opts.get("tunnel", 1.0))
        return
    if st.get("room"):
        ctx.save(); layer(ctx, cam, 1.0, W, H)
        setc(ctx, "#2c3d5c" if tod == "night" else "#5e7fa6")
        ctx.rectangle(-3000, -2000, 6000, 2000); ctx.fill()
        setc(ctx, "#6b4f3a"); ctx.rectangle(-3000, 0, 6000, 1500); ctx.fill()
        setc(ctx, "#4d3929")
        for i in range(-30, 30):
            ctx.rectangle(i * 140, 0, 3, 1500); ctx.fill()
        setc(ctx, "#e8e2d4"); ctx.rectangle(-3000, -14, 6000, 14); ctx.fill()
        P.room(ctx, 0, 0, 1.0, t)
        ctx.restore()
        return
    if st.get("interior"):
        ctx.save(); layer(ctx, cam, 0.6, W, H)
        setc(ctx, lc("#4a3526")); ctx.rectangle(-4000, -3000, 8000, 6000); ctx.fill()
        for i in range(40):
            x = (hrand("cw", i) - .5) * 5000
            y = -100 - hrand("cwy", i) * 1100
            setc(ctx, lc(shade("#5a4330", (hrand("cwc", i) - .5) * .3)))
            ctx.save(); ctx.translate(x, y); ctx.rotate(hrand("cwr", i)); ctx.scale(180 + 200 * hrand("cws", i), 60 + 80 * hrand("cwh", i))
            ctx.arc(0, 0, 1, 0, TAU); ctx.restore(); ctx.fill()
        ctx.restore()
        ctx.save(); layer(ctx, cam, 1.0, W, H)
        g = cairo.LinearGradient(0, -60, 0, 700)
        g.add_color_stop_rgba(0, *lc(st["ground"][0])); g.add_color_stop_rgba(1, *lc(st["ground"][1]))
        ctx.set_source(g)
        ctx.move_to(-5000, 0)
        for i in range(0, 101):
            x = -5000 + i * 100
            ctx.line_to(x, -40 + noise1(x * 0.004, 4) * 30)
        ctx.line_to(5000, 2000); ctx.line_to(-5000, 2000); ctx.close_path(); ctx.fill()
        ctx.restore()
        return
    # ---- outdoor sets
    hz = cmix(pal["haze"], pal["sky"][2], 0.35)
    ctx.save(); layer(ctx, cam, 0.12, W, H)
    ridge(ctx, cam[0] * 0.12 - 2200, cam[0] * 0.12 + 2200, 0, 300, 3 + seed, 0.0018, lc(cmix(st["far"], hz, 0.55)))
    ridge(ctx, cam[0] * 0.12 - 2200, cam[0] * 0.12 + 2200, 0, 190, 5 + seed, 0.0025, lc(cmix(st["far"], hz, 0.3)))
    ctx.restore()
    # ground plane from far horizon down
    hy = world_to_screen((0, 0), cam, W, H, 0.12)[1]
    g = cairo.LinearGradient(0, hy, 0, H)
    g.add_color_stop_rgba(0, *lc(cmix(st["ground"][0], hz, 0.45)))
    g.add_color_stop_rgba(0.45, *lc(st["ground"][0]))
    g.add_color_stop_rgba(1, *lc(st["ground"][1]))
    ctx.set_source(g)
    ctx.rectangle(0, hy - 2, W, H - hy + 2)
    ctx.fill()
    ctx.save(); layer(ctx, cam, 0.35, W, H)
    ridge(ctx, cam[0] * 0.35 - 2400, cam[0] * 0.35 + 2400, 0, 110, 8 + seed, 0.002, lc(cmix(st["mid"], hz, 0.35)), 0.2)
    if st.get("trees"):
        for i in range(-12, 13):
            x = math.floor(cam[0] * 0.35 / 380) * 380 + i * 380 + hrand("tr", i, seed) * 200
            ii = math.floor(x / 380)
            if hrand("tree", ii, seed) > 0.55:
                P.acacia(ctx, x, -40 - hrand("try", ii) * 30, 0.32 + 0.12 * hrand("trs", ii), t, ii, col=cmix("#4f6a2f", hz, 0.35))
    ctx.restore()
    ctx.save(); layer(ctx, cam, 0.62, W, H)
    ridge(ctx, cam[0] * 0.62 - 2600, cam[0] * 0.62 + 2600, 30, 60, 12 + seed, 0.003, lc(cmix(st["mid2"], hz, 0.15)), 0.2)
    if st.get("cliff") and opts.get("cliff_x") is not None:
        P.cliff(ctx, opts["cliff_x"], 40, 1.25, t, seed=7, col=cmix("#8c6f55", hz, 0.12), cave=opts.get("cave", True))
    ctx.restore()


def ground_details(ctx, W, H, cam, t, setname, seed=0, front=False):
    st = SETS[setname]
    if st.get("void") or st.get("room"):
        return
    ctx.save(); layer(ctx, cam, 1.0, W, H)
    span = 1400 / max(0.5, cam[2])
    i0, i1 = int((cam[0] - span) // 110) - 1, int((cam[0] + span) // 110) + 2
    for i in range(i0, i1):
        r = hrand("gd", i, seed)
        y = -50 + hrand("gdy", i, seed) * 420
        if front != (y > 120):
            continue
        x = i * 110 + hrand("gdx", i, seed) * 90
        if st.get("interior"):
            if r < 0.3:
                P.rock(ctx, x, y, 0.2 + 0.15 * hrand("rs", i), t, i, col="#4a382a")
            continue
        if r < 0.62:
            P.grass(ctx, x, y, 0.8 + 0.6 * (y / 400), t, i, col="#b4923f" if setname == "savanna" else "#a38a4a")
        elif r < 0.72:
            P.rock(ctx, x, y, 0.15 + 0.12 * hrand("rs", i), t, i)
    ctx.restore()


def weather(ctx, W, H, kind, t, amount=1.0):
    if not kind:
        return
    k = W / BASE_W
    if kind == "dust":
        for i in range(70):
            ph = (t * (0.05 + 0.06 * hrand("du", i)) + hrand("dx", i)) % 1
            x = ph * W * 1.2 - W * 0.1
            y = (hrand("dy", i) * H + math.sin(t + i) * 30) % H
            ctx.set_source_rgba(0.95, 0.85, 0.65, 0.25 * amount * math.sin(ph * math.pi))
            ctx.arc(x, y, (1.5 + 3 * hrand("ds", i)) * k, 0, TAU); ctx.fill()
    elif kind == "rain":
        ctx.set_line_width(2 * k)
        for i in range(260):
            ph = (t * (1.6 + hrand("rs", i)) + hrand("ry", i)) % 1
            x = (hrand("rx", i) * W * 1.2 + ph * 120) % (W * 1.1)
            y = ph * H * 1.1 - 40
            ctx.set_source_rgba(0.75, 0.82, 0.95, 0.35 * amount)
            ctx.move_to(x, y); ctx.line_to(x - 10 * k, y + 34 * k); ctx.stroke()
    elif kind == "snow":
        for i in range(200):
            ph = (t * (0.08 + 0.08 * hrand("ss", i)) + hrand("sy", i)) % 1
            x = (hrand("sx", i) * W + math.sin(t * 0.8 + i) * 40) % W
            y = ph * H
            ctx.set_source_rgba(1, 1, 1, 0.8 * amount)
            ctx.arc(x, y, (2 + 3 * hrand("sr", i)) * k, 0, TAU); ctx.fill()
    elif kind == "embers":
        for i in range(40):
            ph = (t * (0.1 + 0.1 * hrand("em", i)) + hrand("ey", i)) % 1
            x = (hrand("ex", i) * W + math.sin(t * 1.3 + i) * 50) % W
            y = H - ph * H
            ctx.set_source_rgba(1, 0.6, 0.2, 0.7 * amount * math.sin(ph * math.pi))
            ctx.arc(x, y, (1.5 + 2 * hrand("er", i)) * k, 0, TAU); ctx.fill()
    elif kind == "fireflies":
        for i in range(24):
            x = (hrand("ffx", i) * W + noise1(t * 0.3 + i, 2) * 120) % W
            y = H * (0.45 + 0.45 * hrand("ffy", i)) + noise1(t * 0.4 + i, 8) * 60
            a = max(0, math.sin(t * (1 + hrand("ffs", i)) * 2 + i))
            ctx.set_source_rgba(0.95, 1, 0.55, 0.6 * a * amount)
            ctx.arc(x, y, 3 * k, 0, TAU); ctx.fill()


def vignette(ctx, W, H, strength=0.45):
    g = cairo.RadialGradient(W / 2, H / 2, H * 0.35, W / 2, H / 2, H * 1.05)
    g.add_color_stop_rgba(0, 0, 0, 0, 0)
    g.add_color_stop_rgba(1, 0, 0, 0, strength)
    ctx.set_source(g)
    ctx.paint()


# ------------------------------------------------------------------ Scene
class Scene:
    """A resolved scene: all times in seconds relative to scene start."""

    def __init__(self, spec):
        self.spec = spec
        self.dur = spec["dur"]
        self.set = spec.get("set", "savanna")
        self.tod = spec.get("tod", "day")
        self.weather = spec.get("weather")
        self.seed = spec.get("seed", 0)
        self.actors = {}
        self.order = []
        for i, a in enumerate(spec.get("actors", [])):
            act = make_actor(a, seed=i + 1)
            self.actors[act.id] = act
            self.order.append(act)
        for i, a in enumerate(spec.get("crowd_actors", [])):
            act = make_actor(a, seed=100 + i)
            self.actors[act.id] = act
            self.order.append(act)
        self.animals = [Animal(a, seed=i + 7) for i, a in enumerate(spec.get("animals", []))]
        pushes = []
        for act in self.order:
            if isinstance(act, Fardin):
                for p in act.pops:
                    pushes.append({"t": p, "actor": act.id})
        self.pushes = pushes
        self.camera = Camera(spec.get("camera"), spec.get("shake"), [])
        self.props = spec.get("props", [])
        self.graphics = spec.get("graphics", [])
        self.fx = spec.get("fx", [])
        self.lights = spec.get("lights", [])

    def cam_at(self, t):
        cam = self.camera
        pushes = []
        for p in self.pushes:
            a = self.actors[p["actor"]]
            if -0.1 < t - p["t"] < 1.8:
                hx, hy = a.screen_head(p["t"] + 0.2)
                pushes.append({"t": p["t"], "x": hx, "y": hy + 60, "amt": self.spec.get("push_amt", 0.16)})
        cam.pushes = pushes
        return cam.at(t, self.actors)

    def fardin_screen(self, t, W=BASE_W, H=BASE_H):
        for a in self.order:
            if isinstance(a, Fardin):
                cam = self.cam_at(t)
                return world_to_screen(a.screen_head(t), cam, W, H)
        return (W / 2, H / 2)

    def _prop(self, ctx, p, t):
        fn = P.PROPS.get(p["type"])
        if not fn:
            return
        kw = {k: v for k, v in p.items() if k not in ("type", "x", "y", "s", "front", "layer", "from", "until", "anim", "glow")}
        if "anim" in p:  # animated numeric kw: {"butchered": [[t,v],[t,v]]}
            for k, keys in p["anim"].items():
                kw[k] = Track([tuple(kk) for kk in keys])(t)
        ctx.save()
        if p.get("flip"):
            ctx.translate(p["x"], 0); ctx.scale(-1, 1); ctx.translate(-p["x"], 0)
            kw.pop("flip", None)
        else:
            kw.pop("flip", None)
        fn(ctx, p["x"], p.get("y", 0), p.get("s", 1.0), t, **kw)
        ctx.restore()

    def render(self, ctx, W, H, t, ui=True):
        pal = TOD[self.tod]
        cam = self.cam_at(t)
        opts = dict(self.spec.get("set_opts", {}))
        if self.set == "void":
            opts["tunnel"] = Track([tuple(k) for k in self.spec.get("tunnel", [[0, 1]])])(t)
        prev = light_off()
        draw_sky(ctx, W, H, self.tod, t, cam)
        set_light(pal["tint"], pal["amt"], pal["dark"])
        draw_set(ctx, W, H, self.set, self.tod, t, cam, self.seed, opts)
        ground_details(ctx, W, H, cam, t, self.set, self.seed, front=False)
        ctx.save(); layer(ctx, cam, 1.0, W, H)
        visible = lambda o: o.get("from", -1) <= t <= o.get("until", 1e9)
        for p in self.props:
            if not p.get("front") and visible(p):
                self._prop(ctx, p, t)
        items = [(a.layer, 0, a) for a in self.animals] + [(a.layer, 1, a) for a in self.order]
        items.sort(key=lambda k: (k[0], k[1]))
        fardins = []
        for lay, kind, obj in items:
            if isinstance(obj, Fardin):
                fardins.append(obj)
                continue
            if kind == 0:
                obj.draw(ctx, t)
            else:
                obj.draw(ctx, t)
        # projectiles (thrown spears etc.)
        for fx in self.fx:
            if fx["type"] in ("spear_flight", "torch_flight") and fx["t"] <= t <= fx["t"] + fx.get("dur", 0.7):
                G.spear_flight(ctx, dict(fx, style="torch" if fx["type"] == "torch_flight" else "spear"), t)
            elif fx["type"] == "spear_stuck" and t >= fx["t"]:
                x, y = fx["pos"]
                ctx.save(); ctx.translate(x, y); ctx.rotate(fx.get("ang", 0.5))
                ctx.set_line_width(6); setc(ctx, "#6b4724"); ctx.move_to(-150, 0); ctx.line_to(20, 0); ctx.stroke()
                ctx.restore()
            elif fx["type"] == "dust" and 0 <= t - fx["t"] <= fx.get("dur", 1.0):
                k = (t - fx["t"]) / fx.get("dur", 1.0)
                for i in range(9):
                    dx = (i - 4) * 40 * (0.4 + k)
                    r = (20 + 60 * k) * (0.7 + 0.5 * hrand("du", i))
                    ctx.set_source_rgba(0.85, 0.75, 0.55, 0.5 * (1 - k))
                    ctx.arc(fx["x"] + dx, fx.get("y", 0) - r * 0.5 - k * 20, r, 0, TAU); ctx.fill()
        ctx.restore()
        # fire light pools (additive)
        ctx.save(); layer(ctx, cam, 1.0, W, H)
        for p in self.props:
            if p["type"] == "campfire" and p.get("lit", True) and visible(p):
                P.fire_light(ctx, p["x"], p.get("y", 0), p.get("s", 1.0) * p.get("glow", 1.0), t,
                             strength=1.0 if self.tod in ("night", "cave", "dusk") else 0.35)
        for L in self.lights:
            P.fire_light(ctx, L["x"], L.get("y", 0), L.get("s", 1.0), t, L.get("strength", 1.0), color=tuple(L.get("color", (1, .55, .2))))
        ctx.restore()
        # Fardin: unaffected by world lighting -> always the brightest element
        light_off()
        ctx.save(); layer(ctx, cam, 1.0, W, H)
        for f in fardins:
            f.draw(ctx, t)
        ctx.restore()
        set_light(pal["tint"], pal["amt"], pal["dark"])
        ctx.save(); layer(ctx, cam, 1.0, W, H)
        for p in self.props:
            if p.get("front") and visible(p):
                self._prop(ctx, p, t)
        ctx.restore()
        ground_details(ctx, W, H, cam, t, self.set, self.seed, front=True)
        if self.set == "cave":
            G.cave_frame(ctx, W, H, cam)
        light_off()
        weather(ctx, W, H, self.weather, t, self.spec.get("weather_amt", 1.0))
        if self.set != "void":
            vignette(ctx, W, H, 0.55 if self.tod in ("night", "cave") else 0.35)
        light_restore(prev)
        LIGHT["on"] = False
        if ui:
            for gspec in self.graphics:
                lt = t - gspec["t"]
                if 0 <= lt <= gspec.get("dur", 4.0):
                    G.draw_graphic(ctx, W, H, gspec, lt, t)
        for fx in self.fx:
            G.draw_fx(ctx, W, H, fx, t, self)
