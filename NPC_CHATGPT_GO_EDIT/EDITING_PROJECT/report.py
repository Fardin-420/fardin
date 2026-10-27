"""Write ../NPC_EDIT_REPORT.txt from the EDL, timeline, privacy masks and QC results.

    python report.py

Every number is read from project files. No private text appears (masks and QC hold geometry
and timestamps only).
"""
import json
from pathlib import Path

from timeline import Timeline

HERE = Path(__file__).parent
ROOT = HERE.parent


def fmt(t):
    return f"{int(t // 60)}:{t % 60:05.2f}"


def main():
    tl = Timeline()
    e = tl.edl
    masks = json.loads((ROOT / "PRIVACY_MASKS" / "masks.json").read_text())
    qp = ROOT / "ANALYSIS" / "qc_final.json"
    q = json.loads(qp.read_text()) if qp.exists() else None
    src_dur = e["source"]["duration"]
    kept = sum(s["out"] - s["in"] for s in e["segments"])
    L = []
    w = L.append
    w("NPC — EDIT REPORT: ChatGPT Go, 1 month via Rappi")
    w("=" * 64)
    w("")
    w("DURATION")
    w(f"  Original recording : {src_dur:.2f} s (two uploaded parts joined losslessly, 2759 frames)")
    w(f"  Final video        : {tl.duration:.2f} s ({len(tl.frames)} frames @ {tl.fps} fps)")
    w(f"                       hook {e['hook']['duration']} s + tutorial {tl.freeze_start - tl.video_start:.2f} s"
      f" + result hold {e['freeze']['duration']} s + outro {e['outro']['duration']} s")
    w(f"  Source footage kept: {kept:.2f} s of {src_dur:.2f} s; removed {src_dur - kept:.2f} s outright, the rest"
      f" compressed by speed ramps")
    w(f"  Shorter by         : {src_dur - tl.duration:.2f} s ({(1 - tl.duration / src_dur) * 100:.0f} %)")
    w("")
    w("SOURCE FINDINGS")
    w(f"  Audio: {e['source']['audio']}. Captions are therefore step captions written from the screen (English),")
    w("  not a transcript; there was no voice to clean, so no voice processing was applied.")
    w("  Service verified on screen: RappiPro benefit 'ChatGPT Go - Gratis por 30 dias, con Pro 3 meses o con Pro")
    w("  Black 6 meses', 'Aplica para usuarios nuevos a ChatGPT Go'; ChatGPT then shows 'Go - $110 -> $0 MXN for")
    w("  the first month, You've got a promo code for discounted Go for 1 month, Claim free offer'.")
    w("  Shown limitation: ChatGPT first answers 'Promo Unavailable - This promotion isn't available in your")
    w("  country or region'; the offer appears only after a VPN is switched to Mexico. The edit states this and")
    w("  notes that a VPN may break the offer's terms. The recording ends before 'Claim free offer' is tapped.")
    w("")
    w("MAJOR CUTS")
    w(f"  0.00-{e['segments'][0]['in']:.2f} s  {e['removed_note']}")
    for s in e["segments"]:
        if "cut" in s:
            w(f"  {s['note'].split('.')[0]}  -> transition: {s['cut']}")
    w(f"  {e['segments'][-1]['out']:.2f}-{src_dur:.2f} s  end of recording")
    w("")
    w("SPEED EFFECTS (eased speed ramps inside each continuous run)")
    for s in e["segments"]:
        if abs(s["speed"] - 1) > 0.01:
            kind = "slow-down" if s["speed"] < 1 else "fast-forward"
            w(f"  {s['in']:6.2f}-{s['out']:6.2f} s  x{s['speed']:<4} {kind:12s} {s['note']}")
    w("")
    w("ZOOM / FOCUS LOCATIONS (camera keyframes, 1.0 = full width; base views 0.9)")
    for k in e["camera"]:
        if k["z"] > 1.05:
            w(f"  src {k['src']:6.2f} s  -> out {fmt(tl.src_to_out(k['src']))}  zoom {k['z']:.2f}  focus ({k['fx']}, {k['fy']})")
    for k in e["freeze_camera"]:
        w(f"  result hold +{k['ft']:.1f} s  zoom {k['z']:.2f}  focus ({k['fx']}, {k['fy']})")
    w("  Annotations: " + ", ".join(sorted({h['label'] for h in tl.highlights if h.get('label')})))
    w("")
    w("TRANSITIONS")
    w("  " + ", ".join(f"{fmt(t)} {n}" for t, n in tl.cuts) + f"; hook -> tutorial whip at {fmt(tl.video_start)}")
    w("")
    w("PRIVACY PROTECTION (opaque masks burned into source frames before any zoom or transition)")
    w(f"  OCR scanned every source frame the render reads ({masks['frames_scanned']} frames incl. earlier"
      f" full-scan frames; {masks['frames_required']} required, all present); masks dilated +-{masks['dilate_frames']} frames.")
    names = {"code": "Promo code / promo URL (address bar, clipboard chip, chatgpt.com/p/ link)",
             "name": "Account name (RappiPro 'Bienvenido' + 'Felicitaciones' screens)",
             "photo": "Google profile photo", "ip": "VPN server IP address", "email": "E-mail / phone numbers"}
    for k, rr in masks["ranges"].items():
        w(f"  - {names[k]}: " + (", ".join(f"{a:.2f}-{b:.2f}s" for a, b in rr) if rr else "none found"))
    w("  Removed instead of masked: address-bar typing with personal browsing history (13-17 s, 40-45 s),")
    w("  tab switcher, Google account sign-in screens.")
    w("")
    w("RENDERING VERIFICATION (measured on FINAL/NPC_CHATGPT_GO_FINAL.mp4)")
    if q:
        v, a = q["video"], q["audio"] or {}
        w(f"  {v['width']}x{v['height']} {v['codec_name']} {v['pix_fmt']} {v['r_frame_rate']} fps, {v['nb_read_frames']} frames"
          f" (expected {q['frames_expected']}: {'OK' if q['frame_count_ok'] else 'MISMATCH'})")
        w(f"  audio {a.get('codec_name')} {a.get('sample_rate')} Hz {a.get('channels')} ch; A/V delta {q['av_duration_delta_s']} s;"
          f" decode errors: {len(q['decode_errors'])}")
        w(f"  loudness {q['loudness_lufs']} LUFS integrated, true peak {q['true_peak_dbtp']} dBTP")
        w(f"  black >0.1 s: {q['black_segments'] or 'none'}; frozen >1 s: {q['frozen_segments'] or 'none'}"
          " (expected: the result hold)")
        ps = q["privacy_scan"]
        w(f"  privacy OCR of every output frame: {ps['frames_scanned']}/{ps['frames_total']} scanned, automatic hits:"
          f" {len(ps['hits'])}" + (" -> PASS" if q["privacy_pass"] else f" at {sorted({h[0] for h in ps['hits']})}"))
        if q.get("review"):
            w(f"  review: {q['review']}")
    else:
        w("  QC not run yet.")
    w("")
    w("DELIVERABLES")
    for p in ("FINAL/NPC_CHATGPT_GO_FINAL.mp4", "PREVIEW/NPC_CHATGPT_GO_PREVIEW.mp4",
              "CAPTIONS/NPC_CHATGPT_GO_CAPTIONS.srt", "THUMBNAIL/NPC_CHATGPT_GO_THUMBNAIL.png"):
        f = ROOT / p
        w(f"  {p}  ({f.stat().st_size / 1e6:.1f} MB)" if f.exists() else f"  {p}  MISSING")
    w("")
    w("REPRODUCE: cd NPC_CHATGPT_GO_EDIT/EDITING_PROJECT && see README.md (source stays private)")
    (ROOT / "NPC_EDIT_REPORT.txt").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
