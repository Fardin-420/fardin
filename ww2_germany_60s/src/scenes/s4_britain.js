/**
 * SCENE 4 — BATTLE OF BRITAIN (1940).
 * The Channel map dissolves into a night sky: sweeping searchlights (additive gradients),
 * aircraft silhouettes crossing, flak flashes synced to the audio cues, and a blue glow rising
 * over the British skyline as Britain "holds". Parallax: stars < clouds < planes < ground.
 */
'use strict';

const { drawMap, Camera } = require('../lib/map');
const { seeds } = require('../lib/particles');
const { rng, helpers, noise1 } = require('../lib/prng');
const { seg, clamp, pushIn, easeOutCubic, rgba } = require('../lib/easing');
const { territory } = require('./common');

const GROUND_Y = 1470;
const STARS = seeds(401, 160, (r) => ({ x: r.range(0, 1080), y: r.range(0, 1300), s: r.range(0.6, 1.8), ph: r.range(0, 6.3), f: r.range(1, 4) }));
const CLOUDS = seeds(402, 14, (r) => ({ x: r.range(-200, 1300), y: r.range(250, 1250), w: r.range(260, 620), h: r.range(50, 120), layer: r.rand() < 0.5 ? 0 : 1, a: r.range(0.35, 0.7) }));
// town skyline (seeded once)
const SKYLINE = (() => {
  const r = helpers(rng(403));
  const b = [];
  let x = -40;
  while (x < 1120) {
    const w = r.range(48, 120), h = r.range(40, 140);
    b.push({ x, w, h, roof: r.rand() < 0.6 ? r.range(18, 46) : 0, chim: r.rand() < 0.55 ? r.range(0.15, 0.8) : -1, spire: r.rand() < 0.05 });
    x += w + r.range(-6, 6);
  }
  return b;
})();
const BEAMS = [
  { x: 120, base: -1.95, amp: 0.32, w: 0.4, ph: 0.3 },
  { x: 330, base: -1.35, amp: 0.38, w: 0.33, ph: 1.9 },
  { x: 560, base: -1.70, amp: 0.30, w: 0.45, ph: 3.1 },
  { x: 790, base: -1.25, amp: 0.34, w: 0.37, ph: 4.4 },
  { x: 990, base: -1.60, amp: 0.28, w: 0.42, ph: 5.6 },
];
// bomber formation (right -> left) and fighters (left -> right, banking)
const PLANES = [
  ...seeds(404, 6, (r, i) => ({ type: 'bomber', x0: 1250 + (i % 3) * 150 + r.range(-20, 20), y: 560 + Math.floor(i / 3) * 140 + (i % 3) * 45, v: -165, s: r.range(0.8, 1.0) })),
  { type: 'fighter', x0: -180, y: 820, v: 330, s: 0.62, bank: 0.25, start: 0.9 },
  { type: 'fighter', x0: -260, y: 940, v: 300, s: 0.55, bank: 0.32, start: 1.6 },
];

const beamAngle = (b, t) => b.base + b.amp * Math.sin(t * b.w * 2.2 + b.ph);

function drawPlane(ctx, x, y, s, rot, type, lit) {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(rot);
  ctx.scale(s, s);
  ctx.beginPath();
  if (type === 'bomber') { // twin-engine silhouette seen from below, nose pointing left
    ctx.ellipse(0, 0, 70, 9, 0, 0, Math.PI * 2);         // fuselage
    ctx.moveTo(-14, -6); ctx.lineTo(-6, -92); ctx.lineTo(10, -92); ctx.lineTo(12, -6);  // wing (top)
    ctx.moveTo(-14, 6); ctx.lineTo(-6, 92); ctx.lineTo(10, 92); ctx.lineTo(12, 6);      // wing (bottom)
    ctx.moveTo(52, -4); ctx.lineTo(62, -30); ctx.lineTo(72, -30); ctx.lineTo(70, 0);   // tailplane
    ctx.lineTo(72, 30); ctx.lineTo(62, 30); ctx.lineTo(52, 4);
    ctx.moveTo(-20, -40); ctx.ellipse(-12, -40, 16, 5, 0, 0, Math.PI * 2);               // engines
    ctx.moveTo(-20, 40); ctx.ellipse(-12, 40, 16, 5, 0, 0, Math.PI * 2);
  } else { // single-engine fighter, nose pointing right, elliptical wings
    ctx.ellipse(0, 0, 44, 6, 0, 0, Math.PI * 2);
    ctx.moveTo(4, 0); ctx.ellipse(2, 0, 12, 56, 0, 0, Math.PI * 2);
    ctx.moveTo(-34, 0); ctx.ellipse(-36, 0, 6, 18, 0, 0, Math.PI * 2);
  }
  ctx.fillStyle = '#060606';
  ctx.fill();
  if (lit > 0.02) { // caught in a beam: belly lights up
    ctx.fillStyle = `rgba(215,215,210,${0.75 * lit})`;
    ctx.fill();
  }
  ctx.restore();
}

