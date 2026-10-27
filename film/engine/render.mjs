// Offline render driver: serves the film directory, drives headless Chrome (WebGL2 via SwiftShader)
// frame-by-frame and writes lossless PNG frames, review stills, or the SFX cue sheet.
//
//   node engine/render.mjs --frames 0:2093 [--workers 2] [--out build/frames]
//   node engine/render.mjs --stills 3.2,8.5,20 [--out /tmp/verify/stills]
//   node engine/render.mjs --cues            (writes build/cues.json)
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import puppeteer from 'puppeteer-core';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const args = Object.fromEntries(process.argv.slice(2).reduce((acc, a, i, arr) => {
  if (a.startsWith('--')) acc.push([a.slice(2), arr[i + 1] && !arr[i + 1].startsWith('--') ? arr[i + 1] : true]);
  return acc;
}, []));

const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.ttf': 'font/ttf', '.png': 'image/png', '.bin': 'application/octet-stream', '.i16': 'application/octet-stream' };
const server = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
  if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { 'Content-Type': MIME[path.extname(p)] || 'application/octet-stream', 'Access-Control-Allow-Origin': '*' });
  fs.createReadStream(p).pipe(res);
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const URL_ = `http://127.0.0.1:${server.address().port}/render.html`;

async function openPage() {
  const browser = await puppeteer.launch({
    executablePath: process.env.CHROME || '/usr/local/bin/google-chrome',
    headless: true,
    args: ['--no-sandbox', '--enable-unsafe-swiftshader', '--use-angle=swiftshader', '--ignore-gpu-blocklist',
      '--disable-dev-shm-usage', '--hide-scrollbars', '--mute-audio', '--js-flags=--max-old-space-size=4096',
      '--force-color-profile=srgb', '--disable-accelerated-2d-canvas', '--disable-gpu-rasterization', '--disable-background-timer-throttling', '--disable-renderer-backgrounding'],
    protocolTimeout: 0,
  });
  const page = await browser.newPage();
  page.on('console', (m) => { const t = m.text(); if (!/GPU stall|Automatic fallback/.test(t)) console.log('[page]', t); });
  page.on('pageerror', (e) => console.error('[pageerror]', e.message));
  await page.setViewport({ width: 1080, height: 1920, deviceScaleFactor: 1 });
  await page.goto(URL_, { waitUntil: 'load' });
  await page.evaluate(() => window.ready);
  if (args.mb) await page.evaluate((n) => window.setMB(n), Number(args.mb));
  return { browser, page };
}

const info = async (page) => page.evaluate(() => window.info);

if (args.cues) {
  const { browser, page } = await openPage();
  const cues = await page.evaluate(() => window.getCues());
  const out = path.join(ROOT, 'build/cues.json');
  fs.writeFileSync(out, JSON.stringify(cues, null, 0));
  console.log('cues', cues.cues.length, '->', out);
  await browser.close(); server.close(); process.exit(0);
}

if (args.stills) {
  const outDir = path.resolve(args.out || '/tmp/verify/stills');
  fs.mkdirSync(outDir, { recursive: true });
  const { browser, page } = await openPage();
  const I = await info(page);
  for (const s of String(args.stills).split(',')) {
    const f = Math.round(Number(s) * I.fps);
    const t0 = Date.now();
    const url = await page.evaluate((f) => window.renderFrame(f), f);
    const file = path.join(outDir, `still_${String(f).padStart(5, '0')}.png`);
    fs.writeFileSync(file, Buffer.from(url.split(',')[1], 'base64'));
    console.log(`t=${s}s frame ${f} -> ${file} (${Date.now() - t0} ms)`);
  }
  await browser.close(); server.close(); process.exit(0);
}

if (args.frames) {
  const outDir = path.resolve(args.out || path.join(ROOT, 'build/frames'));
  fs.mkdirSync(outDir, { recursive: true });
  const [a, b] = String(args.frames).split(':').map(Number);
  const workers = Number(args.workers || 1);
  const skipExisting = !!args.resume;
  const t0 = Date.now(); let done = 0; const total = b - a + 1;
  await Promise.all(Array.from({ length: workers }, async (_, w) => {
    const { browser, page } = await openPage();
    for (let f = a + w; f <= b; f += workers) {
      const file = path.join(outDir, `f_${String(f).padStart(5, '0')}.png`);
      if (skipExisting && fs.existsSync(file)) { done++; continue; }
      const url = await page.evaluate((f) => window.renderFrame(f), f);
      fs.writeFileSync(file, Buffer.from(url.split(',')[1], 'base64'));
      done++;
      if (done % 30 === 0 || done === total) {
        const el = (Date.now() - t0) / 1000;
        console.log(`${done}/${total} frames  ${(el / done).toFixed(2)} s/frame  eta ${((total - done) * el / done / 60).toFixed(1)} min`);
      }
    }
    await browser.close();
  }));
  server.close(); process.exit(0);
}
console.log('usage: --frames a:b | --stills t1,t2 | --cues'); server.close();
