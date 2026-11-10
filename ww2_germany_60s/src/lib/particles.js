/**
 * particles.js — analytic (stateless) particle systems. A particle's position is a pure function
 * of time, so any frame can be rendered in isolation and renders are bit-for-bit repeatable.
 */
'use strict';

const { rng, helpers } = require('./prng');
const { clamp, rgba } = require('./easing');

const W = 1080, H = 1920;
const mod = (a, n) => ((a % n) + n) % n;

/** Pre-generate particle seeds once per system. */
function seeds(key, n, fn) {
  const r = helpers(rng(key));
  return Array.from({ length: n }, (_, i) => fn(r, i));
}

// ---- snow (3 depth layers) --------------------------------------------------------------------
const SNOW = seeds(901, 620, (r) => {
  const d = r.rand() < 0.5 ? r.range(0.15, 0.4) : r.rand() < 0.7 ? r.range(0.4, 0.75) : r.range(0.75, 1);
  return { x: r.range(0, W), y: r.range(0, H), d, ph: r.range(0, 6.28), sw: r.range(10, 40), fs: r.range(0.6, 1.6) };
});

/**
 * @param t       seconds (drives motion)
 * @param amount  0..1 fraction of particles visible (snow "begins")
 * @param wind    px/s horizontal drift for the nearest layer
 */
function drawSnow(ctx, t, { amount = 1, wind = -120, alpha = 1, speed = 1 } = {}) {
  if (amount <= 0) return;
  const n = Math.floor(SNOW.length * clamp(amount));
  ctx.save();
  for (let i = 0; i < n; i++) {
    const s = SNOW[i];
    const v = (70 + 260 * s.d) * speed;
    const y = mod(s.y + v * t, H + 60) - 30;
    const x = mod(s.x + wind * s.d * t + s.sw * Math.sin(t * s.fs + s.ph), W + 60) - 30;
    const r = 1.2 + 5.2 * s.d * s.d;
    const a = (0.25 + 0.6 * s.d) * alpha;
    if (s.d > 0.8) { // near flakes: soft halo (depth of field)
      ctx.fillStyle = `rgba(232,232,236,${a * 0.25})`;
      ctx.beginPath(); ctx.arc(x, y, r * 2.2, 0, Math.PI * 2); ctx.fill();
    }
    ctx.fillStyle = `rgba(236,236,240,${a})`;
    ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
  }
  ctx.restore();
}

// ---- embers rising ----------------------------------------------------------------------------
const EMBERS = seeds(902, 140, (r) => ({ x: r.range(0, W), y: r.range(0, H), v: r.range(60, 190), ph: r.range(0, 6.28),
  sw: r.range(10, 50), s: r.range(1.5, 4.2), fl: r.range(4, 11) }));

function drawEmbers(ctx, t, { alpha = 1, top = 300, bottom = 1750 } = {}) {
  if (alpha <= 0) return;
  ctx.save();
  ctx.globalCompositeOperation = 'lighter';
  const span = bottom - top;
  for (const e of EMBERS) {
    const y = bottom - mod(e.y + e.v * t, span);
    const x = e.x + e.sw * Math.sin(t * 1.3 + e.ph) + (bottom - y) * 0.08;
    const life = (bottom - y) / span; // fade as they rise
    const a = alpha * (1 - life) * (0.55 + 0.45 * Math.sin(t * e.fl + e.ph));
    if (a <= 0.02) continue;
    ctx.fillStyle = `rgba(232,150,70,${a * 0.3})`;
    ctx.beginPath(); ctx.arc(x, y, e.s * 2.6, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = `rgba(255,205,140,${a})`;
    ctx.beginPath(); ctx.arc(x, y, e.s * 0.8, 0, Math.PI * 2); ctx.fill();
  }
  ctx.restore();
}

// ---- smoke ------------------------------------------------------------------------------------
/**
 * Soft drifting smoke blobs.
 * @param key      seed key (different systems look different)
 * @param area     {x, y, w, h} spawn band
 * @param drift    [vx, vy] px/s
 */
function drawSmoke(ctx, t, { key = 1, n = 18, area = { x: 0, y: 900, w: W, h: 600 }, drift = [-20, -25], color = '#2b2926',
  alpha = 0.5, size = [120, 300], grow = 18, life = 9 } = {}) {
  const S = seeds(9000 + key, n, (r) => ({ x: r.range(0, 1), y: r.range(0, 1), s: r.range(size[0], size[1]), off: r.range(0, life),
    dv: r.range(0.6, 1.4) }));
  ctx.save();
  for (const s of S) {
    const age = mod(t + s.off, life);
    const fade = Math.sin(Math.PI * age / life);
    const x = area.x + s.x * area.w + drift[0] * age * s.dv;
    const y = area.y + s.y * area.h + drift[1] * age * s.dv;
    const rad = s.s + grow * age;
    const g = ctx.createRadialGradient(x, y, 0, x, y, rad);
    g.addColorStop(0, rgba(color, alpha * fade));
    g.addColorStop(1, rgba(color, 0));
    ctx.fillStyle = g;
    ctx.fillRect(x - rad, y - rad, rad * 2, rad * 2);
  }
  ctx.restore();
}

// ---- speed lines (blitz) ----------------------------------------------------------------------
const STREAKS = seeds(903, 70, (r) => ({ y: r.range(250, 1650), x: r.range(0, 1), len: r.range(120, 420), v: r.range(1400, 2600),
  a: r.range(0.08, 0.3), w: r.range(1, 3) }));

function drawSpeedLines(ctx, t, { alpha = 1, dir = -1 } = {}) {
  if (alpha <= 0) return;
  ctx.save();
  for (const s of STREAKS) {
    const x = mod(s.x * (W + 600) + dir * s.v * t, W + 600) - 300;
    const g = ctx.createLinearGradient(x, 0, x - dir * s.len, 0);
    g.addColorStop(0, `rgba(216,210,196,${s.a * alpha})`);
    g.addColorStop(1, 'rgba(216,210,196,0)');
    ctx.fillStyle = g;
    ctx.fillRect(Math.min(x, x - dir * s.len), s.y, s.len, s.w);
  }
  ctx.restore();
}

module.exports = { drawSnow, drawEmbers, drawSmoke, drawSpeedLines, seeds };
