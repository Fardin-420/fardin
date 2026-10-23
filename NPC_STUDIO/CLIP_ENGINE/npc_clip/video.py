"""Frame renderer: content-aware 9:16 reframing, keyframed zooms, transitions, grade — piped to x264 with libass on top."""
from __future__ import annotations

import subprocess
from pathlib import Path

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter1d

from .common import FONTS_DIR, FPS, H, W, log

LOOKS = {  # contrast, saturation, warmth (+ = warm highlights), teal (shadow tint), lift
    "punchy":    (1.10, 1.14, 0.010, 0.000, 0.00),
    "cinematic": (1.08, 1.00, 0.030, 0.035, 0.015),
    "clean":     (1.04, 1.06, 0.005, 0.000, 0.00),
    "warm":      (1.06, 1.08, 0.040, 0.000, 0.00),
    "neon":      (1.10, 1.24, -0.020, 0.020, 0.00),
    "npc":       (1.10, 0.98, 0.020, 0.025, 0.00),
}


# ───────────────────────── grade ─────────────────────────

class Grade:
    def __init__(self, look: str, lo: float, hi: float):
        con, sat, warm, teal, lift = LOOKS.get(look, LOOKS["clean"])
        x = np.linspace(0, 1, 256)
        # gentle auto-levels: move the clip's 0.5/99.5 percentiles halfway to the full range
        lo2, hi2 = lo * 0.5, hi + (1 - hi) * 0.5
        y = np.clip((x - lo2) / max(1e-3, hi2 - lo2), 0, 1)
        k = min(0.95, (con - 1) * 3)
        y = y - k * np.sin(2 * np.pi * y) / (2 * np.pi)
        y = lift + y * (1 - lift)
        sh, hl = (1 - y) ** 2, y ** 2
        b = np.clip(y + teal * sh - warm * hl * 0.6, 0, 1)
        g = np.clip(y + teal * sh * 0.35, 0, 1)
        r = np.clip(y + warm * hl - teal * sh * 0.5, 0, 1)
        self.lut = np.stack([b, g, r], 1).reshape(256, 1, 3).__mul__(255).round().astype(np.uint8)
        self.sat = np.clip(np.arange(256) * sat, 0, 255).astype(np.uint8)
        self.do_sat = abs(sat - 1) > 0.01

    def __call__(self, img: np.ndarray) -> np.ndarray:
        img = cv2.LUT(img, self.lut)
        if self.do_sat:
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            hsv[..., 1] = cv2.LUT(hsv[..., 1], self.sat)
            img = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        return img


def vignette(strength=0.20) -> np.ndarray:
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
    m = np.clip(1 - strength * np.clip(r - 0.35, 0, None) ** 1.6 * 1.6, 0.55, 1)
    return np.repeat((m * 255).astype(np.uint8)[..., None], 3, 2)


# ───────────────────────── camera ─────────────────────────

def ease_out(x):
    return 1 - (1 - np.clip(x, 0, 1)) ** 3


