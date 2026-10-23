"""NPC ranking renderer: timeline from config, tracked reframing, motion graphics, captions -> raw frames to ffmpeg."""
import math
import re
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import track as trk

EMPH = {"FIVE", "FOUR", "THREE", "TWO", "ONE", "YAWN", "SOUL", "BUFFERING", "LATE", "COFFEE", "BRAIN", "BOOTS",
        "STRETCH", "LEGENDARY", "RELATABLE", "EVERY-BONE-CRACKS", "ABSOLUTELY", "YOU?", "WAKE-UPS"}


# ------------------------------------------------------------------ easing / keyframes
def clamp(v, a, b): return max(a, min(b, v))
def ease(x): x = clamp(x, 0.0, 1.0); return x * x * (3 - 2 * x)
def ease_out(x): x = clamp(x, 0.0, 1.0); return 1 - (1 - x) ** 3
def ease_back(x):  # overshoot, for badge slams
    x = clamp(x, 0.0, 1.0); c = 1.9; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def keyed(keys, t, idx=1):
    """Smoothstep interpolation over [[t, v...], ...]."""
    if t <= keys[0][0]: return keys[0][idx]
    for k0, k1 in zip(keys, keys[1:]):
        if t <= k1[0]:
            u = ease((t - k0[0]) / max(1e-6, k1[0] - k0[0]))
            return k0[idx] + (k1[idx] - k0[idx]) * u
    return keys[-1][idx]


# ------------------------------------------------------------------ timeline
def piece_dur(p): return p["dur"] if "freeze" in p else (p["b"] - p["a"]) / p["speed"]


def build_timeline(cfg):
    t, segs = 0.0, []
    for s in cfg["segments"]:
        pcs, u = [], 0.0
        for p in s["pieces"]:
            d = piece_dur(p); pcs.append(dict(p, o0=u, o1=u + d)); u += d
        segs.append(dict(s, start=t, dur=u, pcs=pcs)); t += u
    return segs, t


def src_at(seg, tr):
    """Output time within a segment -> (source key, master time, is_freeze)."""
    for p in seg["pcs"]:
        if tr < p["o1"] or p is seg["pcs"][-1]:
            if "freeze" in p:
                prev = [q for q in seg["pcs"] if "src" in q]
                return prev[-1]["src"], p["freeze"], True
            return p["src"], p["a"] + (min(tr, p["o1"]) - p["o0"]) * p["speed"], False
    raise ValueError


# ------------------------------------------------------------------ frames
class FrameStore:
    def __init__(self, cfg, root):
        self.cfg, self.root, self.cache = cfg, root, {}

    def load(self, key, t0, t1):
        s = self.cfg["sources"][key]
        f0 = max(0.0, t0 - s["offset"] - 0.15); f1 = t1 - s["offset"] + 0.15
        info = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                               "stream=width,height,r_frame_rate", "-of", "csv=p=0", f"{self.root}/{s['file']}"],
                              capture_output=True, text=True).stdout.strip().split(",")
        w, h = int(info[0]), int(info[1]); num, den = map(int, info[2].split("/")); fps = num / den
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{f0:.3f}", "-t", f"{f1 - f0:.3f}", "-i",
                              f"{self.root}/{s['file']}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                             capture_output=True, check=True).stdout
        arr = np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)
        self.cache.setdefault(key, []).append({"t0": f0 + s["offset"], "fps": fps, "frames": arr})

    def get(self, key, t):
        for blk in self.cache[key]:
            i = int(round((t - blk["t0"]) * blk["fps"]))
            if 0 <= i < len(blk["frames"]):
                return blk["frames"][i]
        blk = min(self.cache[key], key=lambda b: abs(t - b["t0"]))
        return blk["frames"][clamp(int(round((t - blk["t0"]) * blk["fps"])), 0, len(blk["frames"]) - 1)]


