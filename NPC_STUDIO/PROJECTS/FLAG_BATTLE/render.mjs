#!/usr/bin/env node
// Country Flag Battle Royale → final/final.mp4
//
//   node render.mjs --winner Japan        search seeds until Japan wins a "good fight", render it
//   node render.mjs --seed 1234           render a specific seed
//   node render.mjs --winner Japan --search-only     just print the seed + fight stats
//   node render.mjs --skip-video          reuse build/video.mp4 (+events.json), redo audio, mux, QA
//   WORKERS=3 node render.mjs ...         parallel render workers (default: cores-1, max 4)
//
// A "good fight" (see verdict() in battle.html): ends on a collision, 33–47 s of combat, first
// elimination after the hook, both duellists ≤ 60 HP when it becomes 1v1, winner finishes ≤ 35 HP,
// a mix of escapes and knock-outs.
import { createRequire } from 'module';
import { spawn, spawnSync, execSync } from 'child_process';
import { mkdirSync, writeFileSync, readFileSync, existsSync, rmSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';
import os from 'os';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const HERE = dirname(fileURLToPath(import.meta.url));
const BUILD = join(HERE, 'build'), FINAL = join(HERE, 'final');
mkdirSync(BUILD, { recursive: true }); mkdirSync(FINAL, { recursive: true });
const args = process.argv.slice(2);
const opt = k => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : undefined; };
const has = k => args.includes(k);
const PY = process.env.PYTHON || 'python3';
const run = (cmd, a) => { const r = spawnSync(cmd, a, { stdio: 'inherit' }); if (r.status !== 0) { console.error(`${cmd} failed`); process.exit(1); } };

// ---------------------------------------------------------------- GPU / encoder
const nvidia = (() => { try { execSync('nvidia-smi -L', { stdio: 'ignore' }); return true; } catch { return false; } })();
const GPU = process.env.GPU === '0' ? false : (nvidia || existsSync('/dev/dri/renderD128'));
const chromeArgs = GPU ? ['--enable-gpu', '--ignore-gpu-blocklist', '--enable-gpu-rasterization', '--use-angle=vulkan'] : [];
const encoder = nvidia ? ['-c:v', 'h264_nvenc', '-preset', 'p7', '-rc', 'vbr', '-cq', '18', '-b:v', '0']
                       : ['-c:v', 'libx264', '-preset', 'slow', '-crf', '18'];
const videoOpts = [...encoder, '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-color_range', 'tv', '-colorspace', 'bt709',
  '-color_primaries', 'bt709', '-color_trc', 'bt709', '-r', '60', '-g', '120'];

async function openPage(browser, seed) {
  const page = await browser.newPage({ viewport: { width: 540, height: 960 } });
  page.on('pageerror', e => { console.error('page error:', e.message); process.exit(1); });
  await page.goto('file://' + join(HERE, 'battle.html') + '?render');
  const info = seed === undefined ? null : await page.evaluate(s => window.ready(s), seed);
  return { page, info };
}

