#!/usr/bin/env python3
# SPACE SECRETS — YouTube Documentary EP01: "What If the Moon Disappeared Tonight?" (1920x1080, 30 fps)
# Edit: shot list keyed to narration lines, crossfades, chapter cards, documentary subtitles, grade. Audio: Kokoro VO + score/SFX.
import json, math, os, re, subprocess, sys
from multiprocessing import Pool

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw

from gfx import *
import scenes as S
from scenes import ls, le, find, LINES, T_GONE
from sfx import SR, lp, hp, bp, envx, place, osc, boom, crack, whoosh, tick, riser, reverb, arng

FPS = 30
TIM = S.TIM
CHAPS = TIM["chapters"]
NARR_END = le(len(LINES) - 1)
T_FINALTXT = NARR_END + 0.9
T_ENDSCREEN = T_FINALTXT + 5.5
DUR = round(T_ENDSCREEN + 5.5, 1)
NF = int(DUR * FPS)

L = S
SHOTS = [
 (0, S.sh_city, dict(moon=True, gone_at=T_GONE, pz=(1.0, 1.04))),
 (1, S.sh_city, dict(moon=False, pz=(1.04, 1.08))),
 (2, S.sh_city, dict(moon=False, clouds=True, pz=(1.0, 1.05))),
 (3, S.sh_hud, {}),
 (4, S.sh_orbit, dict(mode="gone")),
 (5, S.sh_orbit, dict(mode="orbit", facts=True, zoom=(1.0, 1.1))),
 (6, S.sh_orbit, dict(vanish_at=find(6, "gone"), zoom=(1.1, 1.15))),
 (7, S.sh_questions, {}),
 (8, S.sh_timescale, {}),
 (11, S.sh_rule, {}),
 (13, S.sh_versus, {}),
 (15, S.sh_noshock, {}),
 (17, S.sh_city, dict(moon=False, walkers=True, pz=(1.0, 1.02))),
 (18, S.sh_spin, dict(axis=True)),
 (19, S.sh_city, dict(moon=False, walkers=True, pz=(1.02, 1.04))),
 (20, S.sh_city, dict(moon=False, plane=True, pz=(1.02, 1.05))),
 (21, S.sh_spin, dict(cx=1300, R=330)),
 (22, S.sh_landscape, dict(ml=(1.0, 1.0), moon=(1500, 220, 46), text=("The night sky", 23, "night", WHITE))),
 (24, S.sh_landscape, dict(ml=(1.0, 1.0), moon=(1500, 220, 46), lux=True, pan=0.3)),
 (26, S.sh_landscape, dict(ml=(1.0, 0.0, ls(26), le(26)), moon=(1500, 220, 46), lux=True, pan=0.3)),
 (27, S.sh_landscape, dict(ml=(0.0, 0.0), milky=(0.0, 1.0, ls(27), le(28)), pan=0.4)),
 (29, S.sh_landscape, dict(ml=(0.0, 0.0), milky=(1.0, 1.0), pan=0.6, text=("A darker sky, and a brighter Milky Way", 30, "universe", ICE))),
 (31, S.sh_coast, dict(title=("TIDES", "the daily rise and fall of the sea"))),
 (34, S.sh_bulge, dict(notes=[("Tidal bulges", (35, "bulges"), ICE)])),
 (37, S.sh_bulge, dict(moon_off_at=ls(38) + 1.5, notes=[("The oceans can't flatten instantly", (39, "momentum"), GOLD)])),
 (40, S.sh_basin, {}),
 (42, S.sh_bulge, dict(moon_off_at=ls(42) - 9.0, notes=[("Lunar tides fade · solar tides remain", (44, "tides"), GOLD)])),
 (45, S.sh_bars, dict(remove_at=ls(48))),
 (50, S.sh_coast, dict(amp=1.0, amp_to=0.45, flats=True, title=("COASTAL HABITATS", "smaller tides, different rhythms"))),
 (52, S.sh_coast, dict(amp=0.45, flats=True)),
 (53, S.sh_moon_tonight, {}),
 (54, S.sh_phases, {}),
 (55, S.sh_reef, dict(spawn_at=find(56, "spawning"))),
 (57, S.sh_savanna, dict(bright_to=0.0)),
 (60, S.sh_turtles, {}),
 (61, S.sh_cards, dict(title="NO OVERNIGHT COLLAPSE", items=[(("Adaptable", "animals respond to many environmental cues"), (62, "adaptable"), (130, 230, 170)),
                                                           (("Many signals", "day length, temperature, tides, moonlight"), (62, "cues"), ICE)])),
 (63, S.sh_popgraph, {}),
 (67, S.sh_foodweb, {}),
 (70, S.sh_spin, dict(Lvec=True)),
 (74, S.sh_spin, dict(clock=True, cx=760)),
 (75, S.sh_landscape, dict(ml=(0.15, 0.15), dawn=0.8)),
 (77, S.sh_sunorbit, {}),
 (78, S.sh_bulge, dict(lag=15, torque=True, show_sun=False, graph=False, marker=False)),
 (81, S.sh_daychart, {}),
 (83, S.sh_daychart, dict(nomoon_from=ls(83) + 0.4)),
 (85, S.sh_landscape, dict(ml=(0.15, 0.15), dawn=1.0, pan=0.3)),
 (86, S.sh_daychart, dict(nomoon_from=ls(86) - 5)),
 (87, S.sh_axis, dict(title=("EARTH'S TILT", GOLD, "about 23.4° from upright"))),
 (91, S.sh_seasons, {}),
 (96, S.sh_obliquity, {}),
 (98, S.sh_obliquity, dict(nomoon_at=ls(98) + 0.3)),
 (100, S.sh_axis, dict(wobble=28, title=("A WANDERING AXIS?", (255, 150, 130), "hypothetical · over geological time"))),
 (101, S.sh_insol, {}),
 (103, S.sh_axis, dict(ice=1.0, title=("ICE, HABITATS, FARMLAND", (255, 150, 130), "could shift with a changing tilt"))),
 (106, S.sh_cards, dict(title="BUT WE NEED TO BE CAREFUL", items=[
     (("Scientists don't agree", "extreme instability is not inevitable"), (107, "agree"), (255, 150, 130)),
     (("It depends on", "spin rate, gravitational interactions, timescale"), (107, "depends"), ICE),
     (("Not a prediction", "Earth would not suddenly tip onto its side"), (108, "prediction"), (130, 230, 170))])),
 (109, S.sh_system, {}),
 (111, S.sh_lunar_eclipse, {}),
 (113, S.sh_solar_eclipse, dict(total_at=ls(114) + 1.0)),
 (116, S.sh_solar_eclipse, dict(sizes=True, total_at=ls(116) + 60)),
 (118, S.sh_solar_eclipse, dict(total_at=ls(118) + 1.2)),
 (119, S.sh_transit, {}),
 (122, S.sh_phases, {}),
 (124, S.sh_lunar_surface, dict(footprint=False, earth_rise=(0.55, 0.65), text=("The first world beyond Earth where humans walked",
                                                                                "Apollo 11 · July 1969  ·  12 people walked on the Moon, 1969–1972"))),
 (126, S.sh_lunar_surface, dict(earth_rise=(0.55, 0.7))),
 (127, S.sh_weather, dict(big_no=ls(128))),
 (132, S.sh_mixing, {}),
 (135, S.sh_currents, {}),
 (138, S.sh_weather, {}),
 (141, S.sh_night_earth, dict(title=("Could humanity survive?", ls(142), WHITE))),
 (143, S.sh_night_earth, dict(title=("Almost certainly, yes.", find(143, "yes") - 0.2, GOLD), checklist=[
     ("Atmosphere", (144, "atmosphere")), ("Energy from the Sun", (145, "energy")), ("Liquid oceans", (146, "oceans")),
     ("Surface gravity almost unchanged", (147, "gravity")), ("Orbit around the Sun", (148, "orbiting"))])),
 (149, S.sh_night_earth, {}),
 (150, S.sh_cards, dict(title="THE LONGER-TERM CHALLENGES", bg="earth", items=[
     (("Coastal ecosystems", "smaller, simpler tides"), (151, "coastal"), ICE), (("Ocean dynamics", "less tidal mixing"), (152, "ocean"), TEAL),
     (("Biological rhythms", "lost lunar cues"), (153, "biological"), (130, 230, 170)), (("Rotation and climate", "a different long-term path"), (154, "rotational"), GOLD)])),
 (155, S.sh_orbit, dict(mode="plain", zoom=(1.0, 1.08))),
 (158, S.sh_orbit, dict(mode="orbit", zoom=(1.08, 1.16))),
 (160, S.sh_recede, {}),
 (163, S.sh_recede, dict(ruler=True)),
 (166, S.sh_recede, dict(dino=True)),
 (169, S.sh_moon_tonight, {}),
 (172, S.sh_lunar_surface, dict(earth_rise=(0.0, 1.0))),
]
HARD_CUTS = {1, 3}                    # indices in SHOTS that cut hard (the hook)
SHOT_T = []
for i, (li, fn, kw) in enumerate(SHOTS):
    t0 = 0.0 if i == 0 else (T_GONE if i == 1 else ls(li) - 0.35)
    SHOT_T.append(t0)
