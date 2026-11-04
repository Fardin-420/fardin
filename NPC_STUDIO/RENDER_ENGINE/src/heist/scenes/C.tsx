import React from 'react';
import { AbsoluteFill } from 'remotion';
import { C } from '../theme';
import { SceneData } from '../tl';
import { useF } from '../lib/frame';
import { prog } from '../lib/anim';
import { Badge, Center, Counter, Headline, Kicker, QuoteCard, Shot, Shots, SourceTag, UTCClock } from '../components/core';
import { CHAINS, ChainNetwork, FlowPath } from '../components/diagrams1';
import { Bars, DossierReveal, FlowDonut, HeistTimeline, MarketBoard, PlaybookCards, ProgressRing, QState, QuestionCards } from '../components/diagrams2';
import { PlateDawn, PlateDossierLamp, PlateLaptop, PlateSilhouette } from '../components/plates';
import { Checklist, ConvergeFlows, DenyCard, EndScreen, FolderAlarm, JobMessage, LineCard, NameCard, RecruiterEmail, SplitCompare, StatusBoard, TipCards, VideoTiles } from '../components/beats';
import { CARD, SceneShell, helpers } from './shell';

const allLit = Object.fromEntries(CHAINS.map((n) => [n, -100]));

/* ================================================================== S07 THE NAME */
export const S07: React.FC<{ s: SceneData }> = ({ s }) => {
  const { c, D } = helpers(s);
  const pat = c('pattern');
  const shots: Shot[] = [
    {
      at: CARD,
      el: (
        <>
          <PlateDossierLamp len={c('tt') - CARD + 10} />
          <Center>
            <Headline text="ATTRIBUTION" size={190} at={10} sub="OCT 30, 2026" />
          </Center>
        </>
      ),
      drift: 0,
    },
    { at: c('tt'), enter: 'cut', el: <DossierReveal at={0} /> },
    {
      at: c('bitget') - 8,
      enter: 'push',
      el: (
        <>
          <ConvergeFlows />
          <SourceTag text="CHAINALYSIS · ZACHXBT" at={12} />
        </>
      ),
    },
    { at: c('fbi') - 4, enter: 'rise', el: <QuoteCard quote="North Korea was responsible for the theft of more than $6 billion" who="FBI" role="PUBLIC STATEMENT" where="NOV 1, 2026" accent={C.alarm} size={64} /> },
    { at: c('deny') - 40, enter: 'fade', el: <DenyCard /> },
    { at: c('lawenf'), enter: 'fade', el: <LineCard text="BINANCE + LAW ENFORCEMENT" sub="IDENTITY OF THE ATTACKERS: TO BE CONFIRMED · BINANCE, OCT 30, 2026" /> },
    {
      at: c('bybit') - 10,
      enter: 'zoom',
      el: (
        <>
          <HeistTimeline at={0} />
          <div style={{ position: 'absolute', left: 0, right: 0, top: 110, textAlign: 'center' }}>
            <Kicker size={22} color={C.bone}>BYBIT · FEB 2025 · BREACH TRACED TO A COMPROMISED SAFE DEVELOPER MACHINE (FBI)</Kicker>
          </div>
        </>
      ),
    },
    {
      at: c('dmm'),
      enter: 'push',
      el: (
        <>
          <RecruiterEmail />
          <SourceTag text="FBI · DC3 · JAPAN NPA JOINT STATEMENT · DEC 2024" at={10} />
        </>
      ),
    },
    { at: c('playbook'), enter: 'zoom', el: <PlaybookCards at={0} step={Math.round((c('remember') - c('playbook')) / 5)} highlightAt={c('remember') - c('playbook')} /> },
    { at: pat, enter: 'glitch', el: <PlateSilhouette len={88} />, drift: 0 },
    { at: pat + 84, enter: 'fade', el: <Checklist title="TRM LABS: FITS THE PATTERN" items={['STAGING WELL BEFORE THE THEFT', 'TORNADO CASH FUNDING', 'SIGNATURES COLLECTED IN ADVANCE']} step={22} /> },
    {
      at: c('burst') - 2,
      enter: 'flash',
      el: (
        <>
          <AbsoluteFill style={{ opacity: 0.18 }}>
            <ChainNetwork assembleAt={-100} igniteMap={allLit} flashAt={0} />
          </AbsoluteFill>
          <HeistTimeline at={-100} binanceAt={6} />
        </>
      ),
    },
  ];
  return (
    <SceneShell s={s}>
      <Shots shots={shots} end={D} />
    </SceneShell>
  );
};

