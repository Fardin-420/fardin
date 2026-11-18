"""Thumbnails (1280x720): Fardin with a huge expression, one dramatic historical
element, max 3 bold words. Rendered with the same engine as the episode."""
import json
import math
import os
import cairo
from .scene import Scene
from . import graphics as G

W, H = 1280, 720


def bold_words(ctx, words, x, y, size, colors, align="left", rot=-0.04, maxw=None):
    if maxw:
        for wd in words:
            G.font(ctx, size, "black")
            size = min(size, size * maxw / max(1, ctx.text_extents(wd).x_advance))
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(rot)
    yy = 0
    for wd, col in zip(words, colors):
        G.font(ctx, size, "black")
        tw = ctx.text_extents(wd).x_advance
        xx = -tw if align == "right" else (-tw / 2 if align == "center" else 0)
        ctx.move_to(xx + 8, yy + 10)
        ctx.text_path(wd)
        ctx.set_source_rgba(0, 0, 0, 0.6); ctx.fill()
        ctx.move_to(xx, yy)
        ctx.text_path(wd)
        ctx.set_line_width(size * 0.14); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.set_source_rgba(0, 0, 0, 1); ctx.stroke_preserve()
        ctx.set_source_rgba(*col, 1); ctx.fill()
        yy += size * 1.02
    ctx.restore()


def make_all(ep, out_dir, num):
    specs = json.load(open(os.path.join(ep, "thumbs.json")))
    for i, sp in enumerate(specs, 1):
        scene = sp["scene"]
        scene.setdefault("dur", 10)
        sc = Scene(scene)
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
        ctx = cairo.Context(surf)
        sc.render(ctx, W, H, sp.get("t", 1.0))
        # punchy grade: contrast vignette + red rim on Fardin side
        g = cairo.RadialGradient(W * sp.get("focus", 0.3), H * 0.5, H * 0.2, W * 0.5, H * 0.5, W * 0.75)
        g.add_color_stop_rgba(0, 0, 0, 0, 0); g.add_color_stop_rgba(1, 0, 0, 0, 0.55)
        ctx.set_source(g); ctx.paint()
        t = sp["text"]
        bold_words(ctx, t["words"], W * t.get("x", 0.55), H * t.get("y", 0.25), t.get("size", 120),
                   [tuple(c) for c in t["colors"]], t.get("align", "left"), t.get("rot", -0.04), W * t.get("maxw", 0.5))
        path = os.path.join(out_dir, f"timeghost_{num}_thumb{i}.png")
        surf.write_to_png(path)
        print("[thumb]", path)
