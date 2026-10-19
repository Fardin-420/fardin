import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { AbsoluteFill, continueRender, delayRender, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import { Engine } from './engine/Engine';
import { SCENES } from './scenes';
import { envelope, timeline } from './data';
import { Overlay } from './overlay/Overlay';

export type ShowreelProps = { quality: number };

// One engine per browser tab; Remotion renders many frames per tab.
let engine: Engine | null = null;
let enginePromise: Promise<Engine> | null = null;

export const Showreel: React.FC<ShowreelProps> = ({ quality }) => {
  const frame = useCurrentFrame();
  const { width, height, fps } = useVideoConfig();
  const ref = useRef<HTMLCanvasElement>(null);
  const [ready, setReady] = useState(false);
  const [handle] = useState(() => delayRender('NPC engine init', { timeoutInMilliseconds: 240000 }));
  const w = Math.round(width * quality);
  const h = Math.round(height * quality);

  useEffect(() => {
    if (!ref.current) return;
    if (!enginePromise) {
      enginePromise = (async () => {
        const e = new Engine(ref.current!, w, h, timeline, envelope);
        await e.load(staticFile, SCENES);
        engine = e;
        return e;
      })();
    }
    enginePromise
      .then(() => {
        setReady(true);
        continueRender(handle);
      })
      .catch((err) => {
        console.error(err);
        throw err;
      });
  }, [handle, w, h]);

  useLayoutEffect(() => {
    if (ready && engine) engine.render(frame / fps, frame);
  }, [frame, ready, fps]);

  return (
    <AbsoluteFill style={{ backgroundColor: '#000' }}>
      <canvas ref={ref} width={w} height={h} style={{ width, height }} />
      <Overlay frame={frame} fps={fps} />
    </AbsoluteFill>
  );
};
