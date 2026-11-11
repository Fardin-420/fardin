#!/usr/bin/env python3
"""synth.py — procedural score + SFX, frame-synced to build/timeline.json.

Writes (48 kHz stereo float WAV):
  build/audio/music.wav   dark orchestral bed in D minor (string drones, ostinato, timpani, cello,
                          climax, hard cut, silence) — loudness-normalized later in mix.py
  build/audio/sfx.wav     every SFX cue from the timeline, each instance peak-normalized to its
                          cue gain (dBFS)

Nothing is sampled: every sound is built from oscillators, filtered noise and a synthesized
exponential-decay impulse response (convolution reverb). All randomness is seeded (1945).
"""
from __future__ import annotations

import json
import sys
import zlib
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, fftconvolve, sosfilt

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
OUT = BUILD / "audio"
SR = 48000
SEED = 1945


# ================================================================================================
# DSP helpers
# ================================================================================================
def rng_for(*keys) -> np.random.Generator:
    """Deterministic generator from the global seed + keys (crc32, NOT Python's salted hash())."""
    return np.random.default_rng([SEED, *[k if isinstance(k, int) else zlib.crc32(str(k).encode()) for k in keys]])


def n_of(sec: float) -> int:
    return int(round(sec * SR))


def tvec(n: int) -> np.ndarray:
    return np.arange(n) / SR


def _sos(kind, f, order=2):
    nyq = SR / 2
    if isinstance(f, (list, tuple)):
        f = [min(max(x, 10), nyq * 0.95) for x in f]
    else:
        f = min(max(f, 10), nyq * 0.95)
    return butter(order, f, kind, fs=SR, output="sos")


def lp(x, f, order=2):
    return sosfilt(_sos("lowpass", f, order), x, axis=-1)


def hp(x, f, order=2):
    return sosfilt(_sos("highpass", f, order), x, axis=-1)


def bp(x, lo, hi, order=2):
    return sosfilt(_sos("bandpass", [lo, hi], order), x, axis=-1)


def white(n, r):
    return r.standard_normal(n)


