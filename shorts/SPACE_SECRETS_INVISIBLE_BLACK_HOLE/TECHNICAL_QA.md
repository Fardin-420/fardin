# Technical QA — BLACK_HOLE_SPACE_SECRETS_FINAL.mp4
Measured on the actual exported file with ffprobe, ffmpeg (ebur128, blackdetect, cropdetect, freezedetect) and the npc.qc validator.

| Item | Result | Status |
|---|---|---|
| Resolution | **1080×1920** (9:16), native: every frame rendered at 1080×1920 (no upscaling) | PASS |
| Frame rate | **30 fps** constant (r_frame_rate = avg_frame_rate = 30/1) | PASS |
| Video codec | **H.264 High**, yuv420p, level 4.2, GOP 60, aq-mode 3 | PASS |
| Video bitrate | **18.2 Mb/s** (target 12–20) | PASS |
| Audio | **AAC-LC 48 kHz stereo**, 264 kb/s average (encoded at 320k target) | PASS |
| Loudness / peak | **−14.1 LUFS**, true peak **−1.9 dBFS**, 0 clipped samples | PASS |
| Duration | **85.2 s** (target 85–100) | PASS |
| File size | **196.3 MB** (196,280,232 bytes) | — |
| Black frames / bars / silences / freezes ≥1 s | none / none (2554/2554 full-frame) / none / none | PASS |
| Encode generations | **1**: rendered frames → final H.264; audio muxed with `-c:v copy` | PASS |

## Source resolution (Rule 7)
- **Star fields:** 2800×4600 source plates at **2 source pixels per output pixel**. The lens view maps every output pixel into the plate; it never enlarges.
- **Galaxy and N-body:** rendered directly at 1080×1920 (particles splatted with sub-pixel weights).
- **Earth:** 4096×2048 texture (Solar System Scope, CC BY 4.0); its largest on-screen radius (1050 px) is about 1:1.
- **Hubble cutouts, graphs and captions:** drawn at native resolution.

## Motion sharpness check (full-resolution frames from the final file)
- Laplacian variance, hook mid-sweep: 2,689 (0.500 s) and 3,068 (0.533 s). Galaxy fly-in: 482 / 506 (soft by nature: unresolved galaxy glow). N-body: 957.
- 100% crops show crisp individual stars and lensed arcs during camera motion. Consecutive frames are equally sharp (no motion blur or encoder smearing).

## Opening and sync
- **Frame 0:** the lens is already sweeping across the star field, with the title AN INVISIBLE BLACK HOLE?! and the impact on frame 0 (−6.9 dB RMS in the first 20 ms).
- **First word:** "An" at 0.00 s.
- **Captions:** phrase-based (2–6 words), each appearing on the aligned onset of its first spoken word. Inter Black 70 px, centred at y≈1420, inside TikTok's safe area.

## Not guaranteed
TikTok re-encodes uploads, so the platform may lower the bitrate and sharpness after upload. A high-bitrate, native-resolution master gives its encoder the best possible input, but the final appearance on TikTok is outside our control.

## Limitations
- **No real observatory, NASA or Hubble imagery:** those sites are blocked in this environment, and the brief forbids fake NASA images. All telescope and observatory visuals are labelled CGI reconstructions.
- **Light curve:** a textbook point-lens model (shape only), not the published OGLE data.
