import React from 'react';
import { AbsoluteFill } from 'remotion';
import { C, F } from './theme';
import { Rebase } from './lib/frame';
import { FilmGrain, Vignette } from './components/core';
import { PlateLaptop } from './components/plates';

const Frame: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AbsoluteFill style={{ background: C.ink, overflow: 'hidden' }}>
    <AbsoluteFill style={{ width: 1920, height: 1080, transform: 'scale(0.6667)', transformOrigin: '0 0' }}>
      {children}
      <Vignette amount={0.3} />
      <FilmGrain opacity={0.05} />
    </AbsoluteFill>
  </AbsoluteFill>
);

const Crack: React.FC<{ x: number; y: number; w: number; h: number }> = ({ x, y, w, h }) => (
  <svg width={w} height={h} style={{ position: 'absolute', left: x, top: y }}>
    <path d={`M ${w * 0.55} 0 L ${w * 0.48} ${h * 0.3} L ${w * 0.6} ${h * 0.46} L ${w * 0.5} ${h * 0.7} L ${w * 0.57} ${h}`} fill="none" stroke={C.ink} strokeWidth={14} />
    <path d={`M ${w * 0.48} ${h * 0.3} L ${w * 0.3} ${h * 0.4} M ${w * 0.6} ${h * 0.46} L ${w * 0.78} ${h * 0.55}`} fill="none" stroke={C.ink} strokeWidth={8} />
  </svg>
);

/** A — laptop + giant cracked gold "$6.3B" + small red "20 MINUTES". */
export const ThumbA: React.FC = () => (
  <Frame>
    <AbsoluteFill style={{ left: 520 }}>
      <Rebase by={-60}>
        <PlateLaptop len={400} mode="half" />
      </Rebase>
    </AbsoluteFill>
    <AbsoluteFill style={{ background: 'linear-gradient(90deg, #07080B 40%, rgba(7,8,11,.6) 55%, transparent 75%)' }} />
    <div style={{ position: 'absolute', left: 80, top: 210 }}>
      <div style={{ position: 'relative', fontFamily: F.display, fontSize: 470, lineHeight: 0.9, color: C.gold, textShadow: `0 0 60px ${C.gold}88, 0 10px 0 #6b4a12` }}>
        $6.3B
        <Crack x={20} y={0} w={760} h={420} />
      </div>
      <div style={{ fontFamily: F.display, fontSize: 150, color: C.alarm, letterSpacing: '0.04em', marginTop: 10, textShadow: `0 0 40px ${C.alarm}88` }}>20 MINUTES</div>
    </div>
  </Frame>
);

/** B — black frame, red clock "20:05" + "BINANCE" in our own type, cracked. */
export const ThumbB: React.FC = () => (
  <Frame>
    <AbsoluteFill style={{ background: `radial-gradient(900px 600px at 50% 45%, ${C.alarm}33, #000 75%)` }} />
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', flexDirection: 'column' }}>
      <div style={{ fontFamily: F.mono, fontWeight: 700, fontSize: 380, color: C.alarm, lineHeight: 1, textShadow: `0 0 80px ${C.alarm}` }}>20:05</div>
      <div style={{ position: 'relative', fontFamily: F.display, fontSize: 300, color: C.bone, letterSpacing: '0.08em', lineHeight: 1 }}>
        BINANCE
        <Crack x={180} y={0} w={900} h={300} />
      </div>
    </AbsoluteFill>
  </Frame>
);

/** C — small grey "2019 · $40M" → huge red-gold "2026 · $6.3B". */
export const ThumbC: React.FC = () => (
  <Frame>
    <AbsoluteFill style={{ background: 'linear-gradient(90deg, #15120e 0 34%, #07080B 34%)' }} />
    <div style={{ position: 'absolute', left: 90, top: 380, filter: 'sepia(.5) saturate(.5)' }}>
      <div style={{ fontFamily: F.display, fontSize: 130, color: C.mute }}>2019</div>
      <div style={{ fontFamily: F.display, fontSize: 170, color: C.mute }}>$40M</div>
    </div>
    <div style={{ position: 'absolute', left: 560, top: 400, fontFamily: F.display, fontSize: 200, color: C.bone }}>→</div>
    <div style={{ position: 'absolute', left: 820, top: 150 }}>
      <div style={{ fontFamily: F.display, fontSize: 230, color: C.alarm, lineHeight: 1 }}>2026</div>
      <div style={{ fontFamily: F.display, fontSize: 470, lineHeight: 0.9, color: C.gold, textShadow: `0 0 70px ${C.alarm}aa` }}>$6.3B</div>
    </div>
  </Frame>
);
