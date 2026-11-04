"""Pacing pass planner: turn every long hold in the v1 render into a 3-4.5 s rhythm of camera beats.

    .venv/bin/python scripts/pace_plan.py [--master out/v1/master_1080p.mp4] [--qa out/v1/qa.json]

For each hold (> 6 s with only small motion, from qa.json) it schedules camera states:
  P  punch-in   eased 9 frames, frames the main content block above the caption band
  D  detail     hard cut to a tighter crop on the brightest cluster
  W  wide push  eased 14 frames back to ~1.05 with a small lateral offset
Framing is measured from the rendered v1 frames (bright-pixel bounding box, caption band and top HUD
strip excluded), so a punch never pushes the key element under the captions or off screen.
Hand-built detail inserts (components/inserts.tsx) take over parts of the priority hold.
Each hold starts at identity for 1.5 s and returns to identity 0.5 s before it ends, so frames
outside the windows are untouched and the windows splice cleanly.

Writes RENDER_ENGINE/src/heist/data/pace.json and out/chunks/pace_windows.json (global frame windows).
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT.parents[1] / "RENDER_ENGINE" / "src" / "heist"
W, H = 1920, 1080
DW, DH = 480, 270
SAFE = (96, 60, 1824, 760)  # x0, y0, x1, y1: keep framed content above the caption band
FPS = 30
SPACING = 114  # ~3.8 s between camera states
END_SCREEN = 25014 - 600  # last 20 s

# Priority hold (Binance 14 / EIP-7702 explainer): detail inserts locked to the narration (global frames).
INSERTS = [
    {"name": "count50", "f0": 9377, "f1": 9450},   # "Inside it: fifty authorizations —"
    {"name": "ethEip", "f0": 9531, "f1": 9628},    # "using an Ethereum feature called EIP-7702,"
    {"name": "delegate", "f0": 9632, "f1": 9736},  # "which lets a wallet hand its powers to a piece of code."
    {"name": "nonceRun", "f0": 9815, "f1": 9912},  # "Every wallet keeps a running count of its transactions."
]


def decode(master: Path, a: float, g: float, fps: int = 6) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{a:.3f}", "-t", f"{g:.3f}", "-i", str(master),
                          "-vf", f"fps={fps},scale={DW}:{DH},format=gray", "-f", "rawvideo", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, DH, DW)


def content(frames: np.ndarray):
    """Bounding box and brightness centroid (1080p px) of bright content, captions and top HUD excluded."""
    sx = W / DW
    y0, y1 = int(DH * 100 / H), int(DH * 0.72)
    m = np.zeros((DH, DW), bool)
    wsum = np.zeros((DH, DW), np.float32)
    for fr in frames:
        mk = fr > 62
        mk[:y0] = False
        mk[y1:] = False
        m |= mk
        wsum += np.where(mk, fr.astype(np.float32), 0)
    ys, xs = np.nonzero(m)
    if len(xs) < 40:
        return None
    bx0, bx1 = np.percentile(xs, [0.5, 99.5]) * sx
    by0, by1 = np.percentile(ys, [0.5, 99.5]) * sx
    wt = wsum[ys, xs]
    cx, cy = (xs * wt).sum() / wt.sum() * sx, (ys * wt).sum() / wt.sum() * sx
    return (bx0, by0, bx1, by1), (cx, cy)


def frame_to(s: float, cx: float, cy: float, tx_c: float = 960, ty_c: float = 410, box=None):
    tx = tx_c - s * cx
    ty = ty_c - s * cy
    if box is not None:
        # never push framed content into the caption band: bottom of everything shown in this hold <= SAFE y1
        ty = min(ty, SAFE[3] - s * box[3])
    tx = min(0.0, max(W - s * W, tx))
    ty = min(0.0, max(H - s * H, ty))
    return round(tx, 1), round(ty, 1)


def state(kind: str, info, flip: int, hold_box):
    if info is None:
        box, (cx, cy) = (560, 240, 1360, 700), (960, 470)
    else:
        _, (cx, cy) = info
    box = hold_box or (560, 240, 1360, 700)
    bw, bh = max(80, box[2] - box[0]), max(60, box[3] - box[1])
    fit = min((SAFE[2] - SAFE[0]) / bw, (SAFE[3] - SAFE[1]) / bh)
    p = min(1.45, max(1.12, fit * 0.95))
    bcx, bcy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    if kind == "P":
        s = p
        tx, ty = frame_to(s, bcx, bcy, box=box)
        return {"s": round(s, 3), "tx": tx, "ty": ty, "ease": 9}
    if kind == "D":
        s = min(1.8, max(1.35, p * 1.3))
        tx, ty = frame_to(s, cx, cy, box=box)
        return {"s": round(s, 3), "tx": tx, "ty": ty, "ease": 0}
    s = 1.05
    tx, ty = frame_to(s, bcx, bcy, 960 + (30 if flip else -30), 470, box=box)
    return {"s": s, "tx": tx, "ty": ty, "ease": 14}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--master", default=str(ROOT / "out" / "v1" / "master_1080p.mp4"))
    ap.add_argument("--qa", default=str(ROOT / "out" / "v1" / "qa.json"))
    args = ap.parse_args()
    holds = json.loads(Path(args.qa).read_text())["cadence"]["gaps_over_6s"]
    master = Path(args.master)
    cams, windows, used_inserts = [], [], []
    cycle = ["P", "D", "W"]
    ci = 0
    for hi, (a, g) in enumerate(holds):
        A, B = round(a * FPS), round((a + g) * FPS)
        frames = decode(master, a, g)
        fr_at = lambda f: frames[min(len(frames) - 1, max(0, int((f - A) / FPS * 6)))]
        if A >= END_SCREEN:
            continue  # YouTube end-screen template: element slots must stay fixed
        ins = [i for i in INSERTS if A <= i["f0"] and i["f1"] <= B]
        keep = [k for k in range(len(frames)) if not any(i["f0"] <= A + k * FPS / 6 <= i["f1"] for i in ins)]
        hb = content(frames[keep])
        hold_box = hb[0] if hb else None
        used_inserts += ins
        # segments of the hold not covered by inserts
        segs, cur = [], A
        for i in ins:
            if i["f0"] > cur:
                segs.append((cur, i["f0"] - 1, "ins"))
            cur = i["f1"] + 1
        segs.append((cur, B, "end"))
        flip = 0
        for k, (s0, s1, tail) in enumerate(segs):
            start = s0 + 45 if s0 == A else s0
            limit = s1 - 26 if tail == "end" else s1
            span = limit - start
            if span >= 40:
                n = max(1, round(span / SPACING))
                L = span / n
                for j in range(n):
                    f0 = int(start + j * L)
                    f1 = int(start + (j + 1) * L)
                    kind = cycle[ci % 3]
                    ci += 1
                    flip ^= 1
                    smp = np.stack([fr_at(f0 + 6), fr_at((f0 + f1) // 2), fr_at(f1 - 6)])
                    st = state(kind, content(smp), flip, hold_box)
                    if s0 != A and j == 0:
                        st["ease"] = 0  # cut back from an insert to a new framing
                    cams.append({"f": f0, **st, "hold": hi, "kind": kind})
            if tail == "end":
                cams.append({"f": max(start, limit), "s": 1, "tx": 0, "ty": 0, "ease": 10, "hold": hi, "kind": "I"})
        windows.append([A, B])
    cams.sort(key=lambda c: c["f"])
    (ENGINE / "data" / "pace.json").write_text(json.dumps({"cams": cams, "inserts": used_inserts}, indent=0))
    (ROOT / "out" / "chunks" / "pace_windows.json").write_text(json.dumps(windows))
    print(f"{len(holds)} holds, {len(cams)} camera keys, {len(used_inserts)} inserts, "
          f"{sum(b - a + 1 for a, b in windows)} frames to re-render")


if __name__ == "__main__":
    main()