SHOT_T.append(DUR + 1)
XF = 0.5

def shot_at(t):
    for i in range(len(SHOTS)):
        if SHOT_T[i] <= t < SHOT_T[i + 1]: return i
    return len(SHOTS) - 1

def render_shot(i, t):
    li, fn, kw = SHOTS[i]
    return fn(t, SHOT_T[i], SHOT_T[i + 1], **kw)

# ------------------------------------------------------------------ subtitles (documentary style)
SUBS = []
for l in LINES:
    words = l["words"]; cur = []; chunks = []
    for w in words:
        cur.append(w)
        txt = " ".join(x[0] for x in cur)
        if (len(txt) > 58 and re.search(r"[,.?!:;]$", w[0])) or len(txt) > 74: chunks.append(cur); cur = []
    if cur: chunks.append(cur)
    for j, ch in enumerate(chunks):
        a = ch[0][1] - 0.08
        b = chunks[j + 1][0][1] - 0.08 if j + 1 < len(chunks) else ch[-1][2] + 0.35
        SUBS.append((a, b, " ".join(x[0] for x in ch)))

def draw_subs(img, t):
    for a, b, txt in SUBS:
        if a <= t < b:
            d = ImageDraw.Draw(img, "RGBA")
            f = font(F_MED, 34)
            tw = f.getlength(txt)
            al = int(255 * min(1, (t - a) / 0.12, (b - t) / 0.12))
            d.rounded_rectangle((W / 2 - tw / 2 - 22, 968 - 28, W / 2 + tw / 2 + 22, 968 + 28), 8, fill=(0, 0, 0, int(al * 0.5)))
            d.text((W / 2, 968), txt, font=f, fill=(255, 255, 255, al), anchor="mm")
            return