function render(ctx, s) {
  const { t, p, C } = s;
  const flaks = s.cues('flak');
  const holdT = s.w('holds');

  // ---- night sky --------------------------------------------------------------------------------
  const sky = ctx.createLinearGradient(0, 0, 0, GROUND_Y);
  sky.addColorStop(0, '#050608');
  sky.addColorStop(0.7, '#101216');
  sky.addColorStop(1, '#1d1f24');
  ctx.fillStyle = sky;
  ctx.fillRect(0, 0, 1080, 1920);

  const z = pushIn(p);
  const layerScale = (k) => { ctx.translate(540, 900); ctx.scale(1 + (z - 1) * k, 1 + (z - 1) * k); ctx.translate(-540, -900); };

  // stars (slowest parallax)
  ctx.save();
  layerScale(0.3);
  for (const st of STARS) {
    const tw = 0.5 + 0.5 * Math.sin(t * st.f + st.ph);
    ctx.fillStyle = `rgba(220,220,225,${0.15 + 0.35 * tw})`;
    ctx.fillRect(st.x - t * 4, st.y, st.s, st.s);
  }
  ctx.restore();

  // searchlights (additive)
  ctx.save();
  layerScale(1);
  ctx.globalCompositeOperation = 'lighter';
  for (const b of BEAMS) {
    const a = beamAngle(b, t), len = 2000, spread = 0.035;
    const x0 = b.x, y0 = GROUND_Y - 20;
    const g = ctx.createLinearGradient(x0, y0, x0 + Math.cos(a) * len, y0 + Math.sin(a) * len);
    g.addColorStop(0, 'rgba(225,228,235,0.30)');
    g.addColorStop(0.5, 'rgba(225,228,235,0.10)');
    g.addColorStop(1, 'rgba(225,228,235,0)');
    for (const [sp, al] of [[spread * 2.6, 0.35], [spread, 1]]) {
      ctx.globalAlpha = al;
      ctx.beginPath();
      ctx.moveTo(x0 - 6, y0);
      ctx.lineTo(x0 + Math.cos(a - sp) * len, y0 + Math.sin(a - sp) * len);
      ctx.lineTo(x0 + Math.cos(a + sp) * len, y0 + Math.sin(a + sp) * len);
      ctx.lineTo(x0 + 6, y0);
      ctx.closePath();
      ctx.fillStyle = g;
      ctx.fill();
    }
  }
  ctx.restore();

  // clouds (two parallax layers, moonlit undersides)
  ctx.save();
  layerScale(0.6);
  for (const c of CLOUDS) {
    const x = ((c.x - t * (c.layer ? 26 : 12) + 1600) % 1600) - 260;
    const g = ctx.createRadialGradient(x, c.y, 0, x, c.y, c.w / 2);
    g.addColorStop(0, `rgba(40,42,48,${c.a})`);
    g.addColorStop(1, 'rgba(40,42,48,0)');
    ctx.save();
    ctx.translate(x, c.y);
    ctx.scale(1, c.h / c.w);
    ctx.translate(-x, -c.y);
    ctx.fillStyle = g;
    ctx.fillRect(x - c.w / 2, c.y - c.w / 2, c.w, c.w);
    ctx.restore();
  }
  ctx.restore();

  // aircraft
  ctx.save();
  layerScale(0.85);
  for (const pl of PLANES) {
    const tt = t - (pl.start || 0);
    if (tt < 0) continue;
    const x = pl.x0 + pl.v * tt;
    const y = pl.y + 8 * noise1(tt * 0.8, pl.y);
    // lit if inside any beam cone
    let lit = 0;
    for (const b of BEAMS) {
      const a = beamAngle(b, t);
      const ang = Math.atan2(y - (GROUND_Y - 20), x - b.x);
      lit = Math.max(lit, clamp(1 - Math.abs(ang - a) / 0.07));
    }
    const rot = pl.type === 'fighter' ? -pl.bank + 0.08 * Math.sin(tt * 2) : 0.02 * Math.sin(tt);
    drawPlane(ctx, x, y, pl.s, rot, pl.type, lit);
  }
  ctx.restore();

  // flak: bright flash, then a dark puff (positions seeded per cue)
  ctx.save();
  layerScale(0.85);
  flaks.forEach((ft, i) => {
    const r = helpers(rng(405, i));
    for (let k = 0; k < 3; k++) {
      const bt = t - ft - k * r.range(0.05, 0.18);
      if (bt < 0 || bt > 2.2) continue;
      const x = r.range(180, 900), y = r.range(430, 980);
      const puff = easeOutCubic(clamp(bt / 1.6));
      ctx.fillStyle = `rgba(30,30,30,${0.55 * (1 - clamp(bt / 2.2))})`;
      ctx.beginPath(); ctx.arc(x, y, 14 + 34 * puff, 0, Math.PI * 2); ctx.fill();
      const fl = clamp(1 - bt / 0.16);
      if (fl > 0) {
        ctx.globalCompositeOperation = 'lighter';
        const g = ctx.createRadialGradient(x, y, 0, x, y, 120);
        g.addColorStop(0, `rgba(255,236,200,${fl})`);
        g.addColorStop(0.25, `rgba(232,193,112,${0.5 * fl})`);
        g.addColorStop(1, 'rgba(0,0,0,0)');
        ctx.fillStyle = g;
        ctx.fillRect(x - 120, y - 120, 240, 240);
        ctx.globalCompositeOperation = 'source-over';
      }
    }
  });
  ctx.restore();

  // Britain glows blue and holds: glow along the horizon grows on "holds"
  const hold = 0.35 + 0.65 * easeOutCubic(seg(t, holdT - 0.3, holdT + 0.8));
  const pulse = 0.85 + 0.15 * Math.sin(t * 5);
  const hg = ctx.createLinearGradient(0, GROUND_Y - 380, 0, GROUND_Y);
  hg.addColorStop(0, rgba(C.allies, 0));
  hg.addColorStop(1, rgba(C.allies, 0.55 * hold * pulse));
  ctx.save();
  ctx.globalCompositeOperation = 'lighter';
  ctx.fillStyle = hg;
  ctx.fillRect(0, GROUND_Y - 380, 1080, 380);
  ctx.restore();

  // skyline (fastest parallax), blue rim light on the roofs
  ctx.save();
  layerScale(1.2);
  const sk = new Path2DShim();
  for (const b of SKYLINE) {
    const x = b.x - t * 6, top = GROUND_Y - b.h;
    sk.rect(x, top, b.w, b.h + 500);
    if (b.roof) sk.tri(x, top, x + b.w / 2, top - b.roof, x + b.w, top);
    if (b.chim >= 0) sk.rect(x + b.w * b.chim, top - (b.roof ? b.roof * 0.6 : 0) - 26, 12, 30);
    if (b.spire) sk.tri(x + b.w / 2 - 14, top, x + b.w / 2, top - 160, x + b.w / 2 + 14, top);
  }
  ctx.shadowColor = rgba(C.allies, 0.9 * hold);
  ctx.shadowBlur = 26;
  sk.fill(ctx, '#040405');
  ctx.shadowBlur = 0;
  ctx.restore();

  // dissolve in from the Channel map
  const dis = 1 - easeOutCubic(seg(t, 0.05, 0.9));
  if (dis > 0) {
    ctx.save();
    ctx.globalAlpha = dis;
    const cam = new Camera({ lon: 1.0, lat: 50.6, zoom: 3.2 * (1 + 0.1 * t) });
    drawMap(ctx, cam, territory(2, C), { colors: C });
    ctx.restore();
  }
  return {};
}

/** Tiny path accumulator (node-canvas has no Path2D). */
class Path2DShim {
  constructor() { this.ops = []; }
  rect(x, y, w, h) { this.ops.push(['r', x, y, w, h]); }
  tri(a, b, c, d, e, f) { this.ops.push(['t', a, b, c, d, e, f]); }
  fill(ctx, color) {
    ctx.beginPath();
    for (const o of this.ops) {
      if (o[0] === 'r') ctx.rect(o[1], o[2], o[3], o[4]);
      else { ctx.moveTo(o[1], o[2]); ctx.lineTo(o[3], o[4]); ctx.lineTo(o[5], o[6]); ctx.closePath(); }
    }
    ctx.fillStyle = color;
    ctx.fill();
  }
}

module.exports = { render };
