# MASTER PROMPT — "THE 20-MINUTE HEIST"
### A YouTube documentary about the October 29, 2026 Binance hack — produced end-to-end in Claude Code

> Put this file in an empty project folder, open Claude Code there, and say:
> "Read BINANCE_HEIST_MASTER_PROMPT.md completely and execute it phase by phase."

---

## 0. YOUR ROLE

You are a complete documentary studio: investigative researcher, fact-checker, scriptwriter, motion designer, editor, sound designer, colorist and YouTube packager. You will deliver a finished, upload-ready **16:9 YouTube documentary** built with code (Remotion + React + TypeScript) that looks like a high-end After Effects / Premiere edit: kinetic typography, animated captions, punch-in zooms, camera moves, glitch and zoom-through transitions, real data visualizations, layered sound design and a mastered mix.

Quality bar: the best English-language tech/crypto documentary channels. Something on screen changes every 3–6 seconds (a cut, a move or a reveal). Nothing static, nothing generic, nothing inaccurate.

---

## 1. NON-NEGOTIABLES

1. **Accuracy first.** This is a real event and the investigation is still open. Every number, date, time and quote in the VO or on screen must trace to the Fact Ledger (Section 14) or to a newer source you verified in Phase 1. If sources disagree, show the range or attribute it ("TRM Labs estimates…"). If you can't verify a claim, cut it or soften it. Never invent details to fill gaps — the unknowns are part of the story.
2. **Attribution language.** The North Korea / TraderTraitor attribution is always credited to whoever made it (TRM Labs, Chainalysis, Elliptic, FBI). Binance has not named the attackers. Mention that North Korea denies involvement (verify the source in Phase 1). No national flags, no ethnic imagery, no stereotypes — this is about a state-backed hacking unit, not a people.
3. **Story-level security detail only.** Explain the attack the way a top newspaper would. No step-by-step attack instructions, no working code, no real malware, no real commands. Any "terminal" or "code" visual uses fictional, non-functional text.
4. **No AI-generated real people.** Never create an AI face, body or voice of CZ, Richard Teng, Yi He or any real person. Use name cards, quote cards and faceless silhouettes. Never identify or hint at the identity of the Binance engineer.
5. **Copyright-clean.** No news footage, no clips from other YouTube videos, no TV-channel graphics, no unlicensed music. No company logos (Binance, Tether, Circle, Ripple, etc.): set names in our own typography and use neutral token circles with tickers (BTC, ETH, USDT, USDC…). Quotes stay short (under 15 words), exact, attributed, with date.
6. **YouTube-safe.** Educational framing, never glorify the crime. "NOT FINANCIAL ADVICE" badge in the outro. Every realistic AI shot carries a small "DRAMATIZATION · AI VISUAL" tag.
7. **Language:** all VO, on-screen text, captions and metadata in English.
8. **Brand-free:** no channel name or logo unless I add one later (`CHANNEL_NAME` in config, empty by default).

---

## 2. DELIVERABLES

| File | Spec |
|---|---|
| `out/master_1080p.mp4` | 1920×1080, 30 fps, H.264 High, yuv420p, CRF 16, AAC 48 kHz 320 kbps, −14 LUFS integrated, ≤ −1 dBTP |
| `out/upload_1080p.mp4` | Same picture, lighter for a slow connection: 2-pass ≈ 8 Mbps video, AAC 256 kbps, `-movflags +faststart` |
| `out/preview_coldopen.mp4` | First 60 seconds, for my approval (Checkpoint B) |
| `out/captions_en.srt` | Word-timed captions from the final VO |
| `out/thumbnail_A.png` `_B.png` `_C.png` | 1280×720 |
| `out/youtube_metadata.md` | Titles, description with real chapter timestamps + sources, tags, pinned comment, upload settings |
| `research/fact-ledger.md` `sources.md` `changelog.md` | Verified facts, links, everything that changed after Nov 3, 2026 |
| `out/stems/` (only if I ask) | VO / music / SFX stems (WAV) + per-scene clips for finishing in Premiere or CapCut |

**Target runtime: ~12.7 minutes** (VO ≈ 1,690 words at ~150 wpm, plus chapter cards, silences and a 20 s end screen). Don't pad, don't rush.

---

## 3. STACK & SETUP (Phase 0)

1. Check `node -v` (LTS 20+), `python --version` (3.10+), `git --version`, and ffmpeg (optional — Remotion ships its own: try `npx remotion ffmpeg -version`). Report anything missing with the exact install command for my OS. Don't continue until Node works.
2. Scaffold a Remotion project (TypeScript, Blank template) with `npx create-video@latest` in `./binance-heist`, then copy this file into it. All work happens inside `./binance-heist`.
3. Install Remotion's official Agent Skills: `npx skills add remotion-dev/skills` (choose Claude Code). If they were not loaded when this session started, tell me to restart Claude Code and type `continue from Phase 1`. Follow those skills for all Remotion code.
4. Add packages. **Every `@remotion/*` package must match the installed `remotion` version exactly:** `@remotion/transitions`, `@remotion/google-fonts`, `@remotion/captions`, `@remotion/media-utils`, `@remotion/noise`, `@remotion/paths`, `@remotion/shapes`, `@remotion/motion-blur`, `@remotion/install-whisper-cpp` (fallback only). Also `zod`, plus `world-atlas`, `topojson-client`, `d3-geo` only if a map is needed.
5. Python venv `./binance-heist/.venv` for audio/data scripts: `numpy`, `scipy`, `soundfile`, `requests`, `python-dotenv` (+ `kokoro` only if that voice path is used).
6. Read optional keys from `.env` and never print them: `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`, `PEXELS_API_KEY`, `PIXABAY_API_KEY`. A missing key means "use the fallback", never "stop".
7. **Bandwidth rule — my internet is slow.** Always download the smallest file that does the job (1080p stock, never 4K; small Whisper model; no unnecessary packages). Cache everything and never re-download.

```
binance-heist/
  BINANCE_HEIST_MASTER_PROMPT.md
  .env
  research/   fact-ledger.md  sources.md  changelog.md
  script/     script_locked.md  scenes.json
  assets/
    vo/       scene_01.mp3 …   alignment/scene_01.json …
    ai/       AI-01.mp4 …      (I drop AI shots here)
    stock/    (auto-downloaded + LICENSES.md)
    music/    (I drop licensed tracks here; fallback generated)
    sfx/      (generated or dropped)
    data/     btc_price.json
  scripts/    tts_elevenlabs.py  tts_kokoro.py  align.py  fetch_stock.py
              fetch_prices.py  gen_sfx.py  gen_music_fallback.py  master_audio.py
  src/        Root.tsx  Documentary.tsx  theme.ts  scenes/  components/  lib/
  out/
```

---

## 4. WORKFLOW & CHECKPOINTS

Use a task list. After every phase, append a 3-line status to `research/changelog.md`.

- **Phase 0 — Setup** (Section 3).
- **Phase 1 — Re-verify the facts.** Search the web for everything newer than Nov 3, 2026: Binance's post-mortem or technical report, how the laptop was compromised, the "additional points of breach", updated frozen/recovered amounts, withdrawal status, Proof of Reserves, FBI/DOJ/Treasury actions, sanctions or arrests, North Korea's response, and new TRM Labs / Chainalysis / Elliptic findings. Prefer primary sources (Binance announcements and X posts, FBI/IC3, TRM Labs, Chainalysis, Elliptic) and top outlets (Reuters, AP, Bloomberg, CNBC, CoinDesk, The Block). Update the Fact Ledger, then patch the script: change numbers, set the "as of" date everywhere, and add at most one short new beat if something major happened (for example, if the post-mortem explains how the laptop was compromised, that becomes the reveal in Scene 09). Every item marked **VERIFY** in the ledger must be confirmed or cut.
- **⏸ CHECKPOINT A** — show me the fact changelog and the locked script. Wait for "approved".
- **Phase 2 — Voiceover + timing** (Section 7).
- **Phase 3 — Assets.** Build `script/scenes.json` as an asset manifest: for every scene list the MG components, AI shot IDs, stock queries and data. Download stock + data. Check `assets/ai/` for my AI shots; anything missing → stock fallback → designed MG fallback. A missing asset never blocks the render.
- **Phase 4 — Build the edit** in Remotion (Sections 5, 6, 9).
- **Phase 5 — Sound design & mix** (Section 7).
- **Phase 6 — Captions** (Section 8).
- **⏸ CHECKPOINT B** — render `out/preview_coldopen.mp4` (0:00–1:00) at 1080p and wait for my notes.
- **Phase 7 — Full render + QA** (Section 13). Fix everything QA finds, re-render.
- **Phase 8 — YouTube package** (Section 12).

