/**
 * filmfx.js — global archival post-processing applied to every frame:
 *   gate weave (±1.5 px), 2% flicker, seeded film grain (6% opacity), dust specks,
 *   occasional vertical scratches, vignette. All deterministic per frame index.
 */
'use strict';

const { createCanvas } = require('canvas');
const { rng, helpers, noise1 } = require('./prng');
const { clamp } = require('./easing');

const W = 1080, H = 1920;
const GRAIN_TILE = 360;
const GRAIN_TILES = 6;

let grainTiles = null, vignette = null;

function init() {
  if (grainTiles) return;
  grainTiles = [];
  for (let k = 0; k < GRAIN_TILES; k++) {
    const c = createCanvas(GRAIN_TILE, GRAIN_TILE);
    const x = c.getContext('2d');
    const img = x.createImageData(GRAIN_TILE, GRAIN_TILE);
    const r = rng(777, k);
    for (let i = 0; i < GRAIN_TILE * GRAIN_TILE; i++) {
      // roughly gaussian luminance noise
      const v = clamp(128 + ((r() + r() + r() - 1.5) * 2) * 150, 0, 255);
      img.data[i * 4] = img.data[i * 4 + 1] = img.data[i * 4 + 2] = v;
      img.data[i * 4 + 3] = 255;
    }
    x.putImageData(img, 0, 0);
    grainTiles.push(c);
  }
  vignette = createCanvas(W, H);
  const v = vignette.getContext('2d');
  const g = v.createRadialGradient(W / 2, H / 2, H * 0.22, W / 2, H / 2, H * 0.62);
  g.addColorStop(0, 'rgba(0,0,0,0)');
  g.addColorStop(0.65, 'rgba(0,0,0,0.22)');
  g.addColorStop(1, 'rgba(0,0,0,0.62)');
  v.fillStyle = g;
  v.fillRect(0, 0, W, H);
}

/** Gate weave offset for a frame: smooth drift, clamped to ±1.5 px. */
function weave(frame) {
  return [clamp(1.5 * noise1(frame * 0.21, 11), -1.5, 1.5), clamp(1.5 * noise1(frame * 0.17, 12), -1.5, 1.5)];
}

/**
 * Apply film FX on top of the (already composited) frame.
 * @param o { grain: 0..1 multiplier, dust: 0..1, vignette: 0..1 }
 */
function apply(ctx, frame, o = {}) {
  init();
  const grainAmt = o.grain ?? 1, dustAmt = o.dust ?? 1;
  const r = helpers(rng(31337, frame));

  // 2% flicker (brightness wobble)
  const fl = 0.02 * (noise1(frame * 0.9, 21) * 0.7 + (r.rand() - 0.5) * 0.6);
  if (fl > 0) { ctx.fillStyle = `rgba(255,248,235,${fl * 0.5})`; ctx.fillRect(0, 0, W, H); }
  else { ctx.fillStyle = `rgba(0,0,0,${-fl})`; ctx.fillRect(0, 0, W, H); }

  // vignette
  ctx.globalAlpha = o.vignette ?? 1;
  ctx.drawImage(vignette, 0, 0);
  ctx.globalAlpha = 1;

  // film grain: random tile, random offset, slightly enlarged grains
  if (grainAmt > 0) {
    const tile = grainTiles[Math.floor(r.rand() * GRAIN_TILES)];
    const pat = ctx.createPattern(tile, 'repeat');
    ctx.save();
    ctx.globalAlpha = 0.06 * grainAmt;
    ctx.translate(-r.rand() * GRAIN_TILE, -r.rand() * GRAIN_TILE);
    ctx.scale(1.4, 1.4);
    ctx.fillStyle = pat;
    ctx.fillRect(0, 0, W / 1.4 + GRAIN_TILE * 2, H / 1.4 + GRAIN_TILE * 2);
    ctx.restore();
  }

  if (dustAmt > 0) {
    // dust specks: a few per frame, dark or light, irregular
    const n = r.int(0, 5);
    for (let i = 0; i < n; i++) {
      const x = r.range(0, W), y = r.range(0, H), s = r.range(1.2, 4.5);
      const light = r.rand() < 0.35;
      ctx.fillStyle = light ? `rgba(235,228,214,${0.45 * dustAmt})` : `rgba(0,0,0,${0.55 * dustAmt})`;
      ctx.beginPath();
      ctx.ellipse(x, y, s, s * r.range(0.4, 1), r.range(0, Math.PI), 0, Math.PI * 2);
      ctx.fill();
    }
    // occasional hair
    if (r.rand() < 0.04) {
      const x = r.range(80, W - 80), y = r.range(200, H - 200);
      ctx.strokeStyle = `rgba(0,0,0,${0.5 * dustAmt})`;
      ctx.lineWidth = 1.4;
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.bezierCurveTo(x + r.range(-40, 40), y + r.range(-40, 40), x + r.range(-60, 60), y + r.range(-60, 60), x + r.range(-50, 50), y + r.range(20, 80));
      ctx.stroke();
    }
    // vertical scratches: persistent for ~10-frame windows, drifting slightly
    const win = Math.floor(frame / 10);
    const sr = helpers(rng(4242, win));
    if (sr.rand() < 0.28) {
      const x0 = sr.range(60, W - 60) + (frame % 10) * sr.range(-0.6, 0.6);
      const a = (0.12 + 0.12 * r.rand()) * dustAmt;
      ctx.fillStyle = sr.rand() < 0.5 ? `rgba(230,224,210,${a})` : `rgba(0,0,0,${a * 1.4})`;
      const y0 = sr.range(-200, 600), len = sr.range(700, 1900);
      ctx.fillRect(x0, y0, sr.range(1, 2.2), len);
    }
  }
}

module.exports = { apply, weave, init };
