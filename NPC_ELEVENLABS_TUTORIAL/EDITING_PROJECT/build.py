"""One command from source recording to verified export package.

    python build.py SOURCE.mp4 PRIVATE_DIR [--skip-ocr] [--only 9x16|16x9] [--no-qc]

PRIVATE_DIR holds everything derived from unmasked pixels (OCR text, private terms). Keep it
outside the repository.

Pipeline: OCR scan -> privacy masks -> resolve EDL anchors -> score + SFX + master ->
render 9:16 and 16:9 -> mux -> SRT -> thumbnails -> QC (incl. every-frame privacy OCR).
"""
import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent
PY = sys.executable


def run(*args):
    print("+", " ".join(str(a) for a in args), flush=True)
    subprocess.run([str(a) for a in args], check=True, cwd=HERE)


def srt(path):
    from timeline import Timeline
    tl = Timeline()

    def ts(t):
        ms = int(round(t * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"

    lines = []
    for i, c in enumerate(sorted(tl.captions, key=lambda c: c["t0"]), 1):
        lines += [str(i), f"{ts(c['t0'])} --> {ts(c['t1'])}", c["text"], ""]
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("private_dir")
    ap.add_argument("--skip-ocr", action="store_true")
    ap.add_argument("--only")
    ap.add_argument("--no-qc", action="store_true")
    a = ap.parse_args()
    priv = Path(a.private_dir)
    if not a.skip_ocr:
        run(PY, "ocr_scan.py", a.src, priv / "ocr")
    run(PY, "privacy.py", a.src, priv / "ocr", priv)
    run(PY, "resolve_edl.py", a.src)
    run(PY, "activity_scan.py", a.src, ROOT / "ANALYSIS" / "activity.json")
    mix = ROOT / "AUDIO" / "NPC_ELEVENLABS_MIX.wav"
    run(PY, "audio.py", mix)
    (ROOT / "FINAL").mkdir(exist_ok=True)
    for layout in ([a.only] if a.only else ["9x16", "16x9"]):
        silent = ROOT / "PREVIEW" / f".video_{layout}.mp4"
        final = ROOT / "FINAL" / f"NPC_ELEVENLABS_FINAL_{layout}.mp4"
        run(PY, "render.py", a.src, "--layout", layout, "--out", silent)
        run("ffmpeg", "-v", "error", "-y", "-i", silent, "-i", mix, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
            "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-shortest", "-movflags", "+faststart", final)
        silent.unlink()
        if not a.no_qc:
            run(PY, "qc.py", final, priv, ROOT / "ANALYSIS" / f"qc_{layout}.json")
    srt(ROOT / "CAPTIONS" / "NPC_ELEVENLABS_CAPTIONS.srt")
    run(PY, "thumbnail.py", a.src)


if __name__ == "__main__":
    main()
