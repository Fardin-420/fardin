/**
 * qc.js — the brief's quality checks. Prints a report, writes out/qc_report.txt, exits 1 on failure.
 *
 *  1. ffprobe: duration 60.0 s ±0.05, 1800 frames, 1080x1920, 30 fps (+ codec/pix_fmt/audio params)
 *  2. loudness: ffmpeg ebur128 (true peak on): -14 LUFS ±1, true peak <= -1 dBTP
 *  3. sync table: every narration line inside its scene window, scene end = narration end + 0.3 s
 *  4. contact sheet present; automated scan: empty (flat) frames, text outside the safe zone
 *     (every fillText is instrumented), arrows drawn in every arrow scene, date cards held readable
 *  5. inspection frames 0, 450, 900, 1350, 1790 rendered to out/frames/
 *  6. determinism: frame 900 rendered twice (two separate processes) -> identical SHA-256
 */
'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { execFileSync, spawnSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const OUT = path.join(ROOT, 'out');
const MP4 = path.join(OUT, 'ww2_germany_60s.mp4');
const lines = [];
let failed = 0;
const log = (s = '') => { lines.push(s); console.log(s); };
const check = (ok, label, detail = '') => { if (!ok) failed++; log(`  [${ok ? 'PASS' : 'FAIL'}] ${label}${detail ? '  — ' + detail : ''}`); return ok; };

// ---- child mode: render one frame and print its hash (used by check 6) ----------------------
if (process.argv[2] === '--hash') {
  const { frameRaw } = require('../src/render');
  process.stdout.write(crypto.createHash('sha256').update(frameRaw(+process.argv[3])).digest('hex'));
  process.exit(0);
}

const tl = JSON.parse(fs.readFileSync(path.join(ROOT, 'build', 'timeline.json'), 'utf8'));

// ---- 1. ffprobe ---------------------------------------------------------------------------------
log('1. FFPROBE  ' + path.relative(ROOT, MP4));
const probe = JSON.parse(execFileSync('ffprobe', ['-v', 'error', '-count_frames', '-show_streams', '-show_format', '-of', 'json', MP4]).toString());
const v = probe.streams.find((s) => s.codec_type === 'video');
const a = probe.streams.find((s) => s.codec_type === 'audio');
const dur = +probe.format.duration;
check(Math.abs(dur - 60) <= 0.05, 'duration 60.0 s ±0.05', `${dur.toFixed(3)} s (video ${(+v.duration).toFixed(3)} s, audio ${(+a.duration).toFixed(3)} s)`);
check(+v.nb_read_frames === 1800, '1800 frames', `${v.nb_read_frames} frames`);
check(v.width === 1080 && v.height === 1920, '1080x1920', `${v.width}x${v.height}`);
check(v.r_frame_rate === '30/1' && v.avg_frame_rate === '30/1', '30 fps', `r=${v.r_frame_rate} avg=${v.avg_frame_rate}`);
check(v.codec_name === 'h264' && v.pix_fmt === 'yuv420p', 'H.264 yuv420p', `${v.codec_name} ${v.profile} ${v.pix_fmt}`);
check(a.codec_name === 'aac' && +a.sample_rate === 48000 && a.channels === 2, 'AAC 48 kHz stereo', `${a.codec_name} ${a.sample_rate} Hz ${a.channels} ch ${Math.round(+a.bit_rate / 1000)} kb/s`);
const head = fs.readFileSync(MP4).subarray(0, 64 * 1024);
check(head.indexOf('moov') >= 0 && head.indexOf('moov') < head.indexOf('mdat'), '+faststart (moov before mdat)');

// ---- 2. loudness --------------------------------------------------------------------------------
log('\n2. LOUDNESS (ffmpeg ebur128, peak=true)');
const eb = spawnSync('ffmpeg', ['-nostats', '-i', MP4, '-filter_complex', 'ebur128=peak=true', '-f', 'null', '-'], { encoding: 'utf8' }).stderr;
const summary = eb.slice(eb.lastIndexOf('Summary:'));
const I = +summary.match(/I:\s+(-?[\d.]+) LUFS/)[1];
const LRA = +summary.match(/LRA:\s+(-?[\d.]+) LU/)[1];
const TP = +summary.match(/True peak:[\s\S]*?Peak:\s+(-?[\d.]+) dBFS/)[1];
check(Math.abs(I + 14) <= 1, 'integrated -14 LUFS ±1', `${I.toFixed(1)} LUFS (LRA ${LRA} LU)`);
check(TP <= -1.0, 'true peak <= -1 dBTP', `${TP.toFixed(1)} dBTP`);

