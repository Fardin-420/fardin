"""Cover / thumbnail for an episode: out/<slug>.cover.jpg (1080x1920) and out/<slug>.thumb.jpg (1280x720).

Built from the episode's own fight (a blurred, darkened action frame), with the contenders' flags big and
crisp, and the hook as the headline. It never shows who wins.
"""
import math

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

import flags
import render
from render import CX, CY, H, W, text_sprite


def _headline(cfg):
    """'PICK ONE. NO SWITCHING.' → ('PICK ONE', 'NO SWITCHING.')"""
    hook = (cfg.get("cover_text") or cfg["hook"]).upper().strip()
    if "." in hook[:-1]:
        a, b = hook.split(".", 1)
        return a.strip(), b.strip()
    return hook, ""


def _glow_disc(code, d):
    """Flag disc with a soft coloured halo behind it."""
    col = flags.flag_colors(code)[0]
    pad = int(d * 0.28)
    size = d + 2 * pad
    halo = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse([pad - 10, pad - 10, pad + d + 10, pad + d + 10], fill=col + (200,))
    halo = halo.filter(ImageFilter.GaussianBlur(d * 0.11))
    disc = flags.flag_disc(code, d, rim=max(6, d // 30), pad=0)
    halo.alpha_composite(disc, (pad, pad))
    return halo


def _scale(spr, s):
    return spr.resize((max(1, int(spr.width * s)), max(1, int(spr.height * s))), Image.LANCZOS)


def make_cover(cfg, res, renderer, out_dir):
    slug, codes, names = cfg["slug"], [t.lower() for t in cfg["teams"]], [n.upper() for n in cfg["names"]]
    nt = len(codes)
    # ---- background: a real moment from this fight (all balls still in), blurred and dimmed
    f = min(int(0.9 * cfg["fps"]), res["total_frames"] - 1)
    bg = renderer.frame(f)
    bg = bg.crop((0, 520, W, 1300)).resize((W, H), Image.BICUBIC)       # arena only, no UI
    bg = bg.filter(ImageFilter.GaussianBlur(14))
    bg = ImageEnhance.Brightness(bg).enhance(0.42)
    bg = ImageEnhance.Color(bg).enhance(1.25)
    img = Image.blend(renderer.bg, bg, 0.8).convert("RGBA")

    # ---- neon ring with the gap, as in the video
    ring = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    R, cy = 430, 930
    gd = ImageDraw.Draw(ring)
    gap = 26
    gd.arc([CX - R, cy - R, CX + R, cy + R], -90 + gap / 2, 270 - gap / 2, fill=(80, 175, 255, 255), width=26)
    glow = ring.filter(ImageFilter.GaussianBlur(22))
    img.alpha_composite(glow)
    img.alpha_composite(glow)
    core = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(core).arc([CX - R, cy - R, CX + R, cy + R], -90 + gap / 2, 270 - gap / 2, fill=(200, 235, 255, 255), width=9)
    img.alpha_composite(core)
    for a in (-90 - gap / 2, -90 + gap / 2):
        x, y = CX + R * math.cos(math.radians(a)), cy + R * math.sin(math.radians(a))
        ImageDraw.Draw(img).ellipse([x - 14, y - 14, x + 14, y + 14], fill=(255, 255, 255, 255))

    # ---- the contenders: big flags on a circle inside the ring, names under them
    if nt == 2:
        d, spots, vs_y = 300, [(CX - 190, cy), (CX + 190, cy)], cy
    elif nt == 3:                                        # triangle: one on top, two below, VS in the middle
        d, spots, vs_y = 230, [(CX, cy - 215), (CX - 185, cy + 125), (CX + 185, cy + 125)], cy - 45
    else:
        rr = R * 0.55
        d = int(min(210, 2 * rr * math.sin(math.pi / nt) * 0.72))
        spots = [(CX + rr * math.cos(2 * math.pi * k / nt - math.pi / 2), cy + rr * math.sin(2 * math.pi * k / nt - math.pi / 2)) for k in range(nt)]
        vs_y = cy
    for k, (x, y) in enumerate(spots):
        disc = _glow_disc(codes[k], d)
        img.alpha_composite(disc, (int(x - disc.width / 2), int(y - disc.height / 2)))
        lab = text_sprite(names[k], max(30, int(d * 0.19)), max_w=int(d * 1.5), stroke=7)
        above = nt >= 3 and y < cy - 60                  # top flag: name above it, so VS stays clear
        ly = y - d / 2 - 12 - lab.height if above else y + d / 2 + 12
        img.alpha_composite(lab, (int(x - lab.width / 2), int(ly)))
    vs = text_sprite("VS", 104 if nt <= 3 else 84, fill=(255, 214, 64), stroke=11)
    img.alpha_composite(vs, (CX - vs.width // 2, int(vs_y - vs.height / 2)))

    # ---- headline from the hook, inside the safe area (below the top 10%)
    big, small = _headline(cfg)
    head = text_sprite(render.wrap_two(big, 190, 1000), 190, max_w=1000, stroke=16)
    img.alpha_composite(head, (CX - head.width // 2, 215))
    y = 215 + head.height + 14
    if small:
        sub = text_sprite(small, 82, fill=(255, 214, 64), max_w=900, stroke=9)
        img.alpha_composite(sub, (CX - sub.width // 2, y))
    # ---- bottom question, kept above the bottom 20%
    q = text_sprite("WHO SURVIVES?", 92, max_w=900, stroke=10)
    img.alpha_composite(q, (CX - q.width // 2, cy + R + 40))

    cover = img.convert("RGB")
    p_cover = out_dir / f"{slug}.cover.jpg"
    cover.save(p_cover, quality=93, subsampling=0)
    # ---- 16:9 thumbnail variant (for community posts / long-form reuse)
    th = Image.new("RGB", (1280, 720))
    th.paste(renderer.bg.resize((1280, 2276)).crop((0, 778, 1280, 1498)))
    band = ImageEnhance.Brightness(bg.resize((1280, 2276)).crop((0, 778, 1280, 1498))).enhance(1.0)
    th = Image.blend(th, band, 0.8).convert("RGBA")
    dd = 230 if nt <= 3 else int(1100 / nt) - 30
    xs = [640 + (k - (nt - 1) / 2) * (dd + (170 if nt <= 3 else 30)) for k in range(nt)]
    for k, x in enumerate(xs):
        disc = _glow_disc(codes[k], dd)
        th.alpha_composite(disc, (int(x - disc.width / 2), int(400 - disc.height / 2)))
        if k < nt - 1 and nt <= 4:
            v = text_sprite("VS", 78, fill=(255, 214, 64), stroke=9)
            th.alpha_composite(v, (int((x + xs[k + 1]) / 2 - v.width / 2), int(400 - v.height / 2)))
    h2 = text_sprite(big, 132, max_w=1180, stroke=12)
    th.alpha_composite(h2, (640 - h2.width // 2, 34))
    q2 = text_sprite("WHO SURVIVES?", 70, fill=(255, 214, 64), max_w=1100, stroke=8)
    th.alpha_composite(q2, (640 - q2.width // 2, 720 - q2.height - 30))
    p_thumb = out_dir / f"{slug}.thumb.jpg"
    th.convert("RGB").save(p_thumb, quality=93, subsampling=0)
    return p_cover, p_thumb
