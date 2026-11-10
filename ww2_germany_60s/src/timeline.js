/**
 * timeline.js — SINGLE SOURCE OF TRUTH for the whole film.
 *
 * Everything that has a time in this project is defined here: scene windows,
 * narration text, date cards, transitions and every audio cue. Both the
 * renderer (Node) and the audio pipeline (Python) read from this file:
 *
 *   node src/timeline.js --dump      -> build/timeline_base.json   (nominal, pre-TTS)
 *   node src/timeline.js --resolve   -> build/timeline.json        (frame-accurate, post-TTS)
 *
 * TIMING MODEL
 * ------------
 * Each scene has a NOMINAL window (start/end in seconds, from the brief). After
 * narration is synthesized, `resolve()` measures every line and solves for the
 * real scene windows so that:
 *   1. the film is exactly TOTAL_FRAMES long (60.0 s @ 30 fps),
 *   2. every scene ends exactly NARRATION_TAIL (0.3 s) after its narration ends,
 *   3. no scene is shorter than its narration needs (narration is NEVER cut),
 *   4. windows stay as close to the nominal brief as the constraints allow.
 * Scene animations are driven by normalized progress (0..1), so when a window
 * stretches the animation simply slows down to fit.
 *
 * CUE TIMES
 * ---------
 * A cue's time can be given relative to its scene in one of three ways:
 *   { at: 1.2 }        seconds after scene start
 *   { frac: 0.5 }      fraction of the (resolved) scene duration
 *   { fromEnd: 0.4 }   seconds before scene end
 *   { narr: 'start'|'end', offset: s }  relative to the scene's narration line
 *   { word: 'invades', offset: s }      relative to when a narration word is SPOKEN (from TTS
 *                                        word boundaries) — keeps picture & sound on the voice
 */
'use strict';

const fs = require('fs');
const path = require('path');

const FPS = 30;
const WIDTH = 1080;
const HEIGHT = 1920;
const TOTAL_FRAMES = 1800;
const DURATION = TOTAL_FRAMES / FPS; // 60.0 s
const SEED = 1945;
const NARRATION_TAIL = 0.3; // scene end = narration end + 0.3 s
const MIN_LEAD = 0.2;       // narration never starts before this much of a scene has passed
const TRANSITION_FRAMES = 8;

// Safe zone: centered 1080x1350 box, also inside TikTok's UI-free band (top 150 / bottom 350).
const SAFE = { x: 0, y: 285, w: 1080, h: 1350, top: 285, bottom: 1570, left: 60, right: 1020 };

// Palette (archival, near-monochrome + one accent per side). No national/party symbols anywhere.
const COLORS = {
  black: '#0d0d0d',
  paper: '#d8d2c4',
  axis: '#6b6f74',
  allies: '#3d6fa8',
  soviet: '#a8322d',
  land: '#2a2826',
  sea: '#121416',
  border: '#4a4640',
  highlight: '#e8c170',
};

/*
 * SCENES — nominal windows come straight from the brief.
 * `transitionIn` is the transition played at the START of this scene
 * ('dip' = dip-to-black, 'burn' = film-burn flash). Every transition is
 * synced to a low boom cue generated automatically by resolve().
 */
