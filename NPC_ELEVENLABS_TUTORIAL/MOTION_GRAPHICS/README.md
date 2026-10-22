# MOTION_GRAPHICS

All motion graphics are procedural and rendered per frame by `EDITING_PROJECT/render.py` with the
primitives in `EDITING_PROJECT/gfx.py`: kinetic intro typography with glitch reveals and light streaks,
particle field, step badges and chapter cards, focus rectangles with spotlight dimming, tap ripples,
fast-forward badge, word-pop captions with keyword emphasis, NPC lower third, watermark, outro.
Nothing is pre-rendered, so the layers are regenerated from code on every build.
