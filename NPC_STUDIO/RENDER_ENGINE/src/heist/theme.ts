import { continueRender, delayRender, staticFile } from 'remotion';

// Self-hosted fonts (headless Chromium has no proxy route to Google Fonts at render time).
const FACES: [string, string, string][] = [
  ['Bebas Neue', 'BebasNeue-400.woff2', '400'],
  ['Inter', 'Inter-400.woff2', '100 900'],
  ['JetBrains Mono', 'JetBrainsMono-400.woff2', '100 800'],
];
if (typeof document !== 'undefined' && typeof FontFace !== 'undefined') {
  const handle = delayRender('heist fonts');
  Promise.all(
    FACES.map(([fam, file, weight]) =>
      new FontFace(fam, `url(${staticFile(`heist/fonts/${file}`)}) format('woff2')`, { weight }).load().then((f) => {
        (document.fonts as unknown as { add: (f: FontFace) => void }).add(f);
      }),
    ),
  )
    .then(() => continueRender(handle))
    .catch((e) => {
      console.error('font load failed', e);
      continueRender(handle);
    });
}

export const C = {
  ink: '#07080B',
  panel: '#13161B',
  panel2: '#0D0F13',
  line: '#262B33',
  alarm: '#FF3B3B',
  ice: '#6FE7FF',
  gold: '#E9B949',
  bone: '#EDEDED',
  mute: '#8A8F98',
  green: '#4ADE80',
} as const;


export const F = {
  display: `'Bebas Neue', Impact, sans-serif`,
  body: `'Inter', Arial, sans-serif`,
  mono: `'JetBrains Mono', monospace`,
};

/** Title-safe area (spec §5): 96 px left/right, 54 px top/bottom; captions stay above the bottom 140 px. */
export const SAFE = { x: 96, y: 54, captionBottom: 140 };
export const W = 1920;
export const H = 1080;
