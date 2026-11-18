"""Narration (local Kokoro or edge-tts, with word timings), procedural SFX, tempo-locked score, mixing, loudness."""
import asyncio
import hashlib
import json
import os
import re
import subprocess
import numpy as np
from scipy import signal

SR = 48000
CA_BUNDLE = "/root/.ccr/ca-bundle.crt"


# ------------------------------------------------------------------ io
def decode(path, sr=SR):
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "s16le", "-ac", "1", "-ar", str(sr), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype=np.int16).astype(np.float32) / 32768.0


def write_wav(path, x, sr=SR):
    x = np.clip(x, -1, 1)
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    pcm = (x * 32767).astype(np.int16)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "s16le", "-ar", str(sr), "-ac", "2", "-i", "-", path],
                   input=pcm.tobytes(), check=True)


# ------------------------------------------------------------------ TTS
def _patch_certs():
    if os.path.exists(CA_BUNDLE):
        try:
            import certifi
            certifi.where = lambda: CA_BUNDLE
        except ImportError:
            pass


async def _tts(text, voice, rate, pitch, path):
    import edge_tts
    c = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, boundary="WordBoundary")
    words = []
    with open(path, "wb") as f:
        async for ch in c.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                words.append({"w": ch["text"], "t": ch["offset"] / 1e7, "d": ch["duration"] / 1e7})
    return words


# ------------------------------------------------------------------ Kokoro (local) TTS
KOKORO_SR = 24000
_KOKORO = None
_WHISPER = {"model": None, "failed": False}


def _kokoro():
    global _KOKORO
    if _KOKORO is None:
        from kokoro_onnx import Kokoro
        d = os.path.expanduser(os.environ.get("KOKORO_DIR", "~/kokoro"))
        onnx, voices = os.path.join(d, "kokoro-v1.0.onnx"), os.path.join(d, "voices-v1.0.bin")
        if not (os.path.exists(onnx) and os.path.exists(voices)):
            raise SystemExit(f"Kokoro model missing in {d}: download kokoro-v1.0.onnx and voices-v1.0.bin from "
                             "https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0")
        _KOKORO = Kokoro(onnx, voices)
    return _KOKORO


def _whisper():
    if _WHISPER["model"] is None and not _WHISPER["failed"]:
        try:
            from faster_whisper import WhisperModel
            _WHISPER["model"] = WhisperModel("base.en", device="cpu", compute_type="int8")
        except Exception as e:  # not installed or model download blocked
            print(f"[tts] faster-whisper unavailable ({type(e).__name__}); using heuristic word timings", flush=True)
            _WHISPER["failed"] = True
    return _WHISPER["model"]


def _script_words(text):
    return [w for w in text.split() if re.sub(r"[^A-Za-z0-9]", "", w)]


def _align_whisper(x, text):
    m = _whisper()
    if m is None:
        return None
    import tempfile, soundfile as sf
    with tempfile.NamedTemporaryFile(suffix=".wav") as f:
        sf.write(f.name, x, SR)
        segs, _ = m.transcribe(f.name, word_timestamps=True, language="en")
        rec = [w for s in segs for w in (s.words or [])]
    toks = _script_words(text)
    if not rec:
        return None
    # map recognised words onto script words in order (proportional when counts differ)
    out = []
    for i, tk in enumerate(toks):
        j = min(len(rec) - 1, int(round(i * (len(rec) - 1) / max(1, len(toks) - 1)))) if len(rec) != len(toks) else i
        out.append({"w": tk, "t": float(rec[j].start), "d": float(max(0.05, rec[j].end - rec[j].start))})
    for i in range(1, len(out)):  # monotonic
        out[i]["t"] = max(out[i]["t"], out[i - 1]["t"] + 0.03)
    return out


