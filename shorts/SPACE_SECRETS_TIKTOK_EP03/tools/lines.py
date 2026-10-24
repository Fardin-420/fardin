# Narration: {DISPLAY|spoken} spans show one thing in captions and say another. (text, gap_after, speed)
LINES = [
 ("On this planet, the rain could tear you apart.", 0.35, 0.94),
 ("Because it might be made of glass.", 0.8, 0.893),
 ("And the terrifying part? This planet actually exists.", 0.5, 0.94),
 ("Meet {HD 189733 b.|H D one eight nine, seven three three, b.}", 0.8, 0.893),
 ("From space, it looks like a beautiful blue world. Almost like Earth.", 0.4, 0.94),
 ("But that blue color isn't coming from oceans.", 0.35, 0.94),
 ("It's coming from a scorching atmosphere filled with tiny silicate particles.", 0.4, 0.959),
 ("Scientists believe those particles could form droplets of glass.", 0.6, 0.921),
 ("Now imagine those droplets being blasted sideways by winds reaching around {5,400 MPH.|five thousand four hundred miles per hour.}", 0.4, 0.987),
 ("That's faster than anything we've ever measured in Earth's atmosphere.", 0.8, 0.959),
 ("And the heat?", 0.35, 0.893),
 ("On the planet's dayside, temperatures can climb to nearly {2,000°F.|two thousand degrees Fahrenheit.}", 0.6, 0.94),
 ("This is a gas giant, so there's no solid surface to stand on like there is on Earth.", 0.3, 0.987),
 ("Instead, you'd be entering an enormous, violent atmosphere.", 0.9, 0.921),
 ("Here's what's even stranger.", 0.3, 0.94),
 ("This nightmare world is only about {63 light-years|sixty-three light-years} away.", 0.5, 0.94),
 ("Astronomers used the Hubble Space Telescope to determine its deep blue color, and other observations helped reveal its extreme weather.", 0.6, 1.015),
 ("We haven't actually watched glass rain falling there. It's a scientific possibility based on the conditions in its atmosphere.", 0.8, 0.987),
 ("So next time you see a beautiful blue planet, remember this:", 0.45, 0.94),
 ("In space, the prettiest worlds can hide the deadliest weather.", 0.0, 0.865),
]
import re
def parse(text):
    """-> spoken string, display tokens [(display_word, first_spoken_idx, last_spoken_idx)]"""
    spoken, disp = [], []
    for m in re.finditer(r"\{([^|]*)\|([^}]*)\}|(\S+)", text):
        if m.group(3):
            disp.append((m.group(3), len(spoken), len(spoken))); spoken.append(m.group(3))
        else:
            sw = m.group(2).split(); dw = m.group(1).split(); i0 = len(spoken); spoken += sw
            n = len(sw)
            for j, w in enumerate(dw):
                disp.append((w, i0 + j * n // len(dw), i0 + (j + 1) * n // len(dw) - 1))
    return " ".join(spoken), disp