const SCENES = [
  {
    id: 'hook', module: 's1_hook', start: 0.0, end: 3.0,
    narration: "In just six years, one nation's war would change the entire world.",
    dateCard: null,
    transitionIn: null,
    cues: [
      { sfx: 'heartbeat', at: 0.10, gain: -12 },
      { sfx: 'heartbeat', frac: 0.30, gain: -13 },
      // typewriter keys for the "1939" type-on (one per digit), matching s1_hook.js
      { sfx: 'typekey', frac: 0.16, gain: -14 },
      { sfx: 'typekey', frac: 0.22, gain: -14 },
      { sfx: 'typekey', frac: 0.28, gain: -14 },
      { sfx: 'typekey', frac: 0.34, gain: -13 },
      { sfx: 'glitch', frac: 0.70, gain: -18 },
      { sfx: 'subboom', fromEnd: 0.5, gain: -10 }, // brief: sub-boom at f75 of a 90-frame scene
    ],
    music: { intensity: 0.15 },
  },
  {
    id: 'poland', module: 's2_poland', start: 3.0, end: 10.0,
    narration: 'September first, 1939. Germany invades Poland. Two days later, Britain and France declare war.',
    dateCard: { text: 'SEPTEMBER 1, 1939', at: 0.6 },
    transitionIn: 'dip',
    cues: [
      { sfx: 'morse', at: 0.6, gain: -22, dur: 2.0 },
      { sfx: 'artillery', word: 'invades', offset: -0.25, gain: -15 },
      { sfx: 'artillery', word: 'invades', offset: 0.45, gain: -17 },
      { sfx: 'artillery', word: 'invades', offset: 1.15, gain: -16 },
      { sfx: 'radio', word: 'Britain', offset: -0.35, gain: -18 },
    ],
    music: { intensity: 0.35 },
  },
  {
    id: 'blitz', module: 's3_blitz', start: 10.0, end: 18.0,
    narration: 'With lightning-fast tactics, German forces overrun Western Europe. France falls in just six weeks.',
    dateCard: { text: 'JUNE 1940', at: 0.5 },
    transitionIn: 'burn',
    cues: [
      { sfx: 'engines', at: 0.2, gain: -17, dur: 5.5 },
      { sfx: 'riser', at: 0.5, gain: -20, dur: 4.5 },
      { sfx: 'metal', word: 'falls', offset: 0.12, gain: -14 }, // France fill completes (see s3_blitz.js)
    ],
    music: { intensity: 0.55 },
  },
  {
    id: 'britain', module: 's4_britain', start: 18.0, end: 25.0,
    narration: 'But Britain holds out, fighting for survival in the skies.',
    dateCard: { text: '1940', at: 0.5 },
    transitionIn: 'dip',
    cues: [
      { sfx: 'siren', at: 0.1, gain: -20, dur: 4.5 },
      { sfx: 'flyby', frac: 0.22, gain: -15, dur: 3.0 },
      { sfx: 'flak', frac: 0.40, gain: -16 },
      { sfx: 'flak', frac: 0.47, gain: -18 },
      { sfx: 'flak', frac: 0.58, gain: -16 },
      { sfx: 'flyby', frac: 0.55, gain: -17, dur: 2.6, reverse: true },
      { sfx: 'flak', frac: 0.72, gain: -18 },
    ],
    music: { intensity: 0.4 },
  },
  {
    id: 'barbarossa', module: 's5_barbarossa', start: 25.0, end: 34.0,
    narration: 'June 1941. Germany invades the Soviet Union, the largest invasion in history.',
    dateCard: { text: 'JUNE 22, 1941', at: 0.6 },
    transitionIn: 'burn',
    cues: [
      { sfx: 'drum', word: 'invades', offset: -0.1, gain: -9 },   // arrows launch
      { sfx: 'rumble', word: 'invades', offset: -0.1, gain: -15, dur: 4.5 },
      { sfx: 'wind', frac: 0.78, gain: -22, dur: 2.5 },
    ],
    music: { intensity: 0.75 },
  },
  {
    id: 'stalingrad', module: 's6_stalingrad', start: 34.0, end: 42.0,
    narration: 'At Stalingrad, the tide turns. In February 1943, the German Sixth Army surrenders.',
    dateCard: { text: 'FEBRUARY 1943', at: 0.6 },
    transitionIn: 'dip',
    cues: [
      { sfx: 'wind', at: 0.0, gain: -16, dur: 8.0, howl: true },
      { sfx: 'gunfire', frac: 0.20, gain: -22, muffled: true },
      { sfx: 'gunfire', frac: 0.34, gain: -23, muffled: true },
      { sfx: 'gunfire', frac: 0.48, gain: -22, muffled: true },
    ],
    // Music collapses to a cold cello drone, then a silence beat on "surrenders".
    music: { intensity: 0.3, cello: true, silenceAt: { word: 'surrenders', offset: 0 } },
  },
  {
    id: 'dday', module: 's7_dday', start: 42.0, end: 50.0,
    narration: 'June 6, 1944. Allied forces land in Normandy. Germany now fights on two fronts.',
    dateCard: { text: 'JUNE 6, 1944', at: 0.5 },
    transitionIn: 'burn',
    cues: [
      { sfx: 'waves', at: 0.0, gain: -17, dur: 5.6 },
      { sfx: 'gunfire', frac: 0.20, gain: -17 },
      { sfx: 'gunfire', frac: 0.36, gain: -18 },
      { sfx: 'gunfire', frac: 0.52, gain: -17 },
      { sfx: 'whoosh', word: 'Germany', offset: -0.45, gain: -16 }, // cut to map (s7_dday.js)
      { sfx: 'percussion', word: 'Germany', offset: -0.3, gain: -15, dur: 2.6 },
    ],
    music: { intensity: 0.85 },
  },
  {
    id: 'berlin', module: 's8_berlin', start: 50.0, end: 56.0,
    narration: 'By April 1945, Soviet troops reach Berlin.',
    dateCard: { text: 'APRIL 1945', at: 0.5 },
    transitionIn: 'dip',
    cues: [
      { sfx: 'explosion', frac: 0.15, gain: -16 },
      { sfx: 'explosion', word: 'Soviet', offset: -0.3, gain: -14 }, // cut to ruined city (s8_berlin.js)
      { sfx: 'fire', word: 'Soviet', offset: -0.35, gain: -19, dur: 2.6 },
      { sfx: 'explosion', word: 'reach', offset: 0.0, gain: -17 },
    ],
    // Climax, then a hard cut to silence at the end of the scene.
    music: { intensity: 1.0, hardCut: true },
  },
  {
    id: 'ending', module: 's9_ending', start: 56.0, end: 60.0,
    narration: 'May 8, 1945. The war in Europe is over. But the world would never be the same.',
    dateCard: null, // the ending typesets its own title card
    transitionIn: 'dip',
    cues: [
      { sfx: 'wind', at: 0.0, gain: -27, dur: 4.0, soft: true },
      { sfx: 'piano', at: 0.35, gain: -15 }, // single D note
    ],
    music: { intensity: 0.0 },
  },
];

