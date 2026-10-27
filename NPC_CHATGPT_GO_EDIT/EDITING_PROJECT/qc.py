"""Quality assurance for the finished export.

    python qc.py FINAL.mp4 PRIVATE_DIR OUT_JSON [--workers 4]

Checks: specs, frame count vs timeline, decode errors, black / frozen stretches, loudness and
true peak, and a privacy scan that OCRs EVERY frame of the export. Privacy flags: e-mail
addresses, phone numbers, IPv4 addresses, promo-code-like tokens, 'promoCode=' values, private
values collected by privacy.py, a readable 'Felicitaciones ...' line, or any text line directly
under 'Bienvenido' (where the account name sits). Only timestamps are reported, never text.
"""
import argparse
import json
import re
import subprocess
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from privacy import EMAIL_RE, IP_RE, PHONE_RE, codelike


def norm(s):
    return re.sub(r"\s+", " ", s.strip().lower())


def flags_for(res, terms):
    fl = set()
    boxes = [([min(p[0] for p in q), min(p[1] for p in q), max(p[0] for p in q), max(p[1] for p in q)], tx)
             for q, tx, _ in (res or [])]
    for (x0, y0, x1, y1), tx in boxes:
        n = norm(tx)
        if "hidden" in n:
            continue
        if EMAIL_RE.search(n) or "gmail" in n or PHONE_RE.search(tx):
            fl.add("email/phone")
        if IP_RE.search(n) or ("ipaddress" in n.replace(" ", "") and re.search(r"\d+\.\d+", n)):
            fl.add("ip")
        if codelike(tx) or re.search(r"(?:[?&]promocode=?|promocode=)[a-z0-9]{4,}", n.replace(" ", "")):
            fl.add("code")
        if "felicitaciones" in n:
            fl.add("name")
        if n.startswith("bienvenido"):
            for (bx0, by0, bx1, by1), btx in boxes:
                if (0 <= by0 - y1 <= 140 and bx1 > x0 - 40 and bx0 < x1 + 40 and "hidden" not in btx.lower()
                        and len(btx.strip()) <= 14):  # the name line is short; the sentence under it is not
                    fl.add("name")
        if any(re.search(r"(?<![0-9a-z])" + re.escape(t) + r"(?![0-9a-z])", n) for t in terms):
            fl.add("private-value")
    return sorted(fl)


def scan_chunk(args):
    path, w, h, a, b, terms = args
    from rapidocr_onnxruntime import RapidOCR
    ocr = RapidOCR(intra_op_num_threads=1, inter_op_num_threads=1)
    sw, sh = w * 6 // 10 // 2 * 2, h * 6 // 10 // 2 * 2
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-vf", f"scale={sw}:{sh}", "-f", "rawvideo",
                          "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    hits, f, n = [], 0, 0
    while f < b:
        buf = p.stdout.read(sw * sh * 3)
        if len(buf) < sw * sh * 3:
            break
        if f >= a:
            res, _ = ocr(np.frombuffer(buf, np.uint8).reshape(sh, sw, 3))
            fl = flags_for(res, terms)
            if fl:
                hits.append([f, fl])
            n += 1
        f += 1
    p.kill()
    return n, hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("private_dir")
    ap.add_argument("out")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    info = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-count_frames", "-show_entries",
                                               "stream=codec_type,codec_name,width,height,r_frame_rate,pix_fmt,sample_rate,channels,duration,nb_read_frames",
                                               "-of", "json", a.video]))
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    au = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    rep = {"file": Path(a.video).name,
           "video": {k: v.get(k) for k in ("codec_name", "width", "height", "r_frame_rate", "pix_fmt", "nb_read_frames", "duration")},
           "audio": au and {k: au.get(k) for k in ("codec_name", "sample_rate", "channels", "duration")}}
    from timeline import Timeline
    tl = Timeline()
    rep["frames_expected"] = len(tl.frames)
    rep["frame_count_ok"] = int(v["nb_read_frames"]) == len(tl.frames)
    rep["av_duration_delta_s"] = au and round(abs(float(v["duration"]) - float(au["duration"])), 3)
    rep["decode_errors"] = subprocess.run(["ffmpeg", "-v", "error", "-i", a.video, "-f", "null", "-"],
                                          capture_output=True, text=True).stderr.strip().splitlines()[:5]
    bl = subprocess.run(["ffmpeg", "-i", a.video, "-vf", "blackdetect=d=0.1:pix_th=0.06", "-an", "-f", "null", "-"],
                        capture_output=True, text=True).stderr
    rep["black_segments"] = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", bl)
    fz = subprocess.run(["ffmpeg", "-i", a.video, "-vf", "freezedetect=n=0.001:d=1.0", "-an", "-f", "null", "-"],
                        capture_output=True, text=True).stderr
    rep["frozen_segments"] = list(zip(re.findall(r"freeze_start: ([\d.]+)", fz), re.findall(r"freeze_end: ([\d.]+)", fz)))
    ld = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", a.video, "-af", "ebur128=peak=true", "-vn", "-f", "null", "-"],
                        capture_output=True, text=True).stderr.split("Summary:")[-1]
    m = re.search(r"I:\s+(-?[\d.]+) LUFS", ld)
    pk = re.search(r"Peak:\s+(-?[\d.]+) dBFS", ld.split("True peak:")[-1])
    rep["loudness_lufs"] = m and float(m.group(1))
    rep["true_peak_dbtp"] = pk and float(pk.group(1))
    terms = [t for t in json.loads((Path(a.private_dir) / "private_terms.json").read_text())
             if len(re.sub(r"[^0-9a-z]", "", t)) >= 3]
    n = int(v["nb_read_frames"])
    w, h = int(v["width"]), int(v["height"])
    with Pool(a.workers) as pool:
        res = pool.map(scan_chunk, [(a.video, w, h, n * i // a.workers, n * (i + 1) // a.workers, terms)
                                     for i in range(a.workers)])
    fps = eval(v["r_frame_rate"])
    hits = [[round(f / fps, 2), fl] for r in res for f, fl in r[1]]
    rep["privacy_scan"] = {"mode": "every frame", "frames_scanned": sum(r[0] for r in res), "frames_total": n,
                           "private_terms_checked": len(terms), "hits": hits}
    rep["privacy_pass"] = rep["privacy_scan"]["frames_scanned"] == n and not hits
    Path(a.out).write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: rep[k] for k in rep if k != "privacy_scan"}, indent=1))
    print("privacy pass:", rep["privacy_pass"], "| scanned", rep["privacy_scan"]["frames_scanned"], "/", n,
          "| hits", len(hits), sorted({h[0] for h in hits})[:40])


if __name__ == "__main__":
    main()
