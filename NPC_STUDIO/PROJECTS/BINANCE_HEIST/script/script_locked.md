# THE 20-MINUTE HEIST — LOCKED SCRIPT (approved, tightened)

**Facts as of: November 3, 2026 · investigation ongoing.** Narrator: Space Secrets brand voice (Kokoro-82M `am_puck`).
Approved at Checkpoint A; tightened by ~150 words (Scenes 03, 06, plus small trims) with no facts removed. The Checkpoint-A version is kept at `script_locked_v1_checkpointA.md`; all fact deltas are in `research/changelog.md`.

**Machine-read format** (parsed by `scripts/build_vo.py`): each `## SCENE` heading carries `{speed=…}` (the scene's default Kokoro speed). Lines starting with `> ` are narration. Markers are stripped before TTS:
`[[CUE:name]]` (cue on the next word) · `[[PUNCH]]` · `[[IMPACT]]` · `[[SILENCE]]` (1.0 s gap) · `[[SLOW]]` at the start of a sentence (speed 0.87, reveals) · `…` (500 ms gap). Sentence gaps are 250–400 ms.

---

## SCENE 01 — COLD OPEN {speed=0.91}

> [[CUE:clock]]October 29th, 2026. 8:05 PM, UTC.
> On ten blockchains, within minutes, money starts leaving [[CUE:binance]]Binance — the biggest crypto exchange on Earth.
> [[SLOW]]Not thousands. [[SLOW]]Not millions.
> [[SLOW]][[IMPACT]][[CUE:billions]]Billions. [[SILENCE]]
> Within about twenty minutes, most of an estimated [[CUE:total]]six point three billion dollars is gone.
> [[CUE:safe]]Nobody cracked a safe. Binance says it has found no evidence that a single private key was leaked.
> [[CUE:corridor]]Instead, its first investigation pointed somewhere far more ordinary…
> [[SLOW]][[PUNCH]][[CUE:laptop]]an engineer's laptop. [[SILENCE]]
> [[CUE:montage]]This is the story of the biggest crypto heist ever recorded — how the attackers got in, how they emptied the wallets, the race to freeze the money…
> [[SLOW]]and the one question [[CUE:question]]nobody can answer yet.

## SCENE 02 — CHAPTER 1: THE FORTRESS {speed=0.92}

> To understand the size of this, you need to understand Binance.
> It's the world's largest crypto exchange, with around [[CUE:users]]335 million registered users. In its 2025 annual report, it said it held about [[CUE:custody]]162.8 billion dollars in assets under custody.
> An exchange doesn't keep all of that in one place. [[CUE:store]]Think of a store. Most of the money sits in the [[CUE:vault]]vault — cold wallets, kept offline, slow and hard to reach. The rest stays in the [[CUE:register]]cash register — hot wallets — online, so people can withdraw at any second.
> The cash register is convenient. It's also the part of the building that [[PUNCH]][[CUE:street]]faces the street.
> And Binance already knew what happens when someone reaches into it. [[SLOW]]Because [[CUE:before]]it had happened before.

## SCENE 03 — CHAPTER 2: THE FIRST HEIST {speed=0.92}

> [[CUE:may2019]]May 7th, 2019. 17:15 UTC.
> One transaction pulls [[CUE:7000]]seven thousand Bitcoin out of Binance's hot wallet — about forty million dollars at the time.
> Binance later explained: hackers had collected user [[CUE:apikeys]]API keys, two-factor codes and other information — through [[CUE:phishing]]phishing, viruses and other attacks.
> [[CUE:waited]]Then they waited. Binance said the hackers [[CUE:quote2019]]"had the patience to wait" — striking through seemingly unrelated accounts, with a withdrawal built to pass every security check.
> [[SLOW]]The alarms fired [[PUNCH]][[CUE:alarm]]only after the money was gone.
> In a livestream, CEO Changpeng Zhao — [[CUE:cz]]CZ — said Binance was considering an idea first raised by a Bitcoin developer: paying miners to [[CUE:rewrite]]rewrite the blockchain and undo the theft.
> The backlash was immediate. Within a day, CZ dropped it, saying the Bitcoin ledger is [[CUE:quoteCZ]]"the most immutable ledger on the planet."
> Binance covered the loss from [[CUE:safu]]SAFU — its Secure Asset Fund for Users, funded since 2018 with ten percent of trading fees. A week later, withdrawals were back.
> In [[CUE:2022]]2022, an attacker abused a bridge bug on Binance's own BNB Chain to create two million BNB out of thin air — and the chain was halted.
> [[CUE:lesson]]Each time, the lesson was the same. The weak point is never the math. [[SLOW]][[PUNCH]][[CUE:around]]It's everything around it.

## SCENE 04 — CHAPTER 3: THE DOOR {speed=0.92}

> [[CUE:back]]Now — back to October 2026.
> Binance's initial investigation suggested the incident may have started with a [[CUE:laptop2]]compromised laptop belonging to a DevOps engineer — one of the people who build and run the machinery behind the exchange.
> From that laptop, an attacker reached what Binance calls a [[CUE:container]]"service container" — part of its internal infrastructure — and from there, submitted [[CUE:unauth]]unauthorized withdrawal transactions.
> Hours later, Binance said it had found [[CUE:additional]]additional points of breach. Co-CEO Richard Teng put it bluntly: this was not a single [[CUE:oneclick]]"one-click" action. The attacker did not simply use one engineer's permissions.
> And it was planned. According to blockchain analysts at TRM Labs, staging began at least [[CUE:36h]]thirty-six hours earlier, with small withdrawals from the crypto mixer Tornado Cash funding the attacker's operating wallet.
> [[CUE:nokeys]]Investigators believe the attackers didn't need to steal the keys. They got Binance's [[PUNCH]][[CUE:sign]]own systems to sign for them.
> [[CUE:how]]So how do you turn a laptop into six billion dollars?
> [[SLOW]][[CUE:20min]]You give yourself twenty minutes.

## SCENE 05 — CHAPTER 4: THE 20 MINUTES {speed=0.95}

> [[CUE:t2005]]8:05 PM. The first funds start moving — [[CUE:xrp]]on the XRP Ledger, where analysts count about 296 million dollars drained in the first four minutes.
> Ten networks follow — Bitcoin, Ethereum, Tron, Solana, and more. On nine of them, it looks almost normal: [[CUE:ordinary]]ordinary transfers, signed by Binance's own wallets.
> [[PUNCH]][[CUE:ethdiff]]Ethereum is different.
> At [[CUE:t2020]]8:20, one transaction targets a Binance hot wallet labeled [[CUE:b14]]"Binance 14." Inside it: [[CUE:fifty]]fifty authorizations — all signed with Binance 14's own key — using an Ethereum feature called [[CUE:eip]]EIP-7702, which lets a wallet hand its powers to a piece of code.
> [[CUE:why]]Why fifty? Every wallet keeps a running count of its transactions. An authorization only works if it matches the right number — and the attacker didn't know which number Binance 14 was on. [[CUE:slips]]So they brought fifty signed permission slips, one for every possible number.
> [[SLOW]][[IMPACT]][[CUE:onefit]]Exactly one matched. [[SILENCE]]
> In that moment, Binance 14 stopped being Binance's wallet. It was running the attacker's [[CUE:sweeper]]sweeper code.
> In under four minutes, it emptied — about [[CUE:eth167]]167,000 ETH, roughly 1.6 billion USDT, and dozens of other tokens.
> By TRM's count, Ethereum alone accounted for about [[CUE:eth38]]3.8 billion dollars. On Bitcoin: [[CUE:btc18]]18,270 BTC — around 1.47 billion more.
> [[CUE:gone]]Most of it was gone in about twenty minutes.
> And then, around 11 PM, a [[CUE:wave2]]second wave hit — on Avalanche and Polygon.

## SCENE 06 — CHAPTER 5: THE RACE TO FREEZE {speed=0.95}

> While the money moved, [[CUE:race]]a race began.
> Some crypto can be frozen. [[CUE:stables]]Stablecoins like USDT and USDC are issued by companies that can lock tokens in a specific wallet.
> At [[CUE:t2101]]9:01 PM, Tether froze about 971 million USDT in the attacker's main receiving wallet. Three minutes later, [[CUE:t2104]]Circle froze 823 million USDC.
> [[CUE:t2124]]Soon after, Binance posted for the first time: it was aware of "a potential security issue."
> [[CUE:t2125]]Tether's CEO said more than 1.5 billion dollars in USDT was frozen. [[CUE:others]]Ripple and World Liberty Financial froze their stablecoins too.
> That night, Binance [[CUE:suspend]]suspended withdrawals and promised to cover every loss. [[CUE:arb]]Just after midnight UTC, Arbitrum's Security Council moved about 30 million dollars in ETH and ARB out of the attacker's reach.
> Binance now says about [[CUE:frozen3]]2.85 billion dollars has been frozen or intercepted. Elliptic counts 2.84 billion; TRM, around 2.7.
> But Bitcoin and Ether [[PUNCH]][[CUE:nofreeze]]have no company that can freeze them. And the attacker kept moving — [[CUE:dump]]selling about 325 million USDT to market makers at more than a ten percent discount, and borrowing ether against USDT on [[CUE:aave]]Aave.
> As of TRM's latest analysis, the attacker still holds more than [[CUE:remain]]420,000 ETH and 18,270 BTC — about 2.4 billion dollars beyond any freeze — the Bitcoin splitting into [[CUE:peel]]smaller and smaller transfers.

## SCENE 07 — CHAPTER 6: THE NAME {speed=0.92}

> [[CUE:name]]By the next morning, investigators had a name.
> TRM Labs attributed the attack "with high confidence" to [[IMPACT]][[CUE:tt]]TraderTraitor — a North Korean state-backed hacking unit, widely described as part of the Lazarus Group.
> Chainalysis reached the same conclusion, after seeing funds from September's [[CUE:bitget]]Bitget hack mixed with funds stolen from Binance. Elliptic agreed. Then [[CUE:fbi]]the FBI said it publicly: North Korea was responsible.
> North Korea denies it. In a statement carried by state media, Kim Yo Jong — Kim Jong Un's sister — called the accusations [[CUE:deny]]"absurd rhetoric." [[CUE:lawenf]]Binance says it's working with law enforcement to confirm who the attackers are.
> If TraderTraitor sounds familiar, it should. In February 2025, the FBI blamed the same group for the hack of [[CUE:bybit]]Bybit — about 1.5 billion dollars, the record until now. That breach was traced to a compromised developer machine at Safe, the wallet software Bybit relied on.
> In 2024, Japan's [[CUE:dmm]]DMM Bitcoin lost about 300 million dollars. According to the FBI and Japanese police, it began when a fake recruiter sent an employee at a partner company a malicious "pre-employment test."
> [[CUE:playbook]]Fake job offers. Poisoned code. Trusted machines turned into doorways. It's a playbook security agencies have warned about for years.
> [[SLOW]][[CUE:remember]]Remember that first one. We'll come back to it.
> [[CUE:pattern]]TRM says this attack fits the pattern — staging well before the theft, Tornado Cash funding, and signatures collected in advance…
> [[SLOW]]then [[PUNCH]][[CUE:burst]]fired in one burst.

## SCENE 08 — CHAPTER 7: THE MORNING AFTER {speed=0.92}

> [[CUE:markets]]Markets felt it. [[CUE:btclow]]Bitcoin slid to a six-week low near 76,400 dollars. Ether hit a two-month low. BNB fell about five percent, and shares of Coinbase and Strategy dropped in after-hours trading.
> Binance's answer echoed 2019: customers won't pay for this. It said it had set aside about [[CUE:634]]6.34 billion dollars to cover the losses — far more than its SAFU emergency fund, which reportedly holds around one billion.
> Co-CEO Richard Teng wrote, [[CUE:teng]]"Our users will not bear the financial impact of this incident." [[CUE:czcard]]Founder CZ — who stepped down as CEO in 2023 — said that as a shareholder, he expected every user to be made whole.
> On Sunday, November 1st, [[CUE:withdraw]]withdrawals started coming back in phases — Bitcoin first. That day, users pulled out about 4.65 billion dollars and deposited about 1.01 billion.
> [[CUE:net]]Net outflow: 3.64 billion — which Binance says is 2.1 percent of its total assets. CZ's takeaway: [[CUE:98]]"98% choose to stay."
> By then, Binance said it had replenished about [[CUE:95]]95 percent of the affected assets — and was still buying the rest.

## SCENE 09 — CHAPTER 8: THE QUESTION {speed=0.91}

> And yet, the biggest questions are only starting to get answers.
> [[SLOW]][[CUE:q1]]How did the attackers get in?
> [[CUE:nov3]]On November 3rd, Binance gave its first answer. In September, a recruiter on a job platform approached one of its engineers.
> [[CUE:hr]]There was a video interview with "HR"… then one with the [[CUE:ceo]]"CEO" of a company that didn't exist…
> [[SLOW]]and finally, a [[PUNCH]][[CUE:assignment]]take-home coding assignment.
> [[CUE:q2]]The other points of breach? Binance says the attackers used that engineer's computer — and an [[CUE:aitool]]internal AI tool — to reach colleagues' machines, until they found a [[CUE:token]]token that let them deploy code into the wallet system.
> [[CUE:q3]]Exactly how that became fifty valid signatures — with no evidence, Binance says, of a leaked private key — will have to wait for the full technical report.
> [[CUE:q4]]And the billions in Bitcoin and Ether that no issuer can freeze — will any of it ever come back?
> In [[CUE:y2019]]2019, hackers phished their way into user accounts and took forty million dollars.
> In [[CUE:y2026]]2026, investigators believe the attackers turned the exchange's own machinery against it — and moved [[PUNCH]]more than a hundred and fifty times as much. [[SILENCE]]
> [[SLOW]][[CUE:moved]]The money moved in twenty minutes.
> [[SLOW]][[CUE:years]]The investigation could take years. [[SILENCE]]

## SCENE 10 — OUTRO: WHAT IT MEANS FOR YOU {speed=0.92}

> So what does this mean for you?
> Any money you keep on an exchange is protected by their security — not yours. [[CUE:tip1]]Use the strongest two-factor you can, like a hardware key or a passkey. [[CUE:tip2]]Turn on withdrawal address whitelists. [[CUE:tip3]]Don't keep more on an exchange than you need to trade.
> And if you work in tech or crypto: treat surprise job offers and take-home [[CUE:tip4]]"coding tests" from strangers like a live wire. Investigators have seen that door used again and again — and Binance says it was used this time.
> This story isn't over. [[CUE:sub]]Subscribe so you don't miss what the investigation finds next — and tell me in the comments: should exchanges keep billions in wallets that are online at all?

---

## Visual deltas carried from Checkpoint A (applied in the edit)
- S03 CZ quote credit "CZ · MAY 8, 2019". S04 TEST WALLET beat removed. S05 XRP node first (~233.5M XRP · ~$296M · 20:05–20:09 UTC); HUD "20:20 UTC".
- S06: "a potential security issue" — BINANCE ON X · OCT 29, 2026 · "1.5B+ USDT FROZEN" · "OCT 29 · WITHDRAWALS SUSPENDED" (minute unconfirmed; deposits later clarified unaffected) · "40.5M RLUSD · RIPPLE (TRM)" · "27.8M USD1 · WORLD LIBERTY FINANCIAL" · "~$30M ETH + ARB · ARBITRUM SECURITY COUNCIL · 00:08–00:18 UTC" · frozen bars BINANCE ~$2.85B / ELLIPTIC $2.84B / TRM ~$2.7B.
- S07: FBI card "North Korea was responsible for the theft of more than $6 billion" — FBI · NOV 1, 2026 · denial card "absurd rhetoric" — KIM YO JONG, VIA KCNA · NOV 3, 2026 (text only) · Bitget bar "$352M+" · Playbook footer "DOCUMENTED TACTICS (FBI, CISA)".
- S08: ticker "BNB ~−5%"; Teng quote on X; "98% choose to stay." — CZ ON X · NOV 1, 2026. Price beat uses sourced lows only (no live price API reachable — see changelog).
- S09: QuestionCards q1 ANSWERED · BINANCE, NOV 3 / q2 PARTLY ANSWERED / q3 PENDING POST-MORTEM / q4 UNKNOWN; reveal graph footer "SIMPLIFIED · BINANCE INITIAL INCIDENT REPORT, NOV 3, 2026"; engineers never identified.
