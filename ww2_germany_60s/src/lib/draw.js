/**
 * draw.js — map annotations: animated campaign arrows, labels, city markers.
 * Everything is drawn in SCREEN space (after projecting through the camera) so stroke widths
 * stay constant while the camera zooms.
 */
'use strict';

const { clamp, rgba, easeOutCubic } = require('./easing');

/** Evaluate a quadratic/cubic bezier (array of [x,y] control points) at t. */
function bez(p, t) {
  if (p.length === 2) return [p[0][0] + (p[1][0] - p[0][0]) * t, p[0][1] + (p[1][1] - p[0][1]) * t];
  const q = [];
  for (let i = 0; i < p.length - 1; i++) q.push([p[i][0] + (p[i + 1][0] - p[i][0]) * t, p[i][1] + (p[i + 1][1] - p[i][1]) * t]);
  return bez(q, t);
}

/**
 * Animated campaign arrow.
 * @param cam    map Camera
 * @param a      { path: [[lon,lat], ...] (2 = auto-curved, 3 = quadratic, 4 = cubic), bend,
 *                 progress (0..1), color, width (px), head (px), alpha }
 *
 * The arrow GROWS along its path: a tapered ribbon whose length is `progress` of the full
 * curve, capped by an arrowhead, with an animated dash running down its spine.
 */
function drawArrow(ctx, cam, a, time = 0) {
  const prog = clamp(a.progress);
  if (prog <= 0.001) return;
  const qc = global.__QC__; // QC instrumentation (scripts/qc.js): count frames with a visible arrow
  if (qc && qc.cur && (a.alpha ?? 1) > 0.2 && qc.lastArrowFrame !== qc.cur.frame) {
    qc.lastArrowFrame = qc.cur.frame;
    qc.arrows[qc.cur.scene] = (qc.arrows[qc.cur.scene] || 0) + 1;
  }
  let pts = a.path.map((ll) => cam.toScreen(ll));
  if (pts.length === 2) { // auto control point: bend perpendicular to the chord
    const [p0, p1] = pts, mx = (p0[0] + p1[0]) / 2, my = (p0[1] + p1[1]) / 2;
    const dx = p1[0] - p0[0], dy = p1[1] - p0[1], b = a.bend ?? 0.18;
    pts = [p0, [mx - dy * b, my + dx * b], p1];
  }
  // sample + arc length
  const N = 72, S = [], L = [0];
  for (let i = 0; i <= N; i++) S.push(bez(pts, i / N));
  for (let i = 1; i <= N; i++) L.push(L[i - 1] + Math.hypot(S[i][0] - S[i - 1][0], S[i][1] - S[i - 1][1]));
  const total = L[N], target = total * prog;
  const w = a.width || 26, head = a.head || w * 1.9;
  const bodyLen = Math.max(0, target - head * 0.7);
  // collect body points up to bodyLen
  const body = [];
  for (let i = 0; i <= N; i++) {
    if (L[i] <= bodyLen) body.push([S[i][0], S[i][1], L[i]]);
    else {
      const k = (bodyLen - L[i - 1]) / Math.max(1e-6, L[i] - L[i - 1]);
      body.push([S[i - 1][0] + (S[i][0] - S[i - 1][0]) * k, S[i - 1][1] + (S[i][1] - S[i - 1][1]) * k, bodyLen]);
      break;
    }
  }
  // tip point and direction
  let ti = 0;
  while (ti < N && L[ti + 1] < target) ti++;
  const kk = (target - L[ti]) / Math.max(1e-6, L[ti + 1] - L[ti] || 1);
  const tip = [S[ti][0] + (S[Math.min(N, ti + 1)][0] - S[ti][0]) * kk, S[ti][1] + (S[Math.min(N, ti + 1)][1] - S[ti][1]) * kk];
  const back = body.length ? body[body.length - 1] : S[0];
  let dx = tip[0] - back[0], dy = tip[1] - back[1];
  const dl = Math.hypot(dx, dy) || 1; dx /= dl; dy /= dl;

  // ribbon outline (tapered: 45% width at the tail -> full width at the head)
  const left = [], right = [];
  for (let i = 0; i < body.length; i++) {
    const p = body[i], q = body[Math.min(body.length - 1, i + 1)], o = body[Math.max(0, i - 1)];
    let nx = -(q[1] - o[1]), ny = q[0] - o[0];
    const nl = Math.hypot(nx, ny) || 1; nx /= nl; ny /= nl;
    const ww = (w / 2) * (0.45 + 0.55 * (bodyLen > 0 ? p[2] / bodyLen : 1));
    left.push([p[0] + nx * ww, p[1] + ny * ww]);
    right.push([p[0] - nx * ww, p[1] - ny * ww]);
  }
  const hb = [tip[0] - dx * head, tip[1] - dy * head];
  const shape = (c) => {
    c.beginPath();
    if (left.length) { c.moveTo(left[0][0], left[0][1]); for (const p of left) c.lineTo(p[0], p[1]); }
    c.lineTo(hb[0] - dy * w * 1.15, hb[1] + dx * w * 1.15);
    c.lineTo(tip[0], tip[1]);
    c.lineTo(hb[0] + dy * w * 1.15, hb[1] - dx * w * 1.15);
    for (let i = right.length - 1; i >= 0; i--) c.lineTo(right[i][0], right[i][1]);
    c.closePath();
  };
  const alpha = a.alpha ?? 1;
  ctx.save();
  ctx.lineJoin = 'round';
  // shadow
  ctx.translate(4, 7);
  shape(ctx);
  ctx.fillStyle = `rgba(0,0,0,${0.45 * alpha})`;
  ctx.fill();
  ctx.translate(-4, -7);
  // cheap additive glow
  ctx.globalCompositeOperation = 'lighter';
  shape(ctx);
  ctx.strokeStyle = rgba(a.color, 0.12 * alpha); ctx.lineWidth = 18; ctx.stroke();
  ctx.strokeStyle = rgba(a.color, 0.2 * alpha); ctx.lineWidth = 8; ctx.stroke();
  ctx.globalCompositeOperation = 'source-over';
  // body: dark keyline first so arrows read over same-coloured territory
  shape(ctx);
  ctx.strokeStyle = `rgba(8,8,8,${0.85 * alpha})`; ctx.lineWidth = 7; ctx.stroke();
  ctx.fillStyle = rgba(a.color, 0.97 * alpha); ctx.fill();
  ctx.strokeStyle = rgba('#d8d2c4', 0.55 * alpha); ctx.lineWidth = 2; ctx.stroke();
  // moving dashes down the spine (motion cue)
  if (body.length > 2) {
    ctx.beginPath();
    ctx.moveTo(body[0][0], body[0][1]);
    for (const p of body) ctx.lineTo(p[0], p[1]);
    ctx.setLineDash([14, 22]);
    ctx.lineDashOffset = -time * 90;
    ctx.strokeStyle = rgba('#d8d2c4', 0.35 * alpha);
    ctx.lineWidth = 3;
    ctx.lineCap = 'round';
    ctx.stroke();
    ctx.setLineDash([]);
  }
  ctx.restore();
}

