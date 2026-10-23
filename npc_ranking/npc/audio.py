"""Sound design: synthesized score + SFX library, original clip audio time-mapped to the edit, VO mix with ducking."""
import subprocess

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

SR = 48000
rng = np.random.default_rng(11)


def bp(x, lo, hi): return sosfilt(butter(2, [lo, hi], btype="band", fs=SR, output="sos"), x)
def lp(x, hi, o=2): return sosfilt(butter(o, hi, btype="low", fs=SR, output="sos"), x)
def hp(x, lo): return sosfilt(butter(2, lo, btype="high", fs=SR, output="sos"), x)
def envx(n, tau): return np.exp(-np.arange(n) / (tau * SR))
def tone(f, dur):
    tt = np.arange(int(dur * SR)) / SR
    ph = 2 * np.pi * np.cumsum(np.broadcast_to(f, tt.shape) if np.ndim(f) else np.full(tt.shape, f)) / SR
    return np.sin(ph)


def place(buf, sig, t0, g=1.0):
    i = int(t0 * SR)
    if i < 0: sig, i = sig[-i:], 0
    j = min(len(buf), i + len(sig))
    if j > i: buf[i:j] += sig[:j - i] * g


# ------------------------------------------------------------------ SFX library
def bass_hit(dur=1.4, f0=90, f1=34, tau=0.4):
    n = int(dur * SR); tt = np.arange(n) / SR
    s = tone(f1 + (f0 - f1) * np.exp(-tt / 0.08), dur) * envx(n, tau)
    return np.tanh((s + lp(rng.normal(0, 1, n), 3000) * envx(n, 0.012) * 0.6) * 1.7)

def slam(dur=0.5):
    n = int(dur * SR)
    return bp(rng.normal(0, 1, n), 200, 5000) * envx(n, 0.06) * 0.8 + bass_hit(dur, 120, 50, 0.12) * 0.6

def whoosh(dur=0.4, up=True):
    n = int(dur * SR); x = rng.normal(0, 1, n); out = np.zeros(n)
    for s in range(12):
        a, b = s * n // 12, (s + 1) * n // 12
        fc = (300 + 3200 * s / 12) if up else (3500 - 3000 * s / 12)
        out[a:b] = bp(x, fc * 0.6, fc * 1.5)[a:b]
    return out * np.hanning(n)

def tick(f=2200):
    n = int(0.05 * SR); return tone(f, 0.05) * envx(n, 0.008)

def slide_whistle(dur=0.7, f0=1500, f1=420):
    n = int(dur * SR); tt = np.arange(n) / SR
    f = f0 * (f1 / f0) ** (tt / dur) * (1 + 0.015 * np.sin(2 * np.pi * 6 * tt))
    return (tone(f, dur) + 0.3 * tone(2 * f, dur)) * np.minimum(1, tt / 0.03) * np.minimum(1, (dur - tt) / 0.1) * 0.5

def zip_up(dur=0.35):
    n = int(dur * SR); tt = np.arange(n) / SR
    f = 400 * (8 ** (tt / dur))
    return np.sign(tone(f, dur)) * 0.25 * np.hanning(n) + whoosh(dur) * 0.6

def boing(dur=0.75, f0=180, rate=1.0):
    n = int(dur * SR); tt = np.arange(n) / SR
    f = f0 * (1 + 0.9 * np.exp(-tt / 0.18) * np.sin(2 * np.pi * 9 * rate * tt)) * (1 + 0.4 * tt)
    return (tone(f, dur) * 0.7 + tone(f * 2.01, dur) * 0.2) * envx(n, 0.3) * np.minimum(1, tt / 0.005)

def sting(dur=1.6):  # "dun-dun" low brass-ish hit
    n = int(dur * SR); out = np.zeros(n)
    for t0, f in ((0.0, 73.4), (0.32, 69.3)):
        m = n - int(t0 * SR); tt = np.arange(m) / SR
        s = sum(tone(f * h, m / SR) / h for h in (1, 2, 3, 4, 5)) * envx(m, 0.45)
        out[int(t0 * SR):] += lp(np.tanh(s * 1.5), 1800)
    return out * 0.6