async function main() {
  run('node', [join(HERE, 'embed_flags.mjs')]);
  const browser = await chromium.launch({ args: chromeArgs });
  // ---- pick the seed
  let seed = opt('--seed') !== undefined ? +opt('--seed') : undefined;
  if (seed === undefined) {
    const winner = opt('--winner');
    if (!winner) { console.error('pass --winner <Country> or --seed <n>'); process.exit(2); }
    const { page } = await openPage(browser);
    const t = Date.now();
    const r = await page.evaluate(w => window.searchSeed(w, 1, 20000), winner);
    await page.close();
    if (r.error) { console.error(r.error); process.exit(3); }
    console.log(`seed search: ${winner} wins a good fight with seed ${r.seed} (${r.tried} seeds simulated, ${r.wins} ${winner} wins, ${Date.now() - t} ms)`);
    seed = r.seed;
  }
  const { page: p0, info } = await openPage(browser, seed);
  await p0.close();
  console.log(`seed ${seed}: ${info.metrics.winner} wins · ${info.seconds.toFixed(2)} s video · ` +
    `${info.metrics.kills} knock-outs, ${info.metrics.escapes} escapes · duel ${JSON.stringify(info.metrics.duelHP)} → winner ends on ${info.metrics.winnerHP} HP`);
  if (!info.verdict.ok) console.warn('warning: not a "good fight":', info.verdict.why.join('; '));
  if (has('--search-only')) { await browser.close(); return; }

  if (!has('--skip-video')) {
    const total = info.totalFrames;
    const workers = Math.max(1, Math.min(+process.env.WORKERS || Math.min(4, os.cpus().length - 1), 8));
    console.log(`GPU: ${GPU ? 'requested' : 'none detected (software raster)'} · encoder ${encoder[1]} · ${total} frames · ${workers} workers`);
    const per = Math.ceil(total / workers), t0 = Date.now(); let done = 0;
    const segment = async (w, a, b) => {
      const { page } = await openPage(browser, seed);
      const out = join(BUILD, `seg_${w}.mp4`);
      const ff = spawn('ffmpeg', ['-y', '-hide_banner', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', '60', '-c:v', 'mjpeg', '-i', '-',
        '-vf', 'scale=in_range=pc:out_range=tv,format=yuv420p', ...videoOpts, out], { stdio: ['pipe', 'inherit', 'inherit'] });
      const fin = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg ' + c))));
      for (let n = a; n <= b; n++) {
        const b64 = await page.evaluate(n => { window.renderFrame(n); return document.getElementById('c').toDataURL('image/jpeg', 0.95).slice(23); }, n);
        if (!ff.stdin.write(Buffer.from(b64, 'base64'))) await new Promise(r => ff.stdin.once('drain', r));
        if (++done % 15 === 0 || done === total) {
          const fps = done / ((Date.now() - t0) / 1000);
          process.stdout.write(`\rframe ${String(done).padStart(4)}/${total}  ${(100 * done / total).toFixed(0)}%  ${fps.toFixed(1)} fps  ETA ${((total - done) / fps).toFixed(0)}s   `);
        }
      }
      ff.stdin.end(); await fin; await page.close(); return out;
    };
    const jobs = [];
    for (let w = 0; w < workers; w++) { const a = w * per, b = Math.min(total - 1, a + per - 1); if (a <= b) jobs.push(segment(w, a, b)); }
    const files = await Promise.all(jobs);
    process.stdout.write('\n');
    writeFileSync(join(BUILD, 'segments.txt'), files.map(f => `file '${f}'`).join('\n'));
    run('ffmpeg', ['-y', '-hide_banner', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', join(BUILD, 'segments.txt'), '-c', 'copy', join(BUILD, 'video.mp4')]);
    files.forEach(f => rmSync(f));
    console.log(`video rendered in ${((Date.now() - t0) / 1000).toFixed(0)} s`);
    const { page } = await openPage(browser, seed);
    writeFileSync(join(BUILD, 'events.json'), JSON.stringify(await page.evaluate(() => window.getEvents())));
  }
  await browser.close();
  const ev = JSON.parse(readFileSync(join(BUILD, 'events.json'), 'utf8'));
  run(PY, [join(HERE, 'audio.py'), join(BUILD, 'events.json'), join(BUILD, 'audio.wav')]);
  run('ffmpeg', ['-y', '-hide_banner', '-loglevel', 'error', '-i', join(BUILD, 'video.mp4'), '-i', join(BUILD, 'audio.wav'),
    '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-t', String(ev.totalFrames / 60),
    '-movflags', '+faststart', join(FINAL, 'final.mp4')]);
  console.log('final:', join(FINAL, 'final.mp4'));
  if (!has('--no-qa')) run(PY, [join(HERE, 'qa.py')]);
}
main();