def pink(n, r):
    spec = np.fft.rfft(r.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    spec[1:] /= np.sqrt(f[1:])
    spec[0] = 0
    x = np.fft.irfft(spec, n)
    return x / (np.std(x) + 1e-9)


def brown(n, r):
    x = np.cumsum(r.standard_normal(n))
    x = hp(x, 15)
    return x / (np.std(x) + 1e-9)


def expenv(n, tau):
    return np.exp(-tvec(n) / tau)


def adsr(n, a=0.01, r=0.1):
    e = np.ones(n)
    na, nr = min(n, n_of(a)), min(n, n_of(r))
    if na:
        e[:na] = np.linspace(0, 1, na)
    if nr:
        e[n - nr:] *= np.linspace(1, 0, nr)
    return e


def osc_phase(freq):
    """Integrate an instantaneous-frequency array to phase (cycles)."""
    return np.cumsum(freq) / SR


def saw(freq):
    ph = osc_phase(freq)
    return 2 * (ph % 1.0) - 1


def sine_f(freq, phase0=0.0):
    return np.sin(2 * np.pi * osc_phase(freq) + phase0)


def stereo(mono, pan=0.0, width=0.0, r=None):
    """Equal-power pan; optional decorrelated width via a short delay on one side."""
    l = np.cos((pan + 1) * np.pi / 4)
    rr = np.sin((pan + 1) * np.pi / 4)
    L, R = mono * l, mono * rr
    if width > 0:
        d = n_of(0.011)
        R = (1 - width) * R + width * np.concatenate([np.zeros(d), R[:-d]])
    return np.stack([L, R])


_IR = {}


def impulse(rt60=2.0, damp=5000, key=0):
    """Synthesized stereo IR: exponentially decaying decorrelated noise, darker as it decays."""
    k = (round(rt60, 2), damp, key)
    if k in _IR:
        return _IR[k]
    r = rng_for("ir", key, int(rt60 * 100))
    n = n_of(rt60 * 1.15)
    t = tvec(n)
    env = np.exp(-6.9 * t / rt60)
    irs = []
    for ch in range(2):
        bright = white(n, r) * env
        dark = lp(white(n, r), damp * 0.35) * env
        mixk = np.clip(t / rt60, 0, 1)  # high frequencies die first
        ir = bright * (1 - mixk) + dark * mixk * 2.2
        ir[: n_of(0.008)] *= np.linspace(0, 1, n_of(0.008))  # predelay feel
        irs.append(ir / np.sqrt(np.sum(ir ** 2)))
    _IR[k] = np.stack(irs)
    return _IR[k]


def reverb(x, rt60=2.0, wet=0.3, damp=5000, key=0):
    """Convolution reverb with a synthesized IR. x: mono or stereo -> stereo."""
    if x.ndim == 1:
        x = np.stack([x, x])
    ir = impulse(rt60, damp, key)
    tail = n_of(rt60 * 1.15)
    xp = np.pad(x, ((0, 0), (0, tail)))
    w = np.stack([fftconvolve(xp[c], ir[c])[: xp.shape[1]] for c in range(2)])
    return xp * (1 - wet) + w * wet * 0.9


def peak_norm(x, db):
    p = np.max(np.abs(x)) + 1e-12
    return x * (10 ** (db / 20) / p)


def soft_clip(x, drive=1.5):
    return np.tanh(x * drive) / np.tanh(drive)


# ================================================================================================
# SFX generators (each returns mono or stereo float arrays at SR)
# ================================================================================================
def sfx_heartbeat(c, r):
    out = np.zeros(n_of(0.9))
    for off, a in [(0.0, 1.0), (0.27, 0.75)]:
        n = n_of(0.45)
        t = tvec(n)
        f = 48 + 22 * np.exp(-t / 0.03)
        thump = sine_f(f) * expenv(n, 0.085) + 0.25 * lp(white(n, r), 120) * expenv(n, 0.03)
        i = n_of(off)
        out[i:i + n] += a * soft_clip(thump, 2.0)
    return reverb(lp(out, 400), 0.8, 0.15)


def sfx_typekey(c, r):
    n = n_of(0.16)
    t = tvec(n)
    click = hp(white(n, r), 2500) * expenv(n, 0.0025)
    body = bp(white(n, r), 1400 + 600 * r.random(), 3600) * expenv(n, 0.012) * 0.6
    thunk = np.sin(2 * np.pi * (140 + 40 * r.random()) * t) * expenv(n, 0.018) * 0.5
    bar = np.zeros(n)
    j = n_of(0.035 + 0.01 * r.random())  # the typebar striking the platen
    bar[j:] = hp(white(n - j, r), 1500) * expenv(n - j, 0.004) * 0.8
    return reverb(click + body + thunk + bar, 0.4, 0.12, key=1)


def sfx_glitch(c, r):
    n = n_of(0.4)
    x = np.zeros(n)
    seg = n_of(0.018)
    for i in range(0, n, seg):
        if r.random() < 0.7:
            f = r.uniform(80, 2400)
            tt = tvec(min(seg, n - i))
            x[i:i + seg] = np.sign(np.sin(2 * np.pi * f * tt)) * r.uniform(0.3, 1)
    x = np.round(x * 6) / 6  # bitcrush
    return stereo(bp(x, 150, 6000), r.uniform(-0.4, 0.4), 0.6)


def sfx_subboom(c, r):
    n = n_of(3.0)
    t = tvec(n)
    f = 27 + 45 * np.exp(-t / 0.22)
    x = sine_f(f) * expenv(n, 0.8) + 0.5 * lp(brown(n, r), 140) * expenv(n, 0.35)
    return reverb(soft_clip(x, 1.8), 2.6, 0.3, damp=2500)


def sfx_boom(c, r):
    n = n_of(2.0)
    t = tvec(n)
    f = 34 + 22 * np.exp(-t / 0.12)
    x = sine_f(f) * expenv(n, 0.5) + 0.35 * lp(white(n, r), 220) * expenv(n, 0.12)
    return reverb(soft_clip(x, 1.4), 2.2, 0.35, damp=2000, key=2)


def sfx_morse(c, r):
    dur = c.get("dur", 2.0)
    n = n_of(dur)
    x = np.zeros(n)
    unit = 0.055
    pos = 0.05
    while pos < dur - 0.3:
        for _ in range(r.integers(2, 5)):  # one letter
            L = unit * (3 if r.random() < 0.4 else 1)
            i, m = n_of(pos), n_of(L)
            if i + m >= n:
                break
            tone = np.sin(2 * np.pi * 680 * tvec(m)) * adsr(m, 0.004, 0.006)
            x[i:i + m] += tone
            pos += L + unit
        pos += unit * 2
    x = bp(x + 0.05 * white(n, r), 350, 2500)
    return reverb(x * adsr(n, 0.05, 0.3), 0.6, 0.1)


def sfx_artillery(c, r):
    n = n_of(1.2)
    t = tvec(n)
    blast = lp(white(n, r), 380) * expenv(n, 0.22) + 1.2 * np.sin(2 * np.pi * (38 + 30 * np.exp(-t / 0.05)) * t) * expenv(n, 0.3)
    return reverb(soft_clip(blast, 1.5), 3.8, 0.72, damp=1500, key=3)


def sfx_radio(c, r):
    n = n_of(0.9)
    t = tvec(n)
    hiss = bp(white(n, r), 700, 3200)
    gate = (lp(white(n, r), 18) > -0.2).astype(float)
    crack = np.zeros(n)
    for _ in range(40):
        i = r.integers(0, n - 200)
        crack[i:i + 60] += r.uniform(-3, 3) * np.exp(-np.arange(60) / 8)
    whistle = 0.3 * np.sin(2 * np.pi * osc_phase(1100 + 900 * t))
    return (hiss * (0.4 + 0.6 * gate) + crack + whistle) * adsr(n, 0.02, 0.2)


def sfx_engines(c, r):
    dur = c.get("dur", 5.0)
    n = n_of(dur)
    t = tvec(n)
    out = np.zeros((2, n))
    for k, det in enumerate([1.0, 1.013, 0.987, 1.021]):
        f0 = 88 * det * (1 + 0.01 * np.sin(2 * np.pi * 0.2 * t + k))
        ph = osc_phase(f0)
        x = sum(np.sin(2 * np.pi * h * ph) / h for h in range(1, 9))
        x *= 1 + 0.35 * np.sin(2 * np.pi * ph / 3)  # propeller beat
        out += stereo(x, [-0.6, 0.6, -0.2, 0.3][k])
    out += 0.6 * stereo(lp(brown(n, r), 300), 0, 0.8)
    out = lp(out, 1500) * adsr(n, 0.8, 1.2)
    return out


def sfx_riser(c, r):
    dur = c.get("dur", 4.0)
    n = n_of(dur)
    t = tvec(n)
    bend = 2 ** ((2 * t / dur) / 12)
    x = np.zeros(n)
    for f in [146.83, 220.0, 293.66, 440.0]:
        for d in (-0.004, 0.004):
            x += saw(f * bend * (1 + d))
    trem = 0.6 + 0.4 * np.sin(2 * np.pi * 9 * t)
    amp = (t / dur) ** 2.2
    x = lp(x * trem * amp, 2500)
    return reverb(x * adsr(n, 0.3, 0.15), 1.8, 0.3)


def sfx_metal(c, r):
    n = n_of(2.5)
    t = tvec(n)
    f0 = 170
    x = np.zeros(n)
    for ratio, tau, a in [(1, 1.3, 1), (2.32, 0.9, 0.7), (4.25, 0.55, 0.5), (6.63, 0.35, 0.4), (9.38, 0.22, 0.3), (12.1, 0.15, 0.2)]:
        x += a * np.sin(2 * np.pi * f0 * ratio * t + r.uniform(0, 6)) * expenv(n, tau)
    x += 0.8 * hp(white(n, r), 2000) * expenv(n, 0.02)
    x += 1.2 * np.sin(2 * np.pi * (60 + 40 * np.exp(-t / 0.04)) * t) * expenv(n, 0.15)
    return reverb(x, 2.6, 0.4, key=4)


def sfx_siren(c, r):
    dur = c.get("dur", 4.5)
    n = n_of(dur)
    t = tvec(n)
    f = 400 + 500 * (0.5 - 0.5 * np.cos(2 * np.pi * t / 3.4)) + 4 * np.sin(2 * np.pi * 5 * t)
    ph = osc_phase(f)
    x = np.sin(2 * np.pi * ph) + 0.3 * np.sin(4 * np.pi * ph) + 0.12 * np.sin(6 * np.pi * ph)
    x = lp(x, 2500) * adsr(n, 0.6, 1.2)
    return reverb(x, 3.0, 0.6, damp=3000, key=5)


def sfx_flyby(c, r):
    dur = c.get("dur", 3.0)
    n = n_of(dur)
    t = tvec(n)
    v, d, cs = 120.0, 45.0, 343.0
    tc = dur * 0.5
    x_pos = v * (t - tc)
    dist = np.sqrt(x_pos ** 2 + d ** 2)
    vr = v * x_pos / dist                       # radial velocity (+ = receding)
    dop = cs / (cs + vr)
    f = 105 * dop
    ph = osc_phase(f)
    eng = sum(np.sin(2 * np.pi * h * ph) / h ** 0.8 for h in range(1, 10)) * (1 + 0.3 * np.sin(2 * np.pi * ph / 2))
    air = bp(white(n, r), 300, 3000) * 0.5
    amp = (d / dist) ** 1.2
    mono = lp((eng + air) * amp, 2800) * adsr(n, 0.3, 0.4)
    pan = np.clip(x_pos / (np.abs(x_pos) + d), -1, 1) * (-1 if c.get("reverse") else 1)
    L, R = mono * np.cos((pan + 1) * np.pi / 4), mono * np.sin((pan + 1) * np.pi / 4)
    return reverb(np.stack([L, R]), 1.5, 0.2)


def sfx_flak(c, r):
    n = n_of(0.5)
    t = tvec(n)
    x = bp(white(n, r), 250, 2200) * expenv(n, 0.03) + np.sin(2 * np.pi * 70 * t) * expenv(n, 0.07)
    return stereo(reverb(soft_clip(x, 2), 2.6, 0.6, key=6)[0], r.uniform(-0.6, 0.6))


def sfx_drum(c, r):
    n = n_of(2.0)
    t = tvec(n)
    f = 38 + 30 * np.exp(-t / 0.08)
    x = sine_f(f) * expenv(n, 0.9) + 0.6 * lp(white(n, r), 500) * expenv(n, 0.06)
    return reverb(soft_clip(x, 2.2), 3.4, 0.45, damp=2500, key=7)


def sfx_rumble(c, r):
    dur = c.get("dur", 4.5)
    n = n_of(dur)
    t = tvec(n)
    x = lp(brown(n, r), 160) * 1.4
    ph = osc_phase(44 + 2 * np.sin(2 * np.pi * 0.3 * t))
    x += 0.5 * sum(np.sin(2 * np.pi * h * ph) / h for h in range(1, 6)) * (1 + 0.3 * np.sin(2 * np.pi * 7 * t))
    return stereo(lp(x, 400) * adsr(n, 0.25, 1.6), 0, 0.9)


def sfx_wind(c, r):
    dur = c.get("dur", 3.0)
    n = n_of(dur)
    t = tvec(n)
    base = pink(n, r)
    lfo1 = 0.5 + 0.5 * np.sin(2 * np.pi * 0.23 * t + r.uniform(0, 6))
    lfo2 = 0.5 + 0.5 * np.sin(2 * np.pi * 0.37 * t + r.uniform(0, 6))
    x = bp(base, 200, 700) * lfo1 + bp(base, 600, 1600) * lfo2 * 0.6 + lp(base, 250) * 0.8
    if c.get("howl"):
        f = 520 + 260 * np.sin(2 * np.pi * 0.17 * t) + 90 * np.sin(2 * np.pi * 0.53 * t)
        x += 0.35 * bp(base, 300, 1400) * (0.5 + 0.5 * np.sin(2 * np.pi * osc_phase(f) * 0.002)) + 0.12 * sine_f(f) * lfo2
    if c.get("soft"):
        x = lp(x, 500)
    return stereo(x * adsr(n, 0.8, 1.0), 0, 0.9)


def sfx_gunfire(c, r):
    n = n_of(1.6)
    x = np.zeros(n)
    pos = 0.02
    for burst in range(2):
        for _ in range(r.integers(6, 11)):
            m = n_of(0.12)
            tt = tvec(m)
            shot = hp(white(m, r), 900) * np.exp(-tt / 0.008) + 0.8 * np.sin(2 * np.pi * 110 * tt) * np.exp(-tt / 0.025)
            i = n_of(pos)
            if i + m < n:
                x[i:i + m] += shot * r.uniform(0.6, 1)
            pos += 0.075 + r.uniform(-0.01, 0.012)
        pos += r.uniform(0.15, 0.3)
    if c.get("muffled"):
        x = lp(x, 650)
        return reverb(x, 3.0, 0.7, damp=1500, key=8)
    return stereo(reverb(x, 2.0, 0.45, key=9)[0], r.uniform(-0.5, 0.5))


def sfx_waves(c, r):
    dur = c.get("dur", 5.0)
    n = n_of(dur)
    t = tvec(n)
    out = []
    for ch in range(2):
        swell = 0.35 + 0.65 * np.sin(np.pi * ((t + ch * 0.7) / 3.6)) ** 2
        body = lp(pink(n, r), 700) * swell
        foam = hp(white(n, r), 2500) * swell ** 4 * 0.35
        out.append(body + foam)
    return np.stack(out) * adsr(n, 0.4, 0.8)


def sfx_whoosh(c, r):
    n = n_of(0.9)
    t = tvec(n)
    w = white(n, r)
    x = lp(w, 400) * np.exp(-((t - 0.35) / 0.18) ** 2) + bp(w, 800, 2500) * np.exp(-((t - 0.5) / 0.12) ** 2) * 0.7 \
        + hp(w, 3000) * np.exp(-((t - 0.6) / 0.08) ** 2) * 0.5
    pan = np.linspace(-0.7, 0.7, n)
    return np.stack([x * np.cos((pan + 1) * np.pi / 4), x * np.sin((pan + 1) * np.pi / 4)])


def sfx_percussion(c, r):
    dur = c.get("dur", 3.0)
    n = n_of(dur + 1.5)
    x = np.zeros(n)
    times, pos, gap = [], 0.0, 0.42
    while pos < dur:
        times.append(pos)
        pos += gap
        gap = max(0.11, gap * 0.86)
    for k, p in enumerate(times):
        m = n_of(0.5)
        tt = tvec(m)
        hit = np.sin(2 * np.pi * (70 + 40 * np.exp(-tt / 0.03)) * tt) * np.exp(-tt / 0.16) + 0.4 * lp(white(m, r), 1200) * np.exp(-tt / 0.02)
        i = n_of(p)
        x[i:i + m] += hit * (0.35 + 0.65 * (p / dur) ** 1.5)
    return reverb(soft_clip(x, 1.6), 2.4, 0.35, key=10)


def sfx_explosion(c, r):
    n = n_of(2.4)
    t = tvec(n)
    x = lp(white(n, r), 1100) * expenv(n, 0.45) * 1.3
    x += 1.5 * np.sin(2 * np.pi * (32 + 50 * np.exp(-t / 0.06)) * t) * expenv(n, 0.7)
    deb = np.zeros(n)
    for _ in range(70):
        i = r.integers(n_of(0.1), n - 400)
        deb[i:i + 300] += r.uniform(-1, 1) * np.exp(-np.arange(300) / 40) * np.exp(-i / SR / 0.7)
    x += hp(deb, 1500) * 0.6
    return reverb(soft_clip(x, 1.8), 3.0, 0.5, damp=2500, key=11)


def sfx_fire(c, r):
    dur = c.get("dur", 3.0)
    n = n_of(dur)
    t = tvec(n)
    roar = lp(brown(n, r), 350) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.7 * t))
    cr = np.zeros(n)
    for _ in range(int(32 * dur)):
        i = r.integers(0, n - 200)
        cr[i:i + 150] += r.uniform(0.2, 1.2) * r.choice([-1, 1]) * np.exp(-np.arange(150) / 12)
    x = roar + hp(cr, 1800) * 0.9
    return stereo(x * adsr(n, 0.3, 0.9), 0, 0.8)


