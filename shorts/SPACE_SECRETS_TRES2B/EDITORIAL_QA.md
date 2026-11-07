# Editorial QA — "This Planet Is Darker Than Coal" (TrES-2b)
This is an honest review of the actual render. No virality score is claimed.

## Input note
The brief referred to "the complete original English narration and 10-scene timestamped storyboard supplied above", but neither was attached.
- The narration (NARRATION.txt) and the 18-shot plan (SHOTLIST.csv) were written for this video.
- They keep the mandated opener and follow the brief's science, retention and caption rules.
- Send the original text and it can be re-voiced.

## Hook
| Variant | Frame 0 | Verdict |
|---|---|---|
| **A (chosen)** | A black planet silhouette across a blazing star, with a thin red rim | Instantly readable at 200 px: maximum contrast |
| B | Huge dark limb filling the frame, star at the top right | Too dark; the planet is ambiguous |
| C | Planet beside the star | The planet is small and less striking |

- **On screen and audio:** "DARKER THAN COAL?!" in white and yellow with a thick stroke. A bass impact at 0.00 s; the first word at 0.00 s.

**Hook script score (hookscore.py)**
- **Chosen line, 53 (WEAK):** "This planet is darker than coal. Your black paint reflects more. This world bounces back under 1% of its starlight, at over a thousand degrees. Why?"
- **Rejected alternatives:**
  - "You'd lose it against black paint …" scored 60, but it is misleading. The planet is darker than paint, so it wouldn't be lost against it.
  - "Darker than any black paint you could buy" is false: Vantablack-type coatings are darker.
- **Why it can't reach 72:** the ≥72 target is out of reach with the mandated six-word opener, because the first six words leave no room for "you".

**After the 20 s preview:** the paint-vs-planet shot rendered the planet brighter than the black paint, which contradicted the science. It was fixed so the planet is darker than the paint.

## Retention beats (on the render)
| Time | Beat |
|---|---|
| 0–2 s | Hook |
| 2–10 s | Black paint vs planet; "under 1%" first spoken at 5.4 s |
| 10–26 s | Name and distance; 2.5-day orbit, over 1,000 °C; Kepler 2011 |
| 26–35 s | How Kepler measured it (schematic light curve, ~6.5 ppm) |
| **35.6 s** | **"< 1%" reveal**: albedo bars and measurement tones (target ≤ 30 s) |
| **39–46 s** | **Coal comparison**: darker than coal, black acrylic paint, and any planet or moon (target ~35 s) |
| **46–60 s** | **Atmospheric mystery**: Na, K and TiO proposed; "still a mystery" (target ~45 s) |
| **60.6–70 s** | **Red-glow twist**: thermal glow fades up; stove-coil comparison (target ~60 s) |
| 70–79 s | Reflected vs emitted light; separating the two |
| 79–92.5 s | **Final payoff**: dull-red world racing its star, then "BLACKER THAN COAL" |

- **Missed target:** the full "< 1%" reveal lands at 35.6 s, not by 30 s. The figure itself is spoken and shown at ~5 s.
- **Shot length:** 18 shots, about 5 s on average. The longest is the 8.1 s atmosphere slice, which has new molecules and photons appearing in it.

## Science framing
- **Labels:**
  - Every appearance shot is labelled "CGI · artist's impression".
  - The light curve and the reflected/thermal split are labelled schematic.
  - The Kepler model is labelled "CGI reconstruction · not NASA imagery".
  - The planet is never called invisible or a black hole, and no surface is shown.
- **Before the twist:** pre-twist shots show the planet near-black, with only the thin backlit rim visible.
- **The twist:** the red thermal glow is introduced as heat, explicitly not reflected light.
- **Mystery:** the absorbers are "suspected", and "the real cause is still a mystery".
- **Distance:** ~750 light-years (CfA), not the brief's ~700. This is noted in SCIENCE_SOURCES.md.

## Packaging (/yt-package, title.py)
- **Title:** "This Planet Reflects Under 1% of Light". 38 characters, 100/100, and no word overlap with the cover.
- **Cover:** "DARKER THAN COAL?!", the mandated wording.

## Known weaknesses
- **Style:** the visuals are procedural CGI, not photoreal VFX. AI video generation wasn't available.
- **Weak illustrations:** the coal lump and the paint card are the least convincing visuals.
- **Scale:** the planet is drawn much larger relative to its star than reality (real ratio ≈ 1:8). This is labelled "sizes not to scale".
