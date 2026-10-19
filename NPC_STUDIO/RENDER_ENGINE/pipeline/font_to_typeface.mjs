// Convert an OTF/TTF into three.js typeface JSON (ASCII only) for extruded 3D type.
//   node font_to_typeface.mjs <in.otf> <out.json>
import fs from 'node:fs';
import opentype from 'opentype.js';

const [, , src, dst] = process.argv;
const buf = fs.readFileSync(src);
const font = opentype.parse(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength));
const scale = 100000 / ((font.unitsPerEm || 2048) * 72);
const r = Math.round;
const glyphs = {};
for (let code = 32; code < 127; code++) {
  const ch = String.fromCharCode(code);
  const g = font.charToGlyph(ch);
  let o = '';
  for (const c of g.path.commands) {
    const type = c.type.toLowerCase() === 'c' ? 'b' : c.type.toLowerCase();
    o += type + ' ';
    if (c.x !== undefined) o += `${r(c.x * scale)} ${r(c.y * scale)} `;
    if (c.x1 !== undefined) o += `${r(c.x1 * scale)} ${r(c.y1 * scale)} `;
    if (c.x2 !== undefined) o += `${r(c.x2 * scale)} ${r(c.y2 * scale)} `;
  }
  const bb = g.getBoundingBox();
  glyphs[ch] = { ha: r(g.advanceWidth * scale), x_min: r(bb.x1 * scale), x_max: r(bb.x2 * scale), o };
}
fs.writeFileSync(dst, JSON.stringify({
  glyphs, familyName: font.getEnglishName('fullName'),
  ascender: r(font.ascender * scale), descender: r(font.descender * scale),
  underlinePosition: font.tables.post.underlinePosition, underlineThickness: font.tables.post.underlineThickness,
  boundingBox: { xMin: font.tables.head.xMin, xMax: font.tables.head.xMax, yMin: font.tables.head.yMin, yMax: font.tables.head.yMax },
  resolution: 1000,
}));
console.log('wrote', dst);
