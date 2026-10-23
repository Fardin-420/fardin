import soundfile as sf, numpy as np, sys
from kokoro_onnx import Kokoro
T = "/tmp/claude-0/-home-user-fardin/a6ad4762-d397-5227-b379-040b321fcd53/scratchpad/tts/"
k = Kokoro(T + "kokoro-v1.0.onnx", T + "voices-v1.0.bin")
LINES = [
 "Fall into a black hole... and to everyone watching, you'd never quite make it in.",
 "This is a simulation, built from Einstein's equations. That ring is superheated gas, swirling around it.",
 "Its gravity bends light so much, you can see the far side of the disk, warped up and over the top.",
 "In 2019, telescopes captured the first real image of one: a glowing ring, 55 million light-years away.",
 "Now, let's fall in. First problem: tidal forces. Gravity pulls your feet harder than your head.",
 "Near a small black hole, that would stretch you apart, long before the edge. Scientists call it spaghettification.",
 "But near a supermassive one, like the giant at the center of our galaxy, you'd cross in one piece.",
 "Now it gets strange. To a friend far away, your clock ticks slower... and slower. Your light fades redder and dimmer, until you seem to freeze at the edge.",
 "But for you, time feels normal. You'd cross the event horizon without feeling a thing.",
 "Because it isn't a surface. It's the point of no return, where escaping would mean moving faster than light.",
 "Past it, every path leads inward. And at the center? No one knows. It's where our physics breaks down.",
]
sp = float(sys.argv[1]) if len(sys.argv) > 1 else 1.1
tot = 0
for i, l in enumerate(LINES):
    s, sr = k.create(l, voice="am_puck", speed=sp, lang="en-us")
    env = np.convolve(np.abs(s), np.ones(240) / 240, "same"); idx = np.where(env > 0.01)[0]
    s = s[max(0, idx[0] - 240):min(len(s), idx[-1] + 1200)]
    sf.write(f"L{i:02d}.wav", s, sr); tot += len(s) / sr; print(i, round(len(s) / sr, 2), len(l.split()), "words")
print("total speech", round(tot, 2))
