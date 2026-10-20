"""Music analysis for beat-driven edits (built for super-slowed phonk).

    python analyze_music.py <audio> <out.json> [--plot out.png]

A plain beat tracker is unreliable on super-slowed phonk: the 808 is a long
gliding tone, swung percussion sits off the grid, and the strongest moments are
entrances after silence, not loud beats. STFT flux also smears onsets by up to
half a window, which is more than a frame at 60 fps. So this works in the
time domain at 1 ms resolution and combines independent measures:

  * onset "rise": how many dB the log-energy envelope climbs within 10 ms,
    summed over full band, high band (>1.5 kHz) and sub band (40-160 Hz),
  * beat period from the autocorrelation of the rise curve, refined by a comb fit,
  * beat phase from the strongest transients only (they sit on the beat;
    the numerous soft swung hits do not),
  * per beat: rise, energy jump before/after (dB), sub-bass level, 808 pitch,
  * per bar: sub profile, 808 melody, section label, chroma+MFCC similarity.

Strength is relative to the median drop downbeat, so "impact" means
"clearly stronger than an ordinary drop beat".
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import librosa
import numpy as np
from scipy import signal as ss
from scipy.ndimage import maximum_filter1d, median_filter

SR = 48000
MS = SR // 1000  # samples per millisecond; analysis curves run at 1 kHz


def decode(path: str) -> np.ndarray:
    """Any container ffmpeg reads -> float32 stereo at 48 kHz (no limiting, overs kept)."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).copy()


def log_env(x: np.ndarray, win_ms: float) -> np.ndarray:
    k = int(SR * win_ms / 1000)
    e = np.convolve(x.astype(np.float64) ** 2, np.ones(k) / k, mode="same")
    return 10 * np.log10(e[::MS] + 1e-10)


def rise(L: np.ndarray, lag: int = 10) -> np.ndarray:
    r = np.zeros_like(L)
    r[lag:] = L[lag:] - L[:-lag]
    return np.maximum(r, 0)


class Curves:
    """1 kHz analysis curves of one mono signal."""

    def __init__(self, y: np.ndarray):
        self.y = y
        hp = ss.sosfiltfilt(ss.butter(4, 1500, "highpass", fs=SR, output="sos"), y)
        sb = ss.sosfiltfilt(ss.butter(4, [40, 160], "bandpass", fs=SR, output="sos"), y)
        self.L_full, self.L_high, self.L_sub = log_env(y, 5), log_env(hp, 3), log_env(sb, 12)
        self.R_full, self.R_high, self.R_sub = rise(self.L_full), rise(self.L_high), rise(self.L_sub, 15)
        self.R = self.R_full + self.R_high + 0.5 * self.R_sub
        self.n = len(self.R)

    def at(self, x: np.ndarray, t: float, tol_ms: int = 12) -> float:
        i = int(round(t * 1000))
        return float(x[max(0, i - tol_ms): min(self.n, i + tol_ms + 1)].max())

    def mean_db(self, L: np.ndarray, a: float, b: float) -> float:
        i, j = max(0, int(a * 1000)), min(self.n, int(b * 1000))
        return float(10 * np.log10(np.mean(10 ** (L[i:j] / 10)) + 1e-10)) if j > i else -100.0

    def jump(self, L: np.ndarray, t: float) -> float:
        return self.mean_db(L, t + 0.003, t + 0.060) - self.mean_db(L, t - 0.120, t - 0.015)


