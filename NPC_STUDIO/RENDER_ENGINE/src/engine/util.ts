// Deterministic math helpers. Every value on screen is a pure function of time.

export const clamp = (x: number, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
export const range = (t: number, a: number, b: number) => clamp((t - a) / (b - a));
export const smooth = (x: number) => x * x * (3 - 2 * x);

export const easeOutExpo = (x: number) => (x >= 1 ? 1 : 1 - Math.pow(2, -10 * x));
export const easeInExpo = (x: number) => (x <= 0 ? 0 : Math.pow(2, 10 * x - 10));
export const easeOutCubic = (x: number) => 1 - Math.pow(1 - x, 3);
export const easeInCubic = (x: number) => x * x * x;
export const easeInOutCubic = (x: number) =>
  x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
export const easeInOutSine = (x: number) => -(Math.cos(Math.PI * x) - 1) / 2;

/** Anticipation: dips backwards before travelling forward. */
export const easeAnticipate = (x: number, k = 1.7) => x * x * ((k + 1) * x - k);

/**
 * Closed-form damped spring step response (0 → 1 with overshoot / follow-through).
 * t in seconds since release.
 */
export function spring(t: number, freq = 2.2, damping = 0.42): number {
  if (t <= 0) return 0;
  const w = 2 * Math.PI * freq;
  const z = damping;
  if (z >= 1) return 1 - Math.exp(-w * t) * (1 + w * t);
  const wd = w * Math.sqrt(1 - z * z);
  return 1 - Math.exp(-z * w * t) * (Math.cos(wd * t) + ((z * w) / wd) * Math.sin(wd * t));
}

/** Spring velocity, used to drive motion blur and squash from real motion. */
export function springVel(t: number, freq = 2.2, damping = 0.42) {
  const h = 1 / 240;
  return (spring(t + h, freq, damping) - spring(t - h, freq, damping)) / (2 * h);
}

/** Damped camera shake after an impact at t=0. */
export function shake(t: number, amp: number, seed = 1, decay = 5, freq = 23) {
  if (t < 0) return [0, 0] as const;
  const e = Math.exp(-decay * t) * amp;
  return [
    e * Math.sin(t * freq * 6.28 + seed) * 0.7 + e * Math.sin(t * freq * 3.7 + seed * 2) * 0.3,
    e * Math.cos(t * freq * 5.1 + seed * 3) * 0.6 + e * Math.sin(t * freq * 2.3 + seed) * 0.4,
  ] as const;
}

/** Impulse envelope: instant attack, exponential decay. */
export const impulse = (t: number, decay = 6) => (t < 0 ? 0 : Math.exp(-decay * t));

/** Seeded PRNG (mulberry32). */
export function prng(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Smooth 1D value noise for organic drift. */
export function noise1(x: number, seed = 0) {
  const h = (n: number) => {
    const s = Math.sin(n * 127.1 + seed * 311.7) * 43758.5453;
    return s - Math.floor(s);
  };
  const i = Math.floor(x);
  const f = x - i;
  return lerp(h(i), h(i + 1), smooth(f)) * 2 - 1;
}
