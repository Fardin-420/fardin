"""Subject tracking for motion-tracked reframing: template matching (or motion centroid), then smoothing."""
import cv2
import numpy as np


def _smooth(v, k=9):
    if len(v) < 3:
        return v
    k = min(k, len(v) if len(v) % 2 else len(v) - 1)  # odd window no longer than the signal
    pad = np.pad(v, (k // 2, k // 2), mode="edge")
    return np.convolve(pad, np.ones(k) / k, "valid")


def track(frames, box, method="template", scale=0.25):
    """frames: list of HxWx3 uint8 at the source fps; box: [x0,y0,x1,y1] normalized on the first frame.
    Returns per-frame normalized subject centers (cx, cy)."""
    h, w = frames[0].shape[:2]
    small = [cv2.cvtColor(cv2.resize(f, (int(w * scale), int(h * scale))), cv2.COLOR_RGB2GRAY) for f in frames]
    sh, sw = small[0].shape
    x0, y0, x1, y1 = int(box[0] * sw), int(box[1] * sh), int(box[2] * sw), int(box[3] * sh)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    bw, bh = x1 - x0, y1 - y0
    centers = []
    tmpl = small[0][y0:y1, x0:x1].copy()
    for i, g in enumerate(small):
        if method == "motion" and i > 0:
            d = cv2.absdiff(g, small[i - 1]).astype(np.float32)
            d = cv2.GaussianBlur(d, (0, 0), 3)
            # only consider motion near the current subject (keeps background flicker out)
            mask = np.zeros_like(d)
            mx0, my0 = int(max(0, cx - bw)), int(max(0, cy - bh))
            mask[my0:int(min(sh, cy + bh)), mx0:int(min(sw, cx + bw))] = 1
            d *= mask
            if d.sum() > 50:
                ys, xs = np.mgrid[0:sh, 0:sw]
                ncx, ncy = (d * xs).sum() / d.sum(), (d * ys).sum() / d.sum()
                cx, cy = 0.8 * cx + 0.2 * ncx, 0.8 * cy + 0.2 * ncy
        elif method == "template" and i > 0:
            sx0, sy0 = int(max(0, cx - bw)), int(max(0, cy - bh))
            sx1, sy1 = int(min(sw, cx + bw)), int(min(sh, cy + bh))
            win = g[sy0:sy1, sx0:sx1]
            if win.shape[0] > tmpl.shape[0] and win.shape[1] > tmpl.shape[1]:
                res = cv2.matchTemplate(win, tmpl, cv2.TM_CCOEFF_NORMED)
                _, score, _, loc = cv2.minMaxLoc(res)
                if score > 0.35:
                    cx, cy = sx0 + loc[0] + tmpl.shape[1] / 2, sy0 + loc[1] + tmpl.shape[0] / 2
                    tx0, ty0 = int(cx - tmpl.shape[1] / 2), int(cy - tmpl.shape[0] / 2)
                    fresh = g[ty0:ty0 + tmpl.shape[0], tx0:tx0 + tmpl.shape[1]]
                    if fresh.shape == tmpl.shape:  # slowly adapt to pose changes
                        tmpl = cv2.addWeighted(tmpl, 0.85, fresh, 0.15, 0)
        centers.append((cx / sw, cy / sh))
    c = np.array(centers)
    return np.stack([_smooth(c[:, 0]), _smooth(c[:, 1])], 1)
