# EP04 narration (client script, verbatim). {DISPLAY|spoken}. (text, gap_after, speed)
LINES = [
 ("This moon is shooting its ocean into SPACE!", 0.2, 1.0),
 ("And NASA actually flew a spacecraft through the spray.", 0.35, 1.0),
 ("Meet {Enceladus.|Enceladus.}", 0.4, 0.92),
 ("A tiny, frozen moon orbiting Saturn.", 0.3, 0.96),
 ("From a distance, it looks like a lifeless ball of ice.", 0.25, 0.98),
 ("But something extraordinary is happening beneath its surface.", 0.4, 0.96),
 ("Hidden under that frozen shell is a global ocean of liquid water.", 0.35, 0.97),
 ("And near the south pole, enormous cracks cut through the ice.", 0.3, 0.98),
 ("Through these fractures, water vapor and icy particles erupt into space.", 0.4, 0.98),
 ("NASA's Cassini spacecraft flew through these plumes and analyzed their contents.", 0.35, 1.0),
 ("What scientists discovered was incredible.", 0.4, 0.95),
 ("Water.", 0.3, 0.92),
 ("Salts.", 0.3, 0.92),
 ("Organic compounds.", 0.35, 0.94),
 ("And evidence of chemical reactions that could provide energy for life.", 0.4, 0.97),
 ("Later analysis even revealed phosphorus, an element essential to life as we know it, in ice grains from Saturn's {E ring,|E-ring,} which is supplied by Enceladus.", 0.5, 1.02),
 ("But here's the most important part.", 0.3, 0.95),
 ("Scientists have NOT discovered aliens there.", 0.45, 0.93),
 ("They've discovered ingredients and conditions that make this frozen moon one of the most fascinating places to search for life.", 0.5, 1.0),
 ("Imagine an ocean completely hidden from sunlight.", 0.35, 0.94),
 ("An ocean buried beneath kilometers of ice.", 0.35, 0.94),
 ("And a moon that sends samples of that ocean directly into space.", 0.45, 0.96),
 ("Somewhere beneath that frozen surface, an extraordinary mystery is waiting.", 0.5, 0.94),
 ("Could something be alive down there?", 0.0, 0.9),
]
import re
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
