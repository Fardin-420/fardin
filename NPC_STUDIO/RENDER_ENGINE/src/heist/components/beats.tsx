/** One-off story beats. All brands, names and UIs here are fictional/generic; no real logos or faces. */
import React from 'react';
import { AbsoluteFill, interpolate } from 'remotion';
import { C, F } from '../theme';
import { useF } from '../lib/frame';
import { clamp, damp, inPow3, jitter, lerp, outExpo, outPow3, pop, prog, rnd, typeOn } from '../lib/anim';
import { Center, Counter, GlitchBars, Kicker, Panel, Stamp, TokenCircle, UTCClock } from './core';
import { LaptopIcon } from './diagrams1';

export const FlipTiles: React.FC<{ items: string[]; at?: number; step?: number }> = ({ items, at = 0, step = 8 }) => {
  const f = useF();
  return (
    <Center>
      <div style={{ display: 'flex', gap: 40 }}>
        {items.map((t, i) => {
          const p = prog(f, at + i * step, 14, outPow3);
          return (
            <div key={i} style={{ perspective: 1000 }}>
              <Panel border={C.gold} style={{ width: 420, height: 260, display: 'flex', alignItems: 'center', justifyContent: 'center', transform: `rotateX(${(1 - p) * 90}deg)`, opacity: p }}>
                <div style={{ fontFamily: F.display, fontSize: 76, color: C.bone, letterSpacing: '0.05em' }}>{t}</div>
              </Panel>
            </div>
          );
        })}
      </div>
    </Center>
  );
};

/** Generic lookalike login (fictional "EXCHANGE" brand) with one swapped character circled. */
export const PhishCard: React.FC<{ at?: number }> = ({ at = 0 }) => {
  const f = useF();
  const v = damp(f, at, 14);
  const circle = prog(f, at + 24, 14, outPow3);
  return (
    <Center>
      <div style={{ opacity: v, transform: `translateY(${(1 - v) * 30}px)` }}>
        <Panel style={{ width: 900, padding: 0, overflow: 'hidden' }}>
          <div style={{ background: '#1d2127', padding: '18px 26px', display: 'flex', alignItems: 'center', gap: 16 }}>
            {[C.alarm, C.gold, C.green].map((c, i) => (
              <div key={i} style={{ width: 14, height: 14, borderRadius: 14, background: c, opacity: 0.6 }} />
            ))}
            <div style={{ marginLeft: 20, flex: 1, background: '#0c0e11', borderRadius: 8, padding: '10px 18px', fontFamily: F.mono, fontSize: 30, color: C.bone, position: 'relative' }}>
              https://login.exchan<span style={{ position: 'relative' }}>q</span>e.example
              <div style={{ position: 'absolute', left: 392, top: -12, width: 56, height: 66, border: `4px solid ${C.alarm}`, borderRadius: 40, transform: `scale(${circle})`, opacity: circle }} />
            </div>
          </div>
          <div style={{ padding: 50, display: 'flex', flexDirection: 'column', gap: 22 }}>
            <div style={{ fontFamily: F.display, fontSize: 64, color: C.bone }}>EXCHANGE · SIGN IN</div>
            {['EMAIL', 'PASSWORD', '2FA CODE'].map((l) => (
              <div key={l} style={{ border: `1px solid ${C.line}`, borderRadius: 8, padding: '16px 20px', fontFamily: F.mono, fontSize: 22, color: C.mute }}>{l}</div>
            ))}
          </div>
        </Panel>
        <div style={{ marginTop: 18, textAlign: 'center', opacity: circle }}>
          <Kicker size={20} color={C.alarm}>ILLUSTRATION · FICTIONAL LOOKALIKE PAGE</Kicker>
        </div>
      </div>
    </Center>
  );
};

