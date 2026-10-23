"""Candidate generation and the weighted viral scoring model.

Weights (spec): hook 25 · retention 20 · emotion 15 · curiosity/share 15 · standalone 10 · visual 10 · loop 5.
Each factor is a 0–100 score computed from transcript text, prosody (energy/flux), shots and faces.
Scores are heuristics: an agent (or the user) can override the choice with --selection.
"""
from __future__ import annotations

import csv
import math
import re
from collections import Counter

import numpy as np

from .common import log, write_json
from .transcribe import norm

WEIGHTS = {"hook": 0.25, "retention": 0.20, "emotion": 0.15, "curiosity": 0.15,
           "standalone": 0.10, "visual": 0.10, "loop": 0.05}

HOOK = set("""never nobody secret truth mistake mistakes wrong stop worst best biggest crazy insane actually shocking
million billion why how lie lied lying fired quit broke rich money die died dead killed hate love afraid impossible
everyone instantly exactly warning problem dangerous illegal banned failed failure regret only first last ever""".split())
EMOTION = set("""love loved hate hated cried cry crying scared afraid terrified angry furious mad laughed laugh laughing
funny hilarious amazing incredible terrible horrible devastated heartbroken proud shocked insane crazy wild
unbelievable beautiful painful pain fear happy sad alone lost died death dying hurt embarrassing embarrassed
ashamed nervous panic panicked excited obsessed disgusting brutal""".split())
CURIOSITY = set("""secret nobody reason truth actually realized discovered learned lesson mistake trick hack why how
turns most nobody's people imagine guess surprising surprisingly weird strange hidden real really except until
because instead however but""".split())
CONTRAST = {"but", "actually", "instead", "however", "except", "until", "turns"}
DANGLING = set("""and but so because which that also or then he she they it this those these him her them yeah yes no
right okay like plus""".split())
PRONOUN_REF = {"he", "she", "they", "him", "her", "them", "it", "that", "this", "those", "these", "his", "their"}
STOP = set("""the a an and or but so to of in on at for with from by as is are was were be been being it its this that
these those i you he she we they me him her us them my your his our their not no yes do does did done have has had
just like really very can could would should will shall may might must there here what when where who whom which why
how all any some more most much many such than then too also about into over after before out up down off again
once only own same other just get got go going gonna know think mean yeah okay right well thing things kind sort lot
one two because if even ever way say said says see thats dont im youre theyre its i'm you're it's that's don't
didn't can't won't isn't wasn't i've you've we're they're let's""".split())
NUM_RE = re.compile(r"\d|\b(hundred|thousand|million|billion|percent|half|double|triple|twice)\b", re.I)


def _toks(text: str) -> list[str]:
    return [norm(t) for t in text.split() if norm(t)]


def _clip(x, lo=0.0, hi=100.0):
    return float(max(lo, min(hi, x)))


class Prosody:
    def __init__(self, energy: dict):
        self.hop = energy.get("hop", 0.1)
        self.db = np.array(energy.get("rms_db") or [-60.0])
        self.flux = np.array(energy.get("flux") or [0.0])
        voiced = self.db[self.db > np.percentile(self.db, 30)] if len(self.db) > 10 else self.db
        self.med = float(np.median(voiced))
        self.sd = float(np.std(voiced) + 1e-6)
        self.fmed = float(np.median(self.flux) + 1e-6)

    def window(self, s, e):
        a, b = int(s / self.hop), max(int(s / self.hop) + 1, int(e / self.hop))
        return self.db[a:b], self.flux[a:b]

    def z(self, s, e, pct=50):
        d, _ = self.window(s, e)
        return (float(np.percentile(d, pct)) - self.med) / self.sd if len(d) else 0.0


