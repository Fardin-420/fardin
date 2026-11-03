/**
 * Designed motion-graphic plates — the fallback for AI shots AI-01…AI-13 (none supplied, stock APIs
 * unreachable). Stylized, low-key, no faces, no text, no logos. Letterboxed 2.39:1 with Ken Burns.
 */
import React from 'react';
import { AbsoluteFill } from 'remotion';
import { C, F } from '../theme';
import { useF } from '../lib/frame';
import { clamp, lerp, outPow3, prog, rnd } from '../lib/anim';
import { KenBurns, Letterbox } from './core';

const PlateShell: React.FC<{ len: number; seed: string; to?: number; children: React.ReactNode; tag?: string }> = ({ len, seed, to = 1.07, children, tag }) => {
  const f = useF();
  return (
    <AbsoluteFill style={{ background: '#030405', overflow: 'hidden' }}>
      <KenBurns len={len} to={to} seed={seed}>
        {children}
        {/* light dust */}
        {Array.from({ length: 26 }, (_, i) => {
          const x = (rnd(`${seed}dx${i}`) * 1920 + f * (0.2 + rnd(`${seed}vx${i}`) * 0.5)) % 1920;
          const y = (rnd(`${seed}dy${i}`) * 1080 - f * (0.1 + rnd(`${seed}vy${i}`) * 0.3) + 1080) % 1080;
          return <div key={i} style={{ position: 'absolute', left: x, top: y, width: 2.5, height: 2.5, borderRadius: 3, background: '#fff', opacity: 0.1 + 0.18 * rnd(`${seed}o${i}`) }} />;
        })}
      </KenBurns>
      <Letterbox />
      {tag && (
        <div style={{ position: 'absolute', right: 110, top: 150, fontFamily: F.mono, fontSize: 16, letterSpacing: '0.16em', color: C.mute, opacity: prog(f, 6, 10) }}>{tag}</div>
      )}
    </AbsoluteFill>
  );
};

/* AI-01 · server corridor, red beacon */
export const PlateCorridor: React.FC<{ len: number }> = ({ len }) => {
  const f = useF();
  const vx = 960;
  const vy = 500;
  const cols = 14;
  const beam = (f / 45) * Math.PI;
  return (
    <PlateShell len={len} seed="cor" to={1.18}>
      <AbsoluteFill style={{ background: 'radial-gradient(700px 400px at 50% 46%, #0d2333, #020304 75%)' }} />
      <svg width={1920} height={1080} style={{ position: 'absolute', inset: 0 }}>
        {[-1, 1].map((side) =>
          Array.from({ length: cols }, (_, i) => {
            const t0 = Math.pow(i / cols, 1.8);
            const t1 = Math.pow((i + 1) / cols, 1.8);
            const xa = lerp(side < 0 ? -200 : 2120, vx + side * 70, t0);
            const xb = lerp(side < 0 ? -200 : 2120, vx + side * 70, t1);
            const ha = lerp(1500, 120, t0);
            const hb = lerp(1500, 120, t1);
            return (
              <g key={`${side}${i}`}>
                <path d={`M ${xa} ${vy - ha / 2} L ${xb} ${vy - hb / 2} L ${xb} ${vy + hb / 2} L ${xa} ${vy + ha / 2} Z`} fill={i % 2 ? '#0a0f15' : '#0c131b'} stroke="#16212c" strokeWidth={1} />
                {Array.from({ length: 10 }, (_, k) => {
                  const yy = vy - ha / 2 + ((k + 0.5) / 10) * ha;
                  const on = rnd(`led${side}${i}${k}${Math.floor((f + k * 7) / 18)}`) > 0.35;
                  return <circle key={k} cx={lerp(xa, xb, 0.3)} cy={yy} r={Math.max(1, 6 * (1 - t0))} fill={k % 5 === 0 ? '#ff4d4d' : C.ice} opacity={on ? 0.85 : 0.15} />;
                })}
              </g>
            );
          }),
        )}
        <path d={`M 0 1080 L ${vx - 70} ${vy + 60} L ${vx + 70} ${vy + 60} L 1920 1080 Z`} fill="#06090d" />
      </svg>
      <AbsoluteFill style={{ background: `conic-gradient(from ${(beam * 180) / Math.PI}deg at 50% 18%, transparent 0deg, rgba(255,40,40,.55) 18deg, transparent 40deg, transparent 360deg)`, mixBlendMode: 'screen', opacity: 0.8 }} />
      <div style={{ position: 'absolute', left: 940, top: 170, width: 40, height: 24, borderRadius: 6, background: '#ff2a2a', boxShadow: '0 0 60px 20px rgba(255,40,40,.6)' }} />
      <AbsoluteFill style={{ background: 'radial-gradient(500px 300px at 50% 50%, rgba(111,231,255,.08), transparent 70%)' }} />
    </PlateShell>
  );
};

