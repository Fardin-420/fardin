"""Sound for flat 2D explainer projects: a light plucked score plus cartoon foley.

    python SOUND_ENGINE/explainer_sound.py PROJECTS/PERSIAN_TWO_DIALECTS_EN

Like sound_engine.py, every effect sits on a named cue from source/timeline.json,
so nothing is heard without something happening on screen. The bed and effects
duck under the narration (sound_engine.sidechain) and the master goes to -14 LUFS
with a -1.5 dBTP look-ahead limiter.

Writes audio/mix.wav (48 kHz stereo).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pyloudnorm as pyln
import soundfile as sf

from sound_engine import (IR_HALL, IR_ROOM, SR, Track, bandpass, env_ad, highpass, lowpass, noise, pan, secs,
                          sidechain, sub_impact, true_peak_limit, tvec, verb, whoosh)

# D Shur-flavoured scale (D Eb F G A Bb C), the mode much Persian folk music sits in.
SCALE = [0, 1, 3, 5, 7, 8, 10]
D3 = 146.83


def note(deg: int, octave: int = 0) -> float:
    o, d = divmod(deg, 7)
    return D3 * 2 ** (octave + o + SCALE[d] / 12)


def pluck(f: float, dur: float = 0.5, bright: float = 1.0) -> np.ndarray:
    """Santur-ish struck string: a few inharmonic partials with fast decay."""
    t = tvec(dur)
    x = sum(np.sin(2 * np.pi * f * k * 1.0015 ** k * t) * np.exp(-t * (5 + 4 * k / bright)) / k for k in (1, 2, 3, 4))
    return x * env_ad(len(t), 0.002, dur, 1.5)


def bass(f: float, dur: float) -> np.ndarray:
    t = tvec(dur)
    return lowpass(np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t), 400, 2) * env_ad(len(t), 0.005, dur, 2.5)


def score(dur: float, bpm: float = 112) -> np.ndarray:
    """A two-bar plucked ostinato over a simple dombak-like groove, looped."""
    beat = 60 / bpm
    out = Track(dur + 2)
    melody = [0, 2, 4, 2, 5, 4, 2, 1, 0, 2, 4, 6, 5, 4, 2, 0]
    basses = [0, 0, 3, 4]
    rng = np.random.default_rng(31)
    t, i = 0.0, 0
    while t < dur:
        step = i % 16
        out.add(t, pan(pluck(note(melody[step], 1), 0.45) * 0.22, -0.25 + 0.5 * (step % 2)))
        if step % 4 == 0:
            out.add(t, pan(bass(note(basses[(i // 4) % 4], -1), beat * 1.8) * 0.35, 0))
            dum = sub_impact(0.18, 110, 60, 0.35)
            out.add(t, dum)
        if step % 4 == 2:
            tak = highpass(noise(0.08), 1800) * np.exp(-tvec(0.08) * 60) * 0.12
            out.add(t, pan(tak, 0.2))
        if step % 2 == 1:
            sh = bandpass(noise(0.05), 5000, 11000, 2) * np.exp(-tvec(0.05) * 70) * rng.uniform(0.04, 0.07)
            out.add(t, pan(sh, -0.3))
        t += beat / 2
        i += 1
    bed = verb(out.buf[: secs(dur)], IR_ROOM, 0.18)
    fade = np.minimum(1, np.minimum(np.arange(len(bed)) / secs(1.0), (len(bed) - np.arange(len(bed))) / secs(1.5)))
    return bed * fade[:, None]


# ───────────────────────── foley ─────────────────────────

def pop(f: float = 900) -> np.ndarray:
    t = tvec(0.12)
    x = np.sin(2 * np.pi * np.cumsum(f * (1 + 1.5 * np.exp(-t * 60))) / SR) * np.exp(-t * 35)
    return pan(x * 0.5, 0)


def ding(f: float = 1320) -> np.ndarray:
    t = tvec(1.4)
    x = sum(np.sin(2 * np.pi * f * r * t) * np.exp(-t * (2.5 + 2 * k)) / (k + 1) for k, r in enumerate((1, 2.76, 5.4)))
    return verb(pan(x * 0.35, 0), IR_HALL, 0.3)


def boing(dur: float = 0.5) -> np.ndarray:
    t = tvec(dur)
    f = 220 + 160 * np.sin(2 * np.pi * 11 * t) * np.exp(-t * 4)
    return pan(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5) * 0.45, 0)


def stamp() -> np.ndarray:
    t = tvec(0.25)
    body = lowpass(noise(0.25), 500) * np.exp(-t * 30)
    return verb(pan(np.tanh(body * 3) * 0.6, 0), IR_ROOM, 0.2)


def tick(dur: float = 1.0, rate: float = 14) -> np.ndarray:
    out = Track(dur)
    for k in range(int(dur * rate)):
        x = bandpass(noise(0.015), 3000, 8000, 2) * np.exp(-tvec(0.015) * 300) * (0.35 if k % 2 else 0.22)
        out.add(k / rate, pan(x, 0.2 if k % 2 else -0.2))
    return out.buf


def clink() -> np.ndarray:
    t = tvec(0.5)
    x = sum(np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, d in ((2900, 14), (4100, 18), (5600, 25)))
    return verb(pan(x * 0.12, 0.3), IR_ROOM, 0.25)


def layer(*parts: np.ndarray) -> np.ndarray:
    out = np.zeros((max(len(x) for x in parts), 2))
    for x in parts:
        out[: len(x)] += x
    return out


def bonk() -> np.ndarray:
    return layer(sub_impact(0.5, 160, 70, 0.5), pan(bandpass(noise(0.08), 600, 2500, 2) * np.exp(-tvec(0.08) * 50) * 0.6, 0))


def chord_end() -> np.ndarray:
    return layer(*(pan(pluck(note(d, 1), 2.4, 0.6) * 0.3, p) for d, p in ((0, -0.4), (2, 0), (4, 0.4))), ding(note(0, 3)) * 0.4)


def build(project: Path) -> None:
    tl = json.loads((project / "source" / "timeline.json").read_text())
    c = tl["cues"]
    dur = tl["duration"]
    sfx = Track(dur)

    for s in tl["scenes"][1:]:
        sfx.add(s["start"] - 0.22, whoosh(0.4, 400, 5000), -8)
    pops = ["map_iran", "map_afghan", "tomato", "label_iran_tomato", "potato_iran", "potato_afghan", "car_iran", "car_afghan",
            "ice_iran", "ice_afghan", "maqbul", "exam_card", "tired_iran", "tired_afghan", "merci", "zinda", "after1", "after2",
            "insist", "tea", "pulao", "moms", "lion", "milk", "sher", "shir2", "older", "balkh", "claim_iran", "claim_afghan",
            "claim_turkey", "table", "tomato_end"]
    for k, name in enumerate(pops):
        sfx.add(c[name], pop(700 + 140 * (k % 5)), -10)
    for name in ("title", "taarof_champ", "hosp_champ", "heart", "hafez", "rumi_name"):
        sfx.add(c[name], ding(1320 if name != "heart" else 1760), -11)
    sfx.add(c["label_roman"], boing(), -7)
    sfx.add(c["apart"], boing(0.4), -9)
    sfx.add(c["exam"], stamp(), -5)
    sfx.add(c["clock"], tick(1.0), -8)
    for k in range(3):
        sfx.add(c["plates"] + 0.28 * k, clink(), -6)
    sfx.add(c["nextday"], whoosh(1.2, 200, 2500, 0.6, -0.6), -12)
    for at in (c["slipper"], c["slipper"] + 0.3):
        sfx.add(at - 0.5, whoosh(0.5, 600, 3000, 0.8, -0.2), -10)
        sfx.add(at, bonk(), -4)
    sfx.add(c["slipper"] + 0.45, pan(np.sin(2 * np.pi * np.cumsum(1400 + 400 * np.sin(2 * np.pi * 7 * tvec(1.0))) / SR) * np.exp(-tvec(1.0) * 3) * 0.08, 0), -6)
    sfx.add(c["dervish"] - 0.3, whoosh(0.9, 300, 3000, -0.6, 0.6), -11)
    sfx.add(c["tomb"], ding(990), -12)
    sfx.add(c["end"] - 0.1, chord_end(), -5)

    bed = score(dur)
    voice, _ = sf.read(project / "audio" / "narration" / "narration.wav", dtype="float64")
    v = np.zeros(len(sfx.buf))
    v[: min(len(v), len(voice))] = voice[: len(v)]
    bed_d, sfx_d = sidechain(v, bed * 10 ** (-13 / 20), sfx.buf)
    mix = bed_d + sfx_d + pan(v, 0) * 1.0
    meter = pyln.Meter(SR)
    mix *= 10 ** ((-14 - meter.integrated_loudness(mix)) / 20)
    mix = true_peak_limit(mix, -1.5)
    out = project / "audio" / "mix.wav"
    sf.write(out, mix.astype(np.float32), SR)
    print(f"mix {len(mix) / SR:.2f}s  {meter.integrated_loudness(mix):.1f} LUFS  peak {20 * np.log10(np.abs(mix).max()):.1f} dBFS -> {out}")


if __name__ == "__main__":
    build(Path(sys.argv[1]).resolve())
