"""NPC renderer for the ChatGPT Go / Rappi tutorial (vertical 1080x1920).

    python render.py SOURCE.mp4 --out OUT.mp4 [--preview] [--stills DIR --at t1,t2,...]

Every frame is a pure function of output time (timeline.py). Source frames are decoded in
order and privacy masks are burned into each one BEFORE camera moves, transitions or blends.
--preview writes a 540x960 fast encode of the same frames.
"""
import argparse
import math
import os
import subprocess
from pathlib import Path

import cv2
import numpy as np

import gfx
from gfx import IVORY, RED, STEEL
from privacy import Masks
from timeline import Timeline

SRC_W, SRC_H, CROP = 864, 1920, 75
CW, CH = SRC_W, SRC_H - CROP          # status bar removed (clock, notifications)
W, H = 1080, 1920
SAFE_TOP, CAP_Y, CAP_ALT, NOTE_Y, LT_Y = 132, 1430, 360, 1555, 1170   # inside Shorts/Reels/TikTok UI margins


class Source:
    def __init__(self, path, masks):
        self.path, self.masks, self.p, self.idx, self.cur = path, masks, None, -1, None

    def frame(self, target):
        if self.p is None or target < self.idx:
            self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", self.path, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                                      stdout=subprocess.PIPE, bufsize=SRC_W * SRC_H * 3 * 4)
            self.idx = -1
        while self.idx < target:
            buf = self.p.stdout.read(SRC_W * SRC_H * 3)
            if len(buf) < SRC_W * SRC_H * 3:
                break
            self.idx += 1
            if self.idx == target:
                self.cur = self.masks.apply(np.frombuffer(buf, np.uint8).reshape(SRC_H, SRC_W, 3), self.idx)
        return self.cur

    @staticmethod
    def still(path, t, masks):
        f = int(round(t * 30))
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", f"select=eq(n\\,{f})", "-frames:v", "1",
                              "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True, check=True).stdout
        return masks.apply(np.frombuffer(raw, np.uint8).reshape(SRC_H, SRC_W, 3), f)


def place(fx, fy, s, ay=0.46):
    cw, ch = CW * s, CH * s
    x0 = W * 0.5 - fx * s
    y0 = H * ay - (fy - CROP) * s
    x0 = min(0, max(W - cw, x0)) if cw >= W else (W - cw) / 2
    y0 = min(0, max(H - ch, y0)) if ch >= H else (H - ch) / 2
    return x0, y0


def to_view(x, y, s, x0, y0):
    return x0 + x * s, y0 + (y - CROP) * s


def whip(img, d, dur, axis):
    """Velocity whip: outgoing frame (d<0) leaves, incoming (d>=0) arrives, with motion blur."""
    u = 1 - abs(d) / dur
    amt = gfx.ease_in_out(u)
    size = img.shape[1] if axis == 1 else img.shape[0]
    off = int((size * 0.45) * amt) * (-1 if d < 0 else 1)
    out = np.roll(img, off, axis=axis)
    k = max(1, int(140 * amt))
    out = cv2.blur(out, (k, 1) if axis == 1 else (1, k))
    return out


def zoom_blur(img, amt):
    if amt <= 0.02:
        return img
    acc = img.astype(np.float32)
    for i, k in enumerate((1.04, 1.08, 1.13)):
        z = 1 + (k - 1) * amt * 2
        M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, z)
        acc += cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT).astype(np.float32)
    return (acc / 4).astype(np.uint8)


def frame_glitch(img, amt, seed):
    r = np.random.default_rng(seed)
    out = img.copy()
    for _ in range(int(4 + 10 * amt)):
        y = int(r.integers(0, H - 40))
        hh = int(r.integers(8, 90))
        out[y:y + hh] = np.roll(out[y:y + hh], int(r.normal(0, 60 * amt)), axis=1)
    d = int(14 * amt) + 1
    out[..., 2] = np.roll(out[..., 2], d, axis=1)
    out[..., 0] = np.roll(out[..., 0], -d, axis=1)
    return out


