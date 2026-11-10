#!/usr/bin/env python3
"""Soundtrack for the Flag Battle Royale, synthesised from the simulation's event log.

    python3 audio.py build/events.json build/audio.wav

* 128 BPM electronic groove (A minor: Am–F–C–G), bar grid locked to video t = 0.
  Layers build as countries drop out (arp at <= 8 left, extra percussion at <= 4).
* Collision hits: punchy thump + click, volume from impact speed, placed at frame/60 exactly.
* Eliminations: glass shatter at the shatter frame (escapes also get a falling "whoop").
* Final duel: crowd-style rising build (formant-filtered noise "crowd", riser, snare roll)
  from the gap sealing to the final blow; the groove filters away into the slow-motion.
* Winner: big brass-style fanfare chord + timpani + cheer, groove returns for the CTA.
* Master: BS.1770-4 integrated loudness to -14 LUFS, look-ahead true-peak limiter (-1 dBTP).
  Also writes build/stem_hits.wav (hits only) for the sync check.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile
from scipy.ndimage import minimum_filter1d, uniform_filter1d

SR = 48000
BPM = 128
BEAT = 60 / BPM
TARGET_LUFS, CEIL_DBTP = -14.0, -1.0
rng = np.random.default_rng(128)


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def lp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, fs=SR, output="sos"), x)


def hp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, "hp", fs=SR, output="sos"), x)


def bp(x, f0, f1, order=2):
    return signal.sosfilt(signal.butter(order, [f0, f1], "bp", fs=SR, output="sos"), x)


def place(buf, t_or_sample, sig, gain=1.0, pan=0.5, is_sample=False):
    s = int(t_or_sample) if is_sample else int(round(t_or_sample * SR))
    if s >= buf.shape[1] or s + len(sig) <= 0:
        return
    a, b = max(0, -s), min(len(sig), buf.shape[1] - s)
    if buf.shape[0] == 1:                       # mono target
        buf[0, s + a:s + b] += sig[a:b] * gain
        return
    gl, gr = np.cos(pan * np.pi / 2) * np.sqrt(2), np.sin(pan * np.pi / 2) * np.sqrt(2)
    buf[0, s + a:s + b] += sig[a:b] * gain * gl
    buf[1, s + a:s + b] += sig[a:b] * gain * gr


def t_(dur):
    return np.arange(int(dur * SR)) / SR


def saw(f, t, voices=3, det=0.12):
    out = np.zeros_like(t)
    for k in range(voices):
        fk = f * 2 ** (det * (k - (voices - 1) / 2) / 12)
        ph = rng.random()
        out += 2 * ((fk * t + ph) % 1.0) - 1
    return out / voices


# ---------------------------------------------------------------- one-shots
def kick():
    t = t_(0.45)
    f = 45 + 110 * np.exp(-t / 0.035)
    return np.tanh(1.6 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16)) + 0.25 * rng.standard_normal(len(t)) * np.exp(-t / 0.003)


def clap():
    t = t_(0.3)
    n = bp(rng.standard_normal(len(t)), 900, 4000)
    env = np.zeros_like(t)
    for d in (0, 0.011, 0.022):
        env += (t >= d) * np.exp(-np.clip(t - d, 0, None) / 0.012)
    env += (t >= 0.03) * np.exp(-np.clip(t - 0.03, 0, None) / 0.09)
    return n * env * 0.9


def hat(open_=False):
    t = t_(0.35 if open_ else 0.06)
    return hp(rng.standard_normal(len(t)), 7000) * np.exp(-t / (0.09 if open_ else 0.014)) * (0.5 if open_ else 0.45)


def snare():
    t = t_(0.25)
    return hp(rng.standard_normal(len(t)), 1500) * np.exp(-t / 0.06) * 0.8 + np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.04) * 0.6


def hit_sound(impact):
    """Punchy collision: pitched thump + transient click; louder & lower for harder hits."""
    t = t_(0.22)
    k = np.clip((impact - 70) / 1400, 0, 1)
    f = 70 + (260 - 80 * k) * np.exp(-t / 0.018)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (0.05 + 0.05 * k))
    click = lp(rng.standard_normal(len(t)), 6000) * np.exp(-t / 0.004)
    s = np.tanh(1.5 * (body + 0.55 * click))
    return s * (0.25 + 0.75 * np.sqrt(k))


def glass(big=False):
    """Glass shatter: dense cloud of short high resonances + bright noise burst."""
    dur = 1.6 if big else 1.1
    out = np.zeros(int(dur * SR))
    t = np.arange(len(out)) / SR
    out += hp(rng.standard_normal(len(out)), 3500) * np.exp(-t / 0.05) * 0.9
    for _ in range(70 if big else 45):
        st = int(SR * rng.exponential(0.07 if not big else 0.1))
        if st >= len(out):
            continue
        f = rng.uniform(2200, 9000)
        n = min(len(out) - st, int(SR * 0.35))
        tt = np.arange(n) / SR
        out[st:st + n] += np.sin(2 * np.pi * f * tt + rng.random() * 6) * np.exp(-tt / rng.uniform(0.02, 0.12)) * rng.uniform(0.08, 0.25)
    return out * 0.8


def whoop():
    t = t_(0.5)
    f = 900 * np.exp(-t / 0.25) + 150
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.2) * 0.25


def boom():
    t = t_(2.5)
    f = 30 + 70 * np.exp(-t / 0.18)
    return np.tanh(2.0 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.8)) + lp(rng.standard_normal(len(t)), 500) * np.exp(-t / 0.25) * 1.5


# ---------------------------------------------------------------- music
PROG = [(57, [57, 60, 64]), (53, [53, 57, 60]), (48, [55, 60, 64]), (55, [55, 59, 62])]   # Am F C G (bass root, chord)


def groove(dur, alive_at, music_end, resume_at, end):
    """Drums+bass+stabs+arp; silent between music_end and resume_at."""
    n = int(end * SR)
    drums, bass, synth = np.zeros((2, n)), np.zeros((1, n)), np.zeros((2, n))
    K, C, HC, HO = kick(), clap(), hat(), hat(True)
    sixteenth = BEAT / 4
    steps = int(end / sixteenth) + 1
    for k in range(steps):
        t = k * sixteenth
        if music_end <= t < resume_at or t >= end:
            continue
        bar, pos = divmod(k, 16)
        left = alive_at(t)
        intro = t < 2.0
        if pos % 4 == 0:
            place(drums, t, K, 0.95)
        if not intro and pos in (4, 12):
            place(drums, t, C, 0.55, 0.45)
        if pos % 4 == 2:
            place(drums, t, HO, 0.35 if not intro else 0.2, 0.62)
        if not intro and pos % 2 == 1:
            place(drums, t, HC, 0.28 + 0.06 * (pos % 4 == 1), 0.38)
        if left <= 4 and pos in (7, 15, 14):
            place(drums, t, snare(), 0.25, 0.55)
        root, chord = PROG[bar % 4]
        if pos % 4 == 2 or (not intro and pos % 4 == 3 and left <= 10):          # off-beat pumping bass
            tt = t_(sixteenth * 0.95)
            b = saw(hz(root - 12), tt, 2, 0.08) * np.exp(-tt / 0.12)
            place(bass, t, b, 0.5)
        if not intro and pos in (3, 6, 10, 14):                                  # stabs
            tt = t_(0.2)
            st = sum(saw(hz(m), tt, 3, 0.15) for m in chord) / 3 * np.exp(-tt / 0.08)
            place(synth, t, st, 0.33, 0.5)
        if left <= 8 and not intro:                                              # arp
            m = chord[pos % 3] + 12 * (1 + (pos // 8) % 2)
            tt = t_(sixteenth * 0.9)
            a = np.sign(np.sin(2 * np.pi * hz(m) * tt)) * np.exp(-tt / 0.05)
            place(synth, t, a, 0.10, 0.3 if pos % 2 else 0.7)
    bass = lp(bass[0], 700)
    synth = np.stack([lp(synth[0], 2600), lp(synth[1], 2600)])
    # sidechain pump from the kick on bass + synth
    beat_t = (np.arange(n) / SR) % BEAT
    duck = 1 - 0.65 * np.exp(-beat_t / 0.09)
    return drums + (np.stack([bass, bass]) + synth) * duck


def crowd(dur, rise_power=1.6):
    """Crowd-style roar: many formant-filtered noise 'voices' with chatter, swelling up."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros((2, n))
    for v in range(14):
        x = rng.standard_normal(n)
        f1, f2 = rng.uniform(550, 850), rng.uniform(1000, 1500)
        voice = bp(x, f1 * 0.85, f1 * 1.15) + 0.6 * bp(x, f2 * 0.88, f2 * 1.12)
        mod = 0.55 + 0.45 * np.sin(2 * np.pi * rng.uniform(1.5, 5) * t + rng.random() * 6)
        out[v % 2] += voice * mod
    swell = 0.15 + 0.85 * (t / dur) ** rise_power
    return out / 4 * swell


