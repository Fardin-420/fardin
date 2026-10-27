"""Resolve text anchors in edl.json to source-pixel boxes by OCR-ing the anchor frames.

    python resolve_edl.py SOURCE.mp4

Writes edl_resolved.json next to edl.json. Only geometry is written (no recognised text),
so the resolved EDL is safe to commit.
"""
import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
W, H = 864, 1920
RIGHT = 836  # inner right edge of page cards


def grab(src, t):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", src, "-frames:v", "1",
                          "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(H, W, 3)


def score(query, text, exact=False):
    """Exact (case-sensitive, punctuation-insensitive) labels win; then substrings, shorter first."""
    norm = lambda s: re.sub(r"[^0-9A-Za-z ]", "", s).strip()
    q, t = norm(query), norm(text)
    if exact == "raw":
        return 1.0 if query.strip() == text.strip() else 0.0
    if exact:
        return 1.0 if q == t else 0.0
    if q.lower() == t.lower():
        return 1.0
    if q.lower() in t.lower():
        return 0.8 + 0.2 * len(q) / max(len(t), 1)
    return difflib.SequenceMatcher(None, q.lower(), t.lower()[: len(q) + 4]).ratio()


def box_for(kind, b):
    x0, y0, x1, y1 = b
    if kind == "field":
        return [x0 - 24, y0 - 10, min(x0 + 720, RIGHT), y1 + 105]
    if kind == "line+left":
        return [x0 - 70, y0 - 14, RIGHT - 20, y0 + 112]
    if kind == "wide_button":
        return [max(20, min(x0, 864 - x1) - 70), y0 - 30, min(844, max(x1, 864 - x0) + 70), y1 + 30]
    if kind == "terms":  # three consent checkboxes under the first label
        return [x0 - 60, y0 - 16, RIGHT - 20, y0 + 300]
    if kind == "heading":  # three-line centred headline
        return [40, y0 - 18, 824, y0 + 170]
    if kind == "promo_box":  # 'Promo Unavailable' sheet: title + message line
        return [x0 - 24, y0 - 20, RIGHT - 10, y1 + 110]
    if kind == "price":  # Go card price + promo line
        return [x0 - 20, y0 - 150, RIGHT - 40, y1 + 46]
    if kind == "button":
        return [x0 - 60, y0 - 26, x1 + 60, y1 + 26]
    if kind == "block3":
        return [x0 - 22, y0 - 28, RIGHT - 24, y0 + 250]
    if kind == "title":
        return [x0 - 14, y0 - 12, RIGHT - 30, y1 + 12]
    if kind == "line":
        return [x0 - 12, y0 - 46, max(x1, 700) + 12, y1 + 8]
    if kind == "req":
        return [x0 - 44, y0 - 8, max(x1, 700) + 10, y1 + 44]
    return [x0, y0, x1, y1]


def main(src):
    from rapidocr_onnxruntime import RapidOCR
    ocr = RapidOCR()
    edl = json.loads((HERE / "edl.json").read_text())
    cache = {}

    def find(anchor):
        t = anchor["src"]
        if t not in cache:
            res, _ = ocr(grab(src, t))
            cache[t] = [([min(p[0] for p in q), min(p[1] for p in q), max(p[0] for p in q), max(p[1] for p in q)], txt)
                        for q, txt, _ in (res or [])]
        ex = anchor.get("exact", False)
        sc = lambda bt: score(anchor["text"], bt[1], ex)
        best = max(cache[t], key=sc)
        s = sc(best)
        if anchor.get("pick") == "largest":  # several equal matches: take the tallest text (titles over breadcrumbs)
            best = max((bt for bt in cache[t] if sc(bt) >= s - 0.05), key=lambda bt: bt[0][3] - bt[0][1])
        if s < 0.7:
            raise SystemExit(f"anchor not found at {t}s (best score {s:.2f})")
        return [round(v) for v in best[0]]

    def resolve(item, kind_key="box"):
        out = dict(item)
        if "anchor" in item:
            b = find(item["anchor"])
            out["text_box"] = b
            cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
            if kind_key in item:
                out["rect"] = [round(v) for v in box_for(item[kind_key], b)]
            if "dy" in item:
                # centre on the text block (left-aligned lines), not on the page
                out["fx"], out["fy"] = round((b[0] - 40 + max(b[2], 720) + 20) / 2), round(cy + item["dy"])
            if item.get("at") == "left":
                out["x"], out["y"] = b[0] - 42, round(b[1] + 14)
            else:
                r = out.get("rect", b)
                out["x"], out["y"] = round((r[0] + r[2]) / 2), round((r[1] + r[3]) / 2)
            del out["anchor"]
        return out

    for key in ("camera", "freeze_camera", "highlights", "freeze_highlights", "taps"):
        edl[key] = [resolve(it) for it in edl[key]]
    (HERE / "edl_resolved.json").write_text(json.dumps(edl, indent=1))
    print("resolved", sum(len(edl[k]) for k in ("camera", "freeze_camera", "highlights", "freeze_highlights", "taps")), "items")


if __name__ == "__main__":
    main(sys.argv[1])
