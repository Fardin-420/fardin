#!/usr/bin/env python3
# Three 0-3 s opening variations for "The Moon Is Rusting" (Stage A). Usage: python3 hooks.py A|B|C
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw
from multiprocessing import Pool
import moonfx as M
from moonfx import W, H, FPS, seg, ease, ease_out, ease_in, ease_io, lerp, clamp

TIM = json.load(open("timing.json"))
def ws(i, k): return TIM[i]["words"][k][1]
SUN = (-0.72, 0.30, 0.62)
EC, ER = (540, 2430), 1160                       # Earth: centre far below the frame, top limb at y ~1270
MC, MR = (540, 740), 285                          # Moon above it

def macro(): return M.cache("macro", M.make_macro)

def earth_moon(t, base=None, mR=MR, mc=MC, ec=EC, eR=ER, stream=1.0, hem=0.9, life=1.0):
    arr = M.stars().copy() if base is None else base
    arr = M.earth_disc(arr, ec[0], ec[1], eR, lon=-30 + 2 * t, lat0=28, sun=SUN)
    arr = M.limb_glow(arr, ec[0], ec[1], eR, SUN)
    arr = M.moon(arr, mc[0], mc[1], mR, light=SUN, lon_c=0, lat0=-18, hem=hem, earthshine=0.6)
    if stream > 0:
        paths = []
        for a in np.linspace(-0.42, 0.42, 7):
            p0 = (ec[0] + eR * 1.015 * math.sin(a), ec[1] - eR * 1.015 * math.cos(a))
            p3 = (mc[0] + mR * 0.55 * math.sin(a * 2), mc[1] + mR * 0.86)
            paths.append((p0, (p0[0] + 260 * math.sin(a * 1.7) + 120, p0[1] - 260), (p3[0] + 200, p3[1] + 260), p3))
        arr = M.particles(arr, paths, t, n=320, speed=0.45, amt=0.8 * stream, spread=10, life=life)
    return arr

def topdown(cw):
    """Top-down shaded terrain plate (orbital view), crop width cw map pixels centred on the map."""
    col = M.shaded(14.0)
    ch = cw * H / W; c = M.N / 2
    pil = M.cache("tdimg", lambda: Image.fromarray(np.clip(M.tone(col), 0, 255).astype(np.uint8)))
    return np.asarray(pil.transform((W, H), Image.EXTENT, (c - cw / 2, c - ch / 2, c + cw / 2, c + ch / 2), Image.BILINEAR), np.float32)

def variant_A(t):
    # 0-0.55 macro, rust appears | 0.45-1.15 pullback macro -> orbital terrain -> globe | 1.15+ Moon over Earth, O+ stream
    if t < 0.6:
        k = M.lerp(0.25, 1.25, seg(t, 0.0, 0.5))
        z = lerp(1.9, 1.75, seg(t, 0, 0.5)) * math.exp(-3.2 * ease_in(seg(t, 0.42, 0.6)))
        arr = M.tone(M.macro_frame(macro(), k, zoom=z))
        if t > 0.5:
            td = topdown(180 * math.exp(4.0 * seg(t, 0.5, 0.6)))
            arr = arr * (1 - seg(t, 0.5, 0.6)) + td * seg(t, 0.5, 0.6)
        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    elif t < 1.15:
        u = seg(t, 0.6, 1.15)
        td = topdown(180 * math.exp(4.0 + 2.2 * ease(u)))
        R = lerp(5200, MR, ease_out(seg(t, 0.75, 1.15)))
        cy = lerp(MC[1] + R * 0.55, MC[1], ease_out(seg(t, 0.75, 1.15)))
        base = M.stars().copy()
        if t > 0.95: base = earth_moon(t, base=None, mR=1, stream=0)  # Earth enters underneath
        g = M.moon(base, 540, cy, R, light=SUN, lat0=-18, hem=0.9, earthshine=0.6)
        g = M.tone(g)
        w = seg(t, 0.6, 0.85)
        arr = td * (1 - w) + g * w
        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    else:
        img = M.finish(earth_moon(t, life=clamp((t - 1.15) / 0.9, 0.05, 1.0)), 0.45)
    d = ImageDraw.Draw(img, "RGBA")
    M.hook_title(d, max(0.85, 1.15 - 0.3 * seg(t, 0, 0.12)))
    if t >= 1.15: M.tag(d, "SCIENTIFIC VISUALIZATION  ·  oxygen ions shown glowing", (120, 255, 190))
    return img

