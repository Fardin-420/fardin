/**
 * SCENE 7 — D-DAY (June 6, 1944).
 * Part A: dawn sea horizon, layered sine-wave swells, landing craft heading for the bluffs,
 *         smoke plumes, tracer lines.
 * Part B (cut on "Germany", synced to the whoosh): map — blue arrows from Normandy east, red arrows
 *         from the east west, closing on Germany. Two fronts.
 */
'use strict';

const { drawMap, GROUPS, fillGroup } = require('../lib/map');
const { drawArrow, drawLabel, drawMarker } = require('../lib/draw');
const { drawSmoke, seeds } = require('../lib/particles');
const { rng, helpers } = require('../lib/prng');
const { seg, clamp, pushIn, easeInOutCubic, easeOutCubic, rgba } = require('../lib/easing');
const { travelCam, territory, blackOverlay } = require('./common');

const HORIZON = 760;
const CRAFT = seeds(701, 7, (r, i) => ({ x: 120 + i * 140 + r.range(-40, 40), d0: r.range(0.55, 1.0), v: r.range(0.06, 0.09), bob: r.range(0, 6.3) }));
const TRACERS = seeds(702, 40, (r) => ({ x: r.range(80, 1000), t0: r.range(0, 5), dx: r.range(-380, 380), dy: r.range(420, 760), life: r.range(0.35, 0.7) }));
const BLUFF = (() => { // shoreline profile on the horizon
  const r = helpers(rng(703));
  const pts = [];
  let h = 30;
  for (let x = -40; x <= 1120; x += 24) { h = clamp(h + r.range(-9, 9), 14, 70); pts.push([x, HORIZON - h]); }
  return pts;
})();

const BLUE = [
  { path: [[-0.7, 49.3], [2.6, 49.6], [6.6, 50.6]], delay: 0 },
  { path: [[-0.5, 49.0], [2.2, 48.0], [6.4, 48.7]], delay: 0.15 },
];
const RED = [
  { path: [[29.5, 54.6], [23.8, 53.6], [18.4, 52.7]], delay: 0.05 },
  { path: [[29.8, 50.4], [24.0, 50.6], [18.6, 50.9]], delay: 0.2 },
  { path: [[27.5, 47.4], [22.4, 48.6], [17.6, 49.4]], delay: 0.35 },
];

