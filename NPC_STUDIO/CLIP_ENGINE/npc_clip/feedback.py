"""Performance feedback: join real platform stats to the clip registry and compare by editing decisions.

CSV columns (any subset beyond project/clip): project, clip, platform, views, viewed_vs_swiped, avg_view_duration_s,
completion_rate, replays, shares, comments, follows. Nothing is invented: missing metrics stay missing.
"""
from __future__ import annotations

import csv
from collections import defaultdict

import numpy as np

from .common import REGISTRY, log, read_json, write_json

METRICS = ["views", "viewed_vs_swiped", "avg_view_duration_s", "completion_rate", "replays", "shares",
           "comments", "follows"]
DIMS = ["hook_type", "duration_bucket", "content_type", "caption_style", "density", "creator", "platform", "layout"]


def ingest_stats(csv_path: str) -> dict:
    reg = {(r["project"], r["clip"]): r for r in read_json(REGISTRY / "clips_registry.json", [])}
    rows, unmatched = [], []
    with open(csv_path) as f:
        for r in csv.DictReader(f):
            key = (r.get("project", ""), r.get("clip", ""))
            base = reg.get(key)
            if not base:
                unmatched.append(key)
                continue
            row = dict(base)
            row["platform"] = r.get("platform") or "unknown"
            d = base["duration"]
            row["duration_bucket"] = "<25s" if d < 25 else "25-40s" if d < 40 else "40s+"
            for m in METRICS:
                v = (r.get(m) or "").replace(",", "").replace("%", "").strip()
                row[m] = float(v) if v else None
            rows.append(row)
    hist_p = REGISTRY / "performance_history.json"
    hist = read_json(hist_p, [])
    hist = [h for h in hist if (h["project"], h["clip"], h["platform"]) not in
            {(r["project"], r["clip"], r["platform"]) for r in rows}] + rows
    write_json(hist_p, hist)
    report = {"rows": len(hist), "unmatched": [list(u) for u in unmatched], "by": {}}
    for dim in DIMS:
        groups = defaultdict(list)
        for r in hist:
            groups[str(r.get(dim))].append(r)
        report["by"][dim] = {
            g: {"n": len(rs), **{m: round(float(np.mean([x[m] for x in rs if x.get(m) is not None])), 3)
                                 for m in METRICS if any(x.get(m) is not None for x in rs)}}
            for g, rs in groups.items()}
    # learned prior used by selection: duration with the best completion (needs ≥ 5 clips)
    insights = read_json(REGISTRY / "insights.json", {})
    scored = [r for r in hist if r.get("completion_rate") is not None]
    if len(scored) >= 5:
        w = np.array([r["completion_rate"] for r in scored])
        d = np.array([r["duration"] for r in scored])
        insights["preferred_duration_s"] = round(float(np.clip((w * d).sum() / w.sum(), 20, 50)), 1)
        insights["based_on_clips"] = len(scored)
    write_json(REGISTRY / "insights.json", insights)
    write_json(REGISTRY / "performance_report.json", report)
    log(f"feedback: {len(rows)} rows matched, {len(unmatched)} unmatched → {REGISTRY / 'performance_report.json'}")
    return report
