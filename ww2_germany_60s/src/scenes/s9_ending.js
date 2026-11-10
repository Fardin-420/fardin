/**
 * SCENE 9 — ENDING (May 8, 1945). Near-silence: black, grain only, a single slow-fading date and a
 * smaller line about the human cost. The text block drifts in very slowly (never fully static).
 * The final 15 frames fade to black in render.js.
 */
'use strict';

const { seg, pushIn, easeInOutSine } = require('../lib/easing');
const { spacedText, wrapLines } = require('../lib/text');

function render(ctx, s) {
  const { t, p } = s;
  ctx.fillStyle = '#080808';
  ctx.fillRect(0, 0, 1080, 1920);
  const z = pushIn(p, 0.12);
  ctx.save();
  ctx.translate(540, 880);
  ctx.scale(z, z);
  ctx.translate(-540, -880);
  ctx.textBaseline = 'middle';

  const a1 = easeInOutSine(seg(t, 0.25, 1.9));
  if (a1 > 0) {
    ctx.globalAlpha = a1;
    ctx.font = '700 128px Oswald';
    ctx.fillStyle = '#ddd6c6';
    spacedText(ctx, 'MAY 8, 1945', 540, 800, 10);
    ctx.fillStyle = 'rgba(221,214,198,0.45)';
    ctx.fillRect(540 - 170 * a1, 900, 340 * a1, 2);
  }
  const a2 = easeInOutSine(seg(t, s.w('but') - 0.9, s.w('but') + 0.8));
  if (a2 > 0) {
    ctx.globalAlpha = a2;
    ctx.font = 'italic 400 44px "Libre Baskerville"';
    ctx.fillStyle = '#b3ac9c';
    ctx.textAlign = 'center';
    const lines = wrapLines(ctx, 'An estimated 70–85 million lives lost worldwide.', 760);
    lines.forEach((l, i) => ctx.fillText(l, 540, 990 + i * 66));
  }
  ctx.restore();
  // grain only (no dust/scratches) — "near-silence"
  return { grain: 1, dust: 0.25, vignette: 1 };
}

module.exports = { render };