def sfx_piano(c, r):
    """One D3 piano note: inharmonic partials, 3 detuned strings, two-stage decay, hammer thump."""
    n = n_of(6.0)
    t = tvec(n)
    f0, B = 146.83, 0.00035
    x = np.zeros(n)
    for k in range(1, 16):
        fk = k * f0 * np.sqrt(1 + B * k * k)
        a = (1 / k ** 1.15) * (1 if k < 9 else 0.5)
        tau_fast, tau_slow = 0.35 / (1 + 0.15 * k), 4.2 / (1 + 0.32 * k)
        env = 0.55 * np.exp(-t / tau_fast) + 0.45 * np.exp(-t / tau_slow)
        for det in (-0.0004, 0.0, 0.0005):
            x += a * env * np.sin(2 * np.pi * fk * (1 + det) * t + r.uniform(0, 6)) / 3
    x += 0.25 * lp(white(n, r), 900) * expenv(n, 0.012)
    x *= adsr(n, 0.002, 0.6)
    return reverb(x, 3.6, 0.45, damp=4000, key=12)


GEN = {k[4:]: v for k, v in globals().items() if k.startswith("sfx_")}


# ================================================================================================
# Music (D minor)
# ================================================================================================
NOTE = {"D1": 36.71, "A1": 55.0, "Bb1": 58.27, "C2": 65.41, "D2": 73.42, "E2": 82.41, "F2": 87.31, "G2": 98.0,
        "A2": 110.0, "Bb2": 116.54, "C3": 130.81, "D3": 146.83, "E3": 164.81, "F3": 174.61, "G3": 196.0, "A3": 220.0,
        "Bb3": 233.08, "C4": 261.63, "Cs4": 277.18, "D4": 293.66, "E4": 329.63, "F4": 349.23, "A4": 440.0}

