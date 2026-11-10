#!/usr/bin/env node
// Deterministic headless render of sim.html → build/video.mp4, events.json → audio → final/final.mp4
//
//   node render.mjs                 full pipeline (frames, audio, mux, QA)
//   node render.mjs --frames 0-299  render a sub-range only (debug)
//   node render.mjs --skip-video    reuse build/video.mp4, redo audio + mux + QA
//   WORKERS=4 node render.mjs       parallel segment workers (default: cores-1, max 4)
//
// Each worker loads its own page, fast-forwards the (cheap) physics to its segment start
// and renders its frames; segments are encoded separately and concatenated losslessly.
// The simulation is a pure function of frame number, so the result is identical to a
// single sequential render.
import { createRequire } from 'module';
import { spawn, spawnSync, execSync } from 'child_process';
import { mkdirSync, writeFileSync, existsSync, rmSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';
import os from 'os';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const HERE = dirname(fileURLToPath(import.meta.url));
const BUILD = join(HERE, 'build'), FINAL = join(HERE, 'final');
mkdirSync(BUILD, { recursive: true }); mkdirSync(FINAL, { recursive: true });

const args = process.argv.slice(2);
const has = f => args.includes(f);
const range = (() => { const i = args.indexOf('--frames'); if (i < 0) return null; const [a, b] = args[i + 1].split('-').map(Number); return [a, b]; })();
const PY = process.env.PYTHON || 'python3';

// ---------------------------------------------------------------- GPU detection
function hasNvidia() { try { execSync('nvidia-smi -L', { stdio: 'ignore' }); return true; } catch { return false; } }
const GPU = process.env.GPU === '0' ? false : (hasNvidia() || existsSync('/dev/dri/renderD128'));
const chromeArgs = GPU
  ? ['--enable-gpu', '--ignore-gpu-blocklist', '--enable-gpu-rasterization', '--use-angle=vulkan', '--enable-features=Vulkan']
  : ['--disable-gpu-vsync'];
const encoder = hasNvidia()
  ? ['-c:v', 'h264_nvenc', '-preset', 'p7', '-tune', 'hq', '-rc', 'vbr', '-cq', '17', '-b:v', '0']
  : ['-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-tune', 'animation'];
const videoOpts = [...encoder, '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-color_range', 'tv', '-colorspace', 'bt709',
  '-color_primaries', 'bt709', '-color_trc', 'bt709', '-r', '60', '-g', '120'];

async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: 540, height: 960 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => { console.error('page error:', e.message); process.exit(1); });
  await page.goto('file://' + join(HERE, 'sim.html') + '?render');
  await page.evaluate(() => window.ready());
  return page;
}

async function renderSegment(browser, id, a, b, progress) {
  const page = await openPage(browser);
  const out = join(BUILD, `seg_${String(id).padStart(2, '0')}.mp4`);
  const ff = spawn('ffmpeg', ['-y', '-hide_banner', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', '60', '-c:v', 'mjpeg',
    '-i', '-', '-vf', 'scale=in_range=pc:out_range=tv,format=yuv420p', ...videoOpts, out], { stdio: ['pipe', 'inherit', 'inherit'] });
  const ffDone = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));
  if (a > 0) await page.evaluate(n => window.seekSim(n - 1), a);       // fast-forward physics only
  for (let n = a; n <= b; n++) {
    const b64 = await page.evaluate(n => {
      window.renderFrame(n);
      return document.getElementById('c').toDataURL('image/jpeg', 0.96).slice(23);
    }, n);
    const buf = Buffer.from(b64, 'base64');
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    progress(n);
  }
  ff.stdin.end(); await ffDone; await page.close();
  return out;
}

async function renderVideo() {
  const browser = await chromium.launch({ args: chromeArgs });
  const probe = await openPage(browser);
  const info = await probe.evaluate(() => {
    const gl = document.createElement('canvas').getContext('webgl');
    const ext = gl && gl.getExtension('WEBGL_debug_renderer_info');
    return { total: window.TOTAL_FRAMES, gpu: ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : 'n/a' };
  });
  await probe.close();
  const [a, b] = range || [0, info.total - 1];
  const workers = Math.max(1, Math.min(+process.env.WORKERS || Math.min(4, os.cpus().length - 1), Math.ceil((b - a + 1) / 120)));
  console.log(`GPU: ${GPU ? 'requested' : 'none detected (software raster)'} · renderer: ${info.gpu}`);
  console.log(`encoder: ${encoder[1]} · frames ${a}-${b} · workers ${workers}`);
  const per = Math.ceil((b - a + 1) / workers), segs = [];
  let done = 0; const t0 = Date.now(), total = b - a + 1;
  const progress = n => {
    done++;
    if (done % 10 === 0 || done === total) {
      const el = (Date.now() - t0) / 1000, fps = done / el;
      process.stdout.write(`\rframe ${String(done).padStart(4)}/${total}  (last ${n})  ${fps.toFixed(1)} fps  ETA ${((total - done) / fps).toFixed(0)}s   `);
    }
  };
  for (let w = 0; w < workers; w++) {
    const sa = a + w * per, sb = Math.min(b, sa + per - 1);
    if (sa <= sb) segs.push(renderSegment(browser, w, sa, sb, progress));
  }
  const files = await Promise.all(segs);
  process.stdout.write('\n');
  // events (hit log) from a full sequential sim pass
  const page = await openPage(browser);
  const events = await page.evaluate(n => { window.seekSim(n); return window.getEvents(); }, info.total - 1);
  writeFileSync(join(BUILD, 'events.json'), JSON.stringify(events));
  await browser.close();
  const list = join(BUILD, 'segments.txt');
  writeFileSync(list, files.map(f => `file '${f}'`).join('\n'));
  run('ffmpeg', ['-y', '-hide_banner', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', join(BUILD, 'video.mp4')]);
  files.forEach(f => rmSync(f));
  console.log(`video: ${join(BUILD, 'video.mp4')}  (${((Date.now() - t0) / 1000).toFixed(0)}s)`);
}

function run(cmd, a) {
  const r = spawnSync(cmd, a, { stdio: 'inherit' });
  if (r.status !== 0) { console.error(`${cmd} failed`); process.exit(1); }
}

if (!has('--skip-video')) await renderVideo();
if (range) process.exit(0);
run(PY, [join(HERE, 'audio.py'), join(BUILD, 'events.json'), join(BUILD, 'audio.wav')]);
run('ffmpeg', ['-y', '-hide_banner', '-loglevel', 'error', '-i', join(BUILD, 'video.mp4'), '-i', join(BUILD, 'audio.wav'),
  '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-t', '30',
  '-movflags', '+faststart', join(FINAL, 'final.mp4')]);
console.log('final:', join(FINAL, 'final.mp4'));
if (!has('--no-qa')) run(PY, [join(HERE, 'qa.py')]);
