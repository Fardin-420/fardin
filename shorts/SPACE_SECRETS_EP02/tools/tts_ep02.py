import soundfile as sf, numpy as np, sys
from kokoro_onnx import Kokoro
T = "/tmp/claude-0/-home-user-fardin/a6ad4762-d397-5227-b379-040b321fcd53/scratchpad/tts/"
k = Kokoro(T + "kokoro-v1.0.onnx", T + "voices-v1.0.bin")
LINES = [
 "What if Earth suddenly stopped spinning... for just five seconds? You might think nothing would happen. But the consequences could be catastrophic.",
 "At the equator, the ground carries you east at about 1,670 kilometers per hour. You don't feel it, because the air and oceans move with you.",
 "Now imagine the solid planet halts, but the atmosphere doesn't. Near the equator, air keeps rushing east at up to 1,670 kilometers per hour, about four times the strongest gust ever measured.",
 "The oceans keep moving too. Water could pile against west-facing coasts, and pull away from east-facing ones. How far, or how high, is uncertain. It depends on depth and coastline shape.",
 "Why? Inertia. Anything not locked to the bedrock keeps moving. That motion is fastest at the equator, and fades toward the poles. Friction slows the air near the ground first. And it all depends on how suddenly the stop happens.",
 "Then, after five seconds, the surface lurches back into motion. Just as abruptly. Another jolt, leaving the ground out of step with the air and sea.",
 "Five seconds sounds harmless. But on a rotating planet, how you stop matters more than how long.",
]
sp = float(sys.argv[1]) if len(sys.argv) > 1 else 1.1
tot = 0
for i, l in enumerate(LINES):
    s, sr = k.create(l, voice="am_puck", speed=sp, lang="en-us")
    env = np.convolve(np.abs(s), np.ones(240) / 240, "same"); idx = np.where(env > 0.01)[0]
    s = s[max(0, idx[0] - 240):min(len(s), idx[-1] + 1200)]
    sf.write(f"L{i}.wav", s, sr); tot += len(s) / sr; print(i, round(len(s) / sr, 2), len(l.split()), "words")
print("total speech", round(tot, 2))
