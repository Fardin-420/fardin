# Flag Shorts: flag-battle physics Shorts generator

One command renders every episode in `episodes.json` to a finished vertical MP4:

```bash
pip install -r requirements.txt      # pymunk, Pillow, numpy, cairosvg  (+ ffmpeg and node/npm on PATH)
python make.py episodes.json         # → out/<slug>.mp4, out/<slug>.txt, out/<slug>.check.png, out/<slug>.report.json
```

`make.py` installs the `flag-icons` npm package on first run (the only download), rasterises its 1x1 SVGs with
cairosvg, searches seeds, renders, synthesises audio, muxes, and verifies the result with ffprobe.

| Option | Effect |
|---|---|
| `--only spain` | only episodes whose slug contains the text |
| `--seed 58` | skip the search and render that seed |
| `--seeds 500` | search more seeds (default 200) |
| `--workers 4` | parallel processes for search and rendering |

## episodes.json

```json
{
  "defaults": { "balls_per_team": 8, "gap_count": 1, "target_seconds": [28, 38], "seeds": 200 },
  "episodes": [
    { "teams": ["ES", "PT", "IT"], "title": "SPAIN VS PORTUGAL VS ITALY. PICK ONE", "hook": "PICK ONE. NO SWITCHING." }
  ]
}
```

`teams` are ISO codes from flag-icons. Optional per episode: `names` (display names), `slug`, and any physics
default from `sim.py` (`gap_start_deg`, `gap_grow_deg_per_s`, `ring_speed`, `gravity`, `min_speed`, …).

## How a fight works (`sim.py`)

- pymunk, fixed 1/240 s steps. The ring is a rotating kinematic body made of 360 wall segments; a gap is a run of
  removed segments. Every ball has the same radius, mass, elasticity and launch speed. Only the seeded start
  positions and directions differ, and team order is shuffled. Nothing in the physics looks at a ball's team.
- A ball whose centre passes the ring radius plus its own radius is out. A country is out at 0 balls. Last country inside wins.
- No stalling: speed is clamped to 520–1500 px/s every frame. The gap widens 0.5°/s and is forced fully open
  shortly before the target maximum, so every run ends inside the target length.
- After the win the gap seals and the sim runs at quarter speed for the 1.2 s winner hold.

## Seed search and drama score

200 seeds are simulated headless (about 15 s on 4 cores). A seed must meet four rules to count as a good episode:

1. total length inside `target_seconds` (28–38 s)
2. at least 3 near-misses (a ball pokes into the gap mouth and comes back, or bounces off the wall within 4° of the gap edge)
3. final duel (two countries left) lasts 4 s or more
4. at 80 % of the fight the eventual winner leads by at most one ball

Among those, the score also rewards a longer duel (up to 8 s), the winner being behind at 80 %, the winner
finishing with 1–2 balls, an even duel start, lead changes, and no long lull without an exit. The best seed is
rendered; the top five and the per-team win counts are printed, and everything is saved in `out/<slug>.report.json`.

## Files

`make.py` CLI, seed search, parallel render, mux, verify, metadata · `sim.py` physics and scoring ·
`render.py` Pillow/numpy frame renderer · `audio.py` numpy soundtrack · `flags.py` flag-icons + cairosvg.

Flag artwork: [flag-icons](https://github.com/lipis/flag-icons), MIT License.
