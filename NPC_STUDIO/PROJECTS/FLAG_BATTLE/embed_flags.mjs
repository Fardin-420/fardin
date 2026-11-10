#!/usr/bin/env node
// Embed the flag-icons 1x1 SVGs for the COUNTRIES listed in battle.html into its #flag-data block.
// flag-icons is MIT licensed (© 2013 Panayiotis Lipiridis) — https://github.com/lipis/flag-icons
import { readFileSync, writeFileSync, existsSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';
const HERE = dirname(fileURLToPath(import.meta.url));
const FILE = join(HERE, 'battle.html');
const FLAGS = join(HERE, 'node_modules/flag-icons/flags/1x1');
if (!existsSync(FLAGS)) { console.error('flag-icons missing: run `npm install` in', HERE); process.exit(1); }
let html = readFileSync(FILE, 'utf8');
const list = html.match(/const COUNTRIES = \[([\s\S]*?)\];/)[1];
const codes = [...list.matchAll(/\[\s*'[^']+'\s*,\s*'([a-z-]+)'\s*\]/g)].map(m => m[1]);
const data = {};
for (const c of codes) {
  const f = join(FLAGS, `${c}.svg`);
  if (!existsSync(f)) { console.error(`no flag-icons SVG for code "${c}"`); process.exit(1); }
  data[c] = readFileSync(f, 'utf8').trim();
}
const json = JSON.stringify(data).replace(/</g, '\\u003c');
const next = html.replace(/(<script id="flag-data" type="application\/json">)[\s\S]*?(<\/script>)/, (_, a, b) => a + json + b);
if (next !== html) { writeFileSync(FILE, next); console.log(`embedded ${codes.length} flags (${(json.length / 1024).toFixed(0)} KB)`); }
else console.log(`flags up to date (${codes.length})`);
