# NPC VIRAL STUDIO — clip engine (`npc-clip`)

One command takes a long video to vertical shorts that have been edited, quality-checked and packaged.

```bash
./npc-clip --input "VIDEO_FILE_OR_FOLDER_OR_URL" --niche business --clips 12 --platform all \
           --style viral-pro --rights mine --brand
```

| Flag | Meaning |
|---|---|
| `--niche` | **You choose it.** Sets the edit profile (pacing, caption presets, music mood, SFX) and the niche hashtag. Known profiles: `business/podcast/finance`, `comedy/streamer`, `motivation`, `education/science/tech`, `gaming`, `interview/debate/news`. Any other word is still used as your hashtag, with the podcast edit profile. If you leave it out, the engine guesses the niche from the transcript. |
| `--rights` | `mine` · `licensed` · `authorized` · `fair-use` · `unknown` (default). `unknown` stops after analysis. `fair-use` clips render only if they carry original `commentary`. |
| `--style` | `viral-pro` (auto per niche/clip) or a preset key from `./npc-clip styles` |
| `--selection` | JSON list of `{start, end, title, hook, post_caption, hashtags, commentary, cold_open, caption_style}` that replaces auto-selection. This is how a human or agent editor picks clips. |
| `--brand` | Small NPC watermark, only on MINE/LICENSED/AUTHORIZED sources |

Other commands:

```bash
./npc-clip render --project NPC_VIRAL_STUDIO/<NAME> [--clip 3]   # after editing Project/editable_timelines/*.json
./npc-clip feedback --stats perf.csv                              # real analytics → per-decision comparisons
./npc-clip styles                                                 # 15 caption presets
```

## Pipeline

1. **Ingest.** Takes a file, a folder, or a URL (via yt-dlp). Writes `Source/source_metadata.json` and classifies rights.
2. **Transcribe.** NVIDIA Parakeet-TDT 0.6B v2 (int8, sherpa-onnx, CPU) gives punctuated text with word timestamps. Silero VAD splits the audio into chunks.
3. **Analyze.** PySceneDetect finds shots. Audio RMS and spectral flux measure energy. YuNet detects faces, which are tracked with per-face mouth motion to find the active speaker.
4. **Score.** Every 18–55 s window that starts and ends on a sentence is scored on hook 25, retention 20, emotion 15, curiosity 15, standalone 10, visual 10 and loop 5. The engine keeps a pool of distinct candidates (≥20 when the source allows), picks the top N with ≤20 % overlap, and rejects weak windows rather than padding to N.
5. **Plan** (`Project/editable_timelines/NPC_CLIP_XX.json`):
   - Jump cuts on word boundaries remove fillers and dead air but keep short pauses after `?`/`!`.
   - A cold-open teaser is used when a later line is a stronger hook.
   - Framing alternates at cuts. Emphasis words get punch-ins (or slow push-ins on calm profiles).
   - Layout is `track` (speaker-following 9:16 crop), `split` (two speakers), `fit` (full frame over a blurred fill) or `full` (vertical source).
   - Captions and titles are placed inside platform safe zones and kept off faces.
6. **Render.** Frames are composed in OpenCV: grade with LUT and saturation, vignette, zoom blur on punches, whip transition after the teaser. They are piped to x264, and libass burns in the captions and vector graphics: title card, stat callouts, keyword pops, progress bar, attribution, watermark and context card.
7. **Audio.**
   - Segments join with 6 ms crossfades.
   - Dialogue chain: high-pass, light FFT denoise, presence EQ, compressor, loudnorm.
   - The original music bed is synthesized in code, so there are no licensing issues. It ducks −9 dB under speech.
   - Cue-locked SFX come from `SOUND_ENGINE`.
   - Two-pass loudnorm masters to −14 LUFS with true peak ≤ −1.5 dBTP.
8. **QC on the actual MP4**, with automatic repair and re-render where a fix exists:
   - specs, duration and A/V length
   - loudness and true peak
   - black frames, freezes, dead air, letterbox bars
   - faces cut at frame edges, captions over faces
   - caption text vs transcript, plus dictionary flags
   - a contact sheet in `QC/`
9. **Package.** Covers are built from clean, caption-free frames. Writes titles, captions, hashtags, attribution with the disclaimer, `quality_report.json`, `clip_packages.json`, the registry and the ZIP.

## Output

```
NPC_VIRAL_STUDIO/<NAME>/
  Source/source_metadata.json
  Analysis/transcript.json · transcript.txt · scene_analysis.json · face_tracks.json · candidate_scores.csv · selected_clips.json
  Clips/NPC_CLIP_XX.mp4            1080x1920 · 30 fps · H.264 High yuv420p bt709 · AAC 48 kHz stereo
  Covers/NPC_COVER_XX.png
  Metadata/titles.txt · captions.txt · hashtags.txt · source_attribution.txt · quality_report.json · clip_packages.json
  Project/editable_timelines/*.json · editing_config.json
  QC/*_contact_sheet.jpg
  <NAME>_EXPORT.zip
```

## Honest limits

* **Network.** This cloud environment blocks YouTube and Hugging Face. URL downloads work wherever yt-dlp can reach the site; here, upload the file instead. All models come from GitHub releases.
* **Scoring is heuristic.** It uses text, prosody and visuals. For better titles and clip picks, an editor (human or Claude) writes a `--selection` file after reading `transcript.txt`.
* **B-roll.** No stock library is connected, so no stock footage is inserted. Visual support comes from original motion graphics.
* **Commentary.** No voiceover is recorded. Commentary appears as on-screen text cards.
* **No claim protection.** Edits add value but do not protect against copyright claims, Content ID or reused-content limits.
* **QC is automated.** The contact sheets are for visual review; QC does not count as a human review.