/** Clock fast-forward + dozens of unrelated-looking accounts that light up at the same moment. */
export const AccountsGrid: React.FC<{ fireAt: number }> = ({ fireAt }) => {
  const f = useF();
  const fired = f >= fireAt;
  return (
    <AbsoluteFill>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 110, display: 'flex', justifyContent: 'center' }}>
        <UTCClock sec={9 * 3600 + (fired ? fireAt : f) * 413} size={70} color={C.mute} />
      </div>
      {Array.from({ length: 36 }, (_, i) => {
        const x = 230 + (i % 9) * 165 + (rnd(`ax${i}`) - 0.5) * 30;
        const y = 260 + Math.floor(i / 9) * 125 + (rnd(`ay${i}`) - 0.5) * 20;
        const on = fired ? prog(f, fireAt + rnd(`ad${i}`) * 3, 4) : 0;
        return (
          <div key={i} style={{ position: 'absolute', left: x, top: y, width: 140, height: 92, borderRadius: 8, border: `2px solid ${on ? C.alarm : C.line}`, background: on ? `${C.alarm}33` : C.panel, boxShadow: on ? `0 0 26px ${C.alarm}88` : 'none', padding: 10, boxSizing: 'border-box', opacity: prog(f, i * 0.6, 8) }}>
            <div style={{ fontFamily: F.mono, fontSize: 13, color: C.mute }}>ACCT #{String(Math.floor(rnd(`an${i}`) * 90000 + 10000))}</div>
            <div style={{ fontFamily: F.mono, fontSize: 18, color: on ? C.alarm : C.bone, marginTop: 8 }}>{on ? 'WITHDRAW' : 'IDLE'}</div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

export const AlarmVault: React.FC = () => {
  const f = useF();
  const on = Math.floor(f / 6) % 2 === 0;
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ background: C.alarm, opacity: on ? 0.16 : 0.04 }} />
      <Center gap={30} style={{ paddingBottom: 260 }}>
        <svg width={420} height={420} viewBox="-210 -210 420 420">
          <circle r={190} fill="none" stroke={C.mute} strokeWidth={8} />
          <circle r={130} fill="none" stroke={C.mute} strokeWidth={4} strokeDasharray="12 10" />
          <text y={22} textAnchor="middle" fill={C.mute} fontFamily="monospace" fontSize={44}>EMPTY</text>
        </svg>
        <div style={{ fontFamily: F.display, fontSize: 90, color: on ? C.alarm : C.bone, letterSpacing: '0.05em' }}>ALARMS: AFTER THE FACT</div>
      </Center>
    </AbsoluteFill>
  );
};

/** Abstract livestream frame with a voice waveform (no face) + name card. */
export const LiveFrame: React.FC<{ name: string; role: string }> = ({ name, role }) => {
  const f = useF();
  const v = damp(f, 4, 14);
  return (
    <AbsoluteFill>
      <div style={{ position: 'absolute', left: 260, top: 130, width: 1400, height: 560, border: `2px solid ${C.line}`, background: 'linear-gradient(180deg, #11151b, #08090c)', borderRadius: 12, overflow: 'hidden' }}>
        <div style={{ position: 'absolute', left: 30, top: 26, background: C.alarm, color: '#fff', fontFamily: F.mono, fontWeight: 700, fontSize: 22, padding: '6px 14px', letterSpacing: '0.1em' }}>● LIVE</div>
        <svg width={1400} height={560} style={{ position: 'absolute', inset: 0 }}>
          {Array.from({ length: 90 }, (_, i) => {
            const h = 20 + Math.abs(Math.sin(i * 0.45 + f * 0.35) * Math.sin(i * 0.13 + f * 0.11)) * 220;
            return <rect key={i} x={110 + i * 13} y={280 - h / 2} width={7} height={h} rx={3} fill={C.gold} opacity={0.75} />;
          })}
        </svg>
      </div>
      <div style={{ position: 'absolute', left: 300, top: 600, opacity: v, transform: `translateX(${(1 - v) * -30}px)` }}>
        <Panel border={C.gold} style={{ padding: '18px 28px' }}>
          <div style={{ fontFamily: F.display, fontSize: 60, color: C.bone }}>{name}</div>
          <Kicker size={20} color={C.gold}>{role}</Kicker>
        </Panel>
      </div>
    </AbsoluteFill>
  );
};

/** Chain of blocks slides backwards… cracks… stops dead. */
export const BlockRewind: React.FC = () => {
  const f = useF();
  const back = prog(f, 4, 36, outPow3);
  const crack = prog(f, 34, 8);
  const stopShake = f > 40 && f < 48 ? jitter(f, 'br', 1) * 8 : 0;
  return (
    <AbsoluteFill>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 160, textAlign: 'center' }}>
        <Kicker size={24} color={C.gold}>{f < 40 ? '◀◀ REWRITING THE CHAIN?' : 'IMMUTABLE'}</Kicker>
      </div>
      {Array.from({ length: 9 }, (_, i) => {
        const x = 120 + i * 200 + back * 180 + stopShake;
        return (
          <div key={i} style={{ position: 'absolute', left: x, top: 340, width: 160, height: 160, border: `3px solid ${i >= 6 && crack > 0 ? C.alarm : C.gold}`, background: C.panel, borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: F.mono, fontSize: 22, color: C.bone }}>
            BLOCK
            {i < 8 && <div style={{ position: 'absolute', right: -44, top: 76, width: 44, height: 4, background: C.gold }} />}
          </div>
        );
      })}
      {crack > 0 && (
        <svg width={1920} height={1080} style={{ position: 'absolute', inset: 0 }}>
          <path d="M 1500 320 L 1470 380 L 1520 420 L 1480 470 L 1530 530" fill="none" stroke={C.alarm} strokeWidth={6} opacity={crack} strokeDasharray={400} strokeDashoffset={400 * (1 - crack)} />
        </svg>
      )}
    </AbsoluteFill>
  );
};

export const SafuVault: React.FC<{ stampAt: number }> = ({ stampAt }) => {
  const f = useF();
  const fill = prog(f, 4, 70, outPow3);
  return (
    <AbsoluteFill>
      <div style={{ position: 'absolute', left: 660, top: 170, width: 600, height: 520, border: `4px solid ${C.gold}`, borderRadius: 18, overflow: 'hidden', background: C.panel }}>
        <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: `${fill * 80}%`, background: `linear-gradient(180deg, ${C.gold}aa, ${C.gold}33)` }} />
        <div style={{ position: 'absolute', left: 0, right: 0, top: 40, textAlign: 'center', fontFamily: F.display, fontSize: 120, color: C.bone, letterSpacing: '0.08em' }}>SAFU</div>
        <div style={{ position: 'absolute', left: 0, right: 0, top: 170, textAlign: 'center' }}>
          <Kicker size={20} color={C.bone}>SECURE ASSET FUND FOR USERS · SINCE 2018</Kicker>
        </div>
      </div>
      {Array.from({ length: 30 }, (_, i) => {
        const ph = ((f + i * 9) % 60) / 60;
        return <div key={i} style={{ position: 'absolute', left: 700 + rnd(`sp${i}`) * 520, top: lerp(-20, 600, ph), width: 10, height: 10, borderRadius: 10, background: C.gold, opacity: 1 - ph }} />;
      })}
      <div style={{ position: 'absolute', left: 1310, top: 300 }}>
        <Kicker size={22} color={C.gold}>← 10% OF TRADING FEES</Kicker>
      </div>
      <div style={{ position: 'absolute', left: 1290, top: 560 }}>
        <Stamp text="WITHDRAWALS BACK" sub="MAY 15, 2019" at={stampAt} color={C.green} size={56} rotate={-3} />
      </div>
    </AbsoluteFill>
  );
};

