"""Fast privacy gate: OCR EVERY output frame inside the sensitive windows (+-0.2 s).

    python qc_privacy_windows.py FINAL.mp4 PRIVATE_DIR

All private data in this recording lives in these windows (sign-in autofill, profile answers,
birthday, OAuth account screen), so this is the gate run before a file is handed over;
qc.py adds the whole-video scan. Prints timestamps of hits only, never text.
"""
import json
import re
import sys
from multiprocessing import Pool
from pathlib import Path

from qc import generic_words, profile_frames, scan_chunk
from timeline import Timeline

WINDOWS = [(0, 3.3), (17.5, 30.6), (59.5, 69.6), (98.5, 103.0)]

if __name__ == "__main__":
    video, priv = sys.argv[1], Path(sys.argv[2])
    tl = Timeline()
    w, h = (1080, 1920) if "9x16" in video else (1920, 1080)
    rng = [(max(0, int(tl.src_to_out(a) * 30) - 6), int(tl.src_to_out(b, end=True) * 30) + 6) for a, b in WINDOWS]
    gw = generic_words()
    terms = [t for t in json.loads((priv / "private_terms.json").read_text())
             if len(re.sub(r"[^0-9a-z]", "", t)) >= 3 and t not in gw]
    prof = profile_frames()
    with Pool(4) as p:
        res = p.map(scan_chunk, [(video, w, h, a, b, terms, prof) for a, b in rng])
    hits = [[round(f / 30, 2), fl] for r in res for f, fl in r[1]]
    print(Path(video).name, "frames scanned", sum(r[0] for r in res), "of", sum(b - a for a, b in rng), "hits", hits)
