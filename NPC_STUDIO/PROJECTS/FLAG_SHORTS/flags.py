"""Flag artwork from the npm package flag-icons (MIT), rasterised with cairosvg."""
import io
import json
import subprocess
from pathlib import Path

import cairosvg
import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
PKG = HERE / "node_modules" / "flag-icons"
CACHE = HERE / ".cache"
SHORT = {"us": "USA", "gb": "UK", "ae": "UAE", "kr": "South Korea", "kp": "North Korea", "ru": "Russia", "ir": "Iran",
         "tr": "Turkey", "cd": "DR Congo", "cz": "Czechia", "ba": "Bosnia", "do": "Dominican Rep.", "vn": "Vietnam",
         "sy": "Syria", "tz": "Tanzania", "bo": "Bolivia", "ve": "Venezuela", "md": "Moldova", "la": "Laos"}


def ensure_package():
    if not (PKG / "flags" / "1x1").is_dir():
        print("installing flag-icons (npm)…", flush=True)
        subprocess.run(["npm", "install", "--silent", "--no-audit", "--no-fund"], cwd=HERE, check=True)


def country_name(code):
    code = code.lower()
    if code in SHORT:
        return SHORT[code]
    for c in json.loads((PKG / "country.json").read_text()):
        if c["code"] == code:
            return c["name"]
    raise SystemExit(f'unknown country code "{code}" (not in flag-icons)')


def flag_square(code, size=512):
    """Square RGB flag raster (cached)."""
    code = code.lower()
    CACHE.mkdir(exist_ok=True)
    f = CACHE / f"{code}_{size}.png"
    if not f.exists():
        svg = PKG / "flags" / "1x1" / f"{code}.svg"
        if not svg.exists():
            raise SystemExit(f'no flag-icons SVG for "{code}"')
        png = cairosvg.svg2png(url=str(svg), output_width=size, output_height=size)
        Image.open(io.BytesIO(png)).convert("RGB").save(f)
    return Image.open(f).convert("RGB")


def flag_disc(code, diameter, rim=4, pad=3, grey=False):
    """Flag clipped to a circle with a white rim, anti-aliased (4x supersampled). RGBA, size diameter+2*pad."""
    ss = 4
    d, size = diameter * ss, (diameter + 2 * pad) * ss
    img = flag_square(code).resize((d, d), Image.LANCZOS)
    if grey:
        img = Image.merge("RGB", [img.convert("L").point(lambda v: int(v * 0.55 + 30))] * 3)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    mask = Image.new("L", (size, size), 0)
    o = pad * ss
    ImageDraw.Draw(mask).ellipse([o, o, o + d - 1, o + d - 1], fill=255)
    out.paste(img, (o, o))
    out.putalpha(mask)
    dr = ImageDraw.Draw(out)
    dr.ellipse([o, o, o + d - 1, o + d - 1], outline=(150, 150, 155, 255) if grey else (255, 255, 255, 255), width=rim * ss)
    return out.resize((diameter + 2 * pad, diameter + 2 * pad), Image.LANCZOS)


def flag_colors(code, k=3):
    """Dominant flag colours, most 'colourful' first (for trails, confetti, card accents)."""
    a = np.asarray(flag_square(code).resize((48, 48), Image.BILINEAR)).reshape(-1, 3).astype(int)
    q = a // 32
    keys, inv, counts = np.unique(q[:, 0] * 64 + q[:, 1] * 8 + q[:, 2], return_inverse=True, return_counts=True)
    cols = []
    for j in np.argsort(-counts)[:6]:
        c = a[inv == j].mean(axis=0)
        sat = (c.max() - c.min()) / max(c.max(), 1)
        cols.append((counts[j] / len(a) * (0.25 + sat) * (0.4 + c.max() / 255), tuple(int(v) for v in c)))
    cols.sort(reverse=True)
    return [c for _, c in cols[:k]]


def emoji(code):
    return "".join(chr(0x1F1E6 + ord(ch) - 97) for ch in code.lower())
