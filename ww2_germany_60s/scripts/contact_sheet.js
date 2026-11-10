/**
 * contact_sheet.js — one frame every 2 s (60 frames), decoded from the FINAL encoded MP4 so it
 * shows exactly what ships. 30 thumbnails in a 6x5 grid with frame/time labels and the
 * safe-zone guides (center 1080x1350 box, TikTok UI bands) drawn on each thumbnail.
 *   -> out/contact_sheet.png
 */
'use strict';

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const { createCanvas, loadImage } = require('canvas');
const { registerFonts } = require('../src/lib/fonts');

registerFonts();
const ROOT = path.resolve(__dirname, '..');
const src = path.join(ROOT, process.argv[2] || 'out/ww2_germany_60s.mp4');
const dir = path.join(ROOT, 'build', 'contact');
fs.rmSync(dir, { recursive: true, force: true });
fs.mkdirSync(dir, { recursive: true });
execFileSync('ffmpeg', ['-v', 'error', '-i', src, '-vf', "select='not(mod(n\\,60))'", '-vsync', 'vfr', path.join(dir, 'c_%02d.png')]);

(async () => {
  const files = fs.readdirSync(dir).filter((f) => f.endsWith('.png')).sort();
  const TW = 240, TH = 427, COLS = 6, PAD = 10, LABEL = 30;
  const rows = Math.ceil(files.length / COLS);
  const W = COLS * (TW + PAD) + PAD, H = rows * (TH + LABEL + PAD) + PAD + 60;
  const c = createCanvas(W, H);
  const x = c.getContext('2d');
  x.fillStyle = '#151515';
  x.fillRect(0, 0, W, H);
  x.fillStyle = '#d8d2c4';
  x.font = '700 30px Oswald';
  x.fillText("GERMANY'S WAR, 1939–1945 — contact sheet (1 frame / 2 s)", PAD, 42);
  for (let i = 0; i < files.length; i++) {
    const im = await loadImage(path.join(dir, files[i]));
    const cx = PAD + (i % COLS) * (TW + PAD), cy = 60 + PAD + Math.floor(i / COLS) * (TH + LABEL + PAD);
    x.drawImage(im, cx, cy, TW, TH);
    const k = TH / 1920;
    x.strokeStyle = 'rgba(80,200,120,0.6)'; // safe zone 1080x1350
    x.lineWidth = 1;
    x.strokeRect(cx + 0.5, cy + 285 * k, TW - 1, 1350 * k);
    x.fillStyle = 'rgba(255,70,70,0.10)'; // TikTok UI bands
    x.fillRect(cx, cy, TW, 150 * k);
    x.fillRect(cx, cy + (1920 - 350) * k, TW, 350 * k);
    x.fillStyle = '#e8c170';
    x.font = '500 18px Oswald';
    x.fillText(`f${i * 60}  ·  ${(i * 2).toFixed(1)} s`, cx + 4, cy + TH + 21);
  }
  fs.writeFileSync(path.join(ROOT, 'out', 'contact_sheet.png'), c.toBuffer('image/png'));
  console.log(`wrote out/contact_sheet.png (${files.length} frames)`);
})();
