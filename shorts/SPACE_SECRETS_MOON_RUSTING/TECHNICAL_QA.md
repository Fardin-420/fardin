# Technical QA — MOON_RUSTING_SPACE_SECRETS_FINAL.mp4
All results come from the actual exported file (ffprobe, ffmpeg ebur128/blackdetect/cropdetect/freezedetect, and the npc.qc validator).

| Check | Result | Status |
|---|---|---|
| Container / codec | MP4, H.264 High, yuv420p, +faststart | PASS |
| Resolution / aspect | 1080×1920 (9:16) | PASS |
| Frame rate | 30/1 | PASS |
| Duration | 94.200 s (target 85–100) | PASS |
| Video bitrate | 8.5 Mb/s total; file 99.9 MB | PASS |
| Audio | AAC-LC 48 kHz stereo, 256 kb/s | PASS |
| Integrated loudness | −14.1 LUFS (target −14) | PASS |
| True peak | −1.9 dBFS | PASS |
| Clipping | 0 clipped samples | PASS |
| Black frames | none | PASS |
| Silence gaps | none | PASS |
| Letterbox / black bars | 2824/2824 frames full-frame | PASS |
| Frozen picture ≥ 1.0 s | none (the first master froze for 1.7 s at 25.3 s; fixed with a slow spin and push) | PASS |
| First spoken word | "The" at 0.00 s; impact and crack at frame 0 (−9 dB RMS in the first 10 ms) | PASS |
| Caption sync | Each phrase appears on the aligned onset of its first word (energy-dip alignment snapped to the waveform); verified on stills at 2, 3, 5, 15, 18, 20, 31, 39 and 88 s | PASS |
| Caption safe area | Centred at y ≈ 1420 (y ≈ 1180 during the hook, between Moon and Earth); max 900 px wide; never over the main subject | PASS |

## Issues found and fixed during QA
1. **Hook pullback** went through a blurry grey plate with a floating square. Replaced with a radial-blur whip into the Moon.
2. **Pinched lunar poles** on the procedural Moon. Switched to the real NASA-derived albedo map.
3. **Murky low-sun surface shot** and a too-static 3–8 s stretch. Changed to side light with a brisker dolly and a yaw sweep.
4. **Earth sizes** that contradicted the "true apparent size" labels in the telephoto shots. Now computed from 1.9° and the lens FOV.
5. **Repetitive 30–42 s magnetotail block.** Split into three distinct shots: the limb escape, the tail wide, and the reverse angle at the Moon.
6. **Loudness** came out at −11.6 LUFS / 0.0 dBTP on the first master. Replaced with a measured gain plus limiter, verified at −14.1 / −1.9.
7. **Bitrate** below the 8 Mb/s QC floor. Raised to 8.3 Mb/s video.

## Production notes
- **Voice:** Kokoro-82M am_puck, local and offline.
- **Music and SFX:** synthesized in code.
- **Earth texture:** Solar System Scope (CC BY 4.0). **Moon albedo:** three.js moon_1024 (NASA-derived).
- **Everything else** is procedural CGI.
- **No AI video:** the Higgsfield account had 3.28 credits on a free plan, not enough for any AI video generation, so no generative footage was used.
