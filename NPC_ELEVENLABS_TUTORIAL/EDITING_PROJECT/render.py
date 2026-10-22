"""NPC tutorial renderer: EDL + source recording + privacy masks -> finished picture.

    python render.py SOURCE.mp4 --layout 9x16|16x9 --out OUT.mp4 [--frames a:b] [--stills DIR --at t1,t2,...]

Every frame is a pure function of the output time (timeline.py). The source is decoded
sequentially, privacy masks are burned into each source frame *before* any zoom, blend or
transition, and only then is the frame placed by the camera.
"""
import argparse
import math
import subprocess
from pathlib import Path

import cv2
import numpy as np

import gfx
from gfx import IVORY, RED, STEEL, INK
from privacy import Masks
from timeline import Timeline

SRC_W, SRC_H, CROP = 882, 1920, 100
CW, CH = SRC_W, SRC_H - CROP  # content (status bar removed: it shows the recorder's timer)


# ───────────────────────── source access ─────────────────────────

class Source:
    def __init__(self, path, masks):
        self.path, self.masks = path, masks
        self.p = None
        self.idx = -1
        self.cur = None
        self.recent = []

    def _open(self):
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", self.path, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                                  stdout=subprocess.PIPE, bufsize=SRC_W * SRC_H * 3 * 4)
        self.idx = -1

    def frames_upto(self, target):
        """Advance to frame `target`; return the masked frames passed on the way (max 3, newest last)."""
        if self.p is None or target < self.idx:
            self._open()
        passed = []
        while self.idx < target:
            buf = self.p.stdout.read(SRC_W * SRC_H * 3)
            if len(buf) < SRC_W * SRC_H * 3:
                break
            self.idx += 1
            if target - self.idx < 3:
                passed.append(self.masks.apply(np.frombuffer(buf, np.uint8).reshape(SRC_H, SRC_W, 3), self.idx))
        if passed:
            self.cur = passed[-1]
        return passed or [self.cur]

    @staticmethod
    def still(path, t, masks):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1", "-f", "rawvideo",
                              "-pix_fmt", "bgr24", "-"], capture_output=True, check=True).stdout
        return masks.apply(np.frombuffer(raw, np.uint8).reshape(SRC_H, SRC_W, 3), int(round(t * 30)))


# ───────────────────────── camera ─────────────────────────

def place(fx, fy, s, vw, vh, ax=0.5, ay=0.5):
    """Top-left of the content in view coords so source point (fx, fy) lands at (ax*vw, ay*vh),
    clamped so the content never exposes an edge when it is larger than the view."""
    cw, ch = CW * s, CH * s
    x0 = vw * ax - fx * s
    y0 = vh * ay - (fy - CROP) * s
    x0 = min(0, max(vw - cw, x0)) if cw >= vw else (vw - cw) / 2
    y0 = min(0, max(vh - ch, y0)) if ch >= vh else (vh - ch) / 2
    return x0, y0


def warp_content(content, s, x0, y0, vw, vh):
    M = np.float32([[s, 0, x0], [0, s, y0]])
    interp = cv2.INTER_AREA if s < 0.75 else cv2.INTER_LINEAR
    img = cv2.warpAffine(content, M, (vw, vh), flags=interp, borderMode=cv2.BORDER_CONSTANT)
    covered = x0 <= 0 and y0 <= 0 and x0 + CW * s >= vw and y0 + CH * s >= vh
    alpha = None
    if not covered:
        alpha = cv2.warpAffine(gfx.rr_mask(CW, CH, 34), M, (vw, vh), flags=cv2.INTER_LINEAR)
    return img, alpha


def to_view(x, y, s, x0, y0):
    return x0 + x * s, y0 + (y - CROP) * s


# ───────────────────────── renderer ─────────────────────────

