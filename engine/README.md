# Time Ghost engine

This is a code-only 2D animation engine for the *Time Ghost* series. It is built with Python 3, pycairo, numpy/scipy, edge-tts and ffmpeg.

```bash
pip install pycairo numpy scipy edge-tts pillow   # plus ffmpeg on PATH
python render.py episodes/L001            # build narration + mix, render full MP4, write .srt, run QC
python render.py episodes/L001 --stills   # 2 preview stills per scene -> episodes/L001/build/stills
python render.py episodes/L001 --test 30  # first 30 s only
python render.py episodes/L001 --shorts   # 3 vertical Shorts (shorts.json)
python render.py episodes/L001 --thumbs   # thumbnails (thumbs.json)
python render.py episodes/L001 --captions # burn subtitles into the long-form render
```

| Module | What it does |
|---|---|
| `core.py` | Easing (including back/elastic overshoot), keyframe `Track`, deterministic noise, colours, global time-of-day lighting |
| `rig.py` | Stickman skeleton (forward kinematics) and 45+ poses: idle, walk, run, sneak, crouch_hide, point, jump_scared, cover_mouth, hands_on_head, laugh, sit, sleep, climb, look_around, plus era tasks (knap, cook, butcher, smash, aim, throw…). Also the expression set and face drawing |
| `character.py` | Actors with action tracks. Covers blend overshoot, foot-locked walk phase, breathing, hoodie sway, auto-blink, lip-flap, reaction pops (squash and stretch), and speech bubbles. Fardin gets a ghost glow, a semi-transparent body and the cyan watch. Era people get varied skin, hair, hide wraps, brow ridge and held items |
| `animals.py` | Gazelle, hyena and lion, with walk/run/graze/prowl/dead states and glowing night eyes |
| `props.py` | Procedural props: campfire with flame and sparks, smoke, fire light pools, acacia, rocks, cliff with cave, bones, flakes, grass beds, ochre, hide rack, carcass, modern room |
| `scene.py` | Parallax sets (sky, far, mid, ground, foreground), time-of-day palettes (dawn, morning, day, golden, dusk, night, cave), weather (dust, rain, snow, embers, fireflies), camera (keys, tracking, reaction push-ins, shake). Fardin is drawn outside the world lighting so his red hoodie is always the brightest element |
| `graphics.py` | Animated maps (Africa and world), timeline bar, fact cards with count-up, skull comparison, then-vs-now table, chapter and era title cards, list, tags, callouts, watch clock HUD, subscribe card, time tunnel, FX (flash, ripple, speed lines, letterbox, danger pulse, watch bloom) |
| `audio.py` (narration) | `voice: "kokoro:<voice>"` → local Kokoro ONNX (model in `$KOKORO_DIR`, default `~/kokoro`; `rate` = speed factor). Word timings come from faster-whisper `base.en` when available, else a letter-weighted spread snapped to the real pauses. Other voice names still use edge-tts |
| `audio.py` (score) | `music_score()`: tempo-locked 100 BPM 4/4 score in absolute time (kick, taiko, shaker, bass, arp, strings, swells per mood). Same-mood scenes join seamlessly, with crossfades only on mood changes. Music sits ~10.5 dB under narration and ducks under speech. Two-pass EBU R128 loudnorm to −15 LUFS / −1.6 dBTP |
| `audio.py` | edge-tts narration with word timings (cached). Procedural SFX (whoosh, fire, wind, footsteps, crowd murmur, hyena whoop/giggle, growl, knap, bone crack, pops, rumble, riser…), ambience beds, a mood-based music pad, voice ducking and mastering |
| `build.py` | script.json → timeline.json. Times each scene from the measured narration and resolves word cues (`"cue": "w:spear"`). Writes mix.wav and the SRT. If `narration.mp3` exists it uses that file instead (timings scaled), and `music.mp3` is added with ducking |
| `renderer.py` | Renders frames in parallel chunks (multiprocessing → ffmpeg H.264 veryfast, CRF 18, yuv420p). Joins the chunks with concat and muxes AAC. Also handles vertical reframing and word-by-word captions |
| `shorts.py` / `thumbs.py` / `qc.py` | Shorts (2 s hook, captions, end card), thumbnails, and QC (resolution, length, A/V sync, silence and freeze detection) |

Every visual is a pure function of time and all randomness is seeded, so any frame renders identically in any process.
