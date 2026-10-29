// NPC flat 2D explainer renderer.
//
// Every frame is a pure function of time: renderAt(t) rebuilds the whole SVG
// from the timeline (scene bounds, word times, named cues). render.mjs loads
// this page in headless Chromium, calls setup(timeline, geo) once, then
// renderAt(frame / fps) for each frame it captures.
'use strict';

const W = 1080, H = 1920, FLOOR = 1000, CAP_Y = 1300;
const C = {
  navy: '#0d1428', iran: '#F5A623', iranD: '#C9820F', afghan: '#4C82F0', afghanD: '#2F5FC4',
  gold: '#FFC83D', red: '#FF5247', cyan: '#5FE3F0', pink: '#FF6FAE', green: '#3DD68C',
  ivory: '#F6F1E7', skin: '#F1C29A', skinD: '#D29A72', ink: '#151A2B', mouth: '#7A1F2B',
};
const HL = { iran: C.iran, afghan: C.afghan, gold: C.gold, red: C.red, cyan: C.cyan, pink: C.pink, green: C.green };
const ZW = '‌';
const FA = {
  tomato: `گوجه${ZW}فرنگی`, roman: 'بادنجان رومی', potato: `سیب${ZW}زمینی`, kachalu: 'کچالو',
  car: 'ماشین', motar: 'موتر', ice: 'بستنی', shiryakh: 'شیریخ', maqbul: 'مقبول',
  khaste: 'خسته نباشی', mande: 'مانده نباشی', merci: 'مرسی', zinda: 'زنده باشی',
  befarmaid: 'بفرمایید', taarof: 'تعارف', shir: 'شیر', hafez: 'حافظ', rumi: 'مولانا', balkh: 'بلخ', konya: 'قونیه',
};

let TL = null, GEO = null, CUE = {};