const normWord = (w) => w.toLowerCase().replace(/[^a-z0-9']/g, '');
/** Absolute time a word of the scene's narration starts (nth occurrence, default first). */
function wordTime(scene, word, nth = 0) {
  const hits = scene.narration.words.filter((w) => normWord(w.text) === normWord(word));
  if (!hits[nth]) throw new Error(`word "${word}" not in narration of scene ${scene.id}`);
  return hits[nth].start;
}

/** Resolve a scene-relative time spec to absolute seconds. */
function cueTime(spec, scene) {
  const s = scene.startSec, e = scene.endSec, d = e - s;
  if (spec.at !== undefined) return s + spec.at;
  if (spec.frac !== undefined) return s + spec.frac * d;
  if (spec.fromEnd !== undefined) return e - spec.fromEnd;
  if (spec.word !== undefined) return wordTime(scene, spec.word, spec.nth) + (spec.offset || 0);
  if (spec.narr !== undefined) {
    const base = spec.narr === 'end' ? scene.narration.endSec : scene.narration.startSec;
    return base + (spec.offset || 0);
  }
  throw new Error('bad cue time spec: ' + JSON.stringify(spec));
}

/**
 * Solve scene windows from measured narration durations.
 * @param {number[]} durations seconds of each narration line, in scene order
 * @returns {number[]} scene durations in whole frames (sum === TOTAL_FRAMES)
 */
function solveWindows(durations) {
  const nominal = SCENES.map((s) => s.end - s.start);
  const need = durations.map((d) => MIN_LEAD + d + NARRATION_TAIL);
  const needSum = need.reduce((a, b) => a + b, 0);
  if (needSum > DURATION) {
    throw new Error(`Narration needs ${needSum.toFixed(2)} s but the film is ${DURATION} s. ` +
      'audio/tts.py should have re-synthesized at a faster rate.');
  }
  // Start from max(nominal, need); then give back surplus proportionally until sum = DURATION.
  let len = nominal.map((n, i) => Math.max(n, need[i]));
  let sum = len.reduce((a, b) => a + b, 0);
  if (sum > DURATION) {
    const surplus = len.map((l, i) => l - need[i]);
    const surplusSum = surplus.reduce((a, b) => a + b, 0);
    const k = (sum - DURATION) / surplusSum;
    len = len.map((l, i) => l - surplus[i] * k);
  } else if (sum < DURATION) {
    // Cannot happen with nominal windows summing to 60, but keep it robust.
    len = len.map((l) => l * (DURATION / sum));
  }
  // Integer frames: floor each (never below need), hand remaining frames to the largest remainders.
  const exact = len.map((l) => l * FPS);
  const frames = exact.map((x, i) => Math.max(Math.ceil(need[i] * FPS - 1e-6), Math.floor(x)));
  let rem = TOTAL_FRAMES - frames.reduce((a, b) => a + b, 0);
  const order = exact.map((x, i) => [x - Math.floor(x), i]).sort((a, b) => b[0] - a[0]);
  for (let k = 0; rem > 0; k = (k + 1) % order.length, rem--) frames[order[k][1]]++;
  for (let k = order.length - 1; rem < 0; k = (k - 1 + order.length) % order.length) {
    const i = order[k][1];
    if (frames[i] - 1 >= Math.ceil(need[i] * FPS)) { frames[i]--; rem++; }
  }
  return frames;
}

/** Build the fully resolved, frame-accurate timeline from narration_timing.json. */
function resolve(timing) {
  const durations = SCENES.map((s, i) => {
    const line = timing.lines[i];
    if (!line || line.text !== s.narration) throw new Error(`narration_timing.json is stale for scene ${s.id}`);
    return line.duration;
  });
  const frames = solveWindows(durations);
  let f0 = 0;
  const scenes = SCENES.map((s, i) => {
    const startFrame = f0, endFrame = f0 + frames[i]; // [start, end)
    f0 = endFrame;
    const startSec = startFrame / FPS, endSec = endFrame / FPS;
    const narrEnd = endSec - NARRATION_TAIL;
    const narrStart = narrEnd - durations[i];
    const words = timing.lines[i].words.map((w) => ({
      text: w.text, start: narrStart + w.start, end: narrStart + w.end,
    }));
    const sc = {
      ...s, index: i, startFrame, endFrame, frames: frames[i], startSec, endSec,
      narration: { text: s.narration, startSec: narrStart, endSec: narrEnd, duration: durations[i], words },
    };
    if (s.dateCard) sc.dateCard = { ...s.dateCard, startSec: startSec + s.dateCard.at };
    return sc;
  });
  // Absolute audio cues (visual modules use the same numbers via cueTime()).
  const cues = [];
  for (const sc of scenes) {
    for (const c of sc.cues) cues.push({ ...c, scene: sc.id, time: cueTime(c, sc) });
    if (sc.dateCard) {
      // typewriter key-click per visible character of the date card
      [...sc.dateCard.text].forEach((ch, k) => {
        if (ch !== ' ') cues.push({ sfx: 'typekey', scene: sc.id, time: sc.dateCard.startSec + k * DATE_TYPE_INTERVAL, gain: -17 });
      });
    }
    if (sc.transitionIn) cues.push({ sfx: 'boom', scene: sc.id, time: sc.startSec - 2 / FPS, gain: -13, kind: sc.transitionIn });
    if (sc.music && sc.music.silenceAt) sc.music.silenceSec = cueTime(sc.music.silenceAt, sc);
  }
  cues.sort((a, b) => a.time - b.time);
  return { fps: FPS, width: WIDTH, height: HEIGHT, totalFrames: TOTAL_FRAMES, duration: DURATION, seed: SEED,
    narrationTail: NARRATION_TAIL, transitionFrames: TRANSITION_FRAMES, safe: SAFE, colors: COLORS,
    voice: timing.voice, rate: timing.rate, scenes, cues };
}

const DATE_TYPE_INTERVAL = 0.055; // seconds per typed character on date cards

module.exports = { FPS, WIDTH, HEIGHT, TOTAL_FRAMES, DURATION, SEED, SAFE, COLORS, SCENES, NARRATION_TAIL,
  TRANSITION_FRAMES, DATE_TYPE_INTERVAL, MIN_LEAD, cueTime, wordTime, solveWindows, resolve };

// ---- CLI ---------------------------------------------------------------------------------------
if (require.main === module) {
  const root = path.resolve(__dirname, '..');
  const build = path.join(root, 'build');
  fs.mkdirSync(build, { recursive: true });
  const arg = process.argv[2];
  if (arg === '--dump') {
    const base = { fps: FPS, duration: DURATION, narrationTail: NARRATION_TAIL, minLead: MIN_LEAD,
      lines: SCENES.map((s) => ({ id: s.id, text: s.narration, nominal: s.end - s.start })) };
    fs.writeFileSync(path.join(build, 'timeline_base.json'), JSON.stringify(base, null, 2));
    console.log('wrote build/timeline_base.json');
  } else if (arg === '--resolve') {
    const timing = JSON.parse(fs.readFileSync(path.join(build, 'narration_timing.json'), 'utf8'));
    const tl = resolve(timing);
    fs.writeFileSync(path.join(build, 'timeline.json'), JSON.stringify(tl, null, 2));
    console.log('scene        frames        window (s)         narration (s)      fits');
    for (const s of tl.scenes) {
      const fits = s.narration.startSec >= s.startSec && s.narration.endSec <= s.endSec;
      console.log(`${s.id.padEnd(12)} ${String(s.startFrame).padStart(4)}-${String(s.endFrame - 1).padEnd(4)}  ` +
        `${s.startSec.toFixed(2).padStart(5)}-${s.endSec.toFixed(2).padEnd(5)}   ` +
        `${s.narration.startSec.toFixed(2).padStart(5)}-${s.narration.endSec.toFixed(2).padEnd(5)}      ${fits ? 'OK' : 'FAIL'}`);
    }
    console.log('wrote build/timeline.json');
  } else {
    console.log('usage: node src/timeline.js --dump | --resolve');
  }
}
