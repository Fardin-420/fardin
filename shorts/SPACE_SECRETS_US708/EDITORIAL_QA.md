# Editorial QA — "This Star Is Escaping the Milky Way" (US 708)
An honest review of the actual render. No virality score is claimed.

## Input note
The brief referred to "the complete original English narration and 10-scene timestamped storyboard provided above", but neither was attached.

- The narration (NARRATION.txt) and the 17-shot plan (SHOTLIST.csv) were written for this video.
- They keep the mandated opener and follow every science and retention rule in the brief.
- Send the original text and it can be re-voiced.

## Hook
| Variant | Frame 0 | Verdict |
|---|---|---|
| **A (chosen)** | Oblique Milky Way disk filling the lower frame; a big blue-white star above it, with a glowing wake leading back to the disk | Reads as "star leaving the galaxy" at 200 px |
| B | Nearly edge-on disk | Flatter; the galaxy is less recognisable |
| C | Face-on spiral with a small star | Galaxy reads well, but the star is tiny on mobile |

- **Headline:** "ESCAPING THE GALAXY?!" (white and yellow, thick stroke).
- **Sync:** bass impact and whoosh at 0.00 s; the first word is at 0.00 s.

### Hook script score (hookscore.py)
**Final hook unit:** "This star is escaping our galaxy. You could never catch it: it's moving 2.7 million miles per hour. So what threw it?"

| Draft | Score | Note |
|---|---|---|
| **Final hook unit (above)** | **58 WORKABLE** | Chosen |
| First draft | 43 WEAK | Rewritten |
| "You'll never see it again" version | 58 | Rejected as misleading: telescopes will keep seeing it for millions of years |

- The ≥72 target can't be reached: the mandated six-word opener leaves no room for "you" in the first six words.

### After the 20 s preview
- The name shot held one angle for 9 s.
- Fix: a camera push-in, then a cut to a closer angle at "faster than the Milky Way's gravity can hold".

## Retention beats (on the render)
| Time | Beat |
|---|---|
| 0–2.2 s | Hook |
| **4.2 s** | **Speed reveal**: 2.7 million mph (spoken and on screen) |
| 7.6–16.6 s | US 708 located in the halo; ≈1,200 km/s; unbound |
| 16.6–21 s | The usual suspect: the central black hole |
| **23–30 s** | **Mystery**: the traced path misses the centre and comes from the disk |
| 28.7–38.9 s | A strange star: helium-rich, spinning fast; "a close partner?" |
| **39 s** | **Twist**: helium star plus white dwarf, one orbit in minutes |
| **53.1 s** | **Type Ia detonation** (reconstruction); the partner is released (54–61 s); sling diagram |
| **62.6–71.6 s** | **Caveat**: "NO ONE SAW IT", scientific reconstruction (speed, path, makeup) |
| 71.6–81.7 s | Case not closed: two speed estimates; still fast enough to escape |
| 81.7–86.2 s | Not speeding up: coasting |
| 86.2–93.4 s | **Final payoff**: the whole galaxy behind a lone star; "GONE FOREVER" |

- **Shot rhythm:**
  - 17 shots plus one in-shot cut.
  - Average shot length is about 5.5 s.
  - The longest shot is the 8.6 s binary, which has label and headline reveals inside it.

## Science framing
- **Labels:** every supernova and binary frame is labelled "SCIENTIFIC RECONSTRUCTION", and the speed streaks are "artistic".
- **Wording:**
  - The origin is "the leading explanation".
  - The ending says "the case isn't closed", and shows the later, lower speed estimates.
  - No acceleration is shown, and the narration says "It isn't speeding up".
- **Black hole:** depicted only as the ruled-out "usual suspect" and labelled separately. It is never confused with US 708.

## Packaging (/yt-package, title.py)
- **Title:** "What Threw This Star at 2.7 Million MPH?". 40 characters, scores 100/100, no word overlap with the cover.
- **Cover:** "ESCAPING THE GALAXY?!" (mandated wording, 3 words).

## Known weaknesses
- **Style:** the CGI is procedural and stylised rather than photoreal NASA-grade VFX. AI video generation wasn't available in this environment (Higgsfield credits are insufficient), so the "premium photorealistic" goal is only partly met.
- **Speed shot:** the star's surface looks soft at large sizes.
