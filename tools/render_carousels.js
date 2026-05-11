// Renders carousel HTML template into per-slide PNGs at 1080x1350.
// Usage: node tools/render_carousels.js <html-file> <first-series-id>
//   html-file:        path to the carousel HTML (contains a SERIES array)
//   first-series-id:  numeric id of first folder, e.g. 25 -> series-25-, 26 -> series-26-, ...
//
// Output: images/series-NN-/slide-MM.png

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const HTML_FILE = process.argv[2];
const FIRST_ID = parseInt(process.argv[3], 10);

if (!HTML_FILE || !FIRST_ID) {
  console.error('Usage: node render_carousels.js <html-file> <first-series-id>');
  process.exit(1);
}

const ABS_HTML = path.resolve(HTML_FILE);
const URL = 'file:///' + ABS_HTML.replace(/\\/g, '/');
const OUT_ROOT = path.resolve(__dirname, '..', 'images');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({
    viewport: { width: 1080, height: 1350 },
    deviceScaleFactor: 1
  });

  console.log('Loading', URL);
  await page.goto(URL, { waitUntil: 'networkidle' });

  const slidesData = await page.evaluate(() => {
    const out = [];
    const sections = document.querySelectorAll('.series');
    sections.forEach((section, sIdx) => {
      const slides = section.querySelectorAll('.slide-wrap svg');
      slides.forEach((svg, idx) => {
        out.push({ seriesIdx: sIdx, slideIdx: idx, svg: svg.outerHTML });
      });
    });
    return out;
  });

  console.log(`Found ${slidesData.length} slides across ${new Set(slidesData.map(s => s.seriesIdx)).size} series.`);

  for (const item of slidesData) {
    const seriesId = FIRST_ID + item.seriesIdx;
    const folderName = `series-${String(seriesId).padStart(2, '0')}-`;
    const slideName = `slide-${String(item.slideIdx + 1).padStart(2, '0')}.png`;
    const folderPath = path.join(OUT_ROOT, folderName);
    const filePath = path.join(folderPath, slideName);

    fs.mkdirSync(folderPath, { recursive: true });

    const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><style>
      html,body{margin:0;padding:0;background:#fff}
      svg{display:block;width:1080px;height:1350px}
    </style></head><body>${item.svg}</body></html>`;

    await page.setContent(html, { waitUntil: 'load' });
    await page.locator('svg').screenshot({ path: filePath, omitBackground: false });
    console.log(`  ${folderName}/${slideName}`);
  }

  await browser.close();
  console.log('Done.');
})().catch(err => {
  console.error(err);
  process.exit(1);
});
