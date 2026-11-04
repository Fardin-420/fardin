# THE 20-MINUTE HEIST — LOCKED SCRIPT (pending Checkpoint A)

**Facts as of: November 3, 2026 · investigation ongoing.** Narrator: NPC_VOICE_V1.
VO below is final narration. `[[…]]` markers are stripped before TTS. Each Phase-1 change is marked **Δ** and keyed to the ledger ID; all other lines are unchanged from the master prompt §9. VIS/MUS follow the master prompt except where a **VIS Δ** says otherwise.

---

## SCENE 01 — COLD OPEN

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

---

## SCENE 02 — CHAPTER 1: THE FORTRESS

> To understand the size of this, you need to understand Binance.
> It's the world's largest crypto exchange, with around [[CUE:users]]335 million registered users. In its 2025 annual report, it said it held about [[CUE:custody]]162.8 billion dollars in assets under custody.
> An exchange doesn't keep all of that in one place. Think of a store. Most of the money sits in the [[CUE:vault]]vault — cold wallets, kept offline, slow and hard to reach. The rest stays in the [[CUE:register]]cash register — hot wallets — online, so millions of people can withdraw at any second of the day.
> The cash register is convenient. It's also the part of the building that [[PUNCH]]faces the street.
> And Binance already knew what happens when someone reaches into it. Because [[CUE:before]]it had happened before.

---

## SCENE 03 — CHAPTER 2: THE FIRST HEIST (2019 grade)

> [[CUE:may2019]]May 7th, 2019. 17:15 UTC.
> One transaction pulls [[CUE:7000]]seven thousand Bitcoin out of Binance's hot wallet — about forty million dollars at the time.
> Binance later explained how. Hackers had collected a large number of user [[CUE:apikeys]]API keys, two-factor codes and other information — using [[CUE:phishing]]phishing, viruses and other attacks.
> And then they waited. Binance said the hackers [[CUE:quote2019]]"had the patience to wait" — striking through multiple accounts that looked unrelated, with a withdrawal built to pass every security check.
> The alarms fired [[PUNCH]]only after the money was gone.
> Then came the strangest part. In a livestream, Binance's CEO, Changpeng Zhao — [[CUE:cz]]CZ — said the exchange was weighing a radical idea, first floated by a Bitcoin developer: paying miners to [[CUE:rewrite]]rewrite the blockchain and undo the theft.
> The backlash was immediate. Within a day, CZ dropped it, **Δ H3 saying** the Bitcoin ledger is [[CUE:quoteCZ]]"the most immutable ledger on the planet."
> Binance covered the loss from [[CUE:safu]]SAFU — its Secure Asset Fund for Users, funded since 2018 with ten percent of trading fees. A week later, withdrawals were back.
> Three years after that, in [[CUE:2022]]2022, an attacker abused a bug in a bridge on Binance's own BNB Chain to create two million BNB out of thin air — and the chain had to be halted.
> Each time, the lesson was the same. The weak point is never the math. [[PUNCH]]It's everything around it.

**VIS Δ H3:** quote card credit → "CZ · MAY 8, 2019" (venue reported as AMA/statement; not "on X").

---

## SCENE 04 — CHAPTER 3: THE DOOR

> Now — back to October 2026.
> Here's what Binance said at first. Its initial investigation suggested the incident may have started with a [[CUE:laptop2]]compromised laptop belonging to a DevOps engineer — one of the people who build and run the machinery behind the exchange. **(Δ F3/F6 tense: "has said… suggests" → "said at first… suggested", because the Nov 3 report adds more.)**
> From that laptop, an attacker reached what Binance calls a [[CUE:container]]"service container" — part of its internal infrastructure — and from there, submitted [[CUE:unauth]]unauthorized withdrawal transactions.
> Hours later, Binance said it had found [[CUE:additional]]additional points of breach. Co-CEO Richard Teng put it bluntly: this was not a single [[CUE:oneclick]]"one-click" action. The attacker did not simply use one engineer's permissions.
> And it was planned. According to blockchain analysts at TRM Labs, staging began at least [[CUE:36h]]thirty-six hours earlier, with small withdrawals from the crypto mixer Tornado Cash funding the attacker's operating wallet.
> **Δ F8 — CUT:** ~~On-chain reconstructions suggest the attacker even rehearsed on test wallets.~~
> Investigators believe the attackers didn't need to steal the keys. They got Binance's [[PUNCH]]own systems to sign for them.
> So how do you turn a laptop into six billion dollars?
> [[CUE:20min]]You give yourself twenty minutes.