def _align_heuristic(x, text):
    """Spread script words over the voiced span weighted by letters (+1.5) with extra
    weight after punctuation, then snap phrase breaks onto real pauses in the audio."""
    toks = _script_words(text)
    if not toks:
        return []
    idx = np.where(np.abs(x) > 0.02)[0]
    v0, v1 = (idx[0] / SR, idx[-1] / SR) if len(idx) else (0.0, len(x) / SR)
    w, gaps = [], []
    for tk in toks:
        w.append(len(re.sub(r"[^A-Za-z0-9]", "", tk)) + 1.5)
        gaps.append(6.0 if tk[-1:] in ".!?" else 3.0 if tk[-1:] in ",;:" else 0.0)
    total = sum(w) + sum(gaps[:-1])
    pos, starts, ends = 0.0, [], []
    for i in range(len(toks)):
        starts.append(pos); pos += w[i]; ends.append(pos)
        if i < len(toks) - 1:
            pos += gaps[i]
    scale = (v1 - v0) / total
    st = [v0 + a * scale for a in starts]
    en = [v0 + b * scale for b in ends]
    # detect real pauses (10 ms frames, >=90 ms below threshold)
    hop = int(0.01 * SR)
    fr = np.sqrt(np.convolve(x ** 2, np.ones(hop) / hop, mode="same")[::hop])
    quiet = fr < 0.012
    pauses, k = [], 0
    while k < len(quiet):
        if quiet[k]:
            j = k
            while j < len(quiet) and quiet[j]:
                j += 1
            a, b = k * 0.01, j * 0.01
            if b - a >= 0.09 and a > v0 + 0.05 and b < v1 - 0.05:
                pauses.append((a, b))
            k = j
        else:
            k += 1
    # anchors: (model_time, real_time) pairs at punctuation breaks
    anchors = [(v0, v0)]
    used = set()
    for i in range(len(toks) - 1):
        if gaps[i] > 0 and pauses:
            mid_pred = (en[i] + st[i + 1]) / 2
            best = min(range(len(pauses)), key=lambda q: abs((pauses[q][0] + pauses[q][1]) / 2 - mid_pred))
            pa, pb = pauses[best]
            if best not in used and abs((pa + pb) / 2 - mid_pred) < 0.7 and pa > anchors[-1][1]:
                used.add(best)
                anchors.append((en[i], pa))
                anchors.append((st[i + 1], pb))
    anchors.append((v1, v1))
    mx = np.array([a[0] for a in anchors]); rx = np.array([a[1] for a in anchors])
    ok = np.concatenate([[True], np.diff(mx) > 1e-4])
    mx, rx = mx[ok], rx[ok]
    remap = lambda t: float(np.interp(t, mx, rx))
    return [{"w": tk, "t": remap(a), "d": max(0.05, remap(b) - remap(a))} for tk, a, b in zip(toks, st, en)]


def _tts_kokoro(text, voice, rate, cache_dir):
    key = hashlib.sha1(f"{voice}|{rate}|{text}".encode()).hexdigest()[:16]
    wav, js = os.path.join(cache_dir, key + ".wav"), os.path.join(cache_dir, key + ".json")
    if os.path.exists(wav) and os.path.exists(js):
        import soundfile as sf
        x, _ = sf.read(wav, dtype="float32")
        return x, json.load(open(js))
    k = _kokoro()
    y, sr = k.create(text, voice=voice.split(":", 1)[1], speed=float(rate), lang="en-us")
    x = signal.resample_poly(np.asarray(y, np.float32), SR, sr).astype(np.float32)
    idx = np.where(np.abs(x) > 0.01)[0]
    if len(idx):  # trim, keep 60 ms head and 100 ms tail
        x = x[max(0, idx[0] - int(0.06 * SR)): min(len(x), idx[-1] + int(0.1 * SR))]
    words = _align_whisper(x, text) or _align_heuristic(x, text)
    import soundfile as sf
    sf.write(wav, x, SR)
    json.dump(words, open(js, "w"))
    return x, words


def tts(text, cache_dir, voice="kokoro:am_fenrir", rate="1.04", pitch="0"):
    """Returns (samples at SR, words[{w,t,d}]) cached by content hash.
    'kokoro:<voice>' -> local Kokoro (rate = speed factor); anything else -> edge-tts."""
    os.makedirs(cache_dir, exist_ok=True)
    if voice.startswith("kokoro:"):
        return _tts_kokoro(text, voice, rate, cache_dir)
    key = hashlib.sha1(f"{voice}|{rate}|{pitch}|{text}".encode()).hexdigest()[:16]
    mp3, js = os.path.join(cache_dir, key + ".mp3"), os.path.join(cache_dir, key + ".json")
    if not (os.path.exists(mp3) and os.path.exists(js) and os.path.getsize(mp3) > 1000):
        _patch_certs()
        for attempt in range(4):
            try:
                words = asyncio.run(_tts(text, voice, rate, pitch, mp3))
                break
            except Exception as e:  # network hiccups
                if attempt == 3:
                    raise
                import time; time.sleep(2 + attempt * 3)
        json.dump(words, open(js, "w"))
    x = decode(mp3)
    words = json.load(open(js))
    env = np.abs(x)
    idx = np.where(env > 0.01)[0]
    if len(idx):
        x = x[: min(len(x), idx[-1] + int(0.08 * SR))]
    return x, words


# ------------------------------------------------------------------ synthesis helpers
def rng(seed):
    return np.random.default_rng(abs(hash(str(seed))) % (2 ** 32))


def env_ad(n, a=0.005, d=None, curve=4.0):
    t = np.arange(n) / SR
    att = np.clip(t / max(a, 1e-4), 0, 1)
    dec = np.exp(-t * curve / (d or (n / SR)))
    return att * dec


def bp(x, lo, hi, order=2):
    lo, hi = max(20, lo), min(SR / 2 - 100, hi)
    b, a = signal.butter(order, [lo, hi], btype="band", fs=SR)
    return signal.lfilter(b, a, x)


def lp(x, f, order=2):
    b, a = signal.butter(order, min(f, SR / 2 - 100), btype="low", fs=SR)
    return signal.lfilter(b, a, x)


def hp(x, f, order=2):
    b, a = signal.butter(order, f, btype="high", fs=SR)
    return signal.lfilter(b, a, x)


def norm(x, peak=0.9):
    m = np.max(np.abs(x)) + 1e-9
    return x / m * peak


