"""Privacy protection: build per-frame masks from the full OCR scan, and draw them.

    python privacy.py SOURCE.mp4 OCR_DIR PRIVATE_DIR

Rules (all in source pixels, applied before any camera move, so masks follow every zoom):
  email     any text containing '@' (except the generic 'name@email.com' placeholder), 'gmail',
            '[email protected]', and the account line after 'Signed in as'           -> opaque
  field     the input under the profile labels Gender / Race or Ethnicity / Pronouns /
            Birthday, plus any later echo of a value typed there                         -> opaque
  keyboard  inside the EDL's sensitive windows the whole on-screen keyboard (suggestion
            strip, autofill chips, key pop-ups, touch dots) is covered                   -> opaque
Every mask is dilated +-4 frames in time, so a frame where OCR missed the text is still
covered by its neighbours.

Writes ../PRIVACY_MASKS/masks.json (geometry only) and PRIVATE_DIR/private_terms.json
(the detected private strings, used only by qc.py; never committed, never printed).
"""
import json
import re
import sys
from pathlib import Path

import cv2
import numpy as np

import gfx

HERE = Path(__file__).parent
FPS = 30
W, H = 882, 1920
DILATE = 4
PLACEHOLDERS = {"name@email.com", "enter gender", "enter race or ethnicity", "enter race or ethnicit",
                "e.g., she/her, he/him,", "mm / dd / yyyy", "mm/dd/yyyy"}
LABELS = ("gender", "race or ethnicity", "pronouns", "birthday")
PROFILE_WINDOWS = [(18.0, 30.2), (60.0, 69.5)]  # demographics, birthday


def norm(s):
    return re.sub(r"\s+", " ", s.strip().lower())


def in_windows(t, wins):
    return any(a <= t <= b for a, b in wins)


def load_ocr(ocr_dir):
    data = {}
    for p in sorted(Path(ocr_dir).glob("ocr_*.jsonl")):
        for line in open(p):
            try:
                d = json.loads(line)
            except ValueError:  # a line cut off by an interrupted scan; that frame gets re-scanned
                continue
            data[d["f"]] = d
    return data


EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")


def is_label(tx):
    """Profile field label, tolerant of OCR merging words or adding stray glyphs."""
    c = re.sub(r"[^a-z]", "", tx.lower())
    return len(c) <= 22 and any(l.replace(" ", "") in c[:len(l.replace(" ", "")) + 2] for l in LABELS)


def is_email_text(tx):
    n = norm(tx)
    if n in PLACEHOLDERS:
        return False
    if EMAIL_RE.search(n) or "gmail" in n or "email protected" in n or "signed in as" in n:
        return True
    # A leading '@' with no address is the red "(!)" warning icon read by OCR ("(!) Needs a ...").
    return "@" in n and not n.startswith("@")


def keyboard_edges(src, wins, n, scale=0.5):
    """Keyboard top edge for every frame inside the sensitive windows (pixel detector)."""
    import subprocess
    from ocr_scan import keyboard_top
    sw, sh = int(W * scale), int(H * scale)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-vf", f"scale={sw}:{sh}", "-f", "rawvideo",
                          "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    out = {}
    for f in range(n):
        buf = p.stdout.read(sw * sh * 3)
        if len(buf) < sw * sh * 3:
            break
        if in_windows(f / FPS, [(a - 0.5, b + 0.5) for a, b in wins]):
            out[f] = keyboard_top(np.frombuffer(buf, np.uint8).reshape(sh, sw, 3), scale)
    p.kill()
    return out


