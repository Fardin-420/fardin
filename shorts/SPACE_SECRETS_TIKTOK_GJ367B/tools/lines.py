# GJ 367 b narration (/yt-script). {DISPLAY|spoken}. (text, gap_after, speed)
LINES = [
 ("Three years in one day!", 0.25, 1.0),
 ("You'd have a birthday every {7.7 hours|seven point seven hours} here, but you would never survive one. Why?", 0.4, 0.98),
 ("So while one day passes on Earth, it circles its star three times.", 0.45, 0.98),
 ("Meet {GJ 367 b.|G J three sixty-seven b.}", 0.4, 0.94),
 ("A real rocky world, about {31 light-years|thirty-one light-years} away.", 0.3, 0.97),
 ("It's a little smaller than Earth, roughly three-quarters of its width.", 0.4, 0.98),
 ("And it orbits a red dwarf, a star smaller and cooler than our Sun.", 0.3, 0.98),
 ("But it hugs that star incredibly closely, less than one hundredth of the distance between Earth and the Sun.", 0.3, 1.0),
 ("That's why its year is so short.", 0.45, 0.96),
 ("It's probably tidally locked, with one side always facing its star.", 0.3, 0.98),
 ("That side may reach around {2,700 °F.|twenty-seven hundred degrees Fahrenheit.} Hot enough to melt rock.", 0.5, 0.98),
 ("But the real mystery is what it's made of.", 0.45, 0.94),
 ("Early measurements made it look incredibly dense... like a ball of almost pure iron.", 0.4, 0.98),
 ("But new research, published in June {2026,|twenty twenty-six,} revised its mass and its size.", 0.3, 0.98),
 ("Interior models now suggest iron makes up roughly {50 to 70 percent|fifty to seventy percent} of its mass.", 0.4, 0.97),
 ("That's still far more than Earth, which is about one-third iron.", 0.3, 0.98),
 ("So it's probably not pure iron. It looks more like a scorched, oversized cousin of Mercury.", 0.45, 0.98),
 ("And scientists still don't know exactly what's inside, or what its surface really looks like.", 0.3, 0.98),
 ("Everything you're seeing is a reconstruction, built from measurements of starlight.", 0.5, 0.97),
 ("So remember: in the time it takes you to live one ordinary day...", 0.25, 0.95),
 ("this tiny iron-rich world races through three entire years.", 0.0, 0.94),
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
