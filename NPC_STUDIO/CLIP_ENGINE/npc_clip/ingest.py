"""Source intake: URL / file / folder → Source/ + source_metadata.json + rights classification."""
from __future__ import annotations

import hashlib
import os
import re
import time
from pathlib import Path

from .common import ENGINE, log, run, slugify, video_info, write_json

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi"}
RIGHTS = ("MINE", "LICENSED", "AUTHORIZED", "FAIR-USE CANDIDATE", "UNKNOWN")
RIGHTS_ALIASES = {
    "mine": "MINE", "own": "MINE", "licensed": "LICENSED", "authorized": "AUTHORIZED",
    "fair-use": "FAIR-USE CANDIDATE", "fair_use": "FAIR-USE CANDIDATE", "fairuse": "FAIR-USE CANDIDATE",
    "unknown": "UNKNOWN",
}
# Classes that may be rendered without an extra original layer.
CLEARED = {"MINE", "LICENSED", "AUTHORIZED"}


class SourceBlocked(RuntimeError):
    pass


def is_url(s: str) -> bool:
    return bool(re.match(r"^https?://", s.strip()))


def expand_inputs(inp: str) -> list[str]:
    if is_url(inp):
        return [inp]
    p = Path(inp).expanduser()
    if p.is_dir():
        files = sorted(f for f in p.iterdir() if f.suffix.lower() in VIDEO_EXT)
        if not files:
            raise SourceBlocked(f"folder {p} contains no video files ({', '.join(sorted(VIDEO_EXT))})")
        return [str(f.resolve()) for f in files]
    if p.is_file():
        return [str(p.resolve())]
    raise SourceBlocked(f"input not found: {inp}")


def name_for(inp: str) -> str:
    if is_url(inp):
        m = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{6,})", inp)
        return slugify("YT_" + (m.group(1) if m else re.sub(r"\W+", "_", inp)[-24:]))
    return slugify(Path(inp).stem)


def download(url: str, dest_dir: Path) -> tuple[Path, dict]:
    """Fetch a URL with yt-dlp through the environment's proxy. Raises SourceBlocked with the exact reason."""
    ytdlp = ENGINE / ".venv" / "bin" / "yt-dlp"
    out_tmpl = str(dest_dir / "source.%(ext)s")
    cmd = [ytdlp, "--no-playlist", "-f", "bv*[height<=1080]+ba/b[height<=1080]/b", "--merge-output-format", "mp4",
           "--write-info-json", "--no-progress", "-o", out_tmpl, url]
    env = dict(os.environ)
    if os.path.exists("/root/.ccr/ca-bundle.crt"):
        env.setdefault("SSL_CERT_FILE", "/root/.ccr/ca-bundle.crt")
    p = run(cmd, check=False, env=env)
    if p.returncode != 0:
        err = (p.stderr or "").strip().splitlines()
        reason = next((l for l in reversed(err) if "ERROR" in l), err[-1] if err else "unknown error")
        if "403" in reason or "Tunnel" in reason or "ProxyError" in reason:
            reason += "  → this environment's network policy blocks the host. Upload the video file instead."
        raise SourceBlocked(f"could not download {url}: {reason}")
    files = [f for f in dest_dir.glob("source.*") if f.suffix.lower() in VIDEO_EXT]
    if not files:
        raise SourceBlocked(f"yt-dlp finished but produced no video file for {url}")
    info = {}
    ij = dest_dir / "source.info.json"
    if ij.exists():
        import json
        j = json.loads(ij.read_text())
        info = {k: j.get(k) for k in ("id", "title", "uploader", "channel", "channel_url", "upload_date",
                                      "duration", "license", "webpage_url", "description")}
        if info.get("description"):
            info["description"] = info["description"][:600]
    return files[0], info


def sha256(path: Path, limit_mb: int = 64) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read(limit_mb * 1024 * 1024))
    return h.hexdigest()[:16]


def ingest(inp: str, dirs: dict, rights: str, rights_note: str, source_name: str | None) -> dict:
    src_dir = dirs["Source"]
    info = {}
    if is_url(inp):
        log(f"downloading {inp}")
        media, info = download(inp, src_dir)
    else:
        media = Path(inp)
        link = src_dir / ("source" + media.suffix.lower())
        if not link.exists():
            try:
                link.symlink_to(media)
            except OSError:
                import shutil
                shutil.copy2(media, link)
        media = link
    vi = video_info(media)
    if vi["duration"] < 5:
        raise SourceBlocked(f"source is only {vi['duration']:.1f}s long")
    if not vi["has_audio"]:
        log("warning: source has no audio track; transcript-driven selection will be empty")
    rights = RIGHTS_ALIASES.get(rights.lower(), rights.upper())
    if rights not in RIGHTS:
        raise SourceBlocked(f"--rights must be one of {', '.join(RIGHTS_ALIASES)}")
    meta = {
        "input": inp,
        "media_path": str(media.resolve()),
        "fingerprint_sha256_head": sha256(media.resolve()),
        "ingested_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "display_name": source_name or info.get("title") or Path(inp).stem,
        "creator": info.get("channel") or info.get("uploader"),
        "url": info.get("webpage_url") or (inp if is_url(inp) else None),
        "platform_info": info,
        "video": vi,
        "rights": {
            "classification": rights,
            "note": rights_note,
            "cleared_for_render": rights in CLEARED or rights == "FAIR-USE CANDIDATE",
            "requires_original_layer": rights == "FAIR-USE CANDIDATE",
            "declared_license_in_metadata": info.get("license"),
        },
    }
    write_json(src_dir / "source_metadata.json", meta)
    log(f"source: {vi['width']}x{vi['height']} @ {vi['fps']}fps, {vi['duration']:.1f}s, rights={rights}")
    return meta
