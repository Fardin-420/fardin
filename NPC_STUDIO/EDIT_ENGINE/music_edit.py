"""Bar-aligned music edit + frame-accurate event map.

    python music_edit.py <project_dir>

Reads source/edit_plan.json and source/music_analysis_full.json, assembles the
edited soundtrack from whole-beat pieces of the original track (no pitch or
tempo change), scores every seam, re-analyzes the result on its own, and
writes:

  audio/music_edit.wav            float32 stereo 48 kHz (unmastered)
  source/music_events.json        beat/onset/seam map in video time, with 60 fps frames
  previews/music_events.png       verification plot (sections, impacts, seams)

Seams sit 14 ms before the grid point and end 1 ms after it. Real transients in
this track land 4-8 ms after the grid, so the incoming hit is always played
untouched, and the outgoing tail fades under it. Quiet, beatless seams use a
longer 80 ms equal-power crossfade instead.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).parent))
from analyze_music import SR, analyze_signal, decode, plot  # noqa: E402


def mel_db(x: np.ndarray) -> np.ndarray:
    M = librosa.feature.melspectrogram(y=x, sr=SR, n_fft=2048, hop_length=256, n_mels=48, fmax=16000)
    return librosa.power_to_db(M + 1e-10).mean(1)


def build(project: Path) -> dict:
    plan = json.loads((project / "source/edit_plan.json").read_text())
    ana = json.loads((project / "source/music_analysis_full.json").read_text())
    P, ph = ana["beat_period"], ana["grid_phase"]
    fps = plan["fps"]
    bt = lambda k: ph + k * P
    src = decode(str(project / plan["music"]))  # stereo, overs preserved (gain staged at master)
    mono = src.mean(1)

    # ---- resolve pieces to source sample ranges ----
    pieces = []
    for p in plan["music_edit"]["pieces"]:
        if "beats" in p:
            a, b = bt(p["beats"][0]), bt(p["beats"][1])
        elif "to_beat" in p:
            a, b = p["from_t"], bt(p["to_beat"])
        else:
            a, b = bt(p["from_beat"]), bt(p["from_beat"]) + p["dur"]
        pieces.append({**p, "src_a": a, "src_b": b})

    # Output positions in exact seconds; each piece starts where the last one ended.
    t = 0.0
    for p in pieces:
        p["out_a"] = t
        t += p["src_b"] - p["src_a"]
        p["out_b"] = t
    total = t
    n_out = int(round(total * SR))
    out = np.zeros((n_out, 2), np.float32)

    # ---- assemble with seam crossfades ----
    def level_db(x):
        return 10 * np.log10(np.mean(x ** 2) + 1e-12)

    # Seam windows. A piece that continues the source exactly needs no seam at all.
    # Quiet (beatless pad) seams get a long equal-power fade; beat seams a short
    # constant-gain fade placed before the transient so the incoming hit is never touched.
    win = [(0, 0, "none")]
    for i in range(1, len(pieces)):
        e, s = int(round(pieces[i - 1]["src_b"] * SR)), int(round(pieces[i]["src_a"] * SR))
        if abs(e - s) <= 1:
            win.append((0, 0, "none"))
            continue
        quiet = max(level_db(mono[e - SR // 4: e]), level_db(mono[s: s + SR // 4])) < -14
        win.append((int(0.070 * SR), int(0.010 * SR), "power") if quiet else (int(0.014 * SR), int(0.001 * SR), "gain"))
    win.append((0, 0, "none"))

    def fade_in(n, kind):
        x = np.sin(np.linspace(0, np.pi / 2, n))
        return x if kind == "power" else x ** 2

    seams = []
    for i, p in enumerate(pieces):
        To = int(round(p["out_a"] * SR))
        sa = int(round(p["src_a"] * SR))
        pre_in, post_in, kind_in = win[i]
        pre_out, post_out, kind_out = win[i + 1]
        o_start = To - pre_in
        o_end = (int(round(p["out_b"] * SR)) + post_out) if i < len(pieces) - 1 else n_out
        seg = src[sa + (o_start - To): sa + (o_end - To)].copy()
        w = np.ones(len(seg), np.float32)
        if pre_in + post_in:
            w[: pre_in + post_in] = fade_in(pre_in + post_in, kind_in)
        if pre_out + post_out:
            w[-(pre_out + post_out):] *= fade_in(pre_out + post_out, kind_out)[::-1]
        if i == len(pieces) - 1 and "fade_out" in p:
            nf = int(p["fade_out"] * SR)
            w[-nf:] *= np.cos(np.linspace(0, np.pi / 2, nf)) ** 2
        end = min(n_out, o_start + len(seg))
        out[o_start:end] += (seg * w[:, None])[: end - o_start]
        p["xfade_in_ms"] = round(1000 * (pre_in + post_in) / SR, 1)
        p["xfade_curve"] = kind_in

    # ---- seam scoring ----
    # context_mismatch: mel-spectrum distance between what now leads into the incoming
    # piece and what leads into it in the original song. baseline: the same distance
    # between equivalent beats four bars apart inside unedited drops (natural variation).
    # hf_ratio: >4 kHz energy in the fade window vs. the same window in either source
    # (a click or a doubled transient would push it well above 1).
    import scipy.signal as ssig
    hp = ssig.sosfiltfilt(ssig.butter(4, 4000, "highpass", fs=SR, output="sos"), mono)
    hpo = ssig.sosfiltfilt(ssig.butter(4, 4000, "highpass", fs=SR, output="sos"), out.mean(1))
    ctx = lambda x, i: mel_db(x[i - int(0.15 * SR): i - int(0.015 * SR)])
    base = [float(np.sqrt(np.mean((ctx(mono, int(bt(k) * SR)) - ctx(mono, int(bt(k + 16) * SR))) ** 2)))
            for k in list(range(21, 36)) + list(range(125, 136))]
    baseline = float(np.median(base))
    hf = lambda x, i: float(np.mean(x[i - int(0.016 * SR): i + int(0.004 * SR)] ** 2))
    for i in range(1, len(pieces)):
        p, prev = pieces[i], pieces[i - 1]
        T = p["out_a"]
        To, Ts, Te = int(round(T * SR)), int(round(p["src_a"] * SR)), int(round(prev["src_b"] * SR))
        lsd = float(np.sqrt(np.mean((ctx(out.mean(1), To) - ctx(mono, Ts)) ** 2)))
        hf_ratio = hf(hpo, To) / max(hf(hp, Ts), hf(hp, Te), 1e-12)
        seams.append({"at_out_t": round(T, 4), "frame": int(round(T * fps)),
                      "from": prev["role"].split(":")[0], "to": p["role"].split(":")[0],
                      "xfade_ms": p["xfade_in_ms"], "curve": p["xfade_curve"],
                      "context_mismatch_db": round(lsd, 2), "baseline_db": round(baseline, 2),
                      "hf_ratio": round(hf_ratio, 2),
                      "ok": bool(lsd <= baseline + 3.0 and hf_ratio < 1.6)})

    sf.write(project / "audio/music_edit.wav", out, SR, subtype="FLOAT")

    # ---- re-analyze the edited audio on its own grid ----
    pre_len = pieces[1]["out_a"]  # music entrance (source beat 4) in video time
    first_beat = pieces[1]["beats"][0]
    phase_out = pre_len % P
    res = analyze_signal(out.mean(1), "music_edit.wav", grid=(P, phase_out))
    k0 = int(round((pre_len - phase_out) / P))  # output grid index of the entrance

    src_beats = {b["beat"]: b for b in ana["beats"]}
    src_section = {}
    for s in ana["sections"]:
        for k in range(s["start_beat"], s["end_beat"]):
            src_section[k] = s["label"]

    def src_of(t_out):
        for p in pieces:
            if p["out_a"] - 1e-3 <= t_out < p["out_b"] - 1e-3:  # beat times carry 4-decimal rounding
                return p, p["src_a"] + (t_out - p["out_a"])
        return pieces[-1], pieces[-1]["src_a"] + (t_out - pieces[-1]["out_a"])

    # Measured onset of every beat: the moment the rise reaches 50 % (1 ms resolution), and the
    # impact frame: the frame whose start is nearest the onset, allowing the picture to lead the
    # sound by at most 10 ms and to trail it by at most 6.7 ms (audio a hair after picture reads in sync).
    from analyze_music import Curves
    cur = Curves(out.mean(1))
    offs = []

    def onset_of(tg, strong):
        i = int(round(tg * 1000))
        w = cur.R[i - 30: i + 31]
        j = int(np.argmax(w))
        if not strong or w[j] < 12:
            return None
        k = int(np.argmax(w[: j + 1] >= 0.5 * w[j]))
        return (i - 30 + k) / 1000

    for b in res["beats"]:
        o = onset_of(b["t"], b["rise_db"] >= 20)
        if o is not None:
            offs.append(o - b["t"])
    med_off = float(np.median(offs))

    beats = []
    for b in res["beats"]:
        n = b["beat"] - k0
        p, st = src_of(b["t"])
        sk = int(round((st - ph) / P))
        s = src_beats.get(sk, {})
        o = onset_of(b["t"], b["rise_db"] >= 12)
        onset = o if o is not None else b["t"] + med_off
        beats.append({"n": n, "t": b["t"], "onset_t": round(onset, 4), "frame": int(np.ceil(onset * fps - 0.6)),
                      "src_beat": sk, "src_t": round(st, 4), "piece": p["role"].split(":")[0],
                      "section": src_section.get(sk, "pre-roll" if n < 0 else "outro"),
                      "bar_pos": s.get("bar_pos", b["bar_pos"]),
                      "rise_db": b["rise_db"], "jump_full_db": b["jump_full_db"], "level_db": b["level_db"],
                      "sub_level": s.get("sub_level", b["sub_level"]), "pitch_808": s.get("pitch_808", 0.0),
                      "src_rise_db": s.get("rise_db", 0.0), "class": s.get("class", b["class"])})
    onsets = [{**o, "frame": int(np.ceil(o["t"] * fps - 0.6))} for o in res["onsets"]]

    events = {
        "fps": fps, "duration": round(total, 4), "frames": int(round(total * fps)),
        "beat_period": P, "tempo_bpm": round(60 / P, 3), "grid_phase_out": round(phase_out, 4),
        "onset_offset_from_grid_ms": round(1000 * med_off, 2),
        "entrance_t": round(pre_len, 4), "entrance_src_beat": first_beat,
        "frame_rule": "frame = ceil(onset * fps - 0.6): picture leads sound by <= 10 ms, trails by <= 6.7 ms",
        "pieces": [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in p.items()} for p in pieces],
        "seams": seams, "beats": beats, "onsets": onsets,
    }
    (project / "source/music_events.json").write_text(json.dumps(events, indent=1))
    res["sections"] = [{"label": ("seam " + s["to"][:14]), "t": s["at_out_t"], "t_end": s["at_out_t"] + 0.02}
                       for s in seams]
    plot(res, str(project / "previews/music_events.png"),
         events=[{"t": b["t"], "id": f"n{b['n']}/s{b['src_beat']}"} for b in beats
                 if b["class"] in ("impact", "strong") and b["bar_pos"] == 1])
    return events


if __name__ == "__main__":
    ev = build(Path(sys.argv[1]))
    print(f"edited music: {ev['duration']} s, {ev['frames']} frames @ {ev['fps']} fps, entrance at {ev['entrance_t']} s")
    for s in ev["seams"]:
        print(f"  seam {s['at_out_t']:7.3f}s f{s['frame']:5d}  {s['from'][:28]:28s} -> {s['to'][:34]:34s} "
              f"ctx {s['context_mismatch_db']:5.2f} dB (base {s['baseline_db']:.2f})  xf {s['xfade_ms']:5.1f} ms {s['curve']:5s}  hf {s['hf_ratio']:.2f}  {'OK' if s['ok'] else 'CHECK'}")
