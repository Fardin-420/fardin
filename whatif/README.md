# What If… — vertical viral video series

Format matched to the reference: 9:16 (576×1024, 30fps), opening question title, a big
**WORLD POPULATION** counter at mid-left with a time label (DAY 1 → YEAR N), short
italic serif captions, cinematic cuts with a dip to black, ambient drone + boom sound,
and a black end card with a share CTA.

| Video | Hook | Length |
|---|---|---|
| `out/whatif_men.mp4` | What if every Man on Earth disappeared? | ~76s |
| `out/whatif_bees.mp4` | What if every Bee on Earth disappeared? | ~63s |
| `out/whatif_internet.mp4` | What if the Internet disappeared forever? | ~63s |

## Rendering

```bash
python3 engine.py men      out/whatif_men.mp4
python3 engine.py bees     out/whatif_bees.mp4
python3 engine.py internet out/whatif_internet.mp4
```

Needs Python 3 + Pillow + NumPy + ffmpeg. The scripts (captions, counters, scene
types, durations) are in `stories.py`. Edit them to add new stories.

## Upgrading to 3D AI footage

To get the stylized 3D look of the reference, generate one 5s vertical clip per scene
with an AI video model, then put the overlay on top. Base style prompt for every scene:

> stylized 3D animation, soft low-poly characters with simple faces, cinematic lighting,
> volumetric light, shallow depth of field, slow dolly camera push-in, vertical 9:16,
> moody color grade, no text

Then add the scene: e.g. "Times Square at night, huge New Year crowd, half of the
people suddenly vanish leaving clothes on the ground"; "empty hospital corridor with red
alarm lights"; "Paris square full of candles at a night vigil"; "red stock market screen
crashing"; "teal glowing sperm-bank lab with cryo tubes"; "a girl alone by a small light
in the snow at night".
