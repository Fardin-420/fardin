"""Soundtrack: original synthesized score + SFX locked to timeline events, mastered.

    python audio.py OUT.wav

The source recording's audio is digital silence (no narration), so there is no voice to clean
or duck under. The score is written here (no samples, no third-party music): an energetic
128 BPM minor groove that drops to a pad during the result freeze. Every effect sits on a visual
event from timeline.sound_events(). Master: -14.5 LUFS behind a -3 dB limiter ceiling so the
delivered AAC decodes under -1 dBTP.
"""
import sys
from pathlib import Path

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy import signal

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "NPC_STUDIO" / "SOUND_ENGINE"))
import sound_engine as se  # noqa: E402

from timeline import Timeline  # noqa: E402

SR = se.SR
BPM = 128
BEAT = 60 / BPM
NOTE = lambda m: 440.0 * 2 ** ((m - 69) / 12)  # noqa: E731
CHORDS = [(57, 60, 64), (53, 57, 60), (48, 52, 55), (55, 59, 62)]  # Am F C G


def tv(n):
    return np.arange(n) / SR


def soft(x, ms=4.0):
    """Short attack ramp: instant-onset transients make the AAC encoder ring past full scale."""
    n = min(len(x), int(SR * ms / 1000))
    x = x.copy()
    ramp = np.sin(np.linspace(0, np.pi / 2, n)) ** 2
    x[:n] *= ramp[:, None] if x.ndim == 2 else ramp
    return x


def place(buf, at, x, gain_db=0.0):
    if x.ndim == 1:
        x = se.pan(x, 0)
    i = se.secs(at)
    if i < 0:
        x, i = x[-i:], 0
    j = min(len(buf), i + len(x))
    if i < len(buf):
        buf[i:j] += x[: j - i] * 10 ** (gain_db / 20)