def riser(dur):
    t = t_(dur)
    f = 110 * 2 ** (3 * t / dur)
    s = saw(f, t, 3, 0.25) * (0.45 + 0.55 * (t / dur) ** 1.5)
    return lp(s, 3000) * 0.35


def snare_roll(dur):
    out = np.zeros(int(dur * SR))
    tt = 0.0
    S = snare()
    while tt < dur:
        p = tt / dur
        s = int(tt * SR)
        k = min(len(S), len(out) - s)
        out[s:s + k] += S[:k] * (0.15 + 0.85 * p ** 2)
        tt += 0.25 * (1 - p) + 0.03
    return out * 0.6


def fanfare():
    t = t_(3.2)
    chord = [48, 55, 60, 64, 67, 72, 76]                 # C major, wide voicing
    s = np.zeros(len(t))
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * t) * np.clip((t - 0.3) / 0.5, 0, 1)
    for m in chord:
        s += saw(hz(m) * vib, t, 3, 0.18)
    env = np.minimum(1, t / 0.04) * (0.75 + 0.25 * np.exp(-t / 0.3)) * np.exp(-np.clip(t - 1.6, 0, None) / 0.7)
    # brassy filter: opens on the attack
    out = np.zeros(len(t))
    B = 2048
    zi = np.zeros((1, 2))
    for i in range(0, len(t), B):
        fc = 900 + 3200 * np.exp(-t[i] / 0.35) + 600
        out[i:i + B], zi = signal.sosfilt(signal.butter(2, fc, fs=SR, output="sos"), s[i:i + B], zi=zi)
    tim = np.zeros(len(t))
    for k, d in enumerate(np.arange(0, 0.5, 0.06)):
        tt = t_(0.5)
        hit = np.sin(2 * np.pi * (hz(36) + 30 * np.exp(-tt / 0.05)) * tt) * np.exp(-tt / 0.25) * (0.4 + k * 0.08)
        st = int(d * SR)
        tim[st:st + len(hit)] += hit[: len(tim) - st]
    return out * env / 3 + tim


