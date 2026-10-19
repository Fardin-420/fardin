"""NPC sound engine — original, code-synthesized cinematic sound design.

    python sound_engine.py ../PROJECTS/NPC_NO_EDITOR_JUST_CODE

Reads source/timeline.json and places every sound on a named visual cue, so no
sound exists without a matching event on screen. If NPC_VOICE_V1 narration is
present it is mixed in and the bed and effects duck under it.

Outputs (in the project's audio/):
  stems/{bed,sfx}.wav     intermediate stems
  mix.wav                 48 kHz stereo master
  envelope.json           per-frame energy/spectrum used by audio-reactive visuals
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

SR = 48000
RNG = np.random.default_rng(4207)  # fixed seed: the soundtrack is reproducible


# ───────────────────────── primitives ─────────────────────────

def secs(n: float) -> int:
    return int(round(n * SR))


def tvec(dur: float) -> np.ndarray:
    return np.arange(secs(dur)) / SR


def noise(dur: float) -> np.ndarray:
    return RNG.standard_normal(secs(dur))


def env_ad(n: int, attack: float, decay: float, curve: float = 4.0) -> np.ndarray:
    a = secs(attack)
    e = np.ones(n)
    if a > 0:
        e[:a] = np.linspace(0, 1, a) ** 2
    rest = n - a
    if rest > 0:
        e[a:] = np.exp(-curve * np.arange(rest) / max(secs(decay), 1))
    return e


def bandpass(x, lo, hi, order=4):
    sos = signal.butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def lowpass(x, f, order=4):
    return signal.sosfilt(signal.butter(order, f, btype="low", fs=SR, output="sos"), x)


def highpass(x, f, order=4):
    return signal.sosfilt(signal.butter(order, f, btype="high", fs=SR, output="sos"), x)


def sweep_filter(x, f0, f1, q=6.0, blocks=96):
    """Time-varying resonant bandpass, processed in short crossfaded blocks."""
    n = len(x)
    out = np.zeros(n)
    edges = np.linspace(0, n, blocks + 1).astype(int)
    for i in range(blocks):
        a, b = edges[i], edges[i + 1]
        f = f0 * (f1 / f0) ** (i / max(blocks - 1, 1))
        bw = f / q
        lo, hi = max(20, f - bw), min(SR / 2 - 100, f + bw)
        pad = min(a, 2048)
        seg = bandpass(x[a - pad:b], lo, hi, 2)[pad:]
        out[a:b] = seg
    return out


def pan(mono: np.ndarray, p) -> np.ndarray:
    """Equal-power pan; p in [-1, 1] scalar or per-sample array."""
    p = np.broadcast_to(np.asarray(p, float), mono.shape)
    th = (p + 1) * np.pi / 4
    return np.stack([mono * np.cos(th), mono * np.sin(th)], axis=1)


def reverb_ir(dur=2.6, damp=3.2, seed=1):
    r = np.random.default_rng(seed)
    n = secs(dur)
    t = np.arange(n) / SR
    ir = r.standard_normal((n, 2)) * np.exp(-damp * t)[:, None]
    # darker tail: progressively lowpass the decay
    ir[:, 0] = lowpass(ir[:, 0], 6000, 2)
    ir[:, 1] = lowpass(ir[:, 1], 6000, 2)
    ir[0] = [1.0, 1.0]
    return ir / np.abs(ir).sum(axis=0).max() * 8


IR_HALL = reverb_ir(3.2, 2.2, 11)
IR_ROOM = reverb_ir(0.9, 6.0, 12)


def verb(st: np.ndarray, ir: np.ndarray, wet: float) -> np.ndarray:
    w = np.stack([signal.fftconvolve(st[:, c], ir[:, c])[: len(st)] for c in range(2)], axis=1)
    return st * (1 - wet) + w * wet


class Track:
    def __init__(self, dur: float):
        self.buf = np.zeros((secs(dur), 2))

    def add(self, at: float, st: np.ndarray, gain_db: float = 0.0):
        if st.ndim == 1:
            st = pan(st, 0.0)
        i = secs(at)
        if i < 0:
            st, i = st[-i:], 0
        j = min(len(self.buf), i + len(st))
        if j > i:
            self.buf[i:j] += st[: j - i] * 10 ** (gain_db / 20)


# ───────────────────────── sound designs ─────────────────────────

def sub_impact(size=1.0, f_hi=85, f_lo=32, dur=2.8):
    """Deep cinematic hit: pitch-dropping sub, body thump, transient crack, hall tail."""
    t = tvec(dur)
    f = f_lo + (f_hi - f_lo) * np.exp(-t * 7)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ad(len(t), 0.002, dur * 0.55, 3.0)
    body = lowpass(noise(dur), 400) * env_ad(len(t), 0.001, 0.25, 5) * 0.9
    crack = highpass(noise(dur), 2500) * env_ad(len(t), 0.0005, 0.05, 6) * 0.5
    mono = np.tanh((sub * 1.2 + body + crack) * 1.4) * size
    return verb(pan(mono, 0), IR_HALL, 0.22)


def riser(dur=1.6, f0=180, f1=3200):
    """Tension riser ending exactly at the next hit: filtered noise + rising detuned tones."""
    t = tvec(dur)
    shape = (t / dur) ** 2.2
    nz = sweep_filter(noise(dur), f0 * 2, f1 * 2, q=4)
    tones = sum(np.sin(2 * np.pi * np.cumsum(f0 * (f1 / f0) ** (t / dur) * d / 4) / SR)
                for d in (1.0, 1.007, 0.993))
    mono = (nz * 0.8 + tones * 0.12) * shape
    mono[-secs(0.02):] *= np.linspace(1, 0, secs(0.02))
    width = np.sin(t * 9) * 0.5 * shape
    return verb(pan(mono, width), IR_ROOM, 0.25)


def reverse_swell(dur=0.9):
    tail = sub_impact(0.6, 120, 50, dur)[::-1]
    return tail * np.linspace(0, 1, len(tail))[:, None] ** 2


def whoosh(dur=0.55, f0=300, f1=4500, p0=-0.9, p1=0.9):
    """Directional air movement for camera whips; pan follows the motion."""
    n = secs(dur)
    mono = sweep_filter(noise(dur), f0, f1, q=3) * np.sin(np.linspace(0, np.pi, n)) ** 1.5
    return verb(pan(mono * 1.6, np.linspace(p0, p1, n)), IR_ROOM, 0.2)


def glitch(dur=0.35, density=40, seed=0):
    """Digital fragmentation: stuttered bit-crushed grains."""
    r = np.random.default_rng(seed)
    out = np.zeros((secs(dur), 2))
    for _ in range(density):
        g = r.uniform(0.004, 0.03)
        at = r.uniform(0, dur - g)
        t = tvec(g)
        kind = r.integers(3)
        if kind == 0:
            x = np.sign(np.sin(2 * np.pi * r.uniform(200, 3000) * t))
        elif kind == 1:
            x = r.standard_normal(len(t))
        else:
            x = np.sin(2 * np.pi * r.uniform(800, 9000) * t)
        steps = r.integers(2, 6)
        x = np.round(x * steps) / steps  # crush
        x *= np.hanning(len(x)) ** 0.3 * r.uniform(0.2, 0.8)
        i = secs(at)
        out[i:i + len(x)] += pan(x, r.uniform(-0.8, 0.8))
    return out


def metallic(dur=1.8, base=420.0, seed=3, bright=1.0):
    """Chrome resonance: inharmonic struck-plate partials."""
    r = np.random.default_rng(seed)
    t = tvec(dur)
    ratios = [1.0, 1.593, 2.135, 2.653, 3.156, 4.06, 5.2, 6.8]
    mono = np.zeros(len(t))
    for k, ra in enumerate(ratios):
        f = base * ra * r.uniform(0.995, 1.005)
        mono += np.sin(2 * np.pi * f * t + r.uniform(0, 6)) * np.exp(-t * (1.6 + k * 0.9 / bright)) / (1 + k * 0.5)
    mono *= env_ad(len(t), 0.001, dur, 1.0) * 0.5
    return verb(pan(mono, r.uniform(-0.3, 0.3)), IR_HALL, 0.35)


def metal_slide(dur=1.0, f0=900, f1=300):
    """Metallic movement: a scraped resonant band gliding between frequencies."""
    nz = noise(dur) * (1 + 0.6 * np.sin(tvec(dur) * 2 * np.pi * 37))
    mono = sweep_filter(nz, f0, f1, q=18) * np.sin(np.linspace(0, np.pi, secs(dur))) * 2.2
    return verb(pan(mono, np.linspace(0.6, -0.6, len(mono))), IR_HALL, 0.3)


def electric(dur=0.8, seed=5, rate=180):
    """Procedural electrical arcing: sparse resonant crackles over a mains buzz."""
    r = np.random.default_rng(seed)
    n = secs(dur)
    imp = (r.random(n) < rate / SR) * r.standard_normal(n) * 6
    crack = bandpass(imp, 1800, 9000, 2) + bandpass(imp, 300, 900, 2) * 0.4
    t = tvec(dur)
    buzz = sum(np.sign(np.sin(2 * np.pi * 50 * h * t)) / h for h in (1, 3, 5)) * 0.05
    mono = (crack + lowpass(buzz, 1200)) * np.sin(np.linspace(0, np.pi, n)) ** 0.5
    return pan(mono, np.sin(t * 13) * 0.5)


def shatter(dur=1.3, seed=8, count=90):
    """Particle disintegration: a cloud of tiny metallic grains spreading in stereo."""
    r = np.random.default_rng(seed)
    out = np.zeros((secs(dur), 2))
    for i in range(count):
        at = (r.random() ** 2) * (dur - 0.2)
        g = 0.08
        t = tvec(g)
        f = r.uniform(2500, 11000)
        x = np.sin(2 * np.pi * f * t) * np.exp(-t * r.uniform(40, 120)) * r.uniform(0.05, 0.25)
        j = secs(at)
        out[j:j + len(x)] += pan(x, r.uniform(-1, 1))
    return verb(out, IR_HALL, 0.3)


def shockwave(dur=1.2):
    """Low air-pressure sweep for the shockwave distortion."""
    t = tvec(dur)
    mono = sweep_filter(noise(dur), 2000, 90, q=2) * np.exp(-t * 3) * 1.8
    mono += np.sin(2 * np.pi * np.cumsum(70 * np.exp(-t * 2) + 25) / SR) * np.exp(-t * 2.5) * 0.7
    return verb(pan(mono, 0), IR_HALL, 0.3)


def typing(dur=1.0, seed=9, rate=14):
    """Terminal ticks for the code world."""
    r = np.random.default_rng(seed)
    out = np.zeros((secs(dur), 2))
    t = 0.0
    while t < dur - 0.03:
        t += r.exponential(1 / rate)
        if t >= dur - 0.03:
            break
        x = bandpass(r.standard_normal(secs(0.012)), 2500, 7000, 2) * np.exp(-np.arange(secs(0.012)) / 90)
        j = secs(t)
        out[j:j + len(x)] += pan(x * r.uniform(0.2, 0.5), r.uniform(-0.4, 0.4))
    return out


def blip(f=1800, dur=0.12):
    t = tvec(dur)
    return pan(np.sin(2 * np.pi * f * t) * np.exp(-t * 40) * 0.4, 0)


def drone(dur: float):
    """Atmospheric bed: detuned low saws, slow filter breath, air layer."""
    t = tvec(dur)
    saw = lambda f: signal.sawtooth(2 * np.pi * f * t)
    low = sum(saw(f) for f in (36.71, 36.9, 55.0, 55.3, 73.4)) / 5
    lfo = 0.5 + 0.5 * np.sin(2 * np.pi * t / 9.0)
    low = lowpass(low, 240, 2) * (0.6 + 0.4 * lfo)
    air = bandpass(noise(dur), 2500, 9000, 2) * 0.05 * (0.5 + 0.5 * np.sin(2 * np.pi * t / 5.3))
    left = low + air
    right = np.roll(low, secs(0.013)) + bandpass(noise(dur), 2500, 9000, 2) * 0.05
    return np.stack([left, right], axis=1) * 0.5


def pulse_bed(dur: float, bpm=96):
    """Low-frequency tension pulse (heartbeat sub) for the build sections."""
    out = np.zeros((secs(dur), 2))
    beat = 60 / bpm
    t = 0.0
    while t < dur:
        for off, g in ((0, 1.0), (0.18, 0.55)):
            x = sub_impact(0.25 * g, 70, 40, 0.6)
            j = secs(t + off)
            k = min(len(out), j + len(x))
            if j < len(out):
                out[j:k] += x[: k - j]
        t += beat
    return out


# ───────────────────────── score ─────────────────────────

def automation(n: int, points: list[tuple[float, float]]) -> np.ndarray:
    xs = np.array([p[0] for p in points]) * SR
    ys = np.array([p[1] for p in points])
    return np.interp(np.arange(n), xs, ys)


def build(project: Path) -> None:
    tl = json.loads((project / "source" / "timeline.json").read_text())
    c = tl["cues"]
    D = tl["duration"]
    audio = project / "audio"
    (audio / "stems").mkdir(parents=True, exist_ok=True)

    bed, sfx = Track(D), Track(D)

    # Bed: drone across the piece with dynamic automation, pulse during builds.
    dr = drone(D)
    gain = automation(len(dr), [
        (0, 0.0), (0.3, 0.35), (c["pulse"] - 0.1, 0.5), (c["pulse"] + 0.3, 0.9),
        (c["collapse"] - 0.05, 0.9), (c["collapse"] + 0.4, 0.15), (c["explode"] - 0.02, 0.0),
        (c["explode"] + 0.05, 1.0), (D - 2.0, 0.8), (D, 0.0),
    ])
    bed.add(0, dr * gain[:, None], -6)
    s03 = next(s for s in tl["scenes"] if s["id"] == "S03")
    pb = pulse_bed(s03["end"] - s03["start"] + 0.4)
    pb *= automation(len(pb), [(0, 0.2), (1.5, 0.7), (len(pb) / SR - 0.4, 1.0), (len(pb) / SR, 0)])[:, None]
    bed.add(s03["start"], pb, -4)
    s05 = next(s for s in tl["scenes"] if s["id"] == "S05")
    pb2 = pulse_bed(c["collapse"] - s05["start"], bpm=120)
    bed.add(s05["start"], pb2, -3)

    # S01 — impossible opening
    sfx.add(c["cursor_on"], blip(2200), -10)
    sfx.add(c["cursor_on"] + 0.53, blip(2200), -14)
    sfx.add(c["pulse"] - 0.9, reverse_swell(0.9), -4)
    sfx.add(c["pulse"], electric(0.5, seed=21), -6)
    sfx.add(c["title_slam"], sub_impact(1.0), 0)
    sfx.add(c["title_slam"], metallic(2.2, 310, seed=4), -8)

    # S02 — break the rules (one bespoke destruction sound per name)
    sfx.add(c["s02_whip"] - 0.25, whoosh(0.6, 200, 5000, -1, 1), -2)
    sfx.add(c["premiere_in"] - 0.05, metal_slide(0.7, 1400, 500), -10)
    sfx.add(c["premiere_break"], whoosh(0.45, 400, 6000, 0.2, 1), -4)        # velocity displacement
    sfx.add(c["premiere_break"], sub_impact(0.45, 110, 45, 1.2), -6)
    sfx.add(c["capcut_in"] - 0.05, blip(1300, 0.15), -12)
    sfx.add(c["capcut_break"], glitch(0.45, 60, seed=2), -3)                  # digital fragmentation
    sfx.add(c["ae_in"] - 0.05, metal_slide(0.8, 600, 1500), -10)
    sfx.add(c["ae_break"] - 0.6, riser(0.6, 300, 2500), -8)
    sfx.add(c["ae_break"], shatter(1.4, seed=7), -2)                          # particle disintegration
    sfx.add(c["ae_break"], shockwave(1.3), -3)

    # S03 — every frame is code
    sfx.add(c["s03_in"] - 0.3, whoosh(0.6, 2500, 200, 1, -1), -4)
    sfx.add(c["s03_in"], typing(c["code_resolve"] - c["s03_in"], rate=18), -16)
    for k, key in enumerate(("transition_word", "effect_word")):
        sfx.add(c[key], metallic(1.2, 520 + k * 140, seed=30 + k, bright=1.5), -12)
        sfx.add(c[key] - 0.05, glitch(0.18, 18, seed=40 + k), -10)
    sfx.add(c["frame_hit"] - 1.0, riser(1.0, 120, 1800), -6)
    sfx.add(c["frame_hit"], sub_impact(0.9, 70, 28, 3.0), -1)
    sfx.add(c["code_word"], electric(1.0, seed=33, rate=260), -10)
    sfx.add(c["code_resolve"], metallic(2.5, 260, seed=34), -8)

    # S04 — voice reveal (kept sparse: the voice is the subject)
    sfx.add(c["s04_in"] - 0.2, reverse_swell(0.6), -10)
    sfx.add(c["mine"] - 0.02, sub_impact(0.3, 60, 35, 2.0), -8)
    sfx.add(c["symbol_morph"], metal_slide(1.0, 400, 1200), -10)

    # S05 — no timeline
    sfx.add(c["layers"] - 0.2, whoosh(0.5, 300, 4000, -0.8, 0.8), -6)
    sfx.add(c["layers"], glitch(0.6, 50, seed=50), -9)
    sfx.add(c["collapse"], whoosh(0.5, 5000, 150, 0.8, -0.8), -3)
    sfx.add(c["collapse"], metal_slide(0.7, 1800, 200), -6)
    sfx.add(c["explode"] - 1.25, riser(1.25, 90, 4000), -2)
    sfx.add(c["explode"], sub_impact(1.2, 95, 26, 3.5), 2)
    sfx.add(c["explode"], shockwave(1.5), 0)
    sfx.add(c["explode"], shatter(1.6, seed=55, count=160), -5)

    # S06 — identity
    sfx.add(c["s06_in"], shatter(1.4, seed=60, count=120)[::-1], -9)        # particles converging
    sfx.add(c["emblem_lock"], metallic(3.0, 196, seed=61), -3)
    sfx.add(c["emblem_lock"], sub_impact(0.7, 70, 30, 2.5), -5)
    sfx.add(c["tagline"], metal_slide(1.2, 300, 900), -14)
    sfx.add(c["final_hit"], sub_impact(0.8, 60, 28, 3.0), -3)
    sfx.add(c["final_hit"], metallic(3.0, 147, seed=62, bright=0.7), -9)

    # Narration (NPC_VOICE_V1) and ducking.
    narr_path = audio / "narration" / "narration.wav"
    voice = np.zeros_like(bed.buf)
    if tl["voiced"] and narr_path.exists():
        v, sr = sf.read(narr_path)
        assert sr == SR, f"narration must be {SR} Hz"
        v = v if v.ndim == 1 else v.mean(axis=1)
        n = min(len(v), len(voice))
        voice[:n] = pan(v[:n] * 0.9, 0)
    # Duck from the line spans (works before and after the real voice exists),
    # with fast attack and slow release so the bed breathes back between lines.
    duck = np.zeros(len(bed.buf))
    for ln in tl["lines"]:
        duck[secs(ln["start"] - 0.08):secs(ln["end"] + 0.12)] = 1.0
    duck = signal.lfilter([1 - 0.9995], [1, -0.9995], duck)  # ~40 ms smoothing
    duck = np.clip(duck * 1.4, 0, 1)
    bed_gain = 10 ** (-9 * duck / 20)
    sfx_gain = 10 ** (-5 * duck / 20)

    bed_st = bed.buf * bed_gain[:, None]
    sfx_st = sfx.buf * sfx_gain[:, None]
    mix = bed_st + sfx_st + voice

    # Master: gentle glue compression via soft clip, then loudness to -14 LUFS.
    import pyloudnorm as pyln
    meter = pyln.Meter(SR)
    lufs = meter.integrated_loudness(mix)
    mix *= 10 ** ((-14 - lufs) / 20)
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)
    # Ceiling at -1.5 dBFS sample peak leaves headroom for AAC inter-sample overshoot.
    peak = np.abs(mix).max()
    if peak > 0.84:
        mix *= 0.84 / peak
    fade = secs(0.6)
    mix[-fade:] *= np.linspace(1, 0, fade)[:, None]

    sf.write(audio / "stems" / "bed.wav", bed_st, SR, subtype="FLOAT")
    sf.write(audio / "stems" / "sfx.wav", sfx_st, SR, subtype="FLOAT")
    sf.write(audio / "mix.wav", mix, SR, subtype="PCM_24")
    print(f"mix: {len(mix) / SR:.2f}s  LUFS(pre-limit)={lufs:.1f}  final={meter.integrated_loudness(mix):.1f}"
          f"  peak={20 * np.log10(np.abs(mix).max()):.1f} dBFS  voiced={tl['voiced']}")

    write_envelope(tl, mix, voice, audio / "envelope.json")


def write_envelope(tl: dict, mix: np.ndarray, voice: np.ndarray, out: Path) -> None:
    """Per-video-frame features for audio-reactive visuals.

    `voice` drives the Scene 04 waveform. Before NPC_VOICE_V1 exists it is all
    zeros and the visuals fall back to the soundtrack (`mix`)."""
    fps = tl["fps"]
    hop = SR // fps
    n_frames = tl["durationInFrames"]
    bands = 24
    edges = np.geomspace(80, 8000, bands + 1)
    freqs = np.fft.rfftfreq(2048, 1 / SR)
    win = np.hanning(2048)

    def features(x):
        mono = x.mean(axis=1)
        rms, spec = [], []
        for f in range(n_frames):
            c = f * hop + hop // 2
            seg = mono[max(0, c - 1024): c + 1024]
            seg = np.pad(seg, (0, 2048 - len(seg)))
            rms.append(float(np.sqrt(np.mean(seg ** 2))))
            mag = np.abs(np.fft.rfft(seg * win))
            spec.append([float(mag[(freqs >= edges[b]) & (freqs < edges[b + 1])].mean()) for b in range(bands)])
        rms = np.array(rms)
        spec = np.array(spec)
        rms = rms / (rms.max() + 1e-9)
        spec = np.log1p(spec * 50)
        spec = spec / (spec.max() + 1e-9)
        return np.round(rms, 3).tolist(), np.round(spec, 3).tolist()

    mix_rms, mix_spec = features(mix)
    has_voice = bool(np.abs(voice).max() > 0)
    v_rms, v_spec = features(voice) if has_voice else (None, None)
    out.write_text(json.dumps({
        "fps": fps, "frames": n_frames, "bands": bands, "has_voice": has_voice,
        "mix_rms": mix_rms, "mix_spec": mix_spec, "voice_rms": v_rms, "voice_spec": v_spec,
    }, separators=(",", ":")))
    print(f"envelope: {n_frames} frames, voice={'yes' if has_voice else 'no (soundtrack fallback)'}")


if __name__ == "__main__":
    build(Path(sys.argv[1]).resolve())