def build(src, ocr_dir, private_dir):
    edl = json.loads((HERE / "edl.json").read_text())
    kb_wins = edl["sensitive_windows"]["keyboard"]
    ocr = load_ocr(ocr_dir)
    n = max(ocr) + 1
    missing = [f for f in range(n) if f not in ocr]
    if missing:
        raise SystemExit(f"OCR scan incomplete: {len(missing)} frames missing")

    kb = keyboard_edges(src, kb_wins, n)
    raw = {f: [] for f in range(n)}
    terms = set()
    for f in range(n):
        t = f / FPS
        d = ocr[f]
        fields = []
        for x0, y0, x1, y1, sc, tx in d["boxes"]:
            nt = norm(tx)
            if is_email_text(tx):
                if "signed in as" in nt and "@" not in nt and "protected" not in nt:
                    raw[f].append([x1 - 4, y0 - 10, 872, y1 + 10, "email"])  # value right of the label
                else:
                    raw[f].append([x0 - 12, y0 - 10, x1 + 12, y1 + 10, "email"])
                    if "@" in nt:
                        terms.add(nt.split()[-1])
            if in_windows(t, PROFILE_WINDOWS) and is_label(tx):
                r = [x0 - 30, y1 - 4, min(x0 + 750, 872), y1 + 104]
                fields.append(r)
                raw[f].append(r + ["field"])
        # Values inside a protected field become private terms (to catch echoes and for QC).
        for x0, y0, x1, y1, sc, tx in d["boxes"]:
            cx, cy, nt = (x0 + x1) / 2, (y0 + y1) / 2, norm(tx)
            if nt in PLACEHOLDERS or is_label(tx) or len(nt) < 2:
                continue
            if any(r[0] <= cx <= r[2] and r[1] <= cy <= r[3] for r in fields):
                terms.add(nt)
        if in_windows(t, kb_wins) and kb.get(f) is not None:
            raw[f].append([0, kb[f] - 6, W, H, "keyboard"])

    # Echo pass: a private value appearing anywhere during the profile steps is masked too, even
    # after its label has scrolled off-screen. Whole-word matches; every collected value is used
    # (values can be ordinary words), since over-masking on these screens costs nothing.
    echo = [x for x in terms if len(re.sub(r"[^0-9a-z]", "", x)) >= 3 and "@" not in x]
    pats = [re.compile(r"(?<![0-9a-z])" + re.escape(x) + r"(?![0-9a-z])") for x in echo]
    for f in range(n):
        if not in_windows(f / FPS, PROFILE_WINDOWS):
            continue
        for x0, y0, x1, y1, sc, tx in ocr[f]["boxes"]:
            if any(p.search(norm(tx)) for p in pats):
                raw[f].append([x0 - 12, y0 - 10, x1 + 12, y1 + 10, "field"])

    # Keyboard inside a sensitive window but not detected on this frame (e.g. mid slide-in):
    # reuse the nearest detected keyboard edge within 10 frames.
    for f in range(n):
        if in_windows(f / FPS, kb_wins) and not any(r[4] == "keyboard" for r in raw[f]):
            near = [kb[g] for g in range(max(0, f - 10), min(n, f + 11)) if kb.get(g) is not None]
            if near:
                raw[f].append([0, min(near) - 6, W, H, "keyboard"])

    masks = {}
    for f in range(n):
        acc = []
        for g in range(max(0, f - DILATE), min(n, f + DILATE + 1)):
            acc += raw[g]
        if acc:
            masks[f] = merge(acc)

    stats = {}
    for f, rs in masks.items():
        for r in rs:
            s = stats.setdefault(r[4], [f, f, 0])
            s[0], s[1], s[2] = min(s[0], f), max(s[1], f), s[2] + 1
    out = {"version": 1, "fps": FPS, "dilate_frames": DILATE,
           "frames": {str(f): rs for f, rs in sorted(masks.items())},
           "summary": {k: {"first_s": round(v[0] / FPS, 2), "last_s": round(v[1] / FPS, 2), "mask_frames": v[2]}
                       for k, v in stats.items()},
           "ranges": ranges(masks)}
    (HERE.parent / "PRIVACY_MASKS").mkdir(exist_ok=True)
    (HERE.parent / "PRIVACY_MASKS" / "masks.json").write_text(json.dumps(out))
    Path(private_dir).mkdir(parents=True, exist_ok=True)
    (Path(private_dir) / "private_terms.json").write_text(json.dumps(sorted(terms)))
    print("masked frames:", len(masks), "| kinds:", out["summary"], "| private terms collected:", len(terms))


