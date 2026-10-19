// NPC render driver — bundles the Remotion project and renders stills or video.
//
//   node pipeline/render.mjs <project-dir> stills  [--frames 0,120,...] [--quality 0.5]
//   node pipeline/render.mjs <project-dir> preview            (540×960, fast)
//   node pipeline/render.mjs <project-dir> final              (1080×1920, 60 fps)
//
// Video is rendered silent and muxed with audio/mix.wav by ffmpeg so the
// soundtrack is bit-exact with what the sound engine produced.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { bundle } from '@remotion/bundler';
import { openBrowser, renderMedia, renderStill, selectComposition } from '@remotion/renderer';

const here = path.dirname(fileURLToPath(import.meta.url));
const engineDir = path.resolve(here, '..');
const studio = path.resolve(engineDir, '..');
const [, , projectArg, mode = 'stills', ...rest] = process.argv;
const project = path.resolve(projectArg);
const name = path.basename(project);
const opt = (k, d) => {
  const i = rest.indexOf(`--${k}`);
  return i >= 0 ? rest[i + 1] : d;
};

const BROWSER = process.env.NPC_BROWSER ?? '/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell';
const chromiumOptions = { gl: process.env.NPC_GL ?? 'swangle', enableMultiProcessOnLinux: true };

// 1. Stage project data + public assets.
const dataDir = path.join(engineDir, 'src', 'data');
fs.mkdirSync(dataDir, { recursive: true });
fs.copyFileSync(path.join(project, 'source', 'timeline.json'), path.join(dataDir, 'timeline.json'));
fs.copyFileSync(path.join(project, 'audio', 'envelope.json'), path.join(dataDir, 'envelope.json'));

const pub = path.join(engineDir, 'build', 'public');
fs.rmSync(pub, { recursive: true, force: true });
fs.mkdirSync(path.join(pub, 'fonts'), { recursive: true });
fs.mkdirSync(path.join(pub, 'code'), { recursive: true });
for (const f of fs.readdirSync(path.join(studio, 'BRAND', 'fonts'))) {
  if (/\.(otf|ttf|json)$/.test(f)) fs.copyFileSync(path.join(studio, 'BRAND', 'fonts', f), path.join(pub, 'fonts', f));
}
// The code world in Scene 03 is textured with this engine's real source.
const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) =>
  e.isDirectory() ? walk(path.join(d, e.name)) : /\.(ts|tsx|glsl)$/.test(e.name) ? [path.join(d, e.name)] : []);
const code = walk(path.join(engineDir, 'src'))
  .sort()
  .map((f) => `// ${path.relative(engineDir, f)}\n${fs.readFileSync(f, 'utf8')}`)
  .join('\n');
fs.writeFileSync(path.join(pub, 'code', 'engine_source.txt'), code);

// 2. Bundle.
const t0 = Date.now();
const serveUrl = await bundle({ entryPoint: path.join(engineDir, 'src', 'index.ts'), publicDir: pub });
const quality = Number(opt('quality', mode === 'final' ? 1 : 0.5));
const inputProps = { quality };
const comp = await selectComposition({ serveUrl, id: 'NPC-NoEditorJustCode', inputProps, browserExecutable: BROWSER, chromiumOptions });
console.log(`bundled in ${((Date.now() - t0) / 1000).toFixed(1)}s — ${comp.width}x${comp.height} ${comp.fps}fps ${comp.durationInFrames} frames`);

const concurrency = Number(opt('concurrency', Math.max(1, os.cpus().length)));
const previews = path.join(project, 'previews');
const final = path.join(project, 'final');

