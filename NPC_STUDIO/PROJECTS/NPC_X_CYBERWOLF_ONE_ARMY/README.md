# NPC × CYBERWOLF — TWO SHADOWS. ONE ARMY.

A Brazilian-phonk character edit, made **entirely in code** (Python, NumPy, OpenCV, FFmpeg).
There is no timeline editor anywhere in this project. Every cut, camera move, light, glitch, title and sound is placed on a
measured musical event.

| | |
|---|---|
| Deliverable | `final/NPC_X_CYBERWOLF_ONE_ARMY_FINAL.mp4` (git-ignored; rebuilt by `produce_edit.py`) |
| Video | 1080 × 1920 (9:16), 60 fps, 2239 frames, H.264 High, yuv420p, BT.709 |
| Audio | AAC-LC 320 kb/s, 48 kHz stereo. −10.7 LUFS integrated, −1.15 dBTP |
| Duration | 37.32 s |
| Music | MONTAGEM ELDER (SUPER SLOWED), bar-aligned music edit, original pitch and tempo |

## 1. The music, measured

`EDIT_ENGINE/analyze_music.py` analyses the full 111.7 s track. A stock beat tracker fails on super-slowed phonk:
the 808 is a long gliding tone, swung percussion sits off the grid, and the biggest moments are entrances after
silence. It also measures STFT flux up to 20 ms early, which is more than a frame at 60 fps. So the analysis
runs in the time domain at 1 ms resolution and combines several measures:

* **onset rise**: how many dB the log-energy envelope climbs within 10 ms, summed over full band, highs (>1.5 kHz) and sub (40–160 Hz)
* **tempo**: period from the rise-curve autocorrelation, refined with a comb fit over 100 s → **108.00 BPM** (beat 0.55556 s, bar 2.2222 s)
* **phase**: from the strongest 1.5 % of transients only (they sit on the beat; soft swung hits do not) → beat k at **k × 0.55556 + 0.0059 s**
* per beat: energy jump before/after (dB), sub-bass level, **808 pitch**; per bar: section label and chroma+MFCC similarity
* **manual verification**: waveform and spectrogram plots around every key event (`previews/music_analysis_full.png`).
  The first flux-based phase estimate was 81 ms early, and was rejected after inspecting the waveforms.

### Structure of the full song (source time)

| Section | Beats | Time | Bars |
|---|---|---|---|
| intro (fade-in, soft pulses on beats 2 and 4) | 0–16 | 0.006 – 8.895 s | 4 |
| 808 riser into drop 1 | 16–20 | 8.895 – 11.117 s | 1 |
| drop 1 | 20–52 | 11.117 – 28.895 s | 8 |
| break: bass silent | 52–56 | 28.895 – 31.117 s | 1 |
| riser | 56–60 | 31.117 – 33.340 s | 1 |
| drop 2 (same loop as drop 1, +40 beats) | 60–92 | 33.340 – 51.117 s | 8 |
| breakdown: quiet, beatless | 92–108 | 51.117 – 60.006 s | 4 |
| build: four-on-the-floor kicks | 108–120 | 60.006 – 66.673 s | 3 |
| last build bar + **near-silent gap** (beats 122–123) | 120–124 | 66.673 – 68.895 s | 1 |
| drop 3 | 124–152 | 68.895 – 84.451 s | 7 |
| break: one hit, three silent beats | 152–156 | 84.451 – 86.673 s | 1 |
| drop 4 | 156–188 | 86.673 – 104.451 s | 8 |
| stop + reverb tail | 188– | 104.451 – 111.1 s | — |

The drops share a 2-bar 808 melody: bar **A** = 36.6 / 36.6 / 28.6 / 28.6 Hz and bar **B** = 32.2 / 32.2 / 36.6 / 36.6 Hz.
Bars four apart are 99.5–99.8 % alike in cosine similarity.

### Strong hits vs soft pulses (onset rise; an ordinary drop downbeat is 28.9 dB)