def variant_B(t):
    # 0-1.3 Moon over Earth with the stream, push into the north polar region | 1.3+ macro: grains turn to hematite
    if t < 1.35:
        u = ease_in(seg(t, 0.25, 1.35))
        R = lerp(MR, 6000, u); cy = lerp(MC[1], MC[1] + R * 0.82, u)
        arr = earth_moon(t, mR=MR, life=1.0)
        if u > 0:
            arr = M.moon(M.stars().copy() if u > 0.25 else arr, 540, cy, R, light=SUN, lat0=-18, hem=0.9 + 0.6 * u, earthshine=0.6)
        img = M.finish(arr, 0.45)
        if t > 1.2: img = Image.blend(img, Image.fromarray(np.clip(M.tone(M.macro_frame(macro(), 0.2, zoom=1.0)), 0, 255).astype(np.uint8)), seg(t, 1.2, 1.35))
    else:
        k = lerp(0.2, 1.25, seg(t, 1.35, 2.2))
        img = Image.fromarray(np.clip(M.tone(M.macro_frame(macro(), k, zoom=lerp(1.0, 1.8, ease_out(seg(t, 1.35, 2.6))))), 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img, "RGBA")
    M.hook_title(d, max(0.85, 1.15 - 0.3 * seg(t, 0, 0.12)))
    return img

def variant_C(t):
    # low lunar horizon, huge Earth over it; ion stream raining onto the regolith; foreground grains redden
    u = ease(seg(t, 0, 2.6))
    sky = M.stars().copy()
    sky = M.earth_disc(sky, 540, lerp(980, 900, u), 760, lon=-30, lat0=20, sun=SUN)
    sky = M.limb_glow(sky, 540, lerp(980, 900, u), 760, SUN)
    h = M.terrain()[0]
    arr = M.terrain_shot(700 + 160 * u, 1000, h[1000, 760] + lerp(16, 26, u), 0.05, horizon=0.58, fov=60, sun_el=14, sky=sky)
    paths = [((540 + 700 * math.sin(a), 900 - 760 * math.cos(a) * 0.2), (540 + 300 * a, 1100), (500 + 500 * a, 1300), (540 + 900 * a, 1650)) for a in np.linspace(-0.5, 0.5, 6)]
    arr = M.particles(arr, paths, t, n=300, speed=0.5, amt=0.8, spread=16)
    mac = M.macro_frame(macro(), lerp(0.2, 1.25, seg(t, 0.1, 1.6)), zoom=1.2, dof=False)
    ym = np.clip((np.arange(H) - 1450) / 250, 0, 1)[:, None, None]
    arr = arr * (1 - ym * 0.85) + mac * ym * 0.85
    img = M.finish(arr, 0.45); d = ImageDraw.Draw(img, "RGBA")
    M.hook_title(d, max(0.85, 1.15 - 0.3 * seg(t, 0, 0.12)))
    return img

V = {"A": variant_A, "B": variant_B, "C": variant_C}
def frame(args):
    v, i = args
    return V[v](i / FPS).tobytes()

if __name__ == "__main__":
    v = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 90
    macro(); M.terrain(); M.shaded(14.0)
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", f"hook{v}.mp4"], stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for b in pool.imap(frame, [(v, i) for i in range(n)]): p.stdin.write(b)
    p.stdin.close(); p.wait(); print("done", v)
