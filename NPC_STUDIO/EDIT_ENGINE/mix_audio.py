"""Final soundtrack: edited music + sparse transition sound design + true-peak master.

    python mix_audio.py <project>      -> audio/mix.wav (48 kHz float, exactly frames/fps long)

Gain staging: the decoded track already overshoots full scale (AAC overs up to
+1.2 dBFS), so the music is trimmed before anything is added, and a look-ahead
true-peak limiter (4x oversampled) holds the master at -1.0 dBTP. No compression
or EQ is applied to the music: its pitch, rhythm and dynamics stay as released.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "SOUND_ENGINE"))
import sound_engine as se  # noqa: E402

SR = se.SR
CEILING_DB = -1.0
MUSIC_TRIM_DB = -2.0


def shimmer(dur=1.5):
    """Airy rising sparkle: high sine grains whose density and pitch grow toward the end."""
    r = np.random.default_rng(56)
    out = np.zeros((se.secs(dur), 2))
    for _ in range(140):
        u = r.random() ** 0.5                    # denser near the end
        at = u * (dur - 0.06)
        t = se.tvec(0.06)
        f = 3000 + 6000 * u * r.uniform(0.8, 1.2)
        x = np.sin(2 * np.pi * f * t) * np.hanning(len(t)) * r.uniform(0.05, 0.2) * (0.3 + 0.7 * u)
        j = se.secs(at)
        out[j:j + len(x)] += se.pan(x, r.uniform(-0.9, 0.9))
    return se.verb(out, se.IR_HALL, 0.45)


def shimmer_tail(dur=2.2):
    return shimmer(dur)[::-1] * np.linspace(1, 0, se.secs(dur))[:, None] ** 2


def make(kind, p):
    if kind == "shimmer":
        return shimmer(**p)
    if kind == "shimmer_tail":
        return shimmer_tail(**p)
    return getattr(se, kind)(**p)


def lufs(x):
    import pyloudnorm as pyln
    return pyln.Meter(SR).integrated_loudness(x)


def true_peak_db(x):
    from scipy import signal
    return 20 * np.log10(np.abs(signal.resample_poly(x, 4, 1, axis=0)).max() + 1e-12)


def main(project: Path) -> dict:
    ev = json.loads((project / "source/music_events.json").read_text())
    fps = ev["fps"]
    n = int(round(ev["frames"] / fps * SR))
    music, sr = sf.read(project / "audio/music_edit.wav", dtype="float64")
    assert sr == SR
    music = np.pad(music, ((0, max(0, n - len(music))), (0, 0)))[:n]
    src_peak = true_peak_db(music)
    music *= 10 ** (MUSIC_TRIM_DB / 20)

    spec = importlib.util.spec_from_file_location("edit", project / "source/edit.py")
    sys.path.insert(0, str(ROOT / "EDIT_ENGINE"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    frames = {b["n"]: b["frame"] for b in ev["beats"]}

    def beat(k):  # same impact frames as the picture (engine.Ctx.beat)
        if float(k).is_integer() and int(k) in frames:
            return frames[int(k)] / fps
        t = ev["entrance_t"] + k * ev["beat_period"] + ev["onset_offset_from_grid_ms"] / 1000
        return float(np.ceil(t * fps - 0.6)) / fps

    sfx = np.zeros_like(music)
    placed = []
    for kind, t, align, gain, p in mod.sound_cues(beat):
        x = make(kind, p)
        if x.ndim == 1:
            x = np.column_stack([x, x])
        if align == "start":
            i = se.secs(t)
        elif align == "end":
            i = se.secs(t) - len(x)
        else:  # peak of the envelope lands on t
            env = np.abs(x).mean(1)
            env = np.convolve(env, np.ones(480) / 480, mode="same")
            i = se.secs(t) - int(np.argmax(env))
        x = x / (np.abs(x).max() + 1e-9) * 10 ** (gain / 20)
        a, b = max(0, i), min(n, i + len(x))
        sfx[a:b] += x[a - i:b - i]
        placed.append({"kind": kind, "t": round(t, 3), "align": align, "gain_db": gain})

    mix = music + sfx
    pre_peak = true_peak_db(mix)
    master = se.true_peak_limit(mix, CEILING_DB - 0.15)
    master = np.clip(master, -1, 1)
    # gentle 4 ms fade-in so the first sample is clean; the ending fade is the edit's own
    master[: se.secs(0.004)] *= np.linspace(0, 1, se.secs(0.004))[:, None]
    sf.write(project / "audio/mix.wav", master.astype(np.float32), SR, subtype="FLOAT")
    loud = np.abs(mix).max(1) > 1e-3  # measure gain reduction only where there is signal
    loud[: se.secs(0.01)] = False      # (the 4 ms de-click fade is not limiting)
    gr = 20 * np.log10(np.abs(master).max(1)[loud] / np.abs(mix).max(1)[loud])
    rep = {"samples": n, "duration": n / SR, "source_true_peak_dbtp": round(float(src_peak), 2),
           "pre_limiter_true_peak_dbtp": round(float(pre_peak), 2), "master_true_peak_dbtp": round(float(true_peak_db(master)), 2),
           "max_gain_reduction_db": round(float(-gr.min()), 2),
           "limited_ms": round(1000 * float((gr < -0.1).sum()) / SR, 1),
           "integrated_lufs": round(float(lufs(master)), 2), "music_lufs": round(float(lufs(music)), 2), "sfx": placed}
    (project / "audio/mix_report.json").write_text(json.dumps(rep, indent=1))
    return rep


if __name__ == "__main__":
    r = main(Path(sys.argv[1]))
    print({k: v for k, v in r.items() if k != "sfx"})
