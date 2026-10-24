import soundfile as sf, numpy as np, os
from kokoro_onnx import Kokoro
from lines import flat, parse, SPEED
T = "/tmp/claude-0/-home-user-fardin/a6ad4762-d397-5227-b379-040b321fcd53/scratchpad/tts/"
k = Kokoro(T + "kokoro-v1.0.onnx", T + "voices-v1.0.bin")
os.makedirs("vo", exist_ok=True)
tot = 0
for i, (ci, pi, text) in enumerate(flat()):
    s, sr = k.create(parse(text)[0], voice="am_puck", speed=SPEED, lang="en-us")
    env = np.convolve(np.abs(s), np.ones(240) / 240, "same"); idx = np.where(env > 0.01)[0]
    s = s[max(0, idx[0] - 240):min(len(s), idx[-1] + 1200)]
    sf.write(f"vo/L{i:03d}.wav", s, sr); tot += len(s) / sr
print("lines", i + 1, "speech total", round(tot, 1))
