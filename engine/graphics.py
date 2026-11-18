"""Documentary graphics: maps, timeline bars, fact cards, comparisons, chapter and
era title cards, time tunnel, screen FX. All screen-space and resolution-aware
(landscape 1920x1080 or vertical 1080x1920)."""
import math
import cairo
from .core import clamp, lerp, ease, hrand, noise1, setc, hexc, TAU, out_back, out_cubic, in_out_cubic, smoothstep

FONT = "Inter Display"
CYAN = (0.25, 0.92, 1.0)
RED = (1.0, 0.17, 0.17)
PANEL = (0.04, 0.06, 0.1)
CREAM = (0.98, 0.95, 0.88)


def U(W, H):
    return min(W, H) / 1080.0


def font(ctx, size, weight="bold"):
    fam = {"black": FONT + " Black", "xbold": FONT + " ExtraBold", "bold": FONT, "semi": FONT + " SemiBold",
           "med": FONT + " Medium", "reg": FONT}[weight]
    w = cairo.FONT_WEIGHT_BOLD if weight == "bold" else cairo.FONT_WEIGHT_NORMAL
    ctx.select_font_face(fam, cairo.FONT_SLANT_NORMAL, w)
    ctx.set_font_size(size)


def text(ctx, s, x, y, size, col=CREAM, weight="bold", align="left", alpha=1.0, spacing=0.0, shadow=True):
    font(ctx, size, weight)
    if spacing:
        widths = [ctx.text_extents(ch).x_advance + spacing * size for ch in s]
        tw = sum(widths) - spacing * size
    else:
        tw = ctx.text_extents(s).x_advance
    if align == "center":
        x -= tw / 2
    elif align == "right":
        x -= tw
    def put(dx, dy, c, a):
        ctx.set_source_rgba(c[0], c[1], c[2], a)
        if spacing:
            xx = x + dx
            for ch, w in zip(s, widths):
                ctx.move_to(xx, y + dy); ctx.show_text(ch); xx += w
        else:
            ctx.move_to(x + dx, y + dy); ctx.show_text(s)
    if shadow:
        put(size * 0.04, size * 0.06, (0, 0, 0), 0.45 * alpha)
    put(0, 0, col, alpha)
    return tw


