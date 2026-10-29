"""One-command production for flat 2D explainer projects.

    python produce_explainer.py PROJECTS/PERSIAN_TWO_DIALECTS_EN            # full render
    python produce_explainer.py PROJECTS/PERSIAN_TWO_DIALECTS_EN --stills   # contact sheet only

narration (Kokoro, measured + word-aligned) → timeline (scenes, captions, cues)
→ sound (score + cue-locked foley, ducked, -14 LUFS) → render (SVG in headless
Chromium) → final/<NAME>.mp4
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(*cmd: str) -> None:
    print("›", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=ROOT)


def main(project: Path, stills: bool) -> None:
    py = sys.executable
    run(py, "VOICE_ENGINE/explainer_narration.py", str(project))
    run(py, "RENDER_ENGINE/pipeline/build_explainer_timeline.py", str(project))
    run(py, "SOUND_ENGINE/explainer_sound.py", str(project))
    run("node", "RENDER_ENGINE/flat2d/render.mjs", str(project), "stills" if stills else "video")


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve(), "--stills" in sys.argv)
