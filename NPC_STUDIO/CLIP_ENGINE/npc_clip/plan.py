"""Edit planning: turns a selected window into an editable timeline (cuts, layout, zooms, captions, graphics, sound)."""
from __future__ import annotations

import re

import numpy as np

from .captions import STYLES
from .common import FPS, H, W
from .select import CURIOSITY, EMOTION, HOOK, NUM_RE, STOP, Prosody
from .transcribe import norm

STYLE_MAP = {
    "podcast": ["hormozi", "high_energy_podcast", "bold_viral", "npc_signature"],
    "comedy": ["bold_viral", "fast_kinetic", "neon_accent"],
    "motivational": ["minimal_cinematic", "elegant_white", "dramatic_red"],
    "educational": ["clean_documentary", "modern_creator", "storytelling_yellow"],
    "gaming": ["gaming_impact", "neon_accent", "fast_kinetic"],
    "interview": ["modern_creator", "clean_documentary", "minimal_shadow", "premium_gradient"],
}
MUSIC = {"podcast": "pulse", "comedy": "playful", "motivational": "cinematic", "educational": "light",
         "gaming": "drive", "interview": "pad"}
DENSITY = {
    "high":   {"max_gap": 0.22, "punch": 0.14, "punch_every": 5.0, "alt_zoom": 0.07, "sfx_max": 4, "pops": 2, "push": False},
    "medium": {"max_gap": 0.30, "punch": 0.10, "punch_every": 7.0, "alt_zoom": 0.06, "sfx_max": 3, "pops": 1, "push": False},
    "low":    {"max_gap": 0.45, "punch": 0.07, "punch_every": 9.0, "alt_zoom": 0.035, "sfx_max": 2, "pops": 0, "push": True},
}
ACCENT = {"hormozi": "#3CFF5A", "high_energy_podcast": "#FF3B30", "bold_viral": "#FFE600", "npc_signature": "#FF2B1C",
          "fast_kinetic": "#FFE600", "neon_accent": "#39FF14", "gaming_impact": "#00F0FF", "dramatic_red": "#FF1E1E",
          "premium_gradient": "#FF8A00", "modern_creator": "#8C6CFF", "storytelling_yellow": "#FFD60A"}


def faces_in(samples: list[dict], s: float, e: float) -> list[dict]:
    return [x for x in samples if s - 0.01 <= x["t"] <= e + 0.01]


def choose_layout(vinfo: dict, fs: list[dict]) -> dict:
    sw, sh = vinfo["width"], vinfo["height"]
    aspect = sw / sh
    if aspect <= 0.62:
        return {"mode": "full", "reason": "source is already vertical"}
    n = max(1, len(fs))
    face_ratio = sum(1 for x in fs if x["faces"]) / n
    upscale = H / sh
    if face_ratio < 0.4:
        return {"mode": "fit", "reason": f"faces visible only {face_ratio:.0%} of the time; keep the full frame"}
    if upscale > 2.4:
        return {"mode": "fit", "reason": f"source height {sh}px would need {upscale:.1f}x upscale for a face crop"}
    if aspect * 9 / 16 > 1.02 or aspect >= 0.62:
        return {"mode": "track", "reason": "content-aware 9:16 crop that follows the active speaker; "
                                           "shots holding two separated speakers switch to split-screen"}
    return {"mode": "fit", "reason": "fallback"}


def two_faces(x: dict) -> bool:
    fs = sorted(x["faces"], key=lambda f: -f["w"] * f["h"])[:2]
    if len(fs) < 2 or fs[1]["w"] * fs[1]["h"] < 0.35 * fs[0]["w"] * fs[0]["h"]:
        return False
    return abs((fs[0]["x"] + fs[0]["w"] / 2) - (fs[1]["x"] + fs[1]["w"] / 2)) > 0.28


