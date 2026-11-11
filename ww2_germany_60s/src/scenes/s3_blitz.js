/**
 * SCENE 3 — BLITZKRIEG WEST (May–June 1940).
 * Fast arrows west through the Netherlands and Belgium into France; speed lines; camera pans west.
 * The Low Countries fill on "overrun"; France fills gray and lands with a metallic impact on "falls".
 */
'use strict';

const { drawMap, GROUPS, fillGroup } = require('../lib/map');
const { drawArrow, drawLabel } = require('../lib/draw');
const { drawSpeedLines } = require('../lib/particles');
const { seg, clamp, easeInOutCubic, easeOutCubic, envelope } = require('../lib/easing');
const { travelCam, territory, baseDist } = require('./common');

const ARROWS = [
  { path: [[7.1, 52.4], [6.0, 52.5], [4.9, 52.3]], at: 'lightning-fast', delay: -0.2, dur: 0.9 },    // Netherlands
  { path: [[6.9, 51.0], [5.6, 51.1], [4.3, 50.8]], at: 'lightning-fast', delay: 0.05, dur: 0.9 },    // Belgium
  { path: [[6.6, 49.9], [4.6, 49.6], [2.2, 50.3]], at: 'german', delay: 0, dur: 1.1 },        // Ardennes -> Channel
  { path: [[6.4, 49.3], [4.2, 48.9], [2.5, 48.5]], at: 'overrun', delay: 0, dur: 1.1 },       // -> Paris
  { path: [[2.6, 48.3], [1.6, 47.0], [-0.3, 46.3]], at: 'france', delay: -0.5, dur: 1.0 },    // -> south-west
];

function render(ctx, s) {
  const { t, p, C } = s;
  const tOver = s.w('overrun'), tEur = s.w('europe'), tFalls = s.cue('metal'); // impact cue = fill complete
  const cam = travelCam(p, { lon: 8.6, lat: 51.0, zoom: 2.45 }, { lon: 3.6, lat: 48.9, zoom: 2.45 }, { travelStart: 0.08, travelEnd: 0.92 });

  const fills = territory(1, C);
  fillGroup(fills, GROUPS.france, C.allies, 0.55);
  // Low Countries overrun
  const lowK = easeInOutCubic(seg(t, tOver - 0.4, tOver + 0.6));
  // France: sweep from the north-east, completing exactly on the impact cue
  const fraK = easeInOutCubic(seg(t, tEur - 0.2, tFalls));
  if (fraK >= 1) fillGroup(fills, GROUPS.france, C.axis, 0.92);
  if (lowK >= 1) fillGroup(fills, GROUPS.lowCountries, C.axis, 0.92);
  const sweeps = [];
  if (lowK > 0 && lowK < 1) sweeps.push({ names: GROUPS.lowCountries, color: C.axis, origin: [7.2, 51.4], radius: baseDist([7.2, 51.4], [2.4, 51.2]) * lowK, soft: 40, alpha: 0.92, edge: 1 });
  if (fraK > 0 && fraK < 1) sweeps.push({ names: GROUPS.france, color: C.axis, origin: [7.5, 49.6], radius: baseDist([7.5, 49.6], [-4.8, 43.0]) * fraK, soft: 90, alpha: 0.92, edge: 1 });

  drawMap(ctx, cam, fills, { colors: C, sweeps });

  // impact flash on France
  const imp = clamp(1 - (t - tFalls) / 0.45) * (t >= tFalls ? 1 : 0);
  if (imp > 0) {
    const [fx, fy] = cam.toScreen([2.4, 47.0]);
    const g = ctx.createRadialGradient(fx, fy, 0, fx, fy, 520);
    g.addColorStop(0, `rgba(235,228,214,${0.45 * imp})`);
    g.addColorStop(1, 'rgba(235,228,214,0)');
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, 1080, 1920);
    ctx.restore();
  }

  drawLabel(ctx, cam, 'GERMANY', [10.0, 51.0], { alpha: 1 - seg(p, 0.5, 0.7) });
  drawLabel(ctx, cam, 'BRITAIN', [-1.5, 52.6], { alpha: seg(t, 0.4, 1.0) });
  drawLabel(ctx, cam, 'FRANCE', [2.4, 47.0], { alpha: seg(t, tEur - 0.4, tEur + 0.2), size: 40 });

  // speed lines while the armour is moving (westward)
  drawSpeedLines(ctx, t, { alpha: envelope(t, s.w('lightning-fast') - 0.6, s.w('lightning-fast'), tFalls - 0.4, tFalls + 0.2) * 0.9, dir: -1 });

  for (const a of ARROWS) {
    const t0 = s.w(a.at) + a.delay;
    const k = easeOutCubic(seg(t, t0, t0 + a.dur));
    drawArrow(ctx, cam, { path: a.path, progress: k, color: C.axis, width: 30, head: 56 }, t);
  }
  const shake = t >= tFalls ? 10 * Math.exp(-(t - tFalls) * 8) : 0;
  return { shake };
}

module.exports = { render };
