"""Timeline for flat 2D explainer projects — the single source of timing truth.

    python RENDER_ENGINE/pipeline/build_explainer_timeline.py PROJECTS/PERSIAN_TWO_DIALECTS_EN

Merges source/script.json with the measured narration (narration_manifest.json):
lines and word times, scene bounds (a scene runs from its first line to the next
scene's first line), caption chunks, and named cues resolved from "LINE:word"
references. The renderer and the sound engine both read only this file.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

PUNCT = ",.?!:;"


def chunks(words: list[dict], line_end: float, next_start: float) -> list[dict]:
    """Captions show one or two words at a time, breaking at punctuation."""
    out: list[list[dict]] = []
    for w in words:
        if not out or len(out[-1]) == 2 or out[-1][-1]["w"][-1] in PUNCT or len(w["w"]) > 9 and len(out[-1]) == 1 and len(out[-1][0]["w"]) > 5:
            out.append([w])
        else:
            out[-1].append(w)
    res = []
    for i, c in enumerate(out):
        end = out[i + 1][0]["start"] if i + 1 < len(out) else min(next_start, line_end + 0.6)
        res.append({"text": " ".join(w["w"] for w in c), "words": [w["w"] for w in c], "start": c[0]["start"], "end": end})
    return res


def main(project: Path) -> None:
    script = json.loads((project / "source" / "script.json").read_text())
    man = json.loads((project / "audio" / "narration" / "narration_manifest.json").read_text())
    measured = {l["id"]: l for l in man["lines"]}
    lines = []
    for sl in script["lines"]:
        m = measured[sl["id"]]
        lines.append({"id": sl["id"], "scene": sl["scene"], "text": sl["text"], "start": m["start"], "end": m["end"],
                      "words": m["words"], "hl": sl.get("hl", {})})
    duration = man["duration"] + script["tail"]
    for i, l in enumerate(lines):
        l["captions"] = chunks(l["words"], l["end"], lines[i + 1]["start"] if i + 1 < len(lines) else duration)

    scenes = []
    for l in lines:
        if not scenes or scenes[-1]["id"] != l["scene"]:
            scenes.append({"id": l["scene"], "label": script["scene_labels"][l["scene"]], "start": 0.0 if not scenes else l["start"] - 0.25})
    for i, s in enumerate(scenes):
        s["end"] = scenes[i + 1]["start"] if i + 1 < len(scenes) else duration
        s["start"], s["end"] = round(s["start"], 3), round(s["end"], 3)

    by_id = {l["id"]: l for l in lines}
    cues = {}
    for name, ref in script["cues"].items():
        off = 0.0
        if "+" in ref:
            ref, o = ref.split("+")
            off = float(o)
        lid, key = ref.split(":", 1)
        l = by_id[lid]
        if key in ("start", "end"):
            t = l[key]
        else:
            t = next((w["start"] for w in l["words"] if w["w"] == key), None)
            if t is None:
                raise SystemExit(f"cue {name}: word {key!r} not in {lid}")
        cues[name] = round(t + off, 3)
    for s in scenes:
        cues[f"scene_{s['id']}"] = s["start"]

    fps = script["fps"]
    tl = {"project": script["project"], "voice": man["source"], "width": script["width"], "height": script["height"], "fps": fps,
          "duration": round(duration, 3), "durationInFrames": math.ceil(duration * fps), "highlight": script["highlight"],
          "lines": lines, "scenes": scenes, "cues": dict(sorted(cues.items(), key=lambda kv: kv[1]))}
    (project / "source" / "timeline.json").write_text(json.dumps(tl, indent=1, ensure_ascii=False))
    print(f"timeline: {duration:.2f}s, {len(scenes)} scenes, {len(cues)} cues")
    for s in scenes:
        print(f"  {s['id']:12s} {s['start']:6.2f} – {s['end']:6.2f}")


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