/* AI-04 · vault door, red seam */
export const PlateVault: React.FC<{ len: number }> = ({ len }) => {
  const f = useF();
  const seam = 0.3 + 0.7 * prog(f, 10, 60);
  const arc = Math.sin(f / 70) * 8;
  return (
    <PlateShell len={len} seed="vault" to={1.05}>
      <AbsoluteFill style={{ background: 'radial-gradient(900px 600px at 50% 50%, #12273a, #030507 80%)' }} />
      <AbsoluteFill style={{ transform: `perspective(1800px) rotateY(${arc}deg)`, alignItems: 'center', justifyContent: 'center' }}>
        <svg width={900} height={900} viewBox="-450 -450 900 900">
          <defs>
            <radialGradient id="vd" cx="35%" cy="30%">
              <stop offset="0%" stopColor="#5e7487" />
              <stop offset="60%" stopColor="#25323d" />
              <stop offset="100%" stopColor="#0d1218" />
            </radialGradient>
          </defs>
          <circle r={430} fill="#0b1015" stroke="#2c3a46" strokeWidth={10} />
          <circle r={380} fill="url(#vd)" />
          {Array.from({ length: 24 }, (_, i) => {
            const a = (i / 24) * Math.PI * 2;
            return <circle key={i} cx={Math.cos(a) * 405} cy={Math.sin(a) * 405} r={11} fill="#3d4d5b" stroke="#111" />;
          })}
          {[300, 230, 150].map((r, i) => (
            <circle key={i} r={r} fill="none" stroke="#6c8396" strokeOpacity={0.35} strokeWidth={6 - i} />
          ))}
          <g transform={`rotate(${f * 0.15})`}>
            {Array.from({ length: 6 }, (_, i) => (
              <rect key={i} x={-10} y={-210} width={20} height={150} rx={8} fill="#7d93a5" opacity={0.6} transform={`rotate(${i * 60})`} />
            ))}
            <circle r={60} fill="#1b242c" stroke="#8aa0b3" strokeWidth={6} />
          </g>
          <rect x={-3} y={-380} width={6} height={760} fill="#ff3030" opacity={seam} style={{ filter: 'drop-shadow(0 0 18px #ff2020)' }} />
        </svg>
      </AbsoluteFill>
      <AbsoluteFill style={{ background: `radial-gradient(120px 500px at 50% 50%, rgba(255,30,30,${0.25 * seam}), transparent 70%)`, mixBlendMode: 'screen' }} />
    </PlateShell>
  );
};

