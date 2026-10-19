# NPC STUDIO — code-only cinematic video engine

Every frame, transition, effect, sound, and timing in NPC videos comes from code here.
There is no timeline editor. One command takes a script to a verified MP4.

```
NPC_STUDIO/
  produce.py                 one-command production (narration → timeline → sound → render → QC → package)
  VOICE/NPC_VOICE_V1/        permanent NPC voice profile (recordings git-ignored, private)
  VOICE_ENGINE/              Chatterbox TTS pipeline: register, test, narrate, speaker-similarity gate
  SOUND_ENGINE/              numpy/scipy synthesis: impacts, risers, glitches, metal, electricity, drones, ducking, master
  RENDER_ENGINE/             Remotion + Three.js/WebGL + GLSL scenes, DOM typography, render & QC scripts
  BRAND/                     fonts (Inter Display, JetBrains Mono, OFL), logos/, visual_identity/
  CONFIG/                    brand.json (palette, rules), studio.json (render/audio defaults)
  PROJECTS/<NAME>/           source/script.json → timeline.json, audio/, previews/, final/
```

## How a video is made

1. **Script**: `PROJECTS/<NAME>/source/script.json` holds lines, emotions, pauses and scene assignment.
2. **Narration**: `VOICE_ENGINE/build_narration.py` speaks each line in NPC_VOICE_V1 using that line's emotion settings, keeps the take closest to your voice, and **measures** the real durations.
3. **Timeline**: `RENDER_ENGINE/pipeline/build_timeline.py` derives scene bounds and ~30 named **cues** (`title_slam`, `capcut_break`, `explode`…) from the measured line times. It is the single source of timing truth.
4. **Sound**: `SOUND_ENGINE/sound_engine.py` places every sound on a cue, so no sound plays without a visual event. Bed and effects duck under the voice (−9 dB / −5 dB). The master goes to −14 LUFS. It also writes `envelope.json` (per-frame RMS plus a 24-band spectrum) for audio-reactive visuals.
5. **Render**: `RENDER_ENGINE/pipeline/render.mjs` bundles the Remotion project and renders headless Chromium WebGL with a post-process stack (bloom, shockwave refraction, block glitch, directional and zoom motion blur, chromatic aberration, grade, grain). The silent video is muxed with the master mix via ffmpeg.
6. **QC**: `RENDER_ENGINE/pipeline/qc.py` checks ffprobe specs, frame count, A/V duration, black frames, freezes, loudness and clipping, and whether the voice is present.

Every value on screen is a pure function of time. Frames render in parallel and out of order, and re-running the code reproduces the video exactly (seeded randomness throughout).

## Commands

```bash
cd NPC_STUDIO
# one-time setup
(cd RENDER_ENGINE && npm install)
(cd VOICE_ENGINE && uv venv --python 3.11 .venv && uv pip install --python .venv/bin/python chatterbox-tts librosa soundfile pyloudnorm)

# voice (once — reused forever)
VOICE_ENGINE/.venv/bin/python VOICE_ENGINE/register_voice.py ~/my_voice.m4a
(cd VOICE_ENGINE && .venv/bin/python voice_test.py)

# produce
VOICE_ENGINE/.venv/bin/python produce.py PROJECTS/NPC_NO_EDITOR_JUST_CODE
VOICE_ENGINE/.venv/bin/python produce.py PROJECTS/NPC_NO_EDITOR_JUST_CODE --preview         # fast check
VOICE_ENGINE/.venv/bin/python produce.py PROJECTS/NPC_NO_EDITOR_JUST_CODE --allow-no-voice  # pre-voice cut
```

`produce.py` refuses to make a final cut without NPC_VOICE_V1 unless you pass `--allow-no-voice`.
Even then the file is named `*_FINAL_PREVOICE.mp4` and contains **no** substitute narrator.

## New videos

Copy `PROJECTS/NPC_NO_EDITOR_JUST_CODE`, edit `source/script.json`, add or adapt scene modules
in `RENDER_ENGINE/src/scenes/` (each one is `update(ctx) → post params`, with cues coming from the timeline),
and run `produce.py`. The voice profile, brand palette, fonts, sound library and post stack are shared.

## Showreel: NPC — NO EDITOR. JUST CODE.

| Scene | Lines | Technique |
|---|---|---|
| 01 Impossible opening | "Look closer." | Blinking terminal cursor, charge-up, GPU energy ring, spark burst, shockwave refraction; 3D extruded chrome "THIS WASN'T EDITED." flies in from depth with zoom blur, spring squash and stretch, camera shake, and a travelling red rim light |
| 02 Break the rules | Premiere / CapCut / After Effects | Names set in NPC chrome type (no logos). A red laser cut slices each one. Premiere: particle assembly, then **velocity displacement**. CapCut: Y-axis spring flip-in, then **digital fragmentation** (quantized row tearing plus post block glitch). After Effects: X-rotation rise, then **particle disintegration** into embers with a **shockwave**. Lateral **camera whips** with banking and directional blur |
| 03 Every frame is code | 4 lines | Fly-through corridor of 30 panels textured with **this engine's real source code**. ~27k glyph particles detach and assemble a geodesic shell. A chrome 9:16 frame slams past with a barrel roll. The shell re-forms into a torus-knot structure. Kinetic DOM typography |
| 04 Voice reveal | "…That's mine." | 120-bar radial spectrum, 4 rings, 5 layered waveforms, and a particle halo, **all driven by envelope.json**; halo morphs into the NPC symbol |
| 05 No timeline | 3 lines | 340 synchronized layer slabs collapse into one luminous line, which charges, then detonates into chrome "JUST CODE." with shockwave, rays and particle blast |
| 06 NPC identity | "This is NPC. Built with Claude Code." | 30k metallic particles in a vortex assemble the procedural monogram (chrome ring, NPC letters, red cursor callback); orbit settles frontal; light sweep; tagline lockup |

## Known constraints in the build environment

* No GPU: WebGL runs on SwiftShader (`NPC_GL=swangle`). On a GPU machine, set `NPC_GL=angle` for much faster renders.
* The network policy blocked `huggingface.co` here, so Chatterbox weights could not be downloaded in-session (see `VOICE/NPC_VOICE_V1/README.md`).
