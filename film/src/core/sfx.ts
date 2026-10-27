// Sound cue registry. Scenes declare cues from the same timing data they animate with,
// so picture and procedural sound design can never drift apart.
export interface Cue {
  t: number; type: string; params?: Record<string, any>; gain_db?: number; pan?: number;
  bus?: 'fx' | 'amb' | 'hits'; send?: { room?: number; night?: number }; seed?: number;
  lp?: number; hp?: number; dur?: number; fade_in?: number; fade_out?: number; anchor?: 'start' | 'end'; tag?: string;
}
const list: Cue[] = [];
export function cue(c: Cue) { list.push({ bus: 'fx', gain_db: 0, pan: 0, ...c, t: Math.round(c.t * 10000) / 10000 }); }
export function cues() { return [...list].sort((a, b) => a.t - b.t); }
let seed = 1000;
/** Typed text -> one thock per visible keystroke (with matching variants for space/enter). */
export function typingCues(text: string, times: number[], o: { gain?: number; pan?: number; room?: number; tag?: string } = {}) {
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    const variant = ch === ' ' ? 'space' : ch === '\n' ? 'enter' : 'alpha';
    cue({ t: times[i], type: 'thock', params: { variant, vel: 0.75 + ((i * 7919) % 100) / 400 }, gain_db: (o.gain ?? -12) + (variant === 'space' ? 1 : 0),
      pan: (o.pan ?? 0) + (((i * 31) % 17) / 17 - 0.5) * 0.25, send: { room: o.room ?? 0.18 }, seed: seed++, tag: o.tag ?? 'type' });
  }
}
