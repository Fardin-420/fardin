"""Build a project's timeline.json — the single source of timing truth.

Line times come from the measured NPC_VOICE_V1 narration when it exists
(audio/narration/narration_manifest.json), otherwise from the estimates in
script.json. Scene bounds and every animation/sound cue are derived from those
line times, so the renderer and the sound engine always agree.

    python build_timeline.py ../../PROJECTS/NPC_NO_EDITOR_JUST_CODE
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path


def word_time(line: dict, word: str) -> float:
    """Approximate the onset of `word` inside a line by character position."""
    text = line["text"]
    i = text.find(word)
    if i < 0:
        raise KeyError(f"{word!r} not in {text!r}")
    return line["start"] + (line["end"] - line["start"]) * (i / max(len(text), 1)) * 0.92


def main(project: Path) -> None:
    script = json.loads((project / "source" / "script.json").read_text())
    manifest_path = project / "audio" / "narration" / "narration_manifest.json"
    measured = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
    measured_by_id = {l["id"]: l for l in measured["lines"]} if measured else {}

    t = script["lead_in"]
    lines = []
    for line in script["lines"]:
        if line["id"] in measured_by_id:
            m = measured_by_id[line["id"]]
            start, end = m["start"], m["end"]
            t = end + line["pause_after"]
        else:
            start, end = t, t + line["est"]
            t = end + line["pause_after"]
        lines.append({"id": line["id"], "scene": line["scene"], "text": line["text"],
                      "emotion": line["emotion"], "start": round(start, 3), "end": round(end, 3)})
    L = {l["id"]: l for l in lines}

    fps = script["video"]["fps"]
    duration = L["L15"]["end"] + script["tail"]
    frames = math.ceil(duration * fps)

    bounds = {
        "S01": (0.0, L["L02"]["start"] - 0.35),
        "S02": (L["L02"]["start"] - 0.35, L["L05"]["start"] - 0.3),
        "S03": (L["L05"]["start"] - 0.3, L["L09"]["start"] - 0.35),
        "S04": (L["L09"]["start"] - 0.35, L["L11"]["start"] - 0.3),
        "S05": (L["L11"]["start"] - 0.3, L["L14"]["start"] - 0.5),
        "S06": (L["L14"]["start"] - 0.5, duration),
    }
    scenes = [{"id": k, "start": round(a, 3), "end": round(b, 3)} for k, (a, b) in bounds.items()]

    w = word_time
    cues = {
        # S01 — impossible opening
        "cursor_on": 0.3,
        "whisper": L["L01"]["start"],
        "pulse": L["L01"]["end"] + 0.25,
        "title_slam": L["L01"]["end"] + 0.42,
        # S02 — break the rules
        "s02_whip": bounds["S02"][0],
        "premiere_in": w(L["L02"], "Premiere"),
        "premiere_break": L["L03"]["start"] - 0.12,
        "capcut_in": w(L["L03"], "CapCut"),
        "capcut_break": L["L04"]["start"] - 0.08,
        "ae_in": w(L["L04"], "After"),
        "ae_break": L["L04"]["end"] + 0.18,
        # S03 — every frame is code
        "s03_in": bounds["S03"][0],
        "transition_word": L["L05"]["start"],
        "effect_word": L["L06"]["start"],
        "frame_word": L["L07"]["start"],
        "frame_hit": w(L["L07"], "frame"),
        "code_word": L["L08"]["start"],
        "code_resolve": L["L08"]["end"] + 0.1,
        # S04 — voice reveal
        "s04_in": bounds["S04"][0],
        "mine": L["L10"]["start"],
        "symbol_morph": L["L10"]["end"] + 0.05,
        # S05 — no timeline
        "layers": L["L11"]["start"],
        "collapse": L["L12"]["start"],
        "explode": L["L13"]["start"] + 0.02,
        # S06 — identity
        "s06_in": bounds["S06"][0],
        "emblem_lock": L["L14"]["start"] + 0.35,
        "tagline": L["L15"]["start"],
        "final_hit": L["L15"]["end"] + 0.35,
    }
    cues = {k: round(v, 3) for k, v in cues.items()}

    timeline = {
        "project": script["project"],
        "voiced": measured is not None,
        "timing_source": "measured NPC_VOICE_V1 narration" if measured else "estimated (awaiting NPC_VOICE_V1)",
        "width": script["video"]["width"], "height": script["video"]["height"],
        "fps": fps, "duration": round(duration, 3), "durationInFrames": frames,
        "lines": lines, "scenes": scenes, "cues": cues,
    }
    out = project / "source" / "timeline.json"
    out.write_text(json.dumps(timeline, indent=2) + "\n")
    print(f"timeline: {duration:.2f}s / {frames} frames ({timeline['timing_source']}) -> {out}")


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