def ease_io(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def punch_curve(tl: dict, n: int) -> np.ndarray:
    t = np.arange(n) / FPS
    z = np.zeros(n)
    for e in tl["zooms"]:
        a, at, hold, rel = e["amount"], e["attack"], e["hold"], e["release"]
        u = t - e["t"]
        f = ease_io if e["type"] == "push" else ease_out
        up = f(u / at) * (u >= 0)
        down = 1 - ease_io((u - at - hold) / rel)
        z = np.maximum(z, a * np.minimum(up, np.where(u > at + hold, down, 1)))
    return z


class Faces:
    def __init__(self, ft: dict):
        self.s = ft["samples"]
        self.t = np.array([x["t"] for x in self.s]) if self.s else np.zeros(1)
        self.fps = ft["sample_fps"]

    def near(self, t: float) -> list[dict]:
        if not self.s:
            return []
        i = int(np.clip(np.searchsorted(self.t, t), 0, len(self.s) - 1))
        if i and abs(self.t[i - 1] - t) < abs(self.t[i] - t):
            i -= 1
        return self.s[i]["faces"] if abs(self.t[i] - t) <= 1.5 / self.fps else []

    def mouth_avg(self, t: float, fid: int, win=0.6) -> float:
        a, b = np.searchsorted(self.t, t - win), np.searchsorted(self.t, t + win)
        v = [f["mouth"] for x in self.s[a:b] for f in x["faces"] if f["id"] == fid]
        return float(np.mean(v)) if v else 0.0


def src_times(tl: dict) -> np.ndarray:
    out = []
    for seg in tl["segments"]:
        out += [seg["src_s"] + k / FPS for k in range(seg["frames"])]
    return np.array(out)


def camera_path(tl: dict, faces: Faces, scenes: list[dict], track: int | None = None) -> np.ndarray:
    """Per output frame (cx, cy, size) in normalized source coords, smoothed per continuous shot."""
    st = src_times(tl)
    n = len(st)
    raw = np.full((n, 3), np.nan)
    active, since = None, 0
    for f, t in enumerate(st):
        fs = faces.near(t)
        if track is not None:
            fs = [x for x in fs if x["id"] == track] or []
        if not fs:
            continue
        if track is None and len(fs) > 1:
            m = {x["id"]: faces.mouth_avg(t, x["id"]) for x in fs}
            best = max(fs, key=lambda x: m[x["id"]] + 0.02 * x["w"] * 100)
            if active is None or active not in m:
                active = best["id"]
            elif best["id"] != active and m[best["id"]] > 1.3 * m[active] + 0.3:
                since += 1
                if since >= int(0.8 * FPS):
                    active, since = best["id"], 0
            else:
                since = 0
            pick = next(x for x in fs if x["id"] == active)
        else:
            pick = max(fs, key=lambda x: x["w"] * x["h"])
        raw[f] = [pick["x"] + pick["w"] / 2, pick["y"] + pick["h"] / 2, pick["h"]]
    # fill gaps: hold last known, back-fill the start, default centre
    if np.isnan(raw[:, 0]).all():
        raw[:] = [0.5, 0.42, 0.3]
    else:
        for c in range(3):
            col = raw[:, c]
            idx = np.where(~np.isnan(col))[0]
            raw[:, c] = np.interp(np.arange(n), idx, col[idx]) if len(idx) > 1 else col[idx[0]]
    # shot breaks: scene boundaries crossed, or a source jump between segments
    breaks = [0]
    cuts = [sc["s"] for sc in scenes]
    for f in range(1, n):
        if st[f] - st[f - 1] > 0.5 or any(st[f - 1] < c <= st[f] for c in cuts) \
                or abs(raw[f, 0] - raw[f - 1, 0]) > 0.2:
            breaks.append(f)
    breaks.append(n)
    out = raw.copy()
    for a, b in zip(breaks, breaks[1:]):
        seg = raw[a:b].copy()
        cur = seg[0, 0]
        for k in range(len(seg)):                       # deadzone: ignore small drift
            if abs(seg[k, 0] - cur) > 0.035:
                cur = seg[k, 0]
            seg[k, 0] = cur
        if b - a > 3:
            seg = gaussian_filter1d(seg, sigma=min(0.45 * FPS, (b - a) / 3), axis=0, mode="nearest")
        out[a:b] = seg
    return out


# ───────────────────────── decoding ─────────────────────────

class SourceReader:
    """Reads frames for output-frame source times, decoding forward runs continuously and seeking otherwise."""

    def __init__(self, path: str, w: int, h: int):
        self.path, self.w, self.h = path, w, h
        self.p, self.k, self.t0, self.last = None, -1, 0.0, None

    def _open(self, t: float):
        self.close()
        self.t0 = max(0.0, t)
        cmd = ["ffmpeg", "-v", "error", "-ss", f"{self.t0:.4f}", "-i", self.path, "-vf", f"fps={FPS}",
               "-an", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
        self.p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=self.w * self.h * 3 * 2)
        self.k = -1

    def get(self, t: float) -> np.ndarray:
        want = int(round((t - self.t0) * FPS))
        if self.p is None or want < self.k or want - self.k > 3 * FPS:
            self._open(t)
            want = 0
        sz = self.w * self.h * 3
        while self.k < want:
            buf = self.p.stdout.read(sz)
            if len(buf) < sz:
                break  # end of stream: reuse the last good frame
            self.last = np.frombuffer(buf, np.uint8).reshape(self.h, self.w, 3)
            self.k += 1
        if self.last is None:
            raise RuntimeError(f"could not decode frame at {t:.2f}s from {self.path}")
        return self.last

    def close(self):
        if self.p:
            self.p.stdout.close()
            self.p.kill()
            self.p.wait()
            self.p = None


# ───────────────────────── composition ─────────────────────────

def warp_crop(img, cx, cy, cw, ch, ow, oh, interp=cv2.INTER_CUBIC):
    s = ow / cw
    M = np.float32([[s, 0, ow / 2 - cx * s], [0, s, oh / 2 - cy * s]])
    return cv2.warpAffine(img, M, (ow, oh), flags=interp, borderMode=cv2.BORDER_REFLECT101)


def zoom_blur(img, amount=0.05):
    acc = img.astype(np.float32)
    for k in (1, 2):
        sc = 1 + amount * k / 2
        M = cv2.getRotationMatrix2D((W / 2, H * 0.42), 0, sc)
        acc += cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT101)
    return (acc / 3).astype(np.uint8)


