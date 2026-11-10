/**
 * fonts.js — bundle Oswald + Libre Baskerville from @fontsource and register them with node-canvas.
 *
 * @fontsource only ships WOFF/WOFF2, while node-canvas (Pango/FreeType) wants TTF/OTF. WOFF 1.0 is
 * just an sfnt with each table optionally zlib-compressed, so we rebuild a plain TTF in a few lines
 * with Node's built-in zlib (no extra dependency) and cache it in build/fonts/.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const { registerFont } = require('canvas');

const ROOT = path.resolve(__dirname, '..', '..');
const OUT = path.join(ROOT, 'build', 'fonts');

// family alias used in ctx.font  ->  fontsource file
const FONTS = [
  { family: 'Oswald', weight: '700', file: '@fontsource/oswald/files/oswald-latin-700-normal.woff' },
  { family: 'Oswald', weight: '500', file: '@fontsource/oswald/files/oswald-latin-500-normal.woff' },
  { family: 'Oswald', weight: '300', file: '@fontsource/oswald/files/oswald-latin-300-normal.woff' },
  { family: 'Libre Baskerville', weight: '400', file: '@fontsource/libre-baskerville/files/libre-baskerville-latin-400-normal.woff' },
  { family: 'Libre Baskerville', weight: '400', style: 'italic', file: '@fontsource/libre-baskerville/files/libre-baskerville-latin-400-italic.woff' },
  { family: 'Libre Baskerville', weight: '700', file: '@fontsource/libre-baskerville/files/libre-baskerville-latin-700-normal.woff' },
];

/** Convert a WOFF 1.0 buffer into an sfnt (TTF/OTF) buffer. */
function woffToSfnt(buf) {
  if (buf.toString('ascii', 0, 4) !== 'wOFF') throw new Error('not a WOFF 1.0 file');
  const flavor = buf.readUInt32BE(4);
  const numTables = buf.readUInt16BE(12);
  const tables = [];
  for (let i = 0; i < numTables; i++) {
    const o = 44 + i * 20;
    const tag = buf.readUInt32BE(o), offset = buf.readUInt32BE(o + 4), compLen = buf.readUInt32BE(o + 8);
    const origLen = buf.readUInt32BE(o + 12), checksum = buf.readUInt32BE(o + 16);
    const raw = buf.subarray(offset, offset + compLen);
    const data = compLen < origLen ? zlib.inflateSync(raw) : Buffer.from(raw);
    tables.push({ tag, checksum, data });
  }
  let pow = 1, log = 0;
  while (pow * 2 <= numTables) { pow *= 2; log++; }
  const header = Buffer.alloc(12 + 16 * numTables);
  header.writeUInt32BE(flavor, 0);
  header.writeUInt16BE(numTables, 4);
  header.writeUInt16BE(pow * 16, 6);
  header.writeUInt16BE(log, 8);
  header.writeUInt16BE(numTables * 16 - pow * 16, 10);
  const chunks = [header];
  let offset = header.length;
  tables.forEach((t, i) => {
    const r = 12 + i * 16;
    header.writeUInt32BE(t.tag, r);
    header.writeUInt32BE(t.checksum, r + 4);
    header.writeUInt32BE(offset, r + 8);
    header.writeUInt32BE(t.data.length, r + 12);
    const padded = Buffer.alloc((t.data.length + 3) & ~3);
    t.data.copy(padded);
    chunks.push(padded);
    offset += padded.length;
  });
  return Buffer.concat(chunks);
}

let registered = false;
function registerFonts() {
  if (registered) return;
  fs.mkdirSync(OUT, { recursive: true });
  for (const f of FONTS) {
    const src = require.resolve(f.file, { paths: [ROOT] });
    const dst = path.join(OUT, path.basename(src).replace(/\.woff$/, '.ttf'));
    if (!fs.existsSync(dst)) fs.writeFileSync(dst, woffToSfnt(fs.readFileSync(src)));
    registerFont(dst, { family: f.family, weight: f.weight, style: f.style || 'normal' });
  }
  registered = true;
}

module.exports = { registerFonts, woffToSfnt };
