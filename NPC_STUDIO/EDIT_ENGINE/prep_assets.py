"""Prepare the three images for compositing.

    python prep_assets.py <project_dir> --models <dir with esrgan_ncnn/ and isnet-anime.onnx>

Writes to <project>/source/prepared/:
  cyberwolf_up.png      Real-ESRGAN x4 anime restoration of the 640 px original (2560 px).
                        Restoration only: same drawing, cleaner lines, JPEG noise removed.
  cyberwolf_alpha.png   character matte (IS-Net anime segmentation, guided-filter refined)
  cyberwolf_bg.png      background plate with the character inpainted out (for parallax)
  npc_alpha.png         silhouette matte from the backlight itself (dark figure vs bright sky)
  npc_bg.png            sky/window plate with the figure inpainted out
  logo_rgba.png         the original logo pixels, unchanged, with a circular alpha
  anchors.json          measured points used for framing (goggles, eyes, shirt lettering, ...)

The NPC photo and the logo are never re-synthesized: they are only sampled with
Lanczos at render time.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def guided_filter(I: np.ndarray, p: np.ndarray, r: int, eps: float) -> np.ndarray:
    """He et al. guided filter, gray guide. Snaps a coarse matte to real image edges."""
    box = lambda x: cv2.boxFilter(x, -1, (2 * r + 1, 2 * r + 1))
    mI, mp = box(I), box(p)
    a = (box(I * p) - mI * mp) / (box(I * I) - mI * mI + eps)
    b = mp - a * mI
    return box(a) * I + box(b)


def esrgan_x4(img: np.ndarray, model_dir: Path, model: str, tile: int = 128, pad: int = 16) -> np.ndarray:
    import ncnn
    net = ncnn.Net()
    net.opt.use_vulkan_compute = False
    net.opt.num_threads = 4
    net.load_param(str(model_dir / f"{model}.param"))
    net.load_model(str(model_dir / f"{model}.bin"))
    a = img.astype(np.float32) / 255.0
    H, W, _ = a.shape
    ap = np.pad(a, ((pad, pad + tile), (pad, pad + tile), (0, 0)), mode="reflect")
    out = np.zeros((H * 4, W * 4, 3), np.float32)
    for y in range(0, H, tile):
        for x in range(0, W, tile):
            t = ap[y: y + tile + 2 * pad, x: x + tile + 2 * pad]
            ex = net.create_extractor()
            ex.input("data", ncnn.Mat(np.ascontiguousarray(t.transpose(2, 0, 1))))
            _, o = ex.extract("output")
            o = np.array(o).transpose(1, 2, 0)[pad * 4:(pad + tile) * 4, pad * 4:(pad + tile) * 4]
            h, w = min(tile, H - y) * 4, min(tile, W - x) * 4
            out[y * 4: y * 4 + h, x * 4: x * 4 + w] = o[:h, :w]
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)


def isnet_anime(img: np.ndarray, onnx_path: Path) -> np.ndarray:
    import onnxruntime as ort
    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    x = cv2.resize(img, (1024, 1024), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    x = (x - np.array([0.485, 0.456, 0.406], np.float32)) / 1.0
    pred = sess.run(None, {sess.get_inputs()[0].name: x.transpose(2, 0, 1)[None]})[0][0, 0]
    pred = (pred - pred.min()) / (pred.max() - pred.min() + 1e-9)
    return pred


def inpaint_plate(img: np.ndarray, alpha: np.ndarray, work: int = 512, blur: float = 6.0) -> np.ndarray:
    """Remove the subject from the plate: inpaint a dilated hole at low res, then soften."""
    H, W = img.shape[:2]
    s = work / max(H, W)
    small = cv2.resize(img, (int(W * s), int(H * s)), interpolation=cv2.INTER_AREA)
    hole = cv2.resize((alpha > 0.08).astype(np.uint8) * 255, small.shape[1::-1], interpolation=cv2.INTER_NEAREST)
    hole = cv2.dilate(hole, np.ones((9, 9), np.uint8), iterations=2)
    filled = cv2.inpaint(small, hole, 12, cv2.INPAINT_TELEA)
    filled = cv2.GaussianBlur(filled, (0, 0), blur)
    return cv2.resize(filled, (W, H), interpolation=cv2.INTER_CUBIC)


def main(project: Path, models: Path) -> None:
    src, out = project / "source/assets", project / "source/prepared"
    out.mkdir(parents=True, exist_ok=True)
    anchors: dict = {}

    # ---------------- CYBERWOLF ----------------
    cw = np.asarray(Image.open(src / "cyberwolf.jpg").convert("RGB"))
    up_path = out / "cyberwolf_up.png"
    if not up_path.exists():
        up = esrgan_x4(cw, models / "esrgan_ncnn/models", "realesrgan-x4plus-anime")
        Image.fromarray(up).save(up_path)
    up = np.asarray(Image.open(up_path).convert("RGB"))
    pred = isnet_anime(cw, models / "isnet-anime.onnx")
    coarse = cv2.resize(pred, up.shape[1::-1], interpolation=cv2.INTER_CUBIC).astype(np.float32)
    guide = cv2.cvtColor(up, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    alpha = np.clip(guided_filter(guide, coarse, r=12, eps=1e-3), 0, 1)
    alpha = np.clip((alpha - 0.05) / 0.9, 0, 1)
    Image.fromarray((alpha * 255).astype(np.uint8)).save(out / "cyberwolf_alpha.png")
    Image.fromarray(inpaint_plate(up, alpha)).save(out / "cyberwolf_bg.png")

    # goggles: the two saturated green lenses (measured on the original, stored normalized)
    hsv = cv2.cvtColor(cw, cv2.COLOR_RGB2HSV)
    lens = (hsv[..., 0] > 30) & (hsv[..., 0] < 75) & (hsv[..., 1] > 90) & (hsv[..., 2] > 40)
    lens[:200] = False  # hair is yellow-green; lenses sit below it
    n, lab, st, cen = cv2.connectedComponentsWithStats(lens.astype(np.uint8))
    big = sorted(range(1, n), key=lambda i: -st[i, cv2.CC_STAT_AREA])[:2]
    lenses = sorted([cen[i] for i in big], key=lambda c: c[0])
    gx = float(np.mean([c[0] for c in lenses])) / cw.shape[1]
    gy = float(np.mean([c[1] for c in lenses])) / cw.shape[0]
    ys, xs = np.nonzero(alpha > 0.5)
    anchors["cyberwolf"] = {
        "size": [cw.shape[1], cw.shape[0]], "upscaled": [up.shape[1], up.shape[0]],
        "lens_left": [round(lenses[0][0] / cw.shape[1], 4), round(lenses[0][1] / cw.shape[0], 4)],
        "lens_right": [round(lenses[1][0] / cw.shape[1], 4), round(lenses[1][1] / cw.shape[0], 4)],
        "goggles": [round(gx, 4), round(gy, 4)],
        "eyes": [round(gx, 4), round(gy - 0.115, 4)],  # eye line sits ~74 px above the lens centers
        "subject_bbox": [round(xs.min() / up.shape[1], 4), round(ys.min() / up.shape[0], 4),
                         round(xs.max() / up.shape[1], 4), round(ys.max() / up.shape[0], 4)],
        "keep_out": [0.0, 0.0, 0.085, 0.105],  # artist mark in the top-left corner: framing keeps it out
    }

    # ---------------- NPC ----------------
    npc = np.asarray(Image.open(src / "npc.png").convert("RGB"))
    L = cv2.cvtColor(npc, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    # backlit silhouette: alpha from luminance (soft for translucent hair), snapped by guided filter
    a = np.clip((0.62 - L) / (0.62 - 0.30), 0, 1)
    a = cv2.morphologyEx(a, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    a = np.clip(guided_filter(L, a, r=4, eps=2e-3), 0, 1)
    # the grey shirt lettering is lighter than the figure: keep the interior fully opaque
    hard = (a > 0.5).astype(np.uint8)
    interior = cv2.GaussianBlur(cv2.erode(hard, np.ones((11, 11), np.uint8)).astype(np.float32), (0, 0), 3)
    a = np.maximum(a, interior)
    Image.fromarray((a * 255).astype(np.uint8)).save(out / "npc_alpha.png")
    Image.fromarray(inpaint_plate(npc, a, blur=8.0)).save(out / "npc_bg.png")
    torso = L[550:850, 450:950]
    yy, xx = np.nonzero(torso > np.percentile(torso, 96))
    ys, xs = np.nonzero(a[:900] > 0.5)
    H, W = L.shape
    head_rows = np.nonzero((a[:450] > 0.5).sum(1) > 20)[0]
    anchors["npc"] = {
        "size": [W, H],
        "letters_bbox": [round((xx.min() + 450) / W, 4), round((yy.min() + 550) / H, 4),
                         round((xx.max() + 450) / W, 4), round((yy.max() + 550) / H, 4)],
        "head_top": round(float(head_rows.min()) / H, 4),
        "head_center": [round(float(xs[ys < 420].mean()) / W, 4), round(210 / H, 4)],
        "figure_bbox": [round(xs.min() / W, 4), round(ys.min() / H, 4), round(xs.max() / W, 4), 1.0],
    }

    # ---------------- LOGO ----------------
    lg = np.asarray(Image.open(src / "npc_channel_logo.jpg").convert("RGB"))
    gold = (lg[..., 0] > 150) & (lg[..., 1] > 90) & (lg[..., 2] < 140)
    ys, xs = np.nonzero(gold)
    cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
    yy, xx = np.mgrid[0:lg.shape[0], 0:lg.shape[1]]
    r = np.hypot(xx - cx, yy - cy)
    Lg = lg.mean(2)
    # outer edge of the gold ring: last radius where the ring is still lit
    prof = [np.percentile(Lg[(r >= k) & (r < k + 1)], 90) for k in range(250, 330)]
    r_edge = 250 + max(i for i, v in enumerate(prof) if v > 40) + 1
    la = np.clip((r_edge + 3 - r) / 3, 0, 1)
    Image.fromarray(np.dstack([lg, (la * 255).astype(np.uint8)])).save(out / "logo_rgba.png")
    anchors["logo"] = {"size": [lg.shape[1], lg.shape[0]], "center": [round(cx / lg.shape[1], 4), round(cy / lg.shape[0], 4)],
                       "radius": round(r_edge / lg.shape[1], 4)}

    (out / "anchors.json").write_text(json.dumps(anchors, indent=1))
    print(json.dumps(anchors, indent=1))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[sys.argv.index("--models") + 1]))
