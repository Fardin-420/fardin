# Changelog

Every phase appends a 3-line status. Fact changes after Nov 3, 2026 are listed under Phase 1.

## Phase 0 — Setup · 2026-11-03
- Built inside NPC_STUDIO (PROJECTS/BINANCE_HEIST + shared RENDER_ENGINE): Node 22, Python 3.11 venv, ffmpeg 6.1; all @remotion/* pinned to 4.0.537 (+ zod 4.5.4); 1920×1080 still render verified.
- Narration locked to NPC_VOICE_V1 only (no ElevenLabs/Kokoro). BLOCKER for Phase 2: reference audio absent in this container and profile reports ready_for_cloning=false (1.9 s of speech, needs ≥ 8 s).
- Skipped: Remotion Agent Skills install (blocked by session permissions), AI-influencer and TikTok/auto-publish features (out of scope). No .env → stock/data fallbacks apply.

## Phase 1 — Fact re-verification · 2026-11-03
- 47 ledger items checked: 31 verified, 9 updated, 4 softened, 1 cut (F8 test-wallet rehearsal), 4 new logged. Direct page fetches blocked by network policy → search-index verification; single-source minutes (21:24, 21:25, 00:13 UTC) kept off screen.
- Major: Binance's Nov 3 initial incident report (fake job interview → internal AI tool → deploy token) becomes the Scene 09 reveal; FBI exact wording (Nov 1) and KCNA/Kim Yo Jong denial (Nov 3) confirmed; frozen total now Binance ~$2.85B; XRP Ledger first outflow (~$296M) confirmed.
- Script locked pending Checkpoint A: 1,853 VO words (~12.4 min VO, ~13.5 min total vs 12.7 target).

### Fact changes after Nov 3 baseline
| ID | Was | Now |
|---|---|---|
| F6 | Laptop compromise not disclosed | Nov 3 report: Sept fake recruiter + fake "CEO" interview → malicious assignment repo; AI tool used to reach colleagues; deploy token found Oct 20 (June Homebrew incident detected & remediated) |
| F8 | Rehearsed on three test wallets (VERIFY) | CUT — secondary blogs only |
| F9 | 20:20:59 UTC | "20:20 UTC" on screen |
| F13 | XRP first ~$296M (VERIFY) | Confirmed: ~233.5M XRP, 20:05–20:09 UTC |
| F14 | Exact minutes for Binance post, Tether CEO, suspension | Wording kept, minutes dropped ("soon after", "later that night") |
| F15 | Arbitrum listed before suspension | 00:08–00:18 UTC Oct 30 — "in the same minutes" |
| F15b | Ripple froze RLUSD | TRM: 40.5M RLUSD |
| F16 | Binance ~$3B frozen | Binance ~$2.85B frozen or intercepted |
| F20 | FBI wording to verify | "North Korea was responsible for the theft of more than $6 billion…" (Nov 1) |
| F21 | NK denies (VERIFY) | Kim Yo Jong via KCNA, Nov 3: "absurd rhetoric" |
| F22 | "Binance hasn't named the attackers" | Dropped (conflicting Nov 3 summaries) |
| F24 | SAFU ~$1B | "reportedly" ~$1B |
| F25 | Teng "covering every loss" | Teng on X: "Our users will not bear the financial impact of this incident." |
| F27 | BNB −5.3% | ~−5% |
| F30 | "98% choose to stay!" | "98% choose to stay." |
| C3 | Bitget ~$350M | $352M+ (Bitget confirmed $351.6M; later reports ~$388M) |
| H3 | CZ quote "on X" | Venue reported as AMA/statement → "CZ · May 8, 2019" |

## Checkpoint A — approved · 2026-11-03
- Owner approved the locked script, including the Scene 09 reveal, and switched to FULL AUTO (no further checkpoints).
- Script tightened ~150 words (Scenes 03, 06 plus small trims) with no facts removed → 1,771 VO words.
- Narrator changed by the owner to the "Space Secrets" brand voice: Kokoro-82M (kokoro-onnx) `am_puck`, per-sentence speeds 0.87–0.95.

## Phase 1b — Primary-source re-read · 2026-11-03
- The newly allowed domains (fbi.gov, trmlabs.com, cnbc.com, protos.com, stingrai.io, api.pexels.com, pixabay.com, api.coingecko.com) were still refused by the session proxy (HTTP 403 on CONNECT; allow-list changes typically apply to new sessions). Verified via web search instead, as instructed.
- 21:24 / 21:25 / 00:13 UTC still unconfirmed. Suspension times conflict across compilations (≈22:30 UTC Oct 29 per SOCRadar, 00:13 UTC Oct 30 per Stingrai, 02:23 UTC per AirdropAlert), so the softened wording stays and the screen reads "OCT 29–30 · REPORTED TIMES VARY".
- New nuance: Stingrai notes Binance later clarified that deposits were unaffected → VO and screen now say "suspended withdrawals" (not "deposits and withdrawals"). Arbitrum's move (00:08–00:18 UTC Oct 30) is now worded "just after midnight UTC".

## Phase 2 — Voiceover + timing · 2026-11-03
- 144 sentence files, Kokoro `am_puck`, 80 Hz HPF + light de-ess + soft compression, no reverb, no time-stretch or pitch-shift. Gaps: 270–400 ms between sentences, 1.0 s at [[SILENCE]], 500 ms at "…".
- Word timings: phoneme-weighted per sentence, snapped to detected pauses (Whisper/wav2vec weights unreachable). Voice tests for am_puck / am_michael / am_fenrir are in out/voice_tests/.
- Runtime: 12.2 min speech, 13.15 min with gaps, 13:53 total with chapter cards, title and the 20 s end screen. The requested 0.86–0.96 speeds put am_puck at ~146 wpm, so the film runs longer than the ~12 min target rather than speeding the voice up.

## Phase 3 — Assets · 2026-11-03
- No AI shots supplied; Pexels/Pixabay and every BTC price API refused by the proxy → all 13 AI-shot slots use designed MG plates; the price beat uses a Reuters-sourced market board (no unsourced curve). Manifest: script/scenes.json.

## Phase 4–6 — Edit, sound, captions · 2026-11-03
- Remotion edit in RENDER_ENGINE/src/heist (10 scenes, ~40 MG components, cue-locked shots, punch/impact camera, dipBlack/filmBurn/iceWipe/dataWipe presentations, glitch/zoom/push shot transitions, 2019 grade). Fonts self-hosted.
- Sound: 7 generated score acts (no licensed tracks supplied), cue-locked procedural SFX, music −12 dB under VO; master −14.0 LUFS / −1.5 dBTP.
- Captions: 240 pages, ≤2×34 chars, gold active word, key-term pops, 15 hide windows against doubled text; out/captions_en.srt.
