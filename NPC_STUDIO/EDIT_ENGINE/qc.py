"""Delivery QC for a beat-synced edit.

    python qc.py <project> <video.mp4>

Checks, all measured on the delivered file:
  * container/streams: H.264 High, yuv420p, 1080x1920, 60 fps, exact frame count; AAC 48 kHz stereo
  * A/V alignment: the MP4 audio cross-correlated against the master mix (must be 0 +- 1 ms)
  * impact sync: at every key musical impact, the frame with the largest picture change must be
    within one frame of the audio onset frame from the event map
  * loudness / true peak (ffmpeg ebur128), no accidental silences in the soundtrack
  * black frames only where designed (opening dark, pre-drop pause, final fade); no freezes
  * channel logo appears only in the final sequence (template correlation at the logo position)
  * copy: every on-screen string, spelled as specified; no forbidden names anywhere in the project
Writes <video>.qc.json and exits non-zero on failure.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

sys.path.insert(0, str(Path(__file__).parent))
from analyze_music import Curves  # noqa: E402

REQUIRED_TEXT = ["THEY SEE TWO.", "CYBERWOLF", "THE ONE WHO HOLDS THE LINE.", "THE ONE WHO MOVES IN SILENCE.",
                 "DIFFERENT MINDS.", "SAME CODE.", "UNBREAKABLE", "LOYALTY.", "WHEN ONE GOES SILENT...",
                 "THE OTHER HOLDS THE LINE.", "NO BACKUP.", "NO RETREAT.", "JUST TWO.", "TWO SHADOWS.", "ONE ARMY.",
                 "NPC × CYBERWOLF", "BROTHERS. NOT JUST ADMINS.", "TWO MEN. ONE LEGACY."]
FORBIDDEN = ["fardin"]


def sh(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.stdout + p.stderr


def frames_gray(video, t0, t1, w=136, h=240):
    """Decoded frames in [t0, t1) as small grey images (frame-accurate seek)."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.4f}", "-i", str(video), "-t", f"{t1 - t0:.4f}",
                          "-vf", f"scale={w}:{h},format=gray", "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)


