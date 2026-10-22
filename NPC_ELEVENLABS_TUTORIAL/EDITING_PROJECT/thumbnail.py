"""Branded cover images from the real ElevenLabs offer frame.

    python thumbnail.py SOURCE.mp4

Writes ../THUMBNAIL/NPC_ELEVENLABS_THUMBNAIL.png (1920x1080) and
../THUMBNAIL/NPC_ELEVENLABS_COVER_9x16.png (1080x1920). The card is the genuine frame at the
EDL freeze point (privacy masks applied); nothing on it is altered.
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


def card_crop(src):
    edl = json.loads((HERE / "edl_resolved.json").read_text())
    t = edl["freeze"]["src"]
    img = Source.still(src, t, Masks())
    title = next(h for h in edl["highlights"] if h.get("label") == "THE OFFER")["rect"]
    code = next(h for h in edl["freeze_highlights"] if h.get("label") == "NEXT STEP")["rect"]
    x0, y0, x1, y1 = 14, title[1] - 40, 868, code[3] + 40
    return img[y0:y1, x0:x1].copy()


def phone_card(card, h):
    k = h / card.shape[0]
    c = cv2.resize(card, (int(card.shape[1] * k), h), interpolation=cv2.INTER_AREA)
    a = np.zeros(c.shape[:2] + (4,), np.float32)
    a[..., :3] = c
    a[..., 3] = gfx.rr_mask(c.shape[1], c.shape[0], 24)
    return a


def compose(card, W, H, port):
    img = gfx.brand_background(W, H).copy()
    # soft red glow behind the card
    glow = np.zeros_like(img)
    cx, cy = (W * 0.5, H * 0.66) if port else (W * 0.75, H * 0.52)
    cv2.circle(glow, (int(cx), int(cy)), int(min(W, H) * 0.32), gfx.RED, -1)
    img = cv2.add(img, (cv2.GaussianBlur(glow, (0, 0), 120) * 0.35).astype(np.uint8))
    ch = int(H * (0.42 if port else 0.76))
    spr = phone_card(card, ch)
    # gentle tilt for depth
    hh, ww = spr.shape[:2]
    src_pts = np.float32([[0, 0], [ww, 0], [ww, hh], [0, hh]])
    d = ww * 0.05
    dst_pts = np.float32([[d, d * 0.6], [ww, 0], [ww, hh], [d, hh - d * 0.6]])
    M = cv2.getPerspectiveTransform(src_pts, dst_pts)
    spr = cv2.warpPerspective(spr, M, (ww, hh))
    x, y = int(cx - ww / 2), int(cy - hh / 2)
    shadow = np.zeros((hh + 80, ww + 80, 4), np.float32)
    shadow[40:-40, 40:-40, 3] = spr[..., 3] * 0.8
    shadow[..., 3] = cv2.GaussianBlur(shadow[..., 3], (0, 0), 22)
    gfx.blend(img, shadow, x - 40 + 18, y - 40 + 26)
    gfx.blend(img, spr, x, y)
    gfx.rr_outline(img, [x + d, y + 2, x + ww - 2, y + hh - 2], RED, thick=4, radius=24, glow=10)
    # headline
    if port:
        lines = [("1 MONTH", 190), ("ELEVENLABS", 150), ("CREATOR PLAN", 122)]
        ty = 170
        for i, (txt, s) in enumerate(lines):
            sp = gfx.text_sprite(txt, "black", s, IVORY if i != 1 else RED, -0.01)
            gfx.blend(img, sp, W / 2 - sp.shape[1] / 2, ty)
            ty += sp.shape[0] * 0.9
        pill = gfx.pill("STEP-BY-STEP TUTORIAL", size=34)
        gfx.blend(img, pill, W / 2 - pill.shape[1] / 2, ty + 20)
        wm = gfx.text_sprite("NPC", "black", 84, IVORY, 0.04)
        gfx.blend(img, wm, W / 2 - wm.shape[1] / 2, H - 170)
        note = gfx.text_sprite("via MLH + Hacktoberfest 2026  •  requirements apply", "medium", 32, STEEL)
        gfx.blend(img, note, W / 2 - note.shape[1] / 2, H - 70)
    else:
        lines = [("1 MONTH", 176), ("ELEVENLABS", 138), ("CREATOR", 150), ("PLAN", 150)]
        ty = 70
        for i, (txt, s) in enumerate(lines):
            sp = gfx.text_sprite(txt, "black", s, RED if i == 1 else IVORY, -0.01)
            gfx.blend(img, sp, 80, ty)
            ty += sp.shape[0] * 0.86
        pill = gfx.pill("STEP-BY-STEP TUTORIAL", size=34)
        gfx.blend(img, pill, 88, ty + 18)
        wm = gfx.text_sprite("NPC", "black", 70, IVORY, 0.04)
        gfx.blend(img, wm, W - wm.shape[1] - 70, 40)
        img[40 + int(wm.shape[0] * 0.66):40 + int(wm.shape[0] * 0.66) + 16, W - 66:W - 50] = RED
        note = gfx.text_sprite("via MLH + Hacktoberfest 2026  •  requirements apply", "medium", 30, STEEL)
        gfx.blend(img, note, 88, H - 70)
    return img


def main(src):
    card = card_crop(src)
    out = HERE.parent / "THUMBNAIL"
    out.mkdir(exist_ok=True)
    cv2.imwrite(str(out / "NPC_ELEVENLABS_THUMBNAIL.png"), compose(card, 1920, 1080, False))
    cv2.imwrite(str(out / "NPC_ELEVENLABS_COVER_9x16.png"), compose(card, 1080, 1920, True))
    print("wrote thumbnails")


if __name__ == "__main__":
    main(sys.argv[1])
