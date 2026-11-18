"""Episode builder: script.json -> timeline.json (+ voice/mix wav, .srt).

Timing model: each scene's narration segments are synthesised (edge-tts) and
measured; the scene lasts lead + segments (+ pauses) + tail. Every event in the
scene can be anchored to narration words, so visuals stay in sync with the voice:
  "cue": "w:spear"     first occurrence of the word 'spear' in this scene
  "cue": "w:spear#2"   second occurrence
  "cue": "seg:2" / "seg:2:end"   start / end of narration segment 2
  "at": 0.5            fraction of scene duration
  "e": 1.5             1.5 s before scene end
  "t": 3.0             absolute seconds into the scene
  "off": -0.2          added to any of the above
If <episode>/narration.mp3 exists it replaces the TTS voice; timings are scaled
to its length (segment proportions from TTS are kept).
"""
import copy
import json
import os
import re
import numpy as np
from . import audio as A
from .core import hrand

FPS = 30
DEFAULT_VOICE = {"name": "kokoro:am_fenrir", "rate": "1.04", "pitch": "0"}
DEFAULT_FARDIN_VOICE = {"name": "kokoro:am_eric", "rate": "1.12", "pitch": "0"}
MUSIC_BELOW_VOICE_DB = 10.5   # music RMS relative to narration RMS (before ducking)


def _norm_word(w):
    return re.sub(r"[^a-z0-9']", "", w.lower())


class SceneTiming:
    def __init__(self, dur, segs, words):
        self.dur, self.segs, self.words = dur, segs, words

    def cue(self, c):
        if c.startswith("w:"):
            w = c[2:]
            n = 1
            if "#" in w:
                w, n = w.split("#"); n = int(n)
            w = _norm_word(w)
            k = 0
            for wd in self.words:
                if _norm_word(wd["w"]) == w or (len(w) > 3 and _norm_word(wd["w"]).startswith(w)):
                    k += 1
                    if k == n:
                        return wd["t"]
            raise KeyError(f"cue word not found: {c} in {[x['w'] for x in self.words][:60]}")
        if c.startswith("seg:"):
            parts = c.split(":")
            i = int(parts[1])
            s = self.segs[i]
            return s["end"] if len(parts) > 2 and parts[2] == "end" else s["t"]
        raise KeyError(c)


def resolve_time(obj, tm, key="t"):
    if "cue" in obj:
        t = tm.cue(obj["cue"])
    elif "at" in obj:
        t = obj["at"] * tm.dur
    elif "e" in obj:
        t = tm.dur - obj["e"]
    else:
        t = obj.get(key, 0.0)
    t += obj.get("off", 0.0)
    obj["t"] = max(0.0, min(tm.dur, t))
    for k in ("cue", "at", "e", "off"):
        obj.pop(k, None)
    if "until_cue" in obj:
        obj["until"] = tm.cue(obj.pop("until_cue")) + obj.pop("until_off", 0.0)
    if "from_cue" in obj:
        obj["from"] = tm.cue(obj.pop("from_cue")) + obj.pop("from_off", 0.0)
    if "dur_to" in obj:
        end = tm.cue(obj.pop("dur_to")) if isinstance(obj["dur_to"], str) else obj.pop("dur_to")
        obj["dur"] = max(0.2, end - obj["t"] + obj.pop("dur_off", 0.0))
    if "dur_e" in obj:
        obj["dur"] = max(0.2, tm.dur - obj.pop("dur_e") - obj["t"])
    return obj


TASK_HOLD = {"knap": "stone", "butcher": "flake", "smash": "stone", "eat": "meat", "aim": "spear", "lookout": "spear"}


