# QA REPORT — THE 20-MINUTE HEIST

Automated by `scripts/qa.py` on the final files, plus the manual review notes below.

## Render specs (ffprobe)
| Check | master_1080p.mp4 | upload_1080p.mp4 | Target |
|---|---|---|---|
| Resolution | 1920×1080 | 1920×1080 | 1920×1080 |
| Frame rate | 30/1 | 30/1 | 30 |
| Codec / profile | h264 High | h264 High | H.264 High |
| Pixel format | yuv420p | yuv420p | yuv420p |
| Frames | 25014 (timeline 25014) | 25014 | equal |
| Duration video / audio | 833.8 s / 833.8 s | 833.8 s / 833.8 s | match |
| Audio | aac 48000 Hz 2 ch 324 kbps | aac 324 kbps | AAC 48 kHz 320 (both) |
| Video bitrate (total) | 4.06 Mbps | 3.24 Mbps | CRF 16 / CRF 17 |
| Size | 423.3 MB | **337.8 MB** | upload ≤ ~800 MB ✅ |

## Loudness (ebur128 on the encoded AAC)
- master: **-14.0 LUFS** integrated, true peak **-1.1 dBTP**, LRA 4.5 LU — target −14 ±0.5 LUFS ✅, ≤ −1 dBTP ✅
- upload: -14.0 LUFS, -1.1 dBTP
- Music ducks −12 dB under the voice, driven by VO activity; SFX −4 dB under the voice. The voice was normalized 5 LU above the music bed before the master.

## Picture integrity
- Black segments ≥ 0.5 s: 2 → 497.1–497.6s, 776.8–778.1s (intended: dipBlack into Chapter 6 and into the outro)
- Freezes ≥ 2.5 s (freezedetect): 1 → 53.1–55.7s
- Visible picture changes (mean abs. difference > 1.5/255 between 0.5 s samples, caption band excluded): 915; median gap 0.5 s
- Holds > 6 s with only small motion: 1 (2% of runtime) → 814.0s (+20.0s). Every other stretch changes picture within 6 s (pacing pass v2: camera punch-ins, detail cuts, pushes and four detail inserts in the Binance 14 / EIP-7702 explainer). Any hold starting at or after 13:34 is the YouTube end screen, which is kept static on purpose: its element slots must not move.

## Captions
- 240 pages, overlaps 0 ✅, max 2 lines × 34 chars ✅
- 15 hide windows where the same words are already big on screen (quote cards, counters, headlines).
- Timing source: Kokoro per-sentence files, words weighted by phoneme count and snapped to detected pauses. No ASR model was reachable (Whisper/wav2vec hosts blocked). Sentence starts and ends are sample-exact. Word positions inside a sentence are estimates, typically within ~80–150 ms, so the ±80 ms target is met at sentence edges and approximate mid-sentence.
- Captions sit above the bottom 140 px; all UI and graphics are inside the 96/54 px title-safe margins.

## Guardrails
- No logos (names set in our own type; neutral token circles). No news footage or third-party clips. No images of real people; CZ, Teng, Kim Yo Jong and the FBI appear only as name or quote cards.
- The engineers are never identified: Binance's report uses letters, and the film says only "an engineer" / "colleagues".
- Security detail stays at story level: no code, commands, repository names or payloads. The phishing page, recruiter email, job message and video-call tiles are fictional and labeled.
- Attribution is always credited (TRM, Chainalysis, Elliptic, FBI), and the North Korean denial is included. "NOT FINANCIAL ADVICE" badge in the outro.
- The ~3 s hooded figure (S07) is a stylized vector silhouette, labeled "ILLUSTRATION · DRAMATIZATION". No AI imagery is used anywhere.