class Renderer:
    def __init__(self, src_path):
        self.tl = Timeline()
        self.masks = Masks()
        self.src = Source(src_path, self.masks)
        self.bg = gfx.brand_background(W, H)
        e = self.tl.edl
        self.hook_img = Source.still(src_path, e["hook"]["src"], self.masks)[CROP:]
        self.freeze_img = Source.still(src_path, e["freeze"]["src"], self.masks)[CROP:]
        self.price = next(h for h in e["highlights"] if h.get("label") == "SUCCESS")["rect"]
        self.prev, self.prev_cam, self.last = None, None, None

    # ---------- shared pieces ----------
    def compose(self, content, fx, fy, z):
        s = W / CW * z
        x0, y0 = place(fx, fy, s)
        M = np.float32([[s, 0, x0], [0, s, y0]])
        img = cv2.warpAffine(content, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        covered = x0 <= 0 and y0 <= 0 and x0 + CW * s >= W and y0 + CH * s >= H
        if not covered:
            a = cv2.warpAffine(gfx.rr_mask(CW, CH, 34), M, (W, H))[..., None]
            img = (self.bg * (1 - a) + img * a).astype(np.uint8)
        return img, s, x0, y0

    def draw_highlight(self, img, h, u, s, x0, y0):
        dur = h["dur"]
        a = min(1.0, u / 0.16, (dur - u) / 0.16)
        if a <= 0:
            return
        r = h["rect"]
        X0, Y0 = to_view(r[0], r[1], s, x0, y0)
        X1, Y1 = to_view(r[2], r[3], s, x0, y0)
        k = 1 + 0.16 * (1 - gfx.ease_out(u / 0.25))
        cx, cy = (X0 + X1) / 2, (Y0 + Y1) / 2
        hw, hh = (X1 - X0) / 2 * k + 6, (Y1 - Y0) / 2 * k + 6
        rect = [cx - hw, cy - hh, cx + hw, cy + hh]
        self.avoid.append(rect)
        gfx.dim_outside(img, rect, 0.45 * a, radius=18)
        col = (90, 200, 80) if h.get("label") in ("SUCCESS",) else RED
        gfx.rr_outline(img, rect, col, thick=5, radius=18, alpha=a, glow=7)
        if h.get("label"):
            p = gfx.pill(h["label"], size=24, bg=col)
            py = rect[1] - p.shape[0] - 12 if rect[1] - p.shape[0] - 12 > SAFE_TOP + 90 else rect[3] + 12
            px = min(max(rect[0], 30), W - p.shape[1] - 30)
            gfx.blend(img, p, px, py - 10 * (1 - gfx.ease_out(u / 0.2)), a)

    def draw_tap(self, img, tp, u, s, x0, y0):
        X, Y = to_view(tp["x"], tp["y"], s, x0, y0)
        if -0.5 <= u <= 0.8:
            self.avoid.append([X - 90, Y - 90, X + 90, Y + 90])
        if not 0 <= u <= 0.6:
            return
        X, Y = int(X), int(Y)
        e = gfx.ease_out(u / 0.6)
        over = img.copy()
        cv2.circle(over, (X, Y), int(18 + 80 * e), IVORY, 4, cv2.LINE_AA)
        cv2.circle(over, (X, Y), int(10 + 46 * e), RED, 3, cv2.LINE_AA)
        if u < 0.22:
            cv2.circle(over, (X, Y), 16, RED, -1, cv2.LINE_AA)
        cv2.addWeighted(over, 1 - e, img, e, 0, dst=img)

    def free_y(self, pref, alts, half):
        for y in [pref] + alts:
            if not any(r[1] < y + half and r[3] > y - half for r in self.avoid):
                return y
        return pref

    def text_block(self, img, t, items, size, face, y, max_w, keys_color=RED, box_alpha=0.8, pop=True):
        cur = [c for c in items if c["t0"] <= t < c["t1"]]
        if not cur:
            return
        c = cur[0]
        u, left = t - c["t0"], c["t1"] - t
        keys = {k.lower() for k in c.get("keys", [])}
        words = c["text"].split()
        spr = [gfx.text_sprite(w, face, size, keys_color if w.lower().strip(".,!:()") in keys else IVORY, pad=4)
               for w in words]
        space = int(size * 0.28)
        lines, line, lw = [], [], 0
        for i, sp in enumerate(spr):
            if line and lw + space + sp.shape[1] > max_w:
                lines.append(line)
                line, lw = [], 0
            line.append(i)
            lw += (space if len(line) > 1 else 0) + sp.shape[1]
        lines.append(line)
        lh = int(size * 1.2)
        widths = [sum(spr[i].shape[1] for i in ln) + space * (len(ln) - 1) for ln in lines]
        bw, th = max(widths) + 50, lh * len(lines)
        ex = min(1.0, left / 0.15)
        en = gfx.ease_out(u / 0.18)
        gfx.glass(img, [W / 2 - bw / 2, y - th / 2 - 18 + 8 * (1 - en), W / 2 + bw / 2, y + th / 2 + 18],
                  alpha=box_alpha * min(en, ex), radius=22)
        for li, ln in enumerate(lines):
            x = W / 2 - widths[li] / 2
            yy = y - th / 2 + li * lh + (lh - spr[0].shape[0]) / 2
            for i in ln:
                sp = spr[i]
                wu = (u - i * 0.045) / 0.16 if pop else 1.0
                if wu > 0:
                    k = 0.72 + 0.28 * gfx.ease_out_back(wu) if pop else 1.0
                    ss = gfx.scale_sprite(sp, k)
                    gfx.blend(img, ss, x + (sp.shape[1] - ss.shape[1]) / 2,
                              yy + (sp.shape[0] - ss.shape[0]) / 2 + 12 * (1 - gfx.ease_out(wu)), min(1.0, wu * 1.7) * ex)
                x += sp.shape[1] + space

    def hud(self, img, t):
        tl = self.tl
        p = min(1.0, max(0.0, (t - tl.video_start) / (tl.outro_start - tl.video_start)))
        img[0:6] = (img[0:6] * 0.5).astype(np.uint8)
        img[0:6, :int(W * p)] = RED
        g = np.linspace(0.6, 0, 300, dtype=np.float32)[:, None, None]
        img[:300] = (img[:300] * (1 - g)).astype(np.uint8)
        ct, num, title = tl.chapter(t)
        u = t - ct
        a = gfx.ease_out(u / 0.3)
        pl = gfx.pill(f"STEP {num}", size=26)
        gfx.blend(img, pl, 40 - 30 * (1 - a), SAFE_TOP, a)
        ts = gfx.text_sprite(title, "black", 34, IVORY, 0.01)
        if u < 0.3:
            ts = gfx.glitch(ts, 1 - u / 0.3, int(ct * 10))
        gfx.blend(img, ts, 40 + pl.shape[1] + 14, SAFE_TOP + (pl.shape[0] - ts.shape[0]) / 2, a)
        wm = gfx.text_sprite("NPC", "black", 40, IVORY, 0.04)
        gfx.blend(img, wm, W - 40 - wm.shape[1] - 13, 52, 0.82)
        yy = int(52 + wm.shape[0] * 0.66)
        img[yy:yy + 9, W - 49:W - 40] = RED
        for a0, b0, sp in tl.speedups:
            if a0 <= t < b0:
                al = min(1.0, (t - a0) / 0.12, (b0 - t) / 0.12)
                txt = gfx.text_sprite(f"{sp:.0f}x FAST-FORWARD", "mono", 22, IVORY, 0.1)
                x, y = 40, SAFE_TOP + 62
                gfx.glass(img, [x, y, x + txt.shape[1] + 58, y + 38], alpha=0.7 * al, radius=19)
                over = img.copy()
                for k in range(2):
                    px = x + 15 + k * 12
                    cv2.fillPoly(over, [np.array([[px, y + 10], [px, y + 28], [px + 11, y + 19]], np.int32)], RED, cv2.LINE_AA)
                cv2.addWeighted(over, al, img, 1 - al, 0, dst=img)
                gfx.blend(img, txt, x + 46, y + (38 - txt.shape[0]) / 2, al)
                break

    def lower_third(self, img, t):
        for lt in self.tl.lower_thirds:
            t0 = self.tl.video_start + lt["out"]
            u = t - t0
            if not 0 <= u <= lt["dur"]:
                continue
            ai, ao = gfx.ease_out(u / 0.35), gfx.ease_in_out(min(1.0, (lt["dur"] - u) / 0.3))
            a = min(ai, ao)
            dx = -80 * (1 - ai) - 80 * (1 - ao)
            x, y, w, h = 40 + dx, LT_Y, 560, 140
            gfx.glass(img, [x, y, x + w, y + h], alpha=0.85 * a, radius=20)
            lw = int((w - 52) * gfx.ease_out((u - 0.15) / 0.45))
            if lw > 0:
                over = img.copy()
                over[int(y + 84):int(y + 88), int(x + 26):int(x + 26 + lw)] = RED
                cv2.addWeighted(over, a, img, 1 - a, 0, dst=img)
            nm = gfx.text_sprite("NPC", "black", 64, IVORY, 0.03)
            if u < 0.35:
                nm = gfx.glitch(nm, 1 - u / 0.35, int(u * 30))
            gfx.blend(img, nm, x + 22, y + 6, a)
            tg = gfx.text_sprite("AI TOOLS  •  PREMIUM TUTORIALS", "mono", 23, IVORY, 0.14)
            gfx.blend(img, tg, x + 26, y + 96, a * gfx.ease_out((u - 0.25) / 0.35))

    def chapter_card(self, img, t):
        for ct, num, title in self.tl.chapters[1:]:
            u = t - ct
            if not 0 <= u <= 1.0:
                continue
            a = min(gfx.ease_out(u / 0.2), gfx.ease_in_out((1.0 - u) / 0.25))
            big = gfx.text_sprite(title, "black", 56, IVORY)
            if u < 0.25:
                big = gfx.glitch(big, 1 - u / 0.25, int(ct * 13))
            lab = gfx.text_sprite(f"STEP {num}", "mono", 28, RED, 0.3)
            w, h = max(big.shape[1], lab.shape[1]) + 70, big.shape[0] + lab.shape[0] + 44
            cy = self.free_y(860, [600, 1100], h / 2 + 10)
            dy = 26 * (1 - gfx.ease_out(u / 0.3))
            gfx.glass(img, [W / 2 - w / 2, cy - h / 2 + dy, W / 2 + w / 2, cy + h / 2 + dy], alpha=0.86 * a, radius=24)
            gfx.blend(img, lab, W / 2 - lab.shape[1] / 2, cy - h / 2 + dy + 18, a)
            gfx.blend(img, big, W / 2 - big.shape[1] / 2, cy - h / 2 + dy + 22 + lab.shape[0], a)

    def transitions(self, img, t):
        for k, (tc, name) in enumerate(self.tl.cuts + [(self.tl.video_start, "whip_left_hook")]):
            d = t - tc
            if name.startswith("whip") and abs(d) < 0.2:
                img = whip(img, d, 0.2, 0 if name == "whip_up" else 1)
            elif name == "zoom_punch" and abs(d) < 0.18:
                img = zoom_blur(img, 1 - abs(d) / 0.18)
            elif name == "glitch" and abs(d) < 0.16:
                img = frame_glitch(img, 1 - abs(d) / 0.16, int(t * 30))
            elif name in ("impact", "freeze") and abs(d) < 0.16:
                amt = 1 - abs(d) / 0.16
                img = zoom_blur(img, amt * 0.7)
                cv2.addWeighted(img, 1 - 0.45 * amt, np.full_like(img, IVORY), 0.45 * amt, 0, dst=img)
            elif name == "flash" and abs(d) < 0.1:
                a = 0.4 * (1 - abs(d) / 0.1)
                cv2.addWeighted(img, 1 - a, np.full_like(img, IVORY), a, 0, dst=img)
        for ta in self.tl.alerts:
            d = t - ta
            if 0 <= d < 0.22:
                img = frame_glitch(img, 0.6 * (1 - d / 0.22), int(t * 31))
                red = np.zeros_like(img)
                red[:] = RED
                cv2.addWeighted(img, 1 - 0.22 * (1 - d / 0.22), red, 0.22 * (1 - d / 0.22), 0, dst=img)
        return img

    # ---------- frames ----------
    def frame(self, fr):
        if fr.kind == "hook":
            img = self.hook(fr.t)
            return self.transitions(img, fr.t)
        if fr.kind == "outro":
            return self.outro(fr.t - self.tl.outro_start)
        t = fr.t
        content = self.freeze_img if fr.kind == "freeze" else self.src.frame(min(int(round(fr.src * 30)), 2758))[CROP:]
        fx, fy, z = self.tl.cam(t)
        for tc, name in self.tl.cuts:
            if name in ("impact", "zoom_punch") and abs(t - tc) < 0.3:
                z *= 1 + 0.06 * (1 - abs(t - tc) / 0.3)
        for tp in self.tl.taps:  # click punch
            d = t - tp["t0"]
            if 0 <= d < 0.25:
                z *= 1 + 0.025 * math.sin(math.pi * d / 0.25)
        img, s, x0, y0 = self.compose(content, fx, fy, z)
        cam = (fx, fy, z)
        if self.prev is not None and self.prev_cam is not None:
            v = abs(z - self.prev_cam[2]) * 60 + abs(fy - self.prev_cam[1]) / 40 + abs(fx - self.prev_cam[0]) / 40
            if v > 0.5:
                a = min(0.18, (v - 0.5) * 0.2)
                img = cv2.addWeighted(img, 1 - a, self.prev, a, 0)
        self.prev, self.prev_cam = img, cam
        img = img.copy()
        self.avoid = []
        for h in self.tl.highlights:
            u = t - h["t0"]
            if 0 <= u <= h["dur"]:
                self.draw_highlight(img, h, u, s, x0, y0)
        for tp in self.tl.taps:
            self.draw_tap(img, tp, t - tp["t0"], s, x0, y0)
        img = self.transitions(img, t)
        self.hud(img, t)
        self.chapter_card(img, t)
        self.lower_third(img, t)
        cy = self.free_y(CAP_Y, [CAP_ALT, 560], 80)
        self.text_block(img, t, self.tl.captions, 52, "xbold", cy, 880)
        ny = NOTE_Y if cy == CAP_Y else CAP_ALT + 125
        self.text_block(img, t, self.tl.notes, 27, "medium", ny, 900, keys_color=IVORY, box_alpha=0.72, pop=False)
        return img

    def hook(self, t):
        e = self.tl.edl["hook"]
        dur = e["duration"]
        r = self.price
        fx, fy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
        z = 1.05 + 0.4 * gfx.ease_in_out(t / dur)
        shake = 0
        for hit in (0.12, 0.40):
            if hit <= t < hit + 0.22:
                shake += 14 * (1 - (t - hit) / 0.22) * math.sin((t - hit) * 95)
        img, s, x0, y0 = self.compose(self.hook_img, fx, fy + shake / 2, z)
        dark = 0.62 - 0.32 * gfx.ease_out((t - 1.0) / 0.6)
        img = (img * (1 - dark)).astype(np.uint8)
        if t < 0.5:
            img = cv2.GaussianBlur(img, (0, 0), 1 + 10 * (1 - t / 0.5))
        if t < 0.1:
            img = (img * (t / 0.1)).astype(np.uint8)
        # price highlight once the title has landed
        if t > 0.9:
            u = t - 0.9
            self.avoid = []
            self.draw_highlight(img, {"rect": r, "dur": dur - 0.9 + 0.3, "label": None}, u, s, x0, y0)
        # electric streak
        if 0.08 <= t <= 0.6:
            u = (t - 0.08) / 0.52
            x = -300 + (W + 600) * gfx.ease_in_out(u)
            over = np.zeros_like(img)
            yy = int(H * 0.27)
            cv2.line(over, (int(x - 500), yy), (int(x), yy), RED, 10, cv2.LINE_AA)
            over = cv2.GaussianBlur(over, (0, 0), 8)
            pts = [(int(x - 260 + i * 26), yy + int(np.random.default_rng(int(t * 90) + i).normal(0, 7))) for i in range(11)]
            for p0, p1 in zip(pts, pts[1:]):
                cv2.line(over, p0, p1, IVORY, 3, cv2.LINE_AA)
            cv2.add(img, over, dst=img)
        l1, l2 = e["title"]
        for i, (txt, t0, size) in enumerate(((l1, 0.10, 150), (l2, 0.36, 118))):
            u = (t - t0) / 0.22
            if u <= 0:
                continue
            if i == 0:
                sp = gfx.text_sprite(txt, "black", size, IVORY, -0.01)
            else:  # "1 MONTH" ivory + "FREE?" red
                a_, b_ = txt.rsplit(" ", 1)
                s1 = gfx.text_sprite(a_ + " ", "black", size, IVORY, -0.01)
                s2 = gfx.text_sprite(b_, "black", size, RED, -0.01)
                hh = max(s1.shape[0], s2.shape[0])
                sp = np.zeros((hh, s1.shape[1] + s2.shape[1], 4), np.float32)
                sp[:s1.shape[0], :s1.shape[1]] = s1
                sp[:s2.shape[0], s1.shape[1]:] = s2
            if u < 0.8:
                sp = gfx.glitch(sp, 1 - u / 0.8, int(t * 60) + i)
            k = 1.0 + 0.55 * (1 - gfx.ease_out_back(min(1.0, u)))
            ss = gfx.scale_sprite(sp, k)
            y = 290 + i * 205
            gfx.blend(img, ss, W / 2 - ss.shape[1] / 2 + shake, y - (ss.shape[0] - sp.shape[0]) / 2, min(1.0, u * 2.5))
        if t > 0.75:
            tag = gfx.pill("VIA RAPPI  •  " + e["tag"].upper(), size=24, bg=(20, 20, 20))
            gfx.blend(img, tag, W / 2 - tag.shape[1] / 2, 660, gfx.ease_out((t - 0.75) / 0.25))
        wm = gfx.text_sprite("NPC", "black", 40, IVORY, 0.04)
        gfx.blend(img, wm, W - 40 - wm.shape[1] - 13, 52, 0.82 * gfx.ease_out((t - 0.5) / 0.3))
        return img

    def outro(self, u):
        dur = self.tl.edl["outro"]["duration"]
        img = self.bg.copy()
        big = gfx.text_sprite("NPC", "black", 280, IVORY, 0.04)
        if u < 0.35:
            big = gfx.glitch(big, 1 - u / 0.35, int(u * 60))
        a = gfx.ease_out((u - 0.04) / 0.22)
        k = 0.9 + 0.1 * gfx.ease_out_back((u - 0.04) / 0.35)
        sb = gfx.scale_sprite(big, k)
        cy = H * 0.42
        gfx.blend(img, sb, W / 2 - sb.shape[1] / 2 - 18, cy - sb.shape[0] / 2, a)
        if u > 0.25 and int(u * 5) % 2 == 0:
            bx, by = int(W / 2 + sb.shape[1] / 2 - 6), int(cy + sb.shape[0] * 0.12)
            img[by:by + int(sb.shape[0] * 0.3), bx:bx + 30] = RED
        lw = int(600 * gfx.ease_out((u - 0.3) / 0.35))
        if lw > 0:
            yy = int(cy + sb.shape[0] / 2 + 8)
            img[yy:yy + 6, W // 2 - lw // 2:W // 2 + lw // 2] = RED
        tg = gfx.text_sprite("MORE AI TUTORIALS", "mono", 46, IVORY, 0.22)
        ta = gfx.ease_out((u - 0.35) / 0.3)
        gfx.blend(img, tg, W / 2 - tg.shape[1] / 2, cy + sb.shape[0] / 2 + 40 + 14 * (1 - ta), ta)
        if u < 0.22 and self.last is not None:
            b = 1 - gfx.ease_in_out(u / 0.22)
            img = cv2.addWeighted(img, 1 - b, zoom_blur(self.last, b), b, 0)
        if u > dur - 0.25:
            img = (img * (1 - gfx.ease_in_out((u - (dur - 0.25)) / 0.25))).astype(np.uint8)
        return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--out")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--stills")
    ap.add_argument("--at", default="")
    a = ap.parse_args()
    r = Renderer(a.src)
    tl = r.tl
    if a.stills:
        Path(a.stills).mkdir(parents=True, exist_ok=True)
        want = sorted({min(len(tl.frames) - 1, int(round(float(x) * tl.fps))) for x in a.at.split(",") if x})
        for fr in tl.frames:
            if fr.i > want[-1]:
                break
            if fr.i in want:
                r.prev = None
                cv2.imwrite(f"{a.stills}/{fr.t:06.2f}.jpg", r.frame(fr), [cv2.IMWRITE_JPEG_QUALITY, 88])
            elif fr.kind == "video":
                r.src.frame(min(int(round(fr.src * 30)), 2758))
        return
    ow, oh = (540, 960) if a.preview else (W, H)
    tmp = f"{a.out}.{os.getpid()}.part.mp4"
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{ow}x{oh}",
                            "-r", str(tl.fps), "-i", "-", "-c:v", "libx264", "-preset", "veryfast" if a.preview else "medium",
                            "-crf", "26" if a.preview else "17", "-pix_fmt", "yuv420p", "-color_range", "tv",
                            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                            "-movflags", "+faststart", tmp], stdin=subprocess.PIPE)
    for fr in tl.frames:
        img = r.frame(fr)
        if fr.kind != "outro":
            r.last = img
        if a.preview:
            img = cv2.resize(img, (ow, oh), interpolation=cv2.INTER_AREA)
        enc.stdin.write(np.ascontiguousarray(img).tobytes())
        if fr.i % 150 == 0:
            print(f"frame {fr.i}/{len(tl.frames)}", flush=True)
    enc.stdin.close()
    if enc.wait() != 0:
        raise SystemExit("encoder failed")
    os.replace(tmp, a.out)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