def make_crowd(c, sid):
    out = []
    n = c.get("n", 5)
    x0, x1 = c.get("x", [-400, 400])
    tasks = c.get("tasks", ["idle"])
    for i in range(n):
        r = lambda k: hrand(sid, "crowd", i, k, c.get("seed", 0))
        u = (i + 0.5) / n
        x = x0 + (x1 - x0) * u + (r("jx") - 0.5) * (x1 - x0) / n * 0.6
        kid = i < c.get("kids", 0)
        size = (150 + 50 * r("ks")) if kid else (c.get("size", [250, 300])[0] + (c.get("size", [250, 300])[1] - c.get("size", [250, 300])[0]) * r("sz"))
        task = tasks[i % len(tasks)]
        face = c.get("facing", "random")
        f = (1 if r("f") > 0.5 else -1) if face == "random" else (1 if face in (1, "right") else -1 if face in (-1, "left") else (1 if x < c.get("center", 0) else -1))
        acts = [{"t": 0, "pose": task, "arg": r("arg") * 6, "hold": c.get("holds", {}).get(task, TASK_HOLD.get(task)), "expr": c.get("expr", "neutral")}]
        for ev in c.get("events", []):
            e2 = dict(ev)
            e2["t"] = ev["t"] + r("stag") * ev.get("stagger", 0.4)
            if "to_rel" in e2:
                e2["to"] = x + e2.pop("to_rel") * (1 + 0.2 * r("tr"))
            if e2.get("pose") == "keep":
                e2["pose"] = task
            out_hold = e2.get("hold")
            acts.append(e2)
        out.append({"id": f"{sid}_c{i}", "kind": "era", "x": x, "y": c.get("y", 0) + (r("y") - 0.5) * c.get("ydepth", 0),
                    "size": size, "facing": f, "track": acts, "layer": c.get("layer", 0),
                    "beard": None if kid else None})
        for k in ("beard",):
            if out[-1][k] is None:
                del out[-1][k]
    return out


