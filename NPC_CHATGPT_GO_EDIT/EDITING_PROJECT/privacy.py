"""Privacy protection for the ChatGPT Go / Rappi recording: masks from OCR, and drawing them.

    python privacy.py OCR_DIR PRIVATE_DIR

Rules (source pixels, applied before any camera move, so masks follow every zoom and ramp):
  code   promo codes: any chatgpt.com URL text inside the promo windows (address bar,
         clipboard chip, suggestion rows), 'promoCode=' values, 'chatgpt.com/p/<id>' links,
         and code-like tokens (8+ chars mixing capitals and digits) anywhere          -> opaque
  name   the account name: the line under 'Bienvenido' and the 'Felicitaciones ...' line -> opaque
  photo  the Google profile photo right of the 'Google' logo on result pages             -> opaque
  ip     IPv4 addresses (VPN server address)                                             -> opaque
  email  e-mail addresses and phone numbers anywhere                                     -> opaque
Masks are dilated +-4 frames. PRIVATE_DIR/private_terms.json keeps the detected strings for
qc.py only; it is never committed or printed.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

import gfx

HERE = Path(__file__).parent
FPS = 30
W, H = 864, 1920
DILATE = 4
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
IP_RE = re.compile(r"(?<![\d.])\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?![\d.])")  # no \b: OCR glues words to it
PHONE_RE = re.compile(r"(?<![\w$])\+?\d[\d\s-]{9,}\d(?![\w%])")


def norm(s):
    return re.sub(r"\s+", " ", s.strip().lower())


PROMO_URL_RE = re.compile(r"[?&/]promocode|promocode=")


def codelike(tx):
    """Random-code-like token: 10-24 alphanumerics, 3+ capitals, at most 3 lowercase letters and
    digits in 2+ separate groups. OCR glues ordinary words together ('pay20USD',
    '30DIASDEENVIOS'); those keep their digits in one run and must not match."""
    for tok in re.findall(r"[A-Za-z0-9]{10,24}", tx):
        if (len(re.findall(r"\d+", tok)) >= 2 and sum(c.isupper() for c in tok) >= 3
                and sum(c.islower() for c in tok) <= 3):
            return True
    return False


def inside(t, wins):
    return any(a <= t <= b for a, b in wins)


def load_ocr(ocr_dir):
    data = {}
    for p in sorted(Path(ocr_dir).glob("ocr_*.jsonl")):
        for line in open(p):
            try:
                d = json.loads(line)
            except ValueError:
                continue
            data[d["f"]] = d
    return data


def detect(f, boxes, rules):
    t = f / FPS
    out, terms = [], set()
    pad = lambda b, k: [b[0] - 12, b[1] - 10, b[2] + 12, b[3] + 10, k]
    for i, (x0, y0, x1, y1, sc, tx) in enumerate(boxes):
        n = norm(tx)
        if EMAIL_RE.search(n) or "gmail" in n or PHONE_RE.search(tx):
            out.append(pad((x0, y0, x1, y1), "email"))
            terms.add(n)
        if IP_RE.search(n) or "ipaddress" in n.replace(" ", ""):
            out.append(pad((x0, y0, x1, y1), "ip"))
        if (PROMO_URL_RE.search(n.replace(" ", "")) or "chatgpt.com/p/" in n.replace(" ", "") or codelike(tx)
                or (inside(t, rules["promo_windows"]) and "chatgpt.com" in n.replace(" ", ""))):
            out.append(pad((x0, y0, x1, y1), "code"))
            m = re.search(r"promocode=?([a-z0-9]{4,})", n.replace(" ", ""))
            if m:
                terms.add(m.group(1))
        if inside(t, rules["name_windows"]):
            if n.startswith("¡felicitaciones") or n.startswith("felicitaciones") or "felicitaciones" in n:
                out.append(pad((x0, y0, x1, y1), "name"))
                rest = n.split("felicitaciones", 1)[1].strip(" !¡")
                if len(rest) >= 2:
                    terms.add(rest)
            if n.startswith("bienvenido"):
                # the account name is the short line directly under 'Bienvenido'
                for bx0, by0, bx1, by1, _, btx in boxes:
                    if 0 <= by0 - y1 <= 130 and bx1 > x0 - 60 and bx0 < x1 + 60 and len(btx.strip()) <= 24:
                        out.append(pad((bx0, by0, bx1, by1), "name"))
                        if len(btx.strip()) >= 2:
                            terms.add(norm(btx))
                # if the name line was not read, cover the space where it sits
                out.append([x0 - 40, y1 + 2, x1 + 40, y1 + 74, "name"])
        if inside(t, rules["google_header_windows"]) and n == "google" and 280 < (x0 + x1) / 2 < 600 and y1 < 520:
            cy = (y0 + y1) / 2
            out.append([736, int(cy - 54), 856, int(cy + 54), "photo"])
    return out, terms


def build(ocr_dir, private_dir, frames_file=None):
    edl = json.loads((HERE / "edl.json").read_text())
    rules = edl["privacy"]
    ocr = load_ocr(ocr_dir)
    need = json.loads(Path(frames_file).read_text()) if frames_file else sorted(ocr)
    missing = [f for f in need if f not in ocr]
    if missing:
        raise SystemExit(f"OCR scan incomplete: {len(missing)} of {len(need)} required frames missing")
    raw, terms = {}, set()
    for f, d in ocr.items():
        r, tm = detect(f, d["boxes"], rules)
        raw[f] = r
        terms |= tm
    # echo pass: a detected private value appearing elsewhere is masked too
    echo = [x for x in terms if len(re.sub(r"[^0-9a-z]", "", x)) >= 3]
    pats = [re.compile(r"(?<![0-9a-z])" + re.escape(x) + r"(?![0-9a-z])") for x in echo]
    for f, d in ocr.items():
        for x0, y0, x1, y1, sc, tx in d["boxes"]:
            if any(p.search(norm(tx)) for p in pats):
                raw[f].append([x0 - 12, y0 - 10, x1 + 12, y1 + 10, "code"])
    # Static screens: a name / IP found on any frame of its window is covered on every frame of
    # that window, so a frame where OCR missed the line is still protected.
    for kind, wins in (("name", rules["name_windows"]), ("ip", rules["vpn_windows"])):
        for a, b in wins:
            fs = range(int(a * FPS), int(b * FPS) + 1)
            rects = [r for f in fs for r in raw.get(f, []) if r[4] == kind]
            if rects:
                for f in fs:
                    raw.setdefault(f, []).extend(rects)
    masks = {}
    allf = sorted(set(raw) | set(need))
    for f in allf:
        acc = []
        for g in range(f - DILATE, f + DILATE + 1):
            acc += raw.get(g, [])
        if acc:
            masks[f] = merge(acc)
    rng = {}
    for kind in ("code", "name", "photo", "ip", "email"):
        fs = sorted(f for f, rs in masks.items() if any(r[4] == kind for r in rs))
        rr = []
        for f in fs:
            if rr and f - rr[-1][1] <= 6:
                rr[-1][1] = f
            else:
                rr.append([f, f])
        rng[kind] = [[round(a / FPS, 2), round(b / FPS, 2)] for a, b in rr]
    out = {"version": 1, "fps": FPS, "dilate_frames": DILATE, "frames_scanned": len(ocr),
           "frames_required": len(need), "frames": {str(f): rs for f, rs in sorted(masks.items())}, "ranges": rng}
    (HERE.parent / "PRIVACY_MASKS").mkdir(exist_ok=True)
    (HERE.parent / "PRIVACY_MASKS" / "masks.json").write_text(json.dumps(out))
    Path(private_dir).mkdir(parents=True, exist_ok=True)
    (Path(private_dir) / "private_terms.json").write_text(json.dumps(sorted(terms)))
    print("masked frames:", len(masks), "| ranges:", rng, "| private terms:", len(terms))


def merge(rects):
    out = []
    for kind in ("code", "name", "photo", "ip", "email"):
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


# ───────────────────────── drawing ─────────────────────────

LABELS = {"code": "CODE HIDDEN", "name": "NAME HIDDEN", "photo": "", "ip": "HIDDEN", "email": "PRIVATE"}


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
        for x0, y0, x1, y1, kind in rs:
            x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
            if x1 - x0 >= 2 and y1 - y0 >= 2:
                draw_mask(img, x0, y0, x1, y1, kind)
        return img


def draw_mask(img, x0, y0, x1, y1, kind):
    w, h = x1 - x0, y1 - y0
    fill = (24, 22, 22)
    if kind == "photo":  # opaque disc in the avatar slot
        import cv2
        cv2.ellipse(img, ((x0 + x1) // 2, (y0 + y1) // 2), (w // 2, h // 2), 0, 0, 360, fill, -1, cv2.LINE_AA)
        cv2.ellipse(img, ((x0 + x1) // 2, (y0 + y1) // 2), (w // 2, h // 2), 0, 0, 360, gfx.RED, 2, cv2.LINE_AA)
        return
    c = min(12, h // 3)
    roi = img[y0:y1, x0:x1].astype(np.float32)
    m = gfx.rr_mask(w, h, c)[..., None]
    img[y0:y1, x0:x1] = (roi * (1 - m) + np.array(fill, np.float32) * m).astype(np.uint8)
    img[y0 + c // 2:y1 - c // 2, x0 + c // 2:x1 - c // 2] = fill  # fully opaque core
    img[y0 + 4:y1 - 4, x0:x0 + 4] = gfx.RED
    label = LABELS.get(kind, "PRIVATE")
    if not label:
        return
    size = int(min(24, max(11, h * 0.42)))
    t = gfx.text_sprite(label, "mono", size, gfx.IVORY, 0.12)
    lock = gfx.lock_icon(size + 4, gfx.IVORY)
    if t.shape[1] + lock.shape[1] + 8 < w - 16:
        x = x0 + 16
        gfx.blend(img, lock, x, y0 + (h - lock.shape[0]) // 2, 0.9)
        gfx.blend(img, t, x + lock.shape[1] + 8, y0 + (h - t.shape[0]) // 2, 0.9)


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