**VIS Δ F8:** `[[CUE:rehearse]]` TEST WALLET beat removed.

---

## SCENE 05 — CHAPTER 4: THE 20 MINUTES

> [[CUE:t2005]]8:05 PM. The first funds start moving — **Δ F13** [[CUE:xrp]]on the XRP Ledger, where analysts tracking the theft count about 296 million dollars drained in the first four minutes.
> Binance wallets on ten networks begin sending money out — Bitcoin, Ethereum, Tron, the XRP Ledger, Solana, and more. On nine of those chains, it looks almost normal: [[CUE:ordinary]]ordinary transfers, signed by Binance's own wallets.
> [[PUNCH]]Ethereum is different.
> At [[CUE:t2020]]**Δ F9** 8:20, one transaction targets a Binance hot wallet labeled [[CUE:b14]]"Binance 14." Inside it: [[CUE:fifty]]fifty authorizations — all signed with Binance 14's own key — using an Ethereum feature called [[CUE:eip]]EIP-7702, which lets a wallet hand its powers to a piece of code.
> Why fifty? Every wallet keeps a running count of its transactions. An authorization only works if it matches the right number — and the attacker didn't know which number Binance 14 was on. So they brought fifty signed permission slips, one for every possible number.
> [[IMPACT]][[CUE:onefit]]Exactly one matched. [[SILENCE]]
> In that moment, Binance 14 stopped being Binance's wallet. It was running the attacker's [[CUE:sweeper]]sweeper code.
> In under four minutes, it emptied — about [[CUE:eth167]]167,000 ETH, roughly 1.6 billion USDT, and dozens of other tokens.
> By TRM's count, Ethereum alone accounted for about [[CUE:eth38]]3.8 billion dollars. On Bitcoin: [[CUE:btc18]]18,270 BTC — around 1.47 billion more.
> Most of it was gone in about twenty minutes.
> And then, around 11 PM, a [[CUE:wave2]]second wave hit — on Avalanche and Polygon.

**VIS Δ F13:** XRP Ledger node ignites first with "~233.5M XRP · ~$296M · 20:05–20:09 UTC", SourceTag "TRM LABS, VIA CRYPTOSLATE". **VIS Δ F9:** HUD flashes "20:20 UTC" (not 20:20:59).

---

## SCENE 06 — CHAPTER 5: THE RACE TO FREEZE

> While the money moved, a race began.
> Some crypto can be frozen. [[CUE:stables]]Stablecoins like USDT and USDC are issued by companies — and those companies can lock tokens sitting in a specific wallet.
> At [[CUE:t2101]]9:01 PM, Tether froze about 971 million USDT in the attacker's main receiving wallet. Three minutes later, [[CUE:t2104]]Circle froze 823 million USDC.
> **Δ F14** [[CUE:t2124]]Soon after, Binance posted publicly for the first time: it was aware of "a potential security issue."
> **Δ F14** [[CUE:t2125]]Tether's CEO said more than 1.5 billion dollars in USDT was frozen. [[CUE:others]]Ripple froze its stablecoin. World Liberty Financial froze theirs.
> **Δ F14/F15** Later that night, Binance [[CUE:suspend]]suspended all deposits and withdrawals — and promised to cover every loss. In the same minutes, Arbitrum's Security Council moved about 30 million dollars in ETH and ARB out of the attacker's reach.
> **Δ F16** Binance now says about [[CUE:frozen3]]2.85 billion dollars has been frozen or intercepted. Independent trackers land close — Elliptic, 2.84 billion; TRM, around 2.7.
> But Bitcoin and Ether [[PUNCH]]have no company that can freeze them. And the attacker kept moving — [[CUE:dump]]selling about 325 million USDT to market makers at a discount of more than ten percent, and using USDT on the lending platform [[CUE:aave]]Aave to borrow ether.
> As of TRM's latest analysis, the attacker still holds more than [[CUE:remain]]420,000 ETH and 18,270 BTC — about 2.4 billion dollars that no issuer can freeze — with the Bitcoin splitting into a long chain of [[CUE:peel]]smaller and smaller transfers.