If I say **"full auto"**, skip both checkpoints but still log everything.

---

## 5. VISUAL STYLE BIBLE

**Mood:** cold, precise, investigative — a thriller told with data. Dark frames, controlled light, one accent color at a time.

**Palette (`theme.ts`):**
- `ink` #07080B background · `panel` #13161B · `line` #262B33
- `alarm` #FF3B3B — attacker, danger, outflows
- `ice` #6FE7FF — freezes, defenders, investigators
- `gold` #E9B949 — money, totals, highlights, active caption word
- `bone` #EDEDED — text · `mute` #8A8F98 — secondary text
- **2019 flashback grade:** desaturated warm-teal, VHS/tape artifacts, date stamp, slightly softer — impossible to confuse with 2026.

**Type (`@remotion/google-fonts`):** `Bebas Neue` (titles, chapter cards, big numbers) · `Inter` (captions, body, labels) · `JetBrains Mono` (timestamps, hashes, data, source tags).

**Frame rules:** title-safe margins 96 px left/right, 54 px top/bottom. Captions stay above the bottom 140 px (YouTube controls). Source tags bottom-left, badges top-left, clock/HUD top-right.

**Motion language:**
- Entrances ease-out (power3/expo); exits ease-in and faster. UI springs with high damping (no bounce). Number pops: one small overshoot max.
- Every still or AI shot gets a slow Ken Burns (scale 1.00 → 1.06 over the shot, slight pan) plus sub-pixel noise drift (`@remotion/noise`).
- **[[PUNCH]]** in the script = punch-in: scale 1.00 → 1.08 in 4 frames, hold, relax over ~20 frames, soft whoosh-hit.
- **[[IMPACT]]** = 6-frame decaying camera shake (≈6 px) + RGB split 8 px → 0 over 6 frames + 2-frame 25 % white flash + sub-boom.
- Motion blur (`@remotion/motion-blur`) only on fast moves where it's visible.
- Realistic AI shots play letterboxed at 2.39:1 (bars animate in over 12 frames). Motion graphics are full frame.

**Texture:** film grain 3–5 % opacity, refreshed every 2nd frame (keeps the bitrate down for a slow upload); vignette 20–25 %; scanlines only on screens/UI; light dust in AI shots.

**Transitions** (build as reusable presentations for `@remotion/transitions`; never use default crossfades):
1. `glitchSlice` — 10–12 displaced horizontal slices + RGB split, 10 frames. Attack beats.
2. `zoomThrough` — scale into a UI element until it fills the frame, enter the next shot. Diagram drill-downs.
3. `filmBurn` — procedural warm light-leak sweep, 18 frames. In and out of the 2019 flashback.
4. `iceWipe` — growing crystal mask in `ice`, 16 frames. Freeze chapter.
5. `dataWipe` — vertical scanline sweep, 12 frames. HUD changes.
6. `dipBlack` — 12 frames to black + sub-boom. Chapter breaks only.
7. Hard cuts on beats with a whoosh for everything else.
- **Signature match-cut:** end of Scene 03 — a grid of hundreds of tiny key icons collapses into one glowing laptop icon → Scene 04.

**Chapter cards (2.5 s):** "CHAPTER 0X" in JetBrains Mono (`mute`) above the title in Bebas Neue (~170 px, letter-spacing 0.06em, `bone`); a red underline wipes in; mono date below. Reverse swell into a sub-boom.

---

## 6. COMPONENT LIBRARY (build first, reuse everywhere)

- `UTCClock` — ticking HH:MM:SS UTC; can run accelerated; flashes red on key times.
- `ChainNetwork` — central "BINANCE WALLETS" core + 10 labeled nodes (Bitcoin, Ethereum, Tron, XRP Ledger, Solana, Arbitrum, Optimism, Base, Avalanche, Polygon); nodes ignite red one by one; particles stream outward; "second wave" state for Avalanche + Polygon.
- `Counter` — currency/number counter with tabular digits; gold glow on landing.
- `TimelineRail` — time rail with events snapping in (Scenes 05–06).
- `TokenCircle` — neutral circle with ticker text (BTC, ETH, USDT, USDC, RLUSD, USD1, ARB, BNB). No logos.
- `FreezeStamp` — ice crystals grow over a TokenCircle + "FROZEN" stamp + amount + who froze it + UTC time.
- `HotColdExplainer` — store blueprint: vault (cold, offline) at the back, cash register (hot, online) at the open street edge.
- `AttackPathDiagram` — LAPTOP → SERVICE CONTAINER → UNAUTHORIZED WITHDRAWAL TRANSACTIONS → HOT WALLETS → 10 CHAINS; red dashed path draws itself (`@remotion/paths`); footer "Simplified illustration — based on Binance's preliminary findings".
- `NonceLock` — the 50-authorizations explainer: a wallet card with "NEXT TRANSACTION #: ???"; 50 numbered permission slips fly in; 49 bounce off; one clicks in; the wallet card flips gold → red: "NOW RUNNING: ATTACKER SWEEPER CODE".
- `SweepVortex` — token circles pulled into a sweeper-contract icon.
- `QuoteCard` — exact short quote, speaker + role, platform, date; typewriter reveal; never a clone of X/Twitter UI.
- `SourceTag` — mono tag like "SOURCE: TRM LABS · OCT 30, 2026"; auto-shown with every figure.
- `DossierReveal` — folder opens, "TRADERTRAITOR" stamps in red, sublines with who attributed it.
- `HeistTimeline` — bars scaled to value: DMM Bitcoin 2024 (~$308M) · Bybit 2025 (~$1.5B) · Bitget 2026 (~$350M) · Binance 2026 (~$6.3B, breaks through the top of the frame).
- `PlaybookCards` — FAKE JOB OFFERS · POISONED CODE · TRUSTED MACHINES + footer "Documented tactics (FBI, CISA) — not confirmed in the Binance case".
- `PriceChart` — BTC line from real data, marker at Oct 29 20:05 UTC, low label.
- `FlowDonut` — Nov 1: $4.65B out vs $1.01B in → net $3.64B = 2.1 % of ~$171B.
- `ProgressRing` — 90 % → 95 % replenished.
- `QuestionCards` — four flip cards stamped "UNKNOWN" (or "ANSWERED" if Phase 1 finds answers).
- `KeyGridCollapse` — the 2019 → 2026 match-cut.
- `Badge` — "FACTS AS OF NOV 3, 2026 · INVESTIGATION ONGOING" · "DRAMATIZATION · AI VISUAL" · "NOT FINANCIAL ADVICE".
- `CaptionTrack` — Section 8.
- Overlays: `FilmGrain`, `Vignette`, `Letterbox`, `Scanlines`, `LightLeak`.
- Camera wrappers: `KenBurns`, `PunchZoom` (driven by cue frames), `CameraShake`.
- `AssetSlot` — plays the AI shot if present → else stock → else a designed MG fallback for that shot ID; logs which source it used.

---

## 7. AUDIO BIBLE

**Voice:** deep, calm, intelligent male documentary narrator; neutral American or British accent; ~150 wpm; tension through restraint, never hype.
1. **ElevenLabs** (if `ELEVENLABS_API_KEY`): highest-quality narration model on the account; stability ≈ 0.5, similarity ≈ 0.75, style ≈ 0.2, speaker boost on. Use the `with-timestamps` endpoint and convert character alignment into word timings. **One audio file per scene.** Remind me once that monetized use needs a paid ElevenLabs plan.
2. **Kokoro-82M** (free, local, Apache-2.0) if there's no ElevenLabs key: voice `bm_george` or `am_michael`; word timings via whisper.cpp (`@remotion/install-whisper-cpp`, model `base.en` to save bandwidth).
3. **My own recording:** if `assets/vo/scene_XX.wav` files already exist, use them and only run alignment.
- Strip every `[[…]]` marker before TTS. Treat "…" and line breaks as pauses (300–600 ms). `[[SILENCE]]` = 0.8–1.2 s of near-silence (room tone only).

