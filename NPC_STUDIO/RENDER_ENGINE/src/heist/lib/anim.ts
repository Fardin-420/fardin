import { Easing, interpolate, random } from 'remotion';

export const clamp = (v: number, a = 0, b = 1) => Math.min(b, Math.max(a, v));

export const outExpo = Easing.bezier(0.16, 1, 0.3, 1);
export const outPow3 = Easing.bezier(0.215, 0.61, 0.355, 1);
export const inPow3 = Easing.bezier(0.55, 0.055, 0.675, 0.19);
export const inOut = Easing.bezier(0.65, 0, 0.35, 1);

/** 0→1 over [start, start+len] with an easing (default ease-out expo). */
export const prog = (f: number, start: number, len: number, ease: (t: number) => number = outExpo) =>
  ease(clamp((f - start) / Math.max(len, 1)));

/** Entrance (ease-out) then optional exit (ease-in, faster). Returns 0..1 visibility. */
export const inOutVis = (f: number, start: number, inLen = 14, end?: number, outLen = 9) => {
  const a = prog(f, start, inLen, outExpo);
  if (end === undefined) return a;
  const b = 1 - prog(f, end - outLen, outLen, inPow3);
  return Math.min(a, b);
};

/** Number pop with one small overshoot (spec: max one). */
export const pop = (f: number, start: number, len = 12) => {
  const t = clamp((f - start) / len);
  if (t <= 0) return 0;
  const s = interpolate(t, [0, 0.6, 1], [0, 1.06, 1], { easing: outPow3 });
  return s;
};

/** High-damping spring (no bounce) for UI. */
export const damp = (f: number, start: number, len = 18) => prog(f, start, len, Easing.bezier(0.22, 1, 0.36, 1));

export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

export const rnd = (seed: string | number) => random(String(seed));

/** Deterministic jitter in [-1,1] that changes every `hold` frames. */
export const jitter = (f: number, seed: string | number, hold = 2) => rnd(`${seed}-${Math.floor(f / hold)}`) * 2 - 1;

export const fmtInt = (n: number) => Math.round(n).toLocaleString('en-US');

export const typeOn = (text: string, f: number, start: number, cps = 30, fps = 30) => {
  const n = Math.floor(((f - start) / fps) * cps);
  return text.slice(0, clamp(n, 0, text.length));
};
