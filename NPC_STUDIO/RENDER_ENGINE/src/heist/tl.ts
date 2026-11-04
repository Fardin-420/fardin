import tlJson from './data/timeline.json';
import capJson from './data/captions.json';

export type Word = { w: string; s: number; e: number; scene: string; chunk: string };
export type SceneData = {
  id: string;
  title: string;
  chapter: number | null;
  chapterTitle: string | null;
  chapterDate: string | null;
  start: number;
  end: number;
  voStart: number;
  cues: Record<string, number>;
  punches: number[];
  impacts: number[];
  transitionIn: { type: string; frames: number };
};
export type Timeline = {
  fps: number;
  width: number;
  height: number;
  durationInFrames: number;
  factsAsOf: string;
  voice: string;
  scenes: SceneData[];
  words: Word[];
  sentences: { scene: string; text: string; s: number; e: number }[];
};
export type CaptionPage = {
  s: number;
  e: number;
  lines: { w: string; s: number; e: number; pop: boolean }[][];
};

export const TL = tlJson as unknown as Timeline;
export const CAPTIONS = capJson as unknown as { pages: CaptionPage[]; hide: [number, number][] };
export const FPS = TL.fps;

export const sceneById = (id: string): SceneData => {
  const s = TL.scenes.find((x) => x.id === id);
  if (!s) throw new Error(`scene ${id} missing`);
  return s;
};

/** Scene-local frame of a named cue. Throws at render time if the script lost the cue. */
export const cue = (s: SceneData, name: string): number => {
  const v = s.cues[name];
  if (v === undefined) throw new Error(`cue ${s.id}.${name} missing`);
  return v;
};

const norm = (x: string) => x.toLowerCase().replace(/[^a-z0-9$%]/g, '');

/** Scene-local frame where the nth matching narration word starts (fallback when no cue was authored). */
export const wordAt = (s: SceneData, text: string, nth = 0): number => {
  const target = norm(text);
  let k = 0;
  for (const w of TL.words) {
    if (w.scene !== s.id) continue;
    if (norm(w.w) === target || norm(w.w).startsWith(target)) {
      if (k === nth) return Math.round(w.s * FPS) - s.start;
      k++;
    }
  }
  throw new Error(`word "${text}" (#${nth}) not in ${s.id}`);
};

/** End frame (scene-local) of the sentence that contains a scene-local frame. */
export const sentenceEndAfter = (s: SceneData, local: number): number => {
  const t = (local + s.start) / FPS;
  const sen = TL.sentences.find((x) => x.scene === s.id && x.s <= t + 0.05 && x.e >= t - 0.05);
  return sen ? Math.round(sen.e * FPS) - s.start : local + 90;
};

export const dur = (s: SceneData) => s.end - s.start;
