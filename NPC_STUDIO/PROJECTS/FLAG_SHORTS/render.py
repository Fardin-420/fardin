"""Frame renderer (Pillow + numpy). Every frame is a pure function of (recorded sim, frame index),
so frames can be rendered out of order and in parallel."""
import math
import random
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

import flags
from sim import counts_at

W, H = 1080, 1920
CX, CY = 540, 884                         # arena centre
SAFE_TOP, SAFE_BOTTOM = 192, 1536         # top 10% / bottom 20% stay free of key content
TITLE_Y, POP_Y, BOARD_Y = 205, 402, 1348
HOOK_S = 2.5
TRAIL = 9
GS = 4                                     # glow layer is rendered at 1/4 resolution


def find_font():
    for q in ("Inter Display:black", "Inter:black", "Arial Black", "DejaVu Sans:bold"):
        try:
            p = subprocess.run(["fc-match", "-f", "%{file}", q], capture_output=True, text=True).stdout.strip()
            if p and Path(p).exists():
                return p
        except OSError:
            break
    return None


FONT_PATH = find_font()


def font(size):
    size = max(8, int(round(size)))
    return ImageFont.truetype(FONT_PATH, size) if FONT_PATH else ImageFont.load_default(size)


def smooth(v):
    v = min(1.0, max(0.0, v))
    return v * v * (3 - 2 * v)