if (mode === 'stills') {
  const frames = (opt('frames', '') || '')
    .split(',')
    .filter(Boolean)
    .map(Number);
  const list = frames.length ? frames : Array.from({ length: 16 }, (_, i) => Math.round((i / 15) * (comp.durationInFrames - 1)));
  const dir = path.join(previews, 'frames');
  fs.mkdirSync(dir, { recursive: true });
  const browser = await openBrowser('chrome', { browserExecutable: BROWSER, chromiumOptions });
  for (const f of list) {
    const out = path.join(dir, `f${String(f).padStart(4, '0')}.jpg`);
    const s = Date.now();
    await renderStill({ serveUrl, composition: comp, frame: f, output: out, imageFormat: 'jpeg', jpegQuality: 88, scale: quality, inputProps, puppeteerInstance: browser, chromiumOptions });
    console.log(`still ${f} -> ${path.relative(studio, out)} (${Date.now() - s} ms)`);
  }
  await browser.close({ silent: true });
  // Contact sheet for quick visual QC.
  const sheet = path.join(previews, 'contact_sheet.jpg');
  const inputs = list.map((f) => path.join(dir, `f${String(f).padStart(4, '0')}.jpg`));
  const cols = Math.min(8, inputs.length);
  const rows = Math.ceil(inputs.length / cols);
  execFileSync('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', ...inputs.flatMap((i) => ['-i', i]),
    '-filter_complex', inputs.map((_, i) => `[${i}:v]scale=270:480[v${i}]`).join(';') + ';' +
      inputs.map((_, i) => `[v${i}]`).join('') + `xstack=inputs=${inputs.length}:layout=` +
      inputs.map((_, i) => `${(i % cols) * 274}_${Math.floor(i / cols) * 484}`).join('|') + `:fill=0x202020`,
    '-frames:v', '1', sheet]);
  console.log(`contact sheet -> ${path.relative(studio, sheet)}`);
} else {
  const isFinal = mode === 'final';
  const silent = path.join(isFinal ? final : previews, `.${name}_${mode}_video.mp4`);
  // A cut without NPC_VOICE_V1 narration is never labelled as the final video.
  const voiced = JSON.parse(fs.readFileSync(path.join(project, 'source', 'timeline.json'), 'utf8')).voiced;
  const out = isFinal ? path.join(final, `${name}_FINAL${voiced ? '' : '_PREVOICE'}.mp4`) : path.join(previews, `${name}_PREVIEW.mp4`);
  fs.mkdirSync(path.dirname(out), { recursive: true });
  let last = 0;
  const s = Date.now();
  await renderMedia({
    serveUrl, composition: comp, codec: 'h264', outputLocation: silent, inputProps, muted: true,
    scale: isFinal ? 1 : quality, crf: 8, x264Preset: 'veryfast', pixelFormat: 'yuv420p', // near-lossless intermediate
    concurrency, browserExecutable: BROWSER, chromiumOptions, timeoutInMilliseconds: 240000,
    frameRange: opt('range', null)?.split('-').map(Number) ?? null,
    onProgress: ({ renderedFrames }) => {
      if (renderedFrames - last >= 60) {
        last = renderedFrames;
        const el = (Date.now() - s) / 1000;
        console.log(`  ${renderedFrames}/${comp.durationInFrames} frames  ${(renderedFrames / el).toFixed(2)} fps`);
      }
    },
  });
  execFileSync('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', '-i', silent, '-i', path.join(project, 'audio', 'mix.wav'),
    // Final encode: broadcast-range yuv420p with BT.709 tags (the intermediate is full-range).
    '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'libx264', '-crf', isFinal ? '14' : '20', '-preset', isFinal ? 'slow' : 'medium',
    '-vf', 'scale=in_range=full:out_range=tv,format=yuv420p', '-pix_fmt', 'yuv420p',
    '-color_range', 'tv', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-c:a', 'aac', '-b:a', '320k', '-ar', '48000', '-ac', '2',
    '-movflags', '+faststart', '-shortest', out]);
  fs.rmSync(silent);
  console.log(`rendered ${path.relative(studio, out)} in ${((Date.now() - s) / 1000).toFixed(0)}s`);
}
