"""Whole-source analysis: shot boundaries, audio energy, face tracks, mouth motion (active speaker cue)."""
from __future__ import annotations

import json
import subprocess

import cv2
import numpy as np
import soundfile as sf

from .common import MODELS, log, write_json

YUNET = MODELS / "face_detection_yunet_2023mar.onnx"


def detect_scenes(src, fps: float) -> list[dict]:
    from scenedetect import ContentDetector, detect
    scenes = detect(str(src), ContentDetector(threshold=27.0, min_scene_len=int(max(fps, 1) * 0.6)),
                    show_progress=False)
    return [{"s": round(a.get_seconds(), 3), "e": round(b.get_seconds(), 3)} for a, b in scenes]


def audio_energy(wav16, hop: float = 0.1) -> dict:
    a, sr = sf.read(wav16, dtype="float32")
    n = int(sr * hop)
    frames = len(a) // n
    if frames == 0:
        return {"hop": hop, "rms_db": [], "flux": []}
    x = a[: frames * n].reshape(frames, n)
    rms = np.sqrt((x ** 2).mean(1) + 1e-10)
    db = 20 * np.log10(rms + 1e-9)
    # spectral flux on 512-pt frames: onset / excitement proxy
    spec = np.abs(np.fft.rfft(x[:, : min(n, 1024)] * np.hanning(min(n, 1024)), axis=1))
    flux = np.r_[0, np.maximum(0, np.diff(np.log1p(spec), axis=0)).mean(1)]
    return {"hop": hop, "rms_db": np.round(db, 2).tolist(), "flux": np.round(flux, 4).tolist()}


class _Tracker:
    def __init__(self):
        self.tracks: dict[int, dict] = {}
        self.next_id = 0

    def assign(self, t: float, dets: list[dict]) -> None:
        live = {k: v for k, v in self.tracks.items() if t - v["t"] < 1.5}
        used = set()
        for d in sorted(dets, key=lambda d: -d["w"] * d["h"]):
            cx, cy = d["x"] + d["w"] / 2, d["y"] + d["h"] / 2
            best, bd = None, 1e9
            for k, v in live.items():
                if k in used:
                    continue
                dist = np.hypot(cx - v["cx"], cy - v["cy"])
                if dist < max(d["w"], v["w"]) * 1.2 and dist < bd:
                    best, bd = k, dist
            if best is None:
                best = self.next_id
                self.next_id += 1
            used.add(best)
            d["id"] = best
            self.tracks[best] = {"t": t, "cx": cx, "cy": cy, "w": d["w"], "patch": self.tracks.get(best, {}).get("patch")}


def face_pass(src, vinfo: dict, sample_fps: float) -> dict:
    """Decode at low res, detect faces (YuNet), track them, measure mouth motion and global motion."""
    W0, H0 = vinfo["width"], vinfo["height"]
    pw = 640
    ph = int(round(H0 * pw / W0 / 2) * 2)
    det = cv2.FaceDetectorYN.create(str(YUNET), "", (pw, ph), 0.72, 0.3, 5000)
    cmd = ["ffmpeg", "-v", "error", "-i", str(src), "-vf", f"fps={sample_fps},scale={pw}:{ph}",
           "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=pw * ph * 3 * 4)
    tr = _Tracker()
    samples, prev_gray, i = [], None, 0
    fsz = pw * ph * 3
    while True:
        buf = p.stdout.read(fsz)
        if len(buf) < fsz:
            break
        img = np.frombuffer(buf, np.uint8).reshape(ph, pw, 3)
        t = i / sample_fps
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        small = cv2.resize(gray, (80, int(80 * ph / pw)))
        motion = float(np.abs(small.astype(np.int16) - prev_gray).mean()) if prev_gray is not None else 0.0
        prev_gray = small.astype(np.int16)
        _, faces = det.detect(img)
        dets = []
        if faces is not None:
            for f in faces:
                x, y, w, h = f[:4]
                if w < pw * 0.035:
                    continue
                # mouth corners are landmarks 3 & 4 → mouth patch
                mx0, mx1 = sorted([f[10], f[12]])
                my = (f[11] + f[13]) / 2
                mw = max(mx1 - mx0, w * 0.3)
                x0, x1 = int(max(0, mx0 - mw * 0.25)), int(min(pw, mx1 + mw * 0.25))
                y0, y1 = int(max(0, my - mw * 0.45)), int(min(ph, my + mw * 0.45))
                patch = cv2.resize(gray[y0:y1, x0:x1], (24, 12)).astype(np.int16) if x1 > x0 + 2 and y1 > y0 + 2 else None
                dets.append({"x": float(x), "y": float(y), "w": float(w), "h": float(h),
                             "score": round(float(f[14]), 3), "patch": patch})
        tr.assign(t, dets)
        out = []
        for d in dets:
            prev = tr.tracks[d["id"]].get("patch")
            mouth = float(np.abs(d["patch"] - prev).mean()) if (d["patch"] is not None and prev is not None) else 0.0
            tr.tracks[d["id"]]["patch"] = d["patch"]
            out.append({"id": d["id"], "x": round(d["x"] / pw, 4), "y": round(d["y"] / ph, 4),
                        "w": round(d["w"] / pw, 4), "h": round(d["h"] / ph, 4),
                        "score": d["score"], "mouth": round(mouth, 2)})
        samples.append({"t": round(t, 3), "motion": round(motion, 2), "faces": out})
        i += 1
    p.wait()
    return {"sample_fps": sample_fps, "samples": samples}


def summarize_faces(fp: dict) -> dict:
    s = fp["samples"]
    if not s:
        return {"face_ratio": 0, "multi_face_ratio": 0, "median_faces": 0}
    n_f = [len(x["faces"]) for x in s]
    return {"face_ratio": round(float(np.mean([n > 0 for n in n_f])), 3),
            "multi_face_ratio": round(float(np.mean([n > 1 for n in n_f])), 3),
            "median_faces": float(np.median(n_f)),
            "mean_motion": round(float(np.mean([x["motion"] for x in s])), 3)}


def analyze(src, vinfo: dict, dirs: dict, force: bool = False) -> dict:
    out = dirs["Analysis"] / "scene_analysis.json"
    if out.exists() and not force:
        log("analysis: cached")
        return json.loads(out.read_text())
    log("detecting shot boundaries (PySceneDetect)")
    scenes = detect_scenes(src, vinfo["fps"])
    log(f"  {len(scenes)} shots")
    sample_fps = 8 if vinfo["duration"] < 1500 else 4
    log(f"face tracking + mouth motion at {sample_fps} fps (YuNet)")
    fp = face_pass(src, vinfo, sample_fps)
    write_json(dirs["Analysis"] / "face_tracks.json", fp)
    energy = audio_energy(dirs["work"] / "audio16k.wav")
    res = {"scenes": scenes, "faces_summary": summarize_faces(fp), "audio": energy,
           "face_tracks_file": "face_tracks.json"}
    write_json(out, res)
    log(f"  faces present in {res['faces_summary']['face_ratio']:.0%} of samples")
    return res
