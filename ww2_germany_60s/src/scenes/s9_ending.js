/**
 * SCENE 9 — ENDING (May 8, 1945). Near-silence: black, grain, a slow-fading date and a smaller line
 * about the human cost, then a comment prompt. In the last LOOP_SEC the frame dissolves into the
 * exact opening composition (s1_hook.drawOpening), so the final frame matches frame 0 and the
 * video loops seamlessly on replay.
 */
'use strict';

const { seg, pushIn, easeInOutSine, easeOutCubic } = require('../lib/easing');
const { spacedText, wrapLines } = require('../lib/text');
const { drawOpening } = require('./s1_hook');

const LOOP_SEC = 0.5; // dissolve back into frame 0

function render(ctx, s) {
  const { t, p, dur } = s;
  ctx.fillStyle = '#080808';
  ctx.fillRect(0, 0, 1080, 1920);
  const z = pushIn(p, 0.12);
  ctx.save();
  ctx.translate(540, 880);
  ctx.scale(z, z);
  ctx.translate(-540, -880);
  ctx.textBaseline = 'middle';

  const a1 = easeInOutSine(seg(t, 0.15, 1.2));
  if (a1 > 0) {
    ctx.globalAlpha = a1;
    ctx.font = '700 128px Oswald';
    ctx.fillStyle = '#ddd6c6';
    spacedText(ctx, 'MAY 8, 1945', 540, 690, 10);
    ctx.fillStyle = 'rgba(221,214,198,0.45)';
    ctx.fillRect(540 - 170 * a1, 790, 340 * a1, 2);
  }
  const a2 = easeInOutSine(seg(t, s.w('world') - 0.9, s.w('world') + 0.4));
  if (a2 > 0) {
    ctx.globalAlpha = a2;
    ctx.font = 'italic 400 44px "Libre Baskerville"';
    ctx.fillStyle = '#b3ac9c';
    ctx.textAlign = 'center';
    const lines = wrapLines(ctx, 'An estimated 70–85 million lives lost worldwide.', 760);
    lines.forEach((l, i) => ctx.fillText(l, 540, 880 + i * 66));
  }
  ctx.restore();

  // comment prompt (after the stat line lands)
  const a3 = easeOutCubic(seg(t, s.w('world') + 0.2, s.w('world') + 0.6));
  if (a3 > 0) {
    ctx.save();
    ctx.globalAlpha = a3;
    ctx.textBaseline = 'middle';
    ctx.font = '700 50px Oswald';
    ctx.fillStyle = '#e8c170';
    spacedText(ctx, 'WHICH TURNING POINT', 540, 1075 + (1 - a3) * 16, 3);
    spacedText(ctx, 'MATTERED MOST?', 540, 1140 + (1 - a3) * 16, 3);
    ctx.font = '500 32px Oswald';
    ctx.fillStyle = 'rgba(216,210,196,0.8)';
    spacedText(ctx, 'TELL US IN THE COMMENTS', 540, 1200 + (1 - a3) * 16, 6);
    ctx.restore();
  }

  // loop: dissolve into the opening frame; at the last frame it IS the opening frame
  const loop = seg(t, dur - LOOP_SEC, dur - 1 / 30);
  if (loop > 0) {
    const L = s.layer('opening');
    drawOpening(L.ctx);
    ctx.save();
    ctx.globalAlpha = easeInOutSine(loop);
    ctx.drawImage(L.canvas, 0, 0, L.canvas.width, L.canvas.height, 0, 0, 1080, 1920);
    ctx.restore();
  }
  // film FX return to the opening's settings during the dissolve so the loop cut is invisible
  return { grain: 1, dust: 0.25 + 0.75 * loop, vignette: 1 };
}

module.exports = { render };