def draw_chapter(img, t):
    for ci, c in enumerate(CHAPS):
        if ci == 0: continue
        a, b = c["start"] - 2.7, c["start"] + 1.6
        if a <= t < b:
            k = min(seg(t, a, a + 0.6), 1 - seg(t, b - 0.6, b))
            d = ImageDraw.Draw(img, "RGBA")
            x, y = 120, 760
            d.text((x, y), f"CHAPTER {ci + 1:02d}", font=font(F_MONO, 22), fill=GOLD + (int(255 * k),), anchor="lm")
            d.line((x, y + 26, x + 80 + 380 * ease_out(k), y + 26), fill=GOLD + (int(200 * k),), width=2)
            spaced(d, (x, y + 76), c["title"], font(F_TITLE, 58), (255, 255, 255, int(255 * k)), "lm", 0.08)

def draw_outro(img, t):
    d = ImageDraw.Draw(img, "RGBA")
    if T_FINALTXT <= t < T_ENDSCREEN:
        k = min(seg(t, T_FINALTXT, T_FINALTXT + 1.2), 1 - seg(t, T_ENDSCREEN - 0.8, T_ENDSCREEN))
        spaced(d, (W / 2, 200), "THE MOON IS MORE IMPORTANT THAN IT LOOKS.", font(F_LIGHT, 52), (255, 255, 255, int(255 * k)), "mm", 0.1)

