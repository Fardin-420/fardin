"""THE 20-MINUTE HEIST — score fallback, SFX on cue frames, VO-driven ducking, master.

No licensed tracks were supplied in assets/music/, so every act gets a generated bed
(dark drones, sub pulses, clock ticks, tape-warped pad for 2019, arps for the freeze,
choir-like pad for the attribution, sparse piano for the aftermath). Every SFX sits on
a timeline cue, punch, impact or transition frame. Music ducks ~12 dB under the voice.
Master: two-pass ffmpeg loudnorm to −14 LUFS integrated, true peak ≤ −1 dBTP.

    .venv/bin/python scripts/sound.py
Outputs audio/mix_master.wav (48 kHz stereo 24-bit) + audio/loudness.json
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parents[1] / "SOUND_ENGINE"))
import sound_engine as se  # noqa: E402  (studio primitives: sub_impact, riser, whoosh, glitch, …)

SR = se.SR
FPS = 30
rng = np.random.default_rng(2026)
MUSIC_DIR = ROOT / "assets" / "music"

# ───────────────────────── extra designs ─────────────────────────


def mix_(*xs):
    """Sum stereo/mono clips of different lengths (zero-padded)."""
    xs = [x if x.ndim == 2 else st(x) for x in xs]
    n = max(len(x) for x in xs)
    out = np.zeros((n, 2))
    for x in xs:
        out[: len(x)] += x
    return out


def t_(d):
    return np.arange(se.secs(d)) / SR


def st(m, p=0.0):
    return se.pan(m, p)


def tick(level=0.35, f=3200):
    t = t_(0.03)
    x = np.sin(2 * np.pi * f * t) * np.exp(-t * 300) + se.bandpass(rng.standard_normal(len(t)), 2000, 6000, 2) * np.exp(-t * 400) * 0.6
    return st(x * level)


def clock_ticks(dur, every=1.0, level=0.3):
    out = np.zeros((int(dur * SR), 2))
    k = 0
    while k * every < dur - 0.05:
        x = tick(level * (1 if k % 2 == 0 else 0.7), 3400 if k % 2 == 0 else 2700)
        i = int(k * every * SR)
        out[i:i + len(x)] += x[: len(out) - i]
        k += 1
    return out


def heartbeat(level=0.8):
    out = np.zeros((int(1.0 * SR), 2))
    for off, g in ((0, 1.0), (0.22, 0.65)):
        x = se.sub_impact(0.5 * g * level, 65, 38, 0.5)
        i = int(off * SR)
        out[i:i + len(x)] += x[: len(out) - i]
    return out


def ching():
    t = t_(1.6)
    m = sum(np.sin(2 * np.pi * f * t) * np.exp(-t * d) / (k + 1) for k, (f, d) in enumerate([(2093, 3), (3136, 4), (4186, 5), (5274, 6)]))
    m[: int(0.002 * SR)] *= np.linspace(0, 1, int(0.002 * SR))
    return se.verb(st(m * 0.35, 0.2), se.IR_ROOM, 0.25)


def ice_crack(seed=0):
    r = np.random.default_rng(seed)
    out = se.shatter(0.9, seed=seed, count=50) * 0.7
    t = t_(0.9)
    crack = se.highpass(r.standard_normal(len(t)), 3000) * np.exp(-t * 30) * 0.5
    crack += np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 18) * 0.15
    return mix_(out, st(crack, r.uniform(-0.3, 0.3)))


def alarm2(dur=1.4, level=0.18):
    t = t_(dur)
    f = np.where((t * 2.5).astype(int) % 2 == 0, 880, 660)
    m = signal.square(2 * np.pi * np.cumsum(f) / SR) * 0.3 + np.sin(2 * np.pi * np.cumsum(f) / SR)
    m = se.lowpass(m, 2500) * np.sin(np.linspace(0, np.pi, len(t))) ** 0.3
    return se.verb(st(m * level), se.IR_ROOM, 0.3)


def paper(level=0.3):
    t = t_(0.25)
    m = se.bandpass(rng.standard_normal(len(t)), 1200, 7000, 2) * np.sin(np.linspace(0, np.pi, len(t))) ** 2 * (1 + 0.5 * np.sin(t * 90))
    return st(m * level, rng.uniform(-0.3, 0.3))


def stamp_thud():
    return mix_(se.sub_impact(0.35, 110, 50, 0.7), paper(0.2))


def lock_click():
    t = t_(0.25)
    m = (np.sin(2 * np.pi * 2600 * t) * np.exp(-t * 90) + se.highpass(rng.standard_normal(len(t)), 4000) * np.exp(-t * 200)) * 0.5
    m2 = np.roll(m, int(0.045 * SR)) * 0.7
    return st(m + m2)


def rewind(dur=1.2):
    return se.whoosh(dur, 4000, 300, 0.8, -0.8)[::-1] * 0.8


def pen(dur=1.0):
    t = t_(dur)
    m = se.bandpass(rng.standard_normal(len(t)), 2500, 8000, 2) * (0.5 + 0.5 * np.abs(np.sin(t * 2 * np.pi * 3.3))) * 0.18
    return st(m, 0.1)


def ui_blip(f=1600):
    return se.blip(f, 0.12) * 0.6


def down_sweep(dur=1.2):
    t = t_(dur)
    f = 900 * np.exp(-t * 2.2) + 80
    return st(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.5) * 0.25)


def drop(level=1.0):
    return mix_(se.sub_impact(1.2 * level, 95, 28, 3.2), se.shockwave(1.4) * 0.5)


# ───────────────────────── score (procedural fallback) ─────────────────────────

D1 = 36.71


def pad(dur, freqs, cutoff=900, wow=0.0, level=0.2):
    t = t_(dur)
    m = np.zeros(len(t))
    for f in freqs:
        for det in (0.996, 1.0, 1.004):
            ph = 2 * np.pi * np.cumsum(f * det * (1 + wow * np.sin(2 * np.pi * 0.6 * t))) / SR
            m += signal.sawtooth(ph) * 0.5 + np.sin(ph) * 0.5
    m = se.lowpass(m / (len(freqs) * 3), cutoff, 2)
    lfo = 0.7 + 0.3 * np.sin(2 * np.pi * t / 7.3)
    s = np.stack([m * lfo, np.roll(m, int(0.011 * SR)) * lfo], axis=1)
    return s * level


def pluck(f, dur=0.6, bright=1.0):
    t = t_(dur)
    m = sum(np.sin(2 * np.pi * f * h * t) * np.exp(-t * (6 + 4 * h / bright)) / h for h in (1, 2, 3, 4))
    m[: 96] *= np.linspace(0, 1, 96)
    return m


def piano(f, dur=3.0):
    t = t_(dur)
    m = sum(np.sin(2 * np.pi * f * h * (1 + 0.0004 * h * h) * t) * np.exp(-t * (1.2 + 0.9 * h)) / (h ** 1.3) for h in range(1, 7))
    m[: 48] *= np.linspace(0, 1, 48)
    return m * 0.5


def place(buf, at, x, gain=1.0):
    i = int(at * SR)
    if i >= len(buf) or i + len(x) <= 0:
        return
    if i < 0:
        x, i = x[-i:], 0
    j = min(len(buf), i + len(x))
    if x.ndim == 1:
        x = st(x)
    buf[i:j] += x[: j - i] * gain


def act_music(name, dur, ctx):
    """ctx: dict of act-relative times (s) for hits/cuts."""
    n = se.secs(dur)
    out = np.zeros((n, 2))
    t = np.arange(n) / SR
    if name == "act1_coldopen":
        out += se.drone(dur) * 0.55
        out += pad(dur, [D1 * 2, D1 * 3, D1 * 4 * 1.189], 500, level=0.12)
        beat = 60 / 72
        k = 0
        while k * beat < dur:
            place(out, k * beat, se.sub_impact(0.18, 70, 40, 0.6))
            k += 1
        out += clock_ticks(dur, 1.0, 0.12)
    elif name == "act2_flashback":
        out += pad(dur, [D1 * 4, D1 * 4 * 1.189, D1 * 6, D1 * 8], 1400, wow=0.004, level=0.16)
        beat = 60 / 84
        k = 0
        while k * beat < dur:
            place(out, k * beat, st(se.lowpass(pluck(D1 * 8 * (1.0 if k % 4 else 1.335), 0.5, 0.6), 1800) * 0.12, -0.2))
            k += 1
        hiss = se.bandpass(rng.standard_normal(n), 3000, 9000, 2) * 0.006
        out += st(hiss)
    elif name == "act3_heist":
        out += se.drone(dur) * 0.5
        bpm = 104
        beat = 60 / bpm
        k = 0
        while k * beat < dur:
            tt = k * beat
            g = 0.15 + 0.25 * min(1, tt / max(ctx.get("build", dur), 1))
            place(out, tt, se.sub_impact(g, 75, 40, 0.5))
            if k % 2:
                place(out, tt, tick(0.10, 5200))
            k += 1
        arp = [D1 * 8, D1 * 8 * 1.189, D1 * 12, D1 * 16]
        k = 0
        while k * beat / 2 < dur:
            place(out, k * beat / 2, st(se.lowpass(pluck(arp[k % 4], 0.3), 2600) * 0.05, 0.3 if k % 2 else -0.3))
            k += 1
    elif name == "act4_freeze":
        out += pad(dur, [D1 * 4, D1 * 6, D1 * 4 * 1.498 * 2], 1800, level=0.11)
        bpm = 118
        notes = [D1 * 16, D1 * 16 * 1.189, D1 * 24, D1 * 16 * 1.498, D1 * 32, D1 * 24]
        k = 0
        while k * 60 / bpm / 2 < dur:
            place(out, k * 60 / bpm / 2, st(pluck(notes[k % 6], 0.35, 1.5) * 0.045, np.sin(k) * 0.5))
            k += 1
        out += clock_ticks(dur, 60 / bpm, 0.07)
        place(out, 0, se.drone(dur) * 0.35)
    elif name == "act5_name":
        # choir-like: saws through vowel formants
        base = pad(dur, [D1 * 2, D1 * 3, D1 * 4 * 1.189, D1 * 6], 2400, level=0.5)
        b, a = signal.butter(2, [600 / (SR / 2), 900 / (SR / 2)], "band")
        b2, a2 = signal.butter(2, [1000 / (SR / 2), 1300 / (SR / 2)], "band")
        ch = signal.lfilter(b, a, base, axis=0) + signal.lfilter(b2, a2, base, axis=0) * 0.6
        out += se.verb(ch * 0.55, se.IR_HALL, 0.4)
        out += se.drone(dur) * 0.55
    elif name == "act6_aftermath":
        out += pad(dur, [D1 * 4, D1 * 6, D1 * 8 * 1.189], 700, level=0.07) * np.clip(1 - t / dur * 0.7, 0.2, 1)[:, None]
        seq = [D1 * 8, D1 * 8 * 1.189, D1 * 12, D1 * 8 * 1.335, D1 * 8 * 1.189]
        k = 0
        while k * 3.2 < dur - 4:
            place(out, k * 3.2, st(piano(seq[k % 5]) * 0.16 * max(0.25, 1 - k * 3.2 / dur), -0.15))
            k += 1
        if "lownote" in ctx:
            place(out, ctx["lownote"], se.verb(st(piano(D1 * 2, 6.0) * 0.5), se.IR_HALL, 0.35))
    elif name == "act7_outro":
        out += pad(dur, [D1 * 4, D1 * 6, D1 * 4 * 1.26 * 2, D1 * 9], 1500, level=0.12)
        k = 0
        while k * 60 / 80 < dur:
            place(out, k * 60 / 80, se.sub_impact(0.12, 70, 40, 0.5))
            k += 1
        fade = np.ones(n)
        f = int(2.5 * SR)
        fade[-f:] = np.linspace(1, 0, f)
        out *= fade[:, None]
    return out


def load_or_make(name, dur, ctx):
    for ext in (".wav", ".mp3", ".flac", ".m4a"):
        p = MUSIC_DIR / f"{name}{ext}"
        if p.exists():
            y, sr = sf.read(p, always_2d=True)
            if sr != SR:
                y = signal.resample_poly(y, SR, sr, axis=0)
            y = np.tile(y, (int(np.ceil(dur * SR / len(y))), 1))[: int(dur * SR)]
            return y[:, :2] if y.shape[1] >= 2 else np.repeat(y, 2, axis=1), "licensed"
    return act_music(name, dur, ctx), "generated"


# ───────────────────────── build ─────────────────────────


def main():
    tl = json.loads((ROOT / "script" / "timeline.json").read_text())
    sc = {s["id"]: s for s in tl["scenes"]}
    total = tl["durationInFrames"] / FPS
    N = int(total * SR)
    vo, _ = sf.read(ROOT / "audio" / "vo_track.wav", always_2d=True)
    vo = np.repeat(vo[:N], 2, axis=1) if vo.shape[1] == 1 else vo[:N]
    if len(vo) < N:
        vo = np.vstack([vo, np.zeros((N - len(vo), 2))])

    def T(sid, cue=None, frames=None):
        s = sc[sid]
        f = s["start"] + (s["cues"][cue] if cue else 0) + (frames or 0)
        return f / FPS

    def start(sid):
        return sc[sid]["start"] / FPS

    def end(sid):
        return sc[sid]["end"] / FPS

    # ---------- music acts ----------
    acts = [
        ("act1_coldopen", 0, end("S02"), {}),
        ("act2_flashback", start("S03"), end("S03"), {}),
        ("act3_heist", start("S04"), end("S05"), {"build": T("S05", "onefit") - start("S04")}),
        ("act4_freeze", start("S06"), end("S06"), {}),
        ("act5_name", start("S07"), end("S07"), {}),
        ("act6_aftermath", start("S08"), end("S09"), {"lownote": T("S09", "years") - start("S08") + 1.0}),
        ("act7_outro", start("S10"), total, {}),
    ]
    music = np.zeros((N, 2))
    sources = {}
    XF = 1.5
    for name, a, b, ctx in acts:
        a0 = max(0, a - XF / 2)
        b0 = min(total, b + XF / 2)
        y, src = load_or_make(name, b0 - a0, ctx)
        sources[name] = src
        env = np.ones(len(y))
        k = int(XF * SR)
        if a0 > 0:
            env[:k] = np.linspace(0, 1, k)
        if b0 < total:
            env[-k:] = np.linspace(1, 0, k)
        place(music, a0, y * env[:, None])

    # dramatic music cuts (spec): out on "Billions." → back under the montage; hard cut at "Exactly one matched."
    def gate(a, b, fade=0.05, floor=0.0):
        i, j = int(a * SR), int(b * SR)
        f = int(fade * SR)
        g = np.ones(N)
        g[i:j] = floor
        g[max(0, i - f):i] = np.linspace(1, floor, i - max(0, i - f))
        g[j:j + f] = np.linspace(floor, 1, len(g[j:j + f]))
        return g

    g = gate(T("S01", "billions") - 0.02, T("S01", "montage"), 0.04)
    g *= gate(T("S05", "onefit") - 0.02, T("S05", "sweeper") - 0.1, 0.03)
    g *= gate(T("S01", "laptop"), T("S01", "laptop") + 1.6, 0.2, 0.15)
    g *= gate(T("S09", "moved") - 0.5, T("S09", "years") + 0.2, 0.8, 0.35)  # thinning to near-silence
    music *= g[:, None]

    # ---------- SFX ----------
    sfx = np.zeros((N, 2))
    add = lambda at, x, gain=1.0: place(sfx, at, x, gain)

    for s in tl["scenes"]:
        sid, s0 = s["id"], s["start"] / FPS
        tr = s["transitionIn"]["type"]
        if sid != "S01":
            if tr == "dipBlack":
                add(s0, se.sub_impact(0.7, 80, 30, 2.4))
            elif tr == "filmBurn":
                add(s0 - 0.9, se.reverse_swell(0.9), 0.8)
                add(s0 - 0.3, se.whoosh(0.7, 400, 3000), 0.5)
            elif tr == "iceWipe":
                add(s0 - 0.2, ice_crack(7), 0.9)
            elif tr == "dataWipe":
                add(s0 - 0.2, se.glitch(0.3, 30, 3), 0.5)
                add(s0, ui_blip(2200))
            elif tr == "cut":
                add(s0, heartbeat(0.9))
        if s["chapter"]:
            add(s0 + 14 / FPS - 0.9, se.reverse_swell(0.9), 0.7)
            add(s0 + 14 / FPS, se.sub_impact(0.55, 85, 32, 2.2))
        for p in s["punches"]:
            add(s0 + p / FPS - 0.3, se.whoosh(0.32, 600, 5000, -0.4, 0.4), 0.55)
            add(s0 + p / FPS, se.sub_impact(0.3, 100, 45, 0.9))
        for p in s["impacts"]:
            add(s0 + p / FPS, se.sub_impact(1.0, 90, 30, 2.8))
            add(s0 + p / FPS, se.glitch(0.25, 34, p % 9), 0.5)
        # soft cut whoosh on every cue (shots are cue-driven); specific designs below add character
        for name, f in s["cues"].items():
            if name in ("titlecard", "endscreen"):
                continue
            add(s0 + f / FPS - 0.18, se.whoosh(0.28, 900, 6000, -0.3, 0.3), 0.18)

    C = lambda sid, cue, off=0.0: T(sid, cue) + off
    # S01
    add(T("S01") + 6 / FPS, clock_ticks(C("S01", "binance") - T("S01") - 0.2, 1.0, 0.45))
    add(C("S01", "binance"), se.riser(1.4, 150, 2400), 0.35)
    add(C("S01", "total"), ui_blip(1200))
    add(C("S01", "safe"), se.metal_slide(1.0, 700, 200), 0.4)
    add(C("S01", "corridor"), alarm2(1.6, 0.08))
    add(C("S01", "laptop") + 0.1, heartbeat(1.0))
    add(C("S01", "laptop") + 0.95, heartbeat(0.7))
    for k in range(5):
        add(C("S01", "montage") + 2.2 + k * 0.9, se.glitch(0.2, 20, k), 0.45)
    add(C("S01", "question"), se.glitch(0.4, 40, 11), 0.6)
    add(C("S01", "titlecard") - 0.9, se.reverse_swell(0.9), 0.9)
    add(C("S01", "titlecard") + 26 / FPS, drop(0.8))
    # S02
    add(C("S02", "users"), clock_ticks(1.2, 0.06, 0.15))
    add(C("S02", "custody"), clock_ticks(1.0, 0.06, 0.15))
    add(C("S02", "vault"), se.metallic(1.2, 220, 4, 0.6), 0.35)
    add(C("S02", "register"), ching(), 0.9)
    add(C("S02", "street") - 0.6, se.whoosh(0.8, 200, 2000), 0.5)
    # S03
    add(C("S03", "7000") + 0.4, ui_blip(1400))
    add(C("S03", "7000") + 0.8, se.typing(1.6, 3, 18), 0.6)
    for k in range(3):
        add(C("S03", "apikeys") + k * 8 / FPS, paper(0.35))
    add(C("S03", "phishing") + 0.8, se.glitch(0.2, 18, 5), 0.4)
    add(C("S03", "waited"), clock_ticks(2.0, 0.08, 0.12))
    add(C("S03", "quote2019") + 0.2, se.typing(1.0, 4, 20), 0.5)
    add(C("S03", "alarm"), alarm2(1.6, 0.14))
    add(C("S03", "rewrite"), rewind(1.2), 0.6)
    add(C("S03", "rewrite") + 1.15, se.shatter(0.8, 3, 40), 0.6)
    add(C("S03", "quoteCZ") + 0.2, se.typing(1.2, 6, 20), 0.5)
    add(C("S03", "safu"), se.shatter(1.6, 9, 120), 0.35)
    add(C("S03", "2022"), se.glitch(0.3, 30, 8), 0.5)
    add(C("S03", "2022"), se.sub_impact(0.4, 90, 40, 1.2))
    add(C("S03", "around") + 50 / FPS, se.riser(2.5, 200, 2000), 0.3)
    # S04
    for cue in ("laptop2", "container", "unauth"):
        add(C("S04", cue), ui_blip(1500))
    add(C("S04", "additional"), se.glitch(0.35, 36, 2), 0.55)
    add(C("S04", "oneclick"), se.typing(1.1, 7, 20), 0.5)
    add(C("S04", "36h") - 0.2, paper(0.4))
    for k in range(3):
        add(C("S04", "36h") + (16 + k * 14) / FPS, ui_blip(900 + k * 150))
    add(C("S04", "nokeys") + 0.2, stamp_thud())
    add(C("S04", "sign"), pen(1.0))
    add(C("S04", "20min"), heartbeat(0.9))
    add(C("S04", "20min"), clock_ticks(C("S05", "t2005") - C("S04", "20min") - 2.6, 0.5, 0.25))
    # S05
    add(C("S05", "xrp"), alarm2(1.0, 0.07))
    for k in range(9):
        add(C("S05", "ordinary") + k * 0.1, stamp_thud(), 0.4)
    add(C("S05", "t2020"), ui_blip(2000))
    add(C("S05", "fifty"), ui_blip(1700))
    add(C("S05", "slips"), se.typing(2.2, 12, 26), 0.6)
    add(C("S05", "onefit"), lock_click(), 1.0)
    add(C("S05", "sweeper") - 0.1, drop(1.0))
    add(C("S05", "sweeper"), se.whoosh(1.2, 200, 3000, -0.8, 0.8), 0.5)
    add(C("S05", "eth167"), clock_ticks(1.4, 0.05, 0.12))
    add(C("S05", "gone"), se.sub_impact(0.5, 60, 28, 3.0))
    add(C("S05", "wave2"), se.glitch(0.35, 40, 21), 0.6)
    add(C("S05", "wave2") + 0.2, alarm2(1.2, 0.07))
    # S06
    for k, cue in enumerate(("t2101", "t2104", "others", "arb")):
        add(C("S06", cue) + 0.2, ice_crack(k), 0.85)
    add(C("S06", "others") + 0.4, ice_crack(9), 0.6)
    add(C("S06", "t2124"), se.typing(1.0, 13, 20), 0.5)
    add(C("S06", "t2125"), clock_ticks(0.8, 0.05, 0.12))
    add(C("S06", "suspend") - 0.1, alarm2(1.8, 0.16))
    add(C("S06", "suspend"), se.sub_impact(0.6, 85, 35, 2.0))
    add(C("S06", "frozen3"), clock_ticks(1.4, 0.45, 0.2))
    add(C("S06", "nofreeze") + 0.4, se.shatter(1.0, 14, 50), 0.4)
    add(C("S06", "remain"), clock_ticks(1.2, 0.05, 0.12))
    add(C("S06", "peel"), clock_ticks(2.0, 0.3, 0.1))
    # S07
    add(C("S07", "tt") + 0.6, stamp_thud(), 1.0)
    add(C("S07", "bitget") - 0.2, se.whoosh(1.0, 200, 2500), 0.45)
    add(C("S07", "fbi"), se.typing(1.6, 15, 22), 0.5)
    add(C("S07", "deny") - 1.2, paper(0.3))
    for k in range(3):
        add(C("S07", "bybit") - 10 / FPS + k * 8 / FPS, se.sub_impact(0.35, 90, 40, 1.4))
    add(C("S07", "dmm"), ui_blip(1300))
    add(C("S07", "dmm") + 0.6, alarm2(0.5, 0.05))
    step = round((T("S07", "remember") - T("S07", "playbook")) * FPS / 5)
    for k in range(3):
        add(C("S07", "playbook") + k * step / FPS, se.sub_impact(0.5, 100, 40, 1.4))
    add(C("S07", "burst"), drop(0.9))
    add(C("S07", "burst"), se.shatter(1.3, 17, 90), 0.5)
    # S08
    add(C("S08", "btclow"), down_sweep(1.4))
    add(C("S08", "634"), clock_ticks(0.8, 0.05, 0.1))
    add(C("S08", "teng"), se.typing(1.6, 18, 22), 0.45)
    for k in range(8):
        add(C("S08", "withdraw") + (8 + k * 9) / FPS, ui_blip(1200 + k * 80), 0.7)
    add(C("S08", "net"), se.riser(1.2, 200, 1500), 0.2)
    add(C("S08", "98"), se.typing(0.8, 19, 20), 0.45)
    add(C("S08", "95"), ui_blip(1800))
    # S09
    add(C("S09", "q1"), paper(0.35))
    add(C("S09", "nov3"), ui_blip(1000))
    add(C("S09", "hr"), ui_blip(1400))
    add(C("S09", "ceo") + 1.0, se.glitch(0.3, 30, 31), 0.5)
    add(C("S09", "assignment") + 0.2, alarm2(0.6, 0.06))
    add(C("S09", "token"), alarm2(0.6, 0.06))
    add(C("S09", "q3"), paper(0.3))
    add(C("S09", "q4") + 1.0, stamp_thud(), 0.7)
    add(C("S09", "y2026") + 1.0, se.riser(1.4, 150, 1800), 0.3)
    add(C("S09", "moved"), clock_ticks(1.8, 0.09, 0.2))
    # S10
    for k in range(1, 5):
        add(C("S10", f"tip{k}") + 0.2, ui_blip(1100 + k * 120), 0.6)

    # room tone everywhere (keeps silences alive, never digital black)
    room = se.lowpass(rng.standard_normal(N), 1200, 2) * 10 ** (-62 / 20)
    room = np.stack([room, np.roll(room, 977)], axis=1)

    # ---------- mix ----------
    def rms_env(x, att=0.04, rel=0.45):
        m = np.abs(x.mean(axis=1))
        a = signal.lfilter([1 - np.exp(-1 / (att * SR))], [1, -np.exp(-1 / (att * SR))], m)
        r = signal.lfilter([1 - np.exp(-1 / (rel * SR))], [1, -np.exp(-1 / (rel * SR))], m)
        return np.maximum(a, r)

    e = rms_env(vo)
    act = np.clip(e / (np.percentile(e[e > 1e-4], 50) * 0.35 + 1e-9), 0, 1)
    duck_m = 10 ** (-12 * act / 20)  # music −12 dB under voice
    duck_s = 10 ** (-4 * act / 20)  # SFX −4 dB under voice

    def norm_to(x, lufs_target):
        import pyloudnorm as pyln

        meter = pyln.Meter(SR)
        l = meter.integrated_loudness(x)
        return x * 10 ** ((lufs_target - l) / 20) if np.isfinite(l) else x

    vo_n = norm_to(vo, -16.0)
    mus_n = norm_to(music, -21.0) * duck_m[:, None]
    sfx_pk = np.max(np.abs(sfx)) + 1e-9
    sfx_n = sfx / sfx_pk * 10 ** (-8 / 20) * duck_s[:, None]  # loudest SFX ≈ −8 dBFS pre-master
    mix = vo_n + mus_n + sfx_n + room
    # gentle glue + safety
    mix = np.tanh(mix * 0.95) / 0.95

    (ROOT / "audio" / "stems").mkdir(parents=True, exist_ok=True)
    pre = ROOT / "audio" / "mix_pre.wav"
    sf.write(pre, mix.astype(np.float32), SR, subtype="FLOAT")
    for nm, x in (("vo", vo_n), ("music", mus_n), ("sfx", sfx_n)):
        sf.write(ROOT / "audio" / "stems" / f"{nm}.wav", x.astype(np.float32), SR, subtype="FLOAT")

    # ---------- master: two-pass loudnorm → −14 LUFS, TP −1.5 ----------
    out = ROOT / "audio" / "mix_master.wav"
    p1 = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(pre), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True)
    m = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", p1.stderr, re.S).group(0))
    af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(pre), "-af", af, "-ar", str(SR), "-c:a", "pcm_s24le", str(out)], check=True)
    rep = measure(out)
    rep["music_sources"] = sources
    (ROOT / "audio" / "loudness.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))


def measure(path: Path) -> dict:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    summ = r[r.rfind("Summary:"):]
    I = float(re.search(r"I:\s+(-?[\d.]+) LUFS", summ).group(1))
    LRA = float(re.search(r"LRA:\s+(-?[\d.]+) LU", summ).group(1))
    TP = float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", summ).group(1))
    return {"file": path.name, "integrated_lufs": I, "true_peak_dbtp": TP, "lra_lu": LRA}


if __name__ == "__main__":
    main()
