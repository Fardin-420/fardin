"""Concatenate rendered chunks, mux the mastered mix, and encode the deliverables.

    .venv/bin/python scripts/finalize.py

out/master_1080p.mp4   H.264 High (CRF 16 from Remotion, stream-copied) + AAC 48 kHz 320 kbps
out/upload_1080p.mp4   2-pass ≈ 8 Mbps H.264 + AAC 256 kbps, +faststart
out/preview_coldopen.mp4  0:00–1:00 with audio
"""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
CH = OUT / "chunks"
AUDIO = ROOT / "audio" / "mix_master.wav"


def run(*a):
    print("$", " ".join(map(str, a)))
    subprocess.run(list(map(str, a)), check=True)


def main():
    chunks = sorted(CH.glob("c*.mp4"), key=lambda p: int(p.stem[1:]))
    lst = CH / "list.txt"
    lst.write_text("".join(f"file '{c.name}'\n" for c in chunks))
    video = CH / "video_full.mp4"
    run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", video)
    master = OUT / "master_1080p.mp4"
    run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", video, "-i", AUDIO, "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-ac", "2", "-shortest",
        "-metadata", "title=The 20-Minute Heist", "-movflags", "+faststart", master)
    up = OUT / "upload_1080p.mp4"
    common = ["-c:v", "libx264", "-preset", "slow", "-profile:v", "high", "-pix_fmt", "yuv420p", "-b:v", "8000k",
              "-maxrate", "12000k", "-bufsize", "16000k", "-g", "60", "-bf", "2", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]
    plog = str(CH / "x264pass")
    run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", master, *common, "-pass", "1", "-passlogfile", plog, "-an", "-f", "mp4", "/dev/null")
    run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", master, *common, "-pass", "2", "-passlogfile", plog,
        "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart", up)
    run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", master, "-t", "60", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", OUT / "preview_coldopen.mp4")
    for p in (master, up, OUT / "preview_coldopen.mp4"):
        print(f"{p.name}: {p.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
