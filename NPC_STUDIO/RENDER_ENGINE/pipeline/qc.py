"""Automated QC for a rendered NPC video.

    python qc.py <video.mp4> <timeline.json> [--expect-voice]

Checks container/stream specs with ffprobe, frame count vs timeline, A/V
duration match, unintended black or frozen stretches, audio clipping and
loudness. Exits non-zero on failure and writes <video>.qc.json.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


def sh(cmd: list[str]) -> str:
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.stdout + p.stderr


def main(video: Path, timeline_path: Path, expect_voice: bool) -> None:
    tl = json.loads(timeline_path.read_text())
    probe = json.loads(sh(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", "-count_frames", str(video)]))
    v = next(s for s in probe["streams"] if s["codec_type"] == "video")
    a = next((s for s in probe["streams"] if s["codec_type"] == "audio"), None)
    fps_num, fps_den = map(int, v["r_frame_rate"].split("/"))
    fps = fps_num / fps_den
    frames = int(v.get("nb_read_frames", 0))
    vdur = float(v.get("duration", probe["format"]["duration"]))
    adur = float(a["duration"]) if a else 0.0

    checks: dict[str, tuple[bool, str]] = {}
    checks["codec_h264"] = (v["codec_name"] == "h264", v["codec_name"])
    checks["pix_fmt"] = (v["pix_fmt"] == "yuv420p", v["pix_fmt"])
    checks["fps"] = (abs(fps - tl["fps"]) < 0.01, f"{fps:.3f}")
    full = v["width"] == tl["width"]
    checks["resolution"] = (v["width"] * 16 == v["height"] * 9, f"{v['width']}x{v['height']}" + ("" if full else " (preview)"))
    checks["frame_count"] = (abs(frames - tl["durationInFrames"]) <= 1, f"{frames} / {tl['durationInFrames']}")
    checks["audio_present"] = (a is not None and a["codec_name"] == "aac" and int(a["channels"]) == 2 and a["sample_rate"] == "48000",
                               f"{a['codec_name']} {a['channels']}ch {a['sample_rate']}Hz" if a else "none")
    checks["av_sync_duration"] = (abs(vdur - adur) < 0.05, f"video {vdur:.3f}s audio {adur:.3f}s")

    # Black frames: only the designed opening darkness (first second) may be black.
    log = sh(["ffmpeg", "-hide_banner", "-i", str(video), "-vf", "blackdetect=d=0.25:pix_th=0.04", "-an", "-f", "null", "-"])
    blacks = [(float(m.group(1)), float(m.group(2))) for m in re.finditer(r"black_start:([\d.]+) black_end:([\d.]+)", log)]
    bad_black = [b for b in blacks if b[1] > 1.0]
    checks["no_unintended_black"] = (not bad_black, str(blacks))

    # Frozen stretches (dropped/duplicated frames or a stalled scene).
    log = sh(["ffmpeg", "-hide_banner", "-i", str(video), "-vf", "freezedetect=n=0.0005:d=0.6", "-an", "-f", "null", "-"])
    freezes = re.findall(r"freeze_start: ([\d.]+)", log)
    checks["no_freezes"] = (not freezes, str(freezes))

    # Loudness and clipping.
    log = sh(["ffmpeg", "-hide_banner", "-i", str(video), "-af", "ebur128=peak=true", "-vn", "-f", "null", "-"])
    lufs = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", log)[-1])
    peak = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", log)[-1])
    checks["loudness"] = (-17 <= lufs <= -12, f"{lufs} LUFS")
    checks["no_clipping"] = (peak <= -0.5, f"true peak {peak} dBFS")

    checks["narration_voice"] = (tl["voiced"] or not expect_voice,
                                 "NPC_VOICE_V1" if tl["voiced"] else "absent (pre-voice cut)")

    ok = all(passed for passed, _ in checks.values())
    for k, (passed, detail) in checks.items():
        print(f"  [{'PASS' if passed else 'FAIL'}] {k:22s} {detail}")
    report = {"video": video.name, "pass": ok, "checks": {k: {"pass": p, "detail": d} for k, (p, d) in checks.items()}}
    video.with_suffix(".qc.json").write_text(json.dumps(report, indent=2))
    print("QC PASS" if ok else "QC FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), "--expect-voice" in sys.argv)