def build(ep_dir, force_tts=False):
    script = json.load(open(os.path.join(ep_dir, "script.json")))
    bdir = os.path.join(ep_dir, "build")
    cache = os.path.join(bdir, "tts")
    os.makedirs(cache, exist_ok=True)
    vcfg = script.get("voice", {})
    voice, rate, pitch = vcfg.get("name", DEFAULT_VOICE["name"]), vcfg.get("rate", DEFAULT_VOICE["rate"]), vcfg.get("pitch", "0")
    fv = dict(DEFAULT_FARDIN_VOICE, **script.get("fardin_voice", {}))

    scenes = []
    T = 0.0
    voice_clips = []  # (t_abs, samples)
    fardin_clips = []
    all_words = []
    for si, sc in enumerate(script["scenes"]):
        sc = copy.deepcopy(sc)
        sid = sc.get("id", f"s{si:02d}")
        lead = sc.get("lead", 0.35)
        tail = sc.get("tail", 0.5)
        t = lead
        segs, words = [], []
        narr = sc.get("narration", [])
        if isinstance(narr, str):
            narr = [narr]
        for seg in narr:
            if isinstance(seg, str):
                seg = {"text": seg}
            t += seg.get("pause_before", 0.0)
            x, wds = A.tts(seg["text"], cache, voice, rate, pitch)
            d = len(x) / A.SR
            segs.append({"t": t, "end": t + d, "text": seg["text"]})
            for w in wds:
                words.append({"w": w["w"], "t": t + w["t"], "d": w["d"]})
            voice_clips.append((T + t, x))
            t += d + seg.get("pause", 0.25)
        dur = max(sc.get("min_dur", 0.0), t - (0.25 if narr else 0) + tail)
        tm = SceneTiming(dur, segs, words)
        # resolve everything
        for a in sc.get("actors", []):
            for act in a.get("track", []):
                resolve_time(act, tm)
            for s in a.get("say", []):
                resolve_time(s, tm)
                xs, _ = A.tts(s["text"], cache, fv["name"], fv["rate"], fv["pitch"])
                s.setdefault("dur", len(xs) / A.SR + 0.25)
                if s.get("voice", True):
                    fardin_clips.append((T + s["t"], xs))
        for a in sc.get("animals", []):
            for act in a.get("track", []):
                resolve_time(act, tm)
        for k in sc.get("camera", []):
            resolve_time(k, tm)
        for g in sc.get("graphics", []):
            resolve_time(g, tm)
            if "item_cues" in g:
                g["times"] = [tm.cue(c) - g["t"] for c in g.pop("item_cues")]
            if "mark_cues" in g:
                for m, c in zip(g["marks"], g.pop("mark_cues")):
                    m["t"] = tm.cue(c) - g["t"]
            if "pin_cues" in g:
                for pn, c in zip(g["pins"], g.pop("pin_cues")):
                    pn["t"] = tm.cue(c) - g["t"]
        for f in sc.get("fx", []):
            resolve_time(f, tm)
        for s in sc.get("shake", []):
            s["t0"] = resolve_time(dict(s.get("start", {"t": 0})), tm)["t"]
            s["t1"] = resolve_time(dict(s.get("end", {"e": 0})), tm)["t"]
        for p in sc.get("props", []):
            if "from_cue" in p or "until_cue" in p:
                if "from_cue" in p:
                    p["from"] = tm.cue(p.pop("from_cue")) + p.pop("from_off", 0)
                if "until_cue" in p:
                    p["until"] = tm.cue(p.pop("until_cue")) + p.pop("until_off", 0)
            if "anim" in p:
                for k, keys in p["anim"].items():
                    p["anim"][k] = [[tm.cue(kk[0]) + (kk[2] if len(kk) > 2 else 0) if isinstance(kk[0], str) else kk[0], kk[1]] for kk in keys]
        for s in sc.get("sfx", []):
            resolve_time(s, tm)
        crowd = []
        for ci, c in enumerate(sc.get("crowd", [])):
            for ev in c.get("events", []):
                resolve_time(ev, tm)
            crowd += make_crowd(c, f"{sid}_{ci}")
        sc["crowd_actors"] = crowd
        sc["id"], sc["start"], sc["dur"], sc["segs"], sc["words"] = sid, T, dur, segs, words
        for w in words:
            all_words.append({"w": w["w"], "t": T + w["t"], "d": w["d"]})
        scenes.append(sc)
        T += dur
    total = T
    timeline = {"episode": script.get("episode"), "title": script.get("title"), "fps": FPS, "duration": total,
                "scenes": scenes, "words": all_words, "chapters": chapters(scenes)}

    # ---------------------------------------------------------- audio
    n = int((total + 0.5) * A.SR)
    vo = np.zeros(n, np.float32)
    for t0, x in voice_clips:
        A.place(vo, x, t0)
    nar_mp3 = os.path.join(ep_dir, "narration.mp3")
    if os.path.exists(nar_mp3):
        # external narration: scale every timing to its length
        ext = A.decode(nar_mp3)
        first = voice_clips[0][0] if voice_clips else 0
        last = max(t0 + len(x) / A.SR for t0, x in voice_clips)
        k = (len(ext) / A.SR) / max(1e-3, last - first)
        timeline = _scale_timeline(timeline, k, first)
        total = timeline["duration"]
        n = int((total + 0.5) * A.SR)
        vo = np.zeros(n, np.float32)
        A.place(vo, ext, first)
        fardin_clips = [(first + (t0 - first) * k, x) for t0, x in fardin_clips]
        scenes = timeline["scenes"]
    fv_tr = np.zeros(n, np.float32)
    for t0, x in fardin_clips:
        A.place(fv_tr, x, t0)
    sfx = np.zeros(n, np.float32)
    amb = np.zeros(n, np.float32)
    mus = np.zeros(n, np.float32)
    music_file = os.path.join(ep_dir, "music.mp3")
    for sc in scenes:
        S0, D = sc["start"], sc["dur"]
        for s in sc.get("sfx", []):
            clip = A.SFX[s["type"]](s.get("seed", int(hrand(sc["id"], s["type"], s["t"]) * 1000)))
            A.place(sfx, clip, S0 + s["t"], s.get("vol", 0.7))
        # automatic sounds: reaction pops, graphics, flashes
        for a in sc.get("actors", []):
            if a.get("kind") == "fardin":
                for act in a.get("track", []):
                    if act.get("pop"):
                        A.place(sfx, A.sfx_pop(int(act["t"] * 100)), S0 + act["t"], 0.45)
        for g in sc.get("graphics", []):
            if g["type"] in ("fact", "map", "timeline", "compare", "list", "chapter", "lower", "tag"):
                A.place(sfx, A.sfx_ui(int(g["t"] * 10)), S0 + g["t"], 0.35)
            if g["type"] == "chapter":
                A.place(sfx, A.sfx_stinger(si), S0 + g["t"], 0.4)
            if g["type"] == "callout":
                A.place(sfx, A.sfx_impact(3, 1.0), S0 + g["t"], 0.35)
        for f in sc.get("fx", []):
            if f["type"] == "flash":
                A.place(sfx, A.sfx_flash(1), S0 + f["t"], 0.7)
        # ambience with 0.6 s crossfades
        a0, a1 = int(S0 * A.SR), min(n, int((S0 + D) * A.SR))
        L = a1 - a0
        if L <= 0:
            continue
        fade = np.ones(L)
        fl = min(L // 2, int(0.6 * A.SR))
        fade[:fl] = np.linspace(0, 1, fl)
        fade[-fl:] = np.linspace(1, 0, fl)
        for name, vol in sc.get("amb", {}).items():
            # deterministic absolute-time ambience so adjacent scenes connect
            bed = A.AMB[name](L + fl, hash(name) % 1000 + int(S0))[:L]
            amb[a0:a1] += bed * vol * fade
    if not os.path.exists(music_file):
        # group neighbouring scenes with the same mood into one unbroken, tempo-locked run;
        # crossfade (0.8 s) only where the mood changes
        runs = []
        for sc in scenes:
            mood = sc.get("music", "calm")
            if runs and runs[-1][0] == mood:
                runs[-1][2] = sc["start"] + sc["dur"]
            else:
                runs.append([mood, sc["start"], sc["start"] + sc["dur"]])
        xf = 0.8
        for i, (mood, r0, r1) in enumerate(runs):
            if mood == "none":
                continue
            a = r0 - (xf / 2 if i > 0 else 0)
            b = r1 + (xf / 2 if i < len(runs) - 1 else 0)
            a0, a1 = max(0, int(a * A.SR)), min(n, int(b * A.SR))
            L = a1 - a0
            if L <= 0:
                continue
            seg = A.music_score(L, mood, a0 / A.SR)
            env = np.ones(L)
            fl = min(L // 2, int(xf * A.SR))
            if i > 0 and runs[i - 1][0] != "none":
                env[:fl] = np.sin(np.linspace(0, np.pi / 2, fl)) ** 2
            elif i > 0:
                env[:fl] = np.linspace(0, 1, fl)
            if i < len(runs) - 1:
                env[-fl:] = np.cos(np.linspace(0, np.pi / 2, fl)) ** 2
            else:
                env[-int(1.5 * A.SR):] *= np.linspace(1, 0, min(L, int(1.5 * A.SR)))
            mus[a0:a1] += seg * env
    if os.path.exists(music_file):
        m = A.decode(music_file)
        reps = int(np.ceil(n / len(m)))
        mus = np.tile(m, reps)[:n] * 0.25
    voice_all = vo + fv_tr * 0.9
    duck = A.duck_curve(voice_all, 0.65)
    duck_sfx = A.duck_curve(voice_all, 0.35)
    # normalise voice to a fixed level first
    vr = np.sqrt(np.mean(vo[np.abs(vo) > 0.01] ** 2)) if np.any(np.abs(vo) > 0.01) else 1
    g = 0.16 / max(vr, 1e-4)
    # music sits ~10.5 dB under the narration (measured where music plays), then ducks under speech
    mact = np.abs(mus) > 1e-4
    if mact.any():
        mr = np.sqrt(np.mean(mus[mact] ** 2))
        mus *= 0.16 * 10 ** (-MUSIC_BELOW_VOICE_DB / 20) / max(mr, 1e-6)
    mix = voice_all * g + mus * duck + amb * duck * 0.55 + sfx * duck_sfx * 0.55
    mix = A.master(mix)
    mix_path = os.path.join(bdir, "mix.wav")
    A.write_wav(mix_path, mix)
    A.loudnorm_wav(mix_path, I=-15.0, TP=-1.6)
    A.write_wav(os.path.join(bdir, "voice.wav"), np.clip(voice_all * g, -1, 1))
    timeline["duration"] = total
    json.dump(timeline, open(os.path.join(bdir, "timeline.json"), "w"), indent=1)
    return timeline


def _scale_timeline(tl, k, first):
    def sc(t):
        return first + (t - first) * k if t > first else t
    for s in tl["scenes"]:
        s0 = s["start"]
        s["start"] = sc(s0)
        endabs = sc(s0 + s["dur"])
        kk = (endabs - s["start"]) / max(1e-3, s["dur"])
        _scale_scene(s, kk)
        s["dur"] = endabs - s["start"]
    for w in tl["words"]:
        w["t"] = sc(w["t"]); w["d"] *= k
    tl["duration"] = tl["scenes"][-1]["start"] + tl["scenes"][-1]["dur"]
    tl["chapters"] = chapters(tl["scenes"])
    return tl


def _scale_scene(s, k):
    def walk(o):
        if isinstance(o, dict):
            for key in ("t", "dur", "t0", "t1", "from", "until", "end", "fade", "wdur"):
                if key in o and isinstance(o[key], (int, float)):
                    o[key] *= k
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    for key in ("actors", "animals", "camera", "graphics", "fx", "sfx", "shake", "crowd_actors", "segs", "words", "props"):
        walk(s.get(key, []))


def chapters(scenes):
    out = []
    for s in scenes:
        if s.get("chapter") and (not out or out[-1]["title"] != s["chapter"]):
            out.append({"title": s["chapter"], "t": s["start"]})
    return out


# ------------------------------------------------------------------ captions
def srt_time(t):
    h, m = int(t // 3600), int(t % 3600 // 60)
    s = t % 60
    return f"{h:02d}:{m:02d}:{int(s):02d},{int((s - int(s)) * 1000):03d}"


def caption_lines(words, max_chars=42):
    lines, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        txt = " ".join(x["w"] for x in cur)
        nxt = words[i + 1] if i + 1 < len(words) else None
        gap = (nxt["t"] - (w["t"] + w["d"])) if nxt else 9
        if len(txt) > max_chars - 8 or w["w"][-1:] in ".?!" or gap > 0.45 or (w["w"][-1:] in ",;:" and len(txt) > 18) or nxt is None:
            lines.append({"t0": cur[0]["t"], "t1": w["t"] + w["d"] + 0.15, "text": txt, "words": list(cur)})
            cur = []
    for i in range(len(lines) - 1):
        lines[i]["t1"] = min(lines[i]["t1"], lines[i + 1]["t0"] - 0.02)
    return lines


def write_srt(words, path):
    # edge-tts word boundaries omit punctuation; restore it from segment text where possible
    lines = caption_lines(words)
    with open(path, "w") as f:
        for i, l in enumerate(lines, 1):
            f.write(f"{i}\n{srt_time(l['t0'])} --> {srt_time(l['t1'])}\n{l['text']}\n\n")
    return lines


def punctuate(tl):
    """Attach punctuation from segment text to word list (edge-tts drops it)."""
    out = []
    for s in tl["scenes"]:
        for seg in s["segs"]:
            toks = seg["text"].split()
            ws = [w for w in s["words"] if seg["t"] - 0.01 <= w["t"] <= seg["end"] + 0.01]
            j = 0
            for w in ws:
                ww = dict(w, t=w["t"] + s["start"])
                while j < len(toks) and _norm_word(toks[j]) == "":
                    j += 1
                if j < len(toks) and _norm_word(toks[j]).startswith(_norm_word(w["w"])[:3] or "#"):
                    ww["w"] = toks[j].strip('"“”')
                    j += 1
                out.append(ww)
    return out
