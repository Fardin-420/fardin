import React from 'react';
import { AbsoluteFill } from 'remotion';
import { TransitionSeries, linearTiming } from '@remotion/transitions';
import { TL, SceneData } from './tl';
import { Rebase } from './lib/frame';
import { FilmGrain, Vignette } from './components/core';
import { PRESENTATIONS } from './transitions';
import { CaptionTrack } from './Captions';
import { S01, S02, S03 } from './scenes/A';
import { S04, S05, S06 } from './scenes/B';
import { S07, S08, S09, S10 } from './scenes/C';

const SCENES: Record<string, React.FC<{ s: SceneData }>> = { S01, S02, S03, S04, S05, S06, S07, S08, S09, S10 };

export type DocProps = { burnCaptions: boolean };

/**
 * Scenes on the master clock. A transition of T frames is centred on the boundary B: the outgoing
 * scene is extended by T−⌊T/2⌋ frames, the incoming one starts ⌊T/2⌋ early and sees negative local
 * frames until B — so every cue stays frame-locked to the narration.
 */
export const Doc: React.FC<DocProps> = ({ burnCaptions = true }) => {
  const sc = TL.scenes;
  const half = (s: SceneData) => (PRESENTATIONS[s.transitionIn.type] ? Math.floor(s.transitionIn.frames / 2) : 0);
  const T = (s?: SceneData) => (s && PRESENTATIONS[s.transitionIn.type] ? s.transitionIn.frames : 0);
  const items: React.ReactNode[] = [];
  sc.forEach((s, i) => {
    const next = sc[i + 1];
    const hIn = i === 0 ? 0 : half(s);
    const extOut = next ? T(next) - half(next) : 0;
    const len = s.end - s.start + hIn + extOut;
    const Comp = SCENES[s.id];
    if (i > 0 && T(s) > 0) {
      items.push(
        <TransitionSeries.Transition key={`t${s.id}`} presentation={PRESENTATIONS[s.transitionIn.type]} timing={linearTiming({ durationInFrames: T(s) })} />,
      );
    }
    items.push(
      <TransitionSeries.Sequence key={s.id} durationInFrames={len}>
        <Rebase by={hIn}>
          <Comp s={s} />
        </Rebase>
      </TransitionSeries.Sequence>,
    );
  });
  return (
    <AbsoluteFill style={{ background: '#000' }}>
      <TransitionSeries>{items}</TransitionSeries>
      <Vignette amount={0.22} />
      <FilmGrain opacity={0.04} />
      <CaptionTrack enabled={burnCaptions} />
    </AbsoluteFill>
  );
};
