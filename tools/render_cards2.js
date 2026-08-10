// Renders horizontal post cards (1280x720) from tools/case-cards-2.html into PNGs.
// Серия 2 кейсов (case-14..case-30). Копия render_cards.js с другим источником.
// Usage: node tools/render_cards2.js
// Output: case-images/<data-name>.png

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const HTML_FILE = path.resolve(__dirname, 'case-cards-2.html');
const URL = 'file:///' + HTML_FILE.replace(/\\/g, '/');
const OUT_DIR = path.resolve(__dirname, '..', 'case-images');

(async () => {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({
    viewport: { width: 1360, height: 820 },
    deviceScaleFactor: 2
  });

  console.log('Loading', URL);
  await page.goto(URL, { waitUntil: 'networkidle' });

  const cards = page.locator('.card');
  const count = await cards.count();
  console.log(`Found ${count} cards.`);

  for (let i = 0; i < count; i++) {
    const el = cards.nth(i);
    const name = await el.getAttribute('data-name');
    const file = path.join(OUT_DIR, `${name}.png`);
    await el.screenshot({ path: file });
    console.log(`  ${name}.png`);
  }

  await browser.close();
  console.log(`Done. ${count} files in ${OUT_DIR}`);
})().catch(err => {
  console.error(err);
  process.exit(1);
});
