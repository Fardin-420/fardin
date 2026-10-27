"""Output timeline: which source moment every output frame shows, with eased speed ramps.

Segments that touch form a continuous run. Inside a run the per-frame speed is smoothed
(Gaussian, ~0.2 s) and renormalised so the run still covers exactly its source span: speed
changes ramp instead of jumping. Gaps between runs are cuts and carry a named transition.
All picture and sound timing derives from this module.
"""
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


@dataclass
class Frame:
    i: int
    t: float
    kind: str          # hook | video | freeze | outro
    src: float = 0.0
    speed: float = 1.0
    run: int = -1


class Timeline:
    def __init__(self, edl_path=HERE / "edl_resolved.json"):
        e = self.edl = json.loads(Path(edl_path).read_text())
        fps = self.fps = e["fps"]
        self.frames = []
        for _ in range(round(e["hook"]["duration"] * fps)):
            self._add("hook", e["hook"]["src"])
        self.video_start = len(self.frames) / fps

        # group segments into runs
        runs, cur = [], [e["segments"][0]]
        for a, b in zip(e["segments"], e["segments"][1:]):
            if b["in"] - a["out"] > 0.02:
                runs.append(cur)
                cur = [b]
            else:
                cur.append(b)
        runs.append(cur)
        self.runs = runs
        self.cuts = []      # (output time, transition name)
        self.speedups = []  # (t0, t1, peak speed)
        self.map = []       # (src, out) pairs for src_to_out interpolation
        for ri, run in enumerate(runs):
            t_run = len(self.frames) / fps
            if ri > 0:
                self.cuts.append((t_run, run[0].get("cut", "whip_left")))
            v = []
            for s in run:
                v += [s["speed"]] * max(1, round((s["out"] - s["in"]) / s["speed"] * fps))
            v = np.array(v, float)
            k = np.exp(-0.5 * (np.arange(-9, 10) / 3.5) ** 2)
            vs = np.convolve(np.pad(v, 9, mode="edge"), k / k.sum(), mode="valid")
            span = run[-1]["out"] - run[0]["in"]
            pos = np.concatenate([[0.0], np.cumsum(vs)[:-1]])
            pos = run[0]["in"] + pos * (span / (vs.sum()))
            for p, sp in zip(pos, vs):
                self.map.append((p, len(self.frames) / fps))
                self._add("video", float(p), float(sp), ri)
            # fast stretches for the HUD badge
            fast = vs > 1.8
            i = 0
            while i < len(fast):
                if fast[i]:
                    j = i
                    while j < len(fast) and fast[j]:
                        j += 1
                    if j - i >= 8:
                        self.speedups.append(((len(self.frames) - len(v) + i) / fps,
                                              (len(self.frames) - len(v) + j) / fps, float(vs[i:j].max())))
                    i = j
                else:
                    i += 1
        self.freeze_start = len(self.frames) / fps
        self.cuts.append((self.freeze_start, "freeze"))
        for _ in range(round(e["freeze"]["duration"] * fps)):
            self._add("freeze", e["freeze"]["src"])
        self.outro_start = len(self.frames) / fps
        for _ in range(round(e["outro"]["duration"] * fps)):
            self._add("outro")
        self.duration = len(self.frames) / fps

        self.camera = sorted(
            [(self.src_to_out(k["src"]), k["fx"], k["fy"], k["z"]) for k in e["camera"]]
            + [(self.freeze_start + k["ft"], k["fx"], k["fy"], k["z"]) for k in e["freeze_camera"]])
        self.chapters = [(self.src_to_out(c["src"]), c["num"], c["title"]) for c in e["chapters"]]
        self.chapters[0] = (self.video_start, *self.chapters[0][1:])
        self.highlights = ([dict(h, t0=self.src_to_out(h["src"]), dur=h["dur"] / self._speed_at(h["src"]))
                            for h in e["highlights"]]
                           + [dict(h, t0=self.freeze_start + h["ft"]) for h in e["freeze_highlights"]])
        for h in self.highlights:
            h["dur"] = max(h["dur"], 0.55)
        self.taps = [dict(tp, t0=self.src_to_out(tp["src"])) for tp in e["taps"]]
        self.success = [self.src_to_out(s) for s in e["success"]]
        self.alerts = [self.src_to_out(s) for s in e["alerts"]]
        self.captions = [self._span(c) for c in e["captions"]]
        self.notes = [self._span(c) for c in e.get("notes", [])]
        self.lower_thirds = e["lower_thirds"]

    def _span(self, c):
        if "src" in c:
            return dict(c, t0=self.src_to_out(c["src"][0]), t1=self.src_to_out(c["src"][1], end=True))
        return dict(c, t0=self.freeze_start + c["ft"][0], t1=self.freeze_start + c["ft"][1])

    def _add(self, kind, src=0.0, speed=1.0, run=-1):
        i = len(self.frames)
        self.frames.append(Frame(i, i / self.fps, kind, src, speed, run))

    def _speed_at(self, s):
        for f in self.frames:
            if f.kind == "video" and f.src >= s:
                return max(1.0, f.speed)
        return 1.0

    def src_to_out(self, s, end=False):
        """Output time of source time s (inside a cut: the next kept moment, or with end=True
        the end of the previous one)."""
        m = self.map
        for ri, run in enumerate(self.runs):
            if s < run[0]["in"]:
                if end and ri > 0:
                    return self._run_end(ri - 1)
                return self._run_start(ri)
            if s <= run[-1]["out"]:
                pts = [(p, o) for (p, o), f in zip(m, (fr for fr in self.frames if fr.kind == "video")) if f.run == ri]
                ps = np.array([p for p, _ in pts])
                os_ = np.array([o for _, o in pts])
                return float(np.interp(s, ps, os_, right=os_[-1] + 1 / self.fps))
        return self.freeze_start

    def _run_start(self, ri):
        return next(f.t for f in self.frames if f.kind == "video" and f.run == ri)

    def _run_end(self, ri):
        return max(f.t for f in self.frames if f.kind == "video" and f.run == ri) + 1 / self.fps

    def cam(self, t, ramp=0.45):
        kf = self.camera
        if t <= kf[0][0]:
            return kf[0][1:]
        for a, b in zip(kf, kf[1:]):
            if a[0] <= t < b[0]:
                r = min(ramp, (b[0] - a[0]) * 0.85)
                u = ease((t - (b[0] - r)) / r) if r > 0 else 1.0
                return tuple(a[j] + (b[j] - a[j]) * u for j in (1, 2, 3))
        return kf[-1][1:]

    def chapter(self, t):
        cur = self.chapters[0]
        for c in self.chapters:
            if t >= c[0]:
                cur = c
        return cur

    def used_source_frames(self, margin=2):
        """Every source frame index the render reads (plus neighbours), for the privacy scan."""
        idx = set()
        for f in self.frames:
            if f.kind in ("video", "freeze", "hook"):
                k = int(round(f.src * self.fps))
                idx.update(range(k - margin, k + margin + 1))
        return sorted(i for i in idx if i >= 0)

    def sound_events(self):
        ev = [("hook_hit", 0.12), ("hook_hit2", 0.40), ("hook_riser", self.video_start - 0.55),
              ("whoosh", self.video_start - 0.12)]
        ev += [("chapter", c[0]) for c in self.chapters[1:]]
        ev += [("cut_" + name, t) for t, name in self.cuts if name != "freeze"]
        ev += [("tap", tp["t0"]) for tp in self.taps]
        ev += [("highlight", h["t0"]) for h in self.highlights]
        ev += [("success", t) for t in self.success]
        ev += [("alert", t) for t in self.alerts]
        ev += [("speed", a) for a, b, s in self.speedups if s >= 3.5]
        ev += [("lower_third", lt["out"] + self.video_start) for lt in self.lower_thirds]
        ev += [("freeze", self.freeze_start), ("outro", self.outro_start), ("outro_hit", self.outro_start + 0.25)]
        return sorted(ev, key=lambda x: x[1])


if __name__ == "__main__":
    tl = Timeline()
    vid = tl.freeze_start - tl.video_start
    print(f"duration {tl.duration:.2f}s ({len(tl.frames)} frames)  hook {tl.video_start:.2f}  tutorial {vid:.2f}  "
          f"freeze {tl.freeze_start:.2f}  outro {tl.outro_start:.2f}")
    print("cuts", [(round(t, 2), n) for t, n in tl.cuts])
    for c in tl.chapters:
        print("chapter", round(c[0], 2), c[1], c[2])
    print("speedups", [(round(a, 2), round(b, 2), round(s, 1)) for a, b, s in tl.speedups])
    print("source frames used:", len(tl.used_source_frames()))
