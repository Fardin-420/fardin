"""Short NPC_VOICE_V1 test: one line per emotion, scored against the reference."""
from __future__ import annotations

import json

import soundfile as sf

from npc_voice import PROFILE_DIR, Voice, env_device, trim

LINE = "This is NPC. Every single frame, written in code."


def main() -> None:
    v = Voice(env_device())
    out_dir = PROFILE_DIR / "voice_tests"
    report = {}
    for emotion in v.cfg["synthesis"]["emotions"]:
        wav, sim = v.say(LINE, emotion)
        wav = trim(wav, v.sr)
        sf.write(out_dir / f"test_{emotion.lower()}.wav", wav, v.sr)
        report[emotion] = {"speaker_similarity": round(sim, 3), "seconds": round(len(wav) / v.sr, 2)}
        print(emotion, report[emotion])
    floor = v.cfg["synthesis"]["min_speaker_similarity"]
    report["pass"] = all(r["speaker_similarity"] >= floor for r in report.values() if isinstance(r, dict))
    (out_dir / "voice_test_report.json").write_text(json.dumps(report, indent=2))
    print("PASS" if report["pass"] else f"FAIL: a take fell below speaker similarity {floor}")


if __name__ == "__main__":
    main()
