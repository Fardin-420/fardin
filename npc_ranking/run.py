#!/usr/bin/env python3
"""NPC ranking factory: sources -> analysis -> voice -> audio -> video -> mux -> QC.

usage: python3 run.py [config.json] [--preview] [--skip-voice]
"""
import json
import os
import subprocess
import sys

from npc import analyze, audio, qc, voice
from npc.render import Renderer, build_timeline

ROOT = os.path.dirname(os.path.abspath(__file__))


def fetch_sources(cfg):
    for k, s in cfg["sources"].items():
        p = os.path.join(ROOT, s["file"])
        if not os.path.exists(p):
            os.makedirs(os.path.dirname(p), exist_ok=True)
            subprocess.run(["curl", "-sSL", "-f", "-o", p, s["url"]], check=True)
        info = analyze.probe(p)
        print(f"source {k}: {info['width']}x{info['height']} {info['fps']:.0f}fps {info['duration']:.1f}s")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    cfg = json.load(open(os.path.join(ROOT, args[0] if args else "config.json")))
    out_dir = os.path.join(ROOT, cfg["project"]); work = os.path.join(ROOT, "work")
    os.makedirs(out_dir, exist_ok=True); os.makedirs(work, exist_ok=True)
    fetch_sources(cfg)
    segs, total = build_timeline(cfg)
    print("timeline:", [(s["id"], round(s["start"], 2), round(s["dur"], 2)) for s in segs], "total", round(total, 2))

    vjson = os.path.join(work, "voice", "voice.json")
    if "--skip-voice" in sys.argv and os.path.exists(vjson):
        vo = json.load(open(vjson))
    else:
        lines = [{"id": s["id"], "rank": s["rank"], "vo": s["vo"], "start": s["start"], "dur": s["dur"]} for s in segs]
        end = next(s for s in segs if s["id"] == "r1")
        ec = next(f for f in end["fx"] if f["type"] == "endcard")
        lines.append({"id": "end", "rank": None, "vo": cfg.get("end_vo", ""), "start": end["start"] + ec["t0"] - 0.05,
                      "dur": total - (end["start"] + ec["t0"])})
        vo = voice.generate(cfg, lines, os.path.join(work, "voice"))
    for v in vo:
        print(f"vo {v['id']:<5} {v['start']:6.2f}-{v['start'] + v['dur']:6.2f} {'ok' if v['fits'] else 'OVERRUN'}")

    r = Renderer(cfg, ROOT, vo)
    if "--preview" in sys.argv:
        os.makedirs(os.path.join(work, "pv"), exist_ok=True)
        ts = [s["start"] + f * s["dur"] for s in segs for f in (0.1, 0.4, 0.75)]
        r.render(os.path.join(work, "pv", "p"), ts); return

    mixwav = os.path.join(work, "mix.wav"); vid = os.path.join(work, "video.mp4")
    if "--mux-only" not in sys.argv:
        print("audio:", audio.mix(cfg, ROOT, segs, total, vo, mixwav))
        r.render(vid)

    e = cfg["export"]; final = os.path.join(out_dir, "FINAL_RANKING_SHORT.mp4")
    meas = subprocess.run(["ffmpeg", "-hide_banner", "-i", mixwav, "-af",
                           f"loudnorm=I={e['loudness_lufs']}:TP={e['true_peak']}:LRA=11:print_format=json",
                           "-f", "null", "-"], capture_output=True, text=True).stderr
    m = json.loads(meas[meas.rindex("{"):meas.rindex("}") + 1])
    ln = (f"loudnorm=I={e['loudness_lufs']}:TP={e['true_peak']}:LRA=11:measured_I={m['input_i']}:"
          f"measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
          f"offset={m['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", vid, "-i", mixwav, "-map", "0:v", "-map", "1:a",
                    "-c:v", "libx264", "-preset", "slow", *(["-b:v", e["bitrate"]] if e.get("bitrate") else ["-crf", str(e["crf"])]),
                    "-maxrate", e["maxrate"], "-bufsize", "32M", "-pix_fmt", "yuv420p", "-r", str(e["fps"]), "-af", ln, "-c:a", "aac",
                    "-b:a", e["audio_bitrate"], "-ar", "48000", "-shortest", "-movflags", "+faststart", final],
                   check=True)
    res = qc.validate(final, cfg)
    txt = qc.report(res)
    print(txt)
    open(os.path.join(work, "qc.txt"), "w").write(txt)


if __name__ == "__main__":
    main()
