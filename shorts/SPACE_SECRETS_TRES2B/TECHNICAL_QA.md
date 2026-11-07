# Technical QA — TRES2B_SPACE_SECRETS_FINAL.mp4
Measured on the exported file with ffprobe, ffmpeg's ebur128, blackdetect, cropdetect and freezedetect filters, and the npc.qc validator.

| Item | Result |
|---|---|
| Resolution | **1080×1920** (9:16). Every frame is rendered natively; nothing is upscaled. |
| Frame rate | **30 fps**, constant |
| Codec | **H.264 High**, yuv420p. One final encode: rendered frames go straight to H.264, and the audio is muxed in with `-c:v copy`. |
| Video bitrate | **18.1 Mb/s** (18.4 Mb/s overall; target 12–20) |
| Audio | **AAC-LC 48 kHz stereo**, ~268 kb/s, **−14.0 LUFS**, true peak **−1.8 dBTP**, 0 clipped samples |
| Duration / size | **92.5 s** (target 90–100) / **212.8 MB** |
| Black frames / silences / freezes ≥ 1 s | none / none / none |
| Black-bar detector | **Flags every frame (false positive).** See below. |

**Why the black-bar detector flags every frame:**
- cropdetect thresholds the *average* brightness of each edge row or column.
- This video's brief asked for deep blacks, so the space background sits below that threshold even though stars reach the frame edges. For example, the bottom row of the 13 s frame peaks at a pixel value of 122.
- The frames are drawn edge to edge, and full-resolution frames show no letterbox or pillarbox.
- I left it as is: lifting the blacks would go against the brief and need a second encode.

## Source resolution
| Asset | Resolution |
|---|---|
| Planet | 4096×2048 band texture; largest on-screen radius about 560 px (downsampled, never enlarged) |
| Host star | 6144×3072 granulation map |
| Star fields | 2× supersampled plates |
| Diagrams, illustrations, captions | Drawn at native 1080×1920 |

## Motion sharpness
Laplacian variance, measured on full-resolution frames from the final file:

| Time | Shot | Variance |
|---|---|---|
| 0.5 s | hook | 930 |
| 3 s | paint vs planet | 575 |
| 13 s | name | 1,283 |
| 30 s | light curve | 814 |
| 36 s | albedo bars | 588 |
| 42 s | coal | 653 |
| 50 s | atmosphere | 873 |
| 64 s | glow | 411 |
| 72 s | two kinds of light | 826 |
| 84 s | wide | 989 |
| 91.5 s | final | 1,079 |

- The glow shot scores lowest because most of the frame is a smooth dark disk.
- Planet banding, the stellar granulation, the red rim and the captions all stay crisp while moving.

## Opening and sync
- **Frame 0:** a black planet silhouette in front of a blazing star, with a red atmospheric rim and "DARKER THAN COAL?!" on screen. A bass impact lands at 0.00 s, and the first spoken word starts at 0.00 s.
- **Hook test:** three 60-frame hooks were compared at phone size, and A was chosen.
- **20 s preview:** rendered and inspected. The paint-vs-planet brightness was fixed afterwards.
- **Measurement tones:** they play at the "< 1%" reveal (35.6 s).
- **Captions:** each phrase is 2–6 words and appears on the aligned onset of its first word. They are set in Inter Black, white with yellow emphasis and a black stroke, centred at x≈520 to stay clear of the right-side controls, and at y≈1420 to stay above the bottom 20%.

## Not guaranteed
TikTok re-encodes uploads, so quality on the platform may be lower than this master.
