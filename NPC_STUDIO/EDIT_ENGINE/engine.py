"""Frame compositor: shots, 2.5D parallax, motion blur, impacts, transitions, typography.

The project file (PROJECTS/<name>/source/edit.py) builds a Timeline from the
music event map; this module renders it. Every frame is a pure function of its
time, so frames render in parallel and in any order.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import cv2
import numpy as np
import soundfile as sf
from PIL import Image

import fx
from fx import Cam, Layer, clamp01, ease_in_expo, ease_out_expo, impulse, lerp, smooth
from typo import EMERALD, ICE, SILVER, WHITE, GlyphState, Text

# palette (sRGB floats)
NPC_SILVER = np.float32([0.84, 0.89, 0.97])
NPC_BLUE = np.float32([0.35, 0.50, 0.85])
CW_EMERALD = np.float32([0.16, 0.85, 0.52])
CW_DEEP = np.float32([0.03, 0.16, 0.11])
COOL_WHITE = np.float32([0.90, 0.95, 1.0])


# ----------------------------------------------------------------------------- assets

def _load_rgb(p: Path) -> np.ndarray:
    return np.asarray(Image.open(p).convert("RGB"), np.float32) / 255


def _load_a(p: Path) -> np.ndarray:
    return np.asarray(Image.open(p).convert("L"), np.float32) / 255


def _bg_plate(orig: np.ndarray, alpha: np.ndarray, plate: np.ndarray, grow: float) -> np.ndarray:
    """Original background everywhere it exists; inpainted plate only inside the subject hole."""
    k = max(3, int(grow * max(alpha.shape)) | 1)
    hole = cv2.dilate((alpha > 0.04).astype(np.float32), np.ones((k, k), np.uint8))
    hole = cv2.GaussianBlur(hole, (0, 0), k * 0.35)[..., None]
    return orig * (1 - hole) + plate * hole


class Assets:
    def __init__(self, project: Path):
        prep = project / "source/prepared"
        self.anchors = json.loads((prep / "anchors.json").read_text())
        # ---- CyberWolf: restored 2560 px drawing ----
        cw = _load_rgb(prep / "cyberwolf_up.png")
        cwa = _load_a(prep / "cyberwolf_alpha.png")
        cw_bg = _bg_plate(cw, cwa, _load_rgb(prep / "cyberwolf_bg.png"), 0.02)
        self.cw_fg = Layer(fx.grade(cw, lift=(0.0, 0.006, 0.010), gain=(0.86, 0.89, 0.90), contrast=0.24, sat=1.0, pivot=0.5), cwa)
        # background: dark gunmetal with an emerald cast, ceiling lights stay cool white
        g = fx.grade(cw_bg, lift=(0.004, 0.016, 0.014), gain=(0.42, 0.60, 0.56), sat=0.30, contrast=0.22, pivot=0.5)
        self.cw_bg = Layer(g)
        hsv = cv2.cvtColor((cw * 255).astype(np.uint8), cv2.COLOR_RGB2HSV)
        lens = ((hsv[..., 0] > 30) & (hsv[..., 0] < 75) & (hsv[..., 1] > 80) & (hsv[..., 2] > 35)).astype(np.float32)
        lens[: int(0.40 * lens.shape[0])] = 0
        lens[int(0.66 * lens.shape[0]):] = 0
        lens = cv2.morphologyEx(lens, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
        self.cw_lens = Layer(np.dstack([lens] * 3), cv2.GaussianBlur(lens, (0, 0), 3), overlay=True)
        self.cw_alpha_src = cwa
        # ---- NPC: original photograph (never re-synthesized) ----
        npc = _load_rgb(project / "source/assets/npc.png")
        npa = _load_a(prep / "npc_alpha.png")
        npc_bg = _bg_plate(npc, npa, _load_rgb(prep / "npc_bg.png"), 0.03)
        # subject: deep black, charcoal mids, subtle blue in the shadows
        sub = fx.grade(npc, lift=(0.006, 0.010, 0.022), gain=(0.93, 0.96, 1.0), contrast=0.10, sat=0.6)
        # the grey shirt lettering is lifted locally so NPC reads clearly (grading only)
        x0, y0, x1, y1 = self.anchors["npc"]["letters_bbox"]
        H, W = npc.shape[:2]
        m = np.zeros((H, W), np.float32)
        m[int((y0 - 0.03) * H):int((y1 + 0.03) * H), int((x0 - 0.03) * W):int((x1 + 0.03) * W)] = 1
        m = cv2.GaussianBlur(m, (0, 0), 18)[..., None] * npa[..., None]
        L = sub.mean(2, keepdims=True)
        lifted = sub * (1 + 1.25 * fx.smoothstep_arr(0.10, 0.30, L))
        sub = sub * (1 - m) + lifted * m
        self.npc_fg = Layer(sub, npa)
        # the shirt print itself (for lighting the real lettering as NPC's title)
        Ln = npc.mean(2)
        pm = np.zeros((H, W), np.float32)
        ys0, ys1, xs0, xs1 = int((y0 - 0.02) * H), int((y1 + 0.02) * H), int((x0 - 0.02) * W), int((x1 + 0.02) * W)
        pm[ys0:ys1, xs0:xs1] = fx.smoothstep_arr(0.15, 0.26, Ln[ys0:ys1, xs0:xs1])
        pm = cv2.GaussianBlur(pm, (0, 0), 0.8) * npa
        self.npc_print = Layer(np.dstack([pm] * 3), pm, overlay=True)
        self.npc_bg = Layer(fx.grade(npc_bg, lift=(0.02, 0.03, 0.05), gain=(0.88, 0.93, 1.0), contrast=0.08, sat=0.4))
        self.npc_sky = Layer(np.dstack([np.clip((npc_bg.mean(2) - 0.55) / 0.4, 0, 1)] * 3))
        # ---- logo: original pixels + circular alpha ----
        lg = np.asarray(Image.open(prep / "logo_rgba.png").convert("RGBA"), np.float32) / 255
        self.logo = Layer(lg[..., :3], lg[..., 3], overlay=True)
        self.logo_rgba = lg


# ----------------------------------------------------------------------------- context

@dataclass
class Impact:
    t: float
    punch: float = 0.0       # zoom impulse (fraction)
    shake: float = 0.0       # px at 1080 wide
    flash: float = 0.0       # exposure add
    flash_color: tuple = (1, 1, 1)
    chroma: float = 0.0
    glitch: float = 0.0
    wave: float = 0.0        # shockwave amplitude (px)
    barrel: float = 0.0
    decay: float = 0.07
    seed: int = 0


class Ctx:
    def __init__(self, project: Path, events: dict, scale: float = 1.0):
        self.project = project
        self.ev = events
        self.fps = events["fps"]
        self.W, self.H = int(1080 * scale), int(1920 * scale)
        self.S = scale  # px multiplier relative to 1080x1920
        self.A = Assets(project)
        self.impacts: list[Impact] = []
        self.distort = fx.Distort(self.W, self.H)
        self.vig = fx.vignette_mask(self.W, self.H, 0.5, 0.95)
        self.grain = fx.grain_bank(self.W, self.H)
        self._env()

    def _env(self):
        y, sr = sf.read(self.project / "audio/music_edit.wav", dtype="float32")
        m = y.mean(1)
        from scipy import signal as ss
        sub = ss.sosfilt(ss.butter(4, [35, 120], "bandpass", fs=sr, output="sos"), m)
        hop = sr // self.fps
        n = len(m) // hop + 2
        def rms(x):
            x = np.pad(x, (0, n * hop - len(x)))
            return np.sqrt((x.reshape(n, hop) ** 2).mean(1))
        full, s = rms(m), rms(sub)
        self.env_full = np.clip(full / np.percentile(full, 99), 0, 1.2)
        self.env_sub = np.clip(s / np.percentile(s, 99), 0, 1.2)

    def env(self, t: float, kind: str = "sub") -> float:
        arr = self.env_sub if kind == "sub" else self.env_full
        i = int(t * self.fps)
        return float(arr[min(max(i, 0), len(arr) - 1)])

    def beat(self, n: float) -> float:
        """Video time of the impact frame of output beat n (n = 0 is the music entrance).

        Integer beats use the measured onset frame from the event map; fractional beats use
        the grid plus the measured onset offset, quantized with the same rule."""
        if float(n).is_integer():
            for b in self.ev["beats"]:
                if b["n"] == int(n):
                    return b["frame"] / self.fps
        t = self.ev["entrance_t"] + n * self.ev["beat_period"] + self.ev["onset_offset_from_grid_ms"] / 1000
        return math.ceil(t * self.fps - 0.6) / self.fps

    # --- global camera impulses (shared by every shot, so nothing ever exposes an edge) ---
    def impact_cam(self, t: float, cam: Cam) -> Cam:
        z, ox, oy, rot = 1.0, 0.0, 0.0, 0.0
        for im in self.impacts:
            if t < im.t - 0.02 or t > im.t + im.decay * 8:
                continue
            e = impulse(t, im.t, attack=1 / self.fps, decay=im.decay)
            z *= 1 + im.punch * e
            if im.shake:
                ph = (t - im.t) * 2 * math.pi
                r = np.random.default_rng(im.seed)
                f1, f2, p1, p2 = r.uniform(15, 21), r.uniform(13, 19), r.uniform(0, 6.28), r.uniform(0, 6.28)
                amp = im.shake * e * self.S
                ox += amp * math.sin(ph * f1 + p1)
                oy += amp * 0.8 * math.sin(ph * f2 + p2)
                rot += im.shake * e * 0.012 * math.sin(ph * f1 * 0.7 + p2)
        if z == 1.0 and ox == 0.0 and oy == 0.0:
            return cam
        return Cam(cam.cx, cam.cy, cam.zoom * z * (1.0 + 0.004 * (abs(ox) + abs(oy)) / self.S), cam.rot + rot,
                   cam.ox + ox, cam.oy + oy)

    def impact_post(self, img: np.ndarray, t: float) -> np.ndarray:
        flash, chroma, glitch, wave, barrel, col = 0.0, 0.0, 0.0, 0.0, 0.0, np.zeros(3, np.float32)
        seeds = 0
        for im in self.impacts:
            if t < im.t - 0.02 or t > im.t + 0.6:
                continue
            e = impulse(t, im.t, attack=0, decay=im.decay)
            if im.flash:
                f = im.flash * impulse(t, im.t, attack=0, decay=im.decay * 0.8)
                flash += f
                col += np.float32(im.flash_color) * f
            chroma += im.chroma * e
            if im.glitch and 0 <= t - im.t < 4 / self.fps:
                glitch = max(glitch, im.glitch * (1 - (t - im.t) * self.fps / 4))
                seeds = im.seed * 97 + int((t - im.t) * self.fps)
            if im.wave:
                wave = max(wave, im.wave * math.exp(-(t - im.t) / 0.22))
                wr = (t - im.t) * 2.6
            barrel += im.barrel * e
        if wave > 0.5:
            img = self.distort.shockwave(img, wr, wave * self.S, width=0.07)
        if barrel > 0.002:
            img = self.distort.barrel(img, barrel)
        if chroma > 0.0005:
            img = self.distort.chroma(img, chroma)
        if glitch > 0.02:
            img = fx.glitch_strips(img, seeds, glitch, bands=9, rgb=1.0)
            img = fx.block_displace(img, seeds + 1, glitch * 0.8)
        if flash > 0.003:
            img = img + col[None, None, :] * 0.85 + flash * 0.15 * img
        return img


# ----------------------------------------------------------------------------- shots

def _parallax(cam: Cam, ref: Cam, p: float, base_zoom: float = 1.0) -> Cam:
    return Cam(ref.cx + (cam.cx - ref.cx) * p, ref.cy + (cam.cy - ref.cy) * p,
               (1 + (cam.zoom - 1) * p) * base_zoom, cam.rot * p, cam.ox * p, cam.oy * p)


def project_point(M: np.ndarray, src_xy) -> tuple[float, float]:
    """Source px -> screen px through an out->src matrix."""
    A = np.vstack([M, [0, 0, 1]])
    inv = np.linalg.inv(A)
    v = inv @ np.array([src_xy[0], src_xy[1], 1.0])
    return float(v[0]), float(v[1])


@dataclass
class Sweep:
    t0: float
    dur: float
    angle: float = 62.0
    width: float = 0.07
    strength: float = 0.9
    color: tuple = (0.55, 1.0, 0.75)
    target: str = "lens"     # lens | subject | all


class CharShot:
    """One character with 2.5D parallax, light and atmosphere.

    cam_fn(t) -> Cam in source-normalized coordinates of that character's image."""

    def __init__(self, char: str, cam_fn: Callable[[float], Cam], *, exposure=1.0, rim=0.0, rim_dir=(1.0, -0.6),
                 rays=0.0, sweeps=(), dust=0.0, fg_particles=0.0, fog=0.0, p_bg=0.55, bg_zoom=1.06, dark=0.0,
                 seed=0, mb=True, tint=None, ref_t=0.0, focus=0.0, focus_at=(0.5, 0.45), print_glow=0.0):
        self.char, self.cam_fn = char, cam_fn
        self.exposure = exposure if callable(exposure) else (lambda t, e=exposure: e)
        self.rim = rim if callable(rim) else (lambda t, r=rim: r)
        self.rays = rays if callable(rays) else (lambda t, r=rays: r)
        self.rim_dir, self.sweeps = rim_dir, list(sweeps)
        self.dust, self.fg_particles, self.fog = dust, fg_particles, fog
        self.p_bg, self.bg_zoom, self.dark, self.seed, self.mb, self.tint = p_bg, bg_zoom, dark, seed, mb, tint
        self.focus, self.focus_at = focus, focus_at
        self.print_glow = print_glow if callable(print_glow) else (lambda t, g=print_glow: g)
        self.ref = cam_fn(ref_t)  # parallax is measured from the shot's opening camera

    def layers(self, ctx: Ctx):
        A = ctx.A
        return (A.cw_bg, A.cw_fg) if self.char == "cw" else (A.npc_bg, A.npc_fg)

    def render(self, ctx: Ctx, t: float, wh=None, frame_wh=None, extra: Cam | None = None) -> np.ndarray:
        W, H = wh or (ctx.W, ctx.H)
        FW, FH = frame_wh or (ctx.W, ctx.H)
        bgL, fgL = self.layers(ctx)
        src_wh = (fgL.w, fgL.h)
        bounds = (ctx.A.anchors["cyberwolf"]["keep_out"][2] + 0.005, 0, 1, 1) if self.char == "cw" else None

        def cam_at(tt):
            c = self.cam_fn(tt)
            if extra is not None:
                c = Cam(c.cx + extra.cx, c.cy + extra.cy, c.zoom * extra.zoom, c.rot + extra.rot, c.ox + extra.ox, c.oy + extra.oy)
            return ctx.impact_cam(tt, c)

        # motion blur: 180-degree shutter, sample count from on-screen displacement
        sh = 0.5 / ctx.fps
        c0, c1 = cam_at(t - sh / 2), cam_at(t + sh / 2)
        M0, s0 = fx.cam_matrix(c0, src_wh, (W, H), frame_wh=(FW, FH), bounds=bounds)
        M1, _ = fx.cam_matrix(c1, src_wh, (W, H), frame_wh=(FW, FH), bounds=bounds)
        disp = fx.corners_disp(M0, M1, (W, H), s0) if self.mb else 0.0
        n = int(min(14, max(1, math.ceil(disp / (2.5 * ctx.S)))))
        times = [t] if n == 1 else [t - sh / 2 + sh * i / (n - 1) for i in range(n)]
        bg = np.zeros((H, W, 4), np.float32)
        fg = np.zeros((H, W, 4), np.float32)
        for tt in times:
            c = cam_at(tt)
            M, s = fx.cam_matrix(c, src_wh, (W, H), frame_wh=(FW, FH), bounds=bounds)
            fg += fgL.sample(M, (W, H), s, sharp=(n == 1))
            cb = _parallax(c, self.ref, self.p_bg, self.bg_zoom)
            Mb, sb = fx.cam_matrix(cb, (bgL.w, bgL.h), (W, H), frame_wh=(FW, FH), bounds=bounds)
            bg += bgL.sample(Mb, (W, H), sb, sharp=(n == 1))
        if n > 1:
            fg /= n
            bg /= n
            step = disp / n
            if step > 3 * ctx.S:  # smooth the gaps between sub-samples along the motion
                pts = np.array([[W / 2, H / 2, 1.0]])
                d = (pts @ M1.T - pts @ M0.T)[0] * s0
                k = min(1.0, step / max(1e-6, disp))
                fg = fx.directional_blur(fg, d[0] * k, d[1] * k)
                bg = fx.directional_blur(bg, d[0] * k, d[1] * k)
        c = cam_at(t)
        M, s = fx.cam_matrix(c, src_wh, (W, H), frame_wh=(FW, FH), bounds=bounds)
        a = fg[..., 3:4]
        rgb = bg[..., :3] * (1 - a) + fg[..., :3]
        S = ctx.S * W / ctx.W if wh else ctx.S

        if self.char == "npc":
            rays = self.rays(t)
            if rays > 0.01:
                # backlight: scatter the bright window around the silhouette
                sky = bg[..., :3].mean(2, keepdims=True) * (1 - a)
                sky = np.clip((sky - 0.55) / 0.45, 0, 1)
                hx, hy = project_point(M, (ctx.A.anchors["npc"]["head_center"][0] * fgL.w, 0.16 * fgL.h))
                r = fx.god_rays(np.repeat(sky, 3, 2), (hx, hy), length=0.42, n=14)
                rgb += r * rays * NPC_SILVER
            if self.fog > 0:
                gy = np.linspace(1, 0, H, dtype=np.float32)[:, None, None]
                rgb += (1 - a) * self.fog * 0.15 * gy * NPC_SILVER
        else:
            if self.fog > 0:
                gy = np.linspace(0.2, 1, H, dtype=np.float32)[:, None, None]
                rgb += (1 - a) * self.fog * 0.06 * gy * CW_EMERALD
        pg = self.print_glow(t) if self.char == "npc" else 0.0
        if pg > 0.01:  # the real shirt lettering lights up in cold silver
            pm = ctx.A.npc_print.sample(M, (W, H), s, sharp=True)[..., 3:4]
            rgb = rgb * (1 - 0.6 * pg * pm) + pm * pg * 0.95 * NPC_SILVER + fx.blur(pm[..., 0], 14 * S, down=2)[..., None] * pg * 0.55 * NPC_SILVER
        rimv = self.rim(t)
        if rimv > 0.01:
            rim = fx.rim_light(a[..., 0], self.rim_dir, width=7 * S)
            col = CW_EMERALD * 0.8 + 0.2 if self.char == "cw" else COOL_WHITE
            rgb += rim[..., None] * rimv * np.float32(col)
        for sw in self.sweeps:
            if sw.t0 <= t <= sw.t0 + sw.dur:
                p = (t - sw.t0) / sw.dur
                band = fx.light_band((H, W), t, sw.angle, sw.width, fx.ease_in_out_cubic(p))
                if sw.target == "lens" and self.char == "cw":
                    lm = ctx.A.cw_lens.sample(M, (W, H), s, sharp=False)[..., 3]
                    m = band * lm
                elif sw.target == "print" and self.char == "npc":
                    m = band * ctx.A.npc_print.sample(M, (W, H), s, sharp=False)[..., 3]
                elif sw.target == "subject":
                    m = band * a[..., 0]
                else:
                    m = band
                env = math.sin(p * math.pi)
                rgb += m[..., None] * sw.strength * env * np.float32(sw.color)
        e = self.exposure(t)
        if e != 1.0:
            rgb *= e
        if self.focus > 0:  # light falls off away from the subject's focal point
            ys = (np.arange(H, dtype=np.float32)[:, None] / H - self.focus_at[1]) * (H / W) * 0.75
            xs = np.arange(W, dtype=np.float32)[None, :] / W - self.focus_at[0]
            rgb *= (1 - self.focus * fx.smoothstep_arr(0.18, 0.75, np.sqrt(xs ** 2 + ys ** 2)))[..., None]
        if self.tint is not None:
            rgb *= np.float32(self.tint)
        if self.dust > 0:
            rgb = dust(ctx, rgb, t, self.dust, self.seed, warm=(self.char == "cw"), M=M, ref=self.ref, src_wh=src_wh)
        if self.fg_particles > 0:
            rgb = dark_bokeh(ctx, rgb, t, self.fg_particles, self.seed + 5)
        return rgb


