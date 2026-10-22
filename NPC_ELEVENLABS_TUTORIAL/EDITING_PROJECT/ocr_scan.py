"""Full-frame OCR scan of the source recording (every frame).

    python ocr_scan.py SOURCE.mp4 OUT_DIR [--scale S] [--workers W]

Writes OUT_DIR/ocr_<worker>.jsonl with one line per frame:
{"f": frame, "kb": keyboard_top_or_null, "same": bool, "boxes": [[x0, y0, x1, y1, score, text], ...]}
in full-resolution source pixels.

* The on-screen keyboard (detected by its colour) is excluded from OCR: it never shows page
  content, and inside the sensitive windows privacy.py masks it completely.
* A frame that is pixel-identical (mean abs diff < 0.02 and 3x3-blurred max diff <= 4, i.e. only codec noise) to the previous one reuses its
  result ("same": true). Any visible change triggers a fresh OCR.

The output contains raw on-screen text (including private data), so OUT_DIR must be a private
location outside the repository. Only derived mask geometry is ever committed.
"""
import argparse
import json
import subprocess
from multiprocessing import Process
from pathlib import Path

import cv2
import numpy as np

KB_BGR = np.array([212, 233, 250], np.int16)  # keyboard beige (Gboard theme in this recording)


def probe(src):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets",
                                   "-show_entries", "stream=width,height,nb_read_packets", "-of", "csv=p=0", src])
    w, h, n = out.decode().strip().split(",")
    return int(w), int(h), int(n)


def keyboard_top(img_bgr, scale):
    """Full-res y of the keyboard's top edge (toolbar included), or None."""
    h = img_bgr.shape[0]
    cols = img_bgr[:, :: max(1, img_bgr.shape[1] // 40)].astype(np.int16)
    frac = (np.abs(cols - KB_BGR).max(axis=2) < 16).mean(axis=1)
    # Gboard: a fully beige suggestion strip, then key rows whose gaps stay >= ~5 % beige (the numeric keypad's
    # wide keys leave only ~10 %).
    win = int(400 * scale)
    for y in range(int(600 * scale), h - win):
        if frac[y] > 0.9 and frac[y:y + win].min() > 0.04 and frac[y:y + win].mean() > 0.2:
            return max(0, int(y / scale) - 150)
    return None


def worker(src, out_dir, wid, nw, scale):
    from rapidocr_onnxruntime import RapidOCR
    ocr = RapidOCR(intra_op_num_threads=1, inter_op_num_threads=1)
    w, h, n = probe(src)
    a, b = n * wid // nw, n * (wid + 1) // nw
    sw, sh = int(w * scale) // 2 * 2, int(h * scale) // 2 * 2
    # Decode from the start and skip to the chunk so frame indices are exact (cheap at this scale).
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-threads", "2", "-i", src, "-vf", f"scale={sw}:{sh}", "-f", "rawvideo",
                          "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    cv2.setNumThreads(1)
    path = Path(out_dir) / f"ocr_{wid}.jsonl"
    done = set()
    if path.exists():  # resume: keep finished frames
        for line in open(path):
            try:
                done.add(json.loads(line)["f"])
            except ValueError:
                pass
    fh = open(path, "a")
    prev, prev_boxes, f = None, None, 0
    while True:
        buf = p.stdout.read(sw * sh * 3)
        if len(buf) < sw * sh * 3 or f >= b:
            break
        if f < a - 1:
            f += 1
            continue
        img = np.frombuffer(buf, np.uint8).reshape(sh, sw, 3)
        if f in done:
            prev, prev_boxes, f = img, None, f + 1
            continue
        if f == a - 1:  # warm the identical-frame cache with the previous frame
            prev, f = img, f + 1
            continue
        kb = keyboard_top(img, scale)
        d = np.abs(img.astype(np.int16) - prev) if prev is not None else None
        same = (prev_boxes is not None and d is not None and d.mean() < 0.02
                and int(np.abs(cv2.blur(img, (3, 3)).astype(np.int16) - cv2.blur(prev, (3, 3))).max()) <= 4)
        if same:
            boxes = prev_boxes
        else:
            region = img if kb is None else img[: int(kb * scale)]
            res, _ = ocr(region) if region.shape[0] > 20 else (None, None)
            boxes = []
            for quad, text, score in res or []:
                xs = [q[0] / scale for q in quad]
                ys = [q[1] / scale for q in quad]
                boxes.append([round(min(xs)), round(min(ys)), round(max(xs)), round(max(ys)), round(float(score), 3), text])
        fh.write(json.dumps({"f": f, "kb": kb, "same": bool(same), "boxes": boxes}) + "\n")
        fh.flush()
        prev, prev_boxes = img, boxes
        f += 1
    fh.close()
    p.kill()


if __name__ == "__main__":
    import os
    for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ.setdefault(k, "1")
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out_dir")
    ap.add_argument("--scale", type=float, default=0.5)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    Path(a.out_dir).mkdir(parents=True, exist_ok=True)
    ps = [Process(target=worker, args=(a.src, a.out_dir, i, a.workers, a.scale)) for i in range(a.workers)]
    [p.start() for p in ps]
    [p.join() for p in ps]