def sweep_filter(noise, f0, f1, q=0.6, block=1024):
    """Band-pass with a moving centre frequency (log sweep)."""
    out = np.zeros_like(noise)
    n = len(noise)
    nb = max(1, n // block)
    zi = None
    for i in range(nb + 1):
        s, e = i * block, min(n, (i + 1) * block)
        if s >= e:
            break
        u = s / max(1, n - 1)
        fc = f0 * (f1 / f0) ** u
        lo, hi = fc * (1 - q / 2), fc * (1 + q / 2)
        b, a = signal.butter(2, [max(30, lo), min(SR / 2 - 200, hi)], btype="band", fs=SR)
        if zi is None or len(zi) != max(len(a), len(b)) - 1:
            zi = signal.lfilter_zi(b, a) * 0
        out[s:e], zi = signal.lfilter(b, a, noise[s:e], zi=zi)
    return out


# ------------------------------------------------------------------ SFX library
def sfx_whoosh(d=0.8, seed=0, up=True):
    n = int(d * SR)
    x = rng(("wh", seed)).standard_normal(n)
    x = sweep_filter(x, 300 if up else 3000, 3000 if up else 300, 0.9)
    e = np.sin(np.linspace(0, np.pi, n)) ** 2
    return norm(x * e, 0.8)


def sfx_pop(seed=0):
    n = int(0.16 * SR)
    t = np.arange(n) / SR
    f = 500 + 1300 * (t / t[-1]) ** 0.5
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ad(n, 0.002, 0.08, 3)
    click = rng(("pop", seed)).standard_normal(n) * env_ad(n, 0.0005, 0.01, 6) * 0.3
    return norm(x + hp(click, 2000), 0.75)


def sfx_impact(seed=0, d=1.6):
    n = int(d * SR)
    t = np.arange(n) / SR
    low = np.sin(2 * np.pi * (55 * t - 10 * t * t)) * np.exp(-t * 3)
    nz = lp(rng(("imp", seed)).standard_normal(n), 900) * np.exp(-t * 9)
    return norm(low + 0.6 * nz, 0.95)


def sfx_riser(d=2.0, seed=0):
    n = int(d * SR)
    t = np.arange(n) / SR
    nz = sweep_filter(rng(("ris", seed)).standard_normal(n), 200, 6000, 0.8)
    f = 200 * (8 ** (t / d))
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.25
    e = (t / d) ** 2
    return norm((nz + tone) * e, 0.8)


def sfx_shimmer(d=2.0, seed=0):
    n = int(d * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for i, f in enumerate((1318.5, 1760, 2217.5, 2637, 3520)):
        x += np.sin(2 * np.pi * f * t + i) * (0.5 + 0.5 * np.sin(2 * np.pi * (5 + i) * t)) / (i + 1)
    e = np.minimum(1, t / 0.3) * np.minimum(1, (d - t) / 0.6)
    return norm(x * e, 0.5)


def sfx_rumble(d=4.0, seed=0):
    n = int(d * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * 42 * t) * 0.6 + np.sin(2 * np.pi * 63 * t + 1) * 0.3
    x += lp(rng(("rum", seed)).standard_normal(n), 120) * 3
    e = np.minimum(1, t / (d * 0.6)) * np.minimum(1, (d - t) / 0.5)
    return norm(x * e, 0.8)


def sfx_heartbeat(d=4.0, bpm=96, seed=0):
    n = int(d * SR)
    x = np.zeros(n)
    beat = 60 / bpm
    k = 0
    while k * beat < d:
        for off, amp in ((0, 1.0), (0.18, 0.7)):
            s = int((k * beat + off) * SR)
            m = int(0.15 * SR)
            if s + m < n:
                tt = np.arange(m) / SR
                x[s:s + m] += np.sin(2 * np.pi * 50 * tt) * np.exp(-tt * 30) * amp
        k += 1
    return norm(lp(x, 200), 0.9)


def sfx_knap(seed=0):
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    r = rng(("kn", seed))
    click = hp(r.standard_normal(n), 2500) * np.exp(-t * 400)
    ring = (np.sin(2 * np.pi * (2400 + r.uniform(-300, 300)) * t) * 0.5 + np.sin(2 * np.pi * 3700 * t) * 0.3) * np.exp(-t * 35)
    return norm(click + ring * 0.6, 0.85)


def sfx_crack(seed=0):
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    r = rng(("cr", seed))
    crack = hp(r.standard_normal(n), 1200) * np.exp(-t * 60)
    thud = np.sin(2 * np.pi * 90 * t) * np.exp(-t * 18)
    splinter = bp(r.standard_normal(n), 1500, 5000) * np.exp(-((t - 0.05) ** 2) / 0.001) * 0.6
    return norm(crack + thud + splinter, 0.9)


def sfx_footstep(seed=0, soft=False):
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    r = rng(("fs", seed))
    x = lp(r.standard_normal(n), 700 if soft else 1200) * np.exp(-t * 45) + np.sin(2 * np.pi * 70 * t) * np.exp(-t * 40) * 0.5
    return norm(x, 0.6 if soft else 0.8)


def sfx_steps(d=2.0, rate=2.2, seed=0, soft=False):
    n = int(d * SR)
    x = np.zeros(n)
    k = 0
    r = rng(("steps", seed))
    while True:
        tt = k / rate + r.uniform(-0.02, 0.02)
        if tt >= d:
            break
        s = max(0, int(tt * SR))
        fs = sfx_footstep(seed * 100 + k, soft) * r.uniform(0.6, 1.0)
        e = min(n, s + len(fs))
        if e > s:
            x[s:e] += fs[: e - s]
        k += 1
    return x


def sfx_gallop(d=2.0, seed=0, n_animals=5):
    x = np.zeros(int(d * SR))
    for a in range(n_animals):
        x += sfx_steps(d, 7 + a * 0.7, seed + a * 13) * 0.4
    return norm(x, 0.8)


def sfx_hyena(seed=0, kind="whoop"):
    r = rng(("hy", seed))
    if kind == "whoop":
        d = 1.1
        n = int(d * SR)
        t = np.arange(n) / SR
        f = 350 + 750 * (t / d) ** 0.8 + 18 * np.sin(2 * np.pi * 6 * t)
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.3 * np.sin(4 * np.pi * np.cumsum(f) / SR)
        e = np.minimum(1, t / 0.08) * np.minimum(1, (d - t) / 0.3)
        return norm(lp(x * e, 3000), 0.7)
    # giggle
    notes = 9
    out = []
    for i in range(notes):
        d = 0.09 + r.uniform(0, 0.03)
        n = int(d * SR)
        t = np.arange(n) / SR
        f0 = 780 + r.uniform(-60, 80) - i * 10
        f = f0 + 160 * np.sin(np.pi * t / d)
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.4 * hp(r.standard_normal(n), 1500) * 0.3
        out.append(x * np.sin(np.pi * t / d) ** 1.5)
        out.append(np.zeros(int(0.03 * SR)))
    return norm(lp(np.concatenate(out), 4000), 0.7)


def sfx_growl(d=1.5, seed=0):
    n = int(d * SR)
    t = np.arange(n) / SR
    r = rng(("gr", seed))
    f = 85 + 20 * np.sin(2 * np.pi * 0.7 * t)
    saw = signal.sawtooth(2 * np.pi * np.cumsum(f) / SR)
    am = 0.6 + 0.4 * np.abs(np.sin(2 * np.pi * 11 * t + r.uniform(0, 3)))
    x = lp(saw * am + lp(r.standard_normal(n), 400) * 0.5, 900)
    e = np.minimum(1, t / 0.2) * np.minimum(1, (d - t) / 0.4)
    return norm(x * e, 0.8)


def sfx_snort(seed=0):
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    x = bp(rng(("sn", seed)).standard_normal(n), 400, 2500) * np.exp(-t * 14)
    return norm(x, 0.6)


def sfx_spear(seed=0):
    return sfx_whoosh(0.4, seed, up=False) * 0.8


def sfx_thud(seed=0):
    n = int(0.3 * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * 80 * t) * np.exp(-t * 20) + lp(rng(("th", seed)).standard_normal(n), 600) * np.exp(-t * 30) * 0.6
    return norm(x, 0.85)


def sfx_ui(seed=0):
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * 880 * t) * np.exp(-t * 18) * 0.5 + np.sin(2 * np.pi * 1320 * t) * np.exp(-t * 25) * 0.3
    return norm(x + sfx_whoosh(0.25, seed) * 0.3, 0.5)


def sfx_stinger(seed=0):
    d = 2.5
    n = int(d * SR)
    t = np.arange(n) / SR
    low = np.sin(2 * np.pi * 55 * t) * np.exp(-t * 1.5)
    ch = sum(np.sin(2 * np.pi * f * t) for f in (220, 277.2, 329.6, 440)) * np.exp(-t * 1.2) * 0.25
    return norm(low + ch + sfx_shimmer(d, seed) * 0.3, 0.8)


def sfx_flash(seed=0):
    return norm(sfx_impact(seed, 2.0) + np.pad(sfx_shimmer(1.5, seed), (0, int(0.5 * SR))) * 0.5, 0.95)


def sfx_laugh_fardin(seed=0):
    return sfx_pop(seed) * 0.3


def sfx_buzz(seed=0):
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    x = signal.square(2 * np.pi * 180 * t) * (np.sin(2 * np.pi * 8 * t) > 0) * 0.3
    return norm(lp(x, 1500) * np.minimum(1, (0.6 - t) / 0.05), 0.4)


def sfx_fire_throw(seed=0):
    return norm(sfx_whoosh(0.7, seed, up=False) + bp(rng(("ft", seed)).standard_normal(int(0.7 * SR)), 200, 1200) * 0.3, 0.8)


SFX = {
    "whoosh": lambda s: sfx_whoosh(0.8, s), "whoosh_down": lambda s: sfx_whoosh(0.8, s, False), "pop": sfx_pop,
    "impact": sfx_impact, "riser": lambda s: sfx_riser(2.0, s), "riser_long": lambda s: sfx_riser(3.5, s),
    "shimmer": lambda s: sfx_shimmer(2.5, s), "rumble": lambda s: sfx_rumble(4.0, s), "heartbeat": lambda s: sfx_heartbeat(5.0, 100, s),
    "knap": sfx_knap, "crack": sfx_crack, "footstep": sfx_footstep, "steps": lambda s: sfx_steps(2.5, 2.2, s, True),
    "run_steps": lambda s: sfx_steps(2.0, 5.0, s), "gallop": lambda s: sfx_gallop(2.5, s), "hyena": lambda s: sfx_hyena(s, "whoop"),
    "hyena_giggle": lambda s: sfx_hyena(s, "giggle"), "growl": lambda s: sfx_growl(1.6, s), "snort": sfx_snort, "spear": sfx_spear,
    "thud": sfx_thud, "ui": sfx_ui, "stinger": sfx_stinger, "flash": sfx_flash, "buzz": sfx_buzz, "fire_throw": sfx_fire_throw,
}


# ------------------------------------------------------------------ ambience beds
def amb_wind(n, seed=0):
    t = np.arange(n) / SR
    x = lp(rng(("wind", seed)).standard_normal(n), 500) * 3
    lfo = 0.55 + 0.45 * np.sin(2 * np.pi * 0.07 * t + 1) * np.sin(2 * np.pi * 0.13 * t)
    return x * lfo * 0.25


def amb_birds(n, seed=0):
    x = np.zeros(n)
    r = rng(("birds", seed))
    pos = 0
    while True:
        pos += int(r.uniform(0.6, 2.4) * SR)
        if pos >= n:
            break
        for k in range(r.integers(2, 6)):
            d = r.uniform(0.05, 0.14)
            m = int(d * SR)
            tt = np.arange(m) / SR
            f0 = r.uniform(2500, 4500)
            f = f0 + r.uniform(-1500, 1500) * tt / d
            ch = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tt / d) ** 2
            s = pos + int(k * 0.11 * SR)
            if s + m < n:
                x[s:s + m] += ch * r.uniform(0.2, 0.5)
    return x * 0.25