def score(dur, start, freeze, outro):
    n = se.secs(dur)
    out = np.zeros((n, 2))
    bar = BEAT * 4
    t, ci = start, 0
    while t < dur:  # pads, one chord per bar
        ch = CHORDS[ci % 4]
        d = bar
        tt = tv(se.secs(d + 0.3))
        seg = sum(signal.sawtooth(2 * np.pi * NOTE(m) * f * tt) for m in ch for f in (0.997, 1.003)) / 6
        seg = se.lowpass(seg, 1600, 2) * np.minimum(1, tt / 0.08) * np.minimum(1, (tt[-1] - tt) / 0.3)
        place(out, t, se.pan(seg * 0.12, 0))
        t += d
        ci += 1
    steps = np.arange(start, freeze, BEAT / 4)
    for k, bt in enumerate(steps):
        st = k % 16
        ch = CHORDS[int((bt - start) // bar) % 4]
        if st % 4 == 0:  # four-on-the-floor kick
            place(out, bt, soft(se.sub_impact(0.22, 110, 45, 0.32)), -1)
        if st in (4, 12):  # clap
            cl = se.bandpass(se.noise(0.12), 900, 4000, 2) * np.exp(-tv(se.secs(0.12)) * 30)
            place(out, bt, soft(se.verb(se.pan(cl * 0.35, 0), se.IR_ROOM, 0.25)))
        if st % 2 == 1:  # hats
            hh = se.highpass(se.noise(0.04), 7500) * np.exp(-tv(se.secs(0.04)) * 110)
            place(out, bt, soft(se.pan(hh * 0.16, 0.35 if st % 4 == 1 else -0.35), 2.0))
        if st % 2 == 0:  # rolling bass
            f = NOTE(ch[0] - 24 + (12 if st % 8 == 6 else 0))
            tt = tv(se.secs(BEAT / 2))
            b = np.tanh(2.2 * np.sin(2 * np.pi * f * tt)) * np.exp(-tt * 7) * 0.24
            place(out, bt, soft(se.pan(se.lowpass(b, 900, 2), 0)))
        m = ch[(st // 2) % 3] + 12 + (12 if st % 8 == 7 else 0)  # pluck arp
        tt = tv(se.secs(0.18))
        pl = (np.sin(2 * np.pi * NOTE(m) * tt) + 0.25 * np.sin(4 * np.pi * NOTE(m) * tt)) * np.exp(-tt * 20)
        place(out, bt, soft(se.pan(pl * 0.045, np.sin(k * 0.6) * 0.6)))
    out = se.verb(out, se.IR_ROOM, 0.15)
    g = np.interp(tv(n), [0, start - 0.05, start + 0.15, freeze - 0.05, freeze + 0.3, outro, dur],
                  [0.0, 0.0, 1.0, 1.0, 0.55, 0.55, 0.0])
    return out * g[:, None]


def click():
    t = tv(se.secs(0.06))
    x = se.bandpass(se.noise(0.06), 1800, 6000, 2) * np.exp(-t * 160) * 0.7
    x += np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 120) * 0.25
    return soft(se.pan(se.lowpass(x, 7000, 2), 0))


def pop():
    t = tv(se.secs(0.12))
    f = 900 + 700 * np.exp(-t * 40)
    return soft(se.verb(se.pan(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 32) * 0.35, 0), se.IR_ROOM, 0.2))


def chime():
    out = np.zeros((se.secs(1.4), 2))
    for k, m in enumerate((76, 80, 83, 88)):
        t = tv(se.secs(1.0))
        x = (np.sin(2 * np.pi * NOTE(m) * t) + 0.2 * np.sin(4 * np.pi * NOTE(m) * t)) * np.exp(-t * 5) * 0.22
        i = se.secs(k * 0.06)
        out[i:i + len(x)] += se.pan(x, (k - 1.5) * 0.3)
    return soft(se.verb(out, se.IR_HALL, 0.3))


def alert():
    t = tv(se.secs(0.5))
    x = (np.sign(np.sin(2 * np.pi * 220 * t)) * 0.3 + np.sin(2 * np.pi * 110 * t)) * np.exp(-t * 6) * 0.3
    return soft(se.verb(se.pan(se.lowpass(x, 2500, 2), 0), se.IR_ROOM, 0.25))


def build(out_path):
    tl = Timeline()
    dur = tl.duration + 0.5
    mus = score(dur, tl.video_start, tl.freeze_start, tl.outro_start)
    sfx = se.Track(dur)
    for kind, t in tl.sound_events():
        if kind == "hook_hit":
            sfx.add(t, soft(se.sub_impact(1.0, 95, 30, 2.2)), -2)
            sfx.add(t, soft(se.glitch(0.25, 30, 1)), -12)
            sfx.add(t, soft(se.electric(0.45, 5)), -16)
        elif kind == "hook_hit2":
            sfx.add(t, soft(se.sub_impact(0.6, 120, 50, 1.2)), -7)
            sfx.add(t, soft(se.glitch(0.18, 20, 2)), -14)
        elif kind == "hook_riser":
            sfx.add(t, soft(se.riser(0.5, 300, 3500)), -12)
        elif kind == "whoosh":
            sfx.add(t, soft(se.whoosh(0.4, 400, 6000, 0.8, -0.8)), -9)
        elif kind == "chapter":
            sfx.add(t - 0.05, soft(se.glitch(0.15, 12, int(t))), -19)
        elif kind.startswith("cut_"):
            name = kind[4:]
            if name.startswith("whip"):
                sfx.add(t - 0.16, soft(se.whoosh(0.34, 500, 7000, -0.8, 0.8)), -10)
            elif name == "zoom_punch":
                sfx.add(t - 0.1, soft(se.whoosh(0.25, 300, 5000)), -12)
                sfx.add(t, soft(se.sub_impact(0.3, 90, 45, 0.6)), -12)
            elif name == "glitch":
                sfx.add(t - 0.08, soft(se.glitch(0.25, 34, 7)), -12)
            elif name == "impact":
                sfx.add(t - 0.4, soft(se.riser(0.4, 400, 4000)), -14)
                sfx.add(t, soft(se.sub_impact(0.9)), -4)
            else:  # flash
                sfx.add(t - 0.05, soft(se.whoosh(0.18, 1500, 8000)), -18)
        elif kind == "tap":
            sfx.add(t, click(), -10)
        elif kind == "highlight":
            sfx.add(t, pop(), -18)
        elif kind == "success":
            sfx.add(t + 0.1, chime(), -9)
        elif kind == "alert":
            sfx.add(t, alert(), -11)
            sfx.add(t, soft(se.glitch(0.22, 26, 9)), -14)
        elif kind == "speed":
            sfx.add(t, soft(se.whoosh(0.2, 1500, 8000, -0.3, 0.3)), -22)
        elif kind == "lower_third":
            sfx.add(t, soft(se.glitch(0.2, 16, 5)), -20)
        elif kind == "freeze":
            sfx.add(t, soft(se.sub_impact(0.4, 80, 40, 1.4)), -11)
        elif kind == "outro":
            sfx.add(t - 0.15, soft(se.whoosh(0.35)), -11)
        elif kind == "outro_hit":
            sfx.add(t, soft(se.sub_impact(0.7)), -6)
            sfx.add(t, soft(se.glitch(0.2, 20, 11)), -15)
    mix = mus + sfx.buf[: len(mus)]
    # Band-limit before the limiter: bright transients (hats, glitch grains) make the AAC
    # encoder overshoot by several dB even when the PCM peak is low.
    mix = np.stack([signal.sosfiltfilt(signal.butter(6, 16000, fs=SR, output="sos"), mix[:, c]) for c in range(2)], axis=1)
    meter = pyln.Meter(SR)
    for _ in range(2):
        mix = mix * 10 ** ((-14.5 - meter.integrated_loudness(mix)) / 20)
        mix = se.true_peak_limit(mix, -3.0)
    mix = mix[: int(round(tl.duration * SR))]
    sf.write(out_path, mix.astype(np.float32), SR, subtype="FLOAT")
    print(f"wrote {out_path}  {len(mix) / SR:.2f}s  LUFS {meter.integrated_loudness(mix):.2f}  "
          f"peak {20 * np.log10(np.abs(mix).max()):.2f} dBFS  events {len(tl.sound_events())}")


if __name__ == "__main__":
    build(sys.argv[1])
