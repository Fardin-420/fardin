"""NPC Studio — one command from script to verified MP4.

    python produce.py PROJECTS/NPC_NO_EDITOR_JUST_CODE            # full production
    python produce.py PROJECTS/NPC_NO_EDITOR_JUST_CODE --preview  # stop after preview
    python produce.py PROJECTS/NPC_NO_EDITOR_JUST_CODE --allow-no-voice

Pipeline:
  1. narration   VOICE_ENGINE/build_narration.py   (NPC_VOICE_V1, measured timings)
  2. timeline    RENDER_ENGINE/pipeline/build_timeline.py
  3. sound       SOUND_ENGINE/sound_engine.py       (cue-synced SFX, score, ducking, master)
  4. QC stills   RENDER_ENGINE/pipeline/render.mjs stills
  5. preview     540x960 render + QC
  6. final       1080x1920 60 fps render + QC
  7. package     source zip + voice profile config
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

STUDIO = Path(__file__).resolve().parent
PY = STUDIO / "VOICE_ENGINE" / ".venv" / "bin" / "python"
ENGINE = STUDIO / "RENDER_ENGINE"


def step(title: str, cmd: list, cwd: Path = STUDIO) -> None:
    print(f"\n━━ {title}\n   $ {' '.join(map(str, cmd))}", flush=True)
    subprocess.run(list(map(str, cmd)), cwd=cwd, check=True)


def package(project: Path) -> None:
    final = project / "final"
    name = project.name
    zpath = final / "NPC_PROJECT_SOURCE.zip"
    skip = {"node_modules", ".venv", "build", "__pycache__", "models", "frames", "stems", "narration",
            "original_reference", "clean_reference", "voice_tests", "data"}
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(STUDIO.rglob("*")):
            rel = p.relative_to(STUDIO)
            if p.is_dir() or any(part in skip for part in rel.parts) or p.suffix in {".mp4", ".zip", ".wav"}:
                continue
            z.write(p, Path("NPC_STUDIO") / rel)
    cfg = json.loads((STUDIO / "VOICE" / "NPC_VOICE_V1" / "voice_config.json").read_text())
    (final / "NPC_VOICE_PROFILE_CONFIG.json").write_text(json.dumps(cfg, indent=2) + "\n")
    shutil.copy2(STUDIO / "NPC_STUDIO_README.md", final / "NPC_STUDIO_README.md")
    print(f"packaged {zpath.relative_to(STUDIO)} ({zpath.stat().st_size / 1e6:.1f} MB)")


def main() -> None:
    project = (STUDIO / sys.argv[1]).resolve()
    preview_only = "--preview" in sys.argv
    allow_no_voice = "--allow-no-voice" in sys.argv
    timeline = project / "source" / "timeline.json"

    cfg = json.loads((STUDIO / "VOICE" / "NPC_VOICE_V1" / "voice_config.json").read_text())
    if cfg.get("ready_for_cloning"):
        step("1/7 narration (NPC_VOICE_V1)", [PY, "build_narration.py", project], STUDIO / "VOICE_ENGINE")
    elif allow_no_voice:
        print("\n━━ 1/7 narration SKIPPED — NPC_VOICE_V1 not ready: " + "; ".join(cfg.get("issues", [])))
        print("   Rendering a PRE-VOICE cut (sound design only). No substitute voice is used.")
    else:
        sys.exit("NPC_VOICE_V1 is not ready (" + "; ".join(cfg.get("issues", [])) +
                 "). Register a longer recording, or pass --allow-no-voice for a pre-voice cut.")

    step("2/7 timeline", [PY, ENGINE / "pipeline" / "build_timeline.py", project])
    step("3/7 sound design + mix", [PY, STUDIO / "SOUND_ENGINE" / "sound_engine.py", project])
    step("4/7 QC stills", ["node", "pipeline/render.mjs", project, "stills", "--quality", "0.5"], ENGINE)
    step("5/7 preview render", ["node", "pipeline/render.mjs", project, "preview", "--quality", "0.5"], ENGINE)
    step("    preview QC", [PY, ENGINE / "pipeline" / "qc.py", project / "previews" / f"{project.name}_PREVIEW.mp4", timeline])
    if preview_only:
        return
    step("6/7 final render", ["node", "pipeline/render.mjs", project, "final"], ENGINE)
    voiced = json.loads(timeline.read_text())["voiced"]
    final = project / "final" / f"{project.name}_FINAL{'' if voiced else '_PREVOICE'}.mp4"
    qc = [PY, ENGINE / "pipeline" / "qc.py", final, timeline]
    step("    final QC", qc + ([] if allow_no_voice else ["--expect-voice"]))
    step("7/7 package", [PY, "-c", f"import produce; produce.package(__import__('pathlib').Path(r'{project}'))"])


if __name__ == "__main__":
    main()
