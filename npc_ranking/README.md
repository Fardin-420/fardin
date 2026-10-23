# NPC Ranking Shorts Factory

Config-driven pipeline that turns licensed source footage into a finished vertical Top-N ranking Short:
sources → analysis → voice → captions → motion graphics → sound design → render → mux → QC.

```
python3 run.py                    # full run with config.json
python3 run.py other.json         # another video, same pipeline
python3 run.py --preview          # still frames at 10/40/75% of every segment -> work/pv/
python3 run.py --skip-voice       # reuse work/voice/ (when only visuals or audio changed)
python3 run.py --skip-voice --mux-only   # re-encode/re-master without re-rendering frames
```

Requirements: ffmpeg, Python 3 with `numpy scipy pillow soundfile opencv-python-headless kokoro-onnx`, and the Kokoro
model files (`kokoro-v1.0.onnx`, `voices-v1.0.bin` from github.com/thewh1teagle/kokoro-onnx releases,
tag `model-files-v1.0`). Set their paths in `config.json → voice`.

## Modules (`npc/`)
| file | job |
|---|---|
| `analyze.py` | probe, scene cuts, motion energy, cross-file sync offsets, timestamped contact sheets (`python3 -m npc.analyze file.mp4`) |
| `track.py` | subject tracking for reframing: template matching or motion centroid, smoothed |
| `voice.py` | Kokoro TTS per line, trim, word timing from energy dips, fit check per segment |
| `render.py` | timeline + speed maps + freezes, tracked crop/zoom, blurred backdrop, NPC graphics (progress dots, rank badge, number slam, chips, rings, arrows, end card), whip transitions, impact frames, captions |
| `audio.py` | 120 BPM score with section modes (full / filtered / off / drop), SFX library, original clip audio time-mapped to every speed ramp, VO ducking |
| `qc.py` | ffprobe/ffmpeg validation: codec, size, fps, duration, bitrate, loudness, true peak, black frames, silences, black bars, clipping |

## What the config controls
- `category`, `title_card`, `end_card`, `end_vo`, `credit`: content and attribution
- `segments[]`: number of clips and their order. Each has `rank`, `label`, `vo`, and `pieces` (source in/out + speed,
  or `{"freeze": t, "dur": d}`). Segment length is derived from its pieces.
- per segment camera: `track` (box + method) or `focus` keyframes, `zoom` keyframes, `lift` (shadow lift), `fx`
  (`flash`, `chip`, `ring`, `arrow`, `shake`, `freeze_glow`, `endcard`; ring/arrow can `follow` the tracked subject)
- `voice`: engine paths, `voice_id`, `speed`, `lead_in`
- `captions`: font, size, stroke, colors, y position, max width/lines
- `style`: accent color, panel geometry, fonts, `transition_len`
- `sound`: `bpm`, music / clip-audio / SFX levels, duck amount
- `export`: size, fps, `bitrate` (or `crf`), `maxrate`, audio bitrate, loudness target, true-peak ceiling
- `sources`: key → file, sync `offset`, download `url` (fetched automatically when missing)

## Rights rule
Only use footage you own or that is licensed for reuse (e.g. CC BY with the credit line on screen). Record URL,
license and timestamps in the video's `SOURCE_LINKS.txt`.
