/**
 * render.js — deterministic frame renderer + parallel encoder.
 *
 *   renderFrame(frameIndex, { scale }) -> node-canvas Canvas   (pure function of frameIndex)
 *
 * Per-frame compositing order:
 *   1. scene module draws into the scene layer (1080x1920 logical coords)
 *   2. date card (typewriter) on the scene layer
 *   3. scene layer -> frame with gate weave (±1.5 px) + camera shake
 *   4. transitions (8-frame dip-to-black / film-burn flash at scene boundaries)
 *   5. film FX: flicker, vignette, grain, dust, scratches
 *   6. burned-in word-by-word subtitles
 *   (no final fade: the ending dissolves back into frame 0 so the video loops seamlessly)
 *
 * CLI (used by scripts/build.sh):
 *   node src/render.js --out build/video.mp4 [--scale 0.5] [--workers 4]
 *   node src/render.js --segment <from> <to> --file <seg.mp4> [--scale s]   (internal worker)
 */
'use strict';

const fs = require('fs');
const path = require('path');
const { spawn, fork } = require('child_process');
const { createCanvas } = require('canvas');

const ROOT = path.resolve(__dirname, '..');
const { registerFonts } = require('./lib/fonts');
const filmfx = require('./lib/filmfx');
const { drawDateCard, buildSubtitles, drawSubtitles } = require('./lib/text');
const { clamp } = require('./lib/easing');
const { DATE_TYPE_INTERVAL } = require('./timeline');

registerFonts();

const TL_PATH = path.join(ROOT, 'build', 'timeline.json');
if (!fs.existsSync(TL_PATH)) throw new Error('build/timeline.json missing — run `npm run build` (or audio/tts.py + node src/timeline.js --resolve)');
const TL = JSON.parse(fs.readFileSync(TL_PATH, 'utf8'));
const W = TL.width, H = TL.height, FPS = TL.fps;
const SUBS = buildSubtitles(TL);
const MODULES = Object.fromEntries(TL.scenes.map((s) => [s.module, require(`./scenes/${s.module}`)]));