/* ================================================================== S08 THE MORNING AFTER */
export const S08: React.FC<{ s: SceneData }> = ({ s }) => {
  const { c, w, D } = helpers(s);
  const shots: Shot[] = [
    {
      at: CARD,
      el: (
        <>
          <PlateDawn len={c('btclow') - CARD + 10} />
          <Center>
            <Headline text="THE MORNING AFTER" size={150} at={8} />
          </Center>
        </>
      ),
      drift: 0,
    },
    {
      at: c('btclow') - 4,
      enter: 'push',
      el: (
        <>
          <MarketBoard />
          <SourceTag text="REUTERS · OCT 30, 2026" at={10} />
        </>
      ),
    },
    {
      at: w('answer') - 6,
      enter: 'fade',
      el: <Headline text="WHO PAYS? NOT USERS." size={150} sub="BINANCE'S ANSWER — AS IN 2019" />,
    },
    {
      at: c('634'),
      enter: 'push',
      el: (
        <>
          <Bars
            title="TO COVER THE LOSSES · HONEST SCALE"
            items={[
              { label: 'SET ASIDE BY BINANCE', value: 6.34, text: '~$6.34B', color: C.gold, at: 0 },
              { label: 'SAFU EMERGENCY FUND (REPORTED)', value: 1, text: '~$1B', color: C.mute, at: 20 },
            ]}
            max={6.34}
            y={300}
          />
          <SourceTag text="REUTERS · PRESS ESTIMATES FOR SAFU" at={10} />
        </>
      ),
    },
    { at: c('teng') - 8, enter: 'rise', el: <QuoteCard quote="Our users will not bear the financial impact of this incident." who="RICHARD TENG" role="BINANCE CO-CEO" where="ON X · OCT 31, 2026" size={64} /> },
    { at: c('czcard'), enter: 'push', el: <NameCard name="CHANGPENG ZHAO (CZ)" role="FOUNDER · STEPPED DOWN AS CEO IN 2023" /> },
    {
      at: c('withdraw'),
      enter: 'zoom',
      el: (
        <>
          <StatusBoard items={['BTC', 'ETH', 'BNB', 'USDT', 'USDC', '+10 MORE']} />
          <SourceTag text="BINANCE, VIA COINDESK · NOV 1, 2026" at={10} />
        </>
      ),
    },
    {
      at: c('net') - 6,
      enter: 'push',
      el: (
        <>
          <FlowDonut />
          <SourceTag text="BINANCE, VIA CNBC · NOV 1, 06:00–15:30 UTC" at={10} />
        </>
      ),
    },
    { at: c('98') - 6, enter: 'rise', el: <QuoteCard quote="98% choose to stay." who="CHANGPENG ZHAO (CZ)" role="FOUNDER" where="ON X · NOV 1, 2026" size={96} /> },
    {
      at: c('95') - 10,
      enter: 'zoom',
      el: (
        <>
          <ProgressRing label="AFFECTED ASSETS REPLENISHED" />
          <SourceTag text="BINANCE · NOV 1, 2026" at={10} />
        </>
      ),
    },
  ];
  return (
    <SceneShell s={s} accent={C.gold}>
      <Shots shots={shots} end={D} />
    </SceneShell>
  );
};

/* ================================================================== S09 THE QUESTION */
const Q = (s: SceneData, c: (n: string) => number): QState[] => [
  { q: 'How did the attackers get in?', flipAt: c('q1') - c('q1') + 0, stamp: 'ANSWERED · BINANCE, NOV 3', stampAt: 1e9, color: C.green, answer: 'Fake job interview → malicious coding assignment.' },
  { q: 'What were the other points of breach?', flipAt: 1e9, stamp: 'PARTLY ANSWERED', stampAt: 1e9, color: C.gold, answer: 'Internal AI tool → colleagues’ machines → deploy token.' },
  { q: 'How did that become 50 valid signatures?', flipAt: 1e9, stamp: 'PENDING POST-MORTEM', stampAt: 1e9, color: C.ice },
  { q: 'Will the unfreezable billions come back?', flipAt: 1e9, stamp: 'UNKNOWN', stampAt: 1e9, color: C.alarm },
];

