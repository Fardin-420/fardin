import soundfile as sf, numpy as np
from kokoro_onnx import Kokoro
k = Kokoro("kokoro-v1.0.onnx", "voices-v1.0.bin")
lines = [
 "NASA crashed a spacecraft into an asteroid. On purpose.",
 "In twenty twenty-two, DART flew straight at Dimorphos, at fourteen thousand miles an hour.",
 "Its camera sent back one image every second... until the signal just stopped.",
 "Weeks later, telescopes confirmed it. The asteroid's orbit was thirty-two minutes shorter.",
 "The first time humans ever changed how a celestial body moves.",
]
import sys
voice = sys.argv[1]; speed = float(sys.argv[2])
for i, l in enumerate(lines):
    s, sr = k.create(l, voice=voice, speed=speed, lang="en-us")
    sf.write(f"{voice}_{i}.wav", s, sr)
    print(voice, i, round(len(s)/sr, 2))
