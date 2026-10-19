import type { SceneFactory } from '../engine/Engine';
import { S01 } from './S01Opening';
import { S02 } from './S02BreakRules';
import { S03 } from './S03CodeWorld';
import { S04 } from './S04VoiceReveal';
import { S05 } from './S05NoTimeline';
import { S06 } from './S06Identity';

export const SCENES: SceneFactory[] = [S01, S02, S03, S04, S05, S06];