def amb_crickets(n, seed=0):
    t = np.arange(n) / SR
    x = np.zeros(n)
    for i, f in enumerate((4400, 4950, 5300)):
        gate = (np.sin(2 * np.pi * (28 + i * 3) * t) > 0.3) * (np.sin(2 * np.pi * (0.9 + i * .2) * t + i) > -0.2)
        x += np.sin(2 * np.pi * f * t) * gate * 0.12
    return lp(x, 7000) * 0.5


def amb_fire(n, seed=0):
    r = rng(("fire", seed))
    base = lp(r.standard_normal(n), 300) * 1.5
    crack = np.zeros(n)
    k = 0
    while True:
        k += int(r.exponential(0.12) * SR) + 200
        if k >= n - 2000:
            break
        m = int(r.uniform(0.003, 0.02) * SR)
        crack[k:k + m] += hp(r.standard_normal(m), 1500) * np.exp(-np.arange(m) / (m / 4)) * r.uniform(0.1, 0.8)
    return (base * 0.25 + crack * 0.6) * 0.5


def amb_crowd(n, seed=0):
    r = rng(("crowd", seed))
    x = np.zeros(n)
    t = np.arange(n) / SR
    for v in range(5):
        f = r.uniform(300, 900)
        voice = bp(r.standard_normal(n), f * 0.7, f * 1.6)
        rate = r.uniform(3, 6)
        am = np.clip(np.sin(2 * np.pi * rate * t + r.uniform(0, 6)) + 0.2 * np.sin(2 * np.pi * 0.3 * t + v), 0, 1)
        talk = (np.sin(2 * np.pi * r.uniform(0.08, 0.2) * t + v) > -0.1)
        x += voice * am * talk
    return norm(x, 0.2)


