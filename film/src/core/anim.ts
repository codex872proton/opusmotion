// Deterministic animation toolkit: easing, tweening, springs, seeded randomness and noise.
// Every visual is a pure function of time, so any frame can be rendered in isolation.

export const clamp = (x: number, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
export const inv = (a: number, b: number, x: number) => (b === a ? (x >= b ? 1 : 0) : clamp((x - a) / (b - a)));
export const remap = (x: number, a: number, b: number, c: number, d: number) => lerp(c, d, inv(a, b, x));
export const smooth = (a: number, b: number, x: number) => { const t = inv(a, b, x); return t * t * (3 - 2 * t); };
export const fract = (x: number) => x - Math.floor(x);
export const TAU = Math.PI * 2;

export type Ease = (t: number) => number;
export const E = {
  linear: (t: number) => t,
  inQuad: (t: number) => t * t,
  outQuad: (t: number) => 1 - (1 - t) * (1 - t),
  inOutQuad: (t: number) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2),
  inCubic: (t: number) => t * t * t,
  outCubic: (t: number) => 1 - Math.pow(1 - t, 3),
  inOutCubic: (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
  inQuart: (t: number) => t * t * t * t,
  outQuart: (t: number) => 1 - Math.pow(1 - t, 4),
  inOutQuart: (t: number) => (t < 0.5 ? 8 * t ** 4 : 1 - Math.pow(-2 * t + 2, 4) / 2),
  outQuint: (t: number) => 1 - Math.pow(1 - t, 5),
  inOutQuint: (t: number) => (t < 0.5 ? 16 * t ** 5 : 1 - Math.pow(-2 * t + 2, 5) / 2),
  inExpo: (t: number) => (t <= 0 ? 0 : Math.pow(2, 10 * t - 10)),
  outExpo: (t: number) => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * t)),
  inOutExpo: (t: number) => t <= 0 ? 0 : t >= 1 ? 1 : t < 0.5 ? Math.pow(2, 20 * t - 10) / 2 : (2 - Math.pow(2, -20 * t + 10)) / 2,
  outCirc: (t: number) => Math.sqrt(1 - Math.pow(t - 1, 2)),
  inOutSine: (t: number) => -(Math.cos(Math.PI * t) - 1) / 2,
  outSine: (t: number) => Math.sin((t * Math.PI) / 2),
  inSine: (t: number) => 1 - Math.cos((t * Math.PI) / 2),
  outBack: (t: number, s = 1.4) => 1 + (s + 1) * Math.pow(t - 1, 3) + s * Math.pow(t - 1, 2),
  inBack: (t: number, s = 1.4) => (s + 1) * t * t * t - s * t * t,
};

/** Cubic-bezier easing (CSS semantics), solved with Newton iterations. */
export function bezier(x1: number, y1: number, x2: number, y2: number): Ease {
  const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
  const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
  const sx = (t: number) => ((ax * t + bx) * t + cx) * t;
  const sy = (t: number) => ((ay * t + by) * t + cy) * t;
  const dx = (t: number) => (3 * ax * t + 2 * bx) * t + cx;
  return (x: number) => {
    if (x <= 0) return 0; if (x >= 1) return 1;
    let t = x;
    for (let i = 0; i < 8; i++) { const d = dx(t); if (Math.abs(d) < 1e-6) break; t -= (sx(t) - x) / d; }
    return sy(clamp(t));
  };
}
/** Signature "cinematic" curves used across the film for consistent motion language. */
export const CINE = {
  glide: bezier(0.65, 0, 0.18, 1),   // slow-in, long luxurious settle
  push: bezier(0.32, 0, 0.12, 1),    // camera pushes
  snap: bezier(0.2, 0.9, 0.1, 1),    // UI elements landing
  heavy: bezier(0.7, 0, 0.84, 0),    // accelerating fall
};

/** Progress of a tween that starts at t0 and lasts dur, eased. */
export const tw = (t: number, t0: number, dur: number, ease: Ease = E.outCubic) => ease(inv(t0, t0 + dur, t));

/** Damped spring step response (0 -> 1) for t >= 0. freq in Hz, damping ratio zeta. */
export function spring(t: number, freq = 2.2, zeta = 0.55) {
  if (t <= 0) return 0;
  const w = TAU * freq;
  if (zeta >= 1) return 1 - Math.exp(-w * t) * (1 + w * t);
  const wd = w * Math.sqrt(1 - zeta * zeta);
  return 1 - Math.exp(-zeta * w * t) * (Math.cos(wd * t) + (zeta * w / wd) * Math.sin(wd * t));
}

/** Piecewise keyframes: [[t, v], ...] with per-segment easing. */
export function keys(t: number, k: [number, number][], ease: Ease = E.inOutCubic) {
  if (t <= k[0][0]) return k[0][1];
  for (let i = 1; i < k.length; i++) {
    if (t <= k[i][0]) return lerp(k[i - 1][1], k[i][1], ease(inv(k[i - 1][0], k[i][0], t)));
  }
  return k[k.length - 1][1];
}

/** mulberry32 seeded PRNG. */
export function rng(seed: number) {
  let a = seed >>> 0;
  const f = () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  return Object.assign(f, {
    range: (a: number, b: number) => a + (b - a) * f(),
    pick: <T>(arr: T[]) => arr[Math.floor(f() * arr.length)],
    gauss: () => { let u = 0, v = 0; while (u === 0) u = f(); while (v === 0) v = f(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(TAU * v); },
  });
}
export type RNG = ReturnType<typeof rng>;

const hash1 = (n: number) => fract(Math.sin(n * 127.1 + 311.7) * 43758.5453123);
/** Smooth 1D value noise in [-1, 1]. */
export function noise1(x: number, seed = 0) {
  const i = Math.floor(x), f = x - i, u = f * f * (3 - 2 * f);
  return lerp(hash1(i + seed * 57.3), hash1(i + 1 + seed * 57.3), u) * 2 - 1;
}
/** Fractal 1D noise for organic hand-held camera drift. */
export function fbm1(x: number, seed = 0, oct = 3) {
  let s = 0, a = 0.5, f = 1, n = 0;
  for (let i = 0; i < oct; i++) { s += a * noise1(x * f, seed + i * 13.1); n += a; a *= 0.5; f *= 2.03; }
  return s / n;
}

/** Humanised typing schedule: returns reveal time for each character. */
export function typeSchedule(text: string, t0: number, cps: number, seed = 1, jitter = 0.35) {
  const r = rng(seed);
  const times: number[] = [];
  let t = t0;
  for (let i = 0; i < text.length; i++) {
    times.push(t);
    const ch = text[i];
    let d = 1 / cps;
    d *= 1 + (r() * 2 - 1) * jitter;
    if (ch === ' ') d *= 1.15;
    if (ch === '\n') d *= 2.2;
    if (/[.,:;·—]/.test(ch)) d *= 1.6;
    t += d;
  }
  return times;
}