def hook_score(sent: dict, words: list[dict], pros: Prosody) -> float:
    toks = _toks(sent["text"])
    if not toks:
        return 0.0
    first12 = toks[:12]
    sc = 35.0
    if sent["text"].rstrip().endswith("?"):
        sc += 15
    sc += min(20, 8 * sum(t in HOOK for t in first12))
    if NUM_RE.search(sent["text"]):
        sc += 10
    if any(t in ("you", "your", "you're") for t in first12):
        sc += 8
    n = len(toks)
    sc += 10 if 4 <= n <= 16 else (-10 if n > 28 else 0)
    if toks[0] in DANGLING:
        sc -= 25
    sc += float(np.clip(pros.z(sent["s"], min(sent["e"], sent["s"] + 2.0), 70) * 8, -10, 15))
    return _clip(sc)


def hook_type(text: str) -> str:
    t = text.lower()
    if text.rstrip().endswith("?"):
        return "question"
    if NUM_RE.search(text):
        return "stat"
    toks = set(_toks(t))
    if toks & EMOTION:
        return "emotional"
    if toks & {"never", "nobody", "wrong", "truth", "secret", "stop", "worst", "best", "lie", "everyone"}:
        return "bold-claim"
    if toks & {"i", "we", "my", "was", "were", "when"}:
        return "story"
    return "statement"


def score_window(sents, i, j, words, pros: Prosody, scenes, face_samples, prior_dur=35.0) -> dict:
    S = sents[i:j + 1]
    s0, s1 = S[0]["s"], S[-1]["e"]
    dur = s1 - s0
    ws = words[S[0]["wi"][0]: S[-1]["wi"][1] + 1]
    text = " ".join(x["text"] for x in S)
    toks = _toks(text)
    nw = max(1, len(toks))

    # hook — first sentence, or the strongest short line usable as a cold-open teaser
    first_hook = hook_score(S[0], words, pros)
    cold = None
    for k, x in enumerate(S[1:], 1):
        if x["e"] - x["s"] <= 3.6 and len(_toks(x["text"])) >= 3:
            h = hook_score(x, words, pros)
            if h > first_hook + 15 and (cold is None or h > cold[1]):
                cold = (k, h)
    hook = max(first_hook, cold[1] - 5) if cold else first_hook

    # retention — pace, dead air, dynamics, length fit
    gaps = [b["s"] - a["e"] for a, b in zip(ws, ws[1:])]
    dead = sum(g for g in gaps if g > 0.5)
    speech = max(1e-3, dur - dead)
    wps = nw / speech
    pace = 100 - min(60, abs(wps - 3.1) * 45)
    d_db, d_fx = pros.window(s0, s1)
    dyn = float(np.std(d_db)) if len(d_db) else 0
    retention = (pace * 0.45 + (100 - min(100, dead / dur * 400)) * 0.25
                 + min(100, dyn * 9) * 0.10 + 100 * math.exp(-((dur - prior_dur) / 14) ** 2) * 0.20)

    # emotion — lexicon, exclamations, loudness peaks, onset density
    emo_hits = sum(t in EMOTION for t in toks)
    flux_term = float(np.clip((np.mean(d_fx) / pros.fmed - 1) * 15, 0, 15)) if len(d_fx) else 0.0
    emotion = (min(45, emo_hits / nw * 100 * 9) + min(15, text.count("!") * 7)
               + float(np.clip(pros.z(s0, s1, 95) * 12, 0, 25)) + flux_term)
    emotion = _clip(emotion + 10)

    # curiosity / shareability
    q = sum(x["text"].rstrip().endswith("?") for x in S)
    cur = (min(40, sum(t in CURIOSITY for t in toks) * 6) + min(20, q * 10)
           + min(20, len(NUM_RE.findall(text)) * 8) + min(10, sum(t in CONTRAST for t in toks) * 4)
           + min(10, sum(t in ("you", "your") for t in toks) * 2))
    curiosity = _clip(cur + 10)

    # standalone clarity
    ft = _toks(S[0]["text"])
    st = 100.0
    if ft and ft[0] in DANGLING:
        st -= 35
    if any(t in PRONOUN_REF for t in ft[:4]):
        st -= 15
    if not re.search(r"[.?!]['\"”)]*$", S[-1]["text"].strip()):
        st -= 25
    if i > 0 and S[0]["s"] - sents[i - 1]["e"] < 0.15:
        st -= 10
    standalone = _clip(st)

    # visual — faces on screen, shot variety, motion
    fs = [x for x in face_samples if s0 <= x["t"] <= s1]
    face_ratio = np.mean([len(x["faces"]) > 0 for x in fs]) if fs else 0
    motion = np.mean([x["motion"] for x in fs]) if fs else 0
    shots = sum(1 for sc in scenes if s0 < sc["s"] < s1)
    visual = _clip(face_ratio * 55 + min(25, shots * 6) + min(20, motion * 4))

    # loop — does the ending echo the opening or land on a short punch?
    a = {t for t in ft if t not in STOP}
    b = {t for t in _toks(S[-1]["text"]) if t not in STOP}
    jac = len(a & b) / max(1, len(a | b))
    loop = _clip(jac * 220 + (30 if len(_toks(S[-1]["text"])) <= 8 else 0)
                 + (15 if S[-1]["text"].rstrip().endswith(("?", "!")) else 0) + 15)

    f = {"hook": round(hook, 1), "retention": round(_clip(retention), 1), "emotion": round(emotion, 1),
         "curiosity": round(curiosity, 1), "standalone": round(standalone, 1), "visual": round(visual, 1),
         "loop": round(loop, 1)}
    total = sum(WEIGHTS[k] * v for k, v in f.items())
    return {"i": i, "j": j, "start": round(s0, 3), "end": round(s1, 3), "duration": round(dur, 2),
            "factors": f, "score": round(total, 1), "text": text,
            "first_line": S[0]["text"], "last_line": S[-1]["text"],
            "cold_open_sentence": (i + cold[0]) if cold else None,
            "hook_type": hook_type(S[cold[0]]["text"] if cold else S[0]["text"])}


