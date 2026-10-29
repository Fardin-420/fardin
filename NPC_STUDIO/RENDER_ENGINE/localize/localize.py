"""Localize an existing short video: new narration, new burned-in captions, new music.

    python RENDER_ENGINE/localize/localize.py PROJECTS/RICH_STONES_EN

The footage is kept. The band holding the original captions is softly blurred,
and new captions are drawn over it in the same stacked rounded-box style. Each
segment is spoken at its original start time (Kokoro TTS). A line that runs
long is spoken faster, up to max_speed, and anything still left over pushes the
following lines later. If the narration outlasts the footage, the last frame is
held. The original audio is replaced by the narration over a soft score.

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

    v = script["voice"]
    k = Kokoro(str(MODEL_DIR / "kokoro-v1.0.onnx"), str(MODEL_DIR / "voices-v1.0.bin"))
    style = sum(k.get_voice_style(n) * w for n, w in v["blend"].items())
    segs = script["segments"]
    placed, cursor = [], 0.0
    for i, s in enumerate(segs):
        start = max(s["start"], cursor)
        slot = (segs[i + 1]["start"] if i + 1 < len(segs) else start + 3.0) - start - 0.08
        speed = v["speed"]
        while True:
            wav, sr = k.create(s.get("say", s["text"]), voice=style, speed=speed, lang=v.get("lang", "en-us"))
            wav = resample_poly(trim(wav, sr), SR, sr).astype(np.float64)
            dur = len(wav) / SR
            if dur <= slot or speed >= v["max_speed"]:
                break
            speed = min(v["max_speed"], speed * dur / slot + 0.01)
        placed.append({"text": s["text"], "start": round(start, 3), "end": round(start + dur, 3), "speed": round(speed, 3), "wav": wav})
        print(f"{start:6.2f}–{start + dur:6.2f}  x{speed:.2f}  {s['text']}")
        cursor = start + dur + 0.12
    total = placed[-1]["end"] + 0.6
    voice = np.zeros(secs(total))
    for p in placed:
        i = secs(p["start"])
        voice[i:i + len(p["wav"])] += p["wav"]
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


# ───────────────────────── captions ─────────────────────────

def wrap(text: str, font: ImageFont.FreeTypeFont, maxw: int) -> list[str]:
    lines, cur = [], ""
    for w in text.split():
        trial = f"{cur} {w}".strip()
        if font.getlength(trial) <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    return lines + [cur]


def caption_png(text: str, out: Path, cy: int) -> None:
    """Stacked rounded boxes, one per line, blue gradient, white outlined text."""
    size = 80
    font = ImageFont.truetype(str(FONT), size)
    lines = wrap(text, font, 900)
    if len(lines) > 2:
        size = 68
        font = ImageFont.truetype(str(FONT), size)
        lines = wrap(text, font, 960)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lh = int(size * 1.32)
    top = cy - lh * len(lines) // 2
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    boxes = []
    for i, ln in enumerate(lines):
        tw = font.getlength(ln)
        x0, x1 = int(W / 2 - tw / 2 - 30), int(W / 2 + tw / 2 + 30)
        y0, y1 = top + i * lh - 6, top + (i + 1) * lh + 4
        boxes.append((x0, y0, x1, y1))
        ImageDraw.Draw(shadow).rounded_rectangle((x0, y0 + 8, x1, y1 + 8), 22, fill=(0, 0, 0, 110))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(10)))
    for x0, y0, x1, y1 in boxes:
        grad = Image.new("RGBA", (x1 - x0, y1 - y0))
        gd = ImageDraw.Draw(grad)
        for y in range(y1 - y0):
            k = y / max(1, y1 - y0 - 1)
            gd.line([(0, y), (x1 - x0, y)], fill=(int(46 - 18 * k), int(140 - 40 * k), int(206 - 50 * k), 245))
        mask = Image.new("L", grad.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, grad.size[0] - 1, grad.size[1] - 1), 22, fill=255)
        img.paste(grad, (x0, y0), mask)
    d = ImageDraw.Draw(img)
    for i, ln in enumerate(lines):
        d.text((W / 2, top + i * lh + lh / 2), ln, font=font, anchor="mm", fill="white", stroke_width=5, stroke_fill=(10, 20, 35))
    img.save(out)


def band_mask(band: dict, out: Path) -> None:
    m = Image.new("L", (W, band["h"]), 255)
    d = ImageDraw.Draw(m)
    feather = 40
    for y in range(feather):
        a = int(255 * y / feather)
        d.line([(0, y), (W, y)], fill=a)
        d.line([(0, band["h"] - 1 - y), (W, band["h"] - 1 - y)], fill=a)
    m.save(out)


# ───────────────────────── assemble ─────────────────────────

def main(project: Path) -> None:
    script = json.loads((project / "source" / "script.json").read_text())
    src = project / script["source_video"]
    work = project / "previews" / "localize"
    work.mkdir(parents=True, exist_ok=True)
    vid_dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(src)]))

    voice, placed = narrate(script)
    dur = max(vid_dur, len(voice) / SR)
    voice = np.pad(voice, (0, max(0, secs(dur) - len(voice))))[: secs(dur)]
    bed, _ = sidechain(voice, soft_score(dur), np.zeros((secs(dur), 2)))
    mix = bed + pan(voice, 0)
    meter = pyln.Meter(SR)
    mix *= 10 ** ((-14 - meter.integrated_loudness(mix)) / 20)
    mix = true_peak_limit(mix, -1.5)
    sf.write(work / "mix.wav", mix.astype(np.float32), SR)
    (project / "source" / "timeline.json").write_text(json.dumps(
        {"duration": round(dur, 3), "voice": "+".join(script["voice"]["blend"]), "segments": [{k: v for k, v in p.items() if k != "wav"} for p in placed]}, indent=1))

    band = script["caption_band"]
    band_mask(band, work / "band_mask.png")
    caps = []
    for i, p in enumerate(placed):
        f = work / f"cap{i:02d}.png"
        caption_png(p["text"], f, script["caption_y"])
        end = placed[i + 1]["start"] if i + 1 < len(placed) else dur
        caps.append((f, p["start"], end))

    inputs = ["-i", str(src), "-i", str(work / "band_mask.png")]
    for f, _, _ in caps:
        inputs += ["-i", str(f)]
    inputs += ["-i", str(work / "mix.wav")]
    hold = max(0.0, dur - vid_dur)
    g = [f"[0:v]scale={W}:{H}:flags=lanczos,fps={FPS},tpad=stop_mode=clone:stop_duration={hold:.3f},split[base][b2]",
         f"[b2]crop={W}:{band['h']}:0:{band['y']},gblur=sigma=28,eq=brightness=-0.06[bl]",
         "[1:v]format=gray[m]", "[bl][m]alphamerge[blm]", f"[base][blm]overlay=0:{band['y']}[v0]"]
    for i, (_, a, b) in enumerate(caps):
        g.append(f"[v{i}][{i + 2}:v]overlay=0:0:enable='between(t,{a:.3f},{b:.3f})'[v{i + 1}]")
    out = project / "final" / f"{project.name}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(g),
                    "-map", f"[v{len(caps)}]", "-map", f"{len(caps) + 2}:a", "-t", f"{dur:.3f}",
                    "-c:v", "libx264", "-crf", "18", "-preset", "slow", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart", str(out)], check=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(out), "-vf", "fps=1/2.5,scale=216:-1,tile=7x2",
                    "-frames:v", "1", str(project / "previews" / "contact_sheet.jpg")], check=True)
    print(f"{out}  {dur:.2f}s  {meter.integrated_loudness(mix):.1f} LUFS")


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
