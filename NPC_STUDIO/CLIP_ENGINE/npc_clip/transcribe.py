"""Speech → word-level transcript (Parakeet-TDT 0.6B via sherpa-onnx, Silero VAD chunking)."""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import soundfile as sf

from .common import MODELS, log, run, write_json

ASR_DIR = MODELS / "sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8"
VAD = MODELS / "silero_vad.onnx"
ASR_SR = 16000
FILLERS = {"um", "uh", "erm", "uhm", "ah", "hmm", "mm", "er"}


def extract_wav16(src: Path, out: Path) -> np.ndarray:
    if not out.exists():
        run(["ffmpeg", "-y", "-v", "error", "-i", src, "-vn", "-ac", "1", "-ar", ASR_SR, "-c:a", "pcm_s16le", out])
    a, _ = sf.read(out, dtype="float32")
    return a


def _recognizer():
    import sherpa_onnx
    if not (ASR_DIR / "encoder.int8.onnx").exists():
        raise RuntimeError(f"ASR model missing in {ASR_DIR}. Run CLIP_ENGINE/setup.sh")
    return sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=str(ASR_DIR / "encoder.int8.onnx"), decoder=str(ASR_DIR / "decoder.int8.onnx"),
        joiner=str(ASR_DIR / "joiner.int8.onnx"), tokens=str(ASR_DIR / "tokens.txt"),
        num_threads=4, model_type="nemo_transducer")


def _speech_chunks(audio: np.ndarray) -> list[tuple[int, int]]:
    """Silero VAD regions merged into ≤ 24 s chunks that start/end in pauses."""
    import sherpa_onnx
    cfg = sherpa_onnx.VadModelConfig()
    cfg.silero_vad.model = str(VAD)
    cfg.silero_vad.min_silence_duration = 0.25
    cfg.silero_vad.min_speech_duration = 0.15
    cfg.silero_vad.max_speech_duration = 20
    cfg.sample_rate = ASR_SR
    vad = sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=60)
    win = cfg.silero_vad.window_size
    regions = []
    for i in range(0, len(audio), win):
        vad.accept_waveform(audio[i:i + win])
        while not vad.empty():
            seg = vad.front
            regions.append((seg.start, seg.start + len(seg.samples)))
            vad.pop()
    vad.flush()
    while not vad.empty():
        seg = vad.front
        regions.append((seg.start, seg.start + len(seg.samples)))
        vad.pop()
    pad = int(0.12 * ASR_SR)
    chunks: list[list[int]] = []
    for s, e in regions:
        s, e = max(0, s - pad), min(len(audio), e + pad)
        if chunks and s - chunks[-1][1] < int(0.4 * ASR_SR) and e - chunks[-1][0] < 24 * ASR_SR:
            chunks[-1][1] = e
        else:
            chunks.append([s, e])
    return [(s, e) for s, e in chunks]


def _tokens_to_words(tokens, ts, durs, offset: float) -> list[dict]:
    words: list[dict] = []
    for i, (tok, t) in enumerate(zip(tokens, ts)):
        d = durs[i] if durs is not None and i < len(durs) and durs[i] > 0 else 0.08
        t0, t1 = offset + float(t), offset + float(t) + float(d)
        if tok.startswith(" ") or not words:
            if re.fullmatch(r"\s*[^\w\s]+", tok) and words:
                words[-1]["w"] += tok.strip()
                words[-1]["e"] = max(words[-1]["e"], t1)
                continue
            words.append({"w": tok.strip(), "s": t0, "e": t1})
        else:
            words[-1]["w"] += tok
            words[-1]["e"] = max(words[-1]["e"], t1)
    # end = min(own end, next start); guarantees monotonic non-overlapping words
    for a, b in zip(words, words[1:]):
        a["e"] = min(max(a["e"], a["s"] + 0.05), b["s"]) if b["s"] > a["s"] else a["s"] + 0.05
    return [w for w in words if w["w"]]


def norm(w: str) -> str:
    return re.sub(r"[^\w']", "", w.lower())


def sentences_from_words(words: list[dict]) -> list[dict]:
    out, start = [], 0
    for i, w in enumerate(words):
        gap_next = words[i + 1]["s"] - w["e"] if i + 1 < len(words) else 9
        end_punct = bool(re.search(r"[.?!]['\"”)]*$", w["w"]))
        if end_punct or gap_next > 1.2 or i == len(words) - 1:
            ws = words[start:i + 1]
            out.append({"s": round(ws[0]["s"], 3), "e": round(ws[-1]["e"], 3), "wi": [start, i],
                        "text": " ".join(x["w"] for x in ws)})
            start = i + 1
    return out


def transcribe(src: Path, dirs: dict, force: bool = False) -> dict:
    out_json = dirs["Analysis"] / "transcript.json"
    if out_json.exists() and not force:
        import json
        log("transcript: cached")
        return json.loads(out_json.read_text())
    wav = dirs["work"] / "audio16k.wav"
    audio = extract_wav16(src, wav)
    log(f"transcribing {len(audio) / ASR_SR:.0f}s of audio (Parakeet-TDT, CPU)")
    rec = _recognizer()
    chunks = _speech_chunks(audio)
    words: list[dict] = []
    for k, (s, e) in enumerate(chunks):
        st = rec.create_stream()
        st.accept_waveform(ASR_SR, audio[s:e])
        rec.decode_stream(st)
        r = st.result
        durs = list(r.durations) if getattr(r, "durations", None) else None
        words += _tokens_to_words(r.tokens, r.timestamps, durs, s / ASR_SR)
        if k % 25 == 0:
            log(f"  asr chunk {k + 1}/{len(chunks)}")
    for w in words:
        w["s"], w["e"] = round(w["s"], 3), round(w["e"], 3)
        w["filler"] = norm(w["w"]) in FILLERS
    sents = sentences_from_words(words)
    tr = {"engine": "nemo-parakeet-tdt-0.6b-v2-int8 (sherpa-onnx)", "language": "en",
          "duration": len(audio) / ASR_SR, "words": words, "sentences": sents}
    write_json(out_json, tr)
    lines = [f"[{s['s']:8.2f} → {s['e']:8.2f}] {s['text']}" for s in sents]
    (dirs["Analysis"] / "transcript.txt").write_text("\n".join(lines) + "\n")
    log(f"transcript: {len(words)} words, {len(sents)} sentences")
    return tr
