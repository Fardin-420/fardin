"""Quality checks: resolution, duration, A/V sync, silent gaps, frozen frames."""
import json
import re
import subprocess


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def report(path, expect_dur=None, check_len=True, min_len=480, max_len=600, w=1920, h=1080):
    p = probe(path)
    v = [s for s in p["streams"] if s["codec_type"] == "video"][0]
    a = [s for s in p["streams"] if s["codec_type"] == "audio"]
    vd = float(v.get("duration", p["format"]["duration"]))
    ad = float(a[0].get("duration", 0)) if a else 0
    ok = True
    lines = [f"QC {path}", f"  video {v['width']}x{v['height']} {v['codec_name']} {v.get('pix_fmt')} {v['r_frame_rate']}  dur {vd:.2f}s",
             f"  audio {a[0]['codec_name'] if a else 'NONE'} dur {ad:.2f}s  |A-V| {abs(vd - ad):.3f}s"]
    if (v["width"], v["height"]) != (w, h):
        ok = False; lines.append("  FAIL resolution")
    if not a or abs(vd - ad) > 0.15:
        ok = False; lines.append("  FAIL audio/video length mismatch")
    if check_len and not (min_len <= vd <= max_len):
        ok = False; lines.append(f"  FAIL duration {vd / 60:.2f} min outside {min_len / 60:.0f}-{max_len / 60:.0f} min")
    # silence: gaps > 2 s below -50 dB
    sil = subprocess.run(["ffmpeg", "-v", "info", "-i", path, "-af", "silencedetect=noise=-50dB:d=2", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    gaps = re.findall(r"silence_duration: ([\d.]+)", sil)
    lines.append(f"  silent gaps >2s: {len(gaps)} {gaps[:5]}")
    if gaps:
        ok = False
    fr = subprocess.run(["ffmpeg", "-v", "info", "-i", path, "-vf", "freezedetect=n=0.0008:d=3", "-map", "0:v", "-f", "null", "-"],
                        capture_output=True, text=True).stderr
    freezes = re.findall(r"freeze_start: ([\d.]+)", fr)
    lines.append(f"  frozen stretches >3s: {len(freezes)} {freezes[:8]}")
    if freezes:
        ok = False
    lines.append("  RESULT: " + ("PASS" if ok else "CHECK ABOVE"))
    print("\n".join(lines), flush=True)
    return ok