/* AI-02 / AI-13 · laptop in a dark room */
export const PlateLaptop: React.FC<{ len: number; mode?: 'closed' | 'half' | 'closing'; pulseAt?: number }> = ({ len, mode = 'closed', pulseAt = 8 }) => {
  const f = useF();
  const beat = (t: number) => Math.exp(-Math.pow((t % 34) - 2, 2) / 3) + 0.6 * Math.exp(-Math.pow((t % 34) - 8, 2) / 3);
  const pulse = f >= pulseAt ? beat(f - pulseAt) : 0;
  const lid = mode === 'closed' ? 0 : mode === 'half' ? 0.55 : 0.55 * (1 - prog(f, 20, Math.max(len - 70, 30), outPow3));
  const red = mode === 'closing' ? lid / 0.55 : mode === 'half' ? 1 : 0.35 + 0.65 * pulse;
  const fadeBlack = mode === 'closing' ? prog(f, len - 40, 30) : 0;
  return (
    <PlateShell len={len} seed={`lap${mode}`} to={1.08}>
      <AbsoluteFill style={{ background: 'linear-gradient(180deg, #05080c, #020203)' }} />
      {/* window with rain + bokeh */}
      <div style={{ position: 'absolute', left: 360, top: 120, width: 1200, height: 520, background: 'linear-gradient(180deg, #0b1a29, #070d14)', border: '10px solid #050608', overflow: 'hidden' }}>
        {Array.from({ length: 34 }, (_, i) => (
          <div key={i} style={{ position: 'absolute', left: rnd(`bx${i}`) * 1200, top: 260 + rnd(`by${i}`) * 260, width: 30 + rnd(`bs${i}`) * 60, height: 30 + rnd(`bs${i}`) * 60, borderRadius: 100, background: i % 4 ? '#e9b94933' : '#6fe7ff2a', filter: 'blur(6px)' }} />
        ))}
        {Array.from({ length: 40 }, (_, i) => {
          const x = rnd(`rx${i}`) * 1200;
          const y = ((rnd(`ry${i}`) * 520 + f * (6 + rnd(`rv${i}`) * 6)) % 600) - 60;
          return <div key={i} style={{ position: 'absolute', left: x, top: y, width: 2, height: 40 + rnd(`rl${i}`) * 50, background: 'linear-gradient(180deg, transparent, #9cc9e855)' }} />;
        })}
      </div>
      {/* desk */}
      <div style={{ position: 'absolute', left: 0, right: 0, top: 690, bottom: 0, background: 'linear-gradient(180deg, #1a120c, #0a0705)' }} />
      {/* laptop */}
      <svg width={1920} height={1080} style={{ position: 'absolute', inset: 0 }}>
        <defs>
          <linearGradient id="lb" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stopColor="#9aa3ab" />
            <stop offset="1" stopColor="#3a4046" />
          </linearGradient>
        </defs>
        <path d="M 640 760 L 1280 760 L 1340 800 L 580 800 Z" fill="url(#lb)" />
        {lid > 0.01 && <path d={`M 660 760 L 1260 760 L ${1260 - 20 * lid} ${760 - 420 * lid} L ${660 + 20 * lid} ${760 - 420 * lid} Z`} fill="#15181b" stroke="#596068" strokeWidth={3} />}
        {lid > 0.01 && <path d={`M 680 752 L 1240 752 L ${1240 - 18 * lid} ${768 - 400 * lid} L ${680 + 18 * lid} ${768 - 400 * lid} Z`} fill="#ff2a2a" opacity={0.6 * red} />}
        <path d="M 580 800 L 1340 800" stroke="#ff2a2a" strokeWidth={4} opacity={red} style={{ filter: 'drop-shadow(0 0 14px #ff2020)' }} />
      </svg>
      <AbsoluteFill style={{ background: `radial-gradient(${600 + 300 * lid}px ${180 + 260 * lid}px at 50% 75%, rgba(255,30,30,${0.35 * red}), transparent 70%)`, mixBlendMode: 'screen' }} />
      {fadeBlack > 0 && <AbsoluteFill style={{ background: '#000', opacity: fadeBlack }} />}
    </PlateShell>
  );
};

