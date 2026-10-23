"""Audio: click-free dialogue edit, cleanup chain, original music bed, cue-locked SFX, ducking, -14 LUFS master."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

from .common import FPS, SR, STUDIO, run

sys.path.insert(0, str(STUDIO / "SOUND_ENGINE"))
import sound_engine as se  # noqa: E402  (NPC original synthesized sound library)

TARGET_LUFS, TARGET_TP = -14.0, -1.5


def read_span(src: str, s: float, e: float) -> np.ndarray:
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{s:.4f}", "-t", f"{e - s + 0.2:.4f}", "-i", src, "-vn",
           "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


def assemble_dialogue(tl: dict) -> np.ndarray:
    segs = tl["segments"]
    span_s = min(s["src_s"] for s in segs)
    span = read_span(tl["source"]["path"], span_s, max(s["src_e"] for s in segs))
    total = int(round(tl["frames"] / FPS * SR))
    out = np.zeros((total, 2), np.float32)
    fade = int(0.006 * SR)
    ramp = (0.5 - 0.5 * np.cos(np.linspace(0, np.pi, fade)))[:, None].astype(np.float32)
    for k, seg in enumerate(segs):
        o0, o1 = min(total, int(round(seg["out_s"] * SR))), min(total, int(round(seg["out_e"] * SR)))
        a = int(round((seg["src_s"] - span_s) * SR))
        chunk = span[a:a + (o1 - o0)]
        if len(chunk) < o1 - o0:
            chunk = np.pad(chunk, ((0, o1 - o0 - len(chunk)), (0, 0)))
        chunk = chunk.copy()
        joined_prev = k and abs(segs[k - 1]["src_e"] - seg["src_s"]) < 1e-3
        joined_next = k + 1 < len(segs) and abs(segs[k + 1]["src_s"] - seg["src_e"]) < 1e-3
        if not joined_prev and len(chunk) > 2 * fade:
            chunk[:fade] *= ramp
        if not joined_next and len(chunk) > 2 * fade:
            chunk[-fade:] *= ramp[::-1]
        out[o0:o1] = chunk
    return out


def clean_dialogue(raw: Path, out: Path) -> None:
    chain = ("highpass=f=75,afftdn=nr=6:nf=-50:tn=1,equalizer=f=3200:t=q:w=1.2:g=2,"
             "acompressor=threshold=-22dB:ratio=2.5:attack=8:release=140:makeup=2,"
             "loudnorm=I=-16:TP=-2:LRA=9")
    run(["ffmpeg", "-y", "-v", "error", "-i", raw, "-af", chain, "-ar", SR, "-ac", 2, "-c:a", "pcm_f32le", out])


# ───────────────────────── original music bed ─────────────────────────

def _note(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def music_bed(mood: str, dur: float, seed: int = 7) -> np.ndarray:
    if mood == "none":
        return np.zeros((int(dur * SR), 2), np.float32)
    r = np.random.default_rng(seed)
    bpm = {"pulse": 100, "drive": 128, "playful": 112, "cinematic": 72, "light": 92, "pad": 80}.get(mood, 90)
    beat = 60 / bpm
    bar = beat * 4
    prog = [[57, 60, 64, 69], [53, 57, 60, 65], [48, 55, 60, 64], [55, 59, 62, 67]]  # Am F C G
    if mood in ("playful", "light"):
        prog = [[48, 55, 60, 64], [55, 59, 62, 67], [57, 60, 64, 69], [53, 57, 60, 65]]
    n = int(dur * SR) + SR
    t = np.arange(n) / SR
    pad = np.zeros(n)
    for b in range(int(dur / bar) + 2):
        chord = prog[b % 4]
        a, e = int(b * bar * SR), min(n, int((b + 1) * bar * SR + 0.3 * SR))
        if a >= n:
            break
        tt = t[a:e] - t[a]
        env = np.minimum(1, tt / 0.6) * np.minimum(1, (e / SR - t[a:e]) / 0.35)
        for m in chord:
            for det in (0.997, 1.003):
                f = _note(m) * det
                tone = sum(np.sin(2 * np.pi * f * h * tt + r.uniform(0, 6)) / h ** 1.6 for h in range(1, 5))
                pad[a:e] += tone * env * 0.06
    pad = se.lowpass(pad, 1700 if mood != "cinematic" else 1100)
    mix = pad
    if mood in ("cinematic", "pad"):
        mix = mix + np.sin(2 * np.pi * _note(33) * t) * 0.10 * (0.6 + 0.4 * np.sin(t * 0.4))
    if mood in ("pulse", "drive", "light"):
        kick = np.zeros(n)
        k_len = int(0.28 * SR)
        kt = np.arange(k_len) / SR
        k = np.sin(2 * np.pi * np.cumsum(45 + 80 * np.exp(-kt * 30)) / SR) * np.exp(-kt * 9)
        step = beat if mood != "light" else beat * 2
        for i in range(int(dur / step) + 1):
            a = int(i * step * SR)
            kick[a:a + k_len] += k[: max(0, min(k_len, n - a))] * (0.55 if mood == "drive" else 0.4)
        mix = mix + kick
        if mood != "light":
            hat = np.zeros(n)
            h_len = int(0.03 * SR)
            hn = se.highpass(r.standard_normal(h_len), 7000) * np.exp(-np.arange(h_len) / SR * 120)
            for i in range(int(dur / beat) + 1):
                a = int((i + 0.5) * beat * SR)
                if a + h_len < n:
                    hat[a:a + h_len] += hn * 0.12
            mix = mix + hat
    if mood in ("playful", "light"):
        arp = np.zeros(n)
        p_len = int(0.25 * SR)
        pt = np.arange(p_len) / SR
        step = beat / 2 if mood == "playful" else beat
        for i in range(int(dur / step) + 1):
            chord = prog[int(i * step / bar) % 4]
            m = chord[i % len(chord)] + 12
            a = int(i * step * SR)
            if a + p_len < n:
                arp[a:a + p_len] += np.sin(2 * np.pi * _note(m) * pt) * np.exp(-pt * 14) * 0.12
        mix = mix + arp
    st = se.pan(mix[: int(dur * SR)], 0) if hasattr(se, "pan") else np.stack([mix, mix], 1)
    st = np.asarray(st, np.float32)
    fade_in, fade_out = int(0.4 * SR), int(0.8 * SR)
    st[:fade_in] *= np.linspace(0, 1, fade_in)[:, None]
    st[-fade_out:] *= np.linspace(1, 0, fade_out)[:, None]
    rms = np.sqrt((st ** 2).mean() + 1e-12)
    return st / rms * 10 ** (-20 / 20)


def duck_gain(voice: np.ndarray, depth_db=-9.0) -> np.ndarray:
    hop = int(0.02 * SR)
    m = np.abs(voice).mean(1)
    frames = len(m) // hop + 1
    env = np.array([m[i * hop:(i + 1) * hop].mean() if i * hop < len(m) else 0 for i in range(frames)])
    active = (20 * np.log10(env + 1e-9) > -42).astype(float)
    g = np.ones(frames)
    a_c, r_c = np.exp(-1 / 3), np.exp(-1 / 20)  # ~60 ms attack, ~400 ms release at 20 ms hop
    target = 10 ** (depth_db / 20)
    cur = 1.0
    for i in range(frames):
        tgt = target if active[i] else 1.0
        c = a_c if tgt < cur else r_c
        cur = c * cur + (1 - c) * tgt
        g[i] = cur
    return np.repeat(g, hop)[: len(voice)][:, None]


def sfx_sound(kind: str) -> np.ndarray:
    if kind == "whoosh":
        x = se.whoosh(0.5)
    elif kind == "impact":
        x = se.sub_impact(0.55, 95, 42, 1.1)
    elif kind == "glitch":
        x = se.glitch(0.22, 24, seed=5)
    elif kind == "pop":
        n = int(0.09 * SR)
        tt = np.arange(n) / SR
        mono = np.sin(2 * np.pi * np.cumsum(950 - 3500 * tt) / SR) * np.exp(-tt * 45)
        x = np.stack([mono, mono], 1)
    else:
        x = np.zeros((1, 2))
    x = np.asarray(x, np.float32)
    pk = np.abs(x).max() + 1e-9
    return x / pk


def loudnorm_2pass(inp: Path, out: Path) -> dict:
    p = run(["ffmpeg", "-v", "info", "-i", inp, "-af",
             f"loudnorm=I={TARGET_LUFS}:TP={TARGET_TP}:LRA=11:print_format=json", "-f", "null", "-"])
    txt = p.stderr[p.stderr.rfind("{"): p.stderr.rfind("}") + 1]
    m = json.loads(txt)
    af = (f"loudnorm=I={TARGET_LUFS}:TP={TARGET_TP}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,"
          f"alimiter=limit={10 ** ((TARGET_TP - 0.3) / 20):.4f}:attack=2:release=50:level=disabled")
    run(["ffmpeg", "-y", "-v", "error", "-i", inp, "-af", af, "-ar", SR, "-ac", 2, "-c:a", "pcm_s24le", out])
    return m


def build_audio(tl: dict, work: Path, music_override_db: float | None = None) -> Path:
    cid = tl["clip_id"]
    raw = work / f"{cid}_dialogue_raw.wav"
    voice_p = work / f"{cid}_dialogue.wav"
    sf.write(raw, assemble_dialogue(tl), SR, subtype="FLOAT")
    clean_dialogue(raw, voice_p)
    voice, _ = sf.read(voice_p, dtype="float32")
    n = int(round(tl["frames"] / FPS * SR))
    voice = voice[:n] if len(voice) >= n else np.pad(voice, ((0, n - len(voice)), (0, 0)))
    mix = voice.copy()
    lvl = music_override_db if music_override_db is not None else tl["music"]["level_db"]
    if tl["music"]["mood"] != "none" and lvl > -60:
        bed = music_bed(tl["music"]["mood"], n / SR, seed=int(tl["clip_id"][-2:]))[:n]
        bed = np.pad(bed, ((0, n - len(bed)), (0, 0)))
        bed *= 10 ** ((lvl + 20) / 20) * duck_gain(voice)
        mix += bed
    for ev in tl["sfx"]:
        x = sfx_sound(ev["type"]) * 10 ** (ev["gain_db"] / 20)
        a = int(max(0, ev["t"]) * SR)
        b = min(n, a + len(x))
        if b > a:
            mix[a:b] += x[: b - a]
    pre = work / f"{cid}_premaster.wav"
    sf.write(pre, mix, SR, subtype="FLOAT")
    master = work / f"{cid}_master.wav"
    loudnorm_2pass(pre, master)
    return master
