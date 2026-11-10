#!/usr/bin/env python3
"""mix.py — final mix: narration + ducked music + SFX, loudness-normalized.

  narration   each line placed at its resolved start time; narration bus set to -16 LUFS
  music       bed set to -22 LUFS, then ducked 8 dB under narration (sidechain: narration
              envelope, 20 ms attack / 300 ms release)
  sfx         cue levels already set per cue in synth.py (-27..-9 dBFS peak);
              ducked 3 dB under narration for intelligibility
  master      integrated loudness -> -14 LUFS, 4x-oversampled true-peak limiter at -1.5 dBTP,
              iterated until both targets hold.

Writes build/audio/mix.wav (48 kHz stereo float) and build/audio/mix_report.json.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
AUD = BUILD / "audio"
SR = 48000

NARRATION_LUFS = -16.0
MUSIC_LUFS = -22.0
DUCK_DB = 8.0
SFX_DUCK_DB = 3.0
TARGET_LUFS = -14.0
TP_CEILING = -1.5  # dBTP (leaves headroom for AAC encoding; spec requires <= -1.0)

meter = pyln.Meter(SR)


def lufs(x: np.ndarray) -> float:
    return meter.integrated_loudness(x.T if x.ndim == 2 else x)


def set_lufs(x, target):
    return x * 10 ** ((target - lufs(x)) / 20)


def true_peak_db(x: np.ndarray) -> float:
    up = resample_poly(x, 4, 1, axis=-1)
    return 20 * np.log10(np.max(np.abs(up)) + 1e-12)


def smooth(env: np.ndarray, attack: float, release: float) -> np.ndarray:
    """One-pole attack/release follower (vectorised in blocks via a simple loop on decimated data)."""
    hop = 48  # 1 ms
    e = env[: len(env) // hop * hop].reshape(-1, hop).max(axis=1)
    a_a, a_r = np.exp(-1 / (attack * 1000)), np.exp(-1 / (release * 1000))
    out = np.empty_like(e)
    y = 0.0
    for i, v in enumerate(e):
        c = a_a if v > y else a_r
        y = c * y + (1 - c) * v
        out[i] = y
    full = np.repeat(out, hop)
    return np.pad(full, (0, len(env) - len(full)), mode="edge")


def limiter(x: np.ndarray, ceiling_db: float) -> np.ndarray:
    """Look-ahead true-peak limiter: gain computed from 4x-oversampled peaks, 3 ms look-ahead."""
    ceil = 10 ** (ceiling_db / 20)
    up = np.max(np.abs(resample_poly(x, 4, 1, axis=-1)), axis=0)
    peak = up.reshape(-1, 4).max(axis=1)[: x.shape[1]]
    need = np.minimum(1.0, ceil / (peak + 1e-12))
    la = int(0.003 * SR)
    # look-ahead: minimum over the next `la` samples, then release smoothing
    from scipy.ndimage import minimum_filter1d
    g = minimum_filter1d(need, size=2 * la + 1, mode="nearest")
    rel = np.exp(-1 / (0.08 * SR))
    out = np.empty_like(g)
    y = 1.0
    for i in range(0, len(g), 32):  # block-wise release (fast enough, sample-accurate attack via min)
        blk = g[i:i + 32]
        m = blk.min()
        y = m if m < y else rel ** 32 * y + (1 - rel ** 32) * 1.0
        y = min(y, 1.0)
        out[i:i + 32] = np.minimum(blk, y)
    return x * out


def main() -> None:
    tl = json.loads((BUILD / "timeline.json").read_text())
    total = int(round(tl["duration"] * SR))

    # ---- narration ------------------------------------------------------------------------------
    narr = np.zeros(total)
    for i, sc in enumerate(tl["scenes"]):
        line, sr = sf.read(BUILD / "narration" / f"line_{i:02d}.wav", dtype="float64")
        assert sr == SR
        s = int(round(sc["narration"]["startSec"] * SR))
        narr[s:s + len(line)] += line[: total - s]
    narr = set_lufs(narr, NARRATION_LUFS)
    narr_st = np.stack([narr, narr])

    # ---- sidechain envelope -------------------------------------------------------------------------
    env_db = 20 * np.log10(np.abs(narr) + 1e-9)
    active = (env_db > -45).astype(float)
    duck = smooth(active, 0.02, 0.30)  # 0..1

    music, _ = sf.read(AUD / "music.wav", dtype="float64")
    sfx, _ = sf.read(AUD / "sfx.wav", dtype="float64")
    music, sfx = music.T[:, :total], sfx.T[:, :total]
    music = set_lufs(music, MUSIC_LUFS)
    music *= 10 ** (-DUCK_DB * duck / 20)
    sfx *= 10 ** (-SFX_DUCK_DB * duck / 20)

    mix = narr_st + music + sfx

    # ---- master: loudness + true peak, iterate --------------------------------------------------
    for it in range(6):
        mix = set_lufs(mix, TARGET_LUFS)
        mix = limiter(mix, TP_CEILING - 0.1)
        L, tp = lufs(mix), true_peak_db(mix)
        if abs(L - TARGET_LUFS) < 0.2 and tp <= TP_CEILING:
            break
    mix = mix[:, :total]
    sf.write(AUD / "mix.wav", mix.T.astype(np.float32), SR, subtype="FLOAT")
    rep = {"integrated_lufs": round(lufs(mix), 2), "true_peak_dbtp": round(true_peak_db(mix), 2),
           "duration_s": mix.shape[1] / SR, "iterations": it + 1,
           "narration_lufs": NARRATION_LUFS, "music_lufs": MUSIC_LUFS, "duck_db": DUCK_DB}
    (AUD / "mix_report.json").write_text(json.dumps(rep, indent=2))
    print(f"  mix: {rep['integrated_lufs']} LUFS, true peak {rep['true_peak_dbtp']} dBTP, {rep['duration_s']:.3f} s")


if __name__ == "__main__":
    main()
