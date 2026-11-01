import re
# GJ 367 b narration (/yt-script). {DISPLAY|spoken}. (text, gap_after, speed)
LINES = [
 ("An invisible black hole is moving through our galaxy.", 0.30, 0.91),
 ("And scientists have actually found one.", 0.80, 0.90),
 ("Most black holes are discovered through their effects on nearby stars, or glowing material.", 0.30, 0.86),
 ("But this one was completely alone.", 0.80, 0.86),
 ("It's called {OGLE-2011-BLG-0462.|Ogle twenty eleven, B L G, zero four six two.}", 0.35, 0.86),
 ("Its mass is about seven times our Sun's, yet it gives off no light we can directly detect.", 0.80, 0.86),
 ("So how did astronomers find something invisible?", 0.25, 0.86),
 ("They watched a distant star behave in a very strange way.", 0.80, 0.86),
 ("As the black hole crossed in front of the background star, its gravity bent and magnified the star's light.", 0.70, 0.86),
 ("The star appeared to brighten, and its apparent position shifted by a tiny amount.", 0.30, 0.86),
 ("Hubble tracked that movement over years.", 0.80, 0.86),
 ("Scientists combined those measurements to determine that the hidden object was a stellar-mass black hole.", 0.80, 0.86),
 ("It's roughly {5,000|five thousand} light-years away.", 0.30, 0.86),
 ("There is no evidence that this object is approaching our solar system.", 2.00, 0.86),
 ("But imagine a different black hole passing close to our planetary neighborhood.", 0.30, 0.86),
 ("Its gravity could disturb planetary orbits, depending on its mass and distance.", 0.90, 0.86),
 ("The frightening part isn't that one is coming.", 0.35, 0.86),
 ("It's that the universe can hide something this massive in plain sight.", 0.00, 0.86),
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