def fit_grid(c: Curves, t_lo: float, t_hi: float) -> tuple[float, float]:
    i0, i1 = int(t_lo * 1000), int(t_hi * 1000)
    env = c.R[i0:i1] - c.R[i0:i1].mean()
    ac = ss.fftconvolve(env, env[::-1], mode="full")[len(env) - 1:]
    lag = np.arange(len(ac)) / 1000
    m = (lag > 0.40) & (lag < 0.75)
    P0 = float(lag[m][np.argmax(ac[m])])
    # refine the period over many beats: comb score with a +-3 ms tolerance
    Rt = maximum_filter1d(c.R, 7)

    def comb(P, ph):
        g = np.arange(ph + t_lo, t_hi, P)
        return Rt[np.round(g * 1000).astype(int)].mean()

    _, P = max((max(comb(P, ph) for ph in np.arange(0, P, 0.001)), P)
               for P in np.arange(P0 - 0.002, P0 + 0.002, 0.000005))
    # phase from the strongest transients only (top 1.5 %): circular mean of t mod P
    pk = [i for i in ss.find_peaks(c.R[i0:i1], distance=60)[0] + i0]
    thr = np.percentile(c.R[pk], 98.5)
    strong = np.array([i for i in pk if c.R[i] >= thr]) / 1000
    w = c.R[(strong * 1000).astype(int)]
    ang = 2 * np.pi * (strong % P) / P
    ph = (np.angle(np.sum(w * np.exp(1j * ang))) % (2 * np.pi)) * P / (2 * np.pi)
    return float(P), float(ph)


def detect_onsets(c: Curves) -> list[dict]:
    thr = median_filter(c.R, size=1001) + 6.0
    idx = ss.find_peaks(c.R, height=thr, distance=60)[0]
    out = []
    for i in idx:
        t = i / 1000
        out.append({"t": round(t, 4), "rise_db": round(float(c.R[i]), 1),
                    "rise_sub": round(float(c.R_sub[max(0, i - 8): i + 9].max()), 1),
                    "rise_high": round(float(c.R_high[max(0, i - 8): i + 9].max()), 1),
                    "level_after_db": round(c.mean_db(c.L_full, t, t + 0.08), 1)})
    return out


def pitch808(y: np.ndarray, t: float) -> float:
    a = int((t + 0.03) * SR)
    seg = y[a: a + int(0.30 * SR)]
    if len(seg) < int(0.30 * SR):
        return 0.0
    F = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), n=1 << 16))
    fq = np.fft.rfftfreq(1 << 16, 1 / SR)
    m = (fq > 28) & (fq < 130)
    return float(fq[m][np.argmax(F[m])])


def label_bars(bars: list[dict]) -> None:
    first_drop = next(i for i, b in enumerate(bars) if b["sub"] > 0.55)

    def label(bar, i):
        sp, s, h = bar["sub_profile"], bar["sub"], bar["hi"]
        if s > 0.55:
            return "drop"
        if sp[0] > 0.5 and max(sp[1:]) < 0.1:
            return "break"          # one hit, then the bass cuts out
        if 0.2 < s <= 0.55 and np.std(sp) < 0.15:
            return "build"          # steady four-on-the-floor kicks, no 808 melody
        if sp[-1] - sp[0] > 0.3:
            return "riser"          # 808 glides up into the next drop
        if max(sp) < 0.2:
            if i < first_drop:
                return "intro"
            return "outro" if h < 0.1 and i > len(bars) * 0.8 else "breakdown"
        return "transition"

    for i, bar in enumerate(bars):
        bar["label"] = label(bar, i)
    # a bass-out of at most two bars directly after a drop is a break, not a breakdown
    for i, bar in enumerate(bars):
        if bar["label"] == "breakdown" and i > 0 and bars[i - 1]["label"] in ("drop", "break"):
            run = 1
            while i + run < len(bars) and bars[i + run]["label"] == "breakdown":
                run += 1
            if run <= 2:
                for j in range(i, i + run):
                    bars[j]["label"] = "break"


