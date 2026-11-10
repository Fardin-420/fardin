/**
 * SCENE 8 — FALL OF BERLIN (April 1945).
 * Blue and red arrows meet over Germany, camera zooms to Berlin; on "Soviet" (synced to an
 * explosion) we cut to a procedural ruined skyline — broken facades, empty windows with firelight,
 * drifting smoke and rising embers.
 */
'use strict';

const { drawMap, GROUPS, fillGroup, Camera } = require('../lib/map');
const { drawArrow, drawLabel, drawMarker } = require('../lib/draw');
const { drawSmoke, drawEmbers } = require('../lib/particles');
const { rng, helpers } = require('../lib/prng');
const { seg, clamp, pushIn, easeInOutCubic, easeOutCubic, rgba } = require('../lib/easing');
const { territory } = require('./common');

const BERLIN = [13.40, 52.52];
const ARROWS = [
  { path: [[6.2, 51.5], [9.4, 52.1], [11.9, 52.4]], color: 'allies', delay: 0 },     // west -> Elbe
  { path: [[18.8, 52.6], [16.4, 52.7], [13.9, 52.55]], color: 'soviet', delay: 0.1 },
  { path: [[17.6, 50.6], [15.6, 51.5], [13.75, 52.3]], color: 'soviet', delay: 0.25 },
];

const GROUND = 1500;
/** Procedural ruined buildings: jagged broken tops, window grids, some windows burning. */
function makeRow(key, n, hMin, hMax, wMin, wMax) {
  const r = helpers(rng(801, key));
  const out = [];
  let x = -60;
  while (x < 1180) {
    const w = r.range(wMin, wMax), h = r.range(hMin, hMax);
    const top = [];
    const steps = r.int(3, 7);
    for (let i = 0; i <= steps; i++) top.push([x + (w * i) / steps, GROUND - h * (r.rand() < 0.35 ? r.range(0.45, 0.8) : r.range(0.85, 1.05))]);
    const win = [];
    for (let wy = GROUND - h + 40; wy < GROUND - 30; wy += 46) {
      for (let wx = x + 14; wx < x + w - 24; wx += 34) if (r.rand() < 0.7) win.push([wx, wy, r.rand() < 0.16 ? r.range(0.4, 1) : 0, r.range(0, 6.3)]);
    }
    const girders = r.rand() < 0.45 ? r.int(2, 4) : 0;
    out.push({ x, w, h, top, win, girders });
    x += w + r.range(-10, 30);
  }
  return out;
}
const FAR = makeRow(1, 0, 220, 520, 90, 190);
const NEAR = makeRow(2, 0, 300, 760, 140, 260);

function drawRow(ctx, row, color, t, fire, shift) {
  ctx.save();
  ctx.translate(shift, 0);
  for (const b of row) {
    ctx.beginPath();
    ctx.moveTo(b.x, GROUND + 600);
    for (const q of b.top) ctx.lineTo(q[0], q[1]);
    ctx.lineTo(b.x + b.w, GROUND + 600);
    ctx.closePath();
    ctx.fillStyle = color;
    ctx.fill();
    // skeletal girders sticking out of broken tops
    if (b.girders) {
      ctx.strokeStyle = color;
      ctx.lineWidth = 5;
      for (let g = 0; g < b.girders; g++) {
        const q = b.top[g + 1];
        ctx.beginPath(); ctx.moveTo(q[0], q[1] + 4); ctx.lineTo(q[0] + (g % 2 ? 14 : -10), q[1] - 40 - g * 12); ctx.stroke();
      }
    }
    // empty windows: sky shows through or fire glows inside
    const minTop = Math.max(...b.top.map((q) => q[1]));
    for (const [wx, wy, burn, ph] of b.win) {
      if (wy < minTop + 10) continue;
      if (burn > 0) {
        const fl = burn * fire * (0.65 + 0.35 * Math.sin(t * 9 + ph) * Math.sin(t * 5.3 + ph * 2));
        ctx.fillStyle = `rgba(230,140,60,${clamp(fl)})`;
      } else ctx.fillStyle = 'rgba(70,60,52,0.55)';
      ctx.fillRect(wx, wy, 16, 26);
    }
  }
  ctx.restore();
}

