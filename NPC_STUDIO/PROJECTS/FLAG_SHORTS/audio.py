"""Soundtrack synthesised with numpy only (no samples, no external files)."""
import wave

import numpy as np

from render import heartbeats

SR = 48000
PENT = [0, 2, 4, 7, 9]


def _place(buf, t, sig, gain=1.0, pan=0.5):
    s = int(round(t * SR))
    if s >= buf.shape[1] or s < 0:
        return
    k = min(len(sig), buf.shape[1] - s)
    buf[0, s:s + k] += sig[:k] * gain * np.cos(pan * np.pi / 2) * 1.414
    buf[1, s:s + k] += sig[:k] * gain * np.sin(pan * np.pi / 2) * 1.414


def _t(d):
    return np.arange(int(d * SR)) / SR


def note(freq, vel):
    """Soft mallet-like note."""
    t = _t(0.45)
    env = np.minimum(1, t / 0.004) * np.exp(-t / 0.11)
    s = np.sin(2 * np.pi * freq * t) + 0.28 * np.sin(2 * np.pi * 2 * freq * t) * np.exp(-t / 0.05) + 0.08 * np.sin(2 * np.pi * 4.01 * freq * t) * np.exp(-t / 0.02)
    return s * env * vel


def blip():
    t = _t(0.22)
    f = 520 * np.exp(-t / 0.09) + 140
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.07) * np.minimum(1, t / 0.003)


def boom(rng):
    t = _t(1.8)
    f = 34 + 75 * np.exp(-t / 0.12)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.55)
    noise = rng.standard_normal(len(t))
    k = np.ones(220) / 220                                   # crude low-pass (moving average)
    noise = np.convolve(noise, k, mode="same") * 14 * np.exp(-t / 0.16)
    return np.tanh(1.7 * (sub + 0.5 * noise)) * np.minimum(1, t / 0.002)


def heart():
    t = _t(0.5)
    def thump(t0, f0, a):
        tt = np.clip(t - t0, 0, None)
        return a * np.sin(2 * np.pi * (f0 + 30 * np.exp(-tt / 0.03)) * tt) * np.exp(-tt / 0.07) * (t >= t0)
    return thump(0, 52, 1.0) + thump(0.16, 62, 0.7)


def chime():
    t = _t(1.6)
    out = np.zeros(len(t))
    for k, m in enumerate([84, 88, 91, 96, 100]):            # C6 E6 G6 C7 E7 arpeggio
        f, t0 = 440 * 2 ** ((m - 69) / 12), k * 0.055
        tt = np.clip(t - t0, 0, None)
        bell = (np.sin(2 * np.pi * f * tt) + 0.45 * np.sin(2 * np.pi * 2.76 * f * tt) * np.exp(-tt / 0.25)
                + 0.2 * np.sin(2 * np.pi * 5.4 * f * tt) * np.exp(-tt / 0.1))
        out += bell * np.exp(-tt / 0.6) * np.minimum(1, tt / 0.002) * (t >= t0) * (1 - 0.1 * k)
    return out / 2.2


def build(res, cfg, path):
    fps = cfg["fps"]
    dur = res["total_frames"] / fps
    n = int(round(dur * SR))
    rng = np.random.default_rng(res["seed"])
    notes, fx, low = np.zeros((2, n)), np.zeros((2, n)), np.zeros((2, n))
    # bounces → pentatonic notes that climb while the rally lasts (resets whenever a ball is lost)
    exit_times = [e[0] for e in res["exits"]]
    last, step, ei, played = -1.0, 0, 0, 0
    for t, imp, kind, x in sorted(res["bounces"]):
        while ei < len(exit_times) and exit_times[ei] <= t:
            ei += 1
            step = 0
        if t - last < 0.05 or imp < 120:
            continue
        last = t
        k = step // 2
        k = k if k < 15 else 10 + (k - 10) % 5
        midi = 60 + 12 * (k // 5) + PENT[k % 5]
        vel = 0.25 + 0.75 * min(1.0, imp / 1800)
        _place(notes, t, note(440 * 2 ** ((midi - 69) / 12), vel), 0.5, 0.5 + 0.35 * max(-1, min(1, x / cfg["arena_radius"])))
        step += 1
        played += 1
    elim_t = {round(t, 4) for t, _ in res["elims"]}
    for e in res["exits"]:
        if round(e[0], 4) not in elim_t:
            _place(fx, e[0], blip(), 0.35, 0.5 + 0.35 * max(-1, min(1, e[3] / cfg["arena_radius"])))
    for t, _ in res["elims"]:
        _place(low, t, boom(rng), 1.0)
    hb = heart()
    beats = heartbeats(res["duel_t"], res["t_end"])
    for k, t in enumerate(beats):
        _place(low, t, hb, 0.55 + 0.35 * k / max(1, len(beats) - 1))
    _place(fx, res["t_end"], chime(), 0.9)
    mix = notes + fx + low
    # gentle soft-knee limiter, then peak-normalise to -1 dBFS: nothing can clip
    mix = np.tanh(mix * 0.9) / 0.9
    peak = np.max(np.abs(mix)) or 1.0
    mix *= 10 ** (-1 / 20) / peak
    fade = int(0.012 * SR)
    mix[:, -fade:] *= np.linspace(1, 0, fade)
    pcm = (mix.T * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return dict(notes=played, booms=len(res["elims"]), heartbeats=len(beats), peak_dbfs=round(20 * np.log10(np.max(np.abs(mix))), 2))
