"""Soundtrack: original synthesized score + SFX locked to timeline events, mastered.

    python audio.py OUT.wav

The source recording's audio track is digital silence, so there is no narration to enhance or
duck under. The score is written here (no samples, no third-party music), every effect sits on a
visual event from timeline.sound_events(), and the master is normalised to -14.5 LUFS behind a
-3 dB limiter ceiling, so the delivered AAC decodes under -1 dBTP (measured: -1.4 dBTP).
"""
import sys
from pathlib import Path

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy import signal

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "NPC_STUDIO" / "SOUND_ENGINE"))
import sound_engine as se  # noqa: E402  (NPC studio sound library: impacts, whooshes, glitches, limiter)

from timeline import Timeline  # noqa: E402

SR = se.SR
BPM = 112
BEAT = 60 / BPM
NOTE = lambda m: 440.0 * 2 ** ((m - 69) / 12)  # noqa: E731
# A minor: Am - F - C - G, two bars each
CHORDS = [(57, 60, 64), (53, 57, 60), (48, 52, 55), (55, 59, 62)]
RNG = np.random.default_rng(112)


def tv(n):
    return np.arange(n) / SR


def pad_voice(f, dur):
    t = tv(se.secs(dur))
    x = sum(signal.sawtooth(2 * np.pi * f * d * t) for d in (0.996, 1.0, 1.004)) / 3
    return x