def generate_candidates(tr, ana, face_samples, min_d=18, max_d=55, prior_dur=35.0) -> list[dict]:
    sents = [s for s in tr["sentences"] if s["text"].strip()]
    pros = Prosody(ana["audio"])
    out = []
    for i in range(len(sents)):
        for j in range(i, len(sents)):
            d = sents[j]["e"] - sents[i]["s"]
            if d > max_d:
                break
            if d >= min_d:
                out.append(score_window(sents, i, j, tr["words"], pros, ana["scenes"], face_samples, prior_dur))
    for c in out:
        c["sentences"] = sents
    return out


def overlap(a, b) -> float:
    inter = max(0.0, min(a["end"], b["end"]) - max(a["start"], b["start"]))
    return inter / max(1e-6, min(a["end"] - a["start"], b["end"] - b["start"]))


def choose(cands: list[dict], n: int, min_score: float = 48.0) -> tuple[list[dict], list[dict]]:
    """Distinct top-N (≤20% overlap). Also returns the distinct candidate pool (≥20 when possible) for the report."""
    ranked = sorted(cands, key=lambda c: -c["score"])
    pool: list[dict] = []
    for c in ranked:
        if all(overlap(c, p) < 0.2 for p in pool):
            pool.append(c)
        if len(pool) >= max(24, n * 2):
            break
    best = pool[0]["score"] if pool else 0
    chosen = [c for c in pool if c["score"] >= max(min_score, best - 28)][:n]
    return chosen, pool


# generic verbs/adverbs that make useless hashtags
TAG_STOP = set("""still hear heard answer answered happened happen people everything nothing something anything
nobody somebody everyone believe believed lost tell told want wanted need needed make made take took come came
look looked feel felt give gave keep kept start started actually honestly literally basically maybe never always
again every through about would could should cannot there their where which while years year time times things
back first last next part means mean thought think know knew right left down came went going""".split())


