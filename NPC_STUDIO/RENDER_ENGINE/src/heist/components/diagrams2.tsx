import React from 'react';
import { AbsoluteFill, interpolate } from 'remotion';
import { C, F } from '../theme';
import { useF } from '../lib/frame';
import { clamp, damp, inPow3, jitter, lerp, outExpo, outPow3, pop, prog, rnd } from '../lib/anim';
import { Center, GlitchBars, Kicker, Panel, Stamp } from './core';

/* ------------------------------------------------------------------ ChapterCard (2.5 s) */

export const ChapterCard: React.FC<{ n: number; title: string; date?: string | null; lead?: number }> = ({ n, title, date, lead = 0 }) => {
  const f = useF() - lead;
  const a = prog(f, 2, 16);
  const u = prog(f, 12, 18, outPow3);
  const out = 1 - prog(f, 64, 11, inPow3);
  return (
    <AbsoluteFill style={{ background: C.ink, opacity: out }}>
      <Center gap={14}>
        <Kicker size={30} style={{ opacity: a, letterSpacing: '0.3em' }}>{`CHAPTER ${String(n).padStart(2, '0')}`}</Kicker>
        <div style={{ overflow: 'hidden' }}>
          <div style={{ fontFamily: F.display, fontSize: 170, color: C.bone, letterSpacing: '0.06em', lineHeight: 1, transform: `translateY(${(1 - a) * 100}%)` }}>{title}</div>
        </div>
        <div style={{ height: 6, width: 520, background: C.alarm, transform: `scaleX(${u})`, boxShadow: `0 0 20px ${C.alarm}` }} />
        {date && <Kicker size={24} style={{ opacity: prog(f, 18, 14), marginTop: 8 }}>{date}</Kicker>}
      </Center>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ TitleCard (glitch-slice assembly) */

export const TitleCard: React.FC = () => {
  const f = useF();
  const slices = 12;
  const settle = prog(f, 0, 26, outExpo);
  const out = 1 - prog(f, 108, 12, inPow3);
  return (
    <AbsoluteFill style={{ background: C.ink, opacity: out }}>
      <Center gap={30}>
        <div style={{ position: 'relative', width: 1840, height: 250 }}>
          {Array.from({ length: slices }, (_, i) => {
            const off = (rnd(`ts${i}`) - 0.5) * 900 * (1 - settle) + (f > 26 && f < 34 ? jitter(f, `tj${i}`, 1) * 24 : 0);
            return (
              <div key={i} style={{ position: 'absolute', inset: 0, clipPath: `inset(${(i / slices) * 100}% 0 ${100 - ((i + 1) / slices) * 100}% 0)`, transform: `translateX(${off}px)`, textAlign: 'center', whiteSpace: 'nowrap', fontFamily: F.display, fontSize: 200, lineHeight: '250px', letterSpacing: '0.03em', color: i % 4 === 1 && settle < 0.9 ? C.alarm : C.bone, textShadow: settle > 0.95 ? `0 0 40px ${C.alarm}55` : 'none' }}>
                THE 20-MINUTE HEIST
              </div>
            );
          })}
        </div>
        <div style={{ height: 4, width: 760, background: C.alarm, transform: `scaleX(${prog(f, 20, 20, outPow3)})` }} />
        <Kicker size={30} color={C.mute} style={{ opacity: prog(f, 28, 16), letterSpacing: '0.32em' }}>BINANCE · OCTOBER 29, 2026</Kicker>
      </Center>
      <GlitchBars f={f} amount={1 - settle} seed="title" />
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ DossierReveal */

export const DossierReveal: React.FC<{ at?: number }> = ({ at = 0 }) => {
  const f = useF();
  const open = prog(f, at, 18, outPow3);
  return (
    <AbsoluteFill>
      <div style={{ position: 'absolute', left: 460, top: 160, width: 1000, height: 600, perspective: 1600 }}>
        <div style={{ position: 'absolute', inset: 0, background: '#2a2216', border: '2px solid #5b4a2c', borderRadius: 10, boxShadow: '0 40px 100px rgba(0,0,0,.6)' }} />
        <div style={{ position: 'absolute', inset: 24, background: '#e9e2d0', borderRadius: 4, padding: 46, boxSizing: 'border-box', color: '#1b1b1b' }}>
          <div style={{ fontFamily: F.mono, fontSize: 20, letterSpacing: '0.2em', opacity: 0.7 }}>THREAT ACTOR PROFILE · ATTRIBUTION SUMMARY</div>
          <div style={{ marginTop: 40, opacity: prog(f, at + 22, 12) }}>
            <Stamp text="TRADERTRAITOR" at={at + 18} color="#c4161c" size={130} rotate={-4} />
          </div>
          <div style={{ marginTop: 40, fontFamily: F.body, fontWeight: 600, fontSize: 30, lineHeight: 1.5, opacity: prog(f, at + 30, 14) }}>
            North Korean state-backed hacking unit
            <br />
            <span style={{ fontFamily: F.mono, fontSize: 22, fontWeight: 500 }}>A.K.A. JADE SLEET · LAZARUS GROUP SUBUNIT (PER RESEARCHERS)</span>
          </div>
        </div>
        <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(160deg, #3b2f1c, #241c10)', border: '2px solid #5b4a2c', borderRadius: 10, transformOrigin: 'left center', transform: `rotateY(${-170 * open}deg)`, backfaceVisibility: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ width: 120, height: 120, borderRadius: 120, background: '#8d1414', boxShadow: '0 0 30px #8d141488' }} />
        </div>
      </div>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 110, textAlign: 'center', opacity: prog(f, at + 38, 14) }}>
        <Kicker color={C.bone} size={22}>ATTRIBUTION: TRM LABS · CHAINALYSIS · ELLIPTIC · FBI</Kicker>
      </div>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ HeistTimeline (bars scaled to value) */

export const HeistTimeline: React.FC<{ at?: number; binanceAt?: number }> = ({ at = 0, binanceAt = 1e9 }) => {
  const f = useF();
  const per = 300 / 1.5; // px per $1B — Bybit's $1.5B is 380 px tall
  const bars = [
    { k: 'DMM BITCOIN', d: 'MAY 2024', v: 0.308, lab: '~$308M', at: at },
    { k: 'BYBIT', d: 'FEB 2025', v: 1.5, lab: '~$1.5B', sub: 'FBI: TRADERTRAITOR', at: at + 8 },
    { k: 'BITGET', d: 'SEP 2026', v: 0.352, lab: '$352M+', at: at + 16 },
    { k: 'BINANCE', d: 'OCT 2026', v: 6.3, lab: '~$6.3B', at: binanceAt },
  ];
  const base = 620;
  return (
    <AbsoluteFill>
      <div style={{ position: 'absolute', left: 260, right: 260, top: base, height: 2, background: C.line }} />
      {bars.map((b, i) => {
        const g = prog(f, b.at, b.k === 'BINANCE' ? 22 : 18, b.k === 'BINANCE' ? inPow3 : outExpo);
        const h = b.v * per * g;
        const x = 380 + i * 330;
        const col = b.k === 'BINANCE' ? C.alarm : C.mute;
        return (
          <div key={b.k} style={{ position: 'absolute', left: x, top: 0, width: 200, opacity: prog(f, b.at, 6) }}>
            <div style={{ position: 'absolute', top: base - h, width: 200, height: h, background: `linear-gradient(180deg, ${col}, ${col}55)`, boxShadow: b.k === 'BINANCE' ? `0 0 60px ${C.alarm}` : 'none' }} />
            <div style={{ position: 'absolute', top: Math.max(120, base - h - 80), width: 260, left: -30, textAlign: 'center', fontFamily: F.display, fontSize: 60, color: b.k === 'BINANCE' ? C.alarm : C.bone }}>{b.lab}</div>
            <div style={{ position: 'absolute', top: base + 16, width: 260, left: -30, textAlign: 'center' }}>
              <div style={{ fontFamily: F.display, fontSize: 40, color: C.bone }}>{b.k}</div>
              <Kicker size={16}>{b.d}</Kicker>
              {b.sub && <Kicker size={14} color={C.alarm}>{b.sub}</Kicker>}
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ PlaybookCards */

export const PlaybookCards: React.FC<{ at: number; step?: number; highlightAt?: number; stamped?: boolean }> = ({ at, step = 18, highlightAt = 1e9 }) => {
  const f = useF();
  const items = [
    { t: 'FAKE JOB OFFERS', icon: 'M20 30 h60 v44 h-60 z M38 30 v-10 h24 v10' },
    { t: 'POISONED CODE', icon: 'M30 30 l-16 20 l16 20 M70 30 l16 20 l-16 20 M58 22 l-16 56' },
    { t: 'TRUSTED MACHINES', icon: 'M18 24 h64 v42 h-64 z M10 76 h80' },
  ];
  const hl = f >= highlightAt;
  return (
    <AbsoluteFill>
      {items.map((it, i) => {
        const t = clamp((f - at - i * step) / 8);
        const sc = interpolate(t, [0, 0.7, 1], [1.6, 0.96, 1]);
        const dim = hl && i > 0 ? 0.25 : 1;
        const lit = hl && i === 0;
        return (
          <div key={i} style={{ position: 'absolute', left: 190 + i * 540, top: 230, width: 480, height: 400, opacity: Math.min(1, t * 2) * dim, transform: `scale(${sc}) rotate(${(i - 1) * 2}deg)` }}>
            <Panel border={lit ? C.alarm : C.line} style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 30, boxShadow: lit ? `0 0 80px ${C.alarm}66` : undefined }}>
              <svg width={130} height={110} viewBox="0 0 100 90">
                <path d={it.icon} fill="none" stroke={lit ? C.alarm : C.bone} strokeWidth={5} strokeLinejoin="round" strokeLinecap="round" />
              </svg>
              <div style={{ fontFamily: F.display, fontSize: 68, color: lit ? C.alarm : C.bone, letterSpacing: '0.05em', textAlign: 'center' }}>{it.t}</div>
            </Panel>
          </div>
        );
      })}
      <div style={{ position: 'absolute', left: 0, right: 0, top: 690, textAlign: 'center', opacity: prog(f, at + step * 3, 14) }}>
        <Kicker size={22}>DOCUMENTED TACTICS (FBI, CISA)</Kicker>
      </div>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ MarketBoard (sourced figures only) */

export const MarketBoard: React.FC<{ at?: number }> = ({ at = 0 }) => {
  const f = useF();
  const rows = [
    { k: 'BTC', v: '$76,368', d: '6-WEEK LOW' },
    { k: 'ETH', v: '$2,178', d: '2-MONTH LOW' },
  ];
  const tick = ['BNB ~−5%', 'COINBASE −4.8%', 'STRATEGY ~−6% (AFTER HOURS)'];
  return (
    <AbsoluteFill>
      <div style={{ position: 'absolute', left: 200, top: 170 }}>
        <Kicker size={22} color={C.alarm}>OCT 29–30, 2026 · AFTER 20:05 UTC</Kicker>
      </div>
      {rows.map((r, i) => {
        const v = damp(f, at + i * 14, 16);
        return (
          <div key={r.k} style={{ position: 'absolute', left: 200, top: 230 + i * 200, opacity: v, transform: `translateX(${(1 - v) * -40}px)`, display: 'flex', alignItems: 'center', gap: 50 }}>
            <div style={{ width: 150, fontFamily: F.mono, fontWeight: 700, fontSize: 56, color: C.bone }}>{r.k}</div>
            <svg width={90} height={90} viewBox="0 0 90 90">
              <path d={`M45 10 V${10 + 60 * v} M20 ${50 + 20 * v} L45 ${75 * v + 5} L70 ${50 + 20 * v}`} stroke={C.alarm} strokeWidth={8} fill="none" strokeLinecap="round" />
            </svg>
            <div style={{ fontFamily: F.display, fontSize: 150, color: C.alarm, lineHeight: 1, fontVariantNumeric: 'tabular-nums' }}>{r.v}</div>
            <Kicker size={28} color={C.bone}>{r.d}</Kicker>
          </div>
        );
      })}
      <div style={{ position: 'absolute', left: 0, right: 0, top: 700, height: 64, background: C.panel, borderTop: `1px solid ${C.line}`, borderBottom: `1px solid ${C.line}`, overflow: 'hidden', opacity: prog(f, at + 30, 12) }}>
        <div style={{ whiteSpace: 'nowrap', fontFamily: F.mono, fontSize: 28, color: C.bone, lineHeight: '64px', transform: `translateX(${1920 - ((f - at) * 4) % 3600}px)` }}>
          {[...tick, ...tick, ...tick].map((t, i) => (
            <span key={i} style={{ marginRight: 90, color: i % 3 === 0 ? C.alarm : C.bone }}>▼ {t}</span>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ Bars (generic honest-scale comparison) */

export const Bars: React.FC<{ items: { label: string; value: number; text: string; color?: string; at: number }[]; max?: number; y?: number; width?: number; title?: string; vertical?: boolean }> = ({
  items,
  max,
  y = 300,
  width = 1100,
  title,
}) => {
  const f = useF();
  const m = max ?? Math.max(...items.map((i) => i.value));
  return (
    <AbsoluteFill>
      {title && (
        <div style={{ position: 'absolute', left: 240, top: y - 90 }}>
          <Kicker size={24} color={C.bone}>{title}</Kicker>
        </div>
      )}
      {items.map((it, i) => {
        const g = prog(f, it.at, 22, outExpo);
        return (
          <div key={i} style={{ position: 'absolute', left: 240, top: y + i * 130, opacity: prog(f, it.at, 6) }}>
            <div style={{ fontFamily: F.mono, fontSize: 24, color: C.mute, letterSpacing: '0.1em', marginBottom: 10 }}>{it.label}</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 26 }}>
              <div style={{ height: 54, width: (it.value / m) * width * g, background: it.color ?? C.gold, boxShadow: `0 0 24px ${(it.color ?? C.gold) + '55'}` }} />
              <div style={{ fontFamily: F.display, fontSize: 66, color: it.color ?? C.gold, opacity: prog(f, it.at + 12, 8) }}>{it.text}</div>
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ FlowDonut */

export const FlowDonut: React.FC<{ at?: number }> = ({ at = 0 }) => {
  const f = useF();
  const p = prog(f, at, 40, outPow3);
  const R = 220;
  const circ = 2 * Math.PI * R;
  const out = 4.65 / (4.65 + 1.01);
  const pct = prog(f, at + 34, 24);
  return (
    <AbsoluteFill>
      <svg width={1920} height={1080} style={{ position: 'absolute', inset: 0 }}>
        <g transform="translate(640 430) rotate(-90)">
          <circle r={R} fill="none" stroke={C.line} strokeWidth={56} />
          <circle r={R} fill="none" stroke={C.alarm} strokeWidth={56} strokeDasharray={`${circ * out * p} ${circ}`} />
          <circle r={R} fill="none" stroke={C.ice} strokeWidth={56} strokeDasharray={`${circ * (1 - out) * p} ${circ}`} strokeDashoffset={-circ * out * p} />
        </g>
      </svg>
      <div style={{ position: 'absolute', left: 640 - 200, top: 430 - 80, width: 400, textAlign: 'center' }}>
        <Kicker size={22}>NET OUTFLOW · NOV 1</Kicker>
        <div style={{ fontFamily: F.display, fontSize: 104, color: C.bone, lineHeight: 1, opacity: prog(f, at + 20, 12) }}>−$3.64B</div>
      </div>
      <div style={{ position: 'absolute', left: 1040, top: 250, opacity: damp(f, at + 6, 14) }}>
        <div style={{ fontFamily: F.display, fontSize: 90, color: C.alarm }}>$4.65B OUT</div>
        <div style={{ fontFamily: F.display, fontSize: 90, color: C.ice }}>$1.01B IN</div>
        <div style={{ marginTop: 40, opacity: pct }}>
          <Kicker size={24} color={C.bone}>= 2.1% OF ~$171B TOTAL ASSETS</Kicker>
          <div style={{ marginTop: 16, width: 620, height: 26, background: C.line, position: 'relative' }}>
            <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 620 * 0.021 * pct, minWidth: pct > 0 ? 6 : 0, background: C.alarm, boxShadow: `0 0 14px ${C.alarm}` }} />
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ ProgressRing */

export const ProgressRing: React.FC<{ at?: number; from?: number; to?: number; label: string }> = ({ at = 0, from = 90, to = 95, label }) => {
  const f = useF();
  const v = from + (to - from) * prog(f, at + 10, 40, outPow3);
  const R = 230;
  const circ = 2 * Math.PI * R;
  const a = prog(f, at, 14);
  return (
    <AbsoluteFill style={{ opacity: a }}>
      <svg width={1920} height={1080} style={{ position: 'absolute', inset: 0 }}>
        <g transform="translate(960 430) rotate(-90)">
          <circle r={R} fill="none" stroke={C.line} strokeWidth={34} />
          <circle r={R} fill="none" stroke={C.gold} strokeWidth={34} strokeLinecap="round" strokeDasharray={`${(circ * v) / 100} ${circ}`} style={{ filter: `drop-shadow(0 0 18px ${C.gold})` }} />
        </g>
      </svg>
      <Center gap={6} style={{ top: -110 }}>
        <div style={{ fontFamily: F.display, fontSize: 190, color: C.gold, lineHeight: 1, fontVariantNumeric: 'tabular-nums' }}>{Math.round(v)}%</div>
        <Kicker size={24} color={C.bone}>{label}</Kicker>
      </Center>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ QuestionCards */

export type QState = { q: string; flipAt: number; stamp: string; stampAt: number; color: string; answer?: string };
export const QuestionCards: React.FC<{ items: QState[]; at?: number; focus?: number; focusAt?: number }> = ({ items, at = 0 }) => {
  const f = useF();
  return (
    <AbsoluteFill>
      {items.map((it, i) => {
        const v = damp(f, at + i * 4, 14);
        const fl = prog(f, it.flipAt, 16, outPow3);
        const x = 130 + i * 420;
        return (
          <div key={i} style={{ position: 'absolute', left: x, top: 200, width: 380, height: 500, opacity: v, transform: `translateY(${(1 - v) * 40}px)`, perspective: 1400 }}>
            <div style={{ position: 'absolute', inset: 0, transformStyle: 'preserve-3d', transform: `rotateY(${180 - 180 * fl}deg)` }}>
              <Panel style={{ position: 'absolute', inset: 0, backfaceVisibility: 'hidden', transform: 'rotateY(180deg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <div style={{ fontFamily: F.display, fontSize: 200, color: C.line }}>?</div>
              </Panel>
              <Panel border={f >= it.stampAt ? it.color : C.line} style={{ position: 'absolute', inset: 0, backfaceVisibility: 'hidden', padding: 34, boxSizing: 'border-box', display: 'flex', flexDirection: 'column' }}>
                <Kicker size={18}>{`QUESTION ${i + 1}`}</Kicker>
                <div style={{ fontFamily: F.body, fontWeight: 700, fontSize: 38, color: C.bone, lineHeight: 1.2, marginTop: 18 }}>{it.q}</div>
                {it.answer && <div style={{ fontFamily: F.body, fontSize: 22, color: C.mute, lineHeight: 1.35, marginTop: 16, opacity: prog(f, it.stampAt + 6, 12) }}>{it.answer}</div>}
                <div style={{ marginTop: 'auto' }}>
                  <Stamp text={it.stamp} at={it.stampAt} color={it.color} size={44} rotate={-5} />
                </div>
              </Panel>
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ PeelChain */

export const PeelChain: React.FC<{ at?: number }> = ({ at = 0 }) => {
  const f = useF();
  const segs: { x1: number; y1: number; x2: number; y2: number; w: number; d: number }[] = [];
  const grow = (x: number, y: number, w: number, depth: number, spread: number) => {
    if (depth > 6) return;
    const x2 = x + 210;
    const yA = y - spread;
    const yB = y + spread;
    segs.push({ x1: x, y1: y, x2, y2: yA, w, d: depth });
    segs.push({ x1: x, y1: y, x2, y2: yB, w: w * 0.55, d: depth });
    grow(x2, yA, w * 0.8, depth + 1, spread * 0.62);
    if (depth < 3) grow(x2, yB, w * 0.5, depth + 2, spread * 0.5);
  };
  grow(260, 450, 16, 0, 170);
  return (
    <AbsoluteFill>
      <svg width={1920} height={1080} style={{ position: 'absolute', inset: 0 }}>
        <line x1={120} y1={450} x2={260} y2={450} stroke={C.gold} strokeWidth={18} opacity={prog(f, at, 6)} />
        {segs.map((s, i) => {
          const p = prog(f, at + 6 + s.d * 9, 12, outPow3);
          return <line key={i} x1={s.x1} y1={s.y1} x2={lerp(s.x1, s.x2, p)} y2={lerp(s.y1, s.y2, p)} stroke={C.gold} strokeWidth={s.w} strokeLinecap="round" opacity={0.95 - s.d * 0.1} />;
        })}
      </svg>
      <div style={{ position: 'absolute', left: 120, top: 380 }}>
        <Kicker size={22} color={C.gold}>18,270 BTC</Kicker>
      </div>
      <div style={{ position: 'absolute', right: 120, top: 760, opacity: prog(f, at + 40, 12) }}>
        <Kicker size={20}>PEEL CHAIN · SMALLER AND SMALLER TRANSFERS · TRM LABS</Kicker>
      </div>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ glitching question mark */

export const GlitchQuestion: React.FC<{ at?: number; outAt?: number }> = ({ at = 0, outAt = 1e9 }) => {
  const f = useF();
  const v = pop(f, at, 10);
  const g = f >= outAt ? prog(f, outAt, 12) : 0;
  return (
    <Center>
      <div style={{ fontFamily: F.display, fontSize: 520, color: C.alarm, lineHeight: 1, transform: `scale(${v}) translateX(${g > 0 ? jitter(f, 'q', 1) * 60 * g : 0}px)`, opacity: 1 - g, textShadow: `${8 + 20 * g}px 0 ${C.ice}, ${-8 - 20 * g}px 0 #fff3` }}>?</div>
      <GlitchBars f={f} amount={g} seed="q" />
    </Center>
  );
};
