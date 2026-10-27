import puppeteer from 'puppeteer-core';
const t=Date.now(); const log=(...a)=>console.log(((Date.now()-t)/1000).toFixed(1), ...a);
log('launch');
const browser = await puppeteer.launch({ executablePath: '/usr/local/bin/google-chrome', headless: true, args: ['--no-sandbox','--enable-unsafe-swiftshader','--use-angle=swiftshader','--disable-dev-shm-usage'], protocolTimeout: 30000, dumpio: false });
log('launched', await browser.version());
const page = await browser.newPage(); log('page');
await page.goto('data:text/html,<p>hi</p>'); log('goto');
await browser.close(); log('closed');
