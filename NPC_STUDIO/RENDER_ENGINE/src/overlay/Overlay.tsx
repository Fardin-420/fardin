import React from 'react';
import { AbsoluteFill, staticFile } from 'remotion';
import { envelope, timeline } from '../data';
import { clamp, easeOutCubic, easeOutExpo, impulse, range } from '../engine/util';

// Crisp 2D typography layered over the WebGL frame: HUD, captions and the
// kinetic word choreography. Like the 3D layer, everything is a pure function
// of the frame number.

const IVORY = '#f3eee3';
const RED = '#ff2b1c';
const MONO = "'NPC Mono', 'JetBrains Mono', monospace";
const DISPLAY = "'NPC Display', 'Inter Display', sans-serif";

const fontFaces = `
@font-face { font-family: 'NPC Display'; font-weight: 900; src: url('${staticFile('fonts/InterDisplay-Black.otf')}'); }
@font-face { font-family: 'NPC Display'; font-weight: 800; src: url('${staticFile('fonts/InterDisplay-ExtraBold.otf')}'); }
@font-face { font-family: 'NPC Display'; font-weight: 500; src: url('${staticFile('fonts/InterDisplay-Medium.otf')}'); }
@font-face { font-family: 'NPC Display'; font-weight: 300; src: url('${staticFile('fonts/InterDisplay-Light.otf')}'); }
@font-face { font-family: 'NPC Mono'; font-weight: 400; src: url('${staticFile('fonts/JetBrainsMono-Regular.ttf')}'); }
@font-face { font-family: 'NPC Mono'; font-weight: 500; src: url('${staticFile('fonts/JetBrainsMono-Medium.ttf')}'); }
`;

// Lines whose words are already set as hero typography get no caption.
const NO_CAPTION = new Set(['L05', 'L06', 'L07', 'L08', 'L13', 'L14', 'L15']);

const cue = (k: string) => timeline.cues[k];
const line = (id: string) => timeline.lines.find((l) => l.id === id)!;

/** Letters resolve from blur + offset, staggered — used for hero words. */
const KineticWord: React.FC<{
  text: string; t: number; at: number; out: number; size: number; y: number;
  weight?: number; color?: string; tracking?: number; accent?: string;
}> = ({ text, t, at, out, size, y, weight = 900, color = IVORY, tracking = -0.02, accent }) => {
  if (t < at - 0.05 || t > out + 0.4) return null;
  const leave = easeOutCubic(range(t, out, out + 0.3));
  return (
    <div style={{
      position: 'absolute', left: 0, right: 0, top: y, textAlign: 'center',
      fontFamily: DISPLAY, fontWeight: weight, fontSize: size, letterSpacing: `${tracking}em`,
      color, lineHeight: 1, whiteSpace: 'pre',
      transform: `translateY(${-leave * 40}px) scale(${1 + leave * 0.06})`,
      opacity: 1 - leave, filter: `blur(${leave * 14}px)`,
    }}>
      {[...text].map((ch, i) => {
        const k = easeOutExpo(range(t, at + i * 0.022, at + i * 0.022 + 0.42));
        return (
          <span key={i} style={{
            display: 'inline-block', opacity: k,
            transform: `translateY(${(1 - k) * 0.5 * size}px) rotateX(${(1 - k) * 70}deg)`,
            filter: `blur(${(1 - k) * 18}px)`,
            color: accent && ch === '.' ? accent : undefined,
            textShadow: `0 0 ${30 * (1 - k) + 18}px rgba(243,238,227,${0.18 + (1 - k) * 0.5})`,
          }}>{ch}</span>
        );
      })}
    </div>
  );
};

const Hud: React.FC<{ frame: number; t: number }> = ({ frame, t }) => {
  const a = 0.5 * clamp(range(t, cue('pulse'), cue('pulse') + 0.6));
  const fadeEnd = 1 - range(t, cue('emblem_lock') - 0.6, cue('emblem_lock'));
  const o = a * fadeEnd;
  if (o <= 0) return null;
  const base: React.CSSProperties = { position: 'absolute', fontFamily: MONO, fontSize: 22, color: IVORY, letterSpacing: '0.12em', opacity: o };
  const tc = `${String(Math.floor(t / 60)).padStart(2, '0')}:${String(Math.floor(t % 60)).padStart(2, '0')}:${String(frame % timeline.fps).padStart(2, '0')}`;
  return (
    <>
      <div style={{ ...base, left: 64, top: 74 }}>NPC/STUDIO</div>
      <div style={{ ...base, right: 64, top: 74, textAlign: 'right' }}>1080×1920 · {timeline.fps} FPS</div>
      <div style={{ ...base, left: 64, bottom: 74 }}>
        <span style={{ color: RED }}>●</span> FRAME {String(frame).padStart(4, '0')} / {timeline.durationInFrames}
      </div>
      <div style={{ ...base, right: 64, bottom: 74, textAlign: 'right' }}>TC {tc}</div>
    </>
  );
};