def analyze_signal(y: np.ndarray, name: str, grid: tuple[float, float] | None = None) -> dict:
    dur = len(y) / SR
    c = Curves(y)
    active = np.nonzero(c.L_full > c.L_full.max() - 30)[0] / 1000
    P, ph = grid or fit_grid(c, float(active[0]) + 0.5, float(active[-1]) - 0.5)
    onsets = detect_onsets(c)

    S = np.abs(librosa.stft(y, n_fft=4096, hop_length=480))
    f = librosa.fft_frequencies(sr=SR, n_fft=4096)
    sub_rms = np.sqrt((S[(f >= 30) & (f < 100)] ** 2).mean(0))
    hi_rms = np.sqrt((S[f >= 2500] ** 2).mean(0))
    fr = lambda t: int(np.clip(round(t * SR / 480), 0, S.shape[1] - 1))

    beats = []
    for k in range(int((dur - ph) / P) + 1):
        t = ph + k * P
        if t > dur - 0.05:
            break
        beats.append({
            "beat": k, "t": round(t, 4),
            "rise_db": round(c.at(c.R, t), 1), "rise_sub": round(c.at(c.R_sub, t), 1),
            "rise_high": round(c.at(c.R_high, t), 1),
            "jump_full_db": round(c.jump(c.L_full, t), 1), "jump_sub_db": round(c.jump(c.L_sub, t), 1),
            "level_db": round(c.mean_db(c.L_full, t, t + 0.25), 1),
            "sub_level": float(sub_rms[fr(t): fr(t) + 25].mean()), "hi_level": float(hi_rms[fr(t): fr(t) + 25].mean()),
            "pitch_808": round(pitch808(y, t), 1),
        })
    smax, hmax = max(b["sub_level"] for b in beats), max(b["hi_level"] for b in beats)
    for b in beats:
        b["sub_level"], b["hi_level"] = round(b["sub_level"] / smax, 3), round(b["hi_level"] / hmax, 3)

    # downbeats: bar position where the sub level most often jumps up
    jumps = [np.mean([max(0, beats[k]["sub_level"] - beats[k - 1]["sub_level"])
                      for k in range(max(r, 1), len(beats), 4)]) for r in range(4)]
    db = int(np.argmax(jumps))
    ref = float(np.median([b["rise_db"] for b in beats if b["beat"] % 4 == db and b["sub_level"] > 0.6]) or 1.0)
    for b in beats:
        b["bar_pos"] = (b["beat"] - db) % 4 + 1
        s = b["rise_db"] / ref
        b["strength"] = round(s, 2)
        b["class"] = ("impact" if s >= 1.4 else "strong" if s >= 0.85 else "pulse" if s >= 0.45 else "soft")

    bars = []
    for k in range(db, len(beats) - 3, 4):
        bb = beats[k: k + 4]
        bars.append({"bar_start_beat": k, "t": bb[0]["t"],
                     "sub": round(float(np.mean([b["sub_level"] for b in bb])), 3),
                     "hi": round(float(np.mean([b["hi_level"] for b in bb])), 3),
                     "sub_profile": [b["sub_level"] for b in bb], "pitch_808": [b["pitch_808"] for b in bb]})
    sections = []
    if len(bars) > 4 and any(b["sub"] > 0.55 for b in bars):
        label_bars(bars)
        for bar in bars:
            if sections and sections[-1]["label"] == bar["label"]:
                sections[-1]["bars"] += 1
                sections[-1]["end_beat"] = bar["bar_start_beat"] + 4
            else:
                sections.append({"label": bar["label"], "start_beat": bar["bar_start_beat"],
                                 "end_beat": bar["bar_start_beat"] + 4, "bars": 1, "t": bar["t"]})
        for s in sections:
            s["t_end"] = round(ph + s["end_beat"] * P, 4)

    C = librosa.feature.chroma_stft(S=S ** 2, sr=SR)
    M = librosa.feature.mfcc(S=librosa.power_to_db(librosa.feature.melspectrogram(S=S ** 2, sr=SR)), n_mfcc=20)
    def bfeat(k):
        v = []
        for j in range(4):
            a, b = fr(ph + (k + j) * P), fr(ph + (k + j + 1) * P)
            v.append(np.concatenate([C[:, a:b].mean(1) * 3, M[1:, a:b].mean(1) / 40]))
        return np.concatenate(v)
    F = np.array([bfeat(b["bar_start_beat"]) for b in bars]) if bars else np.zeros((0, 1))
    Fn = F / (np.linalg.norm(F, axis=1, keepdims=True) + 1e-9)

    for o in onsets:
        d = (o["t"] - ph) / P
        o["beat"] = round(d, 2)
        o["grid"] = "beat" if abs(d - round(d)) * P < 0.015 else "eighth" if abs(2 * d - round(2 * d)) * P / 2 < 0.015 else "off"

    return {
        "source": name, "duration": round(dur, 4), "sample_rate": SR,
        "tempo_bpm": round(60 / P, 3), "beat_period": round(P, 6), "grid_phase": round(ph, 4),
        "downbeat_offset": db, "strength_reference_rise_db": round(ref, 1),
        "sections": sections, "bars": bars, "beats": beats, "onsets": onsets,
        "bar_similarity": (Fn @ Fn.T).round(4).tolist(),
        "_plot": {"t": (np.arange(0, c.n, 8) / 1000).tolist(), "L_full": c.L_full[::8].tolist(),
                  "L_sub": c.L_sub[::8].tolist(), "R": maximum_filter1d(c.R, 8)[::8].tolist()},
    }


