/**
 * SCENE 6 — STALINGRAD (encirclement Nov 1942 -> surrender February 1943).
 * Zoom into the Stalingrad point under heavy snowfall (620 particles, 3 depth layers) while frost
 * creeps in from the frame edges. Red pincers close a ring around the German pocket on
 * "tide turns"; on "surrenders" the music drops to silence and the pocket collapses to red.
 */
'use strict';

const { createCanvas } = require('canvas');
const { drawMap, GROUPS, fillGroup, fillRegion, Camera } = require('../lib/map');
const { drawArrow, drawLabel, drawMarker } = require('../lib/draw');
const { drawSnow } = require('../lib/particles');
const { rng, helpers } = require('../lib/prng');
const { seg, clamp, easeInOutCubic, easeOutCubic, pushIn, rgba } = require('../lib/easing');
const { territory, desaturate } = require('./common');

const CITY = [44.52, 48.71];
const POCKET = [43.75, 48.78];      // centre of the encircled area (between the Don and the Volga)
// Approximate German-held area, late 1942: front along the Don from Voronezh to the Stalingrad
// bend, then south toward the Caucasus. Only its eastern edge is ever on screen.
const FRONT_1942 = [[20, 57], [31, 57], [34.5, 54.5], [37.2, 52.6], [39.2, 51.6], [40.6, 50.4], [42.2, 49.9],
  [43.6, 49.4], [44.35, 48.95], [44.62, 48.62], [44.4, 48.2], [44.0, 47.5], [44.3, 46.4], [44.6, 44.0], [30, 44], [20, 44]];
const PINCERS = [
  { path: [[42.1, 50.3], [42.4, 49.3], [43.45, 48.72]], delay: 0 },    // northern pincer (from the Don bend)
  { path: [[45.2, 47.5], [44.2, 48.05], [43.55, 48.66]], delay: 0.2 }, // southern pincer
];

// frost texture: seeded ice-crystal strokes, generated once at full resolution
let FROST = null;
function frost() {
  if (FROST) return FROST;
  FROST = createCanvas(1080, 1920);
  const c = FROST.getContext('2d');
  const r = helpers(rng(601));
  c.lineCap = 'round';
  for (let i = 0; i < 900; i++) {
    // seeds concentrated near the edges
    const edge = r.int(0, 3);
    const d = Math.pow(r.rand(), 2.2) * 420;
    let x = edge === 0 ? d : edge === 1 ? 1080 - d : r.range(0, 1080);
    let y = edge === 2 ? d : edge === 3 ? 1920 - d : r.range(0, 1920);
    if (edge < 2) y = r.range(0, 1920); else x = r.range(0, 1080);
    let a = r.range(0, Math.PI * 2);
    c.strokeStyle = `rgba(225,235,245,${r.range(0.05, 0.22)})`;
    c.lineWidth = r.range(0.6, 2.0);
    c.beginPath();
    c.moveTo(x, y);
    for (let k = 0; k < r.int(3, 8); k++) {
      a += r.range(-0.9, 0.9);
      const l = r.range(8, 34);
      x += Math.cos(a) * l; y += Math.sin(a) * l;
      c.lineTo(x, y);
    }
    c.stroke();
  }
  return FROST;
}

