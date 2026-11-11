"""Fair, deterministic arena physics (pymunk) + drama scoring.

Every ball is identical (radius, mass, launch speed, elasticity); only the seeded start
positions and directions differ. Nothing in here knows or cares which team a ball is on,
except for bookkeeping after it has left the arena.
"""
import math
import random

import numpy as np
import pymunk

NSEG = 360                      # ring = 360 one-degree wall segments; a gap is a run of removed segments
BALL, WALL = 1, 2

DEFAULTS = dict(
    balls_per_team=8, gap_count=1, target_seconds=[28, 38], seeds=200,
    fps=60, substeps=4, hold_seconds=1.2, hold_slowmo=0.25,
    arena_radius=395.0, ball_radius=34.0, wall_thickness=7.0,
    gravity=900.0, ring_speed=0.55, start_speed=850.0, min_speed=520.0, max_speed=1500.0,
    gap_start_deg=20.0, gap_grow_deg_per_s=0.5,
)


def gap_width_deg(cfg, t):
    """Total opening per gap at time t. Grows linearly, then is forced fully open so that
    every run finishes inside the target length (minus the winner hold)."""
    full = 360.0 / cfg["gap_count"]
    # gap_start/grow describe a single gap. With several gaps the *usable* opening (width minus
    # one ball diameter) is shared between them, so more gaps does not simply mean faster games.
    ball = math.degrees(2 * math.asin(cfg["ball_radius"] / cfg["arena_radius"]))
    usable = max(0.0, cfg["gap_start_deg"] - ball) + cfg["gap_grow_deg_per_s"] * t
    w = ball + usable / cfg["gap_count"]
    t_end = cfg["target_seconds"][1] - cfg["hold_seconds"]
    t0, t1 = t_end - 6.0, t_end - 1.5
    if t > t0:
        k = min(1.0, (t - t0) / (t1 - t0))
        w += (full - w) * k * k * (3 - 2 * k)
    return min(full, w)