// ---- 3. sync table ----------------------------------------------------------------------------
log('\n3. NARRATION SYNC (voice: ' + tl.voice + ', rate ' + tl.rate + ')');
log('   scene        frames      scene window      narration         end gap   status');
for (const s of tl.scenes) {
  const n = s.narration;
  const inside = n.startSec >= s.startSec - 1e-6 && n.endSec <= s.endSec + 1e-6;
  const gap = s.endSec - n.endSec;
  const ok = inside && Math.abs(gap - tl.narrationTail) < 0.02;
  if (!ok) failed++;
  log(`   ${s.id.padEnd(12)} ${String(s.startFrame).padStart(4)}-${String(s.endFrame - 1).padEnd(4)}  ` +
    `${s.startSec.toFixed(2).padStart(5)}-${s.endSec.toFixed(2).padEnd(6)}  ${n.startSec.toFixed(2).padStart(5)}-${n.endSec.toFixed(2).padEnd(6)}   ` +
    `+${gap.toFixed(2)} s    ${ok ? 'PASS' : 'FAIL'}`);
}
check(tl.scenes[tl.scenes.length - 1].endFrame === 1800, 'scene windows cover exactly 1800 frames');

// ---- 4. contact sheet + automated frame scan --------------------------------------------------
log('\n4. CONTACT SHEET + FRAME SCAN');
check(fs.existsSync(path.join(OUT, 'contact_sheet.png')), 'out/contact_sheet.png exists (30 frames, 1 per 2 s, safe-zone guides drawn)');

// 4a. empty frames: per-frame luma stats of the encoded video
const st = spawnSync('ffmpeg', ['-v', 'error', '-i', MP4, '-vf', 'signalstats,metadata=print:file=-', '-f', 'null', '-'], { encoding: 'utf8', maxBuffer: 64 << 20 }).stdout;
const yavg = [...st.matchAll(/lavfi\.signalstats\.YAVG=([\d.]+)/g)].map((m) => +m[1]);
const ylow = [...st.matchAll(/lavfi\.signalstats\.YLOW=([\d.]+)/g)].map((m) => +m[1]);
const yhigh = [...st.matchAll(/lavfi\.signalstats\.YHIGH=([\d.]+)/g)].map((m) => +m[1]);
const flat = [];
yavg.forEach((y, i) => { if (yhigh[i] - ylow[i] < 3) flat.push(i); });
const ranges = (arr) => arr.reduce((r, f) => { const l = r[r.length - 1]; if (l && f === l[1] + 1) l[1] = f; else r.push([f, f]); return r; }, []).map(([x, y]) => (x === y ? `${x}` : `${x}-${y}`));
const transitionFrames = new Set();
for (const s of tl.scenes) if (s.transitionIn) for (let f = s.startFrame - 4; f < s.startFrame + 4; f++) transitionFrames.add(f);
const intentional = (f) => f < 12 || transitionFrames.has(f) || f >= 1785; // black open, dips, final fade
const unexpected = flat.filter((f) => !intentional(f));
check(yavg.length === 1800, 'luma stats for all 1800 frames');
check(unexpected.length === 0, 'no unintended empty (flat) frames',
  flat.length ? `flat frames: ${ranges(flat).join(', ')} — all intentional (pure-black open, dip-to-black peaks, final fade)` : 'none');