## Asset sources
| Shot | Spec | Used |
|---|---|---|
| AI-01 corridor | AI shot | Designed MG plate (no AI file supplied; stock APIs unreachable) |
| AI-02 laptop | AI shot | Designed MG plate (no AI file supplied; stock APIs unreachable) |
| AI-03 aerial city | AI shot | Designed MG plate (no AI file supplied; stock APIs unreachable) |
| AI-04 vault | AI shot | Designed MG plate (no AI file supplied; stock APIs unreachable) |
| AI-05 VHS coins | AI shot | Designed MG plate (no AI file supplied; stock APIs unreachable) |
| AI-06 keyboard | AI shot | Designed MG plate (no AI file supplied; stock APIs unreachable) |
| AI-07 vortex | AI shot | Designed MG plate (no AI file supplied; stock APIs unreachable) |
| AI-08 monitors | AI shot | Designed MG plate (no AI file supplied; stock APIs unreachable) |
| AI-09 ice | AI shot | Designed MG plate (no AI file supplied; stock APIs unreachable) |
| AI-10 dossier lamp | AI shot | Designed MG plate (no AI file supplied; stock APIs unreachable) |
| AI-11 silhouette | AI shot | Designed MG plate (no AI file supplied; stock APIs unreachable) |
| AI-12 dawn | AI shot | Designed MG plate (no AI file supplied; stock APIs unreachable) |
| AI-13 laptop closing | AI shot | Designed MG plate (no AI file supplied; stock APIs unreachable) |
| AI-14 | thumbnail still | Code-made laptop plate inside thumbnail A |
| Stock B-roll | Pexels/Pixabay | none (api.pexels.com / pixabay.com refused by the session proxy; no API keys) |
| BTC price chart | CoinGecko hourly | replaced by a sourced market board (Reuters lows), so no unsourced curve is plotted; all price APIs refused by the proxy |
| Music | licensed tracks in assets/music | all 7 acts generated procedurally (scripts/sound.py) |
| SFX | — | all procedural (studio SOUND_ENGINE + scripts/sound.py) |

## On-screen figures ↔ fact ledger
| Scene | On screen | Ledger |
|---|---|---|
| S01 | $6,300,000,000 counter; ESTIMATES: BINANCE ~$6.3B · TRM ~$6.36B | F1, F2 |
| S02 | 335,000,000 users; $162.8B custody | F33 |
| S03 | MAY 7, 2019 17:15 UTC; 7,000 BTC; ≈$40M; ~2% of BTC holdings; tx e8b40609…554ab05ea | H1 |
| S03 | quote “had the patience to wait” — Binance, May 2019 | H2 |
| S03 | quote “the most immutable ledger on the planet” — CZ, May 8, 2019 | H3 |
| S03 | SAFU since 2018, 10% of fees; withdrawals back May 15, 2019 | H4, H5 |
| S03 | Oct 2022 BNB Chain bridge, 2,000,000 BNB, chain halted | H6 |
| S04 | laptop → service container → unauthorized withdrawals; Oct 30 preliminary findings | F3 |
| S04 | quote “not a single 'one-click' action” — Teng, Oct 30 | F4 |
| S04 | T–36H, Oct 28, Tornado Cash → operator wallet | F7 |
| S04 | PRIVATE KEY LEAK: NO EVIDENCE FOUND — BINANCE | F5 |
| S05 | XRP first ~$296M · ~233.5M XRP · 20:05–20:09 UTC | F13 |
| S05 | 20:20 UTC; Binance 14; 50 EIP-7702 authorizations; one applied | F9 |
| S05 | EIP-7702 live since May 2025 | F35 |
| S05 | 167,464 ETH · ~1.62B USDT · ~60 tokens · under 4 minutes | F10 |
| S05 | Ethereum ~$3.79B · Bitcoin 18,270 BTC ~$1.47B | F12 |
| S05 | second wave ~23:05 UTC Avalanche + Polygon | F14 |
| S06 | 971.1M USDT Tether 21:01 · 823M USDC Circle 21:04 | F14 |
| S06 | quote “a potential security issue” — Binance on X, Oct 29 (no minute) | F14 (softened) |
| S06 | 1.5B+ USDT frozen per Tether CEO | F14 |
| S06 | 40.5M RLUSD (TRM) · 27.8M USD1 | F15b, F14 |
| S06 | WITHDRAWALS SUSPENDED · Oct 29–30 · reported times vary | F14 (softened) |
| S06 | ~$30M · 8,426 ETH + 74.6M ARB · 00:08–00:18 UTC Oct 30 | F15 |
| S06 | frozen: Binance ~$2.85B · Elliptic $2.84B · TRM ~$2.7B | F16 |
| S06 | ~325M USDT at 10%+ discount · ~19,760 ETH borrowed on Aave | F17 |
| S06 | 420,000+ ETH · 18,270 BTC · ~$2.4B beyond any freeze · peel chain | F18 |
| S07 | TraderTraitor · Jade Sleet · Lazarus subunit (per researchers) · TRM/Chainalysis/Elliptic/FBI | F19, F20 |
| S07 | Bitget (Sep 2026) + Binance funds commingled | F19, C3 |
| S07 | FBI quote “North Korea was responsible for the theft of more than $6 billion” · Nov 1 | F20 |
| S07 | “absurd rhetoric” — Kim Yo Jong via KCNA · Nov 3 | F21 |
| S07 | DMM ~$308M (May 2024) · Bybit ~$1.5B (Feb 2025, FBI: TraderTraitor, Safe developer machine) · Bitget $352M+ | C1, C2, C3 |
| S07 | Binance ~$6.3B bar | F2 |
| S08 | BTC $76,368 6-week low · ETH $2,178 2-month low · BNB ~−5% · COIN −4.8% · MSTR ~−6% | F27 |
| S08 | $6.34B set aside · SAFU ~$1B (reported) | F24 |
| S08 | Teng: “Our users will not bear the financial impact of this incident.” | F25 |
| S08 | CZ founder, stepped down as CEO 2023 | F26 |
| S08 | Nov 1 from 06:00 UTC, BTC first ~06:20, 15 networks | F28 |
| S08 | $4.65B out · $1.01B in · −$3.64B · 2.1% of ~$171B | F29 |
| S08 | “98% choose to stay.” — CZ, Nov 1 | F30 |
| S08 | 90% → 95% replenished (Nov 1) | F31 |
| S09 | Sept 2026 recruiter → HR + “CEO” of fictitious company → assignment; AI tool → colleagues → deploy token → wallet system | F6 |
| S09 | 2019 $40M vs 2026 ~$6.3B (~157×) | H1, F2 |

