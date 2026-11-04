import React from 'react';
import { AbsoluteFill, interpolate } from 'remotion';
import { C } from '../theme';
import { SceneData } from '../tl';
import { useF } from '../lib/frame';
import { prog } from '../lib/anim';
import { Center, Counter, Headline, Kicker, LowerThird, QuoteCard, Shot, Shots, SourceTag, Stamp, UTCClock } from '../components/core';
import { CHAINS, ChainNetwork, FlowPath, FreezeStamp, NonceLock, SweepVortex, TimelineRail } from '../components/diagrams1';
import { Bars, PeelChain } from '../components/diagrams2';
import { PlateIce, PlateKeyboard, PlateMonitors, PlateVortexBg } from '../components/plates';
import { AlarmWash, CalendarDrip, Countdown, FlowLines, LaptopToBillions, MeltThrough, RaceSplit, SignatureCard, StableSplit } from '../components/beats';
import { CARD, SceneShell, helpers } from './shell';

/* ================================================================== S04 THE DOOR */
export const S04: React.FC<{ s: SceneData }> = ({ s }) => {
  const { c, D } = helpers(s);
  const l2 = c('laptop2');
  const shots: Shot[] = [
    {
      at: CARD,
      el: (
        <>
          <PlateKeyboard len={l2 - CARD + 10} />
          <Center>
            <Headline text="OCTOBER 2026" size={210} at={c('back') - CARD} />
          </Center>
        </>
      ),
      drift: 0,
    },
    {
      at: l2,
      enter: 'zoom',
      el: (
        <FlowPath
          nodes={[
            { label: 'LAPTOP', sub: 'DevOps engineer', at: 0 },
            { label: 'SERVICE CONTAINER', sub: 'internal infrastructure', at: c('container') - l2 },
            { label: 'UNAUTHORIZED WITHDRAWALS', sub: 'transactions submitted', at: c('unauth') - l2 },
            { label: 'HOT WALLETS', at: c('unauth') - l2 + 22 },
            { label: '10 CHAINS', at: c('unauth') - l2 + 36, color: C.alarm },
          ]}
          footer="SIMPLIFIED ILLUSTRATION — BINANCE PRELIMINARY FINDINGS, OCT 30, 2026"
          footerAt={10}
          breachAt={c('additional') - l2}
        />
      ),
    },
    { at: c('oneclick') - 6, enter: 'rise', el: <QuoteCard quote="not a single 'one-click' action" who="RICHARD TENG" role="BINANCE CO-CEO" where="OCT 30, 2026" accent={C.alarm} /> },
    {
      at: c('36h') - 8,
      enter: 'push',
      el: (
        <>
          <CalendarDrip />
          <SourceTag text="TRM LABS · CHAINALYSIS" at={12} />
        </>
      ),
    },
    {
      at: c('nokeys'),
      enter: 'glitch',
      el: (
        <Center>
          <Stamp text="PRIVATE KEY LEAK: NO EVIDENCE FOUND" sub="— BINANCE" at={6} color={C.ice} size={88} rotate={-3} />
        </Center>
      ),
    },
    { at: c('sign') - 10, enter: 'zoom', el: <SignatureCard /> },
    { at: c('how'), enter: 'fade', el: <LaptopToBillions /> },
    { at: c('20min'), enter: 'cut', el: <Countdown /> },
  ];
  return (
    <SceneShell s={s}>
      <Shots shots={shots} end={D} />
    </SceneShell>
  );
};

