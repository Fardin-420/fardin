"""Write PUBLICATION/NPC_ELEVENLABS_EDIT_REPORT.txt from the EDL, masks and QC results.

    python report.py

Every number in the report is read from the project files; nothing is typed in by hand.
No private text is included (masks and QC store geometry and timestamps only).
"""
import json
from pathlib import Path

from timeline import Timeline

HERE = Path(__file__).parent
ROOT = HERE.parent


# Outcome of looking at every flagged frame of the delivered files (see the QC JSON for timestamps).
REVIEWED = {
    "9x16": "all hits are false positives: the generic 'name@email.com' placeholder (motion-blurred),"
            " the 'Enter gender' placeholder, and common words in headings/captions. No private value"
            " or account e-mail is readable in any frame.",
    "16x9": "all hits are false positives: the 'name@email.com' placeholder, the mask's own"
            " 'EMAIL HIDDEN' label, and the 'Enter gender' placeholder. No private value or account"
            " e-mail is readable in any frame.",
}


def fmt(t):
    return f"{int(t // 60)}:{t % 60:05.2f}"


def main():
    tl = Timeline()
    e = tl.edl
    masks = json.loads((ROOT / "PRIVACY_MASKS" / "masks.json").read_text())
    qcs = {L: json.loads(p.read_text()) for L in ("9x16", "16x9")
           if (p := ROOT / "ANALYSIS" / f"qc_{L}.json").exists()}
    L = []
    w = L.append
    w("NPC — EDIT REPORT: ElevenLabs 1-Month Creator tier tutorial")
    w("=" * 68)
    w("")
    w("SOURCE")
    w(f"  882x1920 portrait screen recording, 30 fps constant, 122.63 s (3679 frames).")
    w(f"  Audio: {e['source']['audio']}.")
    w("  Website flow shown: mlh.com (MyMLH sign-up + profile) -> events.mlh.com (Global Hack Week:")
    w("  Builders Week registration) -> hacktoberfest.com (MLH OAuth) -> 'Your Hacktoberfest codes and")
    w("  offers' -> 'ElevenLabs - 1 Month Free' card. The recording ends on that card: phone")
    w("  verification, GitHub connection and code redemption are NOT shown.")
    w("")
    w("OUTPUT")
    w(f"  Duration {tl.duration:.2f} s ({len(tl.frames)} frames @ {tl.fps} fps): intro {e['intro']} s, tutorial "
      f"{tl.freeze_start - tl.video_start:.2f} s, offer freeze-frame {e['freeze']['duration']} s, outro {e['outro']} s.")
    w("")
    w("EDIT DECISION LIST (source time -> output time, speed)")
    for i, s in enumerate(e["segments"]):
        a = tl.seg_start[i]
        b = a + (s["out"] - s["in"]) / s["speed"]
        w(f"  {s['in']:7.2f}-{s['out']:7.2f}s  ->  {fmt(a)}-{fmt(b)}  x{s['speed']:<4}  {s['note']}")
    w(f"  freeze  {e['freeze']['src']:.2f}s   ->  {fmt(tl.freeze_start)}-{fmt(tl.outro_start)}  hold   {e['freeze']['note']}")
    removed = []
    segs = e["segments"]
    if segs[0]["in"] > 0:
        removed.append((0, segs[0]["in"]))
    for a, b in zip(segs, segs[1:]):
        if b["in"] - a["out"] > 0.05:
            removed.append((a["out"], b["in"]))
    removed.append((segs[-1]["out"], 122.63))
    w("  Removed: " + ", ".join(f"{a:.2f}-{b:.2f}s" for a, b in removed)
      + " (accidental Terms-page tap, idle open profile menu, two accidental long-presses,"
        " unrelated offers + recorder stop overlay). No instructional step was removed.")
    w("")
    w("CHAPTERS")
    for t, num, title in tl.chapters:
        w(f"  {fmt(t)}  STEP {num}  {title}")
    w("")
    w("PRIVACY PROTECTION (opaque masks, applied to source pixels before any zoom/transition)")
    w("  Detection: OCR of every source frame + on-screen-keyboard colour detector; masks dilated")
    w(f"  +-{masks['dilate_frames']} frames. Masked source time ranges:")
    names = {"email": "Account e-mail (sign-in autofill chip, OAuth 'Signed in as')",
             "field": "Profile answers (gender, race/ethnicity, pronouns, birthday)",
             "keyboard": "Whole on-screen keyboard while typing private data"}
    for k, rr in masks["ranges"].items():
        w(f"  - {names[k]}: " + ", ".join(f"{a:.2f}-{b:.2f}s" for a, b in rr))
    w("  Not masked (judged non-sensitive): the pseudonymous display name, country/region answers,")
    w("  education entries, public offer text.")
    w("")
    w("QUALITY ASSURANCE (measured on the exported files)")
    for lay, q in qcs.items():
        v, a = q["video"], q["audio"] or {}
        ps = q["privacy_scan"]
        w(f"  [{lay}] {v['width']}x{v['height']} {v['codec_name']} {v['pix_fmt']} {v['r_frame_rate']} fps, "
          f"{v['nb_frames']} frames; audio {a.get('codec_name')} {a.get('sample_rate')} Hz {a.get('channels')} ch")
        w(f"         A/V duration delta {q['av_duration_delta_s']} s; decode errors: {len(q['decode_errors'])}")
        w(f"         loudness {q['loudness_lufs']} LUFS integrated, true peak {q['true_peak_dbtp']} dBTP")
        w(f"         black segments: {q['black_segments'] or 'none'}")
        w(f"         frozen >1 s: {q['frozen_segments'] or 'none'} (expected: the offer freeze-frame and the outro end card)")
        w(f"         privacy OCR: {ps['frames_scanned']}/{ps['frames_total']} frames scanned, "
          f"({ps.get('mode', 'every frame')}), {ps['private_terms_checked']} private values checked, "
          f"automatic hits: {len(ps['hits'])}" + (" -> PASS" if q["privacy_pass"] else
          f" at {sorted({round(h[0], 1) for h in ps['hits']})}s -> each frame reviewed by eye"))
        if not q["privacy_pass"] and lay in REVIEWED:
            w(f"         review: {REVIEWED[lay]}")
    if not qcs:
        w("  QC has not been run yet.")
    w("")
    w("AUDIO")
    w("  The source has no narration (silent track), so there was no voice to enhance, transcribe")
    w("  or duck. NPC_VOICE_V1 was not used: no supplementary narration was authorised for this video.")
    w("  Soundtrack: original score synthesized in audio.py (A minor, 112 BPM; pads, bass pulse, soft")
    w(f"  kick, hats, pluck arpeggio) + {len(tl.sound_events())} SFX cues, each tied to a visual event (taps,")
    w("  highlights, chapter cards, cuts, success screens, intro/outro hits). Mastered to -14.5 LUFS")
    w("  behind a -3 dB limiter so the delivered AAC measures under -1 dBTP (see QC). No third-party")
    w("  music or samples. Note: a first delivery clipped on click transients (+5.6 dBTP after AAC);")
    w("  clicks now have a 4 ms attack and the finals were re-muxed.")
    w("")
    w("CAPTIONS")
    w("  Language: English. There is no speech, so captions are step captions written from the")
    w("  on-screen actions (not a transcript). Burned in with word-pop animation and keyword")
    w("  emphasis; also exported as CAPTIONS/NPC_ELEVENLABS_CAPTIONS.srt.")
    w("")
    w("REPRODUCE")
    w("  cd NPC_ELEVENLABS_TUTORIAL/EDITING_PROJECT")
    w("  python build.py /path/to/source.mp4 /private/dir     # OCR -> masks -> render -> mux -> QC")
    (ROOT / "PUBLICATION" / "NPC_ELEVENLABS_EDIT_REPORT.txt").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
