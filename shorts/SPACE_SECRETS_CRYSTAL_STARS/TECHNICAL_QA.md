# Technical QA — CRYSTAL_STAR_SPACE_SECRETS_FINAL.mp4
Measured on the exported file (ffprobe, ffmpeg ebur128/blackdetect/cropdetect/freezedetect, npc.qc validator).

| Item | Result |
|---|---|
| Resolution | **1080×1920** (9:16), every frame rendered natively; nothing upscaled |
| Frame rate | **30 fps** constant |
| Codec | **H.264 High**, yuv420p, one final encode (rendered frames → H.264; audio muxed with `-c:v copy`) |
| Video bitrate | **18.1 Mb/s** (overall 18.4 Mb/s; target 12–20) |
| Audio | **AAC-LC 48 kHz stereo**, ~267 kb/s, **−14.0 LUFS**, true peak **−1.9 dBTP**, 0 clipped samples |
| Duration / size | **99.3 s** (target 90–100) / **228.3 MB** |
| Black frames / silences / freezes ≥ 1 s | none / none / none |
| Black-bar detector | 2874/2977 frames are full-frame. The 103 flagged frames are all in 0–3.5 s (the hook and the star-field shot), where the bottom 38 rows are dark space. Frame 0 was inspected: there is no letterbox, so this is a dark-sky false positive. Left as is, because fixing it would need a second encode generation. |

## Source resolution
| Asset | Resolution |
|---|---|
| White dwarf, cutaway, lattice, graphs, captions | Vector or procedural, drawn at native 1080×1920 |
| Red-giant photosphere | 6144×3072 granulation map (downsampled, never enlarged) |
| Earth | 4096×2048 textures, on-screen radius 210 px |
| Star fields | 2× supersampled source plates |

## Motion sharpness (full-resolution frames from the final file)
Laplacian variance: 626 (hook, 0.5 s), 642 (crystal front sweep, 36.8 s), 1,964 (lattice orbit, 41 s), 1,210 (pile-up build, 58 s), 909 (floating crystals, 80 s), 727 (ending, 95 s). Lattice points, labels and captions stay crisp during motion.

## Opening and sync
- **Frame 0:** an open white-dwarf cutaway with a glinting crystal core, "STARS TURN INTO CRYSTALS?!" on screen, and a single bass impact plus chime at 0.00 s. The first spoken word is at 0.00 s.
- **Hook test:** three hook candidates (60 frames each) were compared at thumbnail size; C was chosen.
- **20-second preview:** rendered and inspected; shot 2 was split afterwards.
- **Captions:** 2–6-word phrases on each phrase's aligned first-word onset; Inter Black, white with yellow emphasis and a black stroke. Centred at x≈520 (clear of the right-side controls) and y≈1420 (above the bottom 20%).

## Not guaranteed
TikTok re-encodes uploads, so final on-platform quality may be lower than this master.
