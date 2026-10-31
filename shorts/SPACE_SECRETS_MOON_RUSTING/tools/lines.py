import re
# GJ 367 b narration (/yt-script). {DISPLAY|spoken}. (text, gap_after, speed)
LINES = [
 ("The Moon is rusting.", 0.22, 0.97),
 ("And Earth may be why.", 0.45, 0.95),
 ("That sounds impossible.", 0.2, 0.97),
 ("The Moon has almost no atmosphere, hardly any accessible water, and a surface constantly exposed to space.", 0.4, 1.0),
 ("But scientists analyzing data from India's {Chandrayaan-1|Chandra-yaan One} spacecraft found spectral evidence of hematite, a mineral associated with rust, near the Moon's poles.", 0.4, 1.0),
 ("And the strange part?", 0.2, 0.95),
 ("Those signatures appeared more frequently on the side of the Moon facing Earth.", 0.45, 0.98),
 ("One explanation points directly back at our planet.", 0.25, 0.97),
 ("Oxygen particles can escape Earth's upper atmosphere, and travel into the long magnetic tail stretching away from the Sun.", 0.4, 0.98),
 ("As the Moon passes through that region, some of Earth's oxygen may reach its surface.", 0.3, 0.98),
 ("Under the right conditions, that oxygen could help transform iron-bearing minerals into hematite.", 0.45, 0.98),
 ("But the mystery doesn't end there.", 0.3, 0.95),
 ("In {2025,|twenty twenty-five,} researchers reported microscopic iron-oxide crystals in actual lunar soil returned by China's {Chang'e-6|Chahng-uh six} mission.", 0.4, 1.0),
 ("Those samples came from the far side of the Moon.", 0.25, 0.97),
 ("And the researchers suggested that violent impacts could create local conditions for iron oxides to form.", 0.45, 0.98),
 ("So Earth's oxygen might explain part of the story, while impacts and other processes could explain more.", 0.3, 0.99),
 ("Scientists are still working out exactly how lunar rust forms.", 0.5, 0.97),
 ("Think about that.", 0.3, 0.93),
 ("The Moon isn't just a silent rock in our sky.", 0.25, 0.96),
 ("Its surface may preserve traces of Earth's escaping atmosphere, and clues from ancient cosmic collisions.", 0.45, 0.96),
 ("Even our nearest neighbor is hiding a chemical mystery.", 0.0, 0.93),
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
