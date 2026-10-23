"""Builds an authorized (self-made) 16:9 test source for the clip pipeline.

Two-voice conversation synthesized locally with Kokoro-82M (Apache-2.0); visuals are a public-domain NASA
portrait (scikit-image `astronaut`) staged as a two-camera podcast with wide/close-up shot changes,
slow camera drift and sensor grain. Everything here is original or public domain → rights: MINE.

    .venv/bin/python tests/make_test_source.py OUT.mp4
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[2]
KOKORO = ROOT / "VOICE_ENGINE" / "models" / "kokoro"
SR = 24000
FPS = 30

SCRIPT = [
    ("H", "Okay, so you lost everything at twenty six. What actually happened?"),
    ("G", "I had a bakery. Forty thousand dollars of savings, a loan from my dad, and a lease I definitely should not have signed."),
    ("G", "And for eight months it worked. Lines out the door. I thought I was a genius."),
    ("H", "So what changed?"),
    ("G", "A chain opened across the street and sold croissants for a dollar. Mine were four. In six weeks my revenue dropped by seventy percent."),
    ("H", "Seventy percent? That's brutal."),
    ("G", "It was terrifying. I remember sitting in the walk-in fridge, crying, because it was the only place nobody could hear me."),
    ("G", "And here's the part nobody tells you. The business didn't fail because of the chain. It failed because I never knew my numbers."),
    ("H", "What do you mean you didn't know your numbers?"),
    ("G", "I didn't know that every croissant cost me two dollars and ten cents to make. I was proud of my margins and I didn't even have margins."),
    ("H", "That's honestly the most common mistake I hear on this show."),
    ("G", "It is! Most people think they have a sales problem. Ninety percent of the time they have a pricing problem."),
    ("H", "Okay, so you close the bakery. Then what?"),
    ("G", "Then I moved back in with my parents. Twenty seven years old, sleeping in my childhood bedroom, with glow in the dark stars on the ceiling."),
    ("H", "No way. The stars were still up?"),
    ("G", "The stars were still up. My mom refused to take them down. She said I would need them again someday. She was right, by the way."),
    ("H", "So how do you go from that bedroom to where you are now?"),
    ("G", "I started teaching other bakers how to price. One spreadsheet. I sold it for nine dollars on a Tuesday night, and by Friday I had made eleven thousand dollars."),
    ("H", "Eleven thousand dollars from a spreadsheet?"),
    ("G", "From a spreadsheet. That's when I realized the thing that broke me was the thing other people needed most."),
    ("H", "If someone is watching this and their business is struggling right now, what should they do tonight?"),
    ("G", "Write down what one sale actually costs you. Not what you think. What it actually costs. If you can't answer that in one minute, stop spending money until you can."),
    ("G", "Because you can survive a bad month. You cannot survive not knowing why it was bad."),
    ("H", "Let's talk about fear, because I think a lot of people are scared to raise their prices."),
    ("G", "Oh, I was terrified. The first time I raised my price from nine to forty nine dollars, I thought everyone would leave."),
    ("H", "And did they?"),
    ("G", "Sales went up. Not down. Up. When it was cheap, people didn't trust it. When it was forty nine dollars, they assumed it worked."),
    ("H", "That is wild. Cheaper made it look worse."),
    ("G", "Cheap tells people you don't believe in it either. Price is a message, not just a number."),
    ("H", "What's the biggest lie people believe about starting a business?"),
    ("G", "That you need a great idea. You don't. My idea was a spreadsheet. You need a painful problem and the guts to charge for fixing it."),
    ("H", "Last question. Would you open the bakery again?"),
    ("G", "Honestly? Yes. But this time I would know my numbers on day one. And I would put the stars in the shop."),
]
VOICES = {"H": ("am_michael", 1.02), "G": ("af_heart", 1.0)}


def synth() -> tuple[np.ndarray, list[tuple[str, float, float]]]:
    from kokoro_onnx import Kokoro
    k = Kokoro(str(KOKORO / "kokoro-v1.0.onnx"), str(KOKORO / "voices-v1.0.bin"))
    rng = np.random.default_rng(3)
    out, spans, t = [np.zeros(int(0.5 * SR), np.float32)], [], 0.5
    for who, text in SCRIPT:
        v, sp = VOICES[who]
        a, sr = k.create(text, voice=v, speed=sp, lang="en-us")
        assert sr == SR
        a = a.astype(np.float32) * (0.9 if who == "H" else 1.0)
        spans.append((who, t, t + len(a) / SR))
        gap = float(rng.uniform(0.25, 0.7))
        out += [a, np.zeros(int(gap * SR), np.float32)]
        t += len(a) / SR + gap
    return np.concatenate(out), spans


def stage() -> tuple[np.ndarray, dict]:
    from skimage import data
    face = cv2.cvtColor(data.astronaut(), cv2.COLOR_RGB2BGR)
    face = cv2.resize(face, (1000, 1000), interpolation=cv2.INTER_CUBIC)
    guest = cv2.flip(face, 1)
    guest = cv2.convertScaleAbs(guest, alpha=1.0, beta=0)
    guest[..., 2] = cv2.add(guest[..., 2], 18)                     # warmer key light on the guest camera
    canvas = np.zeros((2160, 3840, 3), np.uint8)
    yy, xx = np.mgrid[0:2160, 0:3840]
    canvas[:] = (24, 20, 18)
    glow = np.exp(-(((xx - 1920) / 1500) ** 2 + ((yy - 900) / 900) ** 2))
    canvas = (canvas + (glow[..., None] * np.array([40, 34, 30]))).astype(np.uint8)
    canvas[580:1580, 500:1500] = face
    canvas[580:1580, 2340:3340] = guest
    # face centres in canvas coords (astronaut face ≈ upper-middle of the portrait)
    return canvas, {"H": (1000 + 30, 580 + 330), "G": (2840 - 30, 580 + 330)}


def main(out: Path):
    audio, spans = synth()
    dur = len(audio) / SR
    wav = out.with_suffix(".wav")
    sf.write(wav, audio, SR)
    canvas, centers = stage()
    n = int(dur * FPS)
    # shot list: wide on every 4th line, otherwise close-up on the speaker
    shots = []
    for i, (who, s, e) in enumerate(spans):
        shots.append((s if i else 0.0, "W" if i % 4 == 3 else who))
    rng = np.random.default_rng(1)
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", "1920x1080",
                            "-r", str(FPS), "-i", "-", "-i", str(wav), "-c:v", "libx264", "-preset", "veryfast",
                            "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", str(out)],
                           stdin=subprocess.PIPE)
    si = 0
    for f in range(n):
        t = f / FPS
        while si + 1 < len(shots) and shots[si + 1][0] <= t:
            si += 1
        start, kind = shots[si]
        u = t - start
        if kind == "W":
            cw = 3840 * (0.98 - 0.02 * min(1, u / 6))
            cx, cy = 1920 + 30 * np.sin(u * 0.3), 1080
        else:
            cw = 1900 * (1.0 - 0.05 * min(1, u / 8))
            cx, cy = centers[kind][0] + 40 * np.sin(u * 0.25), centers[kind][1] + 200
        ch = cw * 9 / 16
        s = 1920 / cw
        M = np.float32([[s, 0, 960 - cx * s], [0, s, 540 - cy * s]])
        fr = cv2.warpAffine(canvas, M, (1920, 1080), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)
        grain = rng.integers(-5, 6, (270, 480, 1), dtype=np.int16)
        fr = np.clip(fr.astype(np.int16) + cv2.resize(grain, (1920, 1080))[..., None], 0, 255).astype(np.uint8)
        enc.stdin.write(fr.tobytes())
    enc.stdin.close()
    enc.wait()
    wav.unlink()
    print(f"wrote {out} ({dur:.1f}s)")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
