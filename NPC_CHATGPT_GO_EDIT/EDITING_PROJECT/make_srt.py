"""Write ../CAPTIONS/NPC_CHATGPT_GO_CAPTIONS.srt from the timeline's caption track.

The recording has no speech, so these are the on-screen step captions (not a transcript).
"""
from pathlib import Path

from timeline import Timeline


def ts(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


tl = Timeline()
cues = [(0.1, tl.video_start - 0.05, " / ".join(tl.edl["hook"]["title"]))]
cues += [(c["t0"], c["t1"], c["text"]) for c in sorted(tl.captions, key=lambda c: c["t0"])]
cues += [(tl.outro_start + 0.3, tl.duration - 0.05, " / ".join(tl.edl["outro"]["lines"]))]
out = []
for i, (a, b, text) in enumerate(cues, 1):
    out += [str(i), f"{ts(a)} --> {ts(b)}", text, ""]
p = Path(__file__).parent.parent / "CAPTIONS" / "NPC_CHATGPT_GO_CAPTIONS.srt"
p.write_text("\n".join(out), encoding="utf-8")
print("wrote", p, len(cues), "cues")