def crack():
    n = int(0.06 * SR); return hp(rng.normal(0, 1, n), 1500) * envx(n, 0.006) * 1.2

def riser(dur):
    n = int(dur * SR); tt = np.arange(n) / SR
    s = tone(140 * 2 ** (2.6 * tt / dur), dur) * 0.4 + bp(rng.normal(0, 1, n), 800, 7000) * 0.35 * tt / dur
    return s * (tt / dur) ** 2

def rewind_blip(dur=0.3):
    n = int(dur * SR); tt = np.arange(n) / SR
    return tone(2400 - 2000 * tt / dur, dur) * 0.3 * np.hanning(n) + bp(rng.normal(0, 1, n), 2000, 8000) * 0.2 * np.hanning(n)

def reverb(x, dur=1.4, mix=0.35):
    n = int(dur * SR); ir = rng.normal(0, 1, n) * envx(n, dur / 5); ir = lp(ir, 5000); ir /= np.abs(ir).sum() / 8
    wet = np.convolve(x, ir)  # len(x) + n - 1 samples
    out = np.zeros(len(wet)); out[:len(x)] += x * (1 - mix); out += wet * mix
    return out


# ------------------------------------------------------------------ score
def score(total, bpm, sections):
    """sections: list of (t0, t1, mode) with mode in full / filtered / off / drop."""
    n = int(total * SR); out = np.zeros(n); beat = 60 / bpm
    kick = bass_hit(0.35, 120, 45, 0.09) * 0.9
    clap = bp(rng.normal(0, 1, int(0.18 * SR)), 900, 6000) * envx(int(0.18 * SR), 0.04) * 0.45
    hat = hp(rng.normal(0, 1, int(0.05 * SR)), 7000) * envx(int(0.05 * SR), 0.01) * 0.25
    roots = [55.0, 55.0, 43.65, 49.0]  # A1 A1 F1 G1
    t = 0.0; b = 0
    while t < total:
        place(out, kick, t)
        if b % 2 == 1: place(out, clap, t)
        place(out, hat, t + beat / 2)
        bar = (b // 4) % 4
        bl = tone(roots[bar], beat * 0.9) * envx(int(beat * 0.9 * SR), 0.25) * 0.55
        place(out, np.tanh(bl * 2) * 0.6, t)
        t += beat; b += 1
    pad = (tone(110, total) * 0.25 + tone(164.8, total) * 0.15 + tone(220, total) * 0.1)[:n]
    out += lp(pad, 900) * 0.5
    gain = np.zeros(n); filt = np.zeros(n, bool)
    for t0, t1, mode in sections:
        i, j = int(t0 * SR), min(n, int(t1 * SR))
        gain[i:j] = {"full": 1.0, "filtered": 0.8, "off": 0.0, "drop": 1.25}[mode]
        if mode == "filtered": filt[i:j] = True
    gain = np.convolve(gain, np.ones(960) / 960, "same")  # 20 ms fades between sections
    filtered = lp(out, 500, 4)
    return np.where(filt, filtered, out) * gain


# ------------------------------------------------------------------ clip audio, time-mapped
def clip_audio(cfg, root, segs, total):
    src = cfg["sources"][cfg["audio_source"]]
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", f"{root}/{src['file']}", "-ac", "1", "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.float32).astype(np.float64)
    out = np.zeros(int(total * SR))
    for s in segs:
        for p in s["pcs"]:
            if "freeze" in p: continue
            i0, i1 = int((p["a"] - src["offset"]) * SR), int((p["b"] - src["offset"]) * SR)
            chunk = a[max(0, i0):max(0, i1)]
            if len(chunk) < 10: continue
            m = int(len(chunk) / p["speed"])
            res = np.interp(np.linspace(0, len(chunk) - 1, m), np.arange(len(chunk)), chunk)  # varispeed
            fade = min(len(res) // 2, int(0.015 * SR)); w = np.ones(len(res))
            w[:fade] = np.linspace(0, 1, fade); w[-fade:] = np.linspace(1, 0, fade)
            place(out, res * w * (0.6 if p["speed"] != 1 else 1.0), s["start"] + p["o0"])
    return out


def mix(cfg, root, segs, total, voice, out_path):
    snd = cfg["sound"]; S = {s["id"]: s for s in segs}; n = int(total * SR)
    st = lambda k: S[k]["start"]
    secs = [(0, st("r3"), "full"), (st("r3"), st("r3") + 5.2, "filtered"), (st("r3") + 5.2, st("r2"), "full"),
            (st("r2"), st("r2") + 1.55, "full"), (st("r2") + 1.55, st("r2") + 2.55, "off"),
            (st("r2") + 2.55, st("r1") + 5.55, "filtered"), (st("r1") + 5.55, total, "drop")]
    music = score(total, snd["bpm"], secs)
    fx = np.zeros(n)
    place(fx, bass_hit(1.6), 0.0, 1.0); place(fx, slam(), 0.0, 0.6)
    for s in segs[1:]:
        place(fx, whoosh(0.3), s["start"] - 0.28, 0.55)
        place(fx, bass_hit(1.2), s["start"], 0.8); place(fx, slam(), s["start"], 0.55)
        place(fx, tick(1800), s["start"] + 0.2, 0.5)
    r5, r4, r3, r2, r1 = (S[k] for k in ("r5", "r4", "r3", "r2", "r1"))
    place(fx, slide_whistle(), r5["start"] + 1.35, 0.55)                   # the yawn
    place(fx, whoosh(0.3), r5["start"] + 3.05, 0.35)                        # wing stretch
    place(fx, riser(0.5), r4["start"], 0.5)
    place(fx, zip_up(), r4["start"] + 0.5, 0.8); place(fx, bass_hit(1.0, 80, 40, 0.25), r4["start"] + 0.5, 0.6)
    place(fx, rewind_blip(), r4["start"] + 3.73, 0.6)
    for k in range(10):                                                     # waiting... (fast-forward)
        place(fx, tick(2600 if k % 2 else 2000), r3["start"] + 0.3 + k * 0.29, 0.35)
    place(fx, reverb(sting()), r3["start"] + 5.2, 0.8)                     # the face in the dark
    place(fx, riser(1.2), r2["start"], 0.35)
    place(fx, boing(), r2["start"] + 1.25, 0.9)                             # ears pop
    place(fx, bass_hit(1.0, 70, 40, 0.3), r2["start"] + 1.55, 0.7)          # freeze
    place(fx, rewind_blip(), r2["start"] + 2.5, 0.6)
    place(fx, boing(1.1, 120, 0.5), r2["start"] + 3.675, 0.8)               # slowed replay boing
    place(fx, riser(1.6), r1["start"] - 1.6, 0.6)
    for k, tc in enumerate((1.9, 2.25, 2.55, 3.0, 3.35)):                   # bone cracks on the stretch
        place(fx, crack(), r1["start"] + tc, 0.7 - 0.05 * k)
    place(fx, reverb(bass_hit(2.2, 100, 28, 0.7), 1.8, 0.3), r1["start"] + 5.55, 1.0)  # beat drop reveal
    t_end = next(f["t0"] for f in r1["fx"] if f["type"] == "endcard")
    place(fx, reverb(slam(), 1.2, 0.4), r1["start"] + t_end, 0.8)            # end card
    clip = clip_audio(cfg, root, segs, total)
    vo = np.zeros(n)
    for v in voice:
        s, _ = sf.read(v["file"]); place(vo, s, v["start"])
    vo = lp(hp(vo, 85), 13000); vo = vo / (np.abs(vo).max() + 1e-9) * 0.9
    env = lp(np.abs(vo), 7); env /= env.max() + 1e-9
    duck = 1 - snd["duck"] * np.clip(env * 3, 0, 1)
    m = vo + music * snd["music_level"] * duck + clip * snd["clip_audio_level"] * duck + fx * snd["sfx_level"] * (0.6 + 0.4 * duck)
    m = np.tanh(m * 1.05) * 0.95
    sf.write(out_path, np.stack([m, m], 1).astype(np.float32), SR, subtype="FLOAT")
    return {"peak": float(np.abs(m).max())}
