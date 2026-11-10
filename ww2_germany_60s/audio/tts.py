#!/usr/bin/env python3
"""tts.py — narration for every scene + exact timing.

Reads  build/timeline_base.json   (written by `node src/timeline.js --dump`)
Writes build/narration/line_XX.wav  (48 kHz mono float, silence-trimmed)
       build/narration_timing.json  (per-line duration + per-word start/end, seconds from line start)

Voice:  edge-tts "en-US-AndrewNeural" (fallback "en-US-GuyNeural"), rate -5%.
        Override with env NARRATION_VOICE / NARRATION_RATE.
Custom: if ./narration.wav exists in the project root it is used instead of TTS. It is split into
        one segment per scene at its longest pauses; word timing is distributed by syllable count.

Narration is never cut. If the lines (plus lead-in and 0.3 s tails) cannot fit in 60 s, the whole
script is re-synthesized at a slightly faster rate until it does, and a warning is printed.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
NARR_DIR = BUILD / "narration"
CACHE = BUILD / "tts_cache"
SR = 48000
VOICES = [os.environ.get("NARRATION_VOICE", "en-US-AndrewNeural"), "en-US-GuyNeural"]
BASE_RATE = int(os.environ.get("NARRATION_RATE", "-5").replace("%", ""))
TICKS = 10_000_000  # edge-tts offsets are in 100 ns ticks


# ------------------------------------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------------------------------------
def decode_to_array(path: Path) -> np.ndarray:
    """Decode any audio file to 48 kHz mono float32 with ffmpeg."""
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
        check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def syllables(word: str) -> int:
    w = norm(word)
    if not w:
        return 1
    if w.isdigit():  # "1939" -> "nineteen thirty-nine"
        return 2 * max(1, len(w) // 2) + 1
    groups = re.findall(r"[aeiouy]+", w)
    n = len(groups) - (1 if w.endswith("e") and len(groups) > 1 else 0)
    return max(1, n)


def trim(audio: np.ndarray, thresh_db: float = -45.0, pad: float = 0.03) -> tuple[np.ndarray, float]:
    """Trim leading/trailing silence. Returns (trimmed, seconds removed from the front)."""
    win = int(0.01 * SR)
    frames = len(audio) // win
    if frames == 0:
        return audio, 0.0
    rms = np.sqrt(np.mean(audio[: frames * win].reshape(frames, win) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms + 1e-12)
    loud = np.where(db > thresh_db)[0]
    if len(loud) == 0:
        return audio, 0.0
    a = max(0, loud[0] * win - int(pad * SR))
    b = min(len(audio), (loud[-1] + 1) * win + int(pad * SR))
    return audio[a:b], a / SR


def distribute_words(text: str, duration: float) -> list[dict]:
    """Fallback word timing: spread tokens over the line proportionally to syllable count."""
    tokens = text.split()
    weights = np.array([syllables(t) + (0.6 if re.search(r"[,.;:!?]$", t) else 0.0) for t in tokens], float)
    edges = np.concatenate([[0.0], np.cumsum(weights) / weights.sum() * duration])
    return [{"text": t, "start": round(float(edges[i]), 4), "end": round(float(edges[i + 1]), 4)}
            for i, t in enumerate(tokens)]


def align_tokens(text: str, boundaries: list[dict], offset: float, duration: float) -> list[dict] | None:
    """Map edge-tts WordBoundary events onto the script's own tokens (keeps punctuation for subtitles).

    Works at character level, because edge-tts sometimes merges several tokens into one boundary
    (e.g. "June 6, 1944"): each boundary's characters are spread linearly over its time span, and
    every token takes the time span of its own characters.
    """
    times = []  # (start, end) per normalized character
    for b in boundaries:
        chars = norm(b["text"])
        span = (b["end"] - b["start"]) / max(1, len(chars))
        times += [(b["start"] + k * span, b["start"] + (k + 1) * span) for k in range(len(chars))]
    tokens = text.split()
    if "".join(norm(t) for t in tokens) != "".join(norm(b["text"]) for b in boundaries):
        return None
    out, k = [], 0
    for tok in tokens:
        n = len(norm(tok))
        if n == 0:
            return None
        s, e = times[k][0], times[k + n - 1][1]
        k += n
        out.append({"text": tok, "start": round(max(0.0, s - offset), 4), "end": round(min(duration, e - offset), 4)})
    return out


# ------------------------------------------------------------------------------------------------
# edge-tts
# ------------------------------------------------------------------------------------------------
async def synth_edge(text: str, voice: str, rate: int, mp3: Path) -> list[dict]:
    import edge_tts

    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    comm = edge_tts.Communicate(text, voice, rate=f"{rate:+d}%", proxy=proxy, boundary="WordBoundary")
    bounds = []
    with open(mp3, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                s = chunk["offset"] / TICKS
                bounds.append({"text": chunk["text"], "start": s, "end": s + chunk["duration"] / TICKS})
    if mp3.stat().st_size == 0:
        raise RuntimeError("edge-tts returned no audio")
    return bounds


def tts_line(text: str, rate: int, voice: str, retries: int = 4) -> tuple[np.ndarray, list[dict]]:
    """Synthesize one line with one voice (cached). Retries transient service errors with backoff."""
    import time
    CACHE.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(f"{voice}|{rate}|{text}".encode()).hexdigest()[:16]
    mp3, meta = CACHE / f"{key}.mp3", CACHE / f"{key}.json"
    if not (mp3.exists() and meta.exists()):
        for attempt in range(retries):
            try:
                bounds = asyncio.run(synth_edge(text, voice, rate, mp3))
                meta.write_text(json.dumps(bounds))
                break
            except Exception as e:
                mp3.unlink(missing_ok=True)
                print(f"  ! {voice} attempt {attempt + 1} failed: {e}", file=sys.stderr)
                if attempt == retries - 1:
                    raise
                time.sleep(2 ** (attempt + 1))
    return decode_to_array(mp3), json.loads(meta.read_text())


def build_tts(lines: list[dict], rate: int) -> tuple[list[dict], list[np.ndarray], str]:
    """All lines use ONE voice: the primary if every line succeeds, else the fallback for all."""
    last_err = None
    for voice in VOICES:
        try:
            out, audios = [], []
            for line in lines:
                audio, bounds = tts_line(line["text"], rate, voice)
                trimmed, cut = trim(audio)
                dur = len(trimmed) / SR
                words = align_tokens(line["text"], bounds, cut, dur)
                out.append({"id": line["id"], "text": line["text"], "duration": round(dur, 4),
                            "words": words or distribute_words(line["text"], dur),
                            "word_source": "edge-tts" if words else "syllables"})
                audios.append(trimmed)
            return out, audios, voice
        except Exception as e:
            last_err = e
            print(f"  ! voice {voice} unavailable, trying fallback", file=sys.stderr)
    raise SystemExit(f"edge-tts failed for every voice ({last_err}). Provide ./narration.wav instead.")


# ------------------------------------------------------------------------------------------------
# user-supplied narration.wav
# ------------------------------------------------------------------------------------------------
def build_custom(lines: list[dict], wav: Path) -> tuple[list[dict], list[np.ndarray]]:
    audio, _ = trim(decode_to_array(wav))
    n = len(lines)
    win = int(0.02 * SR)
    frames = len(audio) // win
    rms = np.sqrt(np.mean(audio[: frames * win].reshape(frames, win) ** 2, axis=1))
    silent = 20 * np.log10(rms + 1e-9) < -42
    # collect silent runs, keep the n-1 longest as line breaks
    runs, k = [], 0
    while k < frames:
        if silent[k]:
            j = k
            while j < frames and silent[j]:
                j += 1
            runs.append((j - k, k, j))
            k = j
        else:
            k += 1
    cuts = sorted(sorted(runs, reverse=True)[: n - 1], key=lambda r: r[1])
    if len(cuts) < n - 1:  # not enough pauses: split proportionally to word count
        counts = np.array([len(l["text"].split()) for l in lines], float)
        pos = (np.cumsum(counts)[:-1] / counts.sum() * len(audio)).astype(int)
        bounds = [0, *pos.tolist(), len(audio)]
    else:
        bounds = [0, *[((a + b) // 2) * win for _, a, b in cuts], len(audio)]
    out, audios = [], []
    for i, line in enumerate(lines):
        seg, _ = trim(audio[bounds[i]: bounds[i + 1]])
        dur = len(seg) / SR
        out.append({"id": line["id"], "text": line["text"], "duration": round(dur, 4),
                    "words": distribute_words(line["text"], dur), "word_source": "syllables"})
        audios.append(seg)
    return out, audios


def main() -> None:
    base = json.loads((BUILD / "timeline_base.json").read_text())
    lines, budget = base["lines"], base["duration"]
    overhead = len(lines) * (base["minLead"] + base["narrationTail"])
    custom = ROOT / "narration.wav"
    NARR_DIR.mkdir(parents=True, exist_ok=True)

    if custom.exists():
        print(f"using custom narration: {custom}")
        out, audios = build_custom(lines, custom)
        voice, rate = "custom narration.wav", 0
        if sum(l["duration"] for l in out) + overhead > budget:
            raise SystemExit("narration.wav is too long to fit 60 s with scene tails; shorten the read.")
    else:
        rate = BASE_RATE
        while True:
            out, audios, voice = build_tts(lines, rate)
            total = sum(l["duration"] for l in out)
            print(f"voice {voice} rate {rate:+d}%: narration {total:.2f} s (+{overhead:.1f} s lead/tails, budget {budget} s)")
            if total + overhead <= budget:
                break
            rate += 3
            print(f"  ! does not fit; re-synthesizing at {rate:+d}% (narration is never cut)")
            if rate > 25:
                raise SystemExit("narration cannot fit in 60 s even at +25% rate")

    for i, a in enumerate(audios):
        sf.write(NARR_DIR / f"line_{i:02d}.wav", a.astype(np.float32), SR, subtype="FLOAT")
    timing = {"sample_rate": SR, "voice": voice, "rate": f"{rate:+d}%", "lines": out}
    (BUILD / "narration_timing.json").write_text(json.dumps(timing, indent=2))
    for l in out:
        print(f"  {l['id']:<11} {l['duration']:5.2f} s  {len(l['words']):2d} words ({l['word_source']})")
    print("wrote build/narration_timing.json")


if __name__ == "__main__":
    main()