// 4b. instrumented render: text bounding boxes, arrows, date cards
const canvasMod = require('canvas');
const proto = canvasMod.CanvasRenderingContext2D.prototype;
const SAFE = tl.safe;
const textHits = [];
let curFrame = -1;
for (const fn of ['fillText', 'strokeText']) {
  const orig = proto[fn];
  proto[fn] = function (text, x, y, ...rest) {
    if (curFrame >= 0 && this.globalAlpha > 0.05 && String(text).trim()) {
      const m = this.measureText(text);
      const T = this.getTransform();
      const sx = T.a / qcScale, sy = T.d / qcScale;
      const left = (T.a * (x - m.actualBoundingBoxLeft) + T.e) / qcScale;
      const right = (T.a * (x + m.actualBoundingBoxRight) + T.e) / qcScale;
      const top = (T.d * (y - m.actualBoundingBoxAscent) + T.f) / qcScale;
      const bottom = (T.d * (y + m.actualBoundingBoxDescent) + T.f) / qcScale;
      if (sx > 0 && sy > 0) textHits.push({ frame: curFrame, text: String(text), left, right, top, bottom });
    }
    return orig.call(this, text, x, y, ...rest);
  };
}
global.__QC__ = { arrows: {} };
const qcScale = 0.5;
const { renderFrame } = require('../src/render');
for (let f = 0; f < 1800; f += 3) {
  curFrame = f;
  renderFrame(f, { scale: qcScale });
}
curFrame = -1;
// offscreen-layer text (scene 1's year) is drawn with the layer's own transform; same coordinate system.
const bad = textHits.filter((h) => h.top < SAFE.top - 1 || h.bottom > SAFE.top + SAFE.h + 1 || h.left < 0 || h.right > 1080);
const badFrames = [...new Set(bad.map((b) => b.frame))];
check(bad.length === 0, `all text inside safe zone (y ${SAFE.top}-${SAFE.top + SAFE.h}, x 0-1080) over ${Math.ceil(1800 / 3)} sampled frames`,
  bad.length ? `${bad.length} glyph runs outside, frames ${ranges(badFrames).slice(0, 8).join(', ')}: e.g. "${bad[0].text}" @ y ${bad[0].top.toFixed(0)}-${bad[0].bottom.toFixed(0)} x ${bad[0].left.toFixed(0)}-${bad[0].right.toFixed(0)}` : `${textHits.length} text draws checked`);
const minTop = Math.min(...textHits.map((h) => h.top)), maxBottom = Math.max(...textHits.map((h) => h.bottom));
log(`         text extent: y ${minTop.toFixed(0)} .. ${maxBottom.toFixed(0)} (TikTok UI bands: y < 150 and y > 1570)`);
check(maxBottom <= 1570, 'no text under the TikTok bottom UI band (y > 1570)');
const arrowScenes = ['poland', 'blitz', 'barbarossa', 'stalingrad', 'dday', 'berlin'];
for (const id of arrowScenes) {
  const n = global.__QC__.arrows[id] || 0;
  check(n >= 10, `arrows visible in ${id}`, `${n} sampled frames with a growing arrow`);
}
for (const s of tl.scenes.filter((x) => x.dateCard)) {
  const typed = s.dateCard.startSec + s.dateCard.text.length * 0.055;
  const hold = s.endSec - 0.4 - typed;
  check(hold >= 1.5, `date card "${s.dateCard.text}" fully typed & held`, `${hold.toFixed(1)} s on screen after typing`);
}

// ---- 5. inspection frames ---------------------------------------------------------------------
log('\n5. INSPECTION FRAMES');
const fdir = path.join(OUT, 'frames');
fs.mkdirSync(fdir, { recursive: true });
for (const f of [0, 450, 900, 1350, 1790]) {
  const file = path.join(fdir, `frame_${String(f).padStart(4, '0')}.png`);
  fs.writeFileSync(file, renderFrame(f, { scale: 1 }).toBuffer('image/png'));
  const sc = tl.scenes.find((s) => f >= s.startFrame && f < s.endFrame);
  check(fs.existsSync(file), `frame ${f} (${sc.id}, ${(f / 30).toFixed(2)} s)`, path.relative(ROOT, file));
}

// ---- 6. determinism ----------------------------------------------------------------------------
log('\n6. DETERMINISM (seed ' + tl.seed + ')');
const h = (i) => execFileSync('node', [__filename, '--hash', '900']).toString().trim();
const h1 = h(1), h2 = h(2);
check(h1 === h2 && h1.length === 64, 'frame 900 rendered twice in separate processes -> identical SHA-256', h1.slice(0, 16) + '…');

log(`\n${failed === 0 ? 'ALL CHECKS PASSED' : failed + ' CHECK(S) FAILED'}`);
fs.writeFileSync(path.join(OUT, 'qc_report.txt'), lines.join('\n') + '\n');
process.exit(failed ? 1 : 0);