function sea(ctx, s) {
  const { t, p } = s;
  const z = pushIn(p);
  ctx.save();
  ctx.translate(540, HORIZON);
  ctx.scale(z, z);
  ctx.translate(-540, -HORIZON);
  // dawn sky (desaturated warm)
  const sky = ctx.createLinearGradient(0, 0, 0, HORIZON);
  sky.addColorStop(0, '#141416');
  sky.addColorStop(0.55, '#3a3631');
  sky.addColorStop(1, '#8a7f6c');
  ctx.fillStyle = sky;
  ctx.fillRect(-100, -100, 1300, HORIZON + 100);
  const sun = ctx.createRadialGradient(720, HORIZON - 10, 0, 720, HORIZON - 10, 520);
  sun.addColorStop(0, 'rgba(235,215,175,0.55)');
  sun.addColorStop(0.2, 'rgba(210,180,130,0.22)');
  sun.addColorStop(1, 'rgba(210,180,130,0)');
  ctx.fillStyle = sun;
  ctx.fillRect(-100, -100, 1300, HORIZON + 300);
  // smoke plumes rising from the shore
  drawSmoke(ctx, t, { key: 7, n: 16, area: { x: 0, y: HORIZON - 70, w: 1080, h: 30 }, drift: [-12, -46], color: '#2a2724', alpha: 0.55, size: [40, 90], grow: 26, life: 6 });
  // bluffs
  ctx.beginPath();
  ctx.moveTo(-40, HORIZON + 4);
  for (const q of BLUFF) ctx.lineTo(q[0], q[1]);
  ctx.lineTo(1120, HORIZON + 4);
  ctx.closePath();
  ctx.fillStyle = '#1b1a18';
  ctx.fill();
  // tracers from the shore
  ctx.save();
  ctx.globalCompositeOperation = 'lighter';
  for (const tr of TRACERS) {
    const age = ((t - tr.t0) % 1.6 + 1.6) % 1.6;
    if (age > tr.life) continue;
    const k = age / tr.life;
    const x0 = tr.x + tr.dx * k, y0 = HORIZON - 30 + tr.dy * k;
    ctx.strokeStyle = `rgba(255,215,150,${1 - k * 0.7})`;
    ctx.lineWidth = 3.5;
    ctx.beginPath();
    ctx.moveTo(x0, y0);
    ctx.lineTo(x0 - tr.dx * 0.12, y0 - tr.dy * 0.12);
    ctx.stroke();
  }
  ctx.restore();
  // sea: base + layered sine swells (far -> near, parallax)
  const seaG = ctx.createLinearGradient(0, HORIZON, 0, 1920);
  seaG.addColorStop(0, '#5e594f');
  seaG.addColorStop(0.15, '#2c2b29');
  seaG.addColorStop(1, '#0e0f10');
  ctx.fillStyle = seaG;
  ctx.fillRect(-100, HORIZON, 1300, 1300);
  for (let L = 0; L < 14; L++) {
    const d = L / 13;                         // 0 far .. 1 near
    const y = HORIZON + 8 + Math.pow(d, 1.8) * 1150;
    const amp = 2 + 26 * d * d, wl = 60 + 420 * d, sp = 0.6 + 1.4 * d;
    ctx.beginPath();
    ctx.moveTo(-100, 2000);
    for (let x = -100; x <= 1180; x += 12) {
      const yy = y + amp * Math.sin(x / wl * 6.283 + t * sp + L * 1.7) + amp * 0.4 * Math.sin(x / (wl * 0.43) - t * sp * 1.3 + L);
      ctx.lineTo(x, yy);
    }
    ctx.lineTo(1180, 2000);
    ctx.closePath();
    ctx.fillStyle = `rgba(${18 + 30 * (1 - d)},${18 + 28 * (1 - d)},${18 + 25 * (1 - d)},0.55)`;
    ctx.fill();
    ctx.strokeStyle = `rgba(200,190,170,${0.05 + 0.12 * (1 - d)})`;
    ctx.lineWidth = 1 + 2 * d;
    ctx.stroke();
  }
  // landing craft heading for the beach (shrinking toward the horizon)
  const crafts = CRAFT.map((c) => ({ ...c, d: clamp(c.d0 - c.v * t, 0.05, 1) })).sort((a, b) => a.d - b.d);
  for (const c of crafts) {
    const y = HORIZON + 10 + Math.pow(c.d, 1.8) * 1150;
    const sc = 0.15 + 1.25 * c.d;
    const x = 540 + (c.x - 540) * (0.4 + 0.8 * c.d);
    const bob = Math.sin(t * 2.2 + c.bob) * 6 * sc;
    ctx.save();
    ctx.translate(x, y + bob);
    ctx.scale(sc, sc);
    ctx.rotate(0.03 * Math.sin(t * 1.7 + c.bob));
    // wake
    ctx.fillStyle = 'rgba(210,205,190,0.18)';
    ctx.beginPath(); ctx.ellipse(0, 22, 90, 16, 0, 0, Math.PI * 2); ctx.fill();
    // hull seen from behind: boxy, with raised ramp at the bow
    ctx.fillStyle = '#0b0b0b';
    ctx.beginPath();
    ctx.moveTo(-62, 0); ctx.lineTo(-56, -46); ctx.lineTo(56, -46); ctx.lineTo(62, 0); ctx.lineTo(54, 20); ctx.lineTo(-54, 20);
    ctx.closePath(); ctx.fill();
    ctx.fillRect(-44, -66, 88, 22);                      // ramp
    // dawn rim light along the top edges (sun ahead of the boats)
    ctx.fillStyle = 'rgba(200,180,140,0.55)';
    ctx.fillRect(-44, -66, 88, 3);
    ctx.fillRect(-56, -47, 112, 2);
    // spray at the stern
    ctx.fillStyle = 'rgba(225,220,205,0.35)';
    ctx.beginPath(); ctx.ellipse(-50, 16, 22, 7, 0.2, 0, Math.PI * 2); ctx.ellipse(50, 16, 22, 7, -0.2, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#151514';
    for (let h = -36; h <= 36; h += 12) { ctx.beginPath(); ctx.arc(h, -48, 5, Math.PI, 0); ctx.fill(); } // helmets
    ctx.restore();
  }
  ctx.restore();
}

function render(ctx, s) {
  const { t, p, C } = s;
  const tCut = s.cue('whoosh') + 0.2; // whoosh leads the cut slightly
  if (t < tCut) {
    sea(ctx, s);
    // dissolve-in & quick white blink of the cut
    const blink = seg(t, tCut - 0.12, tCut);
    if (blink > 0) { ctx.fillStyle = `rgba(230,224,210,${0.5 * blink})`; ctx.fillRect(0, 0, 1080, 1920); }
    return { dateCard: { y: 400 } };
  }
  // ---- Part B: two fronts --------------------------------------------------------------------
  const lt = t - tCut, lp = seg(t, tCut, s.dur);
  const cam = travelCam(lp, { lon: 12.0, lat: 51.0, zoom: 1.35 }, { lon: 12.5, lat: 51.0, zoom: 1.45 });
  const fills = territory(3, C);
  fillGroup(fills, GROUPS.ussr, C.soviet, 0.85);
  const pulse = 0.5 + 0.5 * Math.sin(lt * 6);
  fillGroup(fills, ['Germany', 'Austria', 'Czechia', 'East Prussia'], C.axis, 1, 0.15 + 0.25 * pulse * seg(lt, 0.6, 1.2));
  drawMap(ctx, cam, fills, { colors: C });
  drawMarker(ctx, cam, [-0.6, 49.35], { alpha: seg(lt, 0, 0.3), time: lt, color: '#8fb3dd', r: 8 });
  drawLabel(ctx, cam, 'NORMANDY', [-0.6, 49.35], { alpha: seg(lt, 0, 0.3), size: 26, dy: 40 });
  drawLabel(ctx, cam, 'GERMANY', [10.4, 51.2], { alpha: seg(lt, 0.3, 0.7), size: 40 });
  for (const a of BLUE) drawArrow(ctx, cam, { path: a.path, progress: easeInOutCubic(seg(lt, a.delay, 1.7 + a.delay)), color: C.allies, width: 30 }, t);
  for (const a of RED) drawArrow(ctx, cam, { path: a.path, progress: easeInOutCubic(seg(lt, 0.2 + a.delay, 1.9 + a.delay)), color: C.soviet, width: 30 }, t);
  const flash = 1 - easeOutCubic(seg(lt, 0, 0.25));
  blackOverlay(ctx, 0);
  if (flash > 0) { ctx.fillStyle = `rgba(230,224,210,${0.45 * flash})`; ctx.fillRect(0, 0, 1080, 1920); }
  return { dateCard: { y: 400 } };
}

module.exports = { render };
