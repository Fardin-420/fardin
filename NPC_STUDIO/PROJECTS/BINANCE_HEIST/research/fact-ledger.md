# Fact Ledger — THE 20-MINUTE HEIST

Baseline imported verbatim from BINANCE_HEIST_MASTER_PROMPT.md §14 (as of Nov 3, 2026).
Status column is added in Phase 1: VERIFIED / UPDATED / SOFTENED / CUT. Nothing here may reach VO or screen until verified.

## Baseline ledger

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
