"""Automated QC of rendered files (the actual MP4s), plus a contact sheet for visual review."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import cv2
import numpy as np

from .analyze import YUNET
from .common import FPS, H, W, ffprobe, run


def _probe(path: Path) -> dict:
    j = ffprobe(path)
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    a = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)
    num, den = v["avg_frame_rate"].split("/")
    return {"width": v["width"], "height": v["height"], "vcodec": v["codec_name"], "pix_fmt": v["pix_fmt"],
            "fps": round(float(num) / float(den), 3), "frames": int(v.get("nb_frames", 0)),
            "v_dur": float(v.get("duration", 0)), "acodec": a and a["codec_name"],
            "a_sr": a and int(a["sample_rate"]), "a_ch": a and a["channels"], "a_dur": a and float(a.get("duration", 0)),
            "size_mb": round(int(j["format"]["size"]) / 1e6, 2)}


def _filter_log(path: Path, vf: str | None = None, af: str | None = None) -> str:
    cmd = ["ffmpeg", "-v", "info", "-i", str(path)]
    cmd += (["-vf", vf] if vf else ["-vn"]) + (["-af", af] if af else ["-an"]) + ["-f", "null", "-"]
    return subprocess.run(cmd, capture_output=True, text=True).stderr


def loudness(path: Path) -> dict:
    log = _filter_log(path, af="ebur128=peak=true")
    summ = log[log.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[\d.]+) LUFS", summ)
    tp = re.search(r"Peak:\s+(-?[\d.]+) dBFS", summ)
    return {"integrated_lufs": float(i.group(1)) if i else None, "true_peak_dbfs": float(tp.group(1)) if tp else None}


def black_freeze(path: Path) -> dict:
    log = _filter_log(path, vf="blackdetect=d=0.15:pix_th=0.08,freezedetect=n=-60dB:d=1.2")
    blacks = [(float(a), float(b)) for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", log)]
    fz = re.findall(r"freeze_duration: ([\d.]+)", log)
    return {"black_segments": blacks, "freezes_s": [float(x) for x in fz]}


def silences(path: Path) -> list:
    log = _filter_log(path, af="silencedetect=n=-45dB:d=1.2")
    return [float(x) for x in re.findall(r"silence_duration: ([\d.]+)", log)]


def letterbox(path: Path) -> str | None:
    log = _filter_log(path, vf="cropdetect=limit=16:round=2:reset=0")
    m = re.findall(r"crop=(\d+:\d+:\d+:\d+)", log)
    return m[-1] if m else None


def sample_times(path: Path, n: int = 12) -> list[float]:
    dur = float(ffprobe(path)["format"]["duration"])
    return [dur * (k + 0.5) / n for k in range(n)]


def sample_frames(path: Path, n: int = 12) -> list[np.ndarray]:
    dur = float(ffprobe(path)["format"]["duration"])
    out = []
    for k in range(n):
        t = dur * (k + 0.5) / n
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(path), "-frames:v", "1",
                              "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
        if len(raw) == W * H * 3:
            out.append(np.frombuffer(raw, np.uint8).reshape(H, W, 3).copy())
    return out


def face_checks(frames: list[np.ndarray], cap_box: tuple[int, int], times: list[float] | None = None,
                runs: list[dict] | None = None) -> dict:
    """Edge cuts, caption overlap, and presence: a frame (or each split panel) whose shot had faces must show one."""
    det = cv2.FaceDetectorYN.create(str(YUNET), "", (W // 2, H // 2), 0.6, 0.3, 50)
    cut, overlap, seen, missing = 0, 0, 0, []
    for i, fr in enumerate(frames):
        _, faces = det.detect(cv2.resize(fr, (W // 2, H // 2)))
        run = None
        if times and runs:
            run = next((r for r in runs if r["out_s"] - 1e-6 <= times[i] < r["out_e"]), None)
        if run and run.get("faces_expected"):
            ys = [(f[1] + f[3] / 2) * 2 for f in faces] if faces is not None else []
            if run["mode"] == "split":
                if not any(y < 960 for y in ys) or not any(y >= 960 for y in ys):
                    missing.append(round(times[i], 2))
            elif not ys:
                missing.append(round(times[i], 2))
        if faces is None:
            continue
        band = (890, 1030) if run and run["mode"] == "split" else cap_box
        for f in faces:
            x, y, w, h = [v * 2 for v in f[:4]]
            if w < 90:
                continue
            seen += 1
            if x < -w * 0.15 or x + w > W + w * 0.15 or y < -h * 0.1:
                cut += 1
            # mouth/chin region vs caption band
            if y + h * 0.55 < band[1] and y + h > band[0] + 30:
                overlap += 1
    return {"faces_seen": seen, "faces_cut_at_edge": cut, "faces_under_captions": overlap,
            "missing_expected_face_at_s": missing}


def contact_sheet(frames: list[np.ndarray], out: Path, cols: int = 4) -> None:
    th = [cv2.resize(f, (270, 480)) for f in frames]
    while len(th) % cols:
        th.append(np.zeros_like(th[0]))
    rows = [np.hstack(th[i:i + cols]) for i in range(0, len(th), cols)]
    cv2.imwrite(str(out), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 85])


def caption_text_check(tl: dict, transcript_words: list[dict]) -> dict:
    """Captions are generated from ASR words; verify 1:1 text match and flag dictionary-unknown words."""
    from spellchecker import SpellChecker
    sp = SpellChecker()
    src = {round(w["s"], 3): w["w"] for w in transcript_words}
    mismatched = [w["w"] for w in tl["words"] if src.get(round(w["src"], 3)) != w["w"]]
    toks = {re.sub(r"[^A-Za-z']", "", t).lower().strip("'") for w in tl["words"] for t in re.split(r"[-–/]", w["w"])}
    toks = {t for t in toks if t and len(t) > 2}
    unknown = sorted(sp.unknown(toks))
    return {"mismatched_vs_transcript": mismatched, "dictionary_unknown": unknown,
            "note": "dictionary_unknown words need a human/agent check (names and slang are often valid); "
                    "fix real errors with --fix-word WRONG=RIGHT"}


def qc_clip(path: Path, tl: dict, transcript_words: list[dict], sheet: Path) -> dict:
    pr = _probe(path)
    ld = loudness(path)
    bf = black_freeze(path)
    sil = silences(path)
    lb = letterbox(path)
    frames = sample_frames(path, 12)
    contact_sheet(frames, sheet)
    cap_band = (tl["caption_y"] - 70, tl["caption_y"] + 70)
    fc = face_checks(frames, cap_band, sample_times(path, 12), tl["layout"].get("runs"))
    ct = caption_text_check(tl, transcript_words)
    exp_dur = tl["frames"] / FPS
    checks = {
        "dimensions_1080x1920": pr["width"] == W and pr["height"] == H,
        "h264_yuv420p": pr["vcodec"] == "h264" and pr["pix_fmt"] == "yuv420p",
        "fps_30": abs(pr["fps"] - FPS) < 0.01,
        "aac_48k_stereo": pr["acodec"] == "aac" and pr["a_sr"] == 48000 and pr["a_ch"] == 2,
        "duration_matches_timeline": abs(pr["v_dur"] - exp_dur) < 0.1,
        "av_in_sync_length": pr["a_dur"] is not None and abs(pr["a_dur"] - pr["v_dur"]) < 0.08,
        "loudness_-14_lufs": ld["integrated_lufs"] is not None and abs(ld["integrated_lufs"] + 14) <= 1.0,
        "true_peak_le_-1_dbfs": ld["true_peak_dbfs"] is not None and ld["true_peak_dbfs"] <= -1.0,
        "no_black_frames": not bf["black_segments"],
        "no_frozen_video_over_3s": all(x < 3.0 for x in bf["freezes_s"]),
        "no_dead_air_over_1_5s": all(x < 1.5 for x in sil),
        "no_letterbox_bars": lb in (None, f"{W}:{H}:0:0"),
        "no_faces_cut_at_edges": fc["faces_cut_at_edge"] == 0,
        "captions_clear_of_faces": fc["faces_under_captions"] == 0,
        "subject_visible_in_every_panel": not fc["missing_expected_face_at_s"],
        "captions_match_transcript": not ct["mismatched_vs_transcript"],
    }
    return {"file": path.name, "probe": pr, "loudness": ld, "black_freeze": bf, "silences_s": sil,
            "cropdetect": lb, "faces": fc, "captions": ct, "checks": checks,
            "passed": all(checks.values()), "contact_sheet": sheet.name,
            "review_type": "automated checks + contact sheet; no human review implied"}