/* ================================================================== S05 THE 20 MINUTES */
const HUD: React.FC<{ s: SceneData; keys: [number, number][] }> = ({ keys }) => {
  const f = useF();
  const sec = interpolate(f, keys.map((k) => k[0]), keys.map((k) => k[1]), { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const flash = keys.some(([kf]) => f >= kf && f < kf + 24) && f > keys[0][0];
  const vis = prog(f, CARD, 12);
  return (
    <AbsoluteFill style={{ opacity: vis, pointerEvents: 'none' }}>
      <div style={{ position: 'absolute', right: 96, top: 46 }}>
        <UTCClock sec={sec} size={56} flash={flash} />
      </div>
      <TimelineRail t={Math.min(sec, 20 * 3600 + 25 * 60)} y={64} events={[{ t: 20 * 3600 + 5 * 60, label: '' }, { t: 20 * 3600 + 20 * 60 + 59, label: '' }, { t: 20 * 3600 + 25 * 60, label: '' }]} />
    </AbsoluteFill>
  );
};

export const S05: React.FC<{ s: SceneData }> = ({ s }) => {
  const { c, w, D } = helpers(s);
  const t0 = c('t2005');
  const ten = w('Ten');
  const all: Record<string, number> = {};
  CHAINS.forEach((n) => (all[n] = -100));
  const igm: Record<string, number> = { 'XRP Ledger': c('xrp') - t0 };
  CHAINS.filter((n) => n !== 'XRP Ledger').forEach((n, i) => (igm[n] = ten - t0 + i * 6));
  const keys: [number, number][] = [
    [t0, 20 * 3600 + 5 * 60],
    [c('t2020'), 20 * 3600 + 20 * 60 + 59],
    [c('gone'), 20 * 3600 + 25 * 60],
    [c('wave2') - 1, 20 * 3600 + 25 * 60],
    [c('wave2'), 23 * 3600 + 5 * 60],
    [D, 23 * 3600 + 5 * 60 + Math.round((D - c('wave2')) / 30) * 9],
  ];
  const b14 = c('t2020');
  const shots: Shot[] = [
    {
      at: CARD,
      el: (
        <>
          <ChainNetwork
            assembleAt={0}
            igniteMap={igm}
            sealsAt={c('ordinary') - CARD}
            sealSkip={['Ethereum']}
            note={{ node: 'XRP Ledger', text: '~$296M', sub: '~233.5M XRP · 20:05–20:09 UTC', at: c('xrp') - CARD + 10 }}
          />
          <SourceTag text="TRM LABS, VIA CRYPTOSLATE" at={c('xrp') - CARD + 14} until={ten - CARD} />
        </>
      ),
    },
    { at: c('ethdiff'), el: <ChainNetwork assembleAt={-100} igniteMap={all} zoom={{ node: 'Ethereum', at: 0 }} particles />, drift: 0 },
    {
      at: b14,
      enter: 'zoom',
      el: (
        <>
          <NonceLock cardAt={0} fiftyAt={c('fifty') - b14} spinAt={c('why') - b14} slipsAt={c('slips') - b14} matchAt={c('onefit') - b14} />
          <ShowBetween from={c('eip') - b14} to={c('why') - b14 + 40}>
            <LowerThird title="EIP-7702" body="Lets a wallet delegate its behavior to smart-contract code (live on Ethereum since May 2025)" />
          </ShowBetween>
        </>
      ),
    },
    {
      at: c('sweeper'),
      enter: 'zoom',
      el: (
        <>
          <PlateVortexBg />
          <SweepVortex />
        </>
      ),
    },
    {
      at: c('eth167'),
      enter: 'push',
      el: (
        <>
          <AbsoluteFill style={{ flexDirection: 'row', justifyContent: 'center', alignItems: 'center', gap: 90, top: -80 }}>
            <Counter to={167_464} at={0} len={28} suffix=" ETH" size={120} />
            <Counter to={1.62} decimals={2} at={8} len={26} prefix="~" suffix="B USDT" size={120} color={C.bone} />
            <Counter to={60} at={16} len={20} prefix="~" suffix=" TOKENS" size={120} color={C.bone} />
          </AbsoluteFill>
          <AbsoluteFill style={{ top: 110 }}>
            <Center>
              <Stamp text="UNDER 4 MINUTES" at={30} color={C.alarm} size={72} rotate={-2} />
            </Center>
          </AbsoluteFill>
          <SourceTag text="TRM LABS · BLOCKAID RECONSTRUCTION" at={10} />
        </>
      ),
    },
    {
      at: c('eth38'),
      enter: 'fade',
      el: (
        <>
          <Bars
            title="BY CHAIN · TRM LABS ESTIMATES"
            items={[
              { label: 'ETHEREUM', value: 3.79, text: '~$3.79B', color: C.alarm, at: 0 },
              { label: 'BITCOIN · 18,270 BTC', value: 1.47, text: '~$1.47B', color: C.gold, at: c('btc18') - c('eth38') },
              { label: '8 OTHER CHAINS', value: 1.1, text: 'REMAINDER', color: C.mute, at: c('btc18') - c('eth38') + 30 },
            ]}
            max={3.79}
            y={260}
          />
          <SourceTag text="TRM LABS ESTIMATES" at={8} />
        </>
      ),
    },
    {
      at: c('gone'),
      enter: 'fade',
      el: (
        <>
          <PlateMonitors len={c('wave2') - c('gone') + 10} />
          <Center>
            <Headline text="20:25 UTC" size={200} at={6} sub="THE SWEEP IS LARGELY COMPLETE" subColor={C.alarm} />
          </Center>
        </>
      ),
      drift: 0,
    },
    {
      at: c('wave2'),
      enter: 'glitch',
      el: (
        <>
          <ChainNetwork assembleAt={-100} igniteMap={Object.fromEntries(CHAINS.map((n) => [n, n === 'Avalanche' || n === 'Polygon' ? 1e9 : -100]))} wave2At={6} />
          <div style={{ position: 'absolute', left: 0, right: 0, top: 870, textAlign: 'center' }} />
          <AbsoluteFill style={{ top: 360 }}>
            <Center>
              <Kicker size={26} color={C.alarm} style={{ background: 'rgba(7,8,11,.8)', padding: '8px 18px' }}>SECOND WAVE · ~23:05 UTC · AVALANCHE + POLYGON</Kicker>
            </Center>
          </AbsoluteFill>
        </>
      ),
    },
  ];
  return (
    <SceneShell s={s} overlay={<HUD s={s} keys={keys} />}>
      <Shots shots={shots} end={D} />
    </SceneShell>
  );
};

const ShowBetween: React.FC<{ from: number; to: number; children: React.ReactNode }> = ({ from, to, children }) => {
  const f = useF();
  if (f < from || f > to) return null;
  return <AbsoluteFill style={{ opacity: Math.min(prog(f, from, 10), 1 - prog(f, to - 8, 8)) }}>{children}</AbsoluteFill>;
};

/* ================================================================== S06 THE RACE TO FREEZE */
export const S06: React.FC<{ s: SceneData }> = ({ s }) => {
  const { c, D } = helpers(s);
  const shots: Shot[] = [
    { at: CARD, el: <RaceSplit /> },
    { at: c('stables'), enter: 'push', el: <StableSplit /> },
    { at: c('t2101'), enter: 'zoom', el: <FreezeStamp ticker="USDT" amount="971.1M USDT" who="TETHER" time="21:01 UTC · ATTACKER'S MAIN RECEIVING WALLET" /> },
    {
      at: c('t2104'),
      enter: 'fade',
      el: (
        <>
          <PlateIce len={c('t2124') - c('t2104') + 10} />
          <FreezeStamp ticker="USDC" amount="823M USDC" who="CIRCLE" time="21:04 UTC" />
        </>
      ),
      drift: 0,
    },
    { at: c('t2124'), enter: 'rise', el: <QuoteCard quote="a potential security issue" who="BINANCE" role="FIRST PUBLIC STATEMENT" where="ON X · OCT 29, 2026" /> },
    {
      at: c('t2125'),
      enter: 'zoom',
      el: (
        <>
          <Center>
            <Counter to={1.5} decimals={1} at={0} len={24} suffix="B+" size={240} color={C.ice} label="USDT FROZEN · PER TETHER'S CEO" labelColor={C.ice} />
          </Center>
          <SourceTag text="TETHER CEO ON X · OCT 29, 2026" at={8} until={c('others') - c('t2125')} />
        </>
      ),
    },
    {
      at: c('others'),
      enter: 'push',
      el: (
        <Center gap={60} style={{ flexDirection: 'row' }}>
          <Stamp text="40.5M RLUSD" sub="RIPPLE · CONFIRMED BY TRM" at={2} color={C.ice} size={80} rotate={-4} />
          <Stamp text="27.8M USD1" sub="WORLD LIBERTY FINANCIAL" at={12} color={C.ice} size={80} rotate={3} />
        </Center>
      ),
    },
    { at: c('suspend') - 6, enter: 'flash', el: <AlarmWash title="WITHDRAWALS SUSPENDED" sub="OCT 29–30, 2026 · REPORTED TIMES VARY" /> },
    {
      at: c('arb'),
      enter: 'push',
      el: (
        <>
          <Center gap={30}>
            <Stamp text="~$30M ETH + ARB" sub="8,426 ETH + 74.6M ARB" at={4} color={C.ice} size={110} rotate={-2} />
            <Kicker size={24} color={C.bone} style={{ marginTop: 30 }}>ARBITRUM SECURITY COUNCIL · 00:08–00:18 UTC, OCT 30</Kicker>
          </Center>
          <SourceTag text="TRM LABS" at={10} />
        </>
      ),
    },
    {
      at: c('frozen3'),
      enter: 'fade',
      el: (
        <>
          <Bars
            title="FROZEN OR INTERCEPTED · ESTIMATES"
            items={[
              { label: 'BINANCE (NOV 3 UPDATE)', value: 2.85, text: '~$2.85B', color: C.ice, at: 0 },
              { label: 'ELLIPTIC', value: 2.84, text: '$2.84B', color: C.ice, at: 14 },
              { label: 'TRM LABS', value: 2.7, text: '~$2.7B', color: C.ice, at: 28 },
            ]}
            max={3}
            y={270}
          />
          <SourceTag text="BINANCE · ELLIPTIC · TRM LABS" at={8} />
        </>
      ),
    },
    { at: c('nofreeze') - 6, enter: 'cut', el: <MeltThrough /> },
    {
      at: c('dump'),
      enter: 'push',
      el: (
        <>
          <FlowLines
            lines={[
              { from: '~325M USDT', to: 'MARKET MAKERS', note: 'SOLD AT 10%+ DISCOUNT', at: 0 },
              { from: 'USDT COLLATERAL', to: '~19,760 ETH', note: 'BORROWED ON AAVE', at: c('aave') - c('dump') - 10 },
            ]}
          />
          <SourceTag text="TRM LABS" at={10} />
        </>
      ),
    },
    {
      at: c('remain'),
      enter: 'zoom',
      el: (
        <>
          <AbsoluteFill style={{ flexDirection: 'row', justifyContent: 'center', alignItems: 'center', gap: 120, top: -170 }}>
            <Counter to={420_000} at={0} len={30} suffix="+ ETH" size={150} />
            <Counter to={18_270} at={8} len={28} suffix=" BTC" size={150} />
          </AbsoluteFill>
          <AbsoluteFill style={{ top: 110 }}>
            <Center>
              <Stamp text="~$2.4B BEYOND ANY FREEZE" at={30} color={C.alarm} size={76} rotate={-2} />
            </Center>
          </AbsoluteFill>
          <SourceTag text="TRM LABS · LATEST ANALYSIS" at={10} />
        </>
      ),
    },
    { at: c('peel') - 10, enter: 'fade', el: <PeelChain /> },
  ];
  return (
    <SceneShell s={s} accent={C.ice}>
      <Shots shots={shots} end={D} />
      <RaceHeader start={CARD + 20} />
    </SceneShell>
  );
};

const RaceHeader: React.FC<{ start: number }> = ({ start }) => {
  const f = useF();
  const v = prog(f, start, 14);
  return (
    <AbsoluteFill style={{ pointerEvents: 'none', opacity: v }}>
      <div style={{ position: 'absolute', left: 96, top: 54, fontFamily: 'monospace', fontSize: 18, letterSpacing: '0.2em', color: C.alarm }}>■ ATTACKER</div>
      <div style={{ position: 'absolute', right: 96, top: 54, fontFamily: 'monospace', fontSize: 18, letterSpacing: '0.2em', color: C.ice }}>FREEZE ■</div>
    </AbsoluteFill>
  );
};
