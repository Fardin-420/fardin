import React from 'react';
import { AbsoluteFill } from 'remotion';
import { C } from '../theme';
import { SceneData } from '../tl';
import { useF } from '../lib/frame';
import { prog } from '../lib/anim';
import { At, Badge, Center, Counter, Headline, Kicker, QuoteCard, Shot, Shots, SourceTag, Struck, UTCClock } from '../components/core';
import { ChainNetwork, FlowPath, FreezeStamp, HotColdExplainer, KeyGridCollapse, NonceLock, TxCard } from '../components/diagrams1';
import { DossierReveal, GlitchQuestion, TitleCard } from '../components/diagrams2';
import { PlateCity, PlateCoins, PlateCorridor, PlateLaptop, PlateVault } from '../components/plates';
import { AccountsGrid, AlarmVault, BlockRewind, FastCard, FlashbackGrade, FlipTiles, LiveFrame, PhishCard, SafuVault } from '../components/beats';
import { CARD, SceneShell, Snap, helpers } from './shell';

const T2005 = 20 * 3600 + 5 * 60;

const ColdClock: React.FC = () => {
  const f = useF();
  return (
    <Center>
      <UTCClock sec={T2005 + Math.max(0, Math.floor((f - 26) / 30))} size={170} typed={(f - 6) / 2} />
    </Center>
  );
};

/* ================================================================== S01 COLD OPEN */
export const S01: React.FC<{ s: SceneData }> = ({ s }) => {
  const { c, w, D } = helpers(s);
  const th = w('thousands');
  const mi = w('millions');
  const mont = c('montage');
  const shots: Shot[] = [
    { at: 0, el: <ColdClock />, drift: 0.02 },
    { at: c('binance'), el: <ChainNetwork assembleAt={0} igniteAt={16} stagger={4} />, enter: 'zoom' },
    {
      at: th - 4,
      enter: 'glitch',
      el: (
        <Center gap={60} style={{ flexDirection: 'row' }}>
          <Struck text="$1,000" at={0} strikeAt={20} />
          <Struck text="$1,000,000" at={mi - th + 4} strikeAt={mi - th + 22} />
        </Center>
      ),
    },
    {
      at: c('billions'),
      el: (
        <>
          <Center>
            <Counter to={6_300_000_000} at={0} len={Math.max(30, c('total') - c('billions') + 6)} prefix="$" size={210} label="ESTIMATED · MOST OF IT GONE IN ~20 MINUTES" />
          </Center>
          <SourceTag text="ESTIMATES: BINANCE ~$6.3B · TRM LABS ~$6.36B" at={10} />
        </>
      ),
    },
    { at: c('safe'), el: <PlateVault len={c('corridor') - c('safe') + 12} />, enter: 'fade', drift: 0 },
    { at: c('corridor'), el: <PlateCorridor len={c('laptop') - c('corridor') + 12} />, enter: 'fade', drift: 0 },
    { at: c('laptop'), el: <PlateLaptop len={mont - c('laptop') + 10} mode="closed" pulseAt={4} />, enter: 'cut', drift: 0 },
    { at: mont, enter: 'glitch', el: <ChainNetwork assembleAt={-100} igniteAt={-100} stagger={0} flashAt={4} /> },
    { at: w('attackers'), enter: 'glitch', el: <Snap at={160}><FlowPath nodes={[{ label: 'LAPTOP', at: 0 }, { label: 'SERVICE CONTAINER', at: 6 }, { label: 'WITHDRAWALS', at: 12 }, { label: 'HOT WALLETS', at: 18 }, { label: '10 CHAINS', at: 24 }]} /></Snap> },
    { at: w('emptied'), enter: 'glitch', el: <Snap at={10}><NonceLock cardAt={0} slipsAt={-60} matchAt={30} fiftyAt={-10} /></Snap> },
    { at: w('race'), enter: 'glitch', el: <Snap at={20}><FreezeStamp ticker="USDT" amount="971.1M USDT" who="TETHER" time="21:01 UTC" /></Snap> },
    { at: Math.min(w('money', 1) + 6, c('question') - 14), enter: 'glitch', el: <Snap at={60}><DossierReveal /></Snap> },
    { at: c('question'), enter: 'cut', el: <GlitchQuestion at={0} outAt={c('titlecard') - c('question') - 14} /> },
    { at: c('titlecard'), el: <TitleCard />, drift: 0 },
  ];
  return (
    <SceneShell s={s}>
      <Shots shots={shots} end={D} />
      <Badge text="FACTS AS OF NOV 3, 2026 · INVESTIGATION ONGOING" at={4} until={186} />
    </SceneShell>
  );
};

