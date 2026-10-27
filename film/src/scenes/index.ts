import { Engine } from '../core/engine';
import { testScene } from './s00_test';
export async function registerScenes(eng: Engine) {
  eng.add(testScene());
}