# ---------------------------------------------------------------- loudness
def k_weight(x):
    b1, a1 = [1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585]
    b2, a2 = [1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621]
    return signal.lfilter(b2, a2, signal.lfilter(b1, a1, x, axis=-1), axis=-1)


def integrated_lufs(x):
    y = k_weight(x)
    blk, hop = int(0.4 * SR), int(0.1 * SR)
    ms = np.array([np.sum(np.mean(y[:, i:i + blk] ** 2, axis=1)) for i in range(0, y.shape[1] - blk + 1, hop)])
    ms = ms[-0.691 + 10 * np.log10(ms + 1e-20) > -70]
    rel = -0.691 + 10 * np.log10(np.mean(ms)) - 10
    ms = ms[-0.691 + 10 * np.log10(ms) > rel]
    return -0.691 + 10 * np.log10(np.mean(ms))


def true_peak_db(x):
    return 20 * np.log10(np.max(np.abs(signal.resample_poly(x, 4, 1, axis=-1))) + 1e-12)


def limit(x, ceil_db):
    ceil = 10 ** (ceil_db / 20)
    peak = np.abs(signal.resample_poly(x, 4, 1, axis=-1)).max(axis=0).reshape(-1, 4).max(axis=1)[: x.shape[1]]
    need = np.minimum(1.0, ceil / np.maximum(peak, 1e-9))
    L = int(SR * 0.005)
    g = uniform_filter1d(minimum_filter1d(need, size=2 * L + 1), size=L)
    return x * np.minimum(g, minimum_filter1d(need, size=3))


def reverb(x, wet, rt=0.45, length=1.8):
    n = int(SR * length)
    t = np.arange(n) / SR
    out = np.empty_like(x)
    for ch in range(2):
        ir = lp(np.random.default_rng(50 + ch).standard_normal(n) * np.exp(-t / rt), 6000, 1)
        ir[: int(SR * 0.015)] = 0
        ir /= np.sqrt(np.sum(ir ** 2))
        out[ch] = signal.fftconvolve(x[ch], ir)[: x.shape[1]]
    return x * (1 - wet) + out * wet * 1.5