function render(ctx, s) {
  const { t, p, C } = s;
  const tTide = s.w('tide');
  const tSil = s.tl.scenes[s.sc.index].music.silenceSec - s.sc.startSec; // silence beat = surrender

  // camera: zoom into the city (big travel) * brief's push-in
  const k = easeInOutCubic(seg(p, 0, 0.6));
  const zoom = 2.0 * Math.pow(9.0 / 2.0, k) * pushIn(p);
  const cam = new Camera({ lon: 38.5 + (CITY[0] - 0.55 - 38.5) * k, lat: 51.0 + (48.75 - 51.0) * k, zoom });

  const fills = territory(3, C);
  fillGroup(fills, GROUPS.ussr, C.soviet, 0.6);
  // German-held area 1942: gray zone reaching the Volga; recedes once the ring closes
  const ring = easeInOutCubic(seg(t, tTide + 0.9, tTide + 1.9));
  const fall = easeInOutCubic(seg(t, tSil - 0.1, tSil + 0.9));
  drawMap(ctx, cam, fills, { colors: C });
  // the front pushed back west once the ring closes (the pocket stays behind)
  const back = FRONT_1942.map(([lo, la]) => [lo - (lo > 38 ? 3.2 * ring : 0), la]);
  fillRegion(ctx, cam, GROUPS.ussr, back, C.axis, 0.85 * (1 - 0.35 * ring), 0.35);

  // the pocket (gray) inside the ring, collapsing at the surrender
  const [px, py] = cam.toScreen(POCKET);
  const [ex] = cam.toScreen([POCKET[0] + 1.05, POCKET[1]]);
  const rx = Math.abs(ex - px), ry = rx * 0.62;
  const pocketA = (1 - fall) * (0.55 + 0.45 * ring);
  if (pocketA > 0.01) {
    ctx.save();
    ctx.beginPath();
    ctx.ellipse(px, py, rx * (1 - 0.25 * fall), ry * (1 - 0.25 * fall), -0.05, 0, Math.PI * 2);
    ctx.fillStyle = rgba('#8a8f95', 0.9 * pocketA);
    ctx.fill();
    ctx.restore();
  }
  // red ring closes from north and south, meeting in the west (Kalach)
  if (ring > 0) {
    ctx.save();
    ctx.lineCap = 'round';
    const sweep = Math.PI * ring;
    const flare = fall > 0 ? 1 + 0.6 * Math.sin(Math.PI * clamp(fall * 1.5)) : 1;
    for (const [w, a, col] of [[34 * flare, 0.35, C.soviet], [20, 0.9, '#0d0d0d'], [12, 1, '#c8433c']]) {
      ctx.strokeStyle = rgba(col, a);
      ctx.lineWidth = w;
      ctx.beginPath();
      ctx.ellipse(px, py, rx * 1.08, ry * 1.08, -0.05, -sweep, 0);   // east -> north-west (counter-clockwise up)
      ctx.stroke();
      ctx.beginPath();
      ctx.ellipse(px, py, rx * 1.08, ry * 1.08, -0.05, 0, sweep);    // east -> south-west
      ctx.stroke();
    }
    ctx.restore();
  }
  // after the surrender, the pocket is Soviet red
  if (fall > 0) {
    ctx.beginPath();
    ctx.ellipse(px, py, rx * 1.08, ry * 1.08, -0.05, 0, Math.PI * 2);
    ctx.fillStyle = rgba(C.soviet, 0.55 * fall);
    ctx.fill();
  }

  for (const a of PINCERS) {
    const kk = easeOutCubic(seg(t, tTide - 0.35 + a.delay, tTide + 1.0 + a.delay));
    drawArrow(ctx, cam, { path: a.path, progress: kk, color: C.soviet, width: 34, head: 60, alpha: 1 - 0.6 * ring }, t);
  }
  drawMarker(ctx, cam, CITY, { alpha: seg(t, 0.3, 0.9), time: t, r: 10 });
  drawLabel(ctx, cam, 'STALINGRAD', CITY, { alpha: seg(t, s.w('stalingrad') - 0.1, s.w('stalingrad') + 0.4), size: 40, dy: -56, spacing: 8 });

  // winter: desaturate, cold tint, frost from the edges, heavy snow (3 layers)
  desaturate(ctx, 0.35);
  ctx.fillStyle = 'rgba(160,175,190,0.05)';
  ctx.fillRect(0, 0, 1080, 1920);
  drawSnow(ctx, s.time, { amount: 1, wind: -170, alpha: 0.95, speed: 1.1 });

  const fr = easeOutCubic(seg(p, 0.0, 1.0));
  const L = s.layer('frost');
  L.ctx.drawImage(frost(), 0, 0, 1080, 1920);
  L.ctx.globalCompositeOperation = 'destination-in';
  const inner = 980 - 560 * fr;
  const g = L.ctx.createRadialGradient(540, 900, inner * 0.55, 540, 900, inner + 260);
  g.addColorStop(0, 'rgba(0,0,0,0)');
  g.addColorStop(1, 'rgba(0,0,0,1)');
  L.ctx.fillStyle = g;
  L.ctx.fillRect(0, 0, 1080, 1920);
  L.ctx.globalCompositeOperation = 'source-over';
  // frosted edge haze
  const haze = L.ctx.createRadialGradient(540, 900, inner * 0.7, 540, 1000, inner + 500);
  haze.addColorStop(0, 'rgba(200,212,225,0)');
  haze.addColorStop(1, `rgba(200,212,225,${0.2 * fr})`);
  L.ctx.fillStyle = haze;
  L.ctx.fillRect(0, 0, 1080, 1920);
  ctx.drawImage(L.canvas, 0, 0, L.canvas.width, L.canvas.height, 0, 0, 1080, 1920);

  // the silence beat: a brief dimming hold at the surrender
  const hush = seg(t, tSil - 0.05, tSil + 0.15) * (1 - seg(t, tSil + 0.7, tSil + 1.2));
  if (hush > 0) { ctx.fillStyle = `rgba(0,0,0,${0.22 * hush})`; ctx.fillRect(0, 0, 1080, 1920); }
  return {};
}

module.exports = { render };