**Cue system:** `[[CUE:name]]` sits right before a word in the script. After alignment, map each cue to the frame where that word starts. All reveals, counters, punch-ins and impacts trigger from cue frames — never from guessed timings. Scene length = VO length + designed padding.

**Music:** I'll drop licensed tracks (YouTube Audio Library or a licensed AI track) in `assets/music/` named `act1_coldopen`, `act2_flashback`, `act3_heist`, `act4_freeze`, `act5_name`, `act6_aftermath`, `act7_outro`. If any is missing, `gen_music_fallback.py` generates a tasteful bed for it: dark drones, sub pulses, clock ticks; a tape-warped pad for 2019. Crossfade 1–2 s at scene changes; hit points land on cut frames.

**SFX** (generate procedurally if I don't supply any): whoosh (filtered-noise sweep), sub-boom, risers (3–6 s), glitch zaps, UI ticks, keyboard typing, clock tick, subtle two-tone alarm, ice crack, heartbeat, paper/folder, one cash-register "ching" (Scene 02). Every transition and reveal gets a sound — with restraint.

**Mix:** VO always intelligible. Music ducks 10–14 dB under VO (volume curve driven by VO activity) and swells in the gaps. SFX peaks ≈ −10 dBFS. **Master: −14 LUFS integrated, ≤ −1 dBTP**, two-pass ffmpeg `loudnorm`, verified with `ebur128` and reported.

---

## 8. CAPTIONS

- Source: the word timings from Phase 2. Build pages with `@remotion/captions` (`createTikTokStyleCaptions`, ~1,200 ms combine window) but style them like a premium documentary, not TikTok.
- Look: Inter SemiBold 50–54 px, white, soft black shadow (0 4 px 18 px, 85 %), max 2 lines × ~34 characters, centered, above the bottom 140 px. Active word in `gold`. Key terms pop 1.00 → 1.12 once: "$6.3 BILLION", "TWENTY MINUTES", "FIFTY", "FROZEN", "NORTH KOREA".
- When the same words are already large on screen (titles, counters, quote cards), hide captions for that span or move them up — never double text.
- Prop `burnCaptions` (default `true`). Also export `out/captions_en.srt` (use `serializeSrt` from `@remotion/captions` if available, otherwise write it yourself).

---

## 9. THE SCRIPT — SCENE BY SCENE

**Legend:** **VO** = final narration (change only for Phase-1 fact updates) · **VIS** = visuals · **MUS/SFX** = sound · `MG` motion graphic · `AI-xx` AI shot (Section 10) · `STOCK` · `DATA`.
Timings are targets; real timing comes from the VO.

---

### SCENE 01 — COLD OPEN (≈ 0:00–0:51)

**VO**
> [[CUE:clock]]October 29th, 2026. 8:05 PM, UTC.
> On ten blockchains, within minutes, money starts leaving [[CUE:binance]]Binance — the biggest crypto exchange on Earth.
> Not thousands. Not millions.
> [[IMPACT]][[CUE:billions]]Billions. [[SILENCE]]
> Within about twenty minutes, most of an estimated [[CUE:total]]six point three billion dollars is gone.
> Nobody cracked a safe. Binance says it has found no evidence that a single private key was leaked.
> Instead, its first investigation pointed somewhere far more ordinary…
> [[PUNCH]][[CUE:laptop]]an engineer's laptop. [[SILENCE]]
> This is the story of the biggest crypto heist ever recorded — how the attackers got in, how they emptied the wallets, the race to freeze the money…
> and the one question [[CUE:question]]nobody can answer yet.

**VIS**
- 0:00 pure black → `UTCClock` types "20:05:00 UTC" center frame, clock-tick SFX. Badge "FACTS AS OF NOV 3, 2026 · INVESTIGATION ONGOING" top-left for 6 s.
- `[[CUE:binance]]` `ChainNetwork` assembles: core "BINANCE WALLETS" + 10 nodes; nodes ignite red in quick succession; outflow particles.
- "Not thousands. Not millions." → two small counters flick to $1,000 and $1,000,000 and get struck through.
- `[[CUE:billions]]` [[IMPACT]] giant `Counter` slams in and spins to **$6,300,000,000** (gold) landing on `[[CUE:total]]`. SourceTag: "ESTIMATES: BINANCE ~$6.3B · TRM LABS ~$6.36B".
- "Nobody cracked a safe" → `AI-04` vault door, cold blue with a red seam (letterbox).
- "first investigation pointed…" → `AI-01` server corridor, red beacon sweeping.
- `[[CUE:laptop]]` `AI-02` closed laptop in a dark room; edge pulses red; punch-in; ~1 s of near-silence (room tone + heartbeat).
- "how the attackers got in…" → 2–3 s hyper-montage (6–8 frames each, `glitchSlice` between): flashes of AttackPathDiagram, NonceLock, FreezeStamp, DossierReveal.
- `[[CUE:question]]` a single red "?" that glitches out.
- **TITLE CARD (4 s):** "THE 20-MINUTE HEIST" in huge Bebas Neue assembling from glitch slices; mono subline "BINANCE · OCTOBER 29, 2026". Reverse swell → sub-boom → `dipBlack`.

**MUS/SFX:** act1_coldopen — low pulse + clock ticks; music cuts out completely on "Billions."; returns under the montage; hits on the title.

---

### SCENE 02 — CHAPTER 1: THE FORTRESS (≈ 0:51–1:47)

**VO**
> To understand the size of this, you need to understand Binance.
> It's the world's largest crypto exchange, with around [[CUE:users]]335 million registered users. In its 2025 annual report, it said it held about [[CUE:custody]]162.8 billion dollars in assets under custody.
> An exchange doesn't keep all of that in one place. Think of a store. Most of the money sits in the [[CUE:vault]]vault — cold wallets, kept offline, slow and hard to reach. The rest stays in the [[CUE:register]]cash register — hot wallets — online, so millions of people can withdraw at any second of the day.
> The cash register is convenient. It's also the part of the building that [[PUNCH]]faces the street.
> And Binance already knew what happens when someone reaches into it. Because [[CUE:before]]it had happened before.

**VIS**
- Chapter card "CHAPTER 1 — THE FORTRESS".
- `AI-03` aerial night financial district (letterbox) under the first line.
- `[[CUE:users]]` `Counter` "335,000,000 REGISTERED USERS"; `[[CUE:custody]]` "$162.8B IN CUSTODY". SourceTag: "BINANCE 2025 ANNUAL REPORT, VIA REUTERS".
- `[[CUE:vault]]` `HotColdExplainer`: vault lights up `ice` (OFFLINE + lock icon). `[[CUE:register]]` register lights up `gold` (ONLINE + signal icon) + "ching".
- "faces the street" → camera dollies to the register at the open edge of the blueprint; red street light leaks in from outside frame.
- `[[CUE:before]]` → `filmBurn` into the flashback.

---

### SCENE 03 — CHAPTER 2: THE FIRST HEIST (≈ 1:47–3:26)

*Entire scene in the 2019 flashback grade with a date stamp "MAY 07 2019 · 17:15:24 UTC" bottom-right.*

**VO**
> [[CUE:may2019]]May 7th, 2019. 17:15 UTC.
> One transaction pulls [[CUE:7000]]seven thousand Bitcoin out of Binance's hot wallet — about forty million dollars at the time.
> Binance later explained how. Hackers had collected a large number of user [[CUE:apikeys]]API keys, two-factor codes and other information — using [[CUE:phishing]]phishing, viruses and other attacks.
> And then they waited. Binance said the hackers [[CUE:quote2019]]"had the patience to wait" — striking through multiple accounts that looked unrelated, with a withdrawal built to pass every security check.
> The alarms fired [[PUNCH]]only after the money was gone.
> Then came the strangest part. In a livestream, Binance's CEO, Changpeng Zhao — [[CUE:cz]]CZ — said the exchange was weighing a radical idea, first floated by a Bitcoin developer: paying miners to [[CUE:rewrite]]rewrite the blockchain and undo the theft.
> The backlash was immediate. Within a day, CZ dropped it, writing that the Bitcoin ledger is [[CUE:quoteCZ]]"the most immutable ledger on the planet."
> Binance covered the loss from [[CUE:safu]]SAFU — its Secure Asset Fund for Users, funded since 2018 with ten percent of trading fees. A week later, withdrawals were back.
> Three years after that, in [[CUE:2022]]2022, an attacker abused a bug in a bridge on Binance's own BNB Chain to create two million BNB out of thin air — and the chain had to be halted.
> Each time, the lesson was the same. The weak point is never the math. [[PUNCH]]It's everything around it.

**VIS**
- `[[CUE:7000]]` MG single transaction: "BINANCE HOT WALLET" → "7,000 BTC" → unknown address; the real public tx hash types out truncated `e8b40609…554ab05ea`. SourceTag: "BINANCE SECURITY UPDATE · MAY 7, 2019". Under it, `AI-05` VHS gold coins.
- `[[CUE:apikeys]]` three tiles flip in: "API KEYS" / "2FA CODES" / "OTHER INFO".
- `[[CUE:phishing]]` a generic lookalike login card (fictional "EXCHANGE" brand, not Binance's UI) whose URL bar has one subtly different character, circled in red.
- "waited" → clock fast-forward; dozens of small, unrelated-looking account cards light up at the same moment.
- `[[CUE:quote2019]]` `QuoteCard`: "had the patience to wait" — Binance security update, May 2019.
- "only after the money was gone" → alarm light flashing on an empty MG vault; light [[IMPACT]].
- `[[CUE:cz]]` name card "CHANGPENG ZHAO (CZ) — BINANCE CEO IN 2019" over an abstract "LIVE" stream frame with a voice waveform (no face).
- `[[CUE:rewrite]]` MG chain of blocks slides backwards with rewind SFX… cracks… stops dead.
- `[[CUE:quoteCZ]]` `QuoteCard`: "the most immutable ledger on the planet" — CZ on X, May 8, 2019.
- `[[CUE:safu]]` MG vault labeled "SAFU" filling with particles labeled "10% OF TRADING FEES"; stamp "WITHDRAWALS BACK · MAY 15, 2019".
- `[[CUE:2022]]` fast card: "OCT 2022 · BNB CHAIN BRIDGE EXPLOIT · 2,000,000 BNB CREATED · CHAIN HALTED". SourceTag: "BNB CHAIN · OCT 2022".
- End: `KeyGridCollapse` (hundreds of key icons → one glowing laptop icon) → `filmBurn` out of the flashback.

**MUS/SFX:** act2_flashback — tape-warped pad, lo-fi pulse; drops out on "only after the money was gone", resumes.

---

### SCENE 04 — CHAPTER 3: THE DOOR (≈ 3:26–4:42)

**VO**
> Now — back to October 2026.
> Here's what Binance has said. Its initial investigation suggests the incident may have started with a [[CUE:laptop2]]compromised laptop belonging to a DevOps engineer — one of the people who build and run the machinery behind the exchange.
> From that laptop, an attacker reached what Binance calls a [[CUE:container]]"service container" — part of its internal infrastructure — and from there, submitted [[CUE:unauth]]unauthorized withdrawal transactions.
> Hours later, Binance said it had found [[CUE:additional]]additional points of breach. Co-CEO Richard Teng put it bluntly: this was not a single [[CUE:oneclick]]"one-click" action. The attacker did not simply use one engineer's permissions.
> And it was planned. According to blockchain analysts at TRM Labs, staging began at least [[CUE:36h]]thirty-six hours earlier, with small withdrawals from the crypto mixer Tornado Cash funding the attacker's operating wallet. On-chain reconstructions suggest the attacker even [[CUE:rehearse]]rehearsed on test wallets.
> Investigators believe the attackers didn't need to steal the keys. They got Binance's [[PUNCH]]own systems to sign for them.
> So how do you turn a laptop into six billion dollars?
> [[CUE:20min]]You give yourself twenty minutes.

**VIS**
- Chapter card "CHAPTER 3 — THE DOOR".
- `AI-06` hands typing in darkness (letterbox), then `AttackPathDiagram` builds box by box on `[[CUE:laptop2]]`, `[[CUE:container]]`, `[[CUE:unauth]]` (`zoomThrough` into each). Footer: "SIMPLIFIED ILLUSTRATION — BINANCE PRELIMINARY FINDINGS, OCT 30, 2026".
- `[[CUE:additional]]` the diagram glitches; three extra red "?" breach points appear around it.
- `[[CUE:oneclick]]` `QuoteCard`: "not a single 'one-click' action" — Richard Teng, Binance co-CEO, Oct 30, 2026.
- `[[CUE:36h]]` calendar flips to "OCT 28 · T–36H"; three small drips labeled "TORNADO CASH" fall into an "OPERATOR WALLET". SourceTag: TRM LABS.
- `[[CUE:rehearse]]` three small "TEST WALLET" tiles flash, one by one (cut this beat if Phase 1 can't confirm it).
- "didn't need to steal the keys" → stamp "PRIVATE KEY LEAK: NO EVIDENCE FOUND — BINANCE".
- "own systems to sign for them" → a signature line draws itself across a transaction card in `alarm`.
- `[[CUE:20min]]` a huge "20:00" timer appears and starts counting down → hard cut on a heartbeat into Scene 05.

---

### SCENE 05 — CHAPTER 4: THE 20 MINUTES (≈ 4:42–6:16)

*Persistent HUD for the whole scene: `UTCClock` top-right (accelerated), `TimelineRail` 20:05 → 20:25 along the bottom.*

**VO**
> [[CUE:t2005]]8:05 PM. The first funds start moving.
> Binance wallets on ten networks begin sending money out — Bitcoin, Ethereum, Tron, the XRP Ledger, Solana, and more. On nine of those chains, it looks almost normal: [[CUE:ordinary]]ordinary transfers, signed by Binance's own wallets.
> [[PUNCH]]Ethereum is different.
> At [[CUE:t2020]]8:20 and 59 seconds, one transaction targets a Binance hot wallet labeled [[CUE:b14]]"Binance 14." Inside it: [[CUE:fifty]]fifty authorizations — all signed with Binance 14's own key — using an Ethereum feature called [[CUE:eip]]EIP-7702, which lets a wallet hand its powers to a piece of code.
> Why fifty? Every wallet keeps a running count of its transactions. An authorization only works if it matches the right number — and the attacker didn't know which number Binance 14 was on. So they brought fifty signed permission slips, one for every possible number.
> [[IMPACT]][[CUE:onefit]]Exactly one matched. [[SILENCE]]
> In that moment, Binance 14 stopped being Binance's wallet. It was running the attacker's [[CUE:sweeper]]sweeper code.
> In under four minutes, it emptied — about [[CUE:eth167]]167,000 ETH, roughly 1.6 billion USDT, and dozens of other tokens.
> By TRM's count, Ethereum alone accounted for about [[CUE:eth38]]3.8 billion dollars. On Bitcoin: [[CUE:btc18]]18,270 BTC — around 1.47 billion more.
> Most of it was gone in about twenty minutes.
> And then, around 11 PM, a [[CUE:wave2]]second wave hit — on Avalanche and Polygon.

**VIS**
- Chapter card "CHAPTER 4 — THE 20 MINUTES".
- `[[CUE:t2005]]` `ChainNetwork` full screen; nodes ignite with chain names (if Phase 1 confirms the first outflow was on the XRP Ledger, ignite it first and show its amount).
- `[[CUE:ordinary]]` nine nodes receive "SIGNED ✓" seals — rendered in red, ironic.
- "Ethereum is different." → `zoomThrough` into the Ethereum node.
- `[[CUE:b14]]` wallet card "BINANCE 14 — ETHEREUM HOT WALLET (ETHERSCAN LABEL)".
- `[[CUE:fifty]]` `NonceLock`: 50 numbered slips cascade in; "NEXT TRANSACTION #: ???".
- `[[CUE:eip]]` lower third: "EIP-7702 — lets a wallet delegate its behavior to smart-contract code (live on Ethereum since May 2025)".
- `[[CUE:onefit]]` 49 slips bounce off, one clicks in — [[IMPACT]] — the wallet card flips gold → red: "NOW RUNNING: ATTACKER SWEEPER CODE". Hold the silence.
- `[[CUE:sweeper]]` `SweepVortex` over `AI-07` (vortex underlay); ETH, USDT and "~60 TOKENS" swirl in.
- `[[CUE:eth167]]` counters "167,464 ETH" · "~1.62B USDT" · "~60 TOKENS" + tag "UNDER 4 MINUTES". SourceTag: "TRM LABS · BLOCKAID RECONSTRUCTION".
- `[[CUE:eth38]]` bars: "ETHEREUM ~$3.79B" · `[[CUE:btc18]]` "BITCOIN 18,270 BTC ~$1.47B" · "8 OTHER CHAINS — REMAINDER". SourceTag: "TRM LABS ESTIMATES".
- "Most of it was gone…" → clock freezes at 20:25; `AI-08` monitor wall with red graphs and an empty chair.
- `[[CUE:wave2]]` Avalanche + Polygon nodes re-ignite; clock jumps to "23:05 UTC".

**MUS/SFX:** act3_heist — driving pulse building to "Exactly one matched." → hard cut to silence → heavier drop under the sweep. Typing ticks for the slips; lock "click" for the match.

---

### SCENE 06 — CHAPTER 5: THE RACE TO FREEZE (≈ 6:16–7:56)

*Split-screen race UI: left "ATTACKER" (`alarm`), right "FREEZE" (`ice`), vertical `TimelineRail` with UTC times in the middle.*

**VO**
> While the money moved, a race began.
> Some crypto can be frozen. [[CUE:stables]]Stablecoins like USDT and USDC are issued by companies — and those companies can lock tokens sitting in a specific wallet.
> At [[CUE:t2101]]9:01 PM, Tether froze about 971 million USDT in the attacker's main receiving wallet. Three minutes later, [[CUE:t2104]]Circle froze 823 million USDC.
> At [[CUE:t2124]]9:24, Binance posted publicly for the first time: it was aware of "a potential security issue."
> A minute later, Tether's CEO said more than [[CUE:t2125]]1.5 billion dollars in USDT was frozen. [[CUE:others]]Ripple froze its stablecoin. World Liberty Financial froze theirs. Arbitrum's Security Council locked up about 30 million dollars in ETH and ARB.
> Shortly after midnight UTC, Binance [[CUE:suspend]]suspended all deposits and withdrawals — and promised to cover every loss.
> Binance now says about [[CUE:frozen3]]3 billion dollars has been frozen on-chain. Independent trackers count a little less — Elliptic, 2.84 billion; TRM, around 2.7.
> But Bitcoin and Ether [[PUNCH]]have no company that can freeze them. And the attacker kept moving — [[CUE:dump]]selling about 325 million USDT to market makers at a discount of more than ten percent, and using USDT on the lending platform [[CUE:aave]]Aave to borrow ether.
> As of TRM's latest analysis, the attacker still holds more than [[CUE:remain]]420,000 ETH and 18,270 BTC — about 2.4 billion dollars that no issuer can freeze — with the Bitcoin splitting into a long chain of [[CUE:peel]]smaller and smaller transfers.

**VIS**
- Chapter card "CHAPTER 5 — THE RACE TO FREEZE".
- `[[CUE:stables]]` `TokenCircle` USDT + USDC tagged "ISSUER CAN FREEZE ✓"; BTC + ETH tagged "NO ISSUER ✕".
- `[[CUE:t2101]]` `FreezeStamp` "971.1M USDT · TETHER · 21:01 UTC" + `iceWipe`.
- `[[CUE:t2104]]` `FreezeStamp` "823M USDC · CIRCLE · 21:04 UTC" over `AI-09` ice macro.
- `[[CUE:t2124]]` `QuoteCard`: "a potential security issue" — Binance on X, 21:24 UTC.
- `[[CUE:t2125]]` counter jumps to "1.567B+ USDT FROZEN". SourceTag: "TETHER CEO ON X".
- `[[CUE:others]]` three quick stamps: "RLUSD · RIPPLE" · "27.8M USD1 · WORLD LIBERTY FINANCIAL" · "~$30M ETH + ARB · ARBITRUM SECURITY COUNCIL".
- `[[CUE:suspend]]` red alarm wash: "00:13 UTC — ALL DEPOSITS & WITHDRAWALS SUSPENDED". [[IMPACT]].
- `[[CUE:frozen3]]` three bars with sources: "BINANCE ~$3.0B" · "ELLIPTIC $2.84B" · "TRM ~$2.7B".
- "no company that can freeze them" → BTC and ETH circles melt straight through the ice.
- `[[CUE:dump]]` "~325M USDT → MARKET MAKERS · 10%+ DISCOUNT"; `[[CUE:aave]]` "USDT COLLATERAL → ~19,760 ETH BORROWED". SourceTag: TRM LABS.
- `[[CUE:remain]]` big counters "420,000+ ETH" + "18,270 BTC" = "~$2.4B BEYOND ANY FREEZE".
- `[[CUE:peel]]` peel-chain visual: one BTC line splitting into a cascading tree of thinner and thinner lines toward the frame edge.

**MUS/SFX:** act4_freeze — tense arpeggios + ticking; an ice-crack on every freeze; subtle alarm at the suspension.

---

### SCENE 07 — CHAPTER 6: THE NAME (≈ 7:56–9:32)

**VO**
> By the next morning, investigators had a name.
> TRM Labs attributed the attack "with high confidence" to [[IMPACT]][[CUE:tt]]TraderTraitor — a North Korean state-backed hacking unit, widely described as part of the Lazarus Group. Chainalysis reached the same conclusion, linking the funds to September's [[CUE:bitget]]Bitget hack. Elliptic agreed. Then [[CUE:fbi]]the FBI said it publicly: North Korea was responsible.
> North Korea has denied involvement. And Binance itself hasn't named the attackers — it says it's working with law enforcement to confirm who they are.
> If TraderTraitor sounds familiar, it should. In February 2025, the FBI blamed the same group for the hack of [[CUE:bybit]]Bybit — about 1.5 billion dollars, the record until now. In that case, the breach was traced to a compromised developer machine at Safe, the wallet software Bybit relied on.
> In 2024, Japan's [[CUE:dmm]]DMM Bitcoin lost about 300 million dollars. According to the FBI and Japanese police, it began when a fake recruiter sent an employee at a partner company a malicious "pre-employment test."
> [[CUE:playbook]]Fake job offers. Poisoned code. Trusted machines turned into doorways. It's a playbook security agencies have warned about for years.
> To be clear: Binance has not said how its engineer's laptop was compromised.
> But TRM says this attack fits the pattern — staging well before the theft, Tornado Cash funding, and signatures collected in advance… then [[PUNCH]]fired in one burst.

**VIS**
- Chapter card "CHAPTER 6 — THE NAME". `AI-10` archive desk lamp over a dossier.
- `[[CUE:tt]]` `DossierReveal`: "TRADERTRAITOR" red stamp; sublines "A.K.A. JADE SLEET · LAZARUS GROUP SUBUNIT (PER RESEARCHERS)"; badge "ATTRIBUTION: TRM LABS · CHAINALYSIS · ELLIPTIC · FBI".
- `[[CUE:bitget]]` two flows — "BITGET HACK · SEP 2026" and "BINANCE HACK · OCT 2026" — converge into one address node. SourceTag: "CHAINALYSIS · ZACHXBT".
- `[[CUE:fbi]]` text card with the FBI's short statement phrase (exact wording verified in Phase 1) + date.
- "North Korea has denied involvement" → plain `mute` text card "NORTH KOREA DENIES INVOLVEMENT" + source.
- `[[CUE:bybit]]` `HeistTimeline` begins: "DMM BITCOIN · 2024 · ~$308M", "BYBIT · FEB 2025 · ~$1.5B" (sub: "FBI: TRADERTRAITOR · COMPROMISED SAFE DEVELOPER MACHINE"), "BITGET · SEP 2026 · ~$350M"; hold the Binance bar for the end of the scene.
- `[[CUE:dmm]]` MG recruiter-email mockup (fictional names, fictional company, obviously generic) with an attachment "pre_employment_test" glowing red.
- `[[CUE:playbook]]` `PlaybookCards` slam in one per phrase; footer "DOCUMENTED TACTICS (FBI, CISA) — NOT CONFIRMED IN THE BINANCE CASE".
- `AI-11` faceless hooded silhouette in front of glyph screens, max 3 s, with "DRAMATIZATION · AI VISUAL" badge.
- "fired in one burst" → all ten chain nodes flash at once + white flash; the Binance bar "BINANCE · OCT 2026 · ~$6.3B" smashes through the top of the frame. [[IMPACT]].

**MUS/SFX:** act5_name — dark, heavy, low choir-like pad; a sub hit on every card.

---

### SCENE 08 — CHAPTER 7: THE MORNING AFTER (≈ 9:32–10:45)

**VO**
> Markets felt it. [[CUE:btclow]]Bitcoin slid to a six-week low near 76,400 dollars. Ether hit a two-month low. BNB fell more than five percent, and shares of Coinbase and Strategy dropped in after-hours trading.
> Binance's answer echoed 2019: customers won't pay for this. It said it had earmarked about [[CUE:634]]6.34 billion dollars to cover the losses — far more than its SAFU emergency fund, which holds around one billion. Co-CEO Richard Teng told users Binance was [[CUE:teng]]"covering every loss." Founder CZ — who stepped down as CEO in 2023 — said that as a shareholder, he expected every user to be made whole.
> On Sunday, November 1st, [[CUE:withdraw]]withdrawals started coming back in phases — Bitcoin first. That day, users pulled out about 4.65 billion dollars and deposited about 1.01 billion. [[CUE:net]]Net outflow: 3.64 billion — which Binance says is 2.1 percent of its total assets. CZ's takeaway: [[CUE:98]]"98% choose to stay."
> By then, Binance said it had replenished about [[CUE:95]]95 percent of the affected assets — and was still buying the rest.

**VIS**
- Chapter card "CHAPTER 7 — THE MORNING AFTER". `AI-12` dawn skyline.
- `[[CUE:btclow]]` `PriceChart` (DATA, BTC/USD Oct 22 → Nov 3, 2026) with a red marker at Oct 29 20:05 UTC and a low label "$76,368 · 6-WEEK LOW (REUTERS)". Ticker strip: "ETH 2-MONTH LOW · BNB −5.3% · COIN −4.8% · MSTR ~−6% (AFTER HOURS)".
- `[[CUE:634]]` honest-scale comparison: "$6.34B EARMARKED" vs "SAFU ~$1B".
- `[[CUE:teng]]` `QuoteCard`: "covering every loss" — Richard Teng, Binance co-CEO.
- CZ name card "CHANGPENG ZHAO (CZ) — FOUNDER · STEPPED DOWN AS CEO IN 2023" + a paraphrase line (not a quote).
- `[[CUE:withdraw]]` network status board lighting green in sequence: "NOV 1 · PHASE 1 · BTC ✓ ETH ✓ BNB ✓ XRP ✓…".
- `[[CUE:net]]` `FlowDonut`: "$4.65B OUT · $1.01B IN · NET −$3.64B = 2.1% OF ~$171B". SourceTag: "BINANCE, VIA CNBC".
- `[[CUE:98]]` `QuoteCard`: "98% choose to stay!" — CZ on X.
- `[[CUE:95]]` `ProgressRing` 90% → 95% "AFFECTED ASSETS REPLENISHED". SourceTag: "BINANCE · NOV 1, 2026".

**MUS/SFX:** act6_aftermath — sparse piano, soft pulse.

---

### SCENE 09 — CHAPTER 8: THE QUESTION (≈ 10:45–11:35)

**VO**
> And yet, the biggest questions are still open.
> [[CUE:q1]]How was the laptop compromised?
> [[CUE:q2]]What were the other points of breach?
> [[CUE:q3]]How did the attacker get Binance's systems to sign fifty authorizations — with no evidence, Binance says, of a leaked private key?
> [[CUE:q4]]And the billions in Bitcoin and Ether that no issuer can freeze — will any of it ever come back?
> In [[CUE:y2019]]2019, hackers phished their way into user accounts and took forty million dollars.
> In [[CUE:y2026]]2026, investigators believe the attackers turned the exchange's own machinery against it — and moved [[PUNCH]]more than a hundred and fifty times as much.
> [[SILENCE]]The money moved in twenty minutes.
> [[CUE:years]]The investigation could take years.

**VIS**
- Chapter card "CHAPTER 8 — THE QUESTION".
- `[[CUE:q1]]`…`[[CUE:q4]]` `QuestionCards` flip in one per question, each stamped "UNKNOWN". If Phase 1 found an answer, stamp "ANSWERED", show the one-line answer, and adjust the VO.
- `[[CUE:y2019]]` / `[[CUE:y2026]]` split screen: left "2019 · $40M · USER ACCOUNTS" (flashback grade) vs right "2026 · ~$6.3B · THE EXCHANGE'S OWN SYSTEMS"; the right bar grows ~157× and rises out of frame.
- "The money moved in twenty minutes." → `UTCClock` runs 20:05 → 20:25 one last time and freezes.
- `[[CUE:years]]` `AI-13` laptop lid closing, red light narrowing to a line → black. Hold 1 s of silence.

**MUS/SFX:** act6 thinning to near-silence; one low note at the very end.

---

### SCENE 10 — OUTRO: WHAT IT MEANS FOR YOU (≈ 11:35–12:22 + 20 s end screen)

**VO**
> So what does this mean for you?
> Any money you keep on an exchange is protected by their security — not yours. [[CUE:tip1]]Use the strongest two-factor you can, like a hardware key or a passkey. [[CUE:tip2]]Turn on withdrawal address whitelists. [[CUE:tip3]]Don't keep more on an exchange than you need to trade.
> And if you work in tech or crypto: treat surprise job offers and take-home [[CUE:tip4]]"coding tests" from strangers like a live wire. Investigators have seen that door used again and again.
> This story isn't over. [[CUE:sub]]Subscribe so you don't miss what the investigation finds next — and tell me in the comments: should exchanges keep billions in wallets that are online at all?

**VIS**
- Clean `ink` background; four tip cards with simple line icons (security key, checklist, wallet, briefcase with warning) on `[[CUE:tip1]]`–`[[CUE:tip4]]`.
- Badge "NOT FINANCIAL ADVICE".
- `[[CUE:sub]]` end-screen layout for the last 20 s: two empty video-slot frames (right), subscribe area (left), `ChainNetwork` drifting at 15 % opacity behind, line "SOURCES IN THE DESCRIPTION · FACTS AS OF NOV 3, 2026".

**MUS/SFX:** act7_outro — tense but resolving; ends clean on the last frame.

---

## 10. AI SHOT LIST (for Higgsfield / Muse / Gemini / Kling — or any image + video model)

**Rules:** 16:9, 5 s each (10 s where noted), no text, no logos, no recognizable faces, consistent look. Make a still first (image model), then animate it (image-to-video). Save exactly as `AI-01.mp4` … `AI-13.mp4` and `AI-14.png` in `assets/ai/`. Use the same laptop reference image for AI-02, AI-13 and AI-14.

**Append this style suffix to every image prompt:**
`cinematic documentary still, anamorphic framing, low-key lighting, deep blacks, teal shadows with crimson accents, shallow depth of field, subtle 35mm film grain, photoreal, high detail, no text, no logos, no watermark, no visible faces`

| ID | Scene | Image prompt | Motion prompt | Stock fallback query |
|---|---|---|---|---|
| AI-01 | 01 | Endless data-center corridor at night, rows of server racks with tiny blue status LEDs, light haze, a red emergency beacon starting to rotate | Slow dolly forward down the corridor; red beacon light sweeps across the racks | server room red light |
| AI-02 | 01 | A closed silver laptop on a dark wooden desk in an empty apartment at night, rain-streaked window behind with city bokeh, the laptop's edge glowing faint red | Very slow push-in; the red edge glow pulses once like a heartbeat | laptop dark room night |
| AI-03 | 02 | Aerial night view of a futuristic financial district, glass towers, light trails on highways, cold blue fog between buildings | Slow drone glide forward with a slight descent | city night aerial |
| AI-04 | 01 | Massive circular steel vault door, closed, in a cold blue concrete chamber, a thin line of red light appearing along its seam | Slow arc around the door; the red seam light intensifies | bank vault door |
| AI-05 | 03 | Close-up of golden coins engraved with the ₿ symbol scattered on dark velvet, 2019 camcorder look, VHS softness, slight chromatic aberration | Slow handheld drift with VHS tracking flicker | gold coins macro |
| AI-06 | 04 | Extreme close-up of hands typing on a laptop keyboard in total darkness, only the screen glow lights the knuckles, no face in frame | Subtle handheld drift, fingers typing | typing keyboard dark |
| AI-07 | 05 | Abstract streams of golden light particles pulled into a black spiral vortex in empty space, volumetric light | Vortex rotates; particles accelerate inward | abstract particles vortex |
| AI-08 | 05 | Dark room with a wall of monitors showing abstract red graphs and flowing data patterns (no readable text), an empty office chair in silhouette | Slow lateral slide; monitors flicker | monitors data dark room |
| AI-09 | 06 | Macro shot of ice crystals rapidly forming across a glass surface, warm golden light trapped beneath, cold cyan rim light | Crystals spread across the frame | ice forming macro |
| AI-10 | 07 | Dim archive room, a single desk lamp over a closed dossier folder with a red seal (no readable text), dust floating in the light beam | Slow push-in on the folder | documents desk lamp |
| AI-11 | 07 | Anonymous figure in a dark hoodie seen from behind, fully in shadow, backlit by a wall of screens with abstract glyphs | Slow push-in; screens flicker | hacker silhouette screens |
| AI-12 | 08 | Dawn over a quiet city skyline, cold morning light, thin mist, empty streets, a sense of aftermath | Slow tilt up toward the sky | city sunrise skyline |
| AI-13 | 09 | The same silver laptop as AI-02 on the same desk, lid half open, red glow spilling from the screen | Lid slowly closes; the red light narrows to a line and disappears to black (10 s) | laptop closing dark |
| AI-14 | Thumbnail | The same silver laptop on a black surface, intense red glow spilling from the screen, wisps of smoke, dramatic rim light, large empty dark area on the left for text | Still image only | — |

If an image/video-generation connector (for example Higgsfield) is available inside this Claude Code session, you may generate these yourself — **ask me before spending credits.** Otherwise, list any shots still missing at Checkpoint B.

---

## 11. STOCK & DATA (automatic)

- `fetch_stock.py`: Pexels API first (`PEXELS_API_KEY`), Pixabay second (`PIXABAY_API_KEY`). Landscape, ≥ 1920 px wide, prefer 1080p files, 6–15 s, no visible logos or readable brand text. Max 2 candidates per query. Record source URL + license in `assets/stock/LICENSES.md`.
- `fetch_prices.py`: BTC/USD hourly, Oct 22 → Nov 3, 2026, from CoinGecko (use a free demo key if required) or Binance public klines (`BTCUSDT`, 1h). Cache to `assets/data/btc_price.json`. Plot real data only.
- Never download news footage, YouTube videos, or images of real people.

---

## 12. YOUTUBE PACKAGE (`out/youtube_metadata.md`)

- **Titles (≤ 60 characters; recommend one):**
  1. How Hackers Stole $6.3 Billion From Binance in 20 Minutes
  2. The Biggest Crypto Heist in History: Inside the Binance Hack
  3. $6.3 Billion in 20 Minutes: The Binance Heist Explained
- **Thumbnails** (Remotion `still`, 1280×720, max 4 words, readable at phone size, no logos, no real faces):
  - A — `AI-14` laptop + giant gold "$6.3B" with a crack running through it, small red "20 MINUTES".
  - B — black frame, red `UTCClock` "20:05" + the word "BINANCE" in our own type, cracked.
  - C — split: small gray "2019 · $40M" → huge red-gold "2026 · $6.3B".
- **Description:** two-line hook · "Facts as of [date]. The investigation is ongoing." · chapters with real timestamps from the final render (first one at 0:00) · full source list from `research/sources.md` · "AI-generated dramatizations are labeled on screen." · "Not financial advice." · #Binance #CryptoHack #Documentary
- **Tags:** binance hack, binance hacked, binance 6.3 billion, biggest crypto heist, crypto hack documentary, tradertraitor, lazarus group, north korea hackers, eip-7702, bybit hack, crypto security, bitcoin news
- **Pinned comment:** one sharp question to drive replies + "Sources are in the description."
- **Upload settings:** category Science & Technology · language English · upload `captions_en.srt` · **Altered or synthetic content: Yes** (realistic AI B-roll) · not made for kids · end screen on the last 20 s · chapters on.

---

## 13. QA CHECKLIST (run before you call it done)

- [ ] Every figure, date, time and quote in VO and on screen matches `research/fact-ledger.md` — list mismatches and fix them.
- [ ] Quotes are exact, short, attributed and dated.
- [ ] No logos, no news clips, no AI likeness of a real person, nothing identifying the engineer.
- [ ] Captions in sync within ±80 ms; no typos; no doubled text.
- [ ] All text inside title-safe; nothing under the YouTube controls area.
- [ ] Something changes every 3–6 s; no dead frames; no unintended black.
- [ ] Flashback sections are unmistakably 2019 (grade + date stamp).
- [ ] Loudness report: −14 LUFS ±0.5 integrated, true peak ≤ −1 dBTP; VO intelligible everywhere.
- [ ] `ffprobe` confirms render specs; both files play start to finish.
- [ ] Report the size of `upload_1080p.mp4` (target ≤ ~800 MB).
- [ ] Report which shots used AI vs stock vs MG fallback.

---

## 14. FACT LEDGER (verified as of Nov 3, 2026 — re-verify in Phase 1)

### The October 29, 2026 hack
| # | Fact | Source(s) |
|---|---|---|
| F1 | Outflows began ~20:05 UTC, Oct 29, 2026; ~$6.36B moved out of Binance wallets on 10 blockchains, most of it in ~20 minutes | TRM Labs (via AP, Decrypt, BleepingComputer) |
| F2 | Binance's estimate of total impact ~$6.3B; Chainalysis ~$6.4B; Elliptic ~$6.43B (counts 11 chains) | Binance; Chainalysis; Elliptic |
| F3 | Initial finding: compromised DevOps engineer's laptop → access to a "service container" → unauthorized withdrawal transactions submitted | Binance; Richard Teng (via AP, BBC, BleepingComputer) |
| F4 | Later update: "additional points of breach"; Teng: attacker did not simply use one engineer's permissions; not a single "one-click" action; a complex attack | Binance; Teng on X (via Decrypt) |
| F5 | Binance: no evidence of any wallet private key leak | Binance on X (via AP/ITV) |
| F6 | How the laptop was compromised: not disclosed as of Nov 3 | Binance; Elliptic |
| F7 | Staging ≥ 36 h before the theft; operator wallet funded by small Tornado Cash withdrawals starting Oct 28 | TRM Labs; Chainalysis (via Decrypt, Cybersecurity Dive) |
| F8 | Attacker deployed a sweeper contract and rehearsed on three test wallets — **VERIFY** | Protos on-chain reconstruction |
| F9 | 20:20:59 UTC: one transaction carried 50 EIP-7702 authorizations signed by the "Binance 14" hot wallet (Etherscan label) for consecutive nonces; exactly one applied | TRM Labs; Blockaid (via Gizmodo, Protos, CoinAlertNews) |
| F10 | In under 4 minutes Binance 14 was swept of 167,464 ETH, ~1.62B USDT and ~60 other tokens (≈ $2.5B) | TRM Labs (via Cryptoast, CoinAlertNews) |
| F11 | The other 9 chains: ordinary signed transfers | TRM Labs |
| F12 | Ethereum ≈ $3.79B in total; Bitcoin 18,270 BTC ≈ $1.47B | TRM Labs (via CoinDesk, Stingrai) |
| F13 | The first outflow may have been ~$296M on the XRP Ledger — **VERIFY before using** | CryptoSlate (citing TRM) |
| F14 | Freeze timeline (UTC): 21:01 Tether 971.1M USDT · 21:04 Circle 823M USDC · 21:24 Binance "a potential security issue" · 21:25 Tether CEO: >1.567B USDT frozen · ~22:01 Ripple RLUSD · ~22:10 WLFI 27.8M USD1 · 23:05 second wave (Avalanche, Polygon) · 00:13 Oct 30 Binance suspends deposits & withdrawals — **VERIFY each time** | TRM Labs + company posts on X (compiled by Stingrai) |
| F15 | Arbitrum Security Council: 8,426 ETH + 74.6M ARB (~$30M) out of the attacker's reach | TRM Labs |
| F16 | Frozen totals: Binance ~$3B; TRM ~$2.7B; Elliptic $2.84B (~44 %) | Binance; TRM; Elliptic |
| F17 | ~325M USDT sold to market makers at a >10 % discount; ~19,760 ETH borrowed on Aave against USDT | TRM Labs |
| F18 | Attacker still holds >420,000 ETH + 18,270 BTC ≈ $2.4B beyond issuer freezes; BTC moving through a peel chain | TRM Labs (via BleepingComputer, Bitcoin.com) |
| F19 | Attribution: TRM "high confidence" → TraderTraitor (North Korea; Lazarus subunit, a.k.a. Jade Sleet); Chainalysis CEO Jonathan Levin: likely TraderTraitor; Elliptic → North Korea; ZachXBT → likely Lazarus; Binance and Bitget hack funds converged | TRM; Chainalysis; Elliptic; ZachXBT (via AP, Cointelegraph) |
| F20 | FBI: North Korea was responsible for the theft of more than $6B from Binance, on or about Oct 29, 2026 | FBI statement (via CBS News, Nov 1–2) |
| F21 | North Korea denies involvement — **VERIFY wording + source** | CryptoTimes headline; Reuters notes NK routinely denies such accusations |
| F22 | Binance hasn't attributed it to any individual; working with law enforcement "to confirm the identity of the criminals" | Binance spokesperson (AP); Teng |
| F23 | FBI and U.S. Secret Service involved | Cybersecurity Dive; Reuters |
| F24 | Binance earmarked ~$6.34B to cover losses; SAFU holds ~$1B | Reuters; Bankless/CoinDesk |
| F25 | Teng: "covering every loss" | Reuters |
| F26 | CZ: "User funds are safe!"; "does look like a hack on Binance"; as a shareholder expects all user funds fully covered; stepped down as CEO in 2023 | AP |
| F27 | Market: BTC 6-week low $76,368; ETH 2-month low $2,178; BNB −5.3 %; Coinbase −4.8 %; Strategy ~−6 % after hours | Reuters |
| F28 | Withdrawals resumed in phases Nov 1 from 06:00 UTC, Bitcoin first (~06:20 UTC); 15 networks in phase one | Binance (via CoinDesk, BeInCrypto, CryptoTimes) |
| F29 | Nov 1, 06:00–15:30 UTC: $4.65B withdrawn, $1.01B deposited, net −$3.64B = 2.1 % of ~$171B total assets | Binance (via CNBC) |
| F30 | CZ: "98% choose to stay!" | CZ on X (via CNBC) |
| F31 | ~95 % of affected assets replenished (up from 90 %) as of Nov 1 | Binance (via TechCrunch, CNBC) |
| F32 | Nov 3: more assets re-enabled (Security Incident Recovery Update #6) | Binance (via crypto.news, CryptoTimes) |
| F33 | Binance: ~335M registered users; ~$162.8B assets under custody (2025 annual report) | Reuters |
| F34 | Elliptic: "almost certainly the single largest known theft of any kind" | Elliptic (via Reuters) |
| F35 | EIP-7702 went live with Ethereum's Pectra upgrade in May 2025 | multiple |

### Context
| # | Fact | Source(s) |
|---|---|---|
| C1 | Bybit, Feb 21, 2025, ~$1.5B; FBI → TraderTraitor; breach traced to a compromised Safe{Wallet} developer machine | FBI PSA (Feb 2025); Safe statement |
| C2 | DMM Bitcoin, May 2024, 4,502.9 BTC (~$308M); FBI + Japan's NPA → TraderTraitor; a fake LinkedIn recruiter sent an employee of wallet-software firm Ginco a malicious "pre-employment test" | FBI/DC3/NPA joint statement (Dec 2024) |
| C3 | Bitget, Sep 2026, ~$350M stolen | Reuters |

### 2019 and 2022
| # | Fact | Source(s) |
|---|---|---|
| H1 | May 7, 2019, 17:15:24 UTC; 7,000 BTC (~$40M) in one transaction from the BTC hot wallet (~2 % of BTC holdings); tx `e8b406091959700dbffcff30a60b190133721e5c39e89bb5fe23c5a554ab05ea` | Binance Security Breach Update |
| H2 | Hackers obtained user API keys, 2FA codes and other info via phishing, viruses and other attacks; "had the patience to wait"; multiple seemingly independent accounts; transaction passed existing checks; alarms triggered after execution | Binance Security Breach Update |
| H3 | Reorg idea first suggested by Bitcoin developer Jeremy Rubin; CZ discussed it in a livestream AMA; on May 8, 2019 he decided not to pursue it; tweet: "bitcoin ledger is the most immutable ledger on the planet" | CZ on X; Decrypt; Forklog |
| H4 | SAFU covered the full loss; SAFU created July 2018, funded with 10 % of trading fees | Binance |
| H5 | Deposits and withdrawals reopened May 15, 2019 | The Block; CoinDesk |
| H6 | Oct 6, 2022: BSC Token Hub bridge exploit; 2M BNB (~$570M) created via a forged proof; BNB Chain halted; ~$100–110M moved off-chain | BNB Chain; CZ; The Block |

### Key source links
- AP: https://www.wdbj7.com/2026/10/30/north-korea-linked-63-billion-hack-binance-blockchain-intelligence-firms-say/
- BleepingComputer: https://bleepingcomputer.com/news/security/binance-links-63-billion-crypto-theft-to-compromised-devops-laptop
- Reuters (syndicated): https://virginiabusiness.com/hackers-steal-6-3-billion-binance-north-korea-heist/
- Decrypt — attribution: https://decrypt.co/382224/trm-and-chainalysis-tie-6-4b-binance-hack-to-north-koreas-tradertraitor
- Decrypt — additional points of breach: https://decrypt.co/382203/binance-finds-additional-points-of-breach-in-6-3b-hack
- Gizmodo — EIP-7702: https://gizmodo.com/how-hackers-stole-6-3-billion-from-binance-in-minutes-2000833158
- Protos — on-chain reconstruction: https://protos.com/how-the-binance-hack-happened-on-chain-on-ethereum/
- Stingrai — timeline: https://www.stingrai.io/blog/binance-hack-october-2026
- Cybersecurity Dive — FBI/USSS: https://www.cybersecuritydive.com/news/binance-hack-north-korea-cryptocurrency-theft/873304/
- CBS News — FBI statement + withdrawals: https://www.cbsnews.com/news/binance-crypto-heist-withdrawals/
- CNBC — outflows: https://www.cnbc.com/2026/11/02/binance-outflow-hack-bitcoin.html
- TechCrunch — withdrawals resume: https://techcrunch.com/2026/11/01/binance-resumes-withdrawals-following-6-3-billion-breach/
- CoinDesk — phased withdrawals: https://www.coindesk.com/markets/2026/11/01/binance-opens-crypto-withdrawals-in-phases-starting-with-bitcoin-following-usd6-3-billion-hack
- Bankless: https://www.bankless.com/read/binance-just-suffered-the-biggest-hack-in-crypto-history-what-now.md
- 2019 statement (Bitdefender): https://www.bitdefender.com/en-au/blog/hotforsecurity/40-million-worth-of-bitcoin-stolen-from-binance-cryptocurrency-exchange
- 2019 reorg (Decrypt): https://decrypt.co/6941/binance-ceo-changpeng-zhao-dismisses-idea-to-reorg-bitcoin-blockchain-following-hack
- 2019 reopening (The Block): https://www.theblock.co/post/23501/binance-reopens-withdrawals-and-deposits-a-week-after-41-million-hack-bitcoin
- 2022 bridge (The Block): https://www.theblock.co/post/175437/biance-bnb-chain-is-back-up-after-bridge-exploit
- YouTube — altered or synthetic content: https://support.google.com/youtube/answer/14328491

---
*End of master prompt.*