/* AI-03 · aerial night financial district */
export const PlateCity: React.FC<{ len: number }> = ({ len }) => {
  const f = useF();
  return (
    <PlateShell len={len} seed="city" to={1.12}>
      <AbsoluteFill style={{ background: 'linear-gradient(180deg, #040a12, #071420 60%, #0a1a28)' }} />
      <AbsoluteFill style={{ transform: 'perspective(900px) rotateX(58deg) translateY(-120px) scale(2.2)', transformOrigin: '50% 60%' }}>
        {Array.from({ length: 12 * 10 }, (_, i) => {
          const cx = i % 12;
          const cy = Math.floor(i / 12);
          const h = 20 + rnd(`h${i}`) * 80;
          return <div key={i} style={{ position: 'absolute', left: 260 + cx * 120 + (rnd(`ox${i}`) - 0.5) * 20, top: cy * 110 - ((f * 1.2) % 110), width: 80, height: 70, background: `linear-gradient(135deg, #1b3146, #0b1621)`, boxShadow: `0 0 ${h / 4}px rgba(111,231,255,${0.08 + rnd(`g${i}`) * 0.15})`, border: '1px solid #1f3a52' }} />;
        })}
        {Array.from({ length: 10 }, (_, k) => (
          <div key={k} style={{ position: 'absolute', left: 250 + ((k * 240) % 1440), top: (((f * (6 + k)) % 1300) - 200), width: 4, height: 120, background: k % 2 ? 'linear-gradient(180deg, transparent, #ff5a3a)' : 'linear-gradient(180deg, transparent, #fff1c8)', boxShadow: '0 0 10px #ffb070' }} />
        ))}
      </AbsoluteFill>
      <AbsoluteFill style={{ background: 'linear-gradient(180deg, rgba(4,10,18,1) 0%, rgba(4,10,18,0) 35%)' }} />
      <AbsoluteFill style={{ background: 'radial-gradient(1000px 300px at 50% 60%, rgba(111,231,255,.10), transparent 70%)' }} />
    </PlateShell>
  );
};