def end_screen(t):
    k = seg(t, T_ENDSCREEN, T_ENDSCREEN + 1.0)
    arr = S.stars_half_up() * 0.5
    img = finish(arr, 0.1)
    d = ImageDraw.Draw(img, "RGBA")
    spaced(d, (W / 2, 470), "SPACE SECRETS", font(F_SEMI, 92), (255, 255, 255, int(255 * k)), "mm", 0.18)
    d.line((W / 2 - 220 * k, 545, W / 2 + 220 * k, 545), fill=GOLD + (int(255 * k),), width=2)
    spaced(d, (W / 2, 600), "EXPLORE THE UNKNOWN.", font(F_LIGHT, 36), GOLD + (int(255 * k),), "mm", 0.25)
    return img

# ------------------------------------------------------------------ frame
yy_, xx_ = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1 - 0.32 * (((xx_ - W / 2) / (W / 2)) ** 2 + ((yy_ - H / 2) / (H / 2)) ** 2) ** 1.5).clip(0.5, 1)[..., None]
del yy_, xx_
GRN = np.random.default_rng(3)
GRAIN = [GRN.normal(0, 2.6, (H // 2, W // 2, 1)).astype(np.float32).repeat(2, 0).repeat(2, 1) for _ in range(4)]

def frame(fi):
    t = fi / FPS
    if t >= T_ENDSCREEN:
        img = end_screen(t)
    else:
        i = shot_at(t)
        img = render_shot(i, t)
        if i > 0 and i not in HARD_CUTS and t - SHOT_T[i] < XF:
            prev = render_shot(i - 1, t)
            img = Image.blend(prev, img, ease((t - SHOT_T[i]) / XF))
        if t >= T_ENDSCREEN - 1.0:
            img = Image.blend(img, end_screen(t), seg(t, T_ENDSCREEN - 1.0, T_ENDSCREEN))
    arr = np.asarray(img.convert("RGB"), np.float32)
    lum = arr.mean(-1, keepdims=True)
    arr = arr + (1 - np.clip(lum / 90, 0, 1)) * np.array([-1.5, 1.0, 3.0], np.float32)     # cool shadows
    arr = arr * VIG + GRAIN[fi % 4]
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    if t < T_ENDSCREEN:
        draw_chapter(img, t); draw_subs(img, t); draw_outro(img, t)
    return img.tobytes()

def render_range(a, b, out):
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for i, bts in enumerate(pool.imap(frame, range(a, b), chunksize=4)):
            p.stdin.write(bts)
            if i % 300 == 0: print(out, "frame", a + i, "/", b, flush=True)
    p.stdin.close(); p.wait()

def preview(ts, d="pv"):
    os.makedirs(d, exist_ok=True)
    for t in ts:
        Image.frombytes("RGB", (W, H), frame(int(round(t * FPS)))).resize((480, 270)).save(f"{d}/p_{int(t * 10):05d}.jpg", quality=85)

# ------------------------------------------------------------------ audio
def pad(n, chords, cut=1100):
    out = np.zeros(n)
    for ci, (t0, t1, notes, g) in enumerate(chords):
        i0, i1 = int(t0 * SR), min(n, int(t1 * SR)); m = i1 - i0
        if m <= 0: continue
        sg = np.zeros(m)
        for f in notes:
            for det in (-0.1, 0.0, 0.09): sg += osc(f * 2 ** (det / 12), m)
        fade = int(1.5 * SR)
        e = np.minimum(1, np.arange(m) / fade) * np.minimum(1, (m - np.arange(m)) / fade)
        out[i0:i1] += sg * e / 12 * g
    return lp(out, cut) * 0.7 + lp(out, 380) * 0.6

def keys(n, events):
    """Soft felt-piano-like plucks: (time, freq, gain)."""
    out = np.zeros(n)
    for t0, f, g in events:
        m = int(3.0 * SR); tt = np.arange(m) / SR
        s = (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(4 * np.pi * f * tt) + 0.12 * np.sin(6 * np.pi * f * tt)) * np.exp(-tt / 0.9) * np.minimum(1, tt / 0.004)
        place(out, s * g, t0)
    return lp(out, 3500)

PROG = {  # chapter -> chord roots (Hz) cycled through the chapter; mood per chapter
 0: [(55.0, 82.41, 130.81, 164.81), (49.0, 73.42, 116.54, 146.83)], 1: [(65.41, 98.0, 155.56, 196.0), (58.27, 87.31, 138.59, 174.61)],
 2: [(55.0, 82.41, 130.81, 164.81), (61.74, 92.5, 146.83, 185.0)], 3: [(65.41, 98.0, 164.81, 196.0), (73.42, 110.0, 174.61, 220.0)],
 4: [(55.0, 82.41, 130.81, 164.81), (49.0, 73.42, 123.47, 146.83)], 5: [(51.91, 77.78, 123.47, 155.56), (46.25, 69.3, 110.0, 138.59)],
 6: [(65.41, 98.0, 164.81, 196.0), (55.0, 82.41, 138.59, 164.81)], 7: [(58.27, 87.31, 146.83, 174.61), (55.0, 82.41, 130.81, 164.81)],
 8: [(65.41, 98.0, 164.81, 196.0), (73.42, 110.0, 185.0, 220.0)], 9: [(65.41, 98.0, 164.81, 196.0), (87.31, 130.81, 220.0, 261.63), (73.42, 110.0, 174.61, 220.0), (98.0, 146.83, 246.94, 293.66)],
}

def render_audio(out):
    n = int(DUR * SR); tt = np.arange(n) / SR
    chords = []
    for ci, c in enumerate(CHAPS):
        t0 = c["start"] - 2.5 if ci else T_GONE + 1.4
        t1 = (CHAPS[ci + 1]["start"] - 2.5) if ci + 1 < len(CHAPS) else DUR
        prog = PROG[ci]; step = 9.0 if ci < 9 else 6.0; k = 0; t = t0
        while t < t1:
            chords.append((t, min(t1, t + step) + 1.5, prog[k % len(prog)], 1.0)); t += step; k += 1
    mus = pad(n, chords)
    mus += osc(41.2, n, "sin") * 0.18
    # gentle keys in the emotional chapters (humanity, final revelation, end)
    ev = []
    for ci in (8, 9):
        t0 = CHAPS[ci]["start"]; t1 = CHAPS[ci + 1]["start"] - 2.5 if ci + 1 < len(CHAPS) else DUR - 2
        prog = PROG[ci]; t = t0; k = 0
        while t < t1:
            notes = prog[(k // 4) % len(prog)]
            ev.append((t, notes[2 + (k % 2)] * 2, 0.10 if ci == 8 else 0.13)); t += 1.5; k += 1
    mus += keys(n, ev)
    # chapter breaks: soft swell + low hit
    fx = np.zeros(n)
    for ci, c in enumerate(CHAPS):
        if ci == 0: continue
        place(fx, riser(2.0, 70) * 0.5, c["start"] - 2.7, 0.35); place(fx, reverb(boom(2.0, 70, 30, 0.7), 3.0, 0.5), c["start"] - 0.7, 0.45)
    # hook: city ambience, the moment of disappearance, silence
    amb = lp(arng.normal(0, 1, n), 300) * 0.25
    lvl_amb = np.interp(tt, [0, T_GONE - 0.01, T_GONE + 0.01, T_GONE + 1.3, T_GONE + 3.5, DUR], [0.8, 0.8, 0.0, 0.0, 0.35, 0.35])
    place(fx, reverb(boom(3.5, 110, 22, 1.3), 4.0, 0.45), T_GONE, 1.6); place(fx, crack(0.4) * 0.3, T_GONE, 0.4)
    # punctuation at key moments
    marks = [(ls(4), 0.5), (find(6, "gone"), 0.7), (ls(12), 0.3), (ls(23), 0.4), (ls(27), 0.3), (ls(38) + 1.5, 0.35), (ls(48), 0.35),
             (find(56, "spawning"), 0.3), (ls(71), 0.4), (ls(89), 0.35), (ls(98), 0.45), (ls(107), 0.35), (ls(112), 0.4),
             (ls(118) + 1.2, 0.5), (ls(128), 0.6), (find(143, "yes"), 0.45), (ls(161), 0.4), (ls(173), 0.4)]
    for t0, g in marks: place(fx, reverb(boom(1.8, 80, 30, 0.55), 3.0, 0.45), t0, g)
    for t0 in (ls(118) + 1.0, ls(114) + 0.8):                                   # totality shimmer
        m = int(4 * SR); s = sum(np.sin(2 * np.pi * f * np.arange(m) / SR) for f in (1318.5, 1975.5, 2637.0)) / 3
        place(fx, s * np.minimum(1, np.arange(m) / (0.8 * SR)) * np.exp(-np.arange(m) / SR / 1.6), t0, 0.06)
    for li in (31, 50):                                                         # waves
        m = int((ls(li + 2) - ls(li) + 1) * SR); s = lp(arng.normal(0, 1, m), 500) * (0.6 + 0.4 * np.sin(2 * np.pi * np.arange(m) / SR / 7.0) ** 2)
        place(fx, s * np.minimum(1, np.arange(m) / SR / 1.0) * np.minimum(1, (m - np.arange(m)) / SR / 1.0), ls(li) - 0.3, 0.35)
    m = int((le(30) - ls(27)) * SR); place(fx, lp(arng.normal(0, 1, m), 900) * 0.15 * np.minimum(1, np.arange(m) / SR / 2), ls(27), 0.5)  # night air
    place(fx, whoosh(1.2), T_ENDSCREEN - 0.6, 0.25)
    mus_lvl = np.interp(tt, [0, T_GONE - 0.02, T_GONE + 0.02, T_GONE + 1.3, T_GONE + 3.0, NARR_END, NARR_END + 2, DUR - 1.5, DUR],
                        [0.55, 0.6, 0.0, 0.0, 0.8, 0.85, 1.15, 1.0, 0.0])
    mus = mus * mus_lvl + amb * lvl_amb
    vo = np.zeros(n)
    for l in LINES:
        s, _ = sf.read(l["file"]); place(vo, s, l["start"])
    vo = lp(hp(vo, 80), 13000); vo = vo / (np.abs(vo).max() + 1e-9) * 0.9
    env = lp(np.abs(vo), 5); env /= env.max() + 1e-9
    duck = 1 - 0.6 * np.clip(env * 3, 0, 1)
    mix = vo + mus * 0.085 * duck + fx * 0.26 * (0.5 + 0.5 * duck)
    mix = np.tanh(mix * 1.05) * 0.95
    sf.write(out, np.stack([mix, mix], 1).astype(np.float32), SR, subtype="FLOAT")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "preview":
        preview([float(x) for x in sys.argv[2:]])
    elif cmd == "audio":
        render_audio("mix.wav"); print("audio done", DUR)
    elif cmd == "range":
        render_range(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
    elif cmd == "info":
        print("DUR", DUR, "NF", NF, "shots", len(SHOTS))
        for i, (li, fn, kw) in enumerate(SHOTS): print(i, li, fn.__name__, round(SHOT_T[i], 2), round(SHOT_T[i + 1] - SHOT_T[i], 1))
