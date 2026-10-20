"""One command from assets to verified MP4 for a beat-synced photo edit.

    python produce_edit.py <project> [--models DIR] [--preview]

  1. analyze_music.py   full-song analysis       -> source/music_analysis_full.json (+ plot)
  2. music_edit.py      bar-aligned music edit   -> audio/music_edit.wav, source/music_events.json
  3. prep_assets.py     restore / matte / plates -> source/prepared/*   (skipped when present)
  4. mix_audio.py       sound design + master    -> audio/mix.wav
  5. render.py          frames -> H.264 + AAC    -> final/<NAME>_FINAL.mp4 (or previews/ with --preview)
  6. qc.py              delivery checks          -> final/<NAME>_FINAL.qc.json
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(*args):
    print("$", " ".join(str(a) for a in args), flush=True)
    subprocess.run([sys.executable, *map(str, args)], check=True)


def main(argv):
    proj = Path(argv[1]).resolve()
    plan = json.loads((proj / "source/edit_plan.json").read_text())
    run(HERE / "analyze_music.py", proj / plan["music"], proj / "source/music_analysis_full.json",
        "--plot", proj / "previews/music_analysis_full.png")
    run(HERE / "music_edit.py", proj)
    if not (proj / "source/prepared/cyberwolf_up.png").exists():
        models = argv[argv.index("--models") + 1] if "--models" in argv else None
        if not models:
            sys.exit("prepared assets missing: pass --models <dir with esrgan_ncnn/ and isnet-anime.onnx> (see README)")
        run(HERE / "prep_assets.py", proj, "--models", models)
    run(HERE / "mix_audio.py", proj)
    if "--preview" in argv:
        run(HERE / "render.py", proj, "--preview", "--scale", "0.5")
        return
    run(HERE / "render.py", proj, "--final")
    run(HERE / "qc.py", proj, proj / "final/NPC_X_CYBERWOLF_ONE_ARMY_FINAL.mp4")


if __name__ == "__main__":
    main(sys.argv)
