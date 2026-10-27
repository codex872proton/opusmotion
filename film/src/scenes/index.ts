import { Engine } from '../core/engine';
import { s01 } from './s01_intercept';
export async function registerScenes(eng: Engine) {
  eng.add(s01());
}