/* ================================================================== S02 THE FORTRESS */
export const S02: React.FC<{ s: SceneData }> = ({ s }) => {
  const { c, w, D } = helpers(s);
  const ex = w("doesn't");
  const shots: Shot[] = [
    {
      at: CARD,
      el: (
        <>
          <PlateCity len={c('users') - CARD + 10} />
          <Center>
            <Headline text="BINANCE" size={230} at={14} sub="THE WORLD'S LARGEST CRYPTO EXCHANGE" />
          </Center>
        </>
      ),
      drift: 0,
    },
    {
      at: c('users'),
      enter: 'zoom',
      el: (
        <>
          <AbsoluteFill style={{ top: -170 }}>
            <Center>
              <Counter to={335_000_000} at={0} len={34} size={170} label="REGISTERED USERS" />
            </Center>
          </AbsoluteFill>
          <AbsoluteFill style={{ top: 190 }}>
            <Center>
              <Counter to={162.8} decimals={1} at={c('custody') - c('users')} len={30} prefix="$" suffix="B" size={150} color={C.bone} label="ASSETS UNDER CUSTODY" />
            </Center>
          </AbsoluteFill>
          <SourceTag text="BINANCE 2025 ANNUAL REPORT, VIA REUTERS" at={8} />
        </>
      ),
    },
    { at: ex, enter: 'fade', el: <HotColdExplainer drawAt={0} vaultAt={c('vault') - ex} registerAt={c('register') - ex} streetAt={c('street') - ex - 30} /> },
    {
      at: c('before') - 16,
      enter: 'glitch',
      el: <FlashbackGrade stamp="MAY 07 2019"><Headline text="IT HAD HAPPENED BEFORE." size={150} /></FlashbackGrade>,
    },
  ];
  return (
    <SceneShell s={s} accent={C.gold}>
      <Shots shots={shots} end={D} />
    </SceneShell>
  );
};

/* ================================================================== S03 THE FIRST HEIST (2019 grade) */
export const S03: React.FC<{ s: SceneData }> = ({ s }) => {
  const { c, w, D } = helpers(s);
  const shots: Shot[] = [
    {
      at: CARD,
      el: (
        <>
          <PlateCoins len={c('7000') - CARD + 10} />
          <Center>
            <Headline text="MAY 7, 2019" size={200} at={c('may2019') - CARD} sub="17:15 UTC" subColor={C.bone} />
          </Center>
        </>
      ),
      drift: 0,
    },
    {
      at: c('7000'),
      enter: 'push',
      el: (
        <>
          <TxCard hash="e8b40609…554ab05ea" />
          <div style={{ position: 'absolute', left: 0, right: 0, top: 640, textAlign: 'center', opacity: 0.9 }}>
            <Kicker size={26} color={C.gold}>≈ $40 MILLION AT THE TIME · ~2% OF ITS BTC HOLDINGS</Kicker>
          </div>
          <SourceTag text="BINANCE SECURITY UPDATE · MAY 7, 2019" at={10} />
        </>
      ),
    },
    { at: c('apikeys'), enter: 'zoom', el: <FlipTiles items={['API KEYS', '2FA CODES', 'OTHER INFO']} /> },
    { at: c('phishing'), enter: 'push', el: <PhishCard /> },
    { at: c('waited'), enter: 'fade', el: <AccountsGrid fireAt={w('striking') - c('waited')} /> },
    { at: c('quote2019'), enter: 'rise', el: <QuoteCard quote="had the patience to wait" who="BINANCE" role="SECURITY BREACH UPDATE" where="MAY 2019" /> },
    { at: c('alarm') - 4, enter: 'flash', el: <AlarmVault /> },
    { at: c('cz') - 12, enter: 'fade', el: <LiveFrame name="CHANGPENG ZHAO (CZ)" role="BINANCE CEO IN 2019 · LIVESTREAM AMA" /> },
    { at: c('rewrite'), enter: 'glitch', el: <BlockRewind /> },
    { at: c('quoteCZ'), enter: 'rise', el: <QuoteCard quote="the most immutable ledger on the planet" who="CHANGPENG ZHAO (CZ)" role="BINANCE CEO" where="MAY 8, 2019" /> },
    { at: c('safu'), enter: 'zoom', el: <SafuVault stampAt={w('week') - c('safu')} /> },
    {
      at: c('2022'),
      enter: 'glitch',
      el: (
        <>
          <FastCard lines={['OCT 2022', 'BNB CHAIN BRIDGE EXPLOIT', '2,000,000 BNB CREATED', 'CHAIN HALTED']} />
          <SourceTag text="BNB CHAIN · OCT 2022" at={8} />
        </>
      ),
    },
    { at: c('lesson'), enter: 'fade', el: <Headline text="THE WEAK POINT IS NEVER THE MATH." size={130} at={w('weak') - c('lesson')} /> },
    { at: c('around'), enter: 'cut', el: <Headline text="IT'S EVERYTHING AROUND IT." size={160} color={C.alarm} /> },
    { at: c('around') + 50, enter: 'fade', el: <KeyGridCollapse at={0} collapseAt={Math.max(20, D - c('around') - 50 - 40)} /> },
  ];
  return (
    <SceneShell s={s} accent={C.gold} grade={(b) => <FlashbackGrade>{b}</FlashbackGrade>}>
      <Shots shots={shots} end={D} />
    </SceneShell>
  );
};

export const _unused = prog;
export { At };
