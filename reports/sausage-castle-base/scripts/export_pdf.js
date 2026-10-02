#!/usr/bin/env node
/* Export the demo page (index.html) to a landscape PDF with Chromium, using the page's print stylesheet.
   Google Fonts are served from local @fontsource packages so the export works offline / in a sandbox.

   Setup (once):  npm install playwright-core @fontsource/anton @fontsource/barlow @fontsource/jetbrains-mono
   Run:           node scripts/export_pdf.js [out.pdf]
   Env:           CHROMIUM=/path/to/chromium (default: Playwright's bundled build), FONTSOURCE=<node_modules/@fontsource>
   Then encrypt for reviewers:  REVIEW_PASSWORD='...' python3 scripts/encrypt_pdf.py out.pdf ../../review/florida-freedom-world-review.pdf
*/
const path = require('path');
const fs = require('fs');
const http = require('http');
const { chromium } = require('playwright-core');

const BASE = path.resolve(__dirname, '..');
const OUT = path.resolve(process.argv[2] || path.join(BASE, 'florida-freedom-world.pdf'));
const FONTSOURCE = process.env.FONTSOURCE || path.join(process.cwd(), 'node_modules', '@fontsource');
const fonts = {
  'anton-latin-400-normal.woff2': ['Anton', 400, 'anton'],
  'barlow-latin-400-normal.woff2': ['Barlow', 400, 'barlow'],
  'barlow-latin-500-normal.woff2': ['Barlow', 500, 'barlow'],
  'barlow-latin-600-normal.woff2': ['Barlow', 600, 'barlow'],
  'jetbrains-mono-latin-400-normal.woff2': ['JetBrains Mono', 400, 'jetbrains-mono'],
  'jetbrains-mono-latin-500-normal.woff2': ['JetBrains Mono', 500, 'jetbrains-mono'],
};
const fontCss = Object.entries(fonts).map(([f, [fam, w]]) =>
  `@font-face{font-family:'${fam}';font-style:normal;font-weight:${w};font-display:block;src:url(https://fonts.gstatic.com/local/${f}) format('woff2')}`).join('\n');
const types = { '.html': 'text/html; charset=utf-8', '.jpg': 'image/jpeg', '.png': 'image/png', '.json': 'application/json', '.webp': 'image/webp' };

// tiny static server for the demo folder so relative image paths resolve
const server = http.createServer((req, res) => {
  const p = path.join(BASE, decodeURIComponent(req.url.split('?')[0]));
  if (!p.startsWith(BASE) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.statusCode = 404; return res.end(); }
  res.setHeader('Content-Type', types[path.extname(p).toLowerCase()] || 'application/octet-stream');
  fs.createReadStream(p).pipe(res);
});

(async () => {
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  const port = server.address().port;
  const launch = { args: ['--no-sandbox'] };
  if (process.env.CHROMIUM) launch.executablePath = process.env.CHROMIUM;
  const browser = await chromium.launch(launch);
  const ctx = await browser.newContext({ viewport: { width: 1056, height: 816 } });
  const haveFonts = fs.existsSync(FONTSOURCE);
  if (haveFonts) {
    await ctx.route('https://fonts.googleapis.com/**', r => r.fulfill({ body: fontCss, contentType: 'text/css' }));
    await ctx.route('https://fonts.gstatic.com/local/**', r => {
      const f = r.request().url().split('/').pop(); const e = fonts[f];
      const file = e && path.join(FONTSOURCE, e[2], 'files', f);
      return file && fs.existsSync(file) ? r.fulfill({ path: file, contentType: 'font/woff2' }) : r.abort();
    });
  }
  const page = await ctx.newPage();
  await page.goto(`http://127.0.0.1:${port}/index.html`, { waitUntil: 'networkidle' });
  await page.emulateMedia({ media: 'print' });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForFunction(() => [...document.images].every(i => i.complete), null, { timeout: 60000 });
  const loaded = await page.evaluate(() => [...document.fonts].filter(f => f.status === 'loaded').map(f => f.family + ' ' + f.weight));
  const imgs = await page.evaluate(() => [...document.images].filter(i => i.naturalWidth === 0).map(i => i.getAttribute('src')));
  await page.pdf({ path: OUT, width: '11in', height: '8.5in', printBackground: true, preferCSSPageSize: true, margin: { top: 0, right: 0, bottom: 0, left: 0 } });
  await browser.close();
  server.close();
  console.log(`Wrote ${OUT} (${(fs.statSync(OUT).size / 1048576).toFixed(1)} MB). Fonts: ${loaded.join(', ') || 'system fallback'}.` + (imgs.length ? ` Missing images: ${imgs.join(', ')}` : ''));
})().catch(e => { console.error(e); server.close(); process.exit(1); });