def amb_cave(n, seed=0):
    t = np.arange(n) / SR
    x = lp(rng(("cave", seed)).standard_normal(n), 150) * 2 + np.sin(2 * np.pi * 55 * t) * 0.05
    drips = np.zeros(n)
    r = rng(("drip", seed))
    k = 0
    while True:
        k += int(r.uniform(1.5, 4.0) * SR)
        if k >= n - 6000:
            break
        m = 5000
        tt = np.arange(m) / SR
        drips[k:k + m] += np.sin(2 * np.pi * (1800 - 900 * tt / tt[-1]) * tt) * np.exp(-tt * 40) * 0.3
    return x * 0.2 + drips


def amb_city(n, seed=0):
    t = np.arange(n) / SR
    x = lp(rng(("city", seed)).standard_normal(n), 250) * 1.5
    return x * (0.7 + 0.3 * np.sin(2 * np.pi * 0.05 * t)) * 0.3


def amb_tunnel(n, seed=0):
    t = np.arange(n) / SR
    x = sweep_filter(rng(("tun", seed)).standard_normal(n), 200, 2000, 1.2) * 1.5
    x += np.sin(2 * np.pi * 60 * t) * 0.3 + np.sin(2 * np.pi * 90.5 * t) * 0.2
    return x * 0.5


