"""NPC x CYBERWOLF - TWO SHADOWS. ONE ARMY.  (timeline)

Every visual event below is placed on a measured musical event from
source/music_events.json. B(n) is the video time of output beat n (n = 0 is the
music entrance). Beat classes/strengths quoted in comments are measured onset
rises in dB (see the event map): the drops are the loudest transients in the
song, the logo lands on the strongest bass entrance.

Characters are always sampled from their original images:
  cw  = CyberWolf (Real-ESRGAN restoration of the original drawing)
  npc = NPC (the original photograph)
"""
from __future__ import annotations

import math

import numpy as np

import fx
from engine import (CW_EMERALD, COOL_WHITE, NPC_SILVER, Black, CharShot, Ctx, DuoShot, Impact, LogoShot, Overlay,
                    Seg, Sweep, TextCue, Timeline, Trans)
from fx import Cam, clamp01, smooth
from typo import EMERALD, SILVER, WHITE, Text

EASE = {"lin": lambda x: clamp01(x), "smooth": fx.smooth, "out": fx.ease_out_cubic, "in": fx.ease_in_cubic,
        "inout": fx.ease_in_out_cubic, "outexpo": fx.ease_out_expo, "inexpo": fx.ease_in_expo}


def keys(*kf):
    """Camera keyframes: (t, Cam, ease-into-this-key)."""
    kf = [(k[0], k[1], k[2] if len(k) > 2 else "smooth") for k in kf]

    def f(t):
        if t <= kf[0][0]:
            return kf[0][1]
        for (t0, c0, _), (t1, c1, e) in zip(kf, kf[1:]):
            if t <= t1:
                return c0.mix(c1, EASE[e]((t - t0) / max(1e-6, t1 - t0)))
        return kf[-1][1]
    return f


