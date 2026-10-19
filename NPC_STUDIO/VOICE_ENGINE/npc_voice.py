"""NPC voice engine — shared helpers for NPC_VOICE_V1.

Every script in VOICE_ENGINE goes through this module so all narration uses the
same reference audio, the same model and the same per-emotion settings.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import numpy as np

STUDIO = Path(__file__).resolve().parents[1]
PROFILE_DIR = STUDIO / "VOICE" / "NPC_VOICE_V1"
CONFIG_PATH = PROFILE_DIR / "voice_config.json"
LOCAL_MODEL_DIR = Path(__file__).resolve().parent / "models" / "chatterbox"

# Minimum continuous speech in the reference before we trust a clone.
MIN_SPEECH_SECONDS = 8.0
RECOMMENDED_SPEECH_SECONDS = 20.0


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text())


def save_config(cfg: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2) + "\n")


def run(cmd: list[str]) -> str:
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stderr


def clean_reference(src: Path, dst: Path) -> None:
    """Gentle cleanup: rumble filter, light spectral denoise, trim edges, level.

    Denoise strength is deliberately low (nr=10) so the natural texture of the
    voice survives; aggressive denoising is what makes clones sound metallic.
    """
    chain = ",".join([
        "highpass=f=70",
        "afftdn=nr=10:nf=-60",
        "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08",
        "areverse",
        "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.15",
        "areverse",
        "loudnorm=I=-20:TP=-2:LRA=11",
    ])
    dst.parent.mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", "-hide_banner", "-y", "-i", str(src), "-af", chain,
         "-ar", "24000", "-ac", "1", str(dst)])


def speech_seconds(path: Path, threshold_db: float = -40.0) -> float:
    """Seconds of non-silent audio, via ffmpeg silencedetect."""
    dur = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        check=True, capture_output=True, text=True).stdout)
    log = run(["ffmpeg", "-hide_banner", "-i", str(path), "-af",
               f"silencedetect=n={threshold_db}dB:d=0.25", "-f", "null", "-"])
    silent, start = 0.0, None
    for line in log.splitlines():
        if "silence_start" in line:
            start = float(line.split("silence_start:")[1])
        elif "silence_end" in line and start is not None:
            silent += float(line.split("silence_end:")[1].split("|")[0]) - start
            start = None
    if start is not None:
        silent += dur - start
    return max(0.0, dur - silent)


def analyze(path: Path) -> dict:
    import librosa

    y, sr = librosa.load(str(path), sr=24000)
    f0, voiced, _ = librosa.pyin(y, fmin=60, fmax=400, sr=sr)
    f = f0[voiced]
    rms = librosa.feature.rms(y=y)[0]
    noise = np.percentile(rms, 10) + 1e-9
    signal = np.percentile(rms, 90) + 1e-9
    onsets = librosa.onset.onset_detect(y=y, sr=sr, units="time")
    dur = len(y) / sr
    return {
        "duration_s": round(dur, 2),
        "speech_s": round(speech_seconds(path), 2),
        "f0_median_hz": round(float(np.median(f)), 1) if len(f) else None,
        "f0_p5_hz": round(float(np.percentile(f, 5)), 1) if len(f) else None,
        "f0_p95_hz": round(float(np.percentile(f, 95)), 1) if len(f) else None,
        "spectral_centroid_hz": round(float(librosa.feature.spectral_centroid(y=y, sr=sr).mean())),
        "est_snr_db": round(float(20 * np.log10(signal / noise)), 1),
        "onset_rate_per_s": round(len(onsets) / max(dur, 1e-6), 2),
    }


def load_model(device: str = "cpu"):
    """Chatterbox, from VOICE_ENGINE/models/chatterbox if present, else the HF hub."""
    from chatterbox.tts import ChatterboxTTS

    if (LOCAL_MODEL_DIR / "t3_cfg.safetensors").exists():
        return ChatterboxTTS.from_local(LOCAL_MODEL_DIR, device)
    try:
        return ChatterboxTTS.from_pretrained(device=device)
    except Exception as exc:  # network policy, missing weights, ...
        raise SystemExit(
            "Could not load Chatterbox weights.\n"
            f"  cause: {type(exc).__name__}: {exc}\n"
            "  fix:   allow huggingface.co in the environment's network policy, or place\n"
            "         ve.safetensors, t3_cfg.safetensors, s3gen.safetensors, tokenizer.json,\n"
            f"         conds.pt from ResembleAI/chatterbox in {LOCAL_MODEL_DIR}"
        ) from exc


class Voice:
    """NPC_VOICE_V1 synthesizer with speaker-similarity gating."""

    def __init__(self, device: str = "cpu"):
        import torch

        self.cfg = load_config()
        if not self.cfg.get("ready_for_cloning"):
            raise SystemExit(
                "NPC_VOICE_V1 reference is not sufficient for cloning yet: "
                + "; ".join(self.cfg.get("issues", []))
                + "\nRegister a longer recording with register_voice.py.")
        torch.manual_seed(self.cfg["synthesis"]["seed"])
        self.model = load_model(device)
        self.ref = str(STUDIO / self.cfg["clean_reference"])
        self.sr = self.model.sr
        self.ref_embed = self._embed_file(self.ref)

    def _embed(self, wav: np.ndarray, sr: int) -> np.ndarray:
        e = self.model.ve.embeds_from_wavs([wav.astype(np.float32)], sample_rate=sr, as_spk=True)
        return e / np.linalg.norm(e)

    def _embed_file(self, path: str) -> np.ndarray:
        import librosa
        y, sr = librosa.load(path, sr=None)
        return self._embed(y, sr)

    def similarity(self, wav: np.ndarray) -> float:
        return float(np.dot(self._embed(wav, self.sr), self.ref_embed))

    def say(self, text: str, emotion: str = "CONFIDENT") -> tuple[np.ndarray, float]:
        """Generate `takes` candidates and keep the one closest to the reference voice."""
        import torch

        syn = self.cfg["synthesis"]
        params = syn["emotions"][emotion]
        best, best_sim = None, -1.0
        for take in range(syn["takes"]):
            torch.manual_seed(syn["seed"] + take)
            wav = self.model.generate(
                text, audio_prompt_path=self.ref,
                exaggeration=params["exaggeration"], cfg_weight=params["cfg_weight"],
                temperature=params["temperature"],
            ).squeeze(0).cpu().numpy()
            sim = self.similarity(wav)
            if sim > best_sim:
                best, best_sim = wav, sim
        return best, best_sim


def trim(wav: np.ndarray, sr: int, top_db: float = 38, pad: float = 0.04) -> np.ndarray:
    import librosa
    _, (a, b) = librosa.effects.trim(wav, top_db=top_db)
    p = int(pad * sr)
    return wav[max(0, a - p): min(len(wav), b + p)]


def apply_pronunciation(text: str, table: dict) -> str:
    for k, v in table.items():
        text = text.replace(k, v)
    return text


def env_device() -> str:
    return os.environ.get("NPC_DEVICE", "cpu")