AMB = {"wind": amb_wind, "birds": amb_birds, "crickets": amb_crickets, "fire": amb_fire, "crowd": amb_crowd,
       "cave": amb_cave, "city": amb_city, "tunnel": amb_tunnel}


# ------------------------------------------------------------------ music pad
MOODS = {
    "wonder": [(57, [0, 4, 7, 11]), (53, [0, 4, 7, 14]), (60, [0, 4, 7, 11]), (55, [0, 5, 7, 14])],
    "calm": [(50, [0, 7, 12, 16]), (55, [0, 4, 7, 12]), (52, [0, 3, 7, 10]), (53, [0, 4, 7, 12])],
    "tense": [(45, [0, 1, 7, 12]), (45, [0, 3, 6, 12]), (44, [0, 1, 7, 13]), (46, [0, 3, 7, 12])],
    "dark": [(40, [0, 7, 12, 15]), (41, [0, 7, 12, 15]), (38, [0, 7, 12, 15]), (39, [0, 7, 12, 15])],
    "hopeful": [(48, [0, 4, 7, 12]), (55, [0, 4, 7, 11]), (57, [0, 3, 7, 12]), (53, [0, 4, 7, 12])],
    "playful": [(60, [0, 4, 7, 12]), (65, [0, 4, 7, 12]), (67, [0, 4, 7, 10]), (60, [0, 4, 7, 12])],
}


def music_pad(n, mood, t0=0.0, seed=0):
    """Slow evolving pad; chord changes every 4s, phase-continuous with absolute time t0."""
    prog = MOODS.get(mood, MOODS["calm"])
    t = np.arange(n) / SR + t0
    x = np.zeros(n)
    seg = 4.0
    idx = (t // seg).astype(int) % len(prog)
    for ci, (root, ivs) in enumerate(prog):
        mask = idx == ci
        if not mask.any():
            continue
        tt = t[mask]
        ph = (tt % seg) / seg
        e = np.minimum(1, ph / 0.25) * np.minimum(1, (1 - ph) / 0.25) * 0.85 + 0.15
        acc = np.zeros(mask.sum())
        for j, iv in enumerate(ivs):
            f = 440 * 2 ** ((root + iv - 69) / 12)
            for det in (-0.12, 0.12):
                ff = f * 2 ** (det / 12)
                acc += np.sin(2 * np.pi * ff * tt + j) * 0.6 + 0.25 * np.sin(4 * np.pi * ff * tt + j)
        x[mask] = acc * e
    x = lp(x, 1800)
    if mood in ("tense", "dark"):
        x += np.sin(2 * np.pi * 36.7 * t) * 0.6 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.25 * t))
    if mood in ("playful", "wonder", "hopeful"):
        # soft plucks on 8ths
        pl = np.zeros(n)
        step = 0.5
        k0 = int(np.ceil(t0 / step))
        while True:
            tk = k0 * step
            s = int((tk - t0) * SR)
            if s >= n:
                break
            root, ivs = prog[int(tk // seg) % len(prog)]
            note = root + 12 + ivs[(k0 * 3) % len(ivs)]
            f = 440 * 2 ** ((note - 69) / 12)
            m = min(int(0.6 * SR), n - s)
            tt = np.arange(m) / SR
            pl[s:s + m] += np.sin(2 * np.pi * f * tt) * np.exp(-tt * 6) * 0.5
            k0 += 1
        x += pl
    return x * 0.08


# ------------------------------------------------------------------ cinematic score
BPM = 100
BEAT = 60.0 / BPM
BAR = 4 * BEAT
STEP = BEAT / 4  # 16th note
_ONESHOT = {}


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def _cached(key, fn):
    if key not in _ONESHOT:
        _ONESHOT[key] = fn().astype(np.float32)
    return _ONESHOT[key]


def _kick():
    n = int(0.45 * SR); t = np.arange(n) / SR
    f = 45 + 80 * np.exp(-t * 32)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7)
    x += hp(rng("kick").standard_normal(n), 2500) * np.exp(-t * 600) * 0.4
    return x * 0.95


def _tom(p):
    n = int(0.8 * SR); t = np.arange(n) / SR
    f = p * (1 + 0.6 * np.exp(-t * 18))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5.5)
    x += bp(rng(("tom", p)).standard_normal(n), 120, 900) * np.exp(-t * 16) * 0.9
    return x * 0.8


def _shaker(k):
    n = int(0.09 * SR); t = np.arange(n) / SR
    x = hp(rng(("sh", k)).standard_normal(n), 6500) * np.minimum(1, t / 0.006) * np.exp(-t * 55)
    return x * 0.35


def _bass(m, dur):
    n = int((dur + 0.15) * SR); t = np.arange(n) / SR
    f = mtof(m)
    x = signal.sawtooth(2 * np.pi * f * t) * 0.5 + np.sin(2 * np.pi * f * t) + 0.5 * np.sin(np.pi * f * t)
    e = np.minimum(1, t / 0.004) * np.exp(-t * 3.2) * np.clip((dur + 0.12 - t) / 0.12, 0, 1)
    return lp(x * e, 750) * 0.75


