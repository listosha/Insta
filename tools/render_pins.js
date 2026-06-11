// Renders Pinterest pin SVGs into PNGs at 1000x1500 (2:3, стандартный пин).
// Источник — tools/pins-pinterest.html: каждый пин = <svg data-slug="...">.
// Usage: node tools/render_pins.js
// Output: images/pins/<slug>.png

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// Usage: node tools/render_pins.js [html-file] [out-subdir]
//   html-file:  шаблон в tools/ (по умолч. pins-pinterest.html)
//   out-subdir: подпапка в images/ (по умолч. pins)
const HTML = path.resolve(__dirname, process.argv[2] || 'pins-pinterest.html');
const URL = 'file:///' + HTML.replace(/\\/g, '/');
const OUT = path.resolve(__dirname, '..', 'images', process.argv[3] || 'pins');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1000, height: 1500 }, deviceScaleFactor: 1 });
  await page.goto(URL, { waitUntil: 'networkidle' });

  const pins = await page.evaluate(() =>
    Array.from(document.querySelectorAll('svg[data-slug]')).map(svg => ({
      slug: svg.getAttribute('data-slug'),
      svg: svg.outerHTML,
    }))
  );
  console.log(`Found ${pins.length} pins.`);

  fs.mkdirSync(OUT, { recursive: true });
  for (const pin of pins) {
    const html = `<!DOCTYPE html><html><head><meta charset="utf-8">
      <link rel="preconnect" href="https://fonts.googleapis.com">
      <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
      <link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&display=swap" rel="stylesheet">
      <style>
      html,body{margin:0;padding:0;background:#fff}
      svg{display:block;width:1000px;height:1500px}
    </style></head><body>${pin.svg}</body></html>`;
    await page.setContent(html, { waitUntil: 'networkidle' });
    try { await page.evaluate(() => document.fonts.ready); } catch {}
    const file = path.join(OUT, `${pin.slug}.png`);
    await page.locator('svg').screenshot({ path: file, omitBackground: false });
    console.log(`  pins/${pin.slug}.png`);
  }

  await browser.close();
  console.log('Done.');
})().catch(err => { console.error(err); process.exit(1); });
