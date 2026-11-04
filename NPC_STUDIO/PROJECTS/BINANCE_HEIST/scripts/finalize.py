"""Concatenate rendered chunks, mux the mastered mix, and encode the deliverables.

    .venv/bin/python scripts/finalize.py

out/master_1080p.mp4   H.264 High (CRF 16 from Remotion, stream-copied) + AAC 48 kHz 320 kbps
out/upload_1080p.mp4   CRF 17 H.264 (≤12 Mbps) + the master AAC (copied), +faststart
out/preview_coldopen.mp4  0:00–1:00 with audio
"""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
CH = OUT / "chunks"
AUDIO = ROOT / "audio" / "mix_master.wav"


def run(*a):
    print("$", " ".join(map(str, a)))
    subprocess.run(list(map(str, a)), check=True)


CHUNK_START = {1: 0, 2: 1800, 3: 13000, 4: 19000}


def nframes(p: Path) -> int:
    return int(subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
                               "stream=nb_read_packets", "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout)


def apply_patches():
    """Splice re-rendered windows (out/chunks/patches/p<start>_<end>.mp4, global frames) into the chunks.

    Patches may overlap and may cross chunk boundaries. Each frame comes from the newest patch that
    covers it (by file time), otherwise from the original chunk. Splices are frame-exact (trim + concat)
    and a patched chunk is re-encoded once at CRF 14 (visually lossless).
    """
    pdir = CH / "patches"
    if not pdir.exists():
        return
    patches = []
    for p in pdir.glob("p*_*.mp4"):
        if ".part" in p.name:
            continue
        a, b = map(int, p.stem[1:].split("_"))
        patches.append((p.stat().st_mtime, a, b, p))
    patches.sort()
    bounds = sorted(CHUNK_START.items(), key=lambda kv: kv[1])
    for ci, (k, c0) in enumerate(bounds):
        src, orig = CH / f"c{k}.mp4", CH / f"c{k}_orig.mp4"
        base = orig if orig.exists() else src
        total = nframes(base)
        mine = [(m, a, b, p) for m, a, b, p in patches if a < c0 + total and b >= c0]
        if not mine:
            continue
        if orig.exists() and src.exists() and src.stat().st_mtime > max(m for m, *_ in mine):
            continue  # already spliced with the current patches
        if not orig.exists():
            src.rename(orig)
        owner = [-1] * total
        for idx, (m, a, b, p) in enumerate(mine):
            for f in range(max(a, c0) - c0, min(b, c0 + total - 1) - c0 + 1):
                owner[f] = idx
        segs, s0 = [], 0
        for f in range(1, total + 1):
            if f == total or owner[f] != owner[s0]:
                segs.append((owner[s0], s0, f - 1))
                s0 = f
        used = sorted({o for o, *_ in segs if o >= 0})
        inputs = ["-i", str(orig)] + sum([["-i", str(mine[o][3])] for o in used], [])
        ipos = {o: i + 1 for i, o in enumerate(used)}
        uses = {}
        for o, *_ in segs:
            uses[o] = uses.get(o, 0) + 1
        chain, labels, cnt = [], [], {}
        for o, n in uses.items():
            inp = "0:v" if o < 0 else f"{ipos[o]}:v"
            chain.append(f"[{inp}]split={n}" + "".join(f"[s{o + 1}_{j}]" for j in range(n)))
        for i, (o, f0, f1) in enumerate(segs):
            j = cnt.get(o, 0)
            cnt[o] = j + 1
            off = 0 if o < 0 else c0 + 0 - mine[o][1]  # chunk-local frame -> patch-local frame
            st, en = f0 + off, f1 + off + 1
            chain.append(f"[s{o + 1}_{j}]trim=start_frame={st}:end_frame={en},setpts=PTS-STARTPTS[g{i}]")
            labels.append(f"[g{i}]")
        chain.append(f"{''.join(labels)}concat=n={len(labels)}:v=1:a=0,fps=30[out]")
        print(f"c{k}: {len(segs)} segments from {len(used)} patches")
        run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(chain), "-map", "[out]",
            "-video_track_timescale", "90000", "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", src)
        n = nframes(src)
        assert n == total, f"c{k}: spliced {n} frames, expected {total}"


def main():
    apply_patches()
    chunks = sorted((p for p in CH.glob("c*.mp4") if p.stem[1:].isdigit()), key=lambda p: int(p.stem[1:]))
    # Remotion and the patch encoder write different MP4 timescales (1/90000 vs 1/15360); a stream-copy
    # concat of mixed timescales produces a broken timeline, so remux every chunk to 90 kHz first.
    norm = []
    for c in chunks:
        t = CH / f"ts_{c.name}"
        run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", c, "-c", "copy", "-video_track_timescale", "90000", t)
        norm.append(t)
    lst = CH / "list.txt"
    lst.write_text("".join(f"file '{c.name}'\n" for c in norm))
    video = CH / "video_full.mp4"
    run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", video)
    n = int(subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
                            "stream=nb_read_packets", "-of", "csv=p=0", str(video)], capture_output=True, text=True).stdout)
    expected = 25014
    assert n == expected, f"concatenated video has {n} frames, expected {expected}"
    master = OUT / "master_1080p.mp4"
    run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", video, "-i", AUDIO, "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-ac", "2", "-shortest",
        "-metadata", "title=The 20-Minute Heist", "-movflags", "+faststart", master)
    up = OUT / "upload_1080p.mp4"
    # Quality-targeted (CRF 17, capped at 12 Mbps), not a fixed 8 Mbps: these flat graphics need far less than
    # 8 Mbps, and a fixed bitrate pushed the file over the ~800 MB limit for no visible gain.
    run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", master, "-c:v", "libx264", "-preset", "slow", "-profile:v", "high",
        "-crf", "17", "-maxrate", "12000k", "-bufsize", "24000k", "-g", "60", "-bf", "2", "-pix_fmt", "yuv420p",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-c:a", "copy", "-movflags", "+faststart", up)  # reuse the master AAC: re-encoding pushed true peak to -0.8 dBTP
    run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", master, "-t", "60", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", OUT / "preview_coldopen.mp4")
    for p in (master, up, OUT / "preview_coldopen.mp4"):
        print(f"{p.name}: {p.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