const MoveClock: React.FC = () => {
  const f = useF();
  const sec = 20 * 3600 + 5 * 60 + Math.min(1200, Math.floor(prog(f, 4, 50) * 1200));
  return (
    <Center>
      <UTCClock sec={sec} size={200} flash={f > 54} />
    </Center>
  );
};

export const S09: React.FC<{ s: SceneData }> = ({ s }) => {
  const { c, D } = helpers(s);
  const q1 = c('q1');
  const q3 = c('q3');
  const base = Q(s, c);
  const cardsA = base.map((x, i) => ({ ...x, flipAt: i === 0 ? q1 - CARD : 1e9 }));
  const cardsB = base.map((x, i) => ({
    ...x,
    flipAt: i < 2 ? -100 : i === 2 ? 0 : c('q4') - q3,
    stampAt: i === 0 ? -100 : i === 1 ? -90 : i === 2 ? 24 : c('q4') - q3 + 30,
  }));
  const q2 = c('q2');
  const shots: Shot[] = [
    { at: CARD, el: <QuestionCards items={cardsA} at={0} /> },
    { at: c('nov3') - 4, enter: 'push', el: <JobMessage /> },
    { at: c('hr') - 4, enter: 'fade', el: <VideoTiles ceoAt={c('ceo') - c('hr') + 4} /> },
    { at: c('assignment') - 6, enter: 'zoom', el: <FolderAlarm /> },
    {
      at: q2,
      enter: 'zoom',
      el: (
        <FlowPath
          nodes={[
            { label: "ENGINEER'S COMPUTER", sub: 'after the fake interview', at: 0 },
            { label: 'INTERNAL AI TOOL', at: c('aitool') - q2 },
            { label: "COLLEAGUES' MACHINES", at: c('aitool') - q2 + 26 },
            { label: 'DEPLOY TOKEN', sub: 'container deployment permission', at: c('token') - q2, color: C.alarm },
            { label: 'WALLET SYSTEM', at: c('token') - q2 + 24, color: C.alarm },
          ]}
          footer="SIMPLIFIED · BINANCE INITIAL INCIDENT REPORT, NOV 3, 2026 · ENGINEERS NOT IDENTIFIED"
          footerAt={10}
        />
      ),
    },
    { at: q3, enter: 'zoom', el: <QuestionCards items={cardsB} at={-100} /> },
    { at: c('y2019'), enter: 'push', el: <SplitCompare growAt={c('y2026') - c('y2019') + 30} /> },
    { at: c('moved') - 4, enter: 'fade', el: <MoveClock /> },
    { at: c('years') - 6, enter: 'fade', el: <PlateLaptop len={D - c('years') + 6} mode="closing" />, drift: 0 },
  ];
  return (
    <SceneShell s={s}>
      <Shots shots={shots} end={D} />
    </SceneShell>
  );
};

/* ================================================================== S10 OUTRO */
export const S10: React.FC<{ s: SceneData }> = ({ s }) => {
  const { c, D } = helpers(s);
  const t1 = c('tip1');
  const shots: Shot[] = [
    { at: -12, el: <Headline text="WHAT IT MEANS FOR YOU" size={150} at={24} /> },
    { at: t1 - 6, enter: 'fade', el: <TipCards ats={[6, c('tip2') - t1 + 6, c('tip3') - t1 + 6, c('tip4') - t1 + 6]} /> },
    {
      at: c('sub'),
      enter: 'fade',
      el: (
        <>
          <AbsoluteFill style={{ opacity: 0.15 }}>
            <ChainNetwork assembleAt={-100} igniteMap={allLit} />
          </AbsoluteFill>
          <EndScreen />
        </>
      ),
    },
  ];
  return (
    <SceneShell s={s} accent={C.gold}>
      <Shots shots={shots} end={D} />
      <Badge text="NOT FINANCIAL ADVICE" at={t1 - 6} until={D} color={C.gold} />
    </SceneShell>
  );
};

export const _k = Counter;
