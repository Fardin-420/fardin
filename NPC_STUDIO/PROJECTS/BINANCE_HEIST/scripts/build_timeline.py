"""Lay the narration out on the film's master clock and emit timeline.json.

Single source of timing truth for picture (Remotion), captions and sound:
scene bounds, chapter/title cards, cue frames (from word onsets), punch/impact
frames, transitions, and every caption word. Also writes audio/vo_track.wav.

    .venv/bin/python scripts/build_timeline.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT.parents[1] / "RENDER_ENGINE"
FPS, SR = 30, 48000

CHAPTERS = {"S02": (1, "THE FORTRESS"), "S03": (2, "THE FIRST HEIST"), "S04": (3, "THE DOOR"),
            "S05": (4, "THE 20 MINUTES"), "S06": (5, "THE RACE TO FREEZE"), "S07": (6, "THE NAME"),
            "S08": (7, "THE MORNING AFTER"), "S09": (8, "THE QUESTION")}
CHAPTER_DATES = {"S02": "BINANCE · 2025 ANNUAL REPORT", "S03": "MAY 7, 2019", "S04": "OCTOBER 28–30, 2026",
                 "S05": "OCTOBER 29, 2026 · 20:05–23:05 UTC", "S06": "OCTOBER 29–30, 2026",
                 "S07": "OCTOBER 30 – NOVEMBER 3, 2026", "S08": "OCTOBER 30 – NOVEMBER 1, 2026",
                 "S09": "AS OF NOVEMBER 3, 2026"}
# transition INTO each scene: (type, frames)
TRANS_IN = {"S02": ("dipBlack", 12), "S03": ("filmBurn", 18), "S04": ("filmBurn", 18), "S05": ("cut", 0),
            "S06": ("iceWipe", 16), "S07": ("dipBlack", 12), "S08": ("dataWipe", 12),
            "S09": ("dipBlack", 12), "S10": ("dipBlack", 12)}
CARD = 2.5
TITLE = 4.0
END_SCREEN = 20.0


def main():
    man = json.loads((ROOT / "assets" / "vo" / "alignment" / "vo_manifest.json").read_text())
    by_scene: dict[str, list] = {}
    for c in man["chunks"]:
        by_scene.setdefault(c["scene"], []).append(c)

    t = 0.0
    scenes, words, sentences, vo_place = [], [], [], []
    for sc in man["scenes"]:
        sid = sc["id"]
        chunks = by_scene[sid]
        start = t
        lead = 1.2 if sid == "S01" else (CARD + 0.35 if sid in CHAPTERS else 0.9)
        vt = start + lead
        cues, punches, impacts = {}, [], []
        for c in chunks:
            vo_place.append((vt, c["file"]))
            sw = []
            for i, w in enumerate(c["words"]):
                ws, we = vt + w["start"], vt + w["end"]
                rec = {"w": w["w"], "s": round(ws, 3), "e": round(we, 3), "scene": sid, "chunk": c["id"]}
                words.append(rec)
                sw.append(rec)
                for m in c["marks"]:
                    if m["word"] == i:
                        f = round((ws - start) * FPS)
                        if m["mark"].startswith("CUE:"):
                            cues[m["mark"][4:]] = f
                        elif m["mark"] == "PUNCH":
                            punches.append(f)
                        elif m["mark"] == "IMPACT":
                            impacts.append(f)
            sentences.append({"scene": sid, "text": c["text"], "s": sw[0]["s"], "e": sw[-1]["e"]})
            vt += c["dur"] + c["gap_after"]
        vo_end = vt
        if sid == "S01":
            title_at = vo_end + 0.2
            end = title_at + TITLE
            cues["titlecard"] = round((title_at - start) * FPS)
        elif sid == "S09":
            end = vo_end + 1.0  # [[SILENCE]] hold already included; one more second of black
        elif sid == "S10":
            sub = start + cues["sub"] / FPS
            end = max(vo_end + 1.5, sub + END_SCREEN)
            cues["endscreen"] = cues["sub"]
        else:
            end = vo_end + 0.7
        tr = TRANS_IN.get(sid, ("cut", 0))
        scenes.append({
            "id": sid, "title": sc["title"],
            "chapter": CHAPTERS.get(sid, (None, None))[0], "chapterTitle": CHAPTERS.get(sid, (None, None))[1],
            "chapterDate": CHAPTER_DATES.get(sid),
            "start": round(start * FPS), "end": round(end * FPS), "voStart": round(lead * FPS),
            "cues": cues, "punches": punches, "impacts": impacts,
            "transitionIn": {"type": tr[0], "frames": tr[1]},
        })
        t = end
    total = scenes[-1]["end"]

    # VO track on the master clock
    vo = np.zeros(int(total / FPS * SR) + SR, np.float32)
    for at, f in vo_place:
        y, _ = sf.read(ROOT / f, dtype="float32")
        i = int(round(at * SR))
        vo[i:i + len(y)] += y
    (ROOT / "audio").mkdir(exist_ok=True)
    sf.write(ROOT / "audio" / "vo_track.wav", vo[: int(total / FPS * SR)], SR, subtype="PCM_24")

    tl = {"fps": FPS, "width": 1920, "height": 1080, "durationInFrames": total,
          "factsAsOf": "NOV 3, 2026", "voice": man["voice"], "scenes": scenes,
          "words": words, "sentences": sentences}
    out = ENGINE / "src" / "heist" / "data"
    out.mkdir(parents=True, exist_ok=True)
    (out / "timeline.json").write_text(json.dumps(tl))
    (ROOT / "script" / "timeline.json").write_text(json.dumps(tl, indent=1))
    print(f"timeline: {total} frames = {total/FPS/60:.2f} min · {len(scenes)} scenes · {len(words)} words")
    for s in scenes:
        print(f"  {s['id']} {s['start']/FPS/60:5.2f}–{s['end']/FPS/60:5.2f} min  cues={len(s['cues'])} "
              f"punch={len(s['punches'])} impact={len(s['impacts'])}  {s['title']}")


if __name__ == "__main__":
    main()