| Source beat | Time | Rise | Jump | What it is |
|---|---|---|---|---|
| 4 | 2.228 s | 26.5 dB | +11.2 dB | music entrance from near-silence |
| 20 | 11.117 s | 14.5 dB | +7.1 dB | drop 1 (the riser leads in, so the rise is softer) |
| 108 | 60.006 s | **52.0 dB** | +18.3 dB | build entrance after the quiet breakdown |
| 120 | 66.673 s | 43.2 dB | +16.8 dB | last build bar |
| 122–123 | 67.78–68.34 s | 13.5 / 7.9 dB | — | the gap: sub drops ~45 dB |
| **124** | **68.895 s** | **55.4 dB** | **+19.7 dB** | **drop 3: the strongest impact in the song** |
| 128 | 71.118 s | 33.1 dB | +16.0 dB | next major impact (bar-2 downbeat) |
| **156** | **86.673 s** | **45.1 dB** | +17.9 dB | **drop 4 after three silent beats: the final strong bass impact** |
| 187 / 188 | 103.896 / 104.451 s | 31.4 / 4.6 dB | — | last hit / the real stop |

## 2. The music edit (22–32 s was not musically possible; 37.3 s is)

No contiguous 22–32 s window of the song holds an intro, a quiet phrase, a real build, the biggest drop **and** a final
impact with an ending. At 108 BPM one bar lasts 2.22 s, and nine sequences with eighteen text beats need about
sixteen bars. So the track is re-edited **on bar downbeats**, the way trailer music is cut. Pitch and tempo are
untouched, and every seam joins bars that are musically interchangeable (same 808 notes and chords as the bar that
naturally precedes the incoming piece). `EDIT_ENGINE/music_edit.py`:

| Video time | Source | Source time | Role |
|---|---|---|---|
| 0.000 – 1.528 s | 0.70 s → beat 4 | 0.700 – 2.228 s | pre-roll (faint fade-in, real sub pulses) |
| 1.528 – 3.750 s | beats 4–8 | 2.228 – 4.450 s | intro bar 1 (music entrance) |
| 3.750 – 5.973 s | beats 16–20 | 8.895 – 11.117 s | intro bar 4 (808 riser) |
| 5.973 – 12.639 s | beats 20–32 | 11.117 – 17.784 s | drop 1 bars 1–3 (A B A) |
| 12.639 – 14.862 s | beats 88–92 | 48.895 – 51.117 s | drop 2 bar 8 (B, bass cuts on the last beat) |
| 14.862 – 17.084 s | beats 92–96 | 51.117 – 53.340 s | breakdown bar 1 |
| 17.084 – 19.306 s | beats 104–108 | 57.784 – 60.006 s | breakdown bar 4 (hats enter) |
| 19.306 – 20.417 s | beats 108–110 | 60.006 – 61.117 s | build entrance (52 dB) |
| 20.417 – 23.750 s | beats 118–124 | 65.562 – 68.895 s | build end + the gap |
| 23.750 – 30.417 s | beats 124–136 | 68.895 – 75.562 s | drop 3 bars 1–3 (A B A) |
| 30.417 – 32.639 s | beats 152–156 | 84.451 – 86.673 s | drop 3 bar 8 (hit, then bass silent) |
| 32.639 – 33.751 s | beats 156–158 | 86.673 – 87.784 s | drop 4 entrance (45 dB) |
| 33.751 – 34.862 s | beats 186–188 | 103.340 – 104.451 s | drop 4 last half bar (same 36.6 Hz note, final hit) |
| 34.862 – 37.312 s | beat 188 + 2.45 s | 104.451 – 106.901 s | the song's real stop and reverb tail |

Seven of the thirteen joins are exact continuations (no crossfade). The six real seams, scored against the song's
own bar-to-bar variation (baseline 1.69 dB):

| Seam | Join | Crossfade | Context mismatch | HF ratio (click test) |
|---|---|---|---|---|
| 3.750 s (f225) | intro bar 1 → bar 4 | 80 ms equal-power | 4.22 dB | 0.92 |
| 12.639 s (f758) | drop 1 bar 3 → drop 2 bar 8 | 15 ms pre-transient | 3.56 dB | 0.72 |
| 17.084 s (f1025) | breakdown bar 1 → bar 4 | 80 ms equal-power | 2.98 dB | 0.97 |
| 20.417 s (f1225) | build half bar → build end | 15 ms pre-transient | 3.94 dB | 0.71 |
| 30.417 s (f1825) | drop 3 bar 3 → bar 8 | 15 ms pre-transient | 1.39 dB | 0.60 |
| 33.751 s (f2025) | drop 4 entrance → last half bar | 15 ms pre-transient | 2.70 dB | 0.77 |