# ---------------------------------------------------------------- main
def main(ev_path, out_path):
    ev = json.loads(Path(ev_path).read_text())
    fps = ev["fps"]
    end = ev["totalFrames"] / fps
    n = int(round(end * SR))
    fsec = lambda f: f / fps  # noqa: E731
    elim_frames = sorted(e["frame"] for e in ev["elims"])
    total = len(ev["countries"])
    alive_at = lambda t: total - sum(1 for f in elim_frames if fsec(f) <= t)  # noqa: E731
    slow, kill, win = fsec(ev["slowStartFrame"]), fsec(ev["killFrame"]), fsec(ev["winnerFrame"])
    duel = fsec(ev["gapCloseFrame"]) if ev["gapCloseFrame"] is not None else slow - 4
    # groove resumes on the first bar line after the fanfare has landed
    resume = np.ceil((win + 1.3) / BEAT) * BEAT
    music = groove(end, alive_at, slow + 0.35, resume, end)[:, :n]
    # filter the groove away into the slow-motion
    tt = np.arange(n) / SR
    fade = np.clip(1 - (tt - slow) / 0.35, 0, 1)
    fade[tt >= resume - 0.01] = 1
    music *= fade
    fx, hits = np.zeros((2, n)), np.zeros((2, n))

    # collision hits: merge hits closer than 2 frames, keep the strongest impact
    last_f, last_amp = -99, 0
    placed = []
    for h in sorted(ev["hits"], key=lambda h: h["frame"]):
        if h["frame"] - last_f < 2 and placed:
            if h["impact"] > placed[-1]["impact"]:
                placed[-1]["impact"] = h["impact"]
            continue
        placed.append(dict(h))
        last_f = h["frame"]
    for h in placed:
        pan = 0.5 + 0.35 * (h["x"] - 540) / 540
        place(hits, h["frame"] * SR // fps, hit_sound(h["impact"]), 0.7, pan, is_sample=True)
    # eliminations
    for e in ev["elims"]:
        big = e["frame"] == ev["killFrame"]
        pan = 0.5 + 0.3 * (e["x"] - 540) / 540
        if e["cause"] == "escape":
            place(fx, e["frame"] * SR // fps, whoop(), 0.9, pan, is_sample=True)
        place(fx, e["shatterFrame"] * SR // fps, glass(big), 1.2 if big else 0.85, pan, is_sample=True)
    # duel build: crowd from the gap sealing to the kill, riser + snare roll over the slow-motion
    cr = crowd(kill - duel, 1.0)
    place(fx[:1], duel, cr[0], 1.7)
    place(fx[1:], duel, cr[1], 1.7)
    place(fx, slow, riser(kill - slow), 1.8)
    place(fx, slow, snare_roll(kill - slow), 1.2)
    place(fx, kill, boom(), 1.0)
    # winner: fanfare + cheer
    place(fx, win, fanfare(), 1.0)
    ch = crowd(3.0, 0.3) * np.exp(-np.linspace(0, 3, int(3.0 * SR)) / 1.6)
    place(fx[:1], win, ch[0], 0.5)
    place(fx[1:], win, ch[1], 0.5)

    mix = reverb(music, 0.08) + reverb(hits, 0.06) + reverb(fx, 0.22)
    out_fade = int(0.4 * SR)
    mix[:, -out_fade:] *= np.linspace(1, 0, out_fade)
    gain_total = 1.0
    x = mix
    for _ in range(6):
        g = 10 ** ((TARGET_LUFS - integrated_lufs(x)) / 20)
        gain_total *= g
        x = limit(x * g, CEIL_DBTP - 0.3)
        if abs(integrated_lufs(x) - TARGET_LUFS) < 0.1 and true_peak_db(x) <= CEIL_DBTP:
            break
    wavfile.write(out_path, SR, x.T.astype(np.float32))
    wavfile.write(Path(out_path).with_name("stem_hits.wav"), SR, (hits * gain_total).T.astype(np.float32))
    Path(out_path).with_name("hits_placed.json").write_text(json.dumps([{"frame": h["frame"], "impact": h["impact"]} for h in placed]))
    print(f"audio: {end:.2f}s · {len(placed)} hit sounds from {len(ev['hits'])} collisions · {len(ev['elims'])} shatters · "
          f"{integrated_lufs(x):.2f} LUFS · {true_peak_db(x):.2f} dBTP → {out_path}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