const normWord = (w) => w.toLowerCase().replace(/[^a-z0-9']/g, '');

/** Build the per-frame state object handed to a scene module. */
function sceneState(sc, frame, scale) {
  const time = frame / FPS;
  const t = time - sc.startSec;
  const dur = sc.endSec - sc.startSec;
  const words = sc.narration.words;
  const cues = TL.cues.filter((c) => c.scene === sc.id);
  return {
    frame, time, t, dur, p: clamp(t / dur), sc, tl: TL, C: TL.colors, scale,
    /** local time (s) a narration word starts being spoken */
    w(word, nth = 0) {
      const hits = words.filter((x) => normWord(x.text) === normWord(word));
      if (!hits[nth]) throw new Error(`word ${word} not in scene ${sc.id}`);
      return hits[nth].start - sc.startSec;
    },
    /** local time (s) of the nth audio cue of a given sfx in this scene */
    cue(sfx, nth = 0) {
      const hits = cues.filter((c) => c.sfx === sfx);
      if (!hits[nth]) throw new Error(`cue ${sfx}#${nth} not in scene ${sc.id}`);
      return hits[nth].time - sc.startSec;
    },
    cues: (sfx) => cues.filter((c) => c.sfx === sfx).map((c) => c.time - sc.startSec),
    narrStart: sc.narration.startSec - sc.startSec,
    narrEnd: sc.narration.endSec - sc.startSec,
    /** offscreen layer with the same device scale as the frame */
    layer: (id) => getLayer(`${sc.id}:${id}`, scale),
  };
}

const layers = new Map();
function getLayer(id, scale) {
  const key = `${id}@${scale}`;
  let L = layers.get(key);
  if (!L) {
    const canvas = createCanvas(Math.round(W * scale), Math.round(H * scale));
    L = { canvas, ctx: canvas.getContext('2d') };
    layers.set(key, L);
  }
  L.ctx.setTransform(1, 0, 0, 1, 0, 0);
  L.ctx.clearRect(0, 0, L.canvas.width, L.canvas.height);
  L.ctx.setTransform(scale, 0, 0, scale, 0, 0);
  L.ctx.globalAlpha = 1;
  L.ctx.globalCompositeOperation = 'source-over';
  return L;
}

function sceneAt(frame) {
  return TL.scenes.find((s) => frame >= s.startFrame && frame < s.endFrame) || TL.scenes[TL.scenes.length - 1];
}

let frameCanvas = null;
/**
 * Render one frame. Pure: the output depends only on frameIndex (and scale).
 */
function renderFrame(frame, { scale = 1 } = {}) {
  if (!frameCanvas || frameCanvas.width !== Math.round(W * scale)) frameCanvas = createCanvas(Math.round(W * scale), Math.round(H * scale));
  const ctx = frameCanvas.getContext('2d');
  const sc = sceneAt(frame);
  const s = sceneState(sc, frame, scale);
  if (global.__QC__) global.__QC__.cur = { scene: sc.id, frame };

  // 1-2. scene + date card
  const L = getLayer('scene', scale);
  L.ctx.fillStyle = TL.colors.black;
  L.ctx.fillRect(0, 0, W, H);
  const fx = MODULES[sc.module].render(L.ctx, s) || {};
  if (sc.dateCard) drawDateCard(L.ctx, sc.dateCard, s.time, sc.endSec, { interval: DATE_TYPE_INTERVAL, ...(fx.dateCard || {}) });

  // 3. weave + shake
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.fillStyle = '#000';
  ctx.fillRect(0, 0, frameCanvas.width, frameCanvas.height);
  // weave is made periodic: over the last 15 frames it blends into the drift just before frame 0,
  // so the loop cut (last frame -> frame 0) moves no more than an ordinary frame step
  const kL = clamp((frame - (TL.totalFrames - 16)) / 15);
  const wa = filmfx.weave(frame), wb = filmfx.weave(frame - TL.totalFrames);
  const wx = wa[0] * (1 - kL) + wb[0] * kL, wy = wa[1] * (1 - kL) + wb[1] * kL;
  let sx = 0, sy = 0;
  if (fx.shake) {
    sx = fx.shake * Math.sin(frame * 2.7 + 1.3);
    sy = fx.shake * Math.cos(frame * 3.3 + 0.4);
  }
  const pad = 4 * scale;
  ctx.drawImage(L.canvas, (wx + sx) * scale - pad, (wy + sy) * scale - pad, W * scale + pad * 2, H * scale + pad * 2);
  ctx.setTransform(scale, 0, 0, scale, 0, 0);

  // 4. transitions (centered on each scene boundary, TRANSITION_FRAMES long)
  drawTransitions(ctx, frame);

  // 5. film FX
  filmfx.apply(ctx, frame, { grain: fx.grain ?? 1, dust: fx.dust ?? 1, vignette: fx.vignette ?? 1 });

  // 6. subtitles
  drawSubtitles(ctx, SUBS, s.time);

  return frameCanvas;
}

function drawTransitions(ctx, frame) {
  const half = TL.transitionFrames / 2;
  for (const sc of TL.scenes) {
    if (!sc.transitionIn) continue;
    const d = frame - (sc.startFrame - 0.5); // boundary sits between frames start-1 and start
    if (Math.abs(d) > half) continue;
    const a = 1 - Math.abs(d) / half; // triangle: 0 -> 1 -> 0 over 8 frames
    if (sc.transitionIn === 'dip') {
      ctx.fillStyle = `rgba(0,0,0,${clamp(a * 1.25)})`;
      ctx.fillRect(0, 0, W, H);
    } else { // film burn: warm over-exposure blooming from an edge
      ctx.save();
      ctx.globalCompositeOperation = 'screen';
      const g = ctx.createRadialGradient(W * 0.78, H * 0.3, 0, W * 0.78, H * 0.3, H * 0.9);
      g.addColorStop(0, `rgba(255,240,215,${a})`);
      g.addColorStop(0.35, `rgba(240,170,90,${0.85 * a})`);
      g.addColorStop(0.75, `rgba(150,60,20,${0.6 * a})`);
      g.addColorStop(1, `rgba(40,10,0,${0.3 * a})`);
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, W, H);
      ctx.restore();
      if (a > 0.7) { ctx.fillStyle = `rgba(255,236,200,${(a - 0.7) * 2})`; ctx.fillRect(0, 0, W, H); }
    }
  }
}

/** Raw BGRA bytes of a rendered frame (node-canvas native ARGB32, little-endian). */
function frameRaw(frame, opts) {
  return renderFrame(frame, opts).toBuffer('raw');
}

module.exports = { renderFrame, frameRaw, TL, SUBS };

// ---- CLI -------------------------------------------------------------------------------------
function arg(name, def) {
  const i = process.argv.indexOf(name);
  return i >= 0 ? process.argv[i + 1] : def;
}

function x264Args(w, h, file) {
  return ['-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', `${w}x${h}`, '-r', String(FPS), '-i', '-',
    '-vf', 'scale=out_color_matrix=bt709:out_range=tv,format=yuv420p',
    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p',
    '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv', file];
}

async function runSegment(from, to, file, scale) {
  const w = Math.round(W * scale), h = Math.round(H * scale);
  const ff = spawn('ffmpeg', x264Args(w, h, file), { stdio: ['pipe', 'inherit', 'inherit'] });
  const done = new Promise((res, rej) => ff.on('close', (c) => (c === 0 ? res() : rej(new Error(`ffmpeg exit ${c}`)))));
  for (let f = from; f < to; f++) {
    const buf = frameRaw(f, { scale });
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
    if (process.send && (f - from) % 15 === 0) process.send({ progress: f - from });
  }
  ff.stdin.end();
  await done;
}

async function main() {
  if (process.argv.includes('--segment')) {
    const i = process.argv.indexOf('--segment');
    await runSegment(+process.argv[i + 1], +process.argv[i + 2], arg('--file'), +arg('--scale', 1));
    return;
  }
  const out = path.resolve(arg('--out', path.join(ROOT, 'build', 'video.mp4')));
  const scale = +arg('--scale', 1);
  const workers = +arg('--workers', Math.max(1, require('os').cpus().length));
  const N = TL.totalFrames;
  const segDir = path.join(ROOT, 'build', 'segments');
  fs.mkdirSync(segDir, { recursive: true });
  const t0 = Date.now();
  const per = Math.ceil(N / workers);
  const jobs = [];
  const progress = new Array(workers).fill(0);
  const files = [];
  for (let k = 0; k < workers; k++) {
    const a = k * per, b = Math.min(N, a + per);
    if (a >= b) break;
    const file = path.join(segDir, `seg_${scale}_${k}.mp4`);
    files.push(file);
    jobs.push(new Promise((res, rej) => {
      const cp = fork(__filename, ['--segment', a, b, '--file', file, '--scale', scale]);
      cp.on('message', (m) => {
        progress[k] = m.progress;
        const tot = progress.reduce((x, y) => x + y, 0);
        process.stdout.write(`\r  rendering ${tot}/${N} frames  (${((Date.now() - t0) / 1000).toFixed(0)} s)   `);
      });
      cp.on('exit', (c) => (c === 0 ? res() : rej(new Error(`worker ${k} failed`))));
    }));
  }
  await Promise.all(jobs);
  process.stdout.write('\n');
  const list = path.join(segDir, `list_${scale}.txt`);
  fs.writeFileSync(list, files.map((f) => `file '${f}'`).join('\n'));
  await new Promise((res, rej) => {
    const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', out], { stdio: 'inherit' });
    ff.on('close', (c) => (c === 0 ? res() : rej(new Error('concat failed'))));
  });
  console.log(`  video-only render -> ${path.relative(ROOT, out)} in ${((Date.now() - t0) / 1000).toFixed(1)} s`);
}

if (require.main === module) {
  main().catch((e) => { console.error(e); process.exit(1); });
}
