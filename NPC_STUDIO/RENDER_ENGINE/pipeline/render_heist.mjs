// THE 20-MINUTE HEIST — render driver.
//   node pipeline/render_heist.mjs stills <outDir> <frame,frame,...>
//   node pipeline/render_heist.mjs video <out.mp4> [startFrame] [endFrame]   (silent H.264, CRF 16)
//   node pipeline/render_heist.mjs ranges <outDir> <windows.json>   (one bundle; each [a,b] -> p<a>_<b>.mp4, skips existing)
//   node pipeline/render_heist.mjs thumbs <outDir>
import { bundle } from '@remotion/bundler';
import { renderMedia, renderStill, selectComposition } from '@remotion/renderer';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const engine = path.resolve(here, '..');
const studio = JSON.parse(fs.readFileSync(path.resolve(engine, '../CONFIG/studio.json'), 'utf8'));
const browserExecutable = process.env.NPC_BROWSER || studio.render.browser;
const chromiumOptions = { gl: process.env.NPC_GL || 'swangle', headless: true };
const [mode, out, a, b] = process.argv.slice(2);

const serveUrl = await bundle({ entryPoint: path.join(engine, 'src/heist/index.tsx'), publicDir: path.join(engine, 'public'), onProgress: () => {} });
const conc = Math.max(1, Math.min(os.cpus().length, Number(process.env.HEIST_CONCURRENCY || os.cpus().length)));

if (mode === 'stills') {
  const comp = await selectComposition({ serveUrl, id: 'Heist', inputProps: { burnCaptions: true }, browserExecutable, chromiumOptions });
  fs.mkdirSync(out, { recursive: true });
  for (const fr of a.split(',').map(Number)) {
    await renderStill({ serveUrl, composition: comp, frame: fr, output: path.join(out, `f${String(fr).padStart(6, '0')}.jpg`), imageFormat: 'jpeg', jpegQuality: 85, browserExecutable, chromiumOptions, inputProps: { burnCaptions: true } });
    process.stdout.write('.');
  }
  console.log(`\nstills -> ${out}`);
} else if (mode === 'video') {
  const comp = await selectComposition({ serveUrl, id: 'Heist', inputProps: { burnCaptions: true }, browserExecutable, chromiumOptions });
  const start = a ? Number(a) : 0;
  const end = b ? Number(b) : comp.durationInFrames - 1;
  const t0 = Date.now();
  let last = 0;
  await renderMedia({
    serveUrl,
    composition: comp,
    codec: 'h264',
    crf: 16,
    x264Preset: 'medium',
    pixelFormat: 'yuv420p',
    colorSpace: 'bt709',
    muted: true,
    enforceAudioTrack: false,
    outputLocation: out,
    frameRange: [start, end],
    concurrency: conc,
    browserExecutable,
    chromiumOptions,
    inputProps: { burnCaptions: true },
    timeoutInMilliseconds: 120000,
    onProgress: ({ renderedFrames, progress }) => {
      const now = Date.now();
      if (now - last > 30000) {
        last = now;
        const fps = renderedFrames / ((now - t0) / 1000);
        console.log(`${(progress * 100).toFixed(1)}%  ${renderedFrames}/${end - start + 1} frames  ${fps.toFixed(1)} fps`);
      }
    },
  });
  console.log(`video -> ${out}  (${((Date.now() - t0) / 60000).toFixed(1)} min, concurrency ${conc})`);
} else if (mode === 'ranges') {
  const comp = await selectComposition({ serveUrl, id: 'Heist', inputProps: { burnCaptions: true }, browserExecutable, chromiumOptions });
  fs.mkdirSync(out, { recursive: true });
  const wins = JSON.parse(fs.readFileSync(a, 'utf8'));
  const total = wins.reduce((n, [s, e]) => n + e - s + 1, 0);
  let done = 0;
  const t0 = Date.now();
  for (const [s, e] of wins) {
    const dst = path.join(out, `p${s}_${e}.mp4`);
    if (fs.existsSync(dst)) { done += e - s + 1; continue; }
    const tmp = dst.replace(/\.mp4$/, '.part.mp4');
    await renderMedia({
      serveUrl, composition: comp, codec: 'h264', crf: 16, x264Preset: 'medium', pixelFormat: 'yuv420p', colorSpace: 'bt709',
      muted: true, enforceAudioTrack: false, outputLocation: tmp, frameRange: [s, e], concurrency: conc,
      browserExecutable, chromiumOptions, inputProps: { burnCaptions: true }, timeoutInMilliseconds: 120000,
    });
    fs.renameSync(tmp, dst);
    done += e - s + 1;
    const fps = done / ((Date.now() - t0) / 1000);
    console.log(`${dst.split('/').pop()}  ${done}/${total} frames  ~${fps.toFixed(1)} fps`);
  }
  console.log(`ranges -> ${out}  (${((Date.now() - t0) / 60000).toFixed(1)} min)`);
} else if (mode === 'thumbs') {
  fs.mkdirSync(out, { recursive: true });
  for (const id of ['ThumbA', 'ThumbB', 'ThumbC']) {
    const comp = await selectComposition({ serveUrl, id, browserExecutable, chromiumOptions });
    await renderStill({ serveUrl, composition: comp, output: path.join(out, `thumbnail_${id.slice(-1)}.png`), imageFormat: 'png', browserExecutable, chromiumOptions });
  }
  console.log(`thumbs -> ${out}`);
} else {
  console.error('mode: stills | video | thumbs');
  process.exit(1);
}