def build(ctx: Ctx) -> Timeline:
    ev = ctx.ev
    B = ctx.beat
    F = 1 / ctx.fps
    an = ctx.A.anchors
    cwA, npA = an["cyberwolf"], an["npc"]
    EYES = (cwA["eyes"][0], cwA["eyes"][1] + 0.03)
    GOG = tuple(cwA["goggles"])
    LENS_R = tuple(cwA["lens_right"])
    lb = npA["letters_bbox"]
    LET = ((lb[0] + lb[2]) / 2, (lb[1] + lb[3]) / 2)
    HEAD = (npA["head_center"][0], 0.30)
    tl = Timeline(ctx, ev["duration"])
    T_END = ev["frames"] / ctx.fps

    # pre-roll pulses measured in the edited track (sub-bass swells before the entrance)
    pre = [o for o in ev["onsets"] if o["t"] < ev["entrance_t"] - 0.05 and o["rise_sub"] >= 13]
    pre.sort(key=lambda o: -o["rise_sub"])
    T_FLASH_NPC, T_FLASH_CW = sorted(o["frame"] / ctx.fps for o in pre[:2])

    ENTR, DROP_A, DROP_B, LOGO = B(0), B(8), B(40), B(56)
    assert abs(DROP_B * ctx.fps - 1425) < 1.5 and abs(LOGO * ctx.fps - 1958) < 1.5, (DROP_B * ctx.fps, LOGO * ctx.fps)

    # ============================================================== impacts (camera + post)
    imp = ctx.impacts
    # bass breathing: every strong 808 hit inside a drop gives the camera a small push
    designed = {8, 12, 16, 20, 32, 33, 34, 35, 36, 40, 44, 48, 52, 56, 59}
    for b in ev["beats"]:
        if b["n"] in designed or b["section"] != "drop" or b["class"] not in ("strong", "impact"):
            continue
        imp.append(Impact(b["t"], punch=0.018 + 0.0006 * max(0, b["rise_db"] - 25), shake=3.0, decay=0.06, seed=b["n"]))
    imp += [
        Impact(ENTR, chroma=0.004, flash=0.06, decay=0.06, seed=1),
        Impact(DROP_A, punch=0.10, shake=20, flash=0.38, chroma=0.010, barrel=0.035, glitch=0.5, decay=0.075, seed=2),
        Impact(B(11), punch=0.03, shake=6, decay=0.06, seed=3),
        Impact(B(12), punch=0.05, shake=10, chroma=0.004, decay=0.06, seed=4),
        Impact(B(15), punch=0.05, shake=8, flash=0.10, decay=0.07, seed=5),
        Impact(B(16), punch=0.06, shake=12, flash=0.16, chroma=0.006, decay=0.06, seed=6),
        Impact(B(18), punch=0.03, shake=6, glitch=0.6, chroma=0.006, decay=0.05, seed=7),
        Impact(B(19), punch=0.04, shake=8, decay=0.06, seed=8),
        Impact(B(20), punch=0.06, shake=12, flash=0.18, chroma=0.006, decay=0.07, seed=9),
        Impact(B(32), punch=0.08, shake=14, flash=0.28, chroma=0.007, decay=0.07, seed=10),
        Impact(B(33), punch=0.04, shake=8, decay=0.05, seed=11),
        Impact(B(34), punch=0.06, shake=12, flash=0.14, chroma=0.006, decay=0.06, seed=12),
        Impact(B(35), punch=0.04, shake=9, decay=0.05, seed=13),
        Impact(B(36), punch=0.07, shake=14, flash=0.22, chroma=0.006, decay=0.07, seed=14),
        Impact(B(36) + 0.83, glitch=0.35, decay=0.04, seed=15),               # 22.36 s hi-hat accent
        # THE drop: everything hits on the same frame
        Impact(DROP_B, punch=0.16, shake=26, flash=0.95, flash_color=(1.0, 1.0, 1.0), chroma=0.016, glitch=0.9,
               wave=46, barrel=0.06, decay=0.085, seed=16),
        Impact(B(44), punch=0.07, shake=14, flash=0.35, flash_color=(0.75, 1.0, 0.88), chroma=0.008, glitch=0.4,
               wave=24, decay=0.07, seed=17),
        Impact(B(48), punch=0.02, decay=0.10, seed=18),
        Impact(B(52), punch=0.03, shake=6, decay=0.06, seed=19),
        Impact(LOGO, flash=0.30, flash_color=(0.92, 0.97, 1.0), chroma=0.006, wave=34, decay=0.08, seed=20),
        Impact(B(59), flash=0.12, decay=0.08, seed=21),
    ]

    # ============================================================== shots
    # --- SEQ 01: the warning (black, two one-frame flashes on the pre-roll pulses) ---
    black = Black()
    flash_npc = CharShot("npc", lambda t: Cam(HEAD[0], 0.36, 1.55, -1.5), rays=0.5, exposure=1.25, mb=False)
    flash_cw = CharShot("cw", lambda t: Cam(EYES[0], EYES[1], 2.3, 1.5), exposure=1.15, rim=0.6, mb=False)

    # --- SEQ 02: the wolf ---
    t4 = B(4)
    cw_intro = CharShot("cw", keys(
        (t4, Cam(EYES[0] + 0.004, EYES[1] + 0.005, 2.30, -0.4)),
        (DROP_A - 0.02, Cam(EYES[0], EYES[1] + 0.01, 2.62, -0.9), "in"),        # riser: push accelerates
        (DROP_A, Cam(EYES[0], EYES[1] + 0.01, 2.70, -1.6), "lin"),
        (DROP_A + 0.34, Cam(0.50, 0.50, 1.02, 0.0), "outexpo"),                  # velocity zoom to the portrait
        (B(12), Cam(0.505, 0.49, 1.075, 0.35), "smooth")),
        exposure=lambda t: smooth((t - t4) / 0.55) * (1.0 + 0.05 * smooth((t - B(6)) / (DROP_A - B(6)))),
        rim=lambda t: 0.55 * smooth((t - DROP_A) / 0.3), rim_dir=(-1.0, -0.5),
        sweeps=[Sweep(B(5) - 0.05, 0.62, 58, 0.06, 1.1), Sweep(B(7) - 0.10, 0.55, 122, 0.05, 1.3),
                Sweep(DROP_A + 0.45, 0.8, 60, 0.08, 0.7)],
        dust=0.8, fog=0.7, seed=21, ref_t=DROP_A + 0.34, focus=0.55, focus_at=(0.5, 0.42))

    # --- SEQ 03: the shadow ---
    npc_reveal = CharShot("npc", keys(
        (B(12) - 0.12, Cam(HEAD[0] - 0.06, 0.50, 1.18, 1.2)),
        (B(12) + 0.10, Cam(HEAD[0], 0.50, 1.06, 0.0), "outexpo"),
        (B(15), Cam(HEAD[0] + 0.005, 0.505, 1.13, -0.3), "smooth"),
        (B(15) + 0.36, Cam(LET[0], LET[1] + 0.005, 2.25, -0.6), "outexpo"),       # push into the lettering
        (B(16), Cam(LET[0], LET[1] + 0.006, 2.36, -0.7), "lin")),
        rays=lambda t: 0.55 - 0.3 * smooth((t - B(15)) / 0.3), rim=0.35, rim_dir=(0.3, -1.0),
        print_glow=lambda t: 0.85 * fx.impulse(t, B(12) + 0.06, attack=0.12, decay=0.9) + 0.25 + 0.5 * fx.impulse(t, B(15), 0.05, 0.25),
        sweeps=[Sweep(B(12) + 0.15, 0.55, 64, 0.06, 1.4, color=(0.85, 0.92, 1.0), target="print"),
                Sweep(B(15) + 0.05, 0.40, 116, 0.05, 1.2, color=(0.85, 0.92, 1.0), target="print")],
        fg_particles=0.7, dust=0.4, fog=0.5, seed=31, ref_t=B(12) + 0.1)

    # --- SEQ 04: the connection (one image per accent) ---
    cw_c1 = CharShot("cw", keys((B(16), Cam(EYES[0], EYES[1], 2.05, 0.8)), (B(17), Cam(EYES[0] + 0.01, EYES[1], 2.22, 0.2))),
                     rim=0.5, dust=0.5, seed=41, ref_t=B(16), focus=0.6, exposure=0.92)
    npc_c1 = CharShot("npc", keys((B(17), Cam(0.42, 0.25, 1.95, -1.0)), (B(18), Cam(0.425, 0.25, 2.08, -1.6))),
                      rays=0.7, rim=0.4, fg_particles=0.5, seed=42, ref_t=B(17))
    cw_c2 = CharShot("cw", keys((B(18), Cam(LENS_R[0] - 0.03, LENS_R[1], 2.75, -2.0)), (B(19), Cam(LENS_R[0] - 0.035, LENS_R[1] - 0.005, 2.95, -1.2))),
                     rim=0.4, sweeps=[Sweep(B(18) + 0.05, 0.4, 60, 0.07, 1.2)], seed=43, ref_t=B(18), focus=0.6, exposure=0.92)
    npc_c2 = CharShot("npc", keys((B(19), Cam(LET[0], LET[1], 1.85, 1.5)), (B(20), Cam(LET[0] - 0.01, LET[1], 2.0, 0.8))),
                      rays=0.3, rim=0.3, seed=44, ref_t=B(19))
    duo_c = DuoShot(
        CharShot("npc", keys((B(20) - 0.2, Cam(HEAD[0], 0.42, 1.02, 0)), (B(24), Cam(HEAD[0], 0.40, 1.10, 0))), rays=0.5, rim=0.3, fg_particles=0.4, seed=45, ref_t=B(20)),
        CharShot("cw", keys((B(20) - 0.2, Cam(0.50, 0.47, 1.0, 0)), (B(24), Cam(0.50, 0.46, 1.08, 0))), rim=0.5, dust=0.4, seed=46, ref_t=B(20)),
        layout="stack", split=0.56, feather=0.02, seam=lambda t: 0.9 * smooth((t - B(20)) / 0.2),
        dim=lambda t: 1 - 0.55 * smooth((t - B(23)) / 0.45))

    # --- SEQ 05: the promise (quiet: let it breathe) ---
    cw_promise = CharShot("cw", keys((B(24) - 0.3, Cam(0.47, 0.44, 1.55, -0.6)), (B(28) + 0.3, Cam(0.475, 0.445, 1.74, 0.4), "lin")),
                          exposure=0.74, rim=0.9, rim_dir=(-1.0, -0.25), dust=0.6, fog=1.0, seed=51, ref_t=B(24), focus=0.7, focus_at=(0.45, 0.40),
                          sweeps=[Sweep(B(25), 1.6, 70, 0.10, 0.45)])
    npc_promise = CharShot("npc", keys((B(28) - 0.3, Cam(HEAD[0] - 0.02, 0.48, 1.22, 0.8)), (B(32), Cam(HEAD[0], 0.47, 1.36, -0.2), "lin")),
                           rays=lambda t: 0.75 + 0.25 * smooth((t - B(30)) / 0.4), rim=0.5, rim_dir=(0.0, -1.0),
                           fg_particles=0.8, dust=0.6, fog=0.9, seed=52, ref_t=B(28))

    # --- SEQ 06: the final build (cuts tighten with the kicks) ---
    cw_b1 = CharShot("cw", keys((B(32), Cam(0.49, 0.47, 1.45, -3.0)), (B(33) - 0.13, Cam(0.49, 0.46, 1.60, -3.4)),
                                (B(33), Cam(EYES[0], EYES[1], 3.4, -5.0), "inexpo")),                   # depth crash into the lens
                     rim=0.9, rim_dir=(1.0, -0.4), exposure=0.95, dust=0.6, seed=61, ref_t=B(32), focus=0.55, p_bg=0.35)
    # NPC: the bright edge of the silhouette against the window, pulled back out of the crash
    npc_b1 = CharShot("npc", keys((B(33), Cam(0.70, 0.25, 2.9, 2.5)), (B(33) + 0.18, Cam(0.68, 0.26, 1.95, 1.0), "outexpo"),
                                  (B(34), Cam(0.675, 0.26, 2.05, 0.6))),
                      rays=0.3, rim=0.6, rim_dir=(1.0, -0.3), exposure=0.84, fg_particles=0.6, seed=62, ref_t=B(33) + 0.18, p_bg=0.35)
    cw_b2 = CharShot("cw", keys((B(34), Cam(GOG[0], GOG[1] - 0.02, 1.95, 2.5)), (B(35), Cam(GOG[0] + 0.01, GOG[1] - 0.02, 2.15, 2.0))),
                     rim=0.8, sweeps=[Sweep(B(34) + 0.08, 0.38, 120, 0.06, 1.3)], seed=63, ref_t=B(34), focus=0.55, exposure=0.92)
    npc_b2 = CharShot("npc", keys((B(35), Cam(LET[0], LET[1], 1.8, -2.0)), (B(36), Cam(LET[0], LET[1], 2.0, -2.4))),
                      rays=0.5, rim=0.4, seed=64, ref_t=B(35))
    # JUST TWO: first true dual composition, held while the gap opens
    duo_build = DuoShot(
        CharShot("npc", keys((B(36), Cam(HEAD[0], 0.45, 1.10, 0)), (B(39), Cam(HEAD[0], 0.44, 1.30, 0), "in")), rays=0.6, rim=0.5, fg_particles=0.5, seed=65, ref_t=B(36)),
        CharShot("cw", keys((B(36), Cam(0.50, 0.47, 1.10, 0)), (B(39), Cam(0.50, 0.47, 1.30, 0), "in")), rim=0.6, dust=0.5, seed=66, ref_t=B(36)),
        layout="diag", split=0.5, angle=-9, feather=0.004,
        seam=lambda t: 0.8 + 0.6 * smooth((t - B(38)) / 0.55),
        dim=lambda t: 1 - 0.55 * smooth((t - B(38)) / 0.56))

    # --- SEQ 07: the legendary drop ---
    def drop_npc_cam(t):
        k = fx.ease_out_expo((t - DROP_B) / 0.40)
        z = 1.45 - 0.45 * k + 0.05 * smooth((t - DROP_B - 0.4) / 4.0)
        return Cam(HEAD[0], 0.445, z, -2.0 * (1 - k))

    def drop_cw_cam(t):
        k = fx.ease_out_expo((t - DROP_B) / 0.40)
        z = 1.45 - 0.45 * k + 0.05 * smooth((t - DROP_B - 0.4) / 4.0)
        return Cam(0.50, 0.445, z, 2.0 * (1 - k))

    duo_drop = DuoShot(CharShot("npc", drop_npc_cam, rays=0.65, rim=0.5, fg_particles=0.5, dust=0.4, seed=71, ref_t=DROP_B + 0.4),
                       CharShot("cw", drop_cw_cam, rim=0.6, dust=0.5, seed=72, ref_t=DROP_B + 0.4),
                       layout="stack", split=0.5, feather=0.018,
                       seam=lambda t: 1.0 + 0.8 * math.exp(-(t - DROP_B) / 0.3) + 0.6 * math.exp(-max(0, t - B(44)) / 0.3) * (t > B(44)))

    # --- SEQ 08: the signature (calm, premium) ---
    sig = DuoShot(
        CharShot("npc", keys((B(48) - 0.25, Cam(HEAD[0] + 0.01, 0.45, 1.08, 0)), (B(53), Cam(HEAD[0], 0.445, 1.17, 0), "lin")),
                 rays=0.9, rim=0.45, fg_particles=0.35, dust=0.5, fog=0.9, seed=81, ref_t=B(48)),
        CharShot("cw", keys((B(48) - 0.25, Cam(0.50, 0.455, 1.06, 0)), (B(53), Cam(0.50, 0.45, 1.15, 0), "lin")),
                 rim=0.7, dust=0.5, fog=0.9, seed=82, ref_t=B(48),
                 sweeps=[Sweep(B(48) + 0.1, 1.4, 66, 0.09, 0.35, target="subject")]),
        layout="diag", split=0.5, angle=-7, feather=0.006, seam=0.9)

    # --- SEQ 09: the channel logo ---
    logo = LogoShot(t_hit=LOGO, size_px=880, t_start=B(53))

    tl.segs = [
        Seg(0.0, t4, black, "warning"),
        Seg(t4, B(12), cw_intro, "wolf"),
        Seg(B(12), B(16), npc_reveal, "shadow"),
        Seg(B(16), B(17), cw_c1, "conn-cw-eyes"),
        Seg(B(17), B(18), npc_c1, "conn-npc-head"),
        Seg(B(18), B(19), cw_c2, "conn-cw-goggles"),
        Seg(B(19), B(20), npc_c2, "conn-npc-letters"),
        Seg(B(20), B(24), duo_c, "conn-duo"),
        Seg(B(24), B(28), cw_promise, "promise-cw"),
        Seg(B(28), B(32), npc_promise, "promise-npc"),
        Seg(B(32), B(33), cw_b1, "build-cw"),
        Seg(B(33), B(34), npc_b1, "build-npc"),
        Seg(B(34), B(35), cw_b2, "build-cw2"),
        Seg(B(35), B(36), npc_b2, "build-npc2"),
        Seg(B(36), B(39), duo_build, "build-duo"),
        Seg(B(39), DROP_B, black, "pre-drop black"),
        Seg(DROP_B, B(48), duo_drop, "drop"),
        Seg(B(48), B(53), sig, "signature"),
        Seg(B(53), T_END + 1, logo, "logo"),
    ]
    tl.trans = [
        Trans(B(12) - 0.13, B(12) + 0.09, "whip", {"direction": -1}),            # High-velocity directional whip
        Trans(B(16) - 0.10, B(16) + 0.10, "zoom_collision"),                     # Zoom collision
        Trans(B(17) - 2 * F, B(17) + 2 * F, "dark_flash"),                       # Quick dark flash cut
        Trans(B(18) - 3 * F, B(18) + 3 * F, "glitch_cut", {"seed": 18}),         # SAME CODE: digital cut
        Trans(B(19) - 0.09, B(19) + 0.09, "chroma_compress"),                    # Chromatic compression
        Trans(B(20) - 0.20, B(20) + 0.04, "split_slide"),                        # Motion-matched split
        Trans(B(24) - 0.06, B(24) + 0.42, "shadow_wipe", {"angle": -24}),        # Fragmented shadow wipe
        Trans(B(28) - 0.30, B(28) + 0.30, "light_reveal"),                       # Light-triggered reveal
        Trans(B(34) - 3 * F, B(34) + 3 * F, "glitch_cut", {"seed": 34}),
        Trans(B(35) - 2 * F, B(35) + 2 * F, "dark_flash"),
        Trans(B(36) - 0.12, B(36) + 0.03, "split_slide", {"angle": 9}),
        Trans(B(48) - 0.10, B(48) + 0.12, "light_reveal", {"center": (540, 960), "amount": 0.4}),
        Trans(B(53), B(53) + 0.50, "shatter", {"center": (540 * ctx.S, 960 * ctx.S)}),  # Dark digital shatter
    ]
    for tr in tl.trans:
        if "center" in tr.params and tr.kind == "light_reveal":
            tr.params["center"] = (tr.params["center"][0] * ctx.S, tr.params["center"][1] * ctx.S)

    # ============================================================== typography
    def T(s, font, cap, tr=0.0, **kw):
        return Text(s, font, cap, tr, **kw)

    texts = tl.texts
    texts += [
        TextCue(T("THEY SEE TWO.", "anton", 128, 0.02), ENTR, B(3), 540, 900, "slam", 0.16, "fragment", 0.26,
                glow=0.2, tracking=lambda lt: 0.02 + 0.025 * smooth(lt / 1.5), seed=1),
        TextCue(T("CYBERWOLF", "anton", 168, 0.01, accent=EMERALD), DROP_A, B(12) - 0.05, 540, 1420, "slam", 0.15,
                "exit_left", 0.16, accent_glow=0.45, glow=0.12, tracking=lambda lt: 0.01 + 0.02 * smooth(lt / 2.2), seed=2,
                shine=(DROP_A + 0.25, 0.6)),
        TextCue(T("THE ONE WHO HOLDS THE LINE.", "barlow_sb", 48, 0.16), B(9), B(12) - 0.03, 540, 1560, "assemble", 0.42,
                "exit_left", 0.16, glow=0.08, seed=3),
        TextCue(T("THE ONE WHO MOVES IN SILENCE.", "barlow_sb", 48, 0.16), B(13), B(16) - 0.04, 540, 1560, "assemble", 0.42,
                "fragment", 0.14, glow=0.08, seed=5),
        TextCue(T("DIFFERENT MINDS.", "anton", 122, 0.02), B(16), B(18) - 0.03, 540, 1450, "slam", 0.13, "cut", 0.0, glow=0.14, seed=6),
        TextCue(T("SAME CODE.", "anton", 150, 0.03, accent=EMERALD), B(18), B(20) - 0.03, 540, 1450, "slam", 0.13, "cut", 0.0,
                glow=0.14, accent_glow=0.35, seed=7),
        TextCue(T("UNBREAKABLE", "anton", 112, 0.02), B(20), B(23) + 0.30, 540, 805, "slam", 0.14, "fragment", 0.22, glow=0.16, seed=8),
        TextCue(T("LOYALTY.", "anton", 112, 0.08, accent=EMERALD), B(20) + 0.08, B(23) + 0.30, 540, 932, "slam", 0.14, "fragment", 0.22,
                glow=0.16, accent_glow=0.35, seed=9),
        TextCue(T("WHEN ONE GOES SILENT...", "barlow_sb", 58, 0.14), B(24) + 0.18, B(28) - 0.32, 540, 1480, "reveal", 0.9, "blur", 0.35,
                glow=0.06, tracking=lambda lt: 0.14 + 0.05 * smooth(lt / 2.4), seed=10),
        TextCue(T("THE OTHER HOLDS THE LINE.", "barlow_sb", 58, 0.14), B(28) + 0.12, B(32) - 0.04, 540, 1480, "reveal", 0.8, "cut", 0.0,
                glow=0.08, tracking=lambda lt: 0.14 + 0.05 * smooth(lt / 2.2), seed=11),
        TextCue(T("NO BACKUP.", "anton", 150, 0.03), B(32), B(34) - 0.03, 540, 1450, "slam", 0.12, "cut", 0.0, glow=0.14, seed=12),
        TextCue(T("NO RETREAT.", "anton", 150, 0.03), B(34), B(36) - 0.03, 540, 1450, "slam", 0.12, "cut", 0.0, glow=0.14, seed=13),
        TextCue(T("JUST TWO.", "anton", 170, 0.04, accent=EMERALD), B(36), B(39) - 0.02, 540, 815, "slam", 0.14, "cut", 0.0,
                glow=0.18, accent_glow=0.3, tracking=lambda lt: 0.04 + 0.05 * smooth(lt / 1.6), seed=14),
        TextCue(T("TWO SHADOWS.", "anton", 132, 0.03), DROP_B, B(44) - 0.02, 540, 830, "slam", 0.14, "cut", 0.0,
                glow=0.2, tracking=lambda lt: 0.03 + 0.03 * smooth(lt / 2.2), seed=15),
        TextCue(T("ONE ARMY.", "anton", 250, 0.02, accent=EMERALD), B(44), B(48) - 0.10, 540, 815, "slam", 0.17, "blur", 0.22,
                glow=0.26, accent_glow=0.65, scale_fn=lambda lt: 1 + 0.025 * smooth(lt / 2.2), seed=16, max_w=1000,
                shine=(B(44) + 0.22, 0.55)),
        TextCue(T("NPC × CYBERWOLF", "anton", 110, 0.05), B(48) + 0.02, B(53) - 0.02, 540, 855, "reveal", 0.42, "fragment", 0.3,
                glow=0.16, accent_glow=0.2, tracking=lambda lt: 0.05 + 0.03 * smooth(lt / 2.8), seed=17),
        TextCue(T("BROTHERS. NOT JUST ADMINS.", "barlow_sb", 56, 0.12), B(49), B(53) - 0.02, 540, 985, "assemble", 0.5, "fragment", 0.3,
                glow=0.08, seed=18),
        TextCue(T("TWO MEN. ONE LEGACY.", "barlow_sb", 54, 0.24), B(60), T_END, 540, 1470, "fade", 0.7, "cut", 0.0,
                glow=0.10, tracking=lambda lt: 0.30 + 0.06 * smooth(lt / 2.4), seed=19),
    ]

    # ============================================================== overlays
    ov = tl.overlays

    def breath(ctx, img, t, p):  # dim cold light that breathes with the pre-roll pad
        H, W = img.shape[:2]
        ys = np.linspace(-1, 1, H, dtype=np.float32)[:, None, None]
        g = np.exp(-(ys / 0.35) ** 2) * (0.035 * ctx.env(t, "full") + 0.004)
        return img + g * NPC_SILVER

    def flash_frame(shot, t_hit):
        def fn(ctx, img, t, p):
            k = round((t - t_hit) * ctx.fps)
            amt = 1.0 if k < 1 else (0.16 if k < 2 else 0.05)
            return img + shot.render(ctx, t_hit) * amt
        return fn

    def split_light(ctx, img, t, p):  # the two identities as faint light behind THEY SEE TWO
        H, W = img.shape[:2]
        xs = np.linspace(0, 1, W, dtype=np.float32)[None, :, None]
        ys = np.linspace(-1, 1, H, dtype=np.float32)[:, None, None]
        env = smooth(p * 6) * (1 - smooth((p - 0.7) / 0.3))
        g = np.exp(-(ys / 0.20) ** 2) * env * 0.20
        return img + g * (np.exp(-((xs - 0.25) / 0.2) ** 2) * NPC_SILVER + np.exp(-((xs - 0.75) / 0.2) ** 2) * CW_EMERALD)

    def scrim(y0, strength):  # bottom darkening so titles always read (integrated, not a bar)
        def fn(ctx, img, t, p):
            H = img.shape[0]
            ys = np.arange(H, dtype=np.float32)[:, None, None] / H
            env = smooth(p * 8) * smooth((1 - p) * 8)
            return img * (1 - strength * env * fx.smoothstep_arr(y0, y0 + 0.2, ys))
        return fn

    def mid_band(y, half, strength):  # soft dark band behind centred titles on duo shots
        def fn(ctx, img, t, p):
            H = img.shape[0]
            ys = np.arange(H, dtype=np.float32)[:, None, None] / H
            env = smooth(p * 10) * smooth((1 - p) * 10)
            return img * (1 - strength * env * np.exp(-((ys - y) / half) ** 2))
        return fn

    def streaks(t0, t1, n=4, color=None, speed=1.0, seed=0):
        def fn(ctx, img, t, p):
            H, W = img.shape[:2]
            rng = np.random.default_rng(seed)
            for i in range(n):
                y = rng.uniform(0.2, 0.8) * H
                ph = rng.uniform(0, 1)
                q = ((t - t0) * speed * (0.8 + 0.5 * p) + ph) % 1.0
                x0 = -0.3 * W + q * 1.6 * W
                ln = (0.12 + 0.25 * p) * W
                img = fx.streak(img, (x0, y), (x0 + ln, y - 0.02 * ln), 2 * ctx.S, 0.35 * math.sin(q * math.pi),
                                color if color is not None else (NPC_SILVER if i % 2 else CW_EMERALD), glow=8 * ctx.S)
            return img
        return fn

    def gap_line(ctx, img, t, p):  # almost-black pause: a thin line of light gathers before the drop
        H, W = img.shape[:2]
        xs = np.abs(np.arange(W, dtype=np.float32) - W / 2)[None, :, None]
        ys = np.abs(np.arange(H, dtype=np.float32) - H / 2)[:, None, None]
        width = (40 + 260 * fx.ease_in_cubic(p)) * ctx.S
        g = np.exp(-(xs / width) ** 2) * (np.exp(-(ys / (1.8 * ctx.S)) ** 2) + 0.25 * np.exp(-(ys / (14 * ctx.S)) ** 2)) * (0.5 + 0.9 * p)
        return img * 0.04 + g * (NPC_SILVER * 0.5 + CW_EMERALD * 0.5)

    def drop_recover(ctx, img, t, p):  # radial blur recovery right after the impact
        return fx.zoom_blur(img, 0.16 * (1 - fx.ease_out_cubic(p)), n=8)

    def glint(t0, dur):  # brief silver sweep across the logo on the final hit
        def fn(ctx, img, t, p):
            H, W = img.shape[:2]
            band = fx.light_band((H, W), t, 64, 0.05, fx.ease_in_out_cubic(p))
            lg = ctx.A.logo
            s = 880 * ctx.S / lg.w
            lcx, lcy = ctx.A.anchors["logo"]["center"]
            M = np.array([[1 / s, 0, lg.w * lcx - W / 2 / s], [0, 1 / s, lg.h * lcy - H * 0.47 / s]], np.float64)
            a = lg.sample(M, (W, H), s, sharp=False)[..., 3]
            return img + (band * a)[..., None] * 0.30 * math.sin(p * math.pi) * COOL_WHITE
        return fn

    ov += [
        Overlay(0.0, ENTR, breath),
        Overlay(T_FLASH_NPC, T_FLASH_NPC + 3 * F, flash_frame(flash_npc, T_FLASH_NPC)),
        Overlay(T_FLASH_CW, T_FLASH_CW + 3 * F, flash_frame(flash_cw, T_FLASH_CW)),
        Overlay(ENTR, B(3) + 0.3, split_light),
        Overlay(DROP_A - 0.02, B(12) - 0.05, scrim(0.62, 0.6)),
        Overlay(B(12), B(16), scrim(0.60, 0.35)),
        Overlay(B(16), B(20), scrim(0.62, 0.55)),
        Overlay(B(20), B(24), mid_band(0.452, 0.06, 0.45)),
        Overlay(B(24), B(32), scrim(0.62, 0.5)),
        Overlay(B(32), B(36), scrim(0.62, 0.55)),
        Overlay(B(36), B(39), mid_band(0.43, 0.06, 0.45)),
        Overlay(B(36), B(39), streaks(B(36), B(39), n=5, speed=1.4, seed=3)),
        Overlay(B(39), DROP_B, gap_line),
        Overlay(DROP_B, DROP_B + 0.22, drop_recover),
        Overlay(DROP_B, B(48), mid_band(0.44, 0.075, 0.35)),
        Overlay(DROP_B + 0.5, B(48), streaks(DROP_B, B(48), n=3, speed=0.6, seed=7)),
        Overlay(B(48), B(53), mid_band(0.47, 0.07, 0.42)),
        Overlay(B(59) - 0.05, B(59) + 0.5, glint(B(59), 0.55)),
    ]

    # ============================================================== global exposure
    def exposure(t):
        e = 1.0
        if DROP_A <= t < B(24):
            e *= 1 + 0.035 * ctx.env(t)        # bass-responsive exposure pulse
        if DROP_B <= t < B(53):
            e *= 1 + 0.03 * ctx.env(t)
        return e
    tl.exposure = exposure
    tl.fade = lambda t: 1 - smooth((t - (T_END - 1.25)) / 1.15)   # fade to black on the musical ending
    return tl


