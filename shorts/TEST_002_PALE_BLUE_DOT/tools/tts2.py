import soundfile as sf, numpy as np
from kokoro_onnx import Kokoro
T = "/tmp/claude-0/-home-user-fardin/a6ad4762-d397-5227-b379-040b321fcd53/scratchpad/tts/"
k = Kokoro(T + "kokoro-v1.0.onnx", T + "voices-v1.0.bin")
LINES = [
    "This tiny dot might be the most humbling photo ever taken.",
    "In 1990, Voyager 1 turned around, nearly four billion miles from home, for one last look back.",
    "Earth showed up as less than a single pixel... floating in a beam of sunlight.",
    "Soon after, its cameras were switched off for good.",
    "Every person you've ever known lived on that speck.",
]
for i, l in enumerate(LINES):
    s, sr = k.create(l, voice="am_puck", speed=1.1, lang="en-us")
    env = np.convolve(np.abs(s), np.ones(240) / 240, "same"); idx = np.where(env > 0.01)[0]
    s = s[max(0, idx[0] - 240):min(len(s), idx[-1] + 1200)]
    sf.write(f"L{i}.wav", s, sr); print(i, round(len(s) / sr, 2))
