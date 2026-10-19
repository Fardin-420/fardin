"""NPC_GUEST_VOICE — stand-in narrator used until NPC_VOICE_V1 is ready.

Kokoro-82M (Apache-2.0) running locally via ONNX. A fixed blend of two male
voices gives a deeper, cinematic timbre. Same interface as npc_voice.Voice so
build_narration.py can use either engine.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

MODEL_DIR = Path(__file__).resolve().parent / "models" / "kokoro"
NAME = "NPC_GUEST_VOICE"

# Fixed style blend: one consistent speaker for every line.
BLEND = {"am_michael": 0.7, "am_onyx": 0.3}

# Kokoro exposes speed only; emotion is carried by pacing (and by per-line gain in the script).
EMOTION_SPEED = {
    "CALM": 0.90, "MYSTERIOUS": 0.86, "CONFIDENT": 0.94, "CINEMATIC": 0.90,
    "DRAMATIC": 0.85, "AGGRESSIVE": 1.00, "ENERGETIC": 1.05,
}


class GuestVoice:
    def __init__(self):
        from kokoro_onnx import Kokoro

        if not (MODEL_DIR / "kokoro-v1.0.onnx").exists():
            raise SystemExit(
                f"Kokoro model missing. Download kokoro-v1.0.onnx and voices-v1.0.bin into {MODEL_DIR} from\n"
                "https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0")
        self.k = Kokoro(str(MODEL_DIR / "kokoro-v1.0.onnx"), str(MODEL_DIR / "voices-v1.0.bin"))
        self.style = sum(self.k.get_voice_style(v) * w for v, w in BLEND.items())
        self.sr = 24000
        self.name = NAME

    def say(self, text: str, emotion: str = "CONFIDENT") -> tuple[np.ndarray, float | None]:
        wav, sr = self.k.create(text, voice=self.style, speed=EMOTION_SPEED[emotion], lang="en-us")
        assert sr == self.sr
        return wav.astype(np.float32), None
