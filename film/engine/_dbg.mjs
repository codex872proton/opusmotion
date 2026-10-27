import puppeteer from 'puppeteer-core';
import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path';
const ROOT='/tmp/hoplite/workspace/film'; const T=Date.now(); const log=(...a)=>console.log(((Date.now()-T)/1000).toFixed(1), ...a);
const server = http.createServer((req, res) => {
  if (req.method === 'POST') { let n=0; log('POST start', req.url); req.on('data', d=>n+=d.length); req.on('end', ()=>{ log('POST end', n); res.writeHead(200); res.end(); }); return; }
  const p = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
  if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, {'Content-Type': p.endsWith('.js')?'text/javascript':p.endsWith('.html')?'text/html':'application/octet-stream'}); fs.createReadStream(p).pipe(res);
});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const browser = await puppeteer.launch({ executablePath: '/usr/local/bin/google-chrome', headless: true, args: ['--no-sandbox','--enable-unsafe-swiftshader','--use-angle=swiftshader','--ignore-gpu-blocklist','--disable-dev-shm-usage'], protocolTimeout: 0 });
log('launched');
const page = await browser.newPage(); page.on('console', m=>log('[page]', m.text())); page.on('pageerror', e=>log('[err]', e.message));
await page.setViewport({width:1080,height:1920});
await page.goto(`http://127.0.0.1:${server.address().port}/render.html`, {waitUntil:'load'}); log('loaded');
await page.waitForFunction(() => window.ready !== undefined); await page.evaluate(() => window.ready);
log('ready');
for (let f=0; f<3; f++) {
  const r = await page.evaluate(async (f) => { const t0=performance.now(); window.renderFrameRaw(f); const t1=performance.now();
    const res = await fetch('/sink/0', {method:'POST', body: new Uint8Array(1080*1920*4)}); return `render ${Math.round(t1-t0)} post ${Math.round(performance.now()-t1)} status ${res.status}`; }, f);
  log(f, r);
}
await browser.close(); server.close();
