// Project data is copied into src/data/ by pipeline/render.mjs before bundling.
import timelineJson from './data/timeline.json';
import envelopeJson from './data/envelope.json';

export type Line = {
  id: string; scene: string; text: string; emotion: string; start: number; end: number;
};
export type Timeline = {
  project: string;
  voiced: boolean;
  timing_source: string;
  width: number;
  height: number;
  fps: number;
  duration: number;
  durationInFrames: number;
  lines: Line[];
  scenes: { id: string; start: number; end: number }[];
  cues: Record<string, number>;
};
export type EnvelopeData = {
  fps: number;
  frames: number;
  bands: number;
  has_voice: boolean;
  mix_rms: number[];
  mix_spec: number[][];
  voice_rms: number[] | null;
  voice_spec: number[][] | null;
};

export class Envelope {
  constructor(public d: EnvelopeData) {}
  private at<T>(arr: T[], frame: number): T {
    return arr[Math.max(0, Math.min(arr.length - 1, Math.round(frame)))];
  }
  /** Speech energy if NPC_VOICE_V1 narration exists, else the soundtrack. */
  signalRms(frame: number) {
    return this.at(this.d.voice_rms ?? this.d.mix_rms, frame);
  }
  signalSpec(frame: number) {
    return this.at(this.d.voice_spec ?? this.d.mix_spec, frame);
  }
  mixRms(frame: number) {
    return this.at(this.d.mix_rms, frame);
  }
  get source() {
    return this.d.has_voice ? 'NPC_VOICE_V1' : 'SOUNDTRACK';
  }
}

export const timeline = timelineJson as Timeline;
export const envelope = new Envelope(envelopeJson as EnvelopeData);