def keywords(text: str, corpus_counts: Counter, k=4) -> list[str]:
    toks = [t for t in _toks(text) if t not in STOP and t not in TAG_STOP and len(t) > 3 and not t.isdigit()]
    c = Counter(toks)
    total = sum(corpus_counts.values()) or 1
    scored = {t: n * math.log(total / (1 + corpus_counts[t])) for t, n in c.items()}
    return [t for t, _ in sorted(scored.items(), key=lambda x: -x[1])[:k]]


def default_package(c: dict, sents, corpus_counts, content_type: str, creator: str | None,
                    niche_tag: str | None = None) -> dict:
    """Plain, quote-based packaging. Agent/user overrides via --selection replace these."""
    hook_s = sents[c["cold_open_sentence"]] if c["cold_open_sentence"] is not None else sents[c["i"]]
    hook_text = re.sub(r"^(so|and|but|well|okay|yeah|like|um|uh),?\s+", "", hook_s["text"].strip(), flags=re.I)
    words = hook_text.split()
    if len(words) > 10:  # cut at the last clause boundary inside 10 words rather than mid-phrase
        cut = max((k for k, w in enumerate(words[:10]) if w.endswith((",", ";", ":"))), default=None)
        words = words[:cut + 1] if cut and cut >= 4 else words[:10]
    title = " ".join(words).rstrip(",;:")
    title = title[:1].upper() + title[1:]
    kws = keywords(c["text"], corpus_counts, 3)
    niche = {"podcast": "podcast", "comedy": "comedy", "motivational": "motivation", "educational": "learnontiktok",
             "gaming": "gaming", "interview": "interview"}.get(content_type, "shorts")
    niche = niche_tag or niche
    tags = [f"#{w}" for w in kws if w != niche] + [f"#{niche}"]
    quote = c["last_line"] if len(c["last_line"].split()) >= 5 else c["first_line"]
    attribution = f" — {creator}" if creator else ""
    return {"title": title, "hook": hook_s["text"], "post_caption": f"“{quote.strip()}”{attribution}",
            "hashtags": tags[:5], "keywords": kws}


CT_LEX = {
    "podcast": set("business money company startup market customers revenue podcast episode sales brand marketing".split()),
    "comedy": set("funny joke laughed hilarious lol dude bro crazy stupid weird".split()),
    "motivational": set("dream discipline success goals mindset believe purpose hustle grind life fear".split()),
    "educational": set("learn explain science study research data percent example process system works because".split()),
    "gaming": set("game play level boss kill spawn stream chat gg clutch ranked".split()),
    "interview": set("question asked tell career interview journey moment started".split()),
}


NICHE_ALIASES = {
    "business": "podcast", "podcast": "podcast", "finance": "podcast", "money": "podcast", "entrepreneur": "podcast",
    "comedy": "comedy", "funny": "comedy", "streamer": "comedy", "streamers": "comedy",
    "motivation": "motivational", "motivational": "motivational", "self-improvement": "motivational",
    "education": "educational", "educational": "educational", "science": "educational", "tech": "educational",
    "gaming": "gaming", "games": "gaming", "interview": "interview", "interviews": "interview",
    "debate": "interview", "debates": "interview", "news": "interview",
}


def resolve_niche(niche: str | None) -> tuple[str | None, str | None]:
    """User-chosen niche → (editing profile, hashtag). Unknown niches keep the user's word as the hashtag."""
    if not niche:
        return None, None
    key = niche.strip().lower()
    tag = re.sub(r"[^a-z0-9]", "", key)
    return NICHE_ALIASES.get(key, "podcast"), tag or None


def classify_content(tr, ana, niche: str | None = None) -> str:
    profile, _ = resolve_niche(niche)
    if profile:
        return profile
    toks = Counter(_toks(" ".join(s["text"] for s in tr["sentences"])))
    scores = {k: sum(toks[w] for w in v) for k, v in CT_LEX.items()}
    fs = ana["faces_summary"]
    if fs.get("face_ratio", 0) < 0.25 and len(ana["scenes"]) > tr["duration"] / 6:
        scores["gaming"] += 8
    if fs.get("multi_face_ratio", 0) > 0.3:
        scores["interview"] += 4
        scores["podcast"] += 4
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "podcast"