def main(project: Path, video: Path) -> bool:
    ev = json.loads((project / "source/music_events.json").read_text())
    fps = ev["fps"]
    checks: dict[str, tuple[bool, str]] = {}

    probe = json.loads(sh(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", "-count_frames", str(video)]))
    v = next(s for s in probe["streams"] if s["codec_type"] == "video")
    a = next((s for s in probe["streams"] if s["codec_type"] == "audio"), None)
    num, den = map(int, v["r_frame_rate"].split("/"))
    checks["video_codec"] = (v["codec_name"] == "h264" and v.get("profile") == "High", f"{v['codec_name']} {v.get('profile')}")
    checks["pix_fmt"] = (v["pix_fmt"] == "yuv420p", f"{v['pix_fmt']} {v.get('color_space', '?')}/{v.get('color_range', '?')}")
    checks["resolution"] = ((v["width"], v["height"]) == (1080, 1920), f"{v['width']}x{v['height']}")
    checks["fps"] = (num / den == 60, f"{num}/{den}")
    checks["frame_count"] = (int(v["nb_read_frames"]) == ev["frames"], f"{v['nb_read_frames']} / {ev['frames']}")
    checks["audio_stream"] = (a is not None and a["codec_name"] == "aac" and a["sample_rate"] == "48000" and int(a["channels"]) == 2,
                              f"{a['codec_name']} {a['sample_rate']} Hz {a['channels']} ch {int(a.get('bit_rate', 0)) // 1000} kb/s" if a else "none")
    vdur, adur = float(v["duration"]), float(a["duration"])
    checks["av_duration"] = (abs(vdur - adur) < 1 / fps, f"video {vdur:.3f}s audio {adur:.3f}s")
    checks["duration"] = (20 <= vdur <= 40, f"{vdur:.2f}s")
    checks["bitrate"] = (int(probe["format"]["bit_rate"]) > 12_000_000, f"{int(probe['format']['bit_rate']) / 1e6:.1f} Mb/s")

    # ---- A/V alignment against the master ----
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-f", "f32le", "-ac", "1", "-ar", "48000", "-"], capture_output=True).stdout
    au = np.frombuffer(raw, np.float32)
    mix, _ = sf.read(project / "audio/mix.wav", dtype="float32")
    mix = mix.mean(1)
    seg = slice(20 * 48000, 30 * 48000)
    c = signal.correlate(au[seg], mix[seg], mode="full", method="fft")
    lag = int(np.argmax(c) - (len(mix[seg]) - 1))
    checks["av_alignment"] = (abs(lag) <= 48, f"audio offset {lag / 48:.2f} ms vs master")

    # ---- impact sync: picture change peak vs audio onset frame ----
    cur = Curves(au)
    key = {0: "music entrance / THEY SEE TWO", 8: "drop A / CYBERWOLF", 12: "whip to NPC", 32: "build / NO BACKUP",
           36: "JUST TWO", 40: "THE DROP / TWO SHADOWS", 44: "ONE ARMY", 56: "logo reveal"}
    rows = []
    worst = 0
    for b in ev["beats"]:
        if b["n"] not in key:
            continue
        f = b["frame"]
        g = frames_gray(video, (f - 6) / fps, (f + 7) / fps)
        d = np.abs(np.diff(g, axis=0)).mean(axis=(1, 2))      # change into frame f-5 .. f+6
        f_pic = f - 5 + int(np.argmax(d))
        i = int(b["onset_t"] * 1000)
        w = cur.R[i - 40: i + 41]
        j = int(np.argmax(w))
        k = int(np.argmax(w[: j + 1] >= 0.5 * w[j]))
        onset = (i - 40 + k) / 1000
        f_snd = int(np.ceil(onset * fps - 0.6))
        worst = max(worst, abs(f_pic - f_snd))
        rows.append(f"{key[b['n']]}: audio onset {onset:.3f}s -> f{f_snd}, picture impact f{f_pic} ({f_pic - f_snd:+d})")
    checks["impact_sync"] = (worst <= 1, "; ".join(rows))

    # ---- loudness, peaks, silences ----
    log = sh(["ffmpeg", "-hide_banner", "-i", str(video), "-af", "ebur128=peak=true", "-vn", "-f", "null", "-"])
    lufs = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", log)[-1])
    tp = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", log)[-1])
    checks["loudness"] = (-13.0 <= lufs <= -8.0, f"{lufs} LUFS integrated")
    checks["true_peak"] = (tp <= -0.9, f"{tp} dBTP")
    hop = 4800
    rms = 20 * np.log10(np.sqrt((au[: len(au) // hop * hop].reshape(-1, hop) ** 2).mean(1)) + 1e-9)
    tt = np.arange(len(rms)) * 0.1
    gaps = [round(t, 1) for t, r in zip(tt, rms) if r < -50 and 0.5 < t < ev["duration"] - 2.0]
    checks["no_silent_gaps"] = (not gaps, f"{len(gaps)} silent 100 ms windows" + (f" at {gaps[:6]}" if gaps else ""))

    # ---- black / frozen frames ----
    log = sh(["ffmpeg", "-hide_banner", "-i", str(video), "-vf", "blackdetect=d=0.1:pix_th=0.06:pic_th=0.98", "-an", "-f", "null", "-"])
    blacks = [(float(m.group(1)), float(m.group(2))) for m in re.finditer(r"black_start:([\d.]+) black_end:([\d.]+)", log)]
    B = lambda n: next(x["frame"] for x in ev["beats"] if x["n"] == n) / fps
    allowed = [(0, ev["entrance_t"] + 0.1), (B(39) - 0.05, B(40) + 0.02), (ev["duration"] - 1.6, ev["duration"] + 0.1),
               (B(2) + 0.6, B(4) + 0.6),   # opening dark, pre-drop pause, final fade, text exit into the wolf's eyes
               (B(53) + 0.2, B(56) + 0.02)]  # the screen goes dark while particles gather for the logo
    bad = [b for b in blacks if not any(lo <= b[0] and b[1] <= hi for lo, hi in allowed)]
    checks["black_frames_designed_only"] = (not bad, f"black: {blacks}" + (f" UNEXPECTED: {bad}" if bad else ""))
    log = sh(["ffmpeg", "-hide_banner", "-i", str(video), "-vf", "freezedetect=n=0.0008:d=0.8", "-an", "-f", "null", "-"])
    fr = [float(x) for x in re.findall(r"freeze_start: ([\d.]+)", log)]
    fr_bad = [x for x in fr if not (x >= B(57) or any(lo <= x <= hi for lo, hi in allowed))]
    checks["no_freezes"] = (not fr_bad, f"freezes {fr} (logo hold and designed darkness allowed)")

    # ---- logo only in the final sequence ----
    from PIL import Image
    lg = np.asarray(Image.open(project / "source/assets/npc_channel_logo.jpg").convert("L").resize((96, 96)), np.float32)
    lg = (lg - lg.mean()) / (lg.std() + 1e-6)
    W = 270
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"select='not(mod(n\\,6))',scale={W}:480,format=gray",
                          "-vsync", "0", "-f", "rawvideo", "-"], capture_output=True).stdout
    fr6 = np.frombuffer(raw, np.uint8).reshape(-1, 480, W).astype(np.float32)
    cy, r = int(480 * 0.47), int(880 / 1080 * W / 2)
    first = None
    scores = []
    for k, im in enumerate(fr6):
        patch = np.asarray(Image.fromarray(im[cy - r: cy + r, W // 2 - r: W // 2 + r]).resize((96, 96)), np.float32)
        p = (patch - patch.mean()) / (patch.std() + 1e-6)
        s = float((p * lg).mean())
        scores.append(s)
        if s > 0.55 and first is None:
            first = k * 6
    logo_f = next(x["frame"] for x in ev["beats"] if x["n"] == 56)
    pre = max(scores[: (logo_f - 70) // 6]) if scores else 0
    checks["logo_only_at_end"] = (first is not None and first >= logo_f - 1 and pre < 0.4,
                                  f"first logo frame ~f{first} (reveal f{logo_f}); max match before final sequence {pre:.2f}")

    # ---- copy ----
    src = (project / "source/edit.py").read_text()
    missing = [s for s in REQUIRED_TEXT if f'"{s}"' not in src]
    forbidden = []
    for p in list((project / "source").rglob("*.py")) + list((project / "source").rglob("*.json")) + list(Path(__file__).parent.glob("*.py")):
        if p.name == "qc.py":
            continue
        t = p.read_text(errors="ignore").lower()
        forbidden += [f"{w} in {p.name}" for w in FORBIDDEN if w in t]
    checks["on_screen_copy"] = (not missing and not forbidden,
                                f"{len(REQUIRED_TEXT) - len(missing)}/{len(REQUIRED_TEXT)} lines as specified" +
                                (f"; missing {missing}" if missing else "") + (f"; forbidden {forbidden}" if forbidden else ""))

    ok = all(p for p, _ in checks.values())
    for k, (p, d) in checks.items():
        print(f"  [{'PASS' if p else 'FAIL'}] {k:26s} {d}")
    video.with_suffix(".qc.json").write_text(json.dumps(
        {"video": video.name, "pass": ok, "checks": {k: {"pass": p, "detail": d} for k, (p, d) in checks.items()}}, indent=2))
    print("QC PASS" if ok else "QC FAIL")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main(Path(sys.argv[1]), Path(sys.argv[2])) else 1)
