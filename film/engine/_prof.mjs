import puppeteer from 'puppeteer-core';
import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path';
const ROOT='/tmp/hoplite/workspace/film';
const server = http.createServer((req,res)=>{const p=path.join(ROOT,decodeURIComponent(req.url.split('?')[0])); if(!fs.existsSync(p)||fs.statSync(p).isDirectory()){res.writeHead(404);res.end();return;} res.writeHead(200,{'Content-Type': p.endsWith('.js')?'text/javascript':p.endsWith('.html')?'text/html':'application/octet-stream'}); fs.createReadStream(p).pipe(res);});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const b = await puppeteer.launch({executablePath:'/usr/local/bin/google-chrome',headless:true,args:['--no-sandbox','--enable-unsafe-swiftshader','--use-angle=swiftshader','--ignore-gpu-blocklist','--disable-accelerated-2d-canvas','--disable-gpu-rasterization']});
const p = await b.newPage(); await p.setViewport({width:1080,height:1920});
await p.goto(`http://127.0.0.1:${server.address().port}/render.html`); await p.evaluate(()=>window.ready);
const r = await p.evaluate(()=>{
  const out={};
  for (const f of [160,161,162]) { let t0=performance.now(); window.renderFrameRaw(f); const gl=document.getElementById('c').getContext('webgl2'); const px=new Uint8Array(4); gl.readPixels(0,0,1,1,gl.RGBA,gl.UNSIGNED_BYTE,px); out['raw'+f]=performance.now()-t0;
    t0=performance.now(); const u=document.getElementById('c').toDataURL('image/png'); out['png'+f]=performance.now()-t0; }
  // canvas-only cost
  const c=document.createElement('canvas'); c.width=1080;c.height=1920; const x=c.getContext('2d');
  let t0=performance.now(); for(let i=0;i<5;i++){ const g=x.createRadialGradient(300,600,50,400,800,1300); g.addColorStop(0,'rgba(0,0,0,0)'); g.addColorStop(1,'rgba(0,0,0,.8)'); x.fillStyle=g; x.fillRect(0,0,1080,1920);} out.grad5=performance.now()-t0;
  return out; });
console.log(r);
let t0=Date.now(); await p.evaluate(()=>window.renderFrame(163)); console.log('full evaluate', Date.now()-t0);
await b.close(); server.close();
