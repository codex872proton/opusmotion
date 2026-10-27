// Boots the GPU engine, registers scenes and exposes a deterministic frame API to the driver.
import { initRenderer, W, H, renderer } from './core/gfx';
import { loadFonts } from './core/fonts';
import { Engine } from './core/engine';
import { buildCaptions } from './core/captions';
import { cues } from './core/sfx';
import { TL, FPS, DURATION } from './core/timeline';

declare global { interface Window { ready: Promise<void>; renderFrame: (f: number) => string; renderFrameRaw: (f: number) => void; sendFrame: (f: number, url: string) => Promise<void>; info: any; getCues: () => any; setMB: (n: number | null) => void; } }

export function boot(register: (eng: Engine) => Promise<void>) {
  const canvas = document.getElementById('c') as HTMLCanvasElement;
  initRenderer(canvas, W, H);
  const eng = new Engine();
  window.ready = (async () => {
    await loadFonts();
    await register(eng);
    const order = TL.beats.map((b) => b.id);
    buildCaptions((id) => { const i = order.indexOf(id); return i + 1 < order.length ? TL.beats[i + 1].start : DURATION + 5; });
    window.info = { fps: FPS, duration: DURATION, frames: Math.floor(DURATION * FPS), gl: renderer.getContext().getParameter(renderer.getContext().VERSION),
      scenes: eng.scenes.map((s) => ({ id: s.id, t0: s.t0, t1: s.t1 })) };
  })();
  const px = new Uint8Array(W * H * 4);
  window.renderFrameRaw = (f: number) => { eng.renderFrame(f); };
  window.renderFrame = (f: number) => { eng.renderFrame(f); return canvas.toDataURL('image/png'); };
  // Raw RGBA readback (bottom-up rows) posted as binary to the driver: avoids in-browser PNG encoding.
  window.sendFrame = async (f: number, url: string) => {
    eng.renderFrame(f);
    renderer.setRenderTarget(null);
    const gl = renderer.getContext();
    gl.readPixels(0, 0, W, H, gl.RGBA, gl.UNSIGNED_BYTE, px);
    const r = await fetch(url, { method: 'POST', body: px });
    if (!r.ok) throw new Error('sink ' + r.status);
  };
  window.getCues = () => ({ sr: 48000, duration: DURATION, cues: cues() });
  window.setMB = (n) => { eng.mbOverride = n; };
  (window as any).getProf = () => eng.prof;
  return eng;
}