/** Text with manual letter-spacing, centered at x. */
function spacedText(ctx, text, x, y, spacing) {
  const chars = [...text];
  const widths = chars.map((c) => ctx.measureText(c).width);
  const total = widths.reduce((s, v) => s + v, 0) + spacing * (chars.length - 1);
  let cx = x - total / 2;
  const align = ctx.textAlign;
  ctx.textAlign = 'left';
  chars.forEach((c, i) => { ctx.fillText(c, cx, y); cx += widths[i] + spacing; });
  ctx.textAlign = align;
  return total;
}

/** Map label (e.g. "POLAND") at a lon/lat. */
function drawLabel(ctx, cam, text, lonlat, { size = 36, alpha = 1, color = '#d8d2c4', spacing = 6, weight = 500, dy = 0 } = {}) {
  if (alpha <= 0.01) return;
  let [x, y] = cam.toScreen(lonlat);
  ctx.save();
  ctx.font = `${weight} ${size}px Oswald`;
  ctx.textBaseline = 'middle';
  // keep labels inside the safe zone (x 24..1056, y 285+..1635-) even when their place is near an edge
  const half = ([...text].reduce((w, c) => w + ctx.measureText(c).width, 0) + spacing * (text.length - 1)) / 2;
  x = Math.min(1056 - half, Math.max(24 + half, x));
  y = Math.min(1635 - size - dy, Math.max(285 + size - dy, y));
  ctx.fillStyle = `rgba(0,0,0,${0.6 * alpha})`;
  spacedText(ctx, text, x + 2, y + dy + 3, spacing);
  ctx.fillStyle = rgba(color, 0.85 * alpha);
  spacedText(ctx, text, x, y + dy, spacing);
  ctx.restore();
}

/** City marker: dot + expanding ring pulse. */
function drawMarker(ctx, cam, lonlat, { alpha = 1, color = '#d8d2c4', time = 0, r = 9 } = {}) {
  if (alpha <= 0.01) return;
  const [x, y] = cam.toScreen(lonlat);
  ctx.save();
  for (let k = 0; k < 2; k++) {
    const ph = (time * 0.8 + k * 0.5) % 1;
    ctx.beginPath();
    ctx.arc(x, y, r + easeOutCubic(ph) * r * 4, 0, Math.PI * 2);
    ctx.strokeStyle = rgba(color, alpha * (1 - ph) * 0.6);
    ctx.lineWidth = 2.5;
    ctx.stroke();
  }
  ctx.beginPath();
  ctx.arc(x, y, r, 0, Math.PI * 2);
  ctx.fillStyle = rgba('#0d0d0d', alpha);
  ctx.fill();
  ctx.lineWidth = 3;
  ctx.strokeStyle = rgba(color, alpha);
  ctx.stroke();
  ctx.beginPath();
  ctx.arc(x, y, r * 0.4, 0, Math.PI * 2);
  ctx.fillStyle = rgba(color, alpha);
  ctx.fill();
  ctx.restore();
}

module.exports = { drawArrow, drawLabel, drawMarker, spacedText, bez };
