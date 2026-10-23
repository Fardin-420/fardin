"""Final-file validation with ffprobe/ffmpeg: format, duration, loudness, black frames, silences, crop, clipping."""
import json
import re
import subprocess


def _ff(args):
    return subprocess.run(["ffmpeg", "-hide_banner", "-nostats"] + args, capture_output=True, text=True).stderr


def validate(path, cfg, dur_range=(35.0, 50.0)):
    e = cfg["export"]
    pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
                                   capture_output=True, text=True, check=True).stdout)
    v = next(s for s in pr["streams"] if s["codec_type"] == "video")
    a = next((s for s in pr["streams"] if s["codec_type"] == "audio"), None)
    dur = float(pr["format"]["duration"])
    r = {}
    r["container"] = (pr["format"]["format_name"].startswith("mov,mp4"), pr["format"]["format_name"])
    r["video_codec"] = (v["codec_name"] == "h264", f"{v['codec_name']} {v.get('profile')}")
    r["resolution"] = ((v["width"], v["height"]) == (e["width"], e["height"]), f"{v['width']}x{v['height']}")
    r["fps"] = (v["r_frame_rate"] == f"{e['fps']}/1", v["r_frame_rate"])
    r["pix_fmt"] = (v["pix_fmt"] == "yuv420p", v["pix_fmt"])
    r["duration"] = (dur_range[0] <= dur <= dur_range[1], f"{dur:.3f}s")
    r["audio"] = (a is not None and a["codec_name"] == "aac", f"{a['codec_name']} {a['sample_rate']}Hz {a['channels']}ch" if a else "none")
    r["bitrate"] = (int(pr["format"]["bit_rate"]) > 8_000_000, f"{int(pr['format']['bit_rate']) / 1e6:.1f} Mb/s")
    lo = _ff(["-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"])
    I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", lo)[-1]); tp = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", lo)[-1])
    r["loudness"] = (abs(I - e["loudness_lufs"]) <= 1.0, f"{I} LUFS")
    r["true_peak"] = (tp <= e["true_peak"] + 0.3, f"{tp} dBFS")
    bl = _ff(["-i", path, "-vf", "blackdetect=d=0.25:pix_th=0.06", "-an", "-f", "null", "-"])
    blacks = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", bl)
    r["black_frames"] = (len(blacks) == 0, blacks or "none")
    si = _ff(["-i", path, "-af", "silencedetect=n=-45dB:d=1.0", "-vn", "-f", "null", "-"])
    sil = re.findall(r"silence_start: ([\d.]+)", si)
    r["silence_gaps"] = (len(sil) == 0, sil or "none")
    cr = _ff(["-i", path, "-vf", "cropdetect=24:2:0", "-an", "-f", "null", "-"])
    crops = re.findall(r"crop=(\d+:\d+:\d+:\d+)", cr)
    full = sum(1 for c in crops if c.startswith(f"{e['width']}:{e['height']}"))
    r["no_black_bars"] = (crops and full / len(crops) > 0.98, f"{full}/{len(crops)} frames full-frame")
    vol = _ff(["-i", path, "-af", "astats=metadata=0", "-vn", "-f", "null", "-"])
    clipped = sum(int(x) for x in re.findall(r"Number of clipped samples: (\d+)", vol)) if "clipped" in vol else 0
    r["clipping"] = (clipped == 0, f"{clipped} clipped samples")
    return r


def report(r):
    return "\n".join(f"{'PASS' if ok else 'FAIL'}  {k:<14} {val}" for k, (ok, val) in r.items())
