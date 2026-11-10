# Country Flag Battle Royale (YouTube Short)

16 flag balls fight in a spinning neon arena. When two collide, the **faster** ball damages the slower one;
0 HP shatters it. A small gap in the wall slowly rotates, and any ball that falls through is eliminated.
When two are left, the gap welds shut for the final duel. That duel ends in slow motion, and then the winner's flag fills the screen.

| File | What it does |
|---|---|
| `battle.html` | Single-file sim + Canvas 2D renderer + live preview. **Country list at the top** (`[name, flag-icons code]`). `?seed=123` or `?winner=Brazil`; Space / R / ←→ / N (new random winner). Exposes `window.renderFrame(n)`, `searchSeed()`, `getEvents()`. |
| `embed_flags.mjs` | Embeds the flag-icons 1x1 SVGs for the listed countries into `battle.html` (run automatically by `render.mjs`). |
| `render.mjs` | Seed search → headless Playwright render (parallel workers, per-frame progress) → ffmpeg H.264 → `audio.py` → AAC mux → `qa.py`. NVENC/GPU raster if available. |
| `audio.py` | numpy/scipy soundtrack: 128 BPM groove that builds as countries drop, impact-scaled hit thumps on the exact collision frame, glass shatters, crowd-style build + riser + snare roll for the duel, fanfare + cheer for the winner; −14 LUFS, −1 dBTP. |
| `qa.py` | Specs, loudness, fight rules, UI overlap, 8-frame contact sheet, audio↔collision sync. |

```bash
cd NPC_STUDIO/PROJECTS/FLAG_BATTLE
npm install                              # flag-icons (MIT)
pip install numpy scipy pillow           # + Playwright/Chromium + ffmpeg
node render.mjs --winner Japan           # → final/final.mp4, qa/contact_sheet.png, qa/report.json
node render.mjs --seed 601               # a specific fight
node render.mjs --winner Brazil --search-only
```

## Fairness
Every ball has the same radius (46 px), mass, HP (100) and launch speed (640 px/s), and the same energy target.
Only the start position and launch direction differ, and both come from the seeded RNG. Physics: fixed 1/240 s substeps, gravity 520 px/s²,
elastic ball/wall collisions, damage = 0.0058 × impact speed. From 38 s damage ramps up (+3.5 %/s) and is ×1.35 in the duel.
The whole fight is simulated once and recorded per substep, so slow motion and `renderFrame(n)` replay exactly the same fight.

## Seed search ("good fight" rules)
`--winner X` simulates seeds 1, 2, 3 … (≈5 ms each) and takes the first one where X wins **and** the fight
ends on a collision, combat lasts 33–47 s, nobody is out during the hook, both duellists are ≤ 60 HP when it becomes 1v1,
the winner finishes with ≤ 35 HP, the duel lasts 2.5–9 s, and there are at least 6 knock-outs and at least 1 escape.

Flag artwork: [flag-icons](https://github.com/lipis/flag-icons) © 2013 Panayiotis Lipiridis, MIT License.
