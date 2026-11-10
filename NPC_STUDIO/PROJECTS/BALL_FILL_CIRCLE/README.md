# 1 Ball → Fill the Circle (YouTube Short)

One ball in a glowing circle. Every wall hit splits it in two: 1 → 2 → 4 → … → 2048.
Then the wall cracks and everything bursts out in slow motion. "Part 2?"

| File | What it does |
|---|---|
| `sim.html` | Single-file deterministic sim + Canvas 2D renderer. Open it in a browser for a live preview (click for sound; Space pause, R restart, ←/→ seek 5 s). Exposes `window.renderFrame(n)`, `getEvents()`. |
| `render.mjs` | Headless Playwright render → ffmpeg (H.264) → `audio.py` → mux (AAC) → `qa.py`. Uses NVENC + GPU raster when an NVIDIA/DRI device exists, otherwise libx264 + software raster. Parallel segment workers. |
| `audio.py` | numpy/scipy synthesis from the logged hit frames: pentatonic marimba/glass notes (≤ 20/s, merged hits), whoosh build, cracks, boom + shimmer, bell. BS.1770-4 loudness to −14 LUFS, true-peak limiter at −1 dBTP. |
| `qa.py` | Specs, loudness, contact sheet (0/5/10/18/26/29 s), escape / glow / title / counter checks, A/V sync measured on the AAC track decoded from the MP4. |

```bash
cd NPC_STUDIO/PROJECTS/BALL_FILL_CIRCLE
pip install numpy scipy pillow          # Playwright + Chromium + ffmpeg required
node render.mjs                          # → final/final.mp4, qa/contact_sheet.png, qa/report.json
node render.mjs --skip-video             # redo audio + mux + QA only
```

## Physics
- Seeded RNG (mulberry32), 4 fixed substeps per frame (1/240 s; scaled uniformly during the slow-mo finale).
- Gravity 480 px/s², perfectly elastic wall reflection, equal-mass elastic ball–ball impulses with a spatial hash.
- Split rule: a wall hit (normal speed > 35 px/s) spawns a twin with the tangential velocity mirrored and a ±8.6° random
  twist. Splits are allowed in waves (quota 2, 4, 8 … every 2.3 s, cap 2048) so the count doubles on a beat;
  2048 is reached at ~25.9 s.
- All balls share one radius, `58 · N^-0.26` (58 px → 8 px), eased as N grows, so the circle reads as packed at the end.
- A gentle energy thermostat keeps the swarm lively (position correction would otherwise bleed energy and let it puddle).
- Nothing leaves the circle before 27 s: the wall projection is a hard constraint, audited every frame (`stats` in `events.json`).

## Timeline
0.55 s first split · doubling every 2.3 s · 25.9 s 2048 balls · 27.0 s cracks + shake + whoosh peak · 27.8 s shatter, flash,
boom, slow motion (0.16×) · 28.55 s "Part 2?".
