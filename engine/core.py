"""Core math: easing, interpolation, keyframe tracks, deterministic noise, colours.

Every visual value in the engine is a pure function of time, so frames can be
rendered out of order in parallel processes and re-renders are bit-identical.
"""
import math
import hashlib

TAU = math.pi * 2


# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lerp(a, b, t):
    return a + (b - a) * t


def smoothstep(e0, e1, x):
    t = clamp((x - e0) / (e1 - e0) if e1 != e0 else 1.0)
    return t * t * (3 - 2 * t)


def linear(t): return t
def in_quad(t): return t * t
def out_quad(t): return 1 - (1 - t) * (1 - t)
def in_out_quad(t): return 2 * t * t if t < .5 else 1 - (-2 * t + 2) ** 2 / 2
def in_cubic(t): return t ** 3
def out_cubic(t): return 1 - (1 - t) ** 3
def in_out_cubic(t): return 4 * t ** 3 if t < .5 else 1 - (-2 * t + 2) ** 3 / 2
def in_out_sine(t): return -(math.cos(math.pi * t) - 1) / 2
def out_sine(t): return math.sin(t * math.pi / 2)
def out_expo(t): return 1 if t >= 1 else 1 - 2 ** (-10 * t)
def in_expo(t): return 0 if t <= 0 else 2 ** (10 * t - 10)


def out_back(t, s=1.70158):
    t -= 1
    return t * t * ((s + 1) * t + s) + 1


def in_out_back(t, s=1.70158 * 1.525):
    if t < .5:
        return ((2 * t) ** 2 * ((s + 1) * 2 * t - s)) / 2
    return ((2 * t - 2) ** 2 * ((s + 1) * (t * 2 - 2) + s) + 2) / 2


def out_elastic(t):
    if t <= 0: return 0
    if t >= 1: return 1
    return 2 ** (-10 * t) * math.sin((t * 10 - .75) * TAU / 3) + 1


def spring(t, freq=4.5, damp=5.0):
    """Damped spring 0->1 with overshoot (t in seconds-ish units, 0..1 ~ settle)."""
    if t <= 0: return 0.0
    return 1 - math.exp(-damp * t) * math.cos(freq * TAU * t * 0.25 * 2)


EASE = {
    "linear": linear, "inQuad": in_quad, "outQuad": out_quad, "inOutQuad": in_out_quad,
    "inCubic": in_cubic, "outCubic": out_cubic, "inOutCubic": in_out_cubic,
    "inOutSine": in_out_sine, "outSine": out_sine, "outExpo": out_expo, "inExpo": in_expo,
    "outBack": out_back, "inOutBack": in_out_back, "outElastic": out_elastic,
}


def ease(name, t):
    return EASE.get(name or "inOutCubic", in_out_cubic)(clamp(t))


# ---------------------------------------------------------------- tracks
def mix(a, b, t):
    if isinstance(a, (tuple, list)):
        return tuple(lerp(x, y, t) for x, y in zip(a, b))
    return lerp(a, b, t)


class Track:
    """Keyframe track. keys: list of (time, value, ease_into_this_key)."""

    def __init__(self, keys, default=0.0):
        self.keys = sorted(keys, key=lambda k: k[0])
        self.default = default

    def __call__(self, t):
        k = self.keys
        if not k:
            return self.default
        if t <= k[0][0]:
            return k[0][1]
        for i in range(1, len(k)):
            if t < k[i][0]:
                t0, v0 = k[i - 1][0], k[i - 1][1]
                t1, v1, e = k[i][0], k[i][1], (k[i][2] if len(k[i]) > 2 else None)
                u = (t - t0) / max(1e-6, t1 - t0)
                return mix(v0, v1, ease(e, u))
        return k[-1][1]


# ---------------------------------------------------------------- noise
def _hash(i, seed=0):
    h = (i * 374761393 + seed * 668265263) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFFFF) / float(0xFFFFFF)


def hrand(*parts):
    """Deterministic random in [0,1) from arbitrary hashable parts."""
    s = "|".join(str(p) for p in parts).encode()
    return int.from_bytes(hashlib.blake2b(s, digest_size=6).digest(), "little") / float(1 << 48)


def noise1(x, seed=0):
    """Smooth 1D value noise in [-1,1]."""
    i = math.floor(x)
    f = x - i
    u = f * f * (3 - 2 * f)
    return lerp(_hash(i, seed), _hash(i + 1, seed), u) * 2 - 1


def fbm1(x, seed=0, oct=3):
    v, a, fr = 0.0, 0.5, 1.0
    for o in range(oct):
        v += a * noise1(x * fr, seed + o * 17)
        a *= 0.5
        fr *= 2.0
    return v


# ---------------------------------------------------------------- colour
def hexc(h, a=1.0):
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)


def cmix(c1, c2, t):
    c1 = hexc(c1) if isinstance(c1, str) else c1
    c2 = hexc(c2) if isinstance(c2, str) else c2
    if len(c1) == 3: c1 = (*c1, 1.0)
    if len(c2) == 3: c2 = (*c2, 1.0)
    return tuple(lerp(a, b, t) for a, b in zip(c1, c2))


def shade(c, k):
    """k<0 darker, k>0 lighter."""
    c = hexc(c) if isinstance(c, str) else c
    a = c[3] if len(c) > 3 else 1.0
    if k < 0:
        return (c[0] * (1 + k), c[1] * (1 + k), c[2] * (1 + k), a)
    return (lerp(c[0], 1, k), lerp(c[1], 1, k), lerp(c[2], 1, k), a)


def alpha(c, a):
    c = hexc(c) if isinstance(c, str) else c
    return (c[0], c[1], c[2], a)


def setc(ctx, c, a=None):
    if LIGHT["on"] and not isinstance(c, Lit):
        c = lc(c)
    c = hexc(c) if isinstance(c, str) else c
    if len(c) == 3:
        c = (*c, 1.0)
    ctx.set_source_rgba(c[0], c[1], c[2], c[3] if a is None else c[3] * a)


def tint(c, tintc, amount):
    """Multiply-ish lighting tint used for time-of-day grading."""
    c = hexc(c) if isinstance(c, str) else c
    tintc = hexc(tintc) if isinstance(tintc, str) else tintc
    a = c[3] if len(c) > 3 else 1
    m = (c[0] * tintc[0], c[1] * tintc[1], c[2] * tintc[2])
    return (lerp(c[0], m[0], amount), lerp(c[1], m[1], amount), lerp(c[2], m[2], amount), a)


# ---------------------------------------------------------------- global lighting
class Lit(tuple):
    """A colour that already has scene lighting applied."""


LIGHT = {"on": False, "tint": (1, 1, 1), "amt": 0.0, "dark": 0.0, "haze": None}


def set_light(tintc=(1, 1, 1), amt=0.0, dark=0.0):
    LIGHT.update(on=True, tint=tintc, amt=amt, dark=dark)


def light_off():
    prev = dict(LIGHT)
    LIGHT["on"] = False
    return prev


def light_restore(prev):
    LIGHT.update(prev)


def lc(c, a=None):
    c = hexc(c) if isinstance(c, str) else c
    if isinstance(c, Lit):
        return c
    if len(c) == 3:
        c = (*c, 1.0)
    al = c[3] if a is None else c[3] * a
    if not LIGHT["on"]:
        return Lit((c[0], c[1], c[2], al))
    tc = tint(c, LIGHT["tint"], LIGHT["amt"])
    k = 1 - LIGHT["dark"]
    return Lit((tc[0] * k, tc[1] * k, tc[2] * k, al))
