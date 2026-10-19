import React from 'react';
import { Composition } from 'remotion';
import { Showreel } from './Showreel';
import { timeline } from './data';

export const Root: React.FC = () => (
  <Composition
    id="NPC-NoEditorJustCode"
    component={Showreel}
    width={timeline.width}
    height={timeline.height}
    fps={timeline.fps}
    durationInFrames={timeline.durationInFrames}
    defaultProps={{ quality: 1 }}
  />
);