export const FastCard: React.FC<{ lines: string[]; source?: string }> = ({ lines }) => {
  const f = useF();
  return (
    <Center gap={10}>
      {lines.map((l, i) => {
        const p = prog(f, i * 6, 10);
        return (
          <div key={i} style={{ fontFamily: i === 0 ? F.mono : F.display, fontSize: i === 0 ? 34 : 96, color: i === 2 ? C.gold : i === 3 ? C.alarm : C.bone, letterSpacing: '0.05em', opacity: p, transform: `translateX(${(1 - p) * 60}px)` }}>
            {l}
          </div>
        );
      })}
    </Center>
  );
};

/** Calendar flip to OCT 28 · T–36H with three Tornado Cash drips into an operator wallet. */
export const CalendarDrip: React.FC = () => {
  const f = useF();
  const flip = prog(f, 0, 14, outPow3);
  return (
    <AbsoluteFill>
      <div style={{ position: 'absolute', left: 330, top: 200, width: 420, perspective: 900 }}>
        <Panel border={C.alarm} style={{ height: 420, overflow: 'hidden', transform: `rotateX(${(1 - flip) * -80}deg)`, transformOrigin: 'top' }}>
          <div style={{ background: C.alarm, color: '#fff', textAlign: 'center', fontFamily: F.display, fontSize: 64, padding: 10 }}>OCT 2026</div>
          <div style={{ textAlign: 'center', fontFamily: F.display, fontSize: 210, color: C.bone, lineHeight: 1.2 }}>28</div>
          <div style={{ textAlign: 'center', fontFamily: F.mono, fontSize: 40, color: C.alarm }}>T–36H</div>
        </Panel>
      </div>
      <div style={{ position: 'absolute', left: 1050, top: 150, fontFamily: F.display, fontSize: 56, color: C.mute, letterSpacing: '0.05em' }}>TORNADO CASH (MIXER)</div>
      {[0, 1, 2].map((k) => {
        const ph = clamp((f - 16 - k * 14) / 30);
        return ph > 0 && ph < 1 ? <div key={k} style={{ position: 'absolute', left: 1220 + k * 36, top: lerp(230, 520, ph * ph), width: 22, height: 34, borderRadius: '50% 50% 50% 50% / 60% 60% 40% 40%', background: C.ice, boxShadow: `0 0 16px ${C.ice}` }} /> : null;
      })}
      <div style={{ position: 'absolute', left: 1080, top: 540, opacity: prog(f, 10, 12) }}>
        <Panel border={C.alarm} style={{ padding: '24px 34px', width: 420 }}>
          <Kicker size={18} color={C.alarm}>ATTACKER</Kicker>
          <div style={{ fontFamily: F.display, fontSize: 60, color: C.bone }}>OPERATOR WALLET</div>
        </Panel>
      </div>
    </AbsoluteFill>
  );
};

/** Transaction card whose signature line draws itself in red. */
export const SignatureCard: React.FC = () => {
  const f = useF();
  const p = prog(f, 6, 30, outPow3);
  return (
    <Center>
      <Panel style={{ width: 1000, padding: 50 }}>
        <Kicker size={20}>WITHDRAWAL TRANSACTION</Kicker>
        <div style={{ fontFamily: F.mono, fontSize: 28, color: C.bone, marginTop: 20, lineHeight: 1.7 }}>
          FROM: BINANCE HOT WALLET
          <br />
          TO: ATTACKER-CONTROLLED ADDRESS
        </div>
        <div style={{ marginTop: 40, display: 'flex', alignItems: 'flex-end', gap: 20 }}>
          <Kicker size={20}>AUTHORIZED SIGNATURE</Kicker>
          <svg width={560} height={110}>
            <path d="M 10 80 C 60 10, 90 110, 140 60 S 220 20, 260 70 S 340 100, 380 40 S 470 60, 540 50" fill="none" stroke={C.alarm} strokeWidth={6} strokeLinecap="round" strokeDasharray={900} strokeDashoffset={900 * (1 - p)} style={{ filter: `drop-shadow(0 0 10px ${C.alarm})` }} />
            <line x1={0} y1={100} x2={560} y2={100} stroke={C.line} strokeWidth={2} />
          </svg>
        </div>
        <div style={{ marginTop: 26, fontFamily: F.mono, fontSize: 22, color: C.alarm, opacity: prog(f, 34, 10) }}>SIGNED BY BINANCE'S OWN SYSTEMS</div>
      </Panel>
    </Center>
  );
};

