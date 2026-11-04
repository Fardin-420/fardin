// Detail inserts cut into long holds (pacing pass). Every figure here repeats a fact already in the
// narration and the fact ledger; generic illustrations are labeled as such.
import React from 'react';
import { AbsoluteFill } from 'remotion';
import { C, F } from '../theme';
import { useF, Rebase } from '../lib/frame';
import { damp, lerp, outExpo, outPow3, prog } from '../lib/anim';
import { Big, Center, Counter, Kicker, Panel, SourceTag } from './core';
import { CHAINS, ChainNetwork } from './diagrams1';

const Bg: React.FC<{ tint?: string }> = ({ tint = C.alarm }) => (
  <AbsoluteFill style={{ background: `radial-gradient(1100px 700px at 50% 42%, ${tint}1f, ${C.ink} 70%)` }} />
);

/** "Inside it: fifty authorizations" (F9). */
export const InsCount50: React.FC = () => {
  const f = useF();
  return (
    <AbsoluteFill>
      <Bg />
      <Center gap={6} style={{ paddingBottom: 170 }}>
        <Kicker color={C.alarm} size={26} style={{ opacity: prog(f, 0, 8) }}>ONE TRANSACTION · 20:20 UTC</Kicker>
        <Counter to={50} at={2} len={34} size={330} color={C.bone} />
        <Kicker color={C.bone} size={30} style={{ opacity: prog(f, 14, 10) }}>SIGNED AUTHORIZATIONS · EIP-7702</Kicker>
        <Kicker size={22} style={{ opacity: prog(f, 22, 10), marginTop: 10 }}>ALL SIGNED BY THE “BINANCE 14” HOT WALLET</Kicker>
      </Center>
      <SourceTag text="TRM LABS · BLOCKAID" at={4} />
    </AbsoluteFill>
  );
};

/** "using an Ethereum feature called EIP-7702" (F35): split screen, Ethereum node | feature card. */
export const InsEthEip: React.FC = () => {
  const f = useF();
  const all: Record<string, number> = {};
  CHAINS.forEach((n) => (all[n] = -100));
  const split = prog(f, 0, 12, outExpo);
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <AbsoluteFill style={{ clipPath: `inset(0 ${lerp(0, 50, split)}% 0 0)` }}>
        <AbsoluteFill style={{ transform: 'translateX(-300px)' }}>
          <Rebase by={-60}>
            <ChainNetwork assembleAt={-100} igniteMap={all} zoom={{ node: 'Ethereum', at: -60 }} particles />
          </Rebase>
        </AbsoluteFill>
      </AbsoluteFill>
      <div style={{ position: 'absolute', left: '50%', top: 120, bottom: 220, width: 2, background: C.line, opacity: split }} />
      <div style={{ position: 'absolute', left: 1040, top: 250, opacity: prog(f, 8, 12), transform: `translateX(${(1 - damp(f, 8, 14)) * 40}px)` }}>
        <Kicker color={C.ice} size={24}>AN ETHEREUM FEATURE</Kicker>
        <Big size={190} color={C.ice} style={{ marginTop: 8 }}>EIP-7702</Big>
        <Kicker color={C.bone} size={24} style={{ marginTop: 14, opacity: prog(f, 20, 12) }}>LIVE SINCE MAY 2025 (PECTRA UPGRADE)</Kicker>
      </div>
    </AbsoluteFill>
  );
};

