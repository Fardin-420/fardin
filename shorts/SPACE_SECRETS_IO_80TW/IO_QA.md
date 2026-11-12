# QA — IO_80_TRILLION_WATTS_FINAL.mp4
Measured on the exported file: ffprobe, ffmpeg (ebur128 / blackdetect / cropdetect / freezedetect / silencedetect), the npc.qc validator, and frame review. No virality is promised.

## Technical
| Item | Result |
|---|---|
| Resolution | **1080×1920** (9:16), native render; no source enlarged except the labelled raw-JIRAM-pixel views |
| Frame rate | **30 fps** constant |
| Codec | **H.264 High**, yuv420p, one final encode (frames → H.264; audio muxed with `-c:v copy`) |
| Video bitrate | **17.8 Mb/s** (overall 18.1 Mb/s; target 12–20) |
| Audio | **AAC-LC 48 kHz stereo**, ~269 kb/s, **−14.0 LUFS**, true peak **−1.4 dBTP**, 0 clipped samples |
| Duration / size | **94.2 s** (target 90–100) / **212.9 MB** |
| Black frames / black bars / freezes / silences | none / 2824 of 2824 full-frame / none / none |

### Revision
- **First export:** had an unintended 0.57 s near-black frame at 24.7 s (an empty diagram before its square appeared), and the true peak was −0.9 dBTP.
- **Fix:** both were corrected. The video was re-rendered from frames, so it is still a single encode.

### Sharpness
Laplacian variance from the first export, on the same frames:

| Shot | Time | Variance |
|---|---|---|
| Hook | 0.0 s | 1,048 |
| Flyby | 9 s | 544 |
| JIRAM disc | 16 s | 1,382 |
| Record | 22 s | 735 |
| 80 TW | 36 s | 855 |
| Saturation | 47 s | 669 |
| Chamber | 59 s | 643 |
| Squeeze | 72 s | 452 |
| Tidal heating | 82 s | 415 |
| Payoff | 93 s | 983 |

- **Captions and diagrams:** crisp at phone size.
- **JIRAM imagery:** soft by nature, because the data has low native resolution.

## Hook (first 2 s): three variants at phone size
| Variant | Frame 0 | Verdict |
|---|---|---|
| A | Hotspot at ~1.7 source px per output px, pulling back | Good |
| B | Wide static disc; the hotspot is small | Weak on a phone |
| **C (chosen)** | Extreme close-up of the saturated hotspot (1.15 source px per output px), pulling back toward the disc | Most immediate |

- **On screen:** the real JIRAM data (PIA26527) from frame 0, with the caption "80 TRILLION WATTS?!".
- **Sound:** a deep bass impact at 0.00 s, then the thermal-scan sweep at 0.08 s. The voice starts at 0.00 s.
- **Gate frames (0.0 / 0.1 / 0.5 / 1.0 / 2.0 s):**
  - The hotspot is recognisable on a muted phone.
  - Only the one caption block is on screen.
  - The scan bar is visible at 0.1–0.5 s.

## Retention beats (render)
| Time | Beat | Target |
|---|---|---|
| 0–2.2 s | Numerical hook on real data | 0–2 s |
| 2.2–24.6 s | Io (JunoCam), Juno flyby on Dec 27, 2024, raw JIRAM, the hotspot overwhelming the sensor, "most powerful" (NASA, Jan 2025) | 2–20 s |
| 24.6–49.5 s | ~100,000 km² vs Lake Superior; 5× Loki Patera; 80+ TW; heat, not electricity (>20× global electric power); sensor saturated | 20–40 s (ends 9 s late) |
| 49.5–61.5 s | Several eruptions → one magma chamber? (INTERPRETATION, simulation) | 40–55 s |
| 61.5–85.6 s | Why so hot: Jupiter + Io (real); 4:2:1 resonance; eccentric squeeze; ~100 m tide; tidal heating over a real JunoCam + JIRAM composite | 55–75 s |
| 85.6–94.2 s | A new record, back on the real hotspot; "80 TRILLION WATTS" | 75–100 s |

- **Pacing:** 20 shots plus 1 in-shot cut, about 4.6 s on average. The longest is the 7.6 s flyby, which includes a cut to raw JIRAM. Each shot has a new composition.

## Science: observed vs interpretation
- **Observed and labelled real:** date, instrument, saturation, area, power (a lower bound) and record status.
- **Labelled interpretation:** several eruptions and a single magma chamber. These are shown as a schematic and simulation, never as an image of the subsurface.
- **Heat vs electricity:** the 80 TW is never called electricity, and the comparison is stated as heat.
- **No invented lava:** no giant lava lake was invented.
- **Sound:** no Io sounds. All sound effects are synthetic.

## Script and packaging
- **Narration:** the "provided above" narration and storyboard were not attached. This narration was written for the video: 257 words, with the mandated opener.
- **Hook score (hookscore.py):** 38 (WEAK). Higher-scoring variants were rejected for accuracy, as explained in IO_SOURCES.md.
- **Title (/yt-package):** "A 100,000 km² Hot Spot Appeared on Io" (37 characters, title.py 100/100).
- **Cover:** IO_TIKTOK_COVER.png. Real JIRAM disc on black with a bloom on the hotspot, and the headline only.

## Honest limits
- **JIRAM resolution:** low native resolution, so infrared shots look soft.
- **Simulations:** the Juno model and the orbit/tide diagrams are simple CGI.
- **Platform:** TikTok re-encodes uploads, so on-platform quality may be lower than this master.
