"""THE 20-MINUTE HEIST — narration builder (Space Secrets brand voice).

Parses script/script_locked.md, synthesizes one file per sentence with
Kokoro-82M (kokoro-onnx, local, Apache-2.0), applies the cleanup chain
(80 Hz high-pass, light de-ess, soft compression; no reverb, no time-stretch,
no pitch-shift), and estimates word timings from Kokoro's phonemes snapped to
detected pauses.

    .venv/bin/python scripts/build_vo.py                     # am_puck (default)
    .venv/bin/python scripts/build_vo.py --voice am_michael  # swap the voice, re-render
    .venv/bin/python scripts/build_vo.py --voice-tests       # 20 s Scene 01 tests

Output: assets/vo/<voice>/<chunk>.wav (48 kHz, git-ignored) and
assets/vo/alignment/vo_manifest.json (chunks, words, cues, gaps).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import soundfile as sf
from num2words import num2words
from scipy.signal import butter, resample_poly, sosfilt

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT.parents[1] / "VOICE_ENGINE" / "models" / "kokoro"
SR_TTS, SR = 24000, 48000
SLOW = 0.87

# ---------------------------------------------------------------- parsing

MARK = re.compile(r"\[\[(CUE:[A-Za-z0-9_]+|PUNCH|IMPACT|SILENCE|SLOW)\]\]")


def parse_script(path: Path) -> list[dict]:
    scenes, cur = [], None
    for raw in path.read_text().splitlines():
        m = re.match(r"^## SCENE (\d+) — (.+?) \{speed=([0-9.]+)\}", raw)
        if m:
            cur = {"id": f"S{int(m.group(1)):02d}", "title": m.group(2).strip(),
                   "speed": float(m.group(3)), "paragraphs": []}
            scenes.append(cur)
            continue
        if raw.startswith("## "):
            cur = None
        if cur is not None and raw.startswith("> "):
            cur["paragraphs"].append(raw[2:].strip())
    return scenes


def split_sentences(par: str) -> list[str]:
    """Split a narration paragraph into synthesis chunks: sentence ends and every '…'."""
    out, buf, i = [], "", 0
    while i < len(par):
        ch = par[i]
        buf += ch
        if ch in ".?!…":
            j = i + 1
            while j < len(par) and par[j] in "\"”'":
                buf += par[j]
                j += 1
            k = j
            while k < len(par) and par[k] == " ":
                k += 1
            # a marker may follow the terminal ("Billions. [[SILENCE]]")
            while par.startswith("[[SILENCE]]", k):
                buf += " [[SILENCE]]"
                k += len("[[SILENCE]]")
                while k < len(par) and par[k] == " ":
                    k += 1
            if ch == "…" or k >= len(par) or j < len(par) and par[j] == " " or par.startswith("[[", k):
                if ch != "." or not re.search(r"\d\.$", buf) or j >= len(par) or par[j] == " ":
                    out.append(buf.strip())
                    buf, i = "", k
                    continue
            i = j
            continue
        i += 1
    if buf.strip():
        out.append(buf.strip())
    return [s for s in out if MARK.sub("", s).strip()]


# ---------------------------------------------------------------- pronunciation

SAY = {
    "UTC": "U T C", "PM": "P M", "USDT": "U S D T", "USDC": "U S D C", "ETH": "E T H",
    "BTC": "B T C", "BNB": "B N B", "ARB": "A R B", "XRP": "X R P", "API": "A P I",
    "TRM": "T R M", "CZ": "C Z", "CZ's": "C Z's", "DMM": "D M M", "HR": "H R", "CEO": "C E O",
    "Co-CEO": "co-C E O", "DevOps": "dev ops", "SAFU": "Sayfoo", "Aave": "Ahvay",
    "TraderTraitor": "Trader Traitor", "Zhao": "Jao", "Changpeng": "Chang Peng",
    "FBI": "F B I", "AI": "A I", "TRM's": "T R M's",
}
ORD = {"1st": "first", "3rd": "third", "7th": "seventh", "29th": "twenty-ninth"}


def year(n: int) -> str:
    return "twenty " + (num2words(n - 2000) if n >= 2010 else "oh " + num2words(n - 2000))


def num(s: str) -> str:
    return num2words(float(s) if "." in s else int(s)).replace(" and ", " ").replace(",", "")


def say_core(core: str) -> str:
    if core in SAY:
        return SAY[core]
    if core in ORD:
        return ORD[core]
    if m := re.fullmatch(r"EIP-(\d+)", core):
        return "E I P seventy-seven oh two" if m.group(1) == "7702" else "E I P " + num(m.group(1))
    if m := re.fullmatch(r"(\d{1,2}):(\d{2})", core):
        h, mi = int(m.group(1)), int(m.group(2))
        tail = "" if mi == 0 else (" oh " + num2words(mi) if mi < 10 else " " + num2words(mi))
        return num2words(h) + tail
    if re.fullmatch(r"(19|20)\d\d", core):
        return year(int(core))
    if m := re.fullmatch(r"(\d+(?:\.\d+)?)%", core):
        return num(m.group(1)) + " percent"
    if re.fullmatch(r"\d{1,3}(,\d{3})+", core):
        return num(core.replace(",", ""))
    if re.fullmatch(r"\d+(\.\d+)?", core):
        return num(core)
    return core


def tokens(text: str) -> list[tuple[str, str]]:
    """Display tokens and their spoken form (1:1, so word timings map back to captions)."""
    out = []
    for tok in text.split():
        m = re.fullmatch(r"([\"“(]*)(.*?)([\"”).,;:?!…]*)", tok)
        lead, core, trail = m.groups()
        out.append((tok, lead + say_core(core) + trail))
    return out


# ---------------------------------------------------------------- DSP cleanup


def cleanup(x: np.ndarray, sr: int) -> np.ndarray:
    x = sosfilt(butter(4, 80, "highpass", fs=sr, output="sos"), x)
    # light de-ess: duck the 5.5–10 kHz band only when it dominates
    band = sosfilt(butter(4, [5500, min(10000, sr / 2 - 200)], "bandpass", fs=sr, output="sos"), x)

    def env(sig, att, rel):
        # attack-fast/release-slow follower, vectorized: fast one-pole, then slow one-pole on the max
        from scipy.signal import lfilter
        s = np.abs(sig)
        fa = lfilter([1 - np.exp(-1 / (att * sr))], [1, -np.exp(-1 / (att * sr))], s)
        fr = lfilter([1 - np.exp(-1 / (rel * sr))], [1, -np.exp(-1 / (rel * sr))], s)
        return np.maximum(fa, fr)

    eb, ef = env(band, 0.002, 0.04), env(x, 0.002, 0.04) + 1e-9
    ratio = eb / ef
    g = np.clip(0.30 / np.maximum(ratio, 1e-9), 0.55, 1.0)  # at most ≈ −5 dB on sibilants
    x = x - band + band * g
    # soft compression: 2.2:1 above −20 dBFS, soft knee, slow-ish release
    lvl = 20 * np.log10(env(x, 0.008, 0.15) + 1e-9)
    over = np.maximum(lvl + 20, 0)
    knee = 6.0
    red = np.where(over < knee, over ** 2 / (2 * knee), over - knee / 2) * (1 - 1 / 2.2)
    x = x * 10 ** (-red / 20)
    return x.astype(np.float32)


# ---------------------------------------------------------------- alignment


def silent_runs(x: np.ndarray, sr: int, min_ms=55) -> list[tuple[float, float]]:
    hop = int(0.005 * sr)
    n = len(x) // hop
    rms = np.sqrt(np.mean(x[: n * hop].reshape(n, hop) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms)
    thr = max(db.max() - 38, -52)
    sil = db < thr
    runs, i = [], 0
    while i < n:
        if sil[i]:
            j = i
            while j < n and sil[j]:
                j += 1
            if (j - i) * 5 >= min_ms and i > 0 and j < n:
                runs.append((i * hop / sr, j * hop / sr))
            i = j
        else:
            i += 1
    voiced = np.where(~sil)[0]
    span = (voiced[0] * hop / sr, (voiced[-1] + 1) * hop / sr) if len(voiced) else (0, len(x) / sr)
    return runs, span


def align(words: list[tuple[str, str]], x: np.ndarray, sr: int, phon) -> list[dict]:
    w = np.array([max(len(phon(s.strip("\"“”().,;:?!…—"))), 1) + 1.5 for _, s in words], float)
    runs, (t0, t1) = silent_runs(x, sr)
    total_sil = sum(b - a for a, b in runs)
    speech = max(t1 - t0 - total_sil, 0.05)
    # punctuation boundaries are the preferred homes for internal pauses
    punct = [i for i, (d, _) in enumerate(words[:-1]) if re.search(r"[,;:—…]$|—$", d) or words[i + 1][0] == "—"]
    est_b = t0 + np.cumsum(w)[:-1] / w.sum() * (t1 - t0)
    assign, free = {}, set(range(len(words) - 1))
    for a, b in sorted(runs, key=lambda r: r[0] - r[1]):  # longest pauses first
        mid = (a + b) / 2
        cands = [i for i in punct if i in free] or sorted(free)
        if not cands:
            break
        i = min(cands, key=lambda k: abs(est_b[k] - mid))
        if abs(est_b[i] - mid) > 0.6 and i not in punct:
            continue
        assign[i] = (a, b)
        free.discard(i)
    # build times: distribute speech time by weight, insert assigned pauses
    gap_after = {i: b - a for i, (a, b) in assign.items()}
    used = sum(gap_after.values())
    speech = max(t1 - t0 - used, 0.05)
    t, out = t0, []
    for i, (disp, spk) in enumerate(words):
        dur = speech * w[i] / w.sum()
        out.append({"w": disp, "start": round(t, 3), "end": round(t + dur, 3)})
        t += dur + gap_after.get(i, 0.0)
    return out


# ---------------------------------------------------------------- build


def chunk_plan(scenes: list[dict]) -> list[dict]:
    plan = []
    for sc in scenes:
        n = 0
        for pi, par in enumerate(sc["paragraphs"]):
            sents = split_sentences(par)
            for si, s in enumerate(sents):
                n += 1
                slow = "[[SLOW]]" in s
                speed = SLOW if slow else sc["speed"]
                silence = "[[SILENCE]]" in s
                display_marked = s.replace("[[SLOW]]", "").replace("[[SILENCE]]", "").strip()
                # word-indexed markers
                words_raw, marks, pending = [], [], []
                for tok in re.split(r"(\[\[[^\]]+\]\])", display_marked):
                    if not tok.strip():
                        continue
                    if tok.startswith("[["):
                        pending.append(tok[2:-2])
                        continue
                    for wtok in tok.split():
                        for p in pending:
                            marks.append({"word": len(words_raw), "mark": p})
                        pending = []
                        words_raw.append(wtok)
                display = " ".join(words_raw)
                last_in_par = si == len(sents) - 1
                h = int(hashlib.md5(display.encode()).hexdigest(), 16)
                if silence:
                    gap = 1.0
                elif display.endswith("…"):
                    gap = 0.5
                elif last_in_par:
                    gap = 0.40
                else:
                    gap = 0.27 + (h % 9) * 0.01  # 270–350 ms
                plan.append({"id": f"{sc['id']}_{n:03d}", "scene": sc["id"], "text": display,
                             "speed": speed, "gap_after": round(gap, 3), "marks": marks,
                             "silence_after": silence})
    return plan


def synth_chunks(plan, voice: str, outdir: Path, limit_ids=None) -> list[dict]:
    from kokoro_onnx import Kokoro

    k = Kokoro(str(MODELS / "kokoro-v1.0.onnx"), str(MODELS / "voices-v1.0.bin"))
    phon = lambda s: k.tokenizer.phonemize(s, "en-us") if s else ""
    outdir.mkdir(parents=True, exist_ok=True)
    res = []
    for c in plan:
        if limit_ids and c["id"] not in limit_ids:
            continue
        toks = tokens(c["text"])
        tts = " ".join(s for _, s in toks)
        key = hashlib.md5(f"{voice}|{c['speed']}|{tts}".encode()).hexdigest()[:10]
        wav = outdir / f"{c['id']}_{key}.wav"
        if wav.exists():
            y, _ = sf.read(wav, dtype="float32")
        else:
            x, sr = k.create(tts, voice=voice, speed=c["speed"], lang="en-us", trim=True)
            x = cleanup(np.asarray(x, np.float64), sr)
            y = resample_poly(x, SR // SR_TTS, 1).astype(np.float32)
            # gentle 4 ms fades so chunk edges never click
            f = int(0.004 * SR)
            y[:f] *= np.linspace(0, 1, f)
            y[-f:] *= np.linspace(1, 0, f)
            sf.write(wav, y, SR, subtype="PCM_24")
        words = align(toks, y, SR, phon)
        res.append({**c, "tts": tts, "file": str(wav.relative_to(ROOT)), "dur": round(len(y) / SR, 3),
                    "words": words})
        print(f"{c['id']} {len(y)/SR:5.2f}s v={c['speed']:.2f} {c['text'][:70]}")
    return res


def assemble(chunks, pad=0.4) -> np.ndarray:
    parts = [np.zeros(int(pad * SR), np.float32)]
    for c in chunks:
        y, _ = sf.read(ROOT / c["file"], dtype="float32")
        parts += [y, np.zeros(int(c["gap_after"] * SR), np.float32)]
    return np.concatenate(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default="am_puck")
    ap.add_argument("--voice-tests", action="store_true")
    a = ap.parse_args()
    scenes = parse_script(ROOT / "script" / "script_locked.md")
    plan = chunk_plan(scenes)
    if a.voice_tests:
        test_ids, t = [], 0.0
        for c in plan:  # first ~20 s of Scene 01
            if c["scene"] != "S01" or t > 19.0:
                break
            test_ids.append(c["id"])
            t += len(c["text"].split()) / 2.4 + c["gap_after"]
        out = ROOT / "out" / "voice_tests"
        out.mkdir(parents=True, exist_ok=True)
        for v in ["am_puck", "am_michael", "am_fenrir"]:
            ch = synth_chunks(plan, v, ROOT / "assets" / "vo" / v, set(test_ids))
            y = assemble(ch)
            y = y / max(np.abs(y).max(), 1e-6) * 10 ** (-1.5 / 20)
            sf.write(out / f"scene01_test_{v}.wav", y, SR, subtype="PCM_16")
            print(f"-> out/voice_tests/scene01_test_{v}.wav {len(y)/SR:.1f}s")
        return
    chunks = synth_chunks(plan, a.voice, ROOT / "assets" / "vo" / a.voice)
    man = {"voice": a.voice, "engine": "kokoro-onnx / Kokoro-82M v1.0", "sample_rate": SR,
           "alignment": "phoneme-weighted, snapped to detected pauses (no ASR model reachable)",
           "scenes": [{k: s[k] for k in ("id", "title", "speed")} for s in scenes], "chunks": chunks}
    p = ROOT / "assets" / "vo" / "alignment" / "vo_manifest.json"
    p.write_text(json.dumps(man, indent=1))
    words = sum(len(c["words"]) for c in chunks)
    speech = sum(c["dur"] for c in chunks)
    print(f"\n{len(chunks)} chunks · {words} words · {speech/60:.2f} min speech · "
          f"{(speech + sum(c['gap_after'] for c in chunks))/60:.2f} min with gaps -> {p.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