# chord progression per scene: list of (fraction of scene, [notes])
PROG = {
    "hook": [(0, ["D1", "D2", "A2"])],
    "poland": [(0, ["D2", "A2", "D3", "F3"]), (0.55, ["Bb1", "F2", "D3", "F3"])],
    "blitz": [(0, ["G2", "D3", "G3", "Bb3"]), (0.5, ["A2", "E3", "A3", "Cs4"])],
    "britain": [(0, ["F2", "C3", "F3", "A3"]), (0.5, ["D2", "A2", "F3", "A3", "E4"])],
    "barbarossa": [(0, ["G2", "D3", "Bb3", "D4"]), (0.45, ["A1", "A2", "E3", "Cs4"])],
    "stalingrad": [],  # single cold cello drone instead
    "dday": [(0, ["Bb1", "F2", "D3", "F3"]), (0.35, ["C2", "G2", "E3", "G3"]), (0.7, ["D2", "A2", "F3", "A3", "D4"])],
    "berlin": [(0, ["D2", "A2", "D3", "F3", "A3"]), (0.5, ["A1", "A2", "E3", "Cs4", "E4"])],
    "ending": [],
}
DRIVING = {"blitz", "barbarossa", "dday", "berlin"}  # ostinato pulse + rising tension


def pad_voice(freq, n, r, cutoff, detune=0.006):
    t = tvec(n)
    x = np.zeros(n)
    for d in (-detune, 0, detune):
        vib = 1 + 0.002 * np.sin(2 * np.pi * r.uniform(4.5, 5.5) * t + r.uniform(0, 6))
        x += saw(freq * (1 + d) * vib)
    return lp(x / 3, cutoff, 2)