def _pluck(m):
    n = int(0.6 * SR); t = np.arange(n) / SR
    f = mtof(m)
    x = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t)
    return x * np.minimum(1, t / 0.003) * np.exp(-t * 8) * 0.45


def _strings(notes, dur, cut):
    n = int((dur + 0.7) * SR); t = np.arange(n) / SR
    x = np.zeros(n)
    for m in notes:
        for cents in (-8, 0, 8):
            f = mtof(m) * 2 ** (cents / 1200)
            ph = rng(("st", m, cents)).uniform(0, 6.28)
            for h in range(1, 8):
                x += np.sin(2 * np.pi * f * h * t + ph * h) / h
    vib = 1 + 0.06 * np.sin(2 * np.pi * 0.25 * t)
    e = np.minimum(1, t / 0.35) * np.clip((dur + 0.6 - t) / 0.6, 0, 1)
    return lp(x * e * vib, cut) * 0.06


def _swell(dur, seed, strong=False):
    n = int(dur * SR); t = np.arange(n) / SR
    x = sweep_filter(rng(("sw", seed)).standard_normal(n), 250, 6000 if strong else 3500, 0.9)
    tone = np.sin(2 * np.pi * np.cumsum(110 * 2 ** (t / dur * 2)) / SR) * 0.3
    return (x + tone) * (t / dur) ** 2.5 * (0.9 if strong else 0.45)


MOOD_LAYERS = {
    # kick steps, taiko steps, shaker (steps, gain), bass (steps, octave), arp (steps), strings gain, cutoff, swell
    "playful": dict(kick=[0, 4, 8, 12], taiko=[], shaker=(list(range(16)), 1.0), bass=([0, 2, 4, 6, 8, 10, 12, 14], -24),
                    arp=list(range(16)), strings=0.45, cut=1500, swell=None),
    "wonder": dict(kick=[0, 8], taiko=[], shaker=([2, 6, 10, 14], 0.6), bass=([0, 8], -24), arp=[0, 2, 4, 6, 8, 10, 12, 14],
                   strings=1.0, cut=1500, swell="soft"),
    "hopeful": dict(kick=[0, 8], taiko=[], shaker=([2, 6, 10, 14], 0.6), bass=([0, 6, 8, 14], -24), arp=[0, 2, 4, 6, 8, 10, 12, 14],
                    strings=1.0, cut=1700, swell="soft"),
    "calm": dict(kick=[], taiko=[], shaker=([], 0), bass=([0, 4, 8, 12], -24), arp=[0, 3, 6, 8, 11, 14], strings=0.9,
                 cut=1300, swell=None, arp_gain=0.55),
    "tense": dict(kick=[], taiko=[0, 3, 6, 10, 12, 14], shaker=(list(range(16)), 0.6), bass=([0, 2, 4, 6, 8, 10, 12, 14], -24),
                  arp=[], strings=0.9, cut=1400, swell="noise"),
    "dark": dict(kick=[], taiko=[0, 7, 10], shaker=([], 0), bass=([0, 2, 3, 6, 8, 10, 11, 14], -24), arp=[], strings=1.1,
                 cut=900, swell="strong"),
}
TOM_PITCH = [95, 120, 80, 140, 100, 110]