**VIS Δ F14:** QuoteCard "a potential security issue" credit → "BINANCE ON X · OCT 29, 2026" (no minute). Counter → "1.5B+ USDT FROZEN · TETHER CEO". Suspension wash → "OCT 29–30 · ALL DEPOSITS & WITHDRAWALS SUSPENDED" (00:13 pending a primary source).
**VIS Δ F15/F15b:** stamps → "40.5M RLUSD · RIPPLE (TRM)" · "27.8M USD1 · WORLD LIBERTY FINANCIAL" · "~$30M ETH + ARB · ARBITRUM SECURITY COUNCIL · 00:08–00:18 UTC".
**VIS Δ F16:** bars → "BINANCE ~$2.85B" · "ELLIPTIC $2.84B" · "TRM ~$2.7B".

---

## SCENE 07 — CHAPTER 6: THE NAME

> By the next morning, investigators had a name.
> TRM Labs attributed the attack "with high confidence" to [[IMPACT]][[CUE:tt]]TraderTraitor — a North Korean state-backed hacking unit, widely described as part of the Lazarus Group. Chainalysis reached the same conclusion, after seeing funds from September's [[CUE:bitget]]Bitget hack mixed with funds stolen from Binance. Elliptic agreed. Then [[CUE:fbi]]the FBI said it publicly: North Korea was responsible. **(Δ F19 wording: "linking the funds to" → "after seeing funds… mixed with")**
> **Δ F21/F22** North Korea denies it. In a statement carried by state media, Kim Yo Jong — Kim Jong Un's sister — called the accusations [[CUE:deny]]"absurd rhetoric." Binance says it's working with law enforcement to confirm who the attackers are.
> If TraderTraitor sounds familiar, it should. In February 2025, the FBI blamed the same group for the hack of [[CUE:bybit]]Bybit — about 1.5 billion dollars, the record until now. In that case, the breach was traced to a compromised developer machine at Safe, the wallet software Bybit relied on.
> In 2024, Japan's [[CUE:dmm]]DMM Bitcoin lost about 300 million dollars. According to the FBI and Japanese police, it began when a fake recruiter sent an employee at a partner company a malicious "pre-employment test."
> [[CUE:playbook]]Fake job offers. Poisoned code. Trusted machines turned into doorways. It's a playbook security agencies have warned about for years.
> **Δ F6** ~~To be clear: Binance has not said how its engineer's laptop was compromised.~~ → Keep that first one in mind. [[CUE:remember]]Fake job offers. We'll come back to it.
> But TRM says this attack fits the pattern — staging well before the theft, Tornado Cash funding, and signatures collected in advance… then [[PUNCH]]fired in one burst.

**VIS Δ F20:** FBI card — "North Korea was responsible for the theft of more than $6 billion" — FBI · NOV 1, 2026.
**VIS Δ F21:** text card "NORTH KOREA DENIES INVOLVEMENT" + quote "absurd rhetoric" — KIM YO JONG, VIA KCNA · NOV 3, 2026 (name card only; no image of any person).
**VIS Δ C3:** HeistTimeline Bitget bar → "BITGET · SEP 2026 · $352M+".
**VIS Δ F6:** PlaybookCards footer → "DOCUMENTED TACTICS (FBI, CISA)". On `[[CUE:remember]]` the FAKE JOB OFFERS card stays lit in `alarm` while the others dim.

---

## SCENE 08 — CHAPTER 7: THE MORNING AFTER

> Markets felt it. [[CUE:btclow]]Bitcoin slid to a six-week low near 76,400 dollars. Ether hit a two-month low. BNB fell about five percent, and shares of Coinbase and Strategy dropped in after-hours trading. **(Δ F27: "more than five" → "about five")**
> Binance's answer echoed 2019: customers won't pay for this. It said it had set aside about [[CUE:634]]6.34 billion dollars to cover the losses — far more than its SAFU emergency fund, which reportedly holds around one billion. Co-CEO Richard Teng wrote, [[CUE:teng]]"Our users will not bear the financial impact of this incident." Founder CZ — who stepped down as CEO in 2023 — said that as a shareholder, he expected every user to be made whole. **(Δ F24 "reportedly"; Δ F25 new quote)**
> On Sunday, November 1st, [[CUE:withdraw]]withdrawals started coming back in phases — Bitcoin first. That day, users pulled out about 4.65 billion dollars and deposited about 1.01 billion. [[CUE:net]]Net outflow: 3.64 billion — which Binance says is 2.1 percent of its total assets. CZ's takeaway: [[CUE:98]]"98% choose to stay."
> By then, Binance said it had replenished about [[CUE:95]]95 percent of the affected assets — and was still buying the rest.