def render_music(tl: dict) -> np.ndarray:
    total = n_of(tl["duration"])
    out = np.zeros((2, total + n_of(4)))
    r = rng_for("music")
    scenes = tl["scenes"]
    for si, sc in enumerate(scenes):
        sid, s0, s1 = sc["id"], sc["startSec"], sc["endSec"]
        inten = sc["music"]["intensity"]
        dur = s1 - s0
        nxt = scenes[si + 1] if si + 1 < len(scenes) else None
        hard = sc["music"].get("hardCut", False)
        # ---- string pads ----------------------------------------------------------------------
        prog = PROG[sid]
        for ci, (frac, notes) in enumerate(prog):
            a = s0 + frac * dur - (0.35 if ci else 0.25)
            b = s0 + (prog[ci + 1][0] * dur if ci + 1 < len(prog) else dur) + (0.02 if hard and ci + 1 == len(prog) else 0.45)
            if ci + 1 == len(prog) and nxt and nxt["id"] in ("stalingrad", "ending"):
                b = s1 + 0.05
            n = n_of(b - a)
            cutoff = 500 + 2600 * inten
            seg = np.zeros((2, n))
            for k, nm in enumerate(notes):
                v = pad_voice(NOTE[nm], n, r, cutoff) * (1.0 if NOTE[nm] < 120 else 0.6)
                seg += stereo(v, (k / max(1, len(notes) - 1) - 0.5) * 0.9)
            env = adsr(n, 0.4 if ci == 0 else 0.35, 0.02 if (hard and ci + 1 == len(prog)) else 0.45)
            if sid in DRIVING:  # crescendo inside the scene
                env *= np.linspace(0.65, 1.0, n)
            seg *= env * (0.25 + 0.75 * inten)
            out += place(seg, a, out.shape[1])
        # ---- ostinato pulse (driving scenes) ----------------------------------------------------
        if sid in DRIVING:
            bpm = 104 if sid != "berlin" else 116
            step = 60 / bpm / 2
            k = 0
            pos = s0
            root = NOTE[prog[0][1][0]] if prog else NOTE["D2"]
            while pos < s1 - 0.05:
                frac = (pos - s0) / dur
                notes = [nt for f, nt in prog if f <= frac][-1]
                f0 = NOTE[notes[0]] * (2 if NOTE[notes[0]] < 60 else 1)
                m = n_of(step * 0.9)
                tt = tvec(m)
                accent = 1.0 if k % 4 == 0 else 0.6
                v = lp(saw(np.full(m, f0)) + 0.5 * saw(np.full(m, f0 * 2.003)), 900 + 1500 * inten) * np.exp(-tt / 0.09) * accent
                v *= (0.4 + 0.6 * frac) * inten * 0.9
                out += place(stereo(v, 0.0), pos, out.shape[1])
                pos += step
                k += 1
            del root
        # ---- timpani on scene entries + climax roll --------------------------------------------
        if sid not in ("hook", "ending", "stalingrad"):
            out += place(timpani(NOTE["D2"], 0.9, r), s0 + 0.0, out.shape[1]) * (0.5 + 0.5 * inten)
        if sid == "berlin":  # climax roll, crescendo into the hard cut
            pos, gap = s0 + dur * 0.35, 0.16
            while pos < s1 - 0.08:
                g = 0.25 + 0.75 * ((pos - s0) / dur) ** 2
                out += place(timpani(NOTE["A1"] * 2 if int(pos * 10) % 2 else NOTE["D2"], 0.4, r), pos, out.shape[1]) * g * 0.7
                pos += gap
                gap = max(0.06, gap * 0.93)
        # ---- Stalingrad: single cold cello drone, then a silence beat --------------------------
        if sid == "stalingrad":
            sil = sc["music"]["silenceSec"]
            a, b = s0 - 0.1, sil
            n = n_of(b - a)
            t = tvec(n)
            vib = 1 + 0.004 * np.sin(2 * np.pi * 5.2 * t) * np.clip(t / 1.5, 0, 1)
            cel = saw(NOTE["D2"] * vib) + 0.5 * saw(NOTE["D2"] * 2 * vib * 1.001)
            cel = bp(cel, 90, 1400) + 0.04 * bp(white(n, r), 800, 3000)  # bow noise
            cel *= adsr(n, 1.0, 0.03) * (0.85 + 0.15 * np.sin(2 * np.pi * 0.25 * t))
            out += place(stereo(cel, -0.1, 0.5) * 0.9, a, out.shape[1])
    out = out[:, :total]
    # Reverb on the whole bed (hall)
    out = reverb(out, 2.8, 0.35, damp=4500, key=20)[:, :total]
    # Hard cut at the end of Berlin + silence through the ending; silence beat at the surrender
    gate = np.ones(total)
    ber = next(s for s in scenes if s["id"] == "berlin")
    i = n_of(ber["endSec"])
    gate[i:] = 0
    gate[i - n_of(0.012):i] = np.linspace(1, 0, n_of(0.012))
    st = next(s for s in scenes if s["id"] == "stalingrad")
    sil = n_of(st["music"]["silenceSec"])
    end_st = n_of(st["endSec"])
    gate[sil - n_of(0.04):sil] = np.minimum(gate[sil - n_of(0.04):sil], np.linspace(1, 0, n_of(0.04)))
    gate[sil:end_st] = 0
    return out * gate