def plot(res: dict, out: str, events: list[dict] | None = None) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    p = res["_plot"]
    fig, ax = plt.subplots(3, 1, figsize=(28, 10), sharex=True)
    ax[0].plot(p["t"], p["L_full"], lw=0.5, color="k"); ax[0].set_ylabel("level dB"); ax[0].set_ylim(-80, 0)
    ax[1].plot(p["t"], p["L_sub"], lw=0.5); ax[1].set_ylabel("sub 40-160 dB"); ax[1].set_ylim(-80, 0)
    ax[2].plot(p["t"], p["R"], lw=0.5, color="g"); ax[2].set_ylabel("onset rise dB")
    colors = {"drop": "#d33", "break": "#33d", "breakdown": "#39f", "build": "#f90", "intro": "#999",
              "outro": "#555", "riser": "#c6c", "transition": "#6c6"}
    for s in res["sections"]:
        for a in ax:
            a.axvspan(s["t"], s["t_end"], color=colors.get(s["label"], "#eee"), alpha=0.13)
        ax[0].text(s["t"] + 0.05, -6, s["label"], fontsize=9)
    for b in res["beats"]:
        if b["class"] == "impact":
            for a in ax:
                a.axvline(b["t"], color="r", lw=1.4)
        elif b["bar_pos"] == 1:
            ax[2].axvline(b["t"], color="k", lw=0.3, alpha=0.4)
    for e in events or []:
        for a in ax:
            a.axvline(e["t"], color="#0a0", lw=0.8, ls="--")
        ax[0].text(e["t"], -78, e["id"], fontsize=7, rotation=90, va="bottom")
    step = 1 if res["duration"] < 50 else 2
    ax[2].set_xticks(np.arange(0, res["duration"], step))
    ax[2].set_xlim(0, res["duration"])
    plt.tight_layout()
    plt.savefig(out, dpi=50)
    plt.close()


def main(argv: list[str]) -> dict:
    y = decode(argv[1]).mean(1)
    res = analyze_signal(y, Path(argv[1]).name)
    if "--plot" in argv:
        plot(res, argv[argv.index("--plot") + 1])
    res.pop("_plot")
    Path(argv[2]).write_text(json.dumps(res, indent=1))
    print(f"tempo {res['tempo_bpm']} BPM  period {res['beat_period']}s  phase {res['grid_phase']}s  "
          f"downbeat offset {res['downbeat_offset']}  ref rise {res['strength_reference_rise_db']} dB")
    for s in res["sections"]:
        print(f"  {s['label']:10s} beats {s['start_beat']:3d}-{s['end_beat']:3d}  {s['t']:8.3f}-{s['t_end']:8.3f}s ({s['bars']} bars)")
    print("  impacts:", [(b["beat"], b["t"], b["rise_db"], b["strength"]) for b in res["beats"] if b["class"] == "impact"])
    return res


if __name__ == "__main__":
    main(sys.argv)
