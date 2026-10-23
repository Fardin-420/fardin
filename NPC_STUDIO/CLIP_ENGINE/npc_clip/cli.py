"""npc-clip — NPC VIRAL STUDIO command line.

  npc-clip --input SOURCE_URL_OR_FILE_OR_FOLDER --niche business --clips 12 --platform all --style viral-pro --rights mine
  npc-clip render --project NPC_VIRAL_STUDIO/<NAME> [--clip 3]      re-render after editing a timeline JSON
  npc-clip feedback --stats performance.csv                          learn from real platform numbers
  npc-clip styles                                                    list caption presets
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from .common import (FPS, OUTPUT_ROOT, REGISTRY, correct_word, load_corrections, log, project_dirs, read_json,
                     run, write_json)


# ───────────────────────── one clip: ASS → video → audio → mux → QC (+repair) ─────────────────────────

def build_ass(tl: dict, path: Path) -> None:
    from .captions import ASS
    a = ASS(tl["caption_style"], tl["caption_y"])
    from .plan import mode_at
    runs = tl["layout"].get("runs") or []
    a.captions(tl["words"], tl["duration"],
               y_at=lambda t: 960 if runs and mode_at(runs, t) == "split" else tl["caption_y"])
    for g in tl["graphics"]:
        t = g["type"]
        if t == "progress_bar":
            a.progress_bar(tl["duration"], g["color"])
        elif t == "title_card":
            a.title_card(g["text"], g["y"], g["dur"], accent=next(
                (x["color"] for x in tl["graphics"] if x["type"] == "progress_bar"), "#FF2B1C"))
        elif t == "stat":
            a.stat_callout(g["t"], g["value"], g["label"], g["y"], a.st["active"] if a.st["active"] != "#FFFFFF" else "#FFE600")
        elif t == "keyword_pop":
            a.keyword_pop(g["t"], g["word"], g["y"], a.st["emphasis"] if a.st["emphasis"] != "#FFFFFF" else "#FFE600")
        elif t == "attribution":
            a.attribution(g["text"])
        elif t == "watermark":
            a.watermark(tl["duration"], g["text"])
        elif t == "context_card":
            a.context_card(g["s"], g["e"], g["text"], g["y"])
    a.save(path)


def mux(video: Path, audio: Path, out: Path, dur: float) -> None:
    tmp = out.with_name("." + out.name)
    run(["ffmpeg", "-y", "-v", "error", "-i", video, "-i", audio, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-t", f"{dur:.3f}", "-movflags", "+faststart", tmp])
    tmp.replace(out)


def render_clip(root: str, tl_path: str) -> dict:
    from . import audio as au
    from .qc import qc_clip
    from .video import render_video
    root, tl_path = Path(root), Path(tl_path)
    dirs = project_dirs(root)
    tl = json.loads(tl_path.read_text())
    ana = read_json(dirs["Analysis"] / "scene_analysis.json")
    ft = read_json(dirs["Analysis"] / "face_tracks.json")
    meta = read_json(dirs["Source"] / "source_metadata.json")
    tr = read_json(dirs["Analysis"] / "transcript.json")
    fixes = load_corrections(root)
    if fixes:
        for w in tl["words"]:
            w["w"] = correct_word(w["w"], fixes)
        for w in tr["words"]:
            w["w"] = correct_word(w["w"], fixes)
    cid = tl["clip_id"]
    work = dirs["work"] / cid
    work.mkdir(parents=True, exist_ok=True)
    out = dirs["Clips"] / f"{cid}.mp4"
    repairs = []
    t0 = time.time()
    for attempt in range(3):
        ass = work / f"{cid}.ass"
        build_ass(tl, ass)
        vid = work / f"{cid}_video.mp4"
        frames_dir = work / "cover_frames"
        shutil.rmtree(frames_dir, ignore_errors=True)
        log(f"{cid}: rendering {tl['frames']} frames ({tl['layout']['mode']}, {tl['caption_style']})")
        render_video(tl, ana, ft, meta["video"], ass, vid, frames_dir)
        master = au.build_audio(tl, work)
        mux(vid, master, out, tl["duration"])
        rep = qc_clip(out, tl, tr["words"], dirs["QC"] / f"{cid}_contact_sheet.jpg")
        c = rep["checks"]
        if rep["passed"]:
            break
        fixed = False
        if not (c["loudness_-14_lufs"] and c["true_peak_le_-1_dbfs"]):
            lu = rep["loudness"]["integrated_lufs"] or -14
            adj = work / f"{cid}_master_adj.wav"
            run(["ffmpeg", "-y", "-v", "error", "-i", master, "-af",
                 f"volume={-14 - lu:.2f}dB,alimiter=limit=0.8:level=disabled", "-c:a", "pcm_s24le", adj])
            mux(vid, adj, out, tl["duration"])
            repairs.append(f"loudness re-mastered ({lu:.1f} LUFS → -14)")
            rep = qc_clip(out, tl, tr["words"], dirs["QC"] / f"{cid}_contact_sheet.jpg")
            if rep["passed"]:
                break
            c = rep["checks"]
        if not c["captions_clear_of_faces"] and tl["layout"]["mode"] == "track":
            tl["caption_y"] = 1470 if tl["caption_y"] < 1400 else 1180
            repairs.append(f"captions moved to y={tl['caption_y']} (were over a face)")
            fixed = True
        if not c["no_faces_cut_at_edges"] and any(z["amount"] > 0.05 for z in tl["zooms"]):
            for z in tl["zooms"]:
                z["amount"] = round(z["amount"] * 0.5, 3)
            for s in tl["segments"]:
                s["base_zoom"] = round(1 + (s["base_zoom"] - 1) * 0.5, 3)
            repairs.append("zoom intensity halved (face clipped at frame edge)")
            fixed = True
        if not fixed:
            break
        tl["version"] += 1
        tl_path.write_text(json.dumps(tl, indent=2, ensure_ascii=False))
        log(f"{cid}: QC repair → re-render v{tl['version']}: {repairs[-1]}")
    rep["repairs"] = repairs
    rep["render_seconds"] = round(time.time() - t0, 1)
    rep["clip"] = cid
    # cover from clean (caption-free) frames
    from .package import make_cover, pick_cover_frame
    fr = pick_cover_frame(work / "cover_frames")
    if fr is not None:
        accent = next((g["color"] for g in tl["graphics"] if g["type"] == "progress_bar"), "#FF2B1C")
        make_cover(fr, tl["package"].get("cover_text") or tl["package"]["title"], accent,
                   dirs["Covers"] / f"NPC_COVER_{cid[-2:]}.png")
    status = "PASS" if rep["passed"] else "FAIL: " + ", ".join(k for k, v in rep["checks"].items() if not v)
    log(f"{cid}: {status}  ({rep['render_seconds']}s)")
    return rep


def safe_render_clip(root: str, tl_path: str) -> dict:
    """A failure in one clip is reported, never allowed to sink the batch."""
    import traceback
    try:
        return render_clip(root, tl_path)
    except Exception as e:  # noqa: BLE001
        cid = Path(tl_path).stem
        log(f"{cid}: RENDER ERROR {type(e).__name__}: {e}")
        return {"clip": cid, "passed": False, "error": f"{type(e).__name__}: {e}",
                "traceback": traceback.format_exc()[-3000:], "checks": {}, "repairs": []}


def render_all(root: Path, tl_paths: list[Path], jobs: int) -> list[dict]:
    if jobs <= 1 or len(tl_paths) == 1:
        return [safe_render_clip(str(root), str(p)) for p in tl_paths]
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        return list(ex.map(safe_render_clip, [str(root)] * len(tl_paths), [str(p) for p in tl_paths]))


def finalize(root: Path, reports: list[dict]) -> Path:
    from .package import make_zip, register, write_metadata
    dirs = project_dirs(root)
    meta = read_json(dirs["Source"] / "source_metadata.json")
    tls = [json.loads(p.read_text()) for p in sorted(dirs["timelines"].glob("NPC_CLIP_*.json"))]
    tls = [t for t in tls if (dirs["Clips"] / f"{t['clip_id']}.mp4").exists()]
    old = {r["clip"]: r for r in (read_json(dirs["Metadata"] / "quality_report.json", {}) or {}).get("clips", [])}
    old.update({r["clip"]: r for r in reports})
    write_metadata(dirs, meta, tls, [old[k] for k in sorted(old)])
    register(dirs, meta, tls)
    return make_zip(dirs, tls)


# ───────────────────────── full pipeline for one source ─────────────────────────

def process_source(inp: str, a) -> dict:
    from .analyze import analyze
    from .ingest import CLEARED, SourceBlocked, ingest, name_for
    from .plan import plan_clip
    from .select import from_selection, select
    from .transcribe import transcribe
    name = a.name or name_for(inp)
    root = OUTPUT_ROOT / name
    dirs = project_dirs(root)
    meta = ingest(inp, dirs, a.rights, a.rights_note or "", a.source_name)
    src = meta["media_path"]
    tr = transcribe(Path(src), dirs, force=a.force)
    fixes = load_corrections(root)
    fixes.update({k.strip().lower(): v.strip() for k, v in (x.split("=", 1) for x in a.fix_word if "=" in x)})
    if fixes:
        write_json(dirs["Project"] / "caption_corrections.json", fixes)
        for w in tr["words"]:
            w["w"] = correct_word(w["w"], fixes)
        for s in tr["sentences"]:
            s["text"] = " ".join(w["w"] for w in tr["words"][s["wi"][0]: s["wi"][1] + 1])
    if len(tr["words"]) < 30:
        raise SourceBlocked("too little speech detected for transcript-driven clipping")
    ana = analyze(src, meta["video"], dirs, force=a.force)
    ft = read_json(dirs["Analysis"] / "face_tracks.json")
    prior = read_json(REGISTRY / "insights.json", {}).get("preferred_duration_s", 35.0)
    if a.selection:
        chosen, ctype = from_selection(json.loads(Path(a.selection).read_text()), tr, ana, ft["samples"], dirs,
                                       meta.get("creator"), prior, a.niche)
    else:
        chosen, ctype = select(tr, ana, ft["samples"], dirs, a.clips, meta.get("creator"), prior, a.niche)
    write_json(dirs["Analysis"] / "selected_clips.json", [{k: v for k, v in c.items()} for c in chosen])

    rights = meta["rights"]["classification"]
    if rights == "UNKNOWN":
        log("RIGHTS GATE: source rights are UNKNOWN — analysis and candidate scores are saved, nothing rendered.")
        log("Re-run with --rights mine|licensed|authorized|fair-use (fair-use needs commentary per clip).")
        return {"project": str(root), "rendered": 0, "blocked": "rights unknown"}
    if a.analyze_only:
        return {"project": str(root), "rendered": 0, "blocked": "analyze-only"}

    for old in dirs["timelines"].glob("NPC_CLIP_*.json"):
        old.unlink()
    opts = {"style": None if a.style in ("viral-pro", "auto") else a.style, "brand": a.brand}
    tl_paths, flagged = [], []
    for i, c in enumerate(chosen):
        tl = plan_clip(i, c, tr, ana, ft["samples"], meta["video"], meta, ctype, opts)
        if rights == "FAIR-USE CANDIDATE" and not c["package"].get("commentary"):
            flagged.append(tl["clip_id"])
            continue
        p = dirs["timelines"] / f"{tl['clip_id']}.json"
        write_json(p, tl)
        tl_paths.append(p)
    if flagged:
        log(f"RIGHTS GATE: {len(flagged)} fair-use clip(s) lack an original commentary layer and were NOT rendered: "
            f"{', '.join(flagged)}. Add \"commentary\" per clip in a --selection file.")
    write_json(dirs["Project"] / "editing_config.json", {
        "engine": "npc-clip 1.0", "niche": a.niche or "auto", "content_type": ctype, "style_arg": a.style, "brand": a.brand,
        "platform": a.platform, "clips_requested": a.clips, "clips_planned": len(tl_paths),
        "export": {"resolution": "1080x1920", "fps": FPS, "video": "H.264 High, CRF 18, yuv420p, bt709 tv-range",
                   "audio": "AAC 192k 48 kHz stereo, -14 LUFS, true peak ≤ -1.5 dBTP"},
        "rights": meta["rights"], "fair_use_flagged": flagged,
        "rerender": f"npc-clip render --project {root}",
    })
    for old in list(dirs["Clips"].glob("NPC_CLIP_*.mp4")) + list(dirs["Covers"].glob("NPC_COVER_*.png")):
        old.unlink()
    reports = render_all(root, tl_paths, a.jobs)
    zp = finalize(root, reports)
    ok = sum(r["passed"] for r in reports)
    log(f"DONE {root.name}: {len(reports)} clips rendered, {ok} passed QC → {zp}")
    return {"project": str(root), "rendered": len(reports), "passed": ok, "zip": str(zp)}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    sub = argv[0] if argv and argv[0] in ("render", "feedback", "styles", "run") else "run"
    if argv and argv[0] == sub:
        argv = argv[1:]
    if sub == "styles":
        from .captions import STYLES
        for k, v in STYLES.items():
            print(f"{k:22s} {v['name']:22s} {v['font']:26s} anim={v['animation']:8s} density={v['density']}")
        return 0
    if sub == "feedback":
        ap = argparse.ArgumentParser(prog="npc-clip feedback")
        ap.add_argument("--stats", required=True)
        a = ap.parse_args(argv)
        from .feedback import ingest_stats
        r = ingest_stats(a.stats)
        print(json.dumps(r["by"], indent=2)[:4000])
        return 0
    if sub == "render":
        ap = argparse.ArgumentParser(prog="npc-clip render")
        ap.add_argument("--project", required=True)
        ap.add_argument("--clip", type=int, action="append")
        ap.add_argument("--jobs", type=int, default=2)
        ap.add_argument("--fix-word", action="append", default=[], metavar="WRONG=RIGHT")
        a = ap.parse_args(argv)
        root = Path(a.project).resolve()
        dirs = project_dirs(root)
        if a.fix_word:
            fixes = load_corrections(root)
            fixes.update({k.strip().lower(): v.strip() for k, v in (x.split("=", 1) for x in a.fix_word if "=" in x)})
            write_json(dirs["Project"] / "caption_corrections.json", fixes)
            for p in dirs["timelines"].glob("NPC_CLIP_*.json"):
                tl = json.loads(p.read_text())
                pk = tl["package"]
                for k in ("title", "hook", "post_caption", "cover_text"):
                    if pk.get(k):
                        pk[k] = " ".join(correct_word(w, fixes) for w in pk[k].split())
                p.write_text(json.dumps(tl, indent=2, ensure_ascii=False))
        paths = sorted(dirs["timelines"].glob("NPC_CLIP_*.json"))
        if a.clip:
            paths = [p for p in paths if int(p.stem[-2:]) in a.clip]
        reports = render_all(root, paths, a.jobs)
        log(f"re-rendered {len(reports)} clip(s); package → {finalize(root, reports)}")
        return 0
    ap = argparse.ArgumentParser(prog="npc-clip", description="NPC VIRAL STUDIO clipping pipeline")
    ap.add_argument("--input", required=True, help="YouTube/URL, video file, or folder of videos")
    ap.add_argument("--clips", type=int, default=12)
    ap.add_argument("--platform", default="all", help="all|tiktok|shorts|reels|facebook (one master fits all)")
    ap.add_argument("--niche", help="YOUR niche: business|podcast|comedy|motivation|education|gaming|interview|"
                                     "debate|… (drives editing style, music and hashtags; free text allowed)")
    ap.add_argument("--style", default="viral-pro", help="viral-pro (auto per content) or a caption preset key")
    ap.add_argument("--rights", default="unknown", help="mine|licensed|authorized|fair-use|unknown")
    ap.add_argument("--rights-note", default="", help="license / permission details recorded in metadata")
    ap.add_argument("--source-name", help="display name / creator credit override")
    ap.add_argument("--name", help="project folder name")
    ap.add_argument("--selection", help="JSON list of {start,end,title,hook,post_caption,hashtags,commentary,…}")
    ap.add_argument("--fix-word", action="append", default=[], metavar="WRONG=RIGHT",
                    help="correct an ASR spelling in captions/titles (repeatable; saved to the project)")
    ap.add_argument("--brand", action="store_true", help="add the NPC watermark (only on cleared sources)")
    ap.add_argument("--jobs", type=int, default=2, help="clips rendered in parallel")
    ap.add_argument("--analyze-only", action="store_true")
    ap.add_argument("--force", action="store_true", help="redo transcription/analysis")
    a = ap.parse_args(argv)
    from .ingest import SourceBlocked, expand_inputs
    try:
        inputs = expand_inputs(a.input)
    except SourceBlocked as e:
        log(f"BLOCKED: {e}")
        return 2
    results = []
    for inp in inputs:
        try:
            results.append(process_source(inp, a))
        except SourceBlocked as e:
            log(f"BLOCKED ({inp}): {e}")
            results.append({"input": inp, "blocked": str(e)})
    print(json.dumps(results, indent=2))
    return 0 if all("blocked" not in r for r in results) else 3


if __name__ == "__main__":
    sys.exit(main())
