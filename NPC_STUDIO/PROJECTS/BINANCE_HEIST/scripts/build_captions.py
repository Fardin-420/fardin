"""Caption pages (burned-in) + out/captions_en.srt from the same word timings.

Pages: max 2 lines × 34 characters, never crossing a sentence, preferring breaks
at punctuation. Key terms pop once. Captions hide while the same words are
already big on screen (quote cards, the $6.3B counter).

    .venv/bin/python scripts/build_captions.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT.parents[1] / "RENDER_ENGINE"
MAXC, LINES = 34, 2
# (scene, cue that starts the hide, cue/None whose sentence end closes it)
HIDE = [("S01", "billions", "total"), ("S03", "quote2019", None), ("S03", "quoteCZ", None),
        ("S04", "oneclick", None), ("S06", "t2124", None), ("S07", "fbi", None), ("S07", "deny", None),
        ("S08", "teng", None), ("S08", "98", None),
        ("S02", "before", None), ("S03", "apikeys", None), ("S03", "lesson", "around"), ("S04", "back", None),
        ("S07", "playbook", "remember"), ("S07", "pattern", None)]
POP = {"billions", "fifty", "frozen", "north", "korea"}


def n(w: str) -> str:
    return re.sub(r"[^a-z0-9]", "", w.lower())


def pages_for(words):
    pages, lines, cur = [], [], []

    def ln(ws):
        return len(" ".join(x["w"] for x in ws))

    for i, w in enumerate(words):
        if cur and ln(cur + [w]) > MAXC:
            lines.append(cur)
            cur = []
            if len(lines) == LINES:
                pages.append(lines)
                lines = []
        cur.append(w)
        filled = (sum(ln(l) for l in lines) + ln(cur)) / (MAXC * LINES)
        nxt = words[i + 1]["w"] if i + 1 < len(words) else ""
        if filled > 0.55 and (re.search(r"[,;:…]$", w["w"]) or nxt == "—") and i + 1 < len(words):
            lines.append(cur)
            cur = []
            pages.append(lines)
            lines = []
    if cur:
        lines.append(cur)
    if lines:
        pages.append(lines)
    return pages


def ts(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}"


def main():
    tl = json.loads((ROOT / "script" / "timeline.json").read_text())
    fps = tl["fps"]
    words = tl["words"]
    # pop flags
    for i, w in enumerate(words):
        k = n(w["w"])
        prev = n(words[i - 1]["w"]) if i else ""
        nxt = n(words[i + 1]["w"]) if i + 1 < len(words) else ""
        seq = " ".join(n(words[j]["w"]) for j in range(max(0, i - 3), min(len(words), i + 4)))
        w["pop"] = (k in POP or (k == "twenty" and nxt.startswith("minutes")) or
                    (k.startswith("minutes") and prev == "twenty") or
                    (k in {"six", "point", "three", "billion"} and "six point three billion" in seq))
    by_chunk: dict[str, list] = {}
    for w in words:
        by_chunk.setdefault(w["chunk"], []).append(w)
    out = []
    chunk_ids = list(by_chunk)
    for ci, cid in enumerate(chunk_ids):
        ws = by_chunk[cid]
        for pg in pages_for(ws):
            out.append({"s": pg[0][0]["s"], "e": pg[-1][-1]["e"],
                        "lines": [[{"w": x["w"], "s": x["s"], "e": x["e"], "pop": x["pop"]} for x in l] for l in pg]})
    for p in out:
        p["s"] = max(0.0, p["s"] - 0.08)
    for i, p in enumerate(out):
        nxt = out[i + 1]["s"] if i + 1 < len(out) else p["e"] + 1
        p["e"] = min(p["e"] + 0.35, nxt - 0.02) if nxt - p["e"] > 0.6 else nxt - 0.02
    # hide windows (seconds)
    sc = {s["id"]: s for s in tl["scenes"]}
    hide = []
    for sid, c0, c1 in HIDE:
        s = sc[sid]
        t0 = (s["start"] + s["cues"][c0]) / fps
        tref = (s["start"] + s["cues"][c1 or c0]) / fps
        sen = next(x for x in tl["sentences"] if x["scene"] == sid and x["s"] - 0.05 <= tref <= x["e"] + 0.05)
        hide.append([round(t0 - 0.1, 3), round(sen["e"] + 0.3, 3)])
    (ENGINE / "src" / "heist" / "data" / "captions.json").write_text(json.dumps({"pages": out, "hide": hide}))
    srt = []
    for i, p in enumerate(out, 1):
        srt.append(f"{i}\n{ts(p['s'])} --> {ts(p['e'])}\n" + "\n".join(" ".join(x["w"] for x in l) for l in p["lines"]) + "\n")
    (ROOT / "out").mkdir(exist_ok=True)
    (ROOT / "out" / "captions_en.srt").write_text("\n".join(srt))
    longest = max(len(" ".join(x["w"] for x in l)) for p in out for l in p["lines"])
    print(f"{len(out)} caption pages · longest line {longest} chars · {len(hide)} hide windows -> out/captions_en.srt")


if __name__ == "__main__":
    main()
