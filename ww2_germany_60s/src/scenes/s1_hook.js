/**
 * SCENE 1 — HOOK. Pure black -> grain fades in -> huge "1939" types on (one key-click per digit),
 * the documentary title appears, then the year cracks, glitches and splits on the sub-boom.
 */
'use strict';

const { clamp, seg, pushIn, easeOutCubic, easeInCubic, rgba } = require('../lib/easing');
const { rng, helpers } = require('../lib/prng');
const { spacedText } = require('../lib/draw');

const CX = 540, CY = 880;

// ---- crack geometry (seeded, generated once) ---------------------------------------------------
const crack = (() => {
  const r = helpers(rng(1939, 1));
  const main = [];
  let x = CX + 40, y = CY - 260;
  main.push([x, y]);
  for (let i = 0; i < 16; i++) { x += r.range(-26, 22); y += r.range(28, 40); main.push([x, y]); }
  const branches = [];
  for (let b = 0; b < 9; b++) {
    const k = r.int(2, main.length - 3);
    let [bx, by] = main[k];
    const dir = r.rand() < 0.5 ? -1 : 1;
    let ang = dir > 0 ? r.range(-0.6, 0.6) : Math.PI + r.range(-0.6, 0.6);
    const pts = [[bx, by]];
    const n = r.int(4, 9);
    for (let i = 0; i < n; i++) {
      ang += r.range(-0.45, 0.45);
      const len = r.range(18, 42);
      bx += Math.cos(ang) * len; by += Math.sin(ang) * len;
      pts.push([bx, by]);
    }
    branches.push({ k, pts, delay: r.range(0, 0.4) });
  }
  return { main, branches };
})();

function partial(ctx, pts, prog) {
  const n = (pts.length - 1) * clamp(prog);
  if (n <= 0) return;
  ctx.beginPath();
  ctx.moveTo(pts[0][0], pts[0][1]);
  const full = Math.floor(n);
  for (let i = 1; i <= full; i++) ctx.lineTo(pts[i][0], pts[i][1]);
  if (full < pts.length - 1) {
    const f = n - full, a = pts[full], b = pts[full + 1];
    ctx.lineTo(a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f);
  }
  ctx.stroke();
}

function drawYear(ctx, digits, alpha) {
  ctx.font = '700 400px Oswald';
  ctx.textBaseline = 'middle';
  ctx.textAlign = 'left';
  const full = '1939';
  const total = ctx.measureText(full).width + 18 * 3;
  let x = CX - total / 2;
  for (let i = 0; i < 4; i++) {
    const w = ctx.measureText(full[i]).width;
    const a = digits[i];
    if (a > 0) {
      ctx.save();
      ctx.shadowColor = rgba('#e8c170', 0.22 * a * alpha);
      ctx.shadowBlur = 50;
      ctx.fillStyle = rgba('#e2dccd', a * alpha);
      ctx.fillText(full[i], x, CY + (1 - a) * -24);
      ctx.restore();
    }
    x += w + 18;
  }
}

