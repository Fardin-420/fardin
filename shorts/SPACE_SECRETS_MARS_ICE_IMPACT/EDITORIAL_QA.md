# Editorial QA — "Something Hit Mars, and Exposed Buried Ice"
This is an honest review of the actual render. No virality score is claimed.

## Input note
The brief referred to "the complete 210-word English narration and 10-scene timestamped storyboard supplied above". Neither was attached.

- **Narration:** I wrote it for this video (248 words, 89.4 s). It keeps the mandated opener ("Something slammed into Mars, and exposed buried ice"); the em dash is spoken as a comma pause. Send the original and it can be re-voiced.
- **Network:** real NASA images needed a network change. The user approved the "fardin" environment, which allows images-assets.nasa.gov, images-api.nasa.gov and uahirise.org.

## Hook
| Variant | Cut to the real photo | Verdict |
|---|---|---|
| **A (chosen)** | 0.5 s | The impact flash and expanding ring read for 15 frames, then a snap cut to the real HiRISE ice crater. The payoff is on screen by 0.5 s. |
| B | 0.9 s | Longer CGI; the real photo arrives later |
| C | 0.33 s | The flash is too brief to read at phone size |

- **On screen:** "ICE UNDER MARS?!" from frame 0. A bass impact plays at 0.00 s, with a crack on the snap cut. The first spoken word is at 0.00 s.
- **Hook script score (hookscore.py):** 33 (WEAK).
  - It is low because the brief mandates the whole first sentence, and the second sentence is factual setup ("closer to the equator than anyone had ever found it … no one saw the impact happen").
  - The ≥72 target is not reachable with the mandated opener.
- **Preview fix:** the 20 s preview showed an empty frame before "no one saw". The meteoroid now enters on screen.

## Retention beats (on the render)
| Time | Beat | Target |
|---|---|---|
| 0–3 s | Impact → real ice photo | 0–2 s |
| **8.8–25 s** | **Marsquake**: InSight (real), seismometer (real), seismic data graphic (real), M4, first surface waves | 10–25 s |
| 25–29 s | MRO weather camera before/after (real) | |
| **29–44 s** | **Crater discovery**: CTX image (real), 150 × 21 m to scale | 30–45 s |
| 44–51 s | Impact reconstruction (labelled) | |
| **54–59 s** | **Water-ice reveal**: real HiRISE. A sudden silence (music, ambience and SFX cut) before "Blocks of water ice" at 57.3 s. | 45–60 s |
| 59–70 s | Frozen water, lowest latitude record, Oct 27, 2022 announcement | |
| **70–85 s** | **Significance**: water, food, fuel; a resource; caveat (frozen, not liquid; extent unknown) | 60–80 s |
| 85–92.8 s | **Payoff**: strike echo, then the real ice, then "ICE UNDER THE DUST" | Final 10 s |

- **Shots:** 20 shots plus 6 in-shot cuts, about 4 s on average. The longest is 8.7 s (CTX zoom), which has three label reveals.
- **Image mix:** real NASA imagery fills about 45% of the runtime. The rest is labelled reconstruction, schematic or illustration.

## Science and labelling
- **Real images:** every real NASA frame has "REAL NASA IMAGE · PIA#####" and a credit line. Every CGI impact frame says "RECONSTRUCTION · not real footage" (or "the impact was not filmed").
- **Wording:** frozen water, not liquid; ice extent unknown. The Oct 27, 2022 date and both *Science* papers are mentioned.
- **InSight audio:** InSight's sonified recording exists (PIA25582), but the sound effects here are synthetic and not presented as Mars audio. The PIA25582 image is used only as a visual.

## Packaging (/yt-package, title.py)
- **Title:** "A 150 m Crater Exposed Frozen Water". 35 characters, scores 100/100, with no word overlap with the cover.
- **Cover:** "ICE UNDER MARS?!" over the real HiRISE crater at native resolution.

## Known weaknesses
- **Image size:** the HiRISE ice image is only 1013×1080 of real pixels in the NASA library copy. It is shown at native size in a frame on a dark backdrop, not full-bleed. Enlarging it to fill 1080×1920 would break the no-upscaling rule.
- **Reconstruction:** the impact reconstruction is procedural and stylised (flash, ring, ejecta) rather than photoreal.
- **Diagrams:** the surface-wave and latitude diagrams are simple schematics.
