import re
# GJ 367 b narration (/yt-script). {DISPLAY|spoken}. (text, gap_after, speed)
LINES = [
 ('A star ate its own planet.', 0.35, 0.95),
 ("You'd never guess why: in {2025,|twenty twenty-five,} NASA's Webb found the star wasn't dying. So how did it happen?", 0.45, 0.96),
 ('{12,000|Twelve thousand} light-years away, in the constellation Aquila, a star suddenly flared up in {2020.|twenty twenty.}', 0.3, 0.95),
 ('For about ten days, it blazed far brighter than normal. Then it faded, but kept glowing in infrared for months.', 0.45, 0.95),
 ('Astronomers named it {ZTF SLRN-2020.|Z T F, S L R N, twenty twenty.}', 0.4, 0.93),
 ('In {2023,|twenty twenty-three,} a team announced the first direct evidence of a star swallowing a planet, most likely a gas giant, roughly the size of Jupiter.', 0.3, 0.95),
 ('Their explanation: an aging star, swelling into a red giant, had engulfed the planet in its path.', 0.45, 0.95),
 ('Then the James Webb Space Telescope took a closer look.', 0.25, 0.95),
 ('And Webb found a twist.', 0.45, 0.9),
 ('The star was too faint to be a red giant.', 0.3, 0.95),
 ("It's most likely a star still in the prime of its life, slightly smaller and cooler than our Sun.", 0.4, 0.95),
 ("So the star didn't grow to reach the planet. The planet fell into the star.", 0.45, 0.93),
 ('Its orbit probably shrank over a very long time, each lap a little closer than the last.', 0.3, 0.94),
 ("Until it grazed the star's outer atmosphere, and plunged in.", 0.45, 0.93),
 ('The star blasted gas away from its outer layers. As that gas expanded and cooled, it formed dust.', 0.45, 0.95),
 ('And Webb found what was left: hot molecular gas, including carbon monoxide, still glowing close to the star,', 0.25, 0.95),
 ('surrounded by colder dust, farther out.', 0.45, 0.93),
 ('These pictures are reconstructions. To Webb, the whole system is a single point of light. Every detail came from splitting that light into a spectrum.', 0.5, 0.95),
 ('This happened far from us, and it poses no threat to Earth.', 0.4, 0.95),
 ("But somewhere out there, a planet's final moments are still written in light, and Webb is learning to read them.", 0.0, 0.93),
]

def parse(text):
    spoken, disp = [], []
    for m in re.finditer(r"\{([^|]*)\|([^}]*)\}|(\S+)", text):
        if m.group(3):
            disp.append((m.group(3), len(spoken), len(spoken))); spoken.append(m.group(3))
        else:
            sw = m.group(2).split(); dw = m.group(1).split(); i0 = len(spoken); spoken += sw
            for j, w in enumerate(dw):
                disp.append((w, i0 + j * len(sw) // len(dw), i0 + (j + 1) * len(sw) // len(dw) - 1))
    return " ".join(spoken), disp
