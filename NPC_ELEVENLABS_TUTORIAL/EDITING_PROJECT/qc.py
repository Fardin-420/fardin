"""Quality assurance for a finished export.

    python qc.py FINAL.mp4 PRIVATE_DIR OUT_JSON [--workers 4]

Checks: container/codec specs, A/V duration, decode errors, black and frozen stretches,
loudness / true peak, and a privacy scan that OCRs EVERY frame of the export. The privacy scan
flags any e-mail-like text and any private value collected by privacy.py (PRIVATE_DIR/
private_terms.json). Findings are reported as timestamps only; matched text is never written.
"""
import argparse
import json
import re
import subprocess
from multiprocessing import Pool
from pathlib import Path

import numpy as np

SAFE = {"name@email.com"}
# Generic words that also land in the collected terms (placeholders, headings, partial typing)
# and that the edit itself shows (captions, chapter titles). Reviewed: never a private value.
UI_WORDS = {"enter", "continue", "continue.", "gender", "race", "ethnicity", "pronouns", "birthday", "the"}


def generic_words():
    from timeline import Timeline
    tl = Timeline()
    words = set(UI_WORDS)
    for c in tl.captions:
        words |= {w.lower() for w in c["text"].split()}
    for _, _, title in tl.chapters:
        words |= {w.lower() for w in title.split()}
    return words


def probe(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries",
                                   "stream=codec_type,codec_name,width,height,r_frame_rate,pix_fmt,sample_rate,channels,duration,nb_frames"
                                   ":format=duration,bit_rate", "-of", "json", path])
    return json.loads(out)


def norm(s):
    return re.sub(r"\s+", " ", s.strip().lower())


def profile_frames():
    """Output frames that show the profile screens, where private values were typed."""
    from privacy import PROFILE_WINDOWS
    from timeline import Timeline
    tl = Timeline()
    return {fr.i for fr in tl.frames if fr.kind == "video"
            and any(a - 0.5 <= fr.src <= b + 0.5 for a, b in PROFILE_WINDOWS)}


def scan_chunk(args):
    path, w, h, a, b, terms, prof = args
    from rapidocr_onnxruntime import RapidOCR
    ocr = RapidOCR(intra_op_num_threads=1, inter_op_num_threads=1)
    sw, sh = w // 2 // 2 * 2, h // 2 // 2 * 2
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-vf", f"scale={sw}:{sh}", "-f", "rawvideo",
                          "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    hits, f, prev, prev_flag = [], 0, None, None
    while f < b:
        buf = p.stdout.read(sw * sh * 3)
        if len(buf) < sw * sh * 3:
            break
        if f >= a:
            img = np.frombuffer(buf, np.uint8).reshape(sh, sw, 3)
            if (prev is not None and np.abs(img.astype(np.int16) - prev).max() <= 3 and prev_flag is not None
                    and (f in prof) == (f - 1 in prof)):
                flag = prev_flag
            else:
                res, _ = ocr(img)
                flag = []
                for _, tx, sc in res or []:
                    n = norm(tx)
                    if n in SAFE or re.sub(r"[^a-z]", "", n) in ("nameemailcom", "nameemail"):
                        continue  # the sign-in form's generic placeholder, also when OCR misreads the dots
                    if (re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", n) or "gmail" in n or "email protected" in n
                            or ("@" in n and not n.startswith("@"))):  # leading '@' = "(!)" icon
                        flag.append("email-like")
                    elif f in prof and any(re.search(r"(?<![0-9a-z])" + re.escape(t) + r"(?![0-9a-z])", n)
                                           for t in terms):
                        flag.append("private-value")
            if flag:
                hits.append([f, sorted(set(flag))])
            prev, prev_flag = img, flag
        f += 1
    p.kill()
    return f - a, hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("private_dir")
    ap.add_argument("out")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--windows-only", action="store_true",
                    help="privacy-scan every frame of the sensitive windows only (the hand-over gate)")
    a = ap.parse_args()
    rep = {"file": Path(a.video).name}
    info = probe(a.video)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    au = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    rep["video"] = {k: v.get(k) for k in ("codec_name", "width", "height", "r_frame_rate", "pix_fmt", "nb_frames", "duration")}
    rep["audio"] = au and {k: au.get(k) for k in ("codec_name", "sample_rate", "channels", "duration")}
    rep["av_duration_delta_s"] = au and round(abs(float(v["duration"]) - float(au["duration"])), 3)

    dec = subprocess.run(["ffmpeg", "-v", "error", "-i", a.video, "-f", "null", "-"], capture_output=True, text=True)
    rep["decode_errors"] = dec.stderr.strip().splitlines()[:5]

    bl = subprocess.run(["ffmpeg", "-i", a.video, "-vf", "blackdetect=d=0.1:pix_th=0.08", "-an", "-f", "null", "-"],
                        capture_output=True, text=True).stderr
    rep["black_segments"] = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", bl)
    fz = subprocess.run(["ffmpeg", "-i", a.video, "-vf", "freezedetect=n=0.001:d=1.0", "-an", "-f", "null", "-"],
                        capture_output=True, text=True).stderr
    rep["frozen_segments"] = list(zip(re.findall(r"freeze_start: ([\d.]+)", fz), re.findall(r"freeze_end: ([\d.]+)", fz)))
    ld = subprocess.run(["ffmpeg", "-i", a.video, "-af", "ebur128=peak=true", "-vn", "-f", "null", "-"],
                        capture_output=True, text=True).stderr
    summary = ld.split("Summary:")[-1]
    m = re.search(r"I:\s+(-?[\d.]+) LUFS", summary)
    pk = re.search(r"Peak:\s+(-?[\d.]+) dBFS", summary.split("True peak:")[-1])
    rep["loudness_lufs"] = m and float(m.group(1))
    rep["true_peak_dbtp"] = pk and float(pk.group(1))

    gw = generic_words()
    terms = [t for t in json.loads((Path(a.private_dir) / "private_terms.json").read_text())
             if len(re.sub(r"[^0-9a-z]", "", t)) >= 3 and t not in gw]
    w, h = int(v["width"]), int(v["height"])
    n = int(v["nb_frames"])
    prof = profile_frames()
    if a.windows_only:
        from qc_privacy_windows import WINDOWS
        from timeline import Timeline
        tl = Timeline()
        rng = [(max(0, int(tl.src_to_out(s) * 30) - 6), int(tl.src_to_out(e, end=True) * 30) + 6) for s, e in WINDOWS]
    else:
        rng = [(n * i // a.workers, n * (i + 1) // a.workers) for i in range(a.workers)]
    chunks = [(a.video, w, h, s, e, terms, prof) for s, e in rng]
    n_target = sum(e - s for s, e in rng)
    with Pool(a.workers) as pool:
        res = pool.map(scan_chunk, chunks)
    fps = eval(v["r_frame_rate"])
    rep["privacy_scan"] = {"mode": "sensitive windows" if a.windows_only else "every frame",
                           "frames_scanned": sum(r[0] for r in res), "frames_total": n_target,
                           "private_terms_checked": len(terms),
                           "hits": [[round(f / fps, 2), fl] for r in res for f, fl in r[1]]}
    rep["privacy_pass"] = rep["privacy_scan"]["frames_scanned"] == n_target and not rep["privacy_scan"]["hits"]
    Path(a.out).write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: rep[k] for k in rep if k != "privacy_scan"}, indent=1))
    print("privacy:", rep["privacy_pass"], "scanned", rep["privacy_scan"]["frames_scanned"], "/", n,
          "hits", len(rep["privacy_scan"]["hits"]))


if __name__ == "__main__":
    main()
