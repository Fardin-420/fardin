"""Localize an existing short video: new voices, new burned-in captions, new music.

    python RENDER_ENGINE/localize/localize.py PROJECTS/RICH_STONES_EN

The footage is kept. The original caption boxes are found in every frame (by
their box colour, inside `caption_search`) and repainted as clean boxes of the
same style carrying the new text, so no trace of the old captions remains. Each
segment is spoken by its `speaker` (a Kokoro voice from `voices`) at its original
start time. A line that runs long is spoken faster, up to max_speed, and
anything still left over pushes the following lines later. If the narration
outlasts the footage, the last frame is held. The original audio is replaced by
the narration over a soft score.

Writes final/<NAME>.mp4 plus previews/contact_sheet.jpg.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.ndimage import binary_closing, binary_dilation
from scipy.signal import resample_poly

STUDIO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(STUDIO / "SOUND_ENGINE"), str(STUDIO / "VOICE_ENGINE")]

from explainer_narration import MODEL_DIR, trim  # noqa: E402
from sound_engine import IR_HALL, SR, Track, env_ad, lowpass, pan, secs, sidechain, true_peak_limit, tvec, verb  # noqa: E402

W, H, FPS = 1080, 1920, 30
FONT = STUDIO / "BRAND" / "fonts" / "InterDisplay-ExtraBold.otf"


# ───────────────────────── narration ─────────────────────────

def narrate(script: dict) -> tuple[np.ndarray, list[dict]]:
    from kokoro_onnx import Kokoro

    k = Kokoro(str(MODEL_DIR / "kokoro-v1.0.onnx"), str(MODEL_DIR / "voices-v1.0.bin"))
    voices = {name: (sum(k.get_voice_style(n) * w for n, w in v["blend"].items()), v) for name, v in script["voices"].items()}
    segs = script["segments"]
    placed, cursor = [], 0.0
    for i, s in enumerate(segs):
        style, v = voices[s["speaker"]]
        start = max(s["start"], cursor)
        slot = (segs[i + 1]["start"] if i + 1 < len(segs) else start + 3.0) - start - 0.08
        speed = v["speed"]
        while True:
            wav, sr = k.create(s.get("say", s["text"]), voice=style, speed=speed, lang=v.get("lang", "en-us"))
            wav = resample_poly(trim(wav, sr), SR, sr).astype(np.float64) * 10 ** (v.get("gain_db", 0) / 20)
            dur = len(wav) / SR
            if dur <= slot or speed >= v["max_speed"]:
                break
            speed = min(v["max_speed"], speed * dur / slot + 0.01)
        placed.append({"text": s["text"], "speaker": s["speaker"], "start": round(start, 3), "end": round(start + dur, 3),
                       "speed": round(speed, 3), "wav": wav, "pan": v.get("pan", 0.0)})
        print(f"{start:6.2f}–{start + dur:6.2f}  x{speed:.2f}  {s['speaker']:8s} {s['text']}")
        # a change of speaker gets a slightly longer breath, like a real exchange
        cursor = start + dur + 0.12
    total = placed[-1]["end"] + 0.6
    voice = np.zeros((secs(total), 2))
    for p in placed:
        i = secs(p["start"])
        voice[i:i + len(p["wav"])] += pan(p["wav"], p["pan"])
    voice *= 0.89 / np.abs(voice).max()
    return voice, placed


# ───────────────────────── score ─────────────────────────

def soft_score(dur: float) -> np.ndarray:
    """Warm pad (Cmaj7 – Am7 – Fmaj7 – G6) with a quiet bell arpeggio."""
    chords = [[48, 55, 59, 64], [45, 52, 55, 60], [41, 48, 52, 57], [43, 50, 52, 59]]
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    bar = 2.4
    out = Track(dur + bar * 2)
    t, i = 0.0, 0
    while t < dur:
        ch = chords[i % 4]
        tt = tvec(bar * 1.25)
        pad = sum(np.sin(2 * np.pi * hz(m) * d * tt) for m in ch for d in (1.0, 1.003))
        pad = lowpass(pad, 1400, 2) * env_ad(len(tt), 0.8, bar * 1.25, 1.2) * 0.05
        out.add(t, pan(pad, 0))
        for n in range(8):
            m = ch[n % 4] + 12 * (1 + (n // 4))
            nt = tvec(1.2)
            bell = (np.sin(2 * np.pi * hz(m) * nt) + 0.3 * np.sin(2 * np.pi * hz(m) * 2.76 * nt)) * np.exp(-nt * 4) * 0.035
            out.add(t + n * bar / 8, pan(bell, -0.4 + 0.8 * (n % 2)))
        t += bar
        i += 1
    bed = verb(out.buf[: secs(dur)], IR_HALL, 0.35)
    n = len(bed)
    fade = np.minimum(1, np.minimum(np.arange(n) / secs(1.2), (n - np.arange(n)) / secs(1.5)))
    return bed * fade[:, None]


# ───────────────────────── caption repaint ─────────────────────────

def read_frames(src: Path) -> np.ndarray:
    w, h = map(int, subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                                             "-of", "csv=p=0", str(src)]).decode().strip().split(","))
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(src), "-vf", f"fps={FPS}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)


def box_mask(frame: np.ndarray, y0: int, y1: int) -> np.ndarray:
    """Pixels of the original caption box (its blue fill) plus the text inside it."""
    f = frame[y0:y1].astype(int)
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    blue = (b - r > 60) & (g - r > 35) & (b - g > 22) & (b > 105) & (r < 110)
    rows = blue.sum(axis=1) > 25          # a caption row is a long blue run, not a stray crystal
    m = np.zeros_like(blue)
    for y in np.where(rows)[0]:
        xs = np.where(blue[y])[0]
        m[y, xs.min():xs.max() + 1] = True
    return binary_closing(m, iterations=4)


def segment_frames(frames: np.ndarray, search: tuple[int, int], starts: list[float]) -> list[int]:
    """Exact frame where each caption changes: the biggest jump in the caption band near each nominal start."""
    y0, y1 = search
    band = frames[:, y0:y1, :, :].mean(axis=3)
    diff = np.r_[0, np.abs(np.diff(band, axis=0)).mean(axis=(1, 2))]
    cuts = [0]
    for t in starts[1:]:
        c = int(round(t * FPS))
        lo, hi = max(1, c - 10), min(len(frames) - 1, c + 10)
        cuts.append(lo + int(np.argmax(diff[lo:hi + 1])))
    return cuts


def cover_shape(frames: np.ndarray, a: int, b: int, search: tuple[int, int]) -> np.ndarray:
    """Union of the caption box over a segment, slightly grown, in source pixels."""
    y0, y1 = search
    u = np.zeros((y1 - y0, frames.shape[2]), bool)
    for f in range(a, b, 2):
        u |= box_mask(frames[f], y0, y1)
    full = np.zeros(frames.shape[1:3], bool)
    full[y0:y1] = binary_dilation(u, iterations=4)
    return full


def wrap(text: str, font: ImageFont.FreeTypeFont, maxw: int) -> list[str]:
    """Greedy wrap, then rebalance two-line captions so no line is a lone word."""
    lines, cur = [], ""
    for w in text.split():
        trial = f"{cur} {w}".strip()
        if font.getlength(trial) <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    if len(lines) == 2:
        words = text.split()
        splits = [(" ".join(words[:i]), " ".join(words[i:])) for i in range(1, len(words))]
        lines = list(min(splits, key=lambda ab: max(font.getlength(ab[0]), font.getlength(ab[1]))))
    return lines


def gradient_fill(mask: Image.Image) -> Image.Image:
    """Caption-box blue, lighter at the top of each box row."""
    m = np.array(mask) > 0
    out = np.zeros((*m.shape, 4), np.uint8)
    ys = np.where(m.any(axis=1))[0]
    if not len(ys):
        return Image.fromarray(out)
    # each run of rows is one box line; shade it top to bottom
    runs = np.split(ys, np.where(np.diff(ys) > 1)[0] + 1)
    for run in runs:
        for i, y in enumerate(run):
            k = i / max(1, len(run) - 1)
            out[y, m[y]] = (int(52 - 22 * k), int(138 - 34 * k), int(196 - 42 * k), 255)
    return Image.fromarray(out)


def caption_png(text: str, cover: np.ndarray, out: Path) -> None:
    """Repaint the old box (scaled to output size) and set the new text on it, extending boxes where the text is wider."""
    size = 68
    font = ImageFont.truetype(str(FONT), size)
    lines = wrap(text, font, 900)
    if len(lines) > 2:
        size = 58
        font = ImageFont.truetype(str(FONT), size)
        lines = wrap(text, font, 940)
    big = Image.fromarray((cover * 255).astype(np.uint8)).resize((W, H), Image.NEAREST)
    ys = np.where(np.array(big).any(axis=1))[0]
    cy = (ys.min() + ys.max()) / 2 if len(ys) else H * 0.72
    lh = int(size * 1.62)
    top = cy - lh * len(lines) / 2
    mask = big.copy()
    d = ImageDraw.Draw(mask)
    for i, ln in enumerate(lines):
        tw = font.getlength(ln)
        d.rounded_rectangle((W / 2 - tw / 2 - 30, top + i * lh + 2, W / 2 + tw / 2 + 30, top + (i + 1) * lh - 2), 24, fill=255)
    mask = mask.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(1.2))
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fill = gradient_fill(mask.point(lambda v: 255 if v > 127 else 0))
    fill.putalpha(mask)
    img.alpha_composite(fill)
    dr = ImageDraw.Draw(img)
    for i, ln in enumerate(lines):
        dr.text((W / 2, top + i * lh + lh / 2), ln, font=font, anchor="mm", fill="white", stroke_width=5, stroke_fill=(8, 20, 34))
    img.save(out)


# ───────────────────────── assemble ─────────────────────────

def main(project: Path) -> None:
    script = json.loads((project / "source" / "script.json").read_text())
    src = project / script["source_video"]
    work = project / "previews" / "localize"
    work.mkdir(parents=True, exist_ok=True)
    frames = read_frames(src)
    vid_dur = len(frames) / FPS

    voice, placed = narrate(script)
    dur = max(vid_dur, len(voice) / SR)
    voice = np.pad(voice, ((0, max(0, secs(dur) - len(voice))), (0, 0)))[: secs(dur)]
    bed, _ = sidechain(voice.mean(axis=1), soft_score(dur), np.zeros((secs(dur), 2)))
    mix = bed + voice
    meter = pyln.Meter(SR)
    mix *= 10 ** ((-14 - meter.integrated_loudness(mix)) / 20)
    mix = true_peak_limit(mix, -1.5)
    mix = true_peak_limit(mix * 10 ** ((-14 - meter.integrated_loudness(mix)) / 20), -1.5)  # limiter took some level; restore it
    sf.write(work / "mix.wav", mix.astype(np.float32), SR)

    # Captions follow the original caption changes so every old box is always covered.
    search = tuple(script["caption_search"])
    cuts = segment_frames(frames, search, [s["start"] for s in script["segments"]]) + [len(frames)]
    caps = []
    for i, p in enumerate(placed):
        f = work / f"cap{i:02d}.png"
        caption_png(p["text"], cover_shape(frames, cuts[i], cuts[i + 1], search), f)
        a = cuts[i] / FPS
        b = cuts[i + 1] / FPS if i + 1 < len(placed) else dur + 1
        caps.append((f, a, b))
    (project / "source" / "timeline.json").write_text(json.dumps(
        {"duration": round(dur, 3), "voices": {k: "+".join(v["blend"]) for k, v in script["voices"].items()},
         "segments": [{**{k: v for k, v in p.items() if k not in ("wav", "pan")}, "caption": [round(c[1], 3), round(min(c[2], dur), 3)]}
                      for p, c in zip(placed, caps)]}, indent=1))

    inputs = ["-i", str(src)]
    for f, _, _ in caps:
        inputs += ["-i", str(f)]
    inputs += ["-i", str(work / "mix.wav")]
    hold = max(0.0, dur - vid_dur)
    g = [f"[0:v]scale={W}:{H}:flags=lanczos,fps={FPS},tpad=stop_mode=clone:stop_duration={hold:.3f}[v0]"]
    for i, (_, a, b) in enumerate(caps):
        # frame-exact: shown from the frame the old caption appears until the frame before it changes
        g.append(f"[v{i}][{i + 1}:v]overlay=0:0:enable='gte(n,{round(a * FPS)})*lt(n,{round(b * FPS)})'[v{i + 1}]")
    out = project / "final" / f"{project.name}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(g),
                    "-map", f"[v{len(caps)}]", "-map", f"{len(caps) + 1}:a", "-t", f"{dur:.3f}",
                    "-c:v", "libx264", "-crf", "18", "-preset", "slow", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart", str(out)], check=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(out), "-vf", "fps=1/2.5,scale=216:-1,tile=7x2",
                    "-frames:v", "1", str(project / "previews" / "contact_sheet.jpg")], check=True)
    print(f"{out}  {dur:.2f}s  {meter.integrated_loudness(mix):.1f} LUFS")


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
