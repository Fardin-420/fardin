/**
 * export_srt.js — write out/subtitles.srt using exactly the chunks/timings burned into the video.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const { buildSubtitles, toSrt } = require('../src/lib/text');

const ROOT = path.resolve(__dirname, '..');
const tl = JSON.parse(fs.readFileSync(path.join(ROOT, 'build', 'timeline.json'), 'utf8'));
const subs = buildSubtitles(tl);
fs.mkdirSync(path.join(ROOT, 'out'), { recursive: true });
fs.writeFileSync(path.join(ROOT, 'out', 'subtitles.srt'), toSrt(subs));
console.log(`wrote out/subtitles.srt (${subs.length} cues)`);