def merge(rects):
    """Union overlapping rects of the same kind (keeps the mask list short)."""
    out = []
    for kind in ("keyboard", "email", "field"):
        rs = [list(map(int, r[:4])) for r in rects if r[4] == kind]
        changed = True
        while changed:
            changed = False
            res = []
            while rs:
                a = rs.pop()
                for b in rs[:]:
                    if a[0] <= b[2] + 8 and b[0] <= a[2] + 8 and a[1] <= b[3] + 8 and b[1] <= a[3] + 8:
                        a = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]
                        rs.remove(b)
                        changed = True
                res.append(a)
            rs = res
        out += [r + [kind] for r in rs]
    return out


def ranges(masks):
    """Contiguous masked time ranges per kind, for the edit report."""
    res = {}
    for kind in ("email", "field", "keyboard"):
        fs = sorted(f for f, rs in masks.items() if any(r[4] == kind for r in rs))
        rr = []
        for f in fs:
            if rr and f - rr[-1][1] <= 1:
                rr[-1][1] = f
            else:
                rr.append([f, f])
        res[kind] = [[round(a / FPS, 2), round(b / FPS, 2)] for a, b in rr]
    return res


# ───────────────────────── drawing ─────────────────────────

class Masks:
    def __init__(self, path=None):
        import os
        path = path or os.environ.get("NPC_MASKS") or HERE.parent / "PRIVACY_MASKS" / "masks.json"
        self.frames = json.loads(Path(path).read_text())["frames"]

    def get(self, f):
        return self.frames.get(str(f), [])

    def apply(self, img, f):
        rs = self.get(f)
        if not rs:
            return img
        img = img.copy()
        for x0, y0, x1, y1, kind in sorted(rs, key=lambda r: r[4] != "keyboard"):
            x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
            if x1 - x0 < 2 or y1 - y0 < 2:
                continue
            draw_mask(img, x0, y0, x1, y1, kind)
        return img


def draw_mask(img, x0, y0, x1, y1, kind):
    w, h = x1 - x0, y1 - y0
    if kind == "keyboard":
        panel = np.empty((h, w, 3), np.uint8)
        panel[:] = (16, 15, 15)
        yy, xx = np.mgrid[0:h, 0:w]
        panel[((xx + yy) % 34) < 2] = (26, 24, 24)
        panel[:3] = gfx.RED
        img[y0:y1, x0:x1] = panel
        lock = gfx.lock_icon(44, gfx.IVORY)
        t1 = gfx.text_sprite("PRIVATE INPUT HIDDEN", "mono", 30, gfx.IVORY, 0.12)
        t2 = gfx.text_sprite("typing is masked to protect personal data", "medium", 26, gfx.STEEL)
        cy = y0 + min(h // 2, 300)
        gfx.blend(img, lock, x0 + (w - lock.shape[1]) // 2, cy - 90)
        gfx.blend(img, t1, x0 + (w - t1.shape[1]) // 2, cy - 30)
        gfx.blend(img, t2, x0 + (w - t2.shape[1]) // 2, cy + 18, 0.9)
        return
    roi = img[y0:y1, x0:x1].astype(np.float32)
    m = gfx.rr_mask(w, h, min(12, h // 3))[..., None]
    fill = np.array((24, 22, 22), np.float32)
    img[y0:y1, x0:x1] = (roi * (1 - m) + fill * m).astype(np.uint8)  # opaque inside the rounded rect
    # rounded corners leave tiny gaps at the very corners: cover the core fully as well
    c = min(12, h // 3)
    img[y0 + c // 2:y1 - c // 2, x0 + c // 2:x1 - c // 2] = (24, 22, 22)
    img[y0 + 4:y1 - 4, x0:x0 + 4] = gfx.RED
    label = "EMAIL HIDDEN" if kind == "email" else "PRIVATE"
    size = int(min(26, max(12, h * 0.42)))
    t = gfx.text_sprite(label, "mono", size, gfx.IVORY, 0.12)
    lock = gfx.lock_icon(size + 4, gfx.IVORY)
    tw = t.shape[1] + lock.shape[1] + 8
    if tw < w - 16:
        x = x0 + 18
        gfx.blend(img, lock, x, y0 + (h - lock.shape[0]) // 2, 0.9)
        gfx.blend(img, t, x + lock.shape[1] + 8, y0 + (h - t.shape[0]) // 2, 0.9)


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2], sys.argv[3])