class Renderer:
    def __init__(self, src_path, layout):
        self.tl = Timeline()
        self.layout = layout
        self.W, self.H = (1080, 1920) if layout == "9x16" else (1920, 1080)
        self.masks = Masks()
        self.src = Source(src_path, self.masks)
        self.src_path = src_path
        self.bg = gfx.brand_background(self.W, self.H)
        self.freeze_img = Source.still(src_path, self.tl.edl["freeze"]["src"], self.masks)
        self.prev_video = None
        self.prev_cam = None
        self.last_idx = -1

    # ---------- shared overlay pieces ----------

    def active(self, items, t, dur_key="dur"):
        return [(h, t - h["t0"]) for h in items if 0 <= t - h["t0"] <= h[dur_key]]

    def draw_highlight(self, img, h, u, s, x0, y0, ox=0, oy=0, dim=True, label=True, thick=5):
        dur = h["dur"]
        a = min(1.0, u / 0.22, (dur - u) / 0.2)
        if a <= 0:
            return
        r = h["rect"]
        X0, Y0 = to_view(r[0], r[1], s, x0, y0)
        X1, Y1 = to_view(r[2], r[3], s, x0, y0)
        k = 1 + 0.14 * (1 - gfx.ease_out(u / 0.3))
        cx, cy = (X0 + X1) / 2, (Y0 + Y1) / 2
        hw, hh = (X1 - X0) / 2 * k + 6, (Y1 - Y0) / 2 * k + 6
        rect = [cx - hw + ox, cy - hh + oy, cx + hw + ox, cy + hh + oy]
        if hasattr(self, "avoid"):
            self.avoid.append(rect)
        if dim:
            gfx.dim_outside(img, rect, 0.42 * a, radius=16)
        gfx.rr_outline(img, rect, RED, thick=thick, radius=16, alpha=a, glow=6)
        if label and h.get("label"):
            p = gfx.pill(h["label"], size=24 if self.layout == "9x16" else 20)
            py = rect[1] - p.shape[0] - 12 if rect[1] - p.shape[0] - 12 > 150 else rect[3] + 12
            px = min(max(rect[0], 20), img.shape[1] - p.shape[1] - 20)
            gfx.blend(img, p, px, py - 10 * (1 - gfx.ease_out(u / 0.25)), a)

    def draw_tap(self, img, tp, u, s, x0, y0, ox=0, oy=0, scale=1.0):
        if -0.6 <= u <= 0.9 and hasattr(self, "avoid"):
            X, Y = to_view(tp["x"], tp["y"], s, x0, y0)
            self.avoid.append([X + ox - 90, Y + oy - 90, X + ox + 90, Y + oy + 90])
        if not 0 <= u <= 0.65:
            return
        X, Y = to_view(tp["x"], tp["y"], s, x0, y0)
        X, Y = int(X + ox), int(Y + oy)
        e = gfx.ease_out(u / 0.65)
        over = img.copy()
        cv2.circle(over, (X, Y), int((16 + 70 * e) * scale), IVORY, max(2, int(4 * scale)), cv2.LINE_AA)
        cv2.circle(over, (X, Y), int((10 + 40 * e) * scale), RED, max(2, int(3 * scale)), cv2.LINE_AA)
        if u < 0.25:
            cv2.circle(over, (X, Y), int(14 * scale), RED, -1, cv2.LINE_AA)
        a = 1 - e
        cv2.addWeighted(over, a, img, 1 - a, 0, dst=img)

    def free_y(self, preferred, alts, half_h):
        """First caption/card centre whose band does not cover an active highlight or tap."""
        for y in [preferred] + alts:
            if not any(r[1] < y + half_h and r[3] > y - half_h for r in getattr(self, "avoid", [])):
                return y
        return preferred

    def captions(self, img, t, box, size, max_w):
        """Word-pop captions with keyword emphasis, inside `box` (x0, y_center, x1)."""
        cur = [c for c in self.tl.captions if c["t0"] <= t < c["t1"]]
        if not cur:
            return
        c = cur[0]
        u, left = t - c["t0"], c["t1"] - t
        keys = {k.lower().strip(".,!:") for k in c.get("keys", [])}
        words = c["text"].split()
        sprites = []
        for w in words:
            hot = w.lower().strip(".,!:()") in keys
            sprites.append(gfx.text_sprite(w, "xbold", size, RED if hot else IVORY, pad=4))
        space = int(size * 0.28)
        lines, line, lw = [], [], 0
        for i, sp in enumerate(sprites):
            ww = sp.shape[1]
            if line and lw + space + ww > max_w:
                lines.append(line)
                line, lw = [], 0
            line.append(i)
            lw += (space if len(line) > 1 else 0) + ww
        lines.append(line)
        lh = int(size * 1.22)
        bx0, cy, bx1 = box
        total_h = lh * len(lines)
        widths = [sum(sprites[i].shape[1] for i in ln) + space * (len(ln) - 1) for ln in lines]
        bw = max(widths) + 56
        exit_a = min(1.0, left / 0.18)
        enter = gfx.ease_out(u / 0.2)
        mid = (bx0 + bx1) / 2
        gfx.glass(img, [mid - bw / 2, cy - total_h / 2 - 22 + 8 * (1 - enter), mid + bw / 2, cy + total_h / 2 + 22],
                  alpha=0.78 * min(enter, exit_a), radius=24)
        img_h = sprites[0].shape[0]
        for li, ln in enumerate(lines):
            x = mid - widths[li] / 2
            y = cy - total_h / 2 + li * lh + (lh - img_h) / 2
            for i in ln:
                sp = sprites[i]
                wu = (u - i * 0.055) / 0.2
                if wu <= 0:
                    x += sp.shape[1] + space
                    continue
                k = 0.7 + 0.3 * gfx.ease_out_back(wu)
                ssp = gfx.scale_sprite(sp, k)
                gfx.blend(img, ssp, x + (sp.shape[1] - ssp.shape[1]) / 2,
                          y + (sp.shape[0] - ssp.shape[0]) / 2 + 14 * (1 - gfx.ease_out(wu)),
                          min(1.0, wu * 1.6) * exit_a)
                x += sp.shape[1] + space

    def step_badge(self, img, t, x, y, title_size, stack=False):
        ct, num, title = self.tl.chapter(t)
        p = gfx.pill(f"STEP {num}", size=26 if self.layout == "9x16" else 24)
        u = t - ct
        a = gfx.ease_out(u / 0.4)
        gfx.blend(img, p, x - 30 * (1 - a), y, a)
        ts = gfx.text_sprite(title, "black", title_size, IVORY, 0.01)
        if u < 0.35:
            ts = gfx.glitch(ts, 1 - u / 0.35, int(ct * 10))
        if stack:
            gfx.blend(img, ts, x - 6, y + p.shape[0] + 10, a)
        else:
            gfx.blend(img, ts, x + p.shape[1] + 14, y + (p.shape[0] - ts.shape[0]) / 2, a)
        return p.shape[0]

    def speed_badge(self, img, t, x, y):
        for a, b, sp in self.tl.speedups:
            if a <= t < b:
                al = min(1.0, (t - a) / 0.2, (b - t) / 0.2)
                txt = gfx.text_sprite(f"{sp:.1f}x  FAST-FORWARD".replace(".0x", "x"), "mono", 22, IVORY, 0.1)
                w = txt.shape[1] + 62
                gfx.glass(img, [x, y, x + w, y + 40], alpha=0.7 * al, radius=20)
                for k in range(2):
                    px = x + 16 + k * 13
                    pts = np.array([[px, y + 11], [px, y + 29], [px + 12, y + 20]], np.int32)
                    over = img.copy()
                    cv2.fillPoly(over, [pts], RED, cv2.LINE_AA)
                    cv2.addWeighted(over, al, img, 1 - al, 0, dst=img)
                gfx.blend(img, txt, x + 48, y + (40 - txt.shape[0]) / 2, al)
                return

    def watermark(self, img, x_right, y, size=40, alpha=0.88):
        t = gfx.text_sprite("NPC", "black", size, IVORY, 0.04)
        x = x_right - t.shape[1] - size * 0.32
        gfx.blend(img, t, x, y, alpha)
        d = int(size * 0.22)
        yy = int(y + t.shape[0] * 0.66)
        img[yy:yy + d, int(x_right - d):int(x_right)] = RED

    def lower_third(self, img, t, x, y, scale=1.0):
        for lt in self.tl.lower_thirds:
            t0 = self.tl.video_start + lt["out"]
            u = t - t0
            if not 0 <= u <= lt["dur"]:
                continue
            a_in = gfx.ease_out(u / 0.45)
            a_out = gfx.ease_in_out(min(1.0, (lt["dur"] - u) / 0.35))
            a = min(a_in, a_out)
            dx = -80 * (1 - a_in) - 80 * (1 - a_out)
            w, h = int(520 * scale), int(146 * scale)
            gfx.glass(img, [x + dx, y, x + dx + w, y + h], alpha=0.82 * a, radius=int(20 * scale))
            line_w = int((w - 56 * scale) * gfx.ease_out((u - 0.2) / 0.5))
            if line_w > 0:
                yy = int(y + 86 * scale)
                xx = int(x + dx + 28 * scale)
                over = img.copy()
                over[yy:yy + max(2, int(4 * scale)), xx:xx + line_w] = RED
                cv2.addWeighted(over, a, img, 1 - a, 0, dst=img)
            name = gfx.text_sprite("NPC", "black", int(66 * scale), IVORY, 0.03)
            if u < 0.4:
                name = gfx.glitch(name, 1 - u / 0.4, int(t0 * 7) + int(u * 30))
            gfx.blend(img, name, x + dx + 22 * scale, y + 6 * scale, a)
            tag = gfx.text_sprite("TECH  •  AI  •  TUTORIALS", "mono", int(24 * scale), IVORY, 0.16)
            gfx.blend(img, tag, x + dx + 26 * scale, y + 98 * scale, a * gfx.ease_out((u - 0.3) / 0.4))

    def chapter_card(self, img, t, cx, cy, scale=1.0):
        for ct, num, title in self.tl.chapters:
            u = t - ct
            if not 0 <= u <= 1.7:
                continue
            a = min(gfx.ease_out(u / 0.3), gfx.ease_in_out((1.7 - u) / 0.3))
            big = gfx.text_sprite(title, "black", int(58 * scale), IVORY, 0.0)
            if u < 0.3:
                big = gfx.glitch(big, 1 - u / 0.3, int(ct * 13))
            lab = gfx.text_sprite(f"STEP {num}", "mono", int(30 * scale), RED, 0.3)
            w = max(big.shape[1], lab.shape[1]) + int(80 * scale)
            h = big.shape[0] + lab.shape[0] + int(54 * scale)
            dy = 30 * (1 - gfx.ease_out(u / 0.35))
            gfx.glass(img, [cx - w / 2, cy - h / 2 + dy, cx + w / 2, cy + h / 2 + dy], alpha=0.85 * a, radius=26)
            bar = int((w - 80 * scale) * gfx.ease_out((u - 0.1) / 0.5))
            yy = int(cy - h / 2 + dy + 18 * scale)
            if bar > 0:
                over = img.copy()
                over[yy:yy + 4, int(cx - bar / 2):int(cx + bar / 2)] = RED
                cv2.addWeighted(over, a, img, 1 - a, 0, dst=img)
            gfx.blend(img, lab, cx - lab.shape[1] / 2, cy - h / 2 + dy + 26 * scale, a)
            gfx.blend(img, big, cx - big.shape[1] / 2, cy - h / 2 + dy + 26 * scale + lab.shape[0] + 4, a)

    def progress(self, img, t):
        tl = self.tl
        p = min(1.0, max(0.0, (t - tl.video_start) / (tl.outro_start - tl.video_start)))
        img[0:6] = (img[0:6] * 0.6 + np.array((60, 60, 60)) * 0.4).astype(np.uint8)
        img[0:6, : int(self.W * p)] = RED

    def flash(self, img, t):
        tl = self.tl
        for c in tl.cuts + [tl.freeze_start]:
            d = abs(t - c)
            if d < 0.12:
                a = 0.32 * (1 - d / 0.12)
                cv2.addWeighted(img, 1 - a, np.full_like(img, IVORY), a, 0, dst=img)

    # ---------- video frame source ----------

    def source_content(self, fr):
        if fr.kind == "freeze":
            img = self.freeze_img
        else:
            idx = min(int(round(fr.src * 30)), 3678)
            img = self.src.frames_upto(idx)[-1]  # no frame averaging: it ghosts scrolling text
        return img[CROP:]

    def cam(self, t):
        fx, fy, z = self.tl.cam(t)
        for c in self.tl.cuts:
            d = abs(t - c)
            if d < 0.16:
                z *= 1 + 0.05 * (1 - d / 0.16)
        u = t - self.tl.video_start
        if 0 <= u < 0.5:
            z *= 1 + 0.22 * (1 - gfx.ease_out(u / 0.5))
        return fx, fy, z

    # ---------- layouts ----------

    def frame(self, fr):
        if fr.kind == "intro":
            return self.intro(fr.t)
        if fr.kind == "outro":
            return self.outro(fr.t - self.tl.outro_start)
        return self.frame_9x16(fr) if self.layout == "9x16" else self.frame_16x9(fr)

    def motion_blur(self, img, cam):
        if self.prev_video is not None and self.prev_cam is not None:
            v = abs(cam[2] - self.prev_cam[2]) * 60 + abs(cam[1] - self.prev_cam[1]) / 40
            if v > 0.4 and self.prev_video.shape == img.shape:
                a = min(0.25, (v - 0.4) * 0.3)
                img = cv2.addWeighted(img, 1 - a, self.prev_video, a, 0)
        self.prev_video, self.prev_cam = img, cam
        return img

    def frame_9x16(self, fr):
        t, W, H = fr.t, self.W, self.H
        content = self.source_content(fr)
        fx, fy, z = cam = self.cam(t)
        s = W / CW * z
        x0, y0 = place(fx, fy, s, W, H, 0.5, 0.47)
        warped, alpha = warp_content(content, s, x0, y0, W, H)
        img = self.bg.copy()
        if alpha is None:
            img = warped
        else:
            a = alpha[..., None]
            img = (img * (1 - a) + warped * a).astype(np.uint8)
            edge = cv2.dilate(alpha, np.ones((5, 5), np.uint8)) - alpha
            img = (img * (1 - edge[..., None] * 0.5) + np.array((70, 66, 66)) * edge[..., None] * 0.5).astype(np.uint8)
        img = self.motion_blur(img, cam)
        img = img.copy()
        self.avoid = []
        for h, u in self.active(self.tl.highlights, t):
            self.draw_highlight(img, h, u, s, x0, y0)
        for tp in self.tl.taps:
            self.draw_tap(img, tp, t - tp["t0"], s, x0, y0)
        # legibility gradient behind the top HUD
        g = np.linspace(0.62, 0, 230, dtype=np.float32)[:, None, None]
        img[:230] = (img[:230] * (1 - g)).astype(np.uint8)
        self.progress(img, t)
        self.step_badge(img, t, 40, 46, 34)
        self.watermark(img, W - 40, 40)
        self.speed_badge(img, t, 40, 110)
        self.chapter_card(img, t, W / 2, self.free_y(1290, [560, 900], 120))
        self.lower_third(img, t, 40, 1418)
        self.captions(img, t, (40, self.free_y(1700, [330, 520], 95), W - 40), 54, 920)
        self.flash(img, t)
        return img

    def frame_16x9(self, fr):
        t, W, H = fr.t, self.W, self.H
        content = self.source_content(fr)
        fx, fy, z = cam = self.cam(t)
        img = self.bg.copy()
        # left: the whole phone screen, always in context
        ps = 1000 / CH
        px, py = 110, 40
        pw, ph = int(CW * ps), int(CH * ps)
        phone = cv2.resize(content, (pw, ph), interpolation=cv2.INTER_AREA)
        m = gfx.rr_mask(pw, ph, 26)[..., None]
        img[py:py + ph, px:px + pw] = (img[py:py + ph, px:px + pw] * (1 - m) + phone * m).astype(np.uint8)
        gfx.rr_outline(img, [px - 2, py - 2, px + pw + 2, py + ph + 2], (70, 66, 66), thick=2, radius=28)
        # right: magnified camera view of the same moment
        vx, vy, vw, vh = 680, 214, 1180, 560
        ms = vw / CW * max(1.0, z)  # z=1: exactly the full page width
        mx0, my0 = place(fx, fy, ms, vw, vh, 0.5, 0.5)
        view, _ = warp_content(content, ms, mx0, my0, vw, vh)
        view = self.motion_blur(view, cam).copy()
        self.avoid = []
        for h, u in self.active(self.tl.highlights, t):
            self.draw_highlight(view, h, u, ms, mx0, my0)
            self.draw_highlight(img, h, u, ps, px, py - 0, dim=False, label=False, thick=3)
        for tp in self.tl.taps:
            self.draw_tap(view, tp, t - tp["t0"], ms, mx0, my0)
            self.draw_tap(img, tp, t - tp["t0"], ps, px, py, scale=0.5)
        vm = gfx.rr_mask(vw, vh, 26)[..., None]
        img[vy:vy + vh, vx:vx + vw] = (img[vy:vy + vh, vx:vx + vw] * (1 - vm) + view * vm).astype(np.uint8)
        gfx.rr_outline(img, [vx - 2, vy - 2, vx + vw + 2, vy + vh + 2], RED, thick=2, radius=28, alpha=0.55)
        # viewfinder on the phone showing what the magnifier shows
        sx0, sy0 = -mx0 / ms, -my0 / ms + CROP
        sx1, sy1 = sx0 + vw / ms, sy0 + vh / ms
        X0, Y0 = to_view(sx0, sy0, ps, px, py)
        X1, Y1 = to_view(sx1, sy1, ps, px, py)
        gfx.rr_outline(img, [max(X0, px), max(Y0, py), min(X1, px + pw), min(Y1, py + ph)], IVORY, thick=2,
                       radius=8, alpha=0.7)
        zl = gfx.pill(f"ZOOM {ms / ps:.1f}x", size=18, bg=(20, 20, 20))
        gfx.blend(img, zl, vx + 16, vy + 16, 0.9)
        self.progress(img, t)
        self.step_badge(img, t, vx, 60, 46, stack=True)
        self.watermark(img, W - 50, 48, size=44)
        self.speed_badge(img, t, vx + vw - 290, 128)
        self.chapter_card(img, t, vx + vw / 2, vy + vh / 2, 1.1)
        self.captions(img, t, (vx, 868, vx + vw), 46, 1100)
        self.lower_third(img, t, vx, 940, 0.8)
        self.flash(img, t)
        return img

    # ---------- intro / outro ----------

    def backdrop(self, t, strength=0.28, zoom0=1.1):
        """Real (masked) offer frame, blurred and dimmed, as an interface-inspired backdrop."""
        W, H = self.W, self.H
        if not hasattr(self, "_bd"):
            c = self.freeze_img[CROP:]
            s = max(W / CW, H / CH)
            big = cv2.resize(c, (int(CW * s), int(CH * s)))
            big = cv2.GaussianBlur(big, (0, 0), 14)
            self._bd = big
        big = self._bd
        k = zoom0 - (zoom0 - 1.0) * gfx.ease_out(t / 3.6)
        bh, bw = big.shape[:2]
        cw, ch = int(W / k), int(H / k)
        x, y = (bw - cw) // 2, (bh - ch) // 3
        crop = cv2.resize(big[y:y + ch, x:x + cw], (W, H))
        return cv2.addWeighted(self.bg, 1.0, crop, strength, 0)

    def streak(self, img, t, t0, t1, y, direction=1, thick=3):
        if not t0 <= t <= t1:
            return
        u = (t - t0) / (t1 - t0)
        W = self.W
        x = -400 + (W + 800) * gfx.ease_in_out(u) if direction > 0 else W + 400 - (W + 800) * gfx.ease_in_out(u)
        over = np.zeros_like(img)
        cv2.line(over, (int(x - 520 * direction), int(y)), (int(x), int(y)), RED, thick + 6, cv2.LINE_AA)
        over = cv2.GaussianBlur(over, (0, 0), 9)
        cv2.line(over, (int(x - 300 * direction), int(y)), (int(x), int(y)), IVORY, thick, cv2.LINE_AA)
        cv2.add(img, over, dst=img)

    def particles(self, img, t, n=70, seed=3):
        r = np.random.default_rng(seed)
        W, H = self.W, self.H
        for i in range(n):
            x0, y0, sp, sz, ph = r.uniform(0, W), r.uniform(0, H), r.uniform(20, 90), r.uniform(1.5, 4), r.uniform(0, 6)
            x = int(x0 + math.sin(t * 0.8 + ph) * 14)
            y = int((y0 - sp * t) % H)
            col = RED if i % 5 == 0 else IVORY
            a = 0.25 + 0.25 * math.sin(t * 2 + ph)
            cv2.circle(img, (x, y), int(sz), tuple(int(c * a) for c in col), -1, cv2.LINE_AA)

    def intro(self, t):
        W, H = self.W, self.H
        img = self.backdrop(t)
        self.particles(img, t)
        port = self.layout == "9x16"
        shake = 0
        if 0.55 <= t <= 0.85:
            shake = int(10 * (1 - (t - 0.55) / 0.3) * math.sin(t * 90))
        self.streak(img, t, 0.0, 0.62, H * (0.30 if port else 0.28), 1)
        self.streak(img, t, 0.25, 0.95, H * (0.64 if port else 0.74), -1, 2)
        exit_u = max(0.0, (t - 3.15) / 0.45)
        ek = 1 + 0.18 * gfx.ease_in_out(exit_u)
        ea = 1 - gfx.ease_in_out(exit_u)
        # brand tag
        tag = gfx.text_sprite("NPC", "black", 64 if port else 56, IVORY, 0.06)
        if t < 0.6:
            tag = gfx.glitch(tag, 1 - t / 0.6, int(t * 40))
        ta = gfx.ease_out((t - 0.2) / 0.3) * ea
        ty = H * (0.17 if port else 0.12)
        gfx.blend(img, tag, W / 2 - tag.shape[1] / 2 - 10, ty, ta)
        dot = int(14)
        if ta > 0.05 and int(t * 4) % 2 == 0:
            yy = int(ty + tag.shape[0] * 0.62)
            xx = int(W / 2 + tag.shape[1] / 2 - 2)
            img[yy:yy + dot, xx:xx + dot] = RED
        # kinetic headline
        lines = [("1 MONTH", 170 if port else 150), ("ELEVENLABS", 142 if port else 150),
                 ("CREATOR PLAN", 120 if port else 150)]
        if not port:
            lines = [("1 MONTH ELEVENLABS", 128), ("CREATOR PLAN", 128)]
        y = H * (0.30 if port else 0.27)
        for i, (txt, size) in enumerate(lines):
            sp = gfx.text_sprite(txt, "black", size, IVORY if i != 1 or not port else IVORY, -0.01)
            t0 = 0.45 + i * 0.16
            u = (t - t0) / 0.35
            if u > 0:
                if u < 0.6:
                    sp = gfx.glitch(sp, 1 - u / 0.6, int(t * 50) + i)
                k = (0.86 + 0.14 * gfx.ease_out_back(u)) * ek
                ssp = gfx.scale_sprite(sp, k)
                gfx.blend(img, ssp, W / 2 - ssp.shape[1] / 2 + shake, y + (sp.shape[0] - ssp.shape[0]) / 2
                          + 40 * (1 - gfx.ease_out(u)), min(1.0, u * 2) * ea)
            y += sp.shape[0] * 0.92
        # red accent bar
        bu = gfx.ease_out((t - 1.05) / 0.45)
        if bu > 0:
            bw = int((560 if port else 760) * bu * ek)
            yy = int(y + 18)
            over = img.copy()
            over[yy:yy + 8, W // 2 - bw // 2: W // 2 + bw // 2] = RED
            cv2.addWeighted(over, ea, img, 1 - ea, 0, dst=img)
        sub = gfx.text_sprite("STEP-BY-STEP TUTORIAL", "mono", 44 if port else 40, IVORY, 0.24)
        su = gfx.ease_out((t - 1.25) / 0.4)
        gfx.blend(img, sub, W / 2 - sub.shape[1] / 2, y + 56 + 20 * (1 - su), su * ea)
        note = gfx.text_sprite("Shown on MLH + Hacktoberfest 2026  •  requirements apply", "medium",
                               30 if port else 28, STEEL)
        nu = gfx.ease_out((t - 1.7) / 0.4)
        gfx.blend(img, note, W / 2 - note.shape[1] / 2, y + 140, nu * ea)
        if exit_u > 0:
            a = 0.5 * math.sin(math.pi * min(1.0, exit_u))
            cv2.addWeighted(img, 1 - a, np.full_like(img, IVORY), a, 0, dst=img)
        return img

    def outro(self, u):
        W, H = self.W, self.H
        port = self.layout == "9x16"
        img = self.bg.copy()
        self.particles(img, u + 5, 50, 9)
        big = gfx.text_sprite("NPC", "black", 300 if port else 260, IVORY, 0.04)
        if u < 0.5:
            big = gfx.glitch(big, 1 - u / 0.5, int(u * 60))
        a = gfx.ease_out((u - 0.1) / 0.35)
        k = 0.9 + 0.1 * gfx.ease_out_back((u - 0.1) / 0.5)
        sb = gfx.scale_sprite(big, k)
        cy = H * (0.38 if port else 0.36)
        gfx.blend(img, sb, W / 2 - sb.shape[1] / 2 - 20, cy - sb.shape[0] / 2, a)
        if u > 0.4 and int(u * 3.4) % 2 == 0:
            bx = int(W / 2 + sb.shape[1] / 2 - 8)
            by = int(cy + sb.shape[0] * 0.12)
            img[by:by + int(sb.shape[0] * 0.3), bx:bx + 34] = RED
        lw = int((620 if port else 700) * gfx.ease_out((u - 0.5) / 0.5))
        if lw > 0:
            yy = int(cy + sb.shape[0] / 2 + 10)
            img[yy:yy + 6, W // 2 - lw // 2:W // 2 + lw // 2] = RED
        tag = gfx.text_sprite("TECH  •  AI  •  TUTORIALS", "mono", 44 if port else 40, IVORY, 0.2)
        ta = gfx.ease_out((u - 0.7) / 0.4)
        gfx.blend(img, tag, W / 2 - tag.shape[1] / 2, cy + sb.shape[0] / 2 + 46 + 16 * (1 - ta), ta)
        n1 = gfx.text_sprite("Offers, eligibility and availability can change.", "medium", 34 if port else 30, STEEL)
        n2 = gfx.text_sprite("Always check the current terms on hacktoberfest.com", "medium", 34 if port else 30, STEEL)
        na = gfx.ease_out((u - 1.2) / 0.5)
        base = cy + sb.shape[0] / 2 + (200 if port else 150)
        gfx.blend(img, n1, W / 2 - n1.shape[1] / 2, base, na)
        gfx.blend(img, n2, W / 2 - n2.shape[1] / 2, base + n1.shape[0] + 8, na)
        # bridge from the last frame
        if u < 0.4:
            prev = self.frame_cache_last if hasattr(self, "frame_cache_last") else None
            if prev is not None:
                b = 1 - gfx.ease_in_out(u / 0.4)
                img = cv2.addWeighted(img, 1 - b, prev, b, 0)
        dur = self.tl.edl["outro"]
        if u > dur - 0.4:
            f = gfx.ease_in_out((u - (dur - 0.4)) / 0.4)
            img = (img * (1 - f)).astype(np.uint8)
        return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--layout", default="9x16")
    ap.add_argument("--out")
    ap.add_argument("--stills")
    ap.add_argument("--at", default="")
    a = ap.parse_args()
    r = Renderer(a.src, a.layout)
    tl = r.tl
    if a.stills:
        Path(a.stills).mkdir(parents=True, exist_ok=True)
        times = [float(x) for x in a.at.split(",") if x]
        want = sorted({min(len(tl.frames) - 1, int(round(t * tl.fps))) for t in times})
        for fr in tl.frames:
            if fr.i > want[-1]:
                break
            if fr.kind == "video" and fr.i not in want:
                # keep the decoder moving without rendering
                r.src.frames_upto(min(int(round(fr.src * 30)), 3678))
                continue
            if fr.i in want:
                r.prev_video = None  # stills are not consecutive: no motion blur across them
                cv2.imwrite(f"{a.stills}/{a.layout}_{fr.t:06.2f}.jpg", r.frame(fr), [cv2.IMWRITE_JPEG_QUALITY, 88])
        return
    import os
    tmp = f"{a.out}.{os.getpid()}.part.mp4"  # unique per process; renamed only after a clean finish
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{r.W}x{r.H}",
                            "-r", str(tl.fps), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16",
                            "-pix_fmt", "yuv420p", "-color_range", "tv", "-colorspace", "bt709", "-color_primaries",
                            "bt709", "-color_trc", "bt709", "-movflags", "+faststart", tmp], stdin=subprocess.PIPE)
    last = None
    for fr in tl.frames:
        if fr.kind == "outro" and last is not None and not hasattr(r, "frame_cache_last"):
            r.frame_cache_last = last
        img = r.frame(fr)
        last = img
        enc.stdin.write(np.ascontiguousarray(img).tobytes())
        if fr.i % 150 == 0:
            print(f"{a.layout} frame {fr.i}/{len(tl.frames)}", flush=True)
    enc.stdin.close()
    if enc.wait() != 0:
        raise SystemExit("encoder failed")
    os.replace(tmp, a.out)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
