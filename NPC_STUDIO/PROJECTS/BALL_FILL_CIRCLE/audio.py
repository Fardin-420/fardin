#!/usr/bin/env python3
"""Synthesize the soundtrack from the simulation's hit log.

    python3 audio.py build/events.json build/audio.wav

* Every logged wall hit is a candidate marimba/glass note. Notes are rate-limited
  (>= 3 frames = 50 ms apart, i.e. <= 20 notes/s); hits that fall inside a note's window
  are merged into it and raise its velocity.
* A note triggered by the hit logged at frame N starts at sample N * SR / FPS exactly.
* Pitch: C-major pentatonic, base degree = floor(log2(ball count)), plus a short
  repeating melodic pattern, so the melody climbs as the count doubles.
* Final beat: low whoosh build into the shatter, crack snaps, deep boom + shimmer,
  bell on "Part 2?".
* Master: light reverb, BS.1770-4 integrated loudness normalised to -14 LUFS with a
  look-ahead true-peak limiter at -1 dBTP. Writes build/notes.json for the sync check.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile
from scipy.ndimage import minimum_filter1d, uniform_filter1d

SR = 48000
DUR = 30.0
TARGET_LUFS = -14.0
CEIL_DBTP = -1.0
PENT = [0, 2, 4, 7, 9]
PATTERN = [0, 2, 4, 1, 3, 5, 2, 4]          # must match sim.html preview
MIN_GAP_FRAMES = 3
rng = np.random.default_rng(20261110)


def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def note_midi(count, k):
    deg = int(np.floor(np.log2(max(count, 1)))) + PATTERN[k % len(PATTERN)]
    return 60 + 12 * (deg // 5) + PENT[deg % 5]


def add(buf, start, sig, pan=0.5):
    """Mix mono `sig` into stereo `buf` at sample `start` with equal-power pan."""
    if start >= buf.shape[1]:
        return
    n = min(len(sig), buf.shape[1] - start)
    gl, gr = np.cos(pan * np.pi / 2), np.sin(pan * np.pi / 2)
    buf[0, start:start + n] += sig[:n] * gl
    buf[1, start:start + n] += sig[:n] * gr


def env_attack(n, ms=1.5):
    a = np.ones(n)
    k = int(SR * ms / 1000)
    a[:k] = np.linspace(0, 1, k)
    return a


def marimba(f, split, vel):
    tau = 0.42 * (440.0 / f) ** 0.35
    n = int(SR * min(2.0, tau * 6 + 0.1))
    t = np.arange(n) / SR
    s = (np.sin(2 * np.pi * f * t) * np.exp(-t / tau)
         + 0.32 * np.sin(2 * np.pi * 3.93 * f * t) * np.exp(-t / (tau * 0.22))
         + 0.07 * np.sin(2 * np.pi * 9.24 * f * t) * np.exp(-t / (tau * 0.08)))
    # soft mallet: a few ms of filtered noise
    k = int(SR * 0.006)
    click = rng.standard_normal(k) * np.exp(-np.arange(k) / (SR * 0.0012)) * 0.15
    s[:k] += click
    if split:   # glassy overtone on splits
        s += (0.22 * np.sin(2 * np.pi * 2.0 * f * t + 0.3) * np.exp(-t / 0.9)
              + 0.07 * np.sin(2 * np.pi * 5.43 * f * t) * np.exp(-t / 0.35))
    return s * env_attack(n) * vel


def build_notes(ev):
    h = np.array(ev["hits"], dtype=np.int64).reshape(-1, 4)
    notes = []
    for f, a, c, sp in h:
        if notes and f - notes[-1]["frame"] < MIN_GAP_FRAMES:
            nt = notes[-1]                       # merge into the current note
            nt["merged"] += 1
            nt["split"] |= int(sp)
            nt["count"] = max(nt["count"], int(c))
            continue
        notes.append({"frame": int(f), "angle": int(a), "count": int(c), "split": int(sp), "merged": 1})
    for k, nt in enumerate(notes):
        nt["midi"] = note_midi(nt["count"], k)
        nt["sample"] = nt["frame"] * SR // ev["fps"]
    return notes


def noise_sweep(n, f0, f1, seed):
    """Noise through a 2nd-order low-pass whose cutoff glides f0→f1 (block-wise)."""
    r = np.random.default_rng(seed)
    x = r.standard_normal(n)
    out = np.zeros(n)
    zi = np.zeros((1, 2))
    B = 256
    for i in range(0, n, B):
        p = i / n
        fc = f0 * (f1 / f0) ** p
        sos = signal.butter(2, fc, fs=SR, output="sos")
        out[i:i + B], zi = signal.sosfilt(sos, x[i:i + B], zi=zi)
    return out


def whoosh(start_s, peak_s, tail_s=1.4):
    n = int((peak_s - start_s + tail_s) * SR)
    t = np.arange(n) / SR
    tp = peak_s - start_s
    env = np.where(t < tp, (t / tp) ** 2.4, np.exp(-(t - tp) / 0.35))
    L = noise_sweep(n, 120, 2600, 1) * env
    R = noise_sweep(n, 120, 2600, 2) * env
    freq = 38 + 34 * np.clip(t / tp, 0, 1)
    sub = np.sin(2 * np.pi * np.cumsum(freq) / SR) * env * 0.6
    return np.stack([L + sub, R + sub]) * 0.55


def crack():
    n = int(SR * 0.06)
    t = np.arange(n) / SR
    x = rng.standard_normal(n)
    x = signal.sosfilt(signal.butter(2, 1800, "hp", fs=SR, output="sos"), x)
    return (x * np.exp(-t / 0.012) + 0.4 * np.sin(2 * np.pi * 2300 * t) * np.exp(-t / 0.008)) * 0.55


def boom():
    n = int(SR * 3.0)
    t = np.arange(n) / SR
    f = 32 + 58 * np.exp(-t / 0.25)
    sub = np.tanh(1.8 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.9)) * 0.9
    thump = signal.sosfilt(signal.butter(2, 320, fs=SR, output="sos"), rng.standard_normal(n)) * np.exp(-t / 0.22) * 2.2
    click = rng.standard_normal(n) * np.exp(-t / 0.004) * 0.5
    return sub + thump + click


def shimmer():
    n = int(SR * 4.0)
    out = np.zeros((2, n))
    t = np.arange(n) / SR
    for m in [72, 76, 79, 81, 86, 88]:                       # pentatonic pad
        for det in (-4, 4):
            fr = midi_hz(m) * 2 ** (det / 1200)
            pad = np.sin(2 * np.pi * fr * t) * (1 - np.exp(-t / 0.06)) * np.exp(-t / 1.6) * 0.05
            pad *= 1 + 0.25 * np.sin(2 * np.pi * 5.5 * t + m)
            out[0 if det < 0 else 1] += pad
    for _ in range(60):                                      # glassy tinkles
        st = int(SR * min(2.6, rng.exponential(0.7)))
        m = 84 + PENT[rng.integers(5)] + 12 * rng.integers(0, 2)
        fr = midi_hz(m)
        k = int(SR * 1.2)
        tt = np.arange(k) / SR
        s = (np.sin(2 * np.pi * fr * tt) + 0.3 * np.sin(2 * np.pi * 2.76 * fr * tt)) * np.exp(-tt / rng.uniform(0.25, 0.7))
        s *= env_attack(k, 1) * rng.uniform(0.03, 0.08)
        add(out, st, s, rng.uniform(0.1, 0.9))
    return out


def bell():
    n = int(SR * 2.5)
    t = np.arange(n) / SR
    s = np.zeros(n)
    for m, a in ((72, 1.0), (79, 0.6), (84, 0.5)):
        fr = midi_hz(m)
        s += a * (np.sin(2 * np.pi * fr * t) * np.exp(-t / 1.2)
                  + 0.35 * np.sin(2 * np.pi * 2.76 * fr * t) * np.exp(-t / 0.4)
                  + 0.15 * np.sin(2 * np.pi * 5.4 * fr * t) * np.exp(-t / 0.15))
    return s * env_attack(n, 2) * 0.22


def reverb(x, wet=0.22, rt=0.5, length=2.2):
    n = int(SR * length)
    t = np.arange(n) / SR
    out = np.empty_like(x)
    for ch in range(2):
        ir = np.random.default_rng(100 + ch).standard_normal(n) * np.exp(-t / rt)
        ir = signal.sosfilt(signal.butter(1, 5000, fs=SR, output="sos"), ir)
        ir[: int(SR * 0.012)] = 0                              # pre-delay
        ir /= np.sqrt(np.sum(ir ** 2))
        out[ch] = signal.fftconvolve(x[ch], ir)[: x.shape[1]]
    return x * (1 - wet) + out * wet * 1.6


# ---------------------------------------------------------------- loudness (ITU-R BS.1770-4)
def k_weight(x):
    b1, a1 = [1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585]
    b2, a2 = [1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621]
    return signal.lfilter(b2, a2, signal.lfilter(b1, a1, x, axis=-1), axis=-1)


def integrated_lufs(x):
    y = k_weight(x)
    blk, hop = int(0.4 * SR), int(0.1 * SR)
    ms = np.array([np.sum(np.mean(y[:, i:i + blk] ** 2, axis=1)) for i in range(0, y.shape[1] - blk + 1, hop)])
    lk = -0.691 + 10 * np.log10(ms + 1e-20)
    ms = ms[lk > -70]
    rel = -0.691 + 10 * np.log10(np.mean(ms)) - 10
    ms = ms[(-0.691 + 10 * np.log10(ms)) > rel]
    return -0.691 + 10 * np.log10(np.mean(ms))


def true_peak_db(x):
    up = signal.resample_poly(x, 4, 1, axis=-1)
    return 20 * np.log10(np.max(np.abs(up)) + 1e-12)


def limit(x, ceil_db):
    """Look-ahead brick-wall limiter driven by the 4x-oversampled peak."""
    ceil = 10 ** (ceil_db / 20)
    up = np.abs(signal.resample_poly(x, 4, 1, axis=-1)).max(axis=0)
    peak = up.reshape(-1, 4).max(axis=1)[: x.shape[1]]
    need = np.minimum(1.0, ceil / np.maximum(peak, 1e-9))
    L = int(SR * 0.005)
    g = minimum_filter1d(need, size=2 * L + 1)
    g = uniform_filter1d(g, size=L)
    g = np.minimum(g, minimum_filter1d(need, size=3))
    return x * g


def main(events_path, out_path):
    ev = json.loads(Path(events_path).read_text())
    fps = ev["fps"]
    n = int(DUR * SR)
    music = np.zeros((2, n))
    fx = np.zeros((2, n))
    notes = build_notes(ev)
    last = 0
    for nt in notes:
        gap = (nt["frame"] - last) / fps
        last = nt["frame"]
        density = 0.7 if gap < 0.08 else 1.0
        vel = (0.38 + 0.62 * min(1.0, np.log2(1 + nt["merged"]) / 3.0)) * density
        pan = 0.5 + 0.38 * np.cos(np.radians(nt["angle"]))
        add(music, nt["sample"], marimba(midi_hz(nt["midi"]), nt["split"], vel) * 0.32, pan)
    sh = ev["shatterFrame"] * SR // fps
    w = whoosh(25.8, ev["shatterFrame"] / fps)
    s0 = int(25.8 * SR)
    fx[:, s0:s0 + w.shape[1]] += w[:, : n - s0]
    for f in ev["crackFrames"]:
        add(fx, f * SR // fps, crack(), 0.5 + rng.uniform(-0.35, 0.35))
    add(fx, sh, boom() * 0.9, 0.5)
    shm = shimmer()
    fx[:, sh:sh + shm.shape[1]] += shm[:, : n - sh] * 1.4
    add(music, ev["part2Frame"] * SR // fps, bell(), 0.5)

    mix = reverb(music, wet=0.24) + reverb(fx, wet=0.15)
    fade = int(0.25 * SR)
    mix[:, -fade:] *= np.linspace(1, 0, fade)

    # loudness normalisation + true-peak limiting (iterate: limiting lowers loudness)
    x = mix.copy()
    for _ in range(6):
        lufs = integrated_lufs(x)
        x = x * 10 ** ((TARGET_LUFS - lufs) / 20)
        x = limit(x, CEIL_DBTP - 0.3)
        if abs(integrated_lufs(x) - TARGET_LUFS) < 0.1 and true_peak_db(x) <= CEIL_DBTP:
            break
    lufs, tp = integrated_lufs(x), true_peak_db(x)
    wavfile.write(out_path, SR, x.T.astype(np.float32))
    Path(out_path).with_name("notes.json").write_text(json.dumps({"sr": SR, "fps": fps, "notes": notes}))
    print(f"audio: {len(notes)} notes from {len(ev['hits']) // 4} hits · "
          f"max {max_rate(notes, fps)} notes/s · {lufs:.2f} LUFS · {tp:.2f} dBTP → {out_path}")


def max_rate(notes, fps):
    fr = np.array([nt["frame"] for nt in notes])
    return int(max(np.sum((fr >= f) & (fr < f + fps)) for f in fr)) if len(fr) else 0


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