No mismatches found: every figure above traces to `research/fact-ledger.md` (Phase 1 table).

## Manual review (v2, one frame every 3 s, all 13:53)
- **Pacing pass v2.** The 37 v1 holds over 6 s (51% of runtime) were broken into 3–4.5 s camera beats: eased punch-ins, hard-cut detail crops and wide lateral pushes, framed from the rendered v1 so nothing is pushed under the captions. The Binance 14 / EIP-7702 explainer (~5:06–5:38) also gets four detail inserts, each locked to its line of VO: the count to 50 authorizations (TRM Labs · Blockaid), an Ethereum | EIP-7702 split screen (live since May 2025), a wallet → code delegation diagram and a generic nonce counter. The last two are labeled as illustrations. No new facts were added. VO, audio mix and timing are unchanged (same 25,014 frames, same mix_master.wav). Only the 36 affected windows (12,231 frames) were re-rendered and spliced in frame-exactly.
- Remaining hold over 6 s: **1**, the end screen (13:34–13:54). It is left static on purpose, because YouTube end-screen elements are placed over fixed slots.
- A sample of camera beats across all holds was checked: no collisions with captions or HUD. Some detail crops cut text at the frame edge on purpose (e.g. the hot/cold wallet panel and the closing checklist).
- Freeze at 0:53–0:56 is intended: the held "?" on "…the one question nobody can answer yet", before the title card.
- Black at 8:17 and 12:57 is intended: the dips into Chapter 6 and the outro. (v1 also flagged 12:38. That frame is a very dark split card, not a dip, and the v2 punch-in on "$40M" lifts it above the black-detect threshold.)
- The eight caption-collision fixes from v1 are kept (changelog, Phase 7).
- Not yet watched end to end with sound by a person. Before upload, play the upload file once at 1×, mainly to judge the generated score and SFX levels.

## Deliverables
| File | Where | Notes |
|---|---|---|
| out/upload_1080p_v2.mp4 (= out/upload_1080p.mp4) | container only (git-ignored, 337.8 MB) | **the file to upload to YouTube** |
| out/master_1080p_v2.mp4 (= out/master_1080p.mp4) | container only (git-ignored, 423.3 MB) | archive master |
| out/v1/{upload,master}_1080p.mp4 | container only | v1, before the pacing pass |
| out/preview_coldopen.mp4 | committed (19.1 MB) | first 60 s of v2, with audio |
| out/captions_en.srt, out/thumbnail_{A,B,C}.png, out/youtube_metadata.md, out/voice_tests/*.wav | committed | captions and chapters unchanged (timing unchanged) |

GitHub Release upload (v1-binance-heist) was refused for this session type, and Git LFS is blocked by the network policy (lfs.github.com), so the MP4s were not saved outside the container.