export const LaptopToBillions: React.FC = () => {
  const f = useF();
  const a = prog(f, 4, 20, outPow3);
  return (
    <Center>
      <div style={{ display: 'flex', alignItems: 'center', gap: 70 }}>
        <div style={{ opacity: prog(f, 0, 10) }}>
          <LaptopIcon w={360} color={C.bone} />
        </div>
        <svg width={260} height={60}>
          <line x1={0} y1={30} x2={220 * a} y2={30} stroke={C.alarm} strokeWidth={6} />
          {a > 0.95 && <path d="M 210 10 L 245 30 L 210 50" fill="none" stroke={C.alarm} strokeWidth={6} />}
        </svg>
        <div style={{ fontFamily: F.display, fontSize: 200, color: C.gold, opacity: prog(f, 18, 10), transform: `scale(${pop(f, 18, 10) || 0.01})` }}>$6B?</div>
      </div>
    </Center>
  );
};

/** Huge countdown that starts at 20:00. */
export const Countdown: React.FC = () => {
  const f = useF();
  const left = Math.max(0, 1200 - Math.floor((f / 30) * 37));
  const s = pop(f, 0, 10);
  return (
    <Center>
      <div style={{ fontFamily: F.display, fontSize: 420, color: C.alarm, lineHeight: 1, transform: `scale(${s || 0.01})`, textShadow: `0 0 60px ${C.alarm}88`, fontVariantNumeric: 'tabular-nums' }}>
        {String(Math.floor(left / 60)).padStart(2, '0')}:{String(left % 60).padStart(2, '0')}
      </div>
    </Center>
  );
};

/** Split race frame: ATTACKER (alarm) vs FREEZE (ice). */
export const RaceSplit: React.FC = () => {
  const f = useF();
  const a = prog(f, 0, 18, outPow3);
  return (
    <AbsoluteFill>
      <div style={{ position: 'absolute', left: 0, top: 0, width: 960 * a, bottom: 0, background: `linear-gradient(90deg, ${C.alarm}22, transparent)` }} />
      <div style={{ position: 'absolute', right: 0, top: 0, width: 960 * a, bottom: 0, background: `linear-gradient(270deg, ${C.ice}22, transparent)` }} />
      <div style={{ position: 'absolute', left: 958, top: 90, width: 4, height: 760 * a, background: C.line }} />
      <div style={{ position: 'absolute', left: 260, top: 360, fontFamily: F.display, fontSize: 150, color: C.alarm, opacity: a }}>ATTACKER</div>
      <div style={{ position: 'absolute', left: 1180, top: 360, fontFamily: F.display, fontSize: 150, color: C.ice, opacity: a }}>FREEZE</div>
      {Array.from({ length: 24 }, (_, i) => {
        const ph = ((f + i * 7) % 50) / 50;
        return <div key={i} style={{ position: 'absolute', left: lerp(900, 120, ph), top: 300 + rnd(`rs${i}`) * 360, width: 8, height: 8, borderRadius: 8, background: C.alarm, opacity: 1 - ph }} />;
      })}
    </AbsoluteFill>
  );
};

export const StableSplit: React.FC<{ at?: number }> = ({ at = 0 }) => {
  const f = useF();
  const L = [
    { t: 'USDT', ok: true },
    { t: 'USDC', ok: true },
    { t: 'BTC', ok: false },
    { t: 'ETH', ok: false },
  ];
  return (
    <AbsoluteFill>
      {L.map((x, i) => {
        const v = damp(f, at + i * 6, 14);
        const left = i < 2 ? 330 + i * 300 : 1090 + (i - 2) * 300;
        return (
          <div key={x.t} style={{ position: 'absolute', left, top: 260, width: 220, textAlign: 'center', opacity: v, transform: `translateY(${(1 - v) * 30}px)` }}>
            <TokenCircle ticker={x.t} size={200} color={x.ok ? C.ice : C.gold} style={{ margin: '0 auto' }} />
            <div style={{ marginTop: 26, fontFamily: F.mono, fontSize: 20, color: x.ok ? C.ice : C.alarm, letterSpacing: '0.08em' }}>{x.ok ? 'ISSUER CAN FREEZE ✓' : 'NO ISSUER ✕'}</div>
          </div>
        );
      })}
      <div style={{ position: 'absolute', left: 958, top: 230, width: 4, height: 420, background: C.line }} />
    </AbsoluteFill>
  );
};

export const AlarmWash: React.FC<{ title: string; sub?: string }> = ({ title, sub }) => {
  const f = useF();
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ background: `radial-gradient(1200px 700px at 50% 45%, ${C.alarm}66, ${C.ink} 75%)`, opacity: 0.6 + 0.4 * Math.abs(Math.sin(f / 9)) }} />
      <Center gap={20}>
        <Stamp text={title} at={2} color={C.alarm} size={110} rotate={0} />
        {sub && <Kicker size={22} color={C.bone} style={{ opacity: prog(f, 14, 12) }}>{sub}</Kicker>}
      </Center>
    </AbsoluteFill>
  );
};

/** BTC and ETH circles melt straight through an ice sheet. */
export const MeltThrough: React.FC = () => {
  const f = useF();
  const d = prog(f, 8, 40, inPow3);
  return (
    <AbsoluteFill>
      <div style={{ position: 'absolute', left: 200, right: 200, top: 470, height: 40, background: `linear-gradient(180deg, ${C.ice}aa, ${C.ice}22)`, boxShadow: `0 0 40px ${C.ice}66` }} />
      {['BTC', 'ETH'].map((t, i) => (
        <div key={t} style={{ position: 'absolute', left: 620 + i * 480, top: lerp(220, 640, d) }}>
          <TokenCircle ticker={t} size={200} color={C.gold} />
          {d > 0.45 && <div style={{ position: 'absolute', left: 60, top: -120 * (d - 0.45), width: 80, height: 120 * (d - 0.45), background: `linear-gradient(0deg, ${C.gold}66, transparent)` }} />}
        </div>
      ))}
      <div style={{ position: 'absolute', left: 0, right: 0, top: 140, textAlign: 'center' }}>
        <Kicker size={26} color={C.gold}>NO COMPANY CAN FREEZE THEM</Kicker>
      </div>
    </AbsoluteFill>
  );
};

