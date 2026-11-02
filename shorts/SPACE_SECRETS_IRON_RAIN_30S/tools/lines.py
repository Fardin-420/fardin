import re
# GJ 367 b narration (/yt-script). {DISPLAY|spoken}. (text, gap_after, speed)
LINES = [
 ("On this planet, it rains iron.", 0.50, 0.92),
 ("Meet {WASP-76 b,|wasp seventy-six b,} a world so hot that metal can evaporate into the sky.", 0.25, 0.95),
 ("Its dayside reaches over {4,000 °F.|four thousand degrees Fahrenheit.}", 0.25, 0.95),
 ("Powerful winds carry iron vapor toward the cooler nightside.", 0.25, 0.95),
 ("And there, scientists believe the iron condenses into liquid droplets.", 0.30, 0.95),
 ("Imagine a weather forecast that says: molten metal rain.", 0.65, 0.94),
 ("And the craziest part? This isn't science fiction.", 0.25, 0.95),
 ("It's a real planet.", 0.0, 0.90),
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
