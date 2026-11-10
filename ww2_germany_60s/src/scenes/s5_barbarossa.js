/**
 * SCENE 5 — OPERATION BARBAROSSA (June 22, 1941).
 * Camera swings east; Soviet territory glows red; three massive arrows (north / centre / south)
 * surge in on "invades" (synced with the drum hit) while a gray advance spreads behind them.
 * Snow begins to fall at the end.
 */
'use strict';

const { drawMap, GROUPS, fillGroup } = require('../lib/map');
const { drawArrow, drawLabel, drawMarker } = require('../lib/draw');
const { drawSnow } = require('../lib/particles');
const { seg, easeInOutCubic, easeOutCubic, clamp } = require('../lib/easing');
const { travelCam, territory, baseDist, desaturate } = require('./common');

const ARROWS = [
  { path: [[21.6, 55.1], [25.2, 57.6], [29.6, 59.5]], delay: 0.0 },   // Army Group North -> Leningrad
  { path: [[23.4, 52.7], [29.5, 54.2], [36.2, 55.5]], delay: 0.12 },  // Army Group Centre -> Moscow
  { path: [[23.6, 50.5], [29.5, 50.3], [35.5, 48.2]], delay: 0.24 },  // Army Group South -> Ukraine
];

function render(ctx, s) {
  const { t, p, C } = s;
  const tInv = s.cue('drum') + 0.1, tSov = s.w('soviet');
  const cam = travelCam(p, { lon: 13.0, lat: 51.4, zoom: 1.55 }, { lon: 31.0, lat: 53.6, zoom: 1.55 }, { travelStart: 0.0, travelEnd: 0.45 });

  const fills = territory(2, C);
  const red = easeOutCubic(seg(t, 0.4, 1.6));
  const glow = seg(t, tSov - 0.2, tSov + 0.3) * (1 - seg(t, tSov + 1.4, tSov + 2.4)) * (0.6 + 0.4 * Math.sin(t * 7));
  fillGroup(fills, GROUPS.ussr, C.soviet, 0.85 * red, glow);

  // gray advance behind the arrows (clipped to Soviet territory)
  const adv = easeInOutCubic(seg(t, tInv + 0.2, tInv + 3.6));
  const advR = baseDist([17, 52.5], [33.5, 52.5]) * adv;
  drawMap(ctx, cam, fills, {
    colors: C,
    sweeps: adv > 0 ? [{ names: GROUPS.ussr, color: C.axis, origin: [17, 52.5], radius: advR, soft: 140, alpha: 0.78, edge: 1 }] : [],
  });

  drawLabel(ctx, cam, 'SOVIET UNION', [41.5, 57.0], { alpha: seg(t, tSov - 0.2, tSov + 0.4), size: 42, spacing: 10 });
  drawLabel(ctx, cam, 'GERMANY', [10.2, 51.0], { alpha: 1 - seg(p, 0.15, 0.35) });
  drawMarker(ctx, cam, [37.62, 55.75], { alpha: seg(t, tInv + 1.5, tInv + 2.0), time: t, r: 7 });
  drawLabel(ctx, cam, 'MOSCOW', [37.62, 55.75], { alpha: seg(t, tInv + 1.5, tInv + 2.0), size: 26, dy: -38 });

  for (const a of ARROWS) {
    const k = easeInOutCubic(seg(t, tInv + a.delay, tInv + 2.9 + a.delay));
    drawArrow(ctx, cam, { path: a.path, progress: k, color: C.axis, width: 40, head: 72 }, t);
  }

  // cold creeping in: snow begins, palette drains
  const cold = seg(p, 0.76, 1);
  desaturate(ctx, cold * 0.5);
  if (cold > 0) {
    ctx.fillStyle = `rgba(150,165,180,${0.07 * cold})`;
    ctx.fillRect(0, 0, 1080, 1920);
  }
  drawSnow(ctx, s.time, { amount: clamp(cold * 0.45), wind: -90, alpha: cold });
  return {};
}

module.exports = { render };