export const FlowLines: React.FC<{ lines: { from: string; to: string; note: string; at: number; color?: string }[] }> = ({ lines }) => {
  const f = useF();
  return (
    <AbsoluteFill>
      {lines.map((l, i) => {
        const v = damp(f, l.at, 14);
        const ar = prog(f, l.at + 6, 16, outPow3);
        return (
          <div key={i} style={{ position: 'absolute', left: 200, top: 250 + i * 230, opacity: v, display: 'flex', alignItems: 'center', gap: 34 }}>
            <Panel style={{ padding: '20px 30px' }}>
              <div style={{ fontFamily: F.display, fontSize: 64, color: l.color ?? C.gold }}>{l.from}</div>
            </Panel>
            <div style={{ width: 230 * ar, height: 6, background: C.alarm }} />
            <Panel border={C.alarm} style={{ padding: '20px 30px', opacity: prog(f, l.at + 18, 10) }}>
              <div style={{ fontFamily: F.display, fontSize: 64, color: C.bone }}>{l.to}</div>
            </Panel>
            <Kicker size={22} color={C.alarm} style={{ opacity: prog(f, l.at + 24, 10) }}>{l.note}</Kicker>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

/** Bitget-hack funds and Binance-hack funds converge into one address node. */
export const ConvergeFlows: React.FC = () => {
  const f = useF();
  const p = prog(f, 6, 36, outPow3);
  const node = pop(f, 40, 10);
  return (
    <AbsoluteFill>
      <svg width={1920} height={1080} style={{ position: 'absolute', inset: 0 }}>
        <path d="M 260 250 C 800 250, 900 450, 1340 450" fill="none" stroke={C.mute} strokeWidth={10} strokeDasharray={1300} strokeDashoffset={1300 * (1 - p)} />
        <path d="M 260 650 C 800 650, 900 450, 1340 450" fill="none" stroke={C.alarm} strokeWidth={10} strokeDasharray={1300} strokeDashoffset={1300 * (1 - p)} />
      </svg>
      <div style={{ position: 'absolute', left: 120, top: 180 }}>
        <div style={{ fontFamily: F.display, fontSize: 58, color: C.bone }}>BITGET HACK</div>
        <Kicker size={20}>SEP 2026</Kicker>
      </div>
      <div style={{ position: 'absolute', left: 120, top: 690 }}>
        <div style={{ fontFamily: F.display, fontSize: 58, color: C.alarm }}>BINANCE HACK</div>
        <Kicker size={20}>OCT 2026</Kicker>
      </div>
      <div style={{ position: 'absolute', left: 1340 - 80, top: 450 - 80, width: 160, height: 160, borderRadius: 160, border: `4px solid ${C.gold}`, background: `radial-gradient(circle, ${C.gold}55, ${C.panel})`, transform: `scale(${node || 0.01})`, boxShadow: `0 0 50px ${C.gold}` }} />
      <div style={{ position: 'absolute', left: 1480, top: 420, opacity: prog(f, 46, 12) }}>
        <div style={{ fontFamily: F.display, fontSize: 56, color: C.gold }}>SAME ADDRESS</div>
        <Kicker size={18}>FUNDS COMMINGLED</Kicker>
      </div>
    </AbsoluteFill>
  );
};

export const DenyCard: React.FC = () => {
  const f = useF();
  return (
    <Center gap={34}>
      <div style={{ fontFamily: F.display, fontSize: 120, color: C.mute, letterSpacing: '0.05em', opacity: prog(f, 0, 12) }}>NORTH KOREA DENIES INVOLVEMENT</div>
      <div style={{ fontFamily: F.body, fontWeight: 700, fontSize: 70, color: C.bone, opacity: prog(f, 10, 12) }}>“absurd rhetoric”</div>
      <Kicker size={22} style={{ opacity: prog(f, 18, 12) }}>KIM YO JONG, VIA STATE MEDIA (KCNA) · NOV 3, 2026</Kicker>
    </Center>
  );
};

export const LineCard: React.FC<{ text: string; sub?: string; color?: string }> = ({ text, sub, color = C.bone }) => {
  const f = useF();
  const v = damp(f, 0, 16);
  return (
    <Center gap={20}>
      <div style={{ fontFamily: F.display, fontSize: 96, color, letterSpacing: '0.04em', maxWidth: 1600, opacity: v, transform: `translateY(${(1 - v) * 24}px)` }}>{text}</div>
      {sub && <Kicker size={22} style={{ opacity: prog(f, 10, 12) }}>{sub}</Kicker>}
    </Center>
  );
};

/** Generic recruiter email (fictional names/company) with a glowing attachment. */
export const RecruiterEmail: React.FC<{ subject?: string; attachment?: string; label?: string }> = ({ subject = 'Exciting opportunity — next steps', attachment = 'pre_employment_test', label = 'ILLUSTRATION · FICTIONAL MESSAGE' }) => {
  const f = useF();
  const v = damp(f, 0, 14);
  const att = prog(f, 16, 12);
  return (
    <Center>
      <div style={{ opacity: v, transform: `translateY(${(1 - v) * 30}px)` }}>
        <Panel style={{ width: 1050, padding: 46 }}>
          <Kicker size={18}>FROM: “RECRUITER” · FICTIONAL COMPANY</Kicker>
          <div style={{ fontFamily: F.body, fontWeight: 700, fontSize: 44, color: C.bone, marginTop: 14 }}>{subject}</div>
          {[0.92, 0.8, 0.86, 0.6].map((w, i) => (
            <div key={i} style={{ height: 16, width: `${w * 100}%`, background: C.line, borderRadius: 8, marginTop: 20 }} />
          ))}
          <div style={{ marginTop: 34, display: 'inline-flex', alignItems: 'center', gap: 18, border: `2px solid ${C.alarm}`, borderRadius: 10, padding: '16px 24px', opacity: att, boxShadow: `0 0 ${20 + 20 * Math.sin(f / 6)}px ${C.alarm}88` }}>
            <svg width={34} height={40}>
              <path d="M2 2 H22 L32 12 V38 H2 Z" fill="none" stroke={C.alarm} strokeWidth={3} />
            </svg>
            <span style={{ fontFamily: F.mono, fontSize: 28, color: C.alarm }}>{attachment}</span>
          </div>
        </Panel>
        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <Kicker size={18}>{label}</Kicker>
        </div>
      </div>
    </Center>
  );
};

export const Checklist: React.FC<{ title: string; items: string[]; step?: number }> = ({ title, items, step = 14 }) => {
  const f = useF();
  return (
    <AbsoluteFill>
      <div style={{ position: 'absolute', left: 300, top: 200 }}>
        <Kicker size={26} color={C.alarm}>{title}</Kicker>
        {items.map((t, i) => {
          const v = damp(f, 8 + i * step, 12);
          return (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 30, marginTop: 40, opacity: v, transform: `translateX(${(1 - v) * -30}px)` }}>
              <div style={{ width: 60, height: 60, border: `3px solid ${C.alarm}`, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: F.display, fontSize: 50, color: C.alarm }}>✓</div>
              <div style={{ fontFamily: F.display, fontSize: 84, color: C.bone }}>{t}</div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

export const NameCard: React.FC<{ name: string; role: string; line?: string }> = ({ name, role, line }) => {
  const f = useF();
  const v = damp(f, 0, 16);
  return (
    <AbsoluteFill>
      <div style={{ position: 'absolute', left: 260, top: 300, opacity: v, transform: `translateX(${(1 - v) * -40}px)` }}>
        <div style={{ display: 'flex', gap: 30 }}>
          <div style={{ width: 8, background: C.gold }} />
          <div>
            <div style={{ fontFamily: F.display, fontSize: 110, color: C.bone }}>{name}</div>
            <Kicker size={26} color={C.gold}>{role}</Kicker>
            {line && <div style={{ fontFamily: F.body, fontSize: 38, color: C.mute, marginTop: 30, maxWidth: 1200, opacity: prog(f, 14, 12) }}>{line}</div>}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const StatusBoard: React.FC<{ items: string[] }> = ({ items }) => {
  const f = useF();
  return (
    <AbsoluteFill>
      <div style={{ position: 'absolute', left: 260, top: 170 }}>
        <Kicker size={24} color={C.green}>NOV 1, 2026 · FROM 06:00 UTC · PHASE ONE: 15 NETWORKS</Kicker>
      </div>
      {items.map((t, i) => {
        const on = f >= 8 + i * 9;
        return (
          <div key={t} style={{ position: 'absolute', left: 260 + (i % 4) * 360, top: 260 + Math.floor(i / 4) * 170, width: 320, height: 130 }}>
            <Panel border={on ? C.green : C.line} style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 20, boxShadow: on ? `0 0 30px ${C.green}44` : undefined }}>
              <div style={{ width: 18, height: 18, borderRadius: 18, background: on ? C.green : C.alarm }} />
              <div style={{ fontFamily: F.mono, fontWeight: 700, fontSize: 40, color: C.bone }}>{t}</div>
              <div style={{ fontFamily: F.display, fontSize: 40, color: on ? C.green : C.mute }}>{on ? '✓' : '…'}</div>
            </Panel>
            {i === 0 && <div style={{ position: 'absolute', top: 140, left: 0, width: 320, textAlign: 'center' }}><Kicker size={16} color={C.green}>FIRST · ~06:20 UTC</Kicker></div>}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

/** Fictional job-platform message (Binance's Nov 3 report: a recruiter approached an engineer). */
export const JobMessage: React.FC = () => {
  const f = useF();
  const v = damp(f, 0, 14);
  const msg = 'Hi — we are hiring for a senior role and think you could be a great fit. Are you open to a quick video call?';
  return (
    <AbsoluteFill>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 120, textAlign: 'center' }}>
        <Kicker size={22} color={C.gold}>SEPTEMBER 2026 · PER BINANCE'S INITIAL INCIDENT REPORT (NOV 3)</Kicker>
      </div>
      <div style={{ position: 'absolute', left: 460, top: 230, opacity: v, transform: `translateY(${(1 - v) * 30}px)` }}>
        <Panel style={{ width: 1000, padding: 40 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
            <div style={{ width: 70, height: 70, borderRadius: 70, background: C.line }} />
            <div>
              <div style={{ fontFamily: F.body, fontWeight: 700, fontSize: 32, color: C.bone }}>“Project Director” · Fictional Company</div>
              <Kicker size={16}>JOB PLATFORM · NEW MESSAGE</Kicker>
            </div>
          </div>
          <div style={{ marginTop: 30, background: '#1a1e24', borderRadius: 14, padding: 26, fontFamily: F.body, fontSize: 32, color: C.bone, lineHeight: 1.4, minHeight: 130 }}>{typeOn(msg, f, 10, 45)}</div>
        </Panel>
        <div style={{ textAlign: 'center', marginTop: 14 }}>
          <Kicker size={16}>ILLUSTRATION · FICTIONAL NAMES AND TEXT</Kicker>
        </div>
      </div>
    </AbsoluteFill>
  );
};

/** Two faceless video-call tiles; the "CEO" tile glitches to FICTITIOUS COMPANY. */
export const VideoTiles: React.FC<{ ceoAt: number }> = ({ ceoAt }) => {
  const f = useF();
  const tile = (label: string, at: number, glitchAt?: number) => {
    const v = damp(f, at, 14);
    const g = glitchAt !== undefined && f >= glitchAt ? prog(f, glitchAt, 10) : 0;
    return (
      <div style={{ width: 720, height: 460, opacity: v, transform: `translateY(${(1 - v) * 30}px) translateX(${g > 0 && g < 1 ? jitter(f, label, 1) * 14 : 0}px)`, position: 'relative' }}>
        <Panel border={g > 0 ? C.alarm : C.line} style={{ position: 'absolute', inset: 0, overflow: 'hidden', background: '#0b0d10' }}>
          <svg width={720} height={460} style={{ position: 'absolute', inset: 0 }}>
            <circle cx={360} cy={190} r={80} fill="#1b2027" />
            <path d="M 200 460 C 210 320, 510 320, 520 460 Z" fill="#1b2027" />
          </svg>
          <div style={{ position: 'absolute', left: 24, bottom: 20, fontFamily: F.mono, fontSize: 26, color: C.bone, background: 'rgba(0,0,0,.6)', padding: '6px 14px' }}>“{label}”</div>
          {g > 0 && (
            <AbsoluteFill style={{ alignItems: 'center', justifyContent: 'center', background: `rgba(7,8,11,${0.75 * g})` }}>
              <div style={{ opacity: g }}>
                <Stamp text="FICTITIOUS COMPANY" at={glitchAt! + 4} size={52} color={C.alarm} rotate={-4} />
              </div>
            </AbsoluteFill>
          )}
          <GlitchBars f={f} amount={g > 0 && g < 1 ? 1 - g : 0} seed={label} />
        </Panel>
      </div>
    );
  };
  return (
    <AbsoluteFill style={{ alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ display: 'flex', gap: 60, marginTop: -120 }}>
        {tile('HR', 0)}
        {tile('CEO', ceoAt, ceoAt + 30)}
      </div>
    </AbsoluteFill>
  );
};

export const FolderAlarm: React.FC = () => {
  const f = useF();
  const red = prog(f, 8, 14);
  const col = red > 0.5 ? C.alarm : C.gold;
  return (
    <Center gap={30}>
      <svg width={420} height={320} viewBox="0 0 420 320" style={{ filter: `drop-shadow(0 0 ${30 * red}px ${C.alarm})`, transform: `scale(${1 + 0.05 * pop(f, 8, 10)})` }}>
        <path d="M 20 60 L 160 60 L 190 30 L 400 30 L 400 300 L 20 300 Z" fill={`${col}22`} stroke={col} strokeWidth={8} strokeLinejoin="round" />
      </svg>
      <div style={{ fontFamily: F.mono, fontSize: 56, color: col }}>take-home assignment/</div>
      <Kicker size={20} style={{ opacity: prog(f, 16, 12) }}>A MALICIOUS “ASSIGNMENT” · PER BINANCE · CONTENTS NOT SHOWN</Kicker>
    </Center>
  );
};

/** 2019 vs 2026 split; the 2026 bar grows ~157× and rises out of frame. */
export const SplitCompare: React.FC<{ growAt: number }> = ({ growAt }) => {
  const f = useF();
  const g = prog(f, growAt, 40, inPow3);
  return (
    <AbsoluteFill>
      <div style={{ position: 'absolute', left: 0, top: 0, width: 960, bottom: 0, filter: 'sepia(.5) saturate(.6) contrast(1.05)', background: '#120e0a' }}>
        <div style={{ position: 'absolute', left: 140, top: 160 }}>
          <div style={{ fontFamily: F.display, fontSize: 96, color: C.bone }}>2019</div>
          <div style={{ fontFamily: F.display, fontSize: 130, color: C.gold }}>$40M</div>
          <Kicker size={20}>USER ACCOUNTS</Kicker>
        </div>
        <div style={{ position: 'absolute', left: 660, top: 780 - 4, width: 120, height: 4, background: C.gold }} />
      </div>
      <div style={{ position: 'absolute', left: 960, top: 0, width: 960, bottom: 0, background: C.ink, opacity: prog(f, 0, 10) }}>
        <div style={{ position: 'absolute', left: 100, top: 160, opacity: prog(f, growAt - 10, 10) }}>
          <div style={{ fontFamily: F.display, fontSize: 96, color: C.bone }}>2026</div>
          <div style={{ fontFamily: F.display, fontSize: 130, color: C.alarm }}>~$6.3B</div>
          <Kicker size={20}>THE EXCHANGE'S OWN SYSTEMS</Kicker>
        </div>
        <div style={{ position: 'absolute', left: 600, top: 780 - Math.max(4, 4 * 157 * g), width: 120, height: Math.max(4, 4 * 157 * g), background: `linear-gradient(0deg, ${C.alarm}, ${C.alarm}55)`, boxShadow: `0 0 50px ${C.alarm}` }} />
      </div>
      <div style={{ position: 'absolute', left: 958, top: 0, width: 4, bottom: 0, background: C.line }} />
    </AbsoluteFill>
  );
};

export const TipCards: React.FC<{ ats: number[] }> = ({ ats }) => {
  const f = useF();
  const tips = [
    { t: 'HARDWARE KEY OR PASSKEY 2FA', i: 'M30 50 a16 16 0 1 1 0.1 0 M46 50 H90 M76 50 V64 M86 50 V60' },
    { t: 'WITHDRAWAL ADDRESS WHITELIST', i: 'M24 24 H86 M24 48 H86 M24 72 H66 M12 24 h0.1 M12 48 h0.1 M12 72 h0.1' },
    { t: "DON'T KEEP MORE THAN YOU TRADE", i: 'M14 30 H86 V80 H14 Z M14 44 H86 M66 58 h10' },
    { t: 'UNSOLICITED “CODING TESTS” = LIVE WIRE', i: 'M20 34 H80 V80 H20 Z M38 34 V22 H62 V34 M50 46 V62 M50 70 v0.1' },
  ];
  return (
    <AbsoluteFill>
      {tips.map((tp, i) => {
        const v = damp(f, ats[i], 14);
        return (
          <div key={i} style={{ position: 'absolute', left: 150 + i * 415, top: 260, width: 380, height: 420, opacity: v, transform: `translateY(${(1 - v) * 40}px)` }}>
            <Panel border={i === 3 ? C.alarm : C.line} style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 30, padding: 26, boxSizing: 'border-box' }}>
              <svg width={120} height={100} viewBox="0 0 100 100">
                <path d={tp.i} fill="none" stroke={i === 3 ? C.alarm : C.gold} strokeWidth={5} strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <div style={{ fontFamily: F.display, fontSize: 50, lineHeight: 1.05, color: C.bone, textAlign: 'center', letterSpacing: '0.04em' }}>{tp.t}</div>
            </Panel>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

export const EndScreen: React.FC = () => {
  const f = useF();
  const v = damp(f, 0, 20);
  return (
    <AbsoluteFill style={{ opacity: v }}>
      <div style={{ position: 'absolute', left: 140, top: 250 }}>
        <div style={{ fontFamily: F.display, fontSize: 120, color: C.bone, lineHeight: 1 }}>THIS STORY</div>
        <div style={{ fontFamily: F.display, fontSize: 120, color: C.alarm, lineHeight: 1 }}>ISN'T OVER.</div>
        <div style={{ marginTop: 40, width: 380, height: 380, borderRadius: 380, border: `3px dashed ${C.line}`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Kicker size={22}>SUBSCRIBE</Kicker>
        </div>
      </div>
      {[0, 1].map((k) => (
        <div key={k} style={{ position: 'absolute', left: 980, top: 170 + k * 330, width: 800, height: 290, border: `2px solid ${C.line}`, borderRadius: 12, background: 'rgba(19,22,27,.5)', opacity: prog(f, 10 + k * 8, 14) }} />
      ))}
      <div style={{ position: 'absolute', left: 0, right: 0, top: 840, textAlign: 'center', opacity: prog(f, 24, 14) }}>
        <Kicker size={22}>SOURCES IN THE DESCRIPTION · FACTS AS OF NOV 3, 2026</Kicker>
      </div>
    </AbsoluteFill>
  );
};

export const FlashbackGrade: React.FC<{ children: React.ReactNode; stamp?: string }> = ({ children, stamp = 'MAY 07 2019 · 17:15:24 UTC' }) => {
  const f = useF();
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ filter: 'sepia(.42) saturate(.62) hue-rotate(-12deg) contrast(1.06) brightness(.95) blur(.5px)' }}>{children}</AbsoluteFill>
      <AbsoluteFill style={{ background: 'linear-gradient(180deg, rgba(40,90,90,.12), rgba(120,70,20,.12))', mixBlendMode: 'overlay' }} />
      <AbsoluteFill style={{ opacity: 0.14, backgroundImage: 'repeating-linear-gradient(0deg, rgba(0,0,0,.9) 0, rgba(0,0,0,.9) 2px, transparent 2px, transparent 4px)' }} />
      <div style={{ position: 'absolute', left: 0, right: 0, top: ((f * 7) % 1250) - 100, height: 18, background: 'rgba(255,255,255,.08)', filter: 'blur(2px)' }} />
      <div style={{ position: 'absolute', right: 110, top: 70, fontFamily: F.mono, fontSize: 30, color: '#f3e7c9', textShadow: '2px 0 #ff4040aa, -2px 0 #40e0ffaa', letterSpacing: '0.08em' }}>{stamp}</div>
      <div style={{ position: 'absolute', left: 110, top: 70, fontFamily: F.mono, fontSize: 28, color: '#f3e7c9', opacity: Math.floor(f / 20) % 2 ? 1 : 0.4 }}>▶ PLAY</div>
    </AbsoluteFill>
  );
};

export const Dim: React.FC<{ children: React.ReactNode; amount?: number }> = ({ children, amount = 0.25 }) => <AbsoluteFill style={{ opacity: amount }}>{children}</AbsoluteFill>;

export { interpolate, Counter, outExpo, lerp };