def timpani(f, tau, r):
    n = n_of(tau * 4)
    t = tvec(n)
    x = np.sin(2 * np.pi * (f * (1 + 0.15 * np.exp(-t / 0.04))) * t) * np.exp(-t / tau)
    x += 0.5 * np.sin(2 * np.pi * f * 1.5 * t) * np.exp(-t / (tau * 0.5))
    x += 0.4 * lp(white(n, r), 700) * np.exp(-t / 0.03)
    return stereo(soft_clip(x, 1.3), 0, 0.5)


def place(x, at, total):
    buf = np.zeros((2, total))
    if x.ndim == 1:
        x = np.stack([x, x])
    i = n_of(at)
    if i < 0:
        x, i = x[:, -i:], 0
    m = min(x.shape[1], total - i)
    if m > 0:
        buf[:, i:i + m] = x[:, :m]
    return buf


# ================================================================================================
def main() -> None:
    tl = json.loads((BUILD / "timeline.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    total = n_of(tl["duration"])

    print("  synthesizing music bed (D minor) ...")
    music = render_music(tl)

    print(f"  synthesizing {len(tl['cues'])} SFX cues ...")
    sfx = np.zeros((2, total + n_of(8)))
    counts = {}
    for k, c in enumerate(tl["cues"]):
        name = c["sfx"]
        if name not in GEN:
            sys.exit(f"unknown sfx '{name}' in timeline")
        counts[name] = counts.get(name, 0) + 1
        x = GEN[name](c, rng_for("sfx", name, k))
        if x.ndim == 1:
            x = np.stack([x, x])
        x = peak_norm(x, c.get("gain", -18))
        i = n_of(c["time"])
        m = min(x.shape[1], sfx.shape[1] - i)
        sfx[:, i:i + m] += x[:, :m]
    sfx = sfx[:, :total]
    # short tail fade (no click at the loop point; the video loops back to frame 0)
    fade = n_of(0.25)
    for buf in (music, sfx):
        buf[:, -fade:] *= np.linspace(1, 0, fade) ** 2
    sf.write(OUT / "music.wav", music.T.astype(np.float32), SR, subtype="FLOAT")
    sf.write(OUT / "sfx.wav", sfx.T.astype(np.float32), SR, subtype="FLOAT")
    print("  sfx library used: " + ", ".join(f"{k}x{v}" for k, v in sorted(counts.items())))
    print("  wrote build/audio/music.wav, build/audio/sfx.wav")


if __name__ == "__main__":
    main()
