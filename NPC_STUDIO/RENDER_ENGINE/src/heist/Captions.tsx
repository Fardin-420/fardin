import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion';
import { C, F, SAFE } from './theme';
import { CAPTIONS, FPS } from './tl';

/** Premium documentary captions: Inter SemiBold ~52 px, max 2×34 chars, active word gold, key terms pop once. */
export const CaptionTrack: React.FC<{ enabled?: boolean }> = ({ enabled = true }) => {
  const frame = useCurrentFrame();
  if (!enabled) return null;
  const t = frame / FPS;
  if (CAPTIONS.hide.some(([a, b]) => t >= a && t <= b)) return null;
  const page = CAPTIONS.pages.find((p) => t >= p.s && t < p.e);
  if (!page) return null;
  const fadeIn = interpolate(t, [page.s, page.s + 0.1], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const fadeOut = interpolate(t, [page.e - 0.1, page.e], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const words = page.lines.flat();
  return (
    <AbsoluteFill style={{ justifyContent: 'flex-end', alignItems: 'center', paddingBottom: SAFE.captionBottom + 14, pointerEvents: 'none' }}>
      <div style={{ opacity: Math.min(fadeIn, fadeOut), textAlign: 'center' }}>
        {page.lines.map((line, li) => (
          <div key={li} style={{ fontFamily: F.body, fontWeight: 600, fontSize: 52, lineHeight: 1.22, color: '#fff', textShadow: '0 4px 18px rgba(0,0,0,.85), 0 0 2px rgba(0,0,0,.9)', whiteSpace: 'nowrap' }}>
            {line.map((w, wi) => {
              const idx = words.indexOf(w);
              const next = words[idx + 1];
              const active = t >= w.s && (next ? t < next.s : t < page.e);
              const popS = w.pop ? interpolate(t, [w.s, w.s + 0.12, w.s + 0.3], [1, 1.12, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }) : 1;
              return (
                <span key={wi} style={{ display: 'inline-block', marginRight: wi < line.length - 1 ? '0.26em' : 0, color: active || (w.pop && t >= w.s) ? C.gold : '#fff', transform: `scale(${popS})` }}>
                  {w.w}
                </span>
              );
            })}
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};