def dust(ctx: Ctx, rgb, t, amount, seed, warm=False, M=None, ref=None, src_wh=None):
    H, W = rgb.shape[:2]
    rng = np.random.default_rng(seed + 11)
    n = 70
    x0, y0 = rng.uniform(0, W, n), rng.uniform(0, H, n)
    depth = rng.uniform(0.3, 1.0, n)
    vx, vy = rng.normal(0, 8, n), rng.uniform(-22, -6, n)
    ph = rng.uniform(0, 6.28, n)
    xs = (x0 + vx * t * ctx.S + 14 * ctx.S * np.sin(t * 0.7 + ph)) % W
    ys = (y0 + vy * t * ctx.S * depth) % H
    tw = 0.5 + 0.5 * np.sin(t * 3.1 + ph * 3)
    inten = amount * 0.22 * depth * tw * (0.6 + 0.6 * ctx.env(t))
    col = CW_EMERALD * 0.5 + 0.5 if warm else COOL_WHITE
    return fx.splat(rgb, xs, ys, (1.2 + 2.6 * depth) * ctx.S, inten, col)


def dark_bokeh(ctx: Ctx, rgb, t, amount, seed):
    """Out-of-focus dark particles drifting in the foreground (in front of the bright window)."""
    H, W = rgb.shape[:2]
    rng = np.random.default_rng(seed)
    n = 9
    sm = np.zeros((H // 4, W // 4), np.float32)
    for i in range(n):
        x = (rng.uniform(0, W) + (rng.normal(0, 18) + 30) * t * ctx.S) % (W + 200) - 100
        y = (rng.uniform(0, H) - rng.uniform(10, 40) * t * ctx.S) % (H + 200) - 100
        r = rng.uniform(16, 60) * ctx.S
        cv2.circle(sm, (int(x / 4), int(y / 4)), int(r / 4), float(rng.uniform(0.4, 1.0)), -1, cv2.LINE_AA)
    sm = cv2.GaussianBlur(sm, (0, 0), 3.5 * ctx.S + 1)
    m = cv2.resize(sm, (W, H))[..., None]
    return rgb * (1 - amount * 0.75 * m)


class DuoShot:
    """Two characters in one frame: panels (rects) or a diagonal split, with a light seam."""

    def __init__(self, a: CharShot, b: CharShot, layout: str = "stack", split: float = 0.5, angle: float = 0.0,
                 feather: float = 0.012, seam=0.0, seam_color=None, dim=None):
        self.a, self.b, self.layout, self.split, self.angle, self.feather = a, b, layout, split, angle, feather
        self.seam = seam if callable(seam) else (lambda t, s=seam: s)
        self.split_fn = split if callable(split) else (lambda t, s=split: s)
        self.dim = dim if callable(dim) else (lambda t: 1.0)
        self.seam_color = seam_color

    def render(self, ctx: Ctx, t: float, **kw) -> np.ndarray:
        W, H = ctx.W, ctx.H
        sp = self.split_fn(t)
        if self.layout == "stack":
            # panels overlap by 2*feather so the blend never shows a gap
            f = int(self.feather * H)
            ya = int(sp * H) + f
            hb = H - int(sp * H) + f
            top = self.a.render(ctx, t, wh=(W, ya), frame_wh=(W, ya))       # cover-fit to the panel
            bot = self.b.render(ctx, t, wh=(W, hb), frame_wh=(W, hb))
            out = np.zeros((H, W, 3), np.float32)
            yb = int(sp * H) - f
            out[:ya] = top
            ramp = np.linspace(0, 1, ya - yb, dtype=np.float32)[:, None, None]
            ramp = ramp * ramp * (3 - 2 * ramp)
            out[yb:ya] = top[yb:ya] * (1 - ramp) + bot[: ya - yb] * ramp
            out[ya:] = bot[ya - yb:]
            ys = np.arange(H, dtype=np.float32)[:, None]
            dist = np.abs(ys - sp * H)
        else:
            # diagonal seam: each character renders into its own panel (cover-fit to the panel),
            # panels overlap by the seam's vertical extent so the tilted blend never shows a gap
            a = math.radians(self.angle)
            m = int(W / 2 * abs(math.tan(a)) + self.feather * H + 6)
            ya, yb = min(H, int(sp * H) + m), max(0, int(sp * H) - m)
            top = self.a.render(ctx, t, wh=(W, ya), frame_wh=(W, ya))
            bot = self.b.render(ctx, t, wh=(W, H - yb), frame_wh=(W, H - yb))
            ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
            d = (ys - sp * H) * math.cos(a) - (xs - W / 2) * math.sin(a)
            msk = fx.smoothstep_arr(-self.feather * H, self.feather * H, d)[..., None]
            out = np.empty((H, W, 3), np.float32)
            out[:yb] = top[:yb]
            out[ya:] = bot[ya - yb:]
            band = msk[yb:ya]
            out[yb:ya] = top[yb:ya] * (1 - band) + bot[: ya - yb] * band
            dist = np.abs(d)
        sv = self.seam(t)
        if sv > 0.01:
            line = np.exp(-(dist / (2.2 * ctx.S)) ** 2) + 0.35 * np.exp(-(dist / (16 * ctx.S)) ** 2)
            col = self.seam_color if self.seam_color is not None else (NPC_SILVER * 0.55 + CW_EMERALD * 0.45)
            out = out + line[..., None] * sv * np.float32(col)
        return out * self.dim(t)


class LogoShot:
    """Dark stage for the channel logo: converging particles, ring trace, energy pulse, glow."""

    def __init__(self, t_hit: float, size_px: float = 860, t_start: float = 0.0):
        self.t_hit, self.size, self.t_start = t_hit, size_px, t_start

    def render(self, ctx: Ctx, t: float, **kw) -> np.ndarray:
        W, H = ctx.W, ctx.H
        S = ctx.S
        cx, cy = W / 2, H * 0.47
        R = self.size * S / 2 * ctx.A.anchors["logo"]["radius"] / 0.5
        rgb = np.zeros((H, W, 3), np.float32)
        # deep stage: faint radial gradient (never flat grey)
        ys, xs = np.mgrid[0:H:4, 0:W:4].astype(np.float32)
        r = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2) / (0.6 * H)
        pre = clamp01((t - self.t_start) / max(0.01, self.t_hit - self.t_start))
        post = max(0.0, t - self.t_hit)
        stage = np.exp(-r ** 2 * 2.2)[..., None] * (0.020 + 0.05 * smooth(pre) * math.exp(-post / 1.2) + 0.012)
        stage = stage * (NPC_SILVER * 0.6 + CW_EMERALD * 0.4)
        rgb += cv2.resize(stage.astype(np.float32), (W, H))
        # particles converging toward the ring (before the hit), then a gentle orbit afterwards
        rng = np.random.default_rng(404)
        n = 420
        ang = rng.uniform(0, 2 * math.pi, n)
        rad0 = rng.uniform(0.55, 1.25, n) * H * 0.6
        target = R * rng.uniform(0.92, 1.06, n)
        speed = rng.uniform(0.7, 1.3, n)
        if t < self.t_hit:
            k = np.clip(pre * speed, 0, 1) ** 3
            rr = rad0 + (target - rad0) * k
            aa = ang + 0.9 * k
            inten = 0.15 + 0.85 * k
        else:
            rr = target * (1 + 0.6 * (1 - math.exp(-post / 0.25)) * rng.uniform(0.2, 1.0, n))
            aa = ang + 0.9 + 0.15 * post
            inten = np.exp(-post / 0.45) * rng.uniform(0.3, 1.0, n)
        px, py = cx + rr * np.cos(aa), cy + rr * np.sin(aa)
        pcol = np.where(rng.uniform(0, 1, n) < 0.5, 0, 1)
        lay = np.zeros_like(rgb)
        sel = pcol == 0
        inten = np.broadcast_to(np.asarray(inten, np.float32), (n,))
        lay = fx.splat(lay, px[sel], py[sel], 2.2 * S * np.ones(sel.sum()), inten[sel], COOL_WHITE)
        lay = fx.splat(lay, px[~sel], py[~sel], 2.2 * S * np.ones((~sel).sum()), inten[~sel], CW_EMERALD)
        rgb += lay * (0.9 if t < self.t_hit else 1.0) * smooth(pre * 3)
        # metallic streaks tracing the ring silhouette in the last beat before the hit
        tr0 = self.t_hit - 0.56
        if tr0 <= t <= self.t_hit + 0.1:
            q = clamp01((t - tr0) / 0.56)
            for k, (start, colr) in enumerate(((-90, COOL_WHITE), (90, CW_EMERALD * 0.7 + 0.3))):
                a0 = math.radians(start + 360 * fx.ease_in_out_cubic(q) * 0.5)
                a1 = a0 - math.radians(70 * (1 - abs(q - 0.5) * 1.4))
                pts = [(cx + R * 1.005 * math.cos(a1 + (a0 - a1) * j / 12), cy + R * 1.005 * math.sin(a1 + (a0 - a1) * j / 12)) for j in range(13)]
                for p0, p1 in zip(pts[:-1], pts[1:]):
                    rgb = fx.streak(rgb, p0, p1, 3.5 * S, 1.6 * math.sin(q * math.pi) + 0.2, colr, glow=12 * S)
        # the logo itself: snaps in on the hit, pristine afterwards
        if t >= self.t_hit - 1e-6:  # never before the hit frame
            k = clamp01(post / 0.18)
            sc = 1.06 - 0.06 * fx.ease_out_back(k, 2.2) if k < 1 else 1.0
            sc *= 1 + 0.012 * math.sin(post * 1.3) * clamp01(post - 0.6)  # slow breathing hold
            L = ctx.A.logo
            s = self.size * S * sc / L.w
            lcx, lcy = ctx.A.anchors["logo"]["center"]
            M = np.array([[1 / s, 0, L.w * lcx - cx / s], [0, 1 / s, L.h * lcy - cy / s]], np.float64)
            lg = L.sample(M, (W, H), s, sharp=True)
            op = clamp01((post * ctx.fps + 1.2) / 2.0)   # already assembling on the hit frame
            # silver/emerald halo behind the logo (outside its disc only)
            halo = fx.blur(lg[..., 3], 40 * S, down=4)[..., None] * (1 - lg[..., 3:4])
            glow_env = 0.55 * math.exp(-post / 0.35) + 0.16
            rgb += halo * glow_env * (NPC_SILVER * 0.5 + CW_EMERALD * 0.5) * op
            rgb = rgb * (1 - lg[..., 3:4] * op) + lg[..., :3] * op
            # brief specular glint crossing the logo (on the final hit)
        return rgb


class Black:
    def render(self, ctx: Ctx, t: float, **kw):
        return np.zeros((ctx.H, ctx.W, 3), np.float32)


# ----------------------------------------------------------------------------- transitions

def tr_whip(ctx, A, B, p, direction=-1):
    """High-velocity directional whip: both frames travel together, blur follows the velocity."""
    W = ctx.W
    e = fx.ease_in_out_cubic(p)
    off = e * W
    vel = abs(fx.ease_in_out_cubic(min(1, p + 0.04)) - fx.ease_in_out_cubic(max(0, p - 0.04))) / 0.08 * W / ctx.fps * 0.5
    out = np.empty_like(A)
    sh = int(round(off))
    if direction < 0:  # content moves left: A exits left, B enters from the right
        out[:, : W - sh] = A[:, sh:]
        out[:, W - sh:] = B[:, : sh]
    else:
        out[:, sh:] = A[:, : W - sh]
        out[:, :sh] = B[:, W - sh:]
    return fx.directional_blur(out, min(vel, 0.45 * W), 0)


def tr_zoom_collision(ctx, A, B, p):
    """A rushes into the lens, B arrives from behind it; radial blur peaks at the collision."""
    W, H = ctx.W, ctx.H
    if p < 0.5:
        q = p / 0.5
        k = 1 + 1.6 * fx.ease_in_expo(q)
        img = cv2.warpAffine(A, np.float32([[k, 0, (1 - k) * W / 2], [0, k, (1 - k) * H / 2]]), (W, H), borderMode=cv2.BORDER_REFLECT)
        return fx.zoom_blur(img, 0.25 * fx.ease_in_expo(q), n=8)
    q = (p - 0.5) / 0.5
    k = 1 + 0.9 * (1 - fx.ease_out_expo(q))
    img = cv2.warpAffine(B, np.float32([[k, 0, (1 - k) * W / 2], [0, k, (1 - k) * H / 2]]), (W, H), borderMode=cv2.BORDER_REFLECT)
    return fx.zoom_blur(img, 0.22 * (1 - fx.ease_out_expo(q)), n=8)


def tr_shadow_wipe(ctx, A, B, p, angle=-20, strips=7, seed=3):
    """Fragmented shadow wipe: staggered dark strips sweep across and leave B behind them."""
    H, W = A.shape[:2]
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    a = math.radians(angle)
    u = (xs * math.cos(a) + ys * math.sin(a)) / (W * abs(math.cos(a)) + H * abs(math.sin(a)))  # 0..1 across
    v = (-xs * math.sin(a) + ys * math.cos(a)) / (W * abs(math.sin(a)) + H * abs(math.cos(a)))
    rng = np.random.default_rng(seed)
    band = np.floor((v - v.min()) * strips).astype(np.int32) % strips
    delay = rng.uniform(0, 0.35, strips).astype(np.float32)[band]
    front = (p * 1.35 - delay) * 1.25
    edge = fx.smoothstep_arr(front - 0.10, front, u + 0.15)  # 1 behind the front (B), 0 ahead (A)
    m = 1 - edge
    shadow = np.exp(-((u + 0.15 - front) / 0.06) ** 2)[..., None]
    out = A * (1 - m[..., None]) + B * m[..., None]
    return out * (1 - 0.92 * shadow)


def tr_light_reveal(ctx, A, B, p, center=None, amount=1.0):
    """Light-triggered reveal: a bloom of cold light rises over A, B is found inside it."""
    H, W = A.shape[:2]
    cx, cy = center or (W * 0.55, H * 0.25)
    g = math.sin(min(1, p) * math.pi)
    mix = smooth((p - 0.35) / 0.3)
    base = A * (1 - mix) + B * mix
    ys, xs = np.mgrid[0:H:4, 0:W:4].astype(np.float32)
    r = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2) / H
    glow = cv2.resize(np.exp(-(r / (0.18 + 0.5 * g)) ** 2).astype(np.float32), (W, H))[..., None]
    return base + glow * g * 0.75 * amount * COOL_WHITE + base * g * 0.25 * amount