/** "which lets a wallet hand its powers to a piece of code": wallet → code delegation. */
export const InsDelegate: React.FC = () => {
  const f = useF();
  const a = damp(f, 0, 12);
  const line = prog(f, 14, 20, outPow3);
  const b = damp(f, 26, 12);
  const pulse = (f % 30) / 30;
  return (
    <AbsoluteFill>
      <Bg tint={C.ice} />
      <div style={{ position: 'absolute', left: 300, top: 300, opacity: a, transform: `translateY(${(1 - a) * 30}px)` }}>
        <Panel style={{ padding: '34px 40px', width: 460 }}>
          <Kicker size={20}>WALLET</Kicker>
          <div style={{ fontFamily: F.display, fontSize: 76, color: C.bone }}>BINANCE 14</div>
          <Kicker size={18} color={C.gold}>ITS KEY · ITS POWERS</Kicker>
        </Panel>
      </div>
      <svg width={1920} height={1080} style={{ position: 'absolute', inset: 0 }}>
        <line x1={780} y1={400} x2={lerp(780, 1150, line)} y2={400} stroke={C.ice} strokeWidth={5} strokeDasharray="16 12" strokeDashoffset={-f * 3} />
        {line > 0.98 && <circle cx={lerp(800, 1140, pulse)} cy={400} r={9} fill={C.ice} opacity={1 - pulse} />}
      </svg>
      <div style={{ position: 'absolute', left: 860, top: 330, width: 220, textAlign: 'center', opacity: prog(f, 18, 10) }}>
        <Kicker size={20} color={C.ice}>DELEGATES TO</Kicker>
      </div>
      <div style={{ position: 'absolute', left: 1170, top: 300, opacity: b, transform: `translateY(${(1 - b) * 30}px)` }}>
        <Panel border={C.ice} style={{ padding: '34px 40px', width: 420 }}>
          <Kicker size={20} color={C.ice}>SMART-CONTRACT CODE</Kicker>
          <div style={{ fontFamily: F.mono, fontSize: 84, color: C.ice, lineHeight: 1.1 }}>{'</>'}</div>
          <Kicker size={18}>NOW ACTS FOR THE WALLET</Kicker>
        </Panel>
      </div>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 640, textAlign: 'center', opacity: prog(f, 30, 12) }}>
        <Kicker size={20}>SIMPLIFIED ILLUSTRATION · EIP-7702 DELEGATION</Kicker>
      </div>
    </AbsoluteFill>
  );
};

/** "Every wallet keeps a running count of its transactions": a generic nonce counter (illustrative numbers). */
export const InsNonceRun: React.FC = () => {
  const f = useF();
  const n = Math.min(6, Math.floor(f / 11) + 1);
  return (
    <AbsoluteFill>
      <Bg tint={C.gold} />
      <div style={{ position: 'absolute', left: 0, right: 0, top: 230, textAlign: 'center', opacity: prog(f, 0, 8) }}>
        <Kicker color={C.gold} size={26}>EVERY WALLET · A RUNNING COUNT OF ITS TRANSACTIONS</Kicker>
      </div>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 330, display: 'flex', justifyContent: 'center', gap: 26 }}>
        {Array.from({ length: 6 }, (_, i) => {
          const v = damp(f, i * 11, 8);
          const cur = i === n - 1;
          return (
            <div key={i} style={{ opacity: v, transform: `translateY(${(1 - v) * 24}px)` }}>
              <Panel border={cur ? C.gold : C.line} style={{ padding: '22px 26px', width: 170, textAlign: 'center' }}>
                <Kicker size={16}>TX</Kicker>
                <div style={{ fontFamily: F.mono, fontWeight: 700, fontSize: 56, color: cur ? C.gold : C.bone }}>#{i + 1}</div>
              </Panel>
            </div>
          );
        })}
      </div>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 540, textAlign: 'center' }}>
        <span style={{ fontFamily: F.mono, fontSize: 40, color: C.bone }}>NEXT TRANSACTION # → </span>
        <span style={{ fontFamily: F.mono, fontWeight: 700, fontSize: 40, color: C.gold }}>{n + 1}</span>
      </div>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 620, textAlign: 'center', opacity: prog(f, 20, 10) }}>
        <Kicker size={18}>ILLUSTRATION · NUMBERS ARE GENERIC</Kicker>
      </div>
    </AbsoluteFill>
  );
};

export const INSERTS: Record<string, React.FC> = { count50: InsCount50, ethEip: InsEthEip, delegate: InsDelegate, nonceRun: InsNonceRun };