def rrect(ctx, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()


def panel(ctx, x, y, w, h, alpha=0.82, accent=CYAN, r=18):
    rrect(ctx, x, y, w, h, r)
    ctx.set_source_rgba(*PANEL, alpha)
    ctx.fill_preserve()
    ctx.set_source_rgba(*accent, 0.55 * alpha)
    ctx.set_line_width(2)
    ctx.stroke()


def inout(lt, dur, tin=0.45, tout=0.35):
    a = out_back(clamp(lt / tin), 1.4)
    b = 1 - in_out_cubic(clamp((lt - (dur - tout)) / tout))
    return a, b


def wrap(ctx, s, maxw, size, weight="bold"):
    font(ctx, size, weight)
    words, lines, cur = s.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if ctx.text_extents(test).x_advance > maxw and cur:
            lines.append(cur); cur = w
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines


# ------------------------------------------------------------------ geography
AFRICA = [(-5.9, 35.8), (-2, 35.1), (3, 36.8), (10.3, 37.3), (11, 35.2), (10.2, 33.8), (15.2, 32.3), (18.5, 30.3),
          (20.1, 32.1), (23, 32.6), (25.2, 31.6), (29.9, 31.2), (32.3, 31.3), (32.6, 30), (33.9, 27), (35.6, 23.9),
          (37.2, 19.6), (39.5, 15.5), (43.3, 12.6), (45, 10.4), (49, 11.3), (51.2, 11.8), (51, 10.4), (49.8, 7.5),
          (48, 4.5), (45.3, 2), (42, -0.5), (40.2, -2.8), (39.3, -6.8), (40.2, -10.3), (40.6, -14.5), (39.1, -17),
          (35.5, -22), (35.5, -24), (32.6, -25.9), (32.4, -28.6), (30.9, -30), (28, -33), (25.6, -34), (22, -34.2),
          (20, -34.8), (18.4, -34.3), (18.4, -33.9), (17.9, -31.5), (16.5, -28.6), (15.2, -27), (14.5, -22.9),
          (11.8, -17.3), (12.3, -13.5), (13.2, -8.8), (12.3, -6), (11.8, -4.8), (9.3, -1), (9.5, 1), (9.8, 3.8),
          (8.5, 4.5), (6.1, 4.3), (3.4, 6.4), (1, 5.9), (-2, 4.8), (-4, 5.2), (-7.5, 4.4), (-11.5, 6.9), (-13.2, 8.5),
          (-15, 10.8), (-16.7, 12.5), (-17.5, 14.7), (-16.5, 19.4), (-17, 21), (-15.9, 23.7), (-13.2, 27.6),
          (-9.8, 29.8), (-9.6, 32.5), (-6.8, 34.1)]
MADAGASCAR = [(49.3, -12), (50.5, -15.5), (49.8, -17), (47.1, -24.9), (45.1, -25.5), (43.7, -23.5), (44.3, -20),
              (44.0, -17.2), (46.3, -15.9), (48, -13.5)]
EURASIA = [(-9, 43.5), (-9.5, 38.7), (-6, 36.2), (-2, 36.7), (3, 41.5), (3.2, 43.3), (7.5, 43.8), (8.8, 44.4),
           (12.5, 41.9), (16, 38), (18.5, 40.2), (13, 45.7), (19.5, 41.8), (22.9, 36.4), (23.9, 38), (26, 40.5),
           (29, 41), (36, 36.6), (35.5, 33), (34.3, 31.3), (32.6, 30), (34.9, 29.5), (39, 22), (43, 13), (45, 12.8),
           (52, 15.8), (57, 18.9), (59.8, 22.5), (56.4, 26.2), (51.5, 24.5), (50, 26.5), (48, 29.9), (50.5, 29.3),
           (56.5, 27.2), (61.6, 25.2), (66.5, 25.4), (72.8, 19), (77.5, 8), (80.3, 13), (86.9, 20), (90, 22),
           (94.5, 16.5), (98, 16), (100.5, 13.5), (100.3, 6.5), (102, 1.8), (104, 1.4), (104.5, 10.5), (109, 12),
           (106.7, 20.7), (108.3, 21.6), (113.5, 22.2), (119, 25.5), (121.9, 30.9), (119.5, 35), (122.5, 37.4),
           (117.7, 39), (121.5, 40.9), (126.6, 37.5), (129.4, 35.5), (129.6, 42.4), (135.4, 43.8), (140.5, 48.5),
           (141, 52.7), (143.5, 59.3), (155, 59.5), (163, 60), (170.5, 60), (178, 64.5), (180, 68.9), (160, 70),
           (140, 72.5), (113, 73.5), (104, 77.7), (87, 74), (80, 73.5), (69, 72.9), (60, 69.8), (43, 68.5), (33, 69.4),
           (25, 71), (14, 68), (10.5, 64), (5, 62), (5.5, 58.8), (8, 58), (8, 55), (8.6, 53.5), (4.5, 52.3),
           (1.6, 50.9), (-1.6, 49.6), (-4.7, 48.4), (-1.2, 46.2), (-1.8, 43.4)]
BRITAIN = [(-5.7, 50), (1.4, 51.2), (1.7, 52.7), (0, 53.5), (-1.6, 55.6), (-2, 57.7), (-5, 58.6), (-6.2, 56.5),
           (-4.8, 54.8), (-3, 53.4), (-4.5, 52.7), (-5.2, 51.7)]
SUMATRA = [(95.3, 5.6), (98.7, 3.7), (104.5, -2.3), (106, -5.9), (103.5, -4.9), (100.4, -1.1), (96.3, 2.4)]
JAVA = [(105.3, -6.8), (106.1, -6), (110.4, -6.9), (114.5, -7.7), (114.4, -8.7), (108.5, -7.8), (105.5, -7.0)]
BORNEO = [(109, 1.5), (110.5, -3), (116, -4), (117.6, 1), (119, 5.2), (116.8, 7), (115.4, 5), (110.5, 1.8)]
ARABIA_FIX = []


def draw_map(ctx, W, H, g, lt, T):
    u = U(W, H)
    dur = g.get("dur", 6)
    a, b = inout(lt, dur, 0.6, 0.45)
    al = clamp(a) * b
    vertical = H > W
    view = g.get("view", "africa")
    if view == "africa":
        lon0, lon1, lat0, lat1 = -22, 56, -38, 40
        shapes = [AFRICA, MADAGASCAR, EURASIA]
    else:
        lon0, lon1, lat0, lat1 = -20, 135, -38, 62
        shapes = [AFRICA, MADAGASCAR, EURASIA, BRITAIN, SUMATRA, JAVA, BORNEO]
    if vertical:
        mw = W * 0.86
    else:
        mw = W * (0.42 if view == "africa" else 0.62)
    mh = mw * (lat1 - lat0) / (lon1 - lon0) * 1.0
    if not vertical and mh > H * 0.78:
        mh = H * 0.78; mw = mh * (lon1 - lon0) / (lat1 - lat0)
    side = g.get("side", "right")
    mx = (W - mw) / 2 if vertical else (W - mw - 70 * u if side == "right" else 70 * u)
    if g.get("center"):
        mx = (W - mw) / 2
    my = H * 0.1 if vertical else (H - mh) / 2
    slide = (1 - clamp(a)) * 60 * u
    ctx.save()
    ctx.translate(0, slide)
    panel(ctx, mx - 20 * u, my - 20 * u, mw + 40 * u, mh + 40 * u, 0.85 * al)
    ctx.save()
    rrect(ctx, mx - 20 * u, my - 20 * u, mw + 40 * u, mh + 40 * u, 18); ctx.clip()
    ctx.set_source_rgba(0.08, 0.2, 0.32, 0.9 * al)
    ctx.rectangle(mx, my, mw, mh); ctx.fill()
    # graticule
    ctx.set_line_width(1)
    ctx.set_source_rgba(0.4, 0.7, 0.9, 0.12 * al)
    for lon in range(-20, 181, 20):
        px = mx + (lon - lon0) / (lon1 - lon0) * mw
        ctx.move_to(px, my); ctx.line_to(px, my + mh)
    for lat in range(-40, 81, 20):
        py = my + (lat1 - lat) / (lat1 - lat0) * mh
        ctx.move_to(mx, py); ctx.line_to(mx + mw, py)
    ctx.stroke()
    proj = lambda lon, lat: (mx + (lon - lon0) / (lon1 - lon0) * mw, my + (lat1 - lat) / (lat1 - lat0) * mh)
    draw_k = clamp(lt / 1.2)
    for si, shape in enumerate(shapes):
        n = len(shape)
        ctx.move_to(*proj(*shape[0]))
        for p in shape[1:]:
            ctx.line_to(*proj(*p))
        ctx.close_path()
        hl = (si == 0 and view == "africa")
        if hl:
            ctx.set_source_rgba(0.85, 0.68, 0.38, al * draw_k)
        else:
            ctx.set_source_rgba(0.55, 0.52, 0.42, 0.85 * al * draw_k)
        ctx.fill_preserve()
        ctx.set_source_rgba(1, 0.95, 0.8, 0.8 * al)
        ctx.set_line_width(2 * u)
        ctx.stroke()
    # green Sahara tint (optional)
    if g.get("green_sahara"):
        k = smoothstep(1.0, 2.5, lt)
        ctx.save()
        ctx.move_to(*proj(*AFRICA[0]))
        for p in AFRICA[1:]:
            ctx.line_to(*proj(*p))
        ctx.close_path(); ctx.clip()
        gx, gy = proj(10, 22)
        rx = mw * 0.32
        ctx.translate(gx, gy); ctx.scale(1, 0.42)
        grad = cairo.RadialGradient(0, 0, 0, 0, 0, rx)
        grad.add_color_stop_rgba(0, 0.33, 0.62, 0.25, 0.7 * k * al)
        grad.add_color_stop_rgba(0.7, 0.35, 0.6, 0.25, 0.45 * k * al)
        grad.add_color_stop_rgba(1, 0.35, 0.6, 0.25, 0)
        ctx.set_source(grad); ctx.arc(0, 0, rx, 0, TAU); ctx.fill()
        ctx.restore()
    # pins
    for i, pin in enumerate(g.get("pins", [])):
        pt = pin.get("t", 0.8 + i * 0.5)
        pk = clamp((lt - pt) / 0.4)
        if pk <= 0:
            continue
        x, y = proj(pin["lon"], pin["lat"])
        col = tuple(pin.get("color", RED))
        pulse = (lt * 1.2 + i * 0.3) % 1
        ctx.set_source_rgba(*col, (1 - pulse) * 0.6 * al)
        ctx.arc(x, y, (8 + 30 * pulse) * u, 0, TAU); ctx.fill()
        rr = 10 * u * out_back(pk, 3)
        ctx.set_source_rgba(1, 1, 1, al); ctx.arc(x, y, rr + 3 * u, 0, TAU); ctx.fill()
        ctx.set_source_rgba(*col, al); ctx.arc(x, y, rr, 0, TAU); ctx.fill()
        lab = pin.get("label", "")
        fs = pin.get("size", 30) * u
        ldx = pin.get("dx", 18) * u
        ldy = pin.get("dy", -14) * u
        al2 = al * pk
        font(ctx, fs, "xbold")
        tw = ctx.text_extents(lab).x_advance
        lx = x + ldx if ldx >= 0 else x + ldx - tw
        rrect(ctx, lx - 8 * u, y + ldy - fs * 0.95, tw + 16 * u, fs * 1.3, 8 * u)
        ctx.set_source_rgba(*PANEL, 0.75 * al2); ctx.fill()
        text(ctx, lab, lx, y + ldy, fs, CREAM, "xbold", alpha=al2, shadow=False)
        if pin.get("sub"):
            text(ctx, pin["sub"], lx, y + ldy + fs * 1.05, fs * 0.72, (0.8, 0.9, 1.0), "semi", alpha=al2)
    ctx.restore()
    if g.get("title"):
        text(ctx, g["title"], mx + 10 * u, my + 50 * u, 40 * u, CREAM, "black", alpha=al)
    ctx.restore()


# ------------------------------------------------------------------ timeline
def draw_timeline(ctx, W, H, g, lt, T):
    u = U(W, H)
    dur = g.get("dur", 6)
    a, b = inout(lt, dur, 0.5, 0.4)
    al = clamp(a) * b
    vertical = H > W
    x0 = W * (0.08 if not vertical else 0.07)
    x1 = W - x0
    y = H * (0.2 if not vertical else 0.14) if g.get("top", True) else H * 0.8
    span = g.get("span", 300000)
    ctx.save()
    ctx.translate(0, (1 - clamp(a)) * -40 * u)
    panel(ctx, x0 - 30 * u, y - 95 * u, x1 - x0 + 60 * u, 190 * u if not vertical else 230 * u, 0.82 * al)
    grow = out_cubic(clamp(lt / 1.2))
    ctx.set_line_width(10 * u)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_source_rgba(1, 1, 1, 0.18 * al)
    ctx.move_to(x0, y); ctx.line_to(x1, y); ctx.stroke()
    gr = cairo.LinearGradient(x0, 0, x1, 0)
    gr.add_color_stop_rgba(0, 0.95, 0.6, 0.25, al)
    gr.add_color_stop_rgba(1, *CYAN, al)
    ctx.set_source(gr)
    ctx.move_to(x0, y); ctx.line_to(lerp(x0, x1, grow), y); ctx.stroke()
    text(ctx, g.get("left", "300,000 YEARS AGO"), x0, y - 30 * u, 30 * u, (1, .75, .4), "black", alpha=al)
    text(ctx, g.get("right", "TODAY"), x1, y - 30 * u, 30 * u, CYAN, "black", align="right", alpha=al)
    # marks
    for i, m in enumerate(g.get("marks", [])):
        mt = m.get("t", 1.2 + i * 0.6)
        k = clamp((lt - mt) / 0.35)
        if k <= 0:
            continue
        frac = 1 - m["ago"] / span
        mx = lerp(x0, x1, frac)
        ctx.set_source_rgba(1, 1, 1, al * k)
        ctx.arc(mx, y, 9 * u * out_back(k, 3), 0, TAU); ctx.fill()
        row = m.get("row", i % 2)
        ly = y + (48 + row * 40) * u
        ctx.set_line_width(2 * u)
        ctx.move_to(mx, y + 10 * u); ctx.line_to(mx, ly - 26 * u); ctx.stroke()
        text(ctx, m["label"], mx, ly, 26 * u, CREAM, "xbold", align=m.get("align", "center"), alpha=al * k)
    # "you are here" marker for Fardin
    if g.get("marker", True):
        mk = clamp((lt - 0.9) / 0.4)
        frac = g.get("marker_frac", 0.0)
        mx = lerp(x0, x1, frac)
        bob = math.sin(lt * 4) * 4 * u
        ctx.set_source_rgba(*RED, al * mk)
        ctx.move_to(mx, y + 12 * u - bob); ctx.line_to(mx - 14 * u, y + 30 * u - bob); ctx.line_to(mx + 14 * u, y + 30 * u - bob)
        ctx.close_path(); ctx.fill()
        text(ctx, g.get("marker_label", "FARDIN"), mx, y + 52 * u, 24 * u, (1, .45, .45), "black", alpha=al * mk)
    if g.get("caption"):
        text(ctx, g["caption"], W / 2, y + 150 * u if not vertical else y + 190 * u, 34 * u, CREAM, "bold", align="center", alpha=al)
    ctx.restore()


# ------------------------------------------------------------------ fact card
def draw_fact(ctx, W, H, g, lt, T):
    u = U(W, H)
    dur = g.get("dur", 5)
    a, b = inout(lt, dur, 0.5, 0.35)
    al = clamp(a) * b
    vertical = H > W
    w = (W * 0.86) if vertical else 640 * u
    big = g.get("big", "")
    label = g.get("label", "")
    src = g.get("source", "")
    lines = wrap(ctx, label, w - 70 * u, 36 * u, "bold")
    bs = g.get("big_size", 108) * u
    h = 70 * u + bs + len(lines) * 46 * u + (40 * u if src else 0) + 20 * u
    side = g.get("side", "left")
    if vertical:
        x = (W - w) / 2
        y = H * g.get("vy", 0.1)
    else:
        x = 80 * u if side == "left" else W - w - 80 * u
        y = g.get("y", 120) * u
    sl = (1 - clamp(a)) * (-90 * u if side == "left" else 90 * u)
    ctx.save()
    ctx.translate(sl, 0)
    panel(ctx, x, y, w, h, 0.86 * al, tuple(g.get("accent", CYAN)))
    ctx.set_source_rgba(*tuple(g.get("accent", CYAN)), al)
    rrect(ctx, x, y, 12 * u, h, 6 * u); ctx.fill()
    tag = g.get("tag", "FACT")
    text(ctx, tag, x + 40 * u, y + 52 * u, 24 * u, tuple(g.get("accent", CYAN)), "black", alpha=al, spacing=0.12, shadow=False)
    # count-up for numeric big text
    shown = big
    if g.get("count"):
        target = g["count"]
        k = out_cubic(clamp((lt - 0.2) / 1.2))
        val = int(round(target * k))
        shown = g.get("prefix", "") + f"{val:,}" + g.get("suffix", "")
    pk = out_back(clamp((lt - 0.15) / 0.4), 2.5)
    ctx.save()
    ctx.translate(x + 40 * u, y + 60 * u + bs)
    ctx.scale(max(0.01, pk), max(0.01, pk))
    text(ctx, shown, 0, 0, bs, CREAM, "black", alpha=al)
    ctx.restore()
    yy = y + 60 * u + bs + 54 * u
    for ln in lines:
        text(ctx, ln, x + 40 * u, yy, 36 * u, (0.9, 0.92, 0.95), "bold", alpha=al)
        yy += 46 * u
    if src:
        text(ctx, src, x + 40 * u, yy + 4 * u, 24 * u, (0.6, 0.75, 0.85), "med", alpha=al)
    ctx.restore()


def draw_compare(ctx, W, H, g, lt, T):
    u = U(W, H)
    dur = g.get("dur", 6)
    a, b = inout(lt, dur, 0.5, 0.4)
    al = clamp(a) * b
    vertical = H > W
    rows = g.get("rows", [])
    w = W * 0.86 if vertical else 1100 * u
    rh = 64 * u
    h = 150 * u + rh * len(rows)
    x = (W - w) / 2
    y = H * 0.12 if vertical else g.get("y", 50) * u
    ctx.save()
    ctx.translate(0, (1 - clamp(a)) * 50 * u)
    panel(ctx, x, y, w, h, 0.9 * al)
    cx = x + w / 2
    text(ctx, g.get("left_title", "THEN"), x + w * 0.25, y + 80 * u, 50 * u, (1, .72, .38), "black", align="center", alpha=al)
    text(ctx, g.get("right_title", "NOW"), x + w * 0.75, y + 80 * u, 50 * u, CYAN, "black", align="center", alpha=al)
    ctx.set_source_rgba(1, 1, 1, 0.25 * al)
    ctx.rectangle(cx - 1, y + 30 * u, 2, h - 60 * u); ctx.fill()
    for i, (l, r) in enumerate(rows):
        k = clamp((lt - 0.6 - i * 0.45) / 0.35)
        if k <= 0:
            continue
        yy = y + 150 * u + i * rh
        fs = 34 * u if not vertical else 30 * u
        text(ctx, l, x + w * 0.25, yy, fs, CREAM, "bold", align="center", alpha=al * k)
        text(ctx, r, x + w * 0.75, yy, fs, CREAM, "bold", align="center", alpha=al * k)
    ctx.restore()


def draw_chapter(ctx, W, H, g, lt, T):
    u = U(W, H)
    dur = g.get("dur", 3.5)
    a, b = inout(lt, dur, 0.6, 0.5)
    al = clamp(a) * b
    vertical = H > W
    x = 90 * u
    y = H * (0.78 if not vertical else 0.7)
    lw = out_cubic(clamp(lt / 0.7)) * 520 * u
    ctx.save()
    ctx.set_source_rgba(*CYAN, al)
    ctx.rectangle(x, y - 64 * u, lw, 5 * u); ctx.fill()
    text(ctx, g.get("kicker", "CHAPTER"), x, y - 82 * u, 28 * u, CYAN, "black", alpha=al, spacing=0.18)
    ctx.rectangle(x - 10, y - 60 * u, W, 120 * u)
    ctx.save(); ctx.clip()
    off = (1 - out_cubic(clamp((lt - 0.15) / 0.5))) * 90 * u
    text(ctx, g.get("title", ""), x, y + 18 * u + off, 76 * u, CREAM, "black", alpha=al)
    ctx.restore()
    if g.get("time"):
        text(ctx, g["time"], x, y + 72 * u, 30 * u, (1, .8, .55), "xbold", alpha=al * clamp((lt - 0.4) / 0.4))
    ctx.restore()


def draw_era_title(ctx, W, H, g, lt, T):
    u = U(W, H)
    dur = g.get("dur", 4)
    a, b = inout(lt, dur, 0.3, 0.6)
    al = clamp(a) * b
    big = g.get("title", "300,000 YEARS AGO")
    sub = g.get("sub", "")
    k = out_cubic(clamp(lt / 1.0))
    sp = lerp(0.6, 0.06, k)
    ctx.save()
    gl = cairo.RadialGradient(W / 2, H / 2, 0, W / 2, H / 2, W * 0.5)
    gl.add_color_stop_rgba(0, 0, 0, 0, 0.55 * al); gl.add_color_stop_rgba(1, 0, 0, 0, 0)
    ctx.set_source(gl); ctx.paint()
    fs = (118 if W > H else 92) * u
    if W < H:
        parts = big.split(" ", 1)
        text(ctx, parts[0], W / 2, H * 0.45, fs * 1.3, CREAM, "black", align="center", alpha=al, spacing=sp * 0.5)
        if len(parts) > 1:
            text(ctx, parts[1], W / 2, H * 0.45 + fs * 1.15, fs * 0.8, CREAM, "black", align="center", alpha=al, spacing=sp * 0.5)
    else:
        text(ctx, big, W / 2, H * 0.5, fs, CREAM, "black", align="center", alpha=al, spacing=sp)
    ctx.set_source_rgba(*CYAN, al)
    lw = k * 600 * u
    ctx.rectangle(W / 2 - lw / 2, H * 0.5 + 40 * u if W > H else H * 0.6, lw, 4 * u); ctx.fill()
    if sub:
        text(ctx, sub, W / 2, (H * 0.5 + 100 * u) if W > H else H * 0.6 + 70 * u, 40 * u, (0.85, 0.93, 1.0), "semi", align="center",
             alpha=al * clamp((lt - 0.5) / 0.5), spacing=0.08)
    ctx.restore()


def draw_list(ctx, W, H, g, lt, T):
    u = U(W, H)
    dur = g.get("dur", 6)
    a, b = inout(lt, dur, 0.4, 0.4)
    al = clamp(a) * b
    items = g.get("items", [])
    vertical = H > W
    w = W * 0.86 if vertical else 820 * u
    x = (W - w) / 2 if vertical else W - w - 90 * u
    y = H * 0.12 if vertical else 150 * u
    rh = 112 * u
    panel(ctx, x, y, w, 100 * u + rh * len(items), 0.85 * al)
    text(ctx, g.get("title", "COMING UP"), x + 40 * u, y + 62 * u, 32 * u, CYAN, "black", alpha=al, spacing=0.15)
    for i, it in enumerate(items):
        tt = g.get("times", [0.5 + i * 0.8 for _ in items])[i] if g.get("times") else 0.5 + i * 0.8
        k = clamp((lt - tt) / 0.35)
        if k <= 0:
            continue
        yy = y + 100 * u + i * rh
        ctx.save(); ctx.translate((1 - out_back(k)) * 60 * u, 0)
        ctx.set_source_rgba(*RED, al * k)
        ctx.arc(x + 70 * u, yy + 40 * u, 32 * u, 0, TAU); ctx.fill()
        text(ctx, str(i + 1), x + 70 * u, yy + 54 * u, 40 * u, (1, 1, 1), "black", align="center", alpha=al * k, shadow=False)
        lines = wrap(ctx, it, w - 170 * u, 38 * u)
        for j, ln in enumerate(lines[:2]):
            text(ctx, ln, x + 125 * u, yy + 52 * u + j * 44 * u - (20 * u if len(lines) > 1 else 0), 38 * u, CREAM, "bold", alpha=al * k)
        ctx.restore()


def draw_tag(ctx, W, H, g, lt, T):
    u = U(W, H)
    dur = g.get("dur", 3)
    a, b = inout(lt, dur, 0.3, 0.3)
    al = clamp(a) * b
    s = g.get("text", "SCIENTISTS DEBATE THIS")
    fs = 28 * u
    font(ctx, fs, "black")
    tw = ctx.text_extents(s).x_advance
    x = W - tw - 120 * u if W > H else (W - tw) / 2 - 20 * u
    y = g.get("y", 60) * u if W > H else H * 0.06
    rrect(ctx, x, y, tw + 40 * u, 52 * u, 26 * u)
    ctx.set_source_rgba(1, 0.75, 0.2, 0.92 * al); ctx.fill()
    text(ctx, s, x + 20 * u, y + 36 * u, fs, (0.1, 0.07, 0.02), "black", alpha=al, shadow=False)


def draw_callout(ctx, W, H, g, lt, T):
    """Big kinetic word(s) slammed onto screen."""
    u = U(W, H)
    dur = g.get("dur", 1.6)
    k = out_back(clamp(lt / 0.22), 3)
    b = 1 - clamp((lt - dur + 0.3) / 0.3)
    s = g.get("text", "")
    fs = g.get("size", 130) * u
    ang = g.get("rot", -4) * math.pi / 180
    ctx.save()
    x = W * g.get("x", 0.5); y = H * g.get("y", 0.3)
    ctx.translate(x, y); ctx.rotate(ang); ctx.scale(max(0.01, k), max(0.01, k))
    font(ctx, fs, "black")
    tw = ctx.text_extents(s).x_advance
    col = tuple(g.get("color", (1, 0.85, 0.2)))
    ctx.move_to(-tw / 2, fs * 0.35)
    ctx.text_path(s)
    ctx.set_source_rgba(0, 0, 0, 0.85 * b); ctx.set_line_width(fs * 0.12); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke_preserve()
    ctx.set_source_rgba(*col, b); ctx.fill()
    ctx.restore()


def draw_clock(ctx, W, H, g, lt, T):
    """Fardin's watch HUD: '24 HOURS IN THE PAST' and time of day."""
    u = U(W, H)
    t0, t1 = g.get("from", 360), g.get("to", 400)  # minutes since midnight
    dur = g.get("dur", 10)
    m = lerp(t0, t1, clamp(lt / dur))
    hh, mm = int(m // 60) % 24, int(m % 60)
    ampm = "AM" if hh < 12 else "PM"
    h12 = hh % 12 or 12
    a = clamp(lt / 0.5) * (1 - clamp((lt - dur + 0.4) / 0.4))
    x, y = 46 * u, 46 * u
    rrect(ctx, x, y, 270 * u, 78 * u, 39 * u)
    ctx.set_source_rgba(*PANEL, 0.7 * a); ctx.fill()
    ctx.set_source_rgba(*CYAN, a * (0.7 + 0.3 * math.sin(T * 3)))
    ctx.arc(x + 40 * u, y + 39 * u, 13 * u, 0, TAU); ctx.fill()
    text(ctx, f"{h12}:{mm:02d} {ampm}", x + 68 * u, y + 52 * u, 38 * u, CREAM, "black", alpha=a, shadow=False)
    hour_n = g.get("hour")
    if hour_n is not None:
        text(ctx, f"HOUR {hour_n}/24", x + 8 * u, y + 112 * u, 22 * u, CYAN, "black", alpha=a * 0.9, spacing=0.12)


def draw_subscribe(ctx, W, H, g, lt, T):
    u = U(W, H)
    dur = g.get("dur", 5)
    a, b = inout(lt, dur, 0.5, 0.4)
    al = clamp(a) * b
    w, h = 560 * u, 110 * u
    x, y = (W - w) / 2, H * (0.78 if W > H else 0.72)
    pk = 1 + 0.05 * math.sin(lt * 6)
    ctx.save(); ctx.translate(x + w / 2, y + h / 2); ctx.scale(pk * clamp(a, 0.01, 2), pk * clamp(a, 0.01, 2)); ctx.translate(-(x + w / 2), -(y + h / 2))
    rrect(ctx, x, y, w, h, h / 2)
    ctx.set_source_rgba(0.9, 0.08, 0.1, al); ctx.fill()
    ctx.set_source_rgba(1, 1, 1, al)
    tx, ty = x + 70 * u, y + h / 2
    ctx.move_to(tx - 18 * u, ty - 22 * u); ctx.line_to(tx + 22 * u, ty); ctx.line_to(tx - 18 * u, ty + 22 * u); ctx.close_path(); ctx.fill()
    text(ctx, g.get("text", "SUBSCRIBE"), x + w / 2 + 30 * u, y + h / 2 + 20 * u, 56 * u, (1, 1, 1), "black", align="center", alpha=al, shadow=False)
    ctx.restore()
    if g.get("sub"):
        text(ctx, g["sub"], W / 2, y + h + 64 * u, 40 * u, CREAM, "xbold", align="center", alpha=al)


def draw_lower(ctx, W, H, g, lt, T):
    u = U(W, H)
    dur = g.get("dur", 4)
    a, b = inout(lt, dur, 0.4, 0.4)
    al = clamp(a) * b
    s = g.get("text", "")
    sub = g.get("sub", "")
    font(ctx, 44 * u, "black")
    tw = max(ctx.text_extents(s).x_advance, 300 * u)
    font(ctx, 28 * u, "semi")
    tw = max(tw, ctx.text_extents(sub).x_advance)
    x, y = 80 * u, H * 0.82 if W > H else H * 0.62
    ctx.save(); ctx.translate((1 - clamp(a)) * -60 * u, 0)
    panel(ctx, x, y, tw + 80 * u, (110 if sub else 76) * u, 0.85 * al)
    text(ctx, s, x + 40 * u, y + 54 * u, 44 * u, CREAM, "black", alpha=al)
    if sub:
        text(ctx, sub, x + 40 * u, y + 92 * u, 28 * u, CYAN, "semi", alpha=al)
    ctx.restore()


def _cranium(ctx, cx, cy, s, elong):
    # profile skull: braincase + face. elong>0 -> longer, lower braincase
    L, Hh = s * (1.0 + 0.28 * elong), s * (0.86 - 0.16 * elong)
    ctx.save(); ctx.translate(cx, cy)
    ctx.move_to(-L * 0.55, 0)
    ctx.curve_to(-L * 0.62, -Hh * 0.9, L * 0.05, -Hh * 1.05, L * 0.42, -Hh * 0.45)
    ctx.curve_to(L * 0.5, -Hh * 0.25, L * 0.48, -Hh * 0.05, L * 0.5, Hh * 0.1)
    ctx.line_to(L * 0.58, Hh * 0.35); ctx.line_to(L * 0.5, Hh * 0.42); ctx.line_to(L * 0.52, Hh * 0.6)
    ctx.curve_to(L * 0.4, Hh * 0.75, L * 0.2, Hh * 0.72, L * 0.12, Hh * 0.55)
    ctx.curve_to(-L * 0.05, Hh * 0.35, -L * 0.3, Hh * 0.3, -L * 0.55, 0)
    ctx.close_path()
    ctx.restore()


def draw_skulls(ctx, W, H, g, lt, T):
    u = U(W, H)
    dur = g.get("dur", 6)
    a, b = inout(lt, dur, 0.5, 0.4)
    al = clamp(a) * b
    vertical = H > W
    w = W * 0.9 if vertical else 1000 * u
    h = 430 * u
    x = (W - w) / 2
    y = H * 0.1 if vertical else 40 * u
    ctx.save(); ctx.translate(0, (1 - clamp(a)) * -40 * u)
    panel(ctx, x, y, w, h, 0.88 * al)
    labels = [(g.get("left", "JEBEL IRHOUD"), g.get("left_sub", "~300,000 years ago"), 1.0, (1, .72, .38)),
              (g.get("right", "MODERN HUMAN"), g.get("right_sub", "today"), -0.15, CYAN)]
    for i, (lab, sub, el, col) in enumerate(labels):
        k = clamp((lt - 0.3 - i * 0.7) / 0.5)
        cx = x + w * (0.27 + 0.46 * i)
        cy = y + h * 0.48
        _cranium(ctx, cx, cy, 190 * u, el * k + (1 - k) * 0.4)
        ctx.set_source_rgba(0.95, 0.92, 0.84, al * k); ctx.fill_preserve()
        ctx.set_source_rgba(*col, al * k); ctx.set_line_width(5 * u); ctx.stroke()
        ctx.set_source_rgba(0.1, 0.1, 0.12, al * k)
        ctx.arc(cx + 190 * u * 0.33, cy + 190 * u * 0.12, 20 * u, 0, TAU); ctx.fill()
        text(ctx, lab, cx, y + h - 70 * u, 36 * u, col, "black", align="center", alpha=al * k)
        text(ctx, sub, cx, y + h - 30 * u, 26 * u, CREAM, "semi", align="center", alpha=al * k)
    if g.get("note"):
        nk = clamp((lt - 1.8) / 0.5)
        text(ctx, g["note"], x + w / 2, y + 60 * u, 30 * u, CREAM, "bold", align="center", alpha=al * nk)
    ctx.restore()


GRAPHICS = {"skulls": draw_skulls, "map": draw_map, "timeline": draw_timeline, "fact": draw_fact, "compare": draw_compare,
            "chapter": draw_chapter, "era_title": draw_era_title, "list": draw_list, "tag": draw_tag,
            "callout": draw_callout, "clock": draw_clock, "subscribe": draw_subscribe, "lower": draw_lower}


def draw_graphic(ctx, W, H, g, lt, T):
    fn = GRAPHICS.get(g["type"])
    if fn:
        ctx.save()
        fn(ctx, W, H, g, lt, T)
        ctx.restore()


# ------------------------------------------------------------------ special sets / fx
def time_tunnel(ctx, W, H, t, k=1.0):
    ctx.set_source_rgb(0.01, 0.02, 0.06)
    ctx.paint()
    cx, cy = W / 2, H / 2
    u = U(W, H)
    for i in range(26):
        ph = (t * 0.55 * (0.6 + k) + i / 26) % 1
        r = (ph ** 2.2) * W * 0.9
        a = math.sin(ph * math.pi) * 0.6
        ctx.save(); ctx.translate(cx, cy); ctx.rotate(t * 0.6 + i * 0.4); ctx.scale(1, 0.62)
        ctx.set_line_width((2 + 10 * ph) * u)
        col = CYAN if i % 3 else (1, 1, 1)
        ctx.set_source_rgba(*col, a)
        ctx.arc(0, 0, r + 4, 0, TAU * 0.8); ctx.stroke()
        ctx.restore()
    for i in range(120):
        ph = (t * (0.4 + 0.5 * hrand("tn", i)) * (0.6 + k) + hrand("tp", i)) % 1
        ang = hrand("ta", i) * TAU
        r0 = (ph ** 2) * W * 0.8
        r1 = r0 + (20 + 120 * ph) * u
        ctx.set_source_rgba(0.8, 0.95, 1, ph * 0.8)
        ctx.set_line_width((1 + 3 * ph) * u)
        ctx.move_to(cx + math.cos(ang) * r0, cy + math.sin(ang) * r0 * 0.7)
        ctx.line_to(cx + math.cos(ang) * r1, cy + math.sin(ang) * r1 * 0.7)
        ctx.stroke()
    g = cairo.RadialGradient(cx, cy, 0, cx, cy, W * 0.25)
    g.add_color_stop_rgba(0, 0.9, 1, 1, 0.8); g.add_color_stop_rgba(1, 0.3, 0.9, 1, 0)
    ctx.set_source(g); ctx.arc(cx, cy, W * 0.25, 0, TAU); ctx.fill()


def cave_frame(ctx, W, H, cam):
    """Dark rock arch framing an interior shot."""
    ox = -cam[0] * 0.05
    ctx.set_source_rgba(0.05, 0.035, 0.025, 1)
    ctx.move_to(0, 0); ctx.line_to(W, 0); ctx.line_to(W, H)
    pts = []
    n = 30
    for i in range(n + 1):
        a = math.pi * i / n
        r = 1 + 0.05 * noise1(i * 0.7, 3)
        x = W / 2 + ox + math.cos(a) * W * 0.62 * r
        y = H * 1.05 - math.sin(a) * H * 1.02 * r
        pts.append((x, y))
    for p in pts:
        ctx.line_to(*p)
    ctx.line_to(0, H); ctx.close_path()
    ctx.fill()


def flake_pop(ctx, W, H, fx, lt):
    u = U(W, H)
    d = fx.get("dur", 1.6)
    k = clamp(lt / d)
    x0, y0 = fx.get("x", 0.5) * W, fx.get("y", 0.6) * H
    x = x0 + k * 160 * u
    y = y0 - math.sin(min(1, k * 1.3) * math.pi * 0.5) * 300 * u + max(0, k - 0.7) * 200 * u
    sc = (0.4 + 1.6 * out_back(min(1, k * 2.2), 1.6)) * u
    a = 1 - clamp((k - 0.8) / 0.2)
    ctx.save(); ctx.translate(x, y); ctx.rotate(k * 5); ctx.scale(sc, sc)
    for rr, al in ((140, 0.15), (90, 0.25)):
        g = cairo.RadialGradient(0, 0, 0, 0, 0, rr)
        g.add_color_stop_rgba(0, 1, 1, 0.85, al * a); g.add_color_stop_rgba(1, 1, 1, 0.85, 0)
        ctx.set_source(g); ctx.arc(0, 0, rr, 0, TAU); ctx.fill()
    ctx.move_to(-70, 10); ctx.line_to(-20, -38); ctx.line_to(60, -22); ctx.line_to(78, 6); ctx.line_to(10, 34); ctx.close_path()
    ctx.set_source_rgba(0.72, 0.68, 0.6, a); ctx.fill_preserve()
    ctx.set_line_width(4); ctx.set_source_rgba(0.25, 0.22, 0.2, a); ctx.stroke()
    ctx.set_source_rgba(1, 1, 1, 0.8 * a); ctx.set_line_width(3)
    ctx.move_to(-62, 8); ctx.line_to(-18, -32); ctx.line_to(56, -18); ctx.stroke()
    ctx.restore()
    for i in range(14):
        ang = hrand("fp", i) * TAU
        r = (40 + 260 * k) * u * (0.6 + 0.6 * hrand("fpr", i))
        ctx.set_source_rgba(1, 0.95, 0.7, 0.9 * (1 - k))
        ctx.arc(x0 + math.cos(ang) * r, y0 + math.sin(ang) * r, 5 * u, 0, TAU); ctx.fill()


def spear_flight(ctx, fx, t):
    if fx.get("style") == "torch":
        u = clamp((t - fx["t"]) / fx.get("dur", 0.7))
        x0, y0 = fx["from"]; x1, y1 = fx["to"]
        x = lerp(x0, x1, u); y = lerp(y0, y1, u) - math.sin(u * math.pi) * fx.get("arc", 160)
        ctx.save(); ctx.translate(x, y); ctx.rotate(u * 9)
        ctx.set_line_width(10); ctx.set_source_rgba(0.35, 0.22, 0.1, 1)
        ctx.move_to(-50, 0); ctx.line_to(50, 0); ctx.stroke()
        ctx.restore()
        from .props import flame, fire_light
        flame(ctx, x + 40, y, 70, t, 5)
        fire_light(ctx, x, y + 60, 0.5, t, 0.8)
        return
    u = clamp((t - fx["t"]) / fx.get("dur", 0.7))
    x0, y0 = fx["from"]; x1, y1 = fx["to"]
    x = lerp(x0, x1, u)
    arc = fx.get("arc", 120)
    y = lerp(y0, y1, u) - math.sin(u * math.pi) * arc
    dy = (y1 - y0) / max(1, (x1 - x0)) - math.cos(u * math.pi) * arc * math.pi / max(1, (x1 - x0))
    ang = math.atan2(dy * (x1 - x0), (x1 - x0))
    ctx.save(); ctx.translate(x, y); ctx.rotate(ang)
    ctx.set_line_width(6); ctx.set_source_rgba(0.42, 0.28, 0.14, 1)
    ctx.move_to(-140, 0); ctx.line_to(140, 0); ctx.stroke()
    ctx.set_source_rgba(0.55, 0.55, 0.52, 1)
    ctx.move_to(170, 0); ctx.line_to(140, -9); ctx.line_to(140, 9); ctx.close_path(); ctx.fill()
    ctx.set_source_rgba(1, 1, 1, 0.3)
    for i in range(3):
        ctx.rectangle(-300 - i * 40, -2 + i * 4 - 4, 120, 2); ctx.fill()
    ctx.restore()


def draw_fx(ctx, W, H, fx, t, scene):
    typ = fx["type"]
    lt = t - fx.get("t", 0)
    d = fx.get("dur", 0.5)
    if typ == "flake_pop" and 0 <= lt <= d:
        flake_pop(ctx, W, H, fx, lt)
    if typ == "flash" and 0 <= lt <= d:
        a = (1 - lt / d) ** 1.5 * fx.get("amt", 1.0)
        ctx.set_source_rgba(1, 1, 1, a); ctx.paint()
    elif typ == "flash_in" and 0 <= lt <= d:  # ramps up to white
        ctx.set_source_rgba(1, 1, 1, (lt / d) ** 2); ctx.paint()
    elif typ == "fade_in" and 0 <= lt <= d:
        ctx.set_source_rgba(0, 0, 0, 1 - in_out_cubic(lt / d)); ctx.paint()
    elif typ == "fade_out" and 0 <= lt <= d:
        ctx.set_source_rgba(0, 0, 0, in_out_cubic(lt / d)); ctx.paint()
    elif typ == "black" and 0 <= lt <= d:
        ctx.set_source_rgba(0, 0, 0, 1); ctx.paint()
    elif typ == "watch_bloom" and 0 <= lt <= d:
        k = clamp(lt / d)
        x, y = scene.fardin_screen(t, W, H) if fx.get("follow", True) else (W / 2, H / 2)
        R = W * (0.1 + 0.8 * k * k)
        g = cairo.RadialGradient(x, y, 0, x, y, R)
        g.add_color_stop_rgba(0, 0.8, 1, 1, 0.9 * k)
        g.add_color_stop_rgba(0.4, *CYAN, 0.45 * k)
        g.add_color_stop_rgba(1, *CYAN, 0)
        ctx.set_source(g); ctx.paint()
    elif typ == "danger" and 0 <= lt <= d:
        beat = (math.sin(lt * 7.5) * 0.5 + 0.5) ** 3
        g = cairo.RadialGradient(W / 2, H / 2, H * 0.3, W / 2, H / 2, H * 0.95)
        g.add_color_stop_rgba(0, 0.6, 0, 0, 0)
        g.add_color_stop_rgba(1, 0.55, 0, 0, (0.25 + 0.35 * beat) * fx.get("amt", 1.0) * min(1, lt / 0.5, (d - lt) / 0.5))
        ctx.set_source(g); ctx.paint()
    elif typ == "letterbox" and 0 <= lt <= d:
        k = min(clamp(lt / 0.5), clamp((d - lt) / 0.5))
        bh = H * 0.1 * in_out_cubic(k)
        ctx.set_source_rgba(0, 0, 0, 1)
        ctx.rectangle(0, 0, W, bh); ctx.rectangle(0, H - bh, W, bh); ctx.fill()
    elif typ == "speedlines" and 0 <= lt <= d:
        k = min(1, lt / 0.2, (d - lt) / 0.3)
        cx, cy = W / 2, H / 2
        for i in range(60):
            a = hrand("sl", i) * TAU
            r0 = W * (0.35 + 0.15 * hrand("sr", i)) + ((lt * 900 + hrand("so", i) * 300) % 300)
            ctx.set_source_rgba(1, 1, 1, 0.35 * k)
            ctx.set_line_width(3)
            ctx.move_to(cx + math.cos(a) * r0, cy + math.sin(a) * r0)
            ctx.line_to(cx + math.cos(a) * (r0 + 220), cy + math.sin(a) * (r0 + 220))
            ctx.stroke()
    elif typ == "counter" and 0 <= lt <= d:
        k = clamp(lt / d)
        v0, v1 = fx.get("from", 2026), fx.get("to", -298000)
        val = lerp(v0, v1, k ** 3)
        u = U(W, H)
        lab = f"{int(abs(val)):,} {'AD' if val >= 0 else 'BC'}" if abs(val) < 10000 else f"{int(abs(val) // 1000 * 1000):,} BC"
        if val < -5000:
            lab = f"{int((abs(val) + 2026) // 1000 * 1000):,} YEARS AGO"
        text(ctx, lab, W / 2, H * 0.86, 64 * u, (0.85, 1, 1), "black", align="center", alpha=min(1, lt / 0.3, (d - lt) / 0.3) if d - lt < 0.3 else min(1, lt / 0.3), spacing=0.05)
