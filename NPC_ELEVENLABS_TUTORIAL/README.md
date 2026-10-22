# NPC — ElevenLabs 1-Month Creator Tier tutorial (edit package)

A raw phone screen recording, edited into a branded NPC tutorial entirely in code (Python,
OpenCV, NumPy, FFmpeg, RapidOCR). No timeline editor was used.

| Folder | Contents |
|---|---|
| `FINAL/` | `NPC_ELEVENLABS_FINAL_9x16.mp4` (1080x1920) and `NPC_ELEVENLABS_FINAL_16x9.mp4` (1920x1080), H.264 + AAC |
| `CAPTIONS/` | `NPC_ELEVENLABS_CAPTIONS.srt` (step captions; the source has no speech) |
| `THUMBNAIL/` | `NPC_ELEVENLABS_THUMBNAIL.png` (16:9) and `NPC_ELEVENLABS_COVER_9x16.png` |
| `PUBLICATION/` | `NPC_ELEVENLABS_POST.txt` (title, description, steps, Telegram caption, pinned comment), `NPC_ELEVENLABS_EDIT_REPORT.txt` |
| `EDITING_PROJECT/` | All source code + `edl.json` (the edit decision list) and `edl_resolved.json` |
| `PRIVACY_MASKS/` | `masks.json`: per-frame mask rectangles (geometry only, no text) |
| `ANALYSIS/` | Per-frame activity scan and QC results for both exports |
| `AUDIO/` | Mix stem (git-ignored; rebuilt by `audio.py`) |
| `MOTION_GRAPHICS/`, `BRANDING/` | Notes on where the motion graphics and brand assets live |
| `PREVIEW/` | Review contact sheets made from the masked exports |
| `SOURCE/` | Notes only: the raw recording is private and never committed |

## Pipeline (`EDITING_PROJECT/build.py`)

1. `ocr_scan.py`: OCR of every source frame, plus on-screen keyboard detection. The output holds raw text, so it stays in a private directory.
2. `privacy.py`: per-frame opaque masks for the account e-mail, profile answers and the on-screen keyboard while private data is typed. Masks are dilated ±4 frames.
3. `resolve_edl.py`: locates buttons and offer lines named in `edl.json` by OCR. Zooms, highlights and tap ripples land on real UI.
4. `audio.py`: original synthesized score + SFX on timeline events, mastered to −14 LUFS / −1.5 dBTP.
5. `render.py`: masks are burned into the source first, then camera, motion graphics, captions, intro and outro.
6. `qc.py`: specs, decode errors, black/frozen frames, loudness, and an OCR privacy scan of **every** exported frame.
7. `thumbnail.py`, `report.py`: covers and the edit report.

```bash
cd NPC_ELEVENLABS_TUTORIAL/EDITING_PROJECT
python build.py /path/to/source.mp4 /private/scratch/dir
```

Brand: NPC. Palette `#080808` / `#F5F5F0` / `#FF3038`, Inter Display + JetBrains Mono (OFL, in `NPC_STUDIO/BRAND/fonts`).