Beat seams end 1 ms after the grid point, before the real transient (4–8 ms later), so every incoming hit plays untouched.

## 3. Event map (video time, 60 fps) — `source/music_events.json`

Every beat has a measured **onset** (where the 10 ms rise reaches 50 %) and an **impact frame**:
`frame = ceil(onset × 60 − 0.6)`, which puts the picture at most 10 ms ahead of the sound and at most 6.7 ms behind it.

| Beat | Onset | Frame | Source | Rise | Used for |
|---|---|---|---|---|---|
| pre | 0.396 s | 24 | pad pulse | sub +16 dB | one frame of NPC |
| pre | 1.119 s | 67 | pad pulse | sub +23 dB | one frame of CYBERWOLF |
| n0 | 1.512 s | 91 | 4 | 26.5 dB | **THEY SEE TWO.** (music entrance) |
| n4 | 3.746 s | 225 | 16 | 19.9 dB | wolf's eyes emerge (riser bar) |
| n8 | 5.967 s | 358 | 20 | 14.8 dB | **drop A**: velocity zoom-out, **CYBERWOLF** |
| n9 | 6.525 s | 391 | 21 | 19.1 dB | THE ONE WHO HOLDS THE LINE. |
| n12 | 8.190 s | 491 | 24 | 31.8 dB | whip → NPC, shirt print lights up |
| n13 | 8.744 s | 525 | 25 | 18.5 dB | THE ONE WHO MOVES IN SILENCE. |
| n15 | 9.856 s | 591 | 27 | 26.8 dB | push into the shirt lettering |
| n16 | 10.412 s | 625 | 28 | 34.2 dB | zoom collision, DIFFERENT MINDS. |
| n17 | 10.955 s | 657 | 29 | 16.1 dB | dark flash cut → NPC |
| n18 | 11.527 s | 692 | 30 | 20.6 dB | glitch cut, SAME CODE. |
| n19 | 12.078 s | 725 | 31 | 27.5 dB | chromatic compression → NPC print |
| n20 | 12.635 s | 758 | 88 | 31.3 dB | split slide → duo, UNBREAKABLE LOYALTY. |
| n23 | 14.302 s | 858 | 91 | 16.1 dB | the bass cuts out, frame dims |
| n24 | 14.855 s | 891 | 92 | 17.7 dB | shadow wipe → Promise, WHEN ONE GOES SILENT... |
| n28 | 17.079 s | 1025 | 104 | 11.2 dB | light reveal → NPC, THE OTHER HOLDS THE LINE. |
| n32 | 19.300 s | 1158 | 108 | **50.5 dB** | build: NO BACKUP. |
| n33 | 19.858 s | 1191 | 109 | 24.7 dB | depth crash → NPC |
| n34 | 20.414 s | 1225 | 118 | 33.6 dB | NO RETREAT. |
| n35 | 20.969 s | 1258 | 119 | 39.8 dB | dark flash → NPC print |
| n36 | 21.523 s | 1291 | 120 | 42.9 dB | JUST TWO. — first dual composition |
| n38 | 22.634 s | 1358 | 122 | 13.1 dB | gap opens: image dims, seam light rises |
| n39 | 23.190 s | 1391 | 123 | 7.8 dB | cut to almost-black, a line of light gathers |
| **n40** | **23.743 s** | **1424** | 124 | **55.8 dB** | **THE DROP**: both revealed, flash, shake, shockwave, TWO SHADOWS. |
| n44 | 25.967 s | 1558 | 128 | 32.4 dB | **ONE ARMY.** lock-in |
| n48 | 28.189 s | 1691 | 132 | 28.5 dB | signature: NPC × CYBERWOLF |
| n49 | 28.747 s | 1725 | 133 | 15.4 dB | BROTHERS. NOT JUST ADMINS. |
| n52 | 30.412 s | 1825 | 152 | 26.5 dB | last hit before the bass goes silent |
| n53 | 30.968 s | 1858 | 153 | 3.9 dB | images shatter away, particles gather |
| n55 | 32.078 s | 1925 | 155 | 24.8 dB | metallic streaks trace the logo ring |
| **n56** | **32.632 s** | **1958** | 156 | **44.9 dB** | **LOGO REVEAL** + energy pulse |
| n59 | 34.300 s | 2058 | 187 | 31.2 dB | final hit: silver glint across the logo |
| n60 | 34.857 s | 2091 | 188 | 5.0 dB | the music stops: TWO MEN. ONE LEGACY. → fade to black at 37.32 s |