const Captions: React.FC<{ t: number }> = ({ t }) => {
  const l = timeline.lines.find((x) => t >= x.start - 0.08 && t <= x.end + 0.3);
  if (!l || NO_CAPTION.has(l.id)) return null;
  const k = easeOutCubic(range(t, l.start - 0.08, l.start + 0.15));
  const out = range(t, l.end + 0.1, l.end + 0.3);
  return (
    <div style={{
      position: 'absolute', left: 90, right: 90, bottom: 260, textAlign: 'center',
      fontFamily: DISPLAY, fontWeight: 500, fontSize: 44, letterSpacing: '0.01em', color: IVORY,
      opacity: k * (1 - out) * 0.92, transform: `translateY(${(1 - k) * 14}px)`,
      filter: `blur(${(1 - k) * 6 + out * 6}px)`, textShadow: '0 2px 24px rgba(0,0,0,0.9)',
    }}>
      {l.text}
    </div>
  );
};

/** Scene 03: "EVERY TRANSITION. / EVERY EFFECT. / EVERY SINGLE FRAME. / WRITTEN IN CODE." */
const S03Words: React.FC<{ t: number }> = ({ t }) => {
  const L5 = line('L05'), L6 = line('L06'), L7 = line('L07'), L8 = line('L08');
  const hit = impulse(t - cue('frame_hit'), 7);
  return (
    <>
      <KineticWord text="EVERY" t={t} at={L5.start} out={L7.start - 0.15} size={64} y={560} weight={300} tracking={0.4} />
      <KineticWord text="TRANSITION." t={t} at={L5.start + 0.18} out={L6.start - 0.12} size={118} y={640} accent={RED} />
      <KineticWord text="EFFECT." t={t} at={L6.start + 0.12} out={L7.start - 0.15} size={150} y={640} accent={RED} />
      <div style={{ transform: `scale(${1 + hit * 0.05})`, position: 'absolute', inset: 0 }}>
        <KineticWord text="EVERY SINGLE" t={t} at={L7.start} out={L8.start - 0.1} size={70} y={540} weight={300} tracking={0.32} />
        <KineticWord text="FRAME." t={t} at={L7.start + 0.32} out={L8.start - 0.1} size={230} y={620} accent={RED} />
      </div>
      <KineticWord text="WRITTEN IN" t={t} at={L8.start} out={cue('s04_in') - 0.3} size={70} y={1240} weight={300} tracking={0.32} />
      <KineticWord text="CODE." t={t} at={L8.start + 0.25} out={cue('s04_in') - 0.3} size={210} y={1320} accent={RED} />
    </>
  );
};

/** Scene 04: label + live meter for the voice signal. */
const S04Label: React.FC<{ t: number; frame: number }> = ({ t, frame }) => {
  const s = timeline.scenes.find((x) => x.id === 'S04')!;
  if (t < s.start || t > s.end) return null;
  const k = easeOutCubic(range(t, s.start + 0.2, s.start + 0.8)) * (1 - range(t, s.end - 0.25, s.end));
  const rms = envelope.signalRms(frame);
  const db = rms > 0.001 ? (20 * Math.log10(rms)).toFixed(1) : '-inf';
  return (
    <div style={{ position: 'absolute', left: 0, right: 0, top: 1420, textAlign: 'center', fontFamily: MONO, fontSize: 24, letterSpacing: '0.22em', color: IVORY, opacity: k * 0.75 }}>
      <span style={{ color: RED }}>●</span> SIGNAL · {envelope.source} · {db} dB
    </div>
  );
};

/** Scene 06 tagline lockup. */
const S06Type: React.FC<{ t: number }> = ({ t }) => {
  const tag = cue('tagline');
  const k1 = easeOutExpo(range(t, tag, tag + 0.8));
  const k2 = easeOutExpo(range(t, tag + 0.45, tag + 1.3));
  const w = range(t, tag + 0.2, tag + 1.4);
  if (t < tag - 0.05) return null;
  return (
    <>
      <div style={{
        position: 'absolute', left: 0, right: 0, top: 1300, textAlign: 'center',
        fontFamily: DISPLAY, fontWeight: 500, fontSize: 46, letterSpacing: `${0.34 + (1 - k1) * 0.3}em`,
        color: IVORY, opacity: k1, filter: `blur(${(1 - k1) * 12}px)`,
      }}>BUILT WITH CLAUDE CODE</div>
      <div style={{ position: 'absolute', left: '50%', top: 1392, height: 2, width: 520 * w, transform: 'translateX(-50%)', background: `linear-gradient(90deg, transparent, ${RED}, transparent)` }} />
      <div style={{
        position: 'absolute', left: 0, right: 0, top: 1430, textAlign: 'center',
        fontFamily: MONO, fontWeight: 400, fontSize: 25, letterSpacing: '0.28em',
        color: IVORY, opacity: k2 * 0.62,
      }}>100% CODE-DRIVEN MOTION DESIGN</div>
    </>
  );
};

export const Overlay: React.FC<{ frame: number; fps: number }> = ({ frame, fps }) => {
  const t = frame / fps;
  return (
    <AbsoluteFill style={{ pointerEvents: 'none' }}>
      <style>{fontFaces}</style>
      <Hud frame={frame} t={t} />
      <S03Words t={t} />
      <S04Label t={t} frame={frame} />
      <S06Type t={t} />
      <Captions t={t} />
    </AbsoluteFill>
  );
};
