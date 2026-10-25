import numpy as np
from scipy.signal import butter, sosfilt
SR = 48000
# ------------------------------------------------------------------ audio
arng = np.random.default_rng(42)
def bp(x, lo, hi): return sosfilt(butter(2, [lo, hi], btype="band", fs=SR, output="sos"), x)
def lp(x, hi, o=2): return sosfilt(butter(o, hi, btype="low", fs=SR, output="sos"), x)
def hp(x, lo): return sosfilt(butter(2, lo, btype="high", fs=SR, output="sos"), x)
def envx(n, tau): return np.exp(-np.arange(n) / (tau * SR))
def place(buf, sig, t0, g=1.0):
    i = int(t0 * SR)
    if i < 0: sig, i = sig[-i:], 0
    j = min(len(buf), i + len(sig))
    if j > i: buf[i:j] += sig[:j - i] * g
def osc(freq, n, kind="saw"):
    ph = np.cumsum(np.broadcast_to(freq, (n,)) / SR) % 1.0
    return 2 * ph - 1 if kind == "saw" else np.sin(2 * np.pi * ph)
def boom(dur=2.0, f0=90, f1=28, tau=0.6):
    n = int(dur * SR); tt = np.arange(n) / SR
    s = osc(f1 + (f0 - f1) * np.exp(-tt / 0.09), n, "sin") * envx(n, tau)
    return np.tanh((s + lp(arng.normal(0, 1, n), 2500) * envx(n, 0.02) * 0.5) * 1.6)
def crack(dur=0.6):
    n = int(dur * SR); return hp(arng.normal(0, 1, n), 1200) * envx(n, 0.05) * 0.9
def whoosh(dur=0.6):
    n = int(dur * SR); x = arng.normal(0, 1, n); out = np.zeros(n)
    for s in range(12):
        a, b = s * n // 12, (s + 1) * n // 12; fc = 250 + 3000 * s / 12
        out[a:b] = bp(x, fc * 0.6, fc * 1.5)[a:b]
    return out * np.hanning(n)
def tick(f=1500): n = int(0.05 * SR); return osc(f, n, "sin") * envx(n, 0.008)
def riser(dur, f0=90):
    n = int(dur * SR); tt = np.arange(n) / SR
    return (osc(f0 * 2 ** (2.5 * tt / dur), n, "sin") * 0.4 + bp(arng.normal(0, 1, n), 800, 7000) * 0.3 * tt / dur) * (tt / dur) ** 2
def groan(dur=1.6):
    n = int(dur * SR); tt = np.arange(n) / SR
    f = 120 * np.exp(-tt / 0.8) + 32
    return lp(osc(f * (1 + 0.03 * np.sin(2 * np.pi * 9 * tt)), n), 700) * np.minimum(1, tt / 0.05) * np.minimum(1, (dur - tt) / 0.3)
def wind(dur, gust=0.35):
    """Howling wind: band-passed noise with slow gusts and a moving whistle."""
    n = int(dur * SR); tt = np.arange(n) / SR
    x = arng.normal(0, 1, n)
    body = lp(x, 900) * 0.9 + bp(x, 900, 3500) * 0.35
    g = 0.6 + gust * np.sin(2 * np.pi * 0.31 * tt) + 0.25 * np.sin(2 * np.pi * 0.83 * tt + 1)
    whistle = osc(700 + 250 * np.sin(2 * np.pi * 0.2 * tt), n, "sin") * 0.04 * (g > 0.9)
    return (body * g + whistle) * np.minimum(1, tt / 0.6) * np.minimum(1, (dur - tt) / 0.6)
def surf(dur):
    n = int(dur * SR); tt = np.arange(n) / SR
    x = lp(arng.normal(0, 1, n), 400) * 1.6
    sw = 0.5 + 0.5 * np.sin(2 * np.pi * 0.25 * tt) ** 2
    return x * sw * np.minimum(1, tt / 0.8) * np.minimum(1, (dur - tt) / 0.8)
def reverb(x, dur=3.0, mix=0.4):
    n = int(dur * SR); ir = lp(arng.normal(0, 1, n), 5000) * envx(n, dur / 5); ir /= np.abs(ir).sum() / 8
    wet = np.convolve(x, ir); out = np.zeros(len(wet)); out[:len(x)] += x * (1 - mix); out += wet * mix
    return out