/* AI-05 · VHS gold coins (2019) */
export const PlateCoins: React.FC<{ len: number }> = ({ len }) => {
  const f = useF();
  return (
    <PlateShell len={len} seed="coins" to={1.06}>
      <AbsoluteFill style={{ background: 'radial-gradient(900px 600px at 50% 55%, #2a1414, #080404 80%)' }} />
      {Array.from({ length: 16 }, (_, i) => {
        const s = 140 + rnd(`cs${i}`) * 160;
        return (
          <div key={i} style={{ position: 'absolute', left: rnd(`cx${i}`) * 1700, top: 180 + rnd(`cy${i}`) * 620, width: s, height: s * (0.55 + rnd(`ce${i}`) * 0.4), borderRadius: '50%', background: 'radial-gradient(circle at 35% 30%, #fff1b5, #d9a63a 40%, #6b4a12 85%)', boxShadow: '0 20px 40px rgba(0,0,0,.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: F.body, fontWeight: 800, fontSize: s * 0.45, color: '#7a5413', transform: `rotate(${rnd(`cr${i}`) * 60 - 30}deg)` }}>
            ₿
          </div>
        );
      })}
      <AbsoluteFill style={{ top: ((f * 9) % 1300) - 120, height: 26, bottom: 'auto', background: 'rgba(255,255,255,.12)', filter: 'blur(3px)' }} />
    </PlateShell>
  );
};

/* AI-06 · keyboard in darkness (no hands, no face) */
export const PlateKeyboard: React.FC<{ len: number }> = ({ len }) => {
  const f = useF();
  return (
    <PlateShell len={len} seed="keys" to={1.08}>
      <AbsoluteFill style={{ background: 'radial-gradient(1100px 500px at 50% 10%, #10263a, #020304 75%)' }} />
      <AbsoluteFill style={{ transform: 'perspective(1000px) rotateX(55deg) translateY(120px) scale(1.3)', transformOrigin: '50% 70%' }}>
        {Array.from({ length: 5 * 15 }, (_, i) => {
          const cx = i % 15;
          const cy = Math.floor(i / 15);
          const hot = rnd(`k${i}${Math.floor(f / 4)}`) > 0.93;
          return <div key={i} style={{ position: 'absolute', left: 300 + cx * 90 + cy * 18, top: 300 + cy * 92, width: 78, height: 78, borderRadius: 10, background: hot ? '#1d3d55' : '#0d151d', border: `1px solid ${hot ? C.ice : '#1b2733'}`, boxShadow: hot ? `0 0 26px ${C.ice}66` : '0 6px 0 #05080b', transform: hot ? 'translateY(4px)' : undefined }} />;
        })}
      </AbsoluteFill>
      <AbsoluteFill style={{ background: 'linear-gradient(180deg, rgba(111,231,255,.10), transparent 40%)' }} />
    </PlateShell>
  );
};

/* AI-08 · monitor wall, red graphs, empty chair */
export const PlateMonitors: React.FC<{ len: number }> = ({ len }) => {
  const f = useF();
  return (
    <PlateShell len={len} seed="mon" to={1.06}>
      <AbsoluteFill style={{ background: '#030405' }} />
      {Array.from({ length: 4 * 6 }, (_, i) => {
        const cx = i % 6;
        const cy = Math.floor(i / 6);
        const pts = Array.from({ length: 24 }, (_, k) => `${k * 11},${70 - 50 * Math.abs(Math.sin(k * 0.5 + i + f / 20)) * (1 - k / 30) - (k > 12 ? (k - 12) * 3 : 0)}`).join(' ');
        return (
          <div key={i} style={{ position: 'absolute', left: 170 + cx * 270, top: 150 + cy * 165, width: 250, height: 145, background: '#0e0607', border: '3px solid #1a1c1f', boxShadow: `0 0 30px rgba(255,40,40,${0.12 + 0.1 * Math.sin(f / 9 + i)})`, opacity: rnd(`fl${i}${Math.floor(f / 6)}`) > 0.04 ? 1 : 0.4 }}>
            <svg width={250} height={145}>
              <polyline points={pts} transform="translate(-2 30)" fill="none" stroke="#ff3b3b" strokeWidth={3} />
            </svg>
          </div>
        );
      })}
      <svg width={1920} height={1080} style={{ position: 'absolute', inset: 0 }}>
        <path d="M 860 1080 L 880 860 Q 960 800 1040 860 L 1060 1080 Z" fill="#000" />
        <path d="M 850 900 L 1070 900 L 1060 960 L 860 960 Z" fill="#000" />
      </svg>
      <AbsoluteFill style={{ background: 'radial-gradient(1000px 500px at 50% 30%, rgba(255,40,40,.12), transparent 70%)' }} />
    </PlateShell>
  );
};

/* AI-09 · ice crystals forming over warm light */
export const PlateIce: React.FC<{ len: number }> = ({ len }) => {
  const f = useF();
  const g = prog(f, 0, Math.min(len, 120), outPow3);
  return (
    <PlateShell len={len} seed="ice" to={1.05}>
      <AbsoluteFill style={{ background: 'radial-gradient(800px 500px at 50% 55%, #6b4a12, #120c04 75%)' }} />
      <svg width={1920} height={1080} style={{ position: 'absolute', inset: 0 }}>
        {Array.from({ length: 14 }, (_, s) => {
          const sx = rnd(`isx${s}`) * 1920;
          const sy = rnd(`isy${s}`) * 1080;
          return Array.from({ length: 9 }, (_, k) => {
            const a = (k / 9) * Math.PI * 2 + rnd(`ia${s}`);
            const l = (80 + rnd(`il${s}${k}`) * 260) * clamp(g * 1.4 - s * 0.04);
            return (
              <g key={`${s}-${k}`}>
                <line x1={sx} y1={sy} x2={sx + Math.cos(a) * l} y2={sy + Math.sin(a) * l} stroke={C.ice} strokeWidth={2} opacity={0.8} />
                <line x1={sx + Math.cos(a) * l * 0.5} y1={sy + Math.sin(a) * l * 0.5} x2={sx + Math.cos(a + 0.6) * l * 0.75} y2={sy + Math.sin(a + 0.6) * l * 0.75} stroke={C.ice} strokeWidth={1.2} opacity={0.6} />
              </g>
            );
          });
        })}
      </svg>
      <AbsoluteFill style={{ background: `rgba(111,231,255,${0.12 * g})`, mixBlendMode: 'screen' }} />
    </PlateShell>
  );
};

/* AI-10 · desk lamp over a sealed dossier */
export const PlateDossierLamp: React.FC<{ len: number }> = ({ len }) => (
  <PlateShell len={len} seed="lamp" to={1.1}>
    <AbsoluteFill style={{ background: '#030303' }} />
    <AbsoluteFill style={{ background: 'conic-gradient(from 160deg at 50% 0%, transparent 0deg, rgba(255,214,150,.22) 18deg, rgba(255,214,150,.22) 42deg, transparent 60deg)' }} />
    <AbsoluteFill style={{ background: 'radial-gradient(700px 260px at 50% 82%, rgba(255,210,140,.35), transparent 70%)' }} />
    <div style={{ position: 'absolute', left: 700, top: 700, width: 520, height: 230, background: 'linear-gradient(160deg, #4a3a22, #2b2214)', transform: 'perspective(800px) rotateX(55deg)', boxShadow: '0 30px 60px rgba(0,0,0,.8)' }}>
      <div style={{ position: 'absolute', left: 230, top: 80, width: 60, height: 60, borderRadius: 60, background: '#8d1414' }} />
    </div>
  </PlateShell>
);

/* AI-11 · anonymous hooded figure from behind, glyph screens (≤3 s, labeled) */
export const PlateSilhouette: React.FC<{ len: number }> = ({ len }) => {
  const f = useF();
  const glyphs = '01ABCDEF#$%&*+=<>/\\|{}[]';
  return (
    <PlateShell len={len} seed="sil" to={1.06} tag="ILLUSTRATION · DRAMATIZATION">
      <AbsoluteFill style={{ background: '#020304' }} />
      {Array.from({ length: 3 * 5 }, (_, i) => (
        <div key={i} style={{ position: 'absolute', left: 230 + (i % 5) * 300, top: 170 + Math.floor(i / 5) * 230, width: 280, height: 210, background: '#05140f', border: '2px solid #0b2a1f', overflow: 'hidden', fontFamily: F.mono, fontSize: 18, lineHeight: '22px', color: '#3cff9e', opacity: 0.55, wordBreak: 'break-all' }}>
          {Array.from({ length: 120 }, (_, k) => glyphs[Math.floor(rnd(`g${i}${k}${Math.floor(f / 3)}`) * glyphs.length)]).join('')}
        </div>
      ))}
      <svg width={1920} height={1080} style={{ position: 'absolute', inset: 0 }}>
        <path d="M 960 430 C 870 430 830 510 840 590 C 760 630 700 720 680 1080 L 1240 1080 C 1220 720 1160 630 1080 590 C 1090 510 1050 430 960 430 Z" fill="#000" />
      </svg>
      <AbsoluteFill style={{ background: 'radial-gradient(500px 400px at 50% 55%, rgba(60,255,158,.12), transparent 70%)', mixBlendMode: 'screen' }} />
    </PlateShell>
  );
};

/* AI-12 · dawn skyline */
export const PlateDawn: React.FC<{ len: number }> = ({ len }) => {
  const f = useF();
  const tilt = prog(f, 0, len, outPow3);
  return (
    <PlateShell len={len} seed="dawn" to={1.05}>
      <AbsoluteFill style={{ background: 'linear-gradient(180deg, #0b1626 0%, #3a4a63 45%, #c9875a 72%, #f1c58a 80%)', transform: `translateY(${tilt * 60}px)` }} />
      <svg width={1920} height={1080} style={{ position: 'absolute', inset: 0, transform: `translateY(${tilt * 90}px)` }}>
        {Array.from({ length: 40 }, (_, i) => {
          const w = 30 + rnd(`w${i}`) * 70;
          const h = 120 + rnd(`h${i}`) * 360;
          return <rect key={i} x={i * 50 - 20} y={860 - h} width={w} height={h + 300} fill="#0a0d12" />;
        })}
      </svg>
      <AbsoluteFill style={{ background: 'linear-gradient(180deg, transparent 55%, rgba(220,220,230,.18) 75%, transparent 90%)' }} />
    </PlateShell>
  );
};

/* AI-07 · golden particle vortex (underlay for SweepVortex) */
export const PlateVortexBg: React.FC = () => {
  const f = useF();
  return <AbsoluteFill style={{ background: `conic-gradient(from ${f * 1.2}deg at 50% 42%, #000, #3a2a06, #000, #2a1e05, #000)`, opacity: 0.55 }} />;
};
