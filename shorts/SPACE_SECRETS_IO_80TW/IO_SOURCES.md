# Sources — "Io: 80 Trillion Watt Hotspot"
NASA image captions were read directly from images-api.nasa.gov. Other sources were checked through search-indexed copies, because jpl.nasa.gov and nasa.gov can't be opened from this build machine.

## Primary
- **NASA/JPL release, 28 Jan 2025:** "NASA's Juno Mission Spots Most Powerful Volcanic Activity on Io to Date" — https://www.jpl.nasa.gov/news/nasa-juno-mission-spots-most-powerful-volcanic-activity-on-io-to-date/
- **NASA captions** for PIA26527 "Massive Hot Spot on Io" (28 Jan 2025), PIA26594 "Juno's JIRAM Captures Hot Spots on Io" (29 Apr 2025), PIA26526 "Three Views of Io's Southern Hemisphere" (28 Jan 2025).

## Claim → source → status
| Claim (narration / screen) | Source | Observed or interpretation |
|---|---|---|
| Juno flyby of Io on Dec 27, 2024 (PJ68); ~74,400 km closest approach | PIA26527 / PIA26526 captions | Observed |
| JIRAM = Juno's infrared imager (Italian Space Agency) | PIA26527 caption | Fact |
| Hot spot near Io's south pole, so strong it saturated the detector | JPL release (A. Mura quote); PIA26594 caption ("such a strong signal that it saturated the sensor") | Observed |
| Most powerful volcanic activity seen on Io to date | JPL release title | NASA statement |
| Area ~100,000 km² (40,000 sq mi), larger than Lake Superior | JPL release; PIA26527 caption | Measured estimate |
| Previous record: Loki Patera ~20,000 km² → "five times" | JPL release | Arithmetic |
| Radiated power well above 80 trillion watts (80 TW) | JPL release | Measured; a lower bound because of saturation |
| Lake Superior ~82,100 km² (used for the to-scale square) | Standard geography | Reference value |
| **Heat, not electricity:** 80 TW > 20× average global electric power | Global generation ≈ 30,000 TWh/yr (Ember Global Electricity Review 2024: ~29,900 TWh in 2023) → ≈ 3.4 TW average; 80 / 3.4 ≈ 23 | My calculation, labelled on screen |
| **Several eruptions close together, likely fed by one giant magma chamber** | JPL release ("multiple eruptions, likely fueled by a single giant magma chamber") | **Interpretation**, labelled INTERPRETATION / simulation |
| Juno can't see beneath the surface; no subsurface image exists | JIRAM measures surface thermal emission | Framing |
| Tidal heating: the Io–Europa–Ganymede 1:2:4 (Laplace) resonance keeps Io's orbit eccentric, so Jupiter's tides flex Io | Standard planetary science (Peale, Cassen & Reynolds 1979, *Science*; NASA Io overview) | Established |
| Io's orbital period 1.77 days ("every day and a half") | Standard | Fact |
| Solid-body tide up to ~100 m | Widely cited NASA/JPL figure for Io's tidal bulge | Rounded, labelled "up to ~100 m", vertical exaggeration |
| Io about the size of our Moon (radius 1,822 km vs 1,737 km) | Standard | Fact (Io is slightly larger) |
| Most volcanically active world known | NASA | Established |

## Constraints followed
- **Not electricity:** the video never calls the 80 TW electricity. It says so explicitly and labels the comparison "heat".
- **No subsurface image:** the magma chamber is a labelled simulation and interpretation, never a photo.
- **No invented lava lake:** no single giant lava lake is drawn. The cluster shows several sources, as NASA describes.
- **No fake Io audio:** all sounds are synthetic sound design.

## Hook score (hookscore.py, /yt-script)
- **Chosen:** "NASA detected eighty trillion watts. Not from a power plant, but from a hot spot on Jupiter's moon Io." scores **38 (WEAK)**.
- **Rejected:** a 40-point variant implied electricity, and a 37-point variant claimed Io is smaller than our Moon, which is false.
- **The ≥72 target** isn't reachable with the mandated opener.
