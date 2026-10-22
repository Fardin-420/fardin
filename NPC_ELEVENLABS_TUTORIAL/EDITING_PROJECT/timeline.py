"""Output timeline derived from the EDL: every output frame knows what source moment it shows.

All timing used by the renderer and the sound design comes from here, so picture and audio
cannot drift apart.
"""
import json
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).parent


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


@dataclass
class Frame:
    i: int
    t: float          # output seconds
    kind: str         # intro | video | freeze | outro
    src: float = 0.0  # source seconds (video / freeze)
    seg: int = -1
    speed: float = 1.0


class Timeline:
    def __init__(self, edl_path=HERE / "edl_resolved.json"):
        e = self.edl = json.loads(Path(edl_path).read_text())
        self.fps = fps = e["fps"]
        self.frames = []
        n = round(e["intro"] * fps)
        for k in range(n):
            self._add("intro")
        self.video_start = len(self.frames) / fps
        self.seg_start = []
        for si, s in enumerate(e["segments"]):
            self.seg_start.append(len(self.frames) / fps)
            n = round((s["out"] - s["in"]) / s["speed"] * fps)
            for k in range(n):
                self._add("video", s["in"] + k * s["speed"] / fps, si, s["speed"])
        self.freeze_start = len(self.frames) / fps
        for k in range(round(e["freeze"]["duration"] * fps)):
            self._add("freeze", e["freeze"]["src"], len(e["segments"]))
        self.outro_start = len(self.frames) / fps
        for k in range(round(e["outro"] * fps)):
            self._add("outro")
        self.duration = len(self.frames) / fps

        # Hard cuts: boundaries where the source jumps.
        self.cuts = []
        segs = e["segments"]
        for a, b in zip(range(len(segs) - 1), range(1, len(segs))):
            if segs[b]["in"] - segs[a]["out"] > 0.05:
                self.cuts.append(self.seg_start[b])

        self.camera = sorted(
            [(self.src_to_out(k["src"]), k["fx"], k["fy"], k["z"]) for k in e["camera"]]
            + [(self.freeze_start + k["ft"], k["fx"], k["fy"], k["z"]) for k in e["freeze_camera"]])
        self.chapters = [(self.src_to_out(c["src"]), c["num"], c["title"]) for c in e["chapters"]]
        self.chapters[0] = (self.video_start, *self.chapters[0][1:])
        self.highlights = ([dict(h, t0=self.src_to_out(h["src"])) for h in e["highlights"]]
                           + [dict(h, t0=self.freeze_start + h["ft"]) for h in e["freeze_highlights"]])
        self.taps = [dict(tp, t0=self.src_to_out(tp["src"])) for tp in e["taps"]]
        self.success = [self.src_to_out(s) for s in e["success"]]
        self.captions = []
        for c in e["captions"]:
            if "src" in c:
                a, b = self.src_to_out(c["src"][0]), self.src_to_out(c["src"][1], end=True)
            else:
                a, b = self.freeze_start + c["ft"][0], self.freeze_start + c["ft"][1]
            self.captions.append(dict(c, t0=a, t1=b))
        self.lower_thirds = e["lower_thirds"]
        self.speedups = [(self.seg_start[i], self.seg_start[i] + (s["out"] - s["in"]) / s["speed"], s["speed"])
                         for i, s in enumerate(segs) if s["speed"] > 1.01]

    def _add(self, kind, src=0.0, seg=-1, speed=1.0):
        i = len(self.frames)
        self.frames.append(Frame(i, i / self.fps, kind, src, seg, speed))

    def src_to_out(self, t, end=False):
        segs = self.edl["segments"]
        for i, s in enumerate(segs):
            if t < s["in"]:
                # inside a cut: snap to the next kept moment (or the end of the previous one)
                if end and i > 0:
                    p = segs[i - 1]
                    return self.seg_start[i - 1] + (p["out"] - p["in"]) / p["speed"]
                return self.seg_start[i]
            if t <= s["out"]:
                return self.seg_start[i] + (t - s["in"]) / s["speed"]
        return self.freeze_start

    def cam(self, t, ramp=0.75):
        kf = self.camera
        if t <= kf[0][0]:
            return kf[0][1:]
        for a, b in zip(kf, kf[1:]):
            if a[0] <= t < b[0]:
                r = min(ramp, (b[0] - a[0]) * 0.8)
                u = ease((t - (b[0] - r)) / r) if r > 0 else 1.0
                return tuple(a[j] + (b[j] - a[j]) * u for j in (1, 2, 3))
        return kf[-1][1:]

    def chapter(self, t):
        cur = self.chapters[0]
        for c in self.chapters:
            if t >= c[0]:
                cur = c
        return cur

    def sound_events(self):
        """Every sound cue, each tied to a visual event of the timeline."""
        ev = [("intro", 0.0), ("intro_hit", 0.55), ("intro_out", self.video_start - 0.25)]
        ev += [("chapter", c[0]) for c in self.chapters]
        ev += [("cut", t) for t in self.cuts]
        ev += [("tap", tp["t0"]) for tp in self.taps]
        ev += [("highlight", h["t0"]) for h in self.highlights]
        ev += [("success", t) for t in self.success]
        ev += [("speed", a) for a, b, s in self.speedups if s >= 2.5]
        ev += [("lower_third", lt["out"] + self.video_start) for lt in self.lower_thirds]
        ev += [("freeze", self.freeze_start), ("outro", self.outro_start), ("outro_hit", self.outro_start + 0.45)]
        return sorted(ev, key=lambda x: x[1])


if __name__ == "__main__":
    tl = Timeline()
    print(f"duration {tl.duration:.2f}s  frames {len(tl.frames)}  video {tl.video_start:.2f}  "
          f"freeze {tl.freeze_start:.2f}  outro {tl.outro_start:.2f}")
    for c in tl.chapters:
        print("chapter", round(c[0], 2), c[1], c[2])
    print("cuts", [round(c, 2) for c in tl.cuts])
