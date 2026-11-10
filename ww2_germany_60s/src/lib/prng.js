/**
 * prng.js — deterministic randomness. Math.random is never used anywhere in this project.
 */
'use strict';

const SEED = 1945;

/** mulberry32: tiny, fast, good-quality 32-bit PRNG. Returns a function -> float in [0, 1). */
function mulberry32(a) {
  let s = a >>> 0;
  return function rand() {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Integer hash of several values (for per-frame / per-object seeds). */
function hash(...xs) {
  let h = 0x811c9dc5 ^ SEED;
  for (const x of xs) {
    h = Math.imul(h ^ (x | 0), 0x01000193);
    h ^= h >>> 13;
    h = Math.imul(h, 0x5bd1e995);
    h ^= h >>> 15;
  }
  return h >>> 0;
}

/** A PRNG stream uniquely and reproducibly derived from the global seed plus some keys. */
function rng(...keys) {
  return mulberry32(hash(...keys));
}

/** Helpers bound to a rand() function. */
function helpers(rand) {
  return {
    rand,
    range: (a, b) => a + (b - a) * rand(),
    int: (a, b) => Math.floor(a + (b - a + 1) * rand()),
    pick: (arr) => arr[Math.floor(rand() * arr.length)],
    gauss: () => { // Box–Muller
      const u = Math.max(1e-9, rand()), v = rand();
      return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
    },
  };
}

/** Smooth 1-D value noise in [-1, 1] (deterministic), used for gate weave, flicker, sway. */
function noise1(x, key = 0) {
  const i = Math.floor(x), f = x - i;
  const a = mulberry32(hash(key, i))() * 2 - 1;
  const b = mulberry32(hash(key, i + 1))() * 2 - 1;
  const u = f * f * (3 - 2 * f);
  return a + (b - a) * u;
}

module.exports = { SEED, mulberry32, hash, rng, helpers, noise1 };
