// Flat 2D explainer render driver (headless Chromium via Playwright, no WebGL needed).
//
//   node RENDER_ENGINE/flat2d/render.mjs <project-dir> stills [--times 1.2,5,9.5]
//   node RENDER_ENGINE/flat2d/render.mjs <project-dir> video  [--workers 4] [--scale 1]
//
// Each worker opens flat2d/index.html, calls setup(timeline, geo) and then
// renderAt(frame / fps) per frame, piping screenshots into its own ffmpeg
// segment. Segments are concatenated and muxed with audio/mix.wav.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn, execFileSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const here = path.dirname(fileURLToPath(import.meta.url));
const [, , projectArg, mode = 'stills', ...rest] = process.argv;
const project = path.resolve(projectArg);
const name = path.basename(project);
const opt = (k, d) => { const i = rest.indexOf(`--${k}`); return i >= 0 ? rest[i + 1] : d; };

const tl = JSON.parse(fs.readFileSync(path.join(project, 'source', 'timeline.json'), 'utf8'));
const geo = JSON.parse(fs.readFileSync(path.join(here, 'geo.json'), 'utf8'));
const scale = Number(opt('scale', 1));
const url = pathToFileURL(path.join(here, 'index.html')).href;

async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: tl.width, height: tl.height }, deviceScaleFactor: scale });
  page.on('pageerror', (e) => { console.error('page error:', e.message); process.exit(1); });
  await page.goto(url);
  await page.evaluate(([a, b]) => window.setup(a, b), [tl, geo]);
  return page;
}
const shot = async (page, t) => {
  await page.evaluate((x) => window.renderAt(x), t);
  return page.screenshot({ type: 'png', clip: { x: 0, y: 0, width: tl.width, height: tl.height } });
};

const browser = await chromium.launch({ args: ['--font-render-hinting=none'] });
if (mode === 'stills') {
  const times = (opt('times', '') || '').split(',').filter(Boolean).map(Number);
  const list = times.length ? times : tl.scenes.map((s) => +(s.start + Math.min(2.5, (s.end - s.start) * 0.7)).toFixed(2));
  const dir = path.join(project, 'previews', 'frames');
  fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(dir, { recursive: true });
  const page = await openPage(browser);
  const files = [];
  for (const t of list) {
    const f = path.join(dir, `t${t.toFixed(2).padStart(6, '0')}.png`);
    fs.writeFileSync(f, await shot(page, t));
    files.push(f);
  }
  const cols = Math.min(6, files.length), rows = Math.ceil(files.length / cols);
  execFileSync('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', ...files.flatMap((f) => ['-i', f]), '-filter_complex',
    files.map((_, i) => `[${i}:v]scale=270:480[v${i}]`).join(';') + ';' + files.map((_, i) => `[v${i}]`).join('') +
    `xstack=inputs=${files.length}:layout=` + files.map((_, i) => `${(i % cols) * 274}_${Math.floor(i / cols) * 484}`).join('|') + ':fill=0x202020',
    '-frames:v', '1', path.join(project, 'previews', 'contact_sheet.jpg')]);
  console.log(`${files.length} stills -> previews/frames, contact sheet -> previews/contact_sheet.jpg`);
} else {
  const N = tl.durationInFrames, fps = tl.fps;
  const workers = Number(opt('workers', Math.max(1, os.cpus().length)));
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'npc2d-'));
  const per = Math.ceil(N / workers);
  const t0 = Date.now();
  let done = 0;
  await Promise.all(Array.from({ length: workers }, async (_, w) => {
    const a = w * per, b = Math.min(N, a + per);
    if (a >= b) return;
    const page = await openPage(browser);
    const seg = path.join(tmp, `seg${w}.mp4`);
    const ff = spawn('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'png', '-i', '-',
      '-c:v', 'libx264', '-crf', '10', '-preset', 'veryfast', '-pix_fmt', 'yuv444p', seg], { stdio: ['pipe', 'inherit', 'inherit'] });
    const closed = new Promise((r) => ff.on('close', r));
    for (let f = a; f < b; f++) {
      const buf = await shot(page, f / fps);
      if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
      if (++done % 150 === 0) console.log(`  ${done}/${N} frames  ${(done / ((Date.now() - t0) / 1000)).toFixed(1)} fps`);
    }
    ff.stdin.end();
    await closed;
    await page.close();
  }));
  const list = path.join(tmp, 'list.txt');
  fs.writeFileSync(list, Array.from({ length: workers }, (_, w) => path.join(tmp, `seg${w}.mp4`)).filter(fs.existsSync).map((f) => `file '${f}'`).join('\n'));
  const out = path.join(project, 'final', `${name}.mp4`);
  fs.mkdirSync(path.dirname(out), { recursive: true });
  execFileSync('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', list, '-i', path.join(project, 'audio', 'mix.wav'),
    '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'libx264', '-crf', '18', '-preset', 'slow', '-pix_fmt', 'yuv420p',
    '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-ac', '2',
    '-movflags', '+faststart', '-shortest', out]);
  fs.rmSync(tmp, { recursive: true, force: true });
  console.log(`rendered ${path.relative(process.cwd(), out)} (${N} frames) in ${((Date.now() - t0) / 1000).toFixed(0)}s`);
}
await browser.close();