function render(ctx, s) {
  const { t, p, dur } = s;
  const keys = s.cues('typekey');
  const tGlitch = s.cue('glitch');
  const tBoom = s.cue('subboom');
  const crackStart = tGlitch - 0.75;

  ctx.fillStyle = '#0a0a0a';
  ctx.fillRect(0, 0, 1080, 1920);

  // faint warm light falloff behind the type (gives the black some depth)
  const glowA = 0.12 * seg(t, keys[0], keys[3] + 0.3);
  if (glowA > 0) {
    const g = ctx.createRadialGradient(CX, CY, 0, CX, CY, 700);
    g.addColorStop(0, `rgba(120,105,80,${glowA})`);
    g.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, 1080, 1920);
  }

  // ---- year layer -------------------------------------------------------------------------------
  const L = s.layer('year');
  const lc = L.ctx;
  lc.save();
  lc.translate(CX, CY);
  const z = pushIn(p);
  lc.scale(z, z);
  lc.translate(-CX, -CY);
  const digits = keys.map((k) => clamp((t - k) / 0.06));
  const yearAlpha = 1 - seg(t, tBoom + 0.05, dur - 0.05);
  drawYear(lc, digits, yearAlpha);
  // cracks (drawn into the type)
  const cp = seg(t, crackStart, tGlitch + 0.1);
  if (cp > 0) {
    lc.lineCap = 'round';
    lc.lineJoin = 'round';
    for (const [col, w, dx] of [['rgba(10,10,10,1)', 7, 0], ['rgba(235,228,214,0.45)', 1.5, 3]]) {
      lc.strokeStyle = col;
      lc.lineWidth = w;
      lc.save();
      lc.translate(dx, 0);
      partial(lc, crack.main, easeOutCubic(cp));
      for (const b of crack.branches) {
        const bp = seg(cp, b.k / crack.main.length + b.delay * 0.4, 1);
        lc.lineWidth = w * 0.6;
        partial(lc, b.pts, bp);
      }
      lc.restore();
    }
  }
  lc.restore();

  // ---- composite: split the year along the crack after the boom ---------------------------------
  const split = easeOutCubic(seg(t, tBoom - 0.05, dur));
  const sc = s.scale;
  const drawL = (dx, dy) => ctx.drawImage(L.canvas, 0, 0, L.canvas.width, L.canvas.height, dx, dy, 1080, 1920);
  if (split <= 0) {
    drawL(0, 0);
  } else {
    const leftPoly = (c) => {
      c.beginPath();
      c.moveTo(-50, -50);
      c.lineTo(crack.main[0][0], -50);
      for (const q of crack.main) c.lineTo(q[0], q[1]);
      c.lineTo(crack.main[crack.main.length - 1][0], 2000);
      c.lineTo(-50, 2000);
      c.closePath();
    };
    ctx.save(); leftPoly(ctx); ctx.clip(); drawL(-36 * split, 22 * split); ctx.restore();
    ctx.save(); leftPoly(ctx); ctx.rect(-50, -50, 1200, 2100); ctx.clip('evenodd'); drawL(30 * split, -14 * split); ctx.restore();
  }

  // ---- glitch: displaced slices + ghosting for a few frames ------------------------------------
  const gWin = (t >= tGlitch && t < tGlitch + 0.3) || (t >= tBoom && t < tBoom + 0.18);
  if (gWin) {
    const r = helpers(rng(1939, s.frame));
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    ctx.globalAlpha = 0.35;
    drawL(r.range(8, 22), 0);
    drawL(-r.range(8, 22), 0);
    ctx.restore();
    for (let k = 0; k < 7; k++) {
      const y = r.range(CY - 260, CY + 240), h = r.range(6, 40), dx = r.range(-60, 60);
      ctx.fillStyle = '#0a0a0a';
      ctx.fillRect(0, y, 1080, h);
      ctx.drawImage(L.canvas, 0, y * sc, L.canvas.width, h * sc, dx, y, 1080, h);
    }
  }

  // ---- title -------------------------------------------------------------------------------------
  const ta = easeOutCubic(seg(t, keys[3] + 0.35, keys[3] + 1.1)) * (1 - seg(t, tBoom - 0.1, tBoom + 0.25));
  if (ta > 0) {
    ctx.save();
    ctx.globalAlpha = ta;
    ctx.textBaseline = 'middle';
    ctx.font = '500 50px Oswald';
    ctx.fillStyle = '#cfc8b8';
    spacedText(ctx, "GERMANY'S WAR", CX, CY + 300 + (1 - ta) * 14, 16);
    ctx.font = 'italic 400 38px "Libre Baskerville"';
    ctx.fillStyle = '#9d9686';
    ctx.textAlign = 'center';
    ctx.fillText('1939 – 1945', CX, CY + 370 + (1 - ta) * 14);
    ctx.fillStyle = 'rgba(207,200,184,0.5)';
    ctx.fillRect(CX - 140 * ta, CY + 255, 280 * ta, 2);
    ctx.restore();
  }

  // ---- sub-boom flash ----------------------------------------------------------------------------
  const flash = clamp(1 - (t - tBoom) / 0.25) * (t >= tBoom ? 1 : 0);
  if (flash > 0) {
    ctx.fillStyle = `rgba(230,220,200,${0.35 * easeInCubic(flash)})`;
    ctx.fillRect(0, 0, 1080, 1920);
  }

  const shake = t >= tBoom ? 16 * Math.exp(-(t - tBoom) * 7) : (gWin ? 4 : 0);
  // pure black first, then the grain fades in
  return { grain: seg(t, 0.05, 0.7), dust: seg(t, 0.4, 1.2), shake };
}

module.exports = { render };
