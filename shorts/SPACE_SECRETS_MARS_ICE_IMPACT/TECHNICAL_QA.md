# Technical QA — MARS_ICE_IMPACT_FINAL.mp4
Measured on the exported file with ffprobe, the ffmpeg detection filters (ebur128, blackdetect, cropdetect, freezedetect, silencedetect) and the npc.qc validator.

| Item | Result |
|---|---|
| Resolution | **1080×1920** (9:16), native render; no source enlarged |
| Frame rate | **30 fps** constant |
| Codec | **H.264 High**, yuv420p, one final encode (frames → H.264; audio muxed with `-c:v copy`) |
| Video bitrate | **17.7 Mb/s** (overall 17.9 Mb/s; target 12–20) |
| Audio | **AAC-LC 48 kHz stereo**, ~267 kb/s, **−14.0 LUFS**, true peak **−1.8 dBTP**, 0 clipped samples |
| Duration / size | **92.8 s** (target 90–100) / **208.0 MB** |
| Black frames / freezes ≥ 1 s | none / none |
| Black-bar detector | **2782/2782 frames full-frame** (pass) |
| Silence | One deliberate **0.61 s** silence at 56.6–57.2 s, just before "Blocks of water ice". No other gaps. |

## Real-image resolution (never upscaled)
| Asset | Source pixels | On screen |
|---|---|---|
| HiRISE PIA25583 | 1013×1080 real area | 1:1 native panel; a brief scale-in from 0.45× to 1× at 51 s |
| CTX PIA25584 | 5448×3523 | Ken Burns from 1.8 to 1.0 source px per output px; 1:1 at the crater |
| MARCI PIA25585 | 851×1080 per panel | 1:1 |
| PIA25582 / PIA23177 | 976×942 / 1024×1024 | 1:1 panels |
| InSight selfie PIA25287 | 4391×2635 | Scaled down (1.06 source px per output px) |

## Sharpness
Laplacian variance on full-resolution frames from the final file:

| Time | Shot | Variance |
|---|---|---|
| 0.2 s | Impact | 743 |
| 0.6 s | HiRISE | 1,271 |
| 12 s | Selfie | 510 |
| 16 s | Seismic graphic | 404 |
| 27 s | MARCI | 773 |
| 33 s | CTX | 2,832 |
| 41 s | Cross-section | 421 |
| 47 s | Reconstruction | 1,007 |
| 56 s | Boulders | 1,481 |
| 57.8 s | Ice | 649 |
| 75 s | Icons | 1,207 |
| 91 s | Final | 1,296 |

- At phone size the HiRISE ice blocks, CTX rays and captions are crisp.
- No extra sharpening was applied.

## Opening and sync
- **Frame 0:** impact flash (labelled reconstruction) with "ICE UNDER MARS?!" on screen.
- **Snap cut at 0.5 s** to the real HiRISE ice image.
- **Audio:** bass impact at 0.00 s and a crack on the cut.
- **First spoken word:** at 0.00 s.
- **Testing:** three 60-frame hook variants were compared at phone size, and A was chosen. A 20-second preview was rendered and inspected; the meteoroid entry was fixed afterwards.
- **Captions:**
  - 2–6-word phrases, timed to the aligned onset of each phrase's first word.
  - Inter Black, white with #FFD400 emphasis and a black stroke.
  - Centred at x≈520 (clear of the right-side controls) and y≈1420 (above the bottom 20%).
  - Captions overlap the lower edge of some photo panels, but the stroke keeps them readable.

## Not guaranteed
TikTok re-encodes uploads, so on-platform quality may be lower than this master.
