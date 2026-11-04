import React from 'react';
import { AbsoluteFill, Img, interpolate, staticFile } from 'remotion';
import { C, F, H, SAFE, W } from '../theme';
import { At, Rebase, useF } from '../lib/frame';
import { clamp, damp, fmtInt, inPow3, inOutVis, jitter, outExpo, outPow3, pop, prog, rnd, typeOn } from '../lib/anim';

/* ------------------------------------------------------------------ stage & overlays */

export const Stage: React.FC<{ accent?: string; grid?: boolean; children?: React.ReactNode; tint?: number }> = ({
  accent = C.alarm,
  grid = true,
  children,
  tint = 0.1,
}) => {
  const f = useF();
  const gx = (f * 0.25) % 80;
  return (
    <AbsoluteFill style={{ background: C.ink, overflow: 'hidden' }}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(1200px 700px at ${50 + Math.sin(f / 200) * 8}% ${45 + Math.cos(f / 260) * 6}%, ${accent}${Math.round(
            tint * 255,
          )
            .toString(16)
            .padStart(2, '0')}, transparent 70%)`,
        }}
      />
      {grid && (
        <AbsoluteFill
          style={{
            opacity: 0.32,
            backgroundImage: `linear-gradient(${C.line} 1px, transparent 1px), linear-gradient(90deg, ${C.line} 1px, transparent 1px)`,
            backgroundSize: '80px 80px',
            backgroundPosition: `${gx}px ${gx * 0.5}px`,
            maskImage: 'radial-gradient(ellipse at center, black 20%, transparent 75%)',
            WebkitMaskImage: 'radial-gradient(ellipse at center, black 20%, transparent 75%)',
          }}
        />
      )}
      {children}
    </AbsoluteFill>
  );
};

export const FilmGrain: React.FC<{ opacity?: number }> = ({ opacity = 0.045 }) => {
  const f = useF();
  const k = Math.floor(f / 2); // refreshed every 2nd frame (spec: keeps bitrate down)
  const i = k % 8;
  const ox = Math.floor(rnd(`gx${k}`) * 512);
  const oy = Math.floor(rnd(`gy${k}`) * 512);
  return (
    <AbsoluteFill
      style={{
        opacity,
        mixBlendMode: 'overlay',
        backgroundImage: `url(${staticFile(`heist/grain_${i}.png`)})`,
        backgroundPosition: `${ox}px ${oy}px`,
        pointerEvents: 'none',
      }}
    />
  );
};

export const Vignette: React.FC<{ amount?: number }> = ({ amount = 0.23 }) => (
  <AbsoluteFill
    style={{
      background: `radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,${amount * 2.6}) 100%)`,
      pointerEvents: 'none',
    }}
  />
);

export const Scanlines: React.FC<{ opacity?: number }> = ({ opacity = 0.12 }) => (
  <AbsoluteFill
    style={{
      opacity,
      backgroundImage: 'repeating-linear-gradient(0deg, rgba(0,0,0,.9) 0px, rgba(0,0,0,.9) 1px, transparent 1px, transparent 3px)',
      pointerEvents: 'none',
    }}
  />
);

/** 2.39:1 letterbox, bars animate in over 12 frames. */
export const Letterbox: React.FC<{ from?: number }> = ({ from = 0 }) => {
  const f = useF();
  const p = prog(f, from, 12, outPow3);
  const bar = ((H - W / 2.39) / 2) * p;
  return (
    <AbsoluteFill style={{ pointerEvents: 'none' }}>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 0, height: bar, background: '#000' }} />
      <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: bar, background: '#000' }} />
    </AbsoluteFill>
  );
};

/** Procedural warm light leak sweeping across frame (filmBurn look). */
export const LightLeak: React.FC<{ p: number; color?: string; intensity?: number }> = ({ p, color = '#ffb36b', intensity = 1 }) => {
  if (p <= 0 || p >= 1) return null;
  const x = interpolate(p, [0, 1], [-40, 140]);
  const a = Math.sin(Math.PI * p) * intensity;
  return (
    <AbsoluteFill style={{ pointerEvents: 'none', mixBlendMode: 'screen' }}>
      <AbsoluteFill style={{ background: `radial-gradient(900px 1400px at ${x}% 50%, ${color}, transparent 60%)`, opacity: a }} />
      <AbsoluteFill style={{ background: `radial-gradient(600px 900px at ${x - 25}% 30%, #ff5a2a, transparent 65%)`, opacity: a * 0.7 }} />
      <AbsoluteFill style={{ background: '#fff2dc', opacity: a * 0.18 }} />
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ camera */

/** Punch-in (1.00→1.08 in 4f, hold, relax ~20f) + impact (6f shake, RGB split, 2f 25% flash). */
export const Camera: React.FC<{ punches: number[]; impacts: number[]; children: React.ReactNode }> = ({ punches, impacts, children }) => {
  const f = useF();
  let s = 1;
  for (const p of punches) {
    const d = f - p;
    if (d < 0 || d > 34) continue;
    const v = d < 4 ? prog(d, 0, 4, outPow3) : d < 10 ? 1 : 1 - prog(d, 10, 22, outPow3);
    s = Math.max(s, 1 + 0.08 * v);
  }
  let sx = 0;
  let sy = 0;
  let split = 0;
  let flash = 0;
  for (const p of impacts) {
    const d = f - p;
    if (d < 0 || d > 8) continue;
    const k = Math.max(0, 1 - d / 6);
    sx += jitter(f, `sx${p}`, 1) * 6 * k;
    sy += jitter(f, `sy${p}`, 1) * 6 * k;
    split = Math.max(split, 8 * k);
    if (d < 2) flash = 0.25;
    s = Math.max(s, 1 + 0.02 * k);
  }
  return (
    <AbsoluteFill>
      <AbsoluteFill
        style={{
          transform: `translate(${sx}px, ${sy}px) scale(${s})`,
          filter: split > 0.5 ? `drop-shadow(${split}px 0 0 rgba(255,40,40,.75)) drop-shadow(${-split}px 0 0 rgba(80,230,255,.75))` : undefined,
        }}
      >
        {children}
      </AbsoluteFill>
      {flash > 0 && <AbsoluteFill style={{ background: '#fff', opacity: flash }} />}
    </AbsoluteFill>
  );
};

/** Slow Ken Burns: scale 1.00→`to` across `len`, slight pan, plus sub-pixel drift. */
export const KenBurns: React.FC<{ len: number; to?: number; seed?: string; children: React.ReactNode }> = ({ len, to = 1.06, seed = 'kb', children }) => {
  const f = useF();
  const t = clamp(f / Math.max(len, 1));
  const dx = (rnd(seed + 'x') - 0.5) * 40 * t + Math.sin(f / 37) * 0.6;
  const dy = (rnd(seed + 'y') - 0.5) * 24 * t + Math.cos(f / 43) * 0.6;
  return (
    <AbsoluteFill style={{ transform: `translate(${dx}px, ${dy}px) scale(${1 + (to - 1) * t})` }}>{children}</AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ shot sequencer */

export type Enter = 'cut' | 'fade' | 'glitch' | 'zoom' | 'push' | 'flash' | 'rise';
export type Shot = { at: number; el: React.ReactNode; enter?: Enter; drift?: number };
const ENTER_LEN: Record<Enter, number> = { cut: 0, fade: 9, glitch: 9, zoom: 13, push: 12, flash: 3, rise: 12 };

const EnterFx: React.FC<{ type: Enter; children: React.ReactNode }> = ({ type, children }) => {
  const f = useF();
  const L = ENTER_LEN[type];
  if (f >= L || type === 'cut') return <AbsoluteFill>{children}</AbsoluteFill>;
  const p = clamp(f / Math.max(L, 1));
  let style: React.CSSProperties = {};
  if (type === 'fade') style = { opacity: outPow3(p) };
  if (type === 'rise') style = { opacity: outPow3(p), transform: `translateY(${(1 - outExpo(p)) * 40}px)` };
  if (type === 'zoom') style = { opacity: outPow3(p), transform: `scale(${1.3 - 0.3 * outExpo(p)})`, filter: `blur(${(1 - p) * 10}px)` };
  if (type === 'push') style = { opacity: outPow3(p), transform: `translateX(${(1 - outExpo(p)) * 160}px)` };
  if (type === 'glitch') {
    const vis = [1, 0, 1, 1, 0, 1, 1, 1, 1][f] ?? 1;
    const x = jitter(f, 'gl', 1) * 40 * (1 - p);
    const sp = 10 * (1 - p);
    style = {
      opacity: vis,
      transform: `translateX(${x}px) skewX(${jitter(f, 'gk', 1) * 4 * (1 - p)}deg)`,
      filter: `drop-shadow(${sp}px 0 0 rgba(255,40,40,.8)) drop-shadow(${-sp}px 0 0 rgba(80,230,255,.8))`,
    };
  }
  return (
    <AbsoluteFill style={style}>
      {children}
      {type === 'flash' && <AbsoluteFill style={{ background: '#fff', opacity: 0.35 * (1 - p) }} />}
      {type === 'glitch' && <GlitchBars f={f} amount={1 - p} />}
    </AbsoluteFill>
  );
};

export const GlitchBars: React.FC<{ f: number; amount: number; seed?: string }> = ({ f, amount, seed = 'gb' }) => {
  if (amount <= 0.02) return null;
  const bars = Array.from({ length: 9 }, (_, i) => {
    const r = rnd(`${seed}-${i}-${Math.floor(f)}`);
    return (
      <div
        key={i}
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: `${r * 100}%`,
          height: 4 + rnd(`${seed}h${i}${f}`) * 26,
          background: i % 3 === 0 ? C.alarm : i % 3 === 1 ? C.ice : '#fff',
          opacity: 0.18 * amount,
          transform: `translateX(${(rnd(`${seed}x${i}${f}`) - 0.5) * 300}px)`,
          mixBlendMode: 'screen',
        }}
      />
    );
  });
  return <AbsoluteFill style={{ pointerEvents: 'none' }}>{bars}</AbsoluteFill>;
};

/**
 * Plays shots back to back on scene-local frames. Each shot keeps rendering under the next one
 * while the next one's entrance runs; an incoming 'zoom' also scales the outgoing shot (zoomThrough).
 */
export const Shots: React.FC<{ shots: Shot[]; end: number }> = ({ shots, end }) => {
  const list = [...shots].sort((a, b) => a.at - b.at);
  return (
    <AbsoluteFill>
      {list.map((sh, i) => {
        const next = list[i + 1];
        const enterNext = next ? ENTER_LEN[next.enter ?? 'cut'] : 0;
        const len = (next ? next.at : end) - sh.at + enterNext;
        return (
          <At key={i} from={sh.at} len={Math.max(1, len)}>
            <ExitFx outAt={next ? next.at - sh.at : 1e9} type={next?.enter ?? 'cut'}>
              <EnterFx type={sh.enter ?? 'cut'}>
                {sh.drift === 0 ? sh.el : <Drift len={len} amount={sh.drift ?? 0.025} seed={`d${i}${sh.at}`}>{sh.el}</Drift>}
              </EnterFx>
            </ExitFx>
          </At>
        );
      })}
    </AbsoluteFill>
  );
};

const ExitFx: React.FC<{ outAt: number; type: Enter; children: React.ReactNode }> = ({ outAt, type, children }) => {
  const f = useF();
  if (f < outAt) return <AbsoluteFill>{children}</AbsoluteFill>;
  const p = clamp((f - outAt) / Math.max(ENTER_LEN[type], 1));
  let style: React.CSSProperties = {};
  if (type === 'zoom') style = { transform: `scale(${1 + 0.7 * inPow3(p)})`, opacity: 1 - p };
  if (type === 'push') style = { transform: `translateX(${-inPow3(p) * 160}px)`, opacity: 1 - p };
  if (type === 'fade' || type === 'rise') style = { opacity: 1 - p };
  return <AbsoluteFill style={style}>{children}</AbsoluteFill>;
};

const Drift: React.FC<{ len: number; amount: number; seed: string; children: React.ReactNode }> = ({ len, amount, seed, children }) => {
  const f = useF();
  const t = clamp(f / Math.max(len, 1));
  const dx = (rnd(seed + 'x') - 0.5) * 30 * t;
  const dy = (rnd(seed + 'y') - 0.5) * 16 * t;
  return <AbsoluteFill style={{ transform: `translate(${dx}px, ${dy}px) scale(${1 + amount * t})` }}>{children}</AbsoluteFill>;
};

/* ------------------------------------------------------------------ typography & tags */

export const Kicker: React.FC<{ children: React.ReactNode; color?: string; size?: number; style?: React.CSSProperties }> = ({
  children,
  color = C.mute,
  size = 26,
  style,
}) => (
  <div style={{ fontFamily: F.mono, fontSize: size, letterSpacing: '0.14em', color, textTransform: 'uppercase', ...style }}>{children}</div>
);

export const Big: React.FC<{ children: React.ReactNode; size?: number; color?: string; style?: React.CSSProperties }> = ({
  children,
  size = 160,
  color = C.bone,
  style,
}) => (
  <div style={{ fontFamily: F.display, fontSize: size, lineHeight: 0.92, letterSpacing: '0.04em', color, ...style }}>{children}</div>
);

export const Center: React.FC<{ children: React.ReactNode; style?: React.CSSProperties; gap?: number }> = ({ children, style, gap = 18 }) => (
  <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', flexDirection: 'column', gap, textAlign: 'center', ...style }}>
    {children}
  </AbsoluteFill>
);

/** Mono source tag, bottom-left, auto-shown with every figure. */
export const SourceTag: React.FC<{ text: string; at?: number; until?: number }> = ({ text, at = 6, until }) => {
  const f = useF();
  const v = inOutVis(f, at, 12, until, 8);
  if (v <= 0) return null;
  return (
    <div
      style={{
        position: 'absolute',
        left: SAFE.x,
        bottom: SAFE.y + 6,
        fontFamily: F.mono,
        fontSize: 21,
        letterSpacing: '0.12em',
        color: C.mute,
        opacity: v,
        transform: `translateY(${(1 - v) * 10}px)`,
        display: 'flex',
        alignItems: 'center',
        gap: 12,
      }}
    >
      <span style={{ width: 8, height: 8, background: C.gold, display: 'inline-block' }} />
      SOURCE: {text}
    </div>
  );
};

export const Badge: React.FC<{ text: string; at?: number; until?: number; color?: string }> = ({ text, at = 0, until, color = C.bone }) => {
  const f = useF();
  const v = inOutVis(f, at, 12, until, 10);
  if (v <= 0) return null;
  return (
    <div
      style={{
        position: 'absolute',
        left: SAFE.x,
        top: SAFE.y,
        fontFamily: F.mono,
        fontSize: 20,
        letterSpacing: '0.14em',
        color,
        padding: '10px 16px',
        border: `1px solid ${C.line}`,
        background: 'rgba(7,8,11,.72)',
        opacity: v,
        transform: `translateX(${(1 - v) * -16}px)`,
        display: 'flex',
        alignItems: 'center',
        gap: 12,
      }}
    >
      <span style={{ width: 9, height: 9, borderRadius: 9, background: C.alarm, opacity: Math.floor(f / 15) % 2 ? 1 : 0.35 }} />
      {text}
    </div>
  );
};

export const Panel: React.FC<{ children?: React.ReactNode; style?: React.CSSProperties; border?: string }> = ({ children, style, border = C.line }) => (
  <div
    style={{
      background: `linear-gradient(180deg, ${C.panel}, ${C.panel2})`,
      border: `1px solid ${border}`,
      borderRadius: 14,
      boxShadow: '0 30px 80px rgba(0,0,0,.55)',
      ...style,
    }}
  >
    {children}
  </div>
);

/* ------------------------------------------------------------------ numbers */

export const Counter: React.FC<{
  to: number;
  from?: number;
  at?: number;
  len?: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  size?: number;
  color?: string;
  glow?: boolean;
  label?: string;
  labelColor?: string;
}> = ({ to, from = 0, at = 0, len = 40, prefix = '', suffix = '', decimals = 0, size = 150, color = C.gold, glow = true, label, labelColor = C.mute }) => {
  const f = useF();
  const t = prog(f, at, len, outExpo);
  const v = from + (to - from) * t;
  const landed = f >= at + len;
  const shown = decimals ? v.toFixed(decimals) : fmtInt(v);
  const sc = landed ? pop(f, at + len, 10) : 1;
  const vis = prog(f, at - 4, 8);
  return (
    <div style={{ textAlign: 'center', opacity: vis }}>
      <div
        style={{
          fontFamily: F.display,
          fontSize: size,
          color,
          lineHeight: 1,
          letterSpacing: '0.02em',
          fontVariantNumeric: 'tabular-nums',
          transform: `scale(${sc || 1})`,
          textShadow: glow && landed ? `0 0 ${30 + 20 * Math.max(0, 1 - (f - at - len) / 30)}px ${color}88` : 'none',
        }}
      >
        {prefix}
        {shown}
        {suffix}
      </div>
      {label && <Kicker color={labelColor} size={28} style={{ marginTop: 14 }}>{label}</Kicker>}
    </div>
  );
};

/** Neutral token circle with ticker (no logos). */
export const TokenCircle: React.FC<{ ticker: string; size?: number; color?: string; style?: React.CSSProperties }> = ({
  ticker,
  size = 120,
  color = C.bone,
  style,
}) => (
  <div
    style={{
      width: size,
      height: size,
      borderRadius: size,
      border: `3px solid ${color}`,
      background: `radial-gradient(circle at 35% 30%, ${color}33, ${C.panel} 70%)`,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: F.mono,
      fontWeight: 700,
      fontSize: size * (ticker.length > 4 ? 0.2 : 0.26),
      color,
      boxShadow: `0 0 40px ${color}33`,
      ...style,
    }}
  >
    {ticker}
  </div>
);

/* ------------------------------------------------------------------ quote card */

export const QuoteCard: React.FC<{ quote: string; who: string; role?: string; where: string; at?: number; accent?: string; size?: number }> = ({
  quote,
  who,
  role,
  where,
  at = 0,
  accent = C.gold,
  size = 74,
}) => {
  const f = useF();
  const v = damp(f, at, 16);
  const shown = typeOn(quote, f, at + 6, 34);
  return (
    <Center>
      <div style={{ opacity: v, transform: `translateY(${(1 - v) * 30}px) scale(${0.97 + 0.03 * v})`, maxWidth: 1420, textAlign: 'left' }}>
        <div style={{ fontFamily: F.display, fontSize: 220, color: accent, lineHeight: 0.6, height: 110 }}>“</div>
        <div style={{ fontFamily: F.body, fontWeight: 700, fontSize: size, color: C.bone, lineHeight: 1.15, minHeight: size * 1.2 }}>
          {shown}
          <span style={{ opacity: shown.length < quote.length && Math.floor(f / 8) % 2 ? 1 : 0, color: accent }}>▍</span>
        </div>
        <div style={{ marginTop: 36, height: 2, width: 140 * prog(f, at + 10, 20), background: accent }} />
        <div style={{ marginTop: 22, fontFamily: F.body, fontWeight: 600, fontSize: 34, color: C.bone, opacity: prog(f, at + 14, 14) }}>
          {who}
          {role && <span style={{ color: C.mute, fontWeight: 500 }}> · {role}</span>}
        </div>
        <Kicker size={22} style={{ marginTop: 10, opacity: prog(f, at + 18, 14) }}>{where}</Kicker>
      </div>
    </Center>
  );
};

/* ------------------------------------------------------------------ clock */

export const hms = (secOfDay: number) => {
  const s = ((Math.floor(secOfDay) % 86400) + 86400) % 86400;
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const ss = s % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(ss).padStart(2, '0')}`;
};

export const UTCClock: React.FC<{ sec: number; size?: number; flash?: boolean; label?: boolean; color?: string; typed?: number }> = ({
  sec,
  size = 120,
  flash = false,
  label = true,
  color = C.bone,
  typed,
}) => {
  const f = useF();
  const text = hms(sec);
  const shown = typed === undefined ? text : text.slice(0, Math.max(0, Math.floor(typed)));
  const col = flash && Math.floor(f / 4) % 2 === 0 ? C.alarm : color;
  return (
    <div style={{ fontFamily: F.mono, fontWeight: 500, fontSize: size, color: col, letterSpacing: '0.04em', fontVariantNumeric: 'tabular-nums', display: 'flex', alignItems: 'baseline', gap: size * 0.2 }}>
      <span style={{ textShadow: flash ? `0 0 30px ${C.alarm}` : 'none' }}>{shown}</span>
      {label && (typed === undefined || typed >= text.length) && <span style={{ fontSize: size * 0.32, color: C.mute }}>UTC</span>}
    </div>
  );
};

/* ------------------------------------------------------------------ stamps & cards */

export const Stamp: React.FC<{ text: string; at?: number; color?: string; size?: number; rotate?: number; sub?: string }> = ({
  text,
  at = 0,
  color = C.alarm,
  size = 64,
  rotate = -6,
  sub,
}) => {
  const f = useF();
  const t = clamp((f - at) / 8);
  if (t <= 0) return null;
  const sc = interpolate(t, [0, 0.7, 1], [2.2, 0.94, 1]);
  return (
    <div
      style={{
        display: 'inline-block',
        transform: `rotate(${rotate}deg) scale(${sc})`,
        opacity: Math.min(1, t * 2),
        border: `5px solid ${color}`,
        color,
        padding: '10px 26px',
        fontFamily: F.display,
        fontSize: size,
        letterSpacing: '0.08em',
        boxShadow: `0 0 40px ${color}44, inset 0 0 20px ${color}22`,
        background: 'rgba(7,8,11,.55)',
        textAlign: 'center',
      }}
    >
      {text}
      {sub && <div style={{ fontFamily: F.mono, fontSize: size * 0.3, letterSpacing: '0.12em', marginTop: 4 }}>{sub}</div>}
    </div>
  );
};

/** Big headline line that wipes in (used for kinetic statements). */
export const Headline: React.FC<{ text: string; at?: number; size?: number; color?: string; sub?: string; subColor?: string }> = ({
  text,
  at = 0,
  size = 150,
  color = C.bone,
  sub,
  subColor = C.mute,
}) => {
  const f = useF();
  const words = text.split(' ');
  return (
    <Center gap={26}>
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: `0 ${size * 0.22}px`, maxWidth: 1650 }}>
        {words.map((w, i) => {
          const p = prog(f, at + i * 3, 14);
          return (
            <span key={i} style={{ overflow: 'hidden', display: 'inline-block' }}>
              <span style={{ display: 'inline-block', transform: `translateY(${(1 - p) * 110}%)`, fontFamily: F.display, fontSize: size, color, letterSpacing: '0.04em', lineHeight: 1 }}>
                {w}
              </span>
            </span>
          );
        })}
      </div>
      {sub && <Kicker color={subColor} size={28} style={{ opacity: prog(f, at + 10, 14) }}>{sub}</Kicker>}
    </Center>
  );
};

/** Lower third explainer. */
export const LowerThird: React.FC<{ title: string; body: string; at?: number; accent?: string }> = ({ title, body, at = 0, accent = C.ice }) => {
  const f = useF();
  const v = damp(f, at, 16);
  return (
    <div style={{ position: 'absolute', left: SAFE.x, top: 640, opacity: v, transform: `translateX(${(1 - v) * -40}px)` }}>
      <div style={{ display: 'flex', alignItems: 'stretch', gap: 22 }}>
        <div style={{ width: 6, background: accent, transform: `scaleY(${v})`, transformOrigin: 'top' }} />
        <div>
          <div style={{ fontFamily: F.display, fontSize: 64, color: accent, letterSpacing: '0.05em' }}>{title}</div>
          <div style={{ fontFamily: F.body, fontSize: 32, color: C.bone, maxWidth: 1000, marginTop: 6, lineHeight: 1.3 }}>{body}</div>
        </div>
      </div>
    </div>
  );
};

/** Struck-through small counter ("Not thousands. Not millions."). */
export const Struck: React.FC<{ text: string; at: number; strikeAt: number; size?: number }> = ({ text, at, strikeAt, size = 110 }) => {
  const f = useF();
  const v = prog(f, at, 10);
  const s = prog(f, strikeAt, 8);
  return (
    <div style={{ position: 'relative', display: 'inline-block', opacity: v * (1 - 0.55 * s), transform: `translateY(${(1 - v) * 20}px)` }}>
      <span style={{ fontFamily: F.display, fontSize: size, color: C.bone, letterSpacing: '0.03em', fontVariantNumeric: 'tabular-nums' }}>{text}</span>
      <div style={{ position: 'absolute', left: -10, top: '50%', height: 8, background: C.alarm, width: `calc(${s * 100}% + 20px)`, transform: 'rotate(-4deg)' }} />
    </div>
  );
};

export { At, Rebase, useF };