def whip(img, p, direction):
    """p in [0,1]: 0 = untouched, 1 = fully whipped off-frame."""
    if p <= 0.01:
        return img
    shift = direction * ease_io(p) * W * 0.45
    M = np.float32([[1, 0, shift], [0, 1, 0]])
    out = cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT101)
    k = int(3 + 140 * p)
    return cv2.blur(out, (k, 1))


def render_video(tl: dict, ana: dict, face_tracks: dict, vinfo: dict, ass_path: Path, out_path: Path,
                 cover_dir: Path, crf: int = 18) -> dict:
    sw, sh = vinfo["width"], vinfo["height"]
    n = tl["frames"]
    faces = Faces(face_tracks)
    reader = SourceReader(tl["source"]["path"], sw, sh)
    st = src_times(tl)
    punch = punch_curve(tl, n)
    base = np.concatenate([[seg["base_zoom"]] * seg["frames"] for seg in tl["segments"]])
    zoom = base * (1 + punch)
    base_mode = tl["layout"]["mode"]
    runs = tl["layout"].get("runs") or [{"out_s": 0, "out_e": n / FPS + 1, "mode": base_mode}]
    modes = []
    for f in range(n):
        t = f / FPS
        modes.append(next((r["mode"] for r in runs if r["out_s"] - 1e-6 <= t < r["out_e"]), runs[-1]["mode"]))
    paths = [camera_path(tl, faces, ana["scenes"])]
    split_lr, split_m = split_paths(st, modes, faces) if "split" in modes else (None, None)
    # grade from a few representative frames
    lum = []
    for t in st[:: max(1, n // 6)][:6]:
        g = cv2.cvtColor(reader.get(float(t)), cv2.COLOR_BGR2GRAY)
        lum += [np.percentile(g, 0.5) / 255, np.percentile(g, 99.5) / 255]
    reader.close()
    grade = Grade(tl["look"], float(np.min(lum[0::2])), float(np.max(lum[1::2])))
    vig = vignette(0.22 if tl["look"] in ("cinematic", "npc") else 0.14)
    max_up = 2.6
    punch_starts = {int(round(z["t"] * FPS)) for z in tl["zooms"] if z["type"] == "punch"}
    whips = [(int(round(tr["t"] * FPS)), tr["frames"]) for tr in tl["transitions"] if tr["type"] == "whip"]
    cover_frames = sorted({int(round(z["t"] * FPS)) + 6 for z in tl["zooms"]}
                          | {int(n * q) for q in (0.15, 0.35, 0.55, 0.75)})
    cover_dir.mkdir(parents=True, exist_ok=True)

    vf = (f"ass='{ass_path.as_posix()}':fontsdir='{FONTS_DIR.as_posix()}',"
          "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p")
    enc = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS),
         "-i", "-", "-vf", vf, "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-profile:v", "high",
         "-level", "4.1", "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709",
         "-color_trc", "bt709", "-color_range", "tv", "-g", str(FPS * 2), "-an", "-movflags", "+faststart",
         str(out_path)], stdin=subprocess.PIPE)
    blur_bg = None
    try:
        for f in range(n):
            src = reader.get(float(st[f]))
            src = grade(src)
            z = zoom[f]
            mode = modes[f]
            if mode == "split":
                frame = np.empty((H, W, 3), np.uint8)
                m = split_m[f]
                act = None if max(m) < 0.6 or abs(m[0] - m[1]) < 0.25 * max(m) else int(np.argmax(m))
                for p in range(2):
                    cx, cy, fh = split_lr[p][f]
                    ch = min(sh, max(fh * sh * 2.6, sh * 0.5)) / z
                    ch = max(ch, 960 / max_up)
                    cw = min(sw, ch * W / 960)
                    ch = cw * 960 / W
                    x = np.clip(cx * sw, cw / 2, sw - cw / 2)
                    y = np.clip(cy * sh + ch * 0.06, ch / 2, sh - ch / 2)
                    panel = warp_crop(src, x, y, cw, ch, W, 960)
                    if act is not None and act != p:
                        panel = cv2.convertScaleAbs(panel, alpha=0.86)
                    frame[p * 960:(p + 1) * 960] = panel
                frame[956:964] = (28, 43, 255)
            elif mode == "fit":
                fh = int(round(W * sh / sw / 2) * 2)
                cx, cy, _ = paths[0][f]
                cw = sw / z
                ch = sh / z
                x = np.clip(0.5 * sw + (cx - 0.5) * sw * (1 - 1 / z), cw / 2, sw - cw / 2)
                y = np.clip(0.5 * sh + (cy - 0.5) * sh * (1 - 1 / z), ch / 2, sh - ch / 2)
                fg = warp_crop(src, x, y, cw, ch, W, fh)
                if blur_bg is None or f % 2 == 0:
                    sc = max(W / sw, H / sh)
                    small = cv2.resize(src, (max(8, int(sw * sc / 16)), max(8, int(sh * sc / 16))),
                                       interpolation=cv2.INTER_AREA)
                    small = cv2.GaussianBlur(small, (0, 0), 3)
                    bg = cv2.resize(small, (int(sw * sc), int(sh * sc)), interpolation=cv2.INTER_LINEAR)
                    oy, ox = (bg.shape[0] - H) // 2, (bg.shape[1] - W) // 2
                    blur_bg = cv2.convertScaleAbs(bg[oy:oy + H, ox:ox + W], alpha=0.42)
                frame = blur_bg.copy()
                y0 = (H - fh) // 2
                frame[y0:y0 + fh] = fg
                frame[y0 - 3:y0] = frame[y0 + fh:y0 + fh + 3] = (40, 40, 40)
            else:  # track / full
                cx, cy, fhn = paths[0][f]
                # face-size aware: wide shots punch in until the face fills ~22% of frame height
                ch = min(sh, max(fhn * sh / 0.22, H / max_up)) / z
                cw = ch * W / H
                if cw > sw:
                    cw = sw / z
                    ch = cw * H / W
                if H / ch > max_up:
                    ch = H / max_up
                    cw = ch * W / H
                x = np.clip(cx * sw, cw / 2, sw - cw / 2)
                y = np.clip(cy * sh + ch * 0.08, ch / 2, sh - ch / 2)
                frame = warp_crop(src, x, y, cw, ch, W, H)
            if f in punch_starts or (f - 1) in punch_starts:
                frame = zoom_blur(frame, 0.045 if f in punch_starts else 0.02)
            for wf, wn in whips:
                half = wn // 2
                if wf - half <= f < wf:
                    frame = whip(frame, (f - (wf - half) + 1) / half, -1)
                elif wf <= f < wf + half:
                    frame = whip(frame, 1 - (f - wf + 1) / half, +1)
            frame = cv2.multiply(frame, vig, scale=1 / 255)
            if f in cover_frames:
                cv2.imwrite(str(cover_dir / f"frame_{f:05d}.jpg"), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            enc.stdin.write(frame.tobytes())
            if f and f % 300 == 0:
                log(f"  {tl['clip_id']}: frame {f}/{n}")
    finally:
        reader.close()
        enc.stdin.close()
        rc = enc.wait()
    if rc != 0:
        raise RuntimeError(f"x264 encode failed for {tl['clip_id']} (exit {rc})")
    return {"frames": n, "modes": sorted(set(modes))}


def split_paths(st: np.ndarray, modes: list[str], faces: Faces):
    """Left/right speaker paths for split-screen frames: the two largest faces ordered by x, smoothed per run."""
    n = len(st)
    lr = np.full((2, n, 3), np.nan)
    mouth = np.zeros((n, 2))
    for f in range(n):
        if modes[f] != "split":
            continue
        fs = sorted(faces.near(float(st[f])), key=lambda x: -x["w"] * x["h"])[:2]
        if len(fs) < 2:
            continue
        fs.sort(key=lambda x: x["x"])
        for p, x in enumerate(fs):
            lr[p, f] = [x["x"] + x["w"] / 2, x["y"] + x["h"] / 2, x["h"]]
            mouth[f, p] = faces.mouth_avg(float(st[f]), x["id"])
    f = 0
    while f < n:
        if modes[f] != "split":
            f += 1
            continue
        a = f
        while f < n and modes[f] == "split":
            f += 1
        for p in range(2):
            blk = lr[p, a:f]
            for c in range(3):
                col = blk[:, c]
                idx = np.where(~np.isnan(col))[0]
                if len(idx):
                    blk[:, c] = np.interp(np.arange(len(col)), idx, col[idx])
                else:
                    blk[:, c] = [0.3 + 0.4 * p, 0.4, 0.3][c]
            if f - a > 3:
                lr[p, a:f] = gaussian_filter1d(blk, sigma=min(0.45 * FPS, (f - a) / 3), axis=0, mode="nearest")
            else:
                lr[p, a:f] = blk
        mouth[a:f] = gaussian_filter1d(mouth[a:f], sigma=0.4 * FPS, axis=0, mode="nearest") if f - a > 3 else mouth[a:f]
    return lr, mouth
