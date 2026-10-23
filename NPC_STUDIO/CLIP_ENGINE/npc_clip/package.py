"""Covers, publishing metadata, attribution, quality report, registry and ZIP."""
from __future__ import annotations

import json
import time
import zipfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .common import FONTS_DIR, H, REGISTRY, W, fmt_ts, read_json, write_json

FONT = FONTS_DIR / "InterDisplay-Black.otf"


def pick_cover_frame(frame_dir: Path) -> np.ndarray | None:
    det = None
    try:
        from .analyze import YUNET
        det = cv2.FaceDetectorYN.create(str(YUNET), "", (W // 3, H // 3), 0.75, 0.3, 20)
    except Exception:
        pass
    best, best_s = None, -1.0
    for p in sorted(frame_dir.glob("frame_*.jpg")):
        img = cv2.imread(str(p))
        g = cv2.cvtColor(cv2.resize(img, (W // 3, H // 3)), cv2.COLOR_BGR2GRAY)
        sharp = cv2.Laplacian(g, cv2.CV_64F).var()
        face = 0.0
        if det is not None:
            _, f = det.detect(cv2.resize(img, (W // 3, H // 3)))
            if f is not None:
                face = float(max(x[2] * x[3] for x in f)) / (W * H / 9) * 100
        s = np.log1p(sharp) + face * 0.8
        if s > best_s:
            best, best_s = img, s
    return best


def make_cover(frame: np.ndarray, text: str, accent: str, out: Path) -> None:
    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
    # darken lower third for text legibility
    grad = Image.new("L", (1, H))
    for y in range(H):
        grad.putpixel((0, y), int(max(0, (y - H * 0.45) / (H * 0.55)) ** 1.4 * 210))
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    shade.putalpha(grad.resize((W, H)))
    img = Image.alpha_composite(img, shade)
    d = ImageDraw.Draw(img)
    words = text.upper().split()
    size = 112
    font = ImageFont.truetype(str(FONT), size)
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if d.textlength(trial, font=font) > W - 140 and cur:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    lines.append(cur)
    lines = lines[:4]
    y = int(H * 0.86) - len(lines) * int(size * 1.08)
    acc = tuple(int(accent.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    for k, line in enumerate(lines):
        tw = d.textlength(line, font=font)
        x = (W - tw) / 2
        col = acc if k == len(lines) - 1 and len(lines) > 1 else (255, 255, 255)
        d.text((x, y), line, font=font, fill=col + (255,), stroke_width=8, stroke_fill=(0, 0, 0, 255))
        y += int(size * 1.08)
    img.convert("RGB").save(out, "PNG", optimize=True)


def write_metadata(dirs: dict, meta: dict, timelines: list[dict], qc: list[dict]) -> None:
    md = dirs["Metadata"]
    src = meta.get("url") or meta["media_path"]
    titles, caps, tags, attr = [], [], [], []
    for tl in timelines:
        p = tl["package"]
        cid = tl["clip_id"]
        titles.append(f"{cid}: {p['title']}")
        caps.append(f"{cid}: {p['post_caption']}")
        tags.append(f"{cid}: {' '.join(p['hashtags'])}")
        attr.append(f"{cid}: source {src} · {fmt_ts(tl['window']['start'])}–{fmt_ts(tl['window']['end'])} · "
                    f"creator: {meta.get('creator') or 'n/a'} · rights: {meta['rights']['classification']}"
                    + (f" ({meta['rights']['note']})" if meta['rights'].get('note') else ""))
    (md / "titles.txt").write_text("\n".join(titles) + "\n")
    (md / "captions.txt").write_text("\n".join(caps) + "\n")
    (md / "hashtags.txt").write_text("\n".join(tags) + "\n")
    disclaimer = ("Editing (captions, reframing, grading, music, SFX) is added value, not a copyright shield. "
                  "No immunity from Content ID, claims, strikes or reused-content limits is implied.")
    (md / "source_attribution.txt").write_text("\n".join(attr) + "\n\n" + disclaimer + "\n")
    write_json(md / "quality_report.json", {"generated": time.strftime("%Y-%m-%dT%H:%M:%S"), "clips": qc})
    write_json(md / "clip_packages.json", [{
        "clip": tl["clip_id"], "file": f"Clips/{tl['clip_id']}.mp4", "cover": f"Covers/NPC_COVER_{tl['clip_id'][-2:]}.png",
        "title": tl["package"]["title"], "opening_hook": tl["package"]["hook"],
        "post_caption": tl["package"]["post_caption"], "hashtags": tl["package"]["hashtags"],
        "duration_s": tl["duration"], "score": tl["score"], "factors": tl["factors"], "hook_type": tl["hook_type"],
        "caption_style": tl["caption_style"], "layout": tl["layout"]["mode"],
        "retention_assessment": tl["package"].get("retention_notes") or retention_notes(tl),
        "source": {"url": src, "start": tl["window"]["start"], "end": tl["window"]["end"],
                   "rights": meta["rights"]["classification"]},
        "selected_by": tl["selected_by"], "platforms": ["TikTok", "YouTube Shorts", "Instagram Reels", "Facebook Reels"],
    } for tl in timelines])


def retention_notes(tl: dict) -> str:
    f = tl["factors"]
    why = sorted(f, key=lambda k: -f[k])[:2]
    weak = min(f, key=f.get)
    risk = {"hook": "opening line is soft — viewers may swipe in the first 2 s",
            "retention": "pace dips or pauses mid-clip are the likely drop-off points",
            "emotion": "low emotional variation; relies on information value",
            "curiosity": "few open questions — needs the title to create the gap",
            "standalone": "may need context the clip doesn't give",
            "visual": "visually static — captions and zooms carry it",
            "loop": "ending doesn't loop back to the opening"}[weak]
    cold = " Opens with a cold-open teaser of the strongest line." if tl["window"]["cold_open"] else ""
    return f"Strongest factors: {why[0]} ({f[why[0]]:.0f}), {why[1]} ({f[why[1]]:.0f}).{cold} Risk: {risk}."


def register(dirs: dict, meta: dict, timelines: list[dict]) -> None:
    reg_p = REGISTRY / "clips_registry.json"
    reg = read_json(reg_p, [])
    keep = [r for r in reg if r.get("project") != dirs["root"].name]
    for tl in timelines:
        keep.append({"project": dirs["root"].name, "clip": tl["clip_id"], "title": tl["package"]["title"],
                     "duration": tl["duration"], "hook_type": tl["hook_type"], "caption_style": tl["caption_style"],
                     "density": tl["density"], "content_type": tl["content_type"], "layout": tl["layout"]["mode"],
                     "score": tl["score"], "creator": meta.get("creator"), "topic": tl["package"].get("keywords", [])})
    write_json(reg_p, keep)


def make_zip(dirs: dict, timelines: list[dict]) -> Path:
    root = dirs["root"]
    zp = root / f"{root.name}_EXPORT.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_STORED) as z:
        for sub in ("Clips", "Covers", "Metadata"):
            for f in sorted((root / sub).glob("*")):
                if f.is_file():
                    z.write(f, f"{root.name}/{sub}/{f.name}")
        for f in ("Analysis/selected_clips.json", "Analysis/candidate_scores.csv", "Source/source_metadata.json"):
            if (root / f).exists():
                z.write(root / f, f"{root.name}/{f}")
    return zp
