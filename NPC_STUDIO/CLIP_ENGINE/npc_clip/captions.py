"""Word-synced animated captions + vector motion graphics, emitted as one ASS script per clip (libass).

Layers: 0 graphics backplates · 1 captions · 2 overlays/titles · 3 progress bar / watermark.
"""
from __future__ import annotations

import json
import re

from .common import FPS, H, PRESETS, W

STYLES = json.loads((PRESETS / "caption_styles.json").read_text())
STYLES.pop("_doc", None)


def ass_color(hex_rgb: str, alpha: float = 0.0) -> str:
    h = hex_rgb.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{int(alpha * 255):02X}{b}{g}{r}".upper()


def _c(hex_rgb: str) -> str:            # inline \c form
    h = hex_rgb.lstrip("#")
    return f"&H{h[4:6]}{h[2:4]}{h[0:2]}&".upper()


def lerp_hex(a: str, b: str, t: float) -> str:
    a, b = a.lstrip("#"), b.lstrip("#")
    return "#" + "".join(f"{round(int(a[i:i+2], 16) * (1 - t) + int(b[i:i+2], 16) * t):02X}" for i in (0, 2, 4))


def ts(t: float) -> str:
    t = max(0.0, t)
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def esc(s: str) -> str:
    return s.replace("\\", "").replace("{", "(").replace("}", ")")


def display_word(w: str, st: dict) -> str:
    if st["upper"]:
        w = re.sub(r"[.,;:]+$", "", w).upper()
    return esc(w)


def group_words(words: list[dict], st: dict) -> list[list[dict]]:
    groups, cur, chars = [], [], 0
    for k, w in enumerate(words):
        wl = len(w["w"]) + 1
        if cur and (len(cur) >= st["max_words"] or chars + wl > st["max_chars"] * (2 if st["max_words"] >= 5 else 1)
                    or w["s"] - cur[-1]["e"] > 0.55):
            groups.append(cur)
            cur, chars = [], 0
        cur.append(w)
        chars += wl
        if re.search(r"[.?!]['\"”)]*$", w["w"]) or (re.search(r"[,;:]$", w["w"]) and len(cur) >= 2):
            groups.append(cur)
            cur, chars = [], 0
    if cur:
        groups.append(cur)
    # avoid orphan single words when the neighbour has room
    out = []
    for g in groups:
        if out and len(g) == 1 and len(out[-1]) < st["max_words"] and g[0]["s"] - out[-1][-1]["e"] < 0.3 \
                and not re.search(r"[.?!]$", out[-1][-1]["w"]):
            out[-1] = out[-1] + g
        else:
            out.append(g)
    return out


def _line_break(texts: list[str], st: dict) -> list[str]:
    """Insert one \\N for two-line presets when the group is long."""
    total = sum(len(t) + 1 for t in texts)
    if st["max_words"] < 5 or total <= st["max_chars"]:
        return texts
    acc, best, best_d = 0, 0, 1e9
    for i, t in enumerate(texts[:-1]):
        acc += len(t) + 1
        if abs(acc - total / 2) < best_d:
            best, best_d = i, abs(acc - total / 2)
    texts = list(texts)
    texts[best] = texts[best] + "\\N"
    return texts