# ------------------------------------------------------------------ renderer
class Renderer:
    def __init__(self, cfg, root, voice):
        self.cfg, self.root = cfg, root
        self.W, self.H, self.FPS = cfg["export"]["width"], cfg["export"]["height"], cfg["export"]["fps"]
        self.segs, self.total = build_timeline(cfg)
        st = cfg["style"]; self.st = st
        self.P = st["panel"]
        self.acc = tuple(st["accent"])
        self._fc = {}
        self.voice = voice
        self.store = FrameStore(cfg, root)
        for s in self.segs:
            for p in s["pcs"]:
                if "src" in p: self.store.load(p["src"], min(p["a"], p["b"]), max(p["a"], p["b"]))
        self.tracks = {}
        for s in self.segs:
            if "track" in s:
                tk = s["track"]
                blk_frames, times = [], []
                fps = 24.0
                t = tk["a"]
                while t <= tk["b"]:
                    blk_frames.append(self.store.get(tk["src"], t)); times.append(t); t += 1 / fps
                c = trk.track(blk_frames, tk["box"], tk.get("method", "template"))
                self.tracks[s["id"]] = (np.array(times), c)
        size = self.P["size"]
        m = Image.new("L", (size, size), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, size - 1, size - 1), self.P["radius"], fill=255)
        self.mask = m
        self.captions = self._build_captions()
        yy, xx = np.mgrid[0:self.H, 0:self.W].astype(np.float32)
        self.vig = (1 - 0.45 * (((xx - self.W / 2) / (self.W / 2)) ** 2 + ((yy - self.H / 2) / (self.H / 2)) ** 2)
                    ).clip(0.35, 1)[..., None]
        self.rng = np.random.default_rng(5)

    def font(self, path, size):
        size = max(1, int(size))  # animated scales start at 0
        k = (path, size)
        if k not in self._fc: self._fc[k] = ImageFont.truetype(path, size)
        return self._fc[k]

    # ---------- camera
    def focus(self, seg, tr, mt):
        if "focus_after" in seg and tr >= seg["focus_after"][0][0]:
            return keyed(seg["focus_after"], tr, 1), keyed(seg["focus_after"], tr, 2)
        if seg["id"] in self.tracks:
            times, c = self.tracks[seg["id"]]
            i = int(np.argmin(np.abs(times - mt)))
            return float(c[i, 0]), float(c[i, 1])
        return keyed(seg["focus"], tr, 1), keyed(seg["focus"], tr, 2)

    def panel(self, seg, tr):
        key, mt, frz = src_at(seg, tr)
        fr = self.store.get(key, mt)
        h, w = fr.shape[:2]
        z = keyed(seg["zoom"], tr)
        side = min(w, h) / z
        fx, fy = self.focus(seg, tr, mt)
        cx = clamp(fx * w, side / 2, w - side / 2); cy = clamp(fy * h, side / 2, h - side / 2)
        box = (cx - side / 2, cy - side / 2, cx + side / 2, cy + side / 2)
        im = Image.fromarray(fr)
        size = self.P["size"]
        pan = im.resize((size, size), Image.LANCZOS, box=box)
        if side < size * 0.8:  # upscaled low-res source: restore edge crispness
            pan = pan.filter(ImageFilter.UnsharpMask(radius=2.2, percent=70, threshold=2))
        lift = seg.get("lift")
        lut = [int(255 * (v / 255) ** (1 / lift)) if lift else v for v in range(256)]
        # grade: gentle S-curve contrast + warmth
        lut = [clamp(int(128 + (x - 128) * 1.08), 0, 255) for x in lut]
        pan = pan.point(lut * 3)
        # blurred backdrop from the same frame (no black bars)
        bg = im.resize((54, 96), Image.BILINEAR, box=(max(0, w / 2 - h * 9 / 32), 0, min(w, w / 2 + h * 9 / 32), h))
        bg = bg.filter(ImageFilter.GaussianBlur(4)).resize((self.W, self.H), Image.BICUBIC)
        return pan, bg, (box, w, h, (fx, fy)), frz

    def to_panel_xy(self, geom, nx, ny):
        (x0, y0, x1, y1), w, h = geom[:3]
        s = self.P["size"] / (x1 - x0)
        return self.P["x"] + (nx * w - x0) * s, self.P["y"] + (ny * h - y0) * s

    def fx_point(self, geom, fx):
        """Callout anchor: fixed source position, or an offset from the tracked subject so it follows the action."""
        if fx.get("follow"):
            return self.to_panel_xy(geom, geom[3][0] + fx["off"][0], geom[3][1] + fx["off"][1])
        return self.to_panel_xy(geom, *fx["at"])

    # ---------- captions
    def _build_captions(self):
        caps = []
        for v in self.voice:
            words = v["words"]
            seg = self.seg_at(v["start"] + 0.01)
            seg_end = seg["start"] + seg["dur"]
            chunk = []
            for i, (w, a, b) in enumerate(words):
                chunk.append((w, a, b))
                brk = re.search(r"[,.:!?]$", w) or len(chunk) == 3 or i == len(words) - 1
                if brk:
                    caps.append((chunk, seg_end)); chunk = []
        out = []
        for i, (ch, seg_end) in enumerate(caps):
            end = caps[i + 1][0][0][1] if i + 1 < len(caps) and caps[i + 1][0][0][1] - ch[-1][2] < 0.6 else ch[-1][2] + 0.35
            out.append((ch[0][1], min(end, seg_end), ch))  # never let a caption bleed into the next rank
        return out

    def draw_captions(self, img, t):
        c = self.cfg["captions"]; d = ImageDraw.Draw(img)
        for a, b, ch in self.captions:
            if not (a <= t < b): continue
            vis = [x for x in ch if x[1] <= t + 0.03]
            items = []
            for w, s, e in vis:
                age = t - s; pop = 1 + 0.28 * max(0.0, 1 - age / 0.1)
                txt = w.upper().strip()
                core = re.sub(r"[^A-Z\-?]", "", txt)
                emph = core in EMPH or core.rstrip("?") in EMPH
                items.append((txt, int(c["size"] * pop), emph))
            gap = 22; lines, cur, cw = [], [], 0
            for txt, sz, em in items:
                fw = self.font(c["font"], sz).getlength(txt)
                if fw > c["max_width"]:  # one long word: shrink it to the safe width instead of overflowing
                    sz = int(sz * c["max_width"] / fw); fw = self.font(c["font"], sz).getlength(txt)
                if cur and cw + gap + fw > c["max_width"]: lines.append(cur); cur, cw = [], 0
                cur.append((txt, sz, em, fw)); cw += (gap if len(cur) > 1 else 0) + fw
            lines.append(cur); lines = lines[-c["max_lines"]:]
            lh = int(c["size"] * 1.08); y0 = c["y"] - (len(lines) - 1) * lh / 2
            for li, line in enumerate(lines):
                tot = sum(x[3] for x in line) + gap * (len(line) - 1); x = self.W / 2 - tot / 2
                for txt, sz, em, fw in line:
                    d.text((x, y0 + li * lh), txt, font=self.font(c["font"], sz),
                           fill=tuple(c["emphasis"]) if em else tuple(c["color"]), anchor="lm",
                           stroke_width=c["stroke"], stroke_fill=(0, 0, 0))
                    x += fw + gap
            return

    # ---------- motion graphics
    def draw_header(self, img, seg, tr):
        d = ImageDraw.Draw(img)
        st = self.st; F, L, M = st["badge_font"], st["label_font"], st["mono_font"]
        ranks = [5, 4, 3, 2, 1]
        cur = seg["rank"]
        # progress indicator
        x0, y = 150, 118
        for i, r in enumerate(ranks):
            cx = x0 + i * 112
            done = cur is not None and r > cur
            now = r == cur
            k = ease_back(tr / 0.35) if now else 1
            rad = 34 * (1.25 * k if now else 1)
            if now:
                d.ellipse((cx - rad - 10, y - rad - 10, cx + rad + 10, y + rad + 10), fill=(*self.acc, 60))
                d.ellipse((cx - rad, y - rad, cx + rad, y + rad), fill=self.acc, outline=(0, 0, 0), width=4)
                col = (0, 0, 0)
            elif done:
                d.ellipse((cx - rad, y - rad, cx + rad, y + rad), fill=(110, 95, 25), outline=(0, 0, 0), width=3)
                col = (230, 220, 180)
            else:
                d.ellipse((cx - rad, y - rad, cx + rad, y + rad), fill=(25, 25, 25), outline=(200, 200, 200), width=3)
                col = (220, 220, 220)
            d.text((cx, y + 2), str(r), font=self.font(F, int(40 * (1.2 if now else 1))), fill=col, anchor="mm")
            if i < 4:
                fill = self.acc if done or (cur is not None and r == cur and tr > 0.3) else (90, 90, 90)
                d.line((cx + 40, y, cx + 72, y), fill=fill, width=6)
        d.rounded_rectangle((self.W - 170, 92, self.W - 40, 146), 12, fill=self.acc)
        d.text((self.W - 105, 120), "NPC", font=self.font(F, 36), fill=(0, 0, 0), anchor="mm")
        # rank title row
        if cur is not None:
            k = ease_back(tr / 0.3)
            bs = int(150 * max(0.01, k))
            bx, by = 150, 290
            d.rounded_rectangle((bx - bs / 2 - 6, by - bs / 2 - 6, bx + bs / 2 + 6, by + bs / 2 + 6), 28, fill=(*self.acc, 70))
            d.rounded_rectangle((bx - bs / 2, by - bs / 2, bx + bs / 2, by + bs / 2), 24, fill=self.acc, outline=(0, 0, 0), width=6)
            d.text((bx, by + 4), f"#{cur}", font=self.font(F, int(96 * max(0.01, k))), fill=(0, 0, 0), anchor="mm")
            kl = ease_out((tr - 0.12) / 0.3)
            if kl > 0:
                lx = 260 + (1 - kl) * 300
                d.text((lx, 290), seg["label"], font=self.font(L, 60 if len(seg["label"]) < 18 else 50),
                       fill=(255, 255, 255), anchor="lm", stroke_width=6, stroke_fill=(0, 0, 0))
        else:  # hook title
            k = ease_back(tr / 0.3)
            d.text((self.W / 2, 255), "TOP 5", font=self.font(F, int(150 * max(0.01, k))), fill=self.acc,
                   anchor="mm", stroke_width=10, stroke_fill=(0, 0, 0))
            if tr > 0.15:
                d.text((self.W / 2, 345), self.cfg["title_card"].replace("TOP 5 ", ""),
                       font=self.font(L, 50), fill=(255, 255, 255), anchor="mm", stroke_width=6, stroke_fill=(0, 0, 0))

    def big_number(self, img, seg, tr):
        """Full-panel rank slam during the first 0.5 s: readable with the sound off."""
        if seg["rank"] is None or tr > 0.55: return
        a = 1 - ease((tr - 0.25) / 0.3)
        s = 1.8 - 0.8 * ease_out(tr / 0.18)
        txt = f"#{seg['rank']}"
        f = self.font(self.st["badge_font"], int(430 * s))
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
        cy = self.P["y"] + self.P["size"] / 2
        d.text((self.W / 2, cy), txt, font=f, fill=(*self.acc, int(255 * a)), anchor="mm",
               stroke_width=18, stroke_fill=(0, 0, 0, int(255 * a)))
        glow = layer.filter(ImageFilter.GaussianBlur(18))
        img.alpha_composite(glow); img.alpha_composite(layer)

    def draw_fx(self, img, seg, tr, geom, pan_off):
        d = ImageDraw.Draw(img)
        M = self.st["mono_font"]
        for fx in seg.get("fx", []):
            ty = fx["type"]
            if ty == "chip" and fx["t0"] <= tr < fx["t1"]:
                f = self.font(M, 34); tw = f.getlength(fx["text"])
                x, y = self.P["x"] + 30 + pan_off[0], self.P["y"] + 28 + pan_off[1]
                d.rounded_rectangle((x, y, x + tw + 36, y + 58), 12, fill=(215, 30, 30) if "REPLAY" in fx["text"] else (15, 15, 15))
                d.text((x + 18, y + 29), fx["text"], font=f, fill=(255, 255, 255), anchor="lm")
            elif ty == "ring" and fx["t0"] <= tr < fx["t1"]:
                px, py = self.fx_point(geom, fx)
                r = fx["r"] * self.P["size"] * (geom[1] / (geom[0][2] - geom[0][0])) * (1 + 0.05 * math.sin(tr * 14))
                k = ease_out((tr - fx["t0"]) / 0.15); r *= (1.6 - 0.6 * k)
                for wdt, col in ((14, (0, 0, 0)), (7, self.acc)):
                    d.ellipse((px - r, py - r, px + r, py + r), outline=col, width=wdt)
            elif ty == "arrow" and fx["t0"] <= tr < fx["t1"]:
                tx, ty_ = self.fx_point(geom, fx)
                k = ease_out((tr - fx["t0"]) / 0.22); bob = 10 * math.sin(tr * 12)
                sx, sy = tx + 300, ty_ - 260
                if sy < self.P["y"] + 40:  # target near the panel top: come in from below so the header stays clean
                    sx, sy = tx + 280, ty_ + 300
                ex, ey = sx + (tx + 70 - sx) * k, sy + (ty_ + (60 if sy > ty_ else -60) - sy) * k + bob
                ang = math.atan2(ey - sy, ex - sx)
                for wdt, col in ((32, (0, 0, 0)), (18, self.acc)):
                    d.line((sx, sy, ex, ey), fill=col, width=wdt)
                hl = 64
                pts = [(ex + 18 * math.cos(ang), ey + 18 * math.sin(ang)),
                       (ex - hl * math.cos(ang - 0.5), ey - hl * math.sin(ang - 0.5)),
                       (ex - hl * math.cos(ang + 0.5), ey - hl * math.sin(ang + 0.5))]
                d.polygon(pts, fill=self.acc, outline=(0, 0, 0), width=6)
            elif ty == "endcard" and tr >= fx["t0"]:
                k = ease_back((tr - fx["t0"]) / 0.35)
                f = self.font(self.st["badge_font"], int(84 * max(0.01, k)))
                cy = self.P["y"] + 170
                d.text((self.W / 2, cy), self.cfg["end_card"], font=f, fill=self.acc, anchor="mm",
                       stroke_width=12, stroke_fill=(0, 0, 0))

    def flash_amount(self, seg, tr):
        a = 0.0
        for fx in seg.get("fx", []):
            if fx["type"] == "flash" and 0 <= tr - fx["t"] < 0.12:
                a = max(a, 1 - (tr - fx["t"]) / 0.12)
        return a

    def shake(self, seg, tr):
        for fx in seg.get("fx", []):
            if fx["type"] == "shake" and fx["t0"] <= tr < fx["t1"]:
                amp = fx["amp"] * (1 - (tr - fx["t0"]) / (fx["t1"] - fx["t0"]))
                return self.rng.uniform(-amp, amp), self.rng.uniform(-amp, amp)
        return 0, 0

    def seg_at(self, t):
        for s in self.segs:
            if t < s["start"] + s["dur"]: return s
        return self.segs[-1]

    # ---------- frame
    def frame(self, t):
        seg = self.seg_at(t); tr = t - seg["start"]
        pan, bg, geom, frz = self.panel(seg, tr)
        # whip transition around each cut: directional blur + slide
        TL = self.st["transition_len"] / 2
        idx = self.segs.index(seg)
        whip = 0.0
        if idx > 0 and tr < TL: whip = 1 - tr / TL            # entering from the right
        nxt = seg["start"] + seg["dur"] - t
        if idx < len(self.segs) - 1 and nxt < TL: whip = -(1 - nxt / TL)  # leaving to the left
        if whip:
            a = np.asarray(pan, np.float32); acc = np.zeros_like(a); n = 9
            span = int(160 * abs(whip))
            for j in range(n):
                acc += np.roll(a, int(-span * j / n * np.sign(whip)), axis=1)
            pan = Image.fromarray((acc / n).astype(np.uint8))
        canvas = bg.convert("RGB")
        cv = np.asarray(canvas, np.float32) * 0.42 * self.vig
        canvas = Image.fromarray(cv.clip(0, 255).astype(np.uint8)).convert("RGBA")
        off = self.shake(seg, tr)
        slide = int(whip * 120)
        px, py = int(self.P["x"] + off[0] + slide), int(self.P["y"] + off[1])
        fl = self.flash_amount(seg, tr)
        if fl: pan = Image.blend(pan, Image.new("RGB", pan.size, (255, 255, 255)), 0.85 * fl)
        frz_glow = any(fx["type"] == "freeze_glow" and fx["t0"] <= tr < fx["t1"] for fx in seg.get("fx", [])) or frz
        if frz_glow:
            g = Image.new("RGBA", canvas.size, (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
            gd.rounded_rectangle((px - 14, py - 14, px + self.P["size"] + 14, py + self.P["size"] + 14), 44,
                                 outline=(*self.acc, 230), width=16)
            canvas.alpha_composite(g.filter(ImageFilter.GaussianBlur(10)))
        canvas.paste(pan, (px, py), self.mask)
        d = ImageDraw.Draw(canvas)
        d.rounded_rectangle((px, py, px + self.P["size"] - 1, py + self.P["size"] - 1), self.P["radius"],
                            outline=self.acc if frz_glow else (255, 255, 255), width=5)
        self.draw_fx(canvas, seg, tr, geom, (off[0] + slide, off[1]))
        self.big_number(canvas, seg, tr)
        self.draw_header(canvas, seg, tr)
        d = ImageDraw.Draw(canvas)
        d.text((self.W / 2, self.P["y"] - 20), self.cfg["credit"],
               font=self.font(self.st["mono_font"], 22), fill=(185, 185, 185), anchor="mm")
        self.draw_captions(canvas, t)
        return canvas.convert("RGB")

    def render(self, out, preview_times=None):
        if preview_times:
            for t in preview_times:
                self.frame(t).resize((270, 480)).save(f"{out}_{int(t * 100):04d}.jpg", quality=85)
            return
        e = self.cfg["export"]
        p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                              f"{self.W}x{self.H}", "-r", str(self.FPS), "-i", "-", "-c:v", "libx264", "-preset",
                              "medium", "-crf", "16", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
        n = int(round(self.total * self.FPS))
        for i in range(n):
            p.stdin.write(self.frame(i / self.FPS).tobytes())
            if i % 90 == 0: print("frame", i, "/", n, flush=True)
        p.stdin.close(); p.wait()
