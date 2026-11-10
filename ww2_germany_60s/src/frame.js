/**
 * frame.js — render single frames to PNG for inspection.
 *   npm run frame -- 450            -> out/frames/frame_0450.png
 *   npm run frame -- 0 450 900      (several)
 *   npm run frame -- 450 --scale 0.5
 */
'use strict';

const fs = require('fs');
const path = require('path');

const args = process.argv.slice(2);
const si = args.indexOf('--scale');
const scale = si >= 0 ? +args[si + 1] : 1;
const di = args.indexOf('--dir');
const dir = di >= 0 ? path.resolve(args[di + 1]) : path.resolve(__dirname, '..', 'out', 'frames');
const frames = args.filter((a, i) => /^\d+$/.test(a) && args[i - 1] !== '--scale');
if (!frames.length) { console.log('usage: npm run frame -- <frameIndex> [more...] [--scale 0.5]'); process.exit(1); }

const { renderFrame, TL } = require('./render');
fs.mkdirSync(dir, { recursive: true });
for (const f of frames.map(Number)) {
  if (f < 0 || f >= TL.totalFrames) { console.error(`frame ${f} out of range 0..${TL.totalFrames - 1}`); continue; }
  const t0 = Date.now();
  const buf = renderFrame(f, { scale }).toBuffer('image/png');
  const file = path.join(dir, `frame_${String(f).padStart(4, '0')}.png`);
  fs.writeFileSync(file, buf);
  console.log(`${path.relative(process.cwd(), file)}  (${Date.now() - t0} ms)`);
}