class ASS:
    def __init__(self, style_key: str, caption_y: int):
        self.st = STYLES[style_key]
        self.key = style_key
        self.y = caption_y
        self.events: list[str] = []

    def header(self) -> str:
        st = self.st
        bold = 0  # weight comes from the font face
        border_style = 3 if st.get("box") else 1
        back = ass_color(st.get("box_color", st["shadow_color"]), st.get("box_alpha", 0.35) if st.get("box") else 0.25)
        cap = (f"Style: Cap,{st['font']},{st['size']},{ass_color(st['primary'])},{ass_color(st['active'])},"
               f"{ass_color(st['outline'])},{back},{bold},0,0,0,100,100,{st['spacing']},0,{border_style},"
               f"{st['outline_w']},{st['shadow']},5,90,90,0,1")
        gfx = ("Style: Gfx,Inter Display Black,72,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1")
        ui = ("Style: UI,Inter Display SemiBold,34,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,0,0,0,0,100,100,1,0,1,0,2,7,0,0,0,1")
        return ("[Script Info]\nScriptType: v4.00+\nPlayResX: %d\nPlayResY: %d\nWrapStyle: 2\n"
                "ScaledBorderAndShadow: yes\nYCbCr Matrix: TV.709\n\n[V4+ Styles]\n"
                "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, "
                "Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
                "MarginL, MarginR, MarginV, Encoding\n%s\n%s\n%s\n\n[Events]\n"
                "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n") % (W, H, cap, gfx, ui)

    def ev(self, layer: int, s: float, e: float, style: str, text: str) -> None:
        if e - s >= 0.02:
            self.events.append(f"Dialogue: {layer},{ts(s)},{ts(e)},{style},,0,0,0,,{text}")

    # ───────────── captions ─────────────
    def captions(self, words: list[dict], clip_end: float, y_at=None) -> list[dict]:
        st = self.st
        base_y = self.y
        groups = group_words(words, st)
        placed = []
        for gi, g in enumerate(groups):
            g_s = g[0]["s"]
            nxt = groups[gi + 1][0]["s"] if gi + 1 < len(groups) else clip_end
            g_e = min(nxt, g[-1]["e"] + 0.45) if nxt - g[-1]["e"] < 0.8 else g[-1]["e"] + 0.3
            g_e = min(max(g_e, g_s + 0.35), clip_end)
            self.y = y_at(g_s) if y_at else base_y
            texts = _line_break([display_word(w["w"], st) for w in g], st)
            rot = (-2.5 if gi % 2 else 2.5) if st["animation"] == "kinetic" else 0
            placed.append({"s": g_s, "e": g_e, "text": " ".join(t.replace("\\N", "") for t in texts)})
            for k, w in enumerate(g):
                ks = g_s if k == 0 else w["s"]
                ke = g[k + 1]["s"] if k + 1 < len(g) else g_e
                if ke - ks < 0.02:
                    continue
                self.ev(1, ks, ke, "Cap", self._line(g, texts, k, first=(k == 0), rot=rot))
        self.y = base_y
        return placed

    def _line(self, g, texts, active: int, first: bool, rot: float) -> str:
        st = self.st
        y = self.y
        x = W // 2
        anim = st["animation"]
        pre = ""
        if anim == "slide":
            pre = f"\\move({x},{y + 34},{x},{y},0,140)\\fad(90,0)" if first else f"\\pos({x},{y})"
        else:
            pre = f"\\pos({x},{y})"
            if first and anim in ("pop", "kinetic"):
                pre += "\\fscx72\\fscy72\\t(0,110,\\fscx100\\fscy100)"
            elif first and anim == "bounce":
                pre += "\\fscx80\\fscy80\\t(0,80,\\fscx106\\fscy106)\\t(80,150,\\fscx100\\fscy100)"
            elif first and anim in ("fade", "reveal"):
                pre += "\\fad(120,0)"
        if rot:
            pre += f"\\frz{rot}"
        if st.get("glow"):
            pre += f"\\blur{st['glow'] / 4:.1f}"
        if st.get("shadow_blur"):
            pre += f"\\be{st['shadow_blur']}"
        parts = []
        n = len(g)
        for k, (w, t) in enumerate(zip(g, texts)):
            color = st["primary"]
            tags = ""
            if w.get("emph") and st["highlight"] != "none":
                color = st["emphasis"]
            if k == active and st["highlight"] in ("color", "both", "gradient"):
                color = lerp_hex(st["active"], st.get("active_end", st["active"]), k / max(1, n - 1)) \
                    if st["highlight"] == "gradient" else st["active"]
            if anim == "reveal" and k > active:
                tags += "\\alpha&H99&"
            tags += f"\\c{_c(color)}"
            if w.get("emph") and st.get("emphasis_bold"):
                tags += "\\fnInter Display SemiBold"
            sc = int(st["active_scale"] * 100)
            if k == active and st["highlight"] in ("scale", "both", "gradient") and sc != 100:
                tags += f"\\fscx100\\fscy100\\t(0,70,\\fscx{sc}\\fscy{sc})" if not first else f"\\fscx{sc}\\fscy{sc}"
            reset = f"\\c{_c(st['primary'])}\\alpha&H00&"
            if k == active and sc != 100 and st["highlight"] in ("scale", "both", "gradient"):
                reset += "\\fscx100\\fscy100"
            if w.get("emph") and st.get("emphasis_bold"):
                reset += f"\\fn{st['font']}"
            brk = t.endswith("\\N")
            parts.append("{" + tags + "}" + t.replace("\\N", "") + "{" + reset + "}" + ("\\N" if brk else ""))
        out = ""
        for k, piece in enumerate(parts):
            out += piece + ("" if piece.endswith("\\N") or k == len(parts) - 1 else " ")
        return "{" + pre + "}" + out

    # ───────────── graphics ─────────────
    def title_card(self, text: str, y: int, dur: float = 2.6, accent: str = "#FF2B1C") -> None:
        st = self.st
        t = esc(text.upper() if st["upper"] else text)
        lines = _wrap(t, 20)
        fs = 74 if max(len(l) for l in lines) <= 16 else 64
        h = len(lines) * fs * 1.18 + 44
        wbox = min(980, max(len(l) for l in lines) * fs * 0.58 + 90)
        x0, y0 = (W - wbox) / 2, y - h / 2
        box = _rrect(wbox, h, 22)
        e = dur
        self.ev(2, 0.0, e, "Gfx", "{\\an7\\pos(%d,%d)\\bord0\\shad0\\1c&H0B0B0C&\\1a&H22&\\fscx0\\t(0,180,\\fscx100)"
                "\\t(%d,%d,\\fscx0)\\p1}%s{\\p0}" % (x0, y0, int(e * 1000) - 160, int(e * 1000), box))
        self.ev(2, 0.0, e, "Gfx", "{\\an7\\pos(%d,%d)\\bord0\\shad0\\1c%s\\fscx0\\t(0,180,\\fscx100)\\t(%d,%d,\\fscx0)"
                "\\p1}m 0 0 l 10 0 l 10 %d l 0 %d{\\p0}" % (x0, y0, _c(accent), int(e * 1000) - 160, int(e * 1000), h, h))
        txt = "\\N".join(lines)
        self.ev(3, 0.08, e - 0.05, "Gfx", "{\\an5\\pos(%d,%d)\\fn%s\\fs%d\\bord0\\shad0\\c&HFFFFFF&\\fad(120,120)"
                "\\fscx92\\fscy92\\t(0,200,\\fscx100\\fscy100)}%s" % (W / 2 + 5, y, st["font"] if st["upper"] else "Inter Display Black", fs, txt))

    def stat_callout(self, s: float, value: str, label: str, y: int, accent: str) -> None:
        e = s + 1.7
        self.ev(2, s, e, "Gfx", "{\\an5\\pos(%d,%d)\\fs150\\bord6\\3c&H000000&\\shad0\\c%s\\fscx40\\fscy40"
                "\\t(0,140,\\fscx112\\fscy112)\\t(140,240,\\fscx100\\fscy100)\\fad(0,180)}%s"
                % (W / 2, y, _c(accent), esc(value)))
        if label:
            self.ev(2, s + 0.1, e, "Gfx", "{\\an5\\pos(%d,%d)\\fnInter Display SemiBold\\fs44\\bord4\\3c&H000000&"
                    "\\shad0\\c&HFFFFFF&\\fad(140,180)}%s" % (W / 2, y + 108, esc(label.upper())))

    def keyword_pop(self, s: float, word: str, y: int, accent: str) -> None:
        e = s + 0.75
        self.ev(2, s, e, "Gfx", "{\\an5\\pos(%d,%d)\\fs170\\bord8\\3c&H000000&\\shad0\\c%s\\fscx130\\fscy130"
                "\\t(0,90,\\fscx100\\fscy100)\\fad(0,160)\\frz-4}%s" % (W / 2, y, _c(accent), esc(word.upper())))

    def progress_bar(self, dur: float, color: str) -> None:
        y = 0
        self.ev(3, 0, dur, "Gfx", "{\\an7\\pos(0,%d)\\bord0\\shad0\\1c&HFFFFFF&\\1a&HC8&\\p1}m 0 0 l %d 0 l %d 8 l 0 8{\\p0}"
                % (y, W, W))
        self.ev(3, 0, dur, "Gfx", "{\\an7\\pos(0,%d)\\bord0\\shad0\\1c%s\\clip(0,0,0,12)\\t(0,%d,\\clip(0,0,%d,12))"
                "\\p1}m 0 0 l %d 0 l %d 8 l 0 8{\\p0}" % (y, _c(color), int(dur * 1000), W, W, W))

    def attribution(self, text: str, dur: float = 3.5) -> None:
        self.ev(3, 0.2, dur, "UI", "{\\an7\\pos(48,96)\\fad(200,300)\\1a&H30&}%s" % esc(text))

    def watermark(self, dur: float, text: str = "NPC") -> None:
        self.ev(3, 0, dur, "UI", "{\\an9\\pos(1032,96)\\fnInter Display Black\\fs40\\1a&H70&\\bord0\\shad1}%s" % esc(text))

    def context_card(self, s: float, e: float, text: str, y: int) -> None:
        lines = _wrap(esc(text), 34)
        h = len(lines) * 50 + 70
        box = _rrect(940, h, 24)
        self.ev(2, s, e, "Gfx", "{\\an7\\pos(70,%d)\\bord0\\shad0\\1c&H0B0B0C&\\1a&H30&\\fad(200,200)\\p1}%s{\\p0}"
                % (y - h / 2, box))
        self.ev(3, s, e, "Gfx", "{\\an5\\pos(540,%d)\\fnInter Display SemiBold\\fs40\\bord0\\shad0\\fad(200,200)}%s"
                % (y, "\\N".join(lines)))

    def save(self, path) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.header())
            f.write("\n".join(self.events) + "\n")


def _wrap(text: str, n: int) -> list[str]:
    lines, cur = [], ""
    for w in text.split():
        if cur and len(cur) + 1 + len(w) > n:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines[:3]


def _rrect(w: float, h: float, r: float) -> str:
    w, h, r = int(w), int(h), int(r)
    return (f"m {r} 0 l {w - r} 0 b {w} 0 {w} 0 {w} {r} l {w} {h - r} b {w} {h} {w} {h} {w - r} {h} "
            f"l {r} {h} b 0 {h} 0 {h} 0 {h - r} l 0 {r} b 0 0 0 0 {r} 0")


def frame_time(f: int) -> float:
    return f / FPS