def layout_runs(segments: list[dict], face_samples: list[dict], scenes: list[dict], base: str,
                split_ok: bool) -> list[dict]:
    """Per-shot layout: split-screen only where two separated speakers are actually on screen."""
    cuts = sorted(sc["s"] for sc in scenes)
    pieces = []
    for seg in segments:
        bounds = [seg["src_s"]] + [c for c in cuts if seg["src_s"] < c < seg["src_e"]] + [seg["src_e"]]
        for a, b in zip(bounds, bounds[1:]):
            fs = faces_in(face_samples, a, b)
            has_face = sum(1 for x in fs if x["faces"]) / max(1, len(fs))
            two = sum(two_faces(x) for x in fs) / max(1, len(fs))
            mode = "split" if (base == "track" and split_ok and two >= 0.6) else base
            pieces.append({"out_s": round(seg["out_s"] + a - seg["src_s"], 4),
                           "out_e": round(seg["out_s"] + b - seg["src_s"], 4),
                           "mode": mode, "faces_expected": has_face >= 0.6, "two_faces": two >= 0.6})
    runs: list[dict] = []
    for p in pieces:
        if runs and runs[-1]["mode"] == p["mode"] and abs(runs[-1]["out_e"] - p["out_s"]) < 1e-3:
            runs[-1]["out_e"] = p["out_e"]
            runs[-1]["faces_expected"] = runs[-1]["faces_expected"] and p["faces_expected"]
        else:
            runs.append(dict(p))
    for r in runs:  # flicker guard: very short split shots stay in speaker-tracking
        if r["mode"] == "split" and r["out_e"] - r["out_s"] < 0.8:
            r["mode"] = "track"
    merged: list[dict] = []
    for r in runs:
        if merged and merged[-1]["mode"] == r["mode"]:
            merged[-1]["out_e"] = r["out_e"]
            merged[-1]["faces_expected"] = merged[-1]["faces_expected"] and r["faces_expected"]
        else:
            merged.append(r)
    return merged


def mode_at(runs: list[dict], t: float) -> str:
    for r in runs:
        if r["out_s"] - 1e-6 <= t < r["out_e"]:
            return r["mode"]
    return runs[-1]["mode"] if runs else "track"


def build_segments(ws: list[dict], max_gap: float) -> list[list[float]]:
    """Word runs → source segments. Removes fillers and dead air, keeps short dramatic pauses after ?/!."""
    keep = [w for w in ws if not w.get("filler")]
    segs: list[list[float]] = []
    run_s = None
    for k, w in enumerate(keep):
        prev = keep[k - 1] if k else None
        if prev is None:
            run_s = w["s"] - 0.06
            continue
        gap = w["s"] - prev["e"]
        dramatic = re.search(r"[?!]$", prev["w"]) and gap <= 1.2
        removed_filler = any(x.get("filler") and prev["e"] <= x["s"] < w["s"] for x in ws)
        if gap > max_gap or removed_filler:
            if dramatic:
                hold = min(gap, 0.6)
                segs.append([run_s, prev["e"] + hold - 0.06])
            else:
                segs.append([run_s, prev["e"] + min(0.12, gap / 2)])
            run_s = w["s"] - min(0.08, gap / 2)
    if keep:
        segs.append([run_s, keep[-1]["e"] + 0.18])
    # merge micro-gaps, quantize to whole frames
    merged: list[list[float]] = []
    for s, e in segs:
        if merged and s - merged[-1][1] < 0.06:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    out = []
    for s, e in merged:
        n = max(1, round((e - s) * FPS))
        out.append([round(s, 4), round(s + n / FPS, 4)])
    return out


def emphasis_scores(ws: list[dict], pros: Prosody) -> list[float]:
    sc = []
    for w in ws:
        t = norm(w["w"])
        v = 0.0
        if not t or t in STOP:
            sc.append(-1.0)
            continue
        v += 2.0 * (t in HOOK) + 2.0 * (t in EMOTION) + 1.2 * (t in CURIOSITY) + 3.0 * bool(NUM_RE.search(w["w"]))
        v += 0.4 * (len(t) > 5)
        v += float(np.clip(pros.z(w["s"], w["e"], 80), -1, 2))
        if w["w"].endswith(("!", "?")):
            v += 0.8
        sc.append(v)
    return sc


