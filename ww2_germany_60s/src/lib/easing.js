/**
 * easing.js — easing curves and small math helpers shared by every scene.
 */
'use strict';

const clamp = (x, a = 0, b = 1) => (x < a ? a : x > b ? b : x);
const lerp = (a, b, t) => a + (b - a) * t;
/** Map x from [a, b] to [0, 1], clamped. The workhorse for "this happens between 30% and 55%". */
const seg = (x, a, b) => clamp((x - a) / (b - a));
const smoothstep = (a, b, x) => { const t = seg(x, a, b); return t * t * (3 - 2 * t); };

const easeInOutCubic = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);
const easeInCubic = (t) => t * t * t;
const easeOutQuint = (t) => 1 - Math.pow(1 - t, 5);
const easeInOutSine = (t) => -(Math.cos(Math.PI * t) - 1) / 2;
const easeOutBack = (t) => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2); };

/** Attack/hold/release envelope: 0 before a, ramps to 1 by b, holds, falls to 0 between c and d. */
const envelope = (x, a, b, c, d) => (x <= a || x >= d ? 0 : x < b ? seg(x, a, b) : x <= c ? 1 : 1 - seg(x, c, d));

/** Push-in used by every scene: 1.0 -> 1.12 with easeInOutCubic over the scene. */
const pushIn = (p, amount = 0.12) => 1 + amount * easeInOutCubic(clamp(p));

/** Hex '#rrggbb' -> [r, g, b]. */
function hexToRgb(hex) {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}
/** Mix two hex colors -> css rgb() string. */
function mix(c1, c2, t, alpha = 1) {
  const a = hexToRgb(c1), b = hexToRgb(c2);
  const r = a.map((v, i) => Math.round(lerp(v, b[i], clamp(t))));
  return alpha >= 1 ? `rgb(${r[0]},${r[1]},${r[2]})` : `rgba(${r[0]},${r[1]},${r[2]},${alpha})`;
}
/** Hex color with alpha -> css rgba(). */
function rgba(hex, a) {
  const [r, g, b] = hexToRgb(hex);
  return `rgba(${r},${g},${b},${clamp(a)})`;
}

module.exports = { clamp, lerp, seg, smoothstep, envelope, pushIn, easeInOutCubic, easeOutCubic, easeInCubic,
  easeOutQuint, easeInOutSine, easeOutBack, hexToRgb, mix, rgba };