def sound_cues(beat):
    """Supplementary sound, only where it serves a visual transition. beat(n) = video time of beat n.

    The track stays the star: every cue sits 18-30 dB under the music, nothing is placed on
    top of the drops or the logo hit (the music's own transients are the impacts), and the
    reverse swell ends exactly where the drop begins.
    (kind, anchor time, alignment, gain dB, params)  alignment: 'start' | 'peak' | 'end'
    """
    B = beat
    return [
        ("glitch", B(3) + 0.02, "start", -27, {"dur": 0.24, "density": 26, "seed": 3}),     # THEY SEE TWO fragments out
        ("whoosh", B(12) - 0.02, "peak", -21, {"dur": 0.42, "f0": 400, "f1": 5200, "p0": 0.8, "p1": -0.8}),   # whip, pan follows motion
        ("whoosh", B(16) - 0.01, "peak", -24, {"dur": 0.30, "f0": 900, "f1": 7000, "p0": 0.0, "p1": 0.0}),    # zoom collision air
        ("glitch", B(18) - 0.05, "start", -26, {"dur": 0.12, "density": 18, "seed": 18}),   # SAME CODE digital cut
        ("whoosh", B(20) - 0.08, "peak", -25, {"dur": 0.34, "f0": 300, "f1": 2600, "p0": 0.0, "p1": 0.0}),    # split slide
        ("whoosh", B(28), "peak", -28, {"dur": 0.70, "f0": 200, "f1": 1800, "p0": -0.3, "p1": 0.3}),          # light reveal air
        ("glitch", B(34) - 0.05, "start", -27, {"dur": 0.12, "density": 18, "seed": 34}),
        ("reverse_swell", B(40), "end", -22, {"dur": 0.55}),                                  # air pulled in, released by the drop
        ("shatter", B(53), "start", -26, {"dur": 1.0, "seed": 53, "count": 70}),               # signature shatters away
        ("shimmer", B(56), "end", -30, {"dur": 1.5}),                                          # particles converge on the logo
        ("shimmer_tail", B(56), "start", -32, {"dur": 2.2}),
    ]
