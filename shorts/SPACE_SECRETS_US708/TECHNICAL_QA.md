# Technical QA — US708_SPACE_SECRETS_FINAL.mp4
Measured on the exported file with ffprobe, the ffmpeg detection filters (ebur128, blackdetect, cropdetect, freezedetect) and the npc.qc validator.

| Item | Result |
|---|---|
| Resolution | **1080×1920** (9:16), every frame rendered natively; nothing upscaled |
| Frame rate | **30 fps** constant |
| Codec | **H.264 High**, yuv420p; one final encode (rendered frames → H.264; audio muxed with `-c:v copy`) |
| Video bitrate | **18.1 Mb/s** (overall 18.4 Mb/s; target 12–20) |
| Audio | **AAC-LC 48 kHz stereo**, ~267 kb/s, **−14.0 LUFS**, true peak **−1.9 dBTP**, 0 clipped samples |
| Duration / size | **93.4 s** (target 90–100) / **214.9 MB** |
| Black frames / silences / freezes ≥ 1 s | none / none / none |

### Black-bar detector
- **Result:** 2731 of 2800 frames are full-frame.
- **Flagged frames:** all 69 are in the hook (0–2.3 s), where the bottom ~330 rows are dark space beneath the galaxy.
- **Checked:** frame 0 has no letterbox, so this is a dark-sky false positive.
- **Left as is:** fixing it would mean a second encode generation.

## Source resolution
| Asset | Resolution |
|---|---|
| Milky Way | 3D particle model, rasterised at native resolution every frame |
| US 708 photosphere | 6144×3072 granulation map, tinted blue-white |
| Star fields, ejecta, diagrams, captions | Procedural or vector, native 1080×1920; star plates supersampled 2× |

## Motion sharpness
Laplacian variance on full-resolution frames from the final file:

| Time | Shot | Variance |
|---|---|---|
| 0.5 s | Hook | 402 |
| 4 s | Chase | 766 |
| 12 s | Galaxy | 539 |
| 41 s | Binary | 462 |
| 55.5 s | Blast | 786 |
| 58 s | Blast | 866 |
| 66 s | Remnant | 1,203 |
| 84 s | Coast | 964 |
| 91 s | Final | 348 |

- **Lower-scoring shots:** the hook and final shots score lower because large areas are smooth dark space.
- **What stays crisp:** galaxy particles, ejecta filaments and captions.
- **Soft spot:** the star's surface is soft at the largest sizes (speed and coast shots).

## Opening and sync
- **Frame 0:**
  - A blue-white star above the Milky Way disk, with a wake leading back to it.
  - "ESCAPING THE GALAXY?!" on screen.
  - An impact and a whoosh at 0.00 s.
  - The first spoken word at 0.00 s.
- **Testing:** three 60-frame hook candidates were compared at mobile size, and A was chosen. A 20-second preview was rendered and inspected; after it, the name shot was given a push-in and a cut.
- **Captions:** 2–6-word phrases, timed to each phrase's aligned first-word onset. Inter Black, white with yellow emphasis and a black stroke. Centred at x≈520 (clear of the right-side controls) and y≈1420 (above the bottom 20%).

## Not guaranteed
TikTok re-encodes uploads, so on-platform quality may be lower than this master.
