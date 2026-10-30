import soundfile as sf, numpy as np
from kokoro_onnx import Kokoro
from lines import LINES, parse
T = "/tmp/claude-0/-home-user-fardin/a6ad4762-d397-5227-b379-040b321fcd53/scratchpad/tts/"
k = Kokoro(T + "kokoro-v1.0.onnx", T + "voices-v1.0.bin")
tot = 0
for i, (text, gap, sp) in enumerate(LINES):
    s, sr = k.create(parse(text)[0], voice="am_puck", speed=sp, lang="en-us")
    env = np.convolve(np.abs(s), np.ones(240) / 240, "same"); idx = np.where(env > 0.01)[0]
    s = s[max(0, idx[0] - 120):min(len(s), idx[-1] + 1200)]
    sf.write(f"vo/L{i:02d}.wav", s, sr); tot += len(s) / sr + gap
print("total", round(tot, 2))
