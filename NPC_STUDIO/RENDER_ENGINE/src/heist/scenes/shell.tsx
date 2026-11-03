import React from 'react';
import { AbsoluteFill } from 'remotion';
import { C } from '../theme';
import { SceneData, cue, dur, wordAt } from '../tl';
import { At, Rebase } from '../lib/frame';
import { Camera, Stage } from '../components/core';
import { ChapterCard } from '../components/diagrams2';

export const CARD = 75;

export const SceneShell: React.FC<{ s: SceneData; accent?: string; children: React.ReactNode; overlay?: React.ReactNode; grade?: (c: React.ReactNode) => React.ReactNode }> = ({
  s,
  accent = C.alarm,
  children,
  overlay,
  grade,
}) => {
  const body = (
    <Camera punches={s.punches} impacts={s.impacts}>
      {children}
    </Camera>
  );
  return (
    <AbsoluteFill>
      <Stage accent={accent} />
      {grade ? grade(body) : body}
      {overlay}
      {s.chapter && (
        <At from={-12} len={CARD + 13}>
          <ChapterCard n={s.chapter} title={s.chapterTitle ?? ''} date={s.chapterDate} lead={12} />
        </At>
      )}
    </AbsoluteFill>
  );
};

/** Render children as they look `at` frames into their own animation (montage snapshots). */
export const Snap: React.FC<{ at: number; children: React.ReactNode }> = ({ at, children }) => <Rebase by={-at}>{children}</Rebase>;

export const helpers = (s: SceneData) => ({
  c: (n: string) => cue(s, n),
  w: (t: string, n = 0) => wordAt(s, t, n),
  D: dur(s),
});