function ruins(ctx, s, lt) {
  const { t, p } = s;
  const z = pushIn(p);
  const exps = s.cues('explosion').map((x) => t - x);
  const boom = Math.max(0, ...exps.map((d) => (d >= 0 ? Math.exp(-d * 3.2) : 0)));
  // smoky sky with fire glow on the horizon
  const sky = ctx.createLinearGradient(0, 0, 0, GROUND);
  sky.addColorStop(0, '#0c0b0a');
  sky.addColorStop(0.6, '#2a211b');
  sky.addColorStop(1, '#5a3b26');
  ctx.fillStyle = sky;
  ctx.fillRect(0, 0, 1080, 1920);
  const glow = ctx.createRadialGradient(560, GROUND - 60, 0, 560, GROUND - 60, 900);
  glow.addColorStop(0, `rgba(220,120,50,${0.35 + 0.4 * boom})`);
  glow.addColorStop(1, 'rgba(220,120,50,0)');
  ctx.save();
  ctx.globalCompositeOperation = 'lighter';
  ctx.fillStyle = glow;
  ctx.fillRect(0, 0, 1080, 1920);
  ctx.restore();

  ctx.save();
  ctx.translate(540, GROUND);
  ctx.scale(z, z);
  ctx.translate(-540, -GROUND);
  drawSmoke(ctx, t, { key: 81, n: 14, area: { x: 0, y: 500, w: 1080, h: 600 }, drift: [-14, -30], color: '#1c1a18', alpha: 0.75, size: [180, 360], grow: 22, life: 8 });
  drawRow(ctx, FAR, '#1d1a17', t, 0.6, -lt * 6);
  drawSmoke(ctx, t, { key: 82, n: 10, area: { x: 0, y: 1000, w: 1080, h: 400 }, drift: [-22, -38], color: '#2a2622', alpha: 0.6, size: [140, 260], grow: 30, life: 6 });
  drawRow(ctx, NEAR, '#070707', t, 1, -lt * 16);
  ctx.restore();
  ctx.fillStyle = '#070707';
  ctx.fillRect(0, GROUND + 120, 1080, 500);
  drawEmbers(ctx, t, { alpha: 1, top: 350, bottom: 1800 });
  if (boom > 0.01) {
    ctx.fillStyle = `rgba(240,190,130,${0.18 * boom})`;
    ctx.fillRect(0, 0, 1080, 1920);
  }
  return boom;
}

function render(ctx, s) {
  const { t, p, C } = s;
  const tCut = s.cue('explosion', 1);
  if (t >= tCut) {
    const boom = ruins(ctx, s, t - tCut);
    const flash = 1 - easeOutCubic(seg(t, tCut, tCut + 0.35));
    if (flash > 0) { ctx.fillStyle = `rgba(245,225,190,${0.75 * flash})`; ctx.fillRect(0, 0, 1080, 1920); }
    return { shake: 12 * boom };
  }
  // ---- map: fronts meet over Germany, zoom to Berlin ------------------------------------------
  const zk = easeInOutCubic(seg(t, tCut - 1.4, tCut));
  const zoom = 2.0 * Math.pow(9 / 2.0, zk) * pushIn(p);
  const cam = new Camera({ lon: 12.4 + (BERLIN[0] - 12.4) * zk, lat: 51.6 + (BERLIN[1] - 51.6) * zk, zoom });
  const fills = territory(3, C);
  fillGroup(fills, GROUPS.ussr, C.soviet, 0.85);
  fillGroup(fills, GROUPS.poland, C.soviet, 0.6);
  fillGroup(fills, [...GROUPS.france, ...GROUPS.lowCountries], C.allies, 0.55);
  fillGroup(fills, GROUPS.germany1939, C.axis, 1, 0.12 + 0.1 * Math.sin(t * 6));
  drawMap(ctx, cam, fills, { colors: C });
  for (const a of ARROWS) {
    drawArrow(ctx, cam, { path: a.path, progress: easeInOutCubic(seg(t, 0.1 + a.delay, 1.9 + a.delay)), color: C[a.color], width: 32 }, t);
  }
  drawMarker(ctx, cam, BERLIN, { alpha: seg(t, 1.0, 1.5), time: t, r: 10 });
  drawLabel(ctx, cam, 'BERLIN', BERLIN, { alpha: seg(t, 1.0, 1.5), size: 42, dy: -56, spacing: 10 });
  const e0 = s.cue('explosion', 0);
  const fl = t >= e0 ? Math.exp(-(t - e0) * 5) : 0;
  if (fl > 0.01) {
    const [bx, by] = cam.toScreen([14.6, 52.3]);
    const g = ctx.createRadialGradient(bx, by, 0, bx, by, 300);
    g.addColorStop(0, `rgba(255,220,170,${0.6 * fl})`);
    g.addColorStop(1, 'rgba(255,220,170,0)');
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.fillStyle = g; ctx.fillRect(0, 0, 1080, 1920); ctx.restore();
  }
  return { shake: 6 * fl };
}

module.exports = { render };
