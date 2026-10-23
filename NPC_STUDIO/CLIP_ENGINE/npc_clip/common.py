"""Shared paths, process helpers, probing and JSON I/O."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent          # NPC_STUDIO/CLIP_ENGINE
STUDIO = ENGINE.parent                                   # NPC_STUDIO
REPO = STUDIO.parent
OUTPUT_ROOT = REPO / "NPC_VIRAL_STUDIO"
MODELS = ENGINE / "models"
PRESETS = ENGINE / "presets"
FONTS_DIR = STUDIO / "BRAND" / "fonts"
REGISTRY = OUTPUT_ROOT / "_registry"

W, H, FPS = 1080, 1920, 30
SR = 48000


def log(msg: str) -> None:
    print(f"[npc-clip {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def run(cmd: list, quiet: bool = True, check: bool = True, **kw) -> subprocess.CompletedProcess:
    cmd = [str(c) for c in cmd]
    p = subprocess.run(cmd, capture_output=quiet, text=True, **kw)
    if check and p.returncode != 0:
        tail = (p.stderr or "")[-2500:] if quiet else ""
        raise RuntimeError(f"command failed ({p.returncode}): {' '.join(cmd[:8])} …\n{tail}")
    return p


def ffprobe(path: Path) -> dict:
    p = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path])
    return json.loads(p.stdout)


def video_info(path: Path) -> dict:
    j = ffprobe(path)
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)
    if v is None:
        raise RuntimeError(f"{path} has no video stream")
    num, den = (v.get("avg_frame_rate") or v.get("r_frame_rate") or "30/1").split("/")
    fps = float(num) / float(den) if float(den) else 30.0
    rot = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(sd["rotation"])
    w, h = int(v["width"]), int(v["height"])
    if abs(rot) in (90, 270):
        w, h = h, w
    return {
        "width": w, "height": h, "fps": round(fps, 3),
        "duration": float(j["format"].get("duration") or v.get("duration") or 0),
        "vcodec": v.get("codec_name"), "pix_fmt": v.get("pix_fmt"),
        "has_audio": a is not None,
        "acodec": a.get("codec_name") if a else None,
        "sample_rate": int(a["sample_rate"]) if a else None,
        "channels": a.get("channels") if a else None,
        "tags": j["format"].get("tags", {}),
        "size_bytes": int(j["format"].get("size", 0)),
    }


def read_json(p: Path, default=None):
    p = Path(p)
    if not p.exists():
        return default
    return json.loads(p.read_text())


def write_json(p: Path, obj) -> Path:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False))
    return p


def slugify(s: str, n: int = 48) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")
    return (s[:n] or "source").upper()


def need(tool: str) -> None:
    if shutil.which(tool) is None:
        sys.exit(f"npc-clip: required tool '{tool}' not found on PATH")


def project_dirs(root: Path) -> dict:
    d = {k: root / k for k in ("Source", "Analysis", "Clips", "Covers", "Metadata", "Project", "QC")}
    d["timelines"] = root / "Project" / "editable_timelines"
    d["work"] = root / "Project" / "work"
    for p in d.values():
        p.mkdir(parents=True, exist_ok=True)
    d["root"] = root
    return d


def fmt_ts(t: float) -> str:
    m, s = divmod(max(0.0, t), 60)
    h, m = divmod(int(m), 60)
    return f"{h:d}:{m:02d}:{s:05.2f}" if h else f"{m:d}:{s:05.2f}"


def load_corrections(root: Path) -> dict:
    """Project/caption_corrections.json: {"wrong": "right"} — fixes ASR spellings in captions, titles and QC."""
    return {k.lower(): v for k, v in (read_json(Path(root) / "Project" / "caption_corrections.json", {}) or {}).items()}


def correct_word(w: str, fixes: dict) -> str:
    m = re.match(r"^([^\w]*)([\w'’-]+)([^\w]*)$", w)
    if not m or m.group(2).lower() not in fixes:
        return w
    rep = fixes[m.group(2).lower()]
    if m.group(2)[:1].isupper():
        rep = rep[:1].upper() + rep[1:]
    return m.group(1) + rep + m.group(3)