def write_scores_csv(path, pool: list[dict], chosen: list[dict]) -> None:
    ids = {id(c) for c in chosen}
    with open(path, "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["rank", "selected", "start", "end", "duration", "score", *WEIGHTS, "hook_type", "first_line"])
        for r, c in enumerate(pool, 1):
            wr.writerow([r, "yes" if id(c) in ids else "", c["start"], c["end"], c["duration"], c["score"],
                         *[c["factors"][k] for k in WEIGHTS], c["hook_type"], c["first_line"][:140]])


def select(tr, ana, face_samples, dirs, n: int, creator: str | None, prior_dur: float = 35.0,
           niche: str | None = None) -> tuple[list[dict], str]:
    ctype = classify_content(tr, ana, niche)
    niche_tag = resolve_niche(niche)[1]
    cands = generate_candidates(tr, ana, face_samples, prior_dur=prior_dur)
    if not cands:
        raise RuntimeError("no candidate windows: transcript has no 18–55 s stretch of speech")
    chosen, pool = choose(cands, n)
    sents = cands[0]["sentences"]
    corpus = Counter(_toks(" ".join(s["text"] for s in sents)))
    for c in pool:
        c.pop("sentences", None)
    for c in chosen:
        c["package"] = default_package(c, sents, corpus, ctype, creator, niche_tag)
    write_scores_csv(dirs["Analysis"] / "candidate_scores.csv", pool, chosen)
    log(f"content type: {ctype} ({'chosen by user: ' + niche if niche else 'auto-detected'}); {len(cands)} windows scored, {len(pool)} distinct candidates, {len(chosen)} selected")
    if len(chosen) < n:
        log(f"  only {len(chosen)} candidates cleared the quality bar (score ≥ max(48, best−28)); not padding with weak clips")
    return chosen, ctype


def from_selection(entries: list[dict], tr, ana, face_samples, dirs, creator, prior_dur=35.0,
                   niche: str | None = None) -> tuple[list[dict], str]:
    """Use an agent/user-authored selection (start/end + optional packaging) instead of auto-choice.
    Windows snap to whole sentences; every entry is still scored so the report stays comparable."""
    ctype = classify_content(tr, ana, niche)
    niche_tag = resolve_niche(niche)[1]
    sents = [s for s in tr["sentences"] if s["text"].strip()]
    pros = Prosody(ana["audio"])
    corpus = Counter(_toks(" ".join(s["text"] for s in sents)))
    chosen = []
    for e in entries:
        i = next((k for k, s in enumerate(sents) if s["s"] >= e["start"] - 0.35), None)
        j = max((k for k, s in enumerate(sents) if s["e"] <= e["end"] + 0.35), default=None)
        if i is None or j is None or j < i:
            raise RuntimeError(f"selection {e} does not cover any whole sentence")
        c = score_window(sents, i, j, tr["words"], pros, ana["scenes"], face_samples, prior_dur)
        if "cold_open" in e:
            co = e["cold_open"]
            if co is False or co is None:
                c["cold_open_sentence"] = None
            elif isinstance(co, (int, float)) and not isinstance(co, bool):
                k = min(range(len(sents)), key=lambda k: abs(sents[k]["s"] - co))
                c["cold_open_sentence"] = k if i < k <= j else None
        pkg = default_package(c, sents, corpus, e.get("content_type", ctype), creator, niche_tag)
        pkg.update({k: e[k] for k in ("title", "hook", "post_caption", "hashtags", "commentary",
                                      "retention_notes", "caption_style", "cover_text") if k in e})
        c["package"] = pkg
        c["selected_by"] = e.get("selected_by", "agent")
        chosen.append(c)
    log(f"content type: {ctype} ({'chosen by user: ' + niche if niche else 'auto-detected'}); "
        f"using {len(chosen)} clips from the provided selection")
    return chosen, ctype
