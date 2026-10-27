import { Engine } from '../core/engine';
import { s01 } from './s01_intercept';
import { s02, terrain } from './s02_team';
export async function registerScenes(eng: Engine) {
  await terrain.load();
  eng.add(s01());
  eng.add(s02());
  eng.transitions.push({ from: 'intercept', to: 'team', t: 9.05, dur: 0.5, kind: 'ink' });
}
