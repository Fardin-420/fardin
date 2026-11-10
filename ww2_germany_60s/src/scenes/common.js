/**
 * common.js — helpers shared by the map scenes.
 */
'use strict';

const { Camera, GROUPS, fillGroup, project } = require('../lib/map');
const { clamp, easeInOutCubic, pushIn, lerp } = require('../lib/easing');

/**
 * Camera that travels from `a` to `b` (eased over [0, travelEnd] of the scene) while the brief's
 * push-in (1.0 -> 1.12, easeInOutCubic over the whole scene) multiplies the zoom. Never static.
 */
function travelCam(p, a, b, { travelStart = 0, travelEnd = 1, ay = 940 } = {}) {
  const k = easeInOutCubic(clamp((p - travelStart) / (travelEnd - travelStart)));
  const zoom = a.zoom * Math.pow(b.zoom / a.zoom, k) * pushIn(p);
  return new Camera({ lon: lerp(a.lon, b.lon, k), lat: lerp(a.lat, b.lat, k), zoom, ay });
}

/**
 * Historical territory colours at the start of each chapter (colour = side, nothing else).
 * Stages are cumulative.
 */
function territory(stage, C) {
  const f = {};
  const occupied = 0.92;
  fillGroup(f, GROUPS.germany1939, C.axis, 1);
  if (stage >= 1) fillGroup(f, GROUPS.poland, C.axis, occupied);                        // Poland 1939
  if (stage >= 2) { fillGroup(f, GROUPS.lowCountries, C.axis, occupied); fillGroup(f, GROUPS.france, C.axis, occupied); } // 1940
  if (stage >= 1) fillGroup(f, GROUPS.britain, C.allies, 0.8);
  if (stage >= 3) fillGroup(f, GROUPS.ussr, C.soviet, 0.85);                            // 1941
  return f;
}

/** Base-space distance in px between two lon/lat points (for sizing sweeps). */
function baseDist(a, b) {
  const [x0, y0] = project(a), [x1, y1] = project(b);
  return Math.hypot(x1 - x0, y1 - y0);
}

/** Black overlay (fade from black). */
function blackOverlay(ctx, a) {
  if (a <= 0) return;
  ctx.fillStyle = `rgba(13,13,13,${clamp(a)})`;
  ctx.fillRect(-10, -10, 1100, 1940);
}

/** Global cold/desaturate tint (cairo HSL blend modes). */
function desaturate(ctx, amount) {
  if (amount <= 0) return;
  ctx.save();
  ctx.globalCompositeOperation = 'saturation';
  ctx.fillStyle = `rgba(128,128,128,${clamp(amount)})`;
  ctx.fillRect(-10, -10, 1100, 1940);
  ctx.restore();
}

module.exports = { travelCam, territory, baseDist, blackOverlay, desaturate };
