"""Concatenate rendered chunks, mux the mastered mix, and encode the deliverables.

    .venv/bin/python scripts/finalize.py

out/master_1080p.mp4   H.264 High (CRF 16 from Remotion, stream-copied) + AAC 48 kHz 320 kbps
out/upload_1080p.mp4   2-pass ≈ 8 Mbps H.264 + AAC 256 kbps, +faststart
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


def apply_patches():
    """Splice re-rendered windows (out/chunks/patches/p<start>_<end>.mp4, global frames) into their chunk.

    Patches are frame-exact re-renders of the same composition after a layout fix, so splicing only
    swaps the frames that changed. The patched chunk is re-encoded once at CRF 14 (visually lossless).
    """
    pdir = CH / "patches"
    if not pdir.exists():
        return
    by_chunk: dict[int, list] = {}
    starts = sorted(CHUNK_START.items(), key=lambda kv: kv[1])
    for p in sorted(pdir.glob("p*_*.mp4")):
        a, b = map(int, p.stem[1:].split("_"))
        k = max(k for k, s in starts if s <= a)
        by_chunk.setdefault(k, []).append((a - CHUNK_START[k], b - CHUNK_START[k], p))
    for k, plist in by_chunk.items():
        src = CH / f"c{k}.mp4"
        orig = CH / f"c{k}_orig.mp4"
        if orig.exists() and src.exists() and src.stat().st_mtime > max(p.stat().st_mtime for *_, p in plist):
            continue  # already spliced with the current patches
        if not orig.exists():
            src.rename(orig)
        # Frame-exact splice: original [0, a) + patch [a, b] + original (b, end] ... via trim + concat.
        plist.sort()
        inputs, chain, segs, cur = ["-i", str(orig)], [], [], 0
        for i, (a, b, p) in enumerate(plist, 1):
            inputs += ["-i", str(p)]
            if a > cur:
                chain.append(f"[0:v]trim=start_frame={cur}:end_frame={a},setpts=PTS-STARTPTS[o{i}]")
                segs.append(f"[o{i}]")
            chain.append(f"[{i}:v]trim=start_frame=0:end_frame={b - a + 1},setpts=PTS-STARTPTS[p{i}]")
            segs.append(f"[p{i}]")
            cur = b + 1
        total = int(subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
                                    "stream=nb_read_packets", "-of", "csv=p=0", str(orig)], capture_output=True, text=True).stdout)
        if cur < total:
            chain.append(f"[0:v]trim=start_frame={cur},setpts=PTS-STARTPTS[tail]")
            segs.append("[tail]")
        uses = [c for c in chain if c.startswith("[0:v]")]
        for j, c in enumerate(uses):
            chain[chain.index(c)] = f"[src{j}]" + c[len("[0:v]"):]
        chain.insert(0, f"[0:v]split={len(uses)}" + "".join(f"[src{j}]" for j in range(len(uses))))
        chain.append(f"{''.join(segs)}concat=n={len(segs)}:v=1:a=0,fps=30[out]")
        last = "out"
        run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(chain), "-map", f"[{last}]", "-video_track_timescale", "90000",
            "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", src)


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
    common = ["-c:v", "libx264", "-preset", "slow", "-profile:v", "high", "-pix_fmt", "yuv420p", "-b:v", "8000k",
              "-maxrate", "12000k", "-bufsize", "16000k", "-g", "60", "-bf", "2", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]
    plog = str(CH / "x264pass")
    run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", master, *common, "-pass", "1", "-passlogfile", plog, "-an", "-f", "mp4", "/dev/null")
    run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", master, *common, "-pass", "2", "-passlogfile", plog,
        "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart", up)
    run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", master, "-t", "60", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", OUT / "preview_coldopen.mp4")
    for p in (master, up, OUT / "preview_coldopen.mp4"):
        print(f"{p.name}: {p.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
