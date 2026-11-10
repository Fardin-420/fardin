/**
 * SCENE 2 — INVASION OF POLAND (September 1, 1939).
 * Map fades up; Germany fills steel gray; arrows sweep into Poland as the narrator says
 * "invades"; Poland fills progressively from the west; Britain and France pulse blue on
 * "Britain ... France".
 */
'use strict';

const { drawMap, GROUPS, fillGroup } = require('../lib/map');
const { drawArrow, drawLabel, drawMarker } = require('../lib/draw');
const { seg, easeInOutCubic, easeOutCubic } = require('../lib/easing');
const { travelCam, blackOverlay, baseDist } = require('./common');

const ARROWS = [
  { path: [[14.6, 53.7], [18.2, 53.4], [20.6, 52.5]], delay: 0.0 },   // Pomerania -> Warsaw
  { path: [[20.6, 54.3], [20.9, 53.4], [21.1, 52.6]], delay: 0.25 },  // East Prussia -> south
  { path: [[15.8, 51.3], [18.6, 51.9], [20.5, 52.1]], delay: 0.1 },   // Silesia -> Warsaw
  { path: [[17.6, 50.4], [20.0, 50.1], [22.4, 50.7]], delay: 0.35 },  // Silesia -> Kraków / east
];

function render(ctx, s) {
  const { t, p, C } = s;
  const tInv = s.w('invades'), tTwo = s.w('two'), tBrit = s.w('britain'), tFra = s.w('france');
  const cam = travelCam(p, { lon: 13.5, lat: 51.9, zoom: 1.95 }, { lon: 10.2, lat: 51.2, zoom: 1.95 }, { travelStart: 0.45, travelEnd: 1 });

  const fills = {};
  fillGroup(fills, GROUPS.germany1939, C.axis, easeOutCubic(seg(t, 0.5, 1.6)));
  // Poland: sweep from the west, then solid
  const sweepK = easeInOutCubic(seg(t, tInv - 0.1, tTwo + 0.5));
  const polR = baseDist([14.5, 52.2], [24.2, 50.8]) * 1.15;
  if (sweepK >= 1) fillGroup(fills, GROUPS.poland, C.axis, 0.92);
  // Britain & France: pulse blue as they declare war
  const pulse = (t0) => {
    const k = seg(t, t0 - 0.1, t0 + 0.4);
    return k > 0 ? { amount: 0.8 * k, glow: k * (0.55 + 0.45 * Math.sin((t - t0) * 7)) } : null;
  };
  const pb = pulse(tBrit), pf = pulse(tFra);
  if (pb) fillGroup(fills, GROUPS.britain, C.allies, pb.amount, pb.glow);
  if (pf) fillGroup(fills, GROUPS.france, C.allies, pf.amount, pf.glow);

  drawMap(ctx, cam, fills, {
    colors: C,
    sweeps: sweepK > 0 && sweepK < 1 ? [{ names: GROUPS.poland, color: C.axis, origin: [14.5, 52.2], radius: polR * sweepK, soft: 70, alpha: 0.92, edge: 1 }] : [],
  });

  // labels
  drawLabel(ctx, cam, 'GERMANY', [10.4, 51.2], { alpha: seg(t, 1.2, 2.0) });
  drawLabel(ctx, cam, 'POLAND', [19.4, 52.1], { alpha: seg(t, tInv - 0.3, tInv + 0.4) * (1 - 0.5 * sweepK), dy: 70 });
  drawLabel(ctx, cam, 'BRITAIN', [-1.6, 52.7], { alpha: seg(t, tBrit, tBrit + 0.4) });
  drawLabel(ctx, cam, 'FRANCE', [2.4, 47.0], { alpha: seg(t, tFra, tFra + 0.4) });
  drawMarker(ctx, cam, [21.0, 52.23], { alpha: seg(t, tInv + 0.6, tInv + 1.0), time: t, color: '#d8d2c4', r: 7 });

  // arrows (Axis steel gray)
  for (const a of ARROWS) {
    const k = easeInOutCubic(seg(t, tInv - 0.25 + a.delay, tInv + 1.35 + a.delay));
    drawArrow(ctx, cam, { path: a.path, progress: k, color: C.axis, width: 24 }, t);
  }

  blackOverlay(ctx, 1 - easeOutCubic(seg(t, 0.0, 1.0))); // map fades up from darkness
  return {};
}

module.exports = { render };