**VIS Δ F27:** ticker "BNB ~−5%". **VIS Δ F25:** QuoteCard → "Our users will not bear the financial impact of this incident." — RICHARD TENG, BINANCE CO-CEO, ON X. **VIS Δ F30:** QuoteCard "98% choose to stay." — CZ ON X · NOV 1, 2026.

---

## SCENE 09 — CHAPTER 8: THE QUESTION  *(Δ F6 — the reveal)*

> And yet, the biggest questions are only starting to get answers.
> [[CUE:q1]]How did the attackers get in?
> On November 3rd, Binance gave its first answer. In September, a recruiter on a job platform approached one of its engineers. There was a video interview with "HR"… then one with the "CEO" of a company that didn't exist… and finally, a [[PUNCH]][[CUE:assignment]]take-home coding assignment.
> [[CUE:q2]]The other points of breach? Binance says the attackers used that engineer's computer — and an internal AI tool — to reach colleagues' machines, until they found a [[CUE:token]]token that let them deploy code into the wallet system.
> [[CUE:q3]]Exactly how that became fifty valid signatures — with no evidence, Binance says, of a leaked private key — will have to wait for the full technical report.
> [[CUE:q4]]And the billions in Bitcoin and Ether that no issuer can freeze — will any of it ever come back?
> In [[CUE:y2019]]2019, hackers phished their way into user accounts and took forty million dollars.
> In [[CUE:y2026]]2026, investigators believe the attackers turned the exchange's own machinery against it — and moved [[PUNCH]]more than a hundred and fifty times as much.
> [[SILENCE]]The money moved in twenty minutes.
> [[CUE:years]]The investigation could take years.

**VIS Δ:** QuestionCards stamps → q1 "ANSWERED · BINANCE, NOV 3" · q2 "PARTLY ANSWERED" · q3 "PENDING POST-MORTEM" · q4 "UNKNOWN".
Reveal visuals (all fictional, story-level): generic job-platform message card (labeled "FICTIONAL COMPANY" — no real brand or name); two faceless video-call tiles labeled "HR" and "CEO" that glitch to "FICTITIOUS COMPANY"; a folder icon "assignment/" turning `alarm`; then a simple node graph — ENGINEER B'S LAPTOP → INTERNAL AI TOOL → COLLEAGUES' MACHINES → DEPLOY TOKEN → WALLET SYSTEM — with footer "SIMPLIFIED · BINANCE INITIAL INCIDENT REPORT, NOV 3, 2026". No code, no commands, no repository names. Engineers are never identified (letters only, as in Binance's own report).
The q1 answer closes the loop on Scene 07's `[[CUE:remember]]`: the FAKE JOB OFFERS card flies back in and stamps onto q1.

---

## SCENE 10 — OUTRO: WHAT IT MEANS FOR YOU

> So what does this mean for you?
> Any money you keep on an exchange is protected by their security — not yours. [[CUE:tip1]]Use the strongest two-factor you can, like a hardware key or a passkey. [[CUE:tip2]]Turn on withdrawal address whitelists. [[CUE:tip3]]Don't keep more on an exchange than you need to trade.
> And if you work in tech or crypto: treat surprise job offers and take-home [[CUE:tip4]]"coding tests" from strangers like a live wire. **Δ F6** Investigators have seen that door used again and again — and Binance says it was used this time.
> This story isn't over. [[CUE:sub]]Subscribe so you don't miss what the investigation finds next — and tell me in the comments: should exchanges keep billions in wallets that are online at all?

---

## Notes for Checkpoint A
- Spec rule "at most one short new beat": the only new beat is the Scene 09 reveal (≈95 words, replacing the old q1–q3 lines). The Scene 05 XRP clause and Scene 07 denial line are fact patches to existing lines.
- `[[CUE:xrp]]`, `[[CUE:deny]]`, `[[CUE:remember]]`, `[[CUE:assignment]]`, `[[CUE:token]]` are new cues; `[[CUE:rehearse]]` is removed.