def music_score(n, mood, t0=0.0):
    """Tempo-locked score (100 BPM, 4/4, one chord per bar) for absolute time [t0, t0+n/SR).
    Deterministic in absolute time, so same-mood neighbours join seamlessly."""
    L = MOOD_LAYERS.get(mood, MOOD_LAYERS["calm"])
    prog = MOODS.get(mood, MOODS["calm"])
    pre = 1.5
    ta = t0 - pre
    N = n + int(pre * SR)
    tb = ta + N / SR
    drums = np.zeros(N + SR); bass = np.zeros(N + SR); arp = np.zeros(N + SR); strings = np.zeros(N + 2 * SR); fx = np.zeros(N + SR)

    def put(buf, clip, te, g=1.0):
        st = int(round((te - ta) * SR))
        if st >= len(buf) or st + len(clip) <= 0 or g == 0:
            return
        c = clip
        if st < 0:
            c = c[-st:]; st = 0
        e = min(len(buf), st + len(c))
        buf[st:e] += c[: e - st] * g

    b0, b1 = int(np.floor(ta / BAR)) - 1, int(np.floor(tb / BAR)) + 1
    for b in range(b0, b1 + 1):
        if b < 0:
            continue
        root, ivs = prog[b % len(prog)]
        tb0 = b * BAR
        chord = [root + iv for iv in ivs]
        for st in L["kick"]:
            put(drums, _cached("kick", _kick), tb0 + st * STEP, 0.9)
        for i, st in enumerate(L["taiko"]):
            if mood == "dark" and st == 7 and b % 2:
                continue
            p = TOM_PITCH[(i + b) % len(TOM_PITCH)]
            put(drums, _cached(("tom", p), lambda p=p: _tom(p)), tb0 + st * STEP, 0.9 if st == 0 else 0.6)
        steps, sg = L["shaker"]
        for st in steps:
            acc = 1.0 if st % 4 == 2 else 0.55
            put(drums, _cached(("sh", st % 4), lambda k=st % 4: _shaker(k)), tb0 + st * STEP, sg * acc)
        bsteps, boct = L["bass"]
        for j, st in enumerate(bsteps):
            nxt = bsteps[j + 1] if j + 1 < len(bsteps) else 16
            dur = (nxt - st) * STEP * 0.9
            m = root + boct + 12 + (12 if mood == "playful" and j % 2 else 0)
            put(bass, _cached(("bass", m, round(dur, 3)), lambda m=m, d=dur: _bass(m, d)), tb0 + st * STEP, 1.0)
        tones = sorted(chord)
        for j, st in enumerate(L["arp"]):
            seq = tones + [tones[1] + 12, tones[2] + 12] if len(tones) >= 3 else tones
            m = seq[(j + b) % len(seq)] + 12
            put(arp, _cached(("pl", m), lambda m=m: _pluck(m)), tb0 + st * STEP, L.get("arp_gain", 0.8) * (1.0 if st % 4 == 0 else 0.7))
        if L["strings"]:
            notes = [root - 12 + iv for iv in ivs] if mood == "dark" else [root + iv for iv in ivs]
            key = ("str", tuple(notes), L["cut"])
            put(strings, _cached(key, lambda nt=notes, c=L["cut"]: _strings(nt, BAR, c)), tb0, L["strings"])
        if L["swell"] and b % 4 == 3:
            sw = _cached(("swell", L["swell"]), lambda k=L["swell"]: _swell(BAR, k, k == "strong"))
            g = {"soft": 0.35, "noise": 0.6, "strong": 0.9}[L["swell"]]
            put(fx, sw, tb0, g)
    mix = drums[:N] * 0.9 + bass[:N] * 0.75 + arp[:N] * 0.55 + strings[:N] * 1.0 + fx[:N] * 0.5
    mix = np.tanh(mix * 1.3) / 1.3
    return mix[int(pre * SR): int(pre * SR) + n].astype(np.float32)


# ------------------------------------------------------------------ loudness
def loudness(path):
    """Integrated LUFS and true peak (dBTP) via ffmpeg ebur128."""
    out = subprocess.run(["ffmpeg", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    I = re.findall(r"I:\s+(-?[\d.]+) LUFS", out)
    P = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", out)
    return (float(I[-1]) if I else None), (float(P[-1]) if P else None)


def loudnorm_wav(path, I=-15.0, TP=-1.6, LRA=11):
    """Two-pass EBU R128 normalisation in place (linear when possible)."""
    first = subprocess.run(["ffmpeg", "-nostats", "-i", path, "-af", f"loudnorm=I={I}:TP={TP}:LRA={LRA}:print_format=json",
                            "-f", "null", "-"], capture_output=True, text=True).stderr
    js = json.loads(first[first.rindex("{"): first.rindex("}") + 1])
    tmp = path + ".ln.wav"
    af = (f"loudnorm=I={I}:TP={TP}:LRA={LRA}:measured_I={js['input_i']}:measured_TP={js['input_tp']}:"
          f"measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", path, "-af", af, "-ar", str(SR), "-c:a", "pcm_s16le", tmp], check=True)
    os.replace(tmp, path)


# ------------------------------------------------------------------ mixer
def place(track, clip, t, gain=1.0):
    s = int(round(t * SR))
    if s >= len(track) or len(clip) == 0:
        return
    if s < 0:
        clip = clip[-s:]
        s = 0
    e = min(len(track), s + len(clip))
    track[s:e] += clip[: e - s] * gain


def envelope(x, win=0.25):
    k = int(win * SR)
    e = np.sqrt(np.convolve(x ** 2, np.ones(k) / k, mode="same"))
    return e


def smooth_gain(g, att=0.08, rel=0.5):
    """One-pole attack/release smoothing of a gain curve (decimated for speed)."""
    dec = 480
    gg = g[::dec]
    out = np.empty_like(gg)
    a_att, a_rel = np.exp(-dec / (att * SR)), np.exp(-dec / (rel * SR))
    v = gg[0]
    for i, x in enumerate(gg):
        a = a_att if x < v else a_rel
        v = a * v + (1 - a) * x
        out[i] = v
    return np.interp(np.arange(len(g)), np.arange(len(out)) * dec, out)


def duck_curve(voice, depth=0.6):
    e = envelope(voice, 0.2)
    active = np.clip(e / 0.03, 0, 1)
    return smooth_gain(1 - depth * active)


def master(mix, target_rms_db=-17.0):
    rms = np.sqrt(np.mean(mix ** 2)) + 1e-9
    mix = mix * (10 ** (target_rms_db / 20) / rms)
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)  # gentle limiter
    peak = np.max(np.abs(mix))
    if peak > 0.95:
        mix *= 0.95 / peak
    return mix
