"""Generates script.json for Time Ghost L001 — 'I Spent 24 Hours With Early Humans'.

Run:  python episodes/L001/make_script.py
The JSON is the source the engine renders; this file just keeps characters,
staging and repeated patterns consistent. Facts + sources are listed in FACTS.md.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------ cast
PEOPLE = {
    "elder": dict(skin="#5a3826", hide="#7a5a3a", hair="short", beard=True, wrap="cape", size=285),
    "hunterA": dict(skin="#6b4430", hide="#9c7a50", hair="bun", beard=False, wrap="sash", size=280),
    "hunterB": dict(skin="#4d3022", hide="#8b6a45", hair="curls", beard=True, wrap="skirt", size=300, paint=True),
    "hunterC": dict(skin="#7a4e35", hide="#a5845a", hair="short", beard=False, wrap="skirt", size=295),
    "hunterD": dict(skin="#6f4a33", hide="#6e5235", hair="long", beard=False, wrap="cape", size=275),
    "mother": dict(skin="#8a5a3c", hide="#94704a", hair="long", beard=False, wrap="cape", size=275),
    "kid": dict(skin="#7a4e35", hide="#a5845a", hair="curls", beard=False, wrap="skirt", size=175),
    "walker": dict(skin="#5a3826", hide="#8b6a45", hair="curls", beard=True, wrap="sash", size=295),
}


def P(pid, x, track, **kw):
    d = {"id": pid, "kind": "era", "x": x}
    d.update(PEOPLE[pid])
    d.update(kw)
    d["track"] = track
    return d


def F(x, track, **kw):
    d = {"id": "fardin", "kind": "fardin", "x": x, "size": 300, "track": track}
    d.update(kw)
    return d


def k(pose=None, **kw):
    d = {}
    if pose:
        d["pose"] = pose
    d.update(kw)
    return d


DAY_AMB = {"wind": 0.6, "birds": 0.5}
CAMP_AMB = {"wind": 0.4, "birds": 0.35, "crowd": 0.45, "fire": 0.25}
NIGHT_AMB = {"crickets": 0.55, "fire": 0.6, "wind": 0.35}
CAVE_AMB = {"cave": 0.6, "fire": 0.45, "crickets": 0.15}

scenes = []
S = scenes.append

# ================================================================== COLD OPEN
S({
    "id": "co1", "chapter": "Cold Open", "set": "camp", "tod": "night", "set_opts": {"cliff_x": -250},
    "music": "dark", "amb": NIGHT_AMB, "lead": 0.6,
    "narration": [
        {"text": "Night. Three hundred thousand years ago.", "pause": 0.4},
        "Fardin is hiding behind a rock. And he is not alone.",
        {"text": "Something is circling the camp. Then comes the sound.", "pause": 1.5},
    ],
    "actors": [
        F(-330, [k("crouch_hide", t=0, expr="scared"), k("crouch_hide", cue="w:circling", expr="shock", pop=True),
                 k("crouch_hide", cue="w:sound", off=0.9, expr="scared", pop=True)]),
        P("elder", 230, [k("sit", t=0, expr="neutral")], facing=1),
        P("mother", 470, [k("sleep", t=0)], facing=-1),
        P("hunterB", 640, [k("sit", t=0), k("lookout", cue="w:sound", off=1.0, hold="spear", expr="worried")], facing=1),
    ],
    "animals": [
        {"species": "hyena", "x": 1100, "facing": -1, "size": 1.05, "glow": 0.0,
         "track": [{"t": 0, "state": "stand"}, {"cue": "w:circling", "state": "prowl", "glow": 1.0, "to": 900, "dur": 5}]},
        {"species": "hyena", "x": -1050, "facing": 1, "size": 0.95, "glow": 0.0,
         "track": [{"t": 0, "state": "stand"}, {"cue": "w:circling", "state": "prowl", "glow": 0.9, "to": -900, "dur": 6}]},
    ],
    "props": [{"type": "campfire", "x": 420, "s": 1.0}, {"type": "boulder", "x": -300, "y": 20, "s": 1.05, "front": True},
              {"type": "acacia", "x": -900, "y": -30, "s": 1.2}, {"type": "smoke", "x": 420}],
    "camera": [{"t": 0, "x": 150, "zoom": 0.92}, {"cue": "w:Fardin", "x": -250, "zoom": 1.25},
               {"cue": "w:Something", "x": 450, "zoom": 1.05, "ease": "inOutCubic"},
               {"cue": "w:Then", "x": 800, "zoom": 1.25}, {"cue": "w:sound", "off": 0.7, "x": -150, "zoom": 1.15, "ease": "outCubic"}],
    "shake": [{"start": {"cue": "w:sound", "off": 0.8}, "end": {"cue": "w:sound", "off": 2.2}, "amp": 12}],
    "sfx": [{"type": "rumble", "t": 0.2, "vol": 0.5}, {"type": "heartbeat", "cue": "w:Fardin", "vol": 0.5},
            {"type": "hyena", "cue": "w:sound", "off": 0.8, "vol": 0.85}, {"type": "hyena_giggle", "cue": "w:sound", "off": 1.9, "vol": 0.7}],
    "fx": [{"type": "fade_in", "t": 0, "dur": 1.0}, {"type": "danger", "cue": "w:sound", "off": 0.8, "dur": 2.0}],
})
S({
    "id": "co2", "chapter": "Cold Open", "set": "camp", "tod": "night", "set_opts": {"cliff_x": -250},
    "music": "tense", "amb": NIGHT_AMB, "lead": 0.2, "tail": 1.2,
    "narration": [
        {"text": "Spotted hyenas. And Fardin just realized something terrible.", "pause": 0.3},
        "The people around this fire can't see him. But he has no idea if the hyenas can.",
    ],
    "actors": [
        F(-330, [k("crouch_hide", t=0, expr="scared"), k("crouch_hide", cue="w:terrible", expr="shock", pop=True),
                 k("crouch_hide", cue="w:people", expr="worried"), k("crouch_hide", cue="w:hyenas#2", expr="scared", pop=True)],
          say=[{"cue": "seg:1:end", "off": 0.15, "text": "Uh oh."}]),
        P("elder", 230, [k("sit", t=0), k("lookout", cue="w:people", hold="spear", expr="worried")], facing=1),
        P("hunterB", 640, [k("lookout", t=0, hold="spear", expr="worried")], facing=1),
    ],
    "animals": [{"species": "hyena", "x": 1200, "facing": -1, "size": 0.95, "glow": 1.0,
                 "track": [{"t": 0, "state": "prowl", "to": 930, "dur": 6}, {"cue": "w:terrible", "state": "alert"},
                           {"cue": "w:people", "state": "prowl", "to": 1050, "dur": 4}]}],
    "props": [{"type": "campfire", "x": 420}, {"type": "boulder", "x": -300, "y": 20, "s": 1.05, "front": True}],
    "camera": [{"t": 0, "x": 950, "zoom": 1.55}, {"cue": "w:Fardin", "off": -0.2, "x": -300, "y": -300, "zoom": 2.0, "ease": "inOutCubic"},
               {"cue": "w:people", "x": 150, "y": -230, "zoom": 1.2}, {"cue": "w:hyenas#2", "x": -300, "y": -300, "zoom": 2.2, "ease": "outCubic"}],
    "sfx": [{"type": "growl", "t": 0.5, "vol": 0.6}, {"type": "heartbeat", "cue": "w:terrible", "vol": 0.7}, {"type": "riser", "cue": "w:idea", "vol": 0.5}],
    "fx": [{"type": "danger", "cue": "w:terrible", "dur": 6.0}],
})
S({
    "id": "co3", "chapter": "Cold Open", "set": "camp", "tod": "night", "set_opts": {"cliff_x": -250},
    "music": "none", "amb": {"crickets": 0.3}, "lead": 0.2, "tail": 0.6,
    "narration": ["But to understand how he got here, we need to go back a few hours."],
    "actors": [F(-330, [k("crouch_hide", t=0, expr="scared"), k("check_watch", cue="w:back", expr="curious", watch=1.2)])],
    "props": [{"type": "campfire", "x": 420}, {"type": "boulder", "x": -300, "y": 20, "s": 1.05, "front": True}],
    "camera": [{"t": 0, "x": -300, "y": -290, "zoom": 1.9}, {"e": 0.1, "x": -300, "y": -290, "zoom": 2.6, "ease": "inCubic"}],
    "fx": [{"type": "ripple", "cue": "w:back", "dur": 2.2, "amt": 1.0}, {"type": "speedlines", "cue": "w:back", "dur": 2.0},
           {"type": "flash_in", "e": 0.5, "dur": 0.5}],
    "graphics": [{"type": "callout", "cue": "w:few", "dur": 1.8, "text": "REWIND", "size": 150, "y": 0.25}],
    "sfx": [{"type": "whoosh_down", "cue": "w:back", "vol": 0.8}, {"type": "riser", "cue": "w:back", "vol": 0.6}],
})

# ================================================================== TIME TRAVEL
S({
    "id": "tt1", "chapter": "Time Travel", "set": "room", "tod": "day", "music": "playful", "amb": {"city": 0.5},
    "lead": 0.3, "no_dip": True,
    "narration": [
        {"text": "This is Fardin. Normal guy. Red hoodie. One very unusual watch.", "pause": 0.2},
        "Turn the dial, and he falls back through time as a ghost.",
        "Nobody there can see him or hear him. He can only watch.",
        "Tonight, he set the dial further back than ever.",
    ],
    "actors": [F(-700, [k("walk", t=0, to=-60, dur=2.2, ease="outSine", expr="happy"), k("wave", cue="w:Normal", expr="grin"),
                         k("idle", cue="w:hoodie", expr="happy"), k("check_watch", cue="w:watch", expr="curious", watch=0.9),
                         k("shrug", cue="w:ghost", expr="grin"), k("idle", cue="w:Nobody", expr="neutral"),
                         k("shrug", cue="w:only", expr="happy"), k("tap_watch", cue="w:Tonight", expr="determined", watch=1.6, wdur=2.5)],
                 say=[{"cue": "w:Normal", "off": -0.1, "text": "Hi!", "voice": False, "dur": 1.0}])],
    "camera": [{"t": 0, "x": -200, "zoom": 1.0}, {"cue": "w:Normal", "x": -60, "y": -260, "zoom": 1.35},
               {"cue": "w:watch", "x": 0, "y": -300, "zoom": 1.9}, {"cue": "w:Turn", "x": 0, "zoom": 1.1},
               {"cue": "w:Nobody", "x": 60, "zoom": 1.2}, {"cue": "w:Tonight", "x": -40, "y": -300, "zoom": 1.9}],
    "graphics": [{"type": "lower", "cue": "w:Fardin", "dur": 3.4, "text": "FARDIN", "sub": "Time Ghost · invisible in the past"}],
    "sfx": [{"type": "steps", "t": 0.1, "vol": 0.5}, {"type": "shimmer", "cue": "w:watch", "vol": 0.4},
            {"type": "rumble", "cue": "w:Tonight", "vol": 0.6}, {"type": "riser", "cue": "w:further", "vol": 0.6}],
    "fx": [{"type": "fade_in", "t": 0, "dur": 0.4}],
})
S({
    "id": "tt2", "chapter": "Time Travel", "set": "void", "music": "wonder", "amb": {"tunnel": 0.7}, "lead": 1.0, "tail": 3.3,
    "no_dip": True, "tunnel": [[0, 0.2], [2.5, 1.6], [6, 0.6]],
    "narration": ["Three hundred thousand years."],
    "actors": [F(0, [k("tumble", t=0, expr="shock", y_to=-120, dur=3, watch=1.5)], y=-60)],
    "camera": [{"t": 0, "x": 0, "y": -260, "zoom": 1.25}, {"e": 0.1, "x": 0, "y": -260, "zoom": 1.05}],
    "fx": [{"type": "flash", "t": 0, "dur": 0.8}, {"type": "counter", "t": 0.2, "dur": 3.0, "from": 2026, "to": -298000},
           {"type": "flash", "e": 0.25, "dur": 0.25, "amt": 0.6}],
    "graphics": [{"type": "era_title", "e": 3.3, "dur": 3.2, "title": "300,000 YEARS AGO", "sub": "NORTH AFRICA · MIDDLE STONE AGE"}],
    "sfx": [{"type": "whoosh", "t": 0.0, "vol": 0.8}, {"type": "riser_long", "t": 0.3, "vol": 0.5}, {"type": "impact", "e": 3.3, "vol": 0.8},
            {"type": "shimmer", "e": 3.3, "vol": 0.5}],
})
S({
    "id": "tt3", "chapter": "Time Travel", "set": "camp", "tod": "dawn", "set_opts": {"cliff_x": 50}, "music": "wonder",
    "amb": DAY_AMB, "lead": 0.8, "weather": "dust", "weather_amt": 0.6, "no_dip": True,
    "narration": [
        "In the next twenty four hours, he'll see three things that changed how we think about our species.",
        "A hunt with stone tipped spears.",
        "A rock trick so clever, it lasted two hundred thousand years.",
        "And by tonight, the strangest discovery of all: who else was out there.",
    ],
    "actors": [F(-120, [k("land", t=0, expr="shock"), k("look_around", t=1.0, expr="amazed"),
                         k("walk", cue="w:hunt", to=-420, dur=2.2, expr="curious"), k("amazed", cue="w:trick", expr="amazed", face=1),
                         k("point", cue="w:tonight", expr="curious"), k("hands_on_head", cue="w:who", expr="shock", pop=True)],
                y=0)],
    "props": [{"type": "acacia", "x": -1000, "y": -40, "s": 1.3}, {"type": "rock", "x": 420, "y": 30}, {"type": "bush", "x": 700, "y": 10}],
    "camera": [{"t": 0, "x": -120, "y": -280, "zoom": 1.5}, {"t": 1.4, "x": 150, "zoom": 1.0, "ease": "inOutCubic"},
               {"cue": "w:who", "x": -400, "y": -260, "zoom": 1.25}],
    "fx": [{"type": "flash", "t": 0, "dur": 0.9}, {"type": "dust", "t": 0.05, "x": -120, "dur": 1.2}],
    "graphics": [{"type": "list", "cue": "w:three", "dur_e": 0.4, "title": "IN THE NEXT 24 HOURS",
                  "items": ["A hunt with stone-tipped spears", "A rock trick used for 200,000+ years", "Who else was out there…"],
                  "times": []}],
    "sfx": [{"type": "thud", "t": 0.05, "vol": 0.7}],
})
# list item timing: appear on their narration
scenes[-1]["graphics"][0]["item_cues"] = ["w:hunt", "w:trick", "w:strangest"]

# ================================================================== CH1 DAWN
CAMP_PROPS = [{"type": "campfire", "x": 120, "s": 0.85}, {"type": "smoke", "x": 120}, {"type": "hide_rack", "x": -620, "y": -30, "s": 0.9},
              {"type": "bones", "x": 330, "y": 20}, {"type": "flakes", "x": -200, "y": 15}, {"type": "rock", "x": -380, "y": 25, "s": 0.8}]
S({
    "id": "d1", "chapter": "Dawn: The First of Us", "set": "camp", "tod": "dawn", "set_opts": {"cliff_x": -250}, "music": "calm",
    "amb": DAY_AMB, "lead": 0.5,
    "narration": [
        "Dawn. Fardin is standing on a dry, rocky hillside, in what will one day be Morocco. There are no countries yet, no farms, and no cities anywhere on Earth.",
        "Scientists call this place Jebel Irhoud.",
        "In 2017, researchers announced that human fossils found here are about three hundred thousand years old.",
        "They are the oldest known fossils of our own species. Homo sapiens.",
    ],
    "actors": [F(-900, [k("walk", t=0, to=-450, dur=3.5, expr="curious"), k("look_around", t=3.6, expr="curious"),
                         k("amazed", cue="w:oldest", expr="amazed", pop=True)])],
    "props": CAMP_PROPS[2:] + [{"type": "acacia", "x": -1100, "y": -40, "s": 1.25}],
    "camera": [{"t": 0, "x": -700, "zoom": 1.0}, {"cue": "w:Scientists", "x": -300, "zoom": 1.0},
               {"cue": "w:oldest", "x": -350, "y": -250, "zoom": 1.3}],
    "graphics": [{"type": "chapter", "t": 0.4, "dur": 3.6, "kicker": "CHAPTER 1", "title": "DAWN", "time": "6:10 AM · Jebel Irhoud"},
                 {"type": "clock", "t": 0.2, "dur_e": 0.1, "from": 370, "to": 380, "hour": 1},
                 {"type": "map", "cue": "w:Scientists", "dur_to": "seg:2:end", "dur_off": 0.4, "view": "africa", "side": "right",
                  "pins": [{"lat": 31.85, "lon": -8.87, "label": "Jebel Irhoud", "sub": "Morocco", "t": 0.8}]},
                 {"type": "fact", "cue": "w:three", "dur_e": 0.2, "count": 300000, "label": "years old: the oldest known Homo sapiens fossils",
                  "source": "Jebel Irhoud, Morocco · announced 2017", "tag": "FACT", "side": "left", "y": 190}],
})
S({
    "id": "d2", "chapter": "Dawn: The First of Us", "set": "camp", "tod": "dawn", "set_opts": {"cliff_x": -250}, "music": "calm",
    "amb": CAMP_AMB, "lead": 0.3,
    "narration": [
        "And there they are. A small group, waking up beside a cave.",
        {"text": "Fardin's first thought? They look... surprisingly normal.", "pause": 0.4},
        "And he's right, mostly. Their faces were a lot like ours. But the back of the skull was longer and lower.",
        "Their brains were about as big as ours, but shaped differently. The rounder brain shape we have today seems to have appeared later.",
    ],
    "actors": [
        F(-520, [k("idle", t=0, expr="curious"), k("tiptoe", cue="w:there", to=-260, dur=2.4, expr="curious"),
                 k("amazed", cue="w:normal", expr="amazed", pop=True), k("lean_in", cue="w:faces", expr="curious"),
                 k("idle", cue="w:brains", expr="curious")]),
        P("elder", 60, [k("sit", t=0), k("stretch", cue="w:waking"), k("sit", cue="w:thought")], facing=-1),
        P("mother", 300, [k("sleep", t=0), k("sit", cue="w:waking", off=0.6), k("talk", cue="w:faces")], facing=-1),
        P("kid", 470, [k("sit", t=0), k("walk", cue="w:waking", off=1.0, to=620, dur=2), k("idle", cue="w:normal")], facing=1),
        P("hunterB", 720, [k("stretch", t=0), k("idle", cue="w:normal"), k("walk", cue="w:skull", to=900, dur=3)], facing=-1),
        P("hunterA", -60, [k("cook", t=0, expr="focused")], facing=1),
    ],
    "props": CAMP_PROPS,
    "camera": [{"t": 0, "x": 260, "zoom": 0.95}, {"cue": "w:normal", "x": -200, "y": -280, "zoom": 1.6},
               {"cue": "w:faces", "x": 0, "y": -250, "zoom": 1.25}, {"cue": "w:back", "x": 100, "y": -380, "zoom": 1.0}],
    "graphics": [{"type": "clock", "t": 0, "dur_e": 0.1, "from": 381, "to": 392, "hour": 1},
                 {"type": "skulls", "cue": "w:back", "dur_e": 0.3, "left": "JEBEL IRHOUD", "left_sub": "~300,000 years ago",
                  "right": "MODERN HUMAN", "right_sub": "today", "note": "Similar face · longer, lower braincase"}],
})
S({
    "id": "d3", "chapter": "Dawn: The First of Us", "set": "camp", "tod": "morning", "set_opts": {"cliff_x": -250}, "music": "wonder",
    "amb": CAMP_AMB, "lead": 0.3,
    "narration": [
        "Here's a way to feel how long ago this is.",
        "Squeeze the whole story of our species into one twenty four hour day. Farming doesn't show up until about eleven PM.",
        "The pyramids? Eleven thirty eight. Almost everything in your history books happens in the last half hour.",
    ],
    "actors": [F(-150, [k("sit", t=0, expr="curious"), k("sit", cue="w:Farming", expr="shock", pop=True),
                         k("hands_on_head", cue="w:pyramids", expr="shock", pop=True), k("sit", cue="w:Almost", expr="amazed")], y=-20),
               P("kid", 300, [k("idle", t=0), k("walk", t=1.0, to=700, dur=3), k("sit", t=4.2)], facing=1)],
    "props": CAMP_PROPS[:2] + [{"type": "rock", "x": -150, "y": 5, "s": 0.55}],
    "camera": [{"t": 0, "x": -60, "y": -300, "zoom": 1.15}, {"e": 0.1, "x": -120, "y": -300, "zoom": 1.35}],
    "graphics": [{"type": "timeline", "cue": "w:Squeeze", "dur_e": 0.2, "left": "12:00 AM · 300,000 YEARS AGO", "right": "MIDNIGHT · TODAY",
                  "marks": [{"ago": 12000, "label": "FARMING 11:02 PM", "align": "right", "row": 0, "t": 2.4},
                            {"ago": 4500, "label": "PYRAMIDS 11:38 PM", "align": "right", "row": 1, "t": 6.0}],
                  "marker_label": "FARDIN IS HERE", "caption": "Our species' story as one 24-hour day"}],
})
scenes[-1]["graphics"][0]["mark_cues"] = ["w:Farming", "w:pyramids"]
S({
    "id": "d4", "chapter": "Dawn: The First of Us", "set": "savanna", "tod": "morning", "music": "playful", "amb": DAY_AMB, "lead": 0.3,
    "narration": [
        "And forget the Sahara you know. At times, North Africa was much greener, with grasslands, lakes and rivers.",
        {"text": "Gazelles and other grazing animals roamed here. Fardin tries waving at a man walking right past him.", "pause": 1.4},
        "Nothing. Not even a blink. He really is a ghost here.",
        "But that's fine. Because the hunt is about to begin. And it's nothing compared to what happens after dark.",
    ],
    "actors": [F(-100, [k("idle", t=0, expr="happy"), k("wave", cue="w:waving", expr="grin"), k("wave", cue="seg:1:end", expr="happy"),
                         k("shrug", cue="w:Nothing", expr="neutral"), k("idle", cue="w:ghost", expr="curious"),
                         k("walk", cue="w:hunt", to=500, dur=3, expr="determined")],
                 say=[{"cue": "seg:1:end", "off": 0.1, "text": "Hello?"}]),
               P("walker", 900, [k("idle", t=0), k("walk", cue="w:waving", off=-0.5, to=-900, dur=4.5, hold="spear")], facing=-1, hold="spear")],
    "animals": [{"species": "gazelle", "x": 1300 + i * 170, "y": -120 - (i % 2) * 30, "size": 0.5, "facing": -1 if i % 2 else 1,
                 "track": [{"t": 0, "state": "graze" if i % 3 else "stand"}]} for i in range(4)],
    "props": [{"type": "acacia", "x": 700, "y": -60, "s": 1.1}, {"type": "bush", "x": -500, "y": 20}],
    "camera": [{"t": 0, "x": 900, "y": -260, "zoom": 1.0}, {"cue": "w:Gazelles", "x": 1300, "zoom": 1.1},
               {"cue": "w:Fardin", "x": -50, "zoom": 1.2, "ease": "inOutCubic"}, {"cue": "w:Nothing", "x": -100, "y": -300, "zoom": 1.7},
               {"cue": "w:hunt", "x": 300, "zoom": 1.0}],
    "graphics": [{"type": "map", "t": 0.3, "dur_to": "seg:0:end", "dur_off": 0.6, "view": "africa", "side": "right", "green_sahara": True,
                  "pins": [{"lat": 31.85, "lon": -8.87, "label": "Jebel Irhoud", "t": 0.5}]},
                 {"type": "tag", "t": 1.6, "dur": 3.5, "text": "CLIMATE SWUNG BETWEEN WET AND DRY"},
                 {"type": "clock", "t": 0, "dur_e": 0.1, "from": 410, "to": 425, "hour": 2}],
    "sfx": [{"type": "steps", "cue": "w:waving", "vol": 0.4}, {"type": "pop", "cue": "w:blink", "vol": 0.4}],
})

# ================================================================== CH2 THE HUNT
HUNTERS = ["hunterA", "hunterB", "hunterC", "hunterD"]
S({
    "id": "h1", "chapter": "The Hunt", "set": "savanna", "tod": "morning", "music": "playful", "amb": DAY_AMB, "lead": 0.4,
    "narration": [
        "Mid morning. A few hunters grab their spears and head out, and Fardin tags along, three steps behind.",
        "Archaeologists dug up many animal bones at Jebel Irhoud, and the most common by far belonged to gazelles. Many carry cut marks from stone tools.",
    ],
    "actors": [P(h, -700 - i * 200, [k("walk", t=0.3 + i * 0.2, to=900 - i * 200, dur=13, ease="linear", hold="spear")], hold="spear", facing=1)
               for i, h in enumerate(HUNTERS)] +
              [F(-1600, [k("walk", t=0.8, to=-50, dur=12.5, ease="linear", expr="happy"), k("tiptoe", cue="w:Archaeologists", inplace=1, expr="curious")])],
    "props": [{"type": "acacia", "x": 400, "y": -50, "s": 1.2}, {"type": "rock", "x": -300, "y": 40}, {"type": "bush", "x": 1000, "y": 10}],
    "camera": [{"t": 0, "track": "fardin", "dx": 350, "zoom": 1.0}, {"e": 0.1, "track": "fardin", "dx": 350, "zoom": 1.0}],
    "graphics": [{"type": "chapter", "t": 0.3, "dur": 3.6, "kicker": "CHAPTER 2", "title": "THE HUNT", "time": "9:40 AM"},
                 {"type": "clock", "t": 0, "dur_e": 0.1, "from": 580, "to": 595, "hour": 4},
                 {"type": "fact", "cue": "w:most", "dur_e": 0.2, "big": "GAZELLE", "big_size": 96,
                  "label": "The most common animal bones at Jebel Irhoud, many with stone-tool cut marks", "tag": "MENU ITEM #1", "side": "right", "y": 170}],
    "sfx": [{"type": "steps", "t": 0.5, "vol": 0.4}, {"type": "steps", "t": 3.0, "vol": 0.4}, {"type": "steps", "t": 5.5, "vol": 0.4}],
})
S({
    "id": "h2", "chapter": "The Hunt", "set": "savanna", "tod": "morning", "music": "tense", "amb": {"wind": 0.7, "birds": 0.2}, "lead": 0.3,
    "narration": [
        "Here's the problem. A gazelle can sprint at up to around eighty kilometers an hour. No human can catch one.",
        {"text": "So the hunters creep in low. Quiet. Downwind. Closer.", "pause": 0.3},
        {"text": "And closer.", "pause": 0.8},
    ],
    "actors": [P(h, -600 + i * 150, [k("sneak", t=0.2, to=-100 + i * 150, dur=14, ease="linear", hold="spear", expr="focused")], hold="spear", facing=1)
               for i, h in enumerate(HUNTERS)] +
              [F(-900, [k("sneak", t=0.3, to=-500, dur=12, ease="linear", expr="curious"), k("sneak", cue="w:closer#2", expr="scared", pop=True)])],
    "animals": [{"species": "gazelle", "x": 700 + i * 160, "y": -10 - (i % 3) * 25, "size": 0.62, "facing": -1 if i % 2 else 1,
                 "track": [{"t": 0, "state": "graze" if i % 2 else "stand"}]} for i in range(5)],
    "props": [{"type": "bush", "x": 300, "y": 20, "s": 1.4, "front": True}, {"type": "grass", "x": 0, "y": 60, "s": 2, "front": True}],
    "camera": [{"t": 0, "x": 950, "y": -230, "zoom": 1.25}, {"cue": "w:hunters", "x": 100, "zoom": 1.05, "ease": "inOutCubic"},
               {"cue": "w:closer", "x": 200, "y": -260, "zoom": 1.3}, {"cue": "w:closer#2", "x": 250, "y": -260, "zoom": 1.55}],
    "graphics": [{"type": "fact", "cue": "w:sprint", "dur_to": "seg:0:end", "dur_off": 0.6, "count": 80, "suffix": " km/h",
                  "label": "top sprint speed of a gazelle. Humans top out near 45.", "tag": "SPEED", "side": "right", "y": 170},
                 {"type": "clock", "t": 0, "dur_e": 0.1, "from": 600, "to": 615, "hour": 4}],
    "sfx": [{"type": "heartbeat", "cue": "w:creep", "vol": 0.6}],
    "fx": [{"type": "letterbox", "cue": "w:creep", "dur_e": 0.0}],
})
S({
    "id": "h3", "chapter": "The Hunt", "set": "savanna", "tod": "morning", "music": "playful", "amb": DAY_AMB, "lead": 0.2, "tail": 1.4,
    "narration": [
        {"text": "Now!", "pause": 0.9},
        "The spear flies, and misses. The whole herd explodes away.",
        {"text": "Fardin is laughing so hard he forgets he's invisible. Then he remembers, and laughs even louder.", "pause": 0.2},
    ],
    "actors": [P("hunterB", 0, [k("aim", t=0, hold="spear", expr="focused"), k("throw", cue="w:Now", off=0.3, hold=None),
                                k("hands_on_head", cue="w:misses", expr="sad")], hold="spear", facing=1),
               P("hunterA", -180, [k("crouch", t=0, hold="spear"), k("idle", cue="w:misses", hold="spear", expr="sad")], facing=1),
               F(-420, [k("crouch", t=0, expr="curious"), k("jump_scared", cue="w:Now", off=0.2, expr="shock", pop=True),
                        k("laugh", cue="w:laughing", expr="laugh", pop=True), k("laugh", cue="w:remembers", expr="laugh")],
                 say=[{"cue": "seg:2:end", "off": -0.3, "text": "Ha! Missed!"}])],
    "animals": [{"species": "gazelle", "x": 650 + i * 160, "y": -10 - (i % 3) * 25, "size": 0.62, "facing": 1,
                 "track": [{"t": 0, "state": "graze" if i % 2 else "stand"},
                           {"cue": "w:spear", "off": 0.15 + i * 0.08, "state": "run", "to": 2800 + i * 150, "dur": 1.9, "ease": "inQuad"}]} for i in range(5)],
    "props": [{"type": "grass", "x": 200, "y": 60, "s": 2, "front": True}],
    "fx": [{"type": "spear_flight", "cue": "w:Now", "off": 0.45, "dur": 0.75, "from": [80, -300], "to": [760, -20], "arc": 150},
           {"type": "spear_stuck", "cue": "w:Now", "off": 1.2, "pos": [770, -10], "ang": 0.45},
           {"type": "dust", "cue": "w:Now", "off": 1.2, "x": 770, "y": 0, "dur": 0.8}],
    "camera": [{"t": 0, "x": 150, "y": -250, "zoom": 1.25}, {"cue": "w:spear", "x": 650, "zoom": 1.05, "ease": "outCubic"},
               {"cue": "w:Fardin", "x": -380, "y": -280, "zoom": 1.7, "ease": "inOutCubic"}],
    "shake": [{"start": {"cue": "w:explodes"}, "end": {"cue": "w:explodes", "off": 1.4}, "amp": 8}],
    "graphics": [{"type": "callout", "cue": "w:misses", "dur": 1.4, "text": "MISS!", "x": 0.68, "y": 0.3, "color": [1, 0.35, 0.3]}],
    "sfx": [{"type": "spear", "cue": "w:Now", "off": 0.45, "vol": 0.8}, {"type": "thud", "cue": "w:Now", "off": 1.2, "vol": 0.7},
            {"type": "gallop", "cue": "w:spear", "off": 0.2, "vol": 0.8}, {"type": "snort", "cue": "w:spear", "vol": 0.5}],
})
S({
    "id": "h4", "chapter": "The Hunt", "set": "savanna", "tod": "day", "music": "tense", "amb": DAY_AMB, "lead": 0.3,
    "narration": [
        "But the hunters don't give up. They spread out. Patient. Working as a team. Hunting like this takes planning, and trust.",
        {"text": "On the next try, one throw finds its mark.", "pause": 0.6},
        "Some stone points from this site look like they were made to be fixed onto wooden shafts. Did these hunters throw their spears, or stab up close? Scientists are still debating that.",
        "And the strangest part of their day hasn't happened yet.",
    ],
    "actors": [P("hunterC", -200, [k("sneak", t=0, to=150, dur=6, hold="spear"), k("aim", cue="w:next", hold="spear", expr="focused"),
                                   k("throw", cue="w:throw", hold=None), k("cheer", cue="w:mark", off=0.6, expr="happy")], hold="spear", facing=1),
               P("hunterD", 900, [k("sneak", t=0, to=1100, dur=5, hold="spear", face=-1), k("lookout", cue="w:next", hold="spear")], hold="spear", facing=-1),
               P("hunterA", -500, [k("sneak", t=0, to=-150, dur=6, hold="spear"), k("cheer", cue="w:mark", off=0.7, hold="spear", expr="happy")], hold="spear", facing=1),
               F(-700, [k("sneak", t=0, to=-450, dur=6, expr="curious"), k("amazed", cue="w:mark", expr="amazed", pop=True),
                        k("idle", cue="w:Some", expr="curious"), k("shrug", cue="w:debating", expr="curious")])],
    "animals": [{"species": "gazelle", "x": 600, "y": -10, "size": 0.62, "facing": -1,
                 "track": [{"t": 0, "state": "graze"}, {"cue": "w:mark", "state": "dead"}]},
                {"species": "gazelle", "x": 820, "y": -40, "size": 0.58, "facing": 1,
                 "track": [{"t": 0, "state": "stand"}, {"cue": "w:mark", "state": "run", "to": 2600, "dur": 1.8, "ease": "inQuad"}]}],
    "props": [{"type": "bush", "x": 300, "y": 30, "s": 1.2}],
    "fx": [{"type": "spear_flight", "cue": "w:throw", "off": 0.2, "dur": 0.5, "from": [230, -290], "to": [600, -60], "arc": 70},
           {"type": "flash", "cue": "w:mark", "dur": 0.25, "amt": 0.35}],
    "camera": [{"t": 0, "x": 100, "zoom": 1.0}, {"cue": "w:next", "x": 350, "y": -250, "zoom": 1.25},
               {"cue": "w:Some", "x": 0, "zoom": 1.05}, {"cue": "w:strangest", "x": -450, "y": -280, "zoom": 1.6}],
    "graphics": [{"type": "tag", "cue": "w:throw#2", "dur_to": "seg:2:end", "text": "SCIENTISTS ARE STILL DEBATING THIS"},
                 {"type": "clock", "t": 0, "dur_e": 0.1, "from": 640, "to": 670, "hour": 5}],
    "sfx": [{"type": "spear", "cue": "w:throw", "off": 0.2, "vol": 0.8}, {"type": "thud", "cue": "w:mark", "vol": 0.6},
            {"type": "riser", "cue": "w:strangest", "off": -0.5, "vol": 0.4}],
})

# ================================================================== CH3 THE FEAST
S({
    "id": "f1", "chapter": "The Feast", "set": "camp", "tod": "day", "set_opts": {"cliff_x": -250}, "music": "playful", "amb": CAMP_AMB, "lead": 0.4,
    "narration": [
        "Back at camp, it's lunchtime. And Fardin learns a rule fast. Nothing gets wasted.",
        "They slice the meat with stone flakes, sharp enough to cut through hide.",
    ],
    "actors": [P("hunterC", 120, [k("butcher", t=0, hold="flake", expr="focused")], facing=1),
               P("mother", 470, [k("butcher", t=0, hold="flake", expr="focused")], facing=-1),
               P("kid", 650, [k("idle", t=0), k("talk", t=2.0)], facing=-1),
               P("elder", -420, [k("sit", t=0)], facing=1),
               F(-800, [k("walk", t=0.2, to=-180, dur=3.5, expr="happy"), k("lean_in", cue="w:slice", expr="curious")])],
    "props": [{"type": "carcass", "x": 300, "y": 10, "s": 1.0, "anim": {"butchered": [["w:Nothing", 0], ["w:hide", 1]]}}] + CAMP_PROPS[2:],
    "camera": [{"t": 0, "x": -100, "zoom": 1.0}, {"cue": "w:slice", "x": 250, "y": -230, "zoom": 1.45}],
    "graphics": [{"type": "chapter", "t": 0.3, "dur": 3.4, "kicker": "CHAPTER 3", "title": "THE FEAST", "time": "1:10 PM"},
                 {"type": "clock", "t": 0, "dur_e": 0.1, "from": 790, "to": 800, "hour": 8}],
    "sfx": [{"type": "knap", "cue": "w:slice", "vol": 0.3}],
})
S({
    "id": "f2", "chapter": "The Feast", "set": "camp", "tod": "day", "set_opts": {"cliff_x": -250}, "music": "playful", "amb": CAMP_AMB, "lead": 0.3,
    "narration": [
        "Then someone grabs a heavy rock, places a leg bone on a flat stone, and smashes it open.",
        {"text": "Inside is marrow. Soft, fatty, and full of energy. They scoop it out, and eat it. Raw.", "pause": 0.4},
        {"text": "Fardin looks like he's about to be sick.", "pause": 1.7},
        "But to them, this is a treat. Humans and our ancestors had been cracking bones for marrow for more than a million years.",
    ],
    "actors": [P("hunterB", 100, [k("crouch", t=0, hold="stone", expr="focused"), k("smash", cue="w:grabs", hold="stone", arg=0.2),
                                  k("eat", cue="w:scoop", hold="bone", expr="happy")], facing=1),
               P("kid", 380, [k("crouch", t=0), k("eat", cue="w:scoop", off=0.4, hold="bone", expr="happy")], facing=-1),
               F(-260, [k("lean_in", t=0, expr="curious"), k("lean_in", cue="w:smashes", expr="shock", pop=True),
                        k("idle", cue="w:marrow", expr="worried"), k("cover_mouth", cue="w:Raw", expr="disgust", pop=True),
                        k("no", cue="seg:2:end", expr="disgust"), k("cover_mouth", cue="w:treat", expr="disgust")],
                 say=[{"cue": "seg:2:end", "off": 0.05, "text": "Nope. Nope nope."}])],
    "props": [{"type": "rock", "x": 230, "y": 10, "s": 0.55}, {"type": "bones", "x": 260, "y": 15}, {"type": "campfire", "x": 650, "s": 0.8}],
    "camera": [{"t": 0, "x": 120, "y": -200, "zoom": 1.6}, {"cue": "w:smashes", "x": 180, "y": -170, "zoom": 2.0, "ease": "outCubic"},
               {"cue": "w:Inside", "x": 60, "y": -230, "zoom": 1.5}, {"cue": "w:Raw", "x": -240, "y": -280, "zoom": 2.1, "ease": "outBack"},
               {"cue": "w:treat", "x": 50, "y": -240, "zoom": 1.25}],
    "fx": [{"type": "flash", "cue": "w:smashes", "off": 0.15, "dur": 0.2, "amt": 0.4}],
    "shake": [{"start": {"cue": "w:smashes", "off": 0.15}, "end": {"cue": "w:smashes", "off": 0.6}, "amp": 14}],
    "graphics": [{"type": "callout", "cue": "w:Raw", "off": 0.1, "dur": 1.5, "text": "RAW?!", "x": 0.7, "y": 0.28, "color": [0.6, 1, 0.4]},
                 {"type": "fact", "cue": "w:million", "dur_e": 0.2, "big": "1,000,000+", "big_size": 92,
                  "label": "years that humans and our ancestors have cracked bones for marrow", "tag": "FACT", "side": "right", "y": 170},
                 {"type": "clock", "t": 0, "dur_e": 0.1, "from": 805, "to": 815, "hour": 8}],
    "sfx": [{"type": "crack", "cue": "w:smashes", "off": 0.15, "vol": 0.9}, {"type": "crack", "cue": "w:smashes", "off": 1.0, "vol": 0.6}],
})
S({
    "id": "f3", "chapter": "The Feast", "set": "camp", "tod": "day", "set_opts": {"cliff_x": -250}, "music": "calm", "amb": CAMP_AMB, "lead": 0.3,
    "narration": [
        "Did they cook any of it? Possibly. Some flint tools here were burned in fire, and that's actually how scientists dated the site.",
        "But how often people cooked their food this long ago is still uncertain.",
        "They almost certainly ate plants too. Roots, seeds and fruits. But plants rarely survive this long, so most of the menu is lost.",
        {"text": "Fardin decides to skip lunch.", "pause": 0.3},
        "Good call. Because later tonight, he'll find out these people were not alone on this planet.",
    ],
    "actors": [P("mother", 200, [k("cook", t=0, expr="focused")], facing=-1),
               P("hunterA", -250, [k("dig", t=0, expr="focused")], facing=1),
               P("elder", 520, [k("eat", t=0, hold="meat")], facing=-1),
               F(-650, [k("idle", t=0, expr="curious"), k("point", cue="w:flint", expr="curious"), k("idle", cue="w:plants", expr="curious"),
                        k("walk", cue="w:skip", to=-950, dur=2.2, expr="sad"), k("sit", cue="w:Good", expr="worried")])],
    "props": [{"type": "campfire", "x": 60, "s": 0.9}, {"type": "smoke", "x": 60}, {"type": "flakes", "x": -100, "y": 15},
              {"type": "bush", "x": -300, "y": -10, "s": 1.1}, {"type": "hide_rack", "x": 800, "y": -20}],
    "camera": [{"t": 0, "x": 0, "zoom": 1.05}, {"cue": "w:plants", "x": -200, "zoom": 1.15},
               {"cue": "w:skip", "x": -750, "y": -260, "zoom": 1.45}, {"cue": "w:alone", "x": -900, "y": -270, "zoom": 1.75}],
    "graphics": [{"type": "fact", "cue": "w:burned", "dur_to": "seg:0:end", "dur_off": 0.8, "big": "~315,000", "big_size": 96,
                  "label": "years: age of burned flint tools, dated using the heat they received", "tag": "HOW WE KNOW", "side": "right", "y": 170},
                 {"type": "tag", "cue": "w:often", "dur_to": "seg:1:end", "dur_off": 0.6, "text": "STILL UNCERTAIN"},
                 {"type": "clock", "t": 0, "dur_e": 0.1, "from": 820, "to": 835, "hour": 9}],
    "sfx": [{"type": "riser", "cue": "w:alone", "off": -1.2, "vol": 0.4}],
})

# ================================================================== CH4 TOOLS & FIRE
S({
    "id": "t1", "chapter": "Tools & Fire", "set": "camp", "tod": "day", "set_opts": {"cliff_x": -250}, "music": "wonder", "amb": CAMP_AMB, "lead": 0.4,
    "narration": [
        "Afternoon. In the shade of the cliff, an older man sits down with two stones. Fardin sits right next to him.",
        "This, it turns out, is high technology.",
        "He doesn't just smash the rock. He shapes it, chip by chip, as if he's planning several moves ahead. Every strike has to land at just the right angle.",
    ],
    "actors": [P("elder", 80, [k("walk", t=0, to=60, dur=1.0), k("knap", cue="w:sits", hold="stone", expr="focused")], facing=1),
               F(-400, [k("walk", t=0.3, to=-130, dur=2.5, expr="curious"), k("sit", cue="w:next", expr="curious"),
                        k("sit", cue="w:technology", expr="amazed", pop=True), k("sit", cue="w:shapes", expr="curious")])],
    "props": [{"type": "flakes", "x": 120, "y": 20, "n": 14}, {"type": "rock", "x": 330, "y": 10, "s": 0.7}],
    "camera": [{"t": 0, "x": -60, "zoom": 1.05}, {"cue": "w:technology", "x": -20, "y": -190, "zoom": 1.7},
               {"cue": "w:shapes", "x": 50, "y": -170, "zoom": 2.0}],
    "graphics": [{"type": "chapter", "t": 0.3, "dur": 3.4, "kicker": "CHAPTER 4", "title": "TOOLS & FIRE", "time": "3:30 PM"},
                 {"type": "clock", "t": 0, "dur_e": 0.1, "from": 930, "to": 940, "hour": 10}],
    "sfx": [{"type": "knap", "cue": "w:chip", "vol": 0.7}, {"type": "knap", "cue": "w:chip#2", "vol": 0.7}, {"type": "knap", "cue": "w:planning", "vol": 0.6},
            {"type": "knap", "cue": "w:moves", "vol": 0.6}],
})
S({
    "id": "t2", "chapter": "Tools & Fire", "set": "camp", "tod": "day", "set_opts": {"cliff_x": -250}, "music": "wonder", "amb": {"wind": 0.4}, "lead": 0.3,
    "narration": [
        {"text": "Then, one precise strike...", "pause": 1.0},
        "and a ready made blade pops off, sharp along its edges.",
        "Archaeologists call this the Levallois technique. The toolmaker had to picture the final tool inside the stone, before it existed.",
        "Methods like this were used across Africa and beyond for more than two hundred thousand years.",
    ],
    "actors": [P("elder", 80, [k("knap", t=0, hold="stone", expr="focused"), k("knap", cue="seg:0:end", off=0.2, hold="stone", expr="happy")], facing=1),
               F(-130, [k("sit", t=0, expr="curious"), k("amazed", cue="w:pops", expr="amazed", pop=True), k("cheer", cue="w:Levallois", expr="laugh"),
                        k("sit", cue="w:Methods", expr="amazed")])],
    "props": [{"type": "flakes", "x": 120, "y": 20, "n": 14}],
    "camera": [{"t": 0, "x": 60, "y": -170, "zoom": 2.0}, {"cue": "seg:0:end", "x": 80, "y": -160, "zoom": 2.4, "ease": "inCubic"},
               {"cue": "w:Archaeologists", "x": -20, "y": -230, "zoom": 1.3, "ease": "inOutCubic"}],
    "fx": [{"type": "letterbox", "t": 0, "dur_to": "w:Archaeologists"}, {"type": "flash", "cue": "seg:0:end", "off": 0.25, "dur": 0.3, "amt": 0.8},
           {"type": "speedlines", "cue": "seg:0:end", "off": 0.25, "dur": 1.2},
           {"type": "flake_pop", "cue": "seg:0:end", "off": 0.25, "dur": 1.8, "x": 0.55, "y": 0.62}],
    "graphics": [{"type": "callout", "cue": "w:pops", "dur": 1.6, "text": "WOW.", "x": 0.3, "y": 0.25, "color": [0.3, 0.95, 1]},
                 {"type": "fact", "cue": "w:Levallois", "dur_to": "seg:2:end", "dur_off": 0.4, "big": "LEVALLOIS", "big_size": 92,
                  "label": "Shape the stone first, then strike off a ready-made tool", "tag": "THE TECHNIQUE", "side": "right", "y": 170},
                 {"type": "fact", "cue": "w:Methods", "dur_e": 0.2, "count": 200000, "suffix": "+", "big_size": 96,
                  "label": "years that prepared-core methods like this were in use", "tag": "STAYING POWER", "side": "right", "y": 170}],
    "sfx": [{"type": "riser", "t": 0, "vol": 0.5}, {"type": "knap", "cue": "seg:0:end", "off": 0.25, "vol": 1.0}, {"type": "impact", "cue": "seg:0:end", "off": 0.25, "vol": 0.6},
            {"type": "shimmer", "cue": "w:pops", "vol": 0.5}],
})
S({
    "id": "t3", "chapter": "Tools & Fire", "set": "camp", "tod": "golden", "set_opts": {"cliff_x": -250}, "music": "calm", "amb": CAMP_AMB, "lead": 0.3,
    "narration": [
        "Fire is part of life here too. Burnt flint and bone tell us these people used it. Fire meant warmth, light, protection, and maybe cooked food.",
        "And far away in Kenya, at a site called Olorgesailie, people from around this same time carried black obsidian rock from as far as ninety kilometers away.",
        "Ninety kilometers is roughly two marathons, on foot. They also collected red and black pigments. Was that trade between groups? Some scientists think so. Others aren't sure.",
    ],
    "actors": [P("mother", 260, [k("cook", t=0)], facing=-1), P("kid", 450, [k("sit", t=0)], facing=-1),
               P("hunterD", -60, [k("carry", t=0.5, to=-20, dur=1.5), k("idle", t=2.1)], facing=1),
               F(-420, [k("idle", t=0, expr="happy"), k("point", cue="w:Kenya", expr="curious"), k("amazed", cue="w:ninety", expr="amazed", pop=True),
                        k("idle", cue="w:pigments", expr="curious")])],
    "props": [{"type": "campfire", "x": 120, "s": 1.0}, {"type": "smoke", "x": 120}, {"type": "ochre", "x": 330, "y": 20, "s": 1.4},
              {"type": "hide_rack", "x": -800, "y": -20}],
    "camera": [{"t": 0, "x": 80, "y": -220, "zoom": 1.35}, {"cue": "w:Kenya", "x": -100, "zoom": 1.0}, {"cue": "w:pigments", "x": 250, "y": -200, "zoom": 1.6}],
    "graphics": [{"type": "map", "cue": "w:Kenya", "dur_to": "seg:1:end", "dur_off": 0.5, "view": "africa", "side": "right",
                  "pins": [{"lat": 31.85, "lon": -8.87, "label": "Jebel Irhoud", "t": 0.5, "size": 24},
                           {"lat": -1.58, "lon": 36.45, "label": "Olorgesailie", "sub": "Kenya", "t": 1.6, "color": [0.25, 0.92, 1.0]}]},
                 {"type": "fact", "cue": "w:ninety", "dur_e": 0.3, "count": 90, "suffix": " km",
                  "label": "how far obsidian was carried at Olorgesailie, around 320,000 years ago", "tag": "LONG DISTANCE", "side": "left", "y": 190},
                 {"type": "tag", "cue": "w:trade", "dur_e": 0.2, "text": "DEBATED: TRADE OR TRAVEL?"},
                 {"type": "clock", "t": 0, "dur_e": 0.1, "from": 1010, "to": 1030, "hour": 11}],
})
S({
    "id": "t4", "chapter": "Tools & Fire", "set": "camp", "tod": "golden", "set_opts": {"cliff_x": -250}, "music": "wonder", "amb": CAMP_AMB, "lead": 0.3,
    "narration": [
        "Either way, these were people who planned ahead, remembered and connected. Just with very different gear.",
        "Then the sun starts to sink. And Fardin is about to find out why nobody here wanders off after dark.",
    ],
    "actors": [F(-100, [k("idle", t=0, expr="happy"), k("look_around", cue="w:sun", expr="worried")]),
               P("hunterB", 350, [k("idle", t=0, hold="spear"), k("lookout", cue="w:sun", hold="spear", expr="worried")], hold="spear", facing=-1)],
    "props": [{"type": "campfire", "x": 120, "s": 1.0}, {"type": "smoke", "x": 120}],
    "camera": [{"t": 0, "x": 100, "y": -360, "zoom": 1.05}, {"cue": "w:sun", "x": 0, "y": -300, "zoom": 1.5}],
    "graphics": [{"type": "compare", "t": 0.2, "dur_to": "seg:0:end", "dur_off": 2.2, "left_title": "THEN", "right_title": "NOW",
                  "rows": [["Stone flakes", "Steel & silicon"], ["Firelight", "Electric light"],
                           ["Walk 90 km: about 3 days", "Drive 90 km: about 1 hour"], ["Small, scattered groups", "8 billion people"]]},
                 {"type": "clock", "t": 0, "dur_e": 0.1, "from": 1060, "to": 1110, "hour": 12}],
    "sfx": [{"type": "rumble", "cue": "w:dark", "off": -1.5, "vol": 0.5}],
})

# ================================================================== CH5 DANGER AT NIGHT
NIGHT_CAMP = [{"type": "campfire", "x": 120, "s": 1.05}, {"type": "smoke", "x": 120}, {"type": "boulder", "x": -480, "y": 20, "s": 1.05, "front": True}]
S({
    "id": "n1", "chapter": "Danger at Night", "set": "camp", "tod": "dusk", "set_opts": {"cliff_x": -250}, "music": "calm", "amb": NIGHT_AMB, "lead": 0.4,
    "narration": [
        "Sunset. The group pulls in close around the fire. Fardin finally relaxes.",
        {"text": "Big mistake.", "pause": 0.8},
    ],
    "actors": [P("elder", -80, [k("sit", t=0)], facing=1), P("mother", 330, [k("sit", t=0)], facing=-1),
               P("kid", 470, [k("sit", t=0)], facing=-1), P("hunterB", 560, [k("walk", t=0, to=420, dur=2.0, hold="spear"), k("sit", t=2.1, hold=None)], facing=-1),
               F(-330, [k("walk", t=0, to=-260, dur=1.2, expr="happy"), k("sit", t=1.3, expr="happy"), k("sit", cue="w:mistake", expr="worried", pop=True)])],
    "props": NIGHT_CAMP[:2],
    "camera": [{"t": 0, "x": 100, "zoom": 1.0}, {"cue": "w:mistake", "x": -250, "y": -200, "zoom": 1.8, "ease": "outCubic"}],
    "graphics": [{"type": "chapter", "t": 0.3, "dur": 3.4, "kicker": "CHAPTER 5", "title": "DANGER AT NIGHT", "time": "8:30 PM"},
                 {"type": "clock", "t": 0, "dur_e": 0.1, "from": 1230, "to": 1236, "hour": 15}],
    "sfx": [{"type": "rumble", "cue": "w:mistake", "vol": 0.7}, {"type": "growl", "cue": "w:mistake", "off": 0.4, "vol": 0.5}],
})
S({
    "id": "n2", "chapter": "Danger at Night", "set": "camp", "tod": "night", "set_opts": {"cliff_x": -250}, "music": "dark", "amb": NIGHT_AMB, "lead": 0.3,
    "narration": [
        "Out in the dark, shapes are moving.",
        "Across Africa, early humans shared the land with lions, leopards and spotted hyenas.",
        "And here we are. This is the moment from the beginning.",
    ],
    "actors": [P("elder", -80, [k("sit", t=0), k("lookout", cue="w:lions", hold="spear", expr="worried")], facing=1),
               P("mother", 330, [k("sit", t=0, expr="worried")], facing=-1),
               P("hunterB", 520, [k("sit", t=0), k("lookout", cue="w:shapes", hold="spear", expr="worried")], facing=1),
               F(-400, [k("sit", t=0, expr="worried"), k("sneak", cue="w:shapes", to=-480, dur=1.0, expr="scared"),
                        k("crouch_hide", cue="w:land", expr="scared"), k("crouch_hide", cue="w:beginning", expr="shock", pop=True)])],
    "animals": [{"species": "hyena", "x": 1300, "facing": -1, "size": 0.95, "glow": 1.0, "track": [{"t": 0, "state": "prowl", "to": 1000, "dur": 9}]},
                {"species": "hyena", "x": 1500, "y": -40, "facing": -1, "size": 0.8, "glow": 1.0, "track": [{"t": 0.8, "state": "prowl", "to": 1250, "dur": 9}]}],
    "props": NIGHT_CAMP,
    "camera": [{"t": 0, "x": 1000, "zoom": 1.2}, {"cue": "w:Across", "x": 300, "zoom": 1.0}, {"cue": "w:here", "x": -330, "y": -270, "zoom": 1.8}],
    "graphics": [{"type": "fact", "cue": "w:lions", "dur_to": "seg:1:end", "dur_off": 0.6, "big": "PREDATORS", "big_size": 92,
                  "label": "lions, leopards and spotted hyenas all lived alongside early humans in Africa", "tag": "DANGER", "accent": [1, 0.3, 0.3], "side": "left", "y": 190},
                 {"type": "clock", "t": 0, "dur_e": 0.1, "from": 1275, "to": 1280, "hour": 16}],
    "fx": [{"type": "danger", "cue": "w:here", "dur_e": 0}],
    "sfx": [{"type": "hyena", "t": 0.8, "vol": 0.7}, {"type": "heartbeat", "cue": "w:here", "vol": 0.7}, {"type": "hyena_giggle", "cue": "w:beginning", "vol": 0.6}],
})
S({
    "id": "n3", "short_focus": 1350, "chapter": "Danger at Night", "set": "camp", "tod": "night", "set_opts": {"cliff_x": -250}, "music": "tense", "amb": NIGHT_AMB, "lead": 0.3,
    "narration": [
        "The hyenas circle closer. The adults rise, spears ready.",
        {"text": "Someone grabs a burning branch, and hurls it toward the dark.", "pause": 0.5},
        {"text": "The eyes back away.", "pause": 0.4},
        "Fire probably helped keep predators at a distance. It's one of the oldest safety tricks our species has.",
    ],
    "actors": [P("elder", 0, [k("aim", t=0, hold="spear", expr="determined")], facing=1),
               P("hunterB", 520, [k("aim", t=0, hold="spear", expr="determined")], facing=1),
               P("mother", 300, [k("idle", t=0, hold="torch", expr="determined"), k("throw", cue="w:hurls", hold=None), k("idle", cue="w:eyes", expr="happy")], facing=1),
               F(-480, [k("crouch_hide", t=0, expr="scared"), k("crouch_hide", cue="w:hurls", expr="shock", pop=True),
                        k("crouch", cue="w:eyes", expr="amazed"), k("cheer", cue="w:Fire", expr="laugh")])],
    "animals": [{"species": "hyena", "x": 1000, "facing": -1, "size": 0.95, "glow": 1.0,
                 "track": [{"t": 0, "state": "prowl", "to": 850, "dur": 3.5}, {"cue": "w:dark", "off": 0.4, "state": "run", "to": 2400, "dur": 1.6, "ease": "inQuad"}]},
                {"species": "hyena", "x": 1250, "y": -40, "facing": -1, "size": 0.8, "glow": 1.0,
                 "track": [{"t": 0, "state": "prowl", "to": 1100, "dur": 3.5}, {"cue": "w:dark", "off": 0.6, "state": "run", "to": 2600, "dur": 1.6, "ease": "inQuad"}]}],
    "props": NIGHT_CAMP,
    "lights": [],
    "fx": [{"type": "torch_flight", "cue": "w:hurls", "off": 0.2, "dur": 0.9, "from": [330, -330], "to": [950, -40], "arc": 200},
           {"type": "danger", "t": 0, "dur_to": "w:eyes"}],
    "camera": [{"t": 0, "x": 350, "zoom": 1.0}, {"cue": "w:hurls", "x": 650, "zoom": 1.05}, {"cue": "w:eyes", "x": 900, "zoom": 1.3},
               {"cue": "w:Fire", "x": 0, "zoom": 1.05}],
    "shake": [{"start": {"cue": "w:circle"}, "end": {"cue": "w:hurls", "off": 1.0}, "amp": 6}],
    "sfx": [{"type": "growl", "t": 0.3, "vol": 0.6}, {"type": "fire_throw", "cue": "w:hurls", "off": 0.2, "vol": 0.9},
            {"type": "hyena_giggle", "cue": "w:dark", "off": 0.5, "vol": 0.6}, {"type": "gallop", "cue": "w:dark", "off": 0.5, "vol": 0.5}],
    "graphics": [{"type": "tag", "cue": "w:probably", "dur_e": 0.3, "text": "LIKELY, BUT HARD TO PROVE"},
                 {"type": "clock", "t": 0, "dur_e": 0.1, "from": 1282, "to": 1290, "hour": 16}],
})
S({
    "id": "n4", "chapter": "Danger at Night", "set": "camp", "tod": "night", "set_opts": {"cliff_x": -250}, "music": "playful", "amb": NIGHT_AMB, "lead": 0.3,
    "narration": [
        "Fardin's heart is pounding. Then he remembers, he's the only one here who can literally walk through a wall.",
        {"text": "He's still not going out there.", "pause": 1.2},
    ],
    "actors": [F(-100, [k("idle", t=0, expr="worried"), k("shrug", cue="w:remembers", expr="grin"), k("no", cue="w:still", expr="determined")],
                 say=[{"cue": "seg:1:end", "off": 0.1, "text": "Absolutely not."}]),
               P("elder", 250, [k("sit", t=0)], facing=-1)],
    "props": [{"type": "campfire", "x": 120, "s": 1.05}],
    "camera": [{"t": 0, "x": 0, "y": -260, "zoom": 1.5}, {"cue": "w:still", "x": -100, "y": -300, "zoom": 2.0}],
    "sfx": [{"type": "heartbeat", "t": 0, "vol": 0.6}],
})

# ================================================================== CH6 SLEEPING IN THE CAVE
S({
    "id": "c1", "chapter": "Sleeping in the Cave", "set": "cave", "tod": "cave", "music": "calm", "amb": CAVE_AMB, "lead": 0.4,
    "narration": [
        "Late at night, inside the cave, people lie down on beds of grass. Fardin tries one. Surprisingly comfy.",
        "This part isn't a guess. At Border Cave in South Africa, scientists found grass bedding about two hundred thousand years old.",
        "It was laid on top of ash, possibly to keep crawling insects away.",
    ],
    "actors": [P("mother", 360, [k("sleep", t=0)], facing=-1, y=0), P("kid", 600, [k("sleep", t=0)], facing=-1),
               P("elder", 900, [k("sit", t=0), k("sleep", cue="w:bedding")], facing=-1),
               F(-500, [k("tiptoe", t=0, to=-180, dur=2.5, expr="curious"), k("sleep", cue="w:tries", expr="happy"),
                        k("sit", cue="w:guess", expr="curious"), k("lie_awake", cue="w:ash", expr="happy")])],
    "props": [{"type": "campfire", "x": -520, "s": 0.75}, {"type": "grass_bed", "x": -150, "s": 1.0}, {"type": "grass_bed", "x": 380, "s": 1.0},
              {"type": "grass_bed", "x": 620, "s": 0.8}, {"type": "grass_bed", "x": 920, "s": 1.0}],
    "camera": [{"t": 0, "x": 150, "zoom": 1.0}, {"cue": "w:comfy", "x": -150, "y": -170, "zoom": 1.6}, {"cue": "w:Border", "x": 250, "zoom": 1.05},
               {"cue": "w:ash", "x": 100, "y": -150, "zoom": 1.5}],
    "graphics": [{"type": "chapter", "t": 0.3, "dur": 3.4, "kicker": "CHAPTER 6", "title": "SLEEPING IN THE CAVE", "time": "11:40 PM"},
                 {"type": "fact", "cue": "w:Border", "dur_e": 0.2, "count": 200000, "big_size": 100,
                  "label": "years old: grass bedding laid over ash", "source": "Border Cave, South Africa · study published 2020", "tag": "OLDEST BEDS", "side": "right", "y": 170},
                 {"type": "clock", "t": 0, "dur_e": 0.1, "from": 1420, "to": 1430, "hour": 18}],
})
S({
    "id": "c2", "chapter": "Sleeping in the Cave", "set": "camp", "tod": "night", "set_opts": {"cliff_x": -250}, "music": "wonder", "amb": {"crickets": 0.6, "wind": 0.3},
    "lead": 0.3, "tail": 1.1, "weather": "fireflies",
    "narration": [
        {"text": "Fardin lies awake, staring out at the stars. Then his watch buzzes, with one last fact. The biggest one.", "pause": 0.4},
        {"text": "These people were not the only humans on Earth.", "pause": 0.5},
    ],
    "actors": [F(-100, [k("lie_awake", t=0, expr="happy"), k("check_watch", cue="w:buzzes", expr="curious", watch=1.3),
                        k("hands_on_head", cue="w:only", expr="shock", pop=True)],
                 say=[{"cue": "seg:1:end", "off": 0.0, "text": "Wait... what?"}])],
    "props": [{"type": "campfire", "x": 300, "s": 0.6, "glow": 0.6}],
    "camera": [{"t": 0, "x": 0, "y": -600, "zoom": 1.0}, {"t": 3.0, "x": -100, "y": -230, "zoom": 1.5, "ease": "inOutCubic"},
               {"cue": "w:only", "x": -100, "y": -300, "zoom": 2.1, "ease": "outBack"}],
    "sfx": [{"type": "buzz", "cue": "w:buzzes", "vol": 0.6}, {"type": "impact", "cue": "w:only", "vol": 0.8}],
    "graphics": [{"type": "callout", "cue": "w:only", "off": 0.3, "dur": 2.0, "text": "NOT ALONE?!", "y": 0.22},
                 {"type": "clock", "t": 0, "dur_e": 0.1, "from": 1438, "to": 1440, "hour": 18}],
})
S({
    "id": "c3", "chapter": "Sleeping in the Cave", "set": "void", "music": "wonder", "amb": {"wind": 0.2}, "lead": 0.3, "no_dip": True,
    "tunnel": [[0, 0.15]],
    "narration": [
        "Around this time, there were Neanderthal ancestors in Europe, and mysterious Denisovans in Asia, known mostly from their DNA.",
        "A small brained species called Homo naledi lived in South Africa. Another kind of archaic human lived in what is now Zambia. And on the island of Java, probably some of the last Homo erectus.",
        "At least five different kinds of humans may have shared the planet at the same time.",
    ],
    "actors": [],
    "graphics": [{"type": "map", "t": 0.1, "dur_e": 0.1, "view": "world", "center": True, "pins": []},
                 {"type": "fact", "cue": "w:five", "dur_e": 0.2, "count": 5, "suffix": "+", "big_size": 110,
                  "label": "kinds of humans may have shared the planet", "tag": "AT THE SAME TIME", "side": "right", "y": 120}],
    "sfx": [{"type": "shimmer", "t": 0.2, "vol": 0.4}],
})
pins = [("Homo sapiens", 31.85, -8.87, "w:Around", [1, .17, .17], 18, -14),
        ("Neanderthal ancestors", 43.0, 2.0, "w:Neanderthal", [1, .72, .38], 18, -14),
        ("Denisovans", 51.4, 84.7, "w:Denisovans", [0.25, 0.92, 1], 18, -14),
        ("Homo naledi", -26.0, 27.7, "w:naledi", [0.7, 0.9, 0.4], -18, -14),
        ("Kabwe, Zambia", -14.45, 28.45, "w:Zambia", [0.95, 0.6, 0.95], 18, -14),
        ("Homo erectus", -7.4, 111.4, "w:Java", [1, 0.9, 0.3], -18, 34)]
scenes[-1]["graphics"][0]["pin_cues"] = [p[3] for p in pins]
scenes[-1]["graphics"][0]["pins"] = [{"label": p[0], "lat": p[1], "lon": p[2], "color": p[4], "dx": p[5], "dy": p[6], "size": 30} for p in pins]
S({
    "id": "c4", "chapter": "Sleeping in the Cave", "set": "camp", "tod": "night", "set_opts": {"cliff_x": -250}, "music": "hopeful",
    "amb": {"crickets": 0.6, "wind": 0.3}, "lead": 0.3, "weather": "fireflies",
    "narration": [
        {"text": "Today, only one is left. Us.", "pause": 0.6},
        "Scientists are still working out why. Much later, some of those other humans even had children with our ancestors. That's why many people alive today carry a little Neanderthal or Denisovan DNA.",
    ],
    "actors": [F(-100, [k("hands_on_head", t=0, expr="shock"), k("point", cue="w:Us", expr="amazed", pop=True, face=1),
                        k("sit", cue="w:Scientists", expr="curious"), k("amazed", cue="w:DNA", expr="amazed")])],
    "props": [{"type": "campfire", "x": 300, "s": 0.6, "glow": 0.6}],
    "camera": [{"t": 0, "x": -100, "y": -300, "zoom": 1.6}, {"cue": "w:Us", "x": -60, "y": -310, "zoom": 2.2, "ease": "outBack"},
               {"cue": "w:Scientists", "x": 0, "y": -250, "zoom": 1.2}],
    "graphics": [{"type": "callout", "cue": "w:Us", "dur": 2.0, "text": "ONLY ONE LEFT", "y": 0.2, "size": 120},
                 {"type": "fact", "cue": "w:carry", "dur_e": 0.2, "big": "~1–2%", "big_size": 100,
                  "label": "Neanderthal DNA in most people with non-African ancestry", "tag": "INSIDE YOU", "side": "right", "y": 170}],
    "sfx": [{"type": "impact", "cue": "w:Us", "vol": 0.8}],
})
S({
    "id": "c5", "chapter": "Sleeping in the Cave", "set": "camp", "tod": "dawn", "set_opts": {"cliff_x": -250}, "music": "wonder", "amb": DAY_AMB, "lead": 0.4,
    "narration": [
        "Dawn is coming. Fardin's twenty four hours are almost up. His watch starts to glow.",
        {"text": "But the dial is spinning the wrong way.", "pause": 0.5},
        "Next time, Fardin lands in ancient Egypt, right in the middle of building the Great Pyramid.",
    ],
    "actors": [F(-100, [k("stretch", t=0, expr="happy"), k("check_watch", cue="w:watch", expr="happy", watch=1.2),
                        k("jump_scared", cue="w:wrong", expr="shock", pop=True, watch=2.0), k("tumble", cue="w:Next", expr="shock", y_to=-250, dur=3)]),
               P("elder", 300, [k("sleep", t=0)], facing=-1)],
    "props": [{"type": "campfire", "x": 450, "s": 0.6, "lit": False}],
    "camera": [{"t": 0, "x": 0, "zoom": 1.1}, {"cue": "w:watch", "x": -100, "y": -280, "zoom": 1.8}, {"cue": "w:Next", "x": -100, "y": -360, "zoom": 1.3}],
    "fx": [{"type": "ripple", "cue": "w:wrong", "dur": 2.0}, {"type": "watch_bloom", "cue": "w:Next", "dur": 2.0},
           {"type": "flash", "e": 0.6, "dur": 0.6}],
    "graphics": [{"type": "lower", "cue": "w:Next", "dur_e": 0.5, "text": "NEXT: ANCIENT EGYPT", "sub": "The Great Pyramid · about 4,500 years ago"},
                 {"type": "clock", "t": 0, "dur_e": 0.1, "from": 350, "to": 358, "hour": 24}],
    "sfx": [{"type": "shimmer", "cue": "w:glow", "vol": 0.5}, {"type": "rumble", "cue": "w:wrong", "vol": 0.7}, {"type": "riser", "cue": "w:Next", "vol": 0.6}],
})
S({
    "id": "c6", "chapter": "Sleeping in the Cave", "set": "void", "music": "playful", "amb": {"tunnel": 0.4}, "lead": 0.3, "tail": 2.5, "no_dip": True,
    "tunnel": [[0, 1.0], [4, 0.4]],
    "narration": ["Subscribe, or Fardin stays lost in time."],
    "actors": [F(0, [k("tumble", t=0, expr="shock"), k("wave", cue="w:lost", expr="grin")], y=-80)],
    "camera": [{"t": 0, "x": 0, "y": -260, "zoom": 1.0}],
    "graphics": [{"type": "subscribe", "t": 0.2, "dur_e": 0.2, "text": "SUBSCRIBE", "sub": "or Fardin stays lost in time"}],
    "fx": [{"type": "fade_out", "e": 0.8, "dur": 0.8}],
    "sfx": [{"type": "pop", "t": 0.3, "vol": 0.5}],
})

script = {
    "episode": "L001",
    "series": "Time Ghost",
    "title": "I Spent 24 Hours With Early Humans (300,000 years ago)",
    "voice": {"name": "en-US-ChristopherNeural", "rate": "-3%", "pitch": "-4Hz"},
    "fardin_voice": {"name": "en-US-AndrewNeural", "rate": "+8%", "pitch": "+20Hz"},
    "scenes": scenes,
}
json.dump(script, open(os.path.join(HERE, "script.json"), "w"), indent=1, ensure_ascii=False)
words = sum(len((n if isinstance(n, str) else n["text"]).split()) for s in scenes for n in s.get("narration", []))
print(f"wrote script.json: {len(scenes)} scenes, {words} narration words")