def plan_clip(idx: int, c: dict, tr: dict, ana: dict, face_samples: list[dict], vinfo: dict, meta: dict,
              ctype: str, opts: dict) -> dict:
    words = tr["words"]
    sents = [s for s in tr["sentences"] if s["text"].strip()]
    pros = Prosody(ana["audio"])
    style_key = c["package"].get("caption_style") or opts.get("style")
    pal = STYLE_MAP.get(ctype, STYLE_MAP["podcast"])
    if not style_key or style_key not in STYLES:
        energetic = c["factors"]["emotion"] + c["factors"]["hook"] > 125
        style_key = pal[0] if energetic else pal[idx % len(pal)]
        if opts.get("brand") and idx % 4 == 3:
            style_key = "npc_signature"
    st = STYLES[style_key]
    dens = DENSITY[st["density"]]

    # ── cuts: optional cold-open teaser, then the main window
    main_ws = words[sents[c["i"]]["wi"][0]: sents[c["j"]]["wi"][1] + 1]
    parts = []
    if c.get("cold_open_sentence") is not None:
        cs = sents[c["cold_open_sentence"]]
        parts.append(("teaser", build_segments(words[cs["wi"][0]: cs["wi"][1] + 1], dens["max_gap"])))
    parts.append(("main", build_segments(main_ws, dens["max_gap"])))
    segments, t_out = [], 0.0
    for kind, segs in parts:
        for s, e in segs:
            n = round((e - s) * FPS)
            segments.append({"part": kind, "src_s": s, "src_e": e, "out_s": round(t_out, 4),
                             "out_e": round(t_out + n / FPS, 4), "frames": n})
            t_out += n / FPS
    dur = t_out

    # ── words remapped to output time
    out_words = []
    for seg in segments:
        for w in words:
            if w.get("filler") or w["e"] <= seg["src_s"] + 0.01 or w["s"] >= seg["src_e"] - 0.01:
                continue
            s = seg["out_s"] + max(0.0, w["s"] - seg["src_s"])
            e = seg["out_s"] + min(seg["src_e"], w["e"]) - seg["src_s"]
            out_words.append({"w": w["w"], "s": round(s, 3), "e": round(max(e, s + 0.05), 3), "src": w["s"]})
    out_words.sort(key=lambda w: w["s"])
    for a, b in zip(out_words, out_words[1:]):
        a["e"] = min(a["e"], b["s"])

    # ── emphasis words (spaced, limited)
    esc = emphasis_scores(out_words, pros)
    order = sorted(range(len(out_words)), key=lambda k: -esc[k])
    emph: list[int] = []
    budget = max(2, min(7, int(dur / 6)))
    for k in order:
        if esc[k] < 1.6 or len(emph) >= budget:
            break
        if all(abs(out_words[k]["s"] - out_words[m]["s"]) > 2.2 for m in emph):
            emph.append(k)
    for k in emph:
        out_words[k]["emph"] = True

    # ── zooms: alternate framing at jump cuts + punch-ins on strongest emphasis words
    zooms, last_punch = [], -99.0
    for k in sorted(emph, key=lambda k: -esc[k]):
        t = out_words[k]["s"]
        if t - last_punch < dens["punch_every"] * 0.5 or t < 0.4 or t > dur - 0.8:
            continue
        if any(abs(t - z["t"]) < dens["punch_every"] for z in zooms):
            continue
        hold = min(1.8, dur - t - 0.3)
        zooms.append({"t": round(t - 0.04, 3), "type": "push" if dens["push"] else "punch",
                      "amount": dens["punch"], "attack": 1.0 if dens["push"] else 0.12,
                      "hold": round(hold, 2), "release": 0.45, "word": out_words[k]["w"]})
    zooms.sort(key=lambda z: z["t"])
    cut_times = [s["out_s"] for s in segments[1:]]
    base_zoom = []
    lvl = 0
    for i, seg in enumerate(segments):
        if i and not (seg["part"] == "main" and segments[i - 1]["part"] == "teaser"):
            lvl ^= 1
        base_zoom.append(1.0 + lvl * dens["alt_zoom"])
    for seg, z in zip(segments, base_zoom):
        seg["base_zoom"] = round(z, 3)

    # ── layout from the faces inside the source span(s)
    span_s, span_e = min(s["src_s"] for s in segments), max(s["src_e"] for s in segments)
    fs = faces_in(face_samples, span_s, span_e)
    layout = choose_layout(vinfo, fs)
    runs = layout_runs(segments, face_samples, ana["scenes"], layout["mode"], split_ok=H / vinfo["height"] * 0.62 <= 2.6)
    layout["runs"] = runs
    face_band = _face_band(layout, [x for x in fs if not two_faces(x)] or fs, vinfo)

    # caption/title placement inside platform safe zones (top 150, bottom 380, right 130);
    # during split-screen shots captions sit on the panel seam (y=960)
    if layout["mode"] == "fit":
        panel_h = W * vinfo["height"] / vinfo["width"]
        cap_y = int(min(1480, (H + panel_h) / 2 + 150))
        title_y = int(max(260, (H - panel_h) / 2 - 140))
    else:
        cap_y = 1290
        if face_band and face_band[1] > 1160:
            cap_y = 1470
        title_y = 300
        if face_band and face_band[0] < 440:
            title_y = int(cap_y - 230) if cap_y < 1400 else 300
    # ── transitions & sound design events
    transitions = []
    sfx = []
    teaser_end = next((s["out_s"] for s in segments if s["part"] == "main"), 0.0)
    if teaser_end > 0:
        transitions.append({"t": round(teaser_end, 3), "type": "whip", "frames": 8})
        sfx.append({"t": round(teaser_end - 0.2, 3), "type": "whoosh", "gain_db": -14})
    for z in zooms[: max(0, dens["sfx_max"] - len(sfx))]:
        if z["type"] == "punch":
            sfx.append({"t": z["t"], "type": "impact" if st["look"] != "neon" else "glitch", "gain_db": -20})
    # ── graphics
    accent = ACCENT.get(style_key, st["active"])
    graphics = [{"type": "progress_bar", "color": accent}]
    title = c["package"]["title"]
    graphics.append({"type": "title_card", "text": c["package"].get("cover_text") or title, "y": title_y,
                     "dur": round(min(2.8, max(1.8, dur * 0.08)), 2)})
    stats = 0
    for k, w in enumerate(out_words):
        if stats >= 2 or not re.search(r"\d", w["w"]) or w["s"] < 3.0:
            continue
        val = re.sub(r"[,.;:!?]+$", "", w["w"])
        sy = title_y if layout["mode"] != "fit" else title_y + 40
        if mode_at(runs, w["s"]) == "split":
            sy = 960 - 170
        graphics.append({"type": "stat", "t": w["s"], "value": val, "label": "", "y": sy})
        sfx.append({"t": w["s"], "type": "pop", "gain_db": -18})
        stats += 1
    pops = 0
    for k in sorted(emph, key=lambda k: -esc[k]):
        if pops >= dens["pops"]:
            break
        w = out_words[k]
        if re.search(r"\d", w["w"]) or w["s"] < 3.2 or len(norm(w["w"])) < 4 or mode_at(runs, w["s"]) == "split":
            continue
        if any(g.get("t") is not None and abs(g["t"] - w["s"]) < 2 for g in graphics):
            continue
        graphics.append({"type": "keyword_pop", "t": w["s"], "word": re.sub(r"[^\w'-]", "", w["w"]),
                         "y": cap_y - 210 if cap_y > 1100 else cap_y + 230})
        pops += 1
    commentary = c["package"].get("commentary")
    if commentary:
        graphics.append({"type": "context_card", "s": max(0.0, dur - 4.5), "e": dur, "text": commentary,
                         "y": title_y + 40})
    creator = meta.get("creator") or meta.get("display_name")
    if creator and meta["rights"]["classification"] != "MINE":
        graphics.append({"type": "attribution", "text": f"Source: {creator}"})
    if opts.get("brand") and meta["rights"]["classification"] in ("MINE", "LICENSED", "AUTHORIZED"):
        graphics.append({"type": "watermark", "text": "NPC"})

    return {
        "clip_id": f"NPC_CLIP_{idx + 1:02d}",
        "version": 1,
        "source": {"path": meta["media_path"], "url": meta.get("url"), "name": meta.get("display_name"),
                   "creator": meta.get("creator"), "rights": meta["rights"]["classification"]},
        "window": {"start": c["start"], "end": c["end"], "cold_open": c.get("cold_open_sentence") is not None},
        "content_type": ctype, "caption_style": style_key, "density": st["density"], "look": st["look"],
        "music": {"mood": MUSIC.get(ctype, "pad"), "level_db": -24 if st["density"] != "low" else -27},
        "duration": round(dur, 3), "frames": sum(s["frames"] for s in segments),
        "layout": layout, "face_band": face_band, "caption_y": cap_y, "title_y": title_y,
        "segments": segments, "words": out_words, "zooms": zooms, "transitions": transitions,
        "sfx": sfx, "graphics": graphics, "cut_times": cut_times,
        "score": c["score"], "factors": c["factors"], "hook_type": c["hook_type"], "package": c["package"],
        "selected_by": c.get("selected_by", "auto-scorer"),
    }


def _face_band(layout: dict, fs: list[dict], vinfo: dict):
    """Vertical extent (output px) faces occupy in track mode — used to keep captions/titles off faces."""
    if layout["mode"] != "track" or not fs:
        return None
    tops = [f["y"] for x in fs for f in x["faces"]]
    bots = [f["y"] + f["h"] for x in fs for f in x["faces"]]
    if not tops:
        return None
    return [int(np.percentile(tops, 10) * H), int(np.percentile(bots, 90) * H)]