## 4. Visual system — `EDIT_ENGINE/`

| Module | What it does |
|---|---|
| `fx.py` | mip-mapped layer sampling, camera with cover-clamp (no frame can ever show an empty edge; a keep-out box keeps the artist mark out of every CyberWolf frame), directional, zoom and velocity blur, bloom, god rays, rim light, light bands, remap-based shockwave, barrel and chroma, glitch strips, block displacement, scanlines, particles, streaks, grain, filmic shoulder |
| `typo.py` | per-glyph FreeType sprites with kerning and animated tracking: kinetic slam, letter assembly, masked reveal, strip fragmentation, directional exit, light shine; white→silver fill, soft shadow, glow, emerald accent glow; auto-fit to a safe width |
| `engine.py` | asset grading (NPC: deep black, charcoal, cold silver, blue shadows. CyberWolf: hue untouched, gunmetal/emerald background), `CharShot` with 2.5D parallax (subject and inpainted plate move at different depths), **motion blur by temporal supersampling of the camera over a 180° shutter** (up to 14 sub-frames, so blur exists only where there is motion), global impact system (punch, shake, flash, chroma, glitch, shockwave, lens pulse) shared by all shots, `DuoShot` (stacked or diagonal panels, each cover-fit to its own panel, with a light seam), `LogoShot`, 9 transitions |
| `render.py` | forked worker pool → raw RGB → libx264 CRF 14, `slow`, High profile, BT.709 tv range |

Transitions used, each on its own musical event: bass impact zoom (drop A), high-velocity directional whip (n12),
zoom collision (n16), dark flash cut (n17, n35), digital glitch cut (n18, n34), chromatic compression (n19),
motion-matched split (n20, n36), fragmented shadow wipe (n24), light-triggered reveal (n28, n48), depth camera
crash (n33), dark digital shatter (n53).

NPC's title is the real shirt print lit in cold silver at the reveal. A separate typeset "NPC" would duplicate it
(no 9:16 framing shows his head without the print), and lighting the print keeps the photograph's own lettering as the hero.

## 5. Sound

The track is the star. `EDIT_ENGINE/mix_audio.py` trims the music by 2 dB (the decoded AAC overshoots to +1.0 dBTP),
adds 11 transition accents 21–32 dB under the music (whip whoosh panned with the motion, zoom air, glitch ticks,
a reverse swell that *ends* where the drop begins, a shatter crumble in the bass-silent bar, a shimmer converging on
the logo). Nothing is placed on top of the drops or the logo hit. A 4× oversampled look-ahead limiter holds −1.0 dBTP;
it acts for 61 ms in total (max 0.15 dB). There is no compression or EQ on the music.

## 6. Reproduce

```bash
cd NPC_STUDIO
pip install opencv-python-headless scipy librosa soundfile pyloudnorm onnxruntime ncnn matplotlib
# place the four files listed in source/ASSETS.md into PROJECTS/NPC_X_CYBERWOLF_ONE_ARMY/source/assets/
python3 EDIT_ENGINE/produce_edit.py PROJECTS/NPC_X_CYBERWOLF_ONE_ARMY --models <dir with esrgan_ncnn/ and isnet-anime.onnx>
python3 EDIT_ENGINE/produce_edit.py PROJECTS/NPC_X_CYBERWOLF_ONE_ARMY --preview      # 540x960 timing check (~2 min)
python3 EDIT_ENGINE/render.py PROJECTS/NPC_X_CYBERWOLF_ONE_ARMY --stills 1424,1558 --scale 1   # single frames
python3 EDIT_ENGINE/review.py final/NPC_X_CYBERWOLF_ONE_ARMY_FINAL.mp4 strip.jpg 23.6:24.0   # frame strip + audio onsets
```

Everything is deterministic (all randomness is seeded), so the same inputs give the same video.