def simulate(cfg, seed, record=False):
    rng = random.Random(seed)
    teams, bpt = cfg["teams"], cfg["balls_per_team"]
    nt, n = len(teams), len(teams) * bpt
    R, r, fps, sub = cfg["arena_radius"], cfg["ball_radius"], cfg["fps"], cfg["substeps"]
    dt = 1.0 / (fps * sub)
    space = pymunk.Space()
    space.gravity = (0, cfg["gravity"])
    ring = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    ring.angular_velocity = cfg["ring_speed"]
    space.add(ring)

    def make_seg(i):
        a0, a1 = math.radians(i), math.radians(i + 1)
        s = pymunk.Segment(ring, (R * math.cos(a0), R * math.sin(a0)), (R * math.cos(a1), R * math.sin(a1)), cfg["wall_thickness"])
        s.elasticity, s.friction, s.collision_type = 1.0, 0.0, WALL
        return s
    segs = {i: make_seg(i) for i in range(NSEG)}
    space.add(*segs.values())
    centers = [int(round(g * NSEG / cfg["gap_count"])) for g in range(cfg["gap_count"])]        # first gap starts on the right, clear of the hook text
    state = dict(w=0)

    def open_indices(w):
        out = set()
        for c in centers:
            for k in range(w):
                out.add((c - w // 2 + k) % NSEG)
        return out

    def set_gap(w):
        if w == state["w"]:
            return
        for i in open_indices(w):
            if i in segs:
                space.remove(segs.pop(i))
        state["w"] = w

    def seal():
        for i in range(NSEG):
            if i not in segs:
                segs[i] = make_seg(i)
                space.add(segs[i])
        state["w"] = 0

    # identical balls; shuffled team order so no team gets systematically better spots
    order = [i % nt for i in range(n)]
    rng.shuffle(order)
    team_of = np.array(order)
    bodies, pts = [], []
    for i in range(n):
        for _ in range(10000):
            a, d = rng.uniform(0, 2 * math.pi), math.sqrt(rng.random()) * (R - r - 30)
            p = (d * math.cos(a), d * math.sin(a))
            if all((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 > (2 * r + 10) ** 2 for q in pts):
                break
        pts.append(p)
        b = pymunk.Body(1.0, pymunk.moment_for_circle(1.0, 0, r))
        b.position = p
        a = rng.uniform(0, 2 * math.pi)
        b.velocity = (cfg["start_speed"] * math.cos(a), cfg["start_speed"] * math.sin(a))
        sh = pymunk.Circle(b, r)
        sh.elasticity, sh.friction, sh.collision_type = 1.0, 0.0, BALL
        sh.idx = i
        space.add(b, sh)
        bodies.append(b)

    clock = dict(t=0.0)
    bounces, near, last_near = [], [], [-9.0] * n

    def gap_edge_dist(i):
        """Angular distance (deg) from ball i to the nearest gap; negative when inside a gap."""
        p = bodies[i].position
        loc = (math.degrees(math.atan2(p.y, p.x) - ring.angle)) % 360
        best, w = 999.0, state["w"]
        for c in centers:
            mid = c - w // 2 + w / 2.0
            best = min(best, abs((loc - mid + 180) % 360 - 180) - w / 2.0)
        return best

    def note_near(i):
        if clock["t"] - last_near[i] > 0.7:
            near.append((clock["t"], i))
            last_near[i] = clock["t"]

    def wall_hit(arb, sp, data):
        if state.get("hold") or not arb.is_first_contact:
            return
        i = arb.shapes[0].idx if arb.shapes[0].collision_type == BALL else arb.shapes[1].idx
        p = bodies[i].position
        bounces.append((clock["t"], arb.total_impulse.length, 0, p.x))
        if state["w"] and gap_edge_dist(i) < 4.0:          # bounced off the wall right beside the gap
            note_near(i)

    def ball_hit(arb, sp, data):
        if arb.is_first_contact and not state.get("hold"):
            p = bodies[arb.shapes[0].idx].position
            bounces.append((clock["t"], arb.total_impulse.length, 1, p.x))

    space.on_collision(BALL, WALL, post_solve=wall_hit)
    space.on_collision(BALL, BALL, post_solve=ball_hit)

    alive = np.ones(n, bool)
    counts = [bpt] * nt
    exits, elims, timeline = [], [], [(0.0, tuple(counts))]
    in_mouth = [False] * n
    max_frames = int(round((cfg["target_seconds"][1] - cfg["hold_seconds"]) * fps))
    hold_frames = int(round(cfg["hold_seconds"] * fps))
    pos = np.zeros((max_frames + hold_frames + 1, n, 2), np.float32) if record else None
    ang, gapw = [], []
    winner, end_frame, duel_t = None, None, None
    lo, hi = cfg["min_speed"], cfg["max_speed"]

    def snapshot(f):
        if record:
            for i in range(n):
                if alive[i]:
                    pos[f, i] = bodies[i].position
            ang.append(ring.angle)
            gapw.append(state["w"])

    def clamp():
        for i in range(n):
            if not alive[i]:
                continue
            v = bodies[i].velocity
            s = v.length
            if s < 1e-3:
                a = rng.uniform(0, 2 * math.pi)
                bodies[i].velocity = (lo * math.cos(a), lo * math.sin(a))
            elif s < lo:
                bodies[i].velocity = v * (lo / s)
            elif s > hi:
                bodies[i].velocity = v * (hi / s)

    set_gap(int(gap_width_deg(cfg, 0)))
    snapshot(0)
    f = 0
    while f < max_frames and winner is None:
        f += 1
        for s in range(sub):
            clock["t"] = ((f - 1) * sub + s + 1) * dt
            space.step(dt)
            for i in range(n):
                if not alive[i]:
                    continue
                p = bodies[i].position
                d = math.hypot(p.x, p.y)
                if d > R + r:                                   # fully through the gap → out
                    alive[i] = False
                    tm = int(team_of[i])
                    counts[tm] -= 1
                    v = bodies[i].velocity
                    exits.append((clock["t"], i, tm, p.x, p.y, v.x, v.y))
                    timeline.append((clock["t"], tuple(counts)))
                    space.remove(bodies[i], *bodies[i].shapes)
                    left = [k for k in range(nt) if counts[k] > 0]
                    if counts[tm] == 0:
                        elims.append((clock["t"], tm))
                        if len(left) == 2 and duel_t is None:
                            duel_t = clock["t"]
                    if len(left) == 1:
                        winner, end_frame = left[0], f
                        break
                elif state["w"]:
                    m = d > R - r * 0.55 and gap_edge_dist(i) < 0   # poking into the gap mouth
                    if in_mouth[i] and not m and d < R - r * 0.9:
                        note_near(i)                               # …and came back in
                        in_mouth[i] = False
                    elif m:
                        in_mouth[i] = True
            if winner is not None:
                break
        if winner is None:
            clamp()
            set_gap(int(gap_width_deg(cfg, f / fps)))
        snapshot(f)
    if winner is None:      # cannot happen once the gap is fully open, but never crash a batch
        return dict(seed=seed, ok=False)
    if nt == 2:
        duel_t = next((t for t, c in timeline if sum(c) <= max(4, bpt // 2 + 1)), elims[-1][0] - 1e-3)
    # winner hold: gap sealed, slow motion (one substep per frame)
    seal()
    state["hold"] = True
    slow = max(1, int(round(sub * cfg["hold_slowmo"])))
    t_end = clock["t"]
    for k in range(1, hold_frames + 1):
        for _ in range(slow):
            space.step(dt)
        snapshot(end_frame + k)
    total_frames = end_frame + hold_frames
    res = dict(seed=seed, ok=True, winner=winner, t_end=t_end, end_frame=end_frame, total_frames=total_frames,
               seconds=total_frames / fps, exits=exits, elims=elims, near=near, duel_t=duel_t, timeline=timeline,
               bounces=bounces, team_of=team_of, n=n)
    if record:
        res.update(pos=pos[: total_frames + 1], ring_angle=np.array(ang), gap_w=np.array(gapw), centers=centers)
    return res


def counts_at(timeline, t):
    c = timeline[0][1]
    for tt, cc in timeline:
        if tt > t:
            break
        c = cc
    return c


def drama(res, cfg):
    """Score a finished run for watchability. Hard requirements cost so much that any run
    meeting all four always outranks one that does not."""
    if not res.get("ok"):
        return -1e9, {}
    lo, hi = cfg["target_seconds"]
    T, w = res["t_end"], res["winner"]
    b = {}
    sec = res["seconds"]
    b["length_s"] = round(sec, 2)
    b["length_ok"] = lo <= sec <= hi
    nm = len([t for t, _ in res["near"] if t < T])
    b["near_misses"] = nm
    duel = T - res["duel_t"]
    b["duel_s"] = round(duel, 2)
    c80 = counts_at(res["timeline"], 0.8 * T)
    lead = c80[w] - max(c for k, c in enumerate(c80) if k != w)
    b["counts_at_80pct"] = list(c80)
    b["winner_lead_at_80pct"] = lead
    leaders, changes = None, 0
    for t, c in res["timeline"]:
        top = max(c)
        l = tuple(k for k, v in enumerate(c) if v == top)
        if len(l) == 1 and l != leaders:
            changes += leaders is not None
            leaders = l
    b["lead_changes"] = changes
    cd = counts_at(res["timeline"], res["duel_t"])
    duo = sorted((v for v in cd if v > 0), reverse=True)
    b["duel_start_counts"] = list(cd)
    final = counts_at(res["timeline"], T)[w]
    b["winner_balls_left"] = final
    ex = [0.0] + [e[0] for e in res["exits"]]
    b["longest_lull_s"] = round(max(b_ - a_ for a_, b_ in zip(ex, ex[1:])), 2)
    b["hard_ok"] = b["length_ok"] and nm >= 3 and duel >= 4.0 and lead <= 1
    s = 0.0
    s += 0 if b["length_ok"] else -1000 - 50 * min(abs(sec - lo), abs(sec - hi))
    s += min(nm, 8) * 3 if nm >= 3 else -300
    s += (20 + min(duel - 4, 4) * 3 - max(0, duel - 11) * 6) if duel >= 4 else -300 - (4 - duel) * 20
    s += {True: 25}.get(lead <= -1, 18 if lead == 0 else 8 if lead == 1 else -300 - 20 * lead)
    s += {1: 15, 2: 10, 3: 5}.get(final, 0)
    s += 10 if len(duo) >= 2 and duo[0] - duo[1] <= 1 else 0
    s += min(changes, 6) * 2
    s += 5 if b["longest_lull_s"] < 5 else -5 * (b["longest_lull_s"] - 5)
    b["score"] = round(s, 1)
    return s, b
