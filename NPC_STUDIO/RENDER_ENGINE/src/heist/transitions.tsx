import React from 'react';
import { AbsoluteFill } from 'remotion';
import type { TransitionPresentation, TransitionPresentationComponentProps } from '@remotion/transitions';
import { C } from './theme';
import { LightLeak } from './components/core';
import { rnd } from './lib/anim';

type P = Record<string, never>;

const DipBlack: React.FC<TransitionPresentationComponentProps<P>> = ({ children, presentationDirection, presentationProgress: p }) => {
  const o = presentationDirection === 'exiting' ? Math.max(0, 1 - p * 2) : Math.max(0, p * 2 - 1);
  return <AbsoluteFill style={{ opacity: o }}>{children}</AbsoluteFill>;
};

const FilmBurn: React.FC<TransitionPresentationComponentProps<P>> = ({ children, presentationDirection, presentationProgress: p }) => {
  if (presentationDirection === 'exiting') return <AbsoluteFill style={{ opacity: 1 - p }}>{children}</AbsoluteFill>;
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ opacity: p }}>{children}</AbsoluteFill>
      <LightLeak p={p} intensity={1.1} />
    </AbsoluteFill>
  );
};

const icePoly = (p: number) => {
  const n = 28;
  const R = 1500 * p;
  const pts = Array.from({ length: n }, (_, i) => {
    const a = (i / n) * Math.PI * 2;
    const r = R * (i % 2 ? 0.55 + 0.25 * rnd(`ip${i}`) : 1);
    return `${960 + Math.cos(a) * r}px ${540 + Math.sin(a) * r}px`;
  });
  return `polygon(${pts.join(',')})`;
};

const IceWipe: React.FC<TransitionPresentationComponentProps<P>> = ({ children, presentationDirection, presentationProgress: p }) => {
  if (presentationDirection === 'exiting') return <AbsoluteFill>{children}</AbsoluteFill>;
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ clipPath: icePoly(p), WebkitClipPath: icePoly(p) }}>{children}</AbsoluteFill>
      <AbsoluteFill style={{ clipPath: icePoly(Math.min(1, p * 1.04 + 0.02)), background: C.ice, opacity: 0.35 * (1 - p), mixBlendMode: 'screen' }} />
    </AbsoluteFill>
  );
};

const DataWipe: React.FC<TransitionPresentationComponentProps<P>> = ({ children, presentationDirection, presentationProgress: p }) => {
  if (presentationDirection === 'exiting') return <AbsoluteFill>{children}</AbsoluteFill>;
  const y = p * 1080;
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ clipPath: `inset(0 0 ${100 - p * 100}% 0)` }}>{children}</AbsoluteFill>
      <div style={{ position: 'absolute', left: 0, right: 0, top: y - 3, height: 6, background: C.ice, boxShadow: `0 0 30px 8px ${C.ice}`, opacity: p < 1 ? 1 : 0 }} />
    </AbsoluteFill>
  );
};

const mk = (component: React.FC<TransitionPresentationComponentProps<P>>): TransitionPresentation<P> => ({ component, props: {} as P });

export const PRESENTATIONS: Record<string, TransitionPresentation<P>> = {
  dipBlack: mk(DipBlack),
  filmBurn: mk(FilmBurn),
  iceWipe: mk(IceWipe),
  dataWipe: mk(DataWipe),
};
