import React from 'react';
import { AbsoluteFill, interpolate } from 'remotion';
import { C, F } from '../theme';
import { useF } from '../lib/frame';
import { clamp, damp, fmtInt, inPow3, jitter, lerp, outExpo, outPow3, pop, prog, rnd, typeOn } from '../lib/anim';
import { Kicker, Panel, Stamp, TokenCircle } from './core';

/* ------------------------------------------------------------------ ChainNetwork */

export const CHAINS = ['XRP Ledger', 'Bitcoin', 'Ethereum', 'Tron', 'Solana', 'Arbitrum', 'Optimism', 'Base', 'Avalanche', 'Polygon'];
const CX = 960;
const CY = 455;
const RX = 640;
const RY = 290;
export const nodePos = (i: number) => {
  const a = (-90 + i * 36) * (Math.PI / 180);
  return { x: CX + RX * Math.cos(a), y: CY + RY * Math.sin(a) };
};

export const ChainNetwork: React.FC<{
  assembleAt?: number;
  igniteAt?: number;
  stagger?: number;
  order?: string[];
  only?: string[]; // ignite only these on first pass
  sealsAt?: number;
  sealSkip?: string[];
  wave2At?: number;
  flashAt?: number;
  note?: { node: string; text: string; sub?: string; at: number };
  zoom?: { node: string; at: number };
  opacity?: number;
  particles?: boolean;
  coreLabel?: string;
  igniteMap?: Record<string, number>;
}> = ({ igniteMap, assembleAt = 0, igniteAt = 1e9, stagger = 5, order = CHAINS, only, sealsAt, sealSkip = [], wave2At, flashAt, note, zoom, opacity = 1, particles = true, coreLabel = 'BINANCE WALLETS' }) => {
  const f = useF();
  const ig = (name: string) => {
    if (igniteMap && igniteMap[name] !== undefined) return igniteMap[name];
    if (only && !only.includes(name)) return 1e9;
    const k = order.indexOf(name);
    return igniteAt + (k < 0 ? 0 : k) * stagger;
  };
  const w2 = (name: string) => (wave2At !== undefined && (name === 'Avalanche' || name === 'Polygon') ? wave2At : 1e9);
  let zt = '';
  if (zoom) {
    const i = CHAINS.indexOf(zoom.node);
    const p = nodePos(i);
    const z = prog(f, zoom.at, 22, outExpo);
    const S = 1 + 1.8 * z;
    zt = `translate(${(CX - p.x) * z * S}px, ${(540 - p.y) * z * S}px) scale(${S})`;
  }
  const flash = flashAt !== undefined ? Math.max(0, 1 - Math.abs(f - flashAt - 3) / 8) : 0;
  return (
    <AbsoluteFill style={{ opacity, transform: zt, transformOrigin: `${CX}px 540px` }}>
      <svg width={1920} height={1080} style={{ position: 'absolute', inset: 0 }}>
        {CHAINS.map((name, i) => {
          const p = nodePos(i);
          const a = prog(f, assembleAt + i * 2, 16);
          const on = f >= ig(name) || f >= w2(name);
          const t0 = Math.min(ig(name), w2(name));
          const hot = on ? prog(f, t0, 10) : 0;
          const len = Math.hypot(p.x - CX, p.y - CY);
          return (
            <g key={name} opacity={a}>
              <line
                x1={CX}
                y1={CY}
                x2={lerp(CX, p.x, a)}
                y2={lerp(CY, p.y, a)}
                stroke={hot > 0 ? C.alarm : C.line}
                strokeWidth={hot > 0 ? 3 : 2}
                strokeDasharray={hot > 0 ? '0' : '6 8'}
                opacity={0.4 + 0.6 * hot}
              />
              {particles &&
                hot > 0 &&
                Array.from({ length: 7 }, (_, k) => {
                  const ph = ((f - t0) / 40 + k / 7) % 1;
                  const d = ph * len;
                  return (
                    <circle
                      key={k}
                      cx={CX + ((p.x - CX) * d) / len}
                      cy={CY + ((p.y - CY) * d) / len}
                      r={3 + 2 * rnd(`${name}${k}`)}
                      fill={k % 3 === 0 ? C.gold : C.alarm}
                      opacity={(1 - ph) * hot}
                    />
                  );
                })}
            </g>
          );
        })}
      </svg>
      {/* core */}
      <div
        style={{
          position: 'absolute',
          left: CX - 130,
          top: CY - 130,
          width: 260,
          height: 260,
          borderRadius: 260,
          border: `2px solid ${f >= igniteAt ? C.alarm : C.gold}`,
          background: `radial-gradient(circle, ${(f >= igniteAt ? C.alarm : C.gold) + '33'}, ${C.panel} 70%)`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          textAlign: 'center',
          fontFamily: F.display,
          fontSize: 46,
          lineHeight: 1,
          letterSpacing: '0.06em',
          color: C.bone,
          opacity: prog(f, assembleAt, 12),
          transform: `scale(${0.6 + 0.4 * prog(f, assembleAt, 18)})`,
          boxShadow: `0 0 ${60 + 40 * flash}px ${(f >= igniteAt ? C.alarm : C.gold) + '55'}`,
        }}
      >
        {coreLabel}
      </div>
      {CHAINS.map((name, i) => {
        const p = nodePos(i);
        const a = prog(f, assembleAt + 4 + i * 2, 14);
        const on = f >= ig(name) || f >= w2(name);
        const t0 = Math.min(ig(name), w2(name));
        const hot = on ? prog(f, t0, 8) : 0;
        const fl = Math.max(flash, f >= w2(name) ? Math.max(0, 1 - (f - w2(name)) / 12) : 0);
        const seal = sealsAt !== undefined && !sealSkip.includes(name) ? prog(f, sealsAt + i * 3, 8) : 0;
        return (
          <div key={name} style={{ position: 'absolute', left: p.x - 110, top: p.y - 46, width: 220, textAlign: 'center', opacity: a }}>
            <div
              style={{
                margin: '0 auto',
                width: 58,
                height: 58,
                borderRadius: 58,
                border: `3px solid ${hot > 0 ? C.alarm : C.mute}`,
                background: hot > 0 ? `radial-gradient(circle, ${C.alarm}, #5a0b0b)` : C.panel,
                boxShadow: hot > 0 ? `0 0 ${30 + 40 * fl}px ${C.alarm}` : 'none',
                transform: `scale(${1 + 0.25 * fl + (hot > 0 && hot < 1 ? 0.2 * (1 - hot) : 0)})`,
              }}
            />
            <div style={{ fontFamily: F.mono, fontSize: 20, letterSpacing: '0.08em', color: hot > 0 ? C.bone : C.mute, marginTop: 8, textTransform: 'uppercase' }}>{name}</div>
            {seal > 0 && (
              <div style={{ position: 'absolute', left: 140, top: -6, transform: `scale(${seal}) rotate(-8deg)`, fontFamily: F.mono, fontSize: 16, color: C.alarm, border: `2px solid ${C.alarm}`, padding: '2px 6px', whiteSpace: 'nowrap', background: 'rgba(7,8,11,.8)' }}>
                SIGNED ✓
              </div>
            )}
          </div>
        );
      })}
      {note &&
        (() => {
          const i = CHAINS.indexOf(note.node);
          const p = nodePos(i);
          const v = damp(f, note.at, 14);
          return (
            <div style={{ position: 'absolute', left: p.x + 60, top: p.y - 120, opacity: v, transform: `translateY(${(1 - v) * 14}px)` }}>
              <Panel border={C.alarm} style={{ padding: '14px 20px' }}>
                <div style={{ fontFamily: F.display, fontSize: 48, color: C.alarm, letterSpacing: '0.04em' }}>{note.text}</div>
                {note.sub && <Kicker size={18}>{note.sub}</Kicker>}
              </Panel>
            </div>
          );
        })()}
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ HotColdExplainer */

export const HotColdExplainer: React.FC<{ drawAt?: number; vaultAt: number; registerAt: number; streetAt?: number }> = ({ drawAt = 0, vaultAt, registerAt, streetAt = 1e9 }) => {
  const f = useF();
  const d = prog(f, drawAt, 40, outPow3);
  const vault = prog(f, vaultAt, 14);
  const reg = prog(f, registerAt, 14);
  const dolly = prog(f, streetAt, 40, outPow3);
  const per = 2 * (1300 + 560);
  return (
    <AbsoluteFill style={{ transform: `translate(${-40 * dolly}px, 0px) scale(${1 + 0.18 * dolly})`, transformOrigin: '960px 700px' }}>
      <svg width={1920} height={1080} style={{ position: 'absolute', inset: 0 }}>
        <defs>
          <pattern id="bp" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M40 0H0V40" fill="none" stroke={C.ice} strokeOpacity={0.08} />
          </pattern>
        </defs>
        <rect x={310} y={150} width={1300} height={560} fill="url(#bp)" opacity={d} />
        {/* walls: three closed sides, open street edge at the bottom */}
        <path d={`M 310 710 L 310 150 L 1610 150 L 1610 710`} fill="none" stroke={C.ice} strokeWidth={4} strokeDasharray={per} strokeDashoffset={per * (1 - d)} opacity={0.85} />
        <path d="M 310 710 L 760 710 M 1160 710 L 1610 710" stroke={C.ice} strokeWidth={4} opacity={d} />
        {/* back room */}
        <path d="M 310 400 L 820 400 L 820 150" fill="none" stroke={C.ice} strokeWidth={2} strokeDasharray="10 8" opacity={d} />
        <circle cx={565} cy={275} r={82} fill={vault ? `${C.ice}22` : 'none'} stroke={vault > 0 ? C.ice : C.mute} strokeWidth={4} opacity={d} />
        <circle cx={565} cy={275} r={46} fill="none" stroke={vault > 0 ? C.ice : C.mute} strokeWidth={3} opacity={d} />
        {Array.from({ length: 8 }, (_, i) => {
          const a = (i * Math.PI) / 4 + f / 120;
          return <line key={i} x1={565 + Math.cos(a) * 46} y1={275 + Math.sin(a) * 46} x2={565 + Math.cos(a) * 82} y2={275 + Math.sin(a) * 82} stroke={vault > 0 ? C.ice : C.mute} strokeWidth={2} opacity={d} />;
        })}
        {/* register at the open edge */}
        <rect x={880} y={600} width={160} height={90} rx={8} fill={reg > 0 ? `${C.gold}33` : C.panel} stroke={reg > 0 ? C.gold : C.mute} strokeWidth={4} opacity={d} />
        <rect x={905} y={620} width={110} height={28} fill={reg > 0 ? C.gold : C.line} opacity={d * 0.8} />
        {/* signal arcs */}
        {reg > 0 &&
          [0, 1, 2].map((k) => {
            const ph = ((f - registerAt) / 30 + k / 3) % 1;
            return <path key={k} d={`M ${960 - 40 - ph * 60} ${590 - ph * 40} Q 960 ${560 - ph * 80} ${960 + 40 + ph * 60} ${590 - ph * 40}`} fill="none" stroke={C.gold} strokeWidth={3} opacity={1 - ph} />;
          })}
        <text x={1110} y={810} fill={C.mute} fontFamily="monospace" fontSize={22} letterSpacing={6} opacity={d}>
          STREET →
        </text>
      </svg>
      {/* labels */}
      <div style={{ position: 'absolute', left: 340, top: 410, opacity: vault, transform: `translateY(${(1 - vault) * 12}px)` }}>
        <div style={{ fontFamily: F.display, fontSize: 60, color: C.ice, letterSpacing: '0.05em' }}>VAULT · COLD WALLETS</div>
        <Kicker color={C.ice} size={22}>OFFLINE · SLOW · HARD TO REACH</Kicker>
      </div>
      <div style={{ position: 'absolute', left: 1070, top: 560, opacity: reg, transform: `translateY(${(1 - reg) * 12}px)` }}>
        <div style={{ fontFamily: F.display, fontSize: 60, color: C.gold, letterSpacing: '0.05em' }}>CASH REGISTER · HOT WALLETS</div>
        <Kicker color={C.gold} size={22}>ONLINE · WITHDRAWALS 24/7</Kicker>
      </div>
      {dolly > 0 && (
        <AbsoluteFill style={{ background: `radial-gradient(700px 400px at 52% 108%, ${C.alarm}, transparent 70%)`, opacity: 0.55 * dolly * (0.8 + 0.2 * Math.sin(f / 5)), mixBlendMode: 'screen' }} />
      )}
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ FlowPath (attack path / reveal graph) */

export type FlowNode = { label: string; sub?: string; at: number; color?: string };
export const FlowPath: React.FC<{ nodes: FlowNode[]; footer?: string; footerAt?: number; breachAt?: number; y?: number; accent?: string; highlightLast?: boolean }> = ({
  nodes,
  footer,
  footerAt = 0,
  breachAt,
  y = 400,
  accent = C.alarm,
}) => {
  const f = useF();
  const n = nodes.length;
  const gap = 56;
  const bw = Math.min(300, (1728 - gap * (n - 1)) / n);
  const x0 = (1920 - (bw * n + gap * (n - 1))) / 2;
  const bh = 170;
  const gl = breachAt !== undefined && f >= breachAt && f < breachAt + 10;
  return (
    <AbsoluteFill style={{ transform: gl ? `translateX(${jitter(f, 'fp', 1) * 14}px)` : undefined }}>
      <svg width={1920} height={1080} style={{ position: 'absolute', inset: 0 }}>
        {nodes.slice(1).map((nd, i) => {
          const xa = x0 + (i + 1) * bw + i * gap;
          const xb = xa + gap;
          const p = prog(f, nd.at - 6, 14, outPow3);
          return (
            <g key={i}>
              <line x1={xa} y1={y + bh / 2} x2={lerp(xa, xb - 10, p)} y2={y + bh / 2} stroke={accent} strokeWidth={4} strokeDasharray="10 7" strokeDashoffset={-f * 1.5} />
              {p >= 1 && <path d={`M ${xb - 18} ${y + bh / 2 - 10} L ${xb - 4} ${y + bh / 2} L ${xb - 18} ${y + bh / 2 + 10}`} fill="none" stroke={accent} strokeWidth={4} />}
            </g>
          );
        })}
      </svg>
      {nodes.map((nd, i) => {
        const v = damp(f, nd.at, 14);
        const col = nd.color ?? C.bone;
        return (
          <div key={i} style={{ position: 'absolute', left: x0 + i * (bw + gap), top: y, width: bw, height: bh, opacity: v, transform: `translateY(${(1 - v) * 24}px) scale(${0.94 + 0.06 * v})` }}>
            <Panel border={f >= nd.at && f < nd.at + 18 ? accent : C.line} style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', textAlign: 'center', padding: 14, boxSizing: 'border-box' }}>
              <div style={{ fontFamily: F.mono, fontSize: 16, color: C.mute, letterSpacing: '0.14em' }}>STEP {String(i + 1).padStart(2, '0')}</div>
              <div style={{ fontFamily: F.display, fontSize: bw > 280 ? 44 : 38, lineHeight: 1, color: col, letterSpacing: '0.04em', marginTop: 8 }}>{nd.label}</div>
              {nd.sub && <div style={{ fontFamily: F.body, fontSize: 19, color: C.mute, marginTop: 8, lineHeight: 1.25 }}>{nd.sub}</div>}
            </Panel>
          </div>
        );
      })}
      {breachAt !== undefined &&
        [
          [x0 + bw * 0.5, y - 90],
          [x0 + (bw + gap) * 2 + bw * 0.4, y + bh + 70],
          [x0 + (bw + gap) * 3 + bw * 0.8, y - 80],
        ].map(([bx, by], k) => {
          const s = pop(f, breachAt + 8 + k * 5, 10);
          return (
            <div key={k} style={{ position: 'absolute', left: bx - 34, top: by - 34, width: 68, height: 68, borderRadius: 68, border: `3px solid ${C.alarm}`, color: C.alarm, fontFamily: F.display, fontSize: 52, display: 'flex', alignItems: 'center', justifyContent: 'center', transform: `scale(${s})`, background: 'rgba(7,8,11,.8)', boxShadow: `0 0 30px ${C.alarm}88` }}>
              ?
            </div>
          );
        })}
      {footer && (
        <div style={{ position: 'absolute', left: 0, right: 0, top: y + bh + 150, textAlign: 'center', opacity: prog(f, footerAt, 14) }}>
          <Kicker size={20}>{footer}</Kicker>
        </div>
      )}
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ NonceLock */

export const NonceLock: React.FC<{ cardAt: number; slipsAt: number; matchAt: number; title?: string; fiftyAt?: number; spinAt?: number }> = ({ cardAt, slipsAt, matchAt, title = 'BINANCE 14', fiftyAt = 1e9, spinAt }) => {
  const spin0 = spinAt ?? slipsAt;
  const f = useF();
  const card = damp(f, cardAt, 16);
  const matched = f >= matchAt;
  const flip = prog(f, matchAt + 6, 12, outPow3);
  const winner = 37;
  const slotX = 1250;
  const slotY = 470;
  return (
    <AbsoluteFill>
      {/* wallet card */}
      <div style={{ position: 'absolute', left: 1040, top: 210, width: 600, height: 420, opacity: card, transform: `translateY(${(1 - card) * 30}px) perspective(1400px) rotateY(${flip * 180}deg)`, transformStyle: 'preserve-3d' }}>
        <Panel border={C.gold} style={{ position: 'absolute', inset: 0, padding: 34, backfaceVisibility: 'hidden', boxShadow: `0 0 70px ${C.gold}33` }}>
          <Kicker color={C.gold} size={20}>ETHEREUM HOT WALLET · ETHERSCAN LABEL</Kicker>
          <div style={{ fontFamily: F.display, fontSize: 96, color: C.bone, marginTop: 10 }}>{title}</div>
          <div style={{ fontFamily: F.mono, fontSize: 30, color: C.mute, marginTop: 30 }}>NEXT TRANSACTION #</div>
          <div style={{ fontFamily: F.mono, fontSize: 64, color: C.gold, marginTop: 6, fontVariantNumeric: 'tabular-nums' }}>
            {matched ? '✓ MATCH' : f >= spin0 ? `${Math.floor(rnd(`n${Math.floor(f / 2)}`) * 90 + 10)}?` : '???'}
          </div>
          <div style={{ position: 'absolute', left: slotX - 1040 - 70, top: slotY - 210 + 140, width: 160, height: 18, border: `2px dashed ${C.gold}`, borderRadius: 4 }} />
        </Panel>
        <Panel border={C.alarm} style={{ position: 'absolute', inset: 0, padding: 34, backfaceVisibility: 'hidden', transform: 'rotateY(180deg)', background: `linear-gradient(180deg, #3a0c0c, ${C.panel2})`, boxShadow: `0 0 90px ${C.alarm}66` }}>
          <Kicker color={C.alarm} size={20}>{title} · DELEGATED VIA EIP-7702</Kicker>
          <div style={{ fontFamily: F.display, fontSize: 70, color: C.alarm, marginTop: 30, lineHeight: 1 }}>NOW RUNNING:</div>
          <div style={{ fontFamily: F.display, fontSize: 92, color: C.bone, lineHeight: 1 }}>ATTACKER SWEEPER CODE</div>
        </Panel>
      </div>
      <div style={{ position: 'absolute', left: 1040, top: 650, width: 600, textAlign: 'center', fontFamily: F.mono, fontSize: 22, color: C.alarm, letterSpacing: '0.1em', opacity: prog(f, fiftyAt, 10) * (1 - prog(f, matchAt + 6, 8)) }}>50 AUTHORIZATIONS · SIGNED WITH ITS OWN KEY</div>
      {/* 50 slips */}
      {Array.from({ length: 50 }, (_, i) => {
        const t0 = slipsAt + i * 1.2;
        const a = prog(f, t0, 16, outExpo);
        if (a <= 0) return null;
        const col = i % 10;
        const row = Math.floor(i / 10);
        let x = lerp(-200, 140 + col * 84, a);
        let y = lerp(900, 230 + row * 92 + (col % 2) * 10, a);
        let rot = lerp(-30, (rnd(`r${i}`) - 0.5) * 8, a);
        let op = 1;
        if (matched) {
          const m = prog(f, matchAt, 18, i === winner ? outPow3 : inPow3);
          if (i === winner) {
            x = lerp(x, slotX - 36, m);
            y = lerp(y, slotY + 130, m);
            rot = lerp(rot, 0, m);
          } else {
            x += (rnd(`bx${i}`) - 0.3) * 700 * m;
            y += (rnd(`by${i}`) - 0.5) * 500 * m + 300 * m * m;
            rot += (rnd(`br${i}`) - 0.5) * 300 * m;
            op = 1 - m;
          }
        }
        const isW = i === winner && matched;
        return (
          <div key={i} style={{ position: 'absolute', left: x, top: y, width: 72, height: 82, transform: `rotate(${rot}deg)`, opacity: op * (isW && flip > 0.5 ? 0 : 1), background: isW ? C.gold : '#e8e1cf', color: '#111', borderRadius: 4, fontFamily: F.mono, fontSize: 20, fontWeight: 700, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', boxShadow: isW ? `0 0 30px ${C.gold}` : '0 6px 14px rgba(0,0,0,.5)' }}>
            <div style={{ fontSize: 12, letterSpacing: '0.1em', opacity: 0.7 }}>AUTH</div>#{i + 1}
          </div>
        );
      })}
      <div style={{ position: 'absolute', left: 140, top: 160, opacity: prog(f, slipsAt, 12) * (matched ? 1 - prog(f, matchAt, 10) : 1) }}>
        <Kicker color={C.bone} size={22}>50 SIGNED AUTHORIZATIONS · ONE PER POSSIBLE NUMBER</Kicker>
      </div>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ SweepVortex */

export const SweepVortex: React.FC<{ at?: number; tokens?: string[] }> = ({ at = 0, tokens = ['ETH', 'USDT', 'ERC-20', 'ETH', 'ERC-20', 'USDT', 'ERC-20', 'ERC-20'] }) => {
  const f = useF();
  const v = prog(f, at, 16);
  const items = Array.from({ length: 70 }, (_, i) => i);
  return (
    <AbsoluteFill style={{ opacity: v }}>
      <svg width={1920} height={1080} style={{ position: 'absolute', inset: 0 }}>
        {Array.from({ length: 5 }, (_, k) => (
          <circle key={k} cx={960} cy={450} r={120 + k * 90} fill="none" stroke={C.gold} strokeOpacity={0.12} strokeDasharray="4 14" transform={`rotate(${(f * (k % 2 ? -0.6 : 0.8)) % 360} 960 450)`} />
        ))}
      </svg>
      {items.map((i) => {
        const ph = ((f - at) / (70 + (i % 5) * 9) + rnd(`ph${i}`)) % 1;
        const r = lerp(560, 40, ph * ph);
        const a = rnd(`a${i}`) * Math.PI * 2 + ph * 7;
        const x = 960 + Math.cos(a) * r * 1.25;
        const y = 450 + Math.sin(a) * r * 0.62;
        const big = i < tokens.length;
        const sz = big ? 86 * (1 - ph * 0.6) : 14 * (1 - ph * 0.5);
        return big ? (
          <div key={i} style={{ position: 'absolute', left: x - sz / 2, top: y - sz / 2, opacity: 1 - ph * 0.7 }}>
            <TokenCircle ticker={tokens[i]} size={sz} color={i < 2 ? C.gold : C.bone} />
          </div>
        ) : (
          <div key={i} style={{ position: 'absolute', left: x, top: y, width: sz, height: sz, borderRadius: sz, background: i % 4 ? C.gold : C.bone, opacity: (1 - ph) * 0.8 }} />
        );
      })}
      <div style={{ position: 'absolute', left: 960 - 120, top: 450 - 104, width: 240, height: 208, clipPath: 'polygon(25% 0, 75% 0, 100% 50%, 75% 100%, 25% 100%, 0 50%)', background: `radial-gradient(circle, ${C.alarm}, #2a0606)`, display: 'flex', alignItems: 'center', justifyContent: 'center', textAlign: 'center', fontFamily: F.display, fontSize: 40, lineHeight: 1, color: C.bone, letterSpacing: '0.05em', boxShadow: `0 0 80px ${C.alarm}` }}>
        SWEEPER
        <br />
        CONTRACT
      </div>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 760, textAlign: 'center' }}>
        <Kicker color={C.gold} size={22}>ETH · USDT · ~60 OTHER TOKENS</Kicker>
      </div>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ FreezeStamp */

export const FreezeStamp: React.FC<{ ticker: string; amount: string; who: string; time?: string; at?: number; x?: number; y?: number; size?: number }> = ({
  ticker,
  amount,
  who,
  time,
  at = 0,
  x = 960,
  y = 400,
  size = 220,
}) => {
  const f = useF();
  const v = damp(f, at, 14);
  const ice = prog(f, at + 6, 26, outPow3);
  const cr = Array.from({ length: 22 }, (_, i) => i);
  return (
    <div style={{ position: 'absolute', left: x - 380, top: y - size / 2 - 20, width: 760, opacity: v, transform: `scale(${0.9 + 0.1 * v})`, display: 'flex', alignItems: 'center', gap: 40 }}>
      <div style={{ position: 'relative', width: size, height: size, flex: 'none' }}>
        <TokenCircle ticker={ticker} size={size} color={C.gold} />
        <svg width={size} height={size} style={{ position: 'absolute', inset: 0 }}>
          <circle cx={size / 2} cy={size / 2} r={size / 2 - 2} fill={C.ice} opacity={0.25 * ice} />
          {cr.map((i) => {
            const a = rnd(`ca${ticker}${i}`) * Math.PI * 2;
            const l = (0.25 + rnd(`cl${ticker}${i}`) * 0.3) * size * ice;
            const sx = size / 2 + Math.cos(a) * size * 0.45;
            const sy = size / 2 + Math.sin(a) * size * 0.45;
            return <line key={i} x1={sx} y1={sy} x2={sx - Math.cos(a) * l} y2={sy - Math.sin(a) * l} stroke={C.ice} strokeWidth={2.5} opacity={0.9} />;
          })}
        </svg>
        <div style={{ position: 'absolute', left: -20, top: size / 2 - 40 }}>
          <Stamp text="FROZEN" at={at + 16} color={C.ice} size={62} rotate={-10} />
        </div>
      </div>
      <div>
        <div style={{ fontFamily: F.display, fontSize: 92, color: C.bone, lineHeight: 1 }}>{amount}</div>
        <div style={{ fontFamily: F.body, fontWeight: 600, fontSize: 34, color: C.ice, marginTop: 8 }}>{who}</div>
        {time && <Kicker size={24} style={{ marginTop: 8 }}>{time}</Kicker>}
      </div>
    </div>
  );
};

/* ------------------------------------------------------------------ TxCard (2019) */

export const TxCard: React.FC<{ at?: number; hash: string }> = ({ at = 0, hash }) => {
  const f = useF();
  const a = damp(f, at, 14);
  const b = prog(f, at + 12, 22, outPow3);
  const c = damp(f, at + 30, 14);
  return (
    <AbsoluteFill>
      <div style={{ position: 'absolute', left: 170, top: 300, opacity: a, transform: `translateX(${(1 - a) * -40}px)` }}>
        <Panel style={{ padding: '28px 34px', width: 420 }}>
          <Kicker size={18}>FROM</Kicker>
          <div style={{ fontFamily: F.display, fontSize: 58, color: C.bone }}>BINANCE HOT WALLET</div>
        </Panel>
      </div>
      <svg width={1920} height={1080} style={{ position: 'absolute', inset: 0 }}>
        <line x1={640} y1={370} x2={lerp(640, 1240, b)} y2={370} stroke={C.gold} strokeWidth={5} strokeDasharray="14 10" strokeDashoffset={-f * 2} />
      </svg>
      <div style={{ position: 'absolute', left: lerp(640, 1150, b) - 120, top: 250, opacity: prog(f, at + 12, 8) }}>
        <div style={{ fontFamily: F.display, fontSize: 84, color: C.gold, textShadow: `0 0 30px ${C.gold}88` }}>7,000 BTC</div>
      </div>
      <div style={{ position: 'absolute', left: 1260, top: 300, opacity: c, transform: `translateX(${(1 - c) * 40}px)` }}>
        <Panel border={C.alarm} style={{ padding: '28px 34px', width: 440 }}>
          <Kicker size={18} color={C.alarm}>TO</Kicker>
          <div style={{ fontFamily: F.display, fontSize: 58, color: C.bone }}>UNKNOWN ADDRESS</div>
        </Panel>
      </div>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 560, textAlign: 'center', fontFamily: F.mono, fontSize: 34, color: C.mute, letterSpacing: '0.06em' }}>
        TX {typeOn(hash, f, at + 24, 40)}
      </div>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ KeyGridCollapse (match-cut 2019 → 2026) */

export const KeyGridCollapse: React.FC<{ at?: number; collapseAt: number }> = ({ at = 0, collapseAt }) => {
  const f = useF();
  const cols = 30;
  const rows = 14;
  const c = prog(f, collapseAt, 26, inPow3);
  const glow = prog(f, collapseAt + 22, 12);
  return (
    <AbsoluteFill>
      {Array.from({ length: cols * rows }, (_, i) => {
        const cx = i % cols;
        const cy = Math.floor(i / cols);
        const x0 = 120 + cx * 57;
        const y0 = 120 + cy * 50;
        const a = prog(f, at + rnd(`k${i}`) * 20, 10);
        const x = lerp(x0, 948, c);
        const y = lerp(y0, 440, c);
        return (
          <div key={i} style={{ position: 'absolute', left: x, top: y, opacity: a * (1 - glow), transform: `scale(${1 - 0.6 * c})`, color: rnd(`kc${i}`) > 0.85 ? C.gold : C.mute, fontSize: 26 }}>
            <svg width={26} height={14} viewBox="0 0 26 14">
              <circle cx={6} cy={7} r={5} fill="none" stroke="currentColor" strokeWidth={2} />
              <path d="M11 7 H25 M20 7 V12 M24 7 V11" stroke="currentColor" strokeWidth={2} />
            </svg>
          </div>
        );
      })}
      {glow > 0 && (
        <div style={{ position: 'absolute', left: 960 - 170, top: 450 - 110, transform: `scale(${0.6 + 0.4 * glow})`, opacity: glow }}>
          <LaptopIcon w={340} color={C.alarm} />
        </div>
      )}
    </AbsoluteFill>
  );
};

export const LaptopIcon: React.FC<{ w?: number; color?: string; open?: number }> = ({ w = 300, color = C.alarm, open = 1 }) => (
  <svg width={w} height={w * 0.66} viewBox="0 0 300 200" style={{ filter: `drop-shadow(0 0 24px ${color})` }}>
    <rect x={50} y={20} width={200} height={130 * open} rx={8} fill="none" stroke={color} strokeWidth={6} />
    <rect x={64} y={34} width={172} height={102 * open} fill={color} opacity={0.15} />
    <path d="M20 160 H280 L262 182 H38 Z" fill="none" stroke={color} strokeWidth={6} strokeLinejoin="round" />
  </svg>
);

/* ------------------------------------------------------------------ TimelineRail (S05 HUD) */

export const TimelineRail: React.FC<{ t: number; t0?: number; t1?: number; events?: { t: number; label: string }[]; y?: number }> = ({ t, t0 = 20 * 3600 + 5 * 60, t1 = 20 * 3600 + 25 * 60, events = [], y = 980 }) => {
  const x0 = 300;
  const x1 = 1360;
  const p = clamp((t - t0) / (t1 - t0));
  const lab = (s: number) => `${String(Math.floor(s / 3600)).padStart(2, '0')}:${String(Math.floor((s % 3600) / 60)).padStart(2, '0')}`;
  return (
    <div style={{ position: 'absolute', left: 0, top: y, width: 1920, height: 60, pointerEvents: 'none' }}>
      <div style={{ position: 'absolute', left: x0, top: 10, width: x1 - x0, height: 2, background: C.line }} />
      <div style={{ position: 'absolute', left: x0, top: 9, width: (x1 - x0) * p, height: 4, background: C.alarm, boxShadow: `0 0 12px ${C.alarm}` }} />
      {[0, 0.25, 0.5, 0.75, 1].map((k) => (
        <div key={k} style={{ position: 'absolute', left: x0 + (x1 - x0) * k - 30, top: 22, width: 60, textAlign: 'center', fontFamily: F.mono, fontSize: 16, color: C.mute }}>
          {lab(t0 + (t1 - t0) * k)}
        </div>
      ))}
      {events.map((e, i) => {
        const ep = clamp((e.t - t0) / (t1 - t0));
        const on = t >= e.t;
        return <div key={i} style={{ position: 'absolute', left: x0 + (x1 - x0) * ep - 6, top: 5, width: 12, height: 12, borderRadius: 12, background: on ? C.alarm : C.line, transform: `scale(${on ? 1 : 0.6})` }} />;
      })}
      <div style={{ position: 'absolute', left: x0 + (x1 - x0) * p - 7, top: 3, width: 14, height: 14, borderRadius: 14, background: C.bone }} />
    </div>
  );
};

export const fmt = fmtInt;
export { interpolate };
