# Technical QA — STAR_SWALLOWED_PLANET_FINAL.mp4
Measured on the exported file (ffprobe, ffmpeg ebur128/blackdetect/cropdetect/freezedetect, npc.qc validator).

| Item | Result |
|---|---|
| Resolution | **1080×1920** (9:16), every frame rendered natively; nothing upscaled |
| Frame rate | **30 fps** constant |
| Codec | **H.264 High**, yuv420p, one final encode (rendered frames → H.264; audio muxed with `-c:v copy`) |
| Video bitrate | **17.9 Mb/s** (target 12–20) |
| Audio | **AAC-LC 48 kHz stereo**, ~268 kb/s, **−14.0 LUFS**, true peak **−1.9 dBTP**, 0 clipped samples |
| Duration / size | **104.3 s** (target 90–105) / **236.6 MB** |
| Black frames / silences / freezes ≥ 1 s | none / none / none |
| Black-bar detector | 3051/3127 frames full-frame. The 76 flagged frames are all in the hook (0.07–2.57 s), where the top of the frame is dark space above the glowing star. There is no letterbox (frame 0 inspected); a dark-sky false positive. Left as is, because fixing it would need a second encode generation. |

## Source resolution
| Asset | Resolution |
|---|---|
| Star photosphere | 6144×3072 granulation map, ≈1:1 at the largest on-screen radius (1,400 px) |
| Gas giant | 4096×2048 texture; largest radius 380 px (downsampled, never enlarged) |
| Star fields | 2× supersampled source plates |
| Galaxy, graphs, captions | rendered at native resolution |

## Motion sharpness (full-resolution frames from the final file)
- **Laplacian variance:** 882 / 969 (hook mid-plunge, 0.50 / 0.533 s), 1,048 / 1,109 (payoff plunge, 64.5 / 64.533 s), 1,119 (aftermath, 78 s).
- **Crops:** 100% crops show crisp planetary bands, gas streamers and stellar granulation during motion. Consecutive frames are equally sharp.

## Opening and sync
- **Frame 0:** a gas giant ploughs into the outer atmosphere of a huge orange star, with "A STAR ATE A PLANET?!" on screen and a single bass impact at 0.00 s. The first word is at 0.00 s.
- **Hook test:** three hook candidates (60 frames each) were compared; A was chosen and strengthened.
- **20-second preview:** rendered and inspected before the full render.
- **Captions:** 2–5-word phrases on the aligned onset of each phrase's first word; Inter Black 68 px, centred at x≈520 (clear of the right-side controls) and y≈1420 (above the bottom UI).

## Not guaranteed
TikTok re-encodes uploads, so final on-platform quality may be lower.
