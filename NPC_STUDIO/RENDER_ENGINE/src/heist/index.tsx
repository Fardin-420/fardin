import React from 'react';
import { Composition, Still, registerRoot } from 'remotion';
import { TL } from './tl';
import { Doc } from './Doc';
import { ThumbA, ThumbB, ThumbC } from './Thumbs';

const Root: React.FC = () => (
  <>
    <Composition id="Heist" component={Doc} width={TL.width} height={TL.height} fps={TL.fps} durationInFrames={TL.durationInFrames} defaultProps={{ burnCaptions: true }} />
    <Still id="ThumbA" component={ThumbA} width={1280} height={720} />
    <Still id="ThumbB" component={ThumbB} width={1280} height={720} />
    <Still id="ThumbC" component={ThumbC} width={1280} height={720} />
  </>
);

registerRoot(Root);
