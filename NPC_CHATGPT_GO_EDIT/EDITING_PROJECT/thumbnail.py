"""Branded cover (1080x1920) from the real ChatGPT Go offer frame.

    python thumbnail.py SOURCE.mp4

Writes ../THUMBNAIL/NPC_CHATGPT_GO_THUMBNAIL.png. The card is the genuine freeze frame with
privacy masks applied; nothing on it is altered.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

import gfx
from gfx import IVORY, RED, STEEL
from privacy import Masks
from render import Source

HERE = Path(__file__).parent


def main(src):
    edl = json.loads((HERE / "edl_resolved.json").read_text())
    img = Source.still(src, edl["freeze"]["src"], Masks())
    price = next(h for h in edl["highlights"] if h.get("label") == "SUCCESS")["rect"]
    claim = next(h for h in edl["freeze_highlights"] if h.get("label") == "NEXT STEP")["rect"]
    card = img[price[1] - 90:claim[3] + 40, 20:844].copy()
    W, H = 1080, 1920
    out = gfx.brand_background(W, H).copy()
    glow = np.zeros_like(out)
    cv2.circle(glow, (W // 2, int(H * 0.66)), 420, RED, -1)
    out = cv2.add(out, (cv2.GaussianBlur(glow, (0, 0), 140) * 0.4).astype(np.uint8))
    k = 960 / card.shape[1]
    c = cv2.resize(card, (960, int(card.shape[0] * k)), interpolation=cv2.INTER_AREA)
    spr = np.zeros(c.shape[:2] + (4,), np.float32)
    spr[..., :3] = c
    spr[..., 3] = gfx.rr_mask(c.shape[1], c.shape[0], 30)
    x, y = (W - c.shape[1]) // 2, int(H * 0.62 - c.shape[0] / 2)
    sh = np.zeros((c.shape[0] + 80, c.shape[1] + 80, 4), np.float32)
    sh[40:-40, 40:-40, 3] = spr[..., 3] * 0.85
    sh[..., 3] = cv2.GaussianBlur(sh[..., 3], (0, 0), 24)
    gfx.blend(out, sh, x - 22, y - 14)
    gfx.blend(out, spr, x, y)
    gfx.rr_outline(out, [x, y, x + c.shape[1], y + c.shape[0]], RED, thick=5, radius=30, glow=12)
    ty = 170
    for txt, size, col in (("CHATGPT GO", 138, IVORY), ("1 MONTH", 150, IVORY), ("FREE?", 190, RED)):
        sp = gfx.text_sprite(txt, "black", size, col, -0.01)
        gfx.blend(out, sp, W / 2 - sp.shape[1] / 2, ty)
        ty += sp.shape[0] * 0.88
    pill = gfx.pill("VIA RAPPI  •  STEP-BY-STEP", size=34)
    gfx.blend(out, pill, W / 2 - pill.shape[1] / 2, ty + 18)
    wm = gfx.text_sprite("NPC", "black", 84, IVORY, 0.04)
    gfx.blend(out, wm, W / 2 - wm.shape[1] / 2 - 10, H - 190)
    out[H - 190 + int(wm.shape[0] * 0.66):H - 190 + int(wm.shape[0] * 0.66) + 16,
        W // 2 + wm.shape[1] // 2 - 10:W // 2 + wm.shape[1] // 2 + 6] = RED
    note = gfx.text_sprite("New Go users  •  region-limited  •  terms apply", "medium", 32, STEEL)
    gfx.blend(out, note, W / 2 - note.shape[1] / 2, H - 80)
    p = HERE.parent / "THUMBNAIL" / "NPC_CHATGPT_GO_THUMBNAIL.png"
    cv2.imwrite(str(p), out)
    print("wrote", p)


if __name__ == "__main__":
    main(sys.argv[1])