def score(dur, music_start, freeze, outro):
    n = se.secs(dur)
    out = np.zeros((n, 2))
    bar = BEAT * 4
    # pads
    t = music_start - bar * 0.5
    ci = 0
    while t < dur:
        ch = CHORDS[ci % 4]
        d = bar * 2
        seg = sum(pad_voice(NOTE(m), d + 0.6) for m in ch) / 3
        seg = se.lowpass(seg, 1400, 2)
        e = np.minimum(1, tv(len(seg)) / 0.5) * np.minimum(1, (len(seg) / SR - tv(len(seg))) / 0.6)
        st = se.pan(seg * e * 0.16, 0)
        st[:, 1] = np.roll(st[:, 1], se.secs(0.011))
        i = se.secs(max(t, 0))
        j = min(n, i + len(st))
        out[i:j] += st[: j - i]
        t += d
        ci += 1
    # rhythm section between music_start and freeze, then pad only
    beats = np.arange(music_start, freeze, BEAT / 4)
    for k, bt in enumerate(beats):
        step = k % 16
        ch = CHORDS[int((bt - music_start + bar * 0.5) // (bar * 2)) % 4]
        if step in (0, 8):  # soft kick
            x = se.sub_impact(0.18, 95, 45, 0.35)
            _place(out, bt, x, -2)
        if step % 4 == 2:  # off-beat hat
            h = se.highpass(se.noise(0.05), 7000) * np.exp(-tv(se.secs(0.05)) * 90)
            _place(out, bt, soft(se.pan(h * 0.18, 0.3 if step % 8 == 2 else -0.3), 2.0))
        if step % 2 == 0:  # bass pulse
            f = NOTE(ch[0] - 12)
            tt = tv(se.secs(BEAT / 2))
            b = np.sin(2 * np.pi * f * tt) * np.exp(-tt * 6) * 0.28
            _place(out, bt, se.pan(b, 0))
        if bt > music_start + bar * 2:  # pluck arpeggio after the first two bars
            m = ch[(step // 2) % 3] + 12 + (12 if step % 8 == 6 else 0)
            tt = tv(se.secs(0.22))
            pl = (np.sin(2 * np.pi * NOTE(m) * tt) + 0.3 * np.sin(4 * np.pi * NOTE(m) * tt)) * np.exp(-tt * 18)
            _place(out, bt, se.pan(pl * 0.055, np.sin(k * 0.7) * 0.6))
    out = se.verb(out, se.IR_ROOM, 0.18)
    # master the score's own envelope: fade in after the intro hit, fade out across the outro
    g = np.interp(tv(n), [0, music_start - 0.3, music_start + 0.2, freeze, freeze + 0.6, outro + 1.0, dur],
                  [0.0, 0.0, 1.0, 1.0, 0.75, 0.75, 0.0])
    return out * g[:, None]


def _place(buf, at, x, gain_db=0.0):
    if x.ndim == 1:
        x = se.pan(x, 0)
    i = se.secs(at)
    j = min(len(buf), i + len(x))
    if 0 <= i < len(buf):
        buf[i:j] += x[: j - i] * 10 ** (gain_db / 20)


def soft(x, ms=4.0):
    """Short attack ramp: instant-onset transients make the AAC encoder ring past full scale."""
    n = min(len(x), int(SR * ms / 1000))
    x = x.copy()
    ramp = np.sin(np.linspace(0, np.pi / 2, n)) ** 2
    x[:n] *= ramp[:, None] if x.ndim == 2 else ramp
    return x


def click():
    t = tv(se.secs(0.06))
    x = se.bandpass(se.noise(0.06), 1800, 6000, 2) * np.exp(-t * 160) * 0.7
    x += np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 120) * 0.25
    return soft(se.pan(se.lowpass(x, 7000, 2), 0))


def pop():
    t = tv(se.secs(0.12))
    f = 900 + 700 * np.exp(-t * 40)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 32) * 0.35
    return soft(se.verb(se.pan(x, 0), se.IR_ROOM, 0.2))


def chime():
    out = np.zeros((se.secs(1.4), 2))
    for k, m in enumerate((76, 80, 83, 88)):
        t = tv(se.secs(1.0))
        x = (np.sin(2 * np.pi * NOTE(m) * t) + 0.2 * np.sin(4 * np.pi * NOTE(m) * t)) * np.exp(-t * 5) * 0.22
        i = se.secs(k * 0.07)
        out[i:i + len(x)] += se.pan(x, (k - 1.5) * 0.3)
    return se.verb(out, se.IR_HALL, 0.3)


def build(out_path):
    tl = Timeline()
    dur = tl.duration + 0.5
    mus = score(dur, tl.video_start, tl.freeze_start, tl.outro_start)
    sfx = se.Track(dur)
    for kind, t in tl.sound_events():
        if kind == "intro":
            sfx.add(t, se.riser(0.55, 200, 2800), -8)
        elif kind == "intro_hit":
            sfx.add(t, se.sub_impact(0.9), -3)
            sfx.add(t, se.glitch(0.3, 30, 1), -12)
        elif kind == "intro_out":
            sfx.add(t, se.whoosh(0.5), -9)
        elif kind == "chapter":
            sfx.add(t - 0.12, se.whoosh(0.45, 400, 5000, -0.6, 0.6), -13)
            sfx.add(t + 0.05, se.glitch(0.18, 14, int(t)), -20)
        elif kind == "cut":
            sfx.add(t - 0.1, se.whoosh(0.28, 600, 6000, 0.5, -0.5), -16)
        elif kind == "tap":
            sfx.add(t, click(), -10)
        elif kind == "highlight":
            sfx.add(t, pop(), -17)
        elif kind == "success":
            sfx.add(t, chime(), -11)
        elif kind == "speed":
            sfx.add(t, se.whoosh(0.22, 1200, 7000, -0.3, 0.3), -21)
        elif kind == "lower_third":
            sfx.add(t, se.glitch(0.22, 18, 5), -19)
            sfx.add(t + 0.02, soft(se.blip(1500, 0.1)), -18)
        elif kind == "freeze":
            sfx.add(t - 0.6, se.reverse_swell(0.6), -14)
            sfx.add(t, se.sub_impact(0.4, 80, 40, 1.6), -10)
        elif kind == "outro":
            sfx.add(t - 0.2, se.whoosh(0.5), -10)
        elif kind == "outro_hit":
            sfx.add(t, se.sub_impact(0.8), -4)
            sfx.add(t, se.metallic(1.6, 380, 4), -16)
    mix = mus * 0.9 + sfx.buf[: len(mus)]
    meter = pyln.Meter(SR)
    lufs = meter.integrated_loudness(mix)
    mix = mix * 10 ** ((-14.5 - lufs) / 20)
    mix = se.true_peak_limit(mix, -3.0)
    lufs2 = meter.integrated_loudness(mix)
    mix = mix * 10 ** ((-14.5 - lufs2) / 20)
    mix = se.true_peak_limit(mix, -3.0)  # headroom so the AAC decode stays under -1 dBTP
    mix = mix[: int(tl.duration * SR)]
    sf.write(out_path, mix.astype(np.float32), SR, subtype="FLOAT")
    print(f"wrote {out_path}  {len(mix) / SR:.2f}s  LUFS {meter.integrated_loudness(mix):.2f}  "
          f"sample peak {20 * np.log10(np.abs(mix).max()):.2f} dBFS  events {len(tl.sound_events())}")


if __name__ == "__main__":
    build(sys.argv[1])