// ───────────────────────── math ─────────────────────────
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const lerp = (a, b, k) => a + (b - a) * k;
const outCubic = (x) => 1 - Math.pow(1 - clamp(x), 3);
const inOut = (x) => { x = clamp(x); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
const outBack = (x, s = 1.9) => { x = clamp(x); return 1 + (s + 1) * Math.pow(x - 1, 3) + s * Math.pow(x - 1, 2); };
const prog = (t, a, d) => (a == null ? 0 : clamp((t - a) / d));
const pop = (t, a, d = 0.38) => (a == null || t < a ? 0 : outBack((t - a) / d));
const fade = (t, a, d = 0.25) => outCubic(prog(t, a, d));
const hash = (n) => { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
const f1 = (n) => +n.toFixed(2);

// ───────────────────────── svg helpers ─────────────────────────
const tf = (x, y, s = 1, r = 0) => `translate(${f1(x)} ${f1(y)})${r ? ` rotate(${f1(r)})` : ''}${s !== 1 ? ` scale(${f1(s)})` : ''}`;
const G = (transform, inner, op = 1) => (op <= 0.001 ? '' : `<g transform="${transform}"${op < 1 ? ` opacity="${f1(op)}"` : ''}>${inner}</g>`);
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const FONTS = { d: "InterD, sans-serif", m: "Mono, monospace", fa: "Fa, sans-serif" };
function T(x, y, str, o = {}) {
  const { size = 40, weight = 800, fill = '#fff', anchor = 'middle', fam = 'd', stroke = null, sw = 0, ls = 0, op = 1 } = o;
  return `<text x="${f1(x)}" y="${f1(y)}" font-family="${FONTS[fam]}" font-size="${size}" font-weight="${weight}" fill="${fill}" text-anchor="${anchor}" dominant-baseline="central"${ls ? ` letter-spacing="${ls}"` : ''}${stroke ? ` stroke="${stroke}" stroke-width="${sw}" paint-order="stroke" stroke-linejoin="round"` : ''}${op < 1 ? ` opacity="${f1(op)}"` : ''}>${esc(str)}</text>`;
}
const ctx = document.createElement('canvas').getContext('2d');
function measure(str, size, weight = 800, fam = 'd') {
  ctx.font = `${weight} ${size}px ${FONTS[fam]}`;
  return ctx.measureText(str).width;
}
const rrect = (x, y, w, h, r, fill, extra = '') => `<rect x="${f1(x)}" y="${f1(y)}" width="${f1(w)}" height="${f1(h)}" rx="${r}" fill="${fill}" ${extra}/>`;

// A label pill: Latin word, optional Persian script under it, coloured border.
function tag(x, y, latin, o = {}) {
  const { color = C.gold, fa = null, size = 46, sub = null, bg = '#121829', fg = '#fff', s = 1, op = 1 } = o;
  if (s <= 0.001) return '';
  const wl = measure(latin, size, 800);
  const wf = fa ? measure(fa, size * 0.62, 800, 'fa') : 0;
  const ws = sub ? measure(sub, size * 0.42, 500, 'm') : 0;
  const w = Math.max(wl, wf, ws) + 56;
  const h = size * 1.35 + (fa ? size * 0.85 : 0) + (sub ? size * 0.62 : 0);
  let inner = rrect(-w / 2, -h / 2, w, h, 22, bg, `stroke="${color}" stroke-width="5"`);
  let yy = -h / 2 + size * 0.72;
  inner += T(0, yy, latin, { size, fill: fg });
  if (fa) { yy += size * 0.82; inner += T(0, yy, fa, { size: size * 0.62, fill: color, fam: 'fa' }); }
  if (sub) { yy += size * (fa ? 0.66 : 0.78); inner += T(0, yy, sub, { size: size * 0.42, weight: 500, fill: '#aab2c5', fam: 'm' }); }
  return G(tf(x, y, s), `<g filter="url(#shadow)">${inner}</g>`, op);
}
// A small coloured pill (country / role labels).
function chipPill(x, y, label, color, s = 1, size = 34) {
  if (s <= 0.001) return '';
  const w = measure(label, size, 800) + 44;
  return G(tf(x, y, s), rrect(-w / 2, -size * 0.75, w, size * 1.5, size * 0.75, color) + T(0, 2, label, { size, fill: '#10142a' }));
}
// Speech bubble with a tail pointing at (tx, ty) relative to the bubble centre.
function bubble(x, y, text, o = {}) {
  const { tx = 0, ty = 90, s = 1, size = 44, fa = null, sub = null, fill = '#fff', fg = C.ink, accent = null } = o;
  if (s <= 0.001) return '';
  const wl = measure(text, size, 800);
  const wf = fa ? measure(fa, size * 0.7, 800, 'fa') : 0;
  const ws = sub ? measure(sub, size * 0.5, 500, 'm') : 0;
  const w = Math.max(wl, wf, ws) + 60;
  const h = size * 1.45 + (fa ? size * 0.9 : 0) + (sub ? size * 0.7 : 0);
  const bx = clamp(tx, -w / 2 + 40, w / 2 - 40);
  const edge = ty < 0 ? -h / 2 + 4 : h / 2 - 4;
  const tail = `<path d="M${bx - 22},${edge} L${tx},${ty} L${bx + 22},${edge} Z" fill="${fill}"/>`;
  let inner = rrect(-w / 2, -h / 2, w, h, 30, fill, accent ? `stroke="${accent}" stroke-width="5"` : '') + tail;
  let yy = -h / 2 + size * 0.75;
  inner += T(0, yy, text, { size, fill: fg });
  if (fa) { yy += size * 0.92; inner += T(0, yy, fa, { size: size * 0.7, fill: accent ?? '#555', fam: 'fa' }); }
  if (sub) { yy += size * 0.78; inner += T(0, yy, sub, { size: size * 0.5, weight: 500, fill: '#6b7287', fam: 'm' }); }
  return G(tf(x, y, s), `<g filter="url(#shadow)">${inner}</g>`);
}

// ───────────────────────── characters ─────────────────────────
const LOOKS = {
  iranian: { top: '#F4B23E', topD: '#D08A18', sleeve: '#F4B23E', shirt: '#F7F3EA', pants: '#1E2540', hair: '#4B2C1C' },
  afghan: { top: '#3E73DC', topD: '#2A56B0', sleeve: '#F3EEE2', shirt: '#F3EEE2', pants: '#1E2540', hair: '#2A1A12' },
  elder: { top: '#7E8796', topD: '#5F6878', sleeve: '#7E8796', shirt: '#F7F3EA', pants: '#3A4152', hair: '#D3D7DE' },
};
function blinkAt(t, seed) {
  const p = (t + seed * 1.7) % 3.3;
  return p < 0.13 ? Math.sin((p / 0.13) * Math.PI) : 0;
}
function talkAt(t, spans) {
  for (const [a, b] of spans) if (t >= a && t <= b) return 0.35 + 0.65 * Math.abs(Math.sin((t - a) * 17));
  return 0;
}
function star(x, y, r, fill, rot = 0) {
  let d = '';
  for (let i = 0; i < 10; i++) {
    const a = (i / 10) * Math.PI * 2 - Math.PI / 2 + rot;
    const rr = i % 2 ? r * 0.45 : r;
    d += `${i ? 'L' : 'M'}${f1(x + Math.cos(a) * rr)},${f1(y + Math.sin(a) * rr)}`;
  }
  return `<path d="${d}Z" fill="${fill}"/>`;
}
function arm(side, a, color) {
  const sx = side * 70, sy = -318, L = 150;
  const r = (a * Math.PI) / 180;
  const ex = sx + side * Math.sin(r) * L, ey = sy + Math.cos(r) * L;
  return `<line x1="${sx}" y1="${sy}" x2="${f1(ex)}" y2="${f1(ey)}" stroke="${color}" stroke-width="32" stroke-linecap="round"/>` +
    `<circle cx="${f1(ex + side * Math.sin(r) * 8)}" cy="${f1(ey + Math.cos(r) * 8)}" r="17" fill="${C.skin}"/>`;
}
// kind: iranian | afghan | elder.  Feet at (x, y).  armL / armR in degrees: 0 down, 90 sideways, 170 up.
function person(kind, o) {
  const { x, y, s = 1, armL = 8, armR = 8, talk = 0, blink = 0, look = 0, mood = 'neutral', bob = 0, tilt = 0, t = 0, op = 1 } = o;
  const L = LOOKS[kind];
  let g = '';
  // legs + shoes
  g += rrect(-52, -180, 40, 168, 14, L.pants) + rrect(12, -180, 40, 168, 14, L.pants);
  g += `<ellipse cx="-36" cy="-10" rx="36" ry="15" fill="#141726"/><ellipse cx="36" cy="-10" rx="36" ry="15" fill="#141726"/>`;
  // torso
  if (kind === 'afghan') {
    g += `<path d="M-74,-300 Q-78,-334 -48,-338 L48,-338 Q78,-334 74,-300 L86,-130 Q0,-118 -86,-130 Z" fill="${L.shirt}"/>`;
    g += `<path d="M-76,-300 Q-80,-334 -48,-338 L-16,-338 L-10,-170 L-72,-176 Z" fill="${L.top}"/>`;
    g += `<path d="M76,-300 Q80,-334 48,-338 L16,-338 L10,-170 L72,-176 Z" fill="${L.top}"/>`;
    for (let i = 0; i < 7; i++) {
      const yy = -326 + i * 23;
      g += `<circle cx="-22" cy="${yy}" r="4.5" fill="${C.gold}"/><circle cx="22" cy="${yy}" r="4.5" fill="${C.gold}"/>`;
    }
    g += `<path d="M-60,-250 q10,-14 20,0 q10,14 20,0" stroke="${C.gold}" stroke-width="4" fill="none"/><path d="M20,-250 q10,-14 20,0 q10,14 20,0" stroke="${C.gold}" stroke-width="4" fill="none"/>`;
  } else {
    g += `<path d="M-78,-300 Q-82,-334 -50,-338 L50,-338 Q82,-334 78,-300 L72,-165 Q0,-152 -72,-165 Z" fill="${L.top}"/>`;
    g += `<path d="M-26,-338 L26,-338 L14,-190 L0,-176 L-14,-190 Z" fill="${L.shirt}"/>`;
    g += `<path d="M-26,-338 L-6,-262 L-36,-246 Z" fill="${L.topD}"/><path d="M26,-338 L6,-262 L36,-246 Z" fill="${L.topD}"/>`;
    if (kind === 'elder') g += `<path d="M-7,-330 L7,-330 L11,-232 L0,-218 L-11,-232 Z" fill="#C0392B"/>`;
    else g += `<circle cx="0" cy="-238" r="4" fill="${L.topD}"/><circle cx="0" cy="-206" r="4" fill="${L.topD}"/>`;
  }
  // neck + head
  g += rrect(-15, -358, 30, 30, 6, C.skinD);
  g += `<circle cx="-60" cy="-405" r="13" fill="${C.skin}"/><circle cx="60" cy="-405" r="13" fill="${C.skin}"/>`;
  g += `<ellipse cx="0" cy="-410" rx="60" ry="66" fill="${C.skin}"/>`;
  // hair
  if (kind === 'iranian') {
    g += `<path d="M-62,-418 Q-70,-488 -4,-486 Q58,-490 64,-428 Q56,-458 22,-458 Q-12,-474 -34,-446 Q-50,-444 -62,-418 Z" fill="${L.hair}"/>`;
    g += `<path d="M-30,-452 Q10,-500 52,-462 Q20,-470 -30,-452 Z" fill="${L.hair}"/>`;
  } else if (kind === 'afghan') {
    g += `<path d="M-61,-425 Q-62,-484 0,-482 Q62,-484 61,-425 Q50,-458 0,-456 Q-50,-458 -61,-425 Z" fill="${L.hair}"/>`;
    g += `<path d="M-60,-418 Q-64,-344 0,-328 Q64,-344 60,-418 Q54,-384 34,-378 Q0,-360 -34,-378 Q-54,-384 -60,-418 Z" fill="${L.hair}"/>`;
  } else {
    g += `<ellipse cx="-50" cy="-428" rx="16" ry="24" fill="${L.hair}"/><ellipse cx="50" cy="-428" rx="16" ry="24" fill="${L.hair}"/>`;
  }
  // eyes / brows
  const brow = mood === 'shock' ? -452 : mood === 'proud' ? -446 : -440;
  if (mood === 'dizzy') {
    for (const ex of [-22, 22]) g += `<path d="M${ex - 10},-420 L${ex + 10},-400 M${ex + 10},-420 L${ex - 10},-400" stroke="${C.ink}" stroke-width="5" stroke-linecap="round"/>`;
  } else {
    const ry = 14 * (1 - 0.92 * blink) * (mood === 'shock' ? 1.25 : 1);
    for (const ex of [-22, 22]) {
      g += `<ellipse cx="${ex}" cy="-410" rx="12.5" ry="${f1(ry)}" fill="#fff"/>`;
      if (blink < 0.6) g += `<circle cx="${f1(ex + look * 4.5)}" cy="-408" r="${mood === 'shock' ? 5 : 6.5}" fill="${C.ink}"/>`;
    }
  }
  g += `<path d="M-36,${brow} Q-22,${brow - 8} -10,${brow}" stroke="${kind === 'elder' ? '#9aa0aa' : '#2a1a12'}" stroke-width="6" fill="none" stroke-linecap="round"/>`;
  g += `<path d="M10,${brow} Q22,${brow - 8} 36,${brow}" stroke="${kind === 'elder' ? '#9aa0aa' : '#2a1a12'}" stroke-width="6" fill="none" stroke-linecap="round"/>`;
  if (kind === 'elder') g += `<circle cx="-22" cy="-410" r="20" fill="none" stroke="#333a48" stroke-width="5"/><circle cx="22" cy="-410" r="20" fill="none" stroke="#333a48" stroke-width="5"/><line x1="-2" y1="-412" x2="2" y2="-412" stroke="#333a48" stroke-width="5"/>`;
  g += `<path d="M-3,-398 Q6,-390 -2,-384" stroke="${C.skinD}" stroke-width="4" fill="none" stroke-linecap="round"/>`;
  g += `<circle cx="-38" cy="-383" r="10" fill="${C.pink}" opacity="${mood === 'blush' ? 0.7 : 0.28}"/><circle cx="38" cy="-383" r="10" fill="${C.pink}" opacity="${mood === 'blush' ? 0.7 : 0.28}"/>`;
  // mouth
  if (kind === 'afghan') g += `<path d="M-26,-376 Q0,-394 26,-376 Q0,-384 -26,-376 Z" fill="${L.hair}" stroke="${L.hair}" stroke-width="6"/>`;
  if (kind === 'elder') g += `<path d="M-24,-378 Q0,-392 24,-378 Q0,-384 -24,-378 Z" fill="#E8EAEE" stroke="#E8EAEE" stroke-width="5"/>`;
  if (talk > 0.01) g += `<ellipse cx="0" cy="-364" rx="13" ry="${f1(3 + 12 * talk)}" fill="${C.mouth}"/>`;
  else if (mood === 'shock' || mood === 'dizzy') g += `<ellipse cx="0" cy="-362" rx="10" ry="13" fill="${C.mouth}"/>`;
  else if (mood === 'happy' || mood === 'blush' || mood === 'proud') g += `<path d="M-20,-370 Q0,-344 20,-370 Z" fill="${C.mouth}"/><path d="M-15,-369 L15,-369 L13,-363 L-13,-363Z" fill="#fff"/>`;
  else g += `<path d="M-14,-366 Q0,-358 14,-366" stroke="${C.mouth}" stroke-width="5" fill="none" stroke-linecap="round"/>`;
  // arms on top
  g += arm(-1, armL, L.sleeve) + arm(1, armR, L.sleeve);
  if (mood === 'dizzy') for (let i = 0; i < 3; i++) {
    const a = t * 4 + (i * Math.PI * 2) / 3;
    g += star(Math.cos(a) * 70, -500 + Math.sin(a) * 16, 15, C.gold, t * 3);
  }
  return G(`${tf(x, y + bob, s, tilt)}`, g, op);
}
const idle = (t, seed) => Math.sin(t * 2.1 + seed) * 4;

// ───────────────────────── props ─────────────────────────
function tomato(x, y, s, r = 0) {
  if (s <= 0.001) return '';
  return G(tf(x, y, s, r), `<ellipse cx="0" cy="0" rx="62" ry="56" fill="#E8322B"/><ellipse cx="-22" cy="-20" rx="16" ry="10" fill="#fff" opacity=".45"/>` +
    star(0, -50, 30, '#2E9E4F') + `<rect x="-4" y="-76" width="8" height="18" rx="3" fill="#2E7D3F"/>`);
}
function potato(x, y, s, r = 0) {
  if (s <= 0.001) return '';
  let g = `<path d="M-70,-10 Q-66,-52 -10,-50 Q60,-58 72,-6 Q78,40 10,44 Q-74,46 -70,-10Z" fill="#C99A5B"/><path d="M-40,-36 Q0,-46 40,-38" stroke="#E2BB82" stroke-width="8" fill="none" stroke-linecap="round"/>`;
  for (const [a, b] of [[-30, -6], [18, -18], [40, 18], [-8, 24]]) g += `<circle cx="${a}" cy="${b}" r="5" fill="#9C7240"/>`;
  return G(tf(x, y, s, r), g);
}
function car(x, y, s) {
  if (s <= 0.001) return '';
  return G(tf(x, y, s), `<path d="M-120,10 L-112,-28 Q-104,-40 -84,-42 L-50,-42 L-24,-78 Q-16,-86 0,-86 L52,-86 Q66,-86 76,-74 L100,-42 L112,-38 Q124,-34 124,-20 L124,10 Z" fill="#E8463C"/>` +
    `<path d="M-38,-44 L-18,-74 L18,-74 L18,-44 Z M28,-44 L28,-74 L56,-74 Q62,-74 66,-68 L84,-44 Z" fill="#BFE6FF"/>` +
    `<circle cx="-70" cy="12" r="26" fill="#1B1F2E"/><circle cx="-70" cy="12" r="10" fill="#9aa3b5"/><circle cx="74" cy="12" r="26" fill="#1B1F2E"/><circle cx="74" cy="12" r="10" fill="#9aa3b5"/>` +
    `<rect x="108" y="-28" width="14" height="10" rx="3" fill="#FFE18A"/>`);
}
function iceCream(x, y, s, r = 0) {
  if (s <= 0.001) return '';
  let g = `<path d="M-46,-10 L46,-10 L0,110 Z" fill="#E0A458"/>`;
  for (let i = -2; i <= 2; i++) g += `<line x1="${-40 + (i + 2) * 18}" y1="-8" x2="${-6 + (i + 2) * 6}" y2="90" stroke="#B97A35" stroke-width="3"/>`;
  g += `<circle cx="-20" cy="-30" r="34" fill="#FF9EC7"/><circle cx="22" cy="-34" r="34" fill="#FFF3D6"/><circle cx="0" cy="-70" r="30" fill="#FFB6D5"/><circle cx="-10" cy="-80" r="8" fill="#fff" opacity=".6"/>`;
  return G(tf(x, y, s, r), g);
}
function teaGlass(x, y, s, t = 0) {
  if (s <= 0.001) return '';
  let g = `<ellipse cx="0" cy="34" rx="44" ry="10" fill="#d9d3c4"/><path d="M-24,-30 Q-30,0 -22,30 L22,30 Q30,0 24,-30 Z" fill="#fff" opacity=".35" stroke="#fff" stroke-width="3"/>` +
    `<path d="M-23,-12 Q-27,8 -21,28 L21,28 Q27,8 23,-12 Z" fill="#C65A1E" opacity=".9"/>`;
  for (let i = 0; i < 3; i++) g += `<path d="M${-12 + i * 12},-40 q-8,-14 0,-28 q8,-14 0,-28" stroke="#fff" stroke-width="4" fill="none" opacity="${f1(0.25 + 0.25 * Math.sin(t * 3 + i))}" transform="translate(0 ${f1(-((t * 20 + i * 9) % 18))})"/>`;
  return G(tf(x, y, s), g);
}
function plates(x, y, n, s = 1) {
  let g = '';
  for (let i = 0; i < n; i++) g += `<ellipse cx="0" cy="${-i * 16}" rx="70" ry="16" fill="#E9EEF5" stroke="#B9C3D3" stroke-width="3"/>`;
  return G(tf(x, y, s), g);
}
function pulao(x, y, s) {
  if (s <= 0.001) return '';
  let g = `<ellipse cx="0" cy="18" rx="120" ry="28" fill="#D7DEE9"/><path d="M-100,14 Q-60,-70 0,-74 Q60,-70 100,14 Z" fill="#F2C46B"/>`;
  for (let i = 0; i < 26; i++) g += `<rect x="${f1(-80 + hash(i) * 160)}" y="${f1(-50 + hash(i + 40) * 56)}" width="18" height="5" rx="2" fill="${i % 3 ? '#F08A24' : '#5A2D1A'}" transform="rotate(${f1(hash(i + 7) * 90 - 45)} ${f1(-80 + hash(i) * 160)} ${f1(-50 + hash(i + 40) * 56)})"/>`;
  g += `<ellipse cx="-30" cy="-58" rx="22" ry="14" fill="#8A4B2A"/>`;
  return G(tf(x, y, s), g);
}
function slipper(x, y, s, r) {
  if (s <= 0.001) return '';
  return G(tf(x, y, s, r), `<path d="M-30,-90 Q30,-100 34,-40 L36,60 Q34,96 0,98 Q-36,96 -38,60 L-40,-40 Q-38,-86 -30,-90Z" fill="#2E86DE"/>` +
    `<path d="M-40,-20 Q0,-56 38,-20 L38,6 Q0,-24 -40,6Z" fill="#1B5FA8"/><circle cx="0" cy="-60" r="6" fill="#1B5FA8"/>`);
}
function trophy(x, y, s, t = 0) {
  if (s <= 0.001) return '';
  let g = `<circle cx="0" cy="-10" r="110" fill="url(#glowGold)"/>`;
  g += `<path d="M-60,-80 L60,-80 Q58,-10 0,10 Q-58,-10 -60,-80Z" fill="${C.gold}"/><path d="M-60,-70 Q-100,-66 -88,-30 Q-80,-12 -50,-20" stroke="${C.gold}" stroke-width="10" fill="none"/><path d="M60,-70 Q100,-66 88,-30 Q80,-12 50,-20" stroke="${C.gold}" stroke-width="10" fill="none"/>` +
    `<rect x="-10" y="8" width="20" height="30" fill="#E0A82E"/><rect x="-42" y="36" width="84" height="20" rx="5" fill="#C28A1E"/>` + star(0, -46, 20, '#fff8dc', 0) +
    `<ellipse cx="-30" cy="-62" rx="8" ry="16" fill="#fff" opacity=".45"/>`;
  return G(tf(x, y + Math.sin(t * 3) * 6, s), g);
}
function clock(x, y, s, t) {
  if (s <= 0.001) return '';
  const a = t * 900, b = t * 75;
  return G(tf(x, y, s), `<circle r="70" fill="#fff" stroke="#2c3346" stroke-width="10"/>` +
    Array.from({ length: 12 }, (_, i) => `<line x1="0" y1="-56" x2="0" y2="-48" stroke="#2c3346" stroke-width="5" transform="rotate(${i * 30})"/>`).join('') +
    `<line x1="0" y1="0" x2="0" y2="-50" stroke="${C.red}" stroke-width="5" stroke-linecap="round" transform="rotate(${f1(a % 360)})"/>` +
    `<line x1="0" y1="0" x2="0" y2="-32" stroke="#2c3346" stroke-width="8" stroke-linecap="round" transform="rotate(${f1(b % 360)})"/><circle r="7" fill="#2c3346"/>`);
}
function lion(x, y, s) {
  if (s <= 0.001) return '';
  let g = '';
  for (let i = 0; i < 16; i++) g += `<circle cx="${f1(Math.cos(i / 16 * Math.PI * 2) * 74)}" cy="${f1(Math.sin(i / 16 * Math.PI * 2) * 74)}" r="30" fill="${i % 2 ? '#E0892B' : '#C96F1A'}"/>`;
  g += `<circle r="72" fill="#E59B3A"/><circle r="62" fill="#F2B95E"/>` +
    `<circle cx="-50" cy="-52" r="16" fill="#F2B95E"/><circle cx="50" cy="-52" r="16" fill="#F2B95E"/>` +
    `<circle cx="-22" cy="-12" r="8" fill="${C.ink}"/><circle cx="22" cy="-12" r="8" fill="${C.ink}"/>` +
    `<ellipse cx="0" cy="22" rx="26" ry="20" fill="#FCE3B8"/><path d="M-10,10 L10,10 L0,22Z" fill="#5a2d1a"/><path d="M0,22 Q-10,34 -18,28 M0,22 Q10,34 18,28" stroke="#5a2d1a" stroke-width="4" fill="none"/>`;
  return G(tf(x, y, s), g);
}
function milk(x, y, s) {
  if (s <= 0.001) return '';
  return G(tf(x, y, s), `<path d="M-50,-86 L50,-86 L42,86 Q0,96 -42,86 Z" fill="#eef4ff" opacity=".35" stroke="#fff" stroke-width="4"/>` +
    `<path d="M-46,-50 L46,-50 L41,82 Q0,92 -41,82 Z" fill="#fff"/><ellipse cx="0" cy="-50" rx="46" ry="8" fill="#f3f6fb"/><rect x="-36" y="-40" width="10" height="100" rx="5" fill="#dfe8f5"/>`);
}
function book(x, y, s, leftFa, rightFa, pR) {
  if (s <= 0.001) return '';
  let g = `<rect x="-260" y="-160" width="520" height="320" rx="16" fill="#2D4E9E"/>` +
    `<path d="M-244,-148 L-6,-140 L-6,148 L-244,140 Z" fill="#F4E9CF"/><path d="M244,-148 L6,-140 L6,148 L244,140 Z" fill="#F1E4C6"/>` +
    `<path d="M-200,-110 Q-125,-140 -50,-110" stroke="#2D4E9E" stroke-width="8" fill="none"/><path d="M50,-110 Q125,-140 200,-110" stroke="#2D4E9E" stroke-width="8" fill="none"/>`;
  for (let i = 0; i < 3; i++) g += `<line x1="-200" y1="${70 + i * 22}" x2="-50" y2="${70 + i * 22}" stroke="#C9B994" stroke-width="4"/><line x1="50" y1="${70 + i * 22}" x2="200" y2="${70 + i * 22}" stroke="#C9B994" stroke-width="4"/>`;
  g += T(-125, -10, leftFa, { size: 84, fill: '#2D4E9E', fam: 'fa' }) + T(-125, 44, 'Hafez', { size: 30, weight: 500, fill: '#6b5a3a', fam: 'm' });
  if (pR > 0) g += G(tf(125, -10, pR), T(0, 0, rightFa, { size: 84, fill: '#2D4E9E', fam: 'fa' }) + T(0, 54, 'Rumi', { size: 30, weight: 500, fill: '#6b5a3a', fam: 'm' }));
  return G(tf(x, y, s), g);
}
function dervish(x, y, s, t) {
  if (s <= 0.001) return '';
  const sw = Math.sin(t * 7) * 10;
  return G(tf(x, y, s), `<circle cx="0" cy="-170" r="120" fill="url(#glowWarm)"/>` +
    `<path d="M-90,0 Q${-60 + sw},-60 -20,-120 L20,-120 Q${60 + sw},-60 90,0 Q0,22 -90,0Z" fill="#F4F1EA"/><path d="M-60,-4 Q${-30 + sw},-60 -10,-118" stroke="#dcd6ca" stroke-width="5" fill="none"/><path d="M50,-2 Q${30 + sw},-60 10,-118" stroke="#dcd6ca" stroke-width="5" fill="none"/>` +
    `<rect x="-22" y="-200" width="44" height="86" rx="16" fill="#F4F1EA"/>` +
    `<line x1="-18" y1="-190" x2="-70" y2="-250" stroke="#F4F1EA" stroke-width="16" stroke-linecap="round"/><line x1="18" y1="-190" x2="62" y2="-160" stroke="#F4F1EA" stroke-width="16" stroke-linecap="round"/>` +
    `<circle cx="0" cy="-224" r="22" fill="${C.skin}"/><path d="M-14,-240 L-10,-310 Q0,-318 10,-310 L14,-240Z" fill="#9A6B3F"/>`);
}
function pin(x, y, s, color, label, fa) {
  if (s <= 0.001) return '';
  return G(tf(x, y, s), `<path d="M0,0 Q-30,-40 -30,-62 A30,30 0 1 1 30,-62 Q30,-40 0,0Z" fill="${color}"/><circle cx="0" cy="-62" r="11" fill="#fff"/>`) +
    (s > 0.5 ? chipPill(x, y + 40, `${label}`, '#fff', clamp(s), 30) : '');
}
function tomb(x, y, s) {
  if (s <= 0.001) return '';
  return G(tf(x, y, s), `<rect x="-60" y="-40" width="120" height="50" rx="6" fill="#E9DFC9"/><rect x="-22" y="-120" width="44" height="84" fill="#2FA36B"/>` +
    `<path d="M-26,-120 L0,-200 L26,-120Z" fill="#33B877"/><line x1="0" y1="-200" x2="0" y2="-222" stroke="${C.gold}" stroke-width="5"/><path d="M-36,-40 Q0,-70 36,-40Z" fill="#C9BCA0"/>`);
}

// ───────────────────────── backgrounds ─────────────────────────
const DEFS = `<defs>
<filter id="shadow" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="0" dy="8" stdDeviation="10" flood-color="#000" flood-opacity=".35"/></filter>
<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="9"/></filter>
<linearGradient id="bgNavy" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#16214a"/><stop offset=".55" stop-color="#0e1530"/><stop offset="1" stop-color="#090d1d"/></linearGradient>
<linearGradient id="spotO" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${C.iran}" stop-opacity=".42"/><stop offset="1" stop-color="${C.iran}" stop-opacity="0"/></linearGradient>
<linearGradient id="spotB" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${C.afghan}" stop-opacity=".45"/><stop offset="1" stop-color="${C.afghan}" stop-opacity="0"/></linearGradient>
<radialGradient id="glowGold"><stop offset="0" stop-color="${C.gold}" stop-opacity=".55"/><stop offset="1" stop-color="${C.gold}" stop-opacity="0"/></radialGradient>
<radialGradient id="glowWarm"><stop offset="0" stop-color="#FFE7B0" stop-opacity=".5"/><stop offset="1" stop-color="#FFE7B0" stop-opacity="0"/></radialGradient>
<radialGradient id="poolO"><stop offset="0" stop-color="${C.iran}" stop-opacity=".55"/><stop offset="1" stop-color="${C.iran}" stop-opacity="0"/></radialGradient>
<radialGradient id="poolB"><stop offset="0" stop-color="${C.afghan}" stop-opacity=".6"/><stop offset="1" stop-color="${C.afghan}" stop-opacity="0"/></radialGradient>
<radialGradient id="vignette" cx=".5" cy=".42" r=".75"><stop offset=".55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".55"/></radialGradient>
<linearGradient id="sunset" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2a1550"/><stop offset=".3" stop-color="#5b2468"/><stop offset=".45" stop-color="#b44a74"/><stop offset=".52" stop-color="#f0925a"/><stop offset=".53" stop-color="#24113a"/><stop offset="1" stop-color="#140a24"/></linearGradient>
<linearGradient id="doorLight" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFE3AE"/><stop offset="1" stop-color="#F2A65A"/></linearGradient>
<linearGradient id="floorBeam" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFD79A" stop-opacity=".55"/><stop offset="1" stop-color="#FFD79A" stop-opacity="0"/></linearGradient>
<pattern id="carpet" width="90" height="90" patternUnits="userSpaceOnUse"><rect width="90" height="90" fill="#7E1B2A"/><path d="M45,10 L80,45 L45,80 L10,45Z" fill="none" stroke="#B8862F" stroke-width="5"/><circle cx="45" cy="45" r="9" fill="#1F2D5C"/><circle cx="0" cy="0" r="6" fill="#B8862F"/><circle cx="90" cy="0" r="6" fill="#B8862F"/><circle cx="0" cy="90" r="6" fill="#B8862F"/><circle cx="90" cy="90" r="6" fill="#B8862F"/></pattern>
<pattern id="tiles" width="36" height="36" patternUnits="userSpaceOnUse"><rect width="36" height="36" fill="#1A8E8C"/><path d="M18,4 L32,18 L18,32 L4,18Z" fill="#7FD6CF"/><circle cx="18" cy="18" r="4" fill="#F6F1E7"/></pattern>
<pattern id="grid" width="60" height="60" patternUnits="userSpaceOnUse"><path d="M60,0 L0,0 0,60" fill="none" stroke="#8fa6ff" stroke-opacity=".07" stroke-width="2"/></pattern>
</defs>`;

function starsField(n, t, seed = 0, maxY = 950) {
  let g = '';
  for (let i = 0; i < n; i++) {
    const x = hash(i + seed) * W, y = hash(i * 3 + 11 + seed) * maxY;
    const a = 0.25 + 0.5 * (0.5 + 0.5 * Math.sin(t * 1.5 + i));
    g += `<circle cx="${f1(x)}" cy="${f1(y)}" r="${f1(1.2 + hash(i + 99) * 1.8)}" fill="#fff" opacity="${f1(a * 0.6)}"/>`;
  }
  return g;
}
function mapPaths(o) {
  // Iran + Afghanistan in the shared projection, placed behind the two characters.
  const { pIran = 1, pAfghan = 1, glowIran = 0.5, glowAfghan = 0.5, x = -560, y = 260, s = 1 } = o;
  const one = (d, color, p, gl) => p <= 0 ? '' :
    `<path d="${d}" fill="${color}" fill-opacity="${f1(0.13 * p + 0.12 * gl)}" stroke="${color}" stroke-width="${f1(5 / s)}" stroke-linejoin="round" pathLength="1" stroke-dasharray="1 0" opacity="${f1(clamp(p * 1.4))}"/>` +
    `<path d="${d}" fill="none" stroke="${color}" stroke-width="${f1(14 / s)}" opacity="${f1(0.35 * gl * p)}" filter="url(#glow)"/>`;
  return G(tf(x, y, s), one(GEO.countries.iran.d, C.iran, pIran, glowIran) + one(GEO.countries.afghanistan.d, C.afghan, pAfghan, glowAfghan));
}
function bgStage(t, o = {}) {
  const { maps = null, spots = 1 } = o;
  let g = `<rect width="${W}" height="${H}" fill="url(#bgNavy)"/>` + starsField(60, t);
  if (maps) g += mapPaths(maps);
  const sw = Math.sin(t * 0.8) * 20;
  g += `<path d="M${280 + sw},-20 L${360 + sw},-20 L${560},${FLOOR} L${100},${FLOOR} Z" fill="url(#spotO)" opacity="${f1(spots)}"/>`;
  g += `<path d="M${720 - sw},-20 L${800 - sw},-20 L${980},${FLOOR} L${520},${FLOOR} Z" fill="url(#spotB)" opacity="${f1(spots)}"/>`;
  g += `<rect y="${FLOOR}" width="${W}" height="${H - FLOOR}" fill="#0a0f22"/><rect y="${FLOOR}" width="${W}" height="3" fill="#2a3768"/>`;
  g += `<ellipse cx="330" cy="${FLOOR + 6}" rx="200" ry="34" fill="url(#poolO)" opacity="${f1(spots)}"/><ellipse cx="750" cy="${FLOOR + 6}" rx="200" ry="34" fill="url(#poolB)" opacity="${f1(spots)}"/>`;
  return g;
}
function bgGrid(t) {
  return `<rect width="${W}" height="${H}" fill="url(#bgNavy)"/><rect width="${W}" height="${H}" fill="url(#grid)"/>` + starsField(30, t, 7);
}
function bgGreet(t) {
  let g = `<rect width="${W}" height="${H}" fill="url(#sunset)"/>`;
  g += `<g opacity=".22">`;
  for (let i = 0; i < 14; i++) {
    const a = (i / 14) * Math.PI - Math.PI + t * 0.05;
    g += `<path d="M540,980 L${f1(540 + Math.cos(a - 0.04) * 1400)},${f1(980 + Math.sin(a - 0.04) * 1400)} L${f1(540 + Math.cos(a + 0.04) * 1400)},${f1(980 + Math.sin(a + 0.04) * 1400)}Z" fill="#FFE2B8"/>`;
  }
  g += `</g><circle cx="540" cy="960" r="150" fill="#FFD27A" opacity=".95"/>`;
  // skyline: domes and minarets
  const sky = '#2a1240';
  g += `<path d="M0,1000 L0,880 L60,880 L60,840 Q100,780 140,840 L140,880 L230,880 L230,770 L246,740 L262,770 L262,880 L330,880 Q330,790 400,770 Q470,790 470,880 L600,880 L600,860 L700,860 L700,780 L716,750 L732,780 L732,860 L800,860 Q810,800 860,790 Q910,800 920,860 L1000,860 L1000,820 L1080,820 L1080,1000Z" fill="${sky}"/>`;
  g += `<rect y="1000" width="${W}" height="${H - 1000}" fill="#1a0c2c"/><rect y="1000" width="${W}" height="3" fill="#4a2a6a"/>`;
  return g + starsField(25, t, 3, 500);
}
function bgTaarof(t) {
  let g = `<rect width="${W}" height="${FLOOR}" fill="#EADCC1"/>`;
  for (let y = 60; y < FLOOR; y += 64) g += `<rect y="${y}" width="${W}" height="4" fill="#DCCBAA"/>`;
  g += `<path d="M0,${FLOOR} L${W},${FLOOR} L${W},${H} L0,${H}Z" fill="#6a4e39"/><path d="M0,${FLOOR} L${W},${FLOOR} L${W},${FLOOR + 220} L0,${FLOOR + 220}Z" fill="#8C6B4F"/>`;
  g += `<path d="M445,${FLOOR} L635,${FLOOR} L800,${FLOOR + 380} L280,${FLOOR + 380}Z" fill="url(#floorBeam)"/>`;
  // tiled iwan doorway
  g += `<path d="M380,${FLOOR} L380,560 Q380,470 540,400 Q700,470 700,560 L700,${FLOOR}Z" fill="url(#tiles)" stroke="#0F6B69" stroke-width="10"/>`;
  g += `<path d="M435,${FLOOR} L435,600 Q435,530 540,480 Q645,530 645,600 L645,${FLOOR}Z" fill="url(#doorLight)"/>`;
  g += `<path d="M435,${FLOOR} L435,600 Q435,530 540,480 Q645,530 645,600 L645,${FLOOR}" fill="none" stroke="#F6F1E7" stroke-width="6"/>`;
  return g;
}
function bgHosp(t, sky) {
  let g = `<rect width="${W}" height="${FLOOR}" fill="#55301F"/><rect width="${W}" height="${FLOOR}" fill="url(#vignette)" opacity=".6"/>`;
  // window: sky colour and sun/moon are driven by `sky` (0 day → 1 night → 2 day)
  const night = Math.sin(clamp(sky / 2) * Math.PI);
  const skyCol = night > 0.5 ? '#1d2550' : '#8FD3F5';
  g += `<g transform="translate(220 470)"><path d="M-110,140 L-110,-40 Q-110,-130 0,-150 Q110,-130 110,-40 L110,140Z" fill="#3a2015"/>`;
  g += `<path d="M-92,124 L-92,-36 Q-92,-112 0,-130 Q92,-112 92,-36 L92,124Z" fill="${skyCol}"/>`;
  const ang = sky * Math.PI;
  g += `<circle cx="${f1(-Math.cos(ang) * 50)}" cy="${f1(40 - Math.abs(Math.sin(ang)) * 0 - 60 + (night > 0.5 ? 0 : 0))}" r="26" fill="${night > 0.5 ? '#F3F0DD' : '#FFC83D'}"/>`;
  g += `<line x1="0" y1="-130" x2="0" y2="124" stroke="#3a2015" stroke-width="10"/><line x1="-92" y1="20" x2="92" y2="20" stroke="#3a2015" stroke-width="10"/><rect x="-130" y="130" width="260" height="20" rx="6" fill="#3a2015"/></g>`;
  g += `<path d="M110,610 L330,${FLOOR} L110,${FLOOR}Z" fill="#FFE7B0" opacity=".06"/>`;
  g += `<rect y="${FLOOR - 30}" width="${W}" height="${H - FLOOR + 30}" fill="url(#carpet)"/><rect y="${FLOOR - 34}" width="${W}" height="18" fill="#B8862F"/>`;
  g += rrect(160, FLOOR - 92, 150, 62, 18, '#2A3E86') + rrect(770, FLOOR - 92, 150, 62, 18, '#A3263A');
  return g;
}

// ───────────────────────── scenes ─────────────────────────
// Each scene returns SVG for time t (seconds, absolute). c = cues.
const sceneFns = {
  intro(t, c, s) {
    const pI = prog(t, c.map_iran - 0.2, 0.9), pA = prog(t, c.map_afghan - 0.2, 0.9);
    let g = bgStage(t, { maps: { pIran: pI, pAfghan: pA, glowIran: pI, glowAfghan: pA } });
    const inI = outBack(prog(t, c.map_iran - 0.1, 0.5)), inA = outBack(prog(t, c.map_afghan - 0.1, 0.5));
    const shrug = inOut(prog(t, c.title, 0.35)) * 40;
    g += person('iranian', { x: 330, y: FLOOR + (1 - inI) * 700, t, bob: idle(t, 0), blink: blinkAt(t, 0), armL: 8 + shrug, armR: 8 + shrug, look: 1, mood: t > c.title ? 'shock' : 'happy' });
    g += person('afghan', { x: 750, y: FLOOR + (1 - inA) * 700, t, bob: idle(t, 1), blink: blinkAt(t, 1), armL: 8 + shrug, armR: 8 + shrug, look: -1, mood: t > c.title ? 'shock' : 'happy' });
    g += chipPill(330, 410, 'IRANIAN', C.iran, pop(t, c.map_iran + 0.25)) + chipPill(750, 410, 'AFGHAN', C.afghan, pop(t, c.map_afghan + 0.25));
    const ts = pop(t, c.title, 0.45);
    if (ts > 0) g += G(tf(540, 285, ts), T(0, -50, 'So what’s the', { size: 70, fill: '#fff', stroke: '#0a0e1c', sw: 10 }) + T(0, 40, 'difference?', { size: 112, weight: 900, fill: C.gold, stroke: '#0a0e1c', sw: 12 }));
    return g;
  },
  tomato(t, c) {
    let g = bgStage(t, { maps: { pIran: 1, pAfghan: 1, glowIran: 0.2, glowAfghan: 0.2 } });
    const roman = t >= c.label_roman;
    g += person('iranian', { x: 300, y: FLOOR, t, bob: idle(t, 0), blink: blinkAt(t, 0), look: 1, mood: roman ? 'shock' : 'neutral',
      armR: lerp(8, 70, inOut(prog(t, c.label_iran_tomato, 0.3)) * (1 - inOut(prog(t, c.label_roman, 0.25)))), talk: talkAt(t, [[c.label_iran_tomato, c.label_iran_tomato + 0.6]]) });
    g += person('afghan', { x: 780, y: FLOOR, t, bob: idle(t, 1), blink: blinkAt(t, 1), look: -1, mood: roman ? 'happy' : 'neutral',
      armL: lerp(8, 75, inOut(prog(t, c.label_roman, 0.3))), talk: talkAt(t, [[c.label_roman, c.label_roman + 0.9]]) });
    const ts = pop(t, c.tomato);
    g += tomato(540, 870 + Math.sin(t * 3) * 6, ts * 1.15, Math.sin(t * 2) * 6);
    g += tag(540, 720, 'tomato', { color: C.iran, fa: FA.tomato, s: pop(t, c.label_iran_tomato) * (1 - prog(t, c.label_roman, 0.12)) });
    g += tag(600, 680, 'Roman eggplant', { color: C.afghan, fa: FA.roman, sub: 'badenjan-e rumi', s: pop(t, c.label_roman) });
    if (roman) g += T(232, 470 - Math.abs(Math.sin((t - c.label_roman) * 6)) * 14, '?', { size: 120, weight: 900, fill: C.gold, stroke: '#0a0e1c', sw: 8, op: fade(t, c.label_roman) });
    return g;
  },
  words(t, c) {
    let g = bgStage(t, { maps: { pIran: 1, pAfghan: 1, glowIran: 0.15, glowAfghan: 0.15 } });
    const items = [
      { at: c.potato_iran, ai: c.potato_afghan, end: c.car_iran, ir: 'sib-zamini', af: 'kachalu', fi: FA.potato, fa: FA.kachalu, en: 'POTATO', draw: (x, y, s) => potato(x, y, s * 1.2, Math.sin(t * 2) * 5) },
      { at: c.car_iran, ai: c.car_afghan, end: c.ice_iran, ir: 'mashin', af: 'motar', fi: FA.car, fa: FA.motar, en: 'CAR', draw: (x, y, s) => car(x, y + 30, s * 1.1) },
      { at: c.ice_iran, ai: c.ice_afghan, end: 1e9, ir: 'bastani', af: 'shir-yakh', fi: FA.ice, fa: FA.shiryakh, en: 'ICE CREAM', draw: (x, y, s) => iceCream(x, y, s * 1.1, Math.sin(t * 2) * 6) },
    ];
    let spansI = [], spansA = [];
    for (const it of items) { spansI.push([it.at, it.at + 0.55]); spansA.push([it.ai, it.ai + 0.6]); }
    g += person('iranian', { x: 300, y: FLOOR, t, bob: idle(t, 0), blink: blinkAt(t, 0), look: 1, talk: talkAt(t, spansI), mood: 'happy' });
    g += person('afghan', { x: 780, y: FLOOR, t, bob: idle(t, 1), blink: blinkAt(t, 1), look: -1, talk: talkAt(t, spansA), mood: 'happy' });
    for (const it of items) {
      if (t < it.at - 0.1 || t > it.end + 0.25) continue;
      const out = 1 - prog(t, it.end - 0.05, 0.2);
      const sIn = pop(t, it.at - 0.1) * out;
      const slide = lerp(-40, 40, inOut(prog(t, it.ai - 0.1, 0.35)));
      g += it.draw(540 + slide, 880, sIn);
      g += G(tf(540, 990), T(0, 0, it.en, { size: 30, weight: 500, fill: '#aab2c5', fam: 'm', ls: 4 }), sIn);
      g += tag(300, 330, it.ir, { color: C.iran, fa: it.fi, s: pop(t, it.at) * out, size: 44 });
      g += tag(780, 330, it.af, { color: C.afghan, fa: it.fa, s: pop(t, it.ai) * out, size: 44 });
    }
    return g;
  },
  maqbul(t, c) {
    let g = bgStage(t, { maps: { pIran: 1, pAfghan: 1, glowIran: 0.15, glowAfghan: 0.15 } });
    const cardIn = pop(t, c.exam_card), cross = pop(t, c.exam, 0.3), gone = prog(t, c.heart, 0.35);
    const blush = t >= c.heart;
    g += person('iranian', { x: 300, y: FLOOR, t, bob: idle(t, 0), blink: blinkAt(t, 0), look: 1, mood: blush ? 'blush' : t > c.exam_card ? 'shock' : 'neutral', armL: blush ? 30 : 8, armR: blush ? 30 : 8 });
    g += person('afghan', { x: 780, y: FLOOR, t, bob: idle(t, 1), blink: blinkAt(t, 1), look: -1, mood: 'happy', armL: lerp(8, 70, inOut(prog(t, c.maqbul, 0.3))), talk: talkAt(t, [[c.maqbul, c.maqbul + 0.7]]) });
    g += bubble(720, 300, 'maqbul!', { tx: 40, ty: 120, s: pop(t, c.maqbul) * (1 - prog(t, c.heart + 0.8, 0.2)), fa: FA.maqbul, accent: C.afghan, size: 52 });
    if (cardIn > 0 && gone < 1) {
      let card = rrect(-150, -100, 300, 200, 18, '#fff') + rrect(-150, -100, 300, 54, 18, '#2c3346') + rrect(-150, -64, 300, 18, 0, '#2c3346') +
        T(0, -72, 'ENTRANCE EXAM', { size: 24, weight: 500, fill: '#fff', fam: 'm' }) + T(0, 30, 'PASSED ✓', { size: 50, weight: 900, fill: C.green });
      if (cross > 0) card += G(tf(60, 70, cross * 0.85, -14), rrect(-130, -42, 260, 84, 14, 'rgba(255,255,255,.92)', `stroke="${C.red}" stroke-width="10"`) + T(0, 0, 'NOT THAT', { size: 46, weight: 900, fill: C.red }));
      g += G(tf(300, 300 - gone * 900, cardIn, -4 + gone * 40), `<g filter="url(#shadow)">${card}</g>`);
    }
    if (blush) {
      for (let i = 0; i < 7; i++) {
        const k = ((t - c.heart) * 0.7 + i / 7) % 1;
        const hx = 300 + Math.sin(i * 2.3 + t * 2) * 130, hy = 560 - k * 360;
        g += G(tf(hx, hy, 0.6 + 0.5 * hash(i)), `<path d="M0,12 C-30,-10 -18,-34 0,-20 C18,-34 30,-10 0,12Z" fill="${C.pink}"/>`, 1 - k);
      }
      g += tag(540, 200, 'maqbul = good-looking', { color: C.pink, fa: FA.maqbul, s: pop(t, c.heart + 0.15), size: 50 });
    }
    return g;
  },
  greet(t, c) {
    let g = bgGreet(t);
    const iranTalk = [[c.tired_iran, c.tired_iran + 1.1], [c.merci, c.merci + 0.5]];
    const afTalk = [[c.tired_afghan, c.tired_afghan + 1.1], [c.zinda, c.zinda + 0.9]];
    const waveI = t >= c.tired_iran && t < c.tired_iran + 1.4 ? 150 + Math.sin(t * 12) * 15 : t >= c.merci && t < c.merci + 1 ? 130 : 30;
    const waveA = t >= c.tired_afghan && t < c.tired_afghan + 1.4 ? 150 + Math.sin(t * 12) * 15 : t >= c.zinda ? 140 + Math.sin(t * 10) * 12 : 30;
    g += person('iranian', { x: 300, y: FLOOR, t, bob: idle(t, 0), blink: blinkAt(t, 0), look: 1, mood: 'happy', armL: waveI, armR: 30, talk: talkAt(t, iranTalk) });
    g += teaGlass(388, 840, 0.8, t);
    g += person('afghan', { x: 780, y: FLOOR, t, bob: idle(t, 1), blink: blinkAt(t, 1), look: -1, mood: 'happy', armR: waveA, armL: 30, talk: talkAt(t, afTalk) });
    const i1 = t < c.merci, a1 = t < c.zinda;
    g += bubble(310, 330, i1 ? 'khaste nabashi' : 'merci', { tx: -10, ty: 140, s: i1 ? pop(t, c.tired_iran) : pop(t, c.merci), fa: i1 ? FA.khaste : FA.merci, sub: i1 ? '"don’t be tired"' : '"thanks"', accent: C.iran, size: 46 });
    g += bubble(770, 330, a1 ? 'mande nabashi' : 'zinda bashi!', { tx: 10, ty: 140, s: a1 ? pop(t, c.tired_afghan) : pop(t, c.zinda), fa: a1 ? FA.mande : FA.zinda, sub: a1 ? '"don’t be weary"' : '"may you live long!"', accent: C.afghan, size: 46 });
    return g;
  },
  taarof(t, c) {
    let g = bgTaarof(t);
    g += trophy(540, 250, pop(t, c.taarof_champ) * 1.1, t);
    if (t > c.taarof_champ) g += tag(540, 400, 'TAAROF', { color: C.gold, fa: FA.taarof, sub: 'polite insisting', s: pop(t, c.taarof_champ + 0.2) * (1 - prog(t, c.after1, 0.2)), size: 50 });
    // Both keep offering the door to each other, faster and faster.
    const ins = t >= c.insist ? 0.5 + 0.5 * Math.sin((t - c.insist) * 9) : 0;
    const iGest = t >= c.after1 ? (t >= c.after2 && t < c.insist ? 25 : 80) : 8;
    const eGest = t >= c.after2 ? (t >= c.insist ? 80 : 85) : 8;
    const lean = t >= c.insist ? 6 : 0;
    g += person('iranian', { x: 250, y: FLOOR, t, bob: idle(t, 0), blink: blinkAt(t, 0), look: 1, mood: t >= c.nobody ? 'neutral' : 'happy', armR: t >= c.insist ? lerp(40, 95, ins) : iGest, tilt: lean,
      talk: talkAt(t, [[c.after1, c.after1 + 0.5], [c.insist, c.insist + 0.6]]) });
    g += person('elder', { x: 830, y: FLOOR, t, bob: idle(t, 1), blink: blinkAt(t, 1), look: -1, mood: t >= c.nobody ? 'neutral' : 'happy', armL: t >= c.insist ? lerp(95, 40, ins) : eGest, tilt: -lean,
      talk: talkAt(t, [[c.after2, c.after2 + 0.8]]) });
    g += bubble(290, 290, 'After you.', { tx: -20, ty: 150, s: pop(t, c.after1) * (1 - prog(t, c.after2, 0.12)), fa: FA.befarmaid, accent: C.iran, size: 48 });
    g += bubble(770, 300, 'No, after YOU!', { tx: 40, ty: 150, s: pop(t, c.after2) * (1 - prog(t, c.clock - 0.2, 0.15)), accent: '#7E8796', size: 48 });
    g += bubble(300, 470, 'I insist!', { tx: -40, ty: 110, s: pop(t, c.insist) * (1 - prog(t, c.clock - 0.2, 0.15)), accent: C.iran, size: 48 });
    const cs = pop(t, c.clock);
    g += clock(540, 330, cs, t - (c.clock ?? 0));
    g += chipPill(540, 450, '+10 min', C.cyan, pop(t, c.clock + 0.2));
    if (t >= c.nobody) {
      // dust + "nobody passed" counter
      g += tag(540, 560, 'Nobody has gone through', { color: C.red, s: pop(t, c.nobody), size: 40 });
      for (let i = 0; i < 10; i++) g += `<circle cx="${f1(450 + hash(i) * 180)}" cy="${f1(620 + ((t * 30 + i * 37) % 360))}" r="3" fill="#fff" opacity=".35"/>`;
    }
    return g;
  },
  hospitality(t, c) {
    const sky = t >= c.nextday ? clamp((t - c.nextday) / 1.3) * 2 : 0;
    let g = bgHosp(t, sky);
    g += trophy(780, 230, pop(t, c.hosp_champ) * 1.05, t);
    const welcome = t >= c.hosp_champ ? 110 + Math.sin(t * 3) * 6 : 10;
    g += person('iranian', { x: 290, y: FLOOR + 10, t, bob: idle(t, 0), blink: blinkAt(t, 0), look: 1, mood: t >= c.plates ? 'shock' : 'happy', armL: 10, armR: t >= c.tea && t < c.plates ? 40 : 10 });
    g += person('afghan', { x: 780, y: FLOOR + 10, t, bob: idle(t, 1), blink: blinkAt(t, 1), look: -1, mood: 'happy', armL: welcome, armR: welcome });
    // sofreh with tea, then plates, then pulao
    g += `<path d="M150,1080 L930,1080 L990,1200 L90,1200Z" fill="#F4EAD5" stroke="#D8C9A8" stroke-width="5"/>`;
    g += `<path d="M180,1092 L900,1092 L944,1186 L136,1186Z" fill="none" stroke="#C0392B" stroke-width="4" stroke-dasharray="14 10"/>`;
    g += teaGlass(380, 1100, pop(t, c.tea) * 0.9, t);
    g += chipPill(380, 990, '5 min', C.cyan, pop(t, c.tea + 0.15) * (1 - prog(t, c.plates, 0.2)));
    const n = t < c.plates ? 0 : Math.min(3, 1 + Math.floor((t - c.plates) / 0.28));
    if (n) g += plates(830, 1150, n * 3, 0.8) + chipPill(830, 1000, `×${n}`, C.red, pop(t, c.plates));
    g += pulao(540, 1150, pop(t, c.pulao) * 0.95);
    if (t >= c.pulao) g += tag(540, 520, 'Kabuli pulao', { color: C.gold, fa: 'قابلی پلو', s: pop(t, c.pulao) * (1 - prog(t, c.nextday, 0.2)), size: 46 });
    g += tag(540, 520, 'Next day...', { color: C.cyan, sub: 'back for more', s: pop(t, c.nextday + 0.6), size: 50 });
    return g;
  },
  slipper(t, c) {
    let g = bgStage(t, { maps: { pIran: 1, pAfghan: 1, glowIran: 0.3, glowAfghan: 0.3 } });
    const hitA = c.slipper, hitI = c.slipper + 0.3;
    const sh = (a) => (t >= a && t < a + 0.3 ? Math.sin((t - a) * 80) * 18 * (1 - (t - a) / 0.3) : 0);
    g = G(tf(sh(hitA) + sh(hitI), 0), g);
    g += chipPill(330, 410, 'IRANIAN MOM', C.iran, pop(t, c.moms)) + chipPill(750, 410, 'AFGHAN MOM', C.afghan, pop(t, c.moms + 0.15));
    g += person('iranian', { x: 330, y: FLOOR, t, bob: idle(t, 0), blink: blinkAt(t, 0), look: 1, mood: t >= hitI ? 'dizzy' : t >= c.weapon ? 'shock' : 'neutral', tilt: t >= hitI ? Math.sin(t * 5) * 4 : 0 });
    g += person('afghan', { x: 750, y: FLOOR, t, bob: idle(t, 1), blink: blinkAt(t, 1), look: -1, mood: t >= hitA ? 'dizzy' : t >= c.weapon ? 'shock' : 'neutral', tilt: t >= hitA ? Math.sin(t * 5 + 1) * 4 : 0 });
    // two slippers fly in from off-screen and bounce off the heads
    const fly = (a, from, to, spin) => {
      const k = prog(t, a - 0.5, 0.5);
      if (k <= 0) return '';
      if (k < 1) return slipper(lerp(from[0], to[0], k), lerp(from[1], to[1], k) - Math.sin(k * Math.PI) * 160, 0.9, k * spin);
      const b = (t - a) * 1.2;
      return slipper(to[0] + b * 300 * Math.sign(to[0] - 540), to[1] - 200 * b + 900 * b * b, 0.9, spin + b * 400);
    };
    g += fly(hitA, [1200, 200], [750, 560], 720) + fly(hitI, [-120, 200], [330, 560], -720);
    const ts = pop(t, c.slipper, 0.4);
    if (ts > 0) g += G(tf(540, 250, ts, -4), T(0, 0, 'THE SLIPPER!', { size: 120, weight: 900, fill: C.red, stroke: '#0a0e1c', sw: 12 }) + T(0, 92, 'دمپایی', { size: 64, fill: '#fff', fam: 'fa', stroke: '#0a0e1c', sw: 8 }));
    return g;
  },
  shir(t, c) {
    let g = bgGrid(t);
    const st = c.shir_word, afg = t >= c.apart;
    g += tag(540, 320, 'Did you know?', { color: C.gold, s: pop(t, c.scene_shir + 0.2) * (1 - prog(t, st - 0.15, 0.2)), size: 64 });
    const phase2 = prog(t, c.older, 0.3);
    const ws = pop(t, st, 0.45) * (1 - phase2);
    if (ws > 0) {
      g += chipPill(540, 200, afg ? 'AFGHANISTAN' : 'IRAN', afg ? C.afghan : C.iran, ws);
      g += G(tf(540, 400, ws), T(0, 0, FA.shir, { size: 230, fill: '#fff', fam: 'fa', stroke: '#0a0e1c', sw: 10 }));
      const ls = pop(t, c.lion) * (1 - phase2), ms = pop(t, c.milk) * (1 - phase2);
      g += `<line x1="470" y1="500" x2="290" y2="640" stroke="#fff" stroke-width="4" opacity="${f1(ls * 0.6)}"/><line x1="610" y1="500" x2="790" y2="640" stroke="#fff" stroke-width="4" opacity="${f1(ms * 0.6)}"/>`;
      g += lion(270, 760, ls * 1.15) + milk(810, 760, ms * 1.05);
      const eq = afg ? `<text x="0" y="0" font-family="${FONTS.d}" font-size="120" font-weight="900" fill="${C.red}" text-anchor="middle" dominant-baseline="central">≠</text>` : T(0, 0, '=', { size: 120, weight: 900, fill: '#fff' });
      g += G(tf(540, 760, Math.max(ms, afg ? pop(t, c.apart) : 0)), eq);
      g += chipPill(270, 940, afg ? 'shēr' : 'shīr', afg ? C.afghan : C.iran, pop(t, afg ? c.sher : c.lion + 0.2) * (1 - phase2), 40);
      g += chipPill(810, 940, 'shīr', afg ? C.afghan : C.iran, pop(t, afg ? c.shir2 : c.milk + 0.2) * (1 - phase2), 40);
      if (afg) g += T(540, 1060, 'lion ≠ milk', { size: 44, weight: 700, fill: '#aab2c5', op: fade(t, c.apart) * (1 - phase2) });
    }
    const bs = pop(t, c.older, 0.45);
    g += chipPill(540, 330, 'THE OLDER PRONUNCIATION', C.gold, bs, 34);
    g += book(540, 700, bs * 1.6, FA.hafez, FA.rumi, pop(t, c.rumi_name));
    g += T(540, 1010, '14th-century Persian', { size: 34, weight: 500, fill: '#aab2c5', fam: 'm', op: fade(t, c.hafez) });
    return g;
  },
  rumi(t, c) {
    let g = bgGrid(t);
    // region map: Turkey + Iran + Afghanistan, fitted to the frame width
    const s = 0.64, mx = 20, my = 560;
    const P = (p) => [mx + p[0] * s, my + p[1] * s];
    const on = (a) => (t >= a ? 1 : 0);
    const active = t >= c.claim_turkey ? 'turkey' : t >= c.claim_afghan ? 'afghanistan' : t >= c.claim_iran ? 'iran' : null;
    const country = (name, color, at) => {
      const p = prog(t, c.dervish - 0.3 + at, 0.6);
      const lit = active === name ? 1 : 0;
      return `<path d="${GEO.countries[name].d}" fill="${color}" fill-opacity="${f1(0.12 + 0.3 * lit)}" stroke="${color}" stroke-width="${f1(4 / s)}" stroke-linejoin="round" opacity="${f1(p)}"/>` +
        (lit ? `<path d="${GEO.countries[name].d}" fill="none" stroke="${color}" stroke-width="${f1(16 / s)}" opacity=".5" filter="url(#glow)"/>` : '');
    };
    g += G(tf(mx, my, s), country('turkey', C.red, 0.2) + country('iran', C.iran, 0) + country('afghanistan', C.afghan, 0.1));
    const center = (n) => { const b = GEO.countries[n].bbox; return P([(b[0] + b[2]) / 2, (b[1] + b[3]) / 2]); };
    const target = active ? center(active) : [540, 700];
    const prev = t >= c.claim_turkey ? center('afghanistan') : t >= c.claim_afghan ? center('iran') : [540, 700];
    const at = t >= c.claim_turkey ? c.claim_turkey : t >= c.claim_afghan ? c.claim_afghan : c.claim_iran;
    const k = inOut(prog(t, at, 0.5));
    const dx = active ? lerp(prev[0], target[0], k) : 540, dy = active ? lerp(prev[1], target[1], k) - 60 : 640;
    g += dervish(dx, dy, pop(t, c.dervish) * 0.72, t);
    g += T(540, 220, 'Who does Rumi', { size: 66, fill: '#fff', op: fade(t, c.dervish) }) + T(540, 300, 'belong to?', { size: 80, weight: 900, fill: C.gold, op: fade(t, c.dervish + 0.3) });
    const bk = P(GEO.places.balkh), ko = P(GEO.places.konya);
    g += pin(bk[0], bk[1], pop(t, c.balkh), C.afghan, 'Balkh');
    g += pin(ko[0], ko[1], pop(t, c.tomb), C.red, 'Konya');
    g += tomb(ko[0] + 90, ko[1] - 20, pop(t, c.tomb) * 0.7);
    const b = (who, x, y, txt, col, a, e, tx) => bubble(x, y + 90, txt, { tx, ty: -130, s: pop(t, a) * (1 - prog(t, e, 0.15)), accent: col, size: 46 });
    g += b('iran', 560, 1000, 'He’s ours!', C.iran, c.claim_iran, c.claim_afghan, 0);
    g += b('afghan', 700, 1000, 'Born in Balkh. He’s ours!', C.afghan, c.claim_afghan, c.claim_turkey, 100);
    g += b('turkey', 380, 1000, 'His tomb is right here!', C.red, c.claim_turkey, 1e9, -120);
    g += chipPill(560, 1190, 'IRAN', C.iran, pop(t, c.claim_iran) * (1 - prog(t, c.claim_afghan, 0.15)));
    g += chipPill(700, 1190, 'AFGHANISTAN', C.afghan, pop(t, c.claim_afghan) * (1 - prog(t, c.claim_turkey, 0.15)));
    g += chipPill(380, 1190, 'TURKEY', C.red, pop(t, c.claim_turkey));
    return g;
  },
  outro(t, c) {
    let g = bgStage(t, { maps: { pIran: 1, pAfghan: 1, glowIran: 0.35, glowAfghan: 0.35 } });
    const happy = 'happy';
    const hug = inOut(prog(t, c.table, 0.4));
    g += person('iranian', { x: lerp(330, 410, hug), y: FLOOR, t, bob: idle(t, 0), blink: blinkAt(t, 0), look: 1, mood: happy, armR: lerp(8, 60, hug) });
    g += person('afghan', { x: lerp(750, 670, hug), y: FLOOR, t, bob: idle(t, 1), blink: blinkAt(t, 1), look: -1, mood: happy, armL: lerp(8, 60, hug) });
    const so = outCubic(prog(t, c.table, 0.5));
    if (so > 0) {
      g += G(`translate(540 1120) scale(${f1(so)} 1)`, `<path d="M-400,-50 L400,-50 L450,70 L-450,70Z" fill="#F4EAD5" stroke="#D8C9A8" stroke-width="5"/><path d="M-370,-38 L370,-38 L414,58 L-414,58Z" fill="none" stroke="#C0392B" stroke-width="4" stroke-dasharray="14 10"/>`);
      g += G(tf(380, 1110, so), `<ellipse rx="70" ry="22" fill="#D9A55B"/><ellipse rx="56" ry="14" fill="#E8BE7A"/>`);
      g += teaGlass(700, 1090, so * 0.8, t);
    }
    const ts = pop(t, c.tomato_end);
    g += tomato(540, 1090 - ts * 20, ts * 0.95, Math.sin(t * 3) * 6);
    // the two names keep swapping on the same tomato
    if (t >= c.tomato_end) {
      const flip = Math.floor((t - c.tomato_end) / 0.9) % 2;
      g += tag(540, 860, flip ? 'Roman eggplant' : 'tomato', { color: flip ? C.afghan : C.iran, fa: flip ? FA.roman : FA.tomato, s: pop(t, c.tomato_end + 0.1) * (0.92 + 0.08 * Math.abs(Math.cos(((t - c.tomato_end) / 0.9) * Math.PI))), size: 44 });
    }
    const end = fade(t, c.end + 0.15, 0.5);
    g += G(tf(540, 250, 0.9 + 0.1 * end), T(0, -50, 'One language.', { size: 84, weight: 900, fill: '#fff', stroke: '#0a0e1c', sw: 10 }) + T(0, 50, 'One table.', { size: 84, weight: 900, fill: C.gold, stroke: '#0a0e1c', sw: 10 }), fade(t, c.table, 0.4));
    return g;
  },
};

// ───────────────────────── captions + chrome ─────────────────────────
function captionAt(t) {
  for (const l of TL.lines) for (const ch of l.captions) if (t >= ch.start && t < ch.end) return { l, ch };
  return null;
}
function captions(t) {
  const hit = captionAt(t);
  if (!hit) return '';
  const { l, ch } = hit;
  const colorOf = (w) => {
    if (l.hl[w]) return HL[l.hl[w]];
    for (const [k, list] of Object.entries(TL.highlight)) if (list.includes(w)) return HL[k];
    return '#fff';
  };
  let size = 104;
  while (measure(ch.text, size, 900) > 960 && size > 60) size -= 4;
  const s = 0.82 + 0.18 * outBack(prog(t, ch.start, 0.16));
  const spans = ch.words.map((w, i) => `<tspan fill="${colorOf(w)}">${esc(w)}${i < ch.words.length - 1 ? ' ' : ''}</tspan>`).join('');
  return G(tf(540, CAP_Y, s), `<text x="0" y="0" font-family="${FONTS.d}" font-size="${size}" font-weight="900" text-anchor="middle" dominant-baseline="central" stroke="#0a0e1c" stroke-width="18" paint-order="stroke" stroke-linejoin="round">${spans}</text>`);
}
function chip(scene, t) {
  const label = scene.label;
  const w = measure(label, 30, 500, 'm') + 80;
  const a = fade(t, scene.start, 0.3);
  return G(tf(540, 110), rrect(-w / 2, -30, w, 60, 30, 'rgba(8,11,24,.72)', 'stroke="rgba(255,255,255,.14)" stroke-width="2"') +
    `<circle cx="${f1(-w / 2 + 30)}" cy="0" r="7" fill="${C.red}" opacity="${f1(0.6 + 0.4 * Math.sin(t * 5))}"/>` +
    T(16, 1, label, { size: 30, weight: 500, fill: '#d7dbe6', fam: 'm' }), a);
}

// ───────────────────────── frame ─────────────────────────
function renderAt(t) {
  const sc = TL.scenes.find((s) => t >= s.start && t < s.end) ?? TL.scenes[TL.scenes.length - 1];
  const lt = t - sc.start;
  // punch-in at every cut + slow push during the scene
  const zoom = (1 + 0.07 * (1 - outCubic(lt / 0.35))) * (1 + 0.025 * clamp(lt / (sc.end - sc.start)));
  let body = sceneFns[sc.id](t, CUE, sc);
  body = `<g transform="translate(540 760) scale(${f1(zoom)}) translate(-540 -760)">${body}</g>`;
  const flash = 1 - prog(t, sc.start, 0.16);
  let out = DEFS + body;
  out += `<rect width="${W}" height="${H}" fill="url(#vignette)"/>`;
  if (sc.start > 0 && flash > 0) out += `<rect width="${W}" height="${H}" fill="#fff" opacity="${f1(0.22 * flash)}"/>`;
  out += chip(sc, t) + captions(t);
  const endFade = prog(t, TL.duration - 0.6, 0.6);
  if (endFade > 0) out += `<rect width="${W}" height="${H}" fill="#05070f" opacity="${f1(endFade)}"/>`;
  document.getElementById('stage').innerHTML = out;
}

async function setup(tl, geo) {
  TL = tl; GEO = geo; CUE = tl.cues;
  await Promise.all(['900 40px InterD', '800 40px InterD', '700 40px InterD', '500 40px InterD', '500 40px Mono', '800 40px Fa'].map((f) => document.fonts.load(f, 'aبc')));
  await document.fonts.ready;
  return true;
}
window.setup = setup;
window.renderAt = renderAt;