def tr_chroma_compress(ctx, A, B, p):
    """Chromatic compression: A squeezes into a light line with split channels; B unfolds out of it."""
    H, W = A.shape[:2]
    out = np.zeros_like(A)
    if p < 0.5:
        q = fx.ease_in_expo(p / 0.5)
        src, kx = A, max(0.002, 1 - q)
    else:
        q = 1 - fx.ease_out_expo((p - 0.5) / 0.5)
        src, kx = B, max(0.002, 1 - q)
    for ch, d in ((0, 1.0 + 0.5 * q), (1, 1.0), (2, 1.0 - 0.35 * q)):
        k = max(0.002, kx * d)
        M = np.float32([[k, 0, (1 - k) * W / 2], [0, 1, 0]])
        out[..., ch] = cv2.warpAffine(src[..., ch], M, (W, H), borderMode=cv2.BORDER_CONSTANT)
    xs = np.abs(np.arange(W, dtype=np.float32) - W / 2)[None, :, None]
    line = np.exp(-(xs / (3 + 30 * q)) ** 2) * q
    return out + line * (NPC_SILVER * 0.5 + CW_EMERALD * 0.5) * 1.2


def tr_shatter(ctx, A, B, p, seed=9, cells=34, center=None):
    """Dark digital shatter: A splits into shards that fly outward and spin; B emerges darkened."""
    H, W = A.shape[:2]
    rng = np.random.default_rng(seed)
    pts = np.column_stack([rng.uniform(0, W, cells), rng.uniform(0, H, cells)]).astype(np.float32)
    small = 4
    ys, xs = np.mgrid[0:H // small, 0:W // small].astype(np.float32) * small
    d = (xs[..., None] - pts[:, 0]) ** 2 + (ys[..., None] - pts[:, 1]) ** 2
    lab = cv2.resize(np.argmin(d, axis=2).astype(np.float32), (W, H), interpolation=cv2.INTER_NEAREST).astype(np.int32)
    cx, cy = center or (W / 2, H / 2)
    out = B * (0.25 + 0.75 * smooth((p - 0.3) / 0.7))
    for i in range(cells):
        m = (lab == i).astype(np.float32)
        ys_i, xs_i = np.nonzero(m)
        if len(xs_i) == 0:
            continue
        x0, x1, y0, y1 = xs_i.min(), xs_i.max() + 1, ys_i.min(), ys_i.max() + 1
        px, py = pts[i]
        dx, dy = px - cx, py - cy
        L = math.hypot(dx, dy) + 1
        delay = 0.25 * L / math.hypot(W, H)
        q = clamp01((p - delay) / (1 - delay))
        k = fx.ease_in_cubic(q)
        tx, ty = dx / L * k * W * 0.9, dy / L * k * H * 0.5 + 300 * k * k * ctx.S
        ang = rng.uniform(-40, 40) * k
        sc = 1 + 0.4 * k
        sub = A[y0:y1, x0:x1] * (1 - 0.6 * k)
        sm = m[y0:y1, x0:x1]
        Mrot = cv2.getRotationMatrix2D(((x1 - x0) / 2, (y1 - y0) / 2), ang, sc)
        Mrot[0, 2] += x0 + tx
        Mrot[1, 2] += y0 + ty
        wsub = cv2.warpAffine(sub, Mrot, (W, H), borderMode=cv2.BORDER_CONSTANT)
        wm = cv2.warpAffine(sm, Mrot, (W, H), borderMode=cv2.BORDER_CONSTANT)[..., None] * (1 - k ** 3)
        out = out * (1 - wm) + wsub * wm
    # fracture lines light up first (energy), then fade as the shards separate
    edge = (np.abs(np.diff(lab, axis=0, prepend=lab[:1])) + np.abs(np.diff(lab, axis=1, prepend=lab[:, :1]))) > 0
    glow = cv2.GaussianBlur(edge.astype(np.float32), (0, 0), 1.2 * ctx.S + 0.6)
    glow = glow / (glow.max() + 1e-6)
    g_env = math.sin(min(1.0, p / 0.35) * math.pi) * (1 - smooth((p - 0.2) / 0.4))
    return out + glow[..., None] * g_env * 1.4 * (NPC_SILVER * 0.6 + CW_EMERALD * 0.4)


def tr_split_slide(ctx, A, B, p, angle=-12):
    """Motion-matched split: B slides up as a diagonal panel while A keeps travelling with it."""
    H, W = A.shape[:2]
    e = fx.ease_in_out_cubic(p)
    shift = int(e * H * 0.12)
    A2 = np.roll(A, -shift, axis=0)
    B2 = np.roll(B, int((1 - e) * H * 0.12), axis=0)
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    a = math.radians(angle)
    front = H * (1.15 - 1.3 * e)
    d = ys - front - (xs - W / 2) * math.tan(a)
    m = fx.smoothstep_arr(-6 * ctx.S, 6 * ctx.S, d)[..., None]
    out = A2 * (1 - m) + B2 * m
    seam = np.exp(-(d / (3 * ctx.S)) ** 2)[..., None] * math.sin(p * math.pi)
    return out + seam * (NPC_SILVER * 0.5 + CW_EMERALD * 0.5) * 1.4


def tr_dark_flash(ctx, A, B, p, depth=0.92):
    """Quick dark flash cut: dip almost to black for a frame or two at the cut."""
    g = 1 - depth * math.sin(min(1, p) * math.pi) ** 0.5
    return (A if p < 0.5 else B) * g


def tr_glitch_cut(ctx, A, B, p, seed=5):
    base = A if p < 0.5 else B
    other = B if p < 0.5 else A
    amt = math.sin(p * math.pi)
    mixed = fx.glitch_strips(base, seed + int(p * 10), amt, bands=10, rgb=1.0)
    rng = np.random.default_rng(seed + int(p * 10))
    H = A.shape[0]
    for _ in range(4):
        y0 = int(rng.uniform(0, H))
        y1 = min(H, y0 + int(rng.uniform(0.02, 0.08) * H))
        mixed[y0:y1] = other[y0:y1]
    return fx.channel_shift(mixed, 14 * ctx.S * amt)


TRANSITIONS = {"whip": tr_whip, "zoom_collision": tr_zoom_collision, "shadow_wipe": tr_shadow_wipe,
               "light_reveal": tr_light_reveal, "chroma_compress": tr_chroma_compress, "shatter": tr_shatter,
               "split_slide": tr_split_slide, "dark_flash": tr_dark_flash, "glitch_cut": tr_glitch_cut}


# ----------------------------------------------------------------------------- timeline

@dataclass
class Seg:
    t0: float
    t1: float
    shot: object
    name: str = ""


@dataclass
class Trans:
    t0: float
    t1: float
    kind: str
    params: dict = field(default_factory=dict)


@dataclass
class TextCue:
    text: Text
    t_in: float
    t_out: float
    cx: float            # px at 1080 width
    cy: float
    anim_in: str = "slam"     # slam | assemble | reveal | fade | track | none
    in_dur: float = 0.12
    anim_out: str = "fade"    # fade | fragment | exit_left | exit_right | cut | blur
    out_dur: float = 0.12
    scale: float = 1.0
    glow: float = 0.16
    accent_glow: float = 0.0
    shadow: float = 0.6
    tracking: Callable | None = None  # t_local -> em
    drift: tuple = (0.0, 0.0)          # px/s
    seed: int = 0
    scale_fn: Callable | None = None   # t_local -> extra scale
    opacity: float = 1.0
    max_w: float = 900.0               # px at 1080 wide: safe width incl. tracking animation and slam overshoot
    shine: tuple | None = None         # (t0, dur): a band of light travelling through the letters


@dataclass
class Overlay:
    """Frame-level effect over a time window: fn(ctx, img, t, p) -> img."""
    t0: float
    t1: float
    fn: Callable
    after_text: bool = False


class Timeline:
    def __init__(self, ctx: Ctx, duration: float):
        self.ctx, self.duration = ctx, duration
        self.segs: list[Seg] = []
        self.trans: list[Trans] = []
        self.texts: list[TextCue] = []
        self.overlays: list[Overlay] = []
        self.exposure: Callable = lambda t: 1.0   # image only (bass pulses)
        self.fade: Callable = lambda t: 1.0       # everything, text included (opening/ending fades)

    def seg_at(self, t):
        for s in self.segs:
            if s.t0 <= t < s.t1:
                return s
        return self.segs[-1] if t >= self.segs[-1].t1 else self.segs[0]

    def base(self, t: float) -> np.ndarray:
        ctx = self.ctx
        for tr in self.trans:
            if tr.t0 <= t < tr.t1:
                A = self.seg_at(tr.t0 - 1e-4).shot.render(ctx, t)
                B = self.seg_at(tr.t1 + 1e-4).shot.render(ctx, t)
                p = (t - tr.t0) / (tr.t1 - tr.t0)
                return TRANSITIONS[tr.kind](ctx, A, B, p, **tr.params)
        return self.seg_at(t).shot.render(ctx, t)

    def text_layer(self, t: float) -> np.ndarray | None:
        ctx = self.ctx
        active = [c for c in self.texts if c.t_in - 0.001 <= t <= c.t_out + c.out_dur]
        if not active:
            return None
        canvas = np.zeros((ctx.H, ctx.W, 4), np.float32)
        for c in active:
            moving = (t - c.t_in < c.in_dur and c.anim_in in ("slam",)) or (t > c.t_out and c.anim_out in ("exit_left", "exit_right"))
            if moving:
                n = 5
                acc = np.zeros_like(canvas)
                for i in range(n):
                    tt = t + (i / (n - 1) - 0.5) * 0.5 / ctx.fps
                    acc = self._draw_cue(acc, c, tt) if i == 0 else acc + self._draw_cue(np.zeros_like(canvas), c, tt)
                canvas = fx.over_rgba(canvas, acc / n)
            else:
                canvas = self._draw_cue(canvas, c, t)
        return canvas

    def _draw_cue(self, canvas, c: TextCue, t):
        ctx = self.ctx
        S = ctx.S
        lt = t - c.t_in
        st = None
        op = c.opacity
        mask_fn = None
        if lt < 0:
            return canvas
        if c.anim_in == "slam" and lt < c.in_dur * 1.6:
            p = lt / c.in_dur
            st = lambda i, n, p=p: __import__("typo").st_slam(min(1.0, p), i, n)
        elif c.anim_in == "assemble" and lt < c.in_dur:
            p = lt / c.in_dur
            st = lambda i, n, p=p: __import__("typo").st_assemble(p, i, n)
        elif c.anim_in == "fade":
            op *= smooth(lt / c.in_dur)
        elif c.anim_in == "reveal" and lt < c.in_dur:
            p = fx.ease_out_cubic(lt / c.in_dur)
            tw = c.text.width() * c.scale * S
            x0 = c.cx * S - tw / 2 - 20 * S
            front = x0 + (tw + 40 * S) * p
            mask_fn = lambda X, Y, f=front: np.clip((f - X) / (18 * S), 0, 1)
        if t > c.t_out:
            q = (t - c.t_out) / max(1e-3, c.out_dur)
            if q >= 1:
                return canvas
            if c.anim_out == "fade":
                op *= 1 - smooth(q)
            elif c.anim_out == "blur":
                op *= 1 - smooth(q)
                st = lambda i, n, q=q: GlyphState(blur=10 * q, scale=1 + 0.06 * q)
            elif c.anim_out == "fragment":
                st = lambda i, n, q=q, sd=c.seed: __import__("typo").st_fragment(q, i, n, sd, amp=110 * S)
            elif c.anim_out in ("exit_left", "exit_right"):
                d = -520 if c.anim_out == "exit_left" else 520
                st = lambda i, n, q=q, d=d: __import__("typo").st_exit_dir(q, i, n, dx=d * S)
            elif c.anim_out == "cut":
                return canvas
        tr = c.tracking(lt) if c.tracking else None
        sc = c.scale * (c.scale_fn(lt) if c.scale_fn else 1.0)
        widest = max(c.text.width(c.tracking(x) if c.tracking else None) for x in (0.0, 1.0, 3.0, 9.0)) * c.scale * 1.04
        if widest > c.max_w:  # never clip: fit the widest state of this title into the safe width
            sc *= c.max_w / widest
        cx = (c.cx + c.drift[0] * lt) * S
        cy = (c.cy + c.drift[1] * lt) * S
        shine = None
        if c.shine and c.shine[0] <= t <= c.shine[0] + c.shine[1]:
            shine = fx.ease_in_out_cubic((t - c.shine[0]) / c.shine[1])
        return c.text.draw(canvas, cx, cy, state=st, tracking=tr, scale=sc * S, opacity=op, shadow=c.shadow,
                           glow=c.glow, accent_glow=c.accent_glow, mask_fn=mask_fn, shine=shine)

    def frame(self, i: int) -> np.ndarray:
        ctx = self.ctx
        t = i / ctx.fps
        img = self.base(t)
        for o in self.overlays:                      # image-level looks (scrims, light, streaks)
            if o.t0 <= t < o.t1 and not o.after_text:
                img = o.fn(ctx, img, t, (t - o.t0) / (o.t1 - o.t0))
        img = img * self.exposure(t)
        img = fx.bloom(img, threshold=0.78, strength=0.22, sigma=26 * ctx.S)
        img = img * ctx.vig
        img = fx.filmic(img)
        txt = self.text_layer(t)                     # titles stay crisp white above the grade
        if txt is not None:
            img = fx.over(img, txt)
        for o in self.overlays:
            if o.t0 <= t < o.t1 and o.after_text:
                img = o.fn(ctx, img, t, (t - o.t0) / (o.t1 - o.t0))
        img = ctx.impact_post(img, t)                # impacts hit image and type together
        img = img * self.fade(t)
        g = ctx.grain[i % len(ctx.grain)]
        img = img + g * 0.022 * (0.6 + 0.4 * (1 - np.clip(img.mean(2, keepdims=True), 0, 1)))
        return fx.to_u8(img, ctx.grain[(i + 3) % len(ctx.grain)])