def text_sprite(lines, size, fill=(255, 255, 255), stroke=None, max_w=None, spacing=0.08):
    """Centered multi-line text with a black stroke → tight RGBA sprite. Shrinks to fit max_w."""
    if isinstance(lines, str):
        lines = [lines]
    while True:
        f = font(size)
        sw = stroke if stroke is not None else max(3, int(size * 0.09))
        boxes = [f.getbbox(l, stroke_width=sw) for l in lines]
        w = max(b[2] - b[0] for b in boxes)
        if not max_w or w <= max_w or size <= 12:
            break
        size = int(size * max_w / w) - 1
    asc, desc = f.getmetrics()
    lh = int((asc + desc) * (1 + spacing))
    img = Image.new("RGBA", (w + 8, lh * len(lines) + 2 * sw + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for k, l in enumerate(lines):
        d.text((img.width // 2, sw + 4 + k * lh), l, font=f, fill=fill, anchor="ma", stroke_width=sw, stroke_fill=(0, 0, 0))
    return img.crop(img.getbbox())


def wrap_two(text, size, max_w):
    """Split a hook into at most two balanced lines."""
    words = text.split()
    f = font(size)
    if f.getlength(text) <= max_w or len(words) < 2:
        return [text]
    def width(k):
        return max(f.getlength(" ".join(words[:k])), f.getlength(" ".join(words[k:])))
    best = min(range(1, len(words)), key=width)
    ends = [k for k in range(1, len(words)) if words[k - 1][-1] in ".!?,:" and width(k) <= max(max_w, width(best) * 1.25)]
    if ends:                                   # prefer breaking at the end of a sentence
        best = min(ends, key=width)
    return [" ".join(words[:best]), " ".join(words[best:])]


def heartbeats(t0, t1):
    """Heartbeat times for the final duel; speeds up towards the end. Shared by audio and the vignette."""
    out, t = [], t0 + 0.15
    while t < t1 - 0.05:
        out.append(t)
        t += 0.74 - 0.30 * (t - t0) / max(t1 - t0, 1e-6)
    return out


class Renderer:
    def __init__(self, cfg, res):
        self.cfg, self.res = cfg, res
        self.fps = cfg["fps"]
        self.R, self.r = cfg["arena_radius"], cfg["ball_radius"]
        self.codes = [t.lower() for t in cfg["teams"]]
        self.names = [n.upper() for n in cfg["names"]]
        self.nt, self.n = len(self.codes), res["n"]
        self.team_of = res["team_of"]
        self.T, self.end_frame, self.total = res["t_end"], res["end_frame"], res["total_frames"]
        self.duel_t = res["duel_t"]
        self.exit_t = np.full(self.n, np.inf)
        self.exit_state = {}
        for t, i, tm, x, y, vx, vy in res["exits"]:
            self.exit_t[i] = t
            self.exit_state[i] = (t, x, y, vx, vy)
        self.beats = heartbeats(self.duel_t, self.T)
        self._build_assets()

    # ------------------------------------------------------------------ assets
    def _build_assets(self):
        r, R = self.r, self.R
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.hypot(xx - CX, yy - CY)
        top, bot = np.array([14, 16, 38], np.float32), np.array([5, 5, 14], np.float32)
        g = top + (bot - top) * (yy / H)[..., None]
        g += np.array([36, 22, 70], np.float32) * np.exp(-(d / 620) ** 2)[..., None]          # soft pool of light behind the arena
        g *= (1 - 0.45 * np.clip((np.hypot(xx - W / 2, yy - H / 2) - 700) / 500, 0, 1))[..., None]
        rng = np.random.default_rng(7)
        g += rng.normal(0, 1.2, (H, W, 1)).astype(np.float32)                                 # dither against banding
        self.bg = Image.fromarray(np.clip(g, 0, 255).astype(np.uint8), "RGB")
        v = np.clip((np.hypot((xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2)) - 0.62) / 0.75, 0, 1) ** 1.6
        self.vig = Image.fromarray((v * 255).astype(np.uint8), "L")
        self.red = Image.new("RGB", (W, H), (255, 20, 40))
        self.white = Image.new("RGB", (W, H), (255, 255, 255))

        D = int(2 * r)
        self.ball = [flags.flag_disc(c, D, rim=4, pad=4) for c in self.codes]
        self.ball_big = [flags.flag_disc(c, D * 3, rim=12, pad=12) for c in self.codes]       # for the winner zoom
        self.colors = [flags.flag_colors(c) for c in self.codes]
        self.glow_col = []
        for cols in self.colors:
            c = np.array(cols[0], float)
            c = c * (255 / max(c.max(), 1))
            self.glow_col.append(tuple(int(x) for x in c))
        # ring sprite (3x supersampled), centred on the arena
        self.S = S = int(2 * (R + 24))
        ss = 3
        m = Image.new("L", (S * ss, S * ss), 0)
        c0 = S * ss / 2
        ImageDraw.Draw(m).ellipse([c0 - (R + 7) * ss, c0 - (R + 7) * ss, c0 + (R + 7) * ss, c0 + (R + 7) * ss], outline=255, width=14 * ss)
        self.ring_alpha = m.resize((S, S), Image.LANCZOS)
        dot = Image.new("L", (72, 72), 0)
        ImageDraw.Draw(dot).ellipse([4, 4, 67, 67], fill=255)
        self.post = dot.resize((24, 24), Image.LANCZOS)
        self.tick = dot.resize((6, 6), Image.LANCZOS)
        # hook / title
        hook = self.cfg["hook"].upper()
        lines = wrap_two(hook, 116, 960)
        self.hook_big = text_sprite(lines, 116, max_w=960, stroke=11)
        sc = min(0.42, 620 / self.hook_big.width)
        self.hook_small = self.hook_big.resize((int(self.hook_big.width * sc), int(self.hook_big.height * sc)), Image.LANCZOS)
        self.hook_scale_small = sc
        self.out_txt = {tm: text_sprite(f"{self.names[tm]} OUT", 98, fill=(255, 255, 255), max_w=920, stroke=10) for tm in range(self.nt)}
        self.win_txt = text_sprite(f"WINNER: {self.names[self.res['winner']]}", 118, fill=(255, 214, 64), max_w=980, stroke=11)
        # scoreboard geometry
        n = self.nt
        rows = 1 if n <= 4 else 2
        per = math.ceil(n / rows)
        gap = 18
        self.card_w = int(min(310, (1000 - gap * (per - 1)) / per))
        self.card_h = 104 if rows == 1 else 82
        self.flag_d = int(min(self.card_h - 20, self.card_w * 0.40))
        self.card_pos = []
        for k in range(n):
            row, col = divmod(k, per)
            cnt = per if row < rows - 1 else n - per * (rows - 1)
            x0 = (W - (cnt * self.card_w + (cnt - 1) * gap)) // 2
            self.card_pos.append((x0 + col * (self.card_w + gap), BOARD_Y + row * (self.card_h + (46 if rows == 1 else 12))))
        self.show_names = rows == 1
        self.sb_flag = [flags.flag_disc(c, self.flag_d, rim=3, pad=2) for c in self.codes]
        self.sb_flag_grey = [flags.flag_disc(c, self.flag_d, rim=3, pad=2, grey=True) for c in self.codes]
        self._cards = {}
        rnd = random.Random(99)
        wc = [tuple(c) for c in self.colors[self.res["winner"]]] + [(255, 214, 64), (255, 255, 255)]
        self.confetti = [dict(a=rnd.uniform(0, 2 * math.pi), sp=rnd.uniform(350, 1500), rot=rnd.uniform(0, 6.28), spin=rnd.uniform(-14, 14),
                              w=rnd.uniform(14, 26), h=rnd.uniform(8, 14), col=rnd.choice(wc), ph=rnd.uniform(0, 6.28)) for _ in range(170)]

    # ------------------------------------------------------------------ scoreboard
    def _card(self, tm, count, pop=0.0):
        key = (tm, count, round(pop, 2))
        if key in self._cards:
            return self._cards[key]
        dead = count == 0
        w, h = self.card_w, self.card_h
        extra = 44 if self.show_names else 0
        img = Image.new("RGBA", (w, h + extra), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        accent = (95, 95, 105) if dead else self.glow_col[tm]
        d.rounded_rectangle([1, 1, w - 2, h - 2], radius=h // 2, fill=(16, 18, 34, 235), outline=accent + (255,), width=3)
        fl = (self.sb_flag_grey if dead else self.sb_flag)[tm]
        img.alpha_composite(fl, (12, (h - fl.height) // 2))
        fs = self.flag_d * 0.92 * (1 + 0.35 * pop)
        f = font(fs)
        cx = 12 + fl.width + (w - 24 - fl.width) // 2
        d.text((cx, h // 2), str(count), font=f, fill=(120, 120, 128) if dead else (255, 255, 255), anchor="mm",
               stroke_width=4, stroke_fill=(0, 0, 0))
        if dead:
            d.line([18, h - 22, w - 18, 22], fill=(235, 60, 70, 255), width=6)
        if self.show_names:
            nf = font(34)
            name = self.names[tm]
            while nf.getlength(name) > w - 6 and nf.size > 14:
                nf = font(nf.size - 2)
            d.text((w // 2, h + 6), name, font=nf, fill=(120, 120, 128) if dead else (235, 238, 255), anchor="ma",
                   stroke_width=3, stroke_fill=(0, 0, 0))
            if dead:
                tw = nf.getlength(name)
                d.line([w / 2 - tw / 2 - 4, h + 6 + nf.size * 0.62, w / 2 + tw / 2 + 4, h + 6 + nf.size * 0.62], fill=(160, 160, 168, 255), width=3)
        if len(self._cards) < 400:
            self._cards[key] = img
        return img

    # ------------------------------------------------------------------ helpers
    def video_t(self, f):
        return f / self.fps

    def ring_color(self, t):
        base = np.array([70, 170, 255], float)
        if t >= self.T:
            return (255, 214, 64)
        if t >= self.duel_t:
            k = smooth((t - self.duel_t) / 1.0)
            base = base + (np.array([255, 70, 90]) - base) * k
        return tuple(int(v) for v in base)

    def camera(self, f, t):
        """→ zoom, focus point in screen px (focus is drawn at the arena centre)."""
        z, fx, fy = 1.0, float(CX), float(CY)
        if t >= self.duel_t:
            z = 1 + 0.12 * min(1.0, (min(t, self.T) - self.duel_t) / max(self.T - self.duel_t, 1e-6))
        if f > self.end_frame:
            k = 1 - (1 - min(1.0, (f - self.end_frame) / (0.45 * self.fps))) ** 3
            wi = self.win_ball
            p = self.res["pos"][f, wi]
            z = z + (2.3 - z) * k
            fx, fy = CX + p[0] * k, CY + p[1] * k
        return z, fx, fy

    @property
    def win_ball(self):
        if not hasattr(self, "_wb"):
            p = self.res["pos"][self.end_frame]
            alive = [i for i in range(self.n) if self.exit_t[i] == np.inf]
            self._wb = min(alive, key=lambda i: p[i, 0] ** 2 + p[i, 1] ** 2)
        return self._wb

    def shake(self, f, t):
        amp = 0.0
        for te, _ in self.res["elims"]:
            if 0 <= t - te < 0.5:
                amp += 22 * math.exp(-(t - te) / 0.13)
        for e in self.res["exits"]:
            if 0 <= t - e[0] < 0.25:
                amp += 5 * math.exp(-(t - e[0]) / 0.08)
        if amp < 0.4:
            return 0.0, 0.0
        amp = min(amp, 30)
        return math.sin(f * 2.9) * amp + math.sin(f * 7.3) * amp * 0.4, math.cos(f * 2.3) * amp + math.sin(f * 5.9) * amp * 0.4

    # ------------------------------------------------------------------ frame
    def frame(self, f):
        res, r, R, fps = self.res, self.r, self.R, self.fps
        f = min(f, self.total - 1)
        t = self.video_t(f)
        pos = res["pos"][f]
        alive = self.exit_t > t + 1e-9 if f <= self.end_frame else self.exit_t == np.inf
        ring_deg = math.degrees(float(res["ring_angle"][f]))
        gw = int(res["gap_w"][f])
        rc = self.ring_color(t)
        img = self.bg.copy()

        # ---- glow layer (ring neon + ball trails), quarter resolution, blurred, added
        glow = Image.new("RGB", (W // GS, H // GS), (0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gcx, gcy, gR = CX / GS, CY / GS, (R + 7) / GS
        gcol = tuple(int(v * 0.75) for v in rc)
        spans = self._wall_spans(ring_deg, gw)
        for a0, a1 in spans:
            gd.arc([gcx - gR, gcy - gR, gcx + gR, gcy + gR], a0, a1, fill=gcol, width=5)
        for k in range(TRAIL, 0, -1):
            fk = f - k
            if fk < 0:
                continue
            pk = res["pos"][fk]
            fade = (1 - k / (TRAIL + 1))
            rad = r * (0.95 - 0.06 * k) / GS
            for i in range(self.n):
                if not alive[i]:
                    continue
                c = self.glow_col[self.team_of[i]]
                x, y = (CX + pk[i, 0]) / GS, (CY + pk[i, 1]) / GS
                gd.ellipse([x - rad, y - rad, x + rad, y + rad], fill=tuple(int(v * fade * 0.62) for v in c))
        glow = glow.filter(ImageFilter.GaussianBlur(2.6)).resize((W, H), Image.BILINEAR)
        img = ImageChops.add(img, glow)

        # ---- crisp ring with its gap(s), rotating tick marks, gap posts
        S = self.S
        alpha = self.ring_alpha.copy()
        ad = ImageDraw.Draw(alpha)
        for a0, a1 in self._gap_spans(ring_deg, gw):
            ad.pieslice([-4, -4, S + 4, S + 4], a0, a1, fill=0)
        core = tuple(int(v + (255 - v) * 0.55) for v in rc)
        img.paste(Image.new("RGB", (S, S), core), (CX - S // 2, CY - S // 2), alpha)
        for k in range(36):
            a = math.radians(ring_deg + k * 10 + 5)
            img.paste(rc, (int(CX + (R - 20) * math.cos(a)) - 3, int(CY + (R - 20) * math.sin(a)) - 3), self.tick)
        if 0 < gw < 360 // self.cfg["gap_count"]:
            for a0, a1 in self._gap_spans(ring_deg, gw):
                for a in (a0, a1):
                    x, y = CX + (R + 7) * math.cos(math.radians(a)), CY + (R + 7) * math.sin(math.radians(a))
                    img.paste((255, 255, 255), (int(x) - 12, int(y) - 12), self.post)

        # ---- balls leaving through the gap (ballistic, fading), then live balls
        g = self.cfg["gravity"]
        for i, (te, x, y, vx, vy) in self.exit_state.items():
            tau = t - te
            if 0 <= tau < 0.6 and f <= self.end_frame:
                px, py = CX + x + vx * tau, CY + y + vy * tau + 0.5 * g * tau * tau
                self._paste_ball(img, self.ball[self.team_of[i]], px, py, 1 - tau / 0.6)
        for i in range(self.n):
            if alive[i]:
                self._paste_ball(img, self.ball[self.team_of[i]], CX + pos[i, 0], CY + pos[i, 1], 1.0)

        # ---- camera: duel zoom, winner zoom, shake
        z, fx, fy = self.camera(f, t)
        sx, sy = self.shake(f, t)
        if z > 1.001:
            img = img.transform((W, H), Image.AFFINE, (1 / z, 0, fx + sx - CX / z, 0, 1 / z, fy + sy - CY / z), Image.BICUBIC)
            if f > self.end_frame and z > 1.5:          # redraw the winning flag crisply on top of the magnified one
                wi = self.win_ball
                p = res["pos"][f, wi]
                bx, by = CX + (CX + p[0] - fx) * z, CY + (CY + p[1] - fy) * z
                D = int(2 * r * z) + int(8 * z)
                spr = self.ball_big[self.team_of[wi]].resize((D, D), Image.LANCZOS)
                img.paste(spr, (int(bx - D / 2), int(by - D / 2)), spr)
        elif sx or sy:
            img = ImageChops.offset(img, int(sx), int(sy))

        # ---- confetti (screen space, bursts from the winner)
        if f > self.end_frame:
            tau = (f - self.end_frame) / fps
            d = ImageDraw.Draw(img)
            for c in self.confetti:
                px = CX + math.cos(c["a"]) * c["sp"] * tau * (1 - 0.25 * tau)
                py = CY + math.sin(c["a"]) * c["sp"] * tau * (1 - 0.25 * tau) + 0.5 * 1100 * tau * tau - 120 * tau
                ang = c["rot"] + c["spin"] * tau
                wv, hv = c["w"] / 2 * abs(math.cos(tau * 9 + c["ph"])) + 2, c["h"] / 2
                ca, sa = math.cos(ang), math.sin(ang)
                d.polygon([(px + ca * dx - sa * dy, py + sa * dx + ca * dy) for dx, dy in ((-wv, -hv), (wv, -hv), (wv, hv), (-wv, hv))], fill=c["col"])

        # ---- UI (never zoomed or shaken)
        self._ui(img, f, t)

        # ---- duel vignette (pulses with the heartbeat) and elimination flash
        if self.duel_t <= t < self.T:
            last = max((b for b in self.beats if b <= t), default=None)
            k = smooth((t - self.duel_t) / 0.6) * (0.22 + (0.55 * math.exp(-(t - last) / 0.2) if last is not None else 0))
            img.paste(self.red, (0, 0), self.vig.point([int(v * k) for v in range(256)]))
        fl = 0.0
        for te, _ in res["elims"]:
            if 0 <= t - te < 0.35:
                fl = max(fl, 0.85 * math.exp(-(t - te) / 0.075))
        if fl > 0.01:
            img = Image.blend(img, self.white, min(fl, 0.9))
        return img

    def _gap_spans(self, ring_deg, gw):
        return [(ring_deg + c - gw // 2, ring_deg + c - gw // 2 + gw) for c in self.res["centers"]] if gw > 0 else []

    def _wall_spans(self, ring_deg, gw):
        g = self._gap_spans(ring_deg, gw)
        if not g:
            return [(0, 360)]
        return [(g[k][1], g[(k + 1) % len(g)][0] + (360 if k == len(g) - 1 else 0)) for k in range(len(g)) if gw < 360 // len(g)]

    @staticmethod
    def _paste_ball(img, spr, x, y, a):
        x0, y0 = x - spr.width / 2, y - spr.height / 2
        ix, iy = math.floor(x0), math.floor(y0)
        if ix < -spr.width or iy < -spr.height or ix > W or iy > H:
            return
        s = spr.transform(spr.size, Image.AFFINE, (1, 0, -(x0 - ix), 0, 1, -(y0 - iy)), Image.BILINEAR)   # sub-pixel placement
        if a < 0.999:
            s.putalpha(s.getchannel("A").point([int(v * a) for v in range(256)]))
        img.paste(s, (ix, iy), s)

    def _ui(self, img, f, t):
        won = f > self.end_frame
        # hook: huge for 2.5 s, then shrinks into a small title
        if not won:
            k = smooth((t - HOOK_S) / 0.45)
            sc = 1 + (self.hook_scale_small - 1) * k
            if k >= 1:
                spr = self.hook_small
            elif k <= 0:
                spr = self.hook_big
            else:
                spr = self.hook_big.resize((int(self.hook_big.width * sc), int(self.hook_big.height * sc)), Image.LANCZOS)
            img.paste(spr, ((W - spr.width) // 2, TITLE_Y), spr)
        # "<COUNTRY> OUT" pop
        for te, tm in self.res["elims"][:-1]:          # the last elimination is the win itself
            tau = t - te
            if 0 <= tau < 1.25 and not won:
                self._pop(img, self.out_txt[tm], tau, 1.25, POP_Y)
        if won:
            self._pop(img, self.win_txt, (f - self.end_frame) / self.fps, 99, 340)
        # scoreboard
        counts = counts_at(self.res["timeline"], t if not won else self.T)
        last_change = {}
        for e in self.res["exits"]:
            if e[0] <= t:
                last_change[e[2]] = e[0]
        for tm in range(self.nt):
            tau = t - last_change.get(tm, -9)
            pop = math.exp(-tau / 0.09) if 0 <= tau < 0.4 and counts[tm] > 0 else 0.0
            card = self._card(tm, counts[tm], pop)
            img.paste(card, self.card_pos[tm], card)

    @staticmethod
    def _pop(img, spr, tau, life, yc):
        k = min(1.0, tau / 0.16)
        sc = 0.55 + 0.45 * (1 + 2.6 * (k - 1) ** 3 + 1.6 * (k - 1) ** 2)       # ease-out-back
        a = min(1.0, tau / 0.06) * min(1.0, max(0.0, (life - tau) / 0.2))
        s = spr if abs(sc - 1) < 0.004 else spr.resize((max(1, int(spr.width * sc)), max(1, int(spr.height * sc))), Image.BICUBIC)
        if a < 0.999:
            s = s.copy()
            s.putalpha(s.getchannel("A").point([int(v * a) for v in range(256)]))
        img.paste(s, ((W - s.width) // 2, int(yc - s.height / 2)), s)
